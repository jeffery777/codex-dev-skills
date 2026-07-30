from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests import test_improvement_lineage as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "improvementctl.py"


def write_json(directory: pathlib.Path, name: str, value: dict) -> pathlib.Path:
    path = directory / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def run_cli(command: str, *, tamper: bool = False) -> subprocess.CompletedProcess[str]:
    records, evidence = fixtures.valid_lineage()
    if tamper:
        records[0]["authority_invariants"]["promotion_authorized"] = True
        records[0] = fixtures.lineage.seal_record(records[0])
    with tempfile.TemporaryDirectory() as temporary:
        directory = pathlib.Path(temporary)
        record_paths = [
            write_json(directory, f"record-{index}.json", value)
            for index, value in enumerate(records)
        ]
        evidence_paths = [
            write_json(directory, f"evidence-{index}.json", value)
            for index, value in enumerate(evidence)
        ]
        argv = [
            sys.executable,
            str(CLI),
            command,
            *(str(path) for path in record_paths),
            "--evidence",
            *(str(path) for path in evidence_paths),
        ]
        return subprocess.run(
            argv,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


class ImprovementCtlTests(unittest.TestCase):
    def test_validate_set_emits_bounded_non_authoritative_receipt(self):
        result = run_cli("validate-set")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual("valid", output["status"])
        self.assertEqual(fixtures.AUTHORITY, output["authority_invariants"])
        self.assertNotIn("ordered_records", output)

    def test_projection_commands_are_deterministic(self):
        first = run_cli("project-human")
        second = run_cli("project-human")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        graph = run_cli("project-graph")
        self.assertEqual(0, graph.returncode, graph.stderr)
        self.assertEqual("typed-graph-projection-manifest", json.loads(graph.stdout)["kind"])

    def test_authority_violation_is_structured_without_traceback(self):
        result = run_cli("validate-set", tamper=True)
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        output = json.loads(result.stderr)
        self.assertEqual("rejected", output["status"])
        self.assertEqual("authority-violation", output["code"])
        self.assertNotIn("Traceback", result.stderr)

    def test_excessive_evidence_inventory_is_rejected_before_file_reads(self):
        missing = ROOT / "does-not-exist.json"
        result = subprocess.run(
            [
                sys.executable,
                str(CLI),
                "validate-set",
                str(missing),
                "--evidence",
                *(
                    [str(missing)]
                    * (fixtures.evidence.MAX_SET_DOCUMENTS + 1)
                ),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("document-count", json.loads(result.stderr)["code"])


if __name__ == "__main__":
    unittest.main()
