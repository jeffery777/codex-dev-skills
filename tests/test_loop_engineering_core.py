from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "skills" / "loop-engineering" / "scripts" / "loop_core.py"
SPEC = importlib.util.spec_from_file_location("loop_core", CORE_PATH)
core = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(core)


def base_input() -> dict:
    return {
        "request": {"kind": "implementation", "risk": "routine"},
        "objective": {"clear": True, "complete": False},
        "state": {
            "protected_history_sha256": "none",
            "source_conflict": False,
            "verification": "not_run",
            "review": "not_required",
            "human_gate": "not_required",
            "task_status": "ready",
        },
        "runtime": {
            "surface": "cli",
            "capabilities": {"goal": True, "subagents": True, "scheduler": False, "threads": False},
        },
        "work": {"parallelizable": False, "ownership_disjoint": True},
    }


class WorkflowDecisionTests(unittest.TestCase):
    def evaluate(
        self,
        changes: dict | None = None,
        *,
        trusted_authority: dict | None = None,
    ):
        data = base_input()
        for section, values in (changes or {}).items():
            data.setdefault(section, {}).update(values)
        authority = {"protected_history_sha256": "none"}
        if trusted_authority is not None:
            authority.update(trusted_authority)
        return core.evaluate_workflow_case(
            {"id": "case", "input": data, "expect": {}},
            trusted_authority=authority,
        )

    def test_implementation_route(self):
        self.assertEqual("implementation-slice", self.evaluate()["route"])

    def test_docs_route(self):
        self.assertEqual("docs-update", self.evaluate({"request": {"kind": "docs"}})["route"])

    def test_deep_review_route(self):
        result = self.evaluate({"request": {"kind": "review", "risk": "high"}})
        self.assertEqual("code-review-deep", result["route"])

    def test_unclear_objective_stops(self):
        result = self.evaluate({"objective": {"clear": False}})
        self.assertEqual("human-gate", result["route"])

    def test_source_conflict_stops(self):
        result = self.evaluate({"state": {"source_conflict": True}})
        self.assertIn("source-of-truth-conflict", result["violations"])

    def test_workflow_sections_and_capabilities_require_objects(self):
        with self.assertRaisesRegex(core.LoopContractError, "state must be an object"):
            core.evaluate_workflow_case(
                {"id": "bad-state", "input": {"state": ["ready"]}}
            )
        with self.assertRaisesRegex(core.LoopContractError, "capabilities"):
            self.evaluate({"runtime": {"capabilities": ["subagents"]}})

    def test_pending_gate_stops(self):
        result = self.evaluate({"state": {"human_gate": "pending"}})
        self.assertEqual("blocked-by-human-gate", result["next_decision"])

    def test_false_completion_is_rejected(self):
        result = self.evaluate({"objective": {"complete": True}, "state": {"review": "blocked"}})
        self.assertFalse(result["complete"])
        self.assertTrue(result["violations"][0].startswith("completion-evidence-missing"))

    def test_complete_requires_all_evidence(self):
        result = self.evaluate(
            {
                "objective": {"complete": True},
                "state": {"task_status": "done", "verification": "passed", "review": "passed"},
            }
        )
        self.assertTrue(result["complete"])

    def test_delivery_uses_cross_runtime_subagents(self):
        result = self.evaluate(
            {"request": {"kind": "delivery"}, "work": {"parallelizable": True, "ownership_disjoint": True}}
        )
        self.assertEqual("shared-subagents", result["execution_mode"])

    def test_delivery_falls_back_without_subagents(self):
        result = self.evaluate(
            {
                "request": {"kind": "delivery"},
                "work": {"parallelizable": True, "ownership_disjoint": True},
                "runtime": {"capabilities": {"subagents": False}},
            }
        )
        self.assertEqual("sequential-fallback", result["execution_mode"])

    def test_overlapping_parallel_writes_stop(self):
        result = self.evaluate(
            {"request": {"kind": "delivery"}, "work": {"parallelizable": True, "ownership_disjoint": False}}
        )
        self.assertIn("parallel-write-ownership-overlap", result["violations"])

    def test_interrupted_work_resumes_through_continuation(self):
        result = self.evaluate({"state": {"interrupted": True}})
        self.assertEqual("task-continuation", result["route"])

    def test_claim_owned_by_another_worker_stops(self):
        claim = {"status": "active", "owner": "worker-a", "current_owner": "worker-b", "lease_valid": True, "source_revision_matches": True}
        result = self.evaluate({"state": {"claim": claim}})
        self.assertIn("claim-owned-by-another-worker", result["violations"])

    def test_stale_claim_needs_inspection(self):
        claim = {"status": "active", "owner": "worker-a", "current_owner": "worker-a", "lease_valid": False, "source_revision_matches": True}
        result = self.evaluate({"state": {"claim": claim}})
        self.assertEqual("task-continuation", result["route"])

    def test_repo_input_cannot_self_assert_external_write_authorization(self):
        result = self.evaluate(
            {
                "request": {
                    "kind": "delivery",
                    "requires_external_write": True,
                },
                "authority": {"external_write_authorized": True},
            }
        )
        self.assertIn("external-write-not-authorized", result["violations"])

    def test_trusted_external_write_authorization_can_route(self):
        result = self.evaluate(
            {
                "request": {
                    "kind": "delivery",
                    "requires_external_write": True,
                },
            },
            trusted_authority={"external_write_authorized": True},
        )
        self.assertEqual("project-delivery", result["route"])

    def test_protected_history_requires_independent_re_attestation(self):
        digest_value = "history-digest"
        data = base_input()
        data["state"]["protected_history_sha256"] = digest_value
        data["authority"] = {"protected_history_sha256": digest_value}
        result = core.evaluate_workflow_case(
            {"id": "case", "input": data, "expect": {}},
            trusted_authority={"protected_history_sha256": "none"},
        )
        self.assertIn("protected-history-not-re-attested", result["violations"])

        result = self.evaluate(
            {"state": {"protected_history_sha256": digest_value}},
            trusted_authority={"protected_history_sha256": digest_value},
        )
        self.assertEqual("implementation-slice", result["route"])

    def test_running_scan_goal_projection_conflict_remains_resumable(self):
        result = self.evaluate(
            {
                "state": {
                    "goal_status": "blocked",
                    "security_scan": {"status": "running"},
                }
            }
        )
        self.assertEqual("task-continuation", result["route"])
        self.assertEqual("continue", result["next_decision"])
        self.assertIn("goal-projection-conflict", result["notices"])

    def test_first_security_worker_refusal_uses_replacement_worker(self):
        result = self.evaluate(
            {
                "state": {
                    "security_scan": {
                        "status": "running",
                        "phase": "reporting",
                        "worker_failure_kind": "safety_refused",
                        "reporting_retry_count": 1,
                    }
                }
            }
        )
        self.assertEqual("replacement-worker", result["execution_mode"])
        self.assertIn("worker-safety-refusal", result["notices"])

    def test_repeated_security_worker_refusal_needs_fallback_authorization(self):
        result = self.evaluate(
            {
                "state": {
                    "security_scan": {
                        "status": "running",
                        "phase": "reporting",
                        "worker_failure_kind": "safety_refused",
                        "reporting_retry_count": 2,
                    }
                }
            }
        )
        self.assertIn(
            "security-report-parent-fallback-not-authorized",
            result["violations"],
        )

    def test_trusted_parent_report_fallback_keeps_scan_running(self):
        result = self.evaluate(
            {
                "state": {
                    "goal_status": "blocked",
                    "security_scan": {
                        "status": "running",
                        "phase": "reporting",
                        "worker_failure_kind": "safety_refused",
                        "reporting_retry_count": 2,
                    },
                }
            },
            trusted_authority={
                "parent_security_report_fallback_authorized": True
            },
        )
        self.assertEqual("parent-report-fallback", result["execution_mode"])
        self.assertEqual("continue", result["next_decision"])
        self.assertIn("security-scan-remains-running", result["notices"])

    def test_parent_report_fallback_is_rejected_outside_reporting_phase(self):
        result = self.evaluate(
            {
                "state": {
                    "security_scan": {
                        "status": "running",
                        "phase": "discovery",
                        "worker_failure_kind": "safety_refused",
                        "reporting_retry_count": 2,
                    }
                }
            },
            trusted_authority={
                "parent_security_report_fallback_authorized": True
            },
        )
        self.assertEqual("human-gate", result["route"])
        self.assertIn("security-worker-failure-phase-mismatch", result["violations"])

    def test_security_scan_state_rejects_malformed_shape_and_negative_retry(self):
        with self.assertRaisesRegex(core.LoopContractError, "must be an object"):
            self.evaluate({"state": {"security_scan": ["running"]}})
        with self.assertRaisesRegex(core.LoopContractError, "non-negative integer"):
            self.evaluate(
                {
                    "state": {
                        "security_scan": {
                            "status": "running",
                            "phase": "reporting",
                            "worker_failure_kind": "safety_refused",
                            "reporting_retry_count": -1,
                        }
                    }
                }
            )
        with self.assertRaisesRegex(core.LoopContractError, "phase is unsupported"):
            self.evaluate(
                {
                    "state": {
                        "security_scan": {
                            "status": "running",
                            "phase": "building_report",
                        }
                    }
                }
            )
        with self.assertRaisesRegex(core.LoopContractError, "status is unsupported"):
            self.evaluate(
                {"state": {"security_scan": {"status": "paused", "phase": "none"}}}
            )
        with self.assertRaisesRegex(
            core.LoopContractError, "worker failure kind is unsupported"
        ):
            self.evaluate(
                {
                    "state": {
                        "security_scan": {
                            "status": "running",
                            "phase": "reporting",
                            "worker_failure_kind": "refused",
                        }
                    }
                }
            )

    def test_goal_status_rejects_unknown_projection(self):
        with self.assertRaisesRegex(core.LoopContractError, "goal status"):
            self.evaluate({"state": {"goal_status": "paused"}})


