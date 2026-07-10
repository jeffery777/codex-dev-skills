#!/usr/bin/env python3
"""Deterministic Loop Engineering decisions and task transition guards."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from typing import Any


TASK_STATUSES = (
    "planned",
    "ready",
    "in_progress",
    "blocked",
    "reviewing",
    "done",
    "accepted",
    "cancelled",
)

LEGAL_TRANSITIONS = {
    "planned": {"ready", "blocked", "cancelled"},
    "ready": {"in_progress", "blocked", "cancelled"},
    "in_progress": {"ready", "reviewing", "blocked"},
    "blocked": {"planned", "ready", "cancelled"},
    "reviewing": {"in_progress", "done", "blocked"},
    "done": {"accepted", "ready"},
    "accepted": set(),
    "cancelled": set(),
}

ROUTES = {
    "implementation": "implementation-slice",
    "docs": "docs-update",
    "review:routine": "code-review",
    "review:high": "code-review-deep",
    "delivery": "project-delivery",
    "continuation": "task-continuation",
}

EVENT_TYPES = {
    "migration_snapshot",
    "task_transition",
    "claim_acquired",
    "claim_released",
    "claim_expired",
    "claim_revoked",
    "gate_updated",
    "objective_completed",
}

PROTECTED_EVENT_ACTIONS = (
    "task_acceptance",
    "task_completion",
    "claim_revocation",
    "gate_satisfaction",
    "objective_completion",
)

GOAL_STATUSES = {"inactive", "active", "blocked", "complete"}

SECURITY_SCAN_STATUSES = {"not_started", "running", "complete", "failed", "cancelled"}
SECURITY_SCAN_PHASES = {
    "none",
    "preflight",
    "threat_model",
    "discovery",
    "validation",
    "attack_path",
    "reporting",
}
SECURITY_WORKER_FAILURES = {"none", "safety_refused", "transient", "unrecoverable"}

V1_MIGRATION_STATUSES = {
    "planned",
    "ready",
    "claimed",
    "in_progress",
    "blocked",
    "reviewing",
    "done",
    "accepted",
    "unsafe",
}


class LoopContractError(ValueError):
    """Raised when a loop transition or event violates the shared contract."""


def _datetime(value: Any, label: str) -> dt.datetime:
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise LoopContractError(f"{label} must be a valid ISO-8601 timestamp") from exc
    else:
        raise LoopContractError(f"{label} must be a valid ISO-8601 timestamp")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _json_value(value: Any) -> Any:
    if isinstance(value, dt.datetime):
        rendered = value.isoformat()
        return rendered.replace("+00:00", "Z")
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def source_revision_digest(source_revision: dict[str, Any]) -> str:
    """Digest immutable source identity without rolling ledger metadata."""
    required = ("branch", "head_sha", "spec_sha256", "task_manifest_sha256")
    for field in required:
        if not isinstance(source_revision.get(field), str) or not source_revision[field]:
            raise LoopContractError(f"source revision requires {field}")
    fields = (
        "branch",
        "head_sha",
        "spec_sha256",
        "task_manifest_sha256",
        "migration_source_sha256",
    )
    return digest(
        {
            field: source_revision[field]
            for field in fields
            if source_revision.get(field) not in (None, "")
        }
    )


def calculate_event_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return digest(payload)


def protected_payload_digest(payload: dict[str, Any]) -> str:
    """Digest every protected payload field except the embedded authorization."""
    return digest({key: value for key, value in payload.items() if key != "authorization"})


def completion_evidence(input_data: dict[str, Any]) -> tuple[bool, list[str]]:
    objective = input_data.get("objective") or {}
    state = input_data.get("state") or {}
    missing: list[str] = []
    checks = {
        "objective-clear": objective.get("clear") is True,
        "objective-complete": objective.get("complete") is True,
        "source-consistent": state.get("source_conflict") is False,
        "task-terminal": state.get("task_status") in {"done", "accepted"},
        "verification-passed": state.get("verification") == "passed",
        "review-satisfied": state.get("review") in {"not_required", "passed"},
        "human-gate-satisfied": state.get("human_gate") in {"not_required", "satisfied"},
    }
    for name, passed in checks.items():
        if not passed:
            missing.append(name)
    return not missing, missing


def _workflow_result(
    case_id: str,
    *,
    classification: str,
    route: str,
    execution_mode: str,
    next_decision: str,
    complete: bool = False,
    violations: list[str] | None = None,
    notices: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "classification": classification,
        "route": route,
        "execution_mode": execution_mode,
        "next_decision": next_decision,
        "complete": complete,
        "violations": violations or [],
        "notices": notices or [],
    }


def evaluate_workflow_case(
    case: dict[str, Any],
    *,
    trusted_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one deterministic workflow fixture through production routing."""
    if not isinstance(case, dict) or not isinstance(case.get("input"), dict):
        raise LoopContractError("workflow case must contain an input object")
    case_id = str(case.get("id") or "<unknown>")
    data = case["input"]
    sections: dict[str, dict[str, Any]] = {}
    for name in ("request", "objective", "state", "runtime", "work"):
        value = data.get(name)
        if value is None:
            sections[name] = {}
        elif not isinstance(value, dict):
            raise LoopContractError(f"workflow input {name} must be an object")
        else:
            sections[name] = value
    request = sections["request"]
    objective = sections["objective"]
    state = sections["state"]
    runtime = sections["runtime"]
    work = sections["work"]
    if trusted_authority is not None and not isinstance(trusted_authority, dict):
        raise LoopContractError("trusted authority must be an object")
    authority = trusted_authority or {}
    capabilities_value = runtime.get("capabilities")
    if capabilities_value is None:
        capabilities: dict[str, Any] = {}
    elif not isinstance(capabilities_value, dict):
        raise LoopContractError("runtime capabilities must be an object")
    else:
        capabilities = capabilities_value

    if request.get("requires_external_write") is True and authority.get(
        "external_write_authorized"
    ) is not True:
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["external-write-not-authorized"],
        )
    if objective.get("clear") is not True:
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["objective-unclear"],
        )
    if state.get("source_conflict") is True:
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["source-of-truth-conflict"],
        )
    protected_history = state.get("protected_history_sha256", "none")
    if not isinstance(protected_history, str) or not protected_history:
        raise LoopContractError("protected history digest must be a non-empty string")
    if authority.get("protected_history_sha256") != protected_history:
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["protected-history-not-re-attested"],
        )
    goal_status = state.get("goal_status", "inactive")
    if not isinstance(goal_status, str) or goal_status not in GOAL_STATUSES:
        raise LoopContractError("goal status is unsupported")
    security_scan_value = state.get("security_scan")
    if security_scan_value in (None, {}):
        security_scan: dict[str, Any] = {}
    elif not isinstance(security_scan_value, dict):
        raise LoopContractError("security scan state must be an object")
    else:
        security_scan = security_scan_value
    scan_status = security_scan.get("status")
    scan_phase = security_scan.get("phase", "none")
    worker_failure = security_scan.get("worker_failure_kind", "none")
    retry_count = security_scan.get("reporting_retry_count", 0)
    if scan_status is not None and scan_status not in SECURITY_SCAN_STATUSES:
        raise LoopContractError("security scan status is unsupported")
    if scan_phase not in SECURITY_SCAN_PHASES:
        raise LoopContractError("security scan phase is unsupported")
    if worker_failure not in SECURITY_WORKER_FAILURES:
        raise LoopContractError("security scan worker failure kind is unsupported")
    if (
        not isinstance(retry_count, int)
        or isinstance(retry_count, bool)
        or retry_count < 0
    ):
        raise LoopContractError(
            "security scan reporting_retry_count must be a non-negative integer"
        )
    if scan_status == "running":
        goal_projection_conflict = state.get("goal_status") == "blocked"
        if worker_failure == "safety_refused":
            if scan_phase != "reporting":
                return _workflow_result(
                    case_id,
                    classification="human-gate",
                    route="human-gate",
                    execution_mode="stop-for-human-gate",
                    next_decision="blocked-by-human-gate",
                    violations=["security-worker-failure-phase-mismatch"],
                    notices=["security-scan-remains-running"],
                )
            if retry_count >= 2:
                if authority.get("parent_security_report_fallback_authorized") is not True:
                    return _workflow_result(
                        case_id,
                        classification="human-gate",
                        route="human-gate",
                        execution_mode="stop-for-human-gate",
                        next_decision="blocked-by-human-gate",
                        violations=["security-report-parent-fallback-not-authorized"],
                        notices=["security-scan-remains-running"],
                    )
                return _workflow_result(
                    case_id,
                    classification="resumable-capability-failure",
                    route="task-continuation",
                    execution_mode="parent-report-fallback",
                    next_decision="continue",
                    notices=[
                        "security-scan-remains-running",
                        "worker-safety-refusal",
                        *(
                            ["goal-projection-conflict"]
                            if goal_projection_conflict
                            else []
                        ),
                    ],
                )
            return _workflow_result(
                case_id,
                classification="resumable-capability-failure",
                route="task-continuation",
                execution_mode=(
                    "replacement-worker"
                    if capabilities.get("subagents") is True
                    else "current-session"
                ),
                next_decision="continue",
                notices=[
                    "security-scan-remains-running",
                    "worker-safety-refusal",
                    *(
                        ["goal-projection-conflict"]
                        if goal_projection_conflict
                        else []
                    ),
                ],
            )
        if goal_projection_conflict:
            return _workflow_result(
                case_id,
                classification="resumable-capability-failure",
                route="task-continuation",
                execution_mode="current-session",
                next_decision="continue",
                notices=[
                    "security-scan-remains-running",
                    "goal-projection-conflict",
                ],
            )
    if state.get("human_gate") == "pending":
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["human-gate-pending"],
        )

    claim = state.get("claim") or {}
    if claim:
        if claim.get("source_revision_matches") is False:
            return _workflow_result(
                case_id,
                classification="human-gate",
                route="human-gate",
                execution_mode="stop-for-human-gate",
                next_decision="blocked-by-human-gate",
                violations=["claim-source-revision-stale"],
            )
        if claim.get("status") == "active" and claim.get("owner") != claim.get("current_owner"):
            return _workflow_result(
                case_id,
                classification="human-gate",
                route="human-gate",
                execution_mode="stop-for-human-gate",
                next_decision="blocked-by-human-gate",
                violations=["claim-owned-by-another-worker"],
            )
        if claim.get("status") == "active" and claim.get("lease_valid") is False:
            return _workflow_result(
                case_id,
                classification="handoff-or-continuation",
                route="task-continuation",
                execution_mode="stop-for-human-gate",
                next_decision="blocked-by-human-gate",
                violations=["stale-claim-requires-inspection"],
            )

    completion_allowed, missing = completion_evidence(data)
    if objective.get("complete") is True:
        if completion_allowed:
            return _workflow_result(
                case_id,
                classification="complete",
                route="complete",
                execution_mode="current-session",
                next_decision="complete",
                complete=True,
            )
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["completion-evidence-missing:" + ",".join(missing)],
        )

    if state.get("interrupted") is True:
        return _workflow_result(
            case_id,
            classification="handoff-or-continuation",
            route="task-continuation",
            execution_mode="current-session",
            next_decision="continue",
        )

    kind = request.get("kind", "continuation")
    risk = request.get("risk", "routine")
    route_key = f"review:{risk}" if kind == "review" else kind
    route = ROUTES.get(route_key)
    if route is None:
        return _workflow_result(
            case_id,
            classification="human-gate",
            route="human-gate",
            execution_mode="stop-for-human-gate",
            next_decision="blocked-by-human-gate",
            violations=["unsupported-request-kind"],
        )

    classification = {
        "implementation": "single-clear-task",
        "docs": "single-clear-task",
        "review": "review-closure-loop",
        "delivery": "bounded-delivery-objective",
        "continuation": "handoff-or-continuation",
    }[kind]
    execution_mode = "current-session"
    if kind == "delivery" and work.get("parallelizable") is True:
        if work.get("ownership_disjoint") is not True:
            return _workflow_result(
                case_id,
                classification="human-gate",
                route="human-gate",
                execution_mode="stop-for-human-gate",
                next_decision="blocked-by-human-gate",
                violations=["parallel-write-ownership-overlap"],
            )
        execution_mode = (
            "shared-subagents" if capabilities.get("subagents") is True else "sequential-fallback"
        )
    elif kind == "continuation" and request.get("scheduled") is True:
        execution_mode = (
            "desktop-scheduled"
            if runtime.get("surface") == "desktop" and capabilities.get("scheduler") is True
            else "sequential-fallback"
        )
    elif kind == "continuation" and request.get("desktop_thread") is True:
        execution_mode = (
            "desktop-thread"
            if runtime.get("surface") == "desktop" and capabilities.get("threads") is True
            else "sequential-fallback"
        )
    elif request.get("goal_required") is True and capabilities.get("goal") is not True:
        execution_mode = "sequential-fallback"

    return _workflow_result(
        case_id,
        classification=classification,
        route=route,
        execution_mode=execution_mode,
        next_decision="continue",
    )


