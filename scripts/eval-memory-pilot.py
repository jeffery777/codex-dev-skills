#!/usr/bin/env python3
"""Verify digest-bound synthetic observations for the thin local M1 pilot."""
from __future__ import annotations

import copy
import json
import pathlib
import re
import sys
import tempfile
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "loop-engineering" / "scripts"))
import memory_pilot_off as off  # noqa: E402
import memory_contract as memory  # noqa: E402
import memory_pilot as pilot  # noqa: E402
import memory_sqlite as sqlite  # noqa: E402
import operational_evidence as oe  # noqa: E402
from tests import test_memory_contract as record_fixtures  # noqa: E402
from tests import test_memory_pilot as pilot_fixtures  # noqa: E402
from tests import test_memory_sqlite as sqlite_fixtures  # noqa: E402


METRIC_SCHEMA = {
    "retrieval_precision": {"minimum"},
    "stale_memory_rejection": {"minimum"},
    "false_authority_rate": {"maximum"},
    "task_result_non_regression": {"minimum"},
    "bounded_context_reduction": {"minimum_net_tokens", "overhead_tokens"},
    "memory_on_backend_touch": {"minimum"},
}


def _body(value: dict) -> dict:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != "suite_digest"}


def _recall_context(request: dict, record_ids: list[str]) -> tuple[dict, dict]:
    retrieval = record_fixtures.retrieval_input(request=request, records=[])
    retrieval["current"]["source_revision_relations"] = {
        record_id: "exact" for record_id in record_ids
    }
    retrieval["handshake"]["adapter"].update({
        "adapter_id": sqlite.ADAPTER_ID,
        "adapter_version": sqlite.ADAPTER_VERSION,
    })
    evidence = {
        sqlite.ADAPTER_ID: {
            "receipt_digest": "c" * 64,
            "adapter_fingerprint": memory.canonical_digest({
                "adapter": retrieval["handshake"]["adapter"],
                "capabilities": retrieval["handshake"]["capabilities"],
            }),
        }
    }
    return {key: retrieval[key] for key in ("handshake", "current", "extensions")}, evidence


def _remember(bundle: tuple[dict, dict, dict, dict], pilot_class: str, state: pathlib.Path) -> None:
    authority, candidate, eligibility, context = bundle
    pilot.remember(
        pilot_fixtures.envelope("remember", pilot_class), authority, candidate, eligibility,
        accepted_authority_receipts=context["accepted_authority_receipts"],
        accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
        trusted_time=context["trusted_time_value"],
        accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
        expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
    )


def _tokens(value: object) -> int:
    return len(re.findall(r"[A-Za-z0-9_-]+", oe.canonical_json(value)))


def _synthetic_task(advisory_context: list[dict]) -> dict:
    """Answer from repository authority; reject conflicting advisory versions."""
    version = yaml.safe_load((ROOT / "catalog.yaml").read_text(encoding="utf-8"))["version"]
    context_versions = {
        match
        for item in advisory_context
        for match in re.findall(r"\b\d+\.\d+\.\d+\b", item["content"])
    }
    return {
        "status": "conflict" if any(match != version for match in context_versions) else "answered",
        "version": version,
        "authority": "repository",
    }


