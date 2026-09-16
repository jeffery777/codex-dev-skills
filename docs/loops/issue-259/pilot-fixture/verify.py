"""Existing project checks; unittest output is the execution evidence."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import pipeline

class Checks(unittest.TestCase):
    def test_dry_run(self):
        with patch("pipeline.subprocess.run"):
            self.assertEqual({"validated": True}, pipeline.run("input.json", "unused", dry_run=True))

    def test_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "summary.txt").write_text("bundle complete\n")
            self.assertEqual({"summary.txt":"bundle complete\n"}, pipeline.export(root))

    def test_wrapper(self):
        def fake(argv, **kwargs):
            Path(argv[-1]).mkdir(parents=True, exist_ok=True)
            (Path(argv[-1]) / "summary.txt").write_text("bundle complete\n")
            return subprocess.CompletedProcess(argv, 0)
        with tempfile.TemporaryDirectory() as directory:
            pipeline.run("input.json", Path(directory) / "out", runner=fake)

if __name__ == "__main__":
    unittest.main(verbosity=2)
