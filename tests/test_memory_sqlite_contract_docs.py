from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class MemorySQLiteContractDocsTests(unittest.TestCase):
    def test_public_and_portable_contracts_are_additive_and_default_disabled(self):
        files = (
            ROOT / "docs" / "memory-sqlite-reference-contract.md",
            ROOT / "skills" / "loop-engineering" / "references" / "memory-sqlite-v0.md",
            ROOT / "docs" / "loops" / "issue-147" / "loop-spec.md",
        )
        for path in files:
            text = path.read_text(encoding="utf-8")
            for phrase in (
                "loop-memory-sqlite/v0", "default-disabled", "FTS5", "parameter",
                "logical", "no migration", "public/internal", "v0.14.0",
            ):
                self.assertIn(phrase.lower(), text.lower(), f"{path}: {phrase}")

    def test_upstream_production_modules_do_not_import_the_adapter(self):
        for name in (
            "memory_contract.py", "memory_operation.py", "memory_qualification.py",
            "candidate_evaluation.py", "improvement_lineage.py",
            "improvement_proposal.py", "operational_evidence.py",
        ):
            text = (
                ROOT / "skills" / "loop-engineering" / "scripts" / name
            ).read_text(encoding="utf-8")
            self.assertNotIn("memory_sqlite", text)
            self.assertNotIn("sqlitectl", text)

    def test_cli_has_no_service_purge_migration_or_promotion_route(self):
        text = (
            ROOT / "skills" / "loop-engineering" / "scripts" / "sqlitectl.py"
        ).read_text(encoding="utf-8")
        for route in ('sub.add_parser("service")', 'sub.add_parser("purge")',
                      'sub.add_parser("migrate")', 'sub.add_parser("promote")'):
            self.assertNotIn(route, text)


if __name__ == "__main__":
    unittest.main()
