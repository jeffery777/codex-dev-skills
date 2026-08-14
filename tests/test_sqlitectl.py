from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "sqlitectl.py"
SCRIPT_DIR = CLI.parent
sys.path.insert(0, str(SCRIPT_DIR))

import memory_sqlite as adapter  # noqa: E402
from tests import test_memory_sqlite as fixtures  # noqa: E402


def write(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class SQLiteCtlTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args], cwd=ROOT, text=True,
            capture_output=True, check=False,
        )

    def test_probe_initialize_execute_query_receipt_and_integrity(self):
        probed = self.run_cli("probe")
        self.assertEqual(0, probed.returncode, probed.stderr)
        self.assertEqual("qualified", json.loads(probed.stdout)["status"])
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            state = fixtures.secure_state_root(parent)
            initialized = self.run_cli(
                "initialize", "--state-root", str(state), "--repository-root", str(ROOT)
            )
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            authority, candidate, eligibility, context = fixtures.qualified_bundle(state)
            values = {
                "authority.json": authority,
                "candidate.json": candidate,
                "eligibility.json": eligibility,
                "accepted-authority.json": context["accepted_authority_receipts"],
                "accepted-eligibility.json": context["accepted_eligibility_receipts"],
                "trusted-time.json": context["trusted_time_value"],
                "accepted-time.json": context["accepted_trusted_time_receipts"],
                "query.json": fixtures.query_request(),
            }
            for name, value in values.items():
                write(parent / name, value)
            common = (
                str(parent / "authority.json"), str(parent / "candidate.json"),
                str(parent / "eligibility.json"), "--accepted-authority-receipts",
                str(parent / "accepted-authority.json"), "--accepted-eligibility-receipts",
                str(parent / "accepted-eligibility.json"), "--trusted-time",
                str(parent / "trusted-time.json"), "--accepted-trusted-time-receipts",
                str(parent / "accepted-time.json"), "--state-root", str(state),
                "--repository-root", str(ROOT),
            )
            executed = self.run_cli("execute", *common)
            self.assertEqual(0, executed.returncode, executed.stderr)
            self.assertEqual("applied", json.loads(executed.stdout)["payload"]["outcome"])
            queried = self.run_cli(
                "query", str(parent / "query.json"), "--state-root", str(state),
                "--repository-root", str(ROOT),
            )
            self.assertEqual(0, queried.returncode, queried.stderr)
            self.assertEqual(["record-1"], [item["record_id"] for item in json.loads(queried.stdout)["records"]])
            receipt = self.run_cli("receipt", *common)
            self.assertEqual(0, receipt.returncode, receipt.stderr)
            self.assertEqual("applied", json.loads(receipt.stdout)["payload"]["outcome"])
            checked = self.run_cli(
                "integrity", "--state-root", str(state), "--repository-root", str(ROOT)
            )
            self.assertEqual(0, checked.returncode, checked.stderr)
            self.assertEqual("valid", json.loads(checked.stdout)["status"])

    def test_unsupported_route_and_rejection_are_generic(self):
        unsupported = self.run_cli("purge")
        self.assertEqual(2, unsupported.returncode)
        parsed = json.loads(unsupported.stderr)
        self.assertEqual("wrong-route", parsed["code"])
        self.assertEqual("memory sqlite operation was rejected", parsed["message"])
        self.assertNotIn("traceback", unsupported.stderr.lower())

        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            for name in ("qualification.json", "safety.json", "execution.json"):
                write(parent / name, {})
            malformed = self.run_cli(
                "qualification-receipt",
                str(parent / "qualification.json"),
                str(parent / "safety.json"),
                str(parent / "execution.json"),
            )
        self.assertEqual(2, malformed.returncode)
        parsed = json.loads(malformed.stderr)
        self.assertEqual("invalid-structure", parsed["code"])
        self.assertEqual("memory sqlite operation was rejected", parsed["message"])
        self.assertEqual("", malformed.stdout)
        self.assertNotIn("traceback", malformed.stderr.lower())


if __name__ == "__main__":
    unittest.main()
