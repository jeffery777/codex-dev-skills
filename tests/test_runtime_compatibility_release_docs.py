from __future__ import annotations

import json
import pathlib
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class RuntimeCompatibilityReleaseDocsTests(unittest.TestCase):
    def test_v0162_historical_notes_and_traceability_remain(self) -> None:
        notes = read("docs/release-notes-v0.16.2.md")
        for expected in (
            "# Release Notes: v0.16.2",
            "Issue #161",
            "codex agents",
            "codex queue",
            "codex doctor --json",
            "share_thread",
            "ChatGPT data controls",
            "compare/v0.16.1...v0.16.2",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)

        self.assertIn("v0.16.2, published", read("README.md"))
        self.assertIn("Issue #161 owns the v0.16.2", read("docs/roadmap.md"))

    def test_v0163_candidate_metadata_and_traceability_align(self) -> None:
        self.assertEqual("0.16.3", yaml.safe_load(read("catalog.yaml"))["version"])
        self.assertIn('VERSION="0.16.3"', read("install.sh"))

        notes = read("docs/release-notes-v0.16.3.md")
        for expected in (
            "# Release Notes: v0.16.3",
            "Issue #163",
            "desktop_runtime_*",
            "zero detected active runnable",
            "compare/v0.16.2...v0.16.3",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)

        self.assertIn("v0.16.3 candidate", read("README.md"))
        self.assertIn("Issue #163 owns the v0.16.3", read("docs/roadmap.md"))

    def test_generated_plugin_manifest_uses_current_version(self) -> None:
        manifest = json.loads(
            read("plugin/codex-dev-skills/.codex-plugin/plugin.json")
        )
        self.assertEqual("0.16.3", manifest["version"])


if __name__ == "__main__":
    unittest.main()
