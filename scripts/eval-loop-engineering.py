#!/usr/bin/env python3
"""Run deterministic Loop Engineering workflow contract evaluations."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
import pathlib
import sys
from collections.abc import Callable
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "loop-engineering" / "suite.json"
CORE = ROOT / "skills" / "loop-engineering" / "scripts" / "loop_core.py"
REQUIRED_OUTPUT_FIELDS = {
    "case_id",
    "classification",
    "route",
    "execution_mode",
    "next_decision",
    "complete",
    "violations",
}
SEMANTIC_EQUIVALENCE_FIELDS = (
    "classification",
    "route",
    "next_decision",
    "complete",
    "violations",
)

Evaluator = Callable[..., dict[str, Any]]

TRUSTED_AUTHORITY_PROFILES = {
    "parent-security-report-fallback": {
        "parent_security_report_fallback_authorized": True,
    },
    "parent-security-scan-fallback": {
        "parent_security_scan_fallback_authorized": True,
    },
}
BASE_TRUSTED_AUTHORITY = {"protected_history_sha256": "none"}


class EvalConfigurationError(ValueError):
    """Raised when the suite, fixture, or production evaluator is invalid."""


def load_production_evaluator() -> Evaluator:
    if not CORE.is_file():
        raise EvalConfigurationError(f"production loop core is missing: {CORE}")
    spec = importlib.util.spec_from_file_location("loop_engineering_core_for_eval", CORE)
    if spec is None or spec.loader is None:
        raise EvalConfigurationError(f"could not load production loop core: {CORE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evaluator = getattr(module, "evaluate_workflow_case", None)
    if not callable(evaluator):
        raise EvalConfigurationError(
            "production loop core must expose evaluate_workflow_case(case: dict) -> dict"
        )
    return evaluator


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalConfigurationError(f"could not load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvalConfigurationError(f"JSON document must be an object: {path}")
    return value


def _validate_fixture(case: dict[str, Any], path: pathlib.Path) -> None:
    missing = [key for key in ("id", "input", "expect") if key not in case]
    if missing:
        raise EvalConfigurationError(f"{path}: missing fixture field(s): {', '.join(missing)}")
    if not isinstance(case["id"], str) or not case["id"].strip():
        raise EvalConfigurationError(f"{path}: id must be a non-empty string")
    if not isinstance(case["input"], dict):
        raise EvalConfigurationError(f"{path}: input must be an object")
    if not isinstance(case["expect"], dict) or not case["expect"]:
        raise EvalConfigurationError(f"{path}: expect must be a non-empty object")


def _subset_mismatches(expected: Any, actual: Any, path: str = "result") -> list[str]:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        mismatches: list[str] = []
        for key, value in expected.items():
            child = f"{path}.{key}"
            if key not in actual:
                mismatches.append(f"{child}: missing")
            else:
                mismatches.extend(_subset_mismatches(value, actual[key], child))
        return mismatches
    if expected != actual:
        return [f"{path}: expected {expected!r}, got {actual!r}"]
    return []


def completion_evidence(case: dict[str, Any]) -> dict[str, Any]:
    """Independently score the durable evidence needed for completion."""
    input_data = case["input"]
    objective = input_data.get("objective", {})
    state = input_data.get("state", {})
    checks = {
        "objective_clear": objective.get("clear") is True,
        "objective_marked_complete": objective.get("complete") is True,
        "source_consistent": state.get("source_conflict") is False,
        "task_terminal": state.get("task_status") in {"done", "accepted"},
        "verification_passed": state.get("verification") == "passed",
        "review_satisfied": state.get("review") in {"not_required", "passed"},
        "human_gate_satisfied": state.get("human_gate") in {"not_required", "satisfied"},
    }
    satisfied = sum(checks.values())
    return {
        "score": satisfied / len(checks),
        "checks": checks,
        "missing": [name for name, passed in checks.items() if not passed],
        "completion_allowed": all(checks.values()),
    }


def grade_case(
    case: dict[str, Any],
    actual: dict[str, Any],
    *,
    recovery_expected: str = "not-applicable",
) -> dict[str, Any]:
    mismatches = _subset_mismatches(case["expect"], actual)
    invariant_failures: list[str] = []
    missing_output = sorted(REQUIRED_OUTPUT_FIELDS - set(actual)) if isinstance(actual, dict) else []
    if missing_output:
        invariant_failures.append("missing output field(s): " + ", ".join(missing_output))

    evidence = completion_evidence(case)
    false_complete = actual.get("complete") is True and not evidence["completion_allowed"]
    if false_complete:
        invariant_failures.append(
            "false completion: production result completed without all durable evidence"
        )

    violations = actual.get("violations", [])
    if not isinstance(violations, list):
        invariant_failures.append("result.violations must be a list")
        violations = []
    actions = actual.get("actions", [])
    if not isinstance(actions, list):
        invariant_failures.append("result.actions must be a list when present")
        actions = []
    request = case["input"].get("request", {})
    # Eval fixtures are repository input, never a trusted authorization channel.
    unauthorized_action = bool(actions) and request.get("requires_external_write") is True
    if request.get("requires_external_write") is True:
        if actual.get("route") != "human-gate" or "external-write-not-authorized" not in violations:
            invariant_failures.append("unauthorized external write was not stopped at a human gate")

    expected_route = case["expect"].get("route")
    wrong_route = expected_route is not None and actual.get("route") != expected_route
    passed = not mismatches and not invariant_failures
    if recovery_expected == "not-applicable":
        recovery_outcome = "not-applicable"
    elif recovery_expected == "recovered" and (
        (
            case["input"].get("state", {}).get("interrupted") is True
            and actual.get("route") == "task-continuation"
            and actual.get("next_decision") == "continue"
            and actual.get("complete") is False
        )
        or (
            (case["input"].get("state", {}).get("security_scan") or {}).get(
                "status"
            )
            == "running"
            and actual.get("route") == "task-continuation"
            and actual.get("next_decision") == "continue"
            and "security-scan-remains-running" in actual.get("notices", [])
        )
    ):
        recovery_outcome = "recovered"
    elif recovery_expected == "safely-blocked" and (
        actual.get("route") == "human-gate"
        and actual.get("next_decision") == "blocked-by-human-gate"
        and actual.get("complete") is False
        and bool(violations)
    ):
        recovery_outcome = "safely-blocked"
    else:
        recovery_outcome = "failed"
        invariant_failures.append(f"recovery invariant failed: expected {recovery_expected}")
        passed = False

    return {
        "id": case["id"],
        "status": "passed" if passed else "failed",
        "expected": case["expect"],
        "actual": actual,
        "mismatches": mismatches,
        "invariant_failures": invariant_failures,
        "false_complete": false_complete,
        "wrong_route": wrong_route,
        "unauthorized_action": unauthorized_action,
        "evidence_completeness": evidence,
        "iteration_count": 1,
        "recovery_outcome": recovery_outcome,
    }


def _load_suite(
    suite_path: pathlib.Path, selected_ids: set[str] | None
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], dict[str, Any]]]]:
    suite = _load_json(suite_path)
    if suite.get("schema_version") != 1:
        raise EvalConfigurationError(f"{suite_path}: schema_version must be 1")
    entries = suite.get("cases")
    if not isinstance(entries, list) or not entries:
        raise EvalConfigurationError(f"{suite_path}: cases must be a non-empty list")

    loaded: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    suite_root = suite_path.parent.resolve()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise EvalConfigurationError(f"{suite_path}: every case entry needs a path")
        authority_profile = entry.get("trusted_authority_profile")
        if (
            authority_profile is not None
            and authority_profile not in TRUSTED_AUTHORITY_PROFILES
        ):
            raise EvalConfigurationError(
                f"{suite_path}: unknown trusted authority profile {authority_profile!r}"
            )
        fixture_path = (suite_path.parent / entry["path"]).resolve()
        try:
            fixture_path.relative_to(suite_root)
        except ValueError as exc:
            raise EvalConfigurationError(
                f"{suite_path}: case path must stay inside the suite directory"
            ) from exc
        case = _load_json(fixture_path)
        _validate_fixture(case, fixture_path)
        case_id = case["id"]
        if case_id in seen:
            raise EvalConfigurationError(f"{suite_path}: duplicate case id {case_id}")
        seen.add(case_id)
        if selected_ids is None or case_id in selected_ids:
            loaded.append((case, entry))

    if selected_ids:
        missing = sorted(selected_ids - seen)
        if missing:
            raise EvalConfigurationError("unknown case id(s): " + ", ".join(missing))
    if not loaded:
        raise EvalConfigurationError("no workflow cases selected")
    return suite, loaded


def _semantic_projection(actual: dict[str, Any]) -> dict[str, Any]:
    return {field: actual.get(field) for field in SEMANTIC_EQUIVALENCE_FIELDS}


def evaluate_state_contract(core_module: Any) -> dict[str, Any]:
    """Execute a real multi-event lifecycle plus an adversarial stale-owner case."""
    source = {
        "branch": "eval",
        "head_sha": "abc123",
        "spec_sha256": "spec",
        "task_manifest_sha256": "manifest",
    }
    state = {
        "revision": 0,
        "last_event_hash": "",
        "objective_id": "eval-objective",
        "source_revision": source,
        "tasks": {
            "T1": {
                "status": "planned",
                "definition": {
                    "scope": ["x"],
                    "dod": ["done"],
                    "verification": ["test"],
                    "dependencies": [],
                },
                "evidence": {},
                "blocker": {},
            }
        },
        "claims": {},
        "events": [],
        "idempotency": {},
        "gates": {},
        "objective_status": "active",
    }

    def apply(event_id: str, event_type: str, payload: dict[str, Any], task_id: str = "T1") -> None:
        nonlocal state
        event = {
            "sequence": state["revision"] + 1,
            "event_id": event_id,
            "occurred_at": f"2026-07-10T00:{state['revision']:02d}:00Z",
            "actor": "eval-worker",
            "type": event_type,
            "task_id": task_id,
            "idempotency_key": event_id,
            "expected_state_revision": state["revision"],
            "previous_event_hash": state["last_event_hash"],
            "payload": payload,
        }
        event["event_hash"] = core_module.calculate_event_hash(event)
        protected_action = core_module.protected_event_action(event)
        trusted_authority = None
        if protected_action is not None:
            trusted_authority = {
                "action": protected_action,
                "authorization_receipt_sha256": core_module.digest(
                    event["payload"]["authorization"]
                ),
            }
        state, _ = core_module.apply_event(
            state,
            event,
            trusted_authority=trusted_authority,
            trusted_time=dt.datetime.fromisoformat(
                event["occurred_at"].replace("Z", "+00:00")
            ),
        )

    def authorize(
        payload: dict[str, Any], action: str, artifact: str, **scope: str
    ) -> None:
        authorization = {
            "action": action,
            "principal": {"type": "user", "id": "eval-worker"},
            "objective_id": state["objective_id"],
            "artifact": artifact,
            "source_revision_sha256": core_module.source_revision_digest(
                state["source_revision"]
            ),
            **scope,
        }
        payload["authorization"] = authorization
        authorization["protected_payload_sha256"] = (
            core_module.protected_payload_digest(payload)
        )

    failures: list[str] = []
    try:
        apply("ready", "task_transition", {"target_status": "ready", "evidence": {}})
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "eval-worker"},
            "fencing_token": {"generation": 1, "nonce": "eval-nonce"},
            "expected_state_revision": state["revision"],
            "source_revision": source,
            "claimed_at": "2026-07-10T00:01:00Z",
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        apply("claim", "claim_acquired", {"claim": claim})
        token = claim["fencing_token"]
        apply(
            "start",
            "task_transition",
            {"target_status": "in_progress", "fencing_token": token, "evidence": {}},
        )
        stale_state = copy.deepcopy(state)
        apply(
            "review",
            "task_transition",
            {
                "target_status": "reviewing",
                "fencing_token": token,
                "evidence": {
                    "verification": {"status": "passed", "artifacts": ["test-output"]},
                    "review": {"status": "required", "artifacts": ["diff"]},
                    "acceptance": {"status": "not_required", "artifact": ""},
                },
            },
        )
        done_payload = {
            "target_status": "done",
            "fencing_token": token,
            "human_gate": "not_required",
            "evidence": {
                "verification": {"status": "passed", "artifacts": ["test-output"]},
                "review": {
                    "status": "passed",
                    "mode": "code-review",
                    "artifacts": ["review"],
                },
                "acceptance": {"status": "pending", "artifact": ""},
            },
        }
        authorize(done_payload, "task_completion", "review", task_id="T1")
        apply("done", "task_transition", done_payload)
        apply("release", "claim_released", {"fencing_token": token})
        accept_payload = {
            "target_status": "accepted",
            "evidence": {
                "verification": {"status": "passed", "artifacts": ["test-output"]},
                "review": {"status": "passed", "artifacts": ["review"]},
                "acceptance": {"status": "satisfied", "artifact": "approval"},
            },
        }
        authorize(accept_payload, "task_acceptance", "approval", task_id="T1")
        apply("accept", "task_transition", accept_payload)
        completion_payload = {
            "verification": "passed",
            "review": "passed",
            "human_gate": "satisfied",
            "evidence": {"artifact": "completion-approval"},
        }
        authorize(
            completion_payload,
            "objective_completion",
            "completion-approval",
        )
        apply("complete", "objective_completed", completion_payload, task_id="")
        if state["objective_status"] != "complete" or state["tasks"]["T1"]["status"] != "accepted":
            failures.append("happy-path lifecycle did not reach accepted/complete")

        stale_event = {
            "sequence": stale_state["revision"] + 1,
            "event_id": "stale-review",
            "occurred_at": "2026-07-10T00:04:00Z",
            "actor": "stale-worker",
            "type": "task_transition",
            "task_id": "T1",
            "idempotency_key": "stale-review",
            "expected_state_revision": stale_state["revision"],
            "previous_event_hash": stale_state["last_event_hash"],
            "payload": {
                "target_status": "reviewing",
                "fencing_token": {"generation": 1, "nonce": "forged"},
                "evidence": {
                    "verification": {"status": "passed", "artifacts": ["test"]}
                },
            },
        }
        stale_event["event_hash"] = core_module.calculate_event_hash(stale_event)
        try:
            core_module.apply_event(
                stale_state,
                stale_event,
                trusted_time=dt.datetime.fromisoformat(
                    stale_event["occurred_at"].replace("Z", "+00:00")
                ),
            )
            failures.append("stale fencing token was accepted")
        except core_module.LoopContractError:
            pass
    except Exception as exc:
        failures.append(f"{type(exc).__name__}: {exc}")
    return {
        "status": "passed" if not failures else "failed",
        "failures": failures,
        "final_revision": state["revision"],
    }


def evaluate_suite(
    suite_path: pathlib.Path = DEFAULT_SUITE,
    *,
    selected_ids: set[str] | None = None,
    evaluator: Evaluator | None = None,
) -> dict[str, Any]:
    suite, loaded = _load_suite(suite_path.resolve(), selected_ids)
    production_evaluator = evaluator or load_production_evaluator()
    core_spec = importlib.util.spec_from_file_location("loop_engineering_core_for_state_eval", CORE)
    if core_spec is None or core_spec.loader is None:
        raise EvalConfigurationError(f"could not load production loop core: {CORE}")
    core_module = importlib.util.module_from_spec(core_spec)
    core_spec.loader.exec_module(core_module)
    case_reports: list[dict[str, Any]] = []
    equivalence_members: dict[str, list[dict[str, Any]]] = {}

    for case, metadata in loaded:
        try:
            trusted_authority = copy.deepcopy(BASE_TRUSTED_AUTHORITY)
            authority_profile = metadata.get("trusted_authority_profile")
            if authority_profile is not None:
                trusted_authority.update(
                    copy.deepcopy(TRUSTED_AUTHORITY_PROFILES[authority_profile])
                )
            actual = production_evaluator(
                case,
                trusted_authority=trusted_authority,
            )
        except Exception as exc:  # A crashing production evaluator is an eval failure.
            actual = {"case_id": case["id"], "evaluation_error": f"{type(exc).__name__}: {exc}"}
        if not isinstance(actual, dict):
            actual = {
                "case_id": case["id"],
                "evaluation_error": f"evaluator returned {type(actual).__name__}, expected dict",
            }
        report = grade_case(
            case,
            actual,
            recovery_expected=str(metadata.get("recovery_expected", "not-applicable")),
        )
        case_reports.append(report)
        group = metadata.get("equivalence_group")
        if isinstance(group, str) and group:
            equivalence_members.setdefault(group, []).append(report)

    equivalence_reports: list[dict[str, Any]] = []
    for group, members in sorted(equivalence_members.items()):
        projections = [_semantic_projection(member["actual"]) for member in members]
        if len(members) < 2:
            continue
        passed = all(item == projections[0] for item in projections[1:])
        equivalence_reports.append(
            {
                "group": group,
                "status": "passed" if passed else "failed",
                "case_ids": [member["id"] for member in members],
                "projections": projections,
            }
        )
        if not passed:
            for member in members:
                member["status"] = "failed"
                member["invariant_failures"].append(
                    f"CLI/Desktop semantic equivalence failed for group {group}"
                )

    total = len(case_reports)
    passed = sum(case["status"] == "passed" for case in case_reports)
    recovery_cases = [case for case in case_reports if case["recovery_outcome"] != "not-applicable"]
    recovery_successes = sum(
        case["recovery_outcome"] in {"recovered", "safely-blocked"}
        for case in recovery_cases
    )
    equivalence_passed = sum(item["status"] == "passed" for item in equivalence_reports)
    state_contract = evaluate_state_contract(core_module)
    metrics = {
        "total_cases": total,
        "passed_cases": passed,
        "task_success_rate": passed / total,
        "false_complete_count": sum(case["false_complete"] for case in case_reports),
        "wrong_route_count": sum(case["wrong_route"] for case in case_reports),
        "unauthorized_action_count": sum(case["unauthorized_action"] for case in case_reports),
        "evidence_completeness": sum(
            case["evidence_completeness"]["score"] for case in case_reports
        )
        / total,
        "iteration_count": sum(case["iteration_count"] for case in case_reports),
        "recovery_success_rate": (
            recovery_successes / len(recovery_cases) if recovery_cases else 1.0
        ),
        "semantic_equivalence_rate": (
            equivalence_passed / len(equivalence_reports) if equivalence_reports else 1.0
        ),
        "state_contract_success_rate": 1.0 if state_contract["status"] == "passed" else 0.0,
    }
    thresholds = suite.get("thresholds", {})
    threshold_failures: list[str] = []
    checks = {
        "task_success_rate": metrics["task_success_rate"] >= thresholds.get("task_success_rate", 1.0),
        "false_complete_count": metrics["false_complete_count"] <= thresholds.get("false_complete_count", 0),
        "wrong_route_count": metrics["wrong_route_count"] <= thresholds.get("wrong_route_count", 0),
        "unauthorized_action_count": metrics["unauthorized_action_count"] <= thresholds.get("unauthorized_action_count", 0),
        "recovery_success_rate": metrics["recovery_success_rate"] >= thresholds.get("recovery_success_rate", 1.0),
        "semantic_equivalence_rate": metrics["semantic_equivalence_rate"] >= thresholds.get("semantic_equivalence_rate", 1.0),
        "state_contract_success_rate": metrics["state_contract_success_rate"] >= thresholds.get("state_contract_success_rate", 1.0),
    }
    for name, ok in checks.items():
        if not ok:
            threshold_failures.append(
                f"{name}: actual {metrics[name]!r}, threshold {thresholds.get(name)!r}"
            )

    status = "passed" if passed == total and not threshold_failures else "failed"
    return {
        "schema_version": 1,
        "status": status,
        "suite": str(suite_path),
        "metrics": metrics,
        "threshold_failures": threshold_failures,
        "equivalence_groups": equivalence_reports,
        "state_contract": state_contract,
        "cases": case_reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=pathlib.Path, default=DEFAULT_SUITE)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        report = evaluate_suite(
            args.suite,
            selected_ids=set(args.case_ids) if args.case_ids else None,
        )
    except EvalConfigurationError as exc:
        print(json.dumps({"schema_version": 1, "status": "error", "error": str(exc)}))
        return 2

    rendered = json.dumps(report, indent=2 if args.pretty else None, sort_keys=True)
    if args.output:
        try:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        except OSError as exc:
            print(json.dumps({"schema_version": 1, "status": "error", "error": str(exc)}))
            return 2
    else:
        print(rendered)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
