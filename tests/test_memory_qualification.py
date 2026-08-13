from __future__ import annotations

import ast
import copy
import pathlib
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import candidate_evaluation as evaluation  # noqa: E402
import memory_qualification as qualification  # noqa: E402
from tests import test_candidate_evaluation as fixtures  # noqa: E402


def v3b_pair() -> tuple[dict, dict]:
    records, evidence, proposal_set, selected = fixtures.source_bundle()
    source = fixtures.evaluation_input(selected)
    result = evaluation.build_evaluation_result(source, proposal_set, records, evidence)
    verified = evaluation.verify_evaluation_result(result, source, proposal_set, records, evidence)
    return result, verified


def qualification_input(result: dict, verified: dict, *, with_on: bool) -> dict:
    on_arm = None
    if with_on:
        on_arm = {
            "mode": "memory-on",
            "evaluation_result_digest": result["evaluation_result_digest"],
            "verification_result_digest": verified["verification_result_digest"],
            "m1_qualification_receipt_digest": "0" * 64,
            "adapter": {
                "adapter_id": "future-adapter", "adapter_version": "m1-candidate",
                "schema_fingerprint": "b" * 64, "capability_fingerprint": "c" * 64,
                "platform_fingerprint": "d" * 64,
            },
            "safety_observation": {
                "authority_failures": 0, "identity_failures": 0,
                "atomicity_failures": 0, "idempotency_failures": 0,
                "lifecycle_failures": 0, "privacy_failures": 0,
                "recovery_failures": 0, "schema_drift_failures": 0,
                "backend_touch_count": 1,
                "execution_receipt_digests": ["e" * 64],
            },
        }
    source = {
        "contract_version": qualification.CONTRACT_VERSION,
        "kind": qualification.INPUT_KIND,
        "qualification_id": "qualification-1",
        "common_v3b_bindings": qualification._common_bindings(result, verified),
        "off_arm": {
            "mode": "memory-off",
            "evaluation_result_digest": result["evaluation_result_digest"],
            "verification_result_digest": verified["verification_result_digest"],
            "backend_touch_count": 0,
            "zero_backend_filesystem_touch_verified": True,
        },
        "on_arm": on_arm,
        "efficacy_claimed": False,
        "authority_invariants": qualification.authority_invariants(),
    }
    if with_on:
        receipt = m1_receipt(source)
        source["on_arm"]["m1_qualification_receipt_digest"] = receipt["receipt_digest"]
    return qualification.seal_input(source)


def m1_receipt(source: dict) -> dict:
    on = source["on_arm"]
    safety = on["safety_observation"]
    return qualification.seal_m1_receipt({
        "contract_version": qualification.CONTRACT_VERSION,
        "kind": qualification.M1_RECEIPT_KIND,
        "qualification_id": source["qualification_id"],
        "common_v3b_bindings": copy.deepcopy(source["common_v3b_bindings"]),
        "adapter": copy.deepcopy(on["adapter"]),
        "safety_observation_digest": qualification.oe.canonical_digest(safety),
        "execution_receipt_digests": copy.deepcopy(safety["execution_receipt_digests"]),
        "status": "passed",
    })


def m1_args(source: dict) -> dict:
    receipt = m1_receipt(source)
    return {
        "m1_qualification_receipt_value": receipt,
        "accepted_m1_qualification_receipts": {"qualification_receipt_digests": [receipt["receipt_digest"]]},
    }


def accepted(result: dict, verified: dict) -> dict:
    return {"receipt_digests": sorted([result["evaluation_result_digest"], verified["verification_result_digest"]])}


