from __future__ import annotations

import copy
import importlib
import pathlib
import sys
import unittest

from tests import test_improvement_lineage as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
proposal = importlib.import_module("improvement_proposal")


class ImprovementProposalTests(unittest.TestCase):
    def test_generation_is_deterministic_traceable_and_proposal_only(self):
        records, evidence = fixtures.valid_lineage()
        first = proposal.build_proposal_set(records, evidence)
        second = proposal.build_proposal_set(reversed(records), reversed(evidence))
        self.assertEqual(first, second)
        self.assertEqual(proposal.CONTRACT_VERSION, first["contract_version"])
        self.assertEqual(fixtures.AUTHORITY, first["authority_invariants"])
        self.assertEqual(2, len(first["proposals"]))
        self.assertEqual([1, 2], [item["rank"] for item in first["proposals"]])
        for item in first["proposals"]:
            self.assertEqual(fixtures.AUTHORITY, item["authority_invariants"])
            self.assertEqual(
                proposal.proposal_only_invariants(),
                item["proposal_only_invariants"],
            )
            self.assertEqual("pending", item["promotion_gate"]["status"])
            self.assertEqual(
                first["source_record_set_digest"],
                item["source_lineage"]["source_record_set_digest"],
            )
            self.assertTrue(item["source_lineage"]["source_failures"])
            self.assertEqual(
                item["score"]["total"],
                sum(item["score"]["components"].values()),
            )
        self.assertEqual(
            first,
            proposal.validate_proposal_set(first, records, evidence),
        )

    def test_score_uses_only_exact_structured_policy_components(self):
        records, evidence = fixtures.valid_lineage()
        generated = proposal.build_proposal_set(records, evidence)
        item = generated["proposals"][0]
        self.assertEqual(
            {
                "disposition": 300,
                "failure_priority": 15,
                "candidate_observation": 30,
                "typed_evaluation_artifacts": 10,
                "recovery_signal": 20,
            },
            item["score"]["components"],
        )
        self.assertEqual(375, item["score"]["total"])
        self.assertEqual("address-review", item["hypothesis"]["code"])
        self.assertEqual("patch-suggestion", item["output_intent"])

    def test_exact_duplicates_and_equal_score_ties_are_stable(self):
        baseline = fixtures.evidence_bundle(1)
        candidate = fixtures.evidence_bundle(2)
        first = fixtures.improvement_record(
            1,
            baseline=baseline,
            candidate=candidate,
        )
        second = fixtures.improvement_record(
            2,
            baseline=baseline,
            candidate=candidate,
        )
        evidence = baseline + candidate
        forward = proposal.build_proposal_set([first, second], evidence)
        reverse = proposal.build_proposal_set([second, first], reversed(evidence))
        self.assertEqual(forward, reverse)
        self.assertEqual(1, len(forward["proposals"]))
        self.assertEqual(1, len(forward["suppressed_duplicates"]))
        group = forward["suppressed_duplicates"][0]
        selected = group["selected_source_record"]
        suppressed = group["suppressed_source_records"][0]
        self.assertLess(selected["record_digest"], suppressed["record_digest"])
        self.assertEqual(
            forward["proposals"][0]["duplicate_signature"],
            group["duplicate_signature"],
        )

    def test_rejected_and_failure_incomplete_records_are_ineligible(self):
        records, evidence = fixtures.valid_lineage()
        for mutation in ("rejected", "missing-failure"):
            candidate = copy.deepcopy(records[1])
            if mutation == "rejected":
                candidate["payload"]["candidate_disposition"] = "rejected"
            else:
                candidate["payload"]["source_failures"] = []
            candidate = fixtures.lineage.seal_record(candidate)
            result = proposal.build_proposal_set([candidate], evidence)
            with self.subTest(mutation=mutation):
                self.assertEqual([], result["proposals"])
                self.assertEqual(
                    candidate["record_id"],
                    result["ineligible_source_records"][0]["record_id"],
                )

    def test_missing_tampered_and_resealed_mismatched_lineage_fail_closed(self):
        records, evidence = fixtures.valid_lineage()
        with self.assertRaises(proposal.ProposalContractError):
            proposal.build_proposal_set(records, evidence[:-1])

        generated = proposal.build_proposal_set(records, evidence)
        tampered = copy.deepcopy(generated)
        tampered["proposals"][0]["score"]["total"] += 1
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.validate_proposal_set(tampered, records, evidence)
        self.assertEqual("digest-mismatch", caught.exception.code)

        mismatched = copy.deepcopy(generated)
        mismatched["proposals"][0]["source_lineage"]["objective_id"] = "issue-other"
        mismatched = proposal.seal_proposal_set(mismatched)
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.validate_proposal_set(mismatched, records, evidence)
        self.assertEqual("proposal-mismatch", caught.exception.code)

    def test_false_authority_and_private_data_are_rejected(self):
        records, evidence = fixtures.valid_lineage()
        generated = proposal.build_proposal_set(records, evidence)
        raised = copy.deepcopy(generated)
        raised["authority_invariants"]["promotion_authorized"] = True
        raised = proposal.seal_proposal_set(raised)
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.validate_proposal_set(raised, records, evidence)
        self.assertEqual("authority-violation", caught.exception.code)

        private = copy.deepcopy(records[1])
        private["record_id"] = "/home/example/private-record"
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.build_proposal_set([private], evidence)
        self.assertEqual("privacy-violation", caught.exception.code)

    def test_record_and_evidence_iterables_are_bounded(self):
        records, evidence = fixtures.valid_lineage()
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.build_proposal_set(
                (records[0] for _ in range(fixtures.lineage.MAX_RECORDS + 1)),
                evidence,
            )
        self.assertEqual("record-count", caught.exception.code)
        with self.assertRaises(proposal.ProposalContractError) as caught:
            proposal.build_proposal_set(
                records,
                (evidence[0] for _ in range(fixtures.evidence.MAX_SET_DOCUMENTS + 1)),
            )
        self.assertEqual("document-count", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
