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

    def test_future_removal_plan_dispositions_cover_current_inventory(self) -> None:
        inventory = yaml.safe_load(
            (ROOT / legacy.INVENTORY_PATH).read_text(encoding="utf-8")
        )
        plan = (
            ROOT / "docs/loops/issue-169/future-removal-plan.md"
        ).read_text(encoding="utf-8")
        actions: dict[str, set[str]] = {}
        for line in plan.splitlines():
            for action in ("delete", "rewrite", "retain-historical", "regenerate"):
                prefix = f"{action}: "
                if line.startswith(prefix):
                    path = line[len(prefix):].split(" —", 1)[0]
                    actions.setdefault(path, set()).add(action)

        artifacts = {
            path
            for paths in inventory["artifacts"].values()
            for path in paths
        }
        references = set(inventory["classified_reference_files"])
        for path in artifacts:
            with self.subTest(kind="artifact", path=path):
                self.assertEqual(actions.get(path), {"delete"})
        for path in references:
            with self.subTest(kind="reference", path=path):
                self.assertTrue(
                    actions.get(path, set())
                    & {"rewrite", "retain-historical"},
                    path,
                )

        self.assertEqual(
            actions.get("scripts/validate-desktop-wrapper-legacy.py"),
            {"delete"},
        )
        self.assertEqual(
            actions.get("tests/test_desktop_wrapper_legacy.py"),
            {"delete"},
        )
        self.assertEqual(actions.get("scripts/validate-repo.sh"), {"rewrite"})
        for path in (
            "plugin/codex-dev-skills/docs/native-runtime-capabilities.md",
            "plugin/codex-dev-skills/skills/desktop-project-delivery/SKILL.md",
            "plugin/codex-dev-skills/skills/desktop-thread-delegation/SKILL.md",
            "plugin/codex-dev-skills/skills/loop-engineering/SKILL.md",
        ):
            with self.subTest(kind="generated", path=path):
                self.assertEqual(actions.get(path), {"regenerate"})

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

    def test_historical_document_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "historical\npython3 scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_historical_wrapper_test_command_is_rejected(self) -> None:
        relative = "docs/release-notes-v0.2.1.md"
        self._write(
            relative,
            "historical\npython -m unittest tests.test_desktop_runtime_wrapper_planner\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_historical_live_smoke_instruction_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "1. Inject a callable into desktop_runtime_create_thread_live_smoke.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_generated_document_command_is_rejected(self) -> None:
        self._write(
            "plugin/codex-dev-skills/skills/generated/SKILL.md",
            "python3 scripts/desktop_runtime_generated.py --run\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_direct_historical_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "./scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_multiline_historical_wrapper_test_command_is_rejected(self) -> None:
        relative = "docs/release-notes-v0.2.1.md"
        self._write(
            relative,
            "python -m unittest \\\n  tests.test_desktop_runtime_wrapper_planner\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_uv_pytest_historical_wrapper_command_is_rejected(self) -> None:
        relative = "docs/release-notes-v0.2.1.md"
        self._write(
            relative,
            "uv run pytest tests/test_desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_embedded_run_instruction_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "To reproduce, run scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_historical_python_call_expression_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "desktop_runtime_ historical: "
            "execute_create_thread_with_injected_adapter(request, runner=...)\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_historical_python_call_expression_needs_no_reference_token(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "execute_create_thread_with_injected_adapter(request, runner=...)\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_dotted_module_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "python -m scripts.desktop_runtime_wrapper_planner --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_environment_prefixed_module_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "env PYTHONPATH=. python3 -m "
            "scripts.desktop_runtime_create_thread_live_smoke\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_assignment_prefixed_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "PYTHONPATH=. python3 "
            "scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_command_prefixed_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "command python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_backtick_prefixed_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "`python3 scripts/desktop_runtime_wrapper_planner.py --example`\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_canonical_yaml_wrapper_command_is_rejected(self) -> None:
        relative = "templates/orchestration/example.template.yaml"
        self._write(
            relative,
            "command: python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_generated_yaml_wrapper_command_is_rejected(self) -> None:
        self._write(
            "plugin/codex-dev-skills/templates/orchestration/example.template.yaml",
            "python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_env_option_prefixed_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "env -i python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_command_option_prefixed_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "command -p python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_labeled_inline_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "Example: `python3 scripts/desktop_runtime_wrapper_planner.py --example`\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_uppercase_active_wrapper_reference_is_rejected(self) -> None:
        self._write(
            "scripts/active_consumer.sh",
            "python3 scripts/DESKTOP_RUNTIME_WRAPPER_PLANNER.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "runnable legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_uppercase_generic_active_reference_requires_historical_marker(self) -> None:
        relative = "skills/desktop-project-delivery/SKILL.md"
        self._write(relative, "Use DESKTOP_RUNTIME_* as the current adapter.\n")
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "unqualified legacy wrapper reference"
        ):
            legacy.validate(self.root)

    def test_extensionless_readme_wrapper_command_is_rejected(self) -> None:
        self._write(
            "docs/archive/README",
            "python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_standalone_relative_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_uv_run_relative_wrapper_command_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "uv run scripts/desktop_runtime_wrapper_planner.py --example\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_uv_run_relative_wrapper_stdin_redirection_is_rejected(self) -> None:
        relative = "docs/desktop-runtime-wrapper-v1-plan.md"
        self._write(
            relative,
            "uv run scripts/desktop_runtime_wrapper_planner.py < prepared.json\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_uppercase_readme_suffix_wrapper_command_is_rejected(self) -> None:
        self._write(
            "docs/archive/README.MD",
            "python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_generated_extensionless_readme_wrapper_command_is_rejected(self) -> None:
        self._write(
            "plugin/codex-dev-skills/skills/example/README",
            "python3 scripts/desktop_runtime_wrapper_planner.py\n",
        )
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "executable legacy wrapper guidance"
        ):
            legacy.validate(self.root)

    def test_symlinked_generated_documentation_root_is_rejected(self) -> None:
        generated_root = self.root / "plugin/codex-dev-skills"
        generated_file = generated_root / "skills/generated/SKILL.md"
        generated_file.unlink()
        generated_file.parent.rmdir()
        generated_file.parent.parent.rmdir()
        generated_root.rmdir()
        generated_root.symlink_to(self.root / "docs", target_is_directory=True)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "generated documentation root must"
        ):
            legacy.validate(self.root)

    def test_missing_generated_documentation_root_is_rejected(self) -> None:
        generated_root = self.root / "plugin/codex-dev-skills"
        generated_file = generated_root / "skills/generated/SKILL.md"
        generated_file.unlink()
        generated_file.parent.rmdir()
        generated_file.parent.parent.rmdir()
        generated_root.rmdir()
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError, "generated documentation root is missing"
        ):
            legacy.validate(self.root)

    def test_symlinked_generated_documentation_child_is_rejected(self) -> None:
        generated_root = self.root / "plugin/codex-dev-skills"
        linked_child = generated_root / "linked-docs"
        linked_child.symlink_to(self.root / "docs", target_is_directory=True)
        with self.assertRaisesRegex(
            legacy.LegacyInventoryError,
            "generated documentation directory must not be a symlink",
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
