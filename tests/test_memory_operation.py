from __future__ import annotations

import copy
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import memory_contract as memory  # noqa: E402
import memory_operation as operation  # noqa: E402
from tests import test_memory_contract as fixtures  # noqa: E402


def trusted_time(observed_at: str = "2026-08-13T00:30:00Z") -> dict:
    return operation.seal_trusted_time({
        "contract_version": operation.CONTRACT_VERSION,
        "kind": operation.TRUSTED_TIME_KIND,
        "clock_id": "caller-clock-1",
        "observed_at": observed_at,
    })


def validation_context(authority: dict, candidate: dict, eligibility: dict, observed_at: str = "2026-08-13T00:30:00Z") -> dict:
    clock = trusted_time(observed_at)
    return {
        "authority_value": authority,
        "mutation_candidate_value": candidate,
        "eligibility_receipt_value": eligibility,
        "accepted_authority_receipts": {"receipt_digests": [authority["payload"]["authority_receipt_digest"]]},
        "accepted_eligibility_receipts": {"receipt_digests": [eligibility["receipt_digest"]]},
        "trusted_time_value": clock,
        "accepted_trusted_time_receipts": {"receipt_digests": [clock["receipt_digest"]]},
        "expected_pre_state_digest": authority["payload"]["target_before_digest"],
    }


def bundle(operation_kind: str = "upsert") -> tuple[dict, dict, dict, dict]:
    record = fixtures.record()
    eligibility = fixtures.decide_write(fixtures.write_input(candidate=record))
    candidate = {
        "contract_version": memory.CONTRACT_VERSION,
        "kind": "mutation-candidate-request",
        "operation": operation_kind,
        "operation_id": "mutation-1",
        "request_id": "mutation-request-1",
        "idempotency_key": "mutation-key-1",
        "repository": copy.deepcopy(record["repository"]),
        "namespace": record["namespace"],
        "target_record_id": record["record_id"],
        "record": record if operation_kind == "upsert" else None,
        "reason": None if operation_kind == "upsert" else "accepted lifecycle transition",
        "eligibility_receipt_digest": eligibility["receipt_digest"],
        "required_capabilities": [
            {"upsert": "write_upsert", "invalidate": "invalidate", "tombstone": "tombstone", "delete": "delete"}[operation_kind],
            "idempotency",
        ],
        "candidate_only": True,
        "external_write_authorized": False,
        "write_performed": False,
        "extensions": {},
    }
    authority_receipt = "a" * 64
    authority = operation.seal_document({
        "contract_version": operation.CONTRACT_VERSION,
        "kind": operation.AUTHORITY_KIND,
        "document_id": "authority-1",
        "repository": copy.deepcopy(record["repository"]),
        "namespace": record["namespace"],
        "payload": {
            "authority_id": "authority-1",
            "issuer_principal": {"kind": "human", "id": "maintainer-1"},
            "issued_at": "2026-08-13T00:00:00Z",
            "expires_at": "2026-08-13T01:00:00Z",
            "nonce": "nonce-1",
            "operation": operation_kind,
            "operation_id": candidate["operation_id"],
            "request_id": candidate["request_id"],
            "idempotency_key": candidate["idempotency_key"],
            "target_record_id": candidate["target_record_id"],
            "target_before_digest": None if operation_kind == "upsert" else record["canonical_digest"],
            "candidate_record_digest": record["canonical_digest"],
            "mutation_candidate_digest": memory.canonical_digest(candidate),
            "eligibility_receipt_digests": [eligibility["receipt_digest"]],
            "lifecycle_effect": "logical-delete" if operation_kind == "delete" else operation_kind,
            "adapter": {
                "adapter_id": "future-adapter",
                "adapter_version": "m1-candidate",
                "schema_fingerprint": "b" * 64,
                "capability_fingerprint": "c" * 64,
                "required_capabilities": sorted(candidate["required_capabilities"]),
            },
            "state_root": {"state_root_class": "approved-machine-local", "identity_digest": "d" * 64},
            "authority_receipt_digest": authority_receipt,
            "memory_operation_authorized": True,
        },
        "authority_invariants": operation.authority_invariants(),
    })
    request = operation.build_authorized_request(authority, candidate, eligibility, **{
        key: value for key, value in validation_context(authority, candidate, eligibility).items()
        if key not in {"authority_value", "mutation_candidate_value", "eligibility_receipt_value"}
    })
    return authority, candidate, eligibility, request


def receipt(request: dict, outcome: str = "applied", original: dict | None = None) -> dict:
    source = request["payload"]
    return operation.seal_document({
        "contract_version": operation.CONTRACT_VERSION,
        "kind": operation.RECEIPT_KIND,
        "document_id": f"execution-{outcome}",
        "repository": copy.deepcopy(request["repository"]),
        "namespace": request["namespace"],
        "payload": {
            "authorized_request_digest": request["document_digest"],
            "authority_document_digest": source["authority_document_digest"],
            "authority_receipt_digest": source["authority_receipt_digest"],
            "eligibility_receipt_digest": source["eligibility_receipt_digest"],
            "mutation_candidate_digest": source["mutation_candidate_digest"],
            "operation": source["operation"], "operation_id": source["operation_id"],
            "request_id": source["request_id"], "idempotency_key": source["idempotency_key"],
            "target_record_id": source["target_record_id"],
            "adapter": copy.deepcopy(source["adapter"]),
            "platform_fingerprint": "e" * 64,
            "transaction_id": f"transaction-{outcome}",
            "outcome": outcome,
            "failure_code": "transaction-failure" if outcome == "failed" else None,
            "pre_state_digest": source["expected_pre_state_digest"],
            "post_state_digest": None if outcome == "failed" else "f" * 64,
            "original_applied_receipt_digest": original["document_digest"] if original else None,
            "atomic_state_and_receipt_committed": outcome != "failed",
            "no_partial_success": True,
            "no_uncertain_success": True,
            "no_second_application": True,
        },
        "authority_invariants": operation.authority_invariants(),
    })


