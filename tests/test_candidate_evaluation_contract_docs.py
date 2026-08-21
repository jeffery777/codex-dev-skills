from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class CandidateEvaluationContractDocsTests(unittest.TestCase):
    def test_public_and_portable_contracts_preserve_isolation_and_authority(self):
        for text in (
            read("docs/candidate-evaluation-contract.md"),
            read("skills/loop-engineering/references/candidate-evaluation-v0.md"),
        ):
            self.assertIn("loop-candidate-evaluation/v0", text)
            self.assertIn("loop-improvement-proposal/v0", text)
            self.assertIn("memory-off", text)
            self.assertIn("synthetic-advisory", text)
            self.assertIn("independent human/platform promotion gate", text)
            self.assertIn("evaluationctl.py", text)
            self.assertIn("cannot", text.lower())

    def test_repository_entrypoints_expose_v3b_without_release_or_backend_claims(self):
        required = {
            "README.md": ("V3-B", "evaluationctl.py", "v0.13.0"),
            "skills/loop-engineering/SKILL.md": (
                "V3-B", "references/candidate-evaluation-v0.md", "memory-off"
            ),
            "docs/programs/operational-evidence/README.md": (
                "V3-B", "isolated candidate evaluation", "cannot promote"
            ),
            "docs/programs/operational-evidence/implementation-phases.md": (
                "loop-candidate-evaluation/v0", "synthetic-advisory", "v0.13.0"
            ),
            "docs/programs/operational-evidence/continuation.md": (
                "Issue #141", "memory-off", "M1"
            ),
            "docs/programs/operational-evidence/architecture-decisions.md": (
                "OE-015", "packet cannot promote itself", "V3-C"
            ),
        }
        for relative, phrases in required.items():
            text = read(relative)
            for phrase in phrases:
                self.assertIn(phrase, text, relative)
        self.assertIn('VERSION="0.16.1"', read("install.sh"))
        self.assertIn('version: "0.16.1"', read("catalog.yaml"))
        notes = read("docs/release-notes-v0.13.0.md")
        self.assertIn("# Release Notes: v0.13.0", notes)
        self.assertIn("loop-candidate-evaluation/v0", notes)
        self.assertIn("issues/141", notes)
        self.assertIn("pull/142", notes)


if __name__ == "__main__":
    unittest.main()
