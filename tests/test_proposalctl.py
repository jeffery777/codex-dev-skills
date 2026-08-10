from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests import test_improvement_lineage as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "proposalctl.py"


def write_json(directory: pathlib.Path, name: str, value: dict) -> pathlib.Path:
    path = directory / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def inputs(directory: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    records, evidence = fixtures.valid_lineage()
    record_paths = [
        write_json(directory, f"record-{index}.json", value)
        for index, value in enumerate(records)
    ]
    evidence_paths = [
        write_json(directory, f"evidence-{index}.json", value)
        for index, value in enumerate(evidence)
    ]
    return record_paths, evidence_paths


def argv_for(
    command: str,
    records: list[pathlib.Path],
    evidence: list[pathlib.Path],
) -> list[str]:
    return [
        sys.executable,
        str(CLI),
        command,
        *(item for path in records for item in ("--record", str(path))),
        *(item for path in evidence for item in ("--evidence", str(path))),
    ]


class ProposalCtlTests(unittest.TestCase):
    def test_generate_and_validate_are_deterministic_and_stdout_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            records, evidence = inputs(directory)
            before = sorted(path.name for path in directory.iterdir())
            first = subprocess.run(
                argv_for("generate", records, evidence),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            second = subprocess.run(
                argv_for("generate", list(reversed(records)), list(reversed(evidence))),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual("", first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(before, sorted(path.name for path in directory.iterdir()))

            manifest = write_json(directory, "proposal.json", json.loads(first.stdout))
            validate_argv = argv_for("validate", records, evidence)
            validate_argv.insert(3, str(manifest))
            validated = subprocess.run(
                validate_argv,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, validated.returncode, validated.stderr)
            receipt = json.loads(validated.stdout)
            self.assertEqual("valid", receipt["status"])
            self.assertEqual(fixtures.AUTHORITY, receipt["authority_invariants"])

    def test_wrong_route_is_generic_structured_rejection(self):
        result = subprocess.run(
            [sys.executable, str(CLI), "apply"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("wrong-route", json.loads(result.stderr)["code"])
        self.assertNotIn("usage:", result.stderr)

    def test_symlink_and_count_bounds_fail_before_unsafe_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            records, evidence = inputs(directory)
            link = directory / "record-link.json"
            link.symlink_to(records[0])
            symlink_result = subprocess.run(
                argv_for("generate", [link], evidence),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, symlink_result.returncode)
            self.assertEqual("file-boundary", json.loads(symlink_result.stderr)["code"])

            missing = directory / "missing.json"
            excessive = subprocess.run(
                argv_for(
                    "generate",
                    records,
                    [missing] * (fixtures.evidence.MAX_SET_DOCUMENTS + 1),
                ),
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, excessive.returncode)
            self.assertEqual("document-count", json.loads(excessive.stderr)["code"])

            traversal = subprocess.run(
                argv_for("generate", [pathlib.Path("..") / records[0].name], evidence),
                cwd=directory,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(2, traversal.returncode)
            self.assertEqual("file-boundary", json.loads(traversal.stderr)["code"])


if __name__ == "__main__":
    unittest.main()
