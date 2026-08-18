from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
INSTALLER_ENV_OVERRIDES = (
    "CODEX_CLI",
    "CODEX_SKILLS_DIR",
    "CODEX_TEMPLATES_DIR",
    "CODEX_CUSTOM_AGENTS_DIR",
    "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS",
    "CODEX_DEV_SKILLS_TARGET",
)


class RuntimeGroupInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()

    def installer_env(self, home_name: str) -> tuple[pathlib.Path, dict[str, str]]:
        home = self.root / home_name
        home.mkdir(exist_ok=True)
        env = os.environ.copy()
        for name in INSTALLER_ENV_OVERRIDES:
            env.pop(name, None)
        env.update(
            {
                "HOME": str(home),
                "XDG_STATE_HOME": str(self.root / f"{home_name}-state"),
            }
        )
        return home, env

    def run_installer(
        self,
        *arguments: str,
        home_name: str,
        env_overrides: dict[str, str] | None = None,
    ) -> tuple[pathlib.Path, subprocess.CompletedProcess[str]]:
        home, env = self.installer_env(home_name)
        if env_overrides:
            env.update(env_overrides)
        result = subprocess.run(
            [str(INSTALLER), *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return home, result

    def install(self, group: str, home_name: str) -> pathlib.Path:
        home, result = self.run_installer(
            "install", group, home_name=home_name
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return home / ".agents" / "skills"

    def fake_mv_overrides(self, name: str, mode: str) -> dict[str, str]:
        fake_bin = self.root / f"{name}-bin"
        fake_bin.mkdir()
        real_mv = shutil.which("mv")
        self.assertIsNotNone(real_mv)
        fake_mv = fake_bin / "mv"
        fake_mv.write_text(
            "#!/bin/sh\n"
            "case \"${FAKE_MV_MODE:-}\" in\n"
            "  fail-backup)\n"
            "    case \"$2\" in *.bak) echo 'injected backup rename failure' >&2; exit 71 ;; esac\n"
            "    ;;\n"
            "  fail-replace-and-restore)\n"
            "    case \"$1\" in\n"
            "      *.tmp.*/value) echo 'injected replacement failure' >&2; exit 72 ;;\n"
            "      *.bak) echo 'injected restore failure' >&2; exit 73 ;;\n"
            "    esac\n"
            "    ;;\n"
            "esac\n"
            f'exec "{real_mv}" "$@"\n',
            encoding="utf-8",
        )
        fake_mv.chmod(0o755)
        return {
            "FAKE_MV_MODE": mode,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        }

    def test_cli_group_installs_adapter_over_delivery_layer(self) -> None:
        skills = self.install("codex-cli-session-handoff", "cli-home")

        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "code-review-gate" / "SKILL.md").is_file())
        self.assertFalse((skills / "desktop-project-delivery").exists())

    def test_desktop_group_does_not_install_cli_adapter(self) -> None:
        skills = self.install("desktop-delivery-workflow", "desktop-home")

        self.assertTrue((skills / "desktop-project-delivery" / "SKILL.md").is_file())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertFalse((skills / "cli-session-handoff").exists())

    def test_cli_uninstall_preserves_dependencies_and_desktop_groups(
        self,
    ) -> None:
        skills = self.install("desktop-delivery-workflow", "shared-home")
        self.install("codex-review-workflow", "shared-home")
        self.install("codex-cli-session-handoff", "shared-home")

        _, result = self.run_installer(
            "uninstall",
            "codex-cli-session-handoff",
            "--yes",
            home_name="shared-home",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((skills / "cli-session-handoff").exists())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "code-review-gate" / "SKILL.md").is_file())
        self.assertTrue(
            (skills / "desktop-project-delivery" / "SKILL.md").is_file()
        )

    def test_dependency_uninstall_refuses_installed_dependents(self) -> None:
        skills = self.install("codex-cli-session-handoff", "protected-home")

        _, result = self.run_installer(
            "uninstall",
            "codex-delivery-workflow",
            "--yes",
            home_name="protected-home",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("still depend on", result.stderr)
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())

    def test_installer_environment_does_not_escape_fixture(self) -> None:
        external_skills = self.root / "external" / "skills"
        external_templates = self.root / "external" / "templates"
        external_skills.mkdir(parents=True)
        external_templates.mkdir(parents=True)
        sentinel = external_skills / "sentinel.txt"
        sentinel.write_text("unchanged\n", encoding="utf-8")
        inherited = {
            "CODEX_SKILLS_DIR": str(external_skills),
            "CODEX_TEMPLATES_DIR": str(external_templates),
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
            "CODEX_DEV_SKILLS_TARGET": "agents",
        }

        with mock.patch.dict(os.environ, inherited):
            skills = self.install("codex-cli-session-handoff", "isolated-home")

        self.assertEqual("unchanged\n", sentinel.read_text(encoding="utf-8"))
        self.assertEqual([], list(external_templates.iterdir()))
        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())

    def test_differing_existing_skill_fails_before_expanded_group_mutation(self) -> None:
        home, env = self.installer_env("collision-home")
        conflicting = home / ".agents" / "skills" / "loop-engineering"
        conflicting.mkdir(parents=True)
        sentinel = conflicting / "SKILL.md"
        sentinel.write_text("imported local workflow\n", encoding="utf-8")

        result = subprocess.run(
            [str(INSTALLER), "install", "codex-cli-session-handoff"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing to overwrite differing installed or imported artifacts", result.stderr)
        self.assertEqual("imported local workflow\n", sentinel.read_text(encoding="utf-8"))
        self.assertFalse((home / ".agents" / "skills" / "cli-session-handoff").exists())
        self.assertFalse((home / ".codex" / "templates" / "orchestration").exists())

    def test_template_collision_fails_before_other_target_roots_are_created(self) -> None:
        home, env = self.installer_env("template-collision-home")
        conflicting = (
            home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "agent-delegation-policy.md"
        )
        conflicting.parent.mkdir(parents=True)
        conflicting.write_text("imported template\n", encoding="utf-8")

        result = subprocess.run(
            [str(INSTALLER), "install", "shared-review-gates"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing to overwrite differing installed or imported artifacts", result.stderr)
        self.assertEqual("imported template\n", conflicting.read_text(encoding="utf-8"))
        self.assertFalse((home / ".agents").exists())
        self.assertFalse((self.root / "template-collision-home-state").exists())

    def test_installed_plugin_refuses_filesystem_install_before_mutation(self) -> None:
        fake_cli = self.root / "fake-codex"
        fake_cli.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '{\"installed\":[{\"name\":\"codex-dev-skills\",\"installed\":true}]}'\n",
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="plugin-collision-home",
            env_overrides={"CODEX_CLI": str(fake_cli)},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("codex-dev-skills plugin is installed", result.stderr)
        self.assertFalse((home / ".agents").exists())
        self.assertFalse((home / ".codex").exists())

    def test_symlinked_cli_is_resolved_for_plugin_collision_check(self) -> None:
        real_cli = self.root / "real-codex"
        real_cli.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '{\"installed\":[{\"name\":\"codex-dev-skills\",\"installed\":true}]}'\n",
            encoding="utf-8",
        )
        real_cli.chmod(0o755)
        linked_cli = self.root / "codex"
        linked_cli.symlink_to(real_cli)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="symlinked-cli-home",
            env_overrides={"CODEX_CLI": str(linked_cli)},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("codex-dev-skills plugin is installed", result.stderr)
        self.assertNotIn("Ignoring unsafe or unavailable", result.stderr)
        self.assertFalse((home / ".agents").exists())

    def test_update_conflicts_are_preflighted_before_expanded_group_mutation(self) -> None:
        home, installed = self.run_installer(
            "install", "codex-cli-session-handoff", home_name="update-preflight-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        missing_skill = home / ".agents" / "skills" / "closure-triage"
        shutil.rmtree(missing_skill)
        modified_template = (
            home
            / ".codex"
            / "templates"
            / "workflows"
            / "loop-engineering-workflow.md"
        )
        modified_template.write_text("local imported workflow\n", encoding="utf-8")

        _, result = self.run_installer(
            "update", "codex-cli-session-handoff", home_name="update-preflight-home"
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing a partial update", result.stderr)
        self.assertFalse(missing_skill.exists())
        self.assertEqual(
            "local imported workflow\n",
            modified_template.read_text(encoding="utf-8"),
        )

    def test_force_update_backup_collisions_are_preflighted_for_all_artifacts(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="force-preflight-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        first = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        second = home / ".agents" / "skills" / "task-continuation" / "SKILL.md"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        second.parent.with_name("task-continuation.bak").mkdir()

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="force-preflight-home",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("existing backup path", result.stderr)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertFalse(first.parent.with_name("closure-triage.bak").exists())

    def test_file_backup_rename_failure_preserves_target_and_cleans_staging(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="file-rename-failure-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        target = (
            home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "agent-delegation-policy.md"
        )
        target.write_text("local template edit\n", encoding="utf-8")

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="file-rename-failure-home",
            env_overrides=self.fake_mv_overrides("file-rename-failure", "fail-backup"),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("failed to create backup for template", result.stderr)
        self.assertEqual("local template edit\n", target.read_text(encoding="utf-8"))
        self.assertFalse(target.with_suffix(".md.bak").exists())
        self.assertEqual([], list(target.parent.glob(".codex-dev-skills.*.tmp.*")))

    def test_directory_restore_failure_reports_backup_and_cleans_staging(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="dir-restore-failure-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        target = home / ".agents" / "skills" / "closure-triage"
        marker = target / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        backup = target.with_name("closure-triage.bak")

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="dir-restore-failure-home",
            env_overrides=self.fake_mv_overrides(
                "dir-restore-failure", "fail-replace-and-restore"
            ),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("failed to replace skill closure-triage", result.stderr)
        self.assertIn("CRITICAL: failed to restore skill closure-triage", result.stderr)
        self.assertFalse(target.exists())
        self.assertEqual("local skill edit\n", (backup / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual([], list(backup.parent.glob(".codex-dev-skills.*.tmp.*")))

    def test_unsupported_plugin_list_warns_and_preserves_filesystem_fallback(self) -> None:
        fake_cli = self.root / "old-codex"
        fake_cli.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        fake_cli.chmod(0o755)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="old-cli-home",
            env_overrides={"CODEX_CLI": str(fake_cli)},
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("does not expose a readable plugin list", result.stderr)
        self.assertTrue((home / ".agents" / "skills" / "closure-triage" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
