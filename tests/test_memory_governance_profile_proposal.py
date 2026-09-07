"""合成規劃算式的邊界驗證；不把估算當 SQLite 資格驗證。"""

import copy
import importlib.util
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("mg1_profile_proposal", ROOT / "scripts/evaluate-memory-governance-profile.py")
proposal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proposal)
CASES_SPEC = importlib.util.spec_from_file_location(
    "mg1_proposal_cases", ROOT / "scripts/validate-memory-governance-proposal-cases.py"
)
cases_checker = importlib.util.module_from_spec(CASES_SPEC)
CASES_SPEC.loader.exec_module(cases_checker)


class ProfileProposalTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads((ROOT / "docs/loops/issue-213/g0-production-profile.json").read_text())

    def test_complete_version_and_separate_overhead_arithmetic(self):
        self.value["workloads"] = [{
            "case_id": "synthetic-unit", "active_items": 1, "stopped_items": 0,
            "erased_markers": 0, "versions_per_item": 2, "version_bytes": 1024,
            "index_bytes_per_active_item": 256, "proof_count": 1, "witness_count": 0,
        }]
        result = proposal.evaluate(self.value)
        self.assertEqual(result["workloads"][0]["estimated_steady_bytes"], 8393472)
        self.assertEqual(result["workloads"][0]["estimated_peak_bytes"], 84947712)

    def test_stopped_and_erased_items_are_not_active_search_projection(self):
        case = self.value["workloads"][0]
        case.update(active_items=0, stopped_items=3, erased_markers=5, versions_per_item=2,
                    version_bytes=1024, proof_count=0, witness_count=0)
        parts = proposal.evaluate(self.value)["workloads"][0]["estimated_parts"]
        self.assertEqual(parts["retained_version_bytes"], 6144)
        self.assertEqual(parts["current_index_bytes"], 0)
        self.assertEqual(parts["item_metadata_bytes"], 4096)

    def test_exact_capacity_boundary_and_one_byte_over(self):
        self.value["workloads"] = [self.value["workloads"][0]]
        result = proposal.evaluate(self.value)
        remaining = result["steady_limit_bytes"] - result["workloads"][0]["estimated_steady_bytes"]
        self.value["model"]["other_overhead_bytes"] += remaining
        self.assertTrue(proposal.evaluate(self.value)["workloads"][0]["within_steady_model"])
        self.value["model"]["other_overhead_bytes"] += 1
        self.assertFalse(proposal.evaluate(self.value)["workloads"][0]["within_steady_model"])

    def test_simultaneous_count_limits_do_not_guarantee_byte_capacity(self):
        cases = proposal.evaluate(self.value)["workloads"]
        self.assertTrue(cases[2]["within_steady_model"])
        self.assertTrue(cases[3]["within_steady_model"])
        self.assertTrue(cases[3]["uses_maintenance_proof_slots"])
        one_gib = copy.deepcopy(self.value)
        one_gib["profile"]["data_limit_bytes"] = 1_073_741_824
        self.assertFalse(proposal.evaluate(one_gib)["workloads"][3]["within_steady_model"])

    def test_calibrated_data_and_work_models_keep_distinct_boundaries(self):
        result = proposal.evaluate(self.value)
        self.assertEqual(result["max_audit_pages"], 40)
        self.assertEqual(result["maintenance_max_bytes"], 5_368_709_120)
        self.assertEqual([case["estimated_steady_bytes"] for case in result["workloads"]],
                         [12_797_952, 91_893_760, 583_049_216, 2_115_903_488])
        self.assertEqual([case["within_work_model"] for case in result["workloads"]],
                         [True, True, True, True])

    def test_limits_include_erased_markers_and_pending_proof_slots(self):
        original = copy.deepcopy(self.value)
        self.value["workloads"][0]["erased_markers"] = 10_001
        with self.assertRaisesRegex(proposal.ContractError, "item-count-limit"):
            proposal.evaluate(self.value)
        self.value = original
        self.value["workloads"][0]["proof_count"] = 33_793
        with self.assertRaisesRegex(proposal.ContractError, "proof-count-limit"):
            proposal.evaluate(self.value)

    def test_maintenance_ceiling_is_reported_as_a_model_boundary(self):
        self.value["profile"]["maintenance_max_bytes"] = 1
        self.assertFalse(proposal.evaluate(self.value)["workloads"][0]["within_work_model"])

    def test_proposal_cannot_accept_itself_or_emit_operation_authority(self):
        result = proposal.evaluate(self.value)
        for key in ("production_parameters_accepted", "operation_authorized", "runtime_proven", "write_performed"):
            self.assertIs(result[key], False)
        self.value["status"] = "accepted"
        with self.assertRaisesRegex(proposal.ContractError, "proposal-status-required"):
            proposal.evaluate(self.value)

    def test_bool_and_unknown_fields_are_not_parameters(self):
        self.value["profile"]["max_items"] = True
        with self.assertRaises(proposal.ContractError):
            proposal.evaluate(self.value)
        self.value["profile"]["max_items"] = 10_000
        self.value["authority"] = {"accepted": True}
        with self.assertRaises(proposal.ContractError):
            proposal.evaluate(self.value)

    def test_duplicate_cases_and_unbounded_workloads_are_rejected(self):
        self.value["workloads"] = [self.value["workloads"][0]] * 2
        with self.assertRaisesRegex(proposal.ContractError, "duplicate-case"):
            proposal.evaluate(self.value)
        self.value["workloads"] *= 9
        with self.assertRaisesRegex(proposal.ContractError, "invalid-workloads"):
            proposal.evaluate(self.value)

    def test_derived_sizes_remain_exact_json_integers(self):
        self.value["model"]["other_overhead_bytes"] = 2**53 - 1
        with self.assertRaisesRegex(proposal.ContractError, "invalid-integer"):
            proposal.evaluate(self.value)

    def test_cli_reads_explicit_proposal_without_changing_it(self):
        path = ROOT / "docs/loops/issue-213/g0-production-profile.json"
        before = path.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/evaluate-memory-governance-profile.py"),
                                 str(path)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), proposal.evaluate(self.value))
        self.assertEqual(result.stderr, "")
        self.assertEqual(path.read_bytes(), before)

    def test_synthetic_content_examples_fit_complete_version_and_proof_bounds(self):
        cases = json.loads((ROOT / "docs/loops/issue-213/g0-production-cases.json").read_text())
        canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(cases["status"], "oracle-only-not-executed")
        self.assertFalse(cases["operation_authorized"])
        self.assertEqual({v["kind"] for v in cases["version_examples"]}, {"fact", "procedure"})
        for version in cases["version_examples"]:
            self.assertLessEqual(len(canonical(version)), self.value["profile"]["max_payload_bytes"])
            material = {key: value for key, value in version.items()
                        if key not in ("validation", "created_at", "retired_at")}
            self.assertEqual(version["validation"]["content_digest"], hashlib.sha256(canonical(material)).hexdigest())
            if version["kind"] == "procedure":
                self.assertTrue(set(version["procedure"]["success_evidence"]).issubset(
                    {source["source_id"] for source in version["provenance"]}))
        self.assertLessEqual(len(canonical(cases["maximum_width_proof_example"])),
                             self.value["model"]["proof_bytes_ceiling"])