def _evidence_status(proof: dict[str, Any], key: str) -> Any:
    value = proof.get(key)
    return value.get("status") if isinstance(value, dict) else value


def _evidence_artifact(proof: dict[str, Any]) -> Any:
    if proof.get("artifact"):
        return proof["artifact"]
    for key in ("verification", "review"):
        value = proof.get(key)
        if isinstance(value, dict):
            for artifact in value.get("artifacts") or []:
                if artifact and not str(artifact).startswith("<"):
                    return artifact
    return None


def _review_artifact(proof: dict[str, Any]) -> Any:
    value = proof.get("review")
    if not isinstance(value, dict):
        return None
    for artifact in value.get("artifacts") or []:
        if isinstance(artifact, str) and artifact and not artifact.startswith("<"):
            return artifact
    return None


def _acceptance_artifact(proof: dict[str, Any]) -> Any:
    value = proof.get("acceptance")
    if isinstance(value, dict):
        return value.get("artifact") if value.get("status") == "satisfied" else None
    return value


def _require_bound_authorization(
    state: dict[str, Any],
    event: dict[str, Any],
    payload: dict[str, Any],
    *,
    action: str,
    allowed_principal_types: set[str],
    scope: dict[str, str] | None = None,
    evidence_artifact: Any = None,
    principal_must_match_actor: bool = True,
) -> dict[str, Any]:
    authorization = payload.get("authorization")
    if not isinstance(authorization, dict):
        raise LoopContractError(f"{action} requires bound authorization")
    if authorization.get("action") != action:
        raise LoopContractError(f"{action} authorization action mismatch")
    principal = authorization.get("principal")
    if not isinstance(principal, dict):
        raise LoopContractError(f"{action} authorization requires a principal")
    if principal.get("type") not in allowed_principal_types:
        raise LoopContractError(f"{action} authorization principal type is not allowed")
    if principal_must_match_actor and principal.get("id") != event.get("actor"):
        raise LoopContractError(f"{action} authorization principal must match event actor")
    if not isinstance(principal.get("id"), str) or not principal["id"]:
        raise LoopContractError(f"{action} authorization principal requires an id")
    objective_id = state.get("objective_id")
    if not isinstance(objective_id, str) or not objective_id:
        raise LoopContractError(f"{action} requires objective identity")
    if authorization.get("objective_id") != objective_id:
        raise LoopContractError(f"{action} authorization objective mismatch")
    artifact = authorization.get("artifact")
    if (
        not isinstance(artifact, str)
        or not artifact
        or artifact.startswith("<")
    ):
        raise LoopContractError(f"{action} authorization requires a concrete artifact")
    expected_source_digest = source_revision_digest(state.get("source_revision") or {})
    if authorization.get("source_revision_sha256") != expected_source_digest:
        raise LoopContractError(f"{action} authorization source revision mismatch")
    if authorization.get("protected_payload_sha256") != protected_payload_digest(payload):
        raise LoopContractError(f"{action} authorization protected payload mismatch")
    for key, expected in (scope or {}).items():
        if authorization.get(key) != expected:
            raise LoopContractError(f"{action} authorization scope mismatch: {key}")
    if (
        not isinstance(evidence_artifact, str)
        or not evidence_artifact
        or evidence_artifact.startswith("<")
    ):
        raise LoopContractError(f"{action} requires a concrete evidence artifact")
    if artifact != evidence_artifact:
        raise LoopContractError(f"{action} authorization artifact mismatch")
    return authorization


