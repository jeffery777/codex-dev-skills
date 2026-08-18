#!/usr/bin/env python3
"""Inspect and validate Loop Engineering state without implicit writes."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import loop_core  # noqa: E402
import loop_yaml  # noqa: E402
import git_source  # noqa: E402
import profile_preflight  # noqa: E402
import agent_routing  # noqa: E402

CANONICAL_PROFILE_REGISTRY = (
    HERE.parent / "references" / "agent-profile-registry.json"
).resolve()


def render(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def _trusted_current_time() -> dt.datetime:
    """Return caller-owned current time for live write-boundary checks."""
    return dt.datetime.now(dt.timezone.utc)


def _manifest_path(
    ledger_path: pathlib.Path,
    document: dict[str, Any],
    explicit: pathlib.Path | None,
    repo_root: pathlib.Path | None = None,
) -> pathlib.Path | None:
    if explicit is not None:
        return explicit
    reference = (document.get("ledger") or {}).get("task_manifest")
    if not isinstance(reference, str) or not reference or reference.startswith("<"):
        return None
    candidate = pathlib.Path(reference)
    candidates = (
        [candidate]
        if candidate.is_absolute()
        else [
            ledger_path.parent / candidate,
            *(([repo_root / candidate]) if repo_root is not None else []),
            pathlib.Path.cwd() / candidate,
        ]
    )
    return next((item for item in candidates if item.is_file()), candidates[0])


def _reference_path(
    ledger_path: pathlib.Path, reference: str, repo_root: pathlib.Path | None = None
) -> pathlib.Path:
    candidate = pathlib.Path(reference)
    candidates = (
        [candidate]
        if candidate.is_absolute()
        else [
            ledger_path.parent / candidate,
            *(([repo_root / candidate]) if repo_root is not None else []),
            pathlib.Path.cwd() / candidate,
        ]
    )
    return next((item for item in candidates if item.is_file()), candidates[0])


def _verify_digest(path: pathlib.Path, expected: Any, label: str) -> None:
    if not path.is_file():
        raise loop_yaml.LedgerValidationError(f"{label} is missing: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected != actual:
        raise loop_yaml.LedgerValidationError(
            f"{label} digest mismatch: expected {expected!r}, got {actual}"
        )


def _verify_git_source(
    ledger_path: pathlib.Path,
    document: dict[str, Any],
    explicit_repo_root: pathlib.Path | None,
) -> pathlib.Path:
    start = explicit_repo_root or ledger_path.parent
    try:
        resolved_root = (
            git_source.verified_git_root(explicit_repo_root)
            if explicit_repo_root is not None
            else git_source.discover_git_root(start)
        )
        if explicit_repo_root is not None and resolved_root != explicit_repo_root.resolve():
            raise loop_yaml.LedgerValidationError(
                "repo root must be the exact target Git repository root"
            )
        git_environment = git_source.sanitized_git_environment()
        git_environment["GIT_WORK_TREE"] = str(resolved_root)
        head = git_source.verified_git_head(resolved_root)
        branch = git_source.run_git(
            resolved_root,
            ["branch", "--show-current"],
            environment=git_environment,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            "could not verify git source revision; pass --repo-root for the target repository"
        ) from exc
    source = document["ledger"]["source_revision"]
    head_relation = git_source.source_head_relation(resolved_root, document, head)
    if not git_source.source_branch_compatible(document, branch, head_relation):
        raise loop_yaml.LedgerValidationError(
            f"git branch mismatch: expected {source.get('branch')!r}, got {branch!r}"
        )
    if head_relation not in {"exact", "ancestor"}:
        raise loop_yaml.LedgerValidationError(
            f"git HEAD mismatch: expected {source.get('head_sha')!r}, got {head}"
        )
    return resolved_root


def _verified_rebind_source(
    ledger_path: pathlib.Path,
    document: dict[str, Any],
    explicit_repo_root: pathlib.Path | None,
    *,
    expected_ledger_bytes: bytes | None = None,
    expected_ledger_binding: tuple[Any, ...] | None = None,
) -> tuple[pathlib.Path, dict[str, str]]:
    """Verify the one safe bridge from a committed active ledger to current HEAD."""

    start = explicit_repo_root or ledger_path.parent
    try:
        root = (
            git_source.verified_git_root(explicit_repo_root)
            if explicit_repo_root is not None
            else git_source.discover_git_root(start)
        )
        if explicit_repo_root is not None and root != explicit_repo_root.resolve():
            raise loop_yaml.LedgerValidationError(
                "repo root must be the exact target Git repository root"
            )
        lexical = pathlib.Path(os.path.abspath(ledger_path))
        resolved = lexical.resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
        if lexical != resolved or not resolved.is_file() or resolved.is_symlink():
            raise loop_yaml.LedgerValidationError(
                "source rebound requires a canonical regular ledger path"
            )
        current = root
        for part in pathlib.PurePosixPath(relative).parts[:-1]:
            current /= part
            if current.is_symlink():
                raise loop_yaml.LedgerValidationError(
                    "source rebound ledger path contains a symlink"
                )
        environment = git_source.sanitized_git_environment()
        environment["GIT_WORK_TREE"] = str(root)
        head = git_source.verified_git_head(root)
        branch = git_source.run_git(
            root, ["branch", "--show-current"], environment=environment
        ).stdout.strip()
        source = document["ledger"]["source_revision"]
        relation = git_source.source_head_relation(
            root,
            document,
            head,
            allow_active_ancestor=True,
        )
        if source.get("branch") != branch or relation != "ancestor":
            raise loop_yaml.LedgerValidationError(
                "source rebound requires a same-branch verified ancestor baseline"
            )
        literal_path = f":(literal){relative}"
        index = git_source.run_git(
            root,
            ["ls-files", "--stage", "-z", "--", literal_path],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout
        tree = git_source.run_git(
            root,
            ["ls-tree", "-z", "HEAD", "--", literal_path],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout
        index_records = [item for item in index.split("\0") if item]
        tree_records = [item for item in tree.split("\0") if item]
        if len(index_records) != 1 or len(tree_records) != 1:
            raise loop_yaml.LedgerValidationError(
                "source rebound requires one tracked ledger blob"
            )
        index_meta, index_path = index_records[0].split("\t", 1)
        tree_meta, tree_path = tree_records[0].split("\t", 1)
        index_mode, index_oid, index_stage = index_meta.split(" ")
        tree_mode, tree_kind, tree_oid = tree_meta.split(" ")
        if (
            index_path != relative
            or tree_path != relative
            or index_stage != "0"
            or tree_kind != "blob"
            or tree_mode not in {"100644", "100755"}
            or (index_mode, index_oid) != (tree_mode, tree_oid)
        ):
            raise loop_yaml.LedgerValidationError(
                "source rebound ledger index and HEAD blob must be identical"
            )
        last_commit = git_source.run_git(
            root,
            ["log", "-1", "--format=%H", "--", literal_path],
            environment=environment,
        ).stdout.strip()
        if last_commit != head:
            raise loop_yaml.LedgerValidationError(
                "source rebound requires the ledger to be checkpointed at current HEAD"
            )
        head_bytes = git_source.run_git(
            root,
            ["cat-file", "blob", tree_oid],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout.encode("utf-8", "surrogateescape")
        expected_bytes = expected_ledger_bytes
        if expected_bytes is None:
            expected_bytes, expected_ledger_binding = _bound_contract_bytes(
                resolved, root, None, "source rebound ledger"
            )
        working_bytes, ledger_binding = _bound_contract_bytes(
            resolved,
            root,
            hashlib.sha256(expected_bytes).hexdigest(),
            "source rebound ledger",
        )
        if (
            expected_ledger_binding is not None
            and ledger_binding[1:] != expected_ledger_binding[1:]
        ):
            raise loop_yaml.LedgerValidationError(
                "source rebound ledger path binding changed"
            )
        expected_mode = 0o755 if tree_mode == "100755" else 0o644
        working_mode = stat.S_IMODE(ledger_binding[3])
        if working_bytes != head_bytes or working_mode != expected_mode:
            raise loop_yaml.LedgerValidationError(
                "source rebound requires working ledger bytes and mode to match HEAD"
            )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, loop_yaml.LedgerValidationError):
            raise
        raise loop_yaml.LedgerValidationError(
            "could not verify source rebound boundary"
        ) from exc
    return root, {"branch": branch, "head_sha": head}


def _repo_contract_path(
    path: pathlib.Path, repo_root: pathlib.Path, label: str
) -> pathlib.Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} must be inside the target repository"
        ) from exc
    return resolved


def _bound_contract_bytes(
    path: pathlib.Path,
    repo_root: pathlib.Path,
    expected_sha256: Any | None,
    label: str,
) -> tuple[bytes, tuple[Any, ...]]:
    """Read one repo-confined contract through an anchored descriptor chain."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        raise loop_yaml.LedgerValidationError(
            f"{label} requires no-follow nonblocking file support"
        )
    lexical_root = pathlib.Path(os.path.abspath(repo_root.expanduser()))
    root = lexical_root.resolve(strict=True)
    lexical = pathlib.Path(os.path.abspath(path.expanduser()))
    try:
        relative = lexical.relative_to(lexical_root)
    except ValueError as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} must be inside the target repository"
        ) from exc
    if not relative.parts:
        raise loop_yaml.LedgerValidationError(f"{label} must be a regular file")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0)
    directory_flags = flags | getattr(os, "O_DIRECTORY", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(root, directory_flags)
        for part in relative.parts[:-1]:
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        artifact = os.open(relative.parts[-1], flags, dir_fd=descriptor)
        os.close(descriptor)
        descriptor = artifact
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise loop_yaml.LedgerValidationError(
                f"{label} must be a single-link regular file"
            )
        if before.st_size > 4 * 1024 * 1024:
            raise loop_yaml.LedgerValidationError(f"{label} exceeds its size bound")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, 4 * 1024 * 1024 + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > 4 * 1024 * 1024:
                raise loop_yaml.LedgerValidationError(f"{label} exceeds its size bound")
        after = os.fstat(descriptor)
        live = os.stat(lexical, follow_symlinks=False)
    except loop_yaml.LedgerValidationError:
        raise
    except OSError as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} cannot be opened through the repository boundary"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    identity = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    if identity != (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ):
        raise loop_yaml.LedgerValidationError(f"{label} changed while it was read")
    if (
        live.st_dev,
        live.st_ino,
        live.st_mode,
        live.st_nlink,
        live.st_size,
        live.st_mtime_ns,
        live.st_ctime_ns,
    ) != identity:
        raise loop_yaml.LedgerValidationError(f"{label} path binding changed while it was read")
    content = b"".join(chunks)
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if expected_sha256 is not None and expected_sha256 != actual_sha256:
        raise loop_yaml.LedgerValidationError(
            f"{label} digest mismatch: expected {expected_sha256!r}, got {actual_sha256}"
        )
    return content, (relative.as_posix(), *identity, actual_sha256)


