from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate-desktop-wrapper-legacy.py"
SPEC = importlib.util.spec_from_file_location("desktop_wrapper_legacy", VALIDATOR)
assert SPEC is not None and SPEC.loader is not None
legacy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(legacy)


class DesktopWrapperLegacyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.inventory = yaml.safe_load(
            (ROOT / legacy.INVENTORY_PATH).read_text(encoding="utf-8")
        )
        self._write_fixture()

    def _write(self, relative: str, text: str = "fixture\n") -> pathlib.Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def _write_inventory_text(self, text: str) -> None:
        self._write(legacy.INVENTORY_PATH.as_posix(), text)

    def _write_inventory(self) -> None:
        self._write_inventory_text(
            yaml.safe_dump(self.inventory, sort_keys=False, allow_unicode=False)
        )

    def _classify(self, relative: str) -> None:
        self.inventory["classified_reference_files"].append(relative)
        self.inventory["classified_reference_files"].sort()
        self._write_inventory()

    def _write_fixture(self) -> None:
        self._write_inventory()
        for category in ("scripts", "tests"):
            for relative in self.inventory["artifacts"][category]:
                self._write(relative)
        for relative in self.inventory["classified_reference_files"]:
            self._write(relative, "frozen desktop_runtime_ compatibility evidence\n")
        self._write(
            "plugin/codex-dev-skills/skills/generated/SKILL.md",
            "generated scripts/desktop_runtime_generated.py reference\n",
        )
        for relative in legacy.EXPLICIT_ACTIVE_FILES:
            self._write(relative, "{}\n")

    def test_repository_inventory_is_valid(self) -> None:
        result = legacy.validate(ROOT)
        self.assertEqual("valid", result["status"])
        self.assertEqual(32, result["artifact_count"])
        self.assertEqual(0, result["active_entrypoint_count"])

    def test_minimal_fixture_is_valid_and_ignores_generated_copy(self) -> None:
        result = legacy.validate(self.root)
        self.assertEqual("valid", result["status"])

    def test_missing_artifact_is_rejected(self) -> None:
        target = self.root / self.inventory["artifacts"]["scripts"][0]
        target.unlink()
        with self.assertRaisesRegex(legacy.LegacyInventoryError, "inventory mismatch"):
            legacy.validate(self.root)

    def test_unclassified_artifact_is_rejected(self) -> None:
        self._write("scripts/desktop_runtime_unclassified.py")
        with self.assertRaisesRegex(legacy.LegacyInventoryError, "inventory mismatch"):
            legacy.validate(self.root)

    def test_unclassified_reference_is_rejected(self) -> None:
        self._write("docs/unclassified.md", "new desktop_runtime_ reference\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "classified reference inventory mismatch"
        ):
            legacy.validate(self.root)

    def test_aggregate_source_size_is_bounded(self) -> None:
        with mock.patch.object(legacy, "MAX_SCANNED_SOURCE_BYTES", 1):
            with self.assertRaisesRegex(
                legacy.LegacyInventoryError, "aggregate canonical source scan exceeds"
            ):
                legacy.validate(self.root)

    def test_stale_classified_reference_is_rejected(self) -> None:
        relative = self.inventory["classified_reference_files"][0]
        self._write(relative, "no legacy token remains\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "classified reference inventory mismatch"
        ):
            legacy.validate(self.root)

    def test_active_runnable_reference_is_rejected(self) -> None:
        relative = "skills/desktop-project-delivery/SKILL.md"
        self.assertIn(relative, self.inventory["classified_reference_files"])
        self._write(relative, "run scripts/desktop_runtime_wrapper_planner.py\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "active surface contains runnable"
        ):
            legacy.validate(self.root)

    def test_plugin_manifest_runnable_reference_is_rejected(self) -> None:
        self._write(
            ".codex-plugin/plugin.json",
            '{"entrypoint":"scripts/desktop_runtime_wrapper_planner.py"}\n',
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "active surface contains runnable"
        ):
            legacy.validate(self.root)

    def test_active_import_is_rejected(self) -> None:
        relative = "skills/desktop-project-delivery/SKILL.md"
        self._write(relative, "from scripts import desktop_runtime_wrapper_planner\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_non_wrapper_script_import_is_rejected_when_classified(self) -> None:
        relative = "scripts/active_consumer.py"
        self._write(relative, "from scripts import desktop_runtime_wrapper_planner\n")
        self._classify(relative)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_non_wrapper_script_path_is_rejected_when_classified(self) -> None:
        relative = "scripts/active_consumer.py"
        self._write(relative, "run scripts/desktop_runtime_wrapper_planner.py\n")
        self._classify(relative)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_non_historical_test_import_is_rejected_when_classified(self) -> None:
        relative = "tests/test_active_consumer.py"
        self._write(relative, "from scripts import desktop_runtime_wrapper_planner\n")
        self._classify(relative)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "active test contains legacy wrapper import"
        ):
            legacy.validate(self.root)

    def test_readme_runnable_reference_is_rejected(self) -> None:
        self._write(
            "README.md",
            "Run scripts/desktop_runtime_wrapper_planner.py for legacy evidence.\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_release_readiness_runnable_reference_is_rejected(self) -> None:
        relative = "docs/release-readiness.md"
        self._write(relative, "run scripts/desktop_runtime_wrapper_planner.py\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_generated_root_cannot_hide_canonical_references(self) -> None:
        self.inventory["generated_reference_roots"] = ["docs"]
        self._write_inventory()
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "generated_reference_roots must be"
        ):
            legacy.validate(self.root)

    def test_prohibited_roots_cannot_be_weakened(self) -> None:
        self.inventory["prohibited_active_roots"].remove("skills")
        self._write_inventory()
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "prohibited_active_roots must be"
        ):
            legacy.validate(self.root)

    def test_unknown_inventory_key_is_rejected(self) -> None:
        text = yaml.safe_dump(self.inventory, sort_keys=False) + "unexpected: true\n"
        self._write_inventory_text(text)
        with self.assertRaisesRegex(legacy.LegacyInventoryError, "keys mismatch"):
            legacy.validate(self.root)

    def test_duplicate_yaml_key_is_rejected(self) -> None:
        text = yaml.safe_dump(self.inventory, sort_keys=False) + "status: invalid\n"
        self._write_inventory_text(text)
        with self.assertRaisesRegex(legacy.LegacyInventoryError, "duplicate YAML key"):
            legacy.validate(self.root)

    def test_non_scalar_yaml_key_is_rejected_without_type_error(self) -> None:
        text = yaml.safe_dump(self.inventory, sort_keys=False) + "? [bad]\n: value\n"
        self._write_inventory_text(text)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "YAML mapping keys must be scalar"
        ):
            legacy.validate(self.root)

    def test_symlinked_artifact_is_rejected(self) -> None:
        relative = self.inventory["artifacts"]["scripts"][0]
        target = self.root / relative
        target.unlink()
        outside = self._write("outside.py")
        target.symlink_to(outside)
        with self.assertRaisesRegex(legacy.LegacyInventoryError, "non-symlink"):
            legacy.validate(self.root)


if __name__ == "__main__":
    unittest.main()
