from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class MemoryM0ContractDocsTests(unittest.TestCase):
    def test_public_and_portable_contracts_are_additive_and_non_backend(self):
        operation_docs = (
            read("docs/memory-operation-contract.md"),
            read("skills/loop-engineering/references/memory-operation-v0.md"),
        )
        qualification_docs = (
            read("docs/memory-qualification-contract.md"),
            read("skills/loop-engineering/references/memory-qualification-v0.md"),
        )
        for text in operation_docs:
            for phrase in ("loop-memory-operation/v0", "caller", "idempotent", "logical", "operationctl.py"):
                self.assertIn(phrase, text)
            self.assertIn("no backend", text.lower())
        for text in qualification_docs:
            for phrase in ("loop-memory-qualification/v0", "memory-off", "wrapper", "efficacy", "qualificationctl.py"):
                self.assertIn(phrase.lower(), text.lower())
            self.assertIn("zero backend/filesystem touch", text.lower())

    def test_repository_entrypoints_keep_m1_default_disabled(self):
        required = {
            "README.md": ("loop-memory-operation/v0", "loop-memory-qualification/v0", "v0.14.0"),
            "skills/loop-engineering/SKILL.md": ("memory-operation-v0.md", "memory-qualification-v0.md", "SQLite/FTS5"),
            "docs/roadmap.md": ("Issue #145", "Memory M0", "v0.14.0"),
            "docs/release-readiness.md": ("Memory M0", "zero backend/filesystem touch", "physical purge"),
            "docs/programs/operational-evidence/architecture-decisions.md": ("OE-016", "loop-memory-operation/v0", "loop-memory-qualification/v0"),
        }
        for relative, phrases in required.items():
            text = read(relative)
            for phrase in phrases:
                self.assertIn(phrase, text, relative)
        self.assertIn('VERSION="0.16.0"', read("install.sh"))
        self.assertIn('version: "0.16.0"', read("catalog.yaml"))


if __name__ == "__main__":
    unittest.main()