def _observe_cases() -> tuple[list[dict], int, bool]:
    off_task_result = _synthetic_task([])
    with tempfile.TemporaryDirectory() as directory:
        state = sqlite_fixtures.secure_state_root(pathlib.Path(directory))
        sqlite.initialize(state, ROOT)
        relevant = pilot_fixtures.profiled_bundle(
            state, suffix="eval-relevant", record_id="record-eval-relevant",
            content="Repository evidence identifies candidate version 0.23.0.",
        )
        _remember(relevant, "verified-fact", state)
        request = sqlite_fixtures.query_request()
        context, conformance = _recall_context(request, ["record-eval-relevant"])
        source_ref = next(
            ref for ref in relevant[1]["record"]["provenance"]["source_refs"]
            if ref["kind"] == "repository-artifact"
        )
        trusted_sources = {source_ref["locator"]: source_ref["digest"]}
        first = pilot.recall(
            pilot_fixtures.envelope("recall"), request, context,
            trusted_conformance_receipts=conformance,
            trusted_source_digests=trusted_sources,
            state_root=state, repository_root=ROOT,
        )
        controller = pilot_fixtures.profiled_bundle(
            state, pilot_class="decision", suffix="eval-controller",
            record_id="record-eval-controller", supersedes=["record-eval-relevant"],
        )
        _remember(controller, "decision", state)
        context, conformance = _recall_context(
            request, ["record-eval-relevant", "record-eval-controller"],
        )
        second = pilot.recall(
            pilot_fixtures.envelope("recall"), request, context,
            trusted_conformance_receipts=conformance,
            trusted_source_digests=trusted_sources,
            state_root=state, repository_root=ROOT,
        )
        first_dispositions = {
            item["record_id"]: item for item in first["retrieval_receipt"]["dispositions"]
        }
        second_dispositions = {
            item["record_id"]: item for item in second["retrieval_receipt"]["dispositions"]
        }
        record_digest = relevant[1]["record"]["canonical_digest"]
        observations = [
            {
                "id": "verified-relevant", "relevant": True,
                "retrieved": "record-eval-relevant" in first_dispositions,
                "adopted": record_digest in first["adopted_record_digests"],
                "stale_rejected": False,
                "authority_used": first["authority"] != "advisory-only" or any(
                    item["confidence_used_as_authority"]
                    for item in first["retrieval_receipt"]["dispositions"]
                ),
                "task_result_equal": _synthetic_task(first["adopted_context"]) == off_task_result,
                "context_before_tokens": _tokens(relevant[1]["record"]),
                "context_after_tokens": _tokens(first["adopted_context"]),
            },
            {
                "id": "stale-rejected", "relevant": False,
                "retrieved": "record-eval-relevant" in second_dispositions,
                "adopted": record_digest in second["adopted_record_digests"],
                "stale_rejected": "invalidated-or-superseded-by-related-record"
                in second_dispositions["record-eval-relevant"]["reasons"],
                "authority_used": second["authority"] != "advisory-only" or any(
                    item["confidence_used_as_authority"]
                    for item in second["retrieval_receipt"]["dispositions"]
                ),
                "task_result_equal": _synthetic_task(second["adopted_context"]) == off_task_result,
                "context_before_tokens": _tokens(relevant[1]["record"]),
                "context_after_tokens": _tokens(second["adopted_context"]),
            },
        ]
        sqlite.integrity(state, ROOT)
    return observations, 1


