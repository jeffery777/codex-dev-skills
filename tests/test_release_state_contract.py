from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate-release-state.py"
SPEC = importlib.util.spec_from_file_location("validate_release_state", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
release_state = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_state)


class ReleaseStateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.fixture = pathlib.Path(self.temporary.name)
        self.version = yaml.safe_load(
            (ROOT / "catalog.yaml").read_text(encoding="utf-8")
        )["version"]
        self.notes_relative = f"docs/release-notes-v{self.version}.md"
        paths = (
            "catalog.yaml",
            "install.sh",
            "plugin/codex-dev-skills/.codex-plugin/plugin.json",
            "README.md",
            "docs/roadmap.md",
            "docs/release-readiness.md",
            self.notes_relative,
            "policies/release-state-contract.md",
        )
        for relative in paths:
            target = self.fixture / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / relative).read_bytes())
        self.original_root = release_state.ROOT
        release_state.ROOT = self.fixture
        self.addCleanup(setattr, release_state, "ROOT", self.original_root)

    def test_repository_contract_passes_without_publication_metadata(self) -> None:
        self.assertEqual(self.version, release_state.validate_repo())
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(
                    node.func.id,
                    {"__import__", "compile", "eval", "exec"},
                )
        self.assertEqual(
            {
                "__future__",
                "collections.abc",
                "json",
                "pathlib",
                "re",
                "stat",
                "sys",
                "yaml",
            },
            imports,
        )

    def test_source_package_mismatch_fails_closed(self) -> None:
        catalog_path = self.fixture / "catalog.yaml"
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        catalog["version"] = "9.9.9"
        catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "source/package version 9.9.9"
        ):
            release_state.validate_repo()

    def test_missing_matching_candidate_record_fails_closed(self) -> None:
        (self.fixture / self.notes_relative).unlink()
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "required release-state file is missing"
        ):
            release_state.validate_repo()

    def test_mutable_active_publication_claim_fails_closed(self) -> None:
        readme = self.fixture / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\nThe current published version is v0.18.2.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "mutable release-state assertion"
        ):
            release_state.validate_repo()

    def test_latest_publication_synonym_fails_closed(self) -> None:
        readme = self.fixture / "README.md"
        readme.write_text(
            readme.read_text(encoding="utf-8")
            + "\nThe latest published release is v9.9.9.\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "mutable release-state assertion"
        ):
            release_state.validate_repo()

    def test_duplicate_catalog_version_fails_closed(self) -> None:
        catalog = self.fixture / "catalog.yaml"
        catalog.write_text(
            f'version: "{self.version}"\nversion: "{self.version}"\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "duplicate key"
        ):
            release_state.validate_repo()

    def test_duplicate_manifest_version_fails_closed(self) -> None:
        manifest = self.fixture / "plugin/codex-dev-skills/.codex-plugin/plugin.json"
        manifest.write_text(
            f'{{"version":"{self.version}","version":"{self.version}"}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "duplicate key"
        ):
            release_state.validate_repo()

    def test_heading_only_candidate_record_fails_closed(self) -> None:
        notes = self.fixture / self.notes_relative
        notes.write_text(f"# Release Notes: v{self.version}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "release-candidate status"
        ):
            release_state.validate_repo()

    def test_candidate_record_requires_authority_boundary(self) -> None:
        notes = self.fixture / self.notes_relative
        notes.write_text(
            notes.read_text(encoding="utf-8").replace("separate", "combined"),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "separate human gates"
        ):
            release_state.validate_repo()

    def test_manifest_requires_string_version(self) -> None:
        manifest_path = (
            self.fixture / "plugin/codex-dev-skills/.codex-plugin/plugin.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = 18
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(
            release_state.ReleaseStateError, "must declare a string version"
        ):
            release_state.validate_repo()


if __name__ == "__main__":
    unittest.main()
