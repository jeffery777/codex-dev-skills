#!/usr/bin/env python3
"""Inspect and validate Loop Engineering state without implicit writes."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import loop_core  # noqa: E402
import loop_yaml  # noqa: E402


def render(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str))


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
        root = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", root, "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            "could not verify git source revision; pass --repo-root for the target repository"
        ) from exc
    source = document["ledger"]["source_revision"]
    if source.get("head_sha") != head:
        raise loop_yaml.LedgerValidationError(
            f"git HEAD mismatch: expected {source.get('head_sha')!r}, got {head}"
        )
    if source.get("branch") != branch:
        raise loop_yaml.LedgerValidationError(
            f"git branch mismatch: expected {source.get('branch')!r}, got {branch!r}"
        )
    return pathlib.Path(root).resolve()


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


def _git_revision(start: pathlib.Path) -> dict[str, str]:
    try:
        root = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", root, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", root, "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise loop_yaml.LedgerValidationError(
            "could not resolve git source revision for bound migration"
        ) from exc
    if not branch:
        raise loop_yaml.LedgerValidationError("bound migration requires a named git branch")
    return {"root": root, "head_sha": head, "branch": branch}


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
        git_source = _git_revision(repo_root or path.parent)
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
        original_bytes = path.read_bytes()
        document = loop_yaml.load_yaml(path)
        event = loop_yaml.load_yaml(event_path)
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
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(rendered)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
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
                if path.read_bytes() != original_bytes:
                    render(
                        {
                            "status": "rejected",
                            "errors": ["ledger changed after read; compare-and-swap rejected"],
                            "writes_performed": False,
                        }
                    )
                    return 1
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
        "--parent-security-report-fallback-authorized", action="store_true"
    )
    decide.add_argument("--protected-history-sha256")
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
                parent_security_report_fallback_authorized=(
                    args.parent_security_report_fallback_authorized
                ),
                protected_history_sha256=args.protected_history_sha256,
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
