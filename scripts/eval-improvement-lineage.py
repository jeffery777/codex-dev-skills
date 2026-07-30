#!/usr/bin/env python3
"""Run deterministic production-backed V2d-B lineage/projection evaluations."""

from __future__ import annotations

import copy
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import improvement_lineage as lineage  # noqa: E402


SUITE = ROOT / "evals" / "improvement-lineage" / "suite.json"
EXPECTED_SUITE_FIELDS = {
    "contract_version",
    "positive_fixture",
    "negative_cases",
    "duplicate_key_fixture",
    "obsidian_profile",
    "expected",
}


class EvalConfigurationError(ValueError):
    """Checked-in V2d-B eval inventory is incomplete or malformed."""


def _load_config(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = lineage.load_json(path)
    except EvalConfigurationError:
        raise
    except (OSError, lineage.ImprovementContractError) as error:
        raise EvalConfigurationError("eval configuration is unreadable") from error
    if not isinstance(value, dict):
        raise EvalConfigurationError("eval configuration must be an object")
    return value


def _resolve(relative: str) -> pathlib.Path:
    if not isinstance(relative, str) or not relative:
        raise EvalConfigurationError("eval path must be a non-empty string")
    candidate = SUITE.parent / relative
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


def load_suite(path: pathlib.Path = SUITE) -> dict[str, Any]:
    suite = _load_config(path)
    if set(suite) != EXPECTED_SUITE_FIELDS:
        raise EvalConfigurationError("suite has an invalid top-level shape")
    if suite["contract_version"] != "loop-improvement-lineage-eval/v0":
        raise EvalConfigurationError("suite contract version is unsupported")
    expected = suite["expected"]
    if not isinstance(expected, dict) or set(expected) != {
        "positive_cases",
        "negative_cases",
        "false_authority_claims",
        "projection_mismatches",
        "source_record_set_digest",
        "human_projection_digest",
        "graph_projection_digest",
        "graph_nodes",
        "graph_edges",
    }:
        raise EvalConfigurationError("suite expected results are incomplete")
    negative = _load_config(_resolve(suite["negative_cases"]))
    cases = negative.get("cases")
    if (
        not isinstance(cases, list)
        or len(cases) != expected["negative_cases"]
        or any(
            not isinstance(case, dict)
            or set(case) != {"id", "expected_code"}
            or not all(isinstance(value, str) and value for value in case.values())
            for case in cases
        )
    ):
        raise EvalConfigurationError("negative case inventory is invalid")
    if len({case["id"] for case in cases}) != len(cases):
        raise EvalConfigurationError("negative case ids must be unique")
    return {**suite, "cases": cases}


def _fixture(suite: dict[str, Any]) -> tuple[list[dict], list[dict]]:
    wrapper = lineage.load_json(_resolve(suite["positive_fixture"]))
    if set(wrapper) != {"evidence", "records"}:
        raise EvalConfigurationError("positive fixture has an invalid shape")
    evidence = wrapper["evidence"]
    records = wrapper["records"]
    if not isinstance(evidence, list) or not isinstance(records, list):
        raise EvalConfigurationError("positive fixture inventories must be arrays")
    return copy.deepcopy(records), copy.deepcopy(evidence)


def _reseal(record: dict[str, Any]) -> dict[str, Any]:
    return lineage.seal_record(record)


def _environment_mismatch(
    records: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> None:
    environment = next(item for item in evidence if item["document_id"] == "environment-2")
    environment["payload"]["runtime_surface"] = "ci"
    replacement_environment = lineage.oe.seal_document(environment)
    evidence[evidence.index(environment)] = replacement_environment
    run = next(item for item in evidence if item["document_id"] == "receipt-2")
    run["payload"]["environment_fingerprint"]["document_digest"] = (
        replacement_environment["document_digest"]
    )
    replacement_run = lineage.oe.seal_document(run)
    evidence[evidence.index(run)] = replacement_run
    bundle = [
        item
        for item in evidence
        if item["run_id"] == "run-2"
    ]
    set_digest = lineage.oe.validate_set(bundle)["set_digest"]
    root = next(item for item in records if item["record_id"] == "record-1")
    candidate = root["payload"]["candidate"]
    candidate["environment_fingerprint"]["document_digest"] = (
        replacement_environment["document_digest"]
    )
    candidate["run_receipt"]["document_digest"] = replacement_run["document_digest"]
    candidate["environment_key"] = lineage.oe.canonical_digest(
        replacement_environment["payload"]
    )
    candidate["evidence_set_digest"] = set_digest
    records[records.index(root)] = _reseal(root)


def _run_negative(
    case_id: str,
    records: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    suite: dict[str, Any],
) -> None:
    child = next(item for item in records if item["record_id"] == "record-2")
    root = next(item for item in records if item["record_id"] == "record-1")
    if case_id == "duplicate-key":
        lineage.load_json(_resolve(suite["duplicate_key_fixture"]))
        return
    if case_id == "tampered-record-digest":
        root["payload"]["candidate_disposition"] = "evaluated"
        lineage.validate_record(root, evidence)
        return
    if case_id == "unknown-record-field":
        root["title"] = "synthetic"
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "unsupported-record-version":
        root["contract_version"] = "loop-improvement-lineage/v9"
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "authority-escalation":
        root["authority_invariants"]["promotion_authorized"] = True
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "duplicate-improvement-id":
        duplicate = copy.deepcopy(root)
        duplicate["record_id"] = "duplicate-record"
        lineage.validate_lineage([root, _reseal(duplicate)], evidence)
        return
    if case_id == "missing-predecessor":
        child["payload"]["predecessor"]["record_id"] = "missing-record"
        lineage.validate_lineage([root, _reseal(child)], evidence)
        return
    if case_id == "cycle-attempt":
        root["payload"]["predecessor"] = {
            "record_id": child["record_id"],
            "improvement_id": child["improvement_id"],
            "record_digest": child["record_digest"],
        }
        lineage.validate_lineage([_reseal(root), child], evidence)
        return
    if case_id == "stale-baseline":
        child["payload"]["baseline"] = copy.deepcopy(root["payload"]["baseline"])
        lineage.validate_lineage([root, _reseal(child)], evidence)
        return
    if case_id == "baseline-candidate-equality":
        root["payload"]["candidate"] = copy.deepcopy(root["payload"]["baseline"])
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "source-revision-mismatch":
        root["payload"]["baseline"]["source_revision"]["commit_sha"] = "f" * 40
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "environment-mismatch":
        _environment_mismatch(records, evidence)
        changed = next(item for item in records if item["record_id"] == "record-1")
        lineage.validate_record(changed, evidence)
        return
    if case_id == "role-collision":
        root["payload"]["role_assignments"]["promoter"] = copy.deepcopy(
            root["payload"]["role_assignments"]["proposer"]
        )
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "candidate-self-verification":
        root["payload"]["role_assignments"]["independent_verifier"] = {
            "actor_kind": "human",
            "actor_id": "candidate-runner-2",
        }
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "verified-without-review":
        root["payload"]["evaluation_artifacts"] = [
            item
            for item in root["payload"]["evaluation_artifacts"]
            if item["artifact"]["artifact_kind"] != "review"
        ]
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "unsorted-artifacts":
        root["payload"]["evaluation_artifacts"].reverse()
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id == "artifact-source-mismatch":
        root["payload"]["evaluation_artifacts"][0]["artifact"][
            "content_sha256"
        ] = "d" * 64
        lineage.validate_record(_reseal(root), evidence)
        return
    if case_id in {
        "private-path",
        "synthetic-token",
        "gitlab-token",
        "raw-log",
    }:
        root["record_id"] = {
            "private-path": "/home/example/private-record",
            "synthetic-token": "ghp_" + "A" * 36,
            "gitlab-token": "glpat-abcdefghijklmnopqrstuvwxyz",
            "raw-log": "2026-07-30T04:00:00Z ERROR synthetic",
        }[case_id]
        lineage.validate_record(root, evidence)
        return
    if case_id == "projection-source-mismatch":
        manifest = lineage.build_human_projection(records, evidence)["manifest"]
        manifest["payload"]["sections"][0]["candidate_disposition"] = "rejected"
        lineage.validate_projection(
            lineage.seal_projection(manifest), records, evidence
        )
        return
    if case_id == "graph-edge-mismatch":
        manifest = lineage.build_graph_projection(records, evidence)
        manifest["payload"]["edges"][0]["to_node_id"] = manifest["payload"]["nodes"][
            -1
        ]["node_id"]
        lineage.validate_projection(
            lineage.seal_projection(manifest), records, evidence
        )
        return
    raise EvalConfigurationError("negative case implementation is missing")


def _validate_obsidian_profile(path: pathlib.Path) -> None:
    profile = lineage.load_json(path)
    if set(profile) != {
        "profile_id",
        "source_contract",
        "source_kind",
        "required_dependency",
        "target_mutation",
        "note_id_source",
        "link_style",
        "frontmatter",
        "authority_invariants",
    }:
        raise EvalConfigurationError("Obsidian profile has an invalid shape")
    if (
        profile["profile_id"] != "obsidian-reference/v0"
        or profile["source_contract"] != lineage.PROJECTION_CONTRACT_VERSION
        or profile["source_kind"] != lineage.HUMAN_KIND
        or profile["required_dependency"] is not False
        or profile["target_mutation"] is not False
        or profile["authority_invariants"] != lineage.oe.authority_invariants()
        or profile["note_id_source"] != "improvement_id"
        or profile["link_style"] != "escaped-stable-id-wikilink"
        or profile["frontmatter"]
        != {
            "baseline": "baseline_evidence_set_digest",
            "candidate": "candidate_evidence_set_digest",
            "disposition": "candidate_disposition",
            "improvement": "improvement_id",
            "record": "record_digest",
        }
    ):
        raise EvalConfigurationError("Obsidian profile violates its boundary")


def evaluate_suite(path: pathlib.Path = SUITE) -> dict[str, Any]:
    suite = load_suite(path)
    records, evidence = _fixture(suite)
    first = lineage.validate_lineage(records, evidence)
    second = lineage.validate_lineage(reversed(records), reversed(evidence))
    human_first = lineage.build_human_projection(records, evidence)
    human_second = lineage.build_human_projection(
        reversed(records), reversed(evidence)
    )
    graph_first = lineage.build_graph_projection(records, evidence)
    graph_second = lineage.build_graph_projection(
        reversed(records), reversed(evidence)
    )
    lineage.validate_projection(human_first["manifest"], records, evidence)
    lineage.validate_projection(graph_first, records, evidence)
    _validate_obsidian_profile(_resolve(suite["obsidian_profile"]))
    expected = suite["expected"]
    positive = [
        first["source_record_set_digest"] == second["source_record_set_digest"],
        human_first == human_second,
        graph_first == graph_second,
        first["source_record_set_digest"] == expected["source_record_set_digest"],
        human_first["manifest"]["projection_digest"]
        == expected["human_projection_digest"],
        graph_first["projection_digest"] == expected["graph_projection_digest"]
        and len(graph_first["payload"]["nodes"]) == expected["graph_nodes"]
        and len(graph_first["payload"]["edges"]) == expected["graph_edges"],
    ]
    observations = []
    for case in suite["cases"]:
        case_records, case_evidence = _fixture(suite)
        try:
            _run_negative(case["id"], case_records, case_evidence, suite)
            observed = "accepted"
        except lineage.ImprovementContractError as error:
            observed = error.code
        observations.append(
            {
                "id": case["id"],
                "expected_code": case["expected_code"],
                "observed_code": observed,
                "passed": observed == case["expected_code"],
            }
        )
    false_authority = sum(
        value is not False
        for output in (
            first["authority_invariants"],
            human_first["manifest"]["authority_invariants"],
            graph_first["authority_invariants"],
        )
        for value in output.values()
    )
    result = {
        "status": "passed"
        if all(positive)
        and all(item["passed"] for item in observations)
        and false_authority == expected["false_authority_claims"]
        else "failed",
        "positive_cases": sum(positive),
        "negative_cases": sum(item["passed"] for item in observations),
        "false_authority_claims": false_authority,
        "projection_mismatches": 0 if human_first == human_second and graph_first == graph_second else 1,
        "observations": observations,
    }
    if (
        result["positive_cases"] != expected["positive_cases"]
        or result["negative_cases"] != expected["negative_cases"]
        or result["projection_mismatches"] != expected["projection_mismatches"]
    ):
        result["status"] = "failed"
    return result


def main() -> int:
    try:
        result = evaluate_suite()
    except (EvalConfigurationError, lineage.ImprovementContractError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
