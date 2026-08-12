from __future__ import annotations

import copy
import importlib
import pathlib
import sys
import unittest

from tests import test_improvement_lineage as fixtures
from tests import test_memory_contract as memory_fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
proposal = importlib.import_module("improvement_proposal")
evaluation = importlib.import_module("candidate_evaluation")
memory = importlib.import_module("memory_contract")


def source_bundle() -> tuple[list[dict], list[dict], dict, dict]:
    records, evidence = fixtures.valid_lineage()
    proposal_set = proposal.build_proposal_set(records, evidence)
    selected = proposal_set["proposals"][0]
    return records, evidence, proposal_set, selected


def environment(*, mode: str = "ci") -> dict:
    return {
        "runtime_surface": "ci",
        "os_family": "linux",
        "architecture": "x86_64",
        "python": {"major": 3, "minor": 12},
        "execution_mode": mode,
        "sandbox_mode": "workspace-write",
        "redaction_applied": True,
        "prohibited_fields_present": False,
    }


def observation(
    selected: dict,
    role: str,
    *,
    outcome: str = "passed",
    duration: int = 100,
    resources: int = 100,
    environment_fingerprint: dict | None = None,
) -> dict:
    failure = 0 if outcome == "passed" else 1
    return evaluation.seal_observation(
        {
            "snapshot_role": role,
            "evidence_set_digest": selected["source_lineage"][role]["evidence_set_digest"],
            "source_revision": copy.deepcopy(selected["source_lineage"][role]["source_revision"]),
            "environment_fingerprint": copy.deepcopy(environment_fingerprint or environment()),
            "scenario_set_digest": "7" * 64,
            "scenario_count": 4,
            "outcome": outcome,
            "passed_scenarios": 4 if outcome == "passed" else 3,
            "decision_failures": failure,
            "recovery_failures": 0,
            "determinism_failures": 0,
            "authority_failures": 0,
            "privacy_failures": 0,
            "duration_ms": duration,
            "resource_units": resources,
            "authority_invariants": evaluation.authority_invariants(),
        }
    )


def evaluation_input(
    selected: dict,
    *,
    baseline: dict | None = None,
    candidate: dict | None = None,
) -> dict:
    return evaluation.seal_evaluation_input(
        {
            "contract_version": evaluation.CONTRACT_VERSION,
            "kind": evaluation.INPUT_KIND,
            "proposal_id": selected["proposal_id"],
            "scenario_set_digest": "7" * 64,
            "baseline": baseline or observation(selected, "baseline"),
            "candidate": candidate or observation(selected, "candidate"),
            "authority_invariants": evaluation.authority_invariants(),
        }
    )


def context_inputs(value: dict | None = None) -> tuple[dict, dict, dict]:
    decision = value or memory_fixtures.retrieval_input()
    handshake = decision["handshake"]
    trusted_conformance = {
        handshake["adapter"]["adapter_id"]: {
            "receipt_digest": "c" * 64,
            "adapter_fingerprint": memory.canonical_digest(
                {
                    "adapter": handshake["adapter"],
                    "capabilities": handshake["capabilities"],
                }
            ),
        }
    }
    trusted_sources = {
        ref["locator"]: ref["digest"]
        for item in decision["response"]["records"]
        for ref in item.get("provenance", {}).get("source_refs", [])
        if ref.get("kind") == "repository-artifact"
    }
    return decision, trusted_conformance, trusted_sources