class ProposalCasesTests(unittest.TestCase):
    def setUp(self):
        self.cases_path = ROOT / "docs/loops/issue-213/g0-production-cases.json"
        self.profile_path = ROOT / "docs/loops/issue-213/g0-production-profile.json"
        self.cases = json.loads(self.cases_path.read_text())
        self.profile = json.loads(self.profile_path.read_text())

    def evaluate(self):
        return cases_checker.evaluate(self.cases, self.profile)

    def assert_rejected(self):
        with self.assertRaises(cases_checker.ContractError):
            self.evaluate()

    def rebind_preview(self, binding):
        preview_digest = cases_checker.digest(binding["preview"])
        binding["confirmation"]["preview_digest"] = preview_digest
        binding["readback"]["preview_digest"] = preview_digest
        binding["readback"]["proof"]["preview_digest"] = preview_digest

    def rebind_continuation_records(self, binding):
        before_record = {"proof": binding["parent_before"], "witness": None}
        after_parent_record = {"proof": binding["parent_after"], "witness": None}
        child = binding["readback"]["proof"]
        witness = binding["readback"]["witness"]
        witness["parent_before_record"] = before_record
        witness["parent_after_record_digest"] = cases_checker.record_digest(after_parent_record)
        binding["proof_records_before"] = [before_record]
        witness["before_proof_set_digest"] = cases_checker.record_set_digest(binding["proof_records_before"])
        witness["after_proof_set_digest_without_self"] = cases_checker.record_set_digest(
            [after_parent_record], child["operation_id"]
        )
        child["witness_digest"] = cases_checker.digest(witness)
        binding["proof_records_after"] = [after_parent_record, {"proof": child, "witness": witness}]

    def test_positive_fixture_is_documented_only_and_cli_does_not_mutate_inputs(self):
        before_cases = self.cases_path.read_bytes()
        before_profile = self.profile_path.read_bytes()
        expected = {
            "contract_version": "mg1-production-cases-proposal/v0",
            "synthetic_cases_checked": 1,
            "fault_oracles_documented": 30,
            "production_parameters_accepted": False,
            "runtime_proven": False,
            "operation_authorized": False,
            "write_performed": False,
        }
        self.assertEqual(self.evaluate(), expected)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate-memory-governance-proposal-cases.py"),
             str(self.cases_path), "--profile", str(self.profile_path)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout), expected)
        self.assertEqual(result.stderr, "")
        self.assertEqual(self.cases_path.read_bytes(), before_cases)
        self.assertEqual(self.profile_path.read_bytes(), before_profile)

    def test_profile_mapping_and_digest_are_fixed(self):
        self.profile["profile"]["max_items"] = 255
        self.assert_rejected()
        self.profile = json.loads(self.profile_path.read_text())
        self.cases["binding_examples"]["scope"]["profile_digest"] = "0" * 64
        self.assert_rejected()

    def test_policy_and_all_scope_bindings_reject_mutation(self):
        self.cases["binding_examples"]["policy"]["prohibited"].pop()
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["confirmation"]["scope"]["root_id"] = (
            "00000000-0000-4000-8000-000000000099"
        )
        self.assert_rejected()

    def test_preview_nonce_digest_scope_and_time_are_bound(self):
        preview = self.cases["binding_examples"]["preview"]
        preview["nonce"] = "00000000-0000-4000-8000-000000000099"
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["preview"]["before"]["digest"] = "0" * 64
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["preview"]["scope"]["root_id"] = (
            "00000000-0000-4000-8000-000000000099"
        )
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["preview"]["expires_at"] = 501
        self.assert_rejected()

    def test_provenance_change_invalidates_complete_version_digest(self):
        candidate = self.cases["binding_examples"]["preview"]["candidate"]
        candidate["provenance"][0]["source_digest"] = "0" * 64
        self.assert_rejected()

    def test_nul_paths_are_rejected_after_recomputing_content_digest(self):
        candidate = self.cases["binding_examples"]["preview"]["candidate"]
        candidate["applicability"]["paths"] = ["fixtures/\x00widget.json"]
        material = {key: value for key, value in candidate.items()
                    if key not in ("validation", "created_at", "retired_at")}
        candidate["validation"]["content_digest"] = cases_checker.digest(material)
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        candidate = self.cases["binding_examples"]["preview"]["candidate"]
        candidate["provenance"][0]["reference"]["path"] = "docs/\x00synthetic-guide.md"
        material = {key: value for key, value in candidate.items()
                    if key not in ("validation", "created_at", "retired_at")}
        candidate["validation"]["content_digest"] = cases_checker.digest(material)
        self.assert_rejected()

    def test_proof_cross_field_and_readback_bindings_reject_mismatch(self):
        proof = self.cases["binding_examples"]["readback"]["proof"]
        proof["operation"] = "prune"
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"]["proof"]["before_revision"] = 0
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"]["state_digest"] = "0" * 64
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"]["proof"]["recorded_at"] = 500
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        proof = self.cases["maximum_width_proof_example"]
        proof["sanitization"] = "not-requested"
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["maximum_width_proof_example"]["restore_source_revision"] = 1
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"]["proof"]["acceptance_evidence_id"] = "synthetic-other"
        self.assert_rejected()

    def test_omitted_or_duplicate_fault_oracles_are_rejected(self):
        self.cases["fault_cases"].pop()
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["fault_cases"][-1]["case_id"] = self.cases["fault_cases"][0]["case_id"]
        self.assert_rejected()

    def test_extra_fields_and_caller_authority_are_rejected(self):
        self.cases["binding_examples"]["preview"]["authority"].append("root-maintenance")
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"]["caller_accepted"] = True
        self.assert_rejected()

    def test_applied_readback_uses_independent_post_measurement(self):
        preview_files = self.cases["binding_examples"]["preview"]["managed_files"]
        readback_files = self.cases["binding_examples"]["readback"]["managed_files"]
        self.assertNotEqual(preview_files, readback_files)
        self.assertEqual(self.evaluate()["synthetic_cases_checked"], 1)
        self.cases["binding_examples"]["readback"]["storage"]["coverage"] = "partial"
        self.assert_rejected()

    def test_retention_batch_128_is_bounded_and_129_is_rejected(self):
        binding = self.cases["binding_examples"]
        preview = binding["preview"]
        preview.update(
            operation="retention", item_id=None, candidate=None, target_revisions=[],
            target_proofs=[
                {"id": f"00000000-0000-4000-8000-{index:012d}", "digest": f"{index:064x}"}
                for index in range(128)
            ],
            target_markers=[], phases={
                "content": "not-requested", "sanitization": "not-requested", "space_reclaim": "not-requested",
            },
            authority=["readback", "root-maintenance"],
        )
        limits = cases_checker.profile(self.profile)
        accepted = cases_checker.preview(
            preview, binding["scope"], binding["before_state"], binding["after_state"], limits
        )
        self.assertLessEqual(len(cases_checker.canonical(accepted)), 262_144)
        preview["target_proofs"].append({"id": "00000000-0000-4000-0000-000000000128", "digest": "f" * 64})
        with self.assertRaises(cases_checker.ContractError):
            cases_checker.preview(preview, binding["scope"], binding["before_state"], binding["after_state"], limits)

    def test_restore_source_is_preview_bound_but_not_a_proof_delete_target(self):
        binding = self.cases["binding_examples"]
        preview = binding["preview"]
        preview.update(operation="restore", target_revisions=[1])
        limits = cases_checker.profile(self.profile)
        checked_preview = cases_checker.preview(
            preview, binding["scope"], binding["before_state"], binding["after_state"], limits
        )
        proof = binding["readback"]["proof"]
        proof.update(
            operation="restore", preview_digest=cases_checker.digest(checked_preview),
            target_revisions=[], restore_source_revision=1,
        )
        cases_checker.proof(proof, checked_preview, binding["before_state"], binding["after_state"])
        proof["restore_source_revision"] = 2
        with self.assertRaises(cases_checker.ContractError):
            cases_checker.proof(proof, checked_preview, binding["before_state"], binding["after_state"])

    def test_continuation_parent_binding_and_related_proof_are_required(self):
        continuation = self.cases["continuation_example"]
        continuation["parent_before"]["target_revisions"] = [2]
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["continuation_example"]["parent_before"]["acceptance_epoch"] = 2
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["continuation_example"]["readback"]["proof"]["parent_operation_id"] = None
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["continuation_example"]["readback"]["related_proofs"] = []
        self.assert_rejected()

    def test_continuation_cannot_change_parent_target_or_identity(self):
        for change in ("root", "other-item", "new-epoch"):
            with self.subTest(change=change):
                self.cases = json.loads(self.cases_path.read_text())
                binding = self.cases["continuation_example"]
                preview = binding["preview"]
                proof = binding["readback"]["proof"]
                if change == "root":
                    preview["item_id"] = None
                    proof.update(item_id=None, identity_epoch=0, before_revision=0, after_revision=0)
                    proof["projection_digest"] = cases_checker.digest([
                        {"item_id": item["item_id"], "projection_digest": item["projection_digest"]}
                        for item in binding["after_state"]["items"] if item["status"] == "active"
                    ])
                else:
                    for state_name in ("before_state", "after_state"):
                        binding[state_name]["epoch"] = 2
                        item = binding[state_name]["items"][0]
                        if change == "other-item":
                            item = copy.deepcopy(item)
                            item["item_id"] = "00000000-0000-4000-8000-000000000099"
                            binding[state_name]["items"].append(item)
                        item["identity_epoch"] += 1
                    target = binding["after_state"]["items"][-1]
                    preview["item_id"] = target["item_id"]
                    preview["acceptance_epoch"] = proof["acceptance_epoch"] = 2
                    proof.update(item_id=target["item_id"], identity_epoch=target["identity_epoch"])
                    preview["before"]["digest"] = proof["before_digest"] = cases_checker.digest(binding["before_state"])
                    preview["expected_after_digest"] = proof["after_digest"] = cases_checker.digest(binding["after_state"])
                    binding["readback"]["state_digest"] = proof["after_digest"]
                self.rebind_preview(binding)
                with self.assertRaisesRegex(cases_checker.ContractError, "continuation-target-mismatch"):
                    self.evaluate()

    def test_preview_capacity_is_required_before_confirmation(self):
        for change in ("partial", "over-limit", "low-reserve"):
            with self.subTest(change=change):
                self.cases = json.loads(self.cases_path.read_text())
                binding = self.cases["binding_examples"]
                storage = binding["preview"]["storage"]
                if change == "partial":
                    storage["coverage"] = "partial"
                elif change == "low-reserve":
                    storage["available_work_bytes"] = storage["work_budget"]["required_work_bytes"] - 1
                else:
                    files = binding["preview"]["managed_files"]
                    files[0]["bytes"] = self.profile["profile"]["data_limit_bytes"]
                    storage["managed_bytes"] = sum(entry["bytes"] for entry in files)
                    storage["work_budget"]["file_snapshot_digest"] = cases_checker.digest(files)
                self.rebind_preview(binding)
                with self.assertRaisesRegex(cases_checker.ContractError, "preview-capacity-unproven"):
                    self.evaluate()

    def test_preview_epoch_and_rejection_floor_are_bound(self):
        for change in ("future", "stale", "floor"):
            with self.subTest(change=change):
                self.cases = json.loads(self.cases_path.read_text())
                binding = self.cases["binding_examples"]
                if change == "future":
                    binding["preview"]["acceptance_epoch"] += 1
                    binding["readback"]["proof"]["acceptance_epoch"] += 1
                else:
                    if change == "stale":
                        binding["before_state"]["epoch"] += 1
                    else:
                        binding["before_state"]["reject_before"] = binding["preview"]["issued_at"] + 1
                    binding["preview"]["before"]["digest"] = cases_checker.digest(binding["before_state"])
                    binding["readback"]["proof"]["before_digest"] = binding["preview"]["before"]["digest"]
                self.rebind_preview(binding)
                with self.assertRaisesRegex(cases_checker.ContractError, "stale-preview-epoch-or-floor"):
                    self.evaluate()

    def test_continuation_confirmation_cannot_predate_parent(self):
        binding = self.cases["continuation_example"]
        for proof in (binding["parent_before"], binding["parent_after"], binding["readback"]["related_proofs"][0]):
            proof["recorded_at"] = 500
        binding["preview"]["continuation"]["proof_digest"] = cases_checker.digest(binding["parent_before"])
        self.rebind_continuation_records(binding)
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "continuation-before-parent"):
            self.evaluate()

    def test_update_cannot_carry_continuation_metadata(self):
        binding = self.cases["binding_examples"]
        binding["preview"]["continuation"] = copy.deepcopy(self.cases["continuation_example"]["preview"]["continuation"])
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "unexpected-or-missing-continuation"):
            self.evaluate()

    def test_continuation_phases_cannot_expand_or_switch(self):
        for change, error in (("switch", "continuation-phase-mismatch"),
                              ("parent-expand", "unauthorized-parent-phase-change"),
                              ("child-expand", "proof-preview-phase-mismatch")):
            with self.subTest(change=change):
                self.cases = json.loads(self.cases_path.read_text())
                binding = self.cases["continuation_example"]
                if change == "switch":
                    binding["preview"]["phases"].update(sanitization="not-requested", space_reclaim="requested")
                    binding["preview"]["authority"] = ["readback", "root-maintenance"]
                    self.rebind_preview(binding)
                elif change == "parent-expand":
                    binding["parent_after"]["space_reclaim"] = "complete"
                    binding["readback"]["related_proofs"][0]["space_reclaim"] = "complete"
                    self.rebind_continuation_records(binding)
                else:
                    binding["readback"]["proof"]["space_reclaim"] = "complete"
                    binding["readback"]["space_reclaim"] = "complete"
                with self.assertRaisesRegex(cases_checker.ContractError, error):
                    self.evaluate()

    def test_operation_authority_does_not_allow_surplus_capabilities(self):
        binding = self.cases["binding_examples"]
        for operation, authority in (("stop", ["content-write", "readback", "root-maintenance"]),
                                     ("retention", ["content-write", "readback", "root-maintenance"])):
            with self.subTest(operation=operation):
                preview = copy.deepcopy(binding["preview"])
                preview.update(operation=operation, candidate=None, authority=authority,
                               phases={name: "not-requested" for name in preview["phases"]})
                if operation == "retention":
                    preview["item_id"] = None
                    preview["target_proofs"] = [{"id": "00000000-0000-4000-8000-000000000199", "digest": "0" * 64}]
                with self.assertRaisesRegex(cases_checker.ContractError, "unexpected-authority"):
                    cases_checker.preview(preview, binding["scope"], binding["before_state"],
                                          binding["after_state"], cases_checker.profile(self.profile))

    def test_readback_maintenance_must_match_durable_proof(self):
        self.cases["binding_examples"]["readback"]["sanitization"] = "pending"
        with self.assertRaisesRegex(cases_checker.ContractError, "readback-maintenance-mismatch"):
            self.evaluate()

    def test_readback_cannot_measure_capacity_on_another_filesystem(self):
        self.cases["binding_examples"]["readback"]["storage"]["filesystem_id"] = "synthetic-other-filesystem"
        with self.assertRaisesRegex(cases_checker.ContractError, "readback-filesystem-mismatch"):
            self.evaluate()

    def test_proof_operation_cannot_invent_maintenance(self):
        binding = self.cases["binding_examples"]
        binding["readback"]["proof"].update(phase="sanitization-pending", sanitization="pending")
        binding["readback"]["sanitization"] = "pending"
        with self.assertRaisesRegex(cases_checker.ContractError, "unexpected-proof-maintenance"):
            self.evaluate()
        proof = copy.deepcopy(self.cases["maximum_width_proof_example"])
        proof.update(operation="compact", item_id=None, identity_epoch=0, before_revision=0,
                     after_revision=0, target_revisions=[], sanitization="complete")
        with self.assertRaisesRegex(cases_checker.ContractError, "invalid-compact-proof-phase"):
            cases_checker.proof(proof)

    def test_malformed_enum_and_cues_are_contract_errors(self):
        self.cases["binding_examples"]["preview"]["operation"] = []
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["preview"]["phases"]["content"] = {}
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["version_examples"][0]["cues"] = [{"not": "a string"}]
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["readback"] = []
        self.assert_rejected()

    def test_retention_witness_manifest_tampering_is_not_masked_by_old_digest(self):
        binding = self.cases["retention_example"]
        witness = binding["readback"]["witness"]
        witness["target_proofs"][0]["digest"] = "0" * 64
        proof = binding["readback"]["proof"]
        proof["witness_digest"] = cases_checker.digest(witness)
        binding["proof_records_after"] = [{"proof": proof, "witness": witness}]
        with self.assertRaisesRegex(cases_checker.ContractError, "retention-witness-target-mismatch"):
            self.evaluate()

    def test_compact_plan_witness_must_match_preview_after_rebinding_digest(self):
        binding = self.cases["compact_example"]
        witness = binding["readback"]["witness"]
        witness["plan"]["requested_pages"] = 1
        binding["readback"]["proof"]["witness_digest"] = cases_checker.digest(witness)
        with self.assertRaisesRegex(cases_checker.ContractError, "compact-witness-plan-mismatch"):
            self.evaluate()

    def test_restore_copies_source_content_after_preview_rebinding(self):
        binding = self.cases["restore_example"]
        candidate = binding["preview"]["candidate"]
        candidate["summary"] = "synthetic altered summary"
        material = {key: value for key, value in candidate.items()
                    if key not in ("validation", "created_at", "retired_at")}
        candidate["validation"]["content_digest"] = cases_checker.digest(material)
        after_item = self.cases["restore_example"]["after_state"]["items"][0]
        after_item["versions"][-1]["version_digest"] = cases_checker.digest(candidate)
        after_item["projection_digest"] = cases_checker.digest(sorted([
            {"cue": cue, "summary": candidate["summary"], "revision": candidate["revision"]}
            for cue in candidate["cues"]
        ], key=lambda row: row["cue"]))
        self.cases["restore_example"]["preview"]["expected_after_digest"] = cases_checker.digest(
            self.cases["restore_example"]["after_state"]
        )
        proof = self.cases["restore_example"]["readback"]["proof"]
        proof["after_digest"] = self.cases["restore_example"]["preview"]["expected_after_digest"]
        proof["projection_digest"] = after_item["projection_digest"]
        self.cases["restore_example"]["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "restore-content-mismatch"):
            self.evaluate()

    def test_continuation_related_witnesses_are_required(self):
        self.cases["continuation_example"]["readback"]["related_witnesses"] = []
        with self.assertRaisesRegex(cases_checker.ContractError, "invalid-related-witnesses"):
            self.evaluate()

    def test_preview_work_budget_binds_file_snapshot_and_qualification_id(self):
        storage = self.cases["binding_examples"]["preview"]["storage"]
        storage["work_budget"]["file_snapshot_digest"] = "0" * 64
        with self.assertRaisesRegex(cases_checker.ContractError, "work-budget-file-mismatch"):
            self.evaluate()
        self.cases = json.loads(self.cases_path.read_text())
        self.cases["binding_examples"]["preview"]["storage"]["work_budget"]["qualification_id"] = None
        self.assert_rejected()

    def test_preview_work_budget_uses_safe_integer_arithmetic_and_data_limit(self):
        storage = self.cases["binding_examples"]["preview"]["storage"]
        budget = storage["work_budget"]
        budget["journal_bound_bytes"] = 1
        budget["growth_bound_bytes"] = 2**53 - 1
        self.assert_rejected()
        self.cases = json.loads(self.cases_path.read_text())
        storage = self.cases["binding_examples"]["preview"]["storage"]
        budget = storage["work_budget"]
        budget["growth_bound_bytes"] = self.profile["profile"]["data_limit_bytes"]
        budget["required_work_bytes"] = ((budget["journal_bound_bytes"] + budget["temp_bound_bytes"]
                                            + budget["growth_bound_bytes"] + 4095) // 4096) * 4096
        self.assert_rejected()

    def test_postflight_low_free_space_does_not_reject_applied_measurement(self):
        self.cases["binding_examples"]["readback"]["storage"]["available_work_bytes"] = 0
        self.assertEqual(self.evaluate()["synthetic_cases_checked"], 1)

    def test_compact_plan_uses_4gib_data_limit_page_ceiling(self):
        binding = self.cases["compact_example"]
        compact = binding["preview"]["compact"]
        compact.update(requested_pages=1_048_576, freelist_pages_before=1_048_576)
        checked = cases_checker.preview(binding["preview"], binding["preview"]["scope"],
                                        binding["before_state"], binding["after_state"],
                                        cases_checker.profile(self.profile))
        self.assertEqual(checked["compact"]["freelist_pages_before"], 1_048_576)

    def test_4gib_preflight_boundary_is_exact_and_above_limit_rejects(self):
        binding = self.cases["binding_examples"]
        preview = binding["preview"]
        storage = preview["storage"]
        budget = storage["work_budget"]
        data_limit = self.profile["profile"]["data_limit_bytes"]
        self.assertEqual(data_limit, 2**32)
        preview["managed_files"][0]["bytes"] = data_limit
        storage["managed_bytes"] = sum(entry["bytes"] for entry in preview["managed_files"])
        budget["growth_bound_bytes"] = 0
        budget["file_snapshot_digest"] = cases_checker.digest(preview["managed_files"])
        budget["required_work_bytes"] = ((budget["journal_bound_bytes"] + budget["temp_bound_bytes"] + 4095) // 4096) * 4096
        checked = cases_checker.preview(preview, binding["scope"], binding["before_state"],
                                        binding["after_state"], cases_checker.profile(self.profile))
        self.assertEqual(checked["storage"]["managed_bytes"], 2**32)
        preview["managed_files"][0]["bytes"] = data_limit + 1
        storage["managed_bytes"] = sum(entry["bytes"] for entry in preview["managed_files"])
        budget["file_snapshot_digest"] = cases_checker.digest(preview["managed_files"])
        with self.assertRaisesRegex(cases_checker.ContractError, "preview-capacity-unproven"):
            cases_checker.preview(preview, binding["scope"], binding["before_state"],
                                  binding["after_state"], cases_checker.profile(self.profile))

    def test_compact_witness_common_rules_reject_rebound_bad_reclaim(self):
        binding = self.cases["compact_example"]
        witness = binding["readback"]["witness"]
        proof = binding["readback"]["proof"]
        witness["actual_pages_reclaimed"] = 2
        proof["witness_digest"] = cases_checker.digest(witness)
        with self.assertRaisesRegex(cases_checker.ContractError, "compact-reclaim-mismatch"):
            cases_checker.witness(witness, proof, cases_checker.profile(self.profile))

    def test_maximum_width_witness_requires_both_128_target_manifests(self):
        self.cases["maximum_width_witness_example"]["target_markers"].pop()
        with self.assertRaisesRegex(cases_checker.ContractError, "invalid-maximum-witness"):
            self.evaluate()

    def test_malformed_continuation_record_is_contract_error(self):
        self.cases["continuation_example"]["proof_records_before"] = [{}]
        with self.assertRaises(cases_checker.ContractError):
            self.evaluate()

    def test_external_copy_observation_must_follow_proof_and_precede_readback(self):
        readback = self.cases["binding_examples"]["readback"]
        readback["external_copies"]["observed_at"] = readback["proof"]["recorded_at"] - 1
        with self.assertRaisesRegex(cases_checker.ContractError, "external-copy-observation-time"):
            self.evaluate()

    def test_update_candidate_must_be_after_current_revision_after_full_rebinding(self):
        binding = self.cases["binding_examples"]
        after_item = binding["after_state"]["items"][0]
        after_item["versions"].append({"revision": 3, "version_digest": "0" * 64})
        after_item["current_revision"] = after_item["revision_high_water"] = 3
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        proof = binding["readback"]["proof"]
        proof["after_revision"] = 3
        proof["after_digest"] = binding["preview"]["expected_after_digest"]
        binding["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "candidate-after-binding-mismatch"):
            self.evaluate()

    def test_restore_human_source_uses_fresh_attestation_and_rejects_reused_token(self):
        binding = self.cases["restore_example"]
        scope_digest = cases_checker.digest(binding["preview"]["scope"])
        human = {
            "source_id": "synthetic-source", "kind": "human-confirmed-decision",
            "reference": {"evidence_id": "synthetic-human-source"},
            "source_revision": "synthetic-decision-v1", "source_digest": "b" * 64,
        }
        source = binding["source_version"]
        candidate = binding["preview"]["candidate"]
        source["provenance"] = [{**human, "attestation": {
            "scope_digest": scope_digest, "policy_fingerprint": source["validation"]["policy_fingerprint"],
            "issuer_fingerprint": "c" * 64, "accepted_at": 100, "binding_token": "source-token",
        }}]
        candidate["provenance"] = [{**human, "attestation": {
            "scope_digest": scope_digest, "policy_fingerprint": candidate["validation"]["policy_fingerprint"],
            "issuer_fingerprint": "c" * 64, "accepted_at": 250, "binding_token": "restore-token",
        }}]
        for version in (source, candidate):
            material = {key: item for key, item in version.items() if key not in ("validation", "created_at", "retired_at")}
            version["validation"]["content_digest"] = cases_checker.digest(material)
        binding["before_state"]["items"][0]["versions"][0]["version_digest"] = cases_checker.digest(source)
        binding["after_state"]["items"][0]["versions"][0]["version_digest"] = cases_checker.digest(source)
        binding["after_state"]["items"][0]["versions"][-1]["version_digest"] = cases_checker.digest(candidate)
        binding["preview"]["before"]["digest"] = cases_checker.digest(binding["before_state"])
        binding["readback"]["proof"]["before_digest"] = binding["preview"]["before"]["digest"]
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        binding["readback"]["proof"]["after_digest"] = binding["preview"]["expected_after_digest"]
        binding["readback"]["state_digest"] = binding["preview"]["expected_after_digest"]
        self.rebind_preview(binding)
        self.assertEqual(self.evaluate()["synthetic_cases_checked"], 1)
        candidate["provenance"][0]["attestation"]["binding_token"] = "source-token"
        material = {key: item for key, item in candidate.items() if key not in ("validation", "created_at", "retired_at")}
        candidate["validation"]["content_digest"] = cases_checker.digest(material)
        binding["after_state"]["items"][0]["versions"][-1]["version_digest"] = cases_checker.digest(candidate)
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        binding["readback"]["proof"]["after_digest"] = binding["preview"]["expected_after_digest"]
        binding["readback"]["state_digest"] = binding["preview"]["expected_after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "restore-attestation-mismatch"):
            self.evaluate()

    def test_restore_missing_after_target_is_contract_error(self):
        binding = self.cases["restore_example"]
        binding["after_state"]["items"] = []
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        binding["readback"]["proof"]["after_digest"] = binding["preview"]["expected_after_digest"]
        binding["readback"]["state_digest"] = binding["preview"]["expected_after_digest"]
        self.rebind_preview(binding)
        with self.assertRaises(cases_checker.ContractError):
            self.evaluate()

    def test_restore_cannot_remove_retained_source_history_after_full_rebinding(self):
        binding = self.cases["restore_example"]
        after_item = binding["after_state"]["items"][0]
        after_item["versions"] = after_item["versions"][1:]
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        proof = binding["readback"]["proof"]
        proof["after_digest"] = binding["preview"]["expected_after_digest"]
        binding["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "candidate-after-binding-mismatch"):
            self.evaluate()

    def test_update_candidate_transition_rejects_root_target_projection_and_nontarget_drift(self):
        for change in ("root", "high-water", "status", "projection", "nontarget"):
            with self.subTest(change=change):
                self.cases = json.loads(self.cases_path.read_text())
                binding = self.cases["binding_examples"]
                before_item = binding["before_state"]["items"][0]
                after_item = binding["after_state"]["items"][0]
                if change == "root":
                    binding["after_state"]["epoch"] += 1
                elif change == "high-water":
                    after_item["revision_high_water"] += 1
                elif change == "status":
                    after_item["status"] = "stopped"
                    after_item["projection_digest"] = cases_checker.digest([])
                elif change == "projection":
                    after_item["projection_digest"] = "0" * 64
                else:
                    extra_before = copy.deepcopy(before_item)
                    extra_after = copy.deepcopy(after_item)
                    extra_before["item_id"] = extra_after["item_id"] = "00000000-0000-4000-8000-000000000099"
                    extra_after["revision_high_water"] += 1
                    binding["before_state"]["items"].append(extra_before)
                    binding["after_state"]["items"].append(extra_after)
                proof = binding["readback"]["proof"]
                binding["preview"]["before"]["digest"] = cases_checker.digest(binding["before_state"])
                proof["before_digest"] = binding["preview"]["before"]["digest"]
                binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
                proof["after_digest"] = binding["preview"]["expected_after_digest"]
                proof["projection_digest"] = after_item["projection_digest"]
                binding["readback"]["state_digest"] = proof["after_digest"]
                self.rebind_preview(binding)
                with self.assertRaises(cases_checker.ContractError):
                    self.evaluate()

    def test_stopped_update_remains_stopped_and_cannot_resume_implicitly(self):
        binding = self.cases["binding_examples"]
        before_item = binding["before_state"]["items"][0]
        after_item = binding["after_state"]["items"][0]
        before_item["status"] = after_item["status"] = "stopped"
        before_item["projection_digest"] = after_item["projection_digest"] = cases_checker.digest([])
        proof = binding["readback"]["proof"]
        binding["preview"]["before"]["digest"] = proof["before_digest"] = cases_checker.digest(binding["before_state"])
        binding["preview"]["expected_after_digest"] = proof["after_digest"] = cases_checker.digest(binding["after_state"])
        proof["projection_digest"] = cases_checker.digest([])
        binding["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        self.assertEqual(self.evaluate()["synthetic_cases_checked"], 1)
        after_item["status"] = "active"
        candidate = binding["preview"]["candidate"]
        after_item["projection_digest"] = cases_checker.digest(sorted([
            {"cue": cue, "summary": candidate["summary"], "revision": candidate["revision"]}
            for cue in candidate["cues"]
        ], key=lambda row: row["cue"]))
        binding["preview"]["expected_after_digest"] = proof["after_digest"] = cases_checker.digest(binding["after_state"])
        proof["projection_digest"] = after_item["projection_digest"]
        binding["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "candidate-target-mutated"):
            self.evaluate()

    def test_compact_and_retention_reject_rebound_non_target_state_changes(self):
        binding = self.cases["compact_example"]
        binding["after_state"]["items"][0]["projection_digest"] = "0" * 64
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        proof = binding["readback"]["proof"]
        proof["after_digest"] = binding["preview"]["expected_after_digest"]
        proof["projection_digest"] = cases_checker.digest([
            {"item_id": item["item_id"], "projection_digest": item["projection_digest"]}
            for item in binding["after_state"]["items"] if item["status"] == "active"
        ])
        binding["readback"]["state_digest"] = proof["after_digest"]
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "compact-state-changed"):
            self.evaluate()
        self.cases = json.loads(self.cases_path.read_text())
        binding = self.cases["retention_example"]
        binding["after_state"]["items"][0]["projection_digest"] = "0" * 64
        binding["preview"]["expected_after_digest"] = cases_checker.digest(binding["after_state"])
        proof = binding["readback"]["proof"]
        proof["after_digest"] = binding["preview"]["expected_after_digest"]
        proof["projection_digest"] = cases_checker.digest([
            {"item_id": item["item_id"], "projection_digest": item["projection_digest"]}
            for item in binding["after_state"]["items"] if item["status"] == "active"
        ])
        binding["readback"]["state_digest"] = proof["after_digest"]
        binding["proof_records_after"][0]["proof"] = proof
        self.rebind_preview(binding)
        with self.assertRaisesRegex(cases_checker.ContractError, "retention-retained-state-mutated"):
            self.evaluate()

    def test_external_copy_observation_cannot_exceed_outer_readback_time(self):
        readback = self.cases["binding_examples"]["readback"]
        readback["external_copies"]["observed_at"] = readback["observed_at"] + 1
        with self.assertRaisesRegex(cases_checker.ContractError, "external-copy-observation-time"):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
