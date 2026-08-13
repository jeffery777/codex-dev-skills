from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class MemoryOperationEvalTests(unittest.TestCase):
    def test_production_backed_suite_meets_exact_thresholds(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "eval-memory-operation.py")],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("passed", json.loads(result.stdout)["status"])


if __name__ == "__main__":
    unittest.main()
