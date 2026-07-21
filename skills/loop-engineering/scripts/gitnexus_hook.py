#!/usr/bin/env python3
"""Optional Codex hook boundary for V2c-B GitNexus index freshness.

The hook is advisory.  It never makes stale index data adoptable and delegates
every refresh to the qualified V2c-A controller.
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import pathlib
import stat
import sys
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import gitnexus_adapter


HOOK_DRIVER_VERSION = "gitnexus-v2c-b-hook/1"
CONFIG_SCHEMA_VERSION = 1
MAX_INPUT_BYTES = 64 * 1024
MAX_CONFIG_BYTES = 64 * 1024
MAX_PATH_LENGTH = 4096
SESSION_SOURCES = frozenset({"startup", "resume", "clear", "compact"})
HOOK_EVENTS = frozenset({"SessionStart", "PostToolUse"})
MODES = frozenset({"notify-only", "auto-on-demand"})


class GitNexusHookError(RuntimeError):
    """Stable, path-redacted hook rejection."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


@dataclass(frozen=True)
class HookConfig:
    mode: str
    repository_root: pathlib.Path
    repository_id: str
    expected_remote: str
    git_executable: pathlib.Path | None
    qualification: dict[str, Any]
    refresh: dict[str, Any] | None


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GitNexusHookError("json-duplicate-key")
        result[key] = value
    return result


def _decode_json(raw: bytes, *, label: str) -> Any:
    try:
        text = raw.decode("utf-8", "strict")
        return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except GitNexusHookError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GitNexusHookError(f"{label}-json-invalid") from exc