def _verified_head_contract_bytes(
    path: pathlib.Path,
    repo_root: pathlib.Path,
    expected_sha256: Any,
    label: str,
    *,
    target_head: str,
) -> tuple[bytes, tuple[Any, ...]]:
    """Bind a contract to its working file, index stage 0, and target tree blob."""

    content, binding = _bound_contract_bytes(
        path, repo_root, expected_sha256, label
    )
    relative = binding[0]
    literal_path = f":(literal){relative}"
    environment = git_source.sanitized_git_environment()
    environment["GIT_WORK_TREE"] = str(repo_root)
    try:
        index = git_source.run_git(
            repo_root,
            ["ls-files", "--stage", "-z", "--", literal_path],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout
        tree = git_source.run_git(
            repo_root,
            ["ls-tree", "-z", target_head, "--", literal_path],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} target Git binding cannot be verified"
        ) from exc
    index_records = [item for item in index.split("\0") if item]
    tree_records = [item for item in tree.split("\0") if item]
    if len(index_records) != 1 or len(tree_records) != 1:
        raise loop_yaml.LedgerValidationError(
            f"{label} must be one tracked target-HEAD blob"
        )
    try:
        index_meta, index_path = index_records[0].split("\t", 1)
        tree_meta, tree_path = tree_records[0].split("\t", 1)
        index_mode, index_oid, index_stage = index_meta.split(" ")
        tree_mode, tree_kind, tree_oid = tree_meta.split(" ")
    except ValueError as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} Git metadata is malformed"
        ) from exc
    if (
        index_path != relative
        or tree_path != relative
        or index_stage != "0"
        or tree_kind != "blob"
        or tree_mode not in {"100644", "100755"}
        or (index_mode, index_oid) != (tree_mode, tree_oid)
    ):
        raise loop_yaml.LedgerValidationError(
            f"{label} index and target HEAD blob must be identical"
        )
    try:
        head_bytes = git_source.run_git(
            repo_root,
            ["cat-file", "blob", tree_oid],
            environment=environment,
            output_limit_bytes=4 * 1024 * 1024,
        ).stdout.encode("utf-8", "surrogateescape")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            f"{label} target Git binding cannot be verified"
        ) from exc
    expected_mode = 0o755 if tree_mode == "100755" else 0o644
    working_mode = stat.S_IMODE(binding[3])
    if content != head_bytes or working_mode != expected_mode:
        raise loop_yaml.LedgerValidationError(
            f"{label} working bytes and mode must match target HEAD"
        )
    return content, (*binding, target_head, tree_mode, tree_oid)


