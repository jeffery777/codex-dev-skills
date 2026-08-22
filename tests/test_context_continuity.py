import copy
import importlib.util
import json
import pathlib
import subprocess
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills" / "loop-engineering" / "scripts" / "context_continuity.py"
SPEC = importlib.util.spec_from_file_location("context_continuity", MODULE)
continuity = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(continuity)


def metrics(tokens=1000, quality=90):
    return {
        "objective_total_tokens": tokens,
        "wall_time_seconds": 100,
        "repeated_reads": 1,
        "review_fix_rounds": 2,
        "stale_context_errors": 1,
        "blockers": 0,
        "handoff_bootstrap_tokens": 100,
        "quality_score": quality,
    }


def document():
    checkpoint = {
        "checkpoint_id": "cp-1",
        "objective_id": "issue-165",
        "repository_id": "github.com/jeffery777/codex-dev-skills",
        "branch": "codex/165-context-continuity-rollover",
        "head_sha": "a" * 40,
        "worktree_state": "clean",
        "completed": ["implementation"],
        "remaining": ["review"],
        "verification": ["tests passed"],
        "risks": [],
        "next_packet": "run independent review",
        "source_writer": "source",
        "destination_writer": "destination",
        "source_stop_writing_confirmed": True,
    }
    return {
        "contract_version": continuity.CONTRACT_VERSION,
        "assessment_id": "assessment-1",
        "objective_id": "issue-165",
        "repository_id": "github.com/jeffery777/codex-dev-skills",
        "review_fix": {"completed_rounds": 2, "assessment_trigger_rounds": 2},
        "signals": {
            "stale_findings": 1,
            "repeated_reads": 1,
            "phase_boundary": True,
            "compaction_or_token_pressure": False,
            "independent_high_noise_packet": False,
            "current_context_can_reground": True,
            "human_gate_required": False,
        },
        "runtime": {
            "surface": "cli",
            "control_surface": "cli-exec",
            "mode": "non-interactive",
        },
        "worktree": {"state": "clean"},
        "ownership": {
            "source_writer": "source",
            "exclusive_transfer_ready": True,
            "parallel_packet_disjoint": False,
        },
        "checkpoint": checkpoint,
        "lineage": {
            "rollover_id": "rollover-1",
            "prior_rollover_id": None,
            "prior_checkpoint_sha256": None,
            "progress_since_prior_rollover": True,
            "progress_evidence": ["implementation changed since prior checkpoint"],
            "seen_rollovers": [],
            "graph_projection": "absent",
        },
        "comparison": {
            "same_context": metrics(1200, 90),
            "fresh_rollover": metrics(1000, 92),
        },
    }