def _expect_object(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GitNexusHookError(f"{label}-object-required")
    return value


def _expect_fields(
    value: Mapping[str, Any],
    *,
    label: str,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
) -> None:
    keys = set(value)
    if missing := required - keys:
        raise GitNexusHookError(f"{label}-field-missing")
    if keys - required - optional:
        raise GitNexusHookError(f"{label}-field-unknown")


def _expect_string(
    value: Any,
    *,
    label: str,
    maximum: int = 1024,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str) or (not value and not allow_empty) or len(value) > maximum:
        raise GitNexusHookError(f"{label}-string-invalid")
    return value


def _expect_bool(value: Any, *, label: str) -> bool:
    if not isinstance(value, bool):
        raise GitNexusHookError(f"{label}-boolean-required")
    return value


def _absolute_path(value: Any, *, label: str) -> pathlib.Path:
    raw = _expect_string(value, label=label, maximum=MAX_PATH_LENGTH)
    if "\x00" in raw:
        raise GitNexusHookError(f"{label}-nul-forbidden")
    candidate = pathlib.Path(raw)
    if not candidate.is_absolute():
        raise GitNexusHookError(f"{label}-absolute-required")
    return pathlib.Path(os.path.abspath(candidate))


def _optional_absolute_path(value: Any, *, label: str) -> pathlib.Path | None:
    if value is None:
        return None
    return _absolute_path(value, label=label)


def _reject_symlink_components(path: pathlib.Path, *, label: str) -> None:
    current = pathlib.Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current /= part
            if stat.S_ISLNK(current.lstat().st_mode):
                raise GitNexusHookError(f"{label}-symlink-forbidden")
    except GitNexusHookError:
        raise
    except OSError as exc:
        raise GitNexusHookError(f"{label}-unavailable") from exc


def _read_secure_config(path: pathlib.Path) -> bytes:
    if os.name != "posix":
        raise GitNexusHookError("platform-unsupported")
    if not path.is_absolute():
        raise GitNexusHookError("config-path-absolute-required")
    path = pathlib.Path(os.path.abspath(path))
    _reject_symlink_components(path, label="config-path")
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise GitNexusHookError("config-open-failed") from exc
    try:
        inspected = os.fstat(descriptor)
        if not stat.S_ISREG(inspected.st_mode):
            raise GitNexusHookError("config-regular-file-required")
        if stat.S_IMODE(inspected.st_mode) & 0o022:
            raise GitNexusHookError("config-permissions-unsafe")
        if hasattr(os, "geteuid") and inspected.st_uid != os.geteuid():
            raise GitNexusHookError("config-owner-mismatch")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(8192, MAX_CONFIG_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_CONFIG_BYTES:
                raise GitNexusHookError("config-too-large")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _parse_qualification(value: Any) -> dict[str, Any]:
    data = _expect_object(value, label="qualification")
    required = frozenset(
        {
            "executable",
            "allow_symlink",
            "node_executable",
            "allow_node_symlink",
            "package_root",
            "accepted_executable_sha256",
            "accepted_package_sha256",
            "accepted_runtime_sha256",
        }
    )
    _expect_fields(data, label="qualification", required=required)
    digest_fields = (
        "accepted_executable_sha256",
        "accepted_package_sha256",
    )
    result: dict[str, Any] = {
        "executable": _absolute_path(data["executable"], label="qualification-executable"),
        "allow_symlink": _expect_bool(data["allow_symlink"], label="qualification-allow-symlink"),
        "node_executable": _optional_absolute_path(
            data["node_executable"], label="qualification-node-executable"
        ),
        "allow_node_symlink": _expect_bool(
            data["allow_node_symlink"], label="qualification-allow-node-symlink"
        ),
        "package_root": _absolute_path(data["package_root"], label="qualification-package-root"),
    }
    for field in digest_fields:
        digest = _expect_string(data[field], label=f"qualification-{field}", maximum=64)
        if not gitnexus_adapter.SHA256_RE.fullmatch(digest):
            raise GitNexusHookError(f"qualification-{field}-invalid")
        result[field] = digest
    runtime_digest = data["accepted_runtime_sha256"]
    if runtime_digest is not None:
        runtime_digest = _expect_string(
            runtime_digest, label="qualification-accepted-runtime-sha256", maximum=64
        )
        if not gitnexus_adapter.SHA256_RE.fullmatch(runtime_digest):
            raise GitNexusHookError("qualification-accepted-runtime-sha256-invalid")
    result["accepted_runtime_sha256"] = runtime_digest
    if result["node_executable"] is not None and runtime_digest is None:
        raise GitNexusHookError("qualification-node-without-runtime-digest")
    return result


def _parse_refresh(value: Any, *, mode: str) -> dict[str, Any] | None:
    if mode == "notify-only":
        if value is not None:
            raise GitNexusHookError("refresh-config-forbidden-in-notify-mode")
        return None
    data = _expect_object(value, label="refresh")
    _expect_fields(
        data,
        label="refresh",
        required=frozenset({"gitnexus_home_parent", "lock_directory", "timeout_seconds"}),
    )
    timeout = data["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 3600:
        raise GitNexusHookError("refresh-timeout-invalid")
    return {
        "gitnexus_home_parent": _absolute_path(
            data["gitnexus_home_parent"], label="refresh-gitnexus-home-parent"
        ),
        "lock_directory": _absolute_path(data["lock_directory"], label="refresh-lock-directory"),
        "timeout_seconds": timeout,
    }


def load_config(path: pathlib.Path) -> HookConfig:
    document = _expect_object(_decode_json(_read_secure_config(path), label="config"), label="config")
    _expect_fields(
        document,
        label="config",
        required=frozenset({"schema_version", "mode", "repository", "qualification", "refresh"}),
    )
    if document["schema_version"] != CONFIG_SCHEMA_VERSION:
        raise GitNexusHookError("config-schema-unsupported")
    mode = _expect_string(document["mode"], label="config-mode", maximum=32)
    if mode not in MODES:
        raise GitNexusHookError("config-mode-unsupported")
    repository = _expect_object(document["repository"], label="repository")
    _expect_fields(
        repository,
        label="repository",
        required=frozenset({"root", "id", "expected_remote", "git_executable"}),
    )
    root = _absolute_path(repository["root"], label="repository-root")
    config_path = pathlib.Path(os.path.abspath(path))
    try:
        config_path.relative_to(root)
    except ValueError:
        pass
    else:
        raise GitNexusHookError("config-must-be-machine-local")
    return HookConfig(
        mode=mode,
        repository_root=root,
        repository_id=_expect_string(repository["id"], label="repository-id", maximum=512),
        expected_remote=_expect_string(
            repository["expected_remote"], label="repository-expected-remote", maximum=2048
        ),
        git_executable=_optional_absolute_path(
            repository["git_executable"], label="repository-git-executable"
        ),
        qualification=_parse_qualification(document["qualification"]),
        refresh=_parse_refresh(document["refresh"], mode=mode),
    )


def _read_hook_input(stream: Any) -> dict[str, Any]:
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise GitNexusHookError("hook-input-too-large")
    document = _expect_object(_decode_json(raw, label="hook-input"), label="hook-input")
    event = _expect_string(document.get("hook_event_name"), label="hook-event", maximum=32)
    if event not in HOOK_EVENTS:
        raise GitNexusHookError("hook-event-unsupported")
    common = frozenset(
        {"session_id", "transcript_path", "cwd", "hook_event_name", "model", "permission_mode"}
    )
    if event == "SessionStart":
        _expect_fields(
            document,
            label="session-start-input",
            required=frozenset({"cwd", "hook_event_name", "source"}),
            optional=common,
        )
        source = _expect_string(document["source"], label="session-source", maximum=16)
        if source not in SESSION_SOURCES:
            raise GitNexusHookError("session-source-unsupported")
    else:
        _expect_fields(
            document,
            label="post-tool-input",
            required=frozenset({"cwd", "hook_event_name", "tool_name"}),
            optional=common
            | frozenset({"turn_id", "tool_use_id", "tool_input", "tool_response"}),
        )
        if document["tool_name"] != "Bash":
            raise GitNexusHookError("post-tool-name-unsupported")
    _expect_string(document["cwd"], label="hook-cwd", maximum=MAX_PATH_LENGTH)
    return document


def _qualify(config: HookConfig) -> gitnexus_adapter.ExecutableQualification:
    values = config.qualification
    return gitnexus_adapter.qualify_executable(
        values["executable"],
        allow_symlink=values["allow_symlink"],
        runtime_path=values["node_executable"],
        allow_runtime_symlink=values["allow_node_symlink"],
        package_root=values["package_root"],
        accepted_executable_sha256=values["accepted_executable_sha256"],
        accepted_package_sha256=values["accepted_package_sha256"],
        accepted_runtime_sha256=values["accepted_runtime_sha256"],
    )


def _validate_cwd(document: Mapping[str, Any], root: pathlib.Path) -> None:
    try:
        cwd = pathlib.Path(document["cwd"])
        if not cwd.is_absolute():
            raise GitNexusHookError("hook-cwd-absolute-required")
        resolved = cwd.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except GitNexusHookError:
        raise
    except (OSError, ValueError) as exc:
        raise GitNexusHookError("hook-cwd-outside-repository") from exc


def _validate_control_directory(
    path: pathlib.Path, *, root: pathlib.Path, label: str
) -> pathlib.Path:
    _reject_symlink_components(path, label=label)
    try:
        inspected = path.stat()
        resolved = path.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except ValueError:
        pass
    except OSError as exc:
        raise GitNexusHookError(f"{label}-unavailable") from exc
    else:
        raise GitNexusHookError(f"{label}-inside-repository")
    if not stat.S_ISDIR(inspected.st_mode):
        raise GitNexusHookError(f"{label}-directory-required")
    if stat.S_IMODE(inspected.st_mode) & 0o022:
        raise GitNexusHookError(f"{label}-permissions-unsafe")
    if hasattr(os, "geteuid") and inspected.st_uid != os.geteuid():
        raise GitNexusHookError(f"{label}-owner-mismatch")
    return resolved


def _create_isolated_home(parent: pathlib.Path, *, root: pathlib.Path) -> pathlib.Path:
    safe_parent = _validate_control_directory(
        parent, root=root, label="refresh-home-parent"
    )
    try:
        created = pathlib.Path(
            tempfile.mkdtemp(prefix="gitnexus-v2c-b-", dir=safe_parent)
        )
        created.chmod(0o700)
        return created
    except OSError as exc:
        raise GitNexusHookError("refresh-home-create-failed") from exc


def _failure_marker(
    parent: pathlib.Path,
    *,
    root: pathlib.Path,
    repository_identity_digest: str,
) -> pathlib.Path:
    if not gitnexus_adapter.SHA256_RE.fullmatch(repository_identity_digest):
        raise GitNexusHookError("repository-identity-digest-invalid")
    safe_parent = _validate_control_directory(
        parent, root=root, label="refresh-home-parent"
    )
    return safe_parent / f".codex-v2c-b-auto-disabled-{repository_identity_digest}.json"


def _failure_marker_exists(path: pathlib.Path) -> bool:
    try:
        inspected = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise GitNexusHookError("failure-marker-inspection-failed") from exc
    if (
        not stat.S_ISREG(inspected.st_mode)
        or stat.S_ISLNK(inspected.st_mode)
        or inspected.st_nlink != 1
        or stat.S_IMODE(inspected.st_mode) & 0o022
        or (hasattr(os, "geteuid") and inspected.st_uid != os.geteuid())
    ):
        raise GitNexusHookError("failure-marker-unsafe")
    return True


def _record_failure_marker(
    path: pathlib.Path,
    *,
    repository: gitnexus_adapter.RepositoryState,
    qualification: gitnexus_adapter.ExecutableQualification,
    reason: str,
) -> None:
    if _failure_marker_exists(path):
        return
    body = {
        "driver_version": HOOK_DRIVER_VERSION,
        "head": repository.head,
        "kind": "gitnexus-hook-auto-refresh-disabled",
        "qualification_fingerprint": qualification.fingerprint,
        "reason": reason[:256],
        "repository_identity_digest": repository.identity["repository_identity_digest"],
        "status": "disabled-after-failure",
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(path, flags, 0o600)
        created = True
        written = 0
        while written < len(raw):
            count = os.write(descriptor, raw[written:])
            if count <= 0:
                raise OSError(errno.EIO, "short write")
            written += count
        os.fsync(descriptor)
    except FileExistsError:
        if not _failure_marker_exists(path):
            raise GitNexusHookError("failure-marker-race-unsafe")
    except OSError as exc:
        raise GitNexusHookError("failure-marker-write-failed") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if created:
        directory_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            directory_flags |= os.O_DIRECTORY
        if hasattr(os, "O_CLOEXEC"):
            directory_flags |= os.O_CLOEXEC
        try:
            parent_descriptor = os.open(path.parent, directory_flags)
            try:
                os.fsync(parent_descriptor)
            finally:
                os.close(parent_descriptor)
        except OSError as exc:
            raise GitNexusHookError("failure-marker-durability-uncertain") from exc


def _additional_context(event: str, message: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        }
    }


def _warning(error_code: str) -> dict[str, Any]:
    return {
        "systemMessage": (
            f"GitNexus freshness hook skipped ({error_code}); no refresh or index adoption occurred."
        )
    }


def _invalid_config(error_code: str) -> dict[str, Any]:
    return {
        "driver_version": HOOK_DRIVER_VERSION,
        "error_code": error_code,
        "kind": "gitnexus-hook-config-status",
        "status": "invalid",
    }


def _adapter_error_code(error: BaseException) -> str:
    if isinstance(error, gitnexus_adapter.ProcessBoundaryError):
        return error.error_code
    if isinstance(error, gitnexus_adapter.ProbeDeadlineError):
        return "probe-deadline-expired"
    if isinstance(error, OSError):
        return "os-error"
    return "adapter-rejected"


def evaluate_hook(config: HookConfig, document: Mapping[str, Any]) -> dict[str, Any] | None:
    event = document["hook_event_name"]
    _validate_cwd(document, config.repository_root)
    qualification = _qualify(config)
    repository = gitnexus_adapter.collect_repository_state(
        config.repository_root,
        canonical_repository_id=config.repository_id,
        expected_remote=config.expected_remote,
        git_executable=config.git_executable,
    )
    snapshot = gitnexus_adapter.collect_tracked_snapshot(
        repository.root, git_executable=config.git_executable
    )
    metadata = gitnexus_adapter.assess_metadata(repository, snapshot, qualification)
    if metadata.state == "fresh":
        return None

    revision_changed = metadata.indexed_revision != repository.head
    clean = not snapshot.tracked_dirty and not snapshot.outside_derived_dirty
    if (
        event == "PostToolUse"
        and metadata.state == "stale"
        and metadata.reason == "working-tree-dirty"
        and not revision_changed
    ):
        return None

    refresh_eligible = (
        config.mode == "auto-on-demand"
        and clean
        and metadata.state in {"stale", "missing"}
        and (revision_changed or metadata.state == "missing")
    )
    if refresh_eligible:
        assert config.refresh is not None
        marker = _failure_marker(
            config.refresh["gitnexus_home_parent"],
            root=repository.root,
            repository_identity_digest=repository.identity["repository_identity_digest"],
        )
        if _failure_marker_exists(marker):
            return _additional_context(
                event,
                "GitNexus automatic refresh remains disabled after a prior failure. "
                "The stale index must not be used; operator inspection and explicit circuit-breaker clearance are required.",
            )
        isolated_home = _create_isolated_home(
            config.refresh["gitnexus_home_parent"], root=repository.root
        )
        controller = gitnexus_adapter.RefreshController(
            qualification,
            enabled=True,
            timeout_seconds=config.refresh["timeout_seconds"],
            gitnexus_home=isolated_home,
            lock_directory=config.refresh["lock_directory"],
            git_executable=config.git_executable,
        )
        try:
            refreshed = controller.refresh(
                repository,
                expected_head=repository.head,
                explicit_opt_in=True,
            )
        except (gitnexus_adapter.GitNexusAdapterError, OSError) as exc:
            _record_failure_marker(
                marker,
                repository=repository,
                qualification=qualification,
                reason=f"adapter-{_adapter_error_code(exc)}",
            )
            raise
        if refreshed.status == "refreshed":
            return _additional_context(
                event,
                "GitNexus derived index was refreshed and verified for the current clean HEAD. "
                "The index remains advisory and does not prove task completion.",
            )
        _record_failure_marker(
            marker,
            repository=repository,
            qualification=qualification,
            reason=refreshed.reason,
        )
        return _additional_context(
            event,
            f"GitNexus derived-index refresh failed ({refreshed.reason}); the stale index must not be used.",
        )

    suffix = (
        "Automatic refresh is disabled."
        if config.mode == "notify-only"
        else "Automatic refresh was not safe for the current repository state."
    )
    return _additional_context(
        event,
        f"GitNexus derived index is {metadata.state} ({metadata.reason}); it must not be used. {suffix}",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional V2c-B GitNexus freshness hook.")
    parser.add_argument("--config", required=True, help="Absolute machine-local hook configuration path.")
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate the local configuration without reading hook stdin or contacting GitNexus.",
    )
    return parser


def hook_main(argv: Sequence[str] | None = None, *, input_stream: Any | None = None) -> int:
    arguments = _parser().parse_args(argv)
    exit_status = 0
    try:
        config_path = _absolute_path(arguments.config, label="config-path")
        config = load_config(config_path)
        if arguments.validate_config:
            output: dict[str, Any] | None = {
                "driver_version": HOOK_DRIVER_VERSION,
                "kind": "gitnexus-hook-config-status",
                "mode": config.mode,
                "status": "valid",
            }
        else:
            stream = input_stream if input_stream is not None else sys.stdin.buffer
            output = evaluate_hook(config, _read_hook_input(stream))
    except GitNexusHookError as exc:
        if arguments.validate_config:
            output = _invalid_config(exc.error_code)
            exit_status = 2
        else:
            output = _warning(exc.error_code)
    except (gitnexus_adapter.GitNexusAdapterError, OSError) as exc:
        error_code = f"adapter-{_adapter_error_code(exc)}"
        if arguments.validate_config:
            output = _invalid_config(error_code)
            exit_status = 2
        else:
            output = _warning(error_code)
    except Exception:
        if arguments.validate_config:
            output = _invalid_config("internal-error")
            exit_status = 2
        else:
            output = _warning("internal-error")
    if output is not None:
        print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return exit_status


if __name__ == "__main__":
    sys.exit(hook_main())