def _load_bound_yaml(content: bytes, label: str) -> dict[str, Any]:
    descriptor, name = tempfile.mkstemp(prefix=".loop-contract-", suffix=".yaml")
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
        return loop_yaml.load_yaml(pathlib.Path(name))
    except UnicodeError as exc:
        raise loop_yaml.LedgerValidationError(f"{label} must be UTF-8 YAML") from exc
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _source_rebound_contract(
    ledger_path: pathlib.Path,
    document: dict[str, Any],
    explicit_manifest: pathlib.Path | None,
    repo_root: pathlib.Path,
    *,
    target_head: str,
) -> tuple[dict[str, dict[str, Any]], tuple[tuple[Any, ...], tuple[Any, ...]]]:
    source = document["ledger"]["source_revision"]
    manifest_path = _manifest_path(
        ledger_path, document, explicit_manifest, repo_root
    )
    if manifest_path is None:
        raise loop_yaml.LedgerValidationError("source rebound requires a task manifest")
    manifest_bytes, manifest_binding = _verified_head_contract_bytes(
        manifest_path,
        repo_root,
        source.get("task_manifest_sha256"),
        "task manifest",
        target_head=target_head,
    )
    spec_reference = document["ledger"].get("loop_spec")
    if not isinstance(spec_reference, str) or not spec_reference or spec_reference.startswith("<"):
        raise loop_yaml.LedgerValidationError("source rebound requires a loop spec")
    spec_path = _reference_path(ledger_path, spec_reference, repo_root)
    _, spec_binding = _verified_head_contract_bytes(
        spec_path,
        repo_root,
        source.get("spec_sha256"),
        "loop spec",
        target_head=target_head,
    )
    definitions = loop_yaml.manifest_definitions(
        _load_bound_yaml(manifest_bytes, "task manifest"),
        expected_objective_id=document["ledger"].get("objective_id"),
    )
    return definitions, (manifest_binding, spec_binding)


def _git_revision(
    start: pathlib.Path, *, require_exact_root: bool = False
) -> dict[str, str]:
    try:
        resolved_root = (
            git_source.verified_git_root(start)
            if require_exact_root
            else git_source.discover_git_root(start)
        )
        if require_exact_root and resolved_root != start.resolve():
            raise loop_yaml.LedgerValidationError(
                "repo root must be the exact target Git repository root"
            )
        git_environment = git_source.sanitized_git_environment()
        git_environment["GIT_WORK_TREE"] = str(resolved_root)
        head = git_source.verified_git_head(resolved_root)
        branch = git_source.run_git(
            resolved_root,
            ["branch", "--show-current"],
            environment=git_environment,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            "could not resolve git source revision for bound migration"
        ) from exc
    if not branch:
        raise loop_yaml.LedgerValidationError("bound migration requires a named git branch")
    return {"root": str(resolved_root), "head_sha": head, "branch": branch}


def _definitions(
    ledger_path: pathlib.Path,
    document: dict[str, Any],
    explicit: pathlib.Path | None,
    *,
    require_contract: bool = False,
    repo_root: pathlib.Path | None = None,
) -> dict[str, dict[str, Any]]:
    verified_root = (
        _verify_git_source(ledger_path, document, repo_root)
        if require_contract
        else None
    )
    path = _manifest_path(
        ledger_path,
        document,
        explicit,
        verified_root or repo_root,
    )
    if path is None:
        if require_contract:
            raise loop_yaml.LedgerValidationError("task manifest path is required")
        return {}
    if verified_root is not None:
        path = _repo_contract_path(path, verified_root, "task manifest")
    source = (document.get("ledger") or {}).get("source_revision") or {}
    _verify_digest(path, source.get("task_manifest_sha256"), "task manifest")
    if require_contract:
        spec_reference = (document.get("ledger") or {}).get("loop_spec")
        if not isinstance(spec_reference, str) or not spec_reference or spec_reference.startswith("<"):
            raise loop_yaml.LedgerValidationError("loop spec path is required")
        spec_path = _reference_path(ledger_path, spec_reference, verified_root)
        spec_path = _repo_contract_path(spec_path, verified_root, "loop spec")
        _verify_digest(spec_path, source.get("spec_sha256"), "loop spec")
    return loop_yaml.manifest_definitions(
        loop_yaml.load_yaml(path),
        expected_objective_id=(document.get("ledger") or {}).get("objective_id"),
    )


