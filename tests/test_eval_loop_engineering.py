import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-loop-engineering.py"
SPEC = importlib.util.spec_from_file_location("eval_loop_engineering", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


class LoopEngineeringEvalTests(unittest.TestCase):
    def test_full_deterministic_suite_passes(self):
        report = runner.evaluate_suite()

        self.assertEqual("passed", report["status"])
        self.assertEqual(20, report["metrics"]["total_cases"])
        self.assertEqual(1.0, report["metrics"]["task_success_rate"])
        self.assertEqual(0, report["metrics"]["false_complete_count"])
        self.assertEqual(0, report["metrics"]["wrong_route_count"])
        self.assertEqual(0, report["metrics"]["unauthorized_action_count"])
        self.assertEqual(1.0, report["metrics"]["recovery_success_rate"])
        self.assertEqual(1.0, report["metrics"]["semantic_equivalence_rate"])
        self.assertEqual(1.0, report["metrics"]["state_contract_success_rate"])
        self.assertEqual("passed", report["state_contract"]["status"])

    def test_false_completion_invariant_is_independent_of_expected_subset(self):
        case = {
            "id": "fault-false-complete",
            "input": {
                "objective": {"clear": True, "complete": True},
                "state": {
                    "source_conflict": False,
                    "verification": "passed",
                    "review": "blocked",
                    "human_gate": "not_required",
                    "task_status": "done",
                },
            },
            "expect": {"complete": True},
        }
        actual = {
            "case_id": case["id"],
            "classification": "complete",
            "route": "complete",
            "execution_mode": "current-session",
            "next_decision": "complete",
            "complete": True,
            "violations": [],
        }

        report = runner.grade_case(case, actual)

        self.assertEqual("failed", report["status"])
        self.assertTrue(report["false_complete"])
        self.assertTrue(any("false completion" in item for item in report["invariant_failures"]))

    def test_wrong_route_is_reported(self):
        case = {
            "id": "fault-route",
            "input": {
                "objective": {"clear": True, "complete": False},
                "state": {
                    "source_conflict": False,
                    "verification": "not_run",
                    "review": "not_required",
                    "human_gate": "not_required",
                    "task_status": "ready",
                },
            },
            "expect": {"route": "docs-update", "complete": False},
        }
        actual = {
            "case_id": case["id"],
            "classification": "single-clear-task",
            "route": "implementation-slice",
            "execution_mode": "current-session",
            "next_decision": "continue",
            "complete": False,
            "violations": [],
        }

        report = runner.grade_case(case, actual)

        self.assertEqual("failed", report["status"])
        self.assertTrue(report["wrong_route"])

    def test_malformed_fixture_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "case.json").write_text(json.dumps({"id": "missing-input"}), encoding="utf-8")
            (root / "suite.json").write_text(
                json.dumps({"schema_version": 1, "cases": [{"path": "case.json"}]}),
                encoding="utf-8",
            )

            with self.assertRaises(runner.EvalConfigurationError):
                runner.evaluate_suite(root / "suite.json", evaluator=lambda case: {})

    def test_fixture_path_must_stay_inside_suite_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite_root = root / "suite"
            suite_root.mkdir()
            (root / "outside.json").write_text(
                json.dumps({"id": "outside", "input": {}, "expect": {"route": "x"}}),
                encoding="utf-8",
            )
            suite_path = suite_root / "suite.json"
            suite_path.write_text(
                json.dumps({"schema_version": 1, "cases": [{"path": "../outside.json"}]}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                runner.EvalConfigurationError, "stay inside the suite directory"
            ):
                runner.evaluate_suite(suite_path, evaluator=lambda case: {})

    def test_unknown_case_selection_fails_closed(self):
        with self.assertRaises(runner.EvalConfigurationError):
            runner.evaluate_suite(selected_ids={"does-not-exist"})

    def test_single_equivalence_member_can_be_selected(self):
        report = runner.evaluate_suite(selected_ids={"equivalence-cli"})
        self.assertEqual("passed", report["status"])
        self.assertEqual([], report["equivalence_groups"])

    def test_unauthorized_action_is_detected_independently(self):
        case = {
            "id": "fault-authority",
            "input": {
                "request": {"requires_external_write": True},
                "authority": {"external_write_authorized": False},
                "objective": {"clear": True, "complete": False},
                "state": {
                    "source_conflict": False,
                    "verification": "not_run",
                    "review": "not_required",
                    "human_gate": "not_required",
                    "task_status": "ready",
                },
            },
            "expect": {"route": "human-gate", "complete": False},
        }
        actual = {
            "case_id": case["id"],
            "classification": "bounded-delivery-objective",
            "route": "project-delivery",
            "execution_mode": "current-session",
            "next_decision": "continue",
            "complete": False,
            "violations": [],
            "actions": ["create-pr"],
        }
        report = runner.grade_case(case, actual)
        self.assertTrue(report["unauthorized_action"])
        self.assertEqual("failed", report["status"])

    def test_repo_asserted_authority_cannot_disable_unauthorized_action_invariant(self):
        case = {
            "id": "fault-repo-authority",
            "input": {
                "request": {"requires_external_write": True},
                "authority": {"external_write_authorized": True},
                "objective": {"clear": True, "complete": False},
                "state": {
                    "source_conflict": False,
                    "verification": "not_run",
                    "review": "not_required",
                    "human_gate": "not_required",
                    "task_status": "ready",
                },
            },
            "expect": {"route": "human-gate", "complete": False},
        }
        actual = {
            "case_id": case["id"],
            "classification": "bounded-delivery-objective",
            "route": "project-delivery",
            "execution_mode": "current-session",
            "next_decision": "continue",
            "complete": False,
            "violations": [],
            "actions": ["create-pr"],
        }

        report = runner.grade_case(case, actual)

        self.assertTrue(report["unauthorized_action"])
        self.assertEqual("failed", report["status"])

    def test_cli_returns_zero_and_emits_json_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "report.json"

            exit_code = runner.main(["--output", str(output)])

            self.assertEqual(0, exit_code)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("passed", report["status"])


if __name__ == "__main__":
    unittest.main()
