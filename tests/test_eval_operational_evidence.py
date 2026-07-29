from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-operational-evidence.py"
SPEC = importlib.util.spec_from_file_location("eval_operational_evidence", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


class OperationalEvidenceEvalTests(unittest.TestCase):
    def test_production_backed_suite_passes_exact_thresholds(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual("passed", report["status"])
        self.assertEqual(12, report["metrics"]["total_cases"])
        self.assertEqual(1.0, report["metrics"]["decision_correctness_rate"])
        self.assertEqual(
            0, report["metrics"]["false_authority_or_completion_count"]
        )
        self.assertEqual(1.0, report["metrics"]["privacy_safe_rejection_rate"])

    def test_single_case_selection_remains_fail_closed(self):
        report = runner.evaluate_suite(selected_id="tampered-digest")
        self.assertEqual("passed", report["status"])
        self.assertEqual(1, report["metrics"]["total_cases"])
        with self.assertRaises(runner.EvalConfigurationError):
            runner.evaluate_suite(selected_id="missing-case")

    def test_reduced_weakened_or_malformed_suite_is_rejected(self):
        source = ROOT / "evals" / "operational-evidence" / "suite.json"
        suite = json.loads(source.read_text(encoding="utf-8"))
        variants = []
        reduced = json.loads(json.dumps(suite))
        reduced["cases"] = reduced["cases"][:-1]
        variants.append(reduced)
        weakened = json.loads(json.dumps(suite))
        weakened["thresholds"]["decision_correctness_rate"] = 0.5
        variants.append(weakened)
        altered = json.loads(json.dumps(suite))
        altered["cases"][0]["expected_status"] = "rejected"
        variants.append(altered)
        malformed = json.loads(json.dumps(suite))
        malformed["cases"][0]["extra"] = True
        variants.append(malformed)
        for index, variant in enumerate(variants):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                path = root / "suite.json"
                path.write_text(json.dumps(variant), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--suite", str(path)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(2, result.returncode)
                self.assertEqual("error", json.loads(result.stdout)["status"])

    def test_duplicate_suite_keys_fail_closed_before_policy_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "suite.json"
            path.write_text(
                '{"schema_version":1,"schema_version":1,'
                '"thresholds":{},"cases":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                runner.EvalConfigurationError, "duplicate object key"
            ):
                runner.load_suite(path)

    def test_deeply_nested_suite_returns_bounded_cli_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "suite.json"
            path.write_text(
                "[" * 10_000 + "0" + "]" * 10_000,
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--suite", str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual("error", output["status"])
            self.assertEqual(
                "suite must be readable UTF-8 JSON",
                output["error"],
            )

    def test_suite_and_fixture_reads_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite = root / "suite.json"
            suite.write_bytes(b" " * (runner.MAX_SUITE_BYTES + 1))
            with self.assertRaisesRegex(
                runner.EvalConfigurationError, "suite exceeds"
            ):
                runner.load_suite(suite)

            fixture_root = root / "fixtures"
            fixture_root.mkdir()
            fixture = fixture_root / "oversized.json"
            fixture.write_bytes(b"x" * (runner.MAX_FIXTURE_BYTES + 1))
            case = {
                "id": "oversized",
                "fixture": "fixtures/oversized.json",
                "mode": "document",
                "expected_status": "rejected",
                "expected_code": "document-size",
            }
            with self.assertRaisesRegex(
                runner.EvalConfigurationError, "fixture exceeds"
            ):
                runner.evaluate(case, suite)

    def test_privacy_oracle_requires_the_exact_generic_message(self):
        self.assertTrue(
            runner._is_safe_rejection(
                "synthetic-secret",
                "rejected",
                "document contains prohibited sensitive data",
            )
        )
        self.assertFalse(
            runner._is_safe_rejection(
                "synthetic-secret",
                "rejected",
                "rejected token: synthetic-example-only",
            )
        )

    def test_fixture_paths_cannot_escape_suite_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite_root = root / "suite"
            suite_root.mkdir()
            outside = root / "outside.json"
            outside.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(
                runner.EvalConfigurationError, "stay inside"
            ):
                runner._fixture_path(suite_root / "suite.json", "../outside.json")

    def test_fixture_symlink_loop_returns_bounded_cli_error(self):
        source = ROOT / "evals" / "operational-evidence" / "suite.json"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite = root / "suite.json"
            suite.write_bytes(source.read_bytes())
            fixtures = root / "fixtures"
            fixtures.mkdir()
            loop = fixtures / "positive-valid-set.json"
            loop.symlink_to(loop.name)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--suite", str(suite)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("", result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual("error", output["status"])
            self.assertEqual(
                "fixture must be a regular non-symlink file",
                output["error"],
            )

    def test_fixture_symlink_to_internal_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite = root / "suite.json"
            suite.write_text("{}")
            fixtures = root / "fixtures"
            fixtures.mkdir()
            target = fixtures / "target.json"
            target.write_text("{}")
            link = fixtures / "link.json"
            link.symlink_to(target.name)
            case = {
                "id": "link",
                "fixture": "fixtures/link.json",
                "mode": "document",
                "expected_status": "rejected",
                "expected_code": "file-boundary",
            }
            with self.assertRaisesRegex(
                runner.EvalConfigurationError,
                "regular non-symlink",
            ):
                runner.evaluate(case, suite)

    def test_fixture_symlink_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite = root / "suite.json"
            suite.write_text("{}")
            real_fixtures = root / "real-fixtures"
            real_fixtures.mkdir()
            (root / "fixtures").symlink_to(real_fixtures.name)
            with self.assertRaisesRegex(
                runner.EvalConfigurationError,
                "parent must be a real directory",
            ):
                runner._fixture_path(suite, "fixtures/document.json")

    def test_evaluation_uses_one_fixture_byte_snapshot(self):
        fixture = (
            ROOT
            / "evals"
            / "operational-evidence"
            / "fixtures"
            / "positive-run-receipt.json"
        )
        raw = fixture.read_bytes()
        case = {
            "id": "valid-run-receipt",
            "fixture": "fixtures/positive-run-receipt.json",
            "mode": "document",
            "expected_status": "valid",
            "expected_code": None,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            suite = root / "suite.json"
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "positive-run-receipt.json").write_text("{}")
            with mock.patch.object(
                runner,
                "_read_bounded_bytes",
                return_value=raw,
            ) as read:
                result = runner.evaluate(case, suite)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), result["fixture_sha256"])
        self.assertTrue(result["correct"])
        self.assertEqual(1, read.call_count)


if __name__ == "__main__":
    unittest.main()
