"""Strict context-health and fresh-rollover assessment contract."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


CONTRACT_VERSION = "loop-context-continuity/v1"
DECISIONS = {
    "continue-current-context",
    "reground-current-context",
    "delegate-bounded-subagent",
    "prepare-fresh-rollover",
    "stop-for-human-gate",
}
SURFACES = {"desktop", "cli", "ide"}
CONTROL_SURFACES = {"desktop-thread", "cli-exec", "none"}
MODES = {"interactive", "non-interactive"}
WORKTREE_STATES = {"clean", "dirty"}
GRAPH_STATES = {"absent", "advisory-consistent", "advisory-conflicting"}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
HEX_HEAD = re.compile(r"^[0-9a-f]{40}$")


class ContinuityContractError(ValueError):
    """Raised when continuity input is malformed or unsafe."""


def _object(value: Any, label: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContinuityContractError(f"{label} must be an object")
    unknown = set(value) - fields
    if unknown:
        raise ContinuityContractError(
            f"{label} contains unknown field(s): {', '.join(sorted(map(str, unknown)))}"
        )
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 512:
        raise ContinuityContractError(f"{label} must be a bounded non-empty string")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ContinuityContractError(f"{label} must be boolean")
    return value


def _integer(value: Any, label: str, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContinuityContractError(
            f"{label} must be an integer from {minimum} to {maximum}"
        )
    return value


def _enum(value: Any, label: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ContinuityContractError(
            f"{label} must be one of: {', '.join(sorted(allowed))}"
        )
    return value


def _optional_digest(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or HEX_SHA256.fullmatch(value) is None:
        raise ContinuityContractError(f"{label} must be null or a lowercase SHA-256")
    return value


def _bounded_strings(value: Any, label: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list) or len(value) > 128:
        raise ContinuityContractError(f"{label} must be a list with at most 128 items")
    result = [_string(item, f"{label} item") for item in value]
    if required and not result:
        raise ContinuityContractError(f"{label} must not be empty")
    return result


def canonical_checkpoint(checkpoint: dict[str, Any]) -> bytes:
    return json.dumps(
        checkpoint, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def checkpoint_sha256(checkpoint: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_checkpoint(checkpoint)).hexdigest()


def _validate_checkpoint(value: Any, objective_id: str) -> tuple[dict[str, Any] | None, bool]:
    if value is None:
        return None, False
    checkpoint = _object(
        value,
        "checkpoint",
        {
            "checkpoint_id",
            "objective_id",
            "repository_id",
            "branch",
            "head_sha",
            "worktree_state",
            "completed",
            "remaining",
            "verification",
            "risks",
            "next_packet",
            "source_writer",
            "destination_writer",
            "source_stop_writing_confirmed",
        },
    )
    _string(checkpoint.get("checkpoint_id"), "checkpoint.checkpoint_id")
    if _string(checkpoint.get("objective_id"), "checkpoint.objective_id") != objective_id:
        raise ContinuityContractError("checkpoint objective_id must match the assessment")
    _string(checkpoint.get("repository_id"), "checkpoint.repository_id")
    _string(checkpoint.get("branch"), "checkpoint.branch")
    head = checkpoint.get("head_sha")
    if not isinstance(head, str) or HEX_HEAD.fullmatch(head) is None:
        raise ContinuityContractError("checkpoint.head_sha must be a lowercase 40-hex Git SHA")
    _enum(
        checkpoint.get("worktree_state"),
        "checkpoint.worktree_state",
        WORKTREE_STATES,
    )
    _bounded_strings(checkpoint.get("completed"), "checkpoint.completed")
    _bounded_strings(checkpoint.get("remaining"), "checkpoint.remaining", required=True)
    _bounded_strings(checkpoint.get("verification"), "checkpoint.verification", required=True)
    _bounded_strings(checkpoint.get("risks"), "checkpoint.risks")
    _string(checkpoint.get("next_packet"), "checkpoint.next_packet")
    source = _string(checkpoint.get("source_writer"), "checkpoint.source_writer")
    destination = _string(
        checkpoint.get("destination_writer"), "checkpoint.destination_writer"
    )
    if source == destination:
        raise ContinuityContractError("checkpoint writers must be distinct")
    stopped = _boolean(
        checkpoint.get("source_stop_writing_confirmed"),
        "checkpoint.source_stop_writing_confirmed",
    )
    return checkpoint, stopped


METRIC_FIELDS = {
    "objective_total_tokens",
    "wall_time_seconds",
    "repeated_reads",
    "review_fix_rounds",
    "stale_context_errors",
    "blockers",
    "handoff_bootstrap_tokens",
    "quality_score",
}


def _metrics(value: Any, label: str) -> dict[str, int | None]:
    item = _object(value, label, METRIC_FIELDS)
    result: dict[str, int | None] = {}
    for field in METRIC_FIELDS:
        raw = item.get(field)
        if raw is None and field in {"objective_total_tokens", "wall_time_seconds", "quality_score"}:
            result[field] = None
        else:
            result[field] = _integer(raw, f"{label}.{field}")
    return result


def _comparison(value: Any) -> tuple[dict[str, Any], bool]:
    comparison = _object(value, "comparison", {"same_context", "fresh_rollover"})
    same = _metrics(comparison.get("same_context"), "comparison.same_context")
    fresh = _metrics(comparison.get("fresh_rollover"), "comparison.fresh_rollover")
    for label, item in (("same_context", same), ("fresh_rollover", fresh)):
        total = item["objective_total_tokens"]
        if total is not None and item["handoff_bootstrap_tokens"] > total:
            raise ContinuityContractError(
                f"comparison.{label}.handoff_bootstrap_tokens cannot exceed objective_total_tokens"
            )
    measured = all(
        item[field] is not None
        for item in (same, fresh)
        for field in ("objective_total_tokens", "wall_time_seconds", "quality_score")
    )
    qualified = bool(
        measured
        and fresh["objective_total_tokens"] <= same["objective_total_tokens"]
        and fresh["quality_score"] >= same["quality_score"]
        and fresh["stale_context_errors"] <= same["stale_context_errors"]
        and fresh["blockers"] <= same["blockers"]
    )
    return {"same_context": same, "fresh_rollover": fresh, "measured": measured}, qualified


def assess(document: dict[str, Any]) -> dict[str, Any]:
    root = _object(
        document,
        "document",
        {
            "contract_version",
            "assessment_id",
            "objective_id",
            "repository_id",
            "review_fix",
            "signals",
            "runtime",
            "worktree",
            "ownership",
            "checkpoint",
            "lineage",
            "comparison",
        },
    )
    if root.get("contract_version") != CONTRACT_VERSION:
        raise ContinuityContractError(f"contract_version must be {CONTRACT_VERSION}")
    assessment_id = _string(root.get("assessment_id"), "assessment_id")
    objective_id = _string(root.get("objective_id"), "objective_id")
    repository_id = _string(root.get("repository_id"), "repository_id")

    review_fix = _object(
        root.get("review_fix"), "review_fix", {"completed_rounds", "assessment_trigger_rounds"}
    )
    rounds = _integer(review_fix.get("completed_rounds"), "review_fix.completed_rounds", 0, 100)
    trigger = _integer(
        review_fix.get("assessment_trigger_rounds"),
        "review_fix.assessment_trigger_rounds",
        1,
        100,
    )
    trigger_reached = rounds >= trigger

    signals = _object(
        root.get("signals"),
        "signals",
        {
            "stale_findings",
            "repeated_reads",
            "phase_boundary",
            "compaction_or_token_pressure",
            "independent_high_noise_packet",
            "current_context_can_reground",
            "human_gate_required",
        },
    )
    stale = _integer(signals.get("stale_findings"), "signals.stale_findings")
    repeated = _integer(signals.get("repeated_reads"), "signals.repeated_reads")
    phase_boundary = _boolean(signals.get("phase_boundary"), "signals.phase_boundary")
    token_pressure = _boolean(
        signals.get("compaction_or_token_pressure"),
        "signals.compaction_or_token_pressure",
    )
    high_noise = _boolean(
        signals.get("independent_high_noise_packet"),
        "signals.independent_high_noise_packet",
    )
    can_reground = _boolean(
        signals.get("current_context_can_reground"),
        "signals.current_context_can_reground",
    )
    human_gate = _boolean(
        signals.get("human_gate_required"), "signals.human_gate_required"
    )

    runtime = _object(root.get("runtime"), "runtime", {"surface", "control_surface", "mode"})
    surface = _enum(runtime.get("surface"), "runtime.surface", SURFACES)
    control = _enum(runtime.get("control_surface"), "runtime.control_surface", CONTROL_SURFACES)
    mode = _enum(runtime.get("mode"), "runtime.mode", MODES)
    if surface == "desktop" and control not in {"desktop-thread", "none"}:
        raise ContinuityContractError("Desktop may use only desktop-thread or none")
    if surface == "cli" and control not in {"cli-exec", "none"}:
        raise ContinuityContractError("CLI may use only cli-exec or none")
    if surface == "ide" and control != "none":
        raise ContinuityContractError("IDE has no qualified independent task control surface")

    worktree = _object(root.get("worktree"), "worktree", {"state"})
    worktree_state = _enum(worktree.get("state"), "worktree.state", WORKTREE_STATES)
    ownership = _object(
        root.get("ownership"),
        "ownership",
        {"source_writer", "exclusive_transfer_ready", "parallel_packet_disjoint"},
    )
    source_writer = _string(ownership.get("source_writer"), "ownership.source_writer")
    exclusive = _boolean(
        ownership.get("exclusive_transfer_ready"), "ownership.exclusive_transfer_ready"
    )
    disjoint = _boolean(
        ownership.get("parallel_packet_disjoint"), "ownership.parallel_packet_disjoint"
    )

    checkpoint, source_stopped = _validate_checkpoint(root.get("checkpoint"), objective_id)
    digest = checkpoint_sha256(checkpoint) if checkpoint is not None else None
    if checkpoint is not None:
        if checkpoint["repository_id"] != repository_id:
            raise ContinuityContractError("checkpoint repository_id must match the assessment")
        if checkpoint["source_writer"] != source_writer:
            raise ContinuityContractError("checkpoint source_writer must match ownership")
        if checkpoint["worktree_state"] != worktree_state:
            raise ContinuityContractError(
                "checkpoint worktree_state must match the assessment"
            )

    lineage = _object(
        root.get("lineage"),
        "lineage",
        {
            "rollover_id",
            "prior_rollover_id",
            "prior_checkpoint_sha256",
            "progress_since_prior_rollover",
            "progress_evidence",
            "seen_rollovers",
            "graph_projection",
        },
    )
    rollover_id = _string(lineage.get("rollover_id"), "lineage.rollover_id")
    prior_rollover = lineage.get("prior_rollover_id")
    if prior_rollover is not None:
        prior_rollover = _string(prior_rollover, "lineage.prior_rollover_id")
    prior_checkpoint = _optional_digest(
        lineage.get("prior_checkpoint_sha256"), "lineage.prior_checkpoint_sha256"
    )
    if (prior_rollover is None) != (prior_checkpoint is None):
        raise ContinuityContractError(
            "prior_rollover_id and prior_checkpoint_sha256 must be present together"
        )
    if prior_rollover == rollover_id:
        raise ContinuityContractError("rollover_id must differ from prior_rollover_id")
    progress = _boolean(
        lineage.get("progress_since_prior_rollover"),
        "lineage.progress_since_prior_rollover",
    )
    progress_evidence = _bounded_strings(
        lineage.get("progress_evidence"), "lineage.progress_evidence"
    )
    if progress and not progress_evidence:
        raise ContinuityContractError(
            "lineage.progress_evidence must not be empty when progress is true"
        )
    graph = _enum(lineage.get("graph_projection"), "lineage.graph_projection", GRAPH_STATES)
    seen = lineage.get("seen_rollovers")
    if not isinstance(seen, list) or len(seen) > 128:
        raise ContinuityContractError("lineage.seen_rollovers must be a bounded list")
    seen_map: dict[str, str] = {}
    for index, raw in enumerate(seen):
        item = _object(raw, f"lineage.seen_rollovers[{index}]", {"rollover_id", "checkpoint_sha256"})
        seen_id = _string(item.get("rollover_id"), "seen rollover_id")
        seen_digest = _optional_digest(item.get("checkpoint_sha256"), "seen checkpoint_sha256")
        if seen_digest is None:
            raise ContinuityContractError("seen checkpoint_sha256 must not be null")
        if seen_id in seen_map and seen_map[seen_id] != seen_digest:
            raise ContinuityContractError("seen rollover_id has conflicting checkpoint digests")
        seen_map[seen_id] = seen_digest

    if prior_rollover is not None:
        recorded_prior_digest = seen_map.get(prior_rollover)
        if recorded_prior_digest is None:
            raise ContinuityContractError(
                "prior_rollover_id must have durable evidence in seen_rollovers"
            )
        if recorded_prior_digest != prior_checkpoint:
            raise ContinuityContractError(
                "prior_checkpoint_sha256 must match seen_rollovers evidence"
            )
        if digest == prior_checkpoint:
            raise ContinuityContractError(
                "current checkpoint must differ from the prior rollover checkpoint"
            )

    comparison, comparison_qualified = _comparison(root.get("comparison"))
    degraded = stale > 0 or repeated > 0 or phase_boundary
    notices: list[str] = []
    violations: list[str] = []
    decision = "continue-current-context"
    fallback = "none"
    idempotent_replay = False

    if graph == "advisory-conflicting":
        notices.append("graph-lineage-conflict-ignored-as-advisory")
    if token_pressure:
        notices.append("token-or-compaction-signal-is-advisory-only")

    if human_gate:
        decision = "stop-for-human-gate"
        violations.append("human-gate-required")
    elif not trigger_reached:
        notices.append("assessment-trigger-not-reached")
    elif high_noise and disjoint:
        decision = "delegate-bounded-subagent"
    elif not degraded:
        notices.append("assessment-trigger-does-not-imply-rollover")
    else:
        automatic_path = (
            checkpoint is not None
            and source_stopped
            and exclusive
            and progress
            and control != "none"
            and (
                (surface == "desktop" and mode == "non-interactive" and worktree_state == "clean")
                or (surface == "cli" and mode == "non-interactive" and worktree_state == "clean")
            )
        )
        prior_digest = seen_map.get(rollover_id)
        if prior_digest is not None:
            if prior_digest == digest:
                decision = "prepare-fresh-rollover"
                idempotent_replay = True
                notices.append("rollover-idempotent-replay-no-runtime-mutation")
            else:
                decision = "stop-for-human-gate"
                violations.append("rollover-id-reused-with-different-checkpoint")
        elif digest in seen_map.values():
            decision = "stop-for-human-gate"
            violations.append("checkpoint-reused-under-new-rollover-id")
        elif prior_rollover is not None and not progress:
            decision = "stop-for-human-gate"
            violations.append("consecutive-rollover-without-material-progress")
        elif not comparison["measured"]:
            decision = "reground-current-context"
            fallback = "current-session-or-paste-ready-prompt"
            notices.append("measured-rollover-comparison-unavailable")
        elif not comparison_qualified:
            decision = "reground-current-context"
            fallback = "current-session-or-paste-ready-prompt"
            notices.append("measured-rollover-cost-or-quality-regressed")
        elif automatic_path:
            decision = "prepare-fresh-rollover"
        else:
            decision = "reground-current-context"
            if checkpoint is None:
                notices.append("durable-checkpoint-incomplete")
            if not source_stopped:
                notices.append("source-writer-has-not-stopped")
            if not exclusive:
                notices.append("exclusive-transfer-not-ready")
            if worktree_state == "dirty":
                notices.append("dirty-worktree-requires-manual-or-current-context-fallback")
            if mode == "interactive":
                notices.append("interactive-mode-requires-manual-handoff")
            if control == "none":
                notices.append("runtime-control-surface-unavailable")
            fallback = "current-session-or-paste-ready-prompt"
            if not can_reground:
                notices.append("reground-capability-unconfirmed")

    return {
        "contract_version": CONTRACT_VERSION,
        "assessment_id": assessment_id,
        "objective_id": objective_id,
        "decision": decision,
        "assessment_trigger_reached": trigger_reached,
        "assessment_trigger_rounds": trigger,
        "automatic_rollover_authorized": False,
        "runtime_action_performed": False,
        "task_created": False,
        "completion_proven": False,
        "source_of_authority": "repository-git-verification-review-and-accepted-platform-state",
        "checkpoint_sha256": digest,
        "idempotent_replay": idempotent_replay,
        "graph_authority": "advisory-only",
        "comparison": {**comparison, "qualified": comparison_qualified},
        "fallback": fallback,
        "notices": notices,
        "violations": violations,
        "valid_decisions": sorted(DECISIONS),
    }