def evaluate(suite: dict) -> dict:
    expected = {"contract_version", "kind", "metrics", "cases", "pass_status", "prohibitions", "suite_digest"}
    if set(suite) != expected or suite["contract_version"] != "memory-m1-local-pilot-eval/v1" or suite["kind"] != "synthetic-pre-registration":
        raise ValueError("invalid suite")
    if suite["suite_digest"] != oe.canonical_digest(_body(suite)):
        raise ValueError("tampered suite")
    metrics = suite["metrics"]
    if not isinstance(metrics, dict) or set(metrics) != set(METRIC_SCHEMA):
        raise ValueError("invalid metrics")
    for name, fields in METRIC_SCHEMA.items():
        value = metrics[name]
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("invalid metrics")
        if any(type(item) not in {int, float} or item < 0 for item in value.values()):
            raise ValueError("invalid metrics")
    if any(metrics[name][field] > 1 for name, field in (
        ("retrieval_precision", "minimum"),
        ("stale_memory_rejection", "minimum"),
        ("false_authority_rate", "maximum"),
        ("task_result_non_regression", "minimum"),
    )):
        raise ValueError("invalid metrics")
    cases = suite["cases"]
    required = {"id", "scenario", "expected"}
    if not isinstance(cases, list) or not cases or any(not isinstance(case, dict) or set(case) != required for case in cases):
        raise ValueError("invalid cases")
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("invalid cases")
    for case in cases:
        if not isinstance(case["id"], str) or not case["id"] or not isinstance(case["scenario"], str):
            raise ValueError("invalid cases")
        expected_case = case["expected"]
        if not isinstance(expected_case, dict) or set(expected_case) != {"relevant", "retrieved", "adopted", "stale_rejected"}:
            raise ValueError("invalid cases")
        if any(type(expected_case[field]) is not bool for field in expected_case):
            raise ValueError("invalid cases")
    if {case["id"]: case["scenario"] for case in cases} != {
        "verified-relevant": "remember-and-recall",
        "stale-rejected": "cross-class-supersession",
    }:
        raise ValueError("invalid cases")
    if suite["pass_status"] != "synthetic-pilot-qualified-awaiting-human-decision" or suite["prohibitions"] != ["activation", "promotion", "real-user-efficacy"]:
        raise ValueError("invalid qualification boundary")
    observations, backend_touches = _observe_cases()
    expected_by_id = {case["id"]: case["expected"] for case in cases}
    if {case["id"] for case in observations} != set(expected_by_id):
        raise ValueError("observation mismatch")
    for observation in observations:
        expected_case = expected_by_id[observation["id"]]
        if any(observation[field] is not expected_case[field] for field in expected_case):
            raise ValueError("observation mismatch")
    adopted = [case for case in observations if case["adopted"]]
    stale = [case for case in observations if not case["relevant"]]
    outcomes = {
        "retrieval_precision": sum(bool(case["relevant"]) for case in adopted) / len(adopted) if adopted else 0.0,
        "stale_memory_rejection": sum(bool(case["retrieved"] and case["stale_rejected"] and not case["adopted"]) for case in stale) / len(stale) if stale else 0.0,
        "false_authority_rate": sum(bool(case["authority_used"]) for case in observations) / len(observations),
        "task_result_non_regression": sum(bool(case["task_result_equal"]) for case in observations) / len(observations),
        "bounded_context_reduction": sum(case["context_before_tokens"] - case["context_after_tokens"] for case in observations) - suite["metrics"]["bounded_context_reduction"]["overhead_tokens"],
        "memory_off_zero_touch": off.no_memory()["backend_touch_count"],
        "memory_on_backend_touch": backend_touches,
    }
    passed = (
        outcomes["retrieval_precision"] >= metrics["retrieval_precision"]["minimum"]
        and outcomes["stale_memory_rejection"] >= metrics["stale_memory_rejection"]["minimum"]
        and outcomes["false_authority_rate"] <= metrics["false_authority_rate"]["maximum"]
        and outcomes["task_result_non_regression"] >= metrics["task_result_non_regression"]["minimum"]
        and outcomes["bounded_context_reduction"] >= metrics["bounded_context_reduction"]["minimum_net_tokens"]
        and outcomes["memory_off_zero_touch"] == 0
        and outcomes["memory_on_backend_touch"] >= metrics["memory_on_backend_touch"]["minimum"]
    )
    return {
        "status": suite["pass_status"] if passed else "not-qualified",
        "synthetic_only": True,
        "authority": "advisory-only",
        "promotion_authorized": False,
        "suite_digest": suite["suite_digest"],
        "observation_digest": oe.canonical_digest(observations),
        "outcomes": outcomes,
    }


def main() -> int:
    try:
        suite = oe.load_json(ROOT / "evals" / "memory-pilot" / "suite.json")
        result = evaluate(suite)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] == suite["pass_status"] else 1
    except (OSError, ValueError, json.JSONDecodeError, sqlite.MemorySQLiteError, oe.OperationalEvidenceError):
        print('{"status":"rejected"}', file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
