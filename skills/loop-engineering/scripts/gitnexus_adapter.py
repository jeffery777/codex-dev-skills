#!/usr/bin/env python3
"""Fail-closed GitNexus 1.6.9 advisory adapter and refresh controller.

GitNexus metadata and index contents are untrusted, local derived data.  This
module never grants mutation/external-write authority and never parses the
human-oriented ``status`` or query output as a stable interface.
"""

from __future__ import annotations

import contextlib
import argparse
import datetime as dt
import errno
import hashlib
import json
import os
import pathlib
import re
import selectors
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

import memory_contract


DRIVER_VERSION = "gitnexus-v2c-a/1"
QUALIFIED_GITNEXUS_VERSION = "1.6.9"
REQUIRED_ANALYZE_FLAGS = frozenset(
    {"--index-only", "--skip-agents-md", "--skip-skills", "--branch", "--name"}
)
META_REQUIRED_FIELDS = frozenset(
    {
        "repoPath", "lastCommit", "indexedAt", "remoteUrl", "stats",
        "capabilities", "schemaVersion", "cjkSegmentation", "fileHashes",
        "cacheKeys", "branch",
    }
)
META_OPTIONAL_FIELDS = frozenset({"incrementalInProgress", "pdg"})
META_FIELDS = META_REQUIRED_FIELDS | META_OPTIONAL_FIELDS
META_SCHEMA_VERSION = 5
MAX_METADATA_BYTES = 4 * 1024 * 1024
FRESHNESS_STATES = frozenset(
    {"fresh", "stale", "missing", "partial", "unsupported", "incompatible", "corrupt", "unknown"}
)
SAFE_ENVIRONMENT_KEYS = frozenset(
    {"HOME", "LANG", "LC_ALL", "LC_CTYPE"}
)
MAX_GIT_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_DERIVED_INDEX_ENTRIES = 100_000
PROTECTED_BASENAMES = frozenset({"AGENTS.md", "CLA" + "UDE.md"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
FLAG_RE = re.compile(r"(?<![A-Za-z0-9-])--[a-z][a-z0-9-]*")
VERSION_RE = re.compile(r"(?<![0-9])v?(1\.6\.9)(?![0-9.])")
GRAPH_PROVIDER = "lady" + "bugdb"
FTS_PROVIDER = GRAPH_PROVIDER + "-fts"
VECTOR_PROVIDER = GRAPH_PROVIDER + "-vector"


class GitNexusAdapterError(RuntimeError):
    """Raised when qualification or a trusted precondition fails."""


class ProcessBoundaryError(GitNexusAdapterError):
    """Stable, path-redacted failure from the bounded process boundary."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


class ProbeDeadlineError(GitNexusAdapterError):
    """Raised when a shared repository evidence deadline is exhausted."""

    def __init__(self) -> None:
        super().__init__("probe-deadline-expired")


@dataclass(frozen=True)
class ExecutableQualification:
    executable: pathlib.Path
    executable_sha256: str
    version: str
    analyze_flags: tuple[str, ...]
    symlink_policy: str
    fingerprint: str
    stat_identity: tuple[int, int, int, int]
    runtime_executable: pathlib.Path | None = None
    runtime_executable_sha256: str | None = None
    runtime_stat_identity: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class RepositoryState:
    root: pathlib.Path
    canonical_repository_id: str
    canonical_remote: str
    head: str
    branch: str | None
    identity: dict[str, Any]


@dataclass(frozen=True)
class TrackedSnapshot:
    head: str
    tracked_dirty: bool
    outside_derived_dirty: bool
    tracked_state_digest: str
    protected_state_digest: str
    outside_derived_status_digest: str
    complete_status_digest: str


@dataclass(frozen=True)
class MetadataResult:
    state: str
    reason: str
    indexed_revision: str | None
    metadata_digest: str | None
    metadata: dict[str, Any] | None


@dataclass(frozen=True)
class RefreshResult:
    status: str
    reason: str
    receipt: dict[str, Any]


Runner = Callable[..., subprocess.CompletedProcess[Any]]


def _canonical_digest(value: Any) -> str:
    return memory_contract.canonical_digest(value)


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() >= deadline:
        raise ProbeDeadlineError()


def _sha256_file(path: pathlib.Path, *, deadline: float | None = None) -> str:
    digest = hashlib.sha256()
    _check_deadline(deadline)
    with path.open("rb") as stream:
        while True:
            _check_deadline(deadline)
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    _check_deadline(deadline)
    return digest.hexdigest()


def _safe_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    source = os.environ if source is None else source
    return {key: value for key, value in source.items() if key in SAFE_ENVIRONMENT_KEYS}


def _completed_output(result: subprocess.CompletedProcess[Any], label: str) -> str:
    if result.returncode != 0:
        raise GitNexusAdapterError(f"{label} failed with exit status {result.returncode}")
    try:
        stdout = result.stdout.decode("utf-8", "strict") if isinstance(result.stdout, bytes) else result.stdout
        stderr = result.stderr.decode("utf-8", "strict") if isinstance(result.stderr, bytes) else result.stderr
    except UnicodeError as exc:
        raise GitNexusAdapterError(f"{label} output is not valid UTF-8") from exc
    output = f"{stdout or ''}\n{stderr or ''}"
    if len(output.encode("utf-8")) > 64 * 1024:
        raise GitNexusAdapterError(f"{label} output exceeds qualification bound")
    return output


def discover_executable(
    configured_path: str | os.PathLike[str] | None,
    *,
    allow_symlink: bool = False,
) -> tuple[pathlib.Path, str]:
    """Resolve an executable under an explicit regular-file/symlink policy."""
    candidate_text = os.fspath(configured_path) if configured_path is not None else shutil.which("gitnexus")
    if not candidate_text:
        raise GitNexusAdapterError("gitnexus executable was not found")
    candidate = pathlib.Path(candidate_text).expanduser()
    if not candidate.is_absolute():
        candidate = pathlib.Path.cwd() / candidate
    try:
        link_stat = candidate.lstat()
    except OSError as exc:
        raise GitNexusAdapterError("gitnexus executable cannot be inspected") from exc
    is_link = stat.S_ISLNK(link_stat.st_mode)
    if is_link and not allow_symlink:
        raise GitNexusAdapterError("gitnexus executable symlink is forbidden by policy")
    resolved = candidate.resolve(strict=True)
    resolved_stat = resolved.stat()
    if not stat.S_ISREG(resolved_stat.st_mode):
        raise GitNexusAdapterError("gitnexus executable must resolve to a regular file")
    if resolved_stat.st_mode & 0o111 == 0:
        raise GitNexusAdapterError("gitnexus executable is not executable")
    return resolved, "resolved-symlink" if is_link else "regular-file-only"


def _executable_identity(
    path: pathlib.Path,
    *,
    deadline: float | None = None,
) -> tuple[str, tuple[int, int, int, int]]:
    _check_deadline(deadline)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o111 == 0:
        raise GitNexusAdapterError("qualified executable identity is no longer safe")
    return _sha256_file(path, deadline=deadline), (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _env_node_runtime(
    executable: pathlib.Path,
    source: Mapping[str, str],
    *,
    deadline: float | None = None,
) -> tuple[pathlib.Path, str, tuple[int, int, int, int]] | None:
    """Resolve and bind the interpreter used by the qualified npm CLI entry."""
    with executable.open("rb") as stream:
        shebang = stream.readline(256).rstrip(b"\r\n")
    if shebang != b"#!/usr/bin/env node":
        return None
    candidate = shutil.which("node", path=source.get("PATH"))
    if not candidate:
        raise GitNexusAdapterError("GitNexus env-node runtime was not found")
    runtime = pathlib.Path(candidate).resolve(strict=True)
    digest, identity = _executable_identity(runtime, deadline=deadline)
    return runtime, digest, identity


def _qualification_body(
    *,
    executable_sha256: str,
    analyze_flags: Sequence[str],
    symlink_policy: str,
    runtime_executable_sha256: str | None,
) -> dict[str, Any]:
    return {
        "driver_version": DRIVER_VERSION,
        "executable_sha256": executable_sha256,
        "runtime_executable_sha256": runtime_executable_sha256,
        "runtime_launcher": "bound-node" if runtime_executable_sha256 else "direct",
        "gitnexus_version": QUALIFIED_GITNEXUS_VERSION,
        "analyze_flags": list(analyze_flags),
        "metadata_schema": META_SCHEMA_VERSION,
        "metadata_fields": sorted(META_FIELDS),
        "metadata_primary": "gitnexus.json",
        "metadata_legacy_fallback": "meta.json",
        "metadata_capability_profile": {
            "graph": {"provider": GRAPH_PROVIDER, "status": "available"},
            "fts": {"provider": FTS_PROVIDER, "statuses": ["available", "unavailable"]},
            "vectorSearch": {"provider": VECTOR_PROVIDER, "status": "unavailable"},
        },
        "symlink_policy": symlink_policy,
    }


def _qualified_argv(
    executable: pathlib.Path,
    runtime_executable: pathlib.Path | None,
    *arguments: str,
) -> list[str]:
    prefix = [str(runtime_executable), str(executable)] if runtime_executable else [str(executable)]
    return [*prefix, *arguments]


def qualify_executable(
    configured_path: str | os.PathLike[str] | None,
    *,
    allow_symlink: bool = False,
    runner: Runner | None = None,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: int = 10,
) -> ExecutableQualification:
    """Bind exact executable bytes, version, observed flags, and driver schema."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 300:
        raise GitNexusAdapterError("qualification timeout must be an integer from 1 through 300 seconds")
    deadline = time.monotonic() + timeout_seconds
    run_process = runner or _run_adapter_subprocess
    source_environment = os.environ if environment is None else environment
    executable, symlink_policy = discover_executable(configured_path, allow_symlink=allow_symlink)
    before_digest, before_identity = _executable_identity(executable, deadline=deadline)
    runtime = _env_node_runtime(executable, source_environment, deadline=deadline)
    runtime_executable = runtime[0] if runtime else None
    runtime_digest = runtime[1] if runtime else None
    runtime_identity = runtime[2] if runtime else None
    common: dict[str, Any] = {
        "cwd": executable.parent,
        "env": _safe_environment(environment),
    }
    common["timeout"] = _remaining_timeout(deadline)
    version_output = _completed_output(
        run_process(_qualified_argv(executable, runtime_executable, "--version"), **common),
        "gitnexus --version",
    )
    matches = VERSION_RE.findall(version_output)
    if matches != [QUALIFIED_GITNEXUS_VERSION]:
        raise GitNexusAdapterError("GitNexus exact version 1.6.9 is required")
    common["timeout"] = _remaining_timeout(deadline)
    help_output = _completed_output(
        run_process(_qualified_argv(executable, runtime_executable, "analyze", "--help"), **common),
        "gitnexus analyze --help",
    )
    flags = tuple(sorted(set(FLAG_RE.findall(help_output))))
    missing = sorted(REQUIRED_ANALYZE_FLAGS - set(flags))
    if missing:
        raise GitNexusAdapterError(f"GitNexus required analyze flags are missing: {','.join(missing)}")
    after_digest, after_identity = _executable_identity(executable, deadline=deadline)
    if (before_digest, before_identity) != (after_digest, after_identity):
        raise GitNexusAdapterError("GitNexus executable changed during qualification")
    if runtime_executable is not None:
        after_runtime_digest, after_runtime_identity = _executable_identity(runtime_executable, deadline=deadline)
        if (runtime_digest, runtime_identity) != (after_runtime_digest, after_runtime_identity):
            raise GitNexusAdapterError("GitNexus runtime executable changed during qualification")
    body = _qualification_body(
        executable_sha256=after_digest,
        analyze_flags=flags,
        symlink_policy=symlink_policy,
        runtime_executable_sha256=runtime_digest,
    )
    return ExecutableQualification(
        executable=executable,
        executable_sha256=after_digest,
        version=QUALIFIED_GITNEXUS_VERSION,
        analyze_flags=flags,
        symlink_policy=symlink_policy,
        fingerprint=_canonical_digest(body),
        stat_identity=after_identity,
        runtime_executable=runtime_executable,
        runtime_executable_sha256=runtime_digest,
        runtime_stat_identity=runtime_identity,
    )


def verify_qualification(
    qualification: ExecutableQualification,
    *,
    deadline: float | None = None,
) -> None:
    _check_deadline(deadline)
    digest, identity = _executable_identity(qualification.executable, deadline=deadline)
    if digest != qualification.executable_sha256 or identity != qualification.stat_identity:
        raise GitNexusAdapterError("qualified GitNexus executable drifted")
    if qualification.version != QUALIFIED_GITNEXUS_VERSION or not REQUIRED_ANALYZE_FLAGS.issubset(qualification.analyze_flags):
        raise GitNexusAdapterError("GitNexus qualification capability drift requires requalification")
    if qualification.runtime_executable is not None:
        runtime_digest, runtime_identity = _executable_identity(
            qualification.runtime_executable, deadline=deadline
        )
        if (
            runtime_digest != qualification.runtime_executable_sha256
            or runtime_identity != qualification.runtime_stat_identity
        ):
            raise GitNexusAdapterError("qualified GitNexus runtime executable drifted")
    _check_deadline(deadline)
    expected_fingerprint = _canonical_digest(_qualification_body(
        executable_sha256=qualification.executable_sha256,
        analyze_flags=qualification.analyze_flags,
        symlink_policy=qualification.symlink_policy,
        runtime_executable_sha256=qualification.runtime_executable_sha256,
    ))
    if qualification.fingerprint != expected_fingerprint:
        raise GitNexusAdapterError("GitNexus qualification fingerprint is inconsistent")
    _check_deadline(deadline)


def normalize_remote(remote: str) -> str:
    """Normalize a two-segment Git remote to the V2b canonical HTTPS form."""
    if not isinstance(remote, str):
        raise GitNexusAdapterError("repository remote must be text")
    value = remote.strip()
    scp = re.fullmatch(r"(?:[^@/\s]+@)?([A-Za-z0-9.-]+):([^\s]+)", value)
    if scp and "://" not in value:
        host, raw_path = scp.group(1), scp.group(2)
    else:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https", "ssh", "git"} or not parsed.hostname:
            raise GitNexusAdapterError("repository remote must be a supported absolute Git URL")
        if parsed.query or parsed.fragment or (parsed.username and parsed.username != "git") or parsed.password:
            raise GitNexusAdapterError("repository remote contains unsafe URL components")
        try:
            port = parsed.port
        except ValueError as exc:
            raise GitNexusAdapterError("repository remote port is invalid") from exc
        if ":" in parsed.hostname:
            raise GitNexusAdapterError("IPv6 repository remotes are not qualified")
        default_port = {"http": 80, "https": 443, "ssh": 22, "git": 9418}[parsed.scheme]
        host = parsed.hostname if port in {None, default_port} else f"{parsed.hostname}:{port}"
        raw_path = parsed.path
    parts = [part for part in raw_path.strip("/").split("/") if part]
    if len(parts) != 2 or any(part in {".", ".."} for part in parts):
        raise GitNexusAdapterError("repository remote must contain exactly owner and repository")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    component = re.compile(r"^[A-Za-z0-9_.-]+$")
    if not repository or not component.fullmatch(owner) or not component.fullmatch(repository):
        raise GitNexusAdapterError("repository remote contains unsafe path syntax")
    return f"https://{host.lower()}/{owner}/{repository}.git"


def _git_executable() -> str:
    candidate = shutil.which("git")
    if not candidate:
        raise GitNexusAdapterError("git executable was not found")
    return str(pathlib.Path(candidate).resolve(strict=True))


def _git_environment() -> dict[str, str]:
    locale = {
        key: value
        for key, value in _safe_environment().items()
        if key in {"LANG", "LC_ALL", "LC_CTYPE"}
    }
    return {
        **locale,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _remaining_timeout(deadline: float | None, *, default: float = 30.0) -> float:
    if deadline is None:
        return default
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProbeDeadlineError()
    return remaining


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_process_group(
    process: subprocess.Popen[Any],
    *,
    cleanup_timeout: float = 2.0,
) -> bool:
    """Terminate and confirm the leader's complete process group is gone."""
    process_group = process.pid
    deadline = time.monotonic() + cleanup_timeout
    if _process_group_exists(process_group):
        try:
            os.killpg(process_group, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    grace_deadline = min(deadline, time.monotonic() + 0.2)
    while _process_group_exists(process_group) and time.monotonic() < grace_deadline:
        process.poll()  # Reap an exited leader so killpg(0) is not zombie-ambiguous.
        time.sleep(0.01)
    if _process_group_exists(process_group):
        try:
            os.killpg(process_group, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    try:
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return False
    while _process_group_exists(process_group) and time.monotonic() < deadline:
        time.sleep(0.01)
    return not _process_group_exists(process_group)


def _read_process_pipe(
    selector: selectors.BaseSelector,
    file_object: Any,
    destination: bytearray,
    *,
    maximum_output_bytes: int,
    total_size: int,
) -> tuple[int, bool]:
    try:
        chunk = os.read(file_object.fileno(), min(65_536, maximum_output_bytes + 1))
    except BlockingIOError:
        return total_size, False
    except OSError as exc:
        raise ProcessBoundaryError(f"process-pipe-{errno.errorcode.get(exc.errno, 'error').lower()}") from None
    if not chunk:
        try:
            selector.unregister(file_object)
        except KeyError:
            pass
        return total_size, True
    if len(destination) + len(chunk) > maximum_output_bytes or total_size + len(chunk) > maximum_output_bytes:
        raise ProcessBoundaryError("process-output-limit")
    destination.extend(chunk)
    return total_size + len(chunk), False


def _bounded_process(
    argv: Sequence[str],
    *,
    cwd: pathlib.Path,
    env: Mapping[str, str],
    timeout: float,
    maximum_output_bytes: int,
) -> subprocess.CompletedProcess[bytes]:
    if timeout <= 0 or maximum_output_bytes <= 0:
        raise ProcessBoundaryError("process-bound-invalid")
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            bufsize=0,
        )
    except OSError as exc:
        code = errno.errorcode.get(exc.errno, "error").lower()
        raise ProcessBoundaryError(f"process-spawn-{code}") from None
    assert process.stdout is not None and process.stderr is not None
    stdout = bytearray()
    stderr = bytearray()
    total_size = 0
    selector: selectors.BaseSelector | None = None
    try:
        selector = selectors.DefaultSelector()
        for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
    except (OSError, ValueError):
        cleanup_confirmed = _terminate_process_group(process)
        if selector is not None:
            selector.close()
        process.stdout.close()
        process.stderr.close()
        if not cleanup_confirmed:
            raise ProcessBoundaryError("process-group-cleanup-failed") from None
        raise ProcessBoundaryError("process-pipe-setup-failed") from None
    assert selector is not None
    execution_deadline = time.monotonic() + timeout
    failure: ProcessBoundaryError | None = None
    returncode: int | None = None
    try:
        while True:
            if time.monotonic() >= execution_deadline:
                failure = ProcessBoundaryError("process-timeout")
                break
            wait_time = max(0.0, min(0.05, execution_deadline - time.monotonic()))
            for key, _ in selector.select(timeout=wait_time):
                try:
                    target = stdout if key.data == "stdout" else stderr
                    total_size, _ = _read_process_pipe(
                        selector,
                        key.fileobj,
                        target,
                        maximum_output_bytes=maximum_output_bytes,
                        total_size=total_size,
                    )
                except ProcessBoundaryError as exc:
                    failure = exc
                    break
            if failure is not None:
                break
            returncode = process.poll()
            if returncode is not None:
                break
    finally:
        cleanup_confirmed = _terminate_process_group(process)
        # Once the group is gone no descendant can retain these descriptors.
        drain_deadline = time.monotonic() + 0.2
        while selector.get_map() and time.monotonic() < drain_deadline and failure is None:
            events = selector.select(timeout=0.01)
            if not events:
                continue
            for key, _ in events:
                try:
                    target = stdout if key.data == "stdout" else stderr
                    total_size, _ = _read_process_pipe(
                        selector,
                        key.fileobj,
                        target,
                        maximum_output_bytes=maximum_output_bytes,
                        total_size=total_size,
                    )
                except ProcessBoundaryError as exc:
                    failure = exc
                    break
        selector.close()
        process.stdout.close()
        process.stderr.close()
    if not cleanup_confirmed:
        raise ProcessBoundaryError("process-group-cleanup-failed")
    if failure is not None:
        raise failure
    if returncode is None:
        returncode = process.returncode
    return subprocess.CompletedProcess(list(argv), returncode, bytes(stdout), bytes(stderr))


def _run_adapter_subprocess(argv: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    return _bounded_process(
        argv,
        cwd=pathlib.Path(kwargs["cwd"]),
        env=kwargs["env"],
        timeout=float(kwargs["timeout"]),
        maximum_output_bytes=64 * 1024,
    )


def _run_git_result(
    root: pathlib.Path,
    args: Sequence[str],
    *,
    deadline: float | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return _bounded_process(
        [
            _git_executable(),
            "-c", "core.hooksPath=/dev/null",
            "-c", "core.fsmonitor=false",
            "-c", "core.untrackedCache=false",
            *args,
        ],
        cwd=root,
        env=_git_environment(),
        timeout=_remaining_timeout(deadline),
        maximum_output_bytes=MAX_GIT_OUTPUT_BYTES,
    )


def _run_git(
    root: pathlib.Path,
    args: Sequence[str],
    *,
    allow_failure: bool = False,
    deadline: float | None = None,
) -> bytes:
    result = _run_git_result(root, args, deadline=deadline)
    if result.returncode != 0 and not allow_failure:
        raise GitNexusAdapterError(f"git {' '.join(args[:2])} failed with exit status {result.returncode}")
    return result.stdout


def _strict_root(path: str | os.PathLike[str], *, deadline: float | None = None) -> pathlib.Path:
    lexical = pathlib.Path(path).expanduser()
    if not lexical.is_absolute():
        lexical = pathlib.Path.cwd() / lexical
    lexical = pathlib.Path(os.path.abspath(lexical))
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise GitNexusAdapterError("repository target cannot be resolved") from exc
    if lexical != resolved or lexical.is_symlink() or not resolved.is_dir():
        raise GitNexusAdapterError("repository target must be a real non-symlink directory")
    reported = pathlib.Path(
        _run_git(resolved, ["rev-parse", "--show-toplevel"], deadline=deadline).decode("utf-8", "strict").strip()
    ).resolve(strict=True)
    if reported != resolved:
        raise GitNexusAdapterError("target must be the exact Git repository root")
    return resolved


def collect_repository_state(
    root: str | os.PathLike[str],
    *,
    canonical_repository_id: str,
    expected_remote: str | None = None,
    principal_scope: Mapping[str, str] | None = None,
    path_scope: Sequence[str] = (".",),
    deadline: float | None = None,
) -> RepositoryState:
    """Build caller-owned V2b identity from current Git evidence."""
    root_path = _strict_root(root, deadline=deadline)
    head = _run_git(root_path, ["rev-parse", "HEAD"], deadline=deadline).decode().strip()
    if not COMMIT_RE.fullmatch(head):
        raise GitNexusAdapterError("repository HEAD is not an exact commit")
    branch_result = _run_git(root_path, ["symbolic-ref", "--quiet", "--short", "HEAD"], allow_failure=True, deadline=deadline)
    branch = branch_result.decode("utf-8", "strict").strip() or None
    actual_remote = normalize_remote(_run_git(root_path, ["remote", "get-url", "origin"], deadline=deadline).decode("utf-8", "strict"))
    if expected_remote is not None and actual_remote != normalize_remote(expected_remote):
        raise GitNexusAdapterError("repository origin does not match caller expectation")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", canonical_repository_id):
        raise GitNexusAdapterError("caller-owned canonical repository id is invalid")
    principals = dict(principal_scope or {
        "tenant": "not-applicable", "workspace": "not-applicable", "user": "not-applicable"
    })
    git_common = _run_git(root_path, ["rev-parse", "--git-common-dir"], deadline=deadline).decode("utf-8", "strict").strip()
    worktree_digest = _canonical_digest({"root": str(root_path), "git_common_dir": git_common})
    identity = {
        "canonical_repository_id": canonical_repository_id,
        "canonical_remote": actual_remote,
        "principal_scope": principals,
        "source_revision": {"kind": "git", "commit_sha": head, **({"branch": branch} if branch else {})},
        "path_scope": list(path_scope),
        "worktree_id_digest": worktree_digest,
    }
    identity["repository_identity_digest"] = _canonical_digest(identity)
    memory_contract.validate_repository_identity(identity)
    return RepositoryState(root_path, canonical_repository_id, actual_remote, head, branch, identity)


def _tracked_paths(root: pathlib.Path, *, deadline: float | None = None) -> list[str]:
    raw = _run_git(root, ["ls-files", "-z", "--cached"], deadline=deadline)
    return sorted({item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item})


def _path_entry(
    root: pathlib.Path,
    relative: str,
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    _check_deadline(deadline)
    path = root / relative
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"path": relative, "kind": "missing"}
    if stat.S_ISLNK(info.st_mode):
        _check_deadline(deadline)
        target = os.readlink(path).encode("utf-8", "surrogateescape")
        digest = hashlib.sha256(target).hexdigest()
        kind = "symlink"
    elif stat.S_ISREG(info.st_mode):
        digest = _sha256_file(path, deadline=deadline)
        kind = "regular"
    else:
        digest = hashlib.sha256(f"mode:{info.st_mode}".encode()).hexdigest()
        kind = "special"
    return {"path": relative, "kind": kind, "mode": stat.S_IMODE(info.st_mode), "sha256": digest}


def _is_protected(relative: str) -> bool:
    pure = pathlib.PurePosixPath(relative)
    lowered = [part.lower() for part in pure.parts]
    basename = pure.name
    return (
        basename in PROTECTED_BASENAMES
        or ".codex" in lowered
        or "skills" in lowered
        or any(token in basename.lower() for token in ("workflow", "policy", "instruction"))
    )


def _status_paths(raw: bytes) -> list[tuple[str, str]]:
    records = raw.split(b"\0")
    result: list[tuple[str, str]] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2:3] != b" ":
            raise GitNexusAdapterError("git status returned an unexpected porcelain record")
        code = record[:2].decode("ascii", "strict")
        path = record[3:].decode("utf-8", "surrogateescape")
        result.append((code, path))
        if code[0] in "RC" or code[1] in "RC":
            if index >= len(records) or not records[index]:
                raise GitNexusAdapterError("git status rename record is incomplete")
            result.append((code, records[index].decode("utf-8", "surrogateescape")))
            index += 1
    return result


def collect_tracked_snapshot(
    root: str | os.PathLike[str],
    *,
    deadline: float | None = None,
) -> TrackedSnapshot:
    root_path = _strict_root(root, deadline=deadline)
    head = _run_git(root_path, ["rev-parse", "HEAD"], deadline=deadline).decode().strip()
    complete_status = _run_git(root_path, ["status", "--porcelain=v1", "-z", "--untracked-files=all"], deadline=deadline)
    tracked_status = _run_git(root_path, ["status", "--porcelain=v1", "-z", "--untracked-files=no"], deadline=deadline)
    staged_diff = _run_git(root_path, ["diff", "--no-ext-diff", "--no-textconv", "--cached", "--binary", "HEAD", "--"], deadline=deadline)
    worktree_diff = _run_git(root_path, ["diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"], deadline=deadline)
    index_state = _run_git(root_path, ["ls-files", "-z", "--stage"], deadline=deadline)
    entries = [
        _path_entry(root_path, path, deadline=deadline)
        for path in _tracked_paths(root_path, deadline=deadline)
    ]
    protected = [entry for entry in entries if _is_protected(entry["path"])]
    outside_derived = sorted(
        (code, path) for code, path in _status_paths(complete_status)
        if path != ".gitnexus" and not path.startswith(".gitnexus/")
    )
    tracked_body = {
        "head": head,
        "tracked_status_sha256": hashlib.sha256(tracked_status).hexdigest(),
        "staged_diff_sha256": hashlib.sha256(staged_diff).hexdigest(),
        "worktree_diff_sha256": hashlib.sha256(worktree_diff).hexdigest(),
        "index_sha256": hashlib.sha256(index_state).hexdigest(),
        "entries": entries,
    }
    _check_deadline(deadline)
    return TrackedSnapshot(
        head=head,
        tracked_dirty=bool(tracked_status),
        outside_derived_dirty=bool(outside_derived),
        tracked_state_digest=_canonical_digest(tracked_body),
        protected_state_digest=_canonical_digest(protected),
        outside_derived_status_digest=_canonical_digest(outside_derived),
        complete_status_digest=hashlib.sha256(complete_status).hexdigest(),
    )


def _open_directory_nofollow(path: pathlib.Path) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise GitNexusAdapterError("POSIX no-follow directory operations are unavailable")
    return os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)


def _read_regular_at(
    directory_fd: int,
    filename: str,
    *,
    maximum_bytes: int,
    deadline: float | None = None,
) -> bytes:
    _check_deadline(deadline)
    if not hasattr(os, "O_NONBLOCK"):
        raise GitNexusAdapterError("POSIX nonblocking control-file operations are unavailable")
    descriptor = os.open(
        filename,
        os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
        dir_fd=directory_fd,
    )
    try:
        _check_deadline(deadline)
        info = os.fstat(descriptor)
        _check_deadline(deadline)
        if not stat.S_ISREG(info.st_mode):
            raise GitNexusAdapterError("opened control input is not a regular file")
        if info.st_size > maximum_bytes:
            raise GitNexusAdapterError("opened control input exceeds its safety bound")
        chunks: list[bytes] = []
        total = 0
        while True:
            _check_deadline(deadline)
            chunk = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - total))
            _check_deadline(deadline)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise GitNexusAdapterError("opened control input exceeds its safety bound")
        _check_deadline(deadline)
        result = b"".join(chunks)
        _check_deadline(deadline)
        return result
    finally:
        os.close(descriptor)


def _load_metadata_at(
    directory_fd: int,
    filename: str,
    *,
    deadline: float | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    _check_deadline(deadline)
    try:
        raw = _read_regular_at(
            directory_fd, filename, maximum_bytes=MAX_METADATA_BYTES, deadline=deadline
        )
    except FileNotFoundError:
        return None, "missing", "metadata-file-missing"
    except ProbeDeadlineError:
        raise
    except GitNexusAdapterError as exc:
        reason = "metadata-size-bound-exceeded" if "safety bound" in str(exc) else "metadata-not-regular-file"
        return None, "corrupt", reason
    except OSError as exc:
        if exc.errno in {errno.ENOENT, errno.ENOTDIR}:
            return None, "missing", "metadata-file-missing"
        if exc.errno in {errno.ELOOP, errno.EPERM}:
            return None, "corrupt", "metadata-not-regular-file"
        return None, "unknown", "metadata-file-inspection-failed"
    _check_deadline(deadline)
    try:
        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate key")
                result[key] = value
            return result
        _check_deadline(deadline)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
        _check_deadline(deadline)
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError):
        return None, "corrupt", "metadata-invalid-json"
    if not isinstance(value, dict):
        return None, "corrupt", "metadata-not-object"
    missing = META_REQUIRED_FIELDS - set(value)
    if missing:
        return value, "partial", "metadata-required-fields-missing"
    if set(value) - META_FIELDS:
        return value, "corrupt", "metadata-unknown-fields"
    return value, None, None


def _metadata_pair(
    index_directory: pathlib.Path,
    *,
    deadline: float | None = None,
) -> tuple[
    tuple[dict[str, Any] | None, str | None, str | None],
    tuple[dict[str, Any] | None, str | None, str | None],
]:
    _check_deadline(deadline)
    try:
        directory_fd = _open_directory_nofollow(index_directory)
    except FileNotFoundError:
        missing = (None, "missing", "metadata-file-missing")
        return missing, missing
    except OSError as exc:
        state = "corrupt" if exc.errno in {errno.ELOOP, errno.ENOTDIR} else "unknown"
        failure = (None, state, "metadata-directory-inspection-failed")
        return failure, failure
    try:
        _check_deadline(deadline)
        return (
            _load_metadata_at(directory_fd, "gitnexus.json", deadline=deadline),
            _load_metadata_at(directory_fd, "meta.json", deadline=deadline),
        )
    finally:
        os.close(directory_fd)


def _select_metadata(
    index_directory: pathlib.Path,
    *,
    deadline: float | None = None,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Select primary metadata; legacy is used only when primary is provably absent."""
    _check_deadline(deadline)
    primary_result, legacy_result = _metadata_pair(index_directory, deadline=deadline)
    _check_deadline(deadline)
    primary, primary_state, primary_reason = primary_result
    legacy, legacy_state, legacy_reason = legacy_result
    if primary_state == "missing":
        if legacy_state == "missing":
            return None, "missing", "metadata-files-missing"
        return legacy, legacy_state, legacy_reason
    if primary_state in {"corrupt", "unknown"}:
        return primary, primary_state, primary_reason
    if legacy_state != "missing":
        if legacy_state in {"corrupt", "unknown"}:
            return primary, "corrupt", "legacy-mirror-invalid-while-primary-present"
        try:
            _check_deadline(deadline)
            if _canonical_digest(primary) != _canonical_digest(legacy):
                return primary, "incompatible", "metadata-primary-legacy-conflict"
            _check_deadline(deadline)
        except (TypeError, ValueError, memory_contract.MemoryContractError):
            return primary, "corrupt", "metadata-mirror-canonicalization-failed"
    return primary, primary_state, primary_reason


def _metadata_mirrors_converged(
    index_directory: pathlib.Path,
    *,
    deadline: float | None = None,
) -> bool:
    _check_deadline(deadline)
    primary_result, legacy_result = _metadata_pair(index_directory, deadline=deadline)
    _check_deadline(deadline)
    primary, primary_state, _ = primary_result
    legacy, legacy_state, _ = legacy_result
    if primary_state is not None or legacy_state is not None:
        return False
    try:
        _check_deadline(deadline)
        converged = _canonical_digest(primary) == _canonical_digest(legacy)
        _check_deadline(deadline)
        return converged
    except (TypeError, ValueError, memory_contract.MemoryContractError):
        return False


def assess_metadata(
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    metadata_path: str | os.PathLike[str] | None = None,
    deadline: float | None = None,
) -> MetadataResult:
    """Strictly validate the qualified 1.6.9 meta schema and classify freshness."""
    try:
        verify_qualification(qualification, deadline=deadline)
    except (GitNexusAdapterError, OSError):
        return MetadataResult("incompatible", "executable-or-capability-drift", None, None, None)
    path = pathlib.Path(metadata_path) if metadata_path is not None else repository.root / ".gitnexus" / "gitnexus.json"
    try:
        _check_deadline(deadline)
        path = path.absolute()
        if path != repository.root / ".gitnexus" / "gitnexus.json":
            return MetadataResult("incompatible", "metadata-path-outside-qualified-location", None, None, None)
        index_directory = path.parent
        if index_directory.exists() and (
            index_directory.is_symlink() or index_directory.resolve(strict=True) != repository.root / ".gitnexus"
        ):
            return MetadataResult("incompatible", "metadata-directory-confinement-failed", None, None, None)
        _check_deadline(deadline)
        metadata, state, reason = _select_metadata(index_directory, deadline=deadline)
        _check_deadline(deadline)
    except OSError:
        return MetadataResult("unknown", "metadata-io-unknown", None, None, None)
    if state and isinstance(metadata, dict) and metadata.get("schemaVersion") == 1:
        return MetadataResult("incompatible", "legacy-schema-1-not-qualified", None, None, metadata)
    if state:
        return MetadataResult(state, reason or state, None, None, metadata)
    assert metadata is not None
    try:
        _check_deadline(deadline)
        digest = _canonical_digest(metadata)
        _check_deadline(deadline)
    except (TypeError, ValueError, memory_contract.MemoryContractError):
        return MetadataResult("corrupt", "metadata-canonicalization-failed", None, None, metadata)
    if isinstance(metadata["schemaVersion"], bool) or not isinstance(metadata["schemaVersion"], int):
        return MetadataResult("corrupt", "metadata-schema-version-invalid", None, digest, metadata)
    if metadata["schemaVersion"] == 1:
        return MetadataResult("incompatible", "legacy-schema-1-not-qualified", None, digest, metadata)
    if metadata["schemaVersion"] != META_SCHEMA_VERSION:
        return MetadataResult("unsupported", "metadata-schema-version-unsupported", None, digest, metadata)
    indexed = metadata["lastCommit"]
    if not isinstance(indexed, str) or not COMMIT_RE.fullmatch(indexed):
        return MetadataResult("corrupt", "metadata-last-commit-invalid", None, digest, metadata)
    try:
        _check_deadline(deadline)
        repo_path = pathlib.Path(metadata["repoPath"])
        if not repo_path.is_absolute() or repo_path.resolve(strict=True) != repository.root:
            return MetadataResult("incompatible", "metadata-repository-path-mismatch", indexed, digest, metadata)
        if normalize_remote(metadata["remoteUrl"]) != repository.canonical_remote:
            return MetadataResult("incompatible", "metadata-remote-mismatch", indexed, digest, metadata)
        _check_deadline(deadline)
    except (TypeError, OSError, GitNexusAdapterError):
        return MetadataResult("incompatible", "metadata-repository-identity-invalid", indexed, digest, metadata)
    try:
        parsed = dt.datetime.fromisoformat(metadata["indexedAt"].replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        return MetadataResult("corrupt", "metadata-indexed-time-invalid", indexed, digest, metadata)
    expected_stats = {"files", "nodes", "edges", "communities", "processes", "embeddings"}
    stats = metadata["stats"]
    if not isinstance(stats, dict) or set(stats) != expected_stats or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in stats.values()
    ):
        return MetadataResult("corrupt", "metadata-stats-invalid", indexed, digest, metadata)
    capabilities = metadata["capabilities"]
    if not isinstance(capabilities, dict) or set(capabilities) != {"graph", "fts", "vectorSearch"}:
        return MetadataResult("incompatible", "metadata-capability-drift", indexed, digest, metadata)
    graph = capabilities["graph"]
    fts = capabilities["fts"]
    vector = capabilities["vectorSearch"]
    if (
        graph != {"provider": GRAPH_PROVIDER, "status": "available"}
        or not isinstance(fts, dict)
        or set(fts) != {"provider", "status"}
        or fts.get("provider") != FTS_PROVIDER
        or fts.get("status") not in {"available", "unavailable"}
        or not isinstance(vector, dict)
        or set(vector) not in ({"provider", "status", "exactScanLimit"}, {"provider", "status", "exactScanLimit", "reason"})
        or vector.get("provider") != VECTOR_PROVIDER
        or vector.get("status") != "unavailable"
        or isinstance(vector.get("exactScanLimit"), bool)
        or not isinstance(vector.get("exactScanLimit"), int)
        or vector.get("exactScanLimit") <= 0
        or ("reason" in vector and (not isinstance(vector["reason"], str) or len(vector["reason"]) > 512))
    ):
        return MetadataResult("incompatible", "metadata-capability-drift", indexed, digest, metadata)
    if metadata["cjkSegmentation"] != "none":
        return MetadataResult("incompatible", "metadata-cjk-mode-drift", indexed, digest, metadata)
    if repository.branch is None or metadata["branch"] != repository.branch:
        return MetadataResult("incompatible", "metadata-branch-mismatch", indexed, digest, metadata)
    cache_keys = metadata["cacheKeys"]
    _check_deadline(deadline)
    if (
        not isinstance(cache_keys, list)
        or len(cache_keys) > 100_000
        or any(not isinstance(key, str) or not key or len(key) > 256 for key in cache_keys)
        or len(cache_keys) != len(set(cache_keys))
    ):
        return MetadataResult("corrupt", "metadata-cache-keys-invalid", indexed, digest, metadata)
    _check_deadline(deadline)
    if metadata.get("incrementalInProgress") is not None:
        return MetadataResult("partial", "metadata-index-write-in-progress", indexed, digest, metadata)
    if metadata.get("pdg") is not None:
        return MetadataResult("incompatible", "metadata-pdg-mode-not-qualified", indexed, digest, metadata)
    hashes = metadata["fileHashes"]
    if not isinstance(hashes, dict):
        return MetadataResult("corrupt", "metadata-file-hashes-invalid", indexed, digest, metadata)
    for name, value in hashes.items():
        _check_deadline(deadline)
        if not isinstance(name, str):
            return MetadataResult("corrupt", "metadata-file-hash-path-unsafe", indexed, digest, metadata)
        parsed_name = pathlib.PurePosixPath(name)
        if (
            not name
            or name == "."
            or name.startswith("./")
            or "//" in name
            or "\\" in name
            or parsed_name.is_absolute()
            or ".." in parsed_name.parts
            or parsed_name.as_posix() != name
        ):
            return MetadataResult("corrupt", "metadata-file-hash-path-unsafe", indexed, digest, metadata)
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            return MetadataResult("corrupt", "metadata-file-hash-invalid", indexed, digest, metadata)
    _check_deadline(deadline)
    if snapshot.head != repository.head:
        return MetadataResult("unknown", "caller-snapshot-head-conflict", indexed, digest, metadata)
    if snapshot.tracked_dirty or snapshot.outside_derived_dirty:
        return MetadataResult("stale", "working-tree-dirty", indexed, digest, metadata)
    if indexed != repository.head:
        return MetadataResult("stale", "indexed-revision-stale", indexed, digest, metadata)
    _check_deadline(deadline)
    return MetadataResult("fresh", "exact-clean-revision", indexed, digest, metadata)


def build_handshake(
    qualification: ExecutableQualification,
    metadata: MetadataResult,
    *,
    enabled: bool = False,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build a V2b handshake; 1.6.9 has no qualified structured query API."""
    verify_qualification(qualification)
    observed_at = observed_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    status = "disabled" if not enabled else "degraded" if metadata.state == "fresh" else (
        "incompatible" if metadata.state in {"unsupported", "incompatible", "corrupt"} else "unavailable"
    )
    supported = {"namespaces", "repository_isolation", "audit"} if enabled and metadata.state == "fresh" else set()
    capabilities = {}
    for name in memory_contract.CAPABILITIES:
        capabilities[name] = {
            "state": "supported" if name in supported else "unsupported",
            "semantics": {
                "advisory_only": True,
                "structured_query_interface": False,
                "driver_version": DRIVER_VERSION,
                "qualification_fingerprint": qualification.fingerprint,
                "metadata_schema": META_SCHEMA_VERSION,
            },
        }
    handshake = {
        "contract_version": memory_contract.CONTRACT_VERSION,
        "kind": "capability-handshake",
        "adapter": {
            "adapter_id": "gitnexus-local-advisory",
            "adapter_version": f"1.6.9.{qualification.fingerprint}",
            "schema_versions": [memory_contract.CONTRACT_VERSION],
            "consistency": "none",
            "isolation": "repository",
        },
        "capabilities": capabilities,
        "status": status,
        "observed_at": observed_at,
        "extensions": {},
    }
    memory_contract.validate_handshake(handshake)
    return handshake


def decide_advisory_retrieval(
    decision_input: dict[str, Any],
    *,
    trusted_conformance_receipts: dict[str, dict[str, str]] | None = None,
    trusted_source_digests: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Produce a no-memory receipt; CLI query adoption is not qualified."""
    handshake = memory_contract.validate_handshake(decision_input.get("handshake"))
    response = decision_input.get("response")
    if handshake["adapter"]["adapter_id"] != "gitnexus-local-advisory":
        raise GitNexusAdapterError("retrieval input is not bound to the GitNexus adapter")
    if handshake["capabilities"]["read_query"]["state"] != "unsupported":
        raise GitNexusAdapterError("GitNexus 1.6.9 structured query adoption is not qualified")
    if any(
        handshake["capabilities"][name]["state"] != "unsupported"
        for name in ("write_upsert", "invalidate", "tombstone", "delete")
    ):
        raise GitNexusAdapterError("GitNexus backend mutation capability must remain unsupported")
    if not isinstance(response, dict) or response.get("adapter_id") != "gitnexus-local-advisory":
        raise GitNexusAdapterError("retrieval response adapter identity mismatch")
    if response.get("status") not in {"unsupported", "unavailable"}:
        raise GitNexusAdapterError("GitNexus CLI query responses are not an adoptable contract")
    receipt = memory_contract.decide_retrieval(
        decision_input,
        trusted_conformance_receipts=trusted_conformance_receipts,
        trusted_source_digests=trusted_source_digests,
    )
    invariants = receipt["authority_invariants"]
    if any(invariants[key] for key in ("mutation_authorized", "external_write_authorized", "gate_satisfied", "completion_proven")):
        raise GitNexusAdapterError("V2b authority invariant violation")
    return receipt


def unsupported_mutation(operation: str) -> dict[str, Any]:
    if operation not in {"upsert", "invalidate", "tombstone", "delete"}:
        raise GitNexusAdapterError("unknown backend mutation operation")
    body = {
        "contract_version": memory_contract.CONTRACT_VERSION,
        "kind": "gitnexus-mutation-disposition",
        "operation": operation,
        "status": "unsupported",
        "write_performed": False,
        "external_write_authorized": False,
        "completion_proven": False,
    }
    return {**body, "receipt_digest": _canonical_digest(body)}


_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _safe_control_file(directory_fd: int, filename: str, label: str) -> bytes:
    try:
        return _read_regular_at(directory_fd, filename, maximum_bytes=2 * 1024 * 1024)
    except (GitNexusAdapterError, OSError) as exc:
        raise GitNexusAdapterError(f"Git {label} control file is unavailable") from exc


def _git_control_snapshot(
    root: pathlib.Path,
    *,
    require_exclusion: bool,
    deadline: float | None = None,
) -> str:
    try:
        git_fd = _open_directory_nofollow(root / ".git")
    except OSError as exc:
        if exc.errno in {errno.ENOTDIR, errno.ELOOP}:
            raise GitNexusAdapterError("linked-worktree .git file refresh is unsupported by this driver") from exc
        raise GitNexusAdapterError("repository .git control boundary is unavailable") from exc
    try:
        try:
            info_fd = os.open("info", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=git_fd)
        except OSError as exc:
            raise GitNexusAdapterError("linked-worktree or unsafe Git info boundary is unsupported") from exc
        try:
            exclude = _safe_control_file(info_fd, "exclude", "exclude")
        finally:
            os.close(info_fd)
        config = _safe_control_file(git_fd, "config", "config")
        head = _safe_control_file(git_fd, "HEAD", "HEAD")
    finally:
        os.close(git_fd)
    if require_exclusion:
        try:
            entries = {
                line.strip() for line in exclude.decode("utf-8", "strict").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
        except UnicodeError as exc:
            raise GitNexusAdapterError("Git exclude control file is not UTF-8") from exc
        if not ({".gitnexus", ".gitnexus/"} & entries):
            raise GitNexusAdapterError("Git exclude must already contain .gitnexus/ before refresh")
        ignored = _run_git_result(
            root,
            ["check-ignore", "--quiet", "--no-index", "--", ".gitnexus/.codex-v2c-probe"],
            deadline=deadline,
        )
        if ignored.returncode != 0:
            raise GitNexusAdapterError("Git exclude does not effectively ignore .gitnexus/")
    return _canonical_digest({
        "exclude_sha256": hashlib.sha256(exclude).hexdigest(),
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "head_sha256": hashlib.sha256(head).hexdigest(),
    })


def _resolve_isolated_home(path: pathlib.Path | None, root: pathlib.Path) -> pathlib.Path:
    if path is None:
        raise GitNexusAdapterError("refresh requires an explicit isolated GITNEXUS_HOME")
    lexical = pathlib.Path(os.path.abspath(path.expanduser()))
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise GitNexusAdapterError("isolated GITNEXUS_HOME must be a pre-created directory") from exc
    if lexical != resolved or lexical.is_symlink() or not resolved.is_dir():
        raise GitNexusAdapterError("isolated GITNEXUS_HOME must be a real non-symlink directory")
    if resolved == root or root in resolved.parents or resolved in root.parents:
        raise GitNexusAdapterError("isolated GITNEXUS_HOME must be outside the repository boundary")
    return resolved


def _require_empty_isolated_home(path: pathlib.Path) -> None:
    try:
        with os.scandir(path) as entries:
            if next(entries, None) is not None:
                raise GitNexusAdapterError("isolated GITNEXUS_HOME must be empty for each refresh")
    except OSError as exc:
        raise GitNexusAdapterError("isolated GITNEXUS_HOME cannot be inspected") from exc


def _validate_derived_index_tree(
    root: pathlib.Path,
    *,
    deadline: float | None = None,
) -> None:
    _check_deadline(deadline)
    index_root = root / ".gitnexus"
    try:
        root_info = index_root.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise GitNexusAdapterError("derived index boundary cannot be inspected") from exc
    _check_deadline(deadline)
    repository_device = root.stat().st_dev
    _check_deadline(deadline)
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode):
        raise GitNexusAdapterError("derived index root must be a real directory")
    if root_info.st_dev != repository_device:
        raise GitNexusAdapterError("derived index root crosses a filesystem boundary")
    try:
        index_fd = _open_directory_nofollow(index_root)
    except OSError as exc:
        raise GitNexusAdapterError("derived index root cannot be opened safely") from exc
    pending = [index_fd]
    try:
        opened_root = os.fstat(index_fd)
        _check_deadline(deadline)
        if (
            opened_root.st_dev != root_info.st_dev
            or opened_root.st_ino != root_info.st_ino
            or not stat.S_ISDIR(opened_root.st_mode)
        ):
            raise GitNexusAdapterError("derived index root changed during validation")
        count = 1
        while pending:
            _check_deadline(deadline)
            directory_fd = pending.pop()
            try:
                try:
                    with os.scandir(directory_fd) as entries:
                        for entry in entries:
                            _check_deadline(deadline)
                            count += 1
                            if count > MAX_DERIVED_INDEX_ENTRIES:
                                raise GitNexusAdapterError(
                                    "derived index entry count exceeds the safety bound"
                                )
                            try:
                                info = entry.stat(follow_symlinks=False)
                            except OSError as exc:
                                raise GitNexusAdapterError(
                                    "derived index entry cannot be inspected"
                                ) from exc
                            _check_deadline(deadline)
                            if stat.S_ISLNK(info.st_mode) or not (
                                stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)
                            ):
                                raise GitNexusAdapterError(
                                    "derived index contains an unsafe entry"
                                )
                            if info.st_dev != repository_device or (
                                stat.S_ISREG(info.st_mode) and info.st_nlink != 1
                            ):
                                raise GitNexusAdapterError(
                                    "derived index entry escapes the qualified boundary"
                                )
                            flags = os.O_RDONLY | os.O_NOFOLLOW
                            if stat.S_ISDIR(info.st_mode):
                                flags |= os.O_DIRECTORY
                            try:
                                entry_fd = os.open(entry.name, flags, dir_fd=directory_fd)
                            except OSError as exc:
                                raise GitNexusAdapterError(
                                    "derived index entry cannot be opened safely"
                                ) from exc
                            try:
                                opened = os.fstat(entry_fd)
                                _check_deadline(deadline)
                                if (
                                    opened.st_dev != info.st_dev
                                    or opened.st_ino != info.st_ino
                                    or stat.S_IFMT(opened.st_mode) != stat.S_IFMT(info.st_mode)
                                    or opened.st_dev != repository_device
                                    or (stat.S_ISREG(opened.st_mode) and opened.st_nlink != 1)
                                ):
                                    raise GitNexusAdapterError(
                                        "derived index entry changed during validation"
                                    )
                                if stat.S_ISDIR(opened.st_mode):
                                    pending.append(entry_fd)
                                    entry_fd = -1
                            finally:
                                if entry_fd >= 0:
                                    os.close(entry_fd)
                except OSError as exc:
                    raise GitNexusAdapterError(
                        "derived index directory cannot be inspected"
                    ) from exc
            finally:
                os.close(directory_fd)
    finally:
        for descriptor in pending:
            os.close(descriptor)
    _check_deadline(deadline)


def _run_refresh_subprocess(argv: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
    return _run_adapter_subprocess(argv, **kwargs)


@contextlib.contextmanager
def _root_lock(root: pathlib.Path, lock_directory: pathlib.Path | None) -> Iterator[None]:
    key = _canonical_digest({"root": str(root)})
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise GitNexusAdapterError("refresh already holds the repository lock")
    descriptor: int | None = None
    try:
        directory = pathlib.Path(os.path.abspath(
            lock_directory or pathlib.Path(tempfile.gettempdir()) / "codex-gitnexus-locks"
        ))
        unresolved = directory.resolve(strict=False)
        if unresolved == root or root in unresolved.parents:
            raise GitNexusAdapterError("refresh lock directory must be outside the repository")
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir() or directory.resolve(strict=True) != unresolved:
            raise GitNexusAdapterError("refresh lock directory is unsafe")
        lock_path = directory / f"{key}.lock"
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(lock_path, flags, 0o600)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise GitNexusAdapterError("refresh lock is not a regular file")
        try:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError, OSError) as exc:
            raise GitNexusAdapterError("refresh cross-process lock is unavailable") from exc
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        lock.release()


class RefreshController:
    """Explicit opt-in, index-only derived refresh with fail-closed adoption."""

    def __init__(
        self,
        qualification: ExecutableQualification,
        *,
        enabled: bool = False,
        timeout_seconds: int = 120,
        environment: Mapping[str, str] | None = None,
        gitnexus_home: pathlib.Path | None = None,
        lock_directory: pathlib.Path | None = None,
        runner: Runner = _run_refresh_subprocess,
    ) -> None:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 3_600:
            raise GitNexusAdapterError("refresh timeout must be an integer from 1 through 3600 seconds")
        self.qualification = qualification
        self.enabled = enabled
        self.auto_capability_enabled = False
        self.timeout_seconds = timeout_seconds
        self.environment = _safe_environment(environment)
        self.gitnexus_home = gitnexus_home
        self.lock_directory = lock_directory
        self.runner = runner

    def refresh(
        self,
        repository: RepositoryState,
        *,
        expected_head: str,
        explicit_opt_in: bool = False,
    ) -> RefreshResult:
        deadline = time.monotonic() + self.timeout_seconds
        if not self.enabled or not explicit_opt_in:
            raise GitNexusAdapterError("refresh is disabled unless explicitly opted in")
        if not COMMIT_RE.fullmatch(expected_head):
            raise GitNexusAdapterError("refresh expected HEAD is invalid")
        root = _strict_root(repository.root, deadline=deadline)
        if root != repository.root:
            raise GitNexusAdapterError("refresh repository root identity mismatch")
        verify_qualification(self.qualification, deadline=deadline)
        with _root_lock(root, self.lock_directory):
            isolated_home = _resolve_isolated_home(self.gitnexus_home, root)
            _require_empty_isolated_home(isolated_home)
            _validate_derived_index_tree(root, deadline=deadline)
            before_repository = collect_repository_state(
                root,
                canonical_repository_id=repository.canonical_repository_id,
                expected_remote=repository.canonical_remote,
                principal_scope=repository.identity["principal_scope"],
                path_scope=repository.identity["path_scope"],
                deadline=deadline,
            )
            before = collect_tracked_snapshot(root, deadline=deadline)
            before_git_control_digest = _git_control_snapshot(
                root, require_exclusion=True, deadline=deadline
            )
            if before_repository.head != expected_head or before.head != expected_head:
                raise GitNexusAdapterError("refresh expected HEAD does not match current repository")
            if before.tracked_dirty or before.outside_derived_dirty:
                raise GitNexusAdapterError("refresh refuses a dirty working tree outside the derived index")
            if before.outside_derived_dirty:
                raise GitNexusAdapterError("refresh refuses pre-existing changes outside the derived index")
            alias = f"codex-v2c-{repository.identity['repository_identity_digest'][:12]}-{repository.identity['worktree_id_digest'][:12]}"
            argv = [
                *_qualified_argv(
                    self.qualification.executable,
                    self.qualification.runtime_executable,
                    "analyze", "--index-only", "--name", alias, str(root),
                ),
            ]
            process_environment = {
                **self.environment,
                "HOME": str(isolated_home),
                "TMPDIR": str(isolated_home),
                "TMP": str(isolated_home),
                "TEMP": str(isolated_home),
                "GITNEXUS_HOME": str(isolated_home),
                "GITNEXUS_LBUG_EXTENSION_INSTALL": "never",
            }
            process_failure: str | None = None
            try:
                process = self.runner(
                    argv,
                    cwd=root,
                    env=process_environment,
                    timeout=max(0.1, _remaining_timeout(deadline) * 0.7),
                )
            except subprocess.TimeoutExpired:
                process_failure = "refresh-timeout"
                process = None
            except ProcessBoundaryError as exc:
                process_failure = f"refresh-{exc.error_code}"
                process = None
            try:
                after_repository = collect_repository_state(
                    root,
                    canonical_repository_id=repository.canonical_repository_id,
                    expected_remote=repository.canonical_remote,
                    principal_scope=repository.identity["principal_scope"],
                    path_scope=repository.identity["path_scope"],
                    deadline=deadline,
                )
                after = collect_tracked_snapshot(root, deadline=deadline)
                after_git_control_digest = _git_control_snapshot(
                    root, require_exclusion=True, deadline=deadline
                )
                _validate_derived_index_tree(root, deadline=deadline)
                verify_qualification(self.qualification, deadline=deadline)
            except (GitNexusAdapterError, OSError) as exc:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", f"postcondition-unknown:{type(exc).__name__}", repository,
                    before, None, argv, before_git_control_digest=before_git_control_digest,
                )
            mutation = (
                after.head != before.head
                or after.tracked_state_digest != before.tracked_state_digest
                or after.protected_state_digest != before.protected_state_digest
                or after.outside_derived_status_digest != before.outside_derived_status_digest
                or after_git_control_digest != before_git_control_digest
                or after_repository.identity["repository_identity_digest"] != before_repository.identity["repository_identity_digest"]
            )
            if mutation:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "unexpected-repository-mutation", repository, before, after, argv,
                    before_git_control_digest=before_git_control_digest,
                    after_git_control_digest=after_git_control_digest,
                )
            if process_failure is not None:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", process_failure, repository, before, after, argv,
                    before_git_control_digest=before_git_control_digest,
                    after_git_control_digest=after_git_control_digest,
                )
            assert process is not None
            if process.returncode != 0:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", f"refresh-exit-{process.returncode}", repository, before, after, argv,
                    before_git_control_digest=before_git_control_digest,
                    after_git_control_digest=after_git_control_digest,
                )
            if after_repository.head != expected_head:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "post-refresh-head-mismatch", repository, before, after, argv,
                    before_git_control_digest=before_git_control_digest,
                    after_git_control_digest=after_git_control_digest,
                )
            metadata = assess_metadata(
                after_repository, after, self.qualification, deadline=deadline
            )
            if (
                metadata.state != "fresh"
                or metadata.indexed_revision != expected_head
                or not _metadata_mirrors_converged(
                    root / ".gitnexus", deadline=deadline
                )
            ):
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", f"post-refresh-metadata-{metadata.state}", repository, before, after, argv,
                    metadata, before_git_control_digest, after_git_control_digest,
                )
            return self._receipt(
                "refreshed", "qualified-index-adoptable", repository, before, after, argv,
                metadata, before_git_control_digest, after_git_control_digest,
            )

    def _receipt(
        self,
        status_value: str,
        reason: str,
        repository: RepositoryState,
        before: TrackedSnapshot,
        after: TrackedSnapshot | None,
        argv: Sequence[str],
        metadata: MetadataResult | None = None,
        before_git_control_digest: str | None = None,
        after_git_control_digest: str | None = None,
    ) -> RefreshResult:
        body = {
            "contract_version": memory_contract.CONTRACT_VERSION,
            "kind": "gitnexus-derived-index-refresh-receipt",
            "status": status_value,
            "reason": reason,
            "repository_identity_digest": repository.identity["repository_identity_digest"],
            "expected_head": before.head,
            "qualification_fingerprint": self.qualification.fingerprint,
            "argv_digest": _canonical_digest(list(argv)),
            "before_tracked_state_digest": before.tracked_state_digest,
            "before_protected_state_digest": before.protected_state_digest,
            "before_complete_status_digest": before.complete_status_digest,
            "after_tracked_state_digest": after.tracked_state_digest if after else None,
            "after_protected_state_digest": after.protected_state_digest if after else None,
            "after_complete_status_digest": after.complete_status_digest if after else None,
            "before_git_control_digest": before_git_control_digest,
            "after_git_control_digest": after_git_control_digest,
            "indexed_revision": metadata.indexed_revision if metadata else None,
            "authority_invariants": {
                "derived_local_operation_only": True,
                "memory_payload_authorized_refresh": False,
                "mutation_authorized": False,
                "external_write_authorized": False,
                "gate_satisfied": False,
                "completion_proven": False,
                "automatic_refresh_enabled": False,
                "repository_restore_performed": False,
                "repository_stage_performed": False,
            },
        }
        receipt = {**body, "receipt_digest": _canonical_digest(body)}
        return RefreshResult(status_value, reason, receipt)


def _add_executable_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--executable", help="Machine-local GitNexus executable; defaults to explicit PATH discovery.")
    parser.add_argument(
        "--allow-symlink",
        action="store_true",
        help="Explicitly permit one discovered symlink whose resolved target is qualified.",
    )


def _add_repository_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, help="Exact canonical Git worktree root.")
    parser.add_argument("--repository-id", required=True, help="Caller-owned canonical repository id.")
    parser.add_argument("--expected-remote", required=True, help="Caller-owned expected origin URL.")


def _operator_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Default-disabled GitNexus 1.6.9 advisory adapter control plane."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    qualify = commands.add_parser("qualify", help="Discover and fingerprint the local CLI without indexing.")
    _add_executable_arguments(qualify)

    status = commands.add_parser("status", help="Classify strict metadata freshness and emit a V2b handshake.")
    _add_executable_arguments(status)
    _add_repository_arguments(status)
    status.add_argument(
        "--enabled",
        action="store_true",
        help="Opt in for this status invocation only; no setting is persisted.",
    )

    refresh = commands.add_parser("refresh", help="Run one explicit, qualified index-only refresh.")
    _add_executable_arguments(refresh)
    _add_repository_arguments(refresh)
    refresh.add_argument("--expected-head", required=True, help="Exact expected 40-character Git HEAD.")
    refresh.add_argument("--gitnexus-home", required=True, help="Pre-created isolated machine-local GitNexus home.")
    refresh.add_argument("--lock-directory", required=True, help="Machine-local lock directory outside the repository.")
    refresh.add_argument("--timeout-seconds", type=int, default=120)
    refresh.add_argument("--enabled", action="store_true", help="Required runtime opt-in; never persisted.")
    refresh.add_argument(
        "--confirm-explicit-refresh",
        action="store_true",
        help="Required per-operation confirmation that cannot come from memory content.",
    )

    commands.add_parser(
        "disable",
        help="Emit the stateless disable/rollback disposition; no files or indexes are changed.",
    )
    return parser


def _qualification_from_arguments(arguments: argparse.Namespace) -> ExecutableQualification:
    return qualify_executable(
        arguments.executable,
        allow_symlink=arguments.allow_symlink,
    )


def _repository_from_arguments(arguments: argparse.Namespace) -> RepositoryState:
    return collect_repository_state(
        arguments.repo_root,
        canonical_repository_id=arguments.repository_id,
        expected_remote=arguments.expected_remote,
    )


def _disable_disposition() -> dict[str, Any]:
    body = {
        "contract_version": memory_contract.CONTRACT_VERSION,
        "kind": "gitnexus-adapter-disable-disposition",
        "status": "disabled",
        "runtime_opt_in_persisted": False,
        "repository_write_performed": False,
        "index_delete_performed": False,
        "completion_proven": False,
    }
    return {**body, "receipt_digest": _canonical_digest(body)}


def _operator_error_code(error: BaseException) -> str:
    if isinstance(error, ProcessBoundaryError):
        return error.error_code
    if isinstance(error, ProbeDeadlineError):
        return "probe-deadline-expired"
    if isinstance(error, subprocess.TimeoutExpired):
        return "process-timeout"
    if isinstance(error, OSError):
        return f"os-{errno.errorcode.get(error.errno, 'error').lower()}"
    if isinstance(error, GitNexusAdapterError):
        return "adapter-rejected"
    return "subprocess-rejected"


def operator_main(argv: Sequence[str] | None = None) -> int:
    """Run the redacted machine-local operator interface."""
    arguments = _operator_parser().parse_args(argv)
    try:
        if arguments.command == "disable":
            result = _disable_disposition()
            exit_status = 0
        else:
            qualification = _qualification_from_arguments(arguments)
            if arguments.command == "qualify":
                result = {
                    "kind": "gitnexus-qualification-status",
                    "status": "qualified",
                    "version": qualification.version,
                    "symlink_policy": qualification.symlink_policy,
                    "runtime_bound": qualification.runtime_executable is not None,
                    "analyze_flags": list(qualification.analyze_flags),
                    "qualification_fingerprint": qualification.fingerprint,
                }
                exit_status = 0
            else:
                repository = _repository_from_arguments(arguments)
                snapshot = collect_tracked_snapshot(repository.root)
                if arguments.command == "status":
                    metadata = assess_metadata(repository, snapshot, qualification)
                    result = {
                        "kind": "gitnexus-adapter-status",
                        "status": metadata.state,
                        "reason": metadata.reason,
                        "repository_identity_digest": repository.identity["repository_identity_digest"],
                        "head": repository.head,
                        "branch": repository.branch,
                        "indexed_revision": metadata.indexed_revision,
                        "metadata_digest": metadata.metadata_digest,
                        "handshake": build_handshake(
                            qualification,
                            metadata,
                            enabled=arguments.enabled,
                        ),
                    }
                    exit_status = 0
                else:
                    controller = RefreshController(
                        qualification,
                        enabled=arguments.enabled,
                        timeout_seconds=arguments.timeout_seconds,
                        gitnexus_home=pathlib.Path(arguments.gitnexus_home),
                        lock_directory=pathlib.Path(arguments.lock_directory),
                    )
                    refreshed = controller.refresh(
                        repository,
                        expected_head=arguments.expected_head,
                        explicit_opt_in=arguments.confirm_explicit_refresh,
                    )
                    result = refreshed.receipt
                    exit_status = 0 if refreshed.status == "refreshed" else 1
    except (GitNexusAdapterError, OSError, subprocess.SubprocessError) as exc:
        result = {
            "kind": "gitnexus-adapter-error",
            "status": "failed",
            "error_code": _operator_error_code(exc),
            "error": "operation-failed",
            "authority_invariants": {
                "mutation_authorized": False,
                "external_write_authorized": False,
                "completion_proven": False,
            },
        }
        exit_status = 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return exit_status


if __name__ == "__main__":
    sys.exit(operator_main())
