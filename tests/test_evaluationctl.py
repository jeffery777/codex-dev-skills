from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests import test_candidate_evaluation as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "evaluationctl.py"


def write_json(directory: pathlib.Path, name: str, value: dict) -> pathlib.Path:
    path = directory / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def source_paths(directory: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path], pathlib.Path, pathlib.Path, dict, dict, list[dict], list[dict]]:
    records, evidence, proposal_set, selected = fixtures.source_bundle()
    input_doc = fixtures.evaluation_input(selected)
    record_paths = [
        write_json(directory, f"record-{index}.json", value)
        for index, value in enumerate(records)
    ]
    evidence_paths = [
        write_json(directory, f"evidence-{index}.json", value)
        for index, value in enumerate(evidence)
    ]
    proposal_path = write_json(directory, "proposal-set.json", proposal_set)
    input_path = write_json(directory, "evaluation-input.json", input_doc)
    return record_paths, evidence_paths, proposal_path, input_path, proposal_set, input_doc, records, evidence


def common(
    proposal_path: pathlib.Path,
    records: list[pathlib.Path],
    evidence: list[pathlib.Path],
) -> list[str]:
    return [
        "--proposal-set", str(proposal_path),
        *(item for path in records for item in ("--record", str(path))),
        *(item for path in evidence for item in ("--evidence", str(path))),
    ]


class EvaluationCtlTests(unittest.TestCase):
    def test_manual_ci_equivalent_inputs_produce_byte_identical_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            records, evidence, proposal_path, input_path, *_ = source_paths(directory)
            first = subprocess.run(
                [sys.executable, str(CLI), "evaluate", str(input_path), *common(proposal_path, records, evidence)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            second = subprocess.run(
                [sys.executable, str(CLI), "evaluate", str(input_path), *common(proposal_path, list(reversed(records)), list(reversed(evidence)))],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual("", first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual("qualified", json.loads(first.stdout)["comparison"]["status"])

    def test_evaluate_verify_packet_validate_pipeline_is_stdout_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            records, evidence, proposal_path, input_path, proposal_set, input_doc, raw_records, raw_evidence = source_paths(directory)
            result = fixtures.evaluation.build_evaluation_result(
                input_doc, proposal_set, raw_records, raw_evidence
            )
            verification = fixtures.evaluation.verify_evaluation_result(
                result, input_doc, proposal_set, raw_records, raw_evidence
            )
            packet = fixtures.evaluation.build_promotion_packet(
                result, verification, input_doc, proposal_set, raw_records, raw_evidence
            )
            result_path = write_json(directory, "result.json", result)
            verification_path = write_json(directory, "verification.json", verification)
            packet_path = write_json(directory, "packet.json", packet)
            commands = [
                ["verify", str(result_path), str(input_path)],
                ["packet", str(result_path), str(verification_path), str(input_path)],
                ["validate-packet", str(packet_path), str(result_path), str(verification_path), str(input_path)],
            ]
            before = sorted(path.name for path in directory.iterdir())
            for command in commands:
                with self.subTest(command=command[0]):
                    completed = subprocess.run(
                        [sys.executable, str(CLI), *command, *common(proposal_path, records, evidence)],
                        cwd=ROOT, text=True, capture_output=True, check=False,
                    )
                    self.assertEqual(0, completed.returncode, completed.stderr)
                    self.assertEqual("", completed.stderr)
                    self.assertTrue(completed.stdout.endswith("\n"))
            self.assertEqual(before, sorted(path.name for path in directory.iterdir()))

    def test_action_routes_fail_closed(self):
        for route in (
            "apply", "branch", "commit", "push", "draft-pr", "approve",
            "activate", "promote", "merge", "release", "deploy",
        ):
            with self.subTest(route=route):
                completed = subprocess.run(
                    [sys.executable, str(CLI), route], cwd=ROOT,
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(2, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertEqual("wrong-route", json.loads(completed.stderr)["code"])

    def test_parent_traversal_and_symlink_fail_before_input_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary)
            records, evidence, proposal_path, input_path, *_ = source_paths(directory)
            traversing = directory / ".." / directory.name / input_path.name
            completed = subprocess.run(
                [sys.executable, str(CLI), "evaluate", str(traversing), *common(proposal_path, records, evidence)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("", completed.stdout)
            self.assertEqual("file-boundary", json.loads(completed.stderr)["code"])

            symlink = directory / "linked-input.json"
            symlink.symlink_to(input_path)
            completed = subprocess.run(
                [sys.executable, str(CLI), "evaluate", str(symlink), *common(proposal_path, records, evidence)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(2, completed.returncode)
            self.assertEqual("", completed.stdout)
            self.assertEqual("file-boundary", json.loads(completed.stderr)["code"])


if __name__ == "__main__":
    unittest.main()
