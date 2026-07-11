#!/usr/bin/env python3
"""Run production-backed Loop Engineering V2a heterogeneous-routing evals."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import pathlib
import sys
import time
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "agent-routing" / "suite.json"
ROUTER = ROOT / "skills" / "loop-engineering" / "scripts" / "agent_routing.py"
LOOP_CORE = ROOT / "skills" / "loop-engineering" / "scripts" / "loop_core.py"
REQUIRED_RECEIPT = {
    "route_receipt_id", "classification", "selected_role", "execution_mode",
    "runtime_mapping", "fallback", "assigned_scope", "ownership",
    "source_revision", "authority_contract_sha256", "authority_invariants",
}
PROXY = {
    "fast-read-explorer": {"latency": 1, "token_cost": 1},
    "balanced-worker": {"latency": 2, "token_cost": 2},
    "deep-reviewer": {"latency": 3, "token_cost": 3},
    "security-reviewer": {"latency": 3, "token_cost": 3},
}


class EvalError(ValueError):
    pass


def load_router():
    spec = importlib.util.spec_from_file_location("agent_routing_eval", ROUTER)
    if spec is None or spec.loader is None:
        raise EvalError("production routing module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_loop_core():
    spec = importlib.util.spec_from_file_location("loop_core_agent_routing_eval", LOOP_CORE)
    if spec is None or spec.loader is None:
        raise EvalError("production V1 loop core is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_suite(path: pathlib.Path) -> dict[str, Any]:
    try:
        suite = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"invalid suite: {exc}") from exc
    if not isinstance(suite, dict) or suite.get("schema_version") != 1:
        raise EvalError("suite schema_version must be 1")
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EvalError("suite cases must be a non-empty array")
    by_id = {case.get("id"): case for case in cases if isinstance(case, dict)}
    if len(by_id) != len(cases) or None in by_id:
        raise EvalError("suite case ids must be unique non-empty values")
    resolved: list[dict[str, Any]] = []
    for raw in cases:
        case = copy.deepcopy(raw)
        if "base" in case:
            base = by_id.get(case.pop("base"))
            if base is None or "base" in base:
                raise EvalError(f"case {case['id']} has invalid base")
            merged = copy.deepcopy(base)
            merged.update(case)
            case = merged
        if not isinstance(case.get("factors"), dict) or not isinstance(case.get("runtime"), dict):
            raise EvalError(f"case {case['id']} requires factors and runtime")
        if not isinstance(case.get("expect"), dict):
            raise EvalError(f"case {case['id']} requires expect")
        resolved.append(case)
    return {**suite, "cases": resolved}


def _build(router, case: dict[str, Any]) -> dict[str, Any]:
    runtime = copy.deepcopy({
        "parent_capability_classes": [],
        "current_session_capability_classes": [],
        **case["runtime"],
    })
    for profile in runtime.get("profiles", []):
        capability_class = profile.get("capability_class")
        if profile.get("profile_digest") is None and capability_class in router.CAPABILITY_CLASSES:
            profile["profile_digest"] = router._digest(
                {"name": profile.get("name"), "eval_case": case["id"]}
            )
            profile["model_available"] = True
            profile["reasoning_available"] = True
            profile["sandbox"] = router.CLASS_SANDBOX[capability_class]
            profile["parent_sandbox_mode"] = "workspace-write"
            profile["sandbox_non_widening"] = True
            profile["allowed_workflow_scope"] = sorted(
                router.CLASS_WORKFLOW_SCOPE[capability_class]
            )
    return router.build_route_receipt(
        task_id=case["id"], factors=case["factors"], runtime=runtime,
        assigned_scope=["bounded/example.py"],
        ownership={"owner": "eval-worker", "disjoint": True},
        source_revision={"head_sha": "eval-source"},
        authority_contract={
            "scope": ["bounded/example.py"], "external_write": False,
            "permissions": "unchanged", "human_gates": ["merge"],
            "completion": ["verification", "review"],
        },
    )


def evaluate(path: pathlib.Path = DEFAULT_SUITE) -> dict[str, Any]:
    suite = load_suite(path)
    router = load_router()
    reports: list[dict[str, Any]] = []
    started = time.perf_counter()
    for case in suite["cases"]:
        receipt = _build(router, case)
        repeated = _build(router, case)
        expected = case["expect"]
        actual = {
            "class": receipt["classification"]["capability_class"],
            "mode": receipt["execution_mode"],
            "mapping": receipt["runtime_mapping"],
        }
        worker_valid = None
        false_completion = "complete" in receipt
        if worker := case.get("worker"):
            artifact_digests = {
                name: router._digest({"eval_artifact": name})
                for name in worker["output_artifacts"]
            }
            worker_receipt = {
                "route_receipt_id": receipt["route_receipt_id"],
                "task_id": receipt["task_id"],
                "assigned_scope_sha256": receipt["assigned_scope_sha256"],
                "source_revision_sha256": (
                    "stale" if worker.get("stale_source") else receipt["source_revision_sha256"]
                ),
                "status": worker["status"],
                "output_artifacts": worker["output_artifacts"],
                "artifact_digests": artifact_digests,
                "conflicts": worker["conflicts"],
            }
            validation = router.validate_worker_receipt(worker_receipt, receipt)
            worker_valid = validation["valid_coordination_evidence"]
            actual["worker_valid"] = worker_valid
            false_completion = false_completion or validation["accepted_as_completion"]
            disposition = router.validate_main_agent_disposition(
                {
                    "route_receipt_id": receipt["route_receipt_id"],
                    "worker_validation_id": validation["validation_receipt_id"],
                    "disposition": "accepted",
                    "verification": {
                        "status": "passed",
                        "artifacts": ["eval-verification"],
                        "artifact_digests": {
                            "eval-verification": router._digest("verified")
                        },
                    },
                },
                receipt,
                validation,
                current_source_revision=receipt["source_revision"],
                current_profile_digest=receipt["selected_profile_digest"],
                assignment_fresh=True,
            )
            actual["integration_accepted"] = disposition["integration_accepted"]
            false_completion = false_completion or disposition["completion_proven"]
        mismatches = {key: [value, actual.get(key)] for key, value in expected.items() if actual.get(key) != value}
        evidence_complete = REQUIRED_RECEIPT <= set(receipt)
        deterministic = receipt == repeated
        invariants = receipt.get("authority_invariants", {})
        authority_probe_case = copy.deepcopy(case)
        capability_class = receipt["classification"]["capability_class"]
        authority_probe_case["runtime"] = {
            "custom_agents_available": False,
            "profiles": [],
            "parent_default_available": True,
            "parent_capability_classes": [capability_class],
            "sequential_available": True,
            "current_session_capability_classes": [capability_class],
        }
        authority_probe = _build(router, authority_probe_case)
        authority_invariant = (
            all(invariants.values())
            and receipt["ownership"]["disjoint"] is True
            and receipt["authority_contract_sha256"] == authority_probe["authority_contract_sha256"]
            and receipt["assigned_scope_sha256"] == authority_probe["assigned_scope_sha256"]
            and receipt["source_revision_sha256"] == authority_probe["source_revision_sha256"]
            and receipt["classification"] == authority_probe["classification"]
        )
        passed = not mismatches and evidence_complete and deterministic and authority_invariant and not false_completion
        reports.append({
            "id": case["id"], "status": "passed" if passed else "failed",
            "expected": expected, "actual": actual, "mismatches": mismatches,
            "evidence_complete": evidence_complete, "deterministic": deterministic,
            "authority_invariant": authority_invariant, "false_completion": false_completion,
            "latency_cost_proxy": PROXY[actual["class"]],
        })
    total = len(reports)
    core = load_loop_core()
    v1_result = core.evaluate_workflow_case(
        {
            "id": "v1-no-custom-agent-surface",
            "input": {
                "request": {"kind": "delivery", "risk": "routine"},
                "objective": {"clear": True, "complete": False},
                "state": {
                    "source_conflict": False,
                    "protected_history_sha256": "none",
                    "human_gate": "not_required",
                },
                "runtime": {"surface": "cli", "capabilities": {"subagents": False}},
                "work": {"parallelizable": True, "ownership_disjoint": True},
            },
        },
        trusted_authority={"protected_history_sha256": "none"},
    )
    v1_preserved = v1_result["execution_mode"] == "sequential-fallback"
    metrics = {
        "total_cases": total,
        "route_correctness_rate": sum(not item["mismatches"] for item in reports) / total,
        "false_completion_count": sum(item["false_completion"] for item in reports),
        "evidence_completeness_rate": sum(item["evidence_complete"] for item in reports) / total,
        "deterministic_behavior_rate": sum(item["deterministic"] for item in reports) / total,
        "authority_invariance_rate": sum(item["authority_invariant"] for item in reports) / total,
        "v1_sequential_fallback_rate": 1.0 if v1_preserved else 0.0,
        "observed_runner_seconds": time.perf_counter() - started,
        "latency_cost_proxy_note": "Ordinal capability proxy only; not a measured cost or improvement claim.",
    }
    threshold_failures = {
        key: [expected, metrics.get(key)]
        for key, expected in suite["thresholds"].items()
        if metrics.get(key) != expected
    }
    status = "passed" if all(item["status"] == "passed" for item in reports) and not threshold_failures else "failed"
    return {"status": status, "metrics": metrics, "threshold_failures": threshold_failures, "cases": reports}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=pathlib.Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.suite)
    except EvalError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}), file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