class MemoryOperationTests(unittest.TestCase):
    def test_authorized_request_requires_caller_owned_receipts_and_exact_bindings(self):
        authority, candidate, eligibility, request = bundle()
        self.assertEqual(operation.REQUEST_KIND, request["kind"])
        self.assertTrue(request["payload"]["authority_verified_for_exact_request"])
        with self.assertRaisesRegex(operation.MemoryOperationError, "caller-accepted"):
            operation.build_authorized_request(
                authority, candidate, eligibility,
                accepted_authority_receipts={"receipt_digests": ["0" * 64]},
                accepted_eligibility_receipts={"receipt_digests": [eligibility["receipt_digest"]]},
                trusted_time_value=trusted_time(), accepted_trusted_time_receipts={"receipt_digests": [trusted_time()["receipt_digest"]]},
                expected_pre_state_digest=None,
            )
        tampered = copy.deepcopy(candidate)
        tampered["namespace"] = "other"
        with self.assertRaises(operation.MemoryOperationError):
            operation.build_authorized_request(
                authority, tampered, eligibility,
                accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]},
                accepted_eligibility_receipts={"receipt_digests": [eligibility["receipt_digest"]]},
                trusted_time_value=trusted_time(), accepted_trusted_time_receipts={"receipt_digests": [trusted_time()["receipt_digest"]]},
                expected_pre_state_digest=None,
            )

    def test_expired_authority_fails_closed(self):
        authority, candidate, eligibility, _ = bundle()
        with self.assertRaisesRegex(operation.MemoryOperationError, "currently valid"):
            operation.build_authorized_request(
                authority, candidate, eligibility,
                accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]},
                accepted_eligibility_receipts={"receipt_digests": [eligibility["receipt_digest"]]},
                trusted_time_value=trusted_time("2026-08-13T02:00:00Z"), accepted_trusted_time_receipts={"receipt_digests": [trusted_time("2026-08-13T02:00:00Z")["receipt_digest"]]},
                expected_pre_state_digest=None,
            )

    def test_upsert_record_scope_must_match_candidate_envelope(self):
        authority, candidate, eligibility, _ = bundle()
        changed = copy.deepcopy(candidate)
        changed["record"]["namespace"] = "other"
        changed["record"]["canonical_digest"] = memory.canonical_digest(
            memory.record_body(changed["record"])
        )
        authority["payload"]["mutation_candidate_digest"] = memory.canonical_digest(changed)
        authority = operation.seal_document(authority)
        with self.assertRaisesRegex(operation.MemoryOperationError, "record scope"):
            operation.build_authorized_request(
                authority, changed, eligibility,
                accepted_authority_receipts={"receipt_digests": [authority["payload"]["authority_receipt_digest"]]},
                accepted_eligibility_receipts={"receipt_digests": [eligibility["receipt_digest"]]},
                trusted_time_value=trusted_time(), accepted_trusted_time_receipts={"receipt_digests": [trusted_time()["receipt_digest"]]},
                expected_pre_state_digest=None,
            )

    def test_applied_replay_and_failure_receipts_preserve_atomicity(self):
        authority, candidate, eligibility, request = bundle()
        context = validation_context(authority, candidate, eligibility)
        applied = receipt(request)
        self.assertEqual("applied", operation.validate_execution_receipt(applied, request, **context)["payload"]["outcome"])
        replay = receipt(request, "idempotent-replay", applied)
        self.assertEqual("idempotent-replay", operation.validate_execution_receipt(replay, request, original_applied_receipt=applied, **context)["payload"]["outcome"])
        failed = receipt(request, "failed")
        self.assertEqual("failed", operation.validate_execution_receipt(failed, request, **context)["payload"]["outcome"])
        raised = copy.deepcopy(failed)
        raised["payload"]["atomic_state_and_receipt_committed"] = True
        raised = operation.seal_document(raised)
        with self.assertRaisesRegex(operation.MemoryOperationError, "failed receipt"):
            operation.validate_execution_receipt(raised, request, **context)
        wrong_pre_state = copy.deepcopy(applied)
        wrong_pre_state["payload"]["pre_state_digest"] = "1" * 64
        wrong_pre_state = operation.seal_document(wrong_pre_state)
        with self.assertRaisesRegex(operation.MemoryOperationError, "pre-state"):
            operation.validate_execution_receipt(wrong_pre_state, request, **context)

    def test_v2b_delete_is_logical_and_physical_purge_is_absent(self):
        authority, _, _, request = bundle("delete")
        self.assertEqual("delete", authority["payload"]["operation"])
        self.assertEqual("logical-delete", request["payload"]["lifecycle_effect"])
        self.assertNotIn("purge", repr(request).lower())

    def test_false_authority_or_tamper_rejects(self):
        authority, _, _, _ = bundle()
        raised = copy.deepcopy(authority)
        raised["authority_invariants"]["promotion_authorized"] = True
        raised = operation.seal_document(raised)
        with self.assertRaisesRegex(operation.MemoryOperationError, "invariants"):
            operation.validate_operation_authority(raised)


if __name__ == "__main__":
    unittest.main()
