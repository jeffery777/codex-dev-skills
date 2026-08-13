from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "qualificationctl.py"
SCRIPT_DIR = CLI.parent
sys.path.insert(0, str(SCRIPT_DIR))

import memory_qualification as qualification  # noqa: E402
from tests import test_memory_qualification as fixtures  # noqa: E402


def write(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class QualificationCtlTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args], cwd=ROOT, text=True,
            capture_output=True, check=False,
        )

    def test_memory_off_evaluate_and_validate_are_deterministic(self):
        result, verified = fixtures.v3b_pair()
        source = fixtures.qualification_input(result, verified, with_on=False)
        expected = qualification.build_qualification_result(
            source, result, verified,
            accepted_v3b_receipts=fixtures.accepted(result, verified),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            values = {
                "input.json": source, "result.json": result, "verification.json": verified,
                "accepted.json": fixtures.accepted(result, verified), "qualified.json": expected,
            }
            for name, value in values.items():
                write(root / name, value)
            evaluated = self.run_cli(
                "evaluate", str(root / "input.json"), str(root / "result.json"),
                str(root / "verification.json"), "--accepted-v3b-receipts", str(root / "accepted.json"),
            )
            self.assertEqual(0, evaluated.returncode, evaluated.stderr)
            self.assertEqual(expected, json.loads(evaluated.stdout))
            validated = self.run_cli(
                "validate-result", str(root / "qualified.json"), str(root / "input.json"),
                str(root / "result.json"), str(root / "verification.json"),
                "--accepted-v3b-receipts", str(root / "accepted.json"),
            )
            self.assertEqual(0, validated.returncode, validated.stderr)
            self.assertEqual("memory-on-unavailable", json.loads(validated.stdout)["qualification_status"])

    def test_action_route_rejects_generically(self):
        result = self.run_cli("promote")
        self.assertEqual(2, result.returncode)
        self.assertEqual("wrong-route", json.loads(result.stderr)["code"])


if __name__ == "__main__":
    unittest.main()
