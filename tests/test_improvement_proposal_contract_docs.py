from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ImprovementProposalContractDocsTests(unittest.TestCase):
    def test_public_and_portable_contracts_preserve_downstream_boundary(self):
        public = read("docs/improvement-proposal-contract.md")
        portable = read(
            "skills/loop-engineering/references/improvement-proposal-v0.md"
        )
        for text in (public, portable):
            self.assertIn("loop-improvement-proposal/v0", text)
            self.assertIn("loop-improvement-lineage/v0", text)
            self.assertIn("loop-operational-evidence/v0", text)
            self.assertIn("proposal", text.lower())
            self.assertIn("pending", text)
            self.assertIn("external-memory", text)
        self.assertIn("proposalctl.py", public)
        self.assertIn("proposalctl.py", portable)

    def test_skill_program_and_readme_expose_no_apply_or_promotion_path(self):
        for relative in (
            "skills/loop-engineering/SKILL.md",
            "README.md",
            "docs/programs/operational-evidence/README.md",
            "docs/programs/operational-evidence/continuation.md",
            "docs/programs/operational-evidence/implementation-phases.md",
            "docs/programs/operational-evidence/architecture-decisions.md",
        ):
            text = read(relative)
            self.assertIn("V3-A", text, relative)
        skill = read("skills/loop-engineering/SKILL.md")
        self.assertIn("scripts/proposalctl.py", skill)
        self.assertIn("proposal-only", skill)

    def test_v0120_packaging_and_release_preparation_agree(self):
        self.assertIn('VERSION="0.12.0"', read("install.sh"))
        self.assertIn('version: "0.12.0"', read("catalog.yaml"))
        self.assertIn("docs/release-notes-v0.12.0.md", read("README.md"))
        notes = read("docs/release-notes-v0.12.0.md")
        self.assertIn("# Release Notes: v0.12.0", notes)
        self.assertIn("not released", notes)
        self.assertIn("PlugMem", notes)


if __name__ == "__main__":
    unittest.main()
