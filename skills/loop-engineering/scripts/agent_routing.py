#!/usr/bin/env python3
"""Deterministic, capability-neutral routing for Loop Engineering V2a.

This module selects execution capability only.  It deliberately has no API for
granting authority, changing scope, satisfying gates, or proving completion.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


class AgentRoutingContractError(ValueError):
    """Raised when routing inputs or receipts violate the V2a contract."""


FACTOR_VALUES = {
    "ambiguity": {"low", "moderate", "high"},
    "reasoning_depth": {"shallow", "balanced", "deep"},
    "code_context_volume": {"small", "medium", "large"},
    "security_data_migration_public_contract_risk": {
        "none",
        "routine",
        "high",
        "security",
        "data",
        "migration",
        "public-contract",
    },
    "write_blast_radius": {"none", "bounded", "broad"},
    "latency_sensitivity": {"low", "medium", "high"},
    "cost_token_sensitivity": {"low", "medium", "high"},
    "independence_parallelizability": {"coupled", "bounded", "independent"},
    "verification_burden": {"low", "medium", "high"},
}

CAPABILITY_CLASSES = (
    "fast-read-explorer",
    "balanced-worker",
    "deep-reviewer",
    "security-reviewer",
)

CAPABILITY_TIERS = (
    "mechanical",
    "efficient",
    "everyday",
    "advanced",
    "deep",
    "exceptional",
)
TIER_RANK = {tier: index for index, tier in enumerate(CAPABILITY_TIERS)}
WORKLOAD_KINDS = {
    "mechanical",
    "exploration",
    "implementation",
    "review",
    "security-review",
    "research-orchestration",
}

DEFAULT_ROLES = {
    "fast-read-explorer": "fast-read-explorer",
    "balanced-worker": "balanced-worker",
    "deep-reviewer": "deep-reviewer",
    "security-reviewer": "security-reviewer",
}
TIER_ROLES = {
    ("fast-read-explorer", "mechanical"): "loop_v2a_mechanical_reader",
    ("fast-read-explorer", "efficient"): "loop_v2a_fast_explorer",
    ("balanced-worker", "everyday"): "loop_v2a_balanced_worker",
    ("balanced-worker", "advanced"): "loop_v2a_advanced_worker",
    ("deep-reviewer", "deep"): "loop_v2a_deep_reviewer",
    ("deep-reviewer", "exceptional"): "loop_v2a_exceptional_researcher",
    ("security-reviewer", "deep"): "loop_v2a_security_reviewer",
}

HIGH_RISK_CLASSES = {"deep-reviewer", "security-reviewer"}
WORKER_STATUSES = {"complete", "partial", "failed"}
DISPOSITIONS = {"accepted", "rejected", "deferred", "needs-verification"}
MEMORY_BACKEND_STATUSES = {"disabled", "unavailable", "used", "degraded"}
MEMORY_DISPOSITIONS = {"adopt-as-context", "reject", "quarantine", "ignore"}
CLASS_SANDBOX = {
    "fast-read-explorer": "read-only",
    "balanced-worker": "workspace-write",
    "deep-reviewer": "read-only",
    "security-reviewer": "read-only",
}
SANDBOX_RANK = {"read-only": 0, "workspace-write": 1, "danger-full-access": 2}
CLASS_WORKFLOW_SCOPE = {
    "fast-read-explorer": {"read", "search", "summarize", "report-receipt"},
    "balanced-worker": {
        "read",
        "search",
        "bounded-edit",
        "focused-verify",
        "report-receipt",
    },
    "deep-reviewer": {
        "read",
        "search",
        "verify",
        "report-findings",
        "report-receipt",
    },
    "security-reviewer": {
        "read",
        "search",
        "validate",
        "defensive-control-analysis",
        "report-findings",
        "report-receipt",
    },
}


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AgentRoutingContractError(f"{label} must be an object")
    return value


def validate_task_factors(factors: dict[str, Any]) -> dict[str, str]:
    """Validate and return the exact nine capability-neutral task factors."""
    factors = _require_object(factors, "task factors")
    missing = sorted(set(FACTOR_VALUES) - set(factors))
    unknown = sorted(set(factors) - set(FACTOR_VALUES))
    if missing:
        raise AgentRoutingContractError(
            "task factors missing required fields: " + ",".join(missing)
        )
    if unknown:
        raise AgentRoutingContractError(
            "task factors contain unknown fields: " + ",".join(unknown)
        )
    validated: dict[str, str] = {}
    for name, allowed in FACTOR_VALUES.items():
        value = factors[name]
        if not isinstance(value, str) or value not in allowed:
            raise AgentRoutingContractError(
                f"task factor {name} must be one of: {','.join(sorted(allowed))}"
            )
        validated[name] = value
    return validated


def classify_task(
    factors: dict[str, Any],
    *,
    contract_version: int = 1,
    workload_kind: str | None = None,
) -> dict[str, Any]:
    """Classify capability needs using deterministic, non-compensatory triggers."""
    factors = validate_task_factors(factors)
    if type(contract_version) is not int or contract_version not in {1, 2}:
        raise AgentRoutingContractError("agent route contract version must be 1 or 2")
    if contract_version == 1:
        if workload_kind is not None:
            raise AgentRoutingContractError(
                "version 1 routing does not accept workload_kind"
            )
        return _classify_v1(factors)
    if not isinstance(workload_kind, str) or workload_kind not in WORKLOAD_KINDS:
        raise AgentRoutingContractError(
            "version 2 workload_kind must be one of: "
            + ",".join(sorted(WORKLOAD_KINDS))
        )
    return _classify_v2(factors, workload_kind)


def _factor_effects(factors: dict[str, str]) -> dict[str, str]:
    risk = factors["security_data_migration_public_contract_risk"]
    blast = factors["write_blast_radius"]
    return {
        "ambiguity": (
            "deep-capability-trigger" if factors["ambiguity"] == "high" else "no-escalation"
        ),
        "reasoning_depth": (
            "deep-capability-trigger"
            if factors["reasoning_depth"] == "deep"
            else "no-escalation"
        ),
        "code_context_volume": (
            "fast-read-tie-break" if factors["code_context_volume"] == "large" else "neutral"
        ),
        "security_data_migration_public_contract_risk": (
            "security-hard-trigger"
            if risk == "security"
            else (
                "deep-hard-trigger"
                if risk in {"data", "migration", "public-contract", "high"}
                else "no-hard-trigger"
            )
        ),
        "write_blast_radius": (
            "deep-hard-trigger"
            if blast == "broad"
            else ("read-only-fast-eligible" if blast == "none" else "bounded-write")
        ),
        "latency_sensitivity": (
            "fast-read-tie-break" if factors["latency_sensitivity"] == "high" else "neutral"
        ),
        "cost_token_sensitivity": (
            "fast-read-tie-break"
            if factors["cost_token_sensitivity"] == "high"
            else "neutral"
        ),
        "independence_parallelizability": (
            "requires-sequential-current-session"
            if factors["independence_parallelizability"] == "coupled"
            else "delegation-eligible"
        ),
        "verification_burden": (
            "deep-capability-trigger"
            if factors["verification_burden"] == "high"
            else "no-escalation"
        ),
    }


def _classify_v1(factors: dict[str, str]) -> dict[str, Any]:
    """Preserve the published V2a version 1 classification exactly."""
    reasons: list[str] = []
    risk = factors["security_data_migration_public_contract_risk"]
    blast = factors["write_blast_radius"]

    if risk == "security":
        capability_class = "security-reviewer"
        reasons.append("security-risk-hard-trigger")
    elif risk in {"data", "migration", "public-contract", "high"}:
        capability_class = "deep-reviewer"
        reasons.append(f"{risk}-risk-hard-trigger")
    elif blast == "broad":
        capability_class = "deep-reviewer"
        reasons.append("broad-write-blast-radius-hard-trigger")
    elif (
        factors["ambiguity"] == "high"
        or factors["reasoning_depth"] == "deep"
        or factors["verification_burden"] == "high"
    ):
        capability_class = "deep-reviewer"
        if factors["ambiguity"] == "high":
            reasons.append("high-ambiguity")
        if factors["reasoning_depth"] == "deep":
            reasons.append("deep-reasoning")
        if factors["verification_burden"] == "high":
            reasons.append("high-verification-burden")
    elif (
        blast == "none"
        and factors["ambiguity"] == "low"
        and factors["reasoning_depth"] == "shallow"
        and factors["verification_burden"] == "low"
        and (
            factors["code_context_volume"] == "large"
            or factors["latency_sensitivity"] == "high"
            or factors["cost_token_sensitivity"] == "high"
        )
    ):
        capability_class = "fast-read-explorer"
        reasons.append("bounded-read-heavy-work")
        if factors["code_context_volume"] == "large":
            reasons.append("large-context-fast-tie-break")
        if factors["latency_sensitivity"] == "high":
            reasons.append("latency-fast-tie-break")
        if factors["cost_token_sensitivity"] == "high":
            reasons.append("cost-token-fast-tie-break")
    else:
        capability_class = "balanced-worker"
        reasons.append("balanced-default")

    return {
        "capability_class": capability_class,
        "selected_role": DEFAULT_ROLES[capability_class],
        "factors": factors,
        "reasons": reasons,
        "factor_effects": _factor_effects(factors),
        "hard_triggered": any(reason.endswith("hard-trigger") for reason in reasons),
    }


def _classify_v2(factors: dict[str, str], workload_kind: str) -> dict[str, Any]:
    """Classify work shape and the minimum cost-aware capability tier."""
    risk = factors["security_data_migration_public_contract_risk"]
    blast = factors["write_blast_radius"]
    quality_triggers = sum(
        (
            factors["ambiguity"] == "high",
            factors["reasoning_depth"] == "deep",
            factors["verification_burden"] == "high",
            factors["code_context_volume"] == "large",
        )
    )
    reasons: list[str] = []

    if risk == "security" or workload_kind == "security-review":
        capability_class, tier = "security-reviewer", "deep"
        reasons.append("security-risk-hard-trigger")
    elif risk in {"data", "migration", "public-contract", "high"} or blast == "broad":
        capability_class, tier = "deep-reviewer", "deep"
        reasons.append(
            "broad-write-blast-radius-hard-trigger"
            if blast == "broad"
            else f"{risk}-risk-hard-trigger"
        )
    elif (
        workload_kind == "research-orchestration"
        and blast == "none"
        and quality_triggers >= 3
    ):
        capability_class, tier = "deep-reviewer", "exceptional"
        reasons.extend(["explicit-research-orchestration", "quality-first-exceptional-trigger"])
    elif workload_kind == "implementation":
        capability_class = "balanced-worker"
        if blast != "bounded":
            raise AgentRoutingContractError(
                "version 2 implementation workload requires bounded write_blast_radius"
            )
        if (
            factors["ambiguity"] == "high"
            or factors["reasoning_depth"] == "deep"
            or factors["verification_burden"] == "high"
        ):
            tier = "advanced"
            reasons.append("advanced-bounded-implementation")
        else:
            tier = "everyday"
            reasons.append("routine-bounded-implementation")
    elif workload_kind == "mechanical" and (
        blast == "none"
        and risk == "none"
        and factors["ambiguity"] == "low"
        and factors["reasoning_depth"] == "shallow"
        and factors["verification_burden"] == "low"
    ):
        capability_class, tier = "fast-read-explorer", "mechanical"
        reasons.append("clear-repeatable-read-only-work")
    elif workload_kind == "exploration" and blast == "none" and (
        factors["ambiguity"] != "high"
        and factors["reasoning_depth"] != "deep"
        and factors["verification_burden"] != "high"
    ):
        capability_class, tier = "fast-read-explorer", "efficient"
        reasons.append("bounded-read-heavy-work")
    else:
        capability_class, tier = "deep-reviewer", "deep"
        reasons.append("deep-analysis-default")

    return {
        "capability_class": capability_class,
        "capability_tier": tier,
        "selected_role": TIER_ROLES[(capability_class, tier)],
        "workload_kind": workload_kind,
        "factors": factors,
        "reasons": reasons,
        "factor_effects": _factor_effects(factors),
        "hard_triggered": any(reason.endswith("hard-trigger") for reason in reasons),
    }


def _sandbox_is_non_widening(profile: dict[str, Any]) -> bool:
    sandbox = profile.get("sandbox")
    parent = profile.get("parent_sandbox_mode")
    if parent == "unknown-at-least-read-only":
        return sandbox == "read-only"
    return (
        isinstance(sandbox, str)
        and sandbox in SANDBOX_RANK
        and isinstance(parent, str)
        and parent in SANDBOX_RANK
        and SANDBOX_RANK[sandbox] <= SANDBOX_RANK[parent]
    )


def _valid_profile(
    profile: Any, capability_class: str, required_tier: str | None = None
) -> bool:
    profile_digest = profile.get("profile_digest") if isinstance(profile, dict) else None
    workflow_scope = (
        profile.get("allowed_workflow_scope") if isinstance(profile, dict) else None
    )
    return (
        isinstance(profile, dict)
        and profile.get("capability_class") == capability_class
        and (
            required_tier is None
            or (
                isinstance(profile.get("capability_tier"), str)
                and profile.get("capability_tier") in TIER_RANK
                and TIER_RANK[profile["capability_tier"]] >= TIER_RANK[required_tier]
            )
        )
        and profile.get("available") is True
        and profile.get("config_valid") is True
        and profile.get("model_available") is True
        and profile.get("reasoning_available") is True
        and isinstance(profile.get("name"), str)
        and bool(profile["name"])
        and isinstance(profile_digest, str)
        and len(profile_digest) == 64
        and all(character in "0123456789abcdef" for character in profile_digest)
        and profile.get("sandbox") == CLASS_SANDBOX[capability_class]
        and profile.get("sandbox_non_widening") is True
        and _sandbox_is_non_widening(profile)
        and isinstance(workflow_scope, list)
        and all(isinstance(item, str) for item in workflow_scope)
        and len(workflow_scope) == len(set(workflow_scope))
        and set(workflow_scope) == CLASS_WORKFLOW_SCOPE[capability_class]
    )


def _profile_config_evidence(
    profile: dict[str, Any], *, include_tier: bool = False
) -> dict[str, Any]:
    """Project validated runtime/registry facts into receipt-bound evidence."""
    evidence = {
        "name": profile["name"],
        "capability_class": profile["capability_class"],
        "profile_digest": profile["profile_digest"],
        "config_valid": profile["config_valid"],
        "model_available": profile["model_available"],
        "reasoning_available": profile["reasoning_available"],
        "sandbox": profile["sandbox"],
        "parent_sandbox_mode": profile["parent_sandbox_mode"],
        "sandbox_non_widening": profile["sandbox_non_widening"],
        "allowed_workflow_scope": sorted(profile["allowed_workflow_scope"]),
    }
    if include_tier:
        evidence["capability_tier"] = profile["capability_tier"]
    return evidence


def _runtime_route(classification: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    runtime = _require_object(runtime, "runtime capabilities")
    profiles = runtime.get("profiles", [])
    if not isinstance(profiles, list):
        raise AgentRoutingContractError("runtime profiles must be an array")
    capability_class = classification["capability_class"]
    required_tier = classification.get("capability_tier")
    independence = classification["factors"]["independence_parallelizability"]
    parent_classes = runtime.get("parent_capability_classes", [])
    current_classes = runtime.get("current_session_capability_classes", [])
    for value, label in (
        (parent_classes, "parent capability classes"),
        (current_classes, "current session capability classes"),
    ):
        if not isinstance(value, list) or any(
            not isinstance(item, str) or item not in CAPABILITY_CLASSES
            for item in value
        ):
            raise AgentRoutingContractError(f"{label} must be an array of known classes")
    parent_tiers = runtime.get("parent_capability_tiers", {})
    current_tiers = runtime.get("current_session_capability_tiers", {})
    for value, label in (
        (parent_tiers, "parent capability tiers"),
        (current_tiers, "current session capability tiers"),
    ):
        if not isinstance(value, dict) or any(
            not isinstance(key, str)
            or key not in CAPABILITY_CLASSES
            or not isinstance(tiers, list)
            or any(
                not isinstance(tier, str) or tier not in TIER_RANK
                for tier in tiers
            )
            for key, tiers in value.items()
        ):
            raise AgentRoutingContractError(f"{label} must map known classes to known tiers")

    def tier_satisfied(evidence: dict[str, list[str]]) -> bool:
        return required_tier is None or selected_evidence_tier(evidence) is not None

    def selected_evidence_tier(
        evidence: dict[str, list[str]],
    ) -> str | None:
        if required_tier is None:
            return None
        candidates = sorted(
            (
                tier
                for tier in evidence.get(capability_class, [])
                if isinstance(tier, str)
                and tier in TIER_RANK
                and TIER_RANK[tier] >= TIER_RANK[required_tier]
            ),
            key=TIER_RANK.__getitem__,
        )
        return candidates[0] if candidates else None

    def fallback_capability_evidence(
        source: str,
        classes: list[str],
        evidence: dict[str, list[str]],
    ) -> dict[str, Any]:
        selected_tier = selected_evidence_tier(evidence)
        return {
            "source": source,
            "capability_class": capability_class,
            "capability_classes": sorted(set(classes)),
            "class_membership_confirmed": capability_class in classes,
            "capability_tiers": sorted(
                evidence.get(capability_class, []), key=TIER_RANK.__getitem__
            ),
            "selected_capability_tier": selected_tier,
        }

    if independence == "coupled":
        if runtime.get("sequential_available", True) is True:
            route = {
                "execution_mode": "sequential-current-session",
                "runtime_mapping": "current-session",
                "fallback": "sequential-current-session",
                "degraded": False,
                "routing_constraint": "coupled-work-requires-sequential",
                "selected_profile_digest": None,
                "config_evidence_sha256": None,
                "config_evidence": None,
            }
            if required_tier is not None:
                if capability_class not in current_classes or not tier_satisfied(
                    current_tiers
                ):
                    return {
                        "execution_mode": "stop-for-human-gate",
                        "runtime_mapping": "unresolved",
                        "fallback": "human-gate",
                        "degraded": True,
                        "gate_reason": "coupled-work-requires-unavailable-sequential-execution",
                        "selected_profile_digest": None,
                        "config_evidence_sha256": None,
                        "config_evidence": None,
                    }
                selected_tier = selected_evidence_tier(current_tiers)
                fallback_evidence = fallback_capability_evidence(
                    "current-session", current_classes, current_tiers
                )
                route.update(
                    {
                        "required_capability_tier": required_tier,
                        "selected_capability_tier": selected_tier,
                        "cost_degraded": selected_tier != required_tier,
                        "fallback_capability_evidence": fallback_evidence,
                        "fallback_capability_evidence_sha256": _digest(
                            fallback_evidence
                        ),
                    }
                )
            return route
        return {
            "execution_mode": "stop-for-human-gate",
            "runtime_mapping": "unresolved",
            "fallback": "human-gate",
            "degraded": True,
            "gate_reason": "coupled-work-requires-unavailable-sequential-execution",
            "selected_profile_digest": None,
            "config_evidence_sha256": None,
            "config_evidence": None,
        }
    candidates = sorted(
        (
            profile
            for profile in profiles
            if _valid_profile(profile, capability_class, required_tier)
        ),
        key=lambda profile: (
            TIER_RANK.get(profile.get("capability_tier"), -1),
            profile["name"],
        ),
    )
    custom_agents = runtime.get("custom_agents_available")
    if custom_agents is True and candidates:
        profile = candidates[0]
        config_evidence = _profile_config_evidence(
            profile, include_tier=required_tier is not None
        )
        route = {
            "execution_mode": "custom-agent-profile",
            "runtime_mapping": profile["name"],
            "fallback": (
                "same-class-higher-tier"
                if required_tier is not None
                and profile["capability_tier"] != required_tier
                else "none"
            ),
            "degraded": False,
            "routing_constraint": f"{independence}-work-allows-delegation",
            "selected_profile_digest": profile["profile_digest"],
            "config_evidence_sha256": _digest(config_evidence),
            "config_evidence": config_evidence,
        }
        if required_tier is not None:
            route.update(
                {
                    "required_capability_tier": required_tier,
                    "selected_capability_tier": profile["capability_tier"],
                    "cost_degraded": profile["capability_tier"] != required_tier,
                }
            )
        return route

    high_risk = capability_class in HIGH_RISK_CLASSES
    if runtime.get("parent_default_available") is True and (
        (
            capability_class in parent_classes
            if required_tier is not None
            else (not high_risk or capability_class in parent_classes)
        )
        and tier_satisfied(parent_tiers)
    ):
        route = {
            "execution_mode": "parent-default",
            "runtime_mapping": "parent/default",
            "fallback": "parent-default",
            "degraded": True,
            "routing_constraint": f"{independence}-work-allows-delegation",
            "selected_profile_digest": None,
            "config_evidence_sha256": None,
            "config_evidence": None,
        }
        if required_tier is not None:
            selected_tier = selected_evidence_tier(parent_tiers)
            fallback_evidence = fallback_capability_evidence(
                "parent-default", parent_classes, parent_tiers
            )
            route.update({"required_capability_tier": required_tier, "selected_capability_tier": selected_tier, "cost_degraded": selected_tier != required_tier, "fallback_capability_evidence": fallback_evidence, "fallback_capability_evidence_sha256": _digest(fallback_evidence)})
        return route
    if runtime.get("sequential_available", True) is True and (
        (
            capability_class in current_classes
            if required_tier is not None
            else (not high_risk or capability_class in current_classes)
        )
        and tier_satisfied(current_tiers)
    ):
        route = {
            "execution_mode": "sequential-current-session",
            "runtime_mapping": "current-session",
            "fallback": "sequential-current-session",
            "degraded": True,
            "routing_constraint": "runtime-capability-degraded-to-sequential",
            "selected_profile_digest": None,
            "config_evidence_sha256": None,
            "config_evidence": None,
        }
        if required_tier is not None:
            selected_tier = selected_evidence_tier(current_tiers)
            fallback_evidence = fallback_capability_evidence(
                "current-session", current_classes, current_tiers
            )
            route.update({"required_capability_tier": required_tier, "selected_capability_tier": selected_tier, "cost_degraded": selected_tier != required_tier, "fallback_capability_evidence": fallback_evidence, "fallback_capability_evidence_sha256": _digest(fallback_evidence)})
        return route
    return {
        "execution_mode": "stop-for-human-gate",
        "runtime_mapping": "unresolved",
        "fallback": "human-gate",
        "degraded": True,
        "gate_reason": "required-capability-unavailable",
        "selected_profile_digest": None,
        "config_evidence_sha256": None,
        "config_evidence": None,
    }


def build_route_receipt(
    *,
    task_id: str,
    factors: dict[str, Any],
    runtime: dict[str, Any],
    assigned_scope: list[str],
    ownership: dict[str, Any],
    source_revision: dict[str, Any],
    authority_contract: dict[str, Any],
    contract_version: int = 1,
    workload_kind: str | None = None,
) -> dict[str, Any]:
    """Build auditable routing evidence without granting any authority."""
    if not isinstance(task_id, str) or not task_id:
        raise AgentRoutingContractError("task id must be a non-empty string")
    if not isinstance(assigned_scope, list) or not assigned_scope or any(
        not isinstance(path, str) or not path for path in assigned_scope
    ):
        raise AgentRoutingContractError("assigned scope must be a non-empty string array")
    ownership = _require_object(ownership, "ownership")
    source_revision = _require_object(source_revision, "source revision")
    authority_contract = _require_object(authority_contract, "authority contract")
    if ownership.get("disjoint") is not True or not ownership.get("owner"):
        raise AgentRoutingContractError("routing requires explicit disjoint ownership")
    classification = classify_task(
        factors, contract_version=contract_version, workload_kind=workload_kind
    )
    route = _runtime_route(classification, runtime)
    body = {
        "contract_version": contract_version,
        "task_id": task_id,
        "classification": classification,
        "selected_role": classification["selected_role"],
        **route,
        "assigned_scope": list(assigned_scope),
        "assigned_scope_sha256": _digest(assigned_scope),
        "ownership": ownership,
        "source_revision": source_revision,
        "source_revision_sha256": _digest(source_revision),
        "authority_contract_sha256": _digest(authority_contract),
        "authority_invariants": {
            "profile_cannot_expand_scope": True,
            "profile_cannot_expand_permissions": True,
            "profile_cannot_satisfy_human_gates": True,
            "worker_receipt_cannot_prove_completion": True,
        },
    }
    body["route_receipt_id"] = _digest(body)
    return body


def validate_route_receipt(route_receipt: dict[str, Any]) -> dict[str, Any]:
    """Detect stale or modified assignment evidence before consuming it."""
    route_receipt = _require_object(route_receipt, "route receipt")
    issues: list[str] = []
    receipt_id = route_receipt.get("route_receipt_id")
    unsigned = {
        key: value for key, value in route_receipt.items() if key != "route_receipt_id"
    }
    if not isinstance(receipt_id, str) or receipt_id != _digest(unsigned):
        issues.append("route-receipt-integrity-mismatch")
    invariants = route_receipt.get("authority_invariants")
    required_invariants = {
        "profile_cannot_expand_scope": True,
        "profile_cannot_expand_permissions": True,
        "profile_cannot_satisfy_human_gates": True,
        "worker_receipt_cannot_prove_completion": True,
    }
    if invariants != required_invariants:
        issues.append("authority-invariants-missing-or-modified")
    classification = route_receipt.get("classification")
    canonical_classification: dict[str, Any] | None = None
    try:
        contract_version = route_receipt.get("contract_version")
        workload_kind = (
            classification.get("workload_kind")
            if isinstance(classification, dict)
            else None
        )
        if not isinstance(classification, dict):
            issues.append("classification-semantic-mismatch")
        else:
            rebuilt = classify_task(
                classification.get("factors"),
                contract_version=contract_version,
                workload_kind=workload_kind,
            )
            if rebuilt != classification:
                issues.append("classification-semantic-mismatch")
            else:
                canonical_classification = rebuilt
    except AgentRoutingContractError:
        issues.append("classification-semantic-mismatch")
    trusted_classification = canonical_classification or {}
    if canonical_classification is not None and route_receipt.get(
        "selected_role"
    ) != trusted_classification.get("selected_role"):
        issues.append("selected-role-semantic-mismatch")
    assigned_scope = route_receipt.get("assigned_scope")
    if not isinstance(assigned_scope, list) or route_receipt.get("assigned_scope_sha256") != _digest(assigned_scope):
        issues.append("assigned-scope-digest-mismatch")
    source_revision = route_receipt.get("source_revision")
    if not isinstance(source_revision, dict) or route_receipt.get("source_revision_sha256") != _digest(source_revision):
        issues.append("source-revision-digest-mismatch")
    profile_digest = route_receipt.get("selected_profile_digest")
    evidence_sha256 = route_receipt.get("config_evidence_sha256")
    evidence = route_receipt.get("config_evidence")
    execution_mode = route_receipt.get("execution_mode")
    routing_constraint = route_receipt.get("routing_constraint")
    independence = (trusted_classification.get("factors") or {}).get(
        "independence_parallelizability"
    )
    delegation_constraint = f"{independence}-work-allows-delegation"
    is_v2 = route_receipt.get("contract_version") == 2
    tier_contract = (
        not is_v2
        or (
            canonical_classification is not None
            and isinstance(
                trusted_classification.get("capability_tier"), str
            )
            and trusted_classification.get("capability_tier") in TIER_RANK
            and route_receipt.get("required_capability_tier")
            == trusted_classification.get("capability_tier")
            and isinstance(
                route_receipt.get("selected_capability_tier"), str
            )
            and route_receipt.get("selected_capability_tier") in TIER_RANK
            and TIER_RANK[route_receipt["selected_capability_tier"]]
            >= TIER_RANK[trusted_classification["capability_tier"]]
            and isinstance(route_receipt.get("cost_degraded"), bool)
            and route_receipt.get("cost_degraded")
            == (
                route_receipt.get("selected_capability_tier")
                != trusted_classification.get("capability_tier")
            )
        )
    )
    mode_contracts = {
        "custom-agent-profile": (
            isinstance(route_receipt.get("fallback"), str)
            and route_receipt.get("fallback")
            in ({"none", "same-class-higher-tier"} if is_v2 else {"none"})
            and route_receipt.get("degraded") is False
            and isinstance(route_receipt.get("runtime_mapping"), str)
            and independence in {"bounded", "independent"}
            and routing_constraint == delegation_constraint
            and "gate_reason" not in route_receipt
            and tier_contract
            and (
                not is_v2
                or (
                    route_receipt.get("fallback") == "same-class-higher-tier"
                )
                == route_receipt.get("cost_degraded")
            )
        ),
        "parent-default": (
            route_receipt.get("runtime_mapping") == "parent/default"
            and route_receipt.get("fallback") == "parent-default"
            and route_receipt.get("degraded") is True
            and independence in {"bounded", "independent"}
            and routing_constraint == delegation_constraint
            and "gate_reason" not in route_receipt
            and tier_contract
        ),
        "sequential-current-session": (
            route_receipt.get("runtime_mapping") == "current-session"
            and route_receipt.get("fallback") == "sequential-current-session"
            and (
                (independence == "coupled" and route_receipt.get("degraded") is False and routing_constraint == "coupled-work-requires-sequential")
                or (independence in {"bounded", "independent"} and route_receipt.get("degraded") is True and routing_constraint == "runtime-capability-degraded-to-sequential")
            )
            and "gate_reason" not in route_receipt
            and tier_contract
        ),
        "stop-for-human-gate": (
            route_receipt.get("runtime_mapping") == "unresolved"
            and route_receipt.get("fallback") == "human-gate"
            and route_receipt.get("degraded") is True
            and isinstance(route_receipt.get("gate_reason"), str)
            and route_receipt.get("gate_reason") in {
                "required-capability-unavailable",
                "coupled-work-requires-unavailable-sequential-execution",
            }
            and (
                (independence == "coupled" and route_receipt.get("gate_reason") == "coupled-work-requires-unavailable-sequential-execution")
                or (independence in {"bounded", "independent"} and route_receipt.get("gate_reason") == "required-capability-unavailable")
            )
            and routing_constraint is None
        ),
    }
    fallback_capability_evidence = route_receipt.get(
        "fallback_capability_evidence"
    )
    fallback_capability_evidence_sha256 = route_receipt.get(
        "fallback_capability_evidence_sha256"
    )
    if is_v2 and isinstance(execution_mode, str) and execution_mode in {
        "parent-default",
        "sequential-current-session",
    }:
        expected_source = (
            "parent-default"
            if execution_mode == "parent-default"
            else "current-session"
        )
        if (
            not isinstance(fallback_capability_evidence, dict)
            or set(fallback_capability_evidence)
            != {
                "source",
                "capability_class",
                "capability_classes",
                "class_membership_confirmed",
                "capability_tiers",
                "selected_capability_tier",
            }
            or fallback_capability_evidence.get("source") != expected_source
            or fallback_capability_evidence.get("capability_class")
            != trusted_classification.get("capability_class")
            or not isinstance(
                fallback_capability_evidence.get("capability_classes"), list
            )
            or trusted_classification.get("capability_class")
            not in fallback_capability_evidence.get("capability_classes", [])
            or fallback_capability_evidence.get("class_membership_confirmed")
            is not True
            or not isinstance(
                fallback_capability_evidence.get("capability_tiers"), list
            )
            or fallback_capability_evidence.get("selected_capability_tier")
            != route_receipt.get("selected_capability_tier")
            or route_receipt.get("selected_capability_tier")
            not in fallback_capability_evidence.get("capability_tiers", [])
            or fallback_capability_evidence_sha256
            != _digest(fallback_capability_evidence)
        ):
            issues.append("fallback-capability-evidence-mismatch")
    elif (
        fallback_capability_evidence is not None
        or fallback_capability_evidence_sha256 is not None
    ):
        issues.append("unexpected-fallback-capability-evidence")
    if not isinstance(execution_mode, str) or mode_contracts.get(
        execution_mode
    ) is not True:
        issues.append("execution-mode-semantic-mismatch")
    if execution_mode == "custom-agent-profile" and profile_digest is None:
        issues.append("custom-profile-evidence-missing")
    if execution_mode != "custom-agent-profile" and profile_digest is not None:
        issues.append("unexpected-custom-profile-evidence")
    if profile_digest is None:
        if evidence_sha256 is not None or evidence is not None:
            issues.append("unexpected-profile-config-evidence")
    elif (
        not isinstance(evidence, dict)
        or evidence.get("profile_digest") != profile_digest
        or evidence.get("name") != route_receipt.get("runtime_mapping")
        or evidence.get("config_valid") is not True
        or evidence.get("model_available") is not True
        or evidence.get("reasoning_available") is not True
        or not isinstance(evidence.get("capability_class"), str)
        or evidence.get("capability_class") != trusted_classification.get(
            "capability_class"
        )
        or evidence.get("sandbox")
        != CLASS_SANDBOX.get(evidence.get("capability_class"))
        or evidence.get("sandbox_non_widening") is not True
        or not _sandbox_is_non_widening(evidence)
        or not isinstance(evidence.get("allowed_workflow_scope"), list)
        or any(
            not isinstance(item, str)
            for item in evidence.get("allowed_workflow_scope", [])
        )
        or set(evidence.get("allowed_workflow_scope") or [])
        != CLASS_WORKFLOW_SCOPE.get(evidence.get("capability_class"))
        or (
            is_v2
            and (
                evidence.get("capability_tier")
                != route_receipt.get("selected_capability_tier")
                or not isinstance(evidence.get("capability_tier"), str)
                or evidence.get("capability_tier") not in TIER_RANK
            )
        )
        or evidence_sha256 != _digest(evidence)
    ):
        issues.append("profile-config-evidence-mismatch")
    return {"valid": not issues, "issues": issues, "route_receipt_id": receipt_id}


def validate_worker_receipt(
    receipt: dict[str, Any], route_receipt: dict[str, Any]
) -> dict[str, Any]:
    """Validate worker coordination evidence against its immutable assignment."""
    receipt = _require_object(receipt, "worker receipt")
    route_receipt = _require_object(route_receipt, "route receipt")
    issues: list[str] = []
    route_validation = validate_route_receipt(route_receipt)
    issues.extend(route_validation["issues"])
    required = {
        "route_receipt_id",
        "task_id",
        "assigned_scope_sha256",
        "source_revision_sha256",
        "status",
        "output_artifacts",
        "artifact_digests",
    }
    if missing := sorted(required - set(receipt)):
        issues.append("missing-fields:" + ",".join(missing))
    for field in (
        "route_receipt_id",
        "task_id",
        "assigned_scope_sha256",
        "source_revision_sha256",
    ):
        if field in receipt and receipt.get(field) != route_receipt.get(field):
            issues.append(f"stale-or-conflicting-{field}")
    status = receipt.get("status")
    if status not in WORKER_STATUSES:
        issues.append("unsupported-status")
    elif status != "complete":
        issues.append(f"worker-{status}")
    artifacts = receipt.get("output_artifacts")
    if not isinstance(artifacts, list) or not artifacts or any(
        not isinstance(item, str) or not item for item in artifacts
    ):
        issues.append("missing-output-artifacts")
    artifact_digests = receipt.get("artifact_digests")
    if (
        not isinstance(artifact_digests, dict)
        or not isinstance(artifacts, list)
        or set(artifact_digests) != set(artifacts)
        or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in artifact_digests.values()
        )
    ):
        issues.append("artifact-digests-missing-or-invalid")
    conflicts = receipt.get("conflicts", [])
    if not isinstance(conflicts, list):
        issues.append("conflicts-must-be-array")
    elif conflicts:
        issues.append("conflicting-output")
    result = {
        "valid_coordination_evidence": not issues,
        "accepted_as_completion": False,
        "issues": issues,
        "worker_status": status,
        "route_receipt_id": route_receipt.get("route_receipt_id"),
        "worker_receipt_sha256": _digest(receipt),
        "artifact_digests_sha256": (
            _digest(artifact_digests) if isinstance(artifact_digests, dict) else None
        ),
    }
    result["validation_receipt_id"] = _digest(result)
    return result


def _validate_memory_usage_reference(value: Any) -> list[str]:
    """Validate optional V2b usage evidence without making it authoritative."""
    if not isinstance(value, dict):
        return ["memory-usage-must-be-object"]
    required = {
        "contract_version",
        "enabled",
        "backend_status",
        "receipt_digest",
        "dispositions",
        "used_as_authorization",
        "used_as_completion_evidence",
    }
    if set(value) != required:
        return ["memory-usage-fields-invalid"]
    issues: list[str] = []
    if value.get("contract_version") != "loop-memory/v1":
        issues.append("memory-usage-contract-version-invalid")
    if not isinstance(value.get("enabled"), bool):
        issues.append("memory-usage-enabled-invalid")
    backend_status = value.get("backend_status")
    if not isinstance(backend_status, str) or backend_status not in MEMORY_BACKEND_STATUSES:
        issues.append("memory-usage-backend-status-invalid")
    receipt_digest = value.get("receipt_digest")
    if receipt_digest is not None and (
        not isinstance(receipt_digest, str)
        or len(receipt_digest) != 64
        or any(character not in "0123456789abcdef" for character in receipt_digest)
    ):
        issues.append("memory-usage-receipt-digest-invalid")
    if isinstance(backend_status, str) and backend_status in {"disabled", "unavailable"} and receipt_digest is not None:
        issues.append("memory-usage-disabled-or-unavailable-cannot-bind-receipt")
    dispositions = value.get("dispositions")
    if (
        not isinstance(dispositions, list)
        or any(not isinstance(item, str) or item not in MEMORY_DISPOSITIONS for item in dispositions)
        or (all(isinstance(item, str) for item in dispositions) and len(dispositions) != len(set(dispositions)))
    ):
        issues.append("memory-usage-dispositions-invalid")
    if value.get("used_as_authorization") is not False:
        issues.append("memory-usage-cannot-authorize")
    if value.get("used_as_completion_evidence") is not False:
        issues.append("memory-usage-cannot-prove-completion")
    if value.get("enabled") is False and backend_status != "disabled":
        issues.append("memory-usage-disabled-state-inconsistent")
    if value.get("enabled") is True and backend_status == "disabled":
        issues.append("memory-usage-enabled-state-inconsistent")
    if isinstance(backend_status, str) and backend_status in {"used", "degraded"} and receipt_digest is None:
        issues.append("memory-usage-active-state-requires-receipt")
    if isinstance(backend_status, str) and backend_status in {"used", "degraded"} and not value.get("dispositions"):
        issues.append("memory-usage-active-state-requires-disposition")
    if isinstance(backend_status, str) and backend_status in {"disabled", "unavailable"} and value.get("dispositions"):
        issues.append("memory-usage-inactive-state-cannot-have-dispositions")
    return issues


def validate_main_agent_disposition(
    disposition: dict[str, Any],
    route_receipt: dict[str, Any],
    worker_validation: dict[str, Any],
    *,
    current_source_revision: dict[str, Any],
    current_profile_digest: str | None,
    assignment_fresh: bool,
) -> dict[str, Any]:
    """Require main-agent verification before accepting a worker result."""
    disposition = _require_object(disposition, "main-agent disposition")
    route_receipt = _require_object(route_receipt, "route receipt")
    worker_validation = _require_object(worker_validation, "worker validation")
    current_source_revision = _require_object(
        current_source_revision, "current source revision"
    )
    issues: list[str] = []
    issues.extend(validate_route_receipt(route_receipt)["issues"])
    if disposition.get("route_receipt_id") != route_receipt.get("route_receipt_id"):
        issues.append("stale-or-conflicting-route-receipt-id")
    validation_id = worker_validation.get("validation_receipt_id")
    unsigned_validation = {
        key: value
        for key, value in worker_validation.items()
        if key != "validation_receipt_id"
    }
    if not isinstance(validation_id, str) or validation_id != _digest(unsigned_validation):
        issues.append("worker-validation-integrity-mismatch")
    if disposition.get("worker_validation_id") != validation_id:
        issues.append("disposition-worker-validation-mismatch")
    if worker_validation.get("route_receipt_id") != route_receipt.get("route_receipt_id"):
        issues.append("worker-validation-route-mismatch")
    if _digest(current_source_revision) != route_receipt.get("source_revision_sha256"):
        issues.append("stale-source-revision")
    if current_profile_digest != route_receipt.get("selected_profile_digest"):
        issues.append("stale-or-conflicting-profile-digest")
    if assignment_fresh is not True:
        issues.append("assignment-not-fresh")
    if "memory_usage" in disposition:
        issues.extend(_validate_memory_usage_reference(disposition["memory_usage"]))
    decision = disposition.get("disposition")
    if decision not in DISPOSITIONS:
        issues.append("unsupported-disposition")
    if decision == "accepted":
        if worker_validation.get("valid_coordination_evidence") is not True:
            issues.append("invalid-worker-evidence")
        verification = disposition.get("verification")
        if not isinstance(verification, dict) or verification.get("status") != "passed":
            issues.append("main-agent-verification-not-passed")
        else:
            artifacts = verification.get("artifacts")
            artifact_digests = verification.get("artifact_digests")
            if not isinstance(artifacts, list) or not artifacts:
                issues.append("main-agent-verification-artifact-missing")
            elif (
                not isinstance(artifact_digests, dict)
                or set(artifact_digests) != set(artifacts)
                or any(
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(character not in "0123456789abcdef" for character in value)
                    for value in artifact_digests.values()
                )
            ):
                issues.append("main-agent-verification-digests-missing-or-invalid")
    return {
        "valid": not issues,
        "integration_accepted": decision == "accepted" and not issues,
        "completion_proven": False,
        "issues": issues,
        "disposition": decision,
        "worker_validation_id": validation_id,
    }
