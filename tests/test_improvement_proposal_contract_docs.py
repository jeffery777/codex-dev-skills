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

    def test_skill_program_and_readme_expose_proposal_only_no_action_boundary(self):
        required_boundaries = {
            "skills/loop-engineering/SKILL.md": (
                "proposal-only descriptions",
                "Never apply,",
                "independent human/platform promotion gate",
            ),
            "README.md": (
                "proposal-only evidence-to-proposal",
                "The CLI cannot apply, commit, push, create a PR, approve, activate,",
                "human/platform promotion gate",
            ),
            "docs/programs/operational-evidence/README.md": (
                "V3-A is limited to deterministic proposal generation.",
                "It cannot execute or promote a candidate.",
                "human/platform promotion",
            ),
            "docs/programs/operational-evidence/continuation.md": (
                "proposal-only invariants",
                "It excludes external memory, candidate execution, runtime automation, and",
                "independent promotion gate",
            ),
            "docs/programs/operational-evidence/implementation-phases.md": (
                "proposal-only fields",
                "candidate execution, apply/commit/push/PR-create operations",
                "promotion gate is always",
            ),
            "docs/programs/operational-evidence/architecture-decisions.md": (
                "Downstream Proposal-Only Family",
                "but cannot apply, commit, push, create a PR, approve, activate, promote, merge,",
                "independent human/platform promotion gate",
            ),
        }
        for relative, boundaries in required_boundaries.items():
            text = read(relative)
            self.assertIn("V3-A", text, relative)
            for boundary in boundaries:
                self.assertIn(boundary, text, relative)
        skill = read("skills/loop-engineering/SKILL.md")
        self.assertIn("scripts/proposalctl.py", skill)

    def test_current_candidate_packaging_and_release_metadata_agree(self):
        self.assertIn('VERSION="0.17.1"', read("install.sh"))
        self.assertIn('version: "0.17.1"', read("catalog.yaml"))
        self.assertIn("docs/release-notes-v0.15.0.md", read("README.md"))
        notes = read("docs/release-notes-v0.15.0.md")
        self.assertIn("# Release Notes: v0.15.0", notes)
        self.assertIn("Status: release candidate", notes)
        self.assertIn("issues/153", notes)
        self.assertIn("compare/v0.14.2...v0.15.0", notes)
        self.assertIn("scripts/project-python", notes)
        self.assertIn("tag and GitHub Release", notes)

        v0142 = read("docs/release-notes-v0.14.2.md")
        self.assertIn("# Release Notes: v0.14.2", v0142)
        self.assertIn("issues/151", v0142)
        self.assertIn("compare/v0.14.1...v0.14.2", v0142)

        historical = read("docs/release-notes-v0.13.0.md")
        self.assertIn("# Release Notes: v0.13.0", historical)
        self.assertIn("Release date: 2026-08-12", historical)
        self.assertIn("V3-B", historical)

        v0120 = read("docs/release-notes-v0.12.0.md")
        self.assertIn("PlugMem", v0120)

    def test_v0142_permission_remediation_is_exact_and_nonrecursive(self):
        troubleshooting = read("docs/troubleshooting.md")
        self.assertIn(
            'chmod go-w -- "$SKILLS_DIR" "$TEMPLATES_DIR" "$PROFILES_DIR"',
            troubleshooting,
        )
        for boundary in (
            "Include only roots that exist and were individually inspected.",
            "exact, current-user-owned",
            "Do not infer ownership of neighbouring or unknown artifacts.",
            "never use a recursive `chmod`",
            "home-directory target",
            "broader parent",
            "wildcard",
        ):
            self.assertIn(boundary, troubleshooting)

        notes = read("docs/release-notes-v0.14.2.md")
        self.assertIn(
            "Older v0.14.1 state\nchains, selected target roots, or installer-managed artifacts",
            notes,
        )
        self.assertIn("dry-run, exact-path, manually approved `chmod go-w`", notes)
        self.assertIn("neither\nrecurses through a home directory nor mutates unknown legacy backups", notes)


if __name__ == "__main__":
    unittest.main()