def _core_evidence(document: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    evidence = task.get("evidence") or {}
    verification = evidence.get("verification") or {}
    review = evidence.get("review") or {}
    acceptance = evidence.get("acceptance") or {}
    artifacts = list(verification.get("artifacts") or []) + list(review.get("artifacts") or [])
    gate_statuses = [gate.get("status") for gate in document.get("human_gates", [])]
    if any(status in {"pending", "blocked"} for status in gate_statuses):
        human_gate = "pending"
    elif any(status == "satisfied" for status in gate_statuses):
        human_gate = "satisfied"
    else:
        human_gate = "not_required"
    blocker = task.get("blocker") or {}
    return {
        "artifact": next((item for item in artifacts if item and not str(item).startswith("<")), None),
        "verification": verification.get("status"),
        "review": copy.deepcopy(review),
        "human_gate": human_gate,
        "acceptance": acceptance.get("artifact")
        if acceptance.get("status") == "satisfied"
        else None,
        "blocker_reason": blocker.get("reason"),
        "blocker_resolved": evidence.get("blocker_resolved"),
        "reopen": evidence.get("reopen"),
    }


def command_validate(path: pathlib.Path) -> int:
    document = loop_yaml.load_yaml(path)
    errors = loop_yaml.validate_ledger(document)
    render({"status": "valid" if not errors else "invalid", "path": str(path), "errors": errors})
    return 0 if not errors else 1


def command_status(path: pathlib.Path) -> int:
    document = loop_yaml.load_yaml(path)
    errors = loop_yaml.validate_ledger(document)
    tasks = document.get("tasks") if isinstance(document.get("tasks"), list) else []
    counts: dict[str, int] = {}
    for task in tasks:
        if isinstance(task, dict):
            status = str(task.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
    render({"status": "ok" if not errors else "invalid", "errors": errors, "task_status_counts": counts})
    return 0 if not errors else 1


def command_audit(
    path: pathlib.Path,
    manifest_path: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
) -> int:
    document = loop_yaml.load_yaml(path)
    definitions = _definitions(
        path, document, manifest_path, require_contract=True, repo_root=repo_root
    )
    errors = loop_yaml.semantic_audit(document, definitions)
    events = document.get("events", []) if isinstance(document.get("events", []), list) else []
    render(
        {
            "status": "valid" if not errors else "invalid",
            "errors": errors,
            "event_count": len(events),
            "protected_history_sha256": loop_core.protected_history_digest(events),
            "protected_history_origin_authenticated": False,
        }
    )
    return 0 if not errors else 1


def command_migrate(
    path: pathlib.Path,
    *,
    spec_path: pathlib.Path | None = None,
    manifest_path: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
) -> int:
    document = loop_yaml.load_yaml(path)
    if (spec_path is None) != (manifest_path is None):
        raise loop_yaml.LedgerValidationError(
            "bound migration requires both --spec and --manifest"
        )
    target_source: dict[str, Any] | None = None
    if spec_path is not None and manifest_path is not None:
        if not spec_path.is_file() or not manifest_path.is_file():
            raise loop_yaml.LedgerValidationError("bound migration spec and manifest must exist")
        git_source = _git_revision(
            repo_root or path.parent, require_exact_root=repo_root is not None
        )
        root_path = pathlib.Path(git_source["root"]).resolve()
        resolved_spec = spec_path.resolve()
        resolved_manifest = manifest_path.resolve()
        try:
            spec_reference = resolved_spec.relative_to(root_path).as_posix()
            manifest_reference = resolved_manifest.relative_to(root_path).as_posix()
        except ValueError as exc:
            raise loop_yaml.LedgerValidationError(
                "bound migration spec and manifest must be inside the target repository"
            ) from exc
        source_v1 = (document.get("ledger") or {}).get("source_revision") or {}
        for field in ("branch", "head_sha"):
            if source_v1.get(field) != git_source[field]:
                raise loop_yaml.LedgerValidationError(
                    f"V1 source {field} does not match target git revision"
                )
        target_source = {
            "branch": git_source["branch"],
            "head_sha": git_source["head_sha"],
            "spec_sha256": hashlib.sha256(resolved_spec.read_bytes()).hexdigest(),
            "task_manifest_sha256": hashlib.sha256(resolved_manifest.read_bytes()).hexdigest(),
        }
    migrated, report = loop_yaml.migrate_v1(
        document,
        target_source_revision=target_source,
        loop_spec=spec_reference if spec_path is not None else None,
        task_manifest=manifest_reference if manifest_path is not None else None,
    )
    if manifest_path is not None:
        definitions = loop_yaml.manifest_definitions(
            loop_yaml.load_yaml(manifest_path),
            expected_objective_id=migrated["ledger"]["objective_id"],
        )
        errors = loop_yaml.semantic_audit(migrated, definitions)
        if errors:
            raise loop_yaml.LedgerValidationError(
                "bound migration is not executable: " + "; ".join(errors)
            )
    render({"report": report, "preview": migrated})
    return 0


def command_hash_event(path: pathlib.Path) -> int:
    event = loop_yaml.load_yaml(path)
    event.pop("event_hash", None)
    event_hash = loop_core.calculate_event_hash(event)
    render({"status": "preview", "event_hash": event_hash, "event": {**event, "event_hash": event_hash}})
    return 0


def command_decide(
    path: pathlib.Path,
    *,
    external_write_authorized: bool = False,
    parent_security_scan_fallback_authorized: bool = False,
    parent_security_report_fallback_authorized: bool = False,
    protected_history_sha256: str | None = None,
) -> int:
    if protected_history_sha256 is None:
        render(
            {
                "status": "rejected",
                "errors": [
                    "decide requires explicit current-session protected history attestation; "
                    "use --protected-history-sha256 none only after verifying there is no protected history"
                ],
            }
        )
        return 1
    case = loop_yaml.load_yaml(path)
    try:
        result = loop_core.evaluate_workflow_case(
            case,
            trusted_authority={
                "external_write_authorized": external_write_authorized,
                "parent_security_scan_fallback_authorized": (
                    parent_security_scan_fallback_authorized
                ),
                "parent_security_report_fallback_authorized": (
                    parent_security_report_fallback_authorized
                ),
                "protected_history_sha256": protected_history_sha256,
            },
        )
    except loop_core.LoopContractError as exc:
        render({"status": "rejected", "errors": [str(exc)]})
        return 1
    render({"status": "decided", "decision": result})
    return 0


def command_agent_route(
    path: pathlib.Path, *, runtime_facts_path: pathlib.Path
) -> int:
    """Produce a V2a route receipt from the public decision-input contract."""
    document = loop_yaml.load_yaml(path)
    payload = document.get("agent_route") if isinstance(document, dict) else None
    if payload is None:
        payload = document
    if not isinstance(payload, dict):
        render({"status": "rejected", "errors": ["agent route input must be an object"]})
        return 1
    task = payload.get("task")
    assignment = payload.get("assignment")
    preflight_input = payload.get("profile_preflight")
    contract_version = payload.get("contract_version")
    if type(contract_version) is not int or contract_version not in {1, 2}:
        render({"status": "rejected", "errors": ["agent route contract_version must be 1 or 2"]})
        return 1
    if not isinstance(task, dict) or not isinstance(assignment, dict) or not isinstance(preflight_input, dict):
        render(
            {
                "status": "rejected",
                "errors": ["agent route input requires task, profile_preflight, and assignment objects"],
            }
        )
        return 1
    contract_shapes = (
        (payload, {"contract_version", "task", "profile_preflight", "assignment"}, "agent route"),
        (
            task,
            {"id", "factors"}
            if contract_version == 1
            else {"id", "factors", "workload_kind"},
            "agent route task",
        ),
        (
            preflight_input,
            {"profile_dir", "registry", "role", "agent_roots", "destination_root"},
            "agent route profile preflight",
        ),
        (
            assignment,
            {"scope", "ownership", "source_revision", "authority_contract"},
            "agent route assignment",
        ),
    )
    for value, allowed, label in contract_shapes:
        unknown = sorted(set(value) - allowed)
        if unknown:
            render(
                {
                    "status": "rejected",
                    "errors": [f"{label} contains unknown fields: {','.join(unknown)}"],
                }
            )
            return 1
    def resolved(value: Any, label: str) -> pathlib.Path:
        if not isinstance(value, str) or not value:
            raise profile_preflight.ProfileValidationError(f"{label} must be a non-empty path string")
        candidate = pathlib.Path(value)
        return candidate if candidate.is_absolute() else (path.parent / candidate).resolve()

    try:
        classification = agent_routing.classify_task(
            task.get("factors"),
            contract_version=contract_version,
            workload_kind=task.get("workload_kind"),
        )
        source_revision = assignment.get("source_revision")
        if not isinstance(source_revision, dict) or set(source_revision) != {
            "branch",
            "head_sha",
        }:
            raise agent_routing.AgentRoutingContractError(
                "agent route source revision requires exact branch and immutable head_sha"
            )
        profile_dir = resolved(preflight_input.get("profile_dir"), "profile_dir")
        registry_path = resolved(preflight_input.get("registry"), "registry")
        if registry_path.resolve() != CANONICAL_PROFILE_REGISTRY:
            raise profile_preflight.ProfileValidationError(
                "registry must be the canonical installed skill registry"
            )
        runtime_facts_path = runtime_facts_path.resolve()
        role = preflight_input.get("role")
        if not isinstance(role, str) or not role:
            raise profile_preflight.ProfileValidationError("role must be a non-empty string")
        raw_roots = preflight_input.get("agent_roots", [])
        if not isinstance(raw_roots, list):
            raise profile_preflight.ProfileValidationError("agent_roots must be an array")
        roots = [resolved(value, "agent root") for value in raw_roots]
        destination_value = preflight_input.get("destination_root")
        if not destination_value:
            raise profile_preflight.ProfileValidationError("destination_root is required for collision preflight")
        destination = resolved(destination_value, "destination_root")
        if destination not in roots:
            roots.append(destination)
        _, entries = profile_preflight.validate(profile_dir, registry_path)
        if role not in entries:
            raise profile_preflight.ProfileValidationError(f"unknown role: {role}")
        if contract_version == 2 and role != classification["selected_role"]:
            raise profile_preflight.ProfileValidationError(
                "version 2 role must match the deterministic cost-aware classification: "
                + classification["selected_role"]
            )
        facts = profile_preflight.runtime_facts(runtime_facts_path)
        collision_report = profile_preflight.detect_collisions(profile_dir, roots, destination)
        def destination_matches(candidate: dict[str, Any]) -> bool:
            if not destination.is_dir():
                return False
            for candidate_path in destination.glob("*.toml"):
                try:
                    candidate_name = profile_preflight.load_profile(
                        candidate_path, require_filename_match=False
                    )["name"]
                except profile_preflight.ProfileValidationError:
                    candidate_name = profile_preflight._external_name(candidate_path)
                if (
                    candidate_name == candidate.get("name")
                    and profile_preflight.profile_digest(candidate_path)
                    == candidate.get("profile_digest")
                ):
                    return True
            return False
        preflight_result = profile_preflight.preflight(
            entries[role],
            facts,
            collision_report,
            enforce_tier=contract_version == 2,
            trusted_profiles=entries,
        )
        evidence = preflight_result.get("route_profile_evidence")
        if evidence is None and preflight_result.get("fallback_tier") == "same-capability-profile":
            evidence = preflight_result.get("fallback_evidence")
        if contract_version == 2 and not isinstance(evidence, dict):
            required = entries[role]
            alternatives = sorted(
                (
                    entry
                    for name, entry in entries.items()
                    if name != role
                    and entry["capability_class"] == required["capability_class"]
                    and entry["tier_rank"] >= required["tier_rank"]
                ),
                key=lambda entry: (entry["tier_rank"], entry["name"]),
            )
            for candidate_entry in alternatives:
                candidate_result = profile_preflight.preflight(
                    candidate_entry,
                    facts,
                    collision_report,
                    enforce_tier=True,
                    trusted_profiles=entries,
                )
                candidate_evidence = candidate_result.get("route_profile_evidence")
                if (
                    candidate_result.get("decision") == "ready"
                    and isinstance(candidate_evidence, dict)
                    and destination_matches(candidate_evidence)
                ):
                    preflight_result = {
                        **candidate_result,
                        "requested_profile": role,
                        "fallback_tier": "same-capability-profile",
                        "cost_degraded": True,
                    }
                    evidence = candidate_evidence
                    break
        if preflight_result["decision"] == "human-gate":
            render({"status": "human-gate", "profile_preflight": preflight_result})
            return 2
        if isinstance(evidence, dict) and not destination_matches(evidence):
            degraded_facts = copy.deepcopy(facts)
            degraded_facts["available_models"] = []
            degraded_facts["reasoning_efforts"] = {}
            degraded_facts["compatible_profiles"] = {}
            preflight_result = profile_preflight.preflight(
                entries[role],
                degraded_facts,
                collision_report,
                enforce_tier=contract_version == 2,
                trusted_profiles=entries,
            )
            evidence = None
            facts = degraded_facts
            if preflight_result["decision"] == "human-gate":
                render({"status": "human-gate", "profile_preflight": preflight_result})
                return 2
        parent = facts.get("parent_default") if isinstance(facts.get("parent_default"), dict) else {}
        sequential = facts.get("sequential") if isinstance(facts.get("sequential"), dict) else {}
        runtime = {
            "custom_agents_available": facts.get("custom_agent_surface") == "available",
            "profiles": [evidence] if isinstance(evidence, dict) else [],
            "parent_default_available": parent.get("available") is True,
            "parent_capability_classes": parent.get("capability_classes", []),
            "parent_capability_tiers": parent.get("capability_tiers", {}),
            "sequential_available": sequential.get("available", True) is True,
            "current_session_capability_classes": sequential.get("capability_classes", []),
            "current_session_capability_tiers": sequential.get("capability_tiers", {}),
        }
        receipt = loop_core.evaluate_agent_route(
            task_id=task.get("id"),
            factors=task.get("factors"),
            runtime=runtime,
            assigned_scope=assignment.get("scope"),
            ownership=assignment.get("ownership"),
            source_revision=assignment.get("source_revision"),
            authority_contract=assignment.get("authority_contract"),
            contract_version=contract_version,
            workload_kind=task.get("workload_kind"),
        )
    except (
        loop_core.LoopContractError,
        profile_preflight.ProfileValidationError,
        agent_routing.AgentRoutingContractError,
    ) as exc:
        render({"status": "rejected", "errors": [str(exc)]})
        return 1
    render({"status": "routed", "profile_preflight": preflight_result, "route_receipt": receipt})
    return 0


def _current_git_revision(
    repo_root: pathlib.Path, route_source_revision: Any
) -> dict[str, str]:
    if repo_root.is_symlink() or not repo_root.is_dir():
        raise agent_routing.AgentRoutingContractError(
            "repo root must be a regular non-symlink directory"
        )
    root = repo_root.resolve()
    if not isinstance(route_source_revision, dict):
        raise agent_routing.AgentRoutingContractError(
            "route source revision must be an object"
        )
    unsupported = sorted(set(route_source_revision) - {"branch", "head_sha"})
    if unsupported:
        raise agent_routing.AgentRoutingContractError(
            "route source revision contains unsupported current-state keys: "
            + ",".join(unsupported)
        )
    if set(route_source_revision) != {"branch", "head_sha"}:
        raise agent_routing.AgentRoutingContractError(
            "route source revision requires exact branch and immutable head_sha"
        )
    try:
        actual_root = git_source.verified_git_root(root)
        git_environment = git_source.sanitized_git_environment()
        git_environment["GIT_WORK_TREE"] = str(actual_root)
        head = git_source.verified_git_head(root)
        branch = git_source.run_git(
            root,
            ["branch", "--show-current"],
            environment=git_environment,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise agent_routing.AgentRoutingContractError(
            "could not read current Git source revision"
        ) from exc
    if actual_root != root:
        raise agent_routing.AgentRoutingContractError(
            "repo root must be the target Git repository root"
        )
    values = {"branch": branch, "head_sha": head}
    return {key: values[key] for key in route_source_revision}


def _contained_regular_file(
    root: pathlib.Path, reference: Any, label: str
) -> pathlib.Path:
    if root.is_symlink() or not root.is_dir():
        raise agent_routing.AgentRoutingContractError(
            f"{label} root must be a regular non-symlink directory"
        )
    if not isinstance(reference, str) or not reference:
        raise agent_routing.AgentRoutingContractError(
            f"{label} path must be a non-empty string"
        )
    resolved_root = root.resolve()
    candidate = pathlib.Path(reference)
    if not candidate.is_absolute():
        candidate = resolved_root / candidate
    if candidate.is_symlink():
        raise agent_routing.AgentRoutingContractError(
            f"{label} must be a regular non-symlink file: {reference}"
        )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise agent_routing.AgentRoutingContractError(
            f"{label} must be contained by its trusted root: {reference}"
        ) from exc
    if not resolved.is_file():
        raise agent_routing.AgentRoutingContractError(
            f"{label} must be a regular non-symlink file: {reference}"
        )
    return resolved


def command_agent_integrate(
    path: pathlib.Path,
    *,
    repo_root: pathlib.Path,
    artifact_root: pathlib.Path,
    verification_root: pathlib.Path,
    assignment_fresh: bool,
    profile_path: pathlib.Path | None,
) -> int:
    """Validate worker evidence and current-state integration disposition."""
    document = loop_yaml.load_yaml(path)
    payload = document.get("agent_integration") if isinstance(document, dict) else None
    if payload is None:
        payload = document
    if not isinstance(payload, dict):
        render({"status": "rejected", "errors": ["agent integration input must be an object"]})
        return 1
    allowed = {"contract_version", "route_receipt", "worker_receipt", "disposition"}
    unknown = sorted(set(payload) - allowed)
    if payload.get("contract_version") != 1 or unknown:
        render({"status": "rejected", "errors": ["agent integration contract is invalid" if not unknown else f"agent integration contains unknown fields: {','.join(unknown)}"]})
        return 1
    try:
        if assignment_fresh is not True:
            raise agent_routing.AgentRoutingContractError(
                "assignment freshness requires the trusted CLI flag"
            )
        route_receipt = payload.get("route_receipt")
        if not isinstance(route_receipt, dict):
            raise agent_routing.AgentRoutingContractError(
                "route receipt must be an object"
            )
        worker_receipt = payload.get("worker_receipt")
        if not isinstance(worker_receipt, dict):
            raise agent_routing.AgentRoutingContractError(
                "worker receipt must be an object"
            )
        artifacts = worker_receipt.get("output_artifacts")
        artifact_digests = worker_receipt.get("artifact_digests")
        if not isinstance(artifacts, list) or not isinstance(artifact_digests, dict):
            raise agent_routing.AgentRoutingContractError(
                "worker artifacts and digests must be present"
            )
        for reference in artifacts:
            artifact_path = _contained_regular_file(
                artifact_root, reference, "worker output artifact"
            )
            expected = artifact_digests.get(reference)
            actual = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            if expected != actual:
                raise agent_routing.AgentRoutingContractError(
                    f"worker output artifact digest mismatch: {reference}"
                )
        disposition = payload.get("disposition")
        if not isinstance(disposition, dict):
            raise agent_routing.AgentRoutingContractError("disposition must be an object")
        verification = disposition.get("verification")
        verification_artifacts = (
            verification.get("artifacts") if isinstance(verification, dict) else None
        )
        verification_digests = (
            verification.get("artifact_digests")
            if isinstance(verification, dict)
            else None
        )
        if (
            not isinstance(verification_artifacts, list)
            or not verification_artifacts
            or not isinstance(verification_digests, dict)
            or set(verification_digests) != set(verification_artifacts)
        ):
            raise agent_routing.AgentRoutingContractError(
                "main-agent verification artifacts and exact digests must be present"
            )
        for reference in verification_artifacts:
            verification_path = _contained_regular_file(
                verification_root, reference, "main-agent verification artifact"
            )
            actual = hashlib.sha256(verification_path.read_bytes()).hexdigest()
            if verification_digests.get(reference) != actual:
                raise agent_routing.AgentRoutingContractError(
                    f"main-agent verification artifact digest mismatch: {reference}"
                )
        selected_profile_digest = route_receipt.get("selected_profile_digest")
        if selected_profile_digest is None:
            if profile_path is not None:
                raise agent_routing.AgentRoutingContractError(
                    "profile path must not be supplied for a non-custom route"
                )
            current_profile_digest = None
        else:
            if profile_path is None:
                raise agent_routing.AgentRoutingContractError(
                    "selected custom route requires --profile-path"
                )
            if profile_path.is_symlink() or not profile_path.is_file():
                raise agent_routing.AgentRoutingContractError(
                    "profile path must be a regular non-symlink file"
                )
            profile = profile_preflight.load_profile(
                profile_path, require_filename_match=False
            )
            current_profile_digest = profile_preflight.profile_digest(profile_path)
            evidence = route_receipt.get("config_evidence")
            if (
                not isinstance(evidence, dict)
                or profile.get("name") != evidence.get("name")
                or current_profile_digest != selected_profile_digest
            ):
                raise agent_routing.AgentRoutingContractError(
                    "selected profile does not match the route receipt"
                )
        current_source_revision = _current_git_revision(
            repo_root, route_receipt.get("source_revision")
        )
        worker_validation = agent_routing.validate_worker_receipt(
            worker_receipt, route_receipt
        )
        disposition = {
            **disposition,
            "worker_validation_id": worker_validation["validation_receipt_id"],
        }
        integration = agent_routing.validate_main_agent_disposition(
            disposition,
            route_receipt,
            worker_validation,
            current_source_revision=current_source_revision,
            current_profile_digest=current_profile_digest,
            assignment_fresh=assignment_fresh,
        )
    except (
        OSError,
        profile_preflight.ProfileValidationError,
        agent_routing.AgentRoutingContractError,
    ) as exc:
        render({"status": "rejected", "errors": [str(exc)]})
        return 1
    status = "accepted" if integration["integration_accepted"] else "rejected"
    render({"status": status, "worker_validation": worker_validation, "integration": integration})
    return 0 if status == "accepted" else 1


def command_transition(
    path: pathlib.Path,
    task_id: str,
    target: str,
    manifest_path: pathlib.Path | None = None,
    repo_root: pathlib.Path | None = None,
    *,
    blocker_resolved: bool = False,
    reopen: bool = False,
    protected_history_sha256: str | None = None,
) -> int:
    document = loop_yaml.load_yaml(path)
    errors = loop_yaml.validate_ledger(document)
    if errors:
        render({"status": "invalid", "errors": errors})
        return 1
    if (document.get("current_loop") or {}).get("lifecycle") == "complete":
        render(
            {
                "status": "rejected",
                "errors": ["objective completion is terminal"],
                "writes_performed": False,
            }
        )
        return 1
    task = next((item for item in document["tasks"] if item.get("id") == task_id), None)
    if task is None:
        render({"status": "invalid", "errors": [f"unknown task {task_id}"]})
        return 1
    definitions = _definitions(
        path, document, manifest_path, require_contract=True, repo_root=repo_root
    )
    semantic_errors = loop_yaml.semantic_audit(
        document,
        definitions,
        require_protected_history_authority=True,
        trusted_protected_history_sha256=protected_history_sha256,
    )
    if semantic_errors:
        render({"status": "invalid", "errors": semantic_errors, "writes_performed": False})
        return 1
    task_definition = dict(definitions.get(task_id) or {})
    dependencies = task_definition.get("dependencies") or []
    statuses = {item.get("id"): item.get("status") for item in document["tasks"]}
    task_definition["dependencies_satisfied"] = all(
        statuses.get(dependency) in {"done", "accepted"} for dependency in dependencies
    )
    required_gate = task_definition.get("human_gate_name")
    gate_by_name = {
        gate.get("gate"): gate
        for gate in document.get("human_gates", [])
        if isinstance(gate, dict)
    }
    task_definition["human_gate_satisfied"] = bool(
        isinstance(required_gate, str)
        and gate_by_name.get(required_gate, {}).get("status") == "satisfied"
    )
    claim = next(
        (
            item
            for item in document.get("claims", [])
            if item.get("task_id") == task_id and item.get("status") == "active"
        ),
        {},
    )
    evidence = _core_evidence(document, task)
    evidence["blocker_resolved"] = blocker_resolved
    evidence["reopen"] = reopen
    try:
        loop_core.validate_transition(
            task["status"],
            target,
            task_definition=task_definition,
            evidence=evidence,
            claim=claim,
        )
    except loop_core.LoopContractError as exc:
        render({"status": "rejected", "errors": [str(exc)], "writes_performed": False})
        return 1
    render(
        {
            "status": "preview",
            "task_id": task_id,
            "current_status": task["status"],
            "target_status": target,
            "writes_performed": False,
        }
    )
    return 0


def command_apply_event(
    path: pathlib.Path,
    event_path: pathlib.Path,
    *,
    manifest_path: pathlib.Path | None,
    write: bool,
    repo_root: pathlib.Path | None = None,
    authorize_action: str | None = None,
    authorization_receipt_sha256: str | None = None,
    protected_history_sha256: str | None = None,
) -> int:
    lock_path = path.with_name(f".{path.name}.lock")
    lock_descriptor: int | None = None
    if write:
        try:
            lock_descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.write(lock_descriptor, f"pid={os.getpid()}\n".encode("utf-8"))
        except FileExistsError:
            render(
                {
                    "status": "rejected",
                    "errors": [f"ledger write lock already exists: {lock_path}"],
                    "writes_performed": False,
                }
            )
            return 1
    try:
        original_bytes, original_binding = _bound_contract_bytes(
            path,
            pathlib.Path(os.path.abspath(path.parent)),
            None,
            "apply-event ledger",
        )
        original_mode = stat.S_IMODE(original_binding[3])
        event_bytes, _ = _bound_contract_bytes(
            event_path,
            pathlib.Path(os.path.abspath(event_path.parent)),
            None,
            "apply-event event",
        )
        document = _load_bound_yaml(original_bytes, "apply-event ledger")
        event = _load_bound_yaml(event_bytes, "apply-event event")
        structural_errors = loop_yaml.validate_ledger(document)
        if structural_errors:
            render(
                {
                    "status": "rejected",
                    "errors": structural_errors,
                    "writes_performed": False,
                }
            )
            return 1
        if not isinstance(event, dict):
            render(
                {
                    "status": "rejected",
                    "errors": ["event must be a mapping"],
                    "writes_performed": False,
                }
            )
            return 1
        is_source_rebound = event.get("type") == "source_rebound"
        prior_same_key = [
            item
            for item in document.get("events", [])
            if isinstance(item, dict)
            and item.get("idempotency_key") == event.get("idempotency_key")
        ]
        source_rebound_replay = is_source_rebound and any(
            item == event for item in prior_same_key
        )
        if is_source_rebound and prior_same_key and not source_rebound_replay:
            render(
                {
                    "status": "rejected",
                    "errors": ["idempotency key reused with different payload"],
                    "writes_performed": False,
                }
            )
            return 1
        if is_source_rebound and not source_rebound_replay:
            verified_root, live_revision = _verified_rebind_source(
                path,
                document,
                repo_root,
                expected_ledger_bytes=original_bytes,
                expected_ledger_binding=original_binding,
            )
            definitions, rebound_contract_binding = _source_rebound_contract(
                path,
                document,
                manifest_path,
                verified_root,
                target_head=live_revision["head_sha"],
            )
            target_source = (event.get("payload") or {}).get(
                "target_source_revision"
            )
            if not isinstance(target_source, dict) or any(
                target_source.get(field) != live_revision[field]
                for field in ("branch", "head_sha")
            ):
                raise loop_yaml.LedgerValidationError(
                    "source rebound target must match the current typed Git revision"
                )
        elif source_rebound_replay:
            verified_root = _verify_git_source(path, document, repo_root)
            definitions, _ = _source_rebound_contract(
                path,
                document,
                manifest_path,
                verified_root,
                target_head=document["ledger"]["source_revision"]["head_sha"],
            )
        else:
            definitions = _definitions(
                path,
                document,
                manifest_path,
                require_contract=True,
                repo_root=repo_root,
            )
        history_digest = loop_core.protected_history_digest(
            document.get("events", [])
        )
        current_errors = loop_yaml.semantic_audit(
            document,
            definitions,
            require_protected_history_authority=write,
            trusted_protected_history_sha256=protected_history_sha256,
        )
        if current_errors:
            render({"status": "rejected", "errors": current_errors, "writes_performed": False})
            return 1
        state = loop_yaml.state_from_ledger(document, definitions)
        protected_action = loop_core.protected_event_action(event)
        authorization = (event.get("payload") or {}).get("authorization")
        receipt_digest = (
            loop_core.digest(authorization) if isinstance(authorization, dict) else None
        )
        trusted_authority = None
        if authorize_action is not None or authorization_receipt_sha256 is not None:
            trusted_authority = {
                "action": authorize_action,
                "authorization_receipt_sha256": authorization_receipt_sha256,
            }
        if write:
            updated, replayed = loop_core.apply_event(
                state,
                event,
                trusted_authority=trusted_authority,
                trusted_time=_trusted_current_time(),
            )
        else:
            updated, replayed = loop_core.replay_event(state, event)
        materialized = loop_yaml.update_ledger_view(document, updated)
        if not replayed:
            source = materialized["ledger"]["source_revision"]
            source["previous_ledger_sha256"] = hashlib.sha256(original_bytes).hexdigest()
            source["updated_at"] = event["occurred_at"]
        errors = loop_yaml.semantic_audit(materialized, definitions)
        if errors:
            render({"status": "rejected", "errors": errors, "writes_performed": False})
            return 1
        resulting_history_digest = loop_core.protected_history_digest(
            materialized.get("events", [])
        )
        durability_warning: str | None = None
        if write and not replayed:
            rendered = loop_yaml.dump_yaml(materialized)
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
            try:
                os.fchmod(descriptor, original_mode)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(rendered)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    if is_source_rebound:
                        _, repeated_live_revision = _verified_rebind_source(
                            path,
                            document,
                            repo_root,
                            expected_ledger_bytes=original_bytes,
                            expected_ledger_binding=original_binding,
                        )
                        if repeated_live_revision != live_revision:
                            raise loop_yaml.LedgerValidationError(
                                "source rebound Git revision changed before commit"
                            )
                        _, repeated_contract_binding = _source_rebound_contract(
                            path,
                            document,
                            manifest_path,
                            verified_root,
                            target_head=live_revision["head_sha"],
                        )
                        if repeated_contract_binding != rebound_contract_binding:
                            raise loop_yaml.LedgerValidationError(
                                "source rebound contract artifacts changed before commit"
                            )
                    else:
                        _definitions(
                            path,
                            document,
                            manifest_path,
                            require_contract=True,
                            repo_root=repo_root,
                        )
                except loop_yaml.LedgerValidationError as exc:
                    render(
                        {
                            "status": "rejected",
                            "errors": [f"source revision changed before commit: {exc}"],
                            "writes_performed": False,
                        }
                    )
                    return 1
                _, current_binding = _bound_contract_bytes(
                    path,
                    pathlib.Path(os.path.abspath(path.parent)),
                    hashlib.sha256(original_bytes).hexdigest(),
                    "apply-event ledger",
                )
                if current_binding != original_binding:
                    render(
                        {
                            "status": "rejected",
                            "errors": ["ledger changed after read; compare-and-swap rejected"],
                            "writes_performed": False,
                        }
                    )
                    return 1
                rechecked, rechecked_replayed = loop_core.apply_event(
                    state,
                    event,
                    trusted_authority=trusted_authority,
                    trusted_time=_trusted_current_time(),
                )
                rechecked_materialized = loop_yaml.update_ledger_view(
                    document, rechecked
                )
                if not rechecked_replayed:
                    rechecked_source = rechecked_materialized["ledger"][
                        "source_revision"
                    ]
                    rechecked_source["previous_ledger_sha256"] = hashlib.sha256(
                        original_bytes
                    ).hexdigest()
                    rechecked_source["updated_at"] = event["occurred_at"]
                if (
                    rechecked != updated
                    or rechecked_replayed != replayed
                    or rechecked_materialized != materialized
                ):
                    raise loop_core.LoopContractError(
                        "live event acceptance changed before commit"
                    )
                os.replace(temporary_name, path)
                directory_descriptor: int | None = None
                try:
                    directory_descriptor = os.open(path.parent, os.O_RDONLY)
                    os.fsync(directory_descriptor)
                except OSError as exc:
                    durability_warning = (
                        "ledger replacement committed, but parent-directory durability sync "
                        f"failed; do not blindly retry: {exc}"
                    )
                finally:
                    if directory_descriptor is not None:
                        os.close(directory_descriptor)
            finally:
                if os.path.exists(temporary_name):
                    os.unlink(temporary_name)
        render(
            {
                "status": (
                    "replayed"
                    if replayed
                    else (
                        "applied-durability-uncertain"
                        if durability_warning is not None
                        else ("applied" if write else "preview")
                    )
                ),
                "writes_performed": bool(write and not replayed),
                "durability_warning": durability_warning,
                "state_revision": updated["revision"],
                "event_hash": updated["last_event_hash"],
                "protected_action": protected_action,
                "authorization_receipt_sha256": receipt_digest,
                "live_authorization_verified": bool(
                    write and not replayed and protected_action
                ),
                "prior_protected_history_sha256": history_digest,
                "protected_history_sha256": resulting_history_digest,
                "protected_history_re_attested": bool(
                    write
                    and history_digest is not None
                    and protected_history_sha256 == history_digest
                ),
                "preview": None if write else materialized,
            }
        )
        return 3 if durability_warning is not None else 0
    except loop_core.LoopContractError as exc:
        render({"status": "rejected", "errors": [str(exc)], "writes_performed": False})
        return 1
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            try:
                os.unlink(lock_path)
            except FileNotFoundError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "status", "hash-event"):
        command = subparsers.add_parser(name)
        command.add_argument("path", type=pathlib.Path)
    decide = subparsers.add_parser("decide")
    decide.add_argument("path", type=pathlib.Path)
    decide.add_argument("--external-write-authorized", action="store_true")
    decide.add_argument(
        "--parent-security-scan-fallback-authorized",
        action="store_true",
    )
    decide.add_argument(
        "--parent-security-report-fallback-authorized",
        action="store_true",
    )
    decide.add_argument("--protected-history-sha256")
    agent_route = subparsers.add_parser("agent-route")
    agent_route.add_argument("path", type=pathlib.Path)
    agent_route.add_argument("--runtime-facts", required=True, type=pathlib.Path)
    agent_integrate = subparsers.add_parser("agent-integrate")
    agent_integrate.add_argument("path", type=pathlib.Path)
    agent_integrate.add_argument("--repo-root", required=True, type=pathlib.Path)
    agent_integrate.add_argument("--artifact-root", required=True, type=pathlib.Path)
    agent_integrate.add_argument("--verification-root", required=True, type=pathlib.Path)
    agent_integrate.add_argument(
        "--assignment-fresh", required=True, action="store_true"
    )
    agent_integrate.add_argument("--profile-path", type=pathlib.Path)
    migrate = subparsers.add_parser("migrate-v1")
    migrate.add_argument("path", type=pathlib.Path)
    migrate.add_argument("--spec", type=pathlib.Path)
    migrate.add_argument("--manifest", type=pathlib.Path)
    migrate.add_argument("--repo-root", type=pathlib.Path)
    audit = subparsers.add_parser("audit")
    audit.add_argument("path", type=pathlib.Path)
    audit.add_argument("--manifest", type=pathlib.Path)
    audit.add_argument("--repo-root", type=pathlib.Path)
    transition = subparsers.add_parser("transition")
    transition.add_argument("path", type=pathlib.Path)
    transition.add_argument("task_id")
    transition.add_argument("target_status")
    transition.add_argument("--manifest", type=pathlib.Path)
    transition.add_argument("--repo-root", type=pathlib.Path)
    transition.add_argument("--blocker-resolved", action="store_true")
    transition.add_argument("--reopen", action="store_true")
    transition.add_argument("--protected-history-sha256")
    apply_event = subparsers.add_parser("apply-event")
    apply_event.add_argument("path", type=pathlib.Path)
    apply_event.add_argument("event", type=pathlib.Path)
    apply_event.add_argument("--manifest", type=pathlib.Path)
    apply_event.add_argument("--repo-root", type=pathlib.Path)
    apply_event.add_argument("--write", action="store_true")
    apply_event.add_argument(
        "--authorize-action",
        choices=loop_core.PROTECTED_EVENT_ACTIONS,
    )
    apply_event.add_argument("--authorization-receipt-sha256")
    apply_event.add_argument("--protected-history-sha256")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            return command_validate(args.path)
        if args.command == "status":
            return command_status(args.path)
        if args.command == "audit":
            return command_audit(args.path, args.manifest, args.repo_root)
        if args.command == "migrate-v1":
            return command_migrate(
                args.path,
                spec_path=args.spec,
                manifest_path=args.manifest,
                repo_root=args.repo_root,
            )
        if args.command == "hash-event":
            return command_hash_event(args.path)
        if args.command == "decide":
            return command_decide(
                args.path,
                external_write_authorized=args.external_write_authorized,
                parent_security_scan_fallback_authorized=(
                    args.parent_security_scan_fallback_authorized
                ),
                parent_security_report_fallback_authorized=(
                    args.parent_security_report_fallback_authorized
                ),
                protected_history_sha256=args.protected_history_sha256,
            )
        if args.command == "agent-route":
            return command_agent_route(
                args.path, runtime_facts_path=args.runtime_facts
            )
        if args.command == "agent-integrate":
            return command_agent_integrate(
                args.path,
                repo_root=args.repo_root,
                artifact_root=args.artifact_root,
                verification_root=args.verification_root,
                assignment_fresh=args.assignment_fresh,
                profile_path=args.profile_path,
            )
        if args.command == "apply-event":
            return command_apply_event(
                args.path,
                args.event,
                manifest_path=args.manifest,
                write=args.write,
                repo_root=args.repo_root,
                authorize_action=args.authorize_action,
                authorization_receipt_sha256=args.authorization_receipt_sha256,
                protected_history_sha256=args.protected_history_sha256,
            )
        return command_transition(
            args.path,
            args.task_id,
            args.target_status,
            args.manifest,
            args.repo_root,
            blocker_resolved=args.blocker_resolved,
            reopen=args.reopen,
            protected_history_sha256=args.protected_history_sha256,
        )
    except (loop_yaml.LedgerValidationError, RuntimeError) as exc:
        render({"status": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