def protected_event_action(event: dict[str, Any]) -> str | None:
    """Return the exact live authorization action required by an event."""
    event_type = event.get("type")
    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        return None
    if event_type == "task_transition" and payload.get("target_status") == "accepted":
        return "task_acceptance"
    evidence = payload.get("evidence") or {}
    if (
        event_type == "task_transition"
        and payload.get("target_status") == "done"
        and isinstance(evidence, dict)
        and _evidence_status(evidence, "review") == "passed"
    ):
        return "task_completion"
    if event_type == "claim_revoked":
        return "claim_revocation"
    if event_type == "gate_updated" and payload.get("status") in {
        "not_required",
        "satisfied",
    }:
        return "gate_satisfaction"
    if event_type == "objective_completed":
        return "objective_completion"
    return None


def protected_history_digest(events: list[dict[str, Any]]) -> str | None:
    """Digest full protected events for current-session history re-attestation."""
    protected = [event for event in events if protected_event_action(event) is not None]
    return digest(protected) if protected else None


def _require_live_authorization(
    event: dict[str, Any],
    *,
    trusted_authority: dict[str, Any] | None,
) -> None:
    """Require current-session authority that is independent of repository input."""
    action = protected_event_action(event)
    authority = trusted_authority or {}
    if action is None:
        if authority:
            raise LoopContractError(
                "live authorization must not be supplied for an unprotected event"
            )
        return
    authorization = (event.get("payload") or {}).get("authorization")
    if not isinstance(authorization, dict):
        raise LoopContractError(f"{action} requires bound authorization")
    if authority.get("action") != action:
        raise LoopContractError(f"{action} requires exact live action authorization")
    receipt_digest = authority.get("authorization_receipt_sha256")
    if receipt_digest != digest(authorization):
        raise LoopContractError(f"{action} live authorization receipt mismatch")


