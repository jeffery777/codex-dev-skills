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
import math
import os
import pathlib
import re
import selectors
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit

import git_source
import memory_contract


DRIVER_VERSION = "gitnexus-v2c-a/4"
INDEX_IDENTITY_CONTRACT_VERSION = "gitnexus-index-identity/v1"
PR_REVIEW_IDENTITY_CONTRACT_VERSION = "gitnexus-pr-review-identity/v1"
INDEX_IDENTITY_FILENAME = "codex-index-identity.json"
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
# A closed 1.6.12 producer subset; adoption also needs a caller-owned local profile.
LOCAL_1612_SCHEMA = "gitnexus-metadata-1.6.12/v1"
META_1612_REQUIRED_FIELDS = (META_REQUIRED_FIELDS - {"schemaVersion"}) | {
    "storagePath", "contentRetention", "contentRetentionSchemaVersion",
    "ftsProfile", "runnerIdentity", "schemaFingerprint",
    "scopeExtractionReceipt", "analysisFeatures", "springVendorPrefixes",
    "embeddingDims", "indexCoverage",
}
META_1612_REFUSED_FIELDS = frozenset({
    "incrementalInProgress", "graphWriteCollapsed", "scopeExtractionFailures",
    "embeddingCheckpoint", "pdg",
})
MAX_METADATA_BYTES = 4 * 1024 * 1024
MAX_INDEX_IDENTITY_BYTES = 256 * 1024
MAX_SNAPSHOT_ENTRIES = 250_000
MAX_SNAPSHOT_FILE_BYTES = 512 * 1024 * 1024
MAX_SNAPSHOT_DEPTH = 256
FRESHNESS_STATES = frozenset(
    {"fresh", "stale", "missing", "partial", "unsupported", "incompatible", "corrupt", "unknown"}
)
SAFE_ENVIRONMENT_KEYS = frozenset(
    {"HOME", "LANG", "LC_ALL", "LC_CTYPE"}
)
MAX_GIT_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_DERIVED_INDEX_ENTRIES = 100_000
MAX_PACKAGE_ENTRIES = 250_000
MAX_PACKAGE_BYTES = 2 * 1024 * 1024 * 1024
PROTECTED_BASENAMES = frozenset({"AGENTS.md", "CLA" + "UDE.md"})
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
FLAG_RE = re.compile(r"(?<![A-Za-z0-9-])--[a-z][a-z0-9-]*")
VERSION_RE = re.compile(r"(?<![0-9])v?(1\.6\.9)(?![0-9.])")
GRAPH_PROVIDER = "lady" + "bugdb"
FTS_PROVIDER = GRAPH_PROVIDER + "-fts"
VECTOR_PROVIDER = GRAPH_PROVIDER + "-vector"
_LOCK_DIRECTORY_VALIDATION_HOOK: Callable[[pathlib.Path], None] = lambda _path: None
_HOME_THREAD_LOCKS: dict[str, threading.Lock] = {}
_HOME_THREAD_LOCKS_GUARD = threading.Lock()


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
class Local1612Profile:
    """Machine-local accepted evidence, never inferred from index metadata."""

    runner_json: str
    dependency_sha256: str
    coverage_paths: tuple[str, ...]
    probe_sha256: str


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
    runtime_symlink_policy: str | None = None
    runtime_launcher: str = "direct"
    package_root: pathlib.Path | None = None
    package_tree_sha256: str | None = None
    package_stat_identity: tuple[int, int, int, int] | None = None
    trusted_provenance_digest: str | None = None
    local_1612: Local1612Profile | None = None


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
    branch: str | None
    tracked_dirty: bool
    tracked_derived_present: bool
    outside_derived_dirty: bool
    tracked_state_digest: str
    protected_state_digest: str
    outside_derived_status_digest: str
    complete_status_digest: str
    worktree_state_digest: str
    untracked_dirty: bool = False
    relevant_content_digest: str = ""


@dataclass(frozen=True)
class MetadataResult:
    state: str
    reason: str
    indexed_revision: str | None
    metadata_digest: str | None
    metadata: dict[str, Any] | None
    index_identity: dict[str, Any] | None = None


@dataclass(frozen=True)
class RefreshResult:
    status: str
    reason: str
    receipt: dict[str, Any]


@dataclass(frozen=True)
class _IsolatedHomeIdentity:
    path: pathlib.Path
    device: int
    inode: int
    mode: int
    uid: int | None


Runner = Callable[..., subprocess.CompletedProcess[Any]]


def _canonical_digest(value: Any) -> str:
    return memory_contract.canonical_digest(value)


def _validated_deadline(deadline: float) -> float:
    if (
        isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(deadline)
    ):
        raise GitNexusAdapterError(
            "deadline must be a finite monotonic timestamp"
        )
    return float(deadline)


def _check_deadline(deadline: float | None) -> None:
    if deadline is not None:
        validated = _validated_deadline(deadline)
        if time.monotonic() >= validated:
            raise ProbeDeadlineError()


def _validate_timeout_seconds(
    timeout_seconds: int, *, label: str, maximum: int
) -> None:
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, int)
        or not 1 <= timeout_seconds <= maximum
    ):
        raise GitNexusAdapterError(
            f"{label} timeout must be an integer from 1 through {maximum} seconds"
        )


def _timeout_deadline(timeout_seconds: int, *, label: str, maximum: int) -> float:
    _validate_timeout_seconds(timeout_seconds, label=label, maximum=maximum)
    return time.monotonic() + timeout_seconds


def _refresh_deadline(timeout_seconds: int) -> float:
    return _timeout_deadline(timeout_seconds, label="refresh", maximum=3_600)


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


def _discover_explicit_executable(
    configured_path: str | os.PathLike[str] | None,
    *,
    label: str,
    allow_symlink: bool = False,
) -> tuple[pathlib.Path, str]:
    """Resolve an explicitly supplied absolute executable under one policy."""
    if configured_path is None:
        raise GitNexusAdapterError(f"explicit {label} executable path is required")
    candidate = pathlib.Path(os.fspath(configured_path))
    if not candidate.is_absolute():
        raise GitNexusAdapterError(f"{label} executable path must be absolute")
    candidate = pathlib.Path(os.path.abspath(candidate))
    try:
        current = pathlib.Path(candidate.anchor)
        for part in candidate.parts[1:-1]:
            current /= part
            if stat.S_ISLNK(current.lstat().st_mode):
                raise GitNexusAdapterError(
                    f"{label} executable parent path contains a symlink"
                )
        link_stat = candidate.lstat()
    except OSError as exc:
        raise GitNexusAdapterError(f"{label} executable cannot be inspected") from exc
    is_link = stat.S_ISLNK(link_stat.st_mode)
    if is_link and not allow_symlink:
        raise GitNexusAdapterError(f"{label} executable symlink is forbidden by policy")
    if is_link:
        try:
            target = pathlib.Path(os.readlink(candidate))
        except OSError as exc:
            raise GitNexusAdapterError(
                f"{label} executable symlink cannot be inspected"
            ) from exc
        if not target.is_absolute():
            target = candidate.parent / target
        target = pathlib.Path(os.path.abspath(target))
        current = pathlib.Path(target.anchor)
        try:
            for part in target.parts[1:]:
                current /= part
                if stat.S_ISLNK(current.lstat().st_mode):
                    raise GitNexusAdapterError(
                        f"{label} executable permits only one final symlink"
                    )
        except OSError as exc:
            raise GitNexusAdapterError(
                f"{label} executable symlink target cannot be inspected"
            ) from exc
        resolved = target.resolve(strict=True)
        if resolved != target:
            raise GitNexusAdapterError(
                f"{label} executable symlink target must be canonical"
            )
    else:
        resolved = candidate.resolve(strict=True)
        if resolved != candidate:
            raise GitNexusAdapterError(
                f"{label} executable path must be canonical"
            )
    resolved_stat = resolved.stat()
    if not stat.S_ISREG(resolved_stat.st_mode):
        raise GitNexusAdapterError(f"{label} executable must resolve to a regular file")
    if resolved_stat.st_mode & 0o111 == 0:
        raise GitNexusAdapterError(f"{label} executable is not executable")
    return resolved, "resolved-symlink" if is_link else "regular-file-only"


def discover_executable(
    configured_path: str | os.PathLike[str] | None,
    *,
    allow_symlink: bool = False,
) -> tuple[pathlib.Path, str]:
    """Resolve an explicit GitNexus path under a regular-file/symlink policy."""
    return _discover_explicit_executable(
        configured_path,
        label="GitNexus",
        allow_symlink=allow_symlink,
    )


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


def _discover_package_root(
    configured_path: str | os.PathLike[str] | None,
    executable: pathlib.Path,
) -> pathlib.Path:
    """Bind an explicit canonical package directory containing the entry."""
    if configured_path is None:
        raise GitNexusAdapterError("explicit GitNexus package root is required")
    candidate = pathlib.Path(os.fspath(configured_path))
    if not candidate.is_absolute():
        raise GitNexusAdapterError("GitNexus package root must be absolute")
    candidate = pathlib.Path(os.path.abspath(candidate))
    current = pathlib.Path(candidate.anchor)
    try:
        for part in candidate.parts[1:]:
            current /= part
            if stat.S_ISLNK(current.lstat().st_mode):
                raise GitNexusAdapterError("GitNexus package root contains a symlink")
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise GitNexusAdapterError("GitNexus package root cannot be inspected") from exc
    if resolved != candidate or not resolved.is_dir():
        raise GitNexusAdapterError("GitNexus package root must be a canonical directory")
    try:
        executable.relative_to(resolved)
    except ValueError as exc:
        raise GitNexusAdapterError("GitNexus executable must be inside the package root") from exc
    return resolved


