"""Fail-closed Git source-revision relations for loop ledgers."""

from __future__ import annotations

import hashlib
import os
import pathlib
import re
import selectors
import signal
import stat
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Literal


SourceHeadRelation = Literal["exact", "ancestor", "mismatch", "unknown"]
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_GIT_PROBE_TIMEOUT_SECONDS = 10.0
_GIT_PROBE_OUTPUT_LIMIT_BYTES = 64 * 1024
_SAFE_LOCALE_ENVIRONMENT = frozenset({"LANG", "LC_ALL", "LC_CTYPE"})


class _GitExecutablePathError(OSError):
    """Specific executable-path policy rejection preserved for callers/tests."""


@dataclass(frozen=True)
class GitMarkerEvidence:
    git_dir: pathlib.Path
    marker_identity: tuple[int, ...]
    git_dir_identity: tuple[int, int, int]
    binding_sha256: str


def _stat_identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns)


def _directory_identity(info: os.stat_result) -> tuple[int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode)


def sanitized_git_environment() -> dict[str, str]:
    """Return a minimal Git environment without executable-origin selectors."""

    environment = {
        key: value
        for key, value in os.environ.items()
        if key in _SAFE_LOCALE_ENVIRONMENT and "\x00" not in value
    }
    environment.update(
        {
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return environment


def _require_no_symlink_components(path: pathlib.Path) -> os.stat_result:
    current = pathlib.Path(path.anchor)
    try:
        info = current.lstat()
        for part in path.parts[1:]:
            current /= part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise _GitExecutablePathError(
                    "Git executable path must not contain symlinks"
                )
    except _GitExecutablePathError:
        raise
    except OSError as exc:
        raise OSError("Git executable cannot be resolved safely") from exc
    return info


def _resolved_git_executable(
    configured_path: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Bind Git from an explicit override or the OS trusted default path."""

    if configured_path is not None:
        return _validated_git_executable_candidate(pathlib.Path(os.fspath(configured_path)))

    for directory_text in os.defpath.split(os.pathsep):
        if not directory_text:
            continue
        try:
            return _validated_git_executable_candidate(
                pathlib.Path(directory_text) / "git"
            )
        except OSError:
            continue
    raise OSError(
        "Git executable was not found safely in the OS default path; "
        "a trusted caller must supply an explicit absolute path"
    )


def _validated_git_executable_candidate(candidate: pathlib.Path) -> pathlib.Path:
    """Validate one absolute Git candidate without following path symlinks."""

    if not candidate.is_absolute():
        raise OSError("Git executable path must be absolute")
    lexical = pathlib.Path(os.path.abspath(candidate))
    try:
        link_info = _require_no_symlink_components(lexical)
        resolved = lexical.resolve(strict=True)
        info = resolved.stat()
    except _GitExecutablePathError:
        raise
    except OSError as exc:
        raise OSError("Git executable cannot be resolved safely") from exc
    if stat.S_ISLNK(link_info.st_mode) or resolved != lexical:
        raise OSError("Git executable must be a canonical non-symlink path")
    if not stat.S_ISREG(info.st_mode) or not os.access(resolved, os.X_OK):
        raise OSError("Git executable must be an executable regular file")
    try:
        with resolved.open("rb") as stream:
            if stream.read(2) == b"#!":
                raise OSError(
                    "Git script wrappers are unsupported; use a native Git executable"
                )
    except OSError:
        raise
    return resolved


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError as exc:
        if process.poll() is None:
            process.kill()
        raise OSError("Git probe process group cleanup failed") from exc
    if process.poll() is None:
        try:
            process.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()


def run_git(
    repo_root: pathlib.Path,
    arguments: list[str] | tuple[str, ...],
    *,
    check: bool = True,
    environment: dict[str, str] | None = None,
    git_executable: str | os.PathLike[str] | None = None,
    timeout_seconds: float = _GIT_PROBE_TIMEOUT_SECONDS,
    output_limit_bytes: int = _GIT_PROBE_OUTPUT_LIMIT_BYTES,
) -> subprocess.CompletedProcess[str]:
    """Run a bounded, noninteractive Git probe without replacement semantics."""

    if timeout_seconds <= 0 or output_limit_bytes <= 0:
        raise ValueError("Git probe bounds must be positive")
    argv = [
        str(_resolved_git_executable(git_executable)),
        "--no-replace-objects",
        "-C",
        str(pathlib.Path(repo_root)),
        *arguments,
    ]
    if any(not isinstance(item, str) or "\x00" in item for item in argv):
        raise ValueError("Git probe arguments must be safe strings")
    probe_environment = sanitized_git_environment()
    if environment is not None:
        allowed = set(probe_environment) | _SAFE_LOCALE_ENVIRONMENT | {
            "GIT_CONFIG_COUNT",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_NOSYSTEM",
            "GIT_GRAFT_FILE",
            "GIT_NO_LAZY_FETCH",
            "GIT_OPTIONAL_LOCKS",
            "GIT_TERMINAL_PROMPT",
            "GIT_WORK_TREE",
        }
        unknown = sorted(set(environment) - allowed)
        if unknown:
            raise ValueError("Git probe environment contains unsupported keys")
        fixed = {
            key: value
            for key, value in probe_environment.items()
            if key not in _SAFE_LOCALE_ENVIRONMENT
        }
        for key, value in fixed.items():
            if key in environment and environment[key] != value:
                raise ValueError("Git probe environment cannot override fixed controls")
        for key in _SAFE_LOCALE_ENVIRONMENT:
            value = environment.get(key)
            if value is not None:
                if not isinstance(value, str) or "\x00" in value:
                    raise ValueError("Git probe locale environment is invalid")
                probe_environment[key] = value
        work_tree = environment.get("GIT_WORK_TREE")
        if work_tree is not None:
            try:
                configured_work_tree = pathlib.Path(work_tree).resolve(strict=True)
                expected_work_tree = pathlib.Path(repo_root).resolve(strict=True)
            except OSError as exc:
                raise ValueError("Git worktree environment cannot be resolved") from exc
            if configured_work_tree != expected_work_tree:
                raise ValueError("Git worktree environment must match the target root")
            probe_environment["GIT_WORK_TREE"] = str(configured_work_tree)
    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    deadline = time.monotonic() + timeout_seconds
    group_cleaned = False
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=probe_environment,
            start_new_session=True,
        )
        assert process.stdout is not None and process.stderr is not None
        os.set_blocking(process.stdout.fileno(), False)
        os.set_blocking(process.stderr.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ, stdout)
        selector.register(process.stderr, selectors.EVENT_READ, stderr)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise OSError("Git probe exceeded its timeout")
            events = selector.select(min(remaining, 0.1))
            if not events and process.poll() is not None:
                events = [
                    (key, selectors.EVENT_READ)
                    for key in selector.get_map().values()
                ]
            for key, _ in events:
                try:
                    chunk = os.read(key.fd, 8192)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                key.data.extend(chunk)
                if len(stdout) + len(stderr) > output_limit_bytes:
                    raise OSError("Git probe exceeded its output limit")
            if process.poll() is not None and selector.get_map() and not group_cleaned:
                _terminate_process_group(process)
                group_cleaned = True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise OSError("Git probe exceeded its timeout")
        returncode = process.wait(timeout=remaining)
        if not group_cleaned:
            _terminate_process_group(process)
            group_cleaned = True
    except subprocess.TimeoutExpired as exc:
        if process is not None and not group_cleaned:
            _terminate_process_group(process)
            group_cleaned = True
        raise OSError("Git probe exceeded its timeout") from exc
    except BaseException:
        if process is not None and not group_cleaned:
            _terminate_process_group(process)
            group_cleaned = True
        raise
    finally:
        selector.close()
        if process is not None:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
    try:
        stdout_text = bytes(stdout).decode("utf-8")
        stderr_text = bytes(stderr).decode("utf-8")
    except UnicodeError as exc:
        raise OSError("Git probe output was not valid UTF-8") from exc
    completed = subprocess.CompletedProcess(argv, returncode, stdout_text, stderr_text)
    if check and returncode:
        raise subprocess.CalledProcessError(
            returncode,
            argv,
            output=stdout_text,
            stderr=stderr_text,
        )
    return completed


def _read_bounded_single_line(
    path: pathlib.Path | str,
    label: str,
    *,
    directory_fd: int | None = None,
    expected_identity: tuple[int, int, int, int, int] | None = None,
) -> tuple[str, tuple[int, int, int, int, int]]:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise OSError(f"{label} requires no-follow nonblocking file support")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | os.O_NOFOLLOW
            | os.O_NONBLOCK,
            dir_fd=directory_fd,
        )
        info = os.fstat(descriptor)
        opened_identity = _stat_identity(info)
        if expected_identity is not None and opened_identity != expected_identity:
            raise OSError(f"{label} changed before it was opened")
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            raise OSError(f"{label} must be a bounded regular non-symlink file")
        chunks: list[bytes] = []
        remaining = 4097
        while remaining:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if _stat_identity(os.fstat(descriptor)) != opened_identity:
            raise OSError(f"{label} changed while it was read")
    except OSError as exc:
        raise OSError(f"{label} cannot be read safely") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(payload) > 4096:
        raise OSError(f"{label} exceeds the bounded size")
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise OSError(f"{label} cannot be read as UTF-8") from exc
    lines = text.splitlines()
    if len(lines) != 1 or not lines[0] or "\x00" in lines[0]:
        raise OSError(f"{label} must contain exactly one safe line")
    return lines[0], opened_identity


def validated_git_marker(repo_root: pathlib.Path) -> GitMarkerEvidence:
    """Validate a local Git marker and return its expected admin directory."""

    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise OSError("Git marker validation requires POSIX no-follow directory support")
    root = repo_root.resolve(strict=True)
    marker = root / ".git"
    try:
        marker_info = marker.lstat()
    except OSError as exc:
        raise OSError("Git root requires a local .git marker") from exc
    if stat.S_ISLNK(marker_info.st_mode):
        raise OSError("Git root .git marker must not be a symlink")
    if stat.S_ISDIR(marker_info.st_mode):
        descriptor = os.open(marker, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            opened = os.fstat(descriptor)
            if _directory_identity(opened) != _directory_identity(marker_info):
                raise OSError("Git root .git directory changed while it was opened")
            git_dir = marker.resolve(strict=True)
            identity = _directory_identity(opened)
            if (
                _directory_identity(os.fstat(descriptor)) != identity
                or _directory_identity(marker.lstat()) != _directory_identity(marker_info)
            ):
                raise OSError("Git root .git directory changed during validation")
            return GitMarkerEvidence(git_dir, identity, identity, "")
        finally:
            os.close(descriptor)
    if not stat.S_ISREG(marker_info.st_mode):
        raise OSError("Git root .git marker must be a directory or regular file")

    pointer, marker_opened_identity = _read_bounded_single_line(
        marker,
        "Git root .git marker",
        expected_identity=_stat_identity(marker_info),
    )
    prefix = "gitdir: "
    if not pointer.startswith(prefix) or not pointer[len(prefix) :]:
        raise OSError("Git root .git marker has an invalid gitdir pointer")
    target = pathlib.Path(pointer[len(prefix) :])
    target = target if target.is_absolute() else root / target
    target_lexical = pathlib.Path(os.path.abspath(target))
    try:
        target_info = target_lexical.lstat()
        expected_git_dir = target_lexical.resolve(strict=True)
    except OSError as exc:
        raise OSError("Git root gitdir pointer cannot be resolved") from exc
    if (
        target_lexical != expected_git_dir
        or stat.S_ISLNK(target_info.st_mode)
        or not stat.S_ISDIR(target_info.st_mode)
    ):
        raise OSError("Git root gitdir pointer must name a real directory")

    target_fd = os.open(
        target_lexical, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    )
    try:
        opened_target = os.fstat(target_fd)
        if _directory_identity(opened_target) != _directory_identity(target_info):
            raise OSError("Git worktree admin directory changed while it was opened")
        back_info = os.stat("gitdir", dir_fd=target_fd, follow_symlinks=False)
        back_pointer, _ = _read_bounded_single_line(
            "gitdir",
            "Git worktree back-reference",
            directory_fd=target_fd,
            expected_identity=_stat_identity(back_info),
        )
        if _directory_identity(os.fstat(target_fd)) != _directory_identity(opened_target):
            raise OSError("Git worktree admin directory changed during validation")
    finally:
        os.close(target_fd)
    back_path = pathlib.Path(back_pointer)
    back_path = back_path if back_path.is_absolute() else expected_git_dir / back_path
    back_lexical = pathlib.Path(os.path.abspath(back_path))
    try:
        if (
            back_lexical != back_lexical.resolve(strict=True)
            or back_lexical.resolve(strict=True) != marker.resolve(strict=True)
        ):
            raise OSError("Git worktree back-reference does not bind the selected root")
    except OSError as exc:
        raise OSError("Git worktree back-reference cannot be verified") from exc
    try:
        marker_after = marker.lstat()
        target_after = target_lexical.lstat()
    except OSError as exc:
        raise OSError("Git marker binding changed during validation") from exc
    if (
        _stat_identity(marker_after) != _stat_identity(marker_info)
        or _directory_identity(target_after) != _directory_identity(target_info)
    ):
        raise OSError("Git marker binding changed during validation")
    binding_sha256 = hashlib.sha256(
        (pointer + "\x00" + back_pointer).encode("utf-8")
    ).hexdigest()
    return GitMarkerEvidence(
        expected_git_dir,
        marker_opened_identity,
        _directory_identity(opened_target),
        binding_sha256,
    )


def verified_git_root(
    repo_root: pathlib.Path,
    *,
    git_executable: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Return an exact checkout root without trusting ``core.worktree``.

    Git's ``--show-toplevel`` follows repository-local ``core.worktree``.  An
    enclosing repository can therefore name an arbitrary nested directory as
    its worktree.  Require a real local ``.git`` marker first, then override
    the worktree only for the verification probe.
    """

    lexical = pathlib.Path(os.path.abspath(repo_root.expanduser()))
    try:
        resolved = lexical.resolve(strict=True)
        root_info = lexical.lstat()
    except OSError as exc:
        raise OSError("Git root cannot be resolved") from exc
    if (
        stat.S_ISLNK(root_info.st_mode)
        or not stat.S_ISDIR(root_info.st_mode)
    ):
        raise OSError("Git root requires a real non-symlink directory")
    expected_marker = validated_git_marker(resolved)
    expected_git_dir = expected_marker.git_dir
    environment = sanitized_git_environment()
    environment["GIT_WORK_TREE"] = str(resolved)
    result = run_git(
        resolved,
        ["rev-parse", "--show-toplevel"],
        environment=environment,
        git_executable=git_executable,
    )
    reported = pathlib.Path(result.stdout.strip()).resolve(strict=True)
    if reported != resolved:
        raise subprocess.CalledProcessError(
            1, result.args, output=result.stdout, stderr=result.stderr
        )
    git_dir_result = run_git(
        resolved,
        ["rev-parse", "--absolute-git-dir"],
        environment=environment,
        git_executable=git_executable,
    )
    if pathlib.Path(git_dir_result.stdout.strip()).resolve(strict=True) != expected_git_dir:
        raise subprocess.CalledProcessError(
            1, git_dir_result.args, output=git_dir_result.stdout, stderr=git_dir_result.stderr
        )
    if validated_git_marker(resolved) != expected_marker:
        raise OSError("Git root marker changed during verification")
    return resolved


def discover_git_root(
    start: pathlib.Path,
    *,
    git_executable: str | os.PathLike[str] | None = None,
) -> pathlib.Path:
    """Discover the nearest checkout root by a local, non-symlink marker."""

    try:
        resolved = start.expanduser().resolve(strict=True)
    except OSError as exc:
        raise OSError("Git discovery start cannot be resolved") from exc
    if resolved.is_file():
        resolved = resolved.parent
    for candidate in (resolved, *resolved.parents):
        marker = candidate / ".git"
        try:
            marker.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise OSError("Git root marker cannot be inspected") from exc
        return verified_git_root(candidate, git_executable=git_executable)
    raise OSError("no local Git root marker was found")


def verified_git_head(
    repo_root: pathlib.Path,
    *,
    git_executable: str | os.PathLike[str] | None = None,
) -> str:
    """Return the exact current commit object without replacement semantics."""

    root = verified_git_root(repo_root, git_executable=git_executable)
    environment = sanitized_git_environment()
    environment["GIT_WORK_TREE"] = str(root)
    result = run_git(
        root,
        ["rev-parse", "--verify", "HEAD^{commit}"],
        environment=environment,
        git_executable=git_executable,
    )
    head = result.stdout.strip()
    if not _COMMIT_SHA.fullmatch(head):
        raise subprocess.CalledProcessError(
            1, result.args, output=result.stdout, stderr=result.stderr
        )
    return head


def _is_terminal_completed_ledger(document: dict[str, Any]) -> bool:
    current_loop = document.get("current_loop")
    events = document.get("events")
    return bool(
        isinstance(current_loop, dict)
        and current_loop.get("lifecycle") == "complete"
        and isinstance(events, list)
        and events
        and isinstance(events[-1], dict)
        and events[-1].get("type") == "objective_completed"
    )


def source_branch_compatible(
    document: dict[str, Any], current_branch: str, head_relation: SourceHeadRelation
) -> bool:
    """Return whether a named checkout can consume the ledger source branch.

    Active ledgers remain bound to the exact branch. A terminal completed
    ledger may be audited from another named branch only when its immutable
    source commit is a verified strict ancestor of current HEAD. Keeping exact
    commits branch-bound prevents an unrelated repository with identical commit
    bytes from being accepted. Detached checkouts remain rejected.
    """

    if not current_branch:
        return False
    ledger = document.get("ledger")
    source = ledger.get("source_revision") if isinstance(ledger, dict) else None
    source_branch = source.get("branch") if isinstance(source, dict) else None
    if not isinstance(source_branch, str) or not source_branch:
        return False
    if source_branch == current_branch:
        return True
    return _is_terminal_completed_ledger(document) and head_relation == "ancestor"


def source_head_relation(
    repo_root: pathlib.Path,
    document: dict[str, Any],
    current_head: str,
    *,
    git_executable: str | os.PathLike[str] | None = None,
    allow_active_ancestor: bool = False,
) -> SourceHeadRelation:
    """Relate a ledger's immutable source anchor to the current Git HEAD.

    Active ledgers require an exact HEAD. A terminal, objectively completed
    ledger may be committed later and therefore accepts only a verified
    ancestor source anchor. Unknown revisions and Git failures remain closed.
    """

    ledger = document.get("ledger")
    source = ledger.get("source_revision") if isinstance(ledger, dict) else None
    source_head = source.get("head_sha") if isinstance(source, dict) else None
    if not (
        isinstance(source_head, str)
        and _COMMIT_SHA.fullmatch(source_head)
        and isinstance(current_head, str)
        and _COMMIT_SHA.fullmatch(current_head)
    ):
        return "unknown"
    try:
        verified_root = verified_git_root(repo_root, git_executable=git_executable)
        verified_head = verified_git_head(
            verified_root, git_executable=git_executable
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if verified_head != current_head:
        return "unknown"
    if source_head == current_head:
        return "exact"
    if not allow_active_ancestor and not _is_terminal_completed_ledger(document):
        return "mismatch"
    try:
        result = run_git(
            verified_root,
            ["merge-base", "--is-ancestor", source_head, current_head],
            check=False,
            environment={
                **sanitized_git_environment(),
                "GIT_WORK_TREE": str(verified_root),
            },
            git_executable=git_executable,
        )
    except OSError:
        return "unknown"
    if result.returncode == 0:
        return "ancestor"
    if result.returncode == 1:
        return "mismatch"
    return "unknown"