def validate_transition(
    current: str,
    target: str,
    *,
    task_definition: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    claim: dict[str, Any] | None = None,
) -> None:
    if current not in TASK_STATUSES or target not in TASK_STATUSES:
        raise LoopContractError("unknown task status")
    if target not in LEGAL_TRANSITIONS[current]:
        raise LoopContractError(f"illegal task transition: {current} -> {target}")
    definition = task_definition or {}
    proof = evidence or {}
    active_claim = claim or {}
    if target == "ready":
        for key in ("scope", "dod", "verification"):
            if not definition.get(key):
                raise LoopContractError(f"ready requires task definition field: {key}")
        if not isinstance(definition.get("dependencies"), list):
            raise LoopContractError("ready requires manifest dependencies")
        if definition.get("dependencies_satisfied") is not True:
            raise LoopContractError("ready requires all dependencies to be done or accepted")
    if target == "in_progress":
        if active_claim.get("status") != "active" or not active_claim.get("fencing_token"):
            raise LoopContractError("in_progress requires an active fenced claim")
    if target == "reviewing":
        if not _evidence_artifact(proof) or _evidence_status(proof, "verification") not in {
            "passed",
            "failed",
            "skipped",
        }:
            raise LoopContractError("reviewing requires an artifact and verification run")
    if target == "blocked" and not proof.get("blocker_reason"):
        raise LoopContractError("blocked requires blocker evidence")
    if target == "done":
        if _evidence_status(proof, "verification") != "passed":
            raise LoopContractError("done requires passed verification")
        review_status = _evidence_status(proof, "review")
        if definition.get("review_required") is True and review_status != "passed":
            raise LoopContractError("done requires the manifest review")
        if definition.get("review_required") is True:
            review = proof.get("review")
            if not isinstance(review, dict):
                raise LoopContractError("done requires structured manifest review evidence")
            if review.get("mode") != definition.get("review_mode"):
                raise LoopContractError("done requires the manifest review mode")
            if not _review_artifact(proof):
                raise LoopContractError("done requires a concrete manifest review artifact")
        if review_status not in {"not_required", "passed"}:
            raise LoopContractError("done requires satisfied review evidence")
        human_gate_status = _evidence_status(proof, "human_gate")
        if (
            definition.get("human_gate_required") is True
            and definition.get("human_gate_satisfied") is not True
        ):
            raise LoopContractError("done requires the manifest human gate")
        if human_gate_status not in {"not_required", "satisfied"}:
            raise LoopContractError("done requires satisfied human gates")
    if target == "accepted" and not _acceptance_artifact(proof):
        raise LoopContractError("accepted requires explicit acceptance evidence")
    if target == "accepted" and active_claim.get("status") == "active":
        raise LoopContractError("accepted requires releasing the active claim")
    if current == "blocked" and target != "cancelled" and not proof.get("blocker_resolved"):
        raise LoopContractError("leaving blocked requires blocker resolution evidence")
    if current == "done" and target == "ready" and not proof.get("reopen"):
        raise LoopContractError("reopening done requires explicit invalidation evidence")