def _package_regular_file_at(
    directory_fd: int,
    name: str,
    expected: os.stat_result,
    *,
    deadline: float | None = None,
    maximum_bytes: int = MAX_PACKAGE_BYTES,
) -> tuple[str, os.stat_result]:
    """Hash one descriptor-bound package file without following a late link."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise GitNexusAdapterError(
            "POSIX no-follow nonblocking package operations are unavailable"
        )
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_NOFOLLOW
            | os.O_NONBLOCK
            | getattr(os, "O_CLOEXEC", 0),
            dir_fd=directory_fd,
        )
    except OSError as exc:
        raise GitNexusAdapterError(
            "GitNexus package file cannot be opened safely"
        ) from exc
    try:
        opened = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino, opened.st_mode)
            != (expected.st_dev, expected.st_ino, expected.st_mode)
            or not stat.S_ISREG(opened.st_mode)
        ):
            raise GitNexusAdapterError(
                "GitNexus package file changed while it was opened"
            )
        digest = hashlib.sha256()
        total = 0
        while True:
            _check_deadline(deadline)
            chunk = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - total))
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                raise GitNexusAdapterError(
                    "GitNexus package tree exceeds qualification bounds"
                )
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_mode)
            != (opened.st_dev, opened.st_ino, opened.st_mode)
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns
        ):
            raise GitNexusAdapterError(
                "GitNexus package file changed while it was read"
            )
        return digest.hexdigest(), opened
    finally:
        os.close(descriptor)


def _contained_package_target(relative: str, raw_target: str) -> tuple[str, ...]:
    target = pathlib.PurePosixPath(raw_target)
    if target.is_absolute():
        raise GitNexusAdapterError("GitNexus package symlink target must be relative")
    components = list(pathlib.PurePosixPath(relative).parent.parts)
    for part in target.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not components:
                raise GitNexusAdapterError(
                    "GitNexus package symlink must stay inside the package root"
                )
            components.pop()
            continue
        components.append(part)
    if not components:
        raise GitNexusAdapterError(
            "GitNexus package symlink must target a regular file"
        )
    return tuple(components)


def _package_target_identity_at(
    root_fd: int,
    components: Sequence[str],
    *,
    deadline: float | None = None,
    maximum_bytes: int = MAX_PACKAGE_BYTES,
) -> tuple[str, os.stat_result]:
    """Open a lexically confined direct file target from the package root."""
    directory_fd = os.dup(root_fd)
    try:
        for component in components[:-1]:
            _check_deadline(deadline)
            try:
                expected = os.stat(
                    component, dir_fd=directory_fd, follow_symlinks=False
                )
                child_fd = os.open(
                    component,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
            except OSError as exc:
                raise GitNexusAdapterError(
                    "GitNexus package symlink must stay inside the package root"
                ) from exc
            opened = os.fstat(child_fd)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or (opened.st_dev, opened.st_ino, opened.st_mode)
                != (expected.st_dev, expected.st_ino, expected.st_mode)
            ):
                os.close(child_fd)
                raise GitNexusAdapterError(
                    "GitNexus package symlink parent changed during inspection"
                )
            os.close(directory_fd)
            directory_fd = child_fd
        try:
            expected_target = os.stat(
                components[-1], dir_fd=directory_fd, follow_symlinks=False
            )
        except OSError as exc:
            raise GitNexusAdapterError(
                "GitNexus package symlink target cannot be inspected"
            ) from exc
        if not stat.S_ISREG(expected_target.st_mode):
            raise GitNexusAdapterError(
                "GitNexus package symlink must target a regular file"
            )
        if expected_target.st_size > maximum_bytes:
            raise GitNexusAdapterError("qualified input exceeds its byte bound")
        return _package_regular_file_at(
            directory_fd,
            components[-1],
            expected_target,
            deadline=deadline,
            maximum_bytes=maximum_bytes,
        )
    finally:
        os.close(directory_fd)


def _package_tree_identity(
    root: pathlib.Path,
    *,
    deadline: float | None = None,
) -> tuple[str, tuple[int, int, int, int]]:
    """Hash a descriptor-bound package tree and contained direct file links."""
    _check_deadline(deadline)
    root_fd = _open_directory_nofollow(root)
    root_info = os.fstat(root_fd)
    records: list[dict[str, Any]] = []
    total_bytes = 0
    entry_count = 0

    def walk(directory_fd: int, prefix: str, depth: int) -> None:
        nonlocal total_bytes, entry_count
        _check_deadline(deadline)
        if depth > MAX_SNAPSHOT_DEPTH:
            raise GitNexusAdapterError(
                "GitNexus package directory depth exceeds qualification bounds"
            )
        try:
            with os.scandir(directory_fd) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            raise GitNexusAdapterError(
                "GitNexus package tree cannot be enumerated"
            ) from exc
        for entry in entries:
            _check_deadline(deadline)
            entry_count += 1
            if entry_count > MAX_PACKAGE_ENTRIES:
                raise GitNexusAdapterError(
                    "GitNexus package tree exceeds qualification bounds"
                )
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise GitNexusAdapterError(
                    "GitNexus package tree cannot be inspected"
                ) from exc
            if stat.S_ISDIR(info.st_mode):
                try:
                    child_fd = os.open(
                        entry.name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=directory_fd,
                    )
                except OSError as exc:
                    raise GitNexusAdapterError(
                        "GitNexus package directory cannot be opened safely"
                    ) from exc
                try:
                    opened = os.fstat(child_fd)
                    if (
                        (opened.st_dev, opened.st_ino, opened.st_mode)
                        != (info.st_dev, info.st_ino, info.st_mode)
                    ):
                        raise GitNexusAdapterError(
                            "GitNexus package directory changed while it was opened"
                        )
                    records.append(
                        {
                            "path": relative,
                            "kind": "directory",
                            "mode": stat.S_IMODE(opened.st_mode),
                        }
                    )
                    walk(child_fd, relative, depth + 1)
                    after = os.fstat(child_fd)
                    if (
                        (after.st_dev, after.st_ino, after.st_mode)
                        != (opened.st_dev, opened.st_ino, opened.st_mode)
                        or after.st_mtime_ns != opened.st_mtime_ns
                    ):
                        raise GitNexusAdapterError(
                            "GitNexus package directory changed during inspection"
                        )
                finally:
                    os.close(child_fd)
                continue
            if stat.S_ISREG(info.st_mode):
                file_digest, opened = _package_regular_file_at(
                    directory_fd,
                    entry.name,
                    info,
                    deadline=deadline,
                )
                total_bytes += opened.st_size
                if total_bytes > MAX_PACKAGE_BYTES:
                    raise GitNexusAdapterError(
                        "GitNexus package tree exceeds qualification bounds"
                    )
                records.append(
                    {
                        "path": relative,
                        "kind": "file",
                        "mode": stat.S_IMODE(opened.st_mode),
                        "size": opened.st_size,
                        "sha256": file_digest,
                    }
                )
                continue
            if stat.S_ISLNK(info.st_mode):
                try:
                    raw_target = os.readlink(entry.name, dir_fd=directory_fd)
                    after_link = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise GitNexusAdapterError(
                        "GitNexus package symlink cannot be inspected"
                    ) from exc
                if (
                    after_link.st_dev,
                    after_link.st_ino,
                    after_link.st_mode,
                    after_link.st_size,
                    after_link.st_mtime_ns,
                ) != (
                    info.st_dev,
                    info.st_ino,
                    info.st_mode,
                    info.st_size,
                    info.st_mtime_ns,
                ):
                    raise GitNexusAdapterError(
                        "GitNexus package symlink changed during inspection"
                    )
                target_digest, target_info = _package_target_identity_at(
                    root_fd,
                    _contained_package_target(relative, raw_target),
                    deadline=deadline,
                )
                total_bytes += target_info.st_size
                if total_bytes > MAX_PACKAGE_BYTES:
                    raise GitNexusAdapterError(
                        "GitNexus package tree exceeds qualification bounds"
                    )
                records.append(
                    {
                        "path": relative,
                        "kind": "symlink",
                        "mode": stat.S_IMODE(info.st_mode),
                        "target": raw_target,
                        "target_sha256": target_digest,
                    }
                )
                continue
            raise GitNexusAdapterError(
                "GitNexus package tree contains a special file"
            )

    try:
        walk(root_fd, "", 0)
        after_root = os.fstat(root_fd)
        if (
            (after_root.st_dev, after_root.st_ino, after_root.st_mode)
            != (root_info.st_dev, root_info.st_ino, root_info.st_mode)
            or after_root.st_mtime_ns != root_info.st_mtime_ns
        ):
            raise GitNexusAdapterError(
                "GitNexus package root changed during inspection"
            )
    finally:
        os.close(root_fd)
    body = {"schema": "gitnexus-package-tree/v2", "entries": records}
    identity = (
        root_info.st_dev,
        root_info.st_ino,
        root_info.st_size,
        root_info.st_mtime_ns,
    )
    return _canonical_digest(body), identity


def _require_expected_digest(value: str | None, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise GitNexusAdapterError(f"caller-owned {label} sha256 is required")
    return value


def _script_runtime(
    executable: pathlib.Path,
    configured_path: str | os.PathLike[str] | None,
    *,
    allow_symlink: bool = False,
    deadline: float | None = None,
) -> tuple[pathlib.Path, str, tuple[int, int, int, int], str, str] | None:
    """Resolve and bind the interpreter used by every qualified script entry."""
    with executable.open("rb") as stream:
        shebang = stream.readline(256).rstrip(b"\r\n")
    if not shebang.startswith(b"#!"):
        if configured_path is not None:
            raise GitNexusAdapterError(
                "runtime executable path is only valid for a script GitNexus entry"
            )
        return None
    uses_env = shebang.startswith(b"#!/usr/bin/env")
    uses_env_node = False
    if uses_env:
        try:
            tokens = shlex.split(shebang[2:].decode("ascii", "strict"))
        except (UnicodeError, ValueError) as exc:
            raise GitNexusAdapterError("GitNexus env launcher is unsupported") from exc
        uses_env_node = tokens in (
            ["/usr/bin/env", "node"],
            ["/usr/bin/env", "-S", "node"],
        )
        if not uses_env_node:
            raise GitNexusAdapterError("GitNexus env launcher is unsupported")
    if uses_env_node:
        runtime, symlink_policy = _discover_explicit_executable(
            configured_path,
            label="Node",
            allow_symlink=allow_symlink,
        )
        launcher = "bound-node"
    else:
        try:
            tokens = shlex.split(shebang[2:].decode("ascii", "strict"))
        except (UnicodeError, ValueError) as exc:
            raise GitNexusAdapterError("GitNexus script launcher is unsupported") from exc
        if len(tokens) != 1 or not pathlib.PurePath(tokens[0]).is_absolute():
            raise GitNexusAdapterError("GitNexus script launcher is unsupported")
        if configured_path is not None:
            raise GitNexusAdapterError(
                "runtime executable path is only valid for an env-node GitNexus entry"
            )
        try:
            interpreter_target = pathlib.Path(tokens[0]).resolve(strict=True)
        except OSError as exc:
            raise GitNexusAdapterError("GitNexus script interpreter cannot be resolved") from exc
        runtime, _ = _discover_explicit_executable(
            interpreter_target,
            label="GitNexus interpreter",
            allow_symlink=False,
        )
        symlink_policy = "shebang-resolved"
        launcher = "bound-shebang"
    with runtime.open("rb") as stream:
        if stream.read(2) == b"#!":
            raise GitNexusAdapterError(
                "GitNexus runtime interpreter must be a native executable"
            )
    digest, identity = _executable_identity(runtime, deadline=deadline)
    return runtime, digest, identity, symlink_policy, launcher


def _local_json(value: Any) -> str:
    # A separate domain permits Unicode path keys without changing Memory rules.
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _local_input(path: pathlib.Path, *, deadline: float | None = None) -> tuple[dict[str, Any], bytes | None]:
    """Read a small local input through no-follow descriptors at every hop."""
    if not path.is_absolute() or ".." in path.parts:
        raise GitNexusAdapterError("local identity path must be absolute")
    descriptor = _open_directory_nofollow(pathlib.Path("/"))
    try:
        for component in path.parts[1:-1]:
            _check_deadline(deadline)
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        info = os.stat(path.name, dir_fd=descriptor, follow_symlinks=False)
        record = {"path": str(path), "kind": "directory", "identity": [info.st_dev, info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns]}
        if stat.S_ISDIR(info.st_mode):
            return record, None
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_METADATA_BYTES:
            raise GitNexusAdapterError("local identity input must be a small regular file or directory")
        digest, _ = _package_regular_file_at(descriptor, path.name, info, deadline=deadline)
        raw = _read_regular_at(descriptor, path.name, maximum_bytes=MAX_METADATA_BYTES, deadline=deadline)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise GitNexusAdapterError("local identity input changed while read")
        return {**record, "kind": "file", "sha256": digest}, raw
    except FileNotFoundError:
        return {"path": str(path), "kind": "missing"}, None
    except OSError as exc:
        raise GitNexusAdapterError("local identity path is linked or unavailable") from exc
    finally:
        os.close(descriptor)


def local_1612_dependency_identity(package_root: pathlib.Path, *, deadline: float | None = None) -> tuple[str, int, str | None]:
    """Bind the self-contained distribution's closure and ancestor resolution.

    This deliberately rejects external packages and directory links. It follows
    the fixed 1.6.12 runtime/optional/peer/local-dev manifest subset, not npm
    installation or arbitrary package-manager layouts. No code is executed.
    """
    records: dict[str, tuple[dict[str, Any], bytes | None]] = {}
    edges = 0
    total_bytes = 0

    def inspect(path: pathlib.Path) -> tuple[dict[str, Any], bytes | None]:
        nonlocal total_bytes
        _check_deadline(deadline)
        key = str(path)
        if key not in records:
            if len(records) >= 100_000:
                raise GitNexusAdapterError("dependency resolution exceeds path bounds")
            records[key] = _local_input(path, deadline=deadline)
            total_bytes += len(records[key][1] or b"")
            if total_bytes > MAX_METADATA_BYTES:
                raise GitNexusAdapterError("dependency manifests exceed byte bounds")
        return records[key]

    def resolve(parent: pathlib.Path, name: str, *, runtime_input: bool = True) -> pathlib.Path | None:
        nonlocal edges
        edges += 1
        if edges > 100_000 or not re.fullmatch(r"(?:@[A-Za-z0-9._-]+/)?[A-Za-z0-9._-]+", name) or any(p in {".", ".."} for p in name.split("/")):
            raise GitNexusAdapterError("dependency name or edge bound is invalid")
        for cursor in (parent, *parent.parents):
            candidate = cursor / "node_modules"
            inspect(candidate)
            for part in name.split("/"):
                candidate /= part
                inspect(candidate)
            outside = not candidate.is_relative_to(package_root)
            if outside and runtime_input:
                for suffix in (".js", ".json", ".node"):
                    fallback, _ = inspect(candidate.with_name(candidate.name + suffix))
                    if fallback["kind"] != "missing":
                        raise GitNexusAdapterError("external dependency fallback is outside the local profile")
            record, _ = inspect(candidate / "package.json")
            if record["kind"] == "file":
                return candidate
            if outside and runtime_input and inspect(candidate)[0]["kind"] != "missing":
                raise GitNexusAdapterError("external dependency without a manifest is outside the local profile")
            if record["kind"] != "missing":
                raise GitNexusAdapterError("dependency manifest is not regular")
        return None

    queue = [package_root]
    visited = {package_root}
    for parent in queue:
        if len(queue) > 10_000:
            raise GitNexusAdapterError("dependency closure exceeds package bounds")
        record, raw = inspect(parent / "package.json")
        try:
            manifest = json.loads(raw) if raw is not None else None
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise GitNexusAdapterError("dependency manifest is invalid") from exc
        if not isinstance(manifest, dict):
            raise GitNexusAdapterError("dependency manifest is missing or invalid")
        if parent == package_root and manifest.get("version") != "1.6.12":
            raise GitNexusAdapterError("local distribution must be exactly 1.6.12")
        names: set[str] = set()
        for section in ("dependencies", "optionalDependencies", "peerDependencies", "devDependencies"):
            entries = manifest.get(section, {})
            if not isinstance(entries, dict) or any(not isinstance(n, str) or not isinstance(s, str) for n, s in entries.items()):
                raise GitNexusAdapterError("dependency section is invalid")
            for name, specifier in entries.items():
                local = bool(re.match(r"^(?:(?:file|link|workspace|portal):|\.{1,2}[/\\]|~[/\\]|[/\\]|[A-Za-z]:)", specifier.strip()))
                if section != "devDependencies" or local:
                    names.add(name)
                elif parent == package_root:
                    # Root registry dev tools are not runtime inputs. A resolved
                    # checkout link would matter; all directory links are refused.
                    resolved = resolve(parent, name, runtime_input=False)
                    if resolved is not None and "node_modules" not in resolved.parts:
                        names.add(name)
        for name in sorted(names):
            child = resolve(parent, name)
            if child is None:
                continue
            if not child.is_relative_to(package_root):
                raise GitNexusAdapterError("external dependency is outside the local profile")
            if len(child.relative_to(package_root).parts) > MAX_SNAPSHOT_DEPTH:
                raise GitNexusAdapterError("dependency closure exceeds depth bounds")
            if child not in visited:
                visited.add(child)
                queue.append(child)
    lockfile = None
    for parent in (package_root, *package_root.parents):
        candidate = parent / "package-lock.json"
        record, _ = inspect(candidate)
        if record["kind"] == "file":
            lockfile = str(candidate)
            break
        if record["kind"] != "missing":
            raise GitNexusAdapterError("nearest dependency lockfile is not regular")
    # Revalidate every resolution/absence input at the return boundary.
    for path, (record, _) in records.items():
        if _local_input(pathlib.Path(path), deadline=deadline)[0] != record:
            raise GitNexusAdapterError("dependency resolution changed during inspection")
    body = {"schema": "gitnexus-local-dependency-closure/v1", "package_count": len(queue), "lockfile": lockfile, "inputs": [records[k][0] for k in sorted(records)]}
    return hashlib.sha256(_local_json(body).encode("ascii")).hexdigest(), len(queue), lockfile


def _qualification_body(
    *,
    executable_sha256: str,
    analyze_flags: Sequence[str],
    symlink_policy: str,
    runtime_executable_sha256: str | None,
    runtime_symlink_policy: str | None = None,
    runtime_launcher: str | None = None,
    package_tree_sha256: str | None = None,
    trusted_provenance_digest: str | None = None,
    local_1612: Local1612Profile | None = None,
) -> dict[str, Any]:
    launcher = runtime_launcher or (
        "bound-node" if runtime_executable_sha256 else "direct"
    )
    body = {
        "driver_version": DRIVER_VERSION,
        "executable_sha256": executable_sha256,
        "runtime_executable_sha256": runtime_executable_sha256,
        "runtime_symlink_policy": runtime_symlink_policy,
        "runtime_launcher": launcher,
        "package_tree_sha256": package_tree_sha256,
        "trusted_provenance_digest": trusted_provenance_digest,
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
    if local_1612 is not None:
        body.update({
            "gitnexus_version": "1.6.12", "metadata_schema": LOCAL_1612_SCHEMA,
            "metadata_fields": sorted(META_1612_REQUIRED_FIELDS),
            "local_identity": {
                "runner": hashlib.sha256(local_1612.runner_json.encode("ascii")).hexdigest(),
                "dependency_closure": local_1612.dependency_sha256,
                "coverage_paths": list(local_1612.coverage_paths),
                "accepted_probes": local_1612.probe_sha256,
                "schema_fingerprint": "60fc01e4e4ed", "automatic_refresh": False,
                "parse_cache": False, "write_mode": "full-rebuild",
            },
        })
    return body


def _qualified_argv(
    executable: pathlib.Path,
    runtime_executable: pathlib.Path | None,
    *arguments: str,
) -> list[str]:
    prefix = [str(runtime_executable), str(executable)] if runtime_executable else [str(executable)]
    return [*prefix, *arguments]


def _qualify_executable_until(
    configured_path: str | os.PathLike[str] | None,
    *,
    deadline: float,
    allow_symlink: bool = False,
    runtime_path: str | os.PathLike[str] | None = None,
    allow_runtime_symlink: bool = False,
    runner: Runner | None = None,
    environment: Mapping[str, str] | None = None,
    package_root: str | os.PathLike[str] | None = None,
    accepted_executable_sha256: str | None = None,
    accepted_package_sha256: str | None = None,
    accepted_runtime_sha256: str | None = None,
    local_1612: Local1612Profile | None = None,
    accepted_probe_outputs: tuple[str, str] | None = None,
) -> ExecutableQualification:
    """Bind qualification under a caller-owned, already bounded deadline."""
    _check_deadline(deadline)
    run_process = runner or _run_adapter_subprocess
    executable, symlink_policy = discover_executable(configured_path, allow_symlink=allow_symlink)
    before_digest, before_identity = _executable_identity(executable, deadline=deadline)
    runtime = _script_runtime(
        executable,
        runtime_path,
        allow_symlink=allow_runtime_symlink,
        deadline=deadline,
    )
    runtime_executable = runtime[0] if runtime else None
    runtime_digest = runtime[1] if runtime else None
    runtime_identity = runtime[2] if runtime else None
    runtime_symlink_policy = runtime[3] if runtime else None
    runtime_launcher = runtime[4] if runtime else "direct"
    expected_entry = _require_expected_digest(
        accepted_executable_sha256, "GitNexus executable"
    )
    if before_digest != expected_entry:
        raise GitNexusAdapterError("GitNexus executable does not match caller-owned provenance")
    if runtime_executable is None:
        if accepted_runtime_sha256 not in (None, ""):
            raise GitNexusAdapterError("caller-owned runtime sha256 is invalid for a direct executable")
        expected_runtime = None
    else:
        expected_runtime = _require_expected_digest(
            accepted_runtime_sha256, "GitNexus runtime executable"
        )
        if runtime_digest != expected_runtime:
            raise GitNexusAdapterError("GitNexus runtime does not match caller-owned provenance")
    qualified_package_root = _discover_package_root(package_root, executable)
    before_package_digest, before_package_identity = _package_tree_identity(
        qualified_package_root, deadline=deadline
    )
    expected_package = _require_expected_digest(
        accepted_package_sha256, "GitNexus package tree"
    )
    if before_package_digest != expected_package:
        raise GitNexusAdapterError("GitNexus package tree does not match caller-owned provenance")
    if local_1612 is not None:
        _verify_local_1612(local_1612, executable, before_digest, runtime_executable, qualified_package_root, deadline=deadline)
    elif accepted_probe_outputs is not None:
        raise GitNexusAdapterError("accepted probe receipts require the local 1.6.12 profile")
    trusted_provenance_digest = _canonical_digest(
        {
            "schema": "gitnexus-trusted-provenance/v1",
            "executable_sha256": expected_entry,
            "runtime_executable_sha256": expected_runtime,
            "package_tree_sha256": expected_package,
        }
    )
    common: dict[str, Any] = {
        "cwd": executable.parent,
        "env": _safe_environment(environment),
    }
    common["timeout"] = _remaining_timeout(deadline)
    version_output = accepted_probe_outputs[0] if accepted_probe_outputs is not None else _completed_output(
        run_process(_qualified_argv(executable, runtime_executable, "--version"), **common),
        "gitnexus --version",
    )
    version = "1.6.12" if local_1612 is not None else QUALIFIED_GITNEXUS_VERSION
    matches = re.findall(r"(?<![0-9])v?(1\.6\.12)(?![0-9.])", version_output) if local_1612 is not None else VERSION_RE.findall(version_output)
    if matches != [version]:
        raise GitNexusAdapterError(f"GitNexus exact version {version} is required")
    common["timeout"] = _remaining_timeout(deadline)
    help_output = accepted_probe_outputs[1] if accepted_probe_outputs is not None else _completed_output(
        run_process(_qualified_argv(executable, runtime_executable, "analyze", "--help"), **common),
        "gitnexus analyze --help",
    )
    flags = tuple(sorted(set(FLAG_RE.findall(help_output))))
    missing = sorted(REQUIRED_ANALYZE_FLAGS - set(flags))
    if local_1612 is not None and "--no-parse-cache" not in flags:
        missing.append("--no-parse-cache")
    if missing:
        raise GitNexusAdapterError(f"GitNexus required analyze flags are missing: {','.join(missing)}")
    after_digest, after_identity = _executable_identity(executable, deadline=deadline)
    if (before_digest, before_identity) != (after_digest, after_identity):
        raise GitNexusAdapterError("GitNexus executable changed during qualification")
    if runtime_executable is not None:
        after_runtime_digest, after_runtime_identity = _executable_identity(runtime_executable, deadline=deadline)
        if (runtime_digest, runtime_identity) != (after_runtime_digest, after_runtime_identity):
            raise GitNexusAdapterError("GitNexus runtime executable changed during qualification")
    after_package_digest, after_package_identity = _package_tree_identity(
        qualified_package_root, deadline=deadline
    )
    if (before_package_digest, before_package_identity) != (
        after_package_digest,
        after_package_identity,
    ):
        raise GitNexusAdapterError("GitNexus package tree changed during qualification")
    if local_1612 is not None:
        _verify_local_1612(local_1612, executable, after_digest, runtime_executable, qualified_package_root, deadline=deadline)
    body = _qualification_body(
        executable_sha256=after_digest,
        analyze_flags=flags,
        symlink_policy=symlink_policy,
        runtime_executable_sha256=runtime_digest,
        runtime_symlink_policy=runtime_symlink_policy,
        runtime_launcher=runtime_launcher,
        package_tree_sha256=after_package_digest,
        trusted_provenance_digest=trusted_provenance_digest,
        local_1612=local_1612,
    )
    return ExecutableQualification(
        executable=executable,
        executable_sha256=after_digest,
        version=version,
        analyze_flags=flags,
        symlink_policy=symlink_policy,
        fingerprint=_canonical_digest(body),
        stat_identity=after_identity,
        runtime_executable=runtime_executable,
        runtime_executable_sha256=runtime_digest,
        runtime_stat_identity=runtime_identity,
        runtime_symlink_policy=runtime_symlink_policy,
        runtime_launcher=runtime_launcher,
        package_root=qualified_package_root,
        package_tree_sha256=after_package_digest,
        package_stat_identity=after_package_identity,
        trusted_provenance_digest=trusted_provenance_digest,
        local_1612=local_1612,
    )


def qualify_executable(
    configured_path: str | os.PathLike[str] | None,
    *,
    allow_symlink: bool = False,
    runtime_path: str | os.PathLike[str] | None = None,
    allow_runtime_symlink: bool = False,
    runner: Runner | None = None,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: int = 10,
    package_root: str | os.PathLike[str] | None = None,
    accepted_executable_sha256: str | None = None,
    accepted_package_sha256: str | None = None,
    accepted_runtime_sha256: str | None = None,
) -> ExecutableQualification:
    """Bind exact executable bytes under the standalone qualification limit."""
    deadline = _timeout_deadline(
        timeout_seconds, label="qualification", maximum=300
    )
    return _qualify_executable_until(
        configured_path,
        deadline=deadline,
        allow_symlink=allow_symlink,
        runtime_path=runtime_path,
        allow_runtime_symlink=allow_runtime_symlink,
        runner=runner,
        environment=environment,
        package_root=package_root,
        accepted_executable_sha256=accepted_executable_sha256,
        accepted_package_sha256=accepted_package_sha256,
        accepted_runtime_sha256=accepted_runtime_sha256,
    )


def _runner_1612_valid(value: Any) -> bool:
    def record(item: Any, keys: set[str]) -> bool:
        return isinstance(item, dict) and set(item) == keys

    def text(item: Any) -> bool:
        if not isinstance(item, str) or not 0 < len(item) <= 4096 or "\0" in item:
            return False
        try:
            item.encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True

    def absolute(item: Any) -> bool:
        return text(item) and item.startswith("/") and ".." not in pathlib.PurePosixPath(item).parts

    def digest(item: Any) -> bool:
        return isinstance(item, str) and item.startswith("sha256:") and bool(SHA256_RE.fullmatch(item[7:]))

    if not record(value, {"schemaVersion", "runtime", "cliVersion", "invokedArtifact", "build", "dependencyRuntime"}) or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 4 or value["cliVersion"] != "1.6.12":
        return False
    runtime, entry, build, dependency = (value[k] for k in ("runtime", "invokedArtifact", "build", "dependencyRuntime"))
    return (
        record(runtime, {"executablePath", "version", "platform", "architecture", "modulesAbi", "libc"})
        and absolute(runtime["executablePath"]) and all(text(v) for v in runtime.values())
        and record(entry, {"path", "digest"}) and absolute(entry["path"]) and digest(entry["digest"])
        and record(build, {"kind", "rootPath", "canonicalization", "digest"}) and build["kind"] == "distribution"
        and absolute(build["rootPath"]) and build["canonicalization"] == "gitnexus-analyzer-build-v2" and digest(build["digest"])
        and record(dependency, {"manifestPath", "lockfilePath", "canonicalization", "packageCount", "artifactCount", "digest"})
        and absolute(dependency["manifestPath"]) and (dependency["lockfilePath"] is None or absolute(dependency["lockfilePath"]))
        and dependency["canonicalization"] == "gitnexus-analyzer-dependency-runtime-v4" and digest(dependency["digest"])
        and all(type(dependency[k]) is int and 1 <= dependency[k] <= 2**53 - 1 for k in ("packageCount", "artifactCount"))
    )


def _coverage_path_valid(path: Any) -> bool:
    if not isinstance(path, str):
        return False
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return (
        0 < len(path) <= 4096
        and all(p not in {"", ".", ".."} for p in path.split("/"))
        and "\\" not in path and "\0" not in path
        and path.split("/", 1)[0] not in {".git", ".gitnexus"}
    )


def _verify_local_1612(profile: Local1612Profile, executable: pathlib.Path, entry_digest: str,
                       runtime: pathlib.Path | None, package: pathlib.Path, *, deadline: float | None = None) -> None:
    if not isinstance(profile, Local1612Profile) or not all(isinstance(v, str) for v in (profile.runner_json, profile.dependency_sha256, profile.probe_sha256)):
        raise GitNexusAdapterError("accepted local 1.6.12 profile is invalid")
    try:
        runner = json.loads(profile.runner_json)
        valid = (
            _runner_1612_valid(runner) and _local_json(runner) == profile.runner_json
            and runner["invokedArtifact"] == {"path": str(executable), "digest": "sha256:" + entry_digest}
            and runtime is not None and runner["runtime"]["executablePath"] == str(runtime)
            and runner["build"]["rootPath"] == str(package / "dist")
            and runner["dependencyRuntime"]["manifestPath"] == str(package / "package.json")
            and isinstance(profile.coverage_paths, tuple) and 0 < len(profile.coverage_paths) <= MAX_SNAPSHOT_ENTRIES
            and all(_coverage_path_valid(p) for p in profile.coverage_paths)
            and tuple(sorted(set(profile.coverage_paths))) == profile.coverage_paths
            and bool(SHA256_RE.fullmatch(profile.probe_sha256))
        )
    except (ValueError, TypeError, KeyError, UnicodeError):
        valid = False
    if not valid:
        raise GitNexusAdapterError("accepted local 1.6.12 identity is invalid or unbound")
    digest, count, lockfile = local_1612_dependency_identity(package, deadline=deadline)
    if digest != profile.dependency_sha256 or count != runner["dependencyRuntime"]["packageCount"] or lockfile != runner["dependencyRuntime"]["lockfilePath"]:
        raise GitNexusAdapterError("accepted local 1.6.12 dependency closure drifted")


def qualify_local_1612(
    configured_path: str | os.PathLike[str], *, runtime_path: str | os.PathLike[str],
    package_root: str | os.PathLike[str], accepted_executable_sha256: str,
    accepted_runtime_sha256: str, accepted_package_sha256: str,
    accepted_runner_identity: Mapping[str, Any], accepted_dependency_sha256: str,
    expected_coverage_paths: Sequence[str], version_output: str, analyze_help_output: str,
    accepted_probe_sha256: str, timeout_seconds: int = 180,
) -> ExecutableQualification:
    """Reuse caller-accepted version/help receipts; execute no tool or probe.

    The caller independently accepts the local installation, runner receipt and
    explicit coverage scope. Receipt text alone never establishes that trust.
    External runtime dependencies and automatic refresh remain unsupported.
    """
    deadline = _timeout_deadline(timeout_seconds, label="qualification", maximum=300)
    if not _runner_1612_valid(accepted_runner_identity) or not all(isinstance(v, str) for v in (version_output, analyze_help_output)):
        raise GitNexusAdapterError("accepted local 1.6.12 receipts are invalid")
    if not isinstance(expected_coverage_paths, (tuple, list)) or not expected_coverage_paths or not all(_coverage_path_valid(p) for p in expected_coverage_paths):
        raise GitNexusAdapterError("accepted coverage paths are invalid")
    probes = (version_output, analyze_help_output)
    if sum(len(v) for v in probes) > 1024 * 1024 or hashlib.sha256(_local_json(probes).encode("ascii")).hexdigest() != _require_expected_digest(accepted_probe_sha256, "probe receipt"):
        raise GitNexusAdapterError("accepted probe receipt digest mismatch")
    profile = Local1612Profile(
        _local_json(dict(accepted_runner_identity)),
        _require_expected_digest(accepted_dependency_sha256, "dependency closure"),
        tuple(sorted(expected_coverage_paths)), accepted_probe_sha256,
    )
    return _qualify_executable_until(
        configured_path, deadline=deadline, runtime_path=runtime_path, package_root=package_root,
        accepted_executable_sha256=accepted_executable_sha256, accepted_runtime_sha256=accepted_runtime_sha256,
        accepted_package_sha256=accepted_package_sha256, local_1612=profile, accepted_probe_outputs=probes,
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
    expected_version = "1.6.12" if qualification.local_1612 is not None else QUALIFIED_GITNEXUS_VERSION
    if qualification.version != expected_version or not REQUIRED_ANALYZE_FLAGS.issubset(qualification.analyze_flags):
        raise GitNexusAdapterError("GitNexus qualification capability drift requires requalification")
    if qualification.local_1612 is not None and "--no-parse-cache" not in qualification.analyze_flags:
        raise GitNexusAdapterError("local 1.6.12 requires full rebuild without parser cache")
    with qualification.executable.open("rb") as stream:
        shebang = stream.readline(256).rstrip(b"\r\n")
    if shebang.startswith(b"#!/usr/bin/env"):
        expected_launcher = "bound-node"
    elif shebang.startswith(b"#!"):
        expected_launcher = "bound-shebang"
    else:
        expected_launcher = "direct"
    if qualification.runtime_launcher != expected_launcher or (
        (expected_launcher == "direct") != (qualification.runtime_executable is None)
    ):
        raise GitNexusAdapterError(
            "GitNexus qualification runtime binding is inconsistent"
        )
    if qualification.runtime_executable is not None:
        runtime_digest, runtime_identity = _executable_identity(
            qualification.runtime_executable, deadline=deadline
        )
        if (
            runtime_digest != qualification.runtime_executable_sha256
            or runtime_identity != qualification.runtime_stat_identity
        ):
            raise GitNexusAdapterError("qualified GitNexus runtime executable drifted")
    if (
        qualification.package_root is None
        or qualification.package_tree_sha256 is None
        or qualification.package_stat_identity is None
        or qualification.trusted_provenance_digest is None
    ):
        raise GitNexusAdapterError("GitNexus qualification lacks trusted package provenance")
    package_digest, package_identity = _package_tree_identity(
        qualification.package_root, deadline=deadline
    )
    if (
        package_digest != qualification.package_tree_sha256
        or package_identity != qualification.package_stat_identity
    ):
        raise GitNexusAdapterError("qualified GitNexus package tree drifted")
    if qualification.local_1612 is not None:
        _verify_local_1612(qualification.local_1612, qualification.executable, digest, qualification.runtime_executable, qualification.package_root, deadline=deadline)
    _check_deadline(deadline)
    expected_fingerprint = _canonical_digest(_qualification_body(
        executable_sha256=qualification.executable_sha256,
        analyze_flags=qualification.analyze_flags,
        symlink_policy=qualification.symlink_policy,
        runtime_executable_sha256=qualification.runtime_executable_sha256,
        runtime_symlink_policy=qualification.runtime_symlink_policy,
        runtime_launcher=qualification.runtime_launcher,
        package_tree_sha256=qualification.package_tree_sha256,
        trusted_provenance_digest=qualification.trusted_provenance_digest,
        local_1612=qualification.local_1612,
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


def _git_executable(
    configured_path: str | os.PathLike[str] | None = None,
) -> str:
    try:
        executable = git_source._resolved_git_executable(configured_path)
        with executable.open("rb") as stream:
            if stream.read(2) == b"#!":
                raise GitNexusAdapterError(
                    "Git script wrappers are unsupported; select a native Git executable"
                )
        return str(executable)
    except OSError as exc:
        raise GitNexusAdapterError("git executable cannot be bound safely") from exc


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
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _remaining_timeout(deadline: float | None, *, default: float = 30.0) -> float:
    if deadline is None:
        return default
    remaining = _validated_deadline(deadline) - time.monotonic()
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
    git_executable: str | os.PathLike[str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return _bounded_process(
        [
            _git_executable(git_executable),
            "--no-replace-objects",
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
    git_executable: str | os.PathLike[str] | None = None,
) -> bytes:
    result = _run_git_result(
        root, args, deadline=deadline, git_executable=git_executable
    )
    if result.returncode != 0 and not allow_failure:
        raise GitNexusAdapterError(f"git {' '.join(args[:2])} failed with exit status {result.returncode}")
    return result.stdout


def _strict_root(
    path: str | os.PathLike[str],
    *,
    deadline: float | None = None,
    git_executable: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
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
    try:
        expected_marker = git_source.validated_git_marker(resolved)
    except OSError as exc:
        raise GitNexusAdapterError("repository target requires a local .git marker") from exc
    reported = pathlib.Path(
        _run_git(
            resolved,
            ["rev-parse", "--show-toplevel"],
            deadline=deadline,
            git_executable=git_executable,
        ).decode("utf-8", "strict").strip()
    ).resolve(strict=True)
    if reported != resolved:
        raise GitNexusAdapterError("target must be the exact Git repository root")
    reported_git_dir = pathlib.Path(
        _run_git(
            resolved,
            ["rev-parse", "--absolute-git-dir"],
            deadline=deadline,
            git_executable=git_executable,
        )
        .decode("utf-8", "strict")
        .strip()
    ).resolve(strict=True)
    if reported_git_dir != expected_marker.git_dir:
        raise GitNexusAdapterError("target Git administrative directory does not match its marker")
    try:
        if git_source.validated_git_marker(resolved) != expected_marker:
            raise GitNexusAdapterError("target Git marker changed during verification")
    except OSError as exc:
        raise GitNexusAdapterError("target Git marker changed during verification") from exc
    return resolved


def resolve_checkout_root(
    path: str | os.PathLike[str],
    *,
    deadline: float | None = None,
    git_executable: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Resolve a directory to its exact, independently verified Git checkout root."""
    lexical = pathlib.Path(path)
    if not lexical.is_absolute():
        raise GitNexusAdapterError("checkout path must be absolute")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise GitNexusAdapterError("checkout path cannot be resolved") from exc
    if not resolved.is_dir():
        raise GitNexusAdapterError("checkout path must be a directory")
    try:
        reported = pathlib.Path(
            _run_git(
                resolved,
                ["rev-parse", "--show-toplevel"],
                deadline=deadline,
                git_executable=git_executable,
            ).decode("utf-8", "strict").strip()
        )
        if not reported.is_absolute():
            raise GitNexusAdapterError("Git reported a non-absolute checkout root")
        return _strict_root(
            reported, deadline=deadline, git_executable=git_executable
        )
    except (OSError, UnicodeError) as exc:
        raise GitNexusAdapterError("checkout root cannot be verified") from exc


