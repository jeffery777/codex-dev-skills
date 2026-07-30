from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-improvement-lineage.py"
SPEC = importlib.util.spec_from_file_location("eval_improvement_lineage", SCRIPT)
evaluation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evaluation)


class ImprovementLineageEvalTests(unittest.TestCase):
    def test_checked_in_suite_meets_exact_thresholds(self):
        result = evaluation.evaluate_suite()
        self.assertEqual("passed", result["status"])
        self.assertEqual(6, result["positive_cases"])
        self.assertEqual(23, result["negative_cases"])
        self.assertEqual(0, result["false_authority_claims"])
        self.assertEqual(0, result["projection_mismatches"])

    def test_cli_is_deterministic(self):
        first = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        second = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, first.returncode, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual("", first.stderr)

    def test_suite_loader_rejects_symlinks_before_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = pathlib.Path(temporary) / "suite.json"
            link.symlink_to(ROOT / "evals" / "improvement-lineage" / "suite.json")
            with self.assertRaises(evaluation.EvalConfigurationError):
                evaluation.load_suite(link)


if __name__ == "__main__":
    unittest.main()