class MemoryQualificationTests(unittest.TestCase):
    def test_memory_off_is_complete_and_never_touches_adapter_seam(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=False)
        with mock.patch.object(qualification, "_adapter", side_effect=AssertionError("adapter touched")):
            output = qualification.build_qualification_result(
                source, result, verified, accepted_v3b_receipts=accepted(result, verified)
            )
        self.assertEqual("memory-on-unavailable", output["status"])
        self.assertEqual(0, output["off_arm"]["backend_touch_count"])
        self.assertIsNone(output["on_arm"])
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "cannot accept M1 inputs"):
            qualification.build_qualification_result(
                source, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                m1_qualification_receipt_value={"arbitrary": "unvalidated"},
            )

    def test_paired_safety_conformance_passes_without_efficacy_claim(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=True)
        output = qualification.build_qualification_result(
            source, result, verified,
            accepted_v3b_receipts=accepted(result, verified),
            on_result_value=result, on_verification_value=verified,
            **m1_args(source),
        )
        self.assertEqual("conformant-awaiting-human-decision", output["status"])
        self.assertFalse(output["efficacy_claimed"])
        self.assertEqual("pending", output["promotion_gate"]["status"])

    def test_failures_and_pair_mismatch_cannot_conform(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=True)
        source["on_arm"]["safety_observation"]["privacy_failures"] = 1
        changed_receipt = m1_receipt(source)
        source["on_arm"]["m1_qualification_receipt_digest"] = changed_receipt["receipt_digest"]
        source = qualification.seal_input(source)
        output = qualification.build_qualification_result(
            source, result, verified,
            accepted_v3b_receipts=accepted(result, verified),
            on_result_value=result, on_verification_value=verified,
            m1_qualification_receipt_value=changed_receipt,
            accepted_m1_qualification_receipts={"qualification_receipt_digests": [changed_receipt["receipt_digest"]]},
        )
        self.assertEqual("not-conformant", output["status"])
        changed = copy.deepcopy(result)
        changed["policy_digest"] = "0" * 64
        with self.assertRaises(qualification.MemoryQualificationError):
            qualification.build_qualification_result(
                qualification_input(result, verified, with_on=True), result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=changed, on_verification_value=verified,
                **m1_args(qualification_input(result, verified, with_on=True)),
            )

    def test_false_efficacy_and_untrusted_m1_receipt_reject(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=True)
        raised = copy.deepcopy(source)
        raised["efficacy_claimed"] = True
        raised = qualification.seal_input(raised)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "efficacy"):
            qualification.validate_qualification_input(raised)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "caller-accepted"):
            qualification.build_qualification_result(
                source, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=result, on_verification_value=verified,
                m1_qualification_receipt_value=m1_receipt(source),
                accepted_m1_qualification_receipts={"qualification_receipt_digests": ["0" * 64]},
            )

        no_touch = copy.deepcopy(source)
        no_touch["on_arm"]["safety_observation"]["backend_touch_count"] = 0
        no_touch = qualification.seal_input(no_touch)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "backend touch"):
            qualification.validate_qualification_input(no_touch)

    def test_resealed_result_cannot_change_v3b_bindings_or_drop_on_arm(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=True)
        output = qualification.build_qualification_result(
            source, result, verified,
            accepted_v3b_receipts=accepted(result, verified),
            on_result_value=result, on_verification_value=verified,
            **m1_args(source),
        )
        changed = copy.deepcopy(output)
        changed["common_v3b_bindings"]["policy_digest"] = "0" * 64
        changed = qualification.seal_result(changed)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "common bindings"):
            qualification.validate_qualification_result(
                changed, source, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=result, on_verification_value=verified,
                **m1_args(source),
            )

        dropped = copy.deepcopy(output)
        dropped["on_arm"] = None
        dropped["status"] = "memory-on-unavailable"
        dropped = qualification.seal_result(dropped)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "presence"):
            qualification.validate_qualification_result(
                dropped, source, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=result, on_verification_value=verified,
                **m1_args(source),
            )

    def test_verifier_mismatch_and_m1_receipt_scope_replay_reject(self):
        result, verified = v3b_pair()
        source = qualification_input(result, verified, with_on=True)
        receipt = m1_receipt(source)
        changed_verifier = copy.deepcopy(verified)
        changed_verifier["verifier"] = {"role": "different-verifier"}
        changed_verifier = evaluation.seal_verification_result(changed_verifier)
        mismatched_source = copy.deepcopy(source)
        mismatched_source["on_arm"]["verification_result_digest"] = changed_verifier["verification_result_digest"]
        mismatched_source = qualification.seal_input(mismatched_source)
        accepted_receipts = {"receipt_digests": sorted({
            result["evaluation_result_digest"], verified["verification_result_digest"],
            changed_verifier["verification_result_digest"],
        })}
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "exact V3-B bindings"):
            qualification.build_qualification_result(
                mismatched_source, result, verified, accepted_v3b_receipts=accepted_receipts,
                on_result_value=result, on_verification_value=changed_verifier,
                **m1_args(source),
            )
        replayed = copy.deepcopy(source)
        replayed["qualification_id"] = "qualification-2"
        replayed = qualification.seal_input(replayed)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "exact qualification scope"):
            qualification.build_qualification_result(
                replayed, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=result, on_verification_value=verified,
                m1_qualification_receipt_value=receipt,
                accepted_m1_qualification_receipts={"qualification_receipt_digests": [receipt["receipt_digest"]]},
            )
        fingerprint_replayed = copy.deepcopy(source)
        fingerprint_replayed["on_arm"]["adapter"] = {
            "adapter_id": "future-adapter-2",
            "adapter_version": "m1-candidate-2",
            "schema_fingerprint": "1" * 64,
            "capability_fingerprint": "2" * 64,
            "platform_fingerprint": "3" * 64,
        }
        fingerprint_replayed = qualification.seal_input(fingerprint_replayed)
        with self.assertRaisesRegex(qualification.MemoryQualificationError, "exact qualification scope"):
            qualification.build_qualification_result(
                fingerprint_replayed, result, verified,
                accepted_v3b_receipts=accepted(result, verified),
                on_result_value=result, on_verification_value=verified,
                m1_qualification_receipt_value=receipt,
                accepted_m1_qualification_receipts={"qualification_receipt_digests": [receipt["receipt_digest"]]},
            )

    def test_production_surface_has_no_backend_or_filesystem_mutation_path(self):
        forbidden_modules = {"sqlite3", "subprocess", "socket", "requests"}
        forbidden_calls = {"open", "mkdir", "touch", "write_text", "write_bytes", "unlink", "remove"}
        for name in ("memory_qualification.py", "qualificationctl.py"):
            tree = ast.parse((SCRIPT_DIR / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({alias.name.split(".", 1)[0] for alias in node.names} & forbidden_modules)
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".", 1)[0], forbidden_modules)
                if isinstance(node, ast.Call):
                    call = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                    self.assertNotIn(call, forbidden_calls)


if __name__ == "__main__":
    unittest.main()
