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

    def test_v0163_historical_notes_and_traceability_remain(self) -> None:
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

        self.assertIn("v0.16.3, published", read("README.md"))
        self.assertIn("Issue #163 owns the v0.16.3", read("docs/roadmap.md"))

    def test_v0170_candidate_metadata_and_traceability_align(self) -> None:
        self.assertEqual("0.17.0", yaml.safe_load(read("catalog.yaml"))["version"])
        self.assertIn('VERSION="0.17.0"', read("install.sh"))
        notes = read("docs/release-notes-v0.17.0.md")
        for expected in (
            "# Release Notes: v0.17.0",
            "Issue #165",
            "loop-context-continuity/v1",
            "fresh-continuation",
            "compare/v0.16.3...v0.17.0",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)
        self.assertIn("v0.17.0 candidate", read("README.md"))
        self.assertIn("Issue #165 owns the v0.17.0", read("docs/roadmap.md"))

    def test_v0170_paired_run_release_evidence_is_durable_and_consistent(self) -> None:
        evidence_path = "docs/loops/issue-165/paired-run-evidence.md"
        results_path = "docs/loops/issue-165/paired-run-results.json"
        evidence = read(evidence_path)
        results = json.loads(read(results_path))

        self.assertEqual(
            "issue-165-paired-run-release-evidence/v1", results["schema"]
        )
        self.assertEqual("gpt-5.6-terra", results["provenance"]["model"])
        self.assertEqual(
            "4d66efa0429d55b7c4ab8e6399387244684e8960",
            results["provenance"]["head_under_test"],
        )
        self.assertEqual(
            ["compressed-current-context", "fresh-durable-checkpoint"],
            [run["condition"] for run in results["runs"]],
        )
        for run in results["runs"]:
            with self.subTest(condition=run["condition"]):
                usage = run["usage"]
                self.assertEqual(
                    usage["input_tokens"] + usage["output_tokens"],
                    usage["objective_total_tokens_including_bootstrap"],
                )
                self.assertEqual(8, run["quality"]["score"])
                self.assertEqual([True] * 8, run["quality"]["checks"])
                self.assertFalse(
                    run["final_result"]["quality_answers"][
                        "release_evidence_flag"
                    ]
                )
                self.assertEqual(
                    len(set(run["final_result"]["files_read"])),
                    run["measurement"]["declared_unique_repository_reads"],
                )

        compressed, fresh = results["runs"]
        self.assertLess(
            fresh["usage"]["objective_total_tokens_including_bootstrap"],
            compressed["usage"]["objective_total_tokens_including_bootstrap"],
        )
        self.assertLess(
            fresh["measurement"]["wall_seconds"],
            compressed["measurement"]["wall_seconds"],
        )
        self.assertEqual(
            [
                "machine-local absolute paths",
                "command text",
                "runtime log output",
            ],
            results["redaction_boundary"]["excluded"],
        )
        self.assertIn("paired-run-results.json", evidence)
        self.assertIn(evidence_path, read("README.md"))
        self.assertIn(evidence_path, read("docs/release-readiness.md"))
        self.assertIn(evidence_path, read("docs/release-notes-v0.17.0.md"))
        self.assertIn(evidence_path, read("docs/roadmap.md"))

    def test_generated_plugin_manifest_uses_current_version(self) -> None:
        manifest = json.loads(
            read("plugin/codex-dev-skills/.codex-plugin/plugin.json")
        )
        self.assertEqual("0.17.0", manifest["version"])


if __name__ == "__main__":
    unittest.main()
