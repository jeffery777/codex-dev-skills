from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class GitNexusIndexLifecycleEvalTests(unittest.TestCase):
    def test_production_backed_suite_meets_exact_thresholds(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "eval-gitnexus-index-lifecycle.py"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual("passed", document["status"])
        self.assertEqual(0, document["metrics"]["false_authority"])


if __name__ == "__main__":
    unittest.main()