def collect_repository_state(
    root: str | os.PathLike[str],
    *,
    canonical_repository_id: str,
    expected_remote: str | None = None,
    principal_scope: Mapping[str, str] | None = None,
    path_scope: Sequence[str] = (".",),
    deadline: float | None = None,
    git_executable: str | os.PathLike[str] | None = None,
) -> RepositoryState:
    """Build caller-owned V2b identity from current Git evidence."""
    root_path = _strict_root(
        root, deadline=deadline, git_executable=git_executable
    )
    try:
        marker_before = git_source.validated_git_marker(root_path)
    except OSError as exc:
        raise GitNexusAdapterError("repository Git marker cannot be verified") from exc

    def observe() -> tuple[str, str | None, str, str]:
        observed_head = _run_git(
            root_path,
            ["rev-parse", "--verify", "HEAD^{commit}"],
            deadline=deadline,
            git_executable=git_executable,
        ).decode().strip()
        if not COMMIT_RE.fullmatch(observed_head):
            raise GitNexusAdapterError("repository HEAD is not an exact commit")
        observed_branch = _run_git(
            root_path,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
            allow_failure=True,
            deadline=deadline,
            git_executable=git_executable,
        ).decode("utf-8", "strict").strip() or None
        observed_remote = normalize_remote(
            _run_git(
                root_path,
                ["remote", "get-url", "origin"],
                deadline=deadline,
                git_executable=git_executable,
            ).decode("utf-8", "strict")
        )
        observed_common = _run_git(
            root_path,
            ["rev-parse", "--git-common-dir"],
            deadline=deadline,
            git_executable=git_executable,
        ).decode("utf-8", "strict").strip()
        return observed_head, observed_branch, observed_remote, observed_common

    first = observe()
    second = observe()
    try:
        marker_after = git_source.validated_git_marker(root_path)
    except OSError as exc:
        raise GitNexusAdapterError("repository Git marker cannot be reverified") from exc
    if first != second or marker_before != marker_after:
        raise GitNexusAdapterError("repository identity changed during collection")
    head, branch, actual_remote, git_common = first
    if expected_remote is not None and actual_remote != normalize_remote(expected_remote):
        raise GitNexusAdapterError("repository origin does not match caller expectation")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", canonical_repository_id):
        raise GitNexusAdapterError("caller-owned canonical repository id is invalid")
    principals = dict(principal_scope or {
        "tenant": "not-applicable", "workspace": "not-applicable", "user": "not-applicable"
    })
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


