from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class MemorySQLiteEvalTests(unittest.TestCase):
    def test_production_backed_suite_meets_exact_thresholds(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "eval-memory-sqlite.py")],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertEqual("passed", parsed["status"])
        self.assertEqual(18, parsed["metrics"]["cases"])


if __name__ == "__main__":
    unittest.main()