class CandidateEvaluationTests(unittest.TestCase):
    def test_qualified_result_verification_and_packet_are_deterministic(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        result = evaluation.build_evaluation_result(
            input_doc, proposal_set, records, evidence
        )
        replay = evaluation.build_evaluation_result(
            input_doc, proposal_set, reversed(records), reversed(evidence)
        )
        self.assertEqual(result, replay)
        self.assertEqual("qualified", result["comparison"]["status"])
        self.assertEqual("memory-off", result["context"]["mode"])
        self.assertEqual("not-requested", result["context"]["fallback_reason"])
        verification = evaluation.verify_evaluation_result(
            result, input_doc, proposal_set, records, evidence
        )
        self.assertEqual("passed", verification["status"])
        self.assertTrue(verification["structural_independence_only"])
        packet = evaluation.build_promotion_packet(
            result, verification, input_doc, proposal_set, records, evidence
        )
        self.assertEqual(
            "qualified-awaiting-human-decision", packet["disposition"]
        )
        self.assertEqual(evaluation.packet_only_invariants(), packet["packet_only_invariants"])
        self.assertEqual(
            packet,
            evaluation.validate_promotion_packet(
                packet, result, verification, input_doc, proposal_set,
                reversed(records), reversed(evidence),
            ),
        )

    def test_status_priority_covers_baseline_mismatch_uncertain_and_regression(self):
        records, evidence, proposal_set, selected = source_bundle()
        cases = []
        cases.append(("baseline-invalid", evaluation_input(
            selected, baseline=observation(selected, "baseline", outcome="failed")
        )))
        mismatch = observation(selected, "candidate")
        mismatch["scenario_count"] = 3
        mismatch["passed_scenarios"] = 3
        mismatch = evaluation.seal_observation(mismatch)
        cases.append(("input-mismatch", evaluation_input(selected, candidate=mismatch)))
        cases.append(("environment-mismatch", evaluation_input(
            selected,
            candidate=observation(
                selected, "candidate", environment_fingerprint=environment(mode="current-session")
            ),
        )))
        cases.append(("execution-uncertain", evaluation_input(
            selected, candidate=observation(selected, "candidate", outcome="timeout")
        )))
        cases.append(("regressed", evaluation_input(
            selected, candidate=observation(selected, "candidate", duration=121)
        )))
        for expected, input_doc in cases:
            with self.subTest(expected=expected):
                result = evaluation.build_evaluation_result(
                    input_doc, proposal_set, records, evidence
                )
                self.assertEqual(expected, result["comparison"]["status"])
                verification = evaluation.verify_evaluation_result(
                    result, input_doc, proposal_set, records, evidence
                )
                packet = evaluation.build_promotion_packet(
                    result, verification, input_doc, proposal_set, records, evidence
                )
                self.assertEqual("not-qualified", packet["disposition"])

    def test_independent_replay_fails_closed_for_invalid_or_mismatched_result(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        result = evaluation.build_evaluation_result(
            input_doc, proposal_set, records, evidence
        )
        invalid = copy.deepcopy(result)
        invalid["evaluation_result_digest"] = "0" * 64
        receipt = evaluation.verify_evaluation_result(
            invalid, input_doc, proposal_set, records, evidence
        )
        self.assertEqual("failed", receipt["status"])
        self.assertEqual("invalid-evaluation-result", receipt["failure_code"])
        self.assertIsNone(receipt["observed_evaluation_result_digest"])

        mismatched = copy.deepcopy(result)
        mismatched["comparison"]["status"] = "regressed"
        mismatched = evaluation.seal_evaluation_result(mismatched)
        receipt = evaluation.verify_evaluation_result(
            mismatched, input_doc, proposal_set, records, evidence
        )
        self.assertEqual("failed", receipt["status"])
        self.assertEqual("evaluation-mismatch", receipt["failure_code"])
        packet = evaluation.build_promotion_packet(
            mismatched, receipt, input_doc, proposal_set, records, evidence
        )
        self.assertEqual("not-qualified", packet["disposition"])

    def test_source_lineage_and_false_authority_fail_closed(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        for mutation in ("missing", "tampered-proposal", "mismatched-source"):
            bad_records = records
            bad_evidence = evidence
            bad_set = proposal_set
            bad_input = input_doc
            if mutation == "missing":
                bad_evidence = evidence[:-1]
            elif mutation == "tampered-proposal":
                bad_set = copy.deepcopy(proposal_set)
                bad_set["proposal_set_digest"] = "0" * 64
            else:
                bad_input = copy.deepcopy(input_doc)
                bad_input["candidate"]["evidence_set_digest"] = "0" * 64
                bad_input["candidate"] = evaluation.seal_observation(bad_input["candidate"])
                bad_input = evaluation.seal_evaluation_input(bad_input)
            with self.subTest(mutation=mutation):
                with self.assertRaises(evaluation.CandidateEvaluationError):
                    evaluation.build_evaluation_result(
                        bad_input, bad_set, bad_records, bad_evidence
                    )
        raised = copy.deepcopy(input_doc)
        raised["authority_invariants"]["promotion_authorized"] = True
        raised = evaluation.seal_evaluation_input(raised)
        with self.assertRaises(evaluation.CandidateEvaluationError) as caught:
            evaluation.build_evaluation_result(
                raised, proposal_set, records, evidence
            )
        self.assertEqual("authority-violation", caught.exception.code)

    def test_verify_and_packet_iterables_are_bounded_before_materialization(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        result = evaluation.build_evaluation_result(
            input_doc, proposal_set, records, evidence
        )
        with self.assertRaises(evaluation.CandidateEvaluationError) as caught:
            evaluation.verify_evaluation_result(
                result,
                input_doc,
                proposal_set,
                (records[0] for _ in range(evaluation.proposal.lineage.MAX_RECORDS + 1)),
                evidence,
            )
        self.assertEqual("record-count", caught.exception.code)

        verification = evaluation.verify_evaluation_result(
            result, input_doc, proposal_set, records, evidence
        )
        with self.assertRaises(evaluation.CandidateEvaluationError) as caught:
            evaluation.build_promotion_packet(
                result,
                verification,
                input_doc,
                proposal_set,
                records,
                (
                    evidence[0]
                    for _ in range(evaluation.oe.MAX_SET_DOCUMENTS + 1)
                ),
            )
        self.assertEqual("document-count", caught.exception.code)

    def test_valid_context_is_digest_only_and_cannot_change_policy_or_status(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        decision, trusted_conformance, trusted_sources = context_inputs()
        without = evaluation.build_evaluation_result(
            input_doc, proposal_set, records, evidence
        )
        with_context = evaluation.build_evaluation_result(
            input_doc, proposal_set, records, evidence,
            memory_decision_input=decision,
            trusted_conformance_receipts=trusted_conformance,
            trusted_source_digests=trusted_sources,
        )
        self.assertEqual("synthetic-advisory", with_context["context"]["mode"])
        self.assertEqual(without["policy"], with_context["policy"])
        self.assertEqual(without["comparison"], with_context["comparison"])
        self.assertNotIn(
            decision["response"]["records"][0]["content"],
            evaluation.oe.canonical_json(with_context),
        )

    def test_invalid_context_classes_fall_back_to_memory_off(self):
        records, evidence, proposal_set, selected = source_bundle()
        input_doc = evaluation_input(selected)
        base = memory_fixtures.retrieval_input()
        cases: dict[str, tuple[dict | None, dict | None, dict | None]] = {}
        decision, conformance, sources = context_inputs(base)
        cases["partial-input"] = (decision, conformance, None)

        partial = copy.deepcopy(base)
        partial["response"]["status"] = "partial"
        partial["response"]["partial"] = True
        partial["response"]["errors"] = [
            {"code": "partial", "message": "partial", "retryable": True}
        ]
        memory_fixtures.resign_response(partial["response"])
        cases["partial-response"] = context_inputs(partial)

        stale = copy.deepcopy(base)
        stale["current"]["source_revision_relations"]["record-1"] = "ancestor"
        cases["stale"] = context_inputs(stale)

        decision, _conformance, sources = context_inputs(copy.deepcopy(base))
        cases["untrusted"] = (decision, {}, sources)

        sensitive = copy.deepcopy(base)
        sensitive["response"]["records"][0]["content"] = "password=synthetic-secret"
        memory_fixtures.resign_record(sensitive["response"]["records"][0])
        memory_fixtures.resign_response(sensitive["response"])
        cases["sensitive"] = context_inputs(sensitive)

        conflicting = copy.deepcopy(base)
        conflicting["current"]["conflicting_records"] = ["record-1"]
        cases["conflicting"] = context_inputs(conflicting)

        unsupported = copy.deepcopy(base)
        unsupported["handshake"]["capabilities"]["read_query"]["state"] = "unsupported"
        cases["unsupported"] = context_inputs(unsupported)

        for label, context in cases.items():
            with self.subTest(label=label):
                result = evaluation.build_evaluation_result(
                    input_doc, proposal_set, records, evidence,
                    memory_decision_input=context[0],
                    trusted_conformance_receipts=context[1],
                    trusted_source_digests=context[2],
                )
                self.assertEqual("memory-off", result["context"]["mode"])
                self.assertEqual("qualified", result["comparison"]["status"])


if __name__ == "__main__":
    unittest.main()
