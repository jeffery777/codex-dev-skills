#!/usr/bin/env python3
"""Deterministic production-backed safety/conformance eval for Memory M1."""

from __future__ import annotations

import copy
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import memory_contract as memory  # noqa: E402
import memory_qualification as qualification  # noqa: E402
import memory_sqlite as adapter  # noqa: E402
from tests import test_memory_qualification as qualification_fixtures  # noqa: E402
from tests import test_memory_sqlite as fixtures  # noqa: E402


def load(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rejected(callable_value: object) -> str:
    try:
        callable_value()  # type: ignore[operator]
    except (adapter.MemorySQLiteError, memory.MemoryContractError):
        return "rejected"
    return "accepted"


def main() -> int:
    suite = load("evals/memory-sqlite/suite.json")
    cases = load("evals/memory-sqlite/negative-cases.json")
    expected = {item["name"]: item["expected"] for item in cases}  # type: ignore[index]
    outcomes: dict[str, str] = {}
    first_probe = adapter.probe()
    outcomes["probe-qualified"] = first_probe["status"]

    with tempfile.TemporaryDirectory() as directory:
        parent = pathlib.Path(directory)
        state = fixtures.secure_state_root(parent)
        outcomes["initialize-exact-schema"] = adapter.initialize(state, ROOT)["status"]
        applied, bundle = fixtures.execute(state)
        outcomes["authorized-applied"] = applied["payload"]["outcome"]
        queried = adapter.query(fixtures.query_request(), state, ROOT)
        outcomes["structured-query"] = queried["records"][0]["record_id"]
        replayed, _ = fixtures.execute(state)
        outcomes["exact-replay"] = replayed["payload"]["outcome"]

        authority, candidate, eligibility, context = bundle
        recovered = adapter.lookup_receipt(
            authority, candidate, eligibility,
            accepted_authority_receipts=context["accepted_authority_receipts"],
            accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
            trusted_time_value=context["trusted_time_value"],
            accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
            expected_pre_state_digest=context["expected_pre_state_digest"],
            state_root=state, repository_root=ROOT,
        )
        recovery_rejected = rejected(lambda: adapter.lookup_receipt(
            authority, candidate, eligibility,
            accepted_authority_receipts={"receipt_digests": ["0" * 64]},
            accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
            trusted_time_value=context["trusted_time_value"],
            accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
            expected_pre_state_digest=context["expected_pre_state_digest"],
            state_root=state, repository_root=ROOT,
        ))
        outcomes["receipt-recovery"] = (
            "authorized-only"
            if recovered == applied and recovery_rejected == "rejected"
            else "unsafe"
        )

        raw = fixtures.query_request()
        raw["extensions"][adapter.QUERY_EXTENSION]["terms"] = ["alpha OR beta"]
        outcomes["raw-fts-rejected"] = rejected(lambda: adapter.query(raw, state, ROOT))

        scoped = fixtures.query_request()
        scoped["namespace"] = "other"
        outcomes["scope-isolation"] = (
            "isolated" if adapter.query(scoped, state, ROOT)["records"] == [] else "disclosed"
        )

        deleted, _ = fixtures.execute(state, "delete", suffix="delete")
        retained = adapter.integrity(state, ROOT)["counts"]["records"] == 1
        invisible = adapter.query(fixtures.query_request(), state, ROOT)["records"] == []
        outcomes["logical-delete"] = (
            "retained-not-retrieved"
            if deleted["payload"]["outcome"] == "applied" and retained and invisible
            else "failed"
        )

        outcomes["untrusted-authority"] = rejected(lambda: adapter.execute_authorized_operation(
            authority, candidate, eligibility,
            accepted_authority_receipts={"receipt_digests": ["0" * 64]},
            accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
            trusted_time_value=context["trusted_time_value"],
            accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
            expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
        ))
        sensitive = copy.deepcopy(candidate["record"])
        sensitive["sensitivity"]["classification"] = "confidential"
        sensitive["canonical_digest"] = memory.canonical_digest(memory.record_body(sensitive))
        outcomes["privacy-record"] = rejected(
            lambda: adapter._public_internal_record(sensitive)
        )

        result, verified = qualification_fixtures.v3b_pair()
        source = qualification_fixtures.qualification_input(result, verified, with_on=True)
        source = copy.deepcopy(source)
        source["on_arm"]["adapter"] = copy.deepcopy(first_probe["adapter"])
        source["on_arm"]["safety_observation"]["execution_receipt_digests"] = [applied["document_digest"]]
        candidate_receipt = qualification.seal_m1_receipt({
            "contract_version": qualification.CONTRACT_VERSION,
            "kind": qualification.M1_RECEIPT_KIND,
            "qualification_id": source["qualification_id"],
            "common_v3b_bindings": copy.deepcopy(source["common_v3b_bindings"]),
            "adapter": copy.deepcopy(source["on_arm"]["adapter"]),
            "safety_observation_digest": qualification.oe.canonical_digest(
                source["on_arm"]["safety_observation"]
            ),
            "execution_receipt_digests": [applied["document_digest"]],
            "status": "passed",
        })
        source["on_arm"]["m1_qualification_receipt_digest"] = candidate_receipt["receipt_digest"]
        source = qualification.seal_input(source)
        qualified = adapter.build_qualification_receipt(
            source, source["on_arm"]["safety_observation"],
            [fixtures.execution_evidence(applied, bundle)],
        )
        outcomes["qualification-receipt"] = qualified["status"]

        off_source = qualification_fixtures.qualification_input(result, verified, with_on=False)
        with mock.patch.object(adapter, "probe", side_effect=AssertionError("adapter touched")):
            off_result = qualification.build_qualification_result(
                off_source, result, verified,
                accepted_v3b_receipts=qualification_fixtures.accepted(result, verified),
            )
        outcomes["memory-off-zero-touch"] = (
            "zero-touch" if off_result["off_arm"]["backend_touch_count"] == 0 else "touched"
        )

    with tempfile.TemporaryDirectory() as directory:
        state = fixtures.secure_state_root(pathlib.Path(directory))
        adapter.initialize(state, ROOT)
        failed, _ = fixtures.execute(state, fault="before-commit")
        empty = adapter.integrity(state, ROOT)["counts"] == {"operations": 0, "records": 0}
        outcomes["fault-rollback"] = (
            "failed-empty" if failed["payload"]["outcome"] == "failed" and empty else "partial"
        )

        database = state / adapter.DATABASE_NAME
        connection = sqlite3.connect(database)
        connection.execute("PRAGMA user_version=2")
        connection.close()
        connection = sqlite3.connect(database)
        observed_user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        connection.close()
        outcomes["schema-drift"] = (
            "rejected-no-repair"
            if rejected(lambda: adapter.integrity(state, ROOT)) == "rejected"
            and observed_user_version == 2
            else "accepted-or-repaired"
        )

    with tempfile.TemporaryDirectory() as directory:
        unsafe = pathlib.Path(directory) / "unsafe"
        unsafe.mkdir(mode=0o755)
        unsafe.chmod(0o755)
        outcomes["unsafe-root"] = rejected(lambda: adapter.validate_state_root(unsafe, ROOT))

    outcomes["manual-ci-equivalence"] = (
        "equivalent" if adapter.probe() == first_probe else "different"
    )
    cli = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "sqlitectl.py"), "purge"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    outcomes["action-route"] = "rejected" if cli.returncode == 2 else "accepted"

    correct = sum(outcomes.get(name) == value for name, value in expected.items())
    metrics = {
        "cases": len(outcomes),
        "decision_accuracy": correct / len(expected),
        "authority_failures": int(outcomes["untrusted-authority"] != "rejected"),
        "identity_failures": int(outcomes["scope-isolation"] != "isolated"),
        "atomicity_failures": int(outcomes["fault-rollback"] != "failed-empty"),
        "idempotency_failures": int(outcomes["exact-replay"] != "idempotent-replay"),
        "lifecycle_failures": int(outcomes["logical-delete"] != "retained-not-retrieved"),
        "privacy_failures": int(outcomes["privacy-record"] != "rejected"),
        "recovery_failures": int(outcomes["receipt-recovery"] != "authorized-only"),
        "schema_drift_failures": int(outcomes["schema-drift"] != "rejected-no-repair"),
        "unauthorized_routes": int(outcomes["action-route"] != "rejected"),
        "efficacy_claims": 0,
    }
    if metrics != suite["expected"]:  # type: ignore[index]
        raise SystemExit("memory sqlite eval thresholds failed")
    print(json.dumps({"status": "passed", "metrics": metrics, "outcomes": outcomes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