def materialize_v1_snapshot(
    source_document: dict[str, Any],
    tasks: dict[str, dict[str, Any]],
    source_revision: dict[str, Any],
    occurred_at: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Deterministically project an embedded V1 ledger into executable V2 state."""
    source_ledger = source_document.get("ledger")
    if not isinstance(source_ledger, dict) or source_ledger.get("schema_version") != 1:
        raise LoopContractError("migration snapshot requires an embedded schema_version 1 ledger")
    source_revision_v1 = source_ledger.get("source_revision") or {}
    if not isinstance(source_revision_v1, dict):
        raise LoopContractError("migration snapshot source_revision must be an object")
    for field in ("branch", "head_sha"):
        if source_revision_v1.get(field) != source_revision.get(field):
            raise LoopContractError(f"migration snapshot source_revision mismatch: {field}")
    source_tasks = source_document.get("tasks")
    if not isinstance(source_tasks, list) or not all(isinstance(task, dict) for task in source_tasks):
        raise LoopContractError("migration snapshot tasks must be a list of objects")
    source_by_id = {task.get("id"): task for task in source_tasks}
    if len(source_by_id) != len(source_tasks) or set(source_by_id) != set(tasks):
        raise LoopContractError("migration snapshot task ids must exactly match the task manifest")

    migrated_tasks = copy.deepcopy(tasks)
    claims: dict[str, dict[str, Any]] = {}
    status_mapping = {"claimed": "ready", "unsafe": "blocked", "accepted": "done"}
    for task_id, source_task in source_by_id.items():
        old_status = source_task.get("status")
        if old_status not in V1_MIGRATION_STATUSES:
            raise LoopContractError(f"migration snapshot task {task_id} has unsupported status")
        target_status = status_mapping.get(old_status, old_status)
        evidence = source_task.get("evidence") or {}
        if not isinstance(evidence, dict):
            raise LoopContractError(f"migration snapshot task {task_id} evidence must be an object")
        blocker = source_task.get("blocker") or {}
        if not isinstance(blocker, dict):
            raise LoopContractError(f"migration snapshot task {task_id} blocker must be an object")
        if old_status == "unsafe":
            blocker = {
                "reason": blocker.get("reason") or "migrated safety blocker",
                "kind": "safety",
            }
        if old_status == "reviewing":
            target_status = "blocked"
            blocker = {
                "reason": "migrated V1 reviewing state requires a new fenced claim before review resumes",
                "kind": "migration",
            }
        definition = migrated_tasks[task_id].get("definition") or {}
        if target_status in {"done", "accepted"} and (
            definition.get("review_required") is True
            or definition.get("human_gate_required") is True
        ):
            raise LoopContractError(
                f"migration task {task_id} requires new protected review or human gate evidence"
            )
        migrated_tasks[task_id]["status"] = target_status
        migrated_tasks[task_id]["evidence"] = copy.deepcopy(evidence)
        migrated_tasks[task_id]["blocker"] = copy.deepcopy(blocker)

        if old_status in {"claimed", "in_progress"}:
            old_claim = source_task.get("claim") or {}
            owner = copy.deepcopy(source_task.get("owner") or {})
            if not isinstance(old_claim, dict) or not isinstance(owner, dict):
                raise LoopContractError(f"migration snapshot task {task_id} requires owner and claim")
            if owner.get("type") not in {
                "current_session",
                "subagent",
                "codex_thread",
                "maintainer",
            }:
                owner["type"] = "subagent"
            claimed_at = old_claim.get("claimed_at") or source_revision_v1.get("updated_at")
            lease_expires_at = old_claim.get("lease_expires_at")
            if not owner.get("id") or not old_claim.get("lease_id"):
                raise LoopContractError(f"migration snapshot task {task_id} has incomplete claim identity")
            if _datetime(lease_expires_at, "migration lease_expires_at") <= _datetime(
                claimed_at, "migration claimed_at"
            ):
                raise LoopContractError("migration claim lease must expire after it is acquired")
            if _datetime(lease_expires_at, "migration lease_expires_at") <= _datetime(
                occurred_at, "migration occurred_at"
            ):
                raise LoopContractError("migration cannot preserve an already expired active claim")
            claims[task_id] = {
                "task_id": task_id,
                "status": "active",
                "owner": owner,
                "fencing_token": {"generation": 1, "nonce": old_claim["lease_id"]},
                "expected_state_revision": 0,
                "source_revision": {
                    field: source_revision.get(field)
                    for field in ("branch", "head_sha", "spec_sha256", "task_manifest_sha256")
                },
                "claimed_at": claimed_at,
                "lease_expires_at": lease_expires_at,
            }
    for task_id, task in migrated_tasks.items():
        if task.get("status") not in {"ready", "in_progress", "reviewing", "done", "accepted"}:
            continue
        dependencies = (task.get("definition") or {}).get("dependencies") or []
        incomplete = [
            dependency
            for dependency in dependencies
            if migrated_tasks.get(dependency, {}).get("status") not in {"done", "accepted"}
        ]
        if incomplete:
            raise LoopContractError(
                f"migration snapshot task {task_id} has incomplete dependencies: "
                + ", ".join(sorted(incomplete))
            )
    return migrated_tasks, claims


def _apply_event(
    state: dict[str, Any],
    event: dict[str, Any],
    *,
    trusted_authority: dict[str, Any] | None,
    enforce_live_authority: bool,
) -> tuple[dict[str, Any], bool]:
    """Apply one event with revision, hash-chain, and idempotency checks.

    Returns ``(new_state, replayed)``. The input state is never mutated.
    """
    key = event.get("idempotency_key")
    if not isinstance(key, str) or not key:
        raise LoopContractError("event requires idempotency_key")
    for field in ("event_id", "actor", "occurred_at"):
        if event.get(field) in (None, ""):
            raise LoopContractError(f"event requires {field}")
    event_type = event.get("type")
    if event_type not in EVENT_TYPES:
        raise LoopContractError(f"unsupported event type: {event_type!r}")
    if event.get("event_hash") != calculate_event_hash(event):
        raise LoopContractError("event hash is invalid")
    request_hash = digest({k: v for k, v in event.items() if k != "event_hash"})
    prior = (state.get("idempotency") or {}).get(key)
    if prior:
        if prior != request_hash:
            raise LoopContractError("idempotency key reused with different payload")
        return copy.deepcopy(state), True
    if state.get("objective_status") == "complete":
        raise LoopContractError("objective completion is terminal")
    revision = state.get("revision", 0)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise LoopContractError("state revision must be a non-negative integer")
    expected_revision = event.get("expected_state_revision")
    if not isinstance(expected_revision, int) or isinstance(expected_revision, bool):
        raise LoopContractError("event expected_state_revision must be an integer")
    if expected_revision != revision:
        raise LoopContractError("stale expected_state_revision")
    sequence = event.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        raise LoopContractError("event sequence must be an integer")
    if sequence != revision + 1:
        raise LoopContractError("event sequence does not follow state revision")
    if event.get("previous_event_hash") != state.get("last_event_hash"):
        raise LoopContractError("event hash chain mismatch")
    if any(item.get("event_id") == event["event_id"] for item in state.get("events", [])):
        raise LoopContractError("event_id already exists")
    prior_events = state.get("events") or []
    if prior_events and _datetime(event.get("occurred_at"), "event occurred_at") < _datetime(
        prior_events[-1].get("occurred_at"), "previous event occurred_at"
    ):
        raise LoopContractError("event occurred_at must not move backwards")
    _datetime(event.get("occurred_at"), "event occurred_at")

    updated = copy.deepcopy(state)
    tasks = updated.setdefault("tasks", {})
    claims = updated.setdefault("claims", {})
    task_id = event.get("task_id")
    payload = event.get("payload") or {}
    if not isinstance(payload, dict):
        raise LoopContractError("event payload must be an object")
    if enforce_live_authority:
        _require_live_authorization(event, trusted_authority=trusted_authority)
    if event_type == "migration_snapshot":
        if revision != 0 or state.get("events") or state.get("claims") or state.get("gates"):
            raise LoopContractError("migration snapshot must be the first event in an empty V2 history")
        if task_id not in {None, ""}:
            raise LoopContractError("migration snapshot must not target one task")
        source_document = payload.get("source_ledger")
        source_hash = payload.get("source_ledger_sha256")
        if not isinstance(source_document, dict) or source_hash != digest(source_document):
            raise LoopContractError("migration snapshot embedded source hash is invalid")
        if source_hash != (state.get("source_revision") or {}).get("migration_source_sha256"):
            raise LoopContractError("migration snapshot provenance does not match migration_source_sha256")
        migrated_tasks, migrated_claims = materialize_v1_snapshot(
            source_document,
            tasks,
            state.get("source_revision") or {},
            event.get("occurred_at"),
        )
        updated["tasks"] = migrated_tasks
        updated["claims"] = migrated_claims
    elif event_type == "task_transition":
        if not isinstance(task_id, str) or task_id not in tasks:
            raise LoopContractError("task transition references unknown task")
        task = tasks[task_id]
        target = payload.get("target_status")
        active_claim = claims.get(task_id) or {}
        if active_claim.get("status") == "active":
            owner = active_claim.get("owner") or {}
            if event.get("actor") != owner.get("id"):
                raise LoopContractError("task transition requires the active claim owner")
            if payload.get("fencing_token") != active_claim.get("fencing_token"):
                raise LoopContractError("task transition requires the current fencing token")
            if _datetime(active_claim.get("lease_expires_at"), "claim lease_expires_at") <= _datetime(
                event.get("occurred_at"), "event occurred_at"
            ):
                raise LoopContractError("task transition requires an unexpired claim lease")
        elif task.get("status") in {"in_progress", "reviewing"}:
            raise LoopContractError("in-flight task transition requires an active fenced claim")
        if target == "in_progress":
            if active_claim.get("status") != "active":
                raise LoopContractError("in_progress requires an active fenced claim")
        guard_evidence = copy.deepcopy(payload.get("evidence") or {})
        if not isinstance(guard_evidence, dict):
            raise LoopContractError("task transition evidence must be an object")
        if isinstance(payload.get("blocker"), dict):
            guard_evidence["blocker_reason"] = payload["blocker"].get("reason")
        if payload.get("human_gate") is not None:
            guard_evidence["human_gate"] = payload["human_gate"]
        task_definition = copy.deepcopy(task.get("definition") or {})
        dependencies = task_definition.get("dependencies") or []
        task_definition["dependencies_satisfied"] = all(
            tasks.get(dependency, {}).get("status") in {"done", "accepted"}
            for dependency in dependencies
        )
        required_gate = task_definition.get("human_gate_name")
        task_definition["human_gate_satisfied"] = bool(
            isinstance(required_gate, str)
            and (updated.get("gates") or {}).get(required_gate, {}).get("status")
            == "satisfied"
        )
        if task_definition.get("human_gate_required") is True:
            guard_evidence["human_gate"] = (
                "satisfied"
                if task_definition["human_gate_satisfied"]
                else "pending"
            )
        if target == "done" and _evidence_status(guard_evidence, "review") == "passed":
            _require_bound_authorization(
                state,
                event,
                payload,
                action="task_completion",
                allowed_principal_types={"user", "platform"},
                scope={"task_id": task_id},
                evidence_artifact=_review_artifact(guard_evidence),
                principal_must_match_actor=False,
            )
        if target == "accepted":
            _require_bound_authorization(
                state,
                event,
                payload,
                action="task_acceptance",
                allowed_principal_types={"user", "platform"},
                scope={"task_id": task_id},
                evidence_artifact=_acceptance_artifact(guard_evidence),
            )
        validate_transition(
            task.get("status"),
            target,
            task_definition=task_definition,
            evidence=guard_evidence,
            claim=active_claim,
        )
        task["status"] = target
        if payload.get("evidence") is not None:
            task["evidence"] = copy.deepcopy(payload["evidence"])
        if target == "blocked":
            task["blocker"] = copy.deepcopy(payload.get("blocker") or {})
        elif task.get("blocker"):
            task["blocker"] = {"kind": "none", "reason": ""}
    elif event_type == "claim_acquired":
        if not isinstance(task_id, str) or task_id not in tasks:
            raise LoopContractError("claim references unknown task")
        if tasks[task_id].get("status") != "ready":
            raise LoopContractError("claim acquisition requires a ready task")
        claim = payload.get("claim")
        if not isinstance(claim, dict) or claim.get("status") != "active":
            raise LoopContractError("claim acquisition requires an active claim")
        if claim.get("task_id") != task_id:
            raise LoopContractError("claim payload task_id mismatch")
        claim_expected_revision = claim.get("expected_state_revision")
        if (
            not isinstance(claim_expected_revision, int)
            or isinstance(claim_expected_revision, bool)
        ):
            raise LoopContractError("claim expected_state_revision must be an integer")
        if claim_expected_revision != revision:
            raise LoopContractError("claim expected_state_revision is stale")
        source_revision = claim.get("source_revision")
        if not isinstance(source_revision, dict):
            raise LoopContractError("claim requires source_revision")
        for field in ("branch", "head_sha", "spec_sha256", "task_manifest_sha256"):
            if source_revision.get(field) != (state.get("source_revision") or {}).get(field):
                raise LoopContractError(f"claim source_revision mismatch: {field}")
        owner = claim.get("owner") or {}
        token = claim.get("fencing_token") or {}
        generation = token.get("generation")
        if (
            not owner.get("id")
            or not isinstance(generation, int)
            or isinstance(generation, bool)
        ):
            raise LoopContractError("claim requires owner and fencing generation")
        if event.get("actor") != owner.get("id"):
            raise LoopContractError("claim acquisition actor must match claim owner")
        if generation < 1 or not token.get("nonce"):
            raise LoopContractError("claim requires a positive generation and unique nonce")
        if not claim.get("claimed_at") or not claim.get("lease_expires_at"):
            raise LoopContractError("claim requires claimed_at and lease_expires_at")
        if _datetime(claim["lease_expires_at"], "claim lease_expires_at") <= _datetime(
            claim["claimed_at"], "claim claimed_at"
        ):
            raise LoopContractError("claim lease must expire after it is acquired")
        if _datetime(claim["lease_expires_at"], "claim lease_expires_at") <= _datetime(
            event.get("occurred_at"), "event occurred_at"
        ):
            raise LoopContractError("cannot acquire an already expired claim")
        previous_claim = claims.get(task_id) or {}
        if previous_claim.get("status") == "active":
            raise LoopContractError("task already has an active claim")
        previous_generation = (previous_claim.get("fencing_token") or {}).get("generation", 0)
        if generation <= previous_generation:
            raise LoopContractError("claim fencing generation must increase")
        claims[task_id] = copy.deepcopy(claim)
    elif event_type in {"claim_released", "claim_expired", "claim_revoked"}:
        if not isinstance(task_id, str) or task_id not in tasks:
            raise LoopContractError("claim update references unknown task")
        claim = claims.get(task_id) or {}
        if claim.get("status") != "active":
            raise LoopContractError("claim update requires an active claim")
        if payload.get("fencing_token") != claim.get("fencing_token"):
            raise LoopContractError("claim update requires the current fencing token")
        owner = claim.get("owner") or {}
        if event_type == "claim_released" and event.get("actor") != owner.get("id"):
            raise LoopContractError("claim release requires the active claim owner")
        if event_type == "claim_expired" and _datetime(
            event.get("occurred_at"), "event occurred_at"
        ) < _datetime(claim.get("lease_expires_at"), "claim lease_expires_at"):
            raise LoopContractError("claim expiry requires reaching the lease deadline")
        if event_type == "claim_revoked":
            blocker = payload.get("blocker") or {}
            _require_bound_authorization(
                state,
                event,
                payload,
                action="claim_revocation",
                allowed_principal_types={"user", "coordinator"},
                scope={"task_id": task_id},
                evidence_artifact=blocker.get("artifact"),
            )
        if event_type == "claim_released" and tasks[task_id].get("status") in {
            "in_progress",
            "reviewing",
        }:
            raise LoopContractError("release claim only after work leaves the in-flight lifecycle")
        claim["status"] = {
            "claim_released": "released",
            "claim_expired": "expired",
            "claim_revoked": "revoked",
        }[event_type]
        if event_type in {"claim_expired", "claim_revoked"}:
            blocker = payload.get("blocker")
            if not isinstance(blocker, dict) or not blocker.get("reason"):
                raise LoopContractError("claim expiry or revocation requires blocker evidence")
            tasks[task_id]["status"] = "blocked"
            tasks[task_id]["blocker"] = copy.deepcopy(blocker)
    elif event_type == "gate_updated":
        gate_name = payload.get("gate")
        gate_status = payload.get("status")
        if not isinstance(gate_name, str) or not gate_name:
            raise LoopContractError("gate update requires gate name")
        if gate_status not in {"not_required", "pending", "satisfied", "blocked"}:
            raise LoopContractError("gate update has unsupported status")
        if gate_status in {"not_required", "satisfied"}:
            evidence = payload.get("evidence") or {}
            if not isinstance(evidence, dict):
                raise LoopContractError("gate authorization evidence must be an object")
            _require_bound_authorization(
                state,
                event,
                payload,
                action="gate_satisfaction",
                allowed_principal_types={"user", "platform"},
                scope={"gate": gate_name},
                evidence_artifact=evidence.get("artifact"),
            )
        updated.setdefault("gates", {})[gate_name] = copy.deepcopy(payload)
    elif event_type == "objective_completed":
        nonterminal = [
            item_id
            for item_id, task in tasks.items()
            if task.get("status") not in {"done", "accepted", "cancelled"}
        ]
        if nonterminal:
            raise LoopContractError(
                "objective completion requires terminal tasks: " + ", ".join(sorted(nonterminal))
            )
        if payload.get("verification") != "passed":
            raise LoopContractError("objective completion requires passed verification")
        if payload.get("review") not in {"not_required", "passed"}:
            raise LoopContractError("objective completion requires satisfied review evidence")
        if payload.get("human_gate") not in {"not_required", "satisfied"}:
            raise LoopContractError("objective completion requires satisfied human gates")
        evidence = payload.get("evidence") or {}
        if not isinstance(evidence, dict):
            raise LoopContractError("objective completion evidence must be an object")
        _require_bound_authorization(
            state,
            event,
            payload,
            action="objective_completion",
            allowed_principal_types={"user", "platform"},
            evidence_artifact=evidence.get("artifact"),
        )
        updated["objective_status"] = "complete"
    updated["revision"] = revision + 1
    updated["last_event_hash"] = event["event_hash"]
    updated.setdefault("events", []).append(copy.deepcopy(event))
    updated.setdefault("idempotency", {})[key] = request_hash
    return updated, False


def apply_event(
    state: dict[str, Any],
    event: dict[str, Any],
    *,
    trusted_authority: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Apply a live event, requiring out-of-band authority for protected actions."""
    return _apply_event(
        state,
        event,
        trusted_authority=trusted_authority,
        enforce_live_authority=True,
    )


def replay_event(
    state: dict[str, Any], event: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Replay a durable event for integrity checks without authenticating its origin.

    This function must never be used as the write boundary for a new event.
    """
    return _apply_event(
        state,
        event,
        trusted_authority=None,
        enforce_live_authority=False,
    )