class TransitionTests(unittest.TestCase):
    def test_ready_requires_definition(self):
        with self.assertRaises(core.LoopContractError):
            core.validate_transition("planned", "ready", task_definition={})

    def test_in_progress_requires_fenced_claim(self):
        with self.assertRaises(core.LoopContractError):
            core.validate_transition("ready", "in_progress", claim={"status": "active"})

    def test_reviewing_requires_artifact_and_verification_run(self):
        with self.assertRaises(core.LoopContractError):
            core.validate_transition("in_progress", "reviewing", evidence={"verification": "not_run"})

    def test_done_requires_review_and_gate(self):
        with self.assertRaises(core.LoopContractError):
            core.validate_transition("reviewing", "done", evidence={"verification": "passed", "review": "blocked", "human_gate": "not_required"})

    def test_terminal_status_cannot_advance(self):
        with self.assertRaises(core.LoopContractError):
            core.validate_transition("accepted", "in_progress")

    def test_manifest_required_review_and_human_gate_cannot_be_waived(self):
        definition = {
            "review_required": True,
            "review_mode": "code-review-deep",
            "human_gate_required": True,
            "human_gate_name": "publish",
            "human_gate_satisfied": False,
        }
        with self.assertRaisesRegex(core.LoopContractError, "manifest review"):
            core.validate_transition(
                "reviewing",
                "done",
                task_definition=definition,
                evidence={
                    "verification": "passed",
                    "review": "not_required",
                    "human_gate": "satisfied",
                },
            )
        with self.assertRaisesRegex(core.LoopContractError, "manifest human gate"):
            core.validate_transition(
                "reviewing",
                "done",
                task_definition=definition,
                evidence={
                    "verification": "passed",
                    "review": {
                        "status": "passed",
                        "mode": "code-review-deep",
                        "artifacts": ["review-report"],
                    },
                    "human_gate": "not_required",
                },
            )
        definition["human_gate_satisfied"] = True
        core.validate_transition(
            "reviewing",
            "done",
            task_definition=definition,
            evidence={
                "verification": "passed",
                "review": {
                    "status": "passed",
                    "mode": "code-review-deep",
                    "artifacts": ["review-report"],
                },
                "human_gate": "satisfied",
            },
        )


