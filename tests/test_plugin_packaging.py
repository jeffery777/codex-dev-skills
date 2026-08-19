from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "plugin" / "codex-dev-skills"
MANIFEST_PATH = PACKAGE_ROOT / ".codex-plugin" / "plugin.json"
TEMPLATE_SKILLS = (
    "loop-engineering",
    "milestone-continuation",
    "task-continuation",
)
INSTALLER_ENV_OVERRIDES = (
    "CODEX_CLI",
    "CODEX_SKILLS_DIR",
    "CODEX_TEMPLATES_DIR",
    "CODEX_CUSTOM_AGENTS_DIR",
    "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS",
    "CODEX_DEV_SKILLS_TARGET",
)


class PluginPackagingTests(unittest.TestCase):
    def test_manifest_packages_the_generated_skill_tree(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        self.assertEqual("codex-dev-skills", manifest["name"])
        self.assertEqual("0.15.1", manifest["version"])
        self.assertEqual("./skills/", manifest["skills"])
        self.assertTrue((PACKAGE_ROOT / "skills" / "project-delivery" / "SKILL.md").is_file())
        self.assertFalse((ROOT / ".codex-plugin" / "plugin.json").exists())

    def test_repo_marketplace_resolves_to_the_narrow_package_root(self) -> None:
        marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
        marketplace_root = marketplace_path.parents[2]
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual("codex-dev-skills-local", marketplace["name"])
        self.assertEqual(1, len(marketplace["plugins"]))

        entry = marketplace["plugins"][0]
        self.assertEqual("codex-dev-skills", entry["name"])
        self.assertEqual("local", entry["source"]["source"])
        self.assertEqual("./plugin/codex-dev-skills", entry["source"]["path"])
        resolved = (marketplace_root / entry["source"]["path"]).resolve()
        self.assertEqual(PACKAGE_ROOT.resolve(), resolved)
        self.assertNotEqual(ROOT.resolve(), resolved)
        self.assertTrue((resolved / ".codex-plugin" / "plugin.json").is_file())

    def test_generated_package_matches_tracked_allowlist(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts" / "project-python"), "scripts/sync-plugin-package.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        packaged_paths = {
            path.relative_to(PACKAGE_ROOT).as_posix()
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_file()
        }
        top_level_parts = {
            pathlib.PurePosixPath(path).parts[0] for path in packaged_paths
        }
        self.assertFalse({".git", ".gitnexus", ".work"} & top_level_parts)

    def test_packaged_policy_resources_are_git_tracked(self) -> None:
        tracked = subprocess.run(
            ["git", "ls-files", "-z", "--", "policies", "docs"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8").split("\0")
        self.assertIn("policies/github-control-plane-policy.md", tracked)

    def test_generator_rejects_every_extra_package_entry_kind(self) -> None:
        cases = ("ignored-tree", "empty-directory", "symlink", "special")
        for kind in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(
                prefix="plugin-inventory-"
            ) as temp_dir:
                package_root = pathlib.Path(temp_dir) / "package"
                shutil.copytree(PACKAGE_ROOT, package_root)
                if kind == "ignored-tree":
                    sentinel = package_root / ".gitnexus" / "private-sentinel"
                    sentinel.parent.mkdir()
                    sentinel.write_text("must be rejected\n", encoding="utf-8")
                elif kind == "empty-directory":
                    (package_root / "unexpected-empty").mkdir()
                elif kind == "symlink":
                    (package_root / "unexpected-link").symlink_to(
                        ".codex-plugin/plugin.json"
                    )
                else:
                    if not hasattr(os, "mkfifo"):
                        self.skipTest("mkfifo is unavailable")
                    os.mkfifo(package_root / "unexpected-fifo")

                result = subprocess.run(
                    [
                        str(ROOT / "scripts" / "project-python"),
                        "scripts/sync-plugin-package.py",
                        "--package-root",
                        str(package_root),
                    ],
                    cwd=ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(0, result.returncode)
                self.assertIn("unexpected plugin", result.stderr)

    def test_skill_relative_resources_resolve_from_source_and_package(self) -> None:
        reference_pattern = re.compile(r"`(../../(?:policies|templates|docs)/[^`]+)`")
        bare_resource_pattern = re.compile(r"`(?:policies|templates)/[^`]+`")
        references = 0
        for skill_path in sorted((ROOT / "skills").glob("*/SKILL.md")):
            skill_text = skill_path.read_text(encoding="utf-8")
            self.assertIsNone(bare_resource_pattern.search(skill_text), skill_path)
            relative_skill = skill_path.relative_to(ROOT)
            packaged_skill = PACKAGE_ROOT / relative_skill
            for reference in reference_pattern.findall(skill_text):
                references += 1
                self.assertTrue(
                    (skill_path.parent / reference).resolve().is_file(),
                    f"{skill_path}: {reference}",
                )
                self.assertTrue(
                    (packaged_skill.parent / reference).resolve().is_file(),
                    f"{packaged_skill}: {reference}",
                )
        self.assertGreater(references, 20)

    def test_template_references_pair_source_plugin_and_filesystem_paths(self) -> None:
        source_pattern = re.compile(
            r"`../../templates/orchestration/([^`]+)`"
        )
        for skill_name in TEMPLATE_SKILLS:
            skill = ROOT / "skills" / skill_name / "SKILL.md"
            skill_text = skill.read_text(encoding="utf-8")
            references = source_pattern.findall(skill_text)
            self.assertTrue(references, skill)
            for filename in set(references):
                filesystem_reference = (
                    "`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/"
                    f"orchestration/{filename}`"
                )
                self.assertEqual(
                    references.count(filename),
                    skill_text.count(filesystem_reference),
                    f"{skill}: {filename}",
                )

    def test_policy_references_pair_source_plugin_and_filesystem_paths(self) -> None:
        source_pattern = re.compile(r"`../../policies/([^`]+)`")
        references = 0
        for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
            skill_text = skill.read_text(encoding="utf-8")
            filenames = source_pattern.findall(skill_text)
            references += len(filenames)
            for filename in set(filenames):
                filesystem_reference = (
                    "`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/"
                    f"orchestration/policies/{filename}`"
                )
                self.assertEqual(
                    filenames.count(filename),
                    skill_text.count(filesystem_reference),
                    f"{skill}: {filename}",
                )
        self.assertGreater(references, 10)

    def _assert_isolated_filesystem_install_resolves_templates(
        self, custom_templates: bool
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="plugin-fallback-install-") as temp_dir:
            root = pathlib.Path(temp_dir).resolve()
            home = root / "home"
            home.mkdir()
            env = os.environ.copy()
            for name in INSTALLER_ENV_OVERRIDES:
                env.pop(name, None)
            env.update(
                {
                    "HOME": str(home),
                    "XDG_STATE_HOME": str(root / "state"),
                }
            )
            templates_root = home / ".codex" / "templates"
            if custom_templates:
                templates_root = root / "custom" / "templates"
                env.update(
                    {
                        "CODEX_TEMPLATES_DIR": str(templates_root),
                        "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
                    }
                )
            result = subprocess.run(
                [str(ROOT / "install.sh"), "install", "codex-delivery-workflow"],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stderr)

            installed_skills = home / ".agents" / "skills"
            source_pattern = re.compile(
                r"`../../templates/orchestration/([^`]+)`"
            )
            for skill_name in TEMPLATE_SKILLS:
                installed_skill = installed_skills / skill_name / "SKILL.md"
                self.assertTrue(installed_skill.is_file(), installed_skill)
                filenames = source_pattern.findall(
                    installed_skill.read_text(encoding="utf-8")
                )
                self.assertTrue(filenames, installed_skill)
                for filename in filenames:
                    self.assertTrue(
                        (templates_root / "orchestration" / filename).is_file(),
                        f"{installed_skill}: {filename}",
                    )

    def test_default_template_root_resolves_installed_skill_fallbacks(self) -> None:
        self._assert_isolated_filesystem_install_resolves_templates(False)

    def test_custom_template_root_resolves_installed_skill_fallbacks(self) -> None:
        self._assert_isolated_filesystem_install_resolves_templates(True)

    def test_manifest_catalog_and_installer_versions_agree(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        catalog = (ROOT / "catalog.yaml").read_text(encoding="utf-8")
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn(f'version: "{manifest["version"]}"', catalog)
        self.assertIn(f'VERSION="{manifest["version"]}"', installer)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI is required for plugin cache smoke")
    def test_isolated_cli_cache_excludes_checkout_and_ignored_sentinel(self) -> None:
        sentinel = ROOT / ".gitnexus" / "plugin-package-private-sentinel"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("must not enter plugin cache\n", encoding="utf-8")
        self.addCleanup(sentinel.unlink, missing_ok=True)

        with tempfile.TemporaryDirectory(prefix="codex-plugin-home-") as temp_dir:
            codex_home = pathlib.Path(temp_dir) / "codex-home"
            codex_home.mkdir()
            env = os.environ.copy()
            env["CODEX_HOME"] = str(codex_home)
            commands = (
                ["codex", "plugin", "marketplace", "add", ".", "--json"],
                ["codex", "plugin", "add", "codex-dev-skills@codex-dev-skills-local", "--json"],
            )
            for command in commands:
                result = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, result.returncode, result.stderr)

            cache_root = codex_home / "plugins" / "cache"
            cache_files = [path for path in cache_root.rglob("*") if path.is_file()]
            self.assertTrue(cache_files)
            self.assertFalse(any(path.name == sentinel.name for path in cache_files))
            relative_parts = [path.relative_to(cache_root).parts for path in cache_files]
            for forbidden in (".git", ".gitnexus", ".work"):
                self.assertFalse(any(forbidden in parts for parts in relative_parts), forbidden)

            cached_manifests = list(cache_root.rglob(".codex-plugin/plugin.json"))
            self.assertEqual(1, len(cached_manifests))
            cached_package = cached_manifests[0].parents[1]
            reference_pattern = re.compile(
                r"`(\.\./\.\./(?:policies|templates|docs)/[^`]+)`"
            )
            resolved_resources = 0
            for cached_skill in sorted((cached_package / "skills").glob("*/SKILL.md")):
                for reference in reference_pattern.findall(
                    cached_skill.read_text(encoding="utf-8")
                ):
                    resolved_resources += 1
                    self.assertTrue(
                        (cached_skill.parent / reference).resolve().is_file(),
                        f"{cached_skill}: {reference}",
                    )
            self.assertGreater(resolved_resources, 20)


if __name__ == "__main__":
    unittest.main()