def _tracked_paths(
    root: pathlib.Path,
    *,
    deadline: float | None = None,
    git_executable: str | os.PathLike[str] | None = None,
) -> list[str]:
    raw = _run_git(
        root,
        ["ls-files", "-z", "--cached"],
        deadline=deadline,
        git_executable=git_executable,
    )
    return sorted({item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item})


def _reject_repository_git_execution_config(
    root: pathlib.Path,
    *,
    deadline: float | None = None,
    git_executable: str | os.PathLike[str] | None = None,
) -> None:
    """Reject local Git configuration that can execute content filters."""

    def inspected_keys(scope: str) -> list[str]:
        result = _run_git_result(
            root,
            ["config", scope, "--no-includes", "--name-only", "--null", "--list"],
            deadline=deadline,
            git_executable=git_executable,
        )
        if result.returncode != 0:
            raise GitNexusAdapterError(
                "repository-local Git config cannot be inspected safely"
            )
        try:
            return [
                item.decode("utf-8", "strict").lower()
                for item in result.stdout.split(b"\0")
                if item
            ]
        except UnicodeError as exc:
            raise GitNexusAdapterError(
                "repository-local Git config keys are not UTF-8"
            ) from exc

    keys = inspected_keys("--local")
    extension = _run_git_result(
        root,
        ["config", "--local", "--no-includes", "--type=bool", "--get", "extensions.worktreeConfig"],
        deadline=deadline,
        git_executable=git_executable,
    )
    if extension.returncode not in {0, 1}:
        raise GitNexusAdapterError(
            "repository-local Git worktree config capability cannot be inspected safely"
        )
    try:
        worktree_config_enabled = (
            extension.returncode == 0
            and extension.stdout.decode("ascii", "strict").strip() == "true"
        )
    except UnicodeError as exc:
        raise GitNexusAdapterError(
            "repository-local Git worktree config capability is invalid"
        ) from exc
    if extension.returncode == 0 and not worktree_config_enabled:
        if extension.stdout.decode("ascii", "strict").strip() != "false":
            raise GitNexusAdapterError(
                "repository-local Git worktree config capability is invalid"
            )
    if worktree_config_enabled:
        keys.extend(inspected_keys("--worktree"))
    unsafe = sorted(
        key
        for key in keys
        if key.startswith("filter.")
        or key == "include.path"
        or (key.startswith("includeif.") and key.endswith(".path"))
        or key == "core.attributesfile"
    )
    if unsafe:
        raise GitNexusAdapterError(
            "repository-local Git executable filter/include configuration is unsupported"
        )


def _tracked_path_aliases_derived_index(
    root: pathlib.Path,
    relative: str,
    *,
    deadline: float | None = None,
) -> bool:
    """Detect tracked ancestors that alias the fixed derived-index root."""
    pure = pathlib.PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or ".." in pure.parts:
        raise GitNexusAdapterError("git returned an unsafe tracked path")
    derived = root / ".gitnexus"
    derived_identity = unicodedata.normalize("NFC", ".gitnexus").casefold()
    candidate = root
    for part in pure.parts:
        _check_deadline(deadline)
        candidate /= part
        if candidate == derived:
            return True
        candidate_identity = unicodedata.normalize(
            "NFC", candidate.relative_to(root).as_posix()
        ).casefold()
        if candidate_identity == derived_identity:
            return True
        try:
            if candidate.samefile(derived):
                return True
        except (FileNotFoundError, NotADirectoryError):
            continue
        except OSError as exc:
            raise GitNexusAdapterError(
                "tracked derived-index alias cannot be inspected"
            ) from exc
    return False


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


def _regular_file_entry_at(
    directory_fd: int,
    name: str,
    relative: str,
    expected: os.stat_result,
    *,
    deadline: float | None = None,
) -> dict[str, Any]:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise GitNexusAdapterError("POSIX no-follow nonblocking file operations are unavailable")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
        dir_fd=directory_fd,
    )
    try:
        opened = os.fstat(descriptor)
        expected_identity = (expected.st_dev, expected.st_ino, expected.st_mode)
        opened_identity = (opened.st_dev, opened.st_ino, opened.st_mode)
        if opened_identity != expected_identity or not stat.S_ISREG(opened.st_mode):
            raise GitNexusAdapterError("snapshot file changed while it was opened")
        digest = hashlib.sha256()
        total = 0
        while True:
            _check_deadline(deadline)
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SNAPSHOT_FILE_BYTES:
                raise GitNexusAdapterError("snapshot file exceeds the safety bound")
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_mode) != opened_identity
            or after.st_size != opened.st_size
            or after.st_mtime_ns != opened.st_mtime_ns
        ):
            raise GitNexusAdapterError("snapshot file changed while it was read")
        return {
            "path": relative,
            "kind": "regular",
            "device": _snapshot_integer(opened.st_dev),
            "inode": _snapshot_integer(opened.st_ino),
            "mode": stat.S_IMODE(opened.st_mode),
            "size": _snapshot_integer(opened.st_size),
            "mtime_ns": _snapshot_integer(opened.st_mtime_ns, signed=True),
            "sha256": digest.hexdigest(),
        }
    finally:
        os.close(descriptor)


def _snapshot_integer(value: int, *, signed: bool = False) -> str:
    """Encode filesystem integers without relying on JSON safe-number ranges."""

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or (value < 0 and not signed)
    ):
        raise GitNexusAdapterError("snapshot filesystem identity is invalid")
    return str(value)


