from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-improvement-proposal.py"
SPEC = importlib.util.spec_from_file_location("eval_improvement_proposal", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ImprovementProposalEvalTests(unittest.TestCase):
    def test_production_backed_suite_meets_exact_thresholds(self):
        result = module.evaluate_suite()
        self.assertTrue(result["passed"])
        self.assertEqual(module.load_suite()["expected"], result["metrics"])
        self.assertTrue(all(item["passed"] for item in result["observations"]))

    def test_weakened_expected_threshold_fails_configuration(self):
        suite = module.load_suite()
        weakened = {
            key: copy.deepcopy(value)
            for key, value in suite.items()
            if key not in {"cases", "suite_path"}
        }
        weakened["positive_fixture"] = str(
            ROOT
            / "evals"
            / "improvement-lineage"
            / "fixtures"
            / "positive-valid-lineage.json"
        )
        weakened["negative_cases"] = str(
            ROOT / "evals" / "improvement-proposal" / "negative-cases.json"
        )
        weakened["duplicate_key_fixture"] = str(
            ROOT
            / "evals"
            / "improvement-proposal"
            / "fixtures"
            / "negative-duplicate-key.json"
        )
        weakened["expected"]["decision_accuracy"] = 0.9
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "suite.json"
            path.write_text(json.dumps(weakened), encoding="utf-8")
            with self.assertRaises(module.EvalConfigurationError):
                module.load_suite(path)

    def test_suite_loader_rejects_symlink_before_reading(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = pathlib.Path(temporary) / "suite-link.json"
            link.symlink_to(module.SUITE)
            with self.assertRaises(module.EvalConfigurationError):
                module.load_suite(link)


if __name__ == "__main__":
    unittest.main()
