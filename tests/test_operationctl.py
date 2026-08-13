from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "operationctl.py"
SCRIPT_DIR = CLI.parent
sys.path.insert(0, str(SCRIPT_DIR))

from tests import test_memory_operation as fixtures  # noqa: E402


def write(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class OperationCtlTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args], cwd=ROOT, text=True,
            capture_output=True, check=False,
        )

    def test_validate_authorize_and_receipt_pipeline_is_stdout_only(self):
        authority, candidate, eligibility, request = fixtures.bundle()
        applied = fixtures.receipt(request)
        clock = fixtures.trusted_time()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            values = {
                "authority.json": authority, "candidate.json": candidate,
                "eligibility.json": eligibility,
                "accepted-authority.json": {"receipt_digests": [authority["payload"]["authority_receipt_digest"]]},
                "accepted-eligibility.json": {"receipt_digests": [eligibility["receipt_digest"]]},
                "trusted-time.json": clock,
                "accepted-time.json": {"receipt_digests": [clock["receipt_digest"]]},
                "request.json": request, "receipt.json": applied,
            }
            for name, value in values.items():
                write(root / name, value)
            validated = self.run_cli("validate", str(root / "authority.json"))
            self.assertEqual(0, validated.returncode, validated.stderr)
            self.assertEqual("valid", json.loads(validated.stdout)["status"])
            authorized = self.run_cli(
                "authorize", str(root / "authority.json"), str(root / "candidate.json"),
                str(root / "eligibility.json"), "--accepted-authority-receipts",
                str(root / "accepted-authority.json"), "--accepted-eligibility-receipts",
                str(root / "accepted-eligibility.json"), "--trusted-time", str(root / "trusted-time.json"),
                "--accepted-trusted-time-receipts", str(root / "accepted-time.json"),
            )
            self.assertEqual(0, authorized.returncode, authorized.stderr)
            self.assertEqual(request, json.loads(authorized.stdout))
            receipt_result = self.run_cli(
                "validate-receipt", str(root / "receipt.json"), str(root / "request.json"),
                "--authority", str(root / "authority.json"), "--mutation-candidate", str(root / "candidate.json"),
                "--eligibility-receipt", str(root / "eligibility.json"), "--accepted-authority-receipts",
                str(root / "accepted-authority.json"), "--accepted-eligibility-receipts", str(root / "accepted-eligibility.json"),
                "--trusted-time", str(root / "trusted-time.json"), "--accepted-trusted-time-receipts", str(root / "accepted-time.json"),
            )
            self.assertEqual(0, receipt_result.returncode, receipt_result.stderr)
            self.assertEqual("applied", json.loads(receipt_result.stdout)["outcome"])

    def test_action_route_rejects_generically(self):
        result = self.run_cli("execute")
        self.assertEqual(2, result.returncode)
        parsed = json.loads(result.stderr)
        self.assertEqual("wrong-route", parsed["code"])
        self.assertNotIn("traceback", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
