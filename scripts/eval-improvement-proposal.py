#!/usr/bin/env python3
"""Run deterministic production-backed V3-A evidence-to-proposal evaluations."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import improvement_proposal as proposal  # noqa: E402


SUITE = ROOT / "evals" / "improvement-proposal" / "suite.json"
EXPECTED_SUITE_FIELDS = {
    "contract_version",
    "positive_fixture",
    "negative_cases",
    "duplicate_key_fixture",
    "expected",
}
EXPECTED_METRICS = {
    "negative_cases",
    "decision_accuracy",
    "evidence_completeness",
    "recovery",
    "semantic_equivalence",
    "score_determinism",
    "tie_determinism",
    "duplicate_suppression",
    "lineage_rejection",
    "privacy_safe_rejection",
    "false_complete",
    "wrong_route",
    "unauthorized_action",
    "false_authority",
    "external_write",
    "promotion",
}


class EvalConfigurationError(ValueError):
    """Checked-in V3-A eval inventory is incomplete or weakened."""


def _resolve(base: pathlib.Path, relative: str) -> pathlib.Path:
    if not isinstance(relative, str) or not relative:
        raise EvalConfigurationError("eval path must be a non-empty string")
    candidate = base / relative
    if candidate.is_symlink():
        raise EvalConfigurationError("eval path must be a regular non-symlink file")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError) as error:
        raise EvalConfigurationError("eval path must stay inside the repository") from error
    if not resolved.is_file():
        raise EvalConfigurationError("eval path must be a regular non-symlink file")
    return resolved


def _load(path: pathlib.Path) -> dict[str, Any]:
    try:
        return proposal.load_json(path)
    except (OSError, proposal.ProposalContractError) as error:
        raise EvalConfigurationError("eval configuration is unreadable") from error


def load_suite(path: pathlib.Path = SUITE) -> dict[str, Any]:
    suite = _load(path)
    if set(suite) != EXPECTED_SUITE_FIELDS:
        raise EvalConfigurationError("suite has an invalid top-level shape")
    if suite["contract_version"] != "loop-improvement-proposal-eval/v0":
        raise EvalConfigurationError("suite contract version is unsupported")
    expected = suite["expected"]
    if not isinstance(expected, dict) or set(expected) != EXPECTED_METRICS:
        raise EvalConfigurationError("suite expected metrics are incomplete")
    exact_one = {
        "decision_accuracy",
        "evidence_completeness",
        "recovery",
        "semantic_equivalence",
        "score_determinism",
        "tie_determinism",
        "duplicate_suppression",
        "lineage_rejection",
        "privacy_safe_rejection",
    }
    exact_zero = {
        "false_complete",
        "wrong_route",
        "unauthorized_action",
        "false_authority",
        "external_write",
        "promotion",
    }
    if any(expected[key] != 1.0 for key in exact_one) or any(
        expected[key] != 0 for key in exact_zero
    ):
        raise EvalConfigurationError("suite thresholds are weakened")
    cases_wrapper = _load(_resolve(path.parent, suite["negative_cases"]))
    cases = cases_wrapper.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != expected["negative_cases"]
        or any(
            not isinstance(case, dict)
            or set(case) != {"id", "expected_code"}
            or not all(isinstance(item, str) and item for item in case.values())
            for case in cases
        )
        or len({case["id"] for case in cases}) != len(cases)
    ):
        raise EvalConfigurationError("negative case inventory is invalid")
    return {**suite, "cases": cases, "suite_path": path}


def _fixture(suite: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    path = _resolve(suite["suite_path"].parent, suite["positive_fixture"])
    wrapper = _load(path)
    if set(wrapper) != {"records", "evidence"}:
        raise EvalConfigurationError("positive fixture has an invalid shape")
    if not isinstance(wrapper["records"], list) or not isinstance(
        wrapper["evidence"], list
    ):
        raise EvalConfigurationError("positive fixture inventories must be arrays")
    return copy.deepcopy(wrapper["records"]), copy.deepcopy(wrapper["evidence"])


def _duplicate_fixture(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    root = copy.deepcopy(next(item for item in records if item["payload"]["predecessor"] is None))
    clone = copy.deepcopy(root)
    clone["record_id"] = "record-duplicate"
    clone["improvement_id"] = "improvement-duplicate"
    clone["producer"] = {"kind": "agent", "id": "proposer-duplicate"}
    clone["payload"]["role_assignments"] = {
        "proposer": {"actor_kind": "agent", "actor_id": "proposer-duplicate"},
        "evaluator": {"actor_kind": "ci", "actor_id": "evaluator-duplicate"},
        "independent_verifier": {
            "actor_kind": "human",
            "actor_id": "verifier-duplicate",
        },
        "promoter": {"actor_kind": "human", "actor_id": "promoter-duplicate"},
    }
    clone = proposal.lineage.seal_record(clone)
    return [root, clone]


def _run_negative(
    case_id: str,
    records: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    suite: dict[str, Any],
) -> None:
    root = next(item for item in records if item["payload"]["predecessor"] is None)
    if case_id == "duplicate-key":
        proposal.load_json(
            _resolve(suite["suite_path"].parent, suite["duplicate_key_fixture"])
        )
        return
    if case_id == "tampered-record-digest":
        root["payload"]["candidate_disposition"] = "evaluated"
        proposal.build_proposal_set(records, evidence)
        return
    if case_id == "missing-evidence":
        proposal.build_proposal_set(records, evidence[:-1])
        return
    generated = proposal.build_proposal_set(records, evidence)
    if case_id == "resealed-proposal-lineage-mismatch":
        generated["proposals"][0]["source_lineage"]["objective_id"] = "issue-other"
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    if case_id == "authority-escalation":
        generated["authority_invariants"]["promotion_authorized"] = True
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    if case_id == "false-complete":
        generated["proposals"][0]["proposal_only_invariants"][
            "promotion_decision"
        ] = "approved"
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    if case_id == "unauthorized-action":
        generated["proposals"][0]["proposal_only_invariants"][
            "runtime_action_performed"
        ] = True
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    if case_id == "wrong-route":
        generated["proposals"][0]["output_intent"] = "merge-suggestion"
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    if case_id == "source-revision-mismatch":
        root["payload"]["candidate"]["source_revision"]["commit_sha"] = "f" * 40
        proposal.build_proposal_set(
            [proposal.lineage.seal_record(root)], evidence
        )
        return
    if case_id == "artifact-mismatch":
        root["payload"]["evaluation_artifacts"][0]["artifact"][
            "content_sha256"
        ] = "d" * 64
        proposal.build_proposal_set(
            [proposal.lineage.seal_record(root)], evidence
        )
        return
    if case_id == "private-path":
        root["record_id"] = "/home/example/private-record"
        proposal.build_proposal_set([root], evidence)
        return
    if case_id in {
        "hostname-field",
        "username-field",
        "synthetic-token",
        "pii-email",
        "raw-log",
    }:
        field, value = {
            "hostname-field": ("hostname", "synthetic.example.internal"),
            "username-field": ("username", "synthetic-user"),
            "synthetic-token": ("token", "ghp_" + "A" * 36),
            "pii-email": ("email", "synthetic@example.invalid"),
            "raw-log": ("raw_log", "2026-08-10T01:00:00Z ERROR synthetic"),
        }[case_id]
        generated[field] = value
        candidate = (
            proposal.seal_proposal_set(generated)
            if case_id in {"hostname-field", "username-field"}
            else generated
        )
        proposal.validate_proposal_set(candidate, records, evidence)
        return
    if case_id == "unknown-proposal-field":
        generated["unexpected"] = False
        proposal.validate_proposal_set(
            proposal.seal_proposal_set(generated), records, evidence
        )
        return
    raise EvalConfigurationError("negative case implementation is missing")


def evaluate_suite(path: pathlib.Path = SUITE) -> dict[str, Any]:
    suite = load_suite(path)
    records, evidence = _fixture(suite)
    first = proposal.build_proposal_set(records, evidence)
    second = proposal.build_proposal_set(reversed(records), reversed(evidence))
    proposal.validate_proposal_set(first, records, evidence)

    duplicate_records = _duplicate_fixture(records)
    duplicate_first = proposal.build_proposal_set(duplicate_records, evidence)
    duplicate_second = proposal.build_proposal_set(
        reversed(duplicate_records), reversed(evidence)
    )
    duplicate_ok = (
        duplicate_first == duplicate_second
        and len(duplicate_first["proposals"]) == 1
        and len(duplicate_first["suppressed_duplicates"]) == 1
        and len(
            duplicate_first["suppressed_duplicates"][0][
                "suppressed_source_records"
            ]
        )
        == 1
    )
    score_ok = all(
        item["score"]["policy_version"] == proposal.SCORE_POLICY_VERSION
        and item["score"]["total"] == sum(item["score"]["components"].values())
        for item in first["proposals"]
    )
    recovery_positive = any(
        item["score"]["components"]["recovery_signal"] == 20
        for item in first["proposals"]
    )
    rejected = copy.deepcopy(next(item for item in records if item["payload"]["predecessor"] is None))
    rejected["payload"]["candidate_disposition"] = "rejected"
    rejected = proposal.lineage.seal_record(rejected)
    recovery_blocked = proposal.build_proposal_set([rejected], evidence)
    recovery_ok = recovery_positive and not recovery_blocked["proposals"]

    observations: list[dict[str, Any]] = []
    for case in suite["cases"]:
        case_records, case_evidence = _fixture(suite)
        try:
            _run_negative(case["id"], case_records, case_evidence, suite)
            observed = "accepted"
        except proposal.ProposalContractError as error:
            observed = error.code
        observations.append(
            {
                "id": case["id"],
                "expected_code": case["expected_code"],
                "observed_code": observed,
                "passed": observed == case["expected_code"],
            }
        )

    by_id = {item["id"]: item for item in observations}
    lineage_cases = {
        "tampered-record-digest",
        "missing-evidence",
        "resealed-proposal-lineage-mismatch",
        "source-revision-mismatch",
        "artifact-mismatch",
    }
    evidence_cases = {
        "tampered-record-digest",
        "missing-evidence",
        "source-revision-mismatch",
        "artifact-mismatch",
    }
    false_authority = sum(
        value is not False
        for container in [first["authority_invariants"]]
        + [item["authority_invariants"] for item in first["proposals"]]
        for value in container.values()
    )
    false_complete = int(by_id["false-complete"]["observed_code"] == "accepted")
    wrong_route = int(by_id["wrong-route"]["observed_code"] == "accepted")
    unauthorized = int(by_id["unauthorized-action"]["observed_code"] == "accepted")
    metrics = {
        "negative_cases": len(observations),
        "decision_accuracy": sum(item["passed"] for item in observations)
        / len(observations),
        "evidence_completeness": sum(by_id[item]["passed"] for item in evidence_cases)
        / len(evidence_cases),
        "recovery": 1.0 if recovery_ok else 0.0,
        "semantic_equivalence": 1.0 if first == second else 0.0,
        "score_determinism": 1.0 if score_ok else 0.0,
        "tie_determinism": 1.0 if duplicate_first == duplicate_second else 0.0,
        "duplicate_suppression": 1.0 if duplicate_ok else 0.0,
        "lineage_rejection": sum(by_id[item]["passed"] for item in lineage_cases)
        / len(lineage_cases),
        "privacy_safe_rejection": (
            sum(
                by_id[item]["passed"]
                for item in {
                    "private-path",
                    "hostname-field",
                    "username-field",
                    "synthetic-token",
                    "pii-email",
                    "raw-log",
                }
            )
            / 6
        ),
        "false_complete": false_complete,
        "wrong_route": wrong_route,
        "unauthorized_action": unauthorized,
        "false_authority": false_authority,
        "external_write": int(
            any(
                item["proposal_only_invariants"]["external_write_performed"]
                for item in first["proposals"]
            )
        ),
        "promotion": int(
            any(
                item["promotion_gate"]["status"] != "pending"
                or item["proposal_only_invariants"]["promotion_decision"]
                != "not-authorized"
                for item in first["proposals"]
            )
        ),
    }
    passed = metrics == suite["expected"] and all(item["passed"] for item in observations)
    return {
        "contract_version": suite["contract_version"],
        "passed": passed,
        "metrics": metrics,
        "observations": observations,
        "proposal_set_digest": first["proposal_set_digest"],
    }


def main() -> int:
    try:
        result = evaluate_suite()
    except EvalConfigurationError as error:
        print(json.dumps({"passed": False, "error": str(error)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
