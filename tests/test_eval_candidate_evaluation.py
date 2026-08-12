from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-candidate-evaluation.py"


def load_eval_module():
    spec = importlib.util.spec_from_file_location("candidate_evaluation_eval", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CandidateEvaluationEvalTests(unittest.TestCase):
    def test_eval_matches_all_frozen_thresholds(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("", completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual("passed", result["status"])
        self.assertEqual(result["expected"], result["metrics"])
        self.assertEqual(26, len(result["outcomes"]))

    def test_valid_context_authority_mutation_fails_eval(self):
        module = load_eval_module()
        original = module.evaluation.build_evaluation_result

        def mutate(*args, **kwargs):
            result = original(*args, **kwargs)
            if result["context"]["mode"] == "synthetic-advisory":
                result = copy.deepcopy(result)
                result["authority_invariants"]["used_as_authorization"] = True
                return module.evaluation.seal_evaluation_result(result)
            return result

        stdout = io.StringIO()
        with mock.patch.object(
            module.evaluation, "build_evaluation_result", side_effect=mutate
        ), contextlib.redirect_stdout(stdout):
            returncode = module.main()
        result = json.loads(stdout.getvalue())
        self.assertEqual(1, returncode)
        self.assertEqual("failed", result["status"])
        self.assertGreater(result["metrics"]["false_authority"], 0)

    def test_closed_action_surface_is_required_for_zero_metrics(self):
        module = load_eval_module()
        self.assertTrue(module.production_action_surface_is_closed())
        stdout = io.StringIO()
        with mock.patch.object(
            module, "production_action_surface_is_closed", return_value=False
        ), contextlib.redirect_stdout(stdout):
            returncode = module.main()
        result = json.loads(stdout.getvalue())
        self.assertEqual(1, returncode)
        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["metrics"]["unauthorized_action"])
        self.assertEqual(1, result["metrics"]["external_write"])
        self.assertEqual(1, result["metrics"]["promotion"])

    def test_action_surface_scanner_rejects_common_dynamic_and_path_mutations(self):
        module = load_eval_module()
        original_parse = module.ast.parse
        cases = (
            'import importlib\nimportlib.import_module("subprocess").run(["true"])',
            'import pathlib\npathlib.Path("x").symlink_to("y")',
            'import pathlib\npathlib.Path("x").hardlink_to("y")',
            'import os\nos.posix_spawn("/usr/bin/true", ["true"], {})',
            'open("x", "w").write("value")',
        )
        for source in cases:
            with self.subTest(source=source), mock.patch.object(
                module.ast, "parse", side_effect=lambda *_args, **_kwargs: original_parse(source)
            ):
                self.assertFalse(module.production_action_surface_is_closed())


if __name__ == "__main__":
    unittest.main()