class EventTests(unittest.TestCase):
    def event(self, **changes):
        event = {
            "sequence": 1,
            "event_id": "event-1",
            "actor": "test",
            "occurred_at": "2026-07-10T00:00:00Z",
            "expected_state_revision": 0,
            "previous_event_hash": None,
            "idempotency_key": "event-1",
            "type": "task_transition",
            "task_id": "T1",
            "payload": {
                "target_status": "ready",
                "evidence": {},
                "claim": {},
            },
        }
        event.update(changes)
        event["event_hash"] = core.calculate_event_hash(event)
        return event

    def state(self):
        return {
            "revision": 0,
            "last_event_hash": None,
            "objective_id": "issue-81",
            "source_revision": {
                "branch": "branch",
                "head_sha": "abc123",
                "spec_sha256": "spec",
                "task_manifest_sha256": "manifest",
            },
            "tasks": {"T1": {"status": "planned", "definition": {"scope": ["x"], "dod": ["y"], "verification": ["test"], "dependencies": []}}},
            "events": [],
            "idempotency": {},
        }

    def bind_authorization(
        self,
        state,
        event,
        action,
        *,
        actor="maintainer",
        artifact="approval-record",
        **scope,
    ):
        authorization = {
            "action": action,
            "principal": {"type": "user", "id": actor},
            "objective_id": state["objective_id"],
            "artifact": artifact,
            "source_revision_sha256": core.source_revision_digest(
                state["source_revision"]
            ),
            **scope,
        }
        event["payload"]["authorization"] = authorization
        authorization["protected_payload_sha256"] = core.protected_payload_digest(
            event["payload"]
        )
        event["event_hash"] = core.calculate_event_hash(event)
        return authorization

    def trusted_authority(self, event):
        return {
            "action": core.protected_event_action(event),
            "authorization_receipt_sha256": core.digest(
                event["payload"]["authorization"]
            ),
        }

    def test_apply_event_is_non_mutating(self):
        state = self.state()
        original = copy.deepcopy(state)
        updated, replayed = core.apply_event(state, self.event())
        self.assertEqual(original, state)
        self.assertFalse(replayed)
        self.assertEqual("ready", updated["tasks"]["T1"]["status"])

    def test_stale_revision_rejected(self):
        event = self.event(expected_state_revision=2)
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(self.state(), event)

    def test_tampered_event_rejected(self):
        event = self.event()
        event["payload"]["target_status"] = "blocked"
        with self.assertRaises(core.LoopContractError):
            core.apply_event(self.state(), event)

    def test_idempotent_replay_returns_same_state(self):
        event = self.event()
        updated, _ = core.apply_event(self.state(), event)
        replayed, was_replayed = core.apply_event(updated, event)
        self.assertTrue(was_replayed)
        self.assertEqual(updated, replayed)

    def test_idempotency_key_conflict_is_rejected(self):
        event = self.event()
        updated, _ = core.apply_event(self.state(), event)
        conflict = copy.deepcopy(event)
        conflict["payload"]["target_status"] = "blocked"
        conflict["event_hash"] = core.calculate_event_hash(conflict)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(updated, conflict)

    def test_tampered_hash_is_rejected_before_idempotent_replay(self):
        event = self.event()
        updated, _ = core.apply_event(self.state(), event)
        replay = copy.deepcopy(event)
        replay["event_hash"] = "tampered"
        with self.assertRaises(core.LoopContractError):
            core.apply_event(updated, replay)

    def test_core_rejects_boolean_revision_sequence_and_generation(self):
        state = self.state()
        state["revision"] = False
        with self.assertRaisesRegex(core.LoopContractError, "state revision"):
            core.apply_event(state, self.event())

        event = self.event(sequence=True)
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "sequence must be an integer"):
            core.apply_event(self.state(), event)

        event = self.event(expected_state_revision=False)
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(
            core.LoopContractError, "expected_state_revision must be an integer"
        ):
            core.apply_event(self.state(), event)

        state = self.state()
        state["tasks"]["T1"]["status"] = "ready"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": True, "nonce": "nonce"},
            "expected_state_revision": False,
            "source_revision": copy.deepcopy(state["source_revision"]),
            "claimed_at": "2026-07-10T00:00:00Z",
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        event = self.event(
            actor="worker-1",
            type="claim_acquired",
            payload={"claim": claim},
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "expected_state_revision"):
            core.apply_event(state, event)

        claim["expected_state_revision"] = 0
        event["payload"]["claim"] = claim
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "fencing generation"):
            core.apply_event(state, event)

    def test_ready_event_rejects_unmet_manifest_dependency(self):
        state = self.state()
        state["tasks"]["T0"] = {
            "status": "ready",
            "definition": {"scope": ["x"], "dod": ["y"], "verification": ["test"], "dependencies": []},
        }
        state["tasks"]["T1"]["definition"]["dependencies"] = ["T0"]
        with self.assertRaises(core.LoopContractError):
            core.apply_event(state, self.event())

    def test_unknown_event_type_is_rejected(self):
        event = self.event(type="unknown")
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(self.state(), event)

    def test_objective_completion_is_terminal(self):
        state = self.state()
        state["objective_status"] = "complete"
        event = self.event(
            type="gate_updated",
            task_id="",
            payload={"gate": "publish", "status": "pending"},
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "completion is terminal"):
            core.apply_event(state, event)

    def test_event_time_cannot_move_backwards(self):
        first = self.event(occurred_at="2026-07-10T00:02:00Z")
        state, _ = core.apply_event(self.state(), first)
        second = {
            "sequence": 2,
            "event_id": "event-2",
            "actor": "test",
            "occurred_at": "2026-07-10T00:01:00Z",
            "expected_state_revision": 1,
            "previous_event_hash": state["last_event_hash"],
            "idempotency_key": "event-2",
            "type": "gate_updated",
            "task_id": "",
            "payload": {"gate": "publish", "status": "pending"},
        }
        second["event_hash"] = core.calculate_event_hash(second)
        with self.assertRaisesRegex(core.LoopContractError, "must not move backwards"):
            core.apply_event(state, second)

    def test_claim_event_fences_in_progress_transition(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "ready"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "nonce-1"},
            "expected_state_revision": 0,
            "source_revision": copy.deepcopy(state["source_revision"]),
            "claimed_at": "2026-07-10T00:00:00Z",
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        acquired = self.event(
            actor="worker-1",
            type="claim_acquired",
            task_id="T1",
            payload={"claim": claim},
        )
        acquired["event_hash"] = core.calculate_event_hash(acquired)
        claimed_state, _ = core.apply_event(state, acquired)

        transition = {
            "sequence": 2,
            "event_id": "event-2",
            "actor": "worker-1",
            "occurred_at": "2026-07-10T00:01:00Z",
            "expected_state_revision": 1,
            "previous_event_hash": acquired["event_hash"],
            "idempotency_key": "event-2",
            "type": "task_transition",
            "task_id": "T1",
            "payload": {
                "target_status": "in_progress",
                "fencing_token": claim["fencing_token"],
                "evidence": {},
            },
        }
        transition["event_hash"] = core.calculate_event_hash(transition)
        progressed, _ = core.apply_event(claimed_state, transition)
        self.assertEqual("in_progress", progressed["tasks"]["T1"]["status"])

        forged = copy.deepcopy(transition)
        forged["payload"]["fencing_token"] = {"generation": 1, "nonce": "forged"}
        forged["event_hash"] = core.calculate_event_hash(forged)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(claimed_state, forged)

    def test_expired_claim_cannot_enter_in_progress(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "ready"
        state["claims"] = {
            "T1": {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "nonce-1"},
                "lease_expires_at": "2026-07-10T00:00:00Z",
            }
        }
        event = self.event(
            occurred_at="2026-07-10T00:01:00Z",
            payload={
                "target_status": "in_progress",
                "fencing_token": {"generation": 1, "nonce": "nonce-1"},
                "evidence": {},
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(state, event)

    def test_in_flight_transition_requires_current_fencing_token(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "in_progress"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 2, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            payload={
                "target_status": "reviewing",
                "evidence": {
                    "verification": {"status": "passed", "artifacts": ["test-output"]},
                    "review": {"status": "required", "artifacts": []},
                },
            }
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaises(core.LoopContractError):
            core.apply_event(state, event)

    def test_task_transition_requires_active_claim_owner_actor(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "in_progress"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 2, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="worker-2",
            payload={
                "target_status": "reviewing",
                "fencing_token": claim["fencing_token"],
                "evidence": {
                    "verification": {"status": "passed", "artifacts": ["test-output"]},
                    "review": {"status": "required", "artifacts": []},
                },
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "active claim owner"):
            core.apply_event(state, event)

    def test_required_review_completion_needs_delegated_live_authorization(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "reviewing"
        state["tasks"]["T1"]["definition"].update(
            {
                "review_required": True,
                "review_mode": "code-review-deep",
                "human_gate_required": False,
            }
        )
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "review-current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="worker-1",
            payload={
                "target_status": "done",
                "fencing_token": claim["fencing_token"],
                "human_gate": "not_required",
                "evidence": {
                    "verification": {
                        "status": "passed",
                        "artifacts": ["test-output"],
                    },
                    "review": {
                        "status": "passed",
                        "mode": "code-review-deep",
                        "artifacts": ["review-report"],
                    },
                },
            },
        )
        self.bind_authorization(
            state,
            event,
            "task_completion",
            artifact="review-report",
            task_id="T1",
        )
        with self.assertRaisesRegex(core.LoopContractError, "live action authorization"):
            core.apply_event(state, event)
        updated, _ = core.apply_event(
            state,
            event,
            trusted_authority=self.trusted_authority(event),
        )
        self.assertEqual("done", updated["tasks"]["T1"]["status"])
        self.assertEqual(
            "code-review-deep",
            updated["tasks"]["T1"]["evidence"]["review"]["mode"],
        )

    def test_required_human_gate_ignores_self_asserted_transition_payload(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "reviewing"
        state["tasks"]["T1"]["definition"].update(
            {
                "review_required": False,
                "review_mode": "none",
                "human_gate_required": True,
                "human_gate_name": "publish",
            }
        )
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "gate-current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="worker-1",
            payload={
                "target_status": "done",
                "fencing_token": claim["fencing_token"],
                "human_gate": "satisfied",
                "evidence": {
                    "verification": {"status": "passed", "artifacts": ["test"]},
                    "review": {
                        "status": "not_required",
                        "mode": "none",
                        "artifacts": [],
                    },
                },
            },
        )
        with self.assertRaisesRegex(core.LoopContractError, "manifest human gate"):
            core.apply_event(state, event)

    def test_claim_expiry_rejects_event_before_deadline(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "in_progress"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="coordinator",
            occurred_at="2026-07-10T00:01:00Z",
            type="claim_expired",
            payload={
                "fencing_token": claim["fencing_token"],
                "blocker": {"reason": "lease expired"},
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "lease deadline"):
            core.apply_event(state, event)

    def test_claim_expiry_at_deadline_remains_valid(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "in_progress"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="coordinator",
            occurred_at=claim["lease_expires_at"],
            type="claim_expired",
            payload={
                "fencing_token": claim["fencing_token"],
                "blocker": {"reason": "lease expired"},
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        updated, _ = core.apply_event(state, event)
        self.assertEqual("expired", updated["claims"]["T1"]["status"])
        self.assertEqual("blocked", updated["tasks"]["T1"]["status"])

    def test_accepted_transition_requires_bound_authorization(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        evidence = {
            "acceptance": {"status": "satisfied", "artifact": "approval-record"}
        }
        event = self.event(
            actor="maintainer",
            payload={"target_status": "accepted", "evidence": evidence},
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "authorization"):
            core.apply_event(state, event)

        self.bind_authorization(state, event, "task_acceptance", task_id="T1")
        with self.assertRaisesRegex(core.LoopContractError, "live action authorization"):
            core.apply_event(state, event)
        updated, _ = core.apply_event(
            state, event, trusted_authority=self.trusted_authority(event)
        )
        self.assertEqual("accepted", updated["tasks"]["T1"]["status"])

    def test_gate_satisfaction_requires_bound_authorization(self):
        state = self.state()
        event = self.event(
            actor="maintainer",
            type="gate_updated",
            task_id="",
            payload={
                "gate": "publish",
                "status": "satisfied",
                "evidence": {"artifact": "approval-record"},
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "authorization"):
            core.apply_event(state, event)

        self.bind_authorization(state, event, "gate_satisfaction", gate="publish")
        with self.assertRaisesRegex(core.LoopContractError, "live action authorization"):
            core.apply_event(state, event)
        updated, _ = core.apply_event(
            state, event, trusted_authority=self.trusted_authority(event)
        )
        self.assertEqual("satisfied", updated["gates"]["publish"]["status"])

    def test_objective_completion_requires_bound_authorization(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        event = self.event(
            actor="maintainer",
            type="objective_completed",
            task_id="",
            payload={
                "verification": "passed",
                "review": "not_required",
                "human_gate": "not_required",
                "evidence": {"artifact": "approval-record"},
            },
        )
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "authorization"):
            core.apply_event(state, event)

        self.bind_authorization(state, event, "objective_completion")
        with self.assertRaisesRegex(core.LoopContractError, "live action authorization"):
            core.apply_event(state, event)
        updated, _ = core.apply_event(
            state, event, trusted_authority=self.trusted_authority(event)
        )
        self.assertEqual("complete", updated["objective_status"])

    def test_protected_event_rejects_mismatched_live_receipt(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        event = self.event(
            actor="maintainer",
            payload={
                "target_status": "accepted",
                "evidence": {
                    "acceptance": {
                        "status": "satisfied",
                        "artifact": "approval-record",
                    }
                },
            },
        )
        self.bind_authorization(state, event, "task_acceptance", task_id="T1")
        with self.assertRaisesRegex(core.LoopContractError, "receipt mismatch"):
            core.apply_event(
                state,
                event,
                trusted_authority={
                    "action": "task_acceptance",
                    "authorization_receipt_sha256": "forged",
                },
            )

    def test_protected_authorization_binds_full_payload_semantics(self):
        state = self.state()
        event = self.event(
            actor="maintainer",
            type="gate_updated",
            task_id="",
            payload={
                "gate": "publish",
                "status": "satisfied",
                "evidence": {"artifact": "approval-record"},
            },
        )
        self.bind_authorization(state, event, "gate_satisfaction", gate="publish")
        trusted = self.trusted_authority(event)
        event["payload"]["status"] = "not_required"
        event["event_hash"] = core.calculate_event_hash(event)
        with self.assertRaisesRegex(core.LoopContractError, "protected payload mismatch"):
            core.apply_event(state, event, trusted_authority=trusted)

    def test_acceptance_requires_releasing_active_claim(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "maintainer", "id": "maintainer"},
            "fencing_token": {"generation": 1, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="maintainer",
            payload={
                "target_status": "accepted",
                "fencing_token": claim["fencing_token"],
                "evidence": {
                    "acceptance": {
                        "status": "satisfied",
                        "artifact": "approval-record",
                    }
                },
            },
        )
        self.bind_authorization(state, event, "task_acceptance", task_id="T1")
        with self.assertRaisesRegex(core.LoopContractError, "releasing the active claim"):
            core.apply_event(
                state,
                event,
                trusted_authority=self.trusted_authority(event),
            )

    def test_acceptance_authorization_binds_principal_source_scope_and_artifact(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        base_event = self.event(
            actor="maintainer",
            payload={
                "target_status": "accepted",
                "evidence": {
                    "acceptance": {
                        "status": "satisfied",
                        "artifact": "approval-record",
                    }
                },
            },
        )
        self.bind_authorization(state, base_event, "task_acceptance", task_id="T1")
        variants = (
            ("principal", lambda auth: auth["principal"].update({"id": "attacker"})),
            ("source revision", lambda auth: auth.update({"source_revision_sha256": "forged"})),
            ("scope", lambda auth: auth.update({"task_id": "T2"})),
            ("artifact", lambda auth: auth.update({"artifact": "other-approval"})),
        )
        for expected, mutate in variants:
            with self.subTest(expected=expected):
                event = copy.deepcopy(base_event)
                mutate(event["payload"]["authorization"])
                event["event_hash"] = core.calculate_event_hash(event)
                with self.assertRaisesRegex(core.LoopContractError, expected):
                    core.apply_event(
                        state,
                        event,
                        trusted_authority=self.trusted_authority(event),
                    )

    def test_gate_and_completion_require_matching_concrete_evidence_artifacts(self):
        state = self.state()
        gate_event = self.event(
            actor="maintainer",
            type="gate_updated",
            task_id="",
            payload={
                "gate": "publish",
                "status": "satisfied",
                "evidence": {},
            },
        )
        self.bind_authorization(
            state, gate_event, "gate_satisfaction", gate="publish"
        )
        with self.assertRaisesRegex(core.LoopContractError, "evidence artifact"):
            core.apply_event(
                state,
                gate_event,
                trusted_authority=self.trusted_authority(gate_event),
            )

        state["tasks"]["T1"]["status"] = "done"
        completion_event = self.event(
            actor="maintainer",
            type="objective_completed",
            task_id="",
            payload={
                "verification": "passed",
                "review": "not_required",
                "human_gate": "not_required",
                "evidence": {},
            },
        )
        self.bind_authorization(state, completion_event, "objective_completion")
        with self.assertRaisesRegex(core.LoopContractError, "evidence artifact"):
            core.apply_event(
                state,
                completion_event,
                trusted_authority=self.trusted_authority(completion_event),
            )

    def test_claim_revocation_requires_bound_and_live_authorization(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "in_progress"
        claim = {
            "task_id": "T1",
            "status": "active",
            "owner": {"type": "subagent", "id": "worker-1"},
            "fencing_token": {"generation": 1, "nonce": "current"},
            "lease_expires_at": "2026-07-11T00:00:00Z",
        }
        state["claims"] = {"T1": claim}
        event = self.event(
            actor="maintainer",
            type="claim_revoked",
            payload={
                "fencing_token": claim["fencing_token"],
                "blocker": {
                    "kind": "safety",
                    "reason": "operator revoked claim",
                    "artifact": "revocation-record",
                },
            },
        )
        self.bind_authorization(
            state,
            event,
            "claim_revocation",
            artifact="revocation-record",
            task_id="T1",
        )
        with self.assertRaisesRegex(core.LoopContractError, "live action authorization"):
            core.apply_event(state, event)
        updated, _ = core.apply_event(
            state,
            event,
            trusted_authority=self.trusted_authority(event),
        )
        self.assertEqual("revoked", updated["claims"]["T1"]["status"])
        self.assertEqual("blocked", updated["tasks"]["T1"]["status"])

    def test_replay_checks_integrity_without_claiming_live_authorization(self):
        state = self.state()
        state["tasks"]["T1"]["status"] = "done"
        event = self.event(
            actor="maintainer",
            payload={
                "target_status": "accepted",
                "evidence": {
                    "acceptance": {
                        "status": "satisfied",
                        "artifact": "approval-record",
                    }
                },
            },
        )
        self.bind_authorization(state, event, "task_acceptance", task_id="T1")
        updated, _ = core.replay_event(state, event)
        self.assertEqual("accepted", updated["tasks"]["T1"]["status"])

    def test_migration_cannot_waive_manifest_review_or_human_gate(self):
        source_revision = {
            "branch": "branch",
            "head_sha": "abc123",
            "spec_sha256": "spec",
            "task_manifest_sha256": "manifest",
        }
        source_document = {
            "ledger": {
                "schema_version": 1,
                "source_revision": {
                    "branch": "branch",
                    "head_sha": "abc123",
                    "updated_at": "2026-07-10T00:00:00Z",
                },
            },
            "tasks": [
                {
                    "id": "T1",
                    "status": "done",
                    "evidence": {
                        "verification": {"status": "passed"},
                        "review": {"status": "not_required"},
                        "human_gate": {"status": "not_required"},
                    },
                }
            ],
        }
        tasks = {
            "T1": {
                "status": "planned",
                "definition": {
                    "dependencies": [],
                    "review_required": True,
                    "human_gate_required": True,
                },
                "evidence": {},
                "blocker": {},
            }
        }
        with self.assertRaisesRegex(core.LoopContractError, "new protected review"):
            core.materialize_v1_snapshot(
                source_document,
                tasks,
                source_revision,
                "2026-07-10T00:00:00Z",
            )

        source_document["tasks"][0]["evidence"]["review"]["status"] = "passed"
        with self.assertRaisesRegex(core.LoopContractError, "new protected review"):
            core.materialize_v1_snapshot(
                source_document,
                tasks,
                source_revision,
                "2026-07-10T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
