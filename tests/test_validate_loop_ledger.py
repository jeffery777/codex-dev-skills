import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-loop-ledger.py"

spec = importlib.util.spec_from_file_location("validate_loop_ledger", SCRIPT)
validate_loop_ledger = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_loop_ledger)


class ValidateLoopLedgerTests(unittest.TestCase):
    def test_project_validator_rejects_contract_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / "repo"
            root.mkdir()
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            external = base / "external.yaml"
            external.write_text("project: {}\n", encoding="utf-8")
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": str(external),
                    "task_manifest": str(external),
                    "source_revision": {},
                }
            }
            with (
                mock.patch.object(validate_loop_ledger, "ROOT", root),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml,
                    "load_yaml",
                    return_value=document,
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml,
                    "validate_ledger",
                    return_value=[],
                ),
            ):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(any("task manifest must stay within" in error for error in errors))
            self.assertTrue(any("loop spec must stay within" in error for error in errors))

    def test_project_validator_rejects_valid_v1_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(
                """ledger:\n  schema_version: 1\n  objective_id: test\n  objective: test\n  source_revision:\n    branch: branch\n    head_sha: abc\n    updated_at: 2026-07-10T00:00:00Z\ntasks:\n  - id: T1\n    status: ready\n    dependencies: []\n    evidence: {}\n""",
                encoding="utf-8",
            )
            with mock.patch.object(validate_loop_ledger, "ROOT", root):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(any("requires schema_version 2" in error for error in errors))

    def test_quoted_done_status_requires_passed_verification(self):
        block = """
  - id: "T1"
    status: "done"
    evidence:
      verification:
        status: "not_run"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires passed verification" in error for error in errors))

    def test_done_status_accepts_task_scoped_passed_verification(self):
        block = """
  - id: "T1"
    status: "done"
    evidence:
      verification:
        status: "passed"
      review:
        status: "not_required"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertEqual([], errors)

    def test_claimed_status_requires_claim_and_lease(self):
        block = """
  - id: "T1"
    status: "claimed"
    owner:
      type: "worker"
      id: "worker-1"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires owner and lease fields" in error for error in errors))

    def test_blocked_status_requires_non_placeholder_reason(self):
        block = """
  - id: "T1"
    status: "blocked"
    blocker:
      reason: "<reason-or-empty>"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires blocker reason" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
