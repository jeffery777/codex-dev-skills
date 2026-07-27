#!/usr/bin/env python3
"""Run one bounded Codex CLI start or resume handoff.

The executor consumes a versioned JSON request and emits one redacted JSON
receipt. It relies only on the documented stable ``codex exec --json`` surface.
It never reads private Codex session state and never treats child output as
repository completion evidence.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import pathlib
import re
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, BinaryIO, Callable


ADAPTER_VERSION = "0.1.0"
CONTRACT = "codex-cli-session-handoff/v0"
REQUEST_SCHEMA_VERSION = 1
AUTHORIZATION_MARKER = "human-approved-single-cli-session-handoff"
HANDOFF_DEPTH_ENV = "CODEX_CLI_HANDOFF_DEPTH"
PROMPT_BOUNDARY_VERSION = "no-publication-no-recursion/v0"
PROMPT_BOUNDARY_APPENDIX = """

Runtime handoff boundaries:
- Do not commit.
- Do not push.
- Do not open pull requests.
- Do not merge.
- Do not perform platform writes.
- Do not dispatch another session.
- Return changed files, verification evidence, questions, and residual risk to the parent.
""".strip()

ALLOWED_OPERATIONS = {"start", "resume"}
ALLOWED_SANDBOXES = {"read-only", "workspace-write"}
ALLOWED_REQUEST_FIELDS = {
    "schema_version",
    "operation",
    "codex_executable",
    "workspace",
    "prompt",
    "sandbox",
    "timeout_seconds",
    "expected_head",
    "session_id",
    "prompt_boundary_version",
    "authorization",
}
ALLOWED_AUTHORIZATION_FIELDS = {
    "marker",
    "runtime_session_mutation_authorized",
    "sandbox_ceiling",
    "external_write_authorized",
    "destructive_action_approved",
}
MAX_PROMPT_BYTES = 64 * 1024
MAX_STDOUT_BYTES = 1024 * 1024
MAX_STDERR_BYTES = 256 * 1024
MAX_JSONL_LINE_BYTES = 64 * 1024
MAX_EVENTS = 4096
MAX_PATCH_BYTES = 16 * 1024 * 1024
MIN_TIMEOUT_SECONDS = 5
MAX_TIMEOUT_SECONDS = 3600
VERSION_TIMEOUT_SECONDS = 10
MAX_VERSION_STDOUT_BYTES = 1024
MAX_VERSION_STDERR_BYTES = 16 * 1024
TERMINATION_GRACE_SECONDS = 2
PROCESS_TREE_POLL_SECONDS = 0.02
MAX_TRACKED_DESCENDANTS = 1024
SHELL_ENVIRONMENT_CONFIG = (
    'shell_environment_policy.inherit="core"',
    "shell_environment_policy.ignore_default_excludes=false",
)
GIT_TARGETING_ENVIRONMENT_KEYS = frozenset(
    {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_CEILING_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_DIR",
        "GIT_DISCOVERY_ACROSS_FILESYSTEM",
        "GIT_INDEX_FILE",
        "GIT_NAMESPACE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_PREFIX",
        "GIT_WORK_TREE",
    }
)
GIT_TARGETING_ENVIRONMENT_PREFIXES = (
    "GIT_CONFIG_KEY_",
    "GIT_CONFIG_VALUE_",
)

HEX_HEAD_RE = re.compile(r"^[0-9a-f]{40}$")
CLI_VERSION_RE = re.compile(
    r"^codex-cli\s+([0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?)$"
)
SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{12,}\b"),
    re.compile(
        r"(?i)\b(?:[A-Z0-9]+[_-])*(?:"
        r"api[_-]?key|access[_-]?key(?:[_-]?id)?|"
        r"secret[_-]?access[_-]?key|access[_-]?token|"
        r"refresh[_-]?token|session[_-]?token|token|secret|"
        r"password|passwd|private[_-]?key|credential)"
        r"\b\s*[:=]\s*[^\s,;]+"
    ),
)
OMITTED_FINAL_SUMMARY = "<omitted-untrusted-child-summary>"
FORBIDDEN_PROMPT_PATTERNS = (
    re.compile(r"(?i)(?:--dangerously-bypass-approvals-and-sandbox|danger-full-access)"),
    re.compile(r"(?i)(?:~|/)[^\s]*\.codex/(?:auth\.json|sessions?|history\.jsonl)"),
    re.compile(
        r"(?i)[A-Z]:\\[^\s]*\\\.codex\\(?:auth\.json|sessions?|history\.jsonl)"
    ),
)


class HandoffValidationError(ValueError):
    """Raised when the request cannot safely reach a runtime call."""

    def __init__(self, failure_class: str, message: str) -> None:
        super().__init__(message)
        self.failure_class = failure_class


class DuplicateJsonKeyError(ValueError):
    """Raised when JSON input contains duplicate object keys."""


@dataclass(frozen=True)
class ValidatedRequest:
    operation: str
    executable: pathlib.Path
    executable_sha256: str
    cli_version: str
    workspace: pathlib.Path
    workspace_label: str
    expected_head: str
    prompt: str
    sandbox: str
    timeout_seconds: int
    session_id: str | None


@dataclass
class Capture:
    stdout: bytearray
    stdout_bytes: int = 0
    stderr_bytes: int = 0
    overflow_stream: str | None = None


class ProcessTreeTracker:
    """Track descendants even after they leave the original process group."""

    def __init__(self, root_pid: int) -> None:
        self.root_pid = root_pid
        self._known: dict[int, str] = {}
        self._root_token: str | None = None
        self._error = False
        self._overflow = False
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def capture(self) -> None:
        with self._lock:
            known = dict(self._known)
        if self._root_token is None:
            try:
                root_identity = _process_identity(self.root_pid)
            except OSError:
                with self._lock:
                    self._error = True
                return
            if root_identity is None:
                return
            self._root_token = root_identity[1]
        parents = [(self.root_pid, self._root_token), *known.items()]
        visited: set[tuple[int, str]] = set()
        discovered: dict[int, str] = {}
        try:
            while parents:
                parent, parent_token = parents.pop()
                parent_identity = _process_identity(parent)
                if (
                    parent_identity is None
                    or parent_identity[1] != parent_token
                    or (parent, parent_token) in visited
                ):
                    continue
                visited.add((parent, parent_token))
                for child in _direct_child_pids(parent):
                    if child <= 0 or child == self.root_pid:
                        continue
                    child_identity = _process_identity(child)
                    if child_identity is None or child_identity[0] != parent:
                        continue
                    child_token = child_identity[1]
                    if discovered.get(child) != child_token:
                        discovered[child] = child_token
                        parents.append((child, child_token))
                    if len(discovered) > MAX_TRACKED_DESCENDANTS:
                        with self._lock:
                            self._overflow = True
                        return
        except OSError:
            with self._lock:
                self._error = True
            return
        with self._lock:
            self._known.update(discovered)

    def start(self) -> None:
        self.capture()
        self.ensure_available()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=TERMINATION_GRACE_SECONDS)
            if self._thread.is_alive():
                with self._lock:
                    self._error = True

    def snapshot(self) -> dict[int, str]:
        with self._lock:
            return dict(self._known)

    def live_descendants(self) -> set[int]:
        live: set[int] = set()
        try:
            for pid, token in self.snapshot().items():
                identity = _process_identity(pid)
                if identity is not None and identity[1] == token:
                    live.add(pid)
        except OSError:
            with self._lock:
                self._error = True
        return live

    def ensure_available(self) -> None:
        with self._lock:
            error = self._error
            overflow = self._overflow
        if error:
            raise HandoffValidationError(
                "termination_error",
                "Process-tree inventory became unavailable.",
            )
        if overflow:
            raise HandoffValidationError(
                "termination_error",
                "Process-tree inventory exceeded the bounded descendant limit.",
            )

    def _run(self) -> None:
        while not self._stop.wait(PROCESS_TREE_POLL_SECONDS):
            self.capture()


def _base_receipt(
    request: dict[str, Any] | None,
    *,
    status: str,
    failure_class: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    raw_operation = request.get("operation") if isinstance(request, dict) else None
    operation = (
        raw_operation
        if isinstance(raw_operation, str) and raw_operation in ALLOWED_OPERATIONS
        else None
    )
    raw_head = request.get("expected_head") if isinstance(request, dict) else None
    expected_head = (
        raw_head.lower()
        if isinstance(raw_head, str) and HEX_HEAD_RE.fullmatch(raw_head.lower())
        else None
    )
    return {
        "contract": CONTRACT,
        "adapter_version": ADAPTER_VERSION,
        "status": status,
        "failure_class": failure_class,
        "message": message,
        "operation": operation,
        "capability": {
            "kind": "cli-session",
            "source": "documented-codex-exec-json",
            "version_probe_performed": False,
            "cli_version": None,
            "executable_sha256": None,
        },
        "target": {
            "workspace": None,
            "expected_head": expected_head,
            "observed_head": None,
        },
        "result": {
            "session_id": None,
            "terminal_event": None,
            "exit_status": None,
            "final_summary": None,
        },
        "boundaries": {
            "session_call_performed": False,
            "shell_used": False,
            "raw_transcript_persisted": False,
            "private_runtime_state_read": False,
            "child_workspace_isolated": False,
            "child_summary_omitted": False,
            "adapter_repository_write_performed": False,
            "adapter_platform_write_performed": False,
            "child_platform_write_status": "not-observed",
            "repository_completion_claimed": False,
            "parent_integration_required": True,
        },
    }


def _stop(
    request: dict[str, Any] | None,
    failure_class: str,
    message: str,
    *,
    fallback: bool = False,
) -> dict[str, Any]:
    return _base_receipt(
        request,
        status="fallback" if fallback else "stopped",
        failure_class=failure_class,
        message=message,
    )


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HandoffValidationError(
            "validation_error", f"{field} must be a JSON object."
        )
    return value


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandoffValidationError(
            "validation_error", f"{field} must be a non-empty string."
        )
    if "\x00" in value:
        raise HandoffValidationError(
            "validation_error", f"{field} must not contain NUL bytes."
        )
    return value


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError("duplicate JSON object key")
        result[key] = value
    return result


def _is_relative_to(path: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _sha256_file(path: pathlib.Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as exc:
        raise HandoffValidationError(
            "capability_unavailable",
            "Codex executable could not be measured safely.",
        ) from exc


def _canonical_regular_executable(raw: Any, workspace: pathlib.Path) -> pathlib.Path:
    value = _require_string(raw, "codex_executable")
    if any(token in value for token in ("~", "$")):
        raise HandoffValidationError(
            "capability_unavailable",
            "codex_executable must not use shell or environment expansion.",
        )
    candidate = pathlib.Path(value)
    if not candidate.is_absolute():
        raise HandoffValidationError(
            "capability_unavailable", "codex_executable must be absolute."
        )
    try:
        resolved = candidate.resolve(strict=True)
        mode = resolved.stat().st_mode
    except OSError as exc:
        raise HandoffValidationError(
            "capability_unavailable", "codex_executable is unavailable."
        ) from exc
    if not stat.S_ISREG(mode) or not os.access(resolved, os.X_OK):
        raise HandoffValidationError(
            "capability_unavailable",
            "codex_executable must resolve to an executable regular file.",
        )
    if _is_relative_to(resolved, workspace):
        raise HandoffValidationError(
            "capability_unavailable",
            "codex_executable must not be controlled by the target repository.",
        )
    return resolved


def _canonical_workspace(raw: Any) -> pathlib.Path:
    value = _require_string(raw, "workspace")
    if any(token in value for token in ("~", "$")):
        raise HandoffValidationError(
            "target_mismatch",
            "workspace must not use shell or environment expansion.",
        )
    candidate = pathlib.Path(value)
    if not candidate.is_absolute():
        raise HandoffValidationError(
            "target_mismatch", "workspace must be absolute."
        )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise HandoffValidationError(
            "target_mismatch", "workspace is unavailable."
        ) from exc
    if not resolved.is_dir():
        raise HandoffValidationError(
            "target_mismatch", "workspace must resolve to a directory."
        )
    return resolved


def _native_git(workspace: pathlib.Path) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if os.name == "nt":
        path_value = os.environ.get("PATH", "")
        for part in path_value.split(os.pathsep):
            if part:
                candidates.append(pathlib.Path(part) / "git.exe")
    else:
        candidates.extend((pathlib.Path("/usr/bin/git"), pathlib.Path("/bin/git")))
        path_value = os.environ.get("PATH", "")
        for part in path_value.split(os.pathsep):
            if part:
                candidates.append(pathlib.Path(part) / "git")

    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            mode = resolved.stat().st_mode
        except OSError:
            continue
        if (
            stat.S_ISREG(mode)
            and os.access(resolved, os.X_OK)
            and not _is_relative_to(resolved, workspace)
        ):
            return resolved
    raise HandoffValidationError(
        "capability_unavailable", "A native Git executable is required."
    )


def _run_git(git: pathlib.Path, workspace: pathlib.Path, *args: str) -> str:
    try:
        result = subprocess.run(
            [str(git), "-C", str(workspace), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
            shell=False,
            env=_isolated_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git target validation failed."
        ) from exc
    if result.returncode != 0 or len(result.stdout) > 64 * 1024:
        raise HandoffValidationError(
            "target_mismatch", "Git target validation did not complete safely."
        )
    try:
        return result.stdout.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git target output was not valid UTF-8."
        ) from exc


def _git_config_is_true(
    git: pathlib.Path,
    workspace: pathlib.Path,
    key: str,
) -> bool:
    try:
        result = subprocess.run(
            [str(git), "-C", str(workspace), "config", "--bool", "--get", key],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
            shell=False,
            env=_isolated_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git worktree-mode validation failed."
        ) from exc
    if result.returncode == 1:
        return False
    if result.returncode != 0:
        raise HandoffValidationError(
            "target_mismatch", "Git worktree-mode validation failed."
        )
    try:
        value = result.stdout.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git worktree-mode validation failed."
        ) from exc
    if value not in {"true", "false"}:
        raise HandoffValidationError(
            "target_mismatch", "Git worktree-mode validation failed."
        )
    return value == "true"


def _workspace_has_gitlinks(
    git: pathlib.Path,
    workspace: pathlib.Path,
) -> bool:
    try:
        process = subprocess.Popen(
            [str(git), "-C", str(workspace), "ls-files", "--stage"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=os.name == "posix",
            env=_isolated_git_environment(),
        )
    except OSError as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git submodule validation failed."
        ) from exc
    assert process.stdout is not None
    observed: list[bytes] = []

    def read_index() -> None:
        try:
            observed.append(process.stdout.read(MAX_PATCH_BYTES + 1))
        except OSError:
            observed.append(b"")

    reader = threading.Thread(target=read_index, daemon=True)
    reader.start()
    reader.join(timeout=10)
    if reader.is_alive():
        _terminate_original_process_group(process)
        reader.join(timeout=TERMINATION_GRACE_SECONDS)
        process.stdout.close()
        raise HandoffValidationError(
            "target_mismatch", "Git submodule validation timed out."
        )
    output = observed[0] if observed else b""
    if len(output) > MAX_PATCH_BYTES:
        _terminate_original_process_group(process)
        process.stdout.close()
        raise HandoffValidationError(
            "capability_unavailable",
            "Git index exceeded the bounded submodule-validation limit.",
        )
    try:
        returncode = process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _terminate_original_process_group(process)
        process.stdout.close()
        raise HandoffValidationError(
            "target_mismatch", "Git submodule validation did not terminate safely."
        ) from exc
    process.stdout.close()
    if returncode != 0:
        raise HandoffValidationError(
            "target_mismatch", "Git submodule validation failed."
        )
    return any(line.startswith(b"160000 ") for line in output.splitlines())


def _workspace_identity(workspace: pathlib.Path, expected_head: Any) -> tuple[str, str]:
    head = _require_string(expected_head, "expected_head").lower()
    if not HEX_HEAD_RE.fullmatch(head):
        raise HandoffValidationError(
            "target_mismatch", "expected_head must be a full 40-character Git SHA."
        )
    git = _native_git(workspace)
    top_level_raw = _run_git(git, workspace, "rev-parse", "--show-toplevel")
    try:
        top_level = pathlib.Path(top_level_raw).resolve(strict=True)
    except OSError as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git top-level path is unavailable."
        ) from exc
    if top_level != workspace:
        raise HandoffValidationError(
            "target_mismatch",
            "workspace must be the exact canonical Git worktree root.",
        )
    observed_head = _run_git(git, workspace, "rev-parse", "HEAD").lower()
    if observed_head != head:
        raise HandoffValidationError(
            "target_mismatch",
            "workspace HEAD does not match expected_head.",
        )
    if _git_config_is_true(git, workspace, "core.sparseCheckout"):
        raise HandoffValidationError(
            "capability_unavailable",
            "Sparse-checkout worktrees are not qualified for isolated handoff.",
        )
    if _workspace_has_gitlinks(git, workspace):
        raise HandoffValidationError(
            "capability_unavailable",
            "Worktrees with Git submodules are not qualified for isolated handoff.",
        )
    if _workspace_is_dirty(git, workspace):
        raise HandoffValidationError(
            "dirty_workspace",
            "workspace must be clean before a CLI session handoff.",
        )
    path_digest = hashlib.sha256(str(workspace).encode("utf-8")).hexdigest()
    label = f"git-worktree:{path_digest[:12]}"
    return observed_head, label


def _git_quiet_status(
    git: pathlib.Path, workspace: pathlib.Path, *args: str
) -> bool:
    try:
        result = subprocess.run(
            [str(git), "-C", str(workspace), *args],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
            shell=False,
            env=_isolated_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git dirty-state validation failed."
        ) from exc
    if result.returncode == 0:
        return False
    if result.returncode == 1:
        return True
    raise HandoffValidationError(
        "target_mismatch", "Git dirty-state validation failed."
    )


def _git_has_untracked(git: pathlib.Path, workspace: pathlib.Path) -> bool:
    creationflags = 0
    start_new_session = os.name == "posix"
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(
            [
                str(git),
                "-C",
                str(workspace),
                "ls-files",
                "--others",
                "--exclude-standard",
                "--directory",
                "--no-empty-directory",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=start_new_session,
            creationflags=creationflags,
            env=_isolated_git_environment(),
        )
    except OSError as exc:
        raise HandoffValidationError(
            "target_mismatch", "Git untracked-file validation failed."
        ) from exc
    assert process.stdout is not None
    observed: list[bytes] = []

    def read_one() -> None:
        try:
            observed.append(process.stdout.read(1))
        except OSError:
            observed.append(b"")

    reader = threading.Thread(target=read_one, daemon=True)
    reader.start()
    reader.join(timeout=10)
    if reader.is_alive():
        _terminate_process_group(process)
        reader.join(timeout=TERMINATION_GRACE_SECONDS)
        process.stdout.close()
        raise HandoffValidationError(
            "target_mismatch", "Git untracked-file validation timed out."
        )
    if observed and observed[0]:
        process.stdout.close()
        try:
            process.wait(timeout=TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process)
        return True
    try:
        returncode = process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        process.stdout.close()
        raise HandoffValidationError(
            "target_mismatch", "Git untracked-file validation timed out."
        ) from exc
    process.stdout.close()
    if returncode != 0:
        raise HandoffValidationError(
            "target_mismatch", "Git untracked-file validation failed."
        )
    return False


def _workspace_is_dirty(git: pathlib.Path, workspace: pathlib.Path) -> bool:
    if _git_quiet_status(
        git,
        workspace,
        "diff",
        "--quiet",
        "--no-ext-diff",
        "--ignore-submodules",
        "--",
    ):
        return True
    if _git_quiet_status(
        git,
        workspace,
        "diff",
        "--cached",
        "--quiet",
        "--no-ext-diff",
        "--ignore-submodules",
        "--",
    ):
        return True
    return _git_has_untracked(git, workspace)


def _authorization(request: dict[str, Any], sandbox: str) -> None:
    authorization = _require_object(request.get("authorization"), "authorization")
    unknown_fields = set(authorization) - ALLOWED_AUTHORIZATION_FIELDS
    if unknown_fields:
        raise HandoffValidationError(
            "validation_error",
            "authorization contains unknown field(s).",
        )
    if authorization.get("marker") != AUTHORIZATION_MARKER:
        raise HandoffValidationError(
            "authorization_missing",
            "The exact single-session authorization marker is required.",
        )
    if authorization.get("runtime_session_mutation_authorized") is not True:
        raise HandoffValidationError(
            "authorization_missing",
            "runtime_session_mutation_authorized must be true.",
        )
    if authorization.get("external_write_authorized") is not False:
        raise HandoffValidationError(
            "external_write_request",
            "external_write_authorized must be explicitly false.",
        )
    if authorization.get("destructive_action_approved") is not False:
        raise HandoffValidationError(
            "destructive_action_request",
            "destructive_action_approved must be explicitly false.",
        )
    ceiling = authorization.get("sandbox_ceiling")
    if ceiling not in ALLOWED_SANDBOXES:
        raise HandoffValidationError(
            "authorization_missing",
            "authorization.sandbox_ceiling must be read-only or workspace-write.",
        )
    if ceiling == "read-only" and sandbox != "read-only":
        raise HandoffValidationError(
            "permission_widening",
            "The requested sandbox exceeds the authorized ceiling.",
        )


def _validate_prompt(raw: Any) -> str:
    prompt = _require_string(raw, "prompt")
    encoded = prompt.encode("utf-8")
    if len(encoded) > MAX_PROMPT_BYTES:
        raise HandoffValidationError(
            "validation_error",
            f"prompt exceeds {MAX_PROMPT_BYTES} UTF-8 bytes.",
        )
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(prompt):
            raise HandoffValidationError(
                "sensitive_input",
                "prompt appears to contain a credential or secret.",
            )
    for pattern in FORBIDDEN_PROMPT_PATTERNS:
        if pattern.search(prompt):
            raise HandoffValidationError(
                "forbidden_prompt",
                "prompt requests a forbidden permission, private-state, or recursive-session action.",
            )
    return prompt


def _validate_session_id(operation: str, raw: Any) -> str | None:
    if operation == "start":
        if raw not in (None, ""):
            raise HandoffValidationError(
                "validation_error", "session_id is allowed only for resume."
            )
        return None
    value = _require_string(raw, "session_id")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise HandoffValidationError(
            "target_mismatch", "resume session_id must be an exact UUID."
        ) from exc
    canonical = str(parsed)
    if value.lower() != canonical:
        raise HandoffValidationError(
            "target_mismatch", "resume session_id must use canonical UUID form."
        )
    return canonical


def _probe_version(executable: pathlib.Path) -> str:
    environment = _environment_without_git_targeting()
    environment["NO_COLOR"] = "1"
    environment.pop("OLDPWD", None)
    creationflags = 0
    start_new_session = os.name == "posix"
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    capture = Capture(stdout=bytearray())
    lock = threading.Lock()
    with tempfile.TemporaryDirectory(prefix="codex-version-probe-") as temp_root:
        environment["PWD"] = temp_root
        try:
            process = subprocess.Popen(
                [str(executable), "--version"],
                cwd=temp_root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                start_new_session=start_new_session,
                creationflags=creationflags,
                env=environment,
            )
        except OSError as exc:
            raise HandoffValidationError(
                "capability_unavailable", "Codex version probe failed."
            ) from exc
        assert process.stdout is not None
        assert process.stderr is not None
        tracker = ProcessTreeTracker(process.pid)
        readers = [
            threading.Thread(
                target=_capture_reader,
                args=(process.stdout, capture),
                kwargs={
                    "stream_name": "stdout",
                    "limit": MAX_VERSION_STDOUT_BYTES,
                    "lock": lock,
                },
                daemon=True,
            ),
            threading.Thread(
                target=_capture_reader,
                args=(process.stderr, capture),
                kwargs={
                    "stream_name": "stderr",
                    "limit": MAX_VERSION_STDERR_BYTES,
                    "lock": lock,
                },
                daemon=True,
            ),
        ]
        try:
            tracker.start()
            for reader in readers:
                reader.start()
            deadline = time.monotonic() + VERSION_TIMEOUT_SECONDS
            while process.poll() is None:
                with lock:
                    overflow = capture.overflow_stream
                if overflow is not None or time.monotonic() >= deadline:
                    _terminate_process_group(process, tracker)
                    break
                time.sleep(0.02)
        except HandoffValidationError:
            _terminate_original_process_group(process)
            raise
        except KeyboardInterrupt as exc:
            _terminate_process_group(process, tracker)
            raise HandoffValidationError(
                "interrupted",
                "Codex version probe was interrupted and terminated.",
            ) from exc
        finally:
            cleanup_error: HandoffValidationError | None = None
            try:
                tracker.capture()
                if process.poll() is None or tracker.live_descendants():
                    _terminate_process_group(process, tracker)
            except HandoffValidationError as exc:
                cleanup_error = exc
            tracker.stop()
            try:
                tracker.ensure_available()
            except HandoffValidationError as exc:
                if cleanup_error is None:
                    cleanup_error = exc
            for reader in readers:
                if reader.ident is not None:
                    reader.join(timeout=TERMINATION_GRACE_SECONDS)
            process.stdout.close()
            process.stderr.close()
            if cleanup_error is not None:
                raise cleanup_error
        if any(reader.is_alive() for reader in readers):
            raise HandoffValidationError(
                "capability_unavailable",
                "Codex version probe I/O did not terminate safely.",
            )
        with lock:
            output = bytes(capture.stdout)
            overflow = capture.overflow_stream
        returncode = process.returncode
    if returncode != 0 or overflow is not None:
        raise HandoffValidationError(
            "capability_unavailable", "Codex version probe did not complete safely."
        )
    try:
        output_text = output.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise HandoffValidationError(
            "capability_unavailable", "Codex version output was not valid UTF-8."
        ) from exc
    match = CLI_VERSION_RE.fullmatch(output_text)
    if match is None:
        raise HandoffValidationError(
            "capability_unavailable",
            "Codex version output did not match the documented CLI identity.",
        )
    return match.group(1)


def validate_request(request: dict[str, Any]) -> ValidatedRequest:
    if os.name != "posix" or not (
        sys.platform == "darwin" or sys.platform.startswith("linux")
    ):
        raise HandoffValidationError(
            "capability_unavailable",
            "The initial CLI session adapter is qualified only on macOS and Linux.",
        )
    try:
        _direct_child_pids(os.getpid())
    except OSError as exc:
        raise HandoffValidationError(
            "capability_unavailable",
            "Process-tree inventory is unavailable on this host.",
        ) from exc
    unknown_fields = set(request) - ALLOWED_REQUEST_FIELDS
    if unknown_fields:
        raise HandoffValidationError(
            "validation_error",
            "request contains unknown field(s).",
        )
    if (
        isinstance(request.get("schema_version"), bool)
        or request.get("schema_version") != REQUEST_SCHEMA_VERSION
    ):
        raise HandoffValidationError(
            "validation_error",
            f"schema_version must be {REQUEST_SCHEMA_VERSION}.",
        )
    operation = _require_string(request.get("operation"), "operation")
    if operation not in ALLOWED_OPERATIONS:
        raise HandoffValidationError(
            "validation_error", "operation must be start or resume."
        )
    workspace = _canonical_workspace(request.get("workspace"))
    observed_head, workspace_label = _workspace_identity(
        workspace, request.get("expected_head")
    )
    executable = _canonical_regular_executable(
        request.get("codex_executable"), workspace
    )
    sandbox = _require_string(request.get("sandbox"), "sandbox")
    if sandbox not in ALLOWED_SANDBOXES:
        raise HandoffValidationError(
            "permission_widening",
            "sandbox must be read-only or workspace-write.",
        )
    _authorization(request, sandbox)
    if os.environ.get(HANDOFF_DEPTH_ENV):
        raise HandoffValidationError(
            "recursive_handoff",
            "Nested CLI session handoff is not allowed.",
        )
    timeout = request.get("timeout_seconds")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or not MIN_TIMEOUT_SECONDS <= timeout <= MAX_TIMEOUT_SECONDS
    ):
        raise HandoffValidationError(
            "validation_error",
            f"timeout_seconds must be an integer from {MIN_TIMEOUT_SECONDS} to {MAX_TIMEOUT_SECONDS}.",
        )
    if request.get("prompt_boundary_version") != PROMPT_BOUNDARY_VERSION:
        raise HandoffValidationError(
            "prompt_boundary_missing",
            f"prompt_boundary_version must be {PROMPT_BOUNDARY_VERSION}.",
        )
    prompt = (
        _validate_prompt(request.get("prompt")).rstrip()
        + "\n\n"
        + PROMPT_BOUNDARY_APPENDIX
    )
    session_id = _validate_session_id(operation, request.get("session_id"))
    executable_sha256 = _sha256_file(executable)
    cli_version = _probe_version(executable)
    return ValidatedRequest(
        operation=operation,
        executable=executable,
        executable_sha256=executable_sha256,
        cli_version=cli_version,
        workspace=workspace,
        workspace_label=workspace_label,
        expected_head=observed_head,
        prompt=prompt,
        sandbox=sandbox,
        timeout_seconds=timeout,
        session_id=session_id,
    )


def build_argv(
    request: ValidatedRequest,
    *,
    execution_workspace: pathlib.Path | None = None,
) -> list[str]:
    workspace = execution_workspace or request.workspace
    prefix = [
        str(request.executable),
        "--sandbox",
        request.sandbox,
        "--ask-for-approval",
        "never",
        "-c",
        SHELL_ENVIRONMENT_CONFIG[0],
        "-c",
        SHELL_ENVIRONMENT_CONFIG[1],
        "--cd",
        str(workspace),
        "exec",
    ]
    if request.operation == "start":
        return [*prefix, "--ignore-user-config", "--json", "-"]
    assert request.session_id is not None
    return [
        *prefix,
        "resume",
        "--ignore-user-config",
        "--json",
        request.session_id,
        "-",
    ]


def _capture_reader(
    stream: BinaryIO,
    capture: Capture,
    *,
    stream_name: str,
    limit: int,
    lock: threading.Lock,
) -> None:
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        with lock:
            if stream_name == "stdout":
                capture.stdout_bytes += len(chunk)
                if capture.stdout_bytes <= limit:
                    capture.stdout.extend(chunk)
                elif capture.overflow_stream is None:
                    capture.overflow_stream = stream_name
            else:
                capture.stderr_bytes += len(chunk)
                if (
                    capture.stderr_bytes > limit
                    and capture.overflow_stream is None
                ):
                    capture.overflow_stream = stream_name


def _prompt_writer(stream: BinaryIO, prompt: str) -> None:
    try:
        stream.write(prompt.encode("utf-8"))
        stream.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        try:
            stream.close()
        except OSError:
            pass


def _poll_sleep(seconds: float) -> None:
    time.sleep(seconds)


def _process_identity(pid: int) -> tuple[int, str] | None:
    """Return (parent PID, start token) for one live process."""

    if sys.platform == "darwin":
        import ctypes

        class ProcBsdInfo(ctypes.Structure):
            _fields_ = [
                ("pbi_flags", ctypes.c_uint32),
                ("pbi_status", ctypes.c_uint32),
                ("pbi_xstatus", ctypes.c_uint32),
                ("pbi_pid", ctypes.c_uint32),
                ("pbi_ppid", ctypes.c_uint32),
                ("pbi_uid", ctypes.c_uint32),
                ("pbi_gid", ctypes.c_uint32),
                ("pbi_ruid", ctypes.c_uint32),
                ("pbi_rgid", ctypes.c_uint32),
                ("pbi_svuid", ctypes.c_uint32),
                ("pbi_svgid", ctypes.c_uint32),
                ("rfu_1", ctypes.c_uint32),
                ("pbi_comm", ctypes.c_char * 16),
                ("pbi_name", ctypes.c_char * 32),
                ("pbi_nfiles", ctypes.c_uint32),
                ("pbi_pgid", ctypes.c_uint32),
                ("pbi_pjobc", ctypes.c_uint32),
                ("e_tdev", ctypes.c_uint32),
                ("e_tpgid", ctypes.c_uint32),
                ("pbi_nice", ctypes.c_int32),
                ("pbi_start_tvsec", ctypes.c_uint64),
                ("pbi_start_tvusec", ctypes.c_uint64),
            ]

        try:
            libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            process_info = libproc.proc_pidinfo
            process_info.argtypes = [
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_uint64,
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            process_info.restype = ctypes.c_int
            info = ProcBsdInfo()
            size = process_info(
                pid,
                3,  # PROC_PIDTBSDINFO
                0,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
        except (AttributeError, OSError) as exc:
            raise OSError("libproc process identity unavailable") from exc
        if size <= 0:
            if ctypes.get_errno() == errno.ESRCH:
                return None
            if not _pid_exists(pid):
                return None
            raise OSError("libproc process identity failed")
        if size != ctypes.sizeof(info) or int(info.pbi_pid) != pid:
            raise OSError("libproc process identity was malformed")
        return (
            int(info.pbi_ppid),
            f"{int(info.pbi_start_tvsec)}:{int(info.pbi_start_tvusec)}",
        )

    if sys.platform.startswith("linux"):
        try:
            raw = pathlib.Path(f"/proc/{pid}/stat").read_text(
                encoding="ascii", errors="strict"
            )
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError) as exc:
            if not _pid_exists(pid):
                return None
            raise OSError("procfs process identity failed") from exc
        closing_paren = raw.rfind(")")
        if closing_paren < 0:
            raise OSError("procfs process identity was malformed")
        try:
            observed_pid = int(raw[: raw.find("(")].strip())
            fields = raw[closing_paren + 1 :].split()
            parent_pid = int(fields[1])
            start_ticks = fields[19]
        except (ValueError, IndexError) as exc:
            raise OSError("procfs process identity was malformed") from exc
        if observed_pid != pid or not start_ticks.isdecimal():
            raise OSError("procfs process identity was malformed")
        return parent_pid, start_ticks

    raise OSError("unsupported process identity inventory")


def _direct_child_pids(parent_pid: int) -> set[int]:
    if sys.platform == "darwin":
        import ctypes

        try:
            libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
            list_children = libproc.proc_listchildpids
            list_children.argtypes = [
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            list_children.restype = ctypes.c_int
            buffer = (ctypes.c_int * MAX_TRACKED_DESCENDANTS)()
            count = list_children(
                parent_pid, buffer, ctypes.sizeof(buffer)
            )
        except (AttributeError, OSError) as exc:
            raise OSError("libproc child inventory unavailable") from exc
        if count < 0:
            if ctypes.get_errno() == errno.ESRCH:
                return set()
            if not _pid_exists(parent_pid):
                return set()
            raise OSError("libproc child inventory failed")
        if count > MAX_TRACKED_DESCENDANTS:
            raise OSError("libproc child inventory exceeded its bound")
        return {int(buffer[index]) for index in range(count) if buffer[index] > 0}

    if sys.platform.startswith("linux"):
        task_root = pathlib.Path(f"/proc/{parent_pid}/task")
        try:
            children_files = list(task_root.glob("*/children"))
        except OSError as exc:
            raise OSError("procfs child inventory failed") from exc
        if not children_files and not task_root.exists():
            return set()
        children: set[int] = set()
        for children_file in children_files:
            try:
                values = children_file.read_text(
                    encoding="ascii", errors="strict"
                ).split()
            except FileNotFoundError:
                continue
            except (OSError, UnicodeError) as exc:
                raise OSError("procfs child inventory failed") from exc
            for value in values:
                if not value.isdecimal():
                    raise OSError("procfs child inventory was malformed")
                children.add(int(value))
                if len(children) > MAX_TRACKED_DESCENDANTS:
                    raise OSError("procfs child inventory exceeded its bound")
        return children

    raise OSError("unsupported process-tree inventory")


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_pid(pid: int, token: str, sig: signal.Signals) -> None:
    try:
        identity = _process_identity(pid)
    except OSError as exc:
        raise HandoffValidationError(
            "termination_error",
            "A tracked descendant identity could not be verified.",
        ) from exc
    if identity is None or identity[1] != token:
        return
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return
    except PermissionError as exc:
        raise HandoffValidationError(
            "termination_error", "A tracked descendant could not be signaled."
        ) from exc


def _process_identity_matches(pid: int, token: str) -> bool:
    try:
        identity = _process_identity(pid)
    except OSError as exc:
        raise HandoffValidationError(
            "termination_error",
            "A tracked descendant identity could not be verified.",
        ) from exc
    return identity is not None and identity[1] == token


def _signal_process_group(
    process: subprocess.Popen[bytes], sig: signal.Signals
) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return
    except PermissionError as exc:
        if process.poll() is not None:
            return
        raise HandoffValidationError(
            "termination_error", "The Codex process group could not be signaled."
        ) from exc


def _wait_for_process_tree(
    process: subprocess.Popen[bytes],
    descendants: dict[int, str],
    timeout: float,
) -> tuple[bool, set[int]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        process_done = process.poll() is not None
        live = {
            pid
            for pid, token in descendants.items()
            if _process_identity_matches(pid, token)
        }
        if process_done and not live:
            return True, set()
        time.sleep(PROCESS_TREE_POLL_SECONDS)
    return process.poll() is not None, {
        pid
        for pid, token in descendants.items()
        if _process_identity_matches(pid, token)
    }


def _terminate_original_process_group(
    process: subprocess.Popen[bytes],
) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise HandoffValidationError(
            "termination_error",
            "The original Codex process group did not terminate safely.",
        ) from exc


def _terminate_process_group(
    process: subprocess.Popen[bytes],
    tracker: ProcessTreeTracker | None = None,
) -> None:
    active_tracker = tracker or ProcessTreeTracker(process.pid)
    inventory_error: HandoffValidationError | None = None

    def capture_descendants() -> dict[int, str]:
        nonlocal inventory_error
        active_tracker.capture()
        try:
            active_tracker.ensure_available()
        except HandoffValidationError as exc:
            inventory_error = exc
        return active_tracker.snapshot()

    descendants = capture_descendants()
    if inventory_error is not None:
        _terminate_original_process_group(process)
        for pid, token in descendants.items():
            _signal_pid(pid, token, signal.SIGKILL)
        raise inventory_error
    if process.poll() is not None and not any(
        _process_identity_matches(pid, token)
        for pid, token in descendants.items()
    ):
        return

    for pid, token in descendants.items():
        _signal_pid(pid, token, signal.SIGTERM)
    _signal_process_group(process, signal.SIGTERM)

    process_done, live = _wait_for_process_tree(
        process, descendants, TERMINATION_GRACE_SECONDS
    )
    if not process_done or live:
        for pid in live:
            _signal_pid(pid, descendants[pid], signal.SIGKILL)
        _signal_process_group(process, signal.SIGKILL)
        process_done, live = _wait_for_process_tree(
            process, descendants, TERMINATION_GRACE_SECONDS
        )
    if not process_done or live:
        raise HandoffValidationError(
            "termination_error",
            "The Codex process tree did not terminate within the bounded grace period.",
        )
    if inventory_error is not None:
        raise inventory_error


def _parse_jsonl(
    raw: bytes, request: ValidatedRequest
) -> tuple[str, str, str]:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise HandoffValidationError(
            "malformed_jsonl", "Codex JSONL output was not valid UTF-8."
        ) from exc
    session_ids: list[str] = []
    terminal_events: list[str] = []
    errors: list[str] = []
    summary_seen = False
    event_count = 0
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        if len(raw_line.encode("utf-8")) > MAX_JSONL_LINE_BYTES:
            raise HandoffValidationError(
                "output_limit", "Codex JSONL line exceeded the bounded limit."
            )
        event_count += 1
        if event_count > MAX_EVENTS:
            raise HandoffValidationError(
                "output_limit", "Codex JSONL event count exceeded the bounded limit."
            )
        try:
            event = json.loads(
                raw_line,
                object_pairs_hook=_strict_json_object,
            )
        except (json.JSONDecodeError, DuplicateJsonKeyError) as exc:
            raise HandoffValidationError(
                "malformed_jsonl", "Codex output contained a malformed JSONL event."
            ) from exc
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise HandoffValidationError(
                "malformed_jsonl", "Every Codex JSONL event must be a typed object."
            )
        event_type = event["type"]
        if terminal_events and event_type not in {"turn.completed", "turn.failed"}:
            raise HandoffValidationError(
                "malformed_jsonl",
                "No Codex JSONL event may follow the terminal turn event.",
            )
        if event_type == "thread.started":
            if terminal_events:
                raise HandoffValidationError(
                    "malformed_jsonl",
                    "thread.started must precede the terminal turn event.",
                )
            thread_id = event.get("thread_id")
            if not isinstance(thread_id, str):
                raise HandoffValidationError(
                    "malformed_jsonl", "thread.started lacked a string thread_id."
                )
            try:
                canonical = str(uuid.UUID(thread_id))
            except ValueError as exc:
                raise HandoffValidationError(
                    "malformed_jsonl", "thread.started emitted a non-UUID thread_id."
                ) from exc
            if canonical != thread_id.lower():
                raise HandoffValidationError(
                    "malformed_jsonl",
                    "thread.started emitted a non-canonical thread_id.",
                )
            session_ids.append(canonical)
        elif event_type in {"turn.completed", "turn.failed"}:
            if not session_ids:
                raise HandoffValidationError(
                    "malformed_jsonl",
                    "The terminal turn event must follow thread.started.",
                )
            terminal_events.append(event_type)
        elif event_type == "error":
            errors.append("error")
        elif event_type == "item.completed":
            item = event.get("item")
            if (
                isinstance(item, dict)
                and item.get("type") == "agent_message"
                and isinstance(item.get("text"), str)
            ):
                if not session_ids:
                    raise HandoffValidationError(
                        "malformed_jsonl",
                        "A completed agent message must follow thread.started.",
                    )
                summary_seen = True

    if len(session_ids) != 1:
        raise HandoffValidationError(
            "missing_or_duplicate_session_id",
            "Codex output must contain exactly one thread.started event.",
        )
    if len(terminal_events) != 1:
        raise HandoffValidationError(
            "missing_or_duplicate_terminal_event",
            "Codex output must contain exactly one terminal turn event.",
        )
    if errors or terminal_events[0] == "turn.failed":
        raise HandoffValidationError(
            "cli_reported_failure", "Codex JSONL reported a failed turn."
        )
    if not summary_seen:
        raise HandoffValidationError(
            "missing_final_summary",
            "Codex output did not contain a completed agent message.",
        )
    if (
        request.operation == "resume"
        and request.session_id is not None
        and session_ids[0] != request.session_id
    ):
        raise HandoffValidationError(
            "session_id_mismatch",
            "Resumed Codex session did not emit the requested session UUID.",
        )
    return session_ids[0], terminal_events[0], OMITTED_FINAL_SUMMARY


def _environment_without_git_targeting() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key in GIT_TARGETING_ENVIRONMENT_KEYS or key.startswith(
            GIT_TARGETING_ENVIRONMENT_PREFIXES
        ):
            environment.pop(key, None)
    return environment


def _isolated_git_environment() -> dict[str, str]:
    environment = _environment_without_git_targeting()
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _run_isolated_git(
    git: pathlib.Path,
    argv: list[str],
    *,
    input_bytes: bytes | None = None,
    failure_class: str = "isolation_error",
    message: str,
) -> None:
    try:
        result = subprocess.run(
            [str(git), *argv],
            input=input_bytes,
            stdin=subprocess.DEVNULL if input_bytes is None else None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=30,
            shell=False,
            env=_isolated_git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HandoffValidationError(failure_class, message) from exc
    if result.returncode != 0:
        raise HandoffValidationError(failure_class, message)


def _prepare_isolated_workspace(
    request: ValidatedRequest,
    root: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path]:
    git = _native_git(request.workspace)
    workspace = root / "workspace"
    _run_isolated_git(
        git,
        [
            "clone",
            "--quiet",
            "--no-checkout",
            "--no-local",
            "--",
            str(request.workspace),
            str(workspace),
        ],
        message="A private execution workspace could not be created.",
    )
    _run_isolated_git(
        git,
        ["-C", str(workspace), "checkout", "--quiet", "--detach", request.expected_head],
        message="The private execution workspace could not be bound to expected_head.",
    )
    _run_isolated_git(
        git,
        ["-C", str(workspace), "remote", "remove", "origin"],
        message="The private execution workspace retained its source path.",
    )
    return git, workspace


def _capture_isolated_patch(
    git: pathlib.Path,
    workspace: pathlib.Path,
    expected_head: str,
) -> bytes:
    _run_isolated_git(
        git,
        ["-C", str(workspace), "add", "--intent-to-add", "--", "."],
        failure_class="integration_error",
        message="Child changes could not be inventoried safely.",
    )
    try:
        process = subprocess.Popen(
            [
                str(git),
                "-C",
                str(workspace),
                "diff",
                expected_head,
                "--binary",
                "--full-index",
                "--no-ext-diff",
                "--no-renames",
                "--",
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            shell=False,
            start_new_session=os.name == "posix",
            env=_isolated_git_environment(),
        )
    except OSError as exc:
        raise HandoffValidationError(
            "integration_error", "Child changes could not be captured safely."
        ) from exc
    assert process.stdout is not None
    observed: list[bytes] = []

    def read_patch() -> None:
        try:
            observed.append(process.stdout.read(MAX_PATCH_BYTES + 1))
        except OSError:
            observed.append(b"")

    reader = threading.Thread(target=read_patch, daemon=True)
    reader.start()
    reader.join(timeout=30)
    if reader.is_alive():
        _terminate_process_group(process)
        reader.join(timeout=TERMINATION_GRACE_SECONDS)
        process.stdout.close()
        raise HandoffValidationError(
            "integration_error", "Child change capture timed out."
        )
    patch = observed[0] if observed else b""
    if len(patch) > MAX_PATCH_BYTES:
        _terminate_process_group(process)
        process.stdout.close()
        raise HandoffValidationError(
            "output_limit", "Child changes exceeded the bounded patch limit."
        )
    try:
        returncode = process.wait(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_group(process)
        process.stdout.close()
        raise HandoffValidationError(
            "integration_error", "Child change capture did not terminate safely."
        ) from exc
    process.stdout.close()
    if returncode != 0:
        raise HandoffValidationError(
            "integration_error", "Child changes could not be captured safely."
        )
    return patch


def _apply_isolated_patch(
    request: ValidatedRequest,
    git: pathlib.Path,
    patch: bytes,
) -> bool:
    if not patch:
        return False
    observed_head, _ = _workspace_identity(
        request.workspace, request.expected_head
    )
    if observed_head != request.expected_head:
        raise HandoffValidationError(
            "target_mismatch", "workspace identity changed before integration."
        )
    common = [
        "-C",
        str(request.workspace),
        "apply",
        "--binary",
        "--whitespace=nowarn",
    ]
    _run_isolated_git(
        git,
        [*common, "--check", "-"],
        input_bytes=patch,
        failure_class="integration_error",
        message="Child changes did not apply cleanly to the authorized workspace.",
    )
    _run_isolated_git(
        git,
        [*common, "-"],
        input_bytes=patch,
        failure_class="integration_error",
        message="Child changes could not be integrated into the authorized workspace.",
    )
    return True


def _run_child(
    request: ValidatedRequest,
    execution_workspace: pathlib.Path,
    *,
    on_started: Callable[[], None],
) -> tuple[int, bytes, str | None]:
    observed_head, _ = _workspace_identity(
        request.workspace, request.expected_head
    )
    if observed_head != request.expected_head:
        raise HandoffValidationError(
            "target_mismatch", "workspace identity changed before launch."
        )
    if _sha256_file(request.executable) != request.executable_sha256:
        raise HandoffValidationError(
            "executable_changed", "Codex executable changed before launch."
        )
    argv = build_argv(request, execution_workspace=execution_workspace)
    child_env = _environment_without_git_targeting()
    child_env[HANDOFF_DEPTH_ENV] = "1"
    child_env["NO_COLOR"] = "1"
    child_env["PWD"] = str(execution_workspace)
    child_env.pop("OLDPWD", None)
    creationflags = 0
    start_new_session = os.name == "posix"
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        process = subprocess.Popen(
            argv,
            cwd=execution_workspace,
            env=child_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=start_new_session,
            creationflags=creationflags,
        )
    except OSError as exc:
        raise HandoffValidationError(
            "launch_error", "Codex CLI process could not start."
        ) from exc
    on_started()
    assert process.stdout is not None
    assert process.stderr is not None
    assert process.stdin is not None
    tracker = ProcessTreeTracker(process.pid)
    try:
        tracker.start()
    except HandoffValidationError:
        _terminate_original_process_group(process)
        tracker.stop()
        raise
    capture = Capture(stdout=bytearray())
    lock = threading.Lock()
    readers = [
        threading.Thread(
            target=_capture_reader,
            args=(process.stdout, capture),
            kwargs={
                "stream_name": "stdout",
                "limit": MAX_STDOUT_BYTES,
                "lock": lock,
            },
            daemon=True,
        ),
        threading.Thread(
            target=_capture_reader,
            args=(process.stderr, capture),
            kwargs={
                "stream_name": "stderr",
                "limit": MAX_STDERR_BYTES,
                "lock": lock,
            },
            daemon=True,
        ),
    ]
    prompt_writer: threading.Thread | None = None
    deadline = time.monotonic() + request.timeout_seconds
    timed_out = False
    interrupted = False
    overflow_stream: str | None = None
    try:
        for reader in readers:
            reader.start()
        prompt_writer = threading.Thread(
            target=_prompt_writer,
            args=(process.stdin, request.prompt),
            daemon=True,
        )
        prompt_writer.start()
        while process.poll() is None:
            with lock:
                overflow_stream = capture.overflow_stream
            if overflow_stream is not None:
                _terminate_process_group(process, tracker)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _terminate_process_group(process, tracker)
                break
            _poll_sleep(0.05)
    except KeyboardInterrupt:
        interrupted = True
        _terminate_process_group(process, tracker)
    except BaseException:
        _terminate_process_group(process, tracker)
        raise
    finally:
        cleanup_error: HandoffValidationError | None = None
        try:
            tracker.capture()
            if process.poll() is None or tracker.live_descendants():
                _terminate_process_group(process, tracker)
        except HandoffValidationError as exc:
            cleanup_error = exc
        tracker.stop()
        try:
            tracker.ensure_available()
        except HandoffValidationError as exc:
            if cleanup_error is None:
                cleanup_error = exc
        for reader in readers:
            if reader.ident is not None:
                reader.join(timeout=TERMINATION_GRACE_SECONDS)
        if prompt_writer is not None:
            prompt_writer.join(timeout=TERMINATION_GRACE_SECONDS)
        process.stdout.close()
        process.stderr.close()
        if cleanup_error is not None:
            raise cleanup_error
    if (
        any(reader.is_alive() for reader in readers)
        or (prompt_writer is not None and prompt_writer.is_alive())
    ):
        raise HandoffValidationError(
            "termination_error", "Codex I/O workers did not terminate safely."
        )
    if interrupted:
        raise HandoffValidationError(
            "interrupted", "Codex CLI handoff was interrupted and terminated."
        )
    if timed_out:
        raise HandoffValidationError(
            "timeout", "Codex CLI handoff exceeded its bounded timeout."
        )
    with lock:
        overflow_stream = capture.overflow_stream
        stdout = bytes(capture.stdout)
    if overflow_stream is not None:
        raise HandoffValidationError(
            "output_limit",
            f"Codex {overflow_stream} exceeded the bounded output limit.",
        )
    return process.returncode, stdout, None


def execute_handoff(request: dict[str, Any]) -> dict[str, Any]:
    receipt = _base_receipt(request, status="stopped")
    try:
        validated = validate_request(request)
    except HandoffValidationError as exc:
        return _stop(
            request,
            exc.failure_class,
            str(exc),
            fallback=exc.failure_class == "capability_unavailable",
        )
    except OSError:
        return _stop(
            request,
            "capability_unavailable",
            "Host capability validation failed safely.",
            fallback=True,
        )

    receipt["capability"].update(
        {
            "version_probe_performed": True,
            "cli_version": validated.cli_version,
            "executable_sha256": validated.executable_sha256,
        }
    )
    receipt["target"].update(
        {
            "workspace": validated.workspace_label,
            "observed_head": validated.expected_head,
        }
    )

    def mark_session_started() -> None:
        receipt["boundaries"]["session_call_performed"] = True

    try:
        patch = b""
        git: pathlib.Path | None = None
        with tempfile.TemporaryDirectory(prefix="codex-cli-handoff-") as temp_root:
            git, execution_workspace = _prepare_isolated_workspace(
                validated, pathlib.Path(temp_root)
            )
            receipt["boundaries"]["child_workspace_isolated"] = True
            exit_status, raw_stdout, _ = _run_child(
                validated,
                execution_workspace,
                on_started=mark_session_started,
            )
            receipt["result"]["exit_status"] = exit_status
            if exit_status != 0:
                receipt.update(
                    {
                        "status": "failed",
                        "failure_class": "nonzero_exit",
                        "message": "Codex CLI exited unsuccessfully.",
                    }
                )
                return receipt
            session_id, terminal_event, summary = _parse_jsonl(
                raw_stdout, validated
            )
            receipt["boundaries"]["child_summary_omitted"] = True
            if validated.sandbox == "workspace-write":
                child_head = _run_git(
                    git, execution_workspace, "rev-parse", "HEAD"
                ).lower()
                if child_head != validated.expected_head:
                    raise HandoffValidationError(
                        "child_boundary_violation",
                        "The child changed Git HEAD despite the no-commit boundary.",
                    )
                patch = _capture_isolated_patch(
                    git, execution_workspace, validated.expected_head
                )
        if validated.sandbox == "workspace-write":
            assert git is not None
            receipt["boundaries"][
                "adapter_repository_write_performed"
            ] = _apply_isolated_patch(validated, git, patch)
    except HandoffValidationError as exc:
        receipt.update(
            {
                "status": "failed",
                "failure_class": exc.failure_class,
                "message": str(exc),
            }
        )
        return receipt
    except OSError:
        receipt.update(
            {
                "status": "failed",
                "failure_class": "isolation_error",
                "message": "The private execution workspace could not be cleaned safely.",
            }
        )
        return receipt

    receipt.update({"status": "completed", "failure_class": None, "message": None})
    receipt["result"].update(
        {
            "session_id": session_id,
            "terminal_event": terminal_event,
            "final_summary": summary,
        }
    )
    return receipt


def _read_request(path: str) -> dict[str, Any]:
    input_limit = MAX_PROMPT_BYTES * 2
    try:
        if path == "-":
            raw = sys.stdin.buffer.read(input_limit + 1)
        else:
            request_path = pathlib.Path(path)
            if not request_path.is_absolute():
                raise HandoffValidationError(
                    "validation_error", "--request path must be absolute or '-'."
                )
            with request_path.open("rb") as handle:
                raw = handle.read(input_limit + 1)
    except OSError as exc:
        raise HandoffValidationError(
            "validation_error", "request could not be read."
        ) from exc
    if len(raw) > input_limit:
        raise HandoffValidationError(
            "validation_error", "request JSON exceeded the bounded input limit."
        )
    try:
        value = json.loads(raw, object_pairs_hook=_strict_json_object)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DuplicateJsonKeyError,
    ) as exc:
        raise HandoffValidationError(
            "validation_error", "request must be one valid UTF-8 JSON object."
        ) from exc
    return _require_object(value, "request")


def _example_request() -> dict[str, Any]:
    return {
        "schema_version": REQUEST_SCHEMA_VERSION,
        "operation": "start",
        "codex_executable": "/absolute/path/to/codex",
        "workspace": "/absolute/path/to/git-worktree",
        "prompt": (
            "Read AGENTS.md and the selected task brief first. Complete only "
            "the bounded task, run the listed "
            "verification, and return changed files, evidence, questions, and "
            "residual risk."
        ),
        "sandbox": "read-only",
        "timeout_seconds": 900,
        "expected_head": "0" * 40,
        "prompt_boundary_version": PROMPT_BOUNDARY_VERSION,
        "authorization": {
            "marker": AUTHORIZATION_MARKER,
            "runtime_session_mutation_authorized": True,
            "sandbox_ceiling": "read-only",
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one bounded Codex CLI start or resume handoff."
    )
    parser.add_argument(
        "--request",
        help="Absolute request JSON path, or '-' for stdin.",
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Print a non-executable example request.",
    )
    args = parser.parse_args(argv)
    if args.example:
        if args.request is not None:
            parser.error("--example and --request are mutually exclusive")
        json.dump(_example_request(), sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return 0
    if args.request is None:
        parser.error("--request is required unless --example is used")
    try:
        request = _read_request(args.request)
        receipt = execute_handoff(request)
    except HandoffValidationError as exc:
        receipt = _stop(None, exc.failure_class, str(exc))
    json.dump(receipt, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
