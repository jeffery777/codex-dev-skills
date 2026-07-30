from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests import test_operational_evidence as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "evidencectl.py"


def run_cli(command: str, documents: list[dict | str]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        paths = []
        for index, document in enumerate(documents):
            path = pathlib.Path(directory) / f"document-{index}.json"
            if isinstance(document, str):
                path.write_text(document, encoding="utf-8")
            else:
                path.write_text(json.dumps(document), encoding="utf-8")
            paths.append(str(path))
        return subprocess.run(
            [sys.executable, str(CLI), command, *paths],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


class EvidenceCtlTests(unittest.TestCase):
    def test_validate_emits_bounded_non_authoritative_result(self):
        document = fixtures.valid_documents()[0]
        result = run_cli("validate", [document])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("valid", output["status"])
        self.assertEqual(fixtures.AUTHORITY, output["authority_invariants"])
        self.assertNotIn("payload", output)

    def test_validate_set_succeeds_independent_of_input_order(self):
        result = run_cli("validate-set", list(reversed(fixtures.valid_documents())))
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("valid", output["status"])
        self.assertEqual(5, output["document_count"])
        self.assertEqual(fixtures.AUTHORITY, output["authority_invariants"])

    def test_duplicate_key_rejection_is_structured_and_non_echoing(self):
        secret = "do-not-echo-example"
        document = (
            '{"kind":"run-receipt","kind":"failure-summary",'
            f'"value":"{secret}"}}'
        )
        result = run_cli("validate", [document])
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        output = json.loads(result.stderr)
        self.assertEqual("rejected", output["status"])
        self.assertEqual("duplicate-key", output["code"])
        self.assertNotIn(secret, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_private_path_and_raw_log_rejections_do_not_echo_input(self):
        for prohibited in (
            "/home/example/private.txt",
            "ghp_" + "A" * 36,
            "2026-07-29T02:00:00Z ERROR unsafe-example",
        ):
            document = fixtures.valid_documents()[1]
            document["payload"]["task_id"] = prohibited
            result = run_cli("validate", [document])
            with self.subTest(value=prohibited):
                self.assertEqual(1, result.returncode)
                self.assertEqual("", result.stdout)
                output = json.loads(result.stderr)
                self.assertEqual("privacy-violation", output["code"])
                self.assertNotIn(prohibited, result.stderr)
                self.assertNotIn(prohibited[-16:], result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_extreme_integer_is_structured_invalid_json_without_traceback(self):
        result = run_cli("validate", ['{"value":' + "9" * 10_000 + "}"])
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        output = json.loads(result.stderr)
        self.assertEqual("invalid-json", output["code"])
        self.assertNotIn("Traceback", result.stderr)

    def test_timestamp_normalization_overflow_is_structured_without_traceback(self):
        for timestamp in (
            "9999-12-31T23:59:59-23:59",
            "0001-01-01T00:00:00+23:59",
        ):
            document = fixtures.valid_documents()[0]
            document["observed_at"] = timestamp
            document = fixtures.reseal(document)
            result = run_cli("validate", [document])
            with self.subTest(timestamp=timestamp):
                self.assertEqual(1, result.returncode)
                self.assertEqual("", result.stdout)
                output = json.loads(result.stderr)
                self.assertEqual("invalid-structure", output["code"])
                self.assertNotIn(timestamp, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
