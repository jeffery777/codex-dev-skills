from __future__ import annotations

import json
import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RuntimeCompatibilityReleaseDocsTests(unittest.TestCase):
    def test_v0161_candidate_metadata_and_traceability_align(self) -> None:
        self.assertEqual("0.16.1", yaml.safe_load(read("catalog.yaml"))["version"])
        self.assertIn('VERSION="0.16.1"', read("install.sh"))

        notes = read("docs/release-notes-v0.16.1.md")
        for expected in (
            "# Release Notes: v0.16.1",
            "Issue #159",
            "10-second default",
            "1..3600",
            "probe-deadline-expired",
            "Rocky Linux",
            "compare/v0.16.0...v0.16.1",
            "exact-state",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)

        self.assertIn("v0.16.1 candidate", read("README.md"))
        self.assertIn("Issue #159 owns the v0.16.1", read("docs/roadmap.md"))

    def test_generated_plugin_manifest_uses_candidate_version(self) -> None:
        manifest = json.loads(
            read("plugin/codex-dev-skills/.codex-plugin/plugin.json")
        )
        self.assertEqual("0.16.1", manifest["version"])


if __name__ == "__main__":
    unittest.main()
