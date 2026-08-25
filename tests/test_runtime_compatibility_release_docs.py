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
            "compare/v0.16.2...v0.16.3",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)

        self.assertIn("v0.16.3, published", read("README.md"))
        self.assertIn("Issue #163 owns the v0.16.3", read("docs/roadmap.md"))

    def test_v0170_historical_notes_and_traceability_remain(self) -> None:
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
        self.assertIn("v0.17.0, published", read("README.md"))
        self.assertIn("Issue #165 delivered the v0.17.0", read("docs/roadmap.md"))

    def test_v0171_historical_notes_and_traceability_remain(self) -> None:
        notes = read("docs/release-notes-v0.17.1.md")
        for expected in (
            "# Release Notes: v0.17.1",
            "Issue #167",
            "documentation coherence patch",
            "compare/v0.17.0...v0.17.1",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)
        self.assertIn("v0.17.1\npublished the documentation-coherence", read("README.md"))
        self.assertIn("Issue #167 / PR #168 published the v0.17.1", read("docs/roadmap.md"))

    def test_v0180_historical_notes_and_published_traceability_remain(self) -> None:
        notes = read("docs/release-notes-v0.18.0.md")
        for expected in (
            "# Release Notes: v0.18.0",
            "Issue #169 / PR #170",
            "Issue #171 / PR #172",
            "pre-1.0 minor release",
            "compare/v0.17.1...v0.18.0",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)
        published_phrases = {
            "README.md": "v0.18.0 published the Desktop Runtime Wrapper V1 retirement through Issue #174 / PR #173",
            "docs/roadmap.md": "Issue #174 / PR #173 published it as the v0.18.0",
            "docs/release-readiness.md": "Issue #174 / PR #173 published the Issue #171 / PR #172",
        }
        stale_phrases = {
            "README.md": "current development candidate is the v0.18.0",
            "docs/roadmap.md": "prepared for the v0.18.0",
            "docs/release-readiness.md": "For the v0.18.0 Issue #171 / PR #172",
        }
        for document, published_phrase in published_phrases.items():
            text = " ".join(read(document).split())
            for expected in (
                "Issue #174 / PR #173",
                "3b789e2f9749f2643b6fe75397d22f6e21a71ce2",
                "annotated `v0.18.0`",
                "GitHub Release",
                "no deployment target or publish/deploy workflow",
                published_phrase,
            ):
                with self.subTest(document=document, expected=expected):
                    self.assertIn(expected, text)
            self.assertRegex(
                text,
                r"deployment is (?:therefore )?not applicable",
                document,
            )
            self.assertRegex(
                text,
                r"GitHub Release(?: publication)? is not deployment evidence",
                document,
            )
            self.assertNotIn(stale_phrases[document], text, document)

    def test_v0181_historical_notes_and_published_traceability_align(self) -> None:
        notes = read("docs/release-notes-v0.18.1.md")
        for expected in (
            "# Release Notes: v0.18.1",
            "Status: release candidate",
            "Issue #175",
            "post-release state-coherence patch",
            "compare/v0.18.0...v0.18.1",
            "no deployment target or publish/deploy workflow",
            "M2, V3-C, and Memory activation remain",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)
        published_phrases = {
            "README.md": "Issue #175 / PR #176 published the post-release state-coherence patch",
            "docs/roadmap.md": "Issue #175 / PR #176 published the v0.18.1",
            "docs/release-readiness.md": "Issue #175 / PR #176 published the v0.18.1",
        }
        stale_phrases = {
            "README.md": "current development candidate is the v0.18.1",
            "docs/roadmap.md": "Issue #175 owns the v0.18.1",
            "docs/release-readiness.md": "Issue #175 v0.18.1 post-release state-coherence patch candidate",
        }
        for document, published_phrase in published_phrases.items():
            text = " ".join(read(document).split())
            for expected in (
                published_phrase,
                "b5cb03ae467222215f42c3081cad796ad3a2ecf3",
                "annotated `v0.18.1`",
                "GitHub Release",
                "no deployment target or publish/deploy workflow",
            ):
                with self.subTest(document=document, expected=expected):
                    self.assertIn(expected, text)
            self.assertRegex(
                text,
                r"deployment is (?:therefore )?not applicable",
                document,
            )
            self.assertRegex(
                text,
                r"GitHub Release(?: publication)? is not deployment evidence",
                document,
            )
            self.assertNotIn(stale_phrases[document], text, document)

    def test_v0182_historical_candidate_metadata_and_contracts_remain(self) -> None:
        notes = read("docs/release-notes-v0.18.2.md")
        for expected in (
            "# Release Notes: v0.18.2",
            "Status: release candidate for Issue #179",
            "codex mcp-server",
            "--skip-unit-tests",
            "15 embedded unittest invocations",
            "all 11",
            "44-module focused subset",
            "compare/v0.18.1...v0.18.2",
            "0a7b000d4fb55e25228d3329a02247540c341932",
            "no deployment target or publish/deploy workflow",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, notes)
        self.assertRegex(notes, r"57\s+in this\s+candidate")
        self.assertRegex(notes, r"not the source rollback\s+target")
        for document in ("README.md", "docs/roadmap.md"):
            with self.subTest(document=document):
                text = " ".join(read(document).split())
                self.assertIn("v0.18.2", text)

    def test_active_guidance_uses_non_recursive_release_state_roles(self) -> None:
        for document in ("README.md", "docs/roadmap.md", "docs/release-readiness.md"):
            with self.subTest(document=document):
                text = read(document).lower()
                self.assertNotIn("current published version", text)
                self.assertNotIn("current development candidate", text)
        self.assertIn("Repository source/package version", read("README.md"))
        self.assertIn("publication truth", read("docs/roadmap.md"))
        self.assertIn("## Release-State Contract", read("docs/release-readiness.md"))

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

    def test_package_local_plugin_manifest_uses_current_version(self) -> None:
        manifest = json.loads(
            read("plugin/codex-dev-skills/.codex-plugin/plugin.json")
        )
        self.assertEqual(yaml.safe_load(read("catalog.yaml"))["version"], manifest["version"])


if __name__ == "__main__":
    unittest.main()
