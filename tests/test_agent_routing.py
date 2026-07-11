from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "skills" / "loop-engineering" / "scripts" / "agent_routing.py"
SPEC = importlib.util.spec_from_file_location("agent_routing", PATH)
routing = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(routing)

CORE_PATH = ROOT / "skills" / "loop-engineering" / "scripts" / "loop_core.py"
CORE_SPEC = importlib.util.spec_from_file_location("loop_core_for_routing", CORE_PATH)
core = importlib.util.module_from_spec(CORE_SPEC)
assert CORE_SPEC.loader is not None
CORE_SPEC.loader.exec_module(core)


def factors(**changes):
    value = {
        "ambiguity": "moderate",
        "reasoning_depth": "balanced",
        "code_context_volume": "medium",
        "security_data_migration_public_contract_risk": "routine",
        "write_blast_radius": "bounded",
        "latency_sensitivity": "medium",
        "cost_token_sensitivity": "medium",
        "independence_parallelizability": "bounded",
        "verification_burden": "medium",
    }
    value.update(changes)
    return value


def profile(name="loop-balanced", capability_class="balanced-worker"):
    return {
        "name": name,
        "capability_class": capability_class,
        "available": True,
        "config_valid": True,
        "model_available": True,
        "reasoning_available": True,
        "profile_digest": routing._digest({"name": name, "source": "test-profile"}),
        "sandbox": routing.CLASS_SANDBOX[capability_class],
        "parent_sandbox_mode": "workspace-write",
        "sandbox_non_widening": True,
        "allowed_workflow_scope": sorted(
            routing.CLASS_WORKFLOW_SCOPE[capability_class]
        ),
    }


def route(task_factors=None, runtime=None):
    return routing.build_route_receipt(
        task_id="P1",
        factors=task_factors or factors(),
        runtime=runtime
        or {
            "custom_agents_available": True,
            "profiles": [profile()],
            "parent_default_available": True,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        },
        assigned_scope=["skills/loop-engineering/scripts/agent_routing.py"],
        ownership={"owner": "worker-p1", "disjoint": True},
        source_revision={"head_sha": "abc123"},
        authority_contract={
            "scope": "P1",
            "external_write": False,
            "human_gates": ["merge"],
            "completion_criteria": ["tests", "review"],
        },
    )


class ClassificationTests(unittest.TestCase):
    def test_requires_exactly_nine_factors(self):
        incomplete = factors()
        incomplete.pop("ambiguity")
        with self.assertRaisesRegex(routing.AgentRoutingContractError, "missing"):
            routing.classify_task(incomplete)
        with self.assertRaisesRegex(routing.AgentRoutingContractError, "unknown"):
            routing.classify_task({**factors(), "task_name": "review"})

    def test_read_heavy_exploration_is_fast(self):
        result = routing.classify_task(
            factors(
                ambiguity="low",
                reasoning_depth="shallow",
                code_context_volume="large",
                security_data_migration_public_contract_risk="none",
                write_blast_radius="none",
                latency_sensitivity="high",
                cost_token_sensitivity="high",
                independence_parallelizability="independent",
                verification_burden="low",
            )
        )
        self.assertEqual("fast-read-explorer", result["capability_class"])

    def test_bounded_implementation_is_balanced(self):
        self.assertEqual("balanced-worker", routing.classify_task(factors())["capability_class"])

    def test_context_latency_and_cost_are_explainable_fast_tie_breaks(self):
        base = {
            "ambiguity": "low",
            "reasoning_depth": "shallow",
            "security_data_migration_public_contract_risk": "none",
            "write_blast_radius": "none",
            "independence_parallelizability": "independent",
            "verification_burden": "low",
        }
        cases = (
            ({"code_context_volume": "large"}, "large-context-fast-tie-break"),
            ({"latency_sensitivity": "high"}, "latency-fast-tie-break"),
            ({"cost_token_sensitivity": "high"}, "cost-token-fast-tie-break"),
        )
        for change, reason in cases:
            with self.subTest(change=change):
                result = routing.classify_task(factors(**base, **change))
                self.assertEqual("fast-read-explorer", result["capability_class"])
                self.assertIn(reason, result["reasons"])

    def test_deep_factors_are_non_compensatory(self):
        for change in (
            {"ambiguity": "high"},
            {"reasoning_depth": "deep"},
            {"verification_burden": "high"},
            {"write_blast_radius": "broad"},
            {"security_data_migration_public_contract_risk": "data"},
            {"security_data_migration_public_contract_risk": "migration"},
            {"security_data_migration_public_contract_risk": "public-contract"},
        ):
            with self.subTest(change=change):
                result = routing.classify_task(
                    factors(latency_sensitivity="high", cost_token_sensitivity="high", **change)
                )
                self.assertEqual("deep-reviewer", result["capability_class"])

    def test_security_is_security_reviewer(self):
        result = routing.classify_task(
            factors(security_data_migration_public_contract_risk="security")
        )
        self.assertEqual("security-reviewer", result["capability_class"])
        self.assertTrue(result["hard_triggered"])

    def test_all_nine_factors_have_explainable_effects(self):
        result = routing.classify_task(factors())
        self.assertEqual(set(routing.FACTOR_VALUES), set(result["factor_effects"]))


