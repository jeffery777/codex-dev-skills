from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ImprovementLineageContractDocsTests(unittest.TestCase):
    def test_public_and_portable_contracts_preserve_v2d_a_boundary(self):
        public = read("docs/improvement-lineage-contract.md")
        portable = read(
            "skills/loop-engineering/references/improvement-lineage-v0.md"
        )
        for text in (public, portable):
            self.assertIn("loop-improvement-lineage/v0", text)
            self.assertIn("loop-evidence-projection/v0", text)
            self.assertIn("loop-operational-evidence/v0", text)
            self.assertIn("promotion", text)
        self.assertIn("do not add a V2d-A kind or", public)
        self.assertIn("Never add V2d-B fields or kinds to V2d-A", portable)

    def test_runtime_adapters_remain_outside_contract_implementation(self):
        skill = read("skills/loop-engineering/SKILL.md")
        catalog = read("catalog.yaml")
        self.assertIn("Runtime compatibility: shared", skill)
        self.assertIn("scripts/improvementctl.py", skill)
        self.assertIn("runtime: cli", catalog)
        self.assertIn("runtime: desktop", catalog)
        self.assertNotIn("improvementctl.py", read("skills/cli-session-handoff/SKILL.md"))
        self.assertNotIn(
            "improvementctl.py", read("skills/desktop-project-delivery/SKILL.md")
        )

    def test_obsidian_profile_is_optional_and_non_authoritative(self):
        profile = json.loads(
            read(
                "skills/loop-engineering/references/"
                "obsidian-reference-profile-v0.json"
            )
        )
        self.assertFalse(profile["required_dependency"])
        self.assertFalse(profile["target_mutation"])
        self.assertTrue(
            all(value is False for value in profile["authority_invariants"].values())
        )

    def test_current_release_metadata_is_aligned(self):
        self.assertIn('VERSION="0.16.2"', read("install.sh"))
        self.assertIn('version: "0.16.2"', read("catalog.yaml"))
        self.assertIn(
            "docs/release-notes-v0.15.0.md",
            read("README.md"),
        )
        self.assertIn(
            "# Release Notes: v0.15.0",
            read("docs/release-notes-v0.15.0.md"),
        )


if __name__ == "__main__":
    unittest.main()
