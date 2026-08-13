#!/usr/bin/env python3
"""Deterministic production-backed eval for Memory M0 operations."""

from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import memory_operation as operation  # noqa: E402
from tests import test_memory_operation as fixtures  # noqa: E402


def load(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rejected(callable_value: object) -> str:
    try:
        callable_value()  # type: ignore[operator]
    except operation.MemoryOperationError:
        return "rejected"
    return "accepted"


def main() -> int:
    suite = load("evals/memory-operation/suite.json")
    cases = load("evals/memory-operation/negative-cases.json")
    expected = {item["name"]: item["expected"] for item in cases}  # type: ignore[index]
    authority, candidate, eligibility, request = fixtures.bundle()
    if load("evals/memory-operation/" + suite["positive_fixture"]) != authority:
        raise SystemExit("memory operation positive fixture drifted")
    applied = fixtures.receipt(request)
    replay = fixtures.receipt(request, "idempotent-replay", applied)
    failed = fixtures.receipt(request, "failed")
    context = fixtures.validation_context(authority, candidate, eligibility)
    outcomes: dict[str, str] = {
        "valid-authority": "valid" if operation.validate_operation_authority(authority) else "rejected",
        "valid-authorized-request": "valid" if operation.validate_authorized_request(request, **context) else "rejected",
        "applied-receipt": operation.validate_execution_receipt(applied, request, **context)["payload"]["outcome"],
        "replay-receipt": operation.validate_execution_receipt(replay, request, original_applied_receipt=applied, **context)["payload"]["outcome"],
        "failed-receipt": operation.validate_execution_receipt(failed, request, **context)["payload"]["outcome"],
    }
    common = dict(
        authority_value=authority, mutation_candidate_value=candidate,
        eligibility_receipt_value=eligibility,
        accepted_eligibility_receipts={"receipt_digests": [eligibility["receipt_digest"]]},
        trusted_time_value=context["trusted_time_value"],
        accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
        expected_pre_state_digest=None,
    )
    outcomes["untrusted-authority"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": ["0" * 64]}, **common
    ))
    expired = dict(common)
    expired_clock = fixtures.trusted_time("2026-08-13T02:00:00Z")
    expired["trusted_time_value"] = expired_clock
    expired["accepted_trusted_time_receipts"] = {"receipt_digests": [expired_clock["receipt_digest"]]}
    outcomes["expired-authority"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]}, **expired
    ))
    wrong_scope = copy.deepcopy(candidate)
    wrong_scope["namespace"] = "other"
    scoped = dict(common)
    scoped["mutation_candidate_value"] = wrong_scope
    outcomes["scope-mismatch"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]}, **scoped
    ))
    tampered = copy.deepcopy(candidate)
    tampered["operation_id"] = "other-operation"
    changed = dict(common)
    changed["mutation_candidate_value"] = tampered
    outcomes["candidate-tamper"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]}, **changed
    ))
    wrong_record_scope = copy.deepcopy(candidate)
    wrong_record_scope["record"]["namespace"] = "other"
    wrong_record_scope["record"]["canonical_digest"] = operation.memory.canonical_digest(
        operation.memory.record_body(wrong_record_scope["record"])
    )
    scoped_authority = copy.deepcopy(authority)
    scoped_authority["payload"]["mutation_candidate_digest"] = operation.memory.canonical_digest(wrong_record_scope)
    scoped_authority = operation.seal_document(scoped_authority)
    record_scoped = dict(common)
    record_scoped["authority_value"] = scoped_authority
    record_scoped["mutation_candidate_value"] = wrong_record_scope
    outcomes["record-scope-mismatch"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]}, **record_scoped
    ))
    wrong_pre_state = copy.deepcopy(applied)
    wrong_pre_state["payload"]["pre_state_digest"] = "1" * 64
    wrong_pre_state = operation.seal_document(wrong_pre_state)
    outcomes["receipt-pre-state-mismatch"] = rejected(
        lambda: operation.validate_execution_receipt(wrong_pre_state, request, **context)
    )
    forged_request = copy.deepcopy(request)
    forged_request["payload"]["issuer_principal"] = {"kind": "human", "id": "other-maintainer"}
    forged_request = operation.seal_document(forged_request)
    outcomes["forged-request"] = rejected(
        lambda: operation.validate_authorized_request(forged_request, **context)
    )
    outcomes["forged-request-receipt"] = rejected(
        lambda: operation.validate_execution_receipt(applied, forged_request, **context)
    )
    untrusted_clock = fixtures.trusted_time()
    untrusted = dict(common)
    untrusted["trusted_time_value"] = untrusted_clock
    untrusted["accepted_trusted_time_receipts"] = {"receipt_digests": ["0" * 64]}
    outcomes["untrusted-time"] = rejected(lambda: operation.build_authorized_request(
        accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]}, **untrusted
    ))
    raised = copy.deepcopy(authority)
    raised["authority_invariants"]["promotion_authorized"] = True
    raised = operation.seal_document(raised)
    outcomes["false-authority"] = rejected(lambda: operation.validate_operation_authority(raised))
    delete_authority, _, _, delete_request = fixtures.bundle("delete")
    outcomes["delete-is-logical"] = delete_request["payload"]["lifecycle_effect"]
    cli = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "operationctl.py"), "execute"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    outcomes["execution-route"] = "rejected" if cli.returncode == 2 else "accepted"
    correct = sum(outcomes.get(name) == value for name, value in expected.items())
    metrics = {
        "cases": len(outcomes),
        "decision_accuracy": correct / len(expected),
        "binding_completeness": 1.0 if all(outcomes[name] == "rejected" for name in ("scope-mismatch", "candidate-tamper", "record-scope-mismatch", "forged-request")) else 0.0,
        "determinism": 1.0 if fixtures.bundle()[3] == request else 0.0,
        "atomicity_boundary": 1.0 if applied["payload"]["atomic_state_and_receipt_committed"] and not failed["payload"]["atomic_state_and_receipt_committed"] else 0.0,
        "idempotency_boundary": 1.0 if replay["payload"]["no_second_application"] else 0.0,
        "privacy_safe_rejection": 1.0 if "traceback" not in cli.stderr.lower() else 0.0,
        "false_authority": sum(outcomes[name] != "rejected" for name in ("untrusted-authority", "expired-authority", "untrusted-time", "forged-request")),
        "unauthorized_execution": sum(outcomes[name] != "rejected" for name in ("forged-request-receipt", "execution-route")),
        "physical_purge": 1 if "purge" in repr((delete_authority, delete_request)).lower() else 0,
    }
    if metrics != suite["expected"]:
        raise SystemExit("memory operation eval thresholds failed")
    print(json.dumps({"status": "passed", "metrics": metrics}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