class RouteTests(unittest.TestCase):
    def test_loop_core_exposes_thin_routing_boundary(self):
        receipt = core.evaluate_agent_route(
            task_id="P1",
            factors=factors(),
            runtime={
                "custom_agents_available": False,
                "profiles": [],
                "parent_default_available": True,
                "parent_capability_classes": [],
                "current_session_capability_classes": [],
            },
            assigned_scope=["agent_routing.py"],
            ownership={"owner": "worker-p1", "disjoint": True},
            source_revision={"head_sha": "abc123"},
            authority_contract={"scope": "P1"},
        )
        self.assertEqual("balanced-worker", receipt["classification"]["capability_class"])
        with self.assertRaisesRegex(core.LoopContractError, "missing required fields"):
            core.evaluate_agent_route(
                task_id="P1",
                factors={},
                runtime={},
                assigned_scope=["agent_routing.py"],
                ownership={"owner": "worker-p1", "disjoint": True},
                source_revision={"head_sha": "abc123"},
                authority_contract={"scope": "P1"},
            )

    def test_selects_deterministic_same_class_profile(self):
        runtime = {
            "custom_agents_available": True,
            "profiles": [
                profile(name)
                for name in ("z-profile", "a-profile")
            ],
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        }
        self.assertEqual("a-profile", route(runtime=runtime)["runtime_mapping"])

    def test_selected_profile_and_validation_evidence_are_bound(self):
        receipt = route()
        selected = profile()
        self.assertEqual(selected["profile_digest"], receipt["selected_profile_digest"])
        self.assertEqual(
            routing._digest(routing._profile_config_evidence(selected)),
            receipt["config_evidence_sha256"],
        )
        self.assertEqual(
            routing._profile_config_evidence(selected), receipt["config_evidence"]
        )

    def test_invalid_profile_digest_degrades_instead_of_selecting(self):
        invalid = profile()
        invalid["profile_digest"] = "not-a-digest"
        receipt = route(runtime={
            "custom_agents_available": True,
            "profiles": [invalid],
            "parent_default_available": True,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        })
        self.assertEqual("parent-default", receipt["fallback"])

    def test_unknown_model_or_reasoning_availability_degrades(self):
        for missing in ("model_available", "reasoning_available"):
            with self.subTest(missing=missing):
                candidate = profile()
                candidate.pop(missing)
                receipt = route(runtime={
                    "custom_agents_available": True,
                    "profiles": [candidate],
                    "parent_default_available": True,
                    "parent_capability_classes": [],
                    "current_session_capability_classes": [],
                })
                self.assertEqual("parent-default", receipt["fallback"])

    def test_security_profile_cannot_widen_sandbox_or_workflow_scope(self):
        security = profile("loop-security", "security-reviewer")
        security["sandbox"] = "workspace-write"
        security["allowed_workflow_scope"].append("bounded-edit")
        receipt = route(
            factors(security_data_migration_public_contract_risk="security"),
            {
                "custom_agents_available": True,
                "profiles": [security],
                "parent_default_available": False,
                "parent_capability_classes": [],
                "current_session_capability_classes": [],
            },
        )
        self.assertEqual("stop-for-human-gate", receipt["execution_mode"])
        self.assertIsNone(receipt["selected_profile_digest"])

    def test_coupled_work_routes_sequential_even_when_profile_is_available(self):
        receipt = route(factors(independence_parallelizability="coupled"))
        self.assertEqual("sequential-current-session", receipt["execution_mode"])
        self.assertEqual("coupled-work-requires-sequential", receipt["routing_constraint"])

    def test_fallback_order_parent_then_sequential(self):
        parent = route(runtime={
            "custom_agents_available": False,
            "profiles": [],
            "parent_default_available": True,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        })
        self.assertEqual("parent-default", parent["fallback"])
        sequential = route(runtime={
            "custom_agents_available": False,
            "profiles": [],
            "parent_default_available": False,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        })
        self.assertEqual("sequential-current-session", sequential["fallback"])

    def test_high_risk_unknown_capability_stops_at_gate(self):
        receipt = route(
            factors(security_data_migration_public_contract_risk="security"),
            {
                "custom_agents_available": False,
                "profiles": [],
                "parent_default_available": True,
                "parent_capability_classes": [],
                "current_session_capability_classes": [],
            },
        )
        self.assertEqual("human-gate", receipt["fallback"])
        self.assertEqual("unresolved", receipt["runtime_mapping"])

    def test_profile_cannot_self_attest_non_widening_sandbox(self):
        candidate = profile()
        candidate["parent_sandbox_mode"] = "read-only"
        candidate["sandbox_non_widening"] = True
        receipt = route(
            runtime={
                "custom_agents_available": True,
                "profiles": [candidate],
                "parent_default_available": True,
                "parent_capability_classes": [],
                "current_session_capability_classes": [],
            }
        )
        self.assertEqual("parent-default", receipt["fallback"])

    def test_high_risk_can_use_declared_current_capability(self):
        receipt = route(
            factors(security_data_migration_public_contract_risk="security"),
            {
                "custom_agents_available": False,
                "profiles": [],
                "parent_default_available": False,
                "parent_capability_classes": [],
                "current_session_capability_classes": ["security-reviewer"],
            },
        )
        self.assertEqual("sequential-current-session", receipt["fallback"])

    def test_route_only_binds_authority_and_scope(self):
        receipt = route()
        self.assertNotIn("authority", receipt)
        self.assertTrue(receipt["authority_invariants"]["profile_cannot_expand_permissions"])
        self.assertTrue(receipt["authority_invariants"]["worker_receipt_cannot_prove_completion"])

    def test_tampered_route_receipt_is_detected(self):
        receipt = route()
        receipt["assigned_scope"].append("outside-owned-scope.py")
        result = routing.validate_route_receipt(receipt)
        self.assertFalse(result["valid"])
        self.assertIn("route-receipt-integrity-mismatch", result["issues"])

    def test_profile_evidence_semantics_are_validated(self):
        receipt = route()
        receipt["config_evidence"]["name"] = "spoofed-profile"
        receipt["config_evidence"]["config_valid"] = False
        receipt["config_evidence_sha256"] = routing._digest(receipt["config_evidence"])
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        result = routing.validate_route_receipt(receipt)
        self.assertIn("profile-config-evidence-mismatch", result["issues"])

        receipt = route()
        receipt["execution_mode"] = "parent-default"
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        self.assertIn(
            "unexpected-custom-profile-evidence",
            routing.validate_route_receipt(receipt)["issues"],
        )

        receipt = route(runtime={
            "custom_agents_available": False,
            "profiles": [],
            "parent_default_available": True,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        })
        receipt["execution_mode"] = "arbitrary-write-everywhere"
        receipt["runtime_mapping"] = "evil"
        receipt["fallback"] = "none"
        receipt["degraded"] = False
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        self.assertIn(
            "execution-mode-semantic-mismatch",
            routing.validate_route_receipt(receipt)["issues"],
        )

        receipt = route()
        receipt["classification"]["capability_class"] = "security-reviewer"
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        self.assertIn(
            "classification-semantic-mismatch",
            routing.validate_route_receipt(receipt)["issues"],
        )

        receipt = route()
        receipt["selected_role"] = "security-reviewer"
        receipt["assigned_scope_sha256"] = "0" * 64
        receipt["source_revision_sha256"] = "0" * 64
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        issues = routing.validate_route_receipt(receipt)["issues"]
        self.assertIn("selected-role-semantic-mismatch", issues)
        self.assertIn("assigned-scope-digest-mismatch", issues)
        self.assertIn("source-revision-digest-mismatch", issues)

        receipt = route(runtime={
            "custom_agents_available": False,
            "profiles": [],
            "parent_default_available": True,
            "parent_capability_classes": [],
            "current_session_capability_classes": [],
        })
        receipt["classification"] = routing.classify_task(
            factors(independence_parallelizability="coupled")
        )
        receipt["selected_role"] = receipt["classification"]["selected_role"]
        unsigned = {key: value for key, value in receipt.items() if key != "route_receipt_id"}
        receipt["route_receipt_id"] = routing._digest(unsigned)
        self.assertIn(
            "execution-mode-semantic-mismatch",
            routing.validate_route_receipt(receipt)["issues"],
        )