def _filesystem_tree_digests(
    root: pathlib.Path,
    *,
    excluded_top_level: frozenset[str] = frozenset(),
    deadline: float | None = None,
) -> tuple[str, str]:
    """Hash one complete tree as local state and portable relevant content."""

    root_fd = _open_directory_nofollow(root)
    records: list[dict[str, Any]] = []
    content_records: list[dict[str, Any]] = []
    count = 0

    def walk(directory_fd: int, prefix: str, depth: int) -> None:
        nonlocal count
        _check_deadline(deadline)
        if depth > MAX_SNAPSHOT_DEPTH:
            raise GitNexusAdapterError("snapshot directory depth exceeds the safety bound")
        try:
            with os.scandir(directory_fd) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            raise GitNexusAdapterError("snapshot directory cannot be enumerated") from exc
        for entry in entries:
            _check_deadline(deadline)
            if not prefix and entry.name in excluded_top_level:
                continue
            relative = f"{prefix}/{entry.name}" if prefix else entry.name
            count += 1
            if count > MAX_SNAPSHOT_ENTRIES:
                raise GitNexusAdapterError("snapshot entry count exceeds the safety bound")
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise GitNexusAdapterError("snapshot entry cannot be inspected") from exc
            if stat.S_ISDIR(info.st_mode):
                child_fd = os.open(
                    entry.name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
                try:
                    opened = os.fstat(child_fd)
                    if (
                        (opened.st_dev, opened.st_ino, opened.st_mode)
                        != (info.st_dev, info.st_ino, info.st_mode)
                    ):
                        raise GitNexusAdapterError(
                            "snapshot directory changed while it was opened"
                        )
                    record = {
                        "path": relative,
                        "kind": "directory",
                        "device": _snapshot_integer(opened.st_dev),
                        "inode": _snapshot_integer(opened.st_ino),
                        "mode": stat.S_IMODE(opened.st_mode),
                    }
                    records.append(record)
                    content_records.append(
                        {key: record[key] for key in ("path", "kind", "mode")}
                    )
                    walk(child_fd, relative, depth + 1)
                finally:
                    os.close(child_fd)
            elif stat.S_ISREG(info.st_mode):
                record = _regular_file_entry_at(
                    directory_fd,
                    entry.name,
                    relative,
                    info,
                    deadline=deadline,
                )
                records.append(record)
                content_records.append(
                    {
                        key: record[key]
                        for key in ("path", "kind", "mode", "size", "sha256")
                    }
                )
            elif stat.S_ISLNK(info.st_mode):
                try:
                    target = os.readlink(entry.name, dir_fd=directory_fd)
                    after = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise GitNexusAdapterError("snapshot symlink cannot be inspected") from exc
                if (after.st_dev, after.st_ino, after.st_mode) != (
                    info.st_dev,
                    info.st_ino,
                    info.st_mode,
                ):
                    raise GitNexusAdapterError("snapshot symlink changed during inspection")
                record = {
                    "path": relative,
                    "kind": "symlink",
                    "device": _snapshot_integer(info.st_dev),
                    "inode": _snapshot_integer(info.st_ino),
                    "mode": stat.S_IMODE(info.st_mode),
                    "target_sha256": hashlib.sha256(
                        target.encode("utf-8", "surrogateescape")
                    ).hexdigest(),
                }
                records.append(record)
                content_records.append(
                    {
                        key: record[key]
                        for key in ("path", "kind", "mode", "target_sha256")
                    }
                )
            else:
                record = {
                    "path": relative,
                    "kind": "special",
                    "device": _snapshot_integer(info.st_dev),
                    "inode": _snapshot_integer(info.st_ino),
                    "mode": stat.S_IMODE(info.st_mode),
                    "size": _snapshot_integer(info.st_size),
                }
                records.append(record)
                content_records.append(
                    {
                        key: record[key]
                        for key in ("path", "kind", "mode", "size")
                    }
                )

    try:
        walk(root_fd, "", 0)
        return _canonical_digest(records), _canonical_digest(content_records)
    finally:
        os.close(root_fd)


def _filesystem_tree_digest(
    root: pathlib.Path,
    *,
    excluded_top_level: frozenset[str] = frozenset(),
    deadline: float | None = None,
) -> str:
    """Compatibility wrapper for callers that need local-state identity only."""
    return _filesystem_tree_digests(
        root,
        excluded_top_level=excluded_top_level,
        deadline=deadline,
    )[0]


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
    git_executable: str | os.PathLike[str] | None = None,
) -> TrackedSnapshot:
    root_path = _strict_root(
        root, deadline=deadline, git_executable=git_executable
    )
    try:
        marker_before = git_source.validated_git_marker(root_path)
    except OSError as exc:
        raise GitNexusAdapterError("repository Git marker cannot be verified for snapshot") from exc
    head = _run_git(
        root_path,
        ["rev-parse", "--verify", "HEAD^{commit}"],
        deadline=deadline,
        git_executable=git_executable,
    ).decode().strip()
    branch = _run_git(
        root_path,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        allow_failure=True,
        deadline=deadline,
        git_executable=git_executable,
    ).decode("utf-8", "strict").strip() or None
    _reject_repository_git_execution_config(
        root_path,
        deadline=deadline,
        git_executable=git_executable,
    )
    def git(args: Sequence[str], *, allow_failure: bool = False) -> bytes:
        return _run_git(
            root_path,
            args,
            allow_failure=allow_failure,
            deadline=deadline,
            git_executable=git_executable,
        )

    complete_status = git(["status", "--porcelain=v1", "-z", "--untracked-files=all"])
    tracked_status = git(["status", "--porcelain=v1", "-z", "--untracked-files=no"])
    staged_diff = git(["diff", "--no-ext-diff", "--no-textconv", "--cached", "--binary", "HEAD", "--"])
    worktree_diff = git(["diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"])
    index_state = git(["ls-files", "-z", "--stage"])
    entries = [
        _path_entry(root_path, path, deadline=deadline)
        for path in _tracked_paths(
            root_path, deadline=deadline, git_executable=git_executable
        )
    ]
    protected = [entry for entry in entries if _is_protected(entry["path"])]
    tracked_derived_present = any(
        _tracked_path_aliases_derived_index(
            root_path, entry["path"], deadline=deadline
        )
        for entry in entries
    )
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
    worktree_state_digest, relevant_content_digest = _filesystem_tree_digests(
        root_path,
        excluded_top_level=frozenset({".git", ".gitnexus"}),
        deadline=deadline,
    )
    head_after = _run_git(
        root_path,
        ["rev-parse", "--verify", "HEAD^{commit}"],
        deadline=deadline,
        git_executable=git_executable,
    ).decode().strip()
    branch_after = _run_git(
        root_path,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        allow_failure=True,
        deadline=deadline,
        git_executable=git_executable,
    ).decode("utf-8", "strict").strip() or None
    try:
        marker_after = git_source.validated_git_marker(root_path)
    except OSError as exc:
        raise GitNexusAdapterError("repository Git marker cannot be reverified for snapshot") from exc
    if head_after != head or branch_after != branch or marker_after != marker_before:
        raise GitNexusAdapterError("repository identity changed during snapshot")
    _check_deadline(deadline)
    return TrackedSnapshot(
        head=head,
        branch=branch,
        tracked_dirty=bool(tracked_status),
        tracked_derived_present=tracked_derived_present,
        outside_derived_dirty=bool(outside_derived),
        tracked_state_digest=_canonical_digest(tracked_body),
        protected_state_digest=_canonical_digest(protected),
        outside_derived_status_digest=_canonical_digest(outside_derived),
        complete_status_digest=hashlib.sha256(complete_status).hexdigest(),
        worktree_state_digest=worktree_state_digest,
        untracked_dirty=any(code == "??" for code, _path in _status_paths(complete_status)),
        relevant_content_digest=relevant_content_digest,
    )


def _checkout_kind(root: pathlib.Path) -> str:
    try:
        marker = (root / ".git").lstat()
    except OSError as exc:
        raise GitNexusAdapterError("repository Git marker cannot classify checkout") from exc
    if stat.S_ISDIR(marker.st_mode):
        return "primary"
    if stat.S_ISREG(marker.st_mode) and not stat.S_ISLNK(marker.st_mode):
        return "linked-worktree"
    raise GitNexusAdapterError("repository Git marker cannot classify checkout")


def _dirty_classification(snapshot: TrackedSnapshot) -> str:
    if snapshot.tracked_dirty and snapshot.untracked_dirty:
        return "dirty-mixed"
    if snapshot.tracked_dirty:
        return "dirty-tracked"
    if snapshot.untracked_dirty or snapshot.outside_derived_dirty:
        return "dirty-untracked"
    return "clean"


def _lifecycle_context(repository: RepositoryState, checkout_kind: str) -> str:
    if repository.branch is None:
        return "detached"
    if checkout_kind == "linked-worktree":
        return "linked-worktree"
    if repository.branch == "main":
        return "primary-main"
    return "primary-branch"


def _index_alias(
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    lifecycle: str,
) -> str:
    return "-".join(
        (
            "codex-gn1",
            lifecycle,
            repository.identity["worktree_id_digest"][:12],
            repository.head[:12],
            snapshot.relevant_content_digest[:12],
        )
    )


def _index_analyze_arguments(qualification: ExecutableQualification, alias: str, root: pathlib.Path) -> list[str]:
    return ["analyze", "--index-only", *(["--no-parse-cache"] if qualification.local_1612 else []), "--name", alias, str(root)]


