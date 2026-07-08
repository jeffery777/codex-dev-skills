import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-loop-ledger.py"

spec = importlib.util.spec_from_file_location("validate_loop_ledger", SCRIPT)
validate_loop_ledger = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_loop_ledger)


class ValidateLoopLedgerTests(unittest.TestCase):
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
        self.assertTrue(any("requires claim:" in error for error in errors))
        self.assertTrue(any("requires lease_expires_at:" in error for error in errors))

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
