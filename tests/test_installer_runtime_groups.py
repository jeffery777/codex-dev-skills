from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
INSTALLER_ENV_OVERRIDES = (
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
        self, *arguments: str, home_name: str
    ) -> tuple[pathlib.Path, subprocess.CompletedProcess[str]]:
        home, env = self.installer_env(home_name)
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


if __name__ == "__main__":
    unittest.main()