def build_index_identity(
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    metadata_digest: str,
    indexed_at: str,
    observed_at: str,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Build one versioned, non-authoritative exact/advisory index identity."""
    _validated_repository_state_identity(repository)
    verify_qualification(qualification, deadline=deadline)
    if snapshot.head != repository.head:
        raise GitNexusAdapterError("index identity snapshot HEAD conflicts with repository")
    if snapshot.branch != repository.branch:
        raise GitNexusAdapterError(
            "index identity snapshot branch conflicts with repository"
        )
    for label, digest in (
        ("metadata", metadata_digest),
        ("tracked state", snapshot.tracked_state_digest),
        ("complete status", snapshot.complete_status_digest),
        ("worktree state", snapshot.worktree_state_digest),
        ("relevant content", snapshot.relevant_content_digest),
    ):
        if not SHA256_RE.fullmatch(digest):
            raise GitNexusAdapterError(f"index identity {label} digest is invalid")
    try:
        indexed_time = dt.datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
        observed_time = dt.datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if indexed_time.tzinfo is None or observed_time.tzinfo is None:
            raise ValueError
    except (AttributeError, TypeError, ValueError) as exc:
        raise GitNexusAdapterError("index identity freshness time is invalid") from exc
    checkout_kind = _checkout_kind(repository.root)
    lifecycle = _lifecycle_context(repository, checkout_kind)
    content_state = _dirty_classification(snapshot)
    exact_eligible = (
        content_state == "clean"
        and repository.branch is not None
        and not snapshot.tracked_derived_present
    )
    alias = _index_alias(repository, snapshot, lifecycle)
    config_digest = _canonical_digest(
        {
            "argv": _index_analyze_arguments(qualification, alias, repository.root),
            "required_flags": sorted(REQUIRED_ANALYZE_FLAGS),
            "metadata_schema": LOCAL_1612_SCHEMA if qualification.local_1612 else META_SCHEMA_VERSION,
        }
    )
    body = {
        "contract_version": INDEX_IDENTITY_CONTRACT_VERSION,
        "kind": "gitnexus-index-identity",
        "repository": {
            "canonical_repository_id": repository.canonical_repository_id,
            "canonical_remote": repository.canonical_remote,
            "repository_identity_digest": repository.identity["repository_identity_digest"],
        },
        "checkout": {
            "checkout_kind": checkout_kind,
            "checkout_root_sha256": hashlib.sha256(
                str(repository.root).encode("utf-8", "surrogateescape")
            ).hexdigest(),
            "worktree_id_digest": repository.identity["worktree_id_digest"],
        },
        "source": {
            "head": repository.head,
            "branch_state": "branch" if repository.branch is not None else "detached",
            "branch": repository.branch,
        },
        "content": {
            "state": content_state,
            "tracked_state_digest": snapshot.tracked_state_digest,
            "complete_status_digest": snapshot.complete_status_digest,
            "worktree_state_digest": snapshot.worktree_state_digest,
            "relevant_content_digest": snapshot.relevant_content_digest,
        },
        "lifecycle": {
            "context": lifecycle,
            "alias": alias,
            "exact_eligible": exact_eligible,
            "automatic_refresh_eligible": exact_eligible
            and checkout_kind == "primary" and qualification.local_1612 is None,
        },
        "tool": {
            "driver_version": DRIVER_VERSION,
            "gitnexus_version": qualification.version,
            "qualification_fingerprint": qualification.fingerprint,
            "metadata_schema": LOCAL_1612_SCHEMA if qualification.local_1612 else META_SCHEMA_VERSION,
        },
        "configuration": {"analyze_config_digest": config_digest},
        "freshness": {
            "status": "exact" if exact_eligible else "advisory",
            "metadata_digest": metadata_digest,
            "indexed_at": indexed_at,
            "observed_at": observed_at,
        },
        "authority_invariants": {
            "advisory_only": True,
            "authorization_granted": False,
            "review_satisfied": False,
            "gate_satisfied": False,
            "completion_proven": False,
        },
    }
    return {**body, "index_identity_digest": _canonical_digest(body)}


def build_pr_review_identity(
    base_repository: RepositoryState,
    base_snapshot: TrackedSnapshot,
    head_repository: RepositoryState,
    head_snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    observed_at: str,
    deadline: float | None = None,
) -> dict[str, Any]:
    """Bind a clean committed PR base/head pair without granting review authority."""
    if (
        base_repository.canonical_repository_id != head_repository.canonical_repository_id
        or base_repository.canonical_remote != head_repository.canonical_remote
    ):
        raise GitNexusAdapterError("PR review identities must use one canonical repository")
    identities = []
    for role, repository, snapshot in (
        ("base", base_repository, base_snapshot),
        ("head", head_repository, head_snapshot),
    ):
        identity = build_index_identity(
            repository,
            snapshot,
            qualification,
            metadata_digest="0" * 64,
            indexed_at=observed_at,
            observed_at=observed_at,
            deadline=deadline,
        )
        if not identity["lifecycle"]["exact_eligible"]:
            raise GitNexusAdapterError(f"PR review {role} identity must be clean and committed")
        identities.append(
            {
                "role": role,
                "head": repository.head,
                "branch": repository.branch,
                "alias": identity["lifecycle"]["alias"],
                "worktree_id_digest": repository.identity["worktree_id_digest"],
                "relevant_content_digest": snapshot.relevant_content_digest,
                "index_identity_digest": identity["index_identity_digest"],
            }
        )
    if identities[0]["alias"] == identities[1]["alias"]:
        raise GitNexusAdapterError("PR review base and head aliases must be distinct")
    body = {
        "contract_version": PR_REVIEW_IDENTITY_CONTRACT_VERSION,
        "kind": "gitnexus-pr-review-identity",
        "canonical_repository_id": base_repository.canonical_repository_id,
        "canonical_remote": base_repository.canonical_remote,
        "observed_at": observed_at,
        "identities": identities,
        "authority_invariants": {
            "advisory_only": True,
            "review_satisfied": False,
            "gate_satisfied": False,
            "completion_proven": False,
        },
    }
    return {**body, "pr_review_identity_digest": _canonical_digest(body)}


def _open_directory_nofollow(path: pathlib.Path) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise GitNexusAdapterError("POSIX no-follow directory operations are unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return os.open(path, flags)


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


def _load_index_identity_at(
    directory_fd: int,
    *,
    deadline: float | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = _read_regular_at(
            directory_fd,
            INDEX_IDENTITY_FILENAME,
            maximum_bytes=MAX_INDEX_IDENTITY_BYTES,
            deadline=deadline,
        )
    except FileNotFoundError:
        return None, "index-identity-evidence-missing"
    except ProbeDeadlineError:
        raise
    except (GitNexusAdapterError, OSError):
        return None, "index-identity-evidence-unreadable"

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=reject_duplicates
        )
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError):
        return None, "index-identity-evidence-invalid"
    if not isinstance(value, dict):
        return None, "index-identity-evidence-invalid"
    return value, None


def _validate_index_identity(
    value: Mapping[str, Any],
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    metadata_digest: str,
    indexed_at: str,
    deadline: float | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        freshness = value.get("freshness")
        if not isinstance(freshness, dict):
            raise GitNexusAdapterError("index identity freshness is missing")
        observed_at = freshness.get("observed_at")
        if not isinstance(observed_at, str):
            raise GitNexusAdapterError("index identity observed time is missing")
        expected = build_index_identity(
            repository,
            snapshot,
            qualification,
            metadata_digest=metadata_digest,
            indexed_at=indexed_at,
            observed_at=observed_at,
            deadline=deadline,
        )
    except (GitNexusAdapterError, OSError, TypeError, ValueError):
        return None, "index-identity-evidence-invalid"
    if dict(value) != expected:
        try:
            content = value.get("content")
            if (
                isinstance(content, dict)
                and content.get("relevant_content_digest")
                != snapshot.relevant_content_digest
            ):
                return None, "index-identity-content-mismatch"
            source = value.get("source")
            if isinstance(source, dict) and source.get("head") != repository.head:
                return None, "index-identity-head-mismatch"
            checkout = value.get("checkout")
            if (
                isinstance(checkout, dict)
                and checkout.get("worktree_id_digest")
                != repository.identity["worktree_id_digest"]
            ):
                return None, "index-identity-worktree-mismatch"
            tool = value.get("tool")
            if (
                isinstance(tool, dict)
                and tool.get("qualification_fingerprint")
                != qualification.fingerprint
            ):
                return None, "index-identity-tool-mismatch"
        except (KeyError, TypeError):
            pass
        return None, "index-identity-evidence-mismatch"
    if expected["freshness"]["status"] != "exact":
        return None, "index-identity-not-exact"
    return expected, None


def _write_index_identity(
    index_directory: pathlib.Path,
    identity: Mapping[str, Any],
    *,
    deadline: float | None = None,
) -> None:
    _check_deadline(deadline)
    raw = json.dumps(
        dict(identity), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(raw) > MAX_INDEX_IDENTITY_BYTES:
        raise GitNexusAdapterError("index identity evidence exceeds its safety bound")
    _check_deadline(deadline)
    directory_fd = _open_directory_nofollow(index_directory)
    temporary = f".{INDEX_IDENTITY_FILENAME}.tmp-{os.getpid()}-{threading.get_ident()}"
    descriptor: int | None = None
    created = False
    try:
        _check_deadline(deadline)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
        created = True
        written = 0
        while written < len(raw):
            _check_deadline(deadline)
            count = os.write(descriptor, raw[written:])
            if count <= 0:
                raise OSError(errno.EIO, "short write")
            written += count
        _check_deadline(deadline)
        os.fsync(descriptor)
        _check_deadline(deadline)
        os.close(descriptor)
        descriptor = None
        _check_deadline(deadline)
        os.replace(
            temporary,
            INDEX_IDENTITY_FILENAME,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        created = False
        os.fsync(directory_fd)
    except OSError as exc:
        raise GitNexusAdapterError("index identity evidence cannot be written safely") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                os.unlink(temporary, dir_fd=directory_fd)
            except OSError:
                pass
        os.close(directory_fd)


def _metadata_1612_diagnostic_shape(value: dict[str, Any]) -> tuple[str | None, str | None]:
    """Recognize typed 1.6.12 metadata without trusting its receipts or freshness.

    This intentionally covers a narrow producer subset. Unknown fields, omitted
    completeness receipts and unfinished/degraded operations remain rejected.
    Paths and digests here are untrusted declarations; no referenced file is
    opened, executed, authenticated or adopted by this diagnostic parser.
    """
    if "schemaVersion" in value:
        return "corrupt", "metadata-mixed-schema-profiles"
    if META_1612_REQUIRED_FIELDS - set(value):
        return "partial", "metadata-1612-required-fields-missing"
    if set(value) - META_1612_REQUIRED_FIELDS - META_1612_REFUSED_FIELDS:
        return "corrupt", "metadata-1612-unknown-fields"
    # Presence is sufficient to refuse these records, even null/empty markers.
    # Their internal formats are outside this diagnostic subset.
    if set(value) & META_1612_REFUSED_FIELDS:
        return "partial", "metadata-1612-operation-or-coverage-unqualified"

    def text(item: Any, limit: int = 4096) -> bool:
        if not isinstance(item, str) or not 0 < len(item) <= limit or "\x00" in item:
            return False
        try:
            item.encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True

    def integer(item: Any, minimum: int = 0) -> bool:
        return type(item) is int and minimum <= item <= 2**53 - 1

    def absolute(item: Any) -> bool:
        return text(item) and pathlib.PurePosixPath(item).is_absolute() and ".." not in pathlib.PurePosixPath(item).parts

    def relative(item: Any) -> bool:
        return (
            text(item) and "\\" not in item and "//" not in item
            and not item.startswith("/") and not item.endswith("/")
            and all(part not in {"", ".", ".."} for part in item.split("/"))
            and not item.startswith((".git/", ".gitnexus/"))
            and item not in {".git", ".gitnexus"}
        )

    def record(item: Any, keys: set[str]) -> bool:
        return isinstance(item, dict) and set(item) == keys

    def digest(item: Any) -> bool:
        return isinstance(item, str) and item.startswith("sha256:") and bool(SHA256_RE.fullmatch(item[7:]))

    invalid = ("corrupt", "metadata-1612-typed-field-invalid")
    if not (
        absolute(value["repoPath"]) and absolute(value["storagePath"])
        and value["storagePath"] == value["repoPath"].rstrip("/") + "/.gitnexus"
        and isinstance(value["lastCommit"], str) and COMMIT_RE.fullmatch(value["lastCommit"])
        and text(value["remoteUrl"]) and text(value["branch"], 256)
        and text(value["indexedAt"], 128)
    ):
        return invalid
    try:
        timestamp = dt.datetime.fromisoformat(value["indexedAt"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            return invalid
        normalize_remote(value["remoteUrl"])
    except (ValueError, TypeError, GitNexusAdapterError):
        return invalid
    stats = value["stats"]
    if not record(stats, {"files", "nodes", "edges", "communities", "processes", "embeddings"}) or not all(integer(n) for n in stats.values()):
        return invalid
    if (
        value["contentRetention"] != "full" or value["ftsProfile"] != "full"
        or type(value["contentRetentionSchemaVersion"]) is not int
        or value["contentRetentionSchemaVersion"] != 1
        or type(value["scopeExtractionReceipt"]) is not int
        or value["scopeExtractionReceipt"] != 1
        or value["cjkSegmentation"] != "none"
        or type(value["embeddingDims"]) is not int or value["embeddingDims"] != 384
    ):
        return "unsupported", "metadata-1612-profile-unqualified"
    fingerprint = value["schemaFingerprint"]
    if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{12}", fingerprint) is None:
        return invalid
    # Independently derived from the fixed local 1.6.12 DDL source. This is
    # recognition only: neither release provenance nor a DB schema check.
    if fingerprint != "60fc01e4e4ed":
        return "unsupported", "metadata-1612-schema-fingerprint-unqualified"
    features = value["analysisFeatures"]
    if not record(features, {"graph.class-framework-annotations"}) or type(features["graph.class-framework-annotations"]) is not int or features["graph.class-framework-annotations"] != 1:
        return "unsupported", "metadata-1612-analysis-features-unqualified"
    try:
        prefixes = json.loads(value["springVendorPrefixes"])
        if not isinstance(prefixes, list) or len(prefixes) > 1024 or not all(text(p, 256) for p in prefixes) or len(set(prefixes)) != len(prefixes):
            return invalid
    except (TypeError, ValueError, RecursionError):
        return invalid
    capabilities = value["capabilities"]
    if not record(capabilities, {"graph", "fts", "vectorSearch"}):
        return invalid
    graph, fts, vector = (capabilities[k] for k in ("graph", "fts", "vectorSearch"))
    if not record(graph, {"provider", "status"}) or graph != {"provider": GRAPH_PROVIDER, "status": "available"}:
        return invalid
    if not isinstance(fts, dict) or set(fts) not in ({"provider", "status"}, {"provider", "status", "skipReason"}) or fts.get("provider") != FTS_PROVIDER:
        return invalid
    if fts.get("status") == "available":
        if "skipReason" in fts:
            return invalid
    elif fts.get("status") == "unavailable":
        if fts.get("skipReason") not in ("extension-unavailable", "build-failed", "disabled-by-flag", "disabled-by-env"):
            return invalid
        if fts["skipReason"] != "extension-unavailable":
            return "unsupported", "metadata-1612-fts-degradation-unqualified"
    else:
        return invalid
    if not isinstance(vector, dict) or set(vector) not in ({"provider", "status", "exactScanLimit"}, {"provider", "status", "exactScanLimit", "reason"}):
        return invalid
    if vector["provider"] not in (VECTOR_PROVIDER, "exact-scan") or vector["status"] != "unavailable" or not integer(vector["exactScanLimit"], 1) or ("reason" in vector and not text(vector["reason"], 256)):
        return invalid
    if not _runner_1612_valid(value["runnerIdentity"]):
        return invalid
    hashes, keys, coverage = (value[k] for k in ("fileHashes", "cacheKeys", "indexCoverage"))
    if not isinstance(hashes, dict) or len(hashes) > MAX_SNAPSHOT_ENTRIES or not all(relative(p) and isinstance(h, str) and SHA256_RE.fullmatch(h) for p, h in hashes.items()):
        return invalid
    if not isinstance(keys, list) or len(keys) > 100_000 or not all(isinstance(k, str) and SHA256_RE.fullmatch(k) for k in keys) or len(set(keys)) != len(keys):
        return invalid
    if not record(coverage, {"maxFileSizeBytes", "dirtyPaths"}) or not integer(coverage["maxFileSizeBytes"], 1) or not isinstance(coverage["dirtyPaths"], list) or len(coverage["dirtyPaths"]) > MAX_SNAPSHOT_ENTRIES or not all(relative(p) for p in coverage["dirtyPaths"]):
        return invalid
    if coverage["maxFileSizeBytes"] != 524288:
        return "unsupported", "metadata-1612-coverage-policy-unqualified"
    if coverage["dirtyPaths"] or stats["files"] != len(hashes) or not hashes or stats["embeddings"] != 0:
        return "partial", "metadata-1612-coverage-unqualified"
    return None, None


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
    if "schemaFingerprint" in value:
        state, reason = _metadata_1612_diagnostic_shape(value)
        return value, state, reason
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
            primary_1612 = isinstance(primary, dict) and "schemaFingerprint" in primary
            legacy_1612 = isinstance(legacy, dict) and "schemaFingerprint" in legacy
            if primary_1612 != legacy_1612:
                return primary, "incompatible", "metadata-primary-legacy-conflict"
            if primary_1612:
                # Structural comparison is confined to two fully typed records.
                # Never canonicalize untrusted Unicode path keys as memory keys.
                if primary_state is not None or legacy_state is not None:
                    return primary, primary_state or legacy_state, primary_reason or legacy_reason
                matching = primary == legacy
            else:
                matching = _canonical_digest(primary) == _canonical_digest(legacy)
            if not matching:
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
        primary_1612 = isinstance(primary, dict) and "schemaFingerprint" in primary
        legacy_1612 = isinstance(legacy, dict) and "schemaFingerprint" in legacy
        if primary_1612 or legacy_1612:
            converged = primary_1612 and legacy_1612 and primary == legacy
        else:
            converged = _canonical_digest(primary) == _canonical_digest(legacy)
        _check_deadline(deadline)
        return converged
    except (TypeError, ValueError, memory_contract.MemoryContractError):
        return False


def _assess_metadata_1612(repository: RepositoryState, snapshot: TrackedSnapshot,
                          qualification: ExecutableQualification, metadata: dict[str, Any], *,
                          deadline: float | None = None) -> MetadataResult:
    profile = qualification.local_1612
    assert profile is not None
    indexed = metadata["lastCommit"]
    digest = hashlib.sha256((LOCAL_1612_SCHEMA + "\0" + _local_json(metadata)).encode("ascii")).hexdigest()

    def result(state: str, reason: str) -> MetadataResult:
        return MetadataResult(state, reason, indexed, digest, metadata)

    if metadata["runnerIdentity"] != json.loads(profile.runner_json):
        return result("incompatible", "metadata-1612-runner-identity-mismatch")
    if metadata["repoPath"] != str(repository.root) or metadata["storagePath"] != str(repository.root / ".gitnexus"):
        return result("incompatible", "metadata-repository-path-mismatch")
    try:
        if normalize_remote(metadata["remoteUrl"]) != repository.canonical_remote:
            return result("incompatible", "metadata-remote-mismatch")
    except GitNexusAdapterError:
        return result("incompatible", "metadata-repository-identity-invalid")
    if repository.branch is None or metadata["branch"] != repository.branch:
        return result("incompatible", "metadata-branch-mismatch")
    if snapshot.head != repository.head or snapshot.branch != repository.branch:
        return result("unknown", "caller-snapshot-identity-conflict")
    if snapshot.tracked_dirty or snapshot.outside_derived_dirty:
        return result("stale", "working-tree-dirty")
    if indexed != repository.head:
        return result("stale", "indexed-revision-stale")
    if set(metadata["fileHashes"]) != set(profile.coverage_paths):
        return result("partial", "metadata-1612-coverage-set-mismatch")
    root_fd = _open_directory_nofollow(repository.root)
    try:
        # Open only caller-owned paths, never paths supplied by metadata.
        for path in profile.coverage_paths:
            actual, info = _package_target_identity_at(root_fd, path.split("/"), deadline=deadline, maximum_bytes=524288)
            if info.st_size > 524288:
                return result("partial", "metadata-1612-covered-file-too-large")
            if actual != metadata["fileHashes"][path]:
                return result("stale", "metadata-1612-covered-content-mismatch")
    except ProbeDeadlineError:
        raise
    except (GitNexusAdapterError, OSError):
        return result("incompatible", "metadata-1612-covered-input-unsafe")
    finally:
        os.close(root_fd)
    return _metadata_identity_result(repository, snapshot, qualification, metadata, digest, deadline=deadline)


def _metadata_identity_result(repository: RepositoryState, snapshot: TrackedSnapshot,
                              qualification: ExecutableQualification, metadata: dict[str, Any],
                              digest: str, *, deadline: float | None = None) -> MetadataResult:
    indexed = metadata["lastCommit"]
    index_directory = repository.root / ".gitnexus"
    try:
        directory_fd = _open_directory_nofollow(index_directory)
    except OSError:
        return MetadataResult(
            "unknown", "index-identity-directory-unavailable", indexed, digest, metadata
        )
    try:
        identity, identity_reason = _load_index_identity_at(
            directory_fd, deadline=deadline
        )
    finally:
        os.close(directory_fd)
    if identity_reason is not None or identity is None:
        return MetadataResult(
            "stale", identity_reason or "index-identity-evidence-missing", indexed, digest, metadata
        )
    validated_identity, identity_reason = _validate_index_identity(
        identity,
        repository,
        snapshot,
        qualification,
        metadata_digest=digest,
        indexed_at=metadata["indexedAt"],
        deadline=deadline,
    )
    if identity_reason is not None or validated_identity is None:
        return MetadataResult(
            "stale", identity_reason or "index-identity-evidence-invalid", indexed, digest, metadata
        )
    _check_deadline(deadline)
    return MetadataResult(
        "fresh", "exact-clean-content", indexed, digest, metadata, validated_identity
    )


def assess_metadata(
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    metadata_path: str | os.PathLike[str] | None = None,
    deadline: float | None = None,
) -> MetadataResult:
    """Validate one exact qualified profile and its content-bound sidecar."""
    _check_deadline(deadline)
    try:
        _validated_repository_state_identity(repository)
    except GitNexusAdapterError:
        return MetadataResult("incompatible", "caller-repository-identity-invalid", None, None, None)
    try:
        verify_qualification(qualification, deadline=deadline)
    except ProbeDeadlineError:
        raise
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
    if "schemaFingerprint" in metadata:
        if qualification.local_1612 is not None:
            return _assess_metadata_1612(repository, snapshot, qualification, metadata, deadline=deadline)
        return MetadataResult("unsupported", "metadata-1.6.12-runner-unqualified", None, None, metadata)
    if qualification.local_1612 is not None:
        return MetadataResult("unsupported", "metadata-profile-mismatch", None, None, metadata)
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
    if snapshot.branch != repository.branch:
        return MetadataResult(
            "unknown", "caller-snapshot-branch-conflict", indexed, digest, metadata
        )
    if snapshot.tracked_dirty or snapshot.outside_derived_dirty:
        return MetadataResult("stale", "working-tree-dirty", indexed, digest, metadata)
    if indexed != repository.head:
        return MetadataResult("stale", "indexed-revision-stale", indexed, digest, metadata)
    return _metadata_identity_result(repository, snapshot, qualification, metadata, digest, deadline=deadline)


def _assess_metadata_before_identity_write(
    repository: RepositoryState,
    snapshot: TrackedSnapshot,
    qualification: ExecutableQualification,
    *,
    deadline: float | None = None,
) -> MetadataResult:
    """Accept only a fully valid clean revision whose Codex sidecar is absent/stale."""
    result = assess_metadata(
        repository, snapshot, qualification, deadline=deadline
    )
    if result.state == "fresh":
        return result
    if result.state == "stale" and result.reason.startswith("index-identity-"):
        return MetadataResult(
            "fresh",
            "qualified-metadata-clean-revision",
            result.indexed_revision,
            result.metadata_digest,
            result.metadata,
        )
    return result


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
                "metadata_schema": LOCAL_1612_SCHEMA if qualification.local_1612 else META_SCHEMA_VERSION,
            },
        }
    handshake = {
        "contract_version": memory_contract.CONTRACT_VERSION,
        "kind": "capability-handshake",
        "adapter": {
            "adapter_id": "gitnexus-local-advisory",
            "adapter_version": f"{qualification.version}.{qualification.fingerprint}",
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


def _validated_repository_state_identity(repository: RepositoryState) -> dict[str, Any]:
    try:
        identity = memory_contract.validate_repository_identity(repository.identity)
    except (TypeError, ValueError) as exc:
        raise GitNexusAdapterError("refresh repository identity evidence is invalid") from exc
    source = identity["source_revision"]
    if (
        identity["canonical_repository_id"] != repository.canonical_repository_id
        or identity["canonical_remote"] != repository.canonical_remote
        or source["commit_sha"] != repository.head
        or source.get("branch") != repository.branch
    ):
        raise GitNexusAdapterError("refresh repository state fields conflict with identity evidence")
    return identity


def _repository_state_matches(left: RepositoryState, right: RepositoryState) -> bool:
    return bool(
        left.root == right.root
        and left.canonical_repository_id == right.canonical_repository_id
        and left.canonical_remote == right.canonical_remote
        and left.head == right.head
        and left.branch == right.branch
        and left.identity == right.identity
    )


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
    git_executable: str | os.PathLike[str] | None = None,
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
    _reject_repository_git_execution_config(
        root,
        deadline=deadline,
        git_executable=git_executable,
    )
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
            git_executable=git_executable,
        )
        if ignored.returncode != 0:
            raise GitNexusAdapterError("Git exclude does not effectively ignore .gitnexus/")
    admin_tree_digest = _filesystem_tree_digest(root / ".git", deadline=deadline)
    return _canonical_digest({
        "exclude_sha256": hashlib.sha256(exclude).hexdigest(),
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "head_sha256": hashlib.sha256(head).hexdigest(),
        "admin_tree_digest": admin_tree_digest,
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


def _isolated_home_identity_from_stat(
    path: pathlib.Path, info: os.stat_result
) -> _IsolatedHomeIdentity:
    if not stat.S_ISDIR(info.st_mode):
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME must be a real non-symlink directory"
        )
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o022:
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME must not be group- or world-writable"
        )
    uid = getattr(info, "st_uid", None)
    effective_uid = getattr(os, "geteuid", None)
    if callable(effective_uid) and uid != effective_uid():
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME must be owned by the effective user"
        )
    return _IsolatedHomeIdentity(path, info.st_dev, info.st_ino, mode, uid)


def _open_isolated_home(
    path: pathlib.Path,
) -> tuple[_IsolatedHomeIdentity, int]:
    descriptor: int | None = None
    try:
        resolved = path.resolve(strict=True)
        info = path.lstat()
        descriptor = _open_directory_nofollow(path)
        opened = os.fstat(descriptor)
    except (GitNexusAdapterError, OSError) as exc:
        if descriptor is not None:
            os.close(descriptor)
        raise GitNexusAdapterError("isolated GITNEXUS_HOME cannot be inspected") from exc
    if resolved != path or stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        os.close(descriptor)
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME must be a real non-symlink directory"
        )
    if (opened.st_dev, opened.st_ino, opened.st_mode) != (
        info.st_dev,
        info.st_ino,
        info.st_mode,
    ):
        os.close(descriptor)
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME changed during validation"
        )
    try:
        identity = _isolated_home_identity_from_stat(path, opened)
    except GitNexusAdapterError:
        os.close(descriptor)
        raise
    return identity, descriptor


def _capture_isolated_home_identity(path: pathlib.Path) -> _IsolatedHomeIdentity:
    identity, descriptor = _open_isolated_home(path)
    os.close(descriptor)
    return identity


def _recheck_isolated_home_identity(
    identity: _IsolatedHomeIdentity,
    descriptor: int | None = None,
) -> None:
    try:
        if descriptor is not None:
            opened = _isolated_home_identity_from_stat(
                identity.path, os.fstat(descriptor)
            )
            if opened != identity:
                raise GitNexusAdapterError(
                    "isolated GITNEXUS_HOME descriptor identity changed during refresh"
                )
        current = _capture_isolated_home_identity(identity.path)
    except GitNexusAdapterError as exc:
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME safety changed during refresh"
        ) from exc
    if current != identity:
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME identity changed during refresh"
        )


def _require_empty_isolated_home_descriptor(descriptor: int) -> None:
    try:
        with os.scandir(descriptor) as entries:
            if next(entries, None) is not None:
                raise GitNexusAdapterError("isolated GITNEXUS_HOME must be empty for each refresh")
    except OSError as exc:
        raise GitNexusAdapterError("isolated GITNEXUS_HOME cannot be inspected") from exc


def _require_empty_isolated_home(path: pathlib.Path) -> None:
    identity, descriptor = _open_isolated_home(path)
    try:
        _require_empty_isolated_home_descriptor(descriptor)
        _recheck_isolated_home_identity(identity, descriptor)
    finally:
        os.close(descriptor)


def _isolated_home_lock_name(identity: _IsolatedHomeIdentity) -> str:
    key = _canonical_digest({"device": identity.device, "inode": identity.inode})
    return f"home-{key}.lock"


@contextlib.contextmanager
def _isolated_home_resource(
    path: pathlib.Path,
    root: pathlib.Path,
    *,
    deadline: float | None = None,
) -> Iterator[tuple[_IsolatedHomeIdentity, int]]:
    """Hold one descriptor-bound home and its cross-repository mutex."""

    _check_deadline(deadline)
    identity, home_descriptor = _open_isolated_home(path)
    thread_key = _isolated_home_lock_name(identity)
    with _HOME_THREAD_LOCKS_GUARD:
        thread_lock = _HOME_THREAD_LOCKS.setdefault(thread_key, threading.Lock())
    if not thread_lock.acquire(blocking=False):
        os.close(home_descriptor)
        raise GitNexusAdapterError("isolated GITNEXUS_HOME lock is unavailable")
    lock_descriptor: int | None = None
    lock_directory_descriptor: int | None = None
    try:
        _, lock_directory_descriptor = _safe_lock_directory(None, root)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        lock_name = _isolated_home_lock_name(identity)
        lock_descriptor = os.open(
            lock_name, flags, 0o600, dir_fd=lock_directory_descriptor
        )
        lock_info = os.fstat(lock_descriptor)
        lock_entry = os.stat(
            lock_name,
            dir_fd=lock_directory_descriptor,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISREG(lock_info.st_mode)
            or (lock_info.st_dev, lock_info.st_ino)
            != (lock_entry.st_dev, lock_entry.st_ino)
            or lock_info.st_nlink != 1
            or lock_info.st_uid != os.geteuid()
            or lock_info.st_mode & 0o022
        ):
            raise GitNexusAdapterError("isolated GITNEXUS_HOME lock file is unsafe")
        try:
            import fcntl
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError, OSError) as exc:
            raise GitNexusAdapterError(
                "isolated GITNEXUS_HOME cross-process lock is unavailable"
            ) from exc
        locked_entry = os.stat(
            lock_name,
            dir_fd=lock_directory_descriptor,
            follow_symlinks=False,
        )
        locked_info = os.fstat(lock_descriptor)
        if (
            (locked_entry.st_dev, locked_entry.st_ino)
            != (lock_info.st_dev, lock_info.st_ino)
            or (locked_info.st_dev, locked_info.st_ino)
            != (lock_info.st_dev, lock_info.st_ino)
            or locked_info.st_nlink != 1
            or locked_info.st_uid != os.geteuid()
            or locked_info.st_mode & 0o022
        ):
            raise GitNexusAdapterError(
                "isolated GITNEXUS_HOME lock changed during acquisition"
            )
        _check_deadline(deadline)
        _recheck_isolated_home_identity(identity, home_descriptor)
        _require_empty_isolated_home_descriptor(home_descriptor)
        yield identity, home_descriptor
    except GitNexusAdapterError:
        raise
    except OSError as exc:
        raise GitNexusAdapterError(
            "isolated GITNEXUS_HOME lock cannot be acquired safely"
        ) from exc
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
        if lock_directory_descriptor is not None:
            os.close(lock_directory_descriptor)
        os.close(home_descriptor)
        thread_lock.release()


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


def _lock_directory_path(lock_directory: pathlib.Path | None) -> pathlib.Path:
    if lock_directory is None:
        # Mac and Linux both expose /tmp; resolving its fixed OS path avoids
        # per-process TMPDIR/TEMP/TMP selectors splitting the canonical lock.
        base = pathlib.Path("/tmp").resolve(strict=True)
        return base / f"codex-gitnexus-locks-{os.geteuid()}"
    return pathlib.Path(os.path.abspath(lock_directory.expanduser()))


def _safe_lock_directory(
    lock_directory: pathlib.Path | None,
    root: pathlib.Path,
) -> tuple[pathlib.Path, int]:
    lexical = _lock_directory_path(lock_directory)
    if lexical == root or root in lexical.parents:
        raise GitNexusAdapterError("refresh lock directory must be outside the repository")
    directory_flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        directory_flags |= os.O_CLOEXEC
    descriptor: int | None = None
    directory_descriptor: int | None = None
    try:
        descriptor = os.open(lexical.anchor, directory_flags)
        for part in lexical.parts[1:-1]:
            next_descriptor = os.open(part, directory_flags, dir_fd=descriptor)
            opened_parent = os.fstat(next_descriptor)
            sticky_public_root = bool(
                opened_parent.st_uid == 0
                and opened_parent.st_mode & stat.S_ISVTX
                and opened_parent.st_mode & 0o002
            )
            if (
                not stat.S_ISDIR(opened_parent.st_mode)
                or opened_parent.st_uid not in {0, os.geteuid()}
                or (opened_parent.st_mode & 0o022 and not sticky_public_root)
            ):
                os.close(next_descriptor)
                raise GitNexusAdapterError(
                    "refresh lock directory parent boundary is unsafe"
                )
            os.close(descriptor)
            descriptor = next_descriptor
        try:
            os.mkdir(lexical.name, 0o700, dir_fd=descriptor)
        except FileExistsError:
            pass
        directory_descriptor = os.open(
            lexical.name, directory_flags, dir_fd=descriptor
        )
        info = os.fstat(directory_descriptor)
        _LOCK_DIRECTORY_VALIDATION_HOOK(lexical)
        live = os.stat(lexical, follow_symlinks=False)
    except GitNexusAdapterError:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        raise
    except OSError as exc:
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        raise GitNexusAdapterError("refresh lock directory cannot be prepared safely") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_dev != live.st_dev
        or info.st_ino != live.st_ino
        or info.st_uid != os.geteuid()
        or info.st_mode & 0o022
    ):
        assert directory_descriptor is not None
        os.close(directory_descriptor)
        raise GitNexusAdapterError("refresh lock directory is unsafe")
    assert directory_descriptor is not None
    return lexical, directory_descriptor


@contextlib.contextmanager
def _directory_root_lock(
    root: pathlib.Path, lock_directory: pathlib.Path | None
) -> Iterator[None]:
    key = _canonical_digest({"root": str(root)})
    descriptor: int | None = None
    directory_descriptor: int | None = None
    try:
        directory, directory_descriptor = _safe_lock_directory(lock_directory, root)
        opened_directory = os.fstat(directory_descriptor)
        expected_directory = os.stat(directory, follow_symlinks=False)
        if (
            opened_directory.st_dev != expected_directory.st_dev
            or opened_directory.st_ino != expected_directory.st_ino
            or not stat.S_ISDIR(opened_directory.st_mode)
            or opened_directory.st_uid != os.geteuid()
            or opened_directory.st_mode & 0o022
        ):
            raise GitNexusAdapterError("refresh lock directory changed during validation")
        lock_name = f"{key}.lock"
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        descriptor = os.open(lock_name, flags, 0o600, dir_fd=directory_descriptor)
        info = os.fstat(descriptor)
        entry = os.stat(lock_name, dir_fd=directory_descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_dev != entry.st_dev
            or info.st_ino != entry.st_ino
            or stat.S_IFMT(info.st_mode) != stat.S_IFMT(entry.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o022
        ):
            raise GitNexusAdapterError("refresh lock file is unsafe")
        try:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError, OSError) as exc:
            raise GitNexusAdapterError("refresh cross-process lock is unavailable") from exc
        locked_entry = os.stat(lock_name, dir_fd=directory_descriptor, follow_symlinks=False)
        if locked_entry.st_dev != info.st_dev or locked_entry.st_ino != info.st_ino:
            raise GitNexusAdapterError("refresh lock file changed during acquisition")
        yield
        live_directory = os.stat(directory, follow_symlinks=False)
        if (
            live_directory.st_dev != opened_directory.st_dev
            or live_directory.st_ino != opened_directory.st_ino
        ):
            raise GitNexusAdapterError(
                "refresh lock directory changed while the lock was held"
            )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)


@contextlib.contextmanager
def _root_lock(root: pathlib.Path, lock_directory: pathlib.Path | None) -> Iterator[None]:
    """Serialize one repository across processes regardless of optional local paths."""

    key = _canonical_digest({"root": str(root)})
    with _THREAD_LOCKS_GUARD:
        lock = _THREAD_LOCKS.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise GitNexusAdapterError("refresh already holds the repository lock")
    try:
        with _directory_root_lock(root, None):
            if (
                lock_directory is not None
                and _lock_directory_path(lock_directory) != _lock_directory_path(None)
            ):
                with _directory_root_lock(root, lock_directory):
                    yield
            else:
                yield
    finally:
        lock.release()


def _require_local_1612_default_config(root: pathlib.Path, *, deadline: float | None) -> None:
    """Repository config is outside the caller-approved local execution profile."""
    _check_deadline(deadline)
    try:
        descriptor = _open_directory_nofollow(root)
        try:
            os.stat(".gitnexusrc", dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise GitNexusAdapterError("local 1.6.12 repository config inspection failed") from exc
    finally:
        _check_deadline(deadline)
    raise GitNexusAdapterError("local 1.6.12 refresh refuses repository .gitnexusrc")


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
        git_executable: str | os.PathLike[str] | None = None,
        runner: Runner = _run_refresh_subprocess,
    ) -> None:
        _validate_timeout_seconds(
            timeout_seconds, label="refresh", maximum=3_600
        )
        self.qualification = qualification
        self.enabled = enabled
        self.auto_capability_enabled = False
        self.timeout_seconds = timeout_seconds
        self.environment = _safe_environment(environment)
        self.gitnexus_home = gitnexus_home
        self.lock_directory = lock_directory
        self.git_executable = git_executable
        self.runner = runner

    def refresh(
        self,
        repository: RepositoryState,
        *,
        expected_head: str,
        explicit_opt_in: bool = False,
        deadline: float | None = None,
    ) -> RefreshResult:
        controller_deadline = _refresh_deadline(self.timeout_seconds)
        if deadline is None:
            deadline = controller_deadline
        else:
            deadline = min(_validated_deadline(deadline), controller_deadline)
        _check_deadline(deadline)
        if not self.enabled or not explicit_opt_in:
            raise GitNexusAdapterError("refresh is disabled unless explicitly opted in")
        if not COMMIT_RE.fullmatch(expected_head):
            raise GitNexusAdapterError("refresh expected HEAD is invalid")
        supplied_identity = _validated_repository_state_identity(repository)
        if repository.head != expected_head:
            raise GitNexusAdapterError("refresh expected HEAD conflicts with caller evidence")
        root = _strict_root(
            repository.root,
            deadline=deadline,
            git_executable=self.git_executable,
        )
        if root != repository.root:
            raise GitNexusAdapterError("refresh repository root identity mismatch")
        if self.qualification.local_1612 is not None:
            _require_local_1612_default_config(root, deadline=deadline)
        verify_qualification(self.qualification, deadline=deadline)
        isolated_home = _resolve_isolated_home(self.gitnexus_home, root)
        with (
            _root_lock(root, self.lock_directory),
            _isolated_home_resource(
                isolated_home, root, deadline=deadline
            ) as isolated_home_resource,
        ):
            isolated_home_identity, isolated_home_descriptor = isolated_home_resource
            _validate_derived_index_tree(root, deadline=deadline)
            before_repository = collect_repository_state(
                root,
                canonical_repository_id=repository.canonical_repository_id,
                expected_remote=repository.canonical_remote,
                principal_scope=supplied_identity["principal_scope"],
                path_scope=supplied_identity["path_scope"],
                deadline=deadline,
                git_executable=self.git_executable,
            )
            if not _repository_state_matches(repository, before_repository):
                raise GitNexusAdapterError(
                    "refresh caller repository evidence does not match live state"
                )
            repository = before_repository
            before = collect_tracked_snapshot(
                root, deadline=deadline, git_executable=self.git_executable
            )
            before_git_control_digest = _git_control_snapshot(
                root,
                require_exclusion=True,
                deadline=deadline,
                git_executable=self.git_executable,
            )
            if before_repository.head != expected_head or before.head != expected_head:
                raise GitNexusAdapterError("refresh expected HEAD does not match current repository")
            if before.tracked_derived_present:
                raise GitNexusAdapterError(
                    "refresh refuses tracked paths inside the derived index"
                )
            if before.tracked_dirty or before.outside_derived_dirty:
                raise GitNexusAdapterError("refresh refuses a dirty working tree outside the derived index")
            if before.outside_derived_dirty:
                raise GitNexusAdapterError("refresh refuses pre-existing changes outside the derived index")
            if self.qualification.local_1612 is not None:
                previous_metadata, previous_state, _ = _select_metadata(root / ".gitnexus", deadline=deadline)
                if previous_state not in (None, "missing"):
                    raise GitNexusAdapterError("local 1.6.12 refresh refuses invalid existing metadata")
                if previous_metadata is not None and previous_metadata["lastCommit"] == expected_head:
                    raise GitNexusAdapterError("local 1.6.12 same-HEAD refresh is not qualified")
            verify_qualification(self.qualification, deadline=deadline)
            preflight_repository = collect_repository_state(
                root,
                canonical_repository_id=repository.canonical_repository_id,
                expected_remote=repository.canonical_remote,
                principal_scope=repository.identity["principal_scope"],
                path_scope=repository.identity["path_scope"],
                deadline=deadline,
                git_executable=self.git_executable,
            )
            preflight_snapshot = collect_tracked_snapshot(
                root, deadline=deadline, git_executable=self.git_executable
            )
            preflight_git_control_digest = _git_control_snapshot(
                root,
                require_exclusion=True,
                deadline=deadline,
                git_executable=self.git_executable,
            )
            if (
                not _repository_state_matches(repository, preflight_repository)
                or preflight_snapshot != before
                or preflight_git_control_digest != before_git_control_digest
            ):
                raise GitNexusAdapterError(
                    "refresh repository state changed during preflight"
                )
            lifecycle = _lifecycle_context(repository, _checkout_kind(root))
            alias = _index_alias(repository, before, lifecycle)
            argv = [
                *_qualified_argv(
                    self.qualification.executable,
                    self.qualification.runtime_executable,
                    *_index_analyze_arguments(self.qualification, alias, root),
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
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_OPTIONAL_LOCKS": "0",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": "core.fsmonitor",
                "GIT_CONFIG_VALUE_0": "false",
                "GIT_CONFIG_KEY_1": "core.hooksPath",
                "GIT_CONFIG_VALUE_1": "/dev/null",
                "GIT_CONFIG_KEY_2": "core.untrackedCache",
                "GIT_CONFIG_VALUE_2": "false",
            }
            process_failure: str | None = None
            _recheck_isolated_home_identity(
                isolated_home_identity, isolated_home_descriptor
            )
            _require_empty_isolated_home_descriptor(isolated_home_descriptor)
            if self.qualification.local_1612 is not None:
                _require_local_1612_default_config(root, deadline=deadline)
                os.mkdir("identity-cache", mode=0o700, dir_fd=isolated_home_descriptor)
                process_environment["GITNEXUS_ANALYZER_IDENTITY_CACHE_DIR"] = str(isolated_home / "identity-cache")
            try:
                process = self.runner(
                    argv,
                    cwd=root,
                    env=process_environment,
                    timeout=_remaining_timeout(deadline) * 0.7,
                )
            except subprocess.TimeoutExpired:
                process_failure = "refresh-timeout"
                process = None
            except ProcessBoundaryError as exc:
                process_failure = (
                    "refresh-timeout"
                    if exc.error_code == "process-timeout"
                    else f"refresh-{exc.error_code}"
                )
                process = None
            try:
                _recheck_isolated_home_identity(
                    isolated_home_identity, isolated_home_descriptor
                )
                after_repository = collect_repository_state(
                    root,
                    canonical_repository_id=repository.canonical_repository_id,
                    expected_remote=repository.canonical_remote,
                    principal_scope=repository.identity["principal_scope"],
                    path_scope=repository.identity["path_scope"],
                    deadline=deadline,
                    git_executable=self.git_executable,
                )
                after = collect_tracked_snapshot(
                    root, deadline=deadline, git_executable=self.git_executable
                )
                after_git_control_digest = _git_control_snapshot(
                    root,
                    require_exclusion=True,
                    deadline=deadline,
                    git_executable=self.git_executable,
                )
                _validate_derived_index_tree(root, deadline=deadline)
                verify_qualification(self.qualification, deadline=deadline)
            except ProbeDeadlineError:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "probe-deadline-expired", repository,
                    before, None, argv,
                    before_git_control_digest=before_git_control_digest,
                )
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
                or after.worktree_state_digest != before.worktree_state_digest
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
            metadata = _assess_metadata_before_identity_write(
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
            assert metadata.metadata_digest is not None and metadata.metadata is not None
            if self.qualification.local_1612 is not None:
                try:
                    registry = json.loads(_read_regular_at(isolated_home_descriptor, "registry.json", maximum_bytes=MAX_METADATA_BYTES, deadline=deadline))
                    expected_registry = {"name": alias, "path": str(root), **{key: metadata.metadata[key] for key in ("storagePath", "indexedAt", "lastCommit", "remoteUrl", "stats", "branch")}}
                    if registry != [expected_registry]:
                        raise GitNexusAdapterError("isolated registry does not bind this analysis")
                except ProbeDeadlineError:
                    raise
                except (ValueError, RecursionError, OSError, GitNexusAdapterError):
                    return self._receipt("failed", "post-refresh-registry-invalid", repository, before, after, argv, metadata, before_git_control_digest, after_git_control_digest)
            try:
                observed_at = dt.datetime.now(dt.timezone.utc).isoformat().replace(
                    "+00:00", "Z"
                )
                index_identity = build_index_identity(
                    after_repository,
                    after,
                    self.qualification,
                    metadata_digest=metadata.metadata_digest,
                    indexed_at=metadata.metadata["indexedAt"],
                    observed_at=observed_at,
                    deadline=deadline,
                )
                _write_index_identity(
                    root / ".gitnexus", index_identity, deadline=deadline
                )
            except ProbeDeadlineError:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "probe-deadline-expired", repository,
                    before, after, argv, metadata,
                    before_git_control_digest, after_git_control_digest,
                )
            except (GitNexusAdapterError, OSError, KeyError, TypeError):
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "post-refresh-index-identity-invalid", repository,
                    before, after, argv, metadata, before_git_control_digest,
                    after_git_control_digest,
                )
            try:
                _validate_derived_index_tree(root, deadline=deadline)
                final_repository = collect_repository_state(
                    root,
                    canonical_repository_id=repository.canonical_repository_id,
                    expected_remote=repository.canonical_remote,
                    principal_scope=repository.identity["principal_scope"],
                    path_scope=repository.identity["path_scope"],
                    deadline=deadline,
                    git_executable=self.git_executable,
                )
                final_snapshot = collect_tracked_snapshot(
                    root, deadline=deadline, git_executable=self.git_executable
                )
                final_git_control_digest = _git_control_snapshot(
                    root,
                    require_exclusion=True,
                    deadline=deadline,
                    git_executable=self.git_executable,
                )
                _validate_derived_index_tree(root, deadline=deadline)
                verify_qualification(self.qualification, deadline=deadline)
            except ProbeDeadlineError:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "probe-deadline-expired", repository,
                    before, None, argv, metadata,
                    before_git_control_digest, after_git_control_digest,
                )
            except (GitNexusAdapterError, OSError):
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "postcondition-unknown:final-index-identity-check",
                    repository, before, None, argv, metadata,
                    before_git_control_digest, after_git_control_digest,
                )
            if (
                not _repository_state_matches(after_repository, final_repository)
                or final_snapshot != after
                or final_git_control_digest != after_git_control_digest
            ):
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "unexpected-repository-mutation", repository,
                    before, final_snapshot, argv, metadata,
                    before_git_control_digest, final_git_control_digest,
                )
            after_repository = final_repository
            after = final_snapshot
            after_git_control_digest = final_git_control_digest
            try:
                metadata = assess_metadata(
                    after_repository, after, self.qualification, deadline=deadline
                )
            except ProbeDeadlineError:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "probe-deadline-expired", repository,
                    before, after, argv, metadata,
                    before_git_control_digest, after_git_control_digest,
                )
            except (GitNexusAdapterError, OSError, KeyError, TypeError):
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", "post-refresh-index-identity-invalid", repository,
                    before, after, argv, metadata, before_git_control_digest,
                    after_git_control_digest,
                )
            if metadata.state != "fresh" or metadata.index_identity is None:
                self.auto_capability_enabled = False
                return self._receipt(
                    "failed", f"post-refresh-metadata-{metadata.state}", repository,
                    before, after, argv, metadata, before_git_control_digest,
                    after_git_control_digest,
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
            "before_worktree_state_digest": before.worktree_state_digest,
            "after_tracked_state_digest": after.tracked_state_digest if after else None,
            "after_protected_state_digest": after.protected_state_digest if after else None,
            "after_complete_status_digest": after.complete_status_digest if after else None,
            "after_worktree_state_digest": after.worktree_state_digest if after else None,
            "before_git_control_digest": before_git_control_digest,
            "after_git_control_digest": after_git_control_digest,
            "indexed_revision": metadata.indexed_revision if metadata else None,
            "index_identity_digest": (
                metadata.index_identity["index_identity_digest"]
                if metadata and metadata.index_identity else None
            ),
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
    parser.add_argument("--executable", help="Required absolute machine-local GitNexus executable path.")
    parser.add_argument(
        "--allow-symlink",
        action="store_true",
        help="Explicitly permit one discovered symlink whose resolved target is qualified.",
    )
    parser.add_argument(
        "--node-executable",
        help="Required absolute Node executable path when the GitNexus entry uses /usr/bin/env node.",
    )
    parser.add_argument(
        "--allow-node-symlink",
        action="store_true",
        help="Explicitly permit a Node executable symlink whose resolved target is qualified.",
    )
    parser.add_argument(
        "--package-root",
        help="Required canonical machine-local package root containing the GitNexus entry.",
    )
    parser.add_argument(
        "--accepted-executable-sha256",
        help="Caller-owned accepted digest for the selected GitNexus entry.",
    )
    parser.add_argument(
        "--accepted-package-sha256",
        help="Caller-owned accepted digest for the complete package tree.",
    )
    parser.add_argument(
        "--accepted-runtime-sha256",
        help="Caller-owned accepted digest for the bound interpreter when applicable.",
    )


def _add_repository_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, help="Exact canonical Git worktree root.")
    parser.add_argument(
        "--git-executable",
        help="Optional absolute trusted Git executable; defaults to the OS default search path.",
    )
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


def _qualification_from_arguments(
    arguments: argparse.Namespace,
    *,
    deadline: float | None = None,
) -> ExecutableQualification:
    qualify = qualify_executable if deadline is None else _qualify_executable_until
    deadline_arguments = {} if deadline is None else {"deadline": deadline}
    return qualify(
        arguments.executable,
        **deadline_arguments,
        allow_symlink=arguments.allow_symlink,
        runtime_path=arguments.node_executable,
        allow_runtime_symlink=arguments.allow_node_symlink,
        package_root=arguments.package_root,
        accepted_executable_sha256=arguments.accepted_executable_sha256,
        accepted_package_sha256=arguments.accepted_package_sha256,
        accepted_runtime_sha256=arguments.accepted_runtime_sha256,
    )


def _repository_from_arguments(
    arguments: argparse.Namespace, *, deadline: float | None = None
) -> RepositoryState:
    return collect_repository_state(
        arguments.repo_root,
        canonical_repository_id=arguments.repository_id,
        expected_remote=arguments.expected_remote,
        deadline=deadline,
        git_executable=arguments.git_executable,
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
            refresh_deadline = (
                _refresh_deadline(arguments.timeout_seconds)
                if arguments.command == "refresh"
                else None
            )
            qualification = _qualification_from_arguments(
                arguments, deadline=refresh_deadline
            )
            _check_deadline(refresh_deadline)
            if arguments.command == "qualify":
                result = {
                    "kind": "gitnexus-qualification-status",
                    "status": "qualified",
                    "version": qualification.version,
                    "symlink_policy": qualification.symlink_policy,
                    "runtime_symlink_policy": qualification.runtime_symlink_policy,
                    "runtime_bound": qualification.runtime_executable is not None,
                    "analyze_flags": list(qualification.analyze_flags),
                    "qualification_fingerprint": qualification.fingerprint,
                    "trusted_provenance_digest": qualification.trusted_provenance_digest,
                }
                exit_status = 0
            else:
                repository = _repository_from_arguments(
                    arguments, deadline=refresh_deadline
                )
                snapshot = collect_tracked_snapshot(
                    repository.root,
                    deadline=refresh_deadline,
                    git_executable=arguments.git_executable,
                )
                if arguments.command == "status":
                    metadata = assess_metadata(
                        repository, snapshot, qualification,
                        deadline=refresh_deadline,
                    )
                    result = {
                        "kind": "gitnexus-adapter-status",
                        "status": metadata.state,
                        "reason": metadata.reason,
                        "repository_identity_digest": repository.identity["repository_identity_digest"],
                        "head": repository.head,
                        "branch": repository.branch,
                        "indexed_revision": metadata.indexed_revision,
                        "metadata_digest": metadata.metadata_digest,
                        "index_identity_digest": (
                            metadata.index_identity["index_identity_digest"]
                            if metadata.index_identity else None
                        ),
                        "index_lifecycle": (
                            metadata.index_identity["lifecycle"]
                            if metadata.index_identity else None
                        ),
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
                        git_executable=arguments.git_executable,
                    )
                    refreshed = controller.refresh(
                        repository,
                        expected_head=arguments.expected_head,
                        explicit_opt_in=arguments.confirm_explicit_refresh,
                        deadline=refresh_deadline,
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