class ReceiptTests(unittest.TestCase):
    def worker(self, route_receipt, **changes):
        value = {
            "route_receipt_id": route_receipt["route_receipt_id"],
            "task_id": route_receipt["task_id"],
            "assigned_scope_sha256": route_receipt["assigned_scope_sha256"],
            "source_revision_sha256": route_receipt["source_revision_sha256"],
            "status": "complete",
            "output_artifacts": ["test-output.txt"],
            "artifact_digests": {"test-output.txt": routing._digest("test-output")},
            "conflicts": [],
        }
        value.update(changes)
        return value

    def test_valid_worker_receipt_is_coordination_only(self):
        assignment = route()
        result = routing.validate_worker_receipt(self.worker(assignment), assignment)
        self.assertTrue(result["valid_coordination_evidence"])
        self.assertFalse(result["accepted_as_completion"])

    def test_partial_failed_stale_and_conflicting_receipts_are_rejected(self):
        assignment = route()
        cases = (
            {"status": "partial"},
            {"status": "failed"},
            {"source_revision_sha256": "stale"},
            {"conflicts": ["worker-b disagrees"]},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                result = routing.validate_worker_receipt(self.worker(assignment, **changes), assignment)
                self.assertFalse(result["valid_coordination_evidence"])

    def test_missing_receipt_fields_are_rejected_without_crash(self):
        result = routing.validate_worker_receipt({}, route())
        self.assertFalse(result["valid_coordination_evidence"])
        self.assertTrue(result["issues"][0].startswith("missing-fields:"))

    def test_main_agent_must_verify_before_integration(self):
        assignment = route()
        worker = routing.validate_worker_receipt(self.worker(assignment), assignment)
        unverified = routing.validate_main_agent_disposition(
            {
                "route_receipt_id": assignment["route_receipt_id"],
                "worker_validation_id": worker["validation_receipt_id"],
                "disposition": "accepted",
            },
            assignment,
            worker,
            current_source_revision=assignment["source_revision"],
            current_profile_digest=assignment["selected_profile_digest"],
            assignment_fresh=True,
        )
        self.assertFalse(unverified["integration_accepted"])
        accepted = routing.validate_main_agent_disposition(
            {
                "route_receipt_id": assignment["route_receipt_id"],
                "worker_validation_id": worker["validation_receipt_id"],
                "disposition": "accepted",
                "verification": {
                    "status": "passed",
                    "artifacts": ["unittest-output"],
                    "artifact_digests": {"unittest-output": routing._digest("verified")},
                },
            },
            assignment,
            worker,
            current_source_revision=assignment["source_revision"],
            current_profile_digest=assignment["selected_profile_digest"],
            assignment_fresh=True,
        )
        self.assertTrue(accepted["integration_accepted"])
        self.assertFalse(accepted["completion_proven"])
        self.assertEqual(
            routing._digest(self.worker(assignment)), worker["worker_receipt_sha256"]
        )
        self.assertEqual(
            routing._digest({"test-output.txt": routing._digest("test-output")}),
            worker["artifact_digests_sha256"],
        )

    def test_worker_artifact_digests_must_cover_exact_outputs(self):
        assignment = route()
        receipt = self.worker(assignment, artifact_digests={})
        result = routing.validate_worker_receipt(receipt, assignment)
        self.assertIn("artifact-digests-missing-or-invalid", result["issues"])

    def test_main_agent_rejects_stale_source_profile_and_assignment(self):
        assignment = route()
        worker = routing.validate_worker_receipt(self.worker(assignment), assignment)
        result = routing.validate_main_agent_disposition(
            {
                "route_receipt_id": assignment["route_receipt_id"],
                "worker_validation_id": worker["validation_receipt_id"],
                "disposition": "accepted",
                "verification": {
                    "status": "passed",
                    "artifacts": ["test-output"],
                    "artifact_digests": {"test-output": routing._digest("verified")},
                },
            },
            assignment,
            worker,
            current_source_revision={"head_sha": "new-head"},
            current_profile_digest="new-profile",
            assignment_fresh=False,
        )
        self.assertIn("stale-source-revision", result["issues"])
        self.assertIn("stale-or-conflicting-profile-digest", result["issues"])
        self.assertIn("assignment-not-fresh", result["issues"])

    def test_forged_worker_validation_is_rejected(self):
        assignment = route()
        forged = {
            "valid_coordination_evidence": True,
            "route_receipt_id": assignment["route_receipt_id"],
        }
        result = routing.validate_main_agent_disposition(
            {
                "route_receipt_id": assignment["route_receipt_id"],
                "worker_validation_id": "forged-validation",
                "disposition": "accepted",
                "verification": {
                    "status": "passed",
                    "artifacts": ["test-output"],
                    "artifact_digests": {"test-output": routing._digest("verified")},
                },
            },
            assignment,
            forged,
            current_source_revision=assignment["source_revision"],
            current_profile_digest=assignment["selected_profile_digest"],
            assignment_fresh=True,
        )
        self.assertFalse(result["integration_accepted"])
        self.assertIn("worker-validation-integrity-mismatch", result["issues"])


if __name__ == "__main__":
    unittest.main()