class ContextContinuityTests(unittest.TestCase):
    def test_two_round_threshold_only_assesses_and_never_authorizes_action(self):
        value = document()
        value["signals"].update(stale_findings=0, repeated_reads=0, phase_boundary=False)
        result = continuity.assess(value)
        self.assertEqual("continue-current-context", result["decision"])
        self.assertTrue(result["assessment_trigger_reached"])
        self.assertFalse(result["automatic_rollover_authorized"])
        self.assertFalse(result["runtime_action_performed"])
        self.assertFalse(result["task_created"])

    def test_trigger_is_configurable(self):
        value = document()
        value["review_fix"] = {"completed_rounds": 2, "assessment_trigger_rounds": 3}
        result = continuity.assess(value)
        self.assertEqual("continue-current-context", result["decision"])
        self.assertFalse(result["assessment_trigger_reached"])

    def test_five_decisions_are_reachable(self):
        cases = []
        healthy = document()
        healthy["signals"].update(stale_findings=0, repeated_reads=0, phase_boundary=False)
        cases.append((healthy, "continue-current-context"))
        dirty = document()
        dirty["worktree"]["state"] = "dirty"
        dirty["checkpoint"]["worktree_state"] = "dirty"
        cases.append((dirty, "reground-current-context"))
        delegated = document()
        delegated["signals"]["independent_high_noise_packet"] = True
        delegated["ownership"]["parallel_packet_disjoint"] = True
        cases.append((delegated, "delegate-bounded-subagent"))
        cases.append((document(), "prepare-fresh-rollover"))
        blocked = document()
        blocked["signals"]["human_gate_required"] = True
        cases.append((blocked, "stop-for-human-gate"))
        for value, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(expected, continuity.assess(value)["decision"])

    def test_dirty_interactive_and_missing_control_surface_do_not_false_complete(self):
        variants = []
        dirty = document()
        dirty["worktree"]["state"] = "dirty"
        dirty["checkpoint"]["worktree_state"] = "dirty"
        variants.append(dirty)
        interactive = document()
        interactive["runtime"]["mode"] = "interactive"
        variants.append(interactive)
        ide = document()
        ide["runtime"] = {"surface": "ide", "control_surface": "none", "mode": "interactive"}
        variants.append(ide)
        for value in variants:
            result = continuity.assess(value)
            self.assertEqual("reground-current-context", result["decision"])
            self.assertFalse(result["runtime_action_performed"])
            self.assertFalse(result["task_created"])

    def test_checkpoint_requires_single_writer_and_source_stop(self):
        same_writer = document()
        same_writer["checkpoint"]["destination_writer"] = "source"
        with self.assertRaisesRegex(continuity.ContinuityContractError, "distinct"):
            continuity.assess(same_writer)
        not_stopped = document()
        not_stopped["checkpoint"]["source_stop_writing_confirmed"] = False
        result = continuity.assess(not_stopped)
        self.assertEqual("reground-current-context", result["decision"])
        self.assertIn("source-writer-has-not-stopped", result["notices"])

    def test_exact_rollover_replay_is_noop_and_conflict_is_rejected(self):
        value = document()
        digest = continuity.checkpoint_sha256(value["checkpoint"])
        value["lineage"]["seen_rollovers"] = [
            {"rollover_id": "rollover-1", "checkpoint_sha256": digest}
        ]
        replay = continuity.assess(value)
        self.assertTrue(replay["idempotent_replay"])
        self.assertFalse(replay["runtime_action_performed"])
        conflict = copy.deepcopy(value)
        conflict["lineage"]["seen_rollovers"][0]["checkpoint_sha256"] = "b" * 64
        result = continuity.assess(conflict)
        self.assertEqual("stop-for-human-gate", result["decision"])
        self.assertIn("rollover-id-reused-with-different-checkpoint", result["violations"])

    def test_anti_recursion_requires_material_progress(self):
        value = document()
        value["lineage"]["prior_rollover_id"] = "rollover-0"
        value["lineage"]["prior_checkpoint_sha256"] = "c" * 64
        value["lineage"]["progress_since_prior_rollover"] = False
        value["lineage"]["seen_rollovers"] = [
            {"rollover_id": "rollover-0", "checkpoint_sha256": "c" * 64}
        ]
        result = continuity.assess(value)
        self.assertEqual("stop-for-human-gate", result["decision"])
        self.assertIn("consecutive-rollover-without-material-progress", result["violations"])

    def test_graph_is_advisory_only(self):
        value = document()
        value["lineage"]["graph_projection"] = "advisory-conflicting"
        result = continuity.assess(value)
        self.assertEqual("prepare-fresh-rollover", result["decision"])
        self.assertEqual("advisory-only", result["graph_authority"])
        self.assertIn("graph-lineage-conflict-ignored-as-advisory", result["notices"])

    def test_comparison_counts_bootstrap_in_total_and_requires_quality(self):
        result = continuity.assess(document())
        self.assertTrue(result["comparison"]["qualified"])
        shifted = document()
        shifted["comparison"]["fresh_rollover"] = metrics(1400, 92)
        self.assertFalse(continuity.assess(shifted)["comparison"]["qualified"])
        lower_quality = document()
        lower_quality["comparison"]["fresh_rollover"] = metrics(900, 80)
        self.assertFalse(continuity.assess(lower_quality)["comparison"]["qualified"])

    def test_missing_comparison_measurements_regrounds(self):
        value = document()
        value["comparison"]["fresh_rollover"]["objective_total_tokens"] = None
        result = continuity.assess(value)
        self.assertEqual("reground-current-context", result["decision"])
        self.assertIn("measured-rollover-comparison-unavailable", result["notices"])

    def test_unknown_fields_and_boolean_integer_fail_closed(self):
        unknown = document()
        unknown["authority"] = True
        with self.assertRaisesRegex(continuity.ContinuityContractError, "unknown field"):
            continuity.assess(unknown)
        malformed = document()
        malformed["review_fix"]["completed_rounds"] = True
        with self.assertRaises(continuity.ContinuityContractError):
            continuity.assess(malformed)
        for malformed_enum in ([], {}, None):
            with self.subTest(malformed_enum=malformed_enum):
                value = document()
                value["runtime"]["surface"] = malformed_enum
                with self.assertRaises(continuity.ContinuityContractError):
                    continuity.assess(value)

    def test_prior_lineage_and_bootstrap_cost_fail_closed(self):
        missing_digest = document()
        missing_digest["lineage"]["prior_rollover_id"] = "rollover-0"
        with self.assertRaisesRegex(continuity.ContinuityContractError, "present together"):
            continuity.assess(missing_digest)
        shifted = document()
        shifted["comparison"]["fresh_rollover"]["handoff_bootstrap_tokens"] = 2000
        with self.assertRaisesRegex(continuity.ContinuityContractError, "cannot exceed"):
            continuity.assess(shifted)

    def test_prior_lineage_requires_durable_matching_progress_evidence(self):
        value = document()
        value["lineage"].update(
            prior_rollover_id="rollover-0",
            prior_checkpoint_sha256="c" * 64,
            seen_rollovers=[
                {"rollover_id": "rollover-0", "checkpoint_sha256": "c" * 64}
            ],
        )
        self.assertEqual("prepare-fresh-rollover", continuity.assess(value)["decision"])
        mismatch = copy.deepcopy(value)
        mismatch["lineage"]["prior_checkpoint_sha256"] = "d" * 64
        with self.assertRaisesRegex(continuity.ContinuityContractError, "must match"):
            continuity.assess(mismatch)
        no_evidence = document()
        no_evidence["lineage"]["progress_evidence"] = []
        with self.assertRaisesRegex(continuity.ContinuityContractError, "must not be empty"):
            continuity.assess(no_evidence)

    def test_same_checkpoint_under_new_rollover_id_stops(self):
        value = document()
        digest = continuity.checkpoint_sha256(value["checkpoint"])
        value["lineage"]["seen_rollovers"] = [
            {"rollover_id": "rollover-0", "checkpoint_sha256": digest}
        ]
        result = continuity.assess(value)
        self.assertEqual("stop-for-human-gate", result["decision"])
        self.assertIn("checkpoint-reused-under-new-rollover-id", result["violations"])

    def test_loopctl_context_health_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "assessment.yaml"
            path.write_text(yaml.safe_dump(document(), sort_keys=False), encoding="utf-8")
            result = subprocess.run(
                [
                    str(ROOT / "scripts" / "project-python"),
                    str(ROOT / "skills" / "loop-engineering" / "scripts" / "loopctl.py"),
                    "context-health",
                    str(path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual("assessed", output["status"])
            self.assertFalse(output["result"]["runtime_action_performed"])
            self.assertFalse(output["result"]["task_created"])


if __name__ == "__main__":
    unittest.main()
