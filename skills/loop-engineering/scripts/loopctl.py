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
import profile_preflight  # noqa: E402
import agent_routing  # noqa: E402

CANONICAL_PROFILE_REGISTRY = (
    HERE.parent / "references" / "agent-profile-registry.json"
).resolve()


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
    if payload.get("contract_version") != 1:
        render({"status": "rejected", "errors": ["agent route contract_version must be 1"]})
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
        (task, {"id", "factors"}, "agent route task"),
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
        agent_routing.validate_task_factors(task.get("factors"))
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
        facts = profile_preflight.runtime_facts(runtime_facts_path)
        collision_report = profile_preflight.detect_collisions(profile_dir, roots, destination)
        preflight_result = profile_preflight.preflight(entries[role], facts, collision_report)
        if preflight_result["decision"] == "human-gate":
            render({"status": "human-gate", "profile_preflight": preflight_result})
            return 2
        evidence = preflight_result.get("route_profile_evidence")
        if evidence is None and preflight_result.get("fallback_tier") == "same-capability-profile":
            evidence = preflight_result.get("fallback_evidence")
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
        if isinstance(evidence, dict) and not destination_matches(evidence):
            degraded_facts = copy.deepcopy(facts)
            degraded_facts["available_models"] = []
            degraded_facts["reasoning_efforts"] = {}
            degraded_facts["compatible_profiles"] = {}
            preflight_result = profile_preflight.preflight(
                entries[role], degraded_facts, collision_report
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
            "sequential_available": sequential.get("available", True) is True,
            "current_session_capability_classes": sequential.get("capability_classes", []),
        }
        receipt = loop_core.evaluate_agent_route(
            task_id=task.get("id"),
            factors=task.get("factors"),
            runtime=runtime,
            assigned_scope=assignment.get("scope"),
            ownership=assignment.get("ownership"),
            source_revision=assignment.get("source_revision"),
            authority_contract=assignment.get("authority_contract"),
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
        actual_root = pathlib.Path(
            subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        ).resolve()
        head = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
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
