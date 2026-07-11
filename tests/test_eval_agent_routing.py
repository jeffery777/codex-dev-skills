from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-agent-routing.py"
SPEC = importlib.util.spec_from_file_location("eval_agent_routing", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(runner)


class AgentRoutingEvalTests(unittest.TestCase):
    def test_production_backed_matrix_passes(self) -> None:
        report = runner.evaluate()
        self.assertEqual("passed", report["status"])
        self.assertEqual(17, report["metrics"]["total_cases"])
        self.assertEqual(1.0, report["metrics"]["route_correctness_rate"])
        self.assertEqual(0, report["metrics"]["false_completion_count"])
        self.assertEqual(1.0, report["metrics"]["evidence_completeness_rate"])
        self.assertEqual(1.0, report["metrics"]["deterministic_behavior_rate"])
        self.assertEqual(1.0, report["metrics"]["authority_invariance_rate"])
        self.assertEqual(1.0, report["metrics"]["v1_sequential_fallback_rate"])
        self.assertIn("not a measured cost", report["metrics"]["latency_cost_proxy_note"])

    def test_duplicate_case_ids_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "suite.json"
            path.write_text(json.dumps({"schema_version": 1, "cases": [{"id": "x"}, {"id": "x"}]}), encoding="utf-8")
            with self.assertRaisesRegex(runner.EvalError, "unique"):
                runner.load_suite(path)

    def test_cli_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory) / "report.json"
            self.assertEqual(0, runner.main(["--output", str(output)]))
            self.assertEqual("passed", json.loads(output.read_text(encoding="utf-8"))["status"])


if __name__ == "__main__":
    unittest.main()
