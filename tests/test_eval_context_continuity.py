import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-context-continuity.py"
SPEC = importlib.util.spec_from_file_location("eval_context_continuity", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


class ContextContinuityEvalTests(unittest.TestCase):
    def test_suite_covers_negative_paths_and_end_to_end_comparison(self):
        report = runner.evaluate()
        self.assertEqual("passed", report["status"])
        self.assertEqual(9, report["metrics"]["total_cases"])
        self.assertEqual(1.0, report["metrics"]["task_success_rate"])
        self.assertTrue(report["metrics"]["comparison_qualified"])
        self.assertFalse(report["release_evidence_qualified"])
        self.assertEqual(
            "synthetic-contract-fixture",
            report["measurement_provenance"]["evidence_kind"],
        )
        self.assertLess(
            report["metrics"]["fresh_rollover_objective_total_tokens_including_bootstrap"],
            report["metrics"]["same_context_objective_total_tokens"],
        )
        self.assertGreaterEqual(
            report["metrics"]["fresh_rollover_quality_score"],
            report["metrics"]["same_context_quality_score"],
        )


if __name__ == "__main__":
    unittest.main()
