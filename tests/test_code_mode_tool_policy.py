from __future__ import annotations

import os
import hashlib
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
VALIDATOR = ROOT / "scripts" / "validate-code-mode-tool-policy.py"
POLICY_SOURCE = ROOT / "policies" / "code-mode-tool-orchestration-policy.md"
INSTALLED_POLICY = (
    pathlib.Path("orchestration")
    / "policies"
    / "code-mode-tool-orchestration-policy.md"
)
INSTALL_GROUPS = (
    "shared-review-gates",
    "codex-review-workflow",
    "codex-delivery-workflow",
    "codex-cli-session-handoff",
    "desktop-delivery-workflow",
    "codex-agent-profiles",
)
INSTALLER_ENV_OVERRIDES = (
    "CODEX_SKILLS_DIR",
    "CODEX_TEMPLATES_DIR",
    "CODEX_CUSTOM_AGENTS_DIR",
    "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS",
    "CODEX_DEV_SKILLS_TARGET",
)


def managed_backup_path(
    state_root: pathlib.Path,
    target_root: pathlib.Path,
    artifact_kind: str,
    relative_target: str,
) -> pathlib.Path:
    root_digest = hashlib.sha256(
        str(target_root.resolve()).encode("utf-8")
    ).hexdigest()
    return (
        state_root
        / "codex-dev-skills"
        / "backups"
        / "v1"
        / root_digest
        / artifact_kind
        / f"{relative_target}.bak"
    )


class CodeModeToolPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()

    def isolated_env(self, name: str) -> tuple[pathlib.Path, dict[str, str]]:
        home = self.root / name
        home.mkdir()
        env = os.environ.copy()
        for variable in INSTALLER_ENV_OVERRIDES:
            env.pop(variable, None)
        env.update(
            {
                "HOME": str(home),
                "XDG_STATE_HOME": str(self.root / f"{name}-state"),
            }
        )
        return home, env

    def run_installer(
        self,
        installer: pathlib.Path,
        env: dict[str, str],
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(installer), *arguments],
            cwd=installer.parent,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def copy_fixture(self, name: str) -> pathlib.Path:
        fixture = self.root / name
        fixture.mkdir()
        shutil.copy2(INSTALLER, fixture / "install.sh")
        shutil.copy2(ROOT / "catalog.yaml", fixture / "catalog.yaml")
        for item in (
            "agent-profiles",
            "docs",
            "policies",
            "skills",
            "templates",
            "workflows",
        ):
            shutil.copytree(ROOT / item, fixture / item)
        return fixture

    def run_validator(
        self, repo_root: pathlib.Path, *arguments: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                os.environ.get("PYTHON", "python3"),
                str(VALIDATOR),
                "--repo-root",
                str(repo_root),
                *arguments,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_source_policy_references_and_manifest_are_consistent(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

        manifest = subprocess.run(
            [str(INSTALLER), "manifest"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, manifest.returncode, manifest.stderr)
        self.assertIn(
            "shared-review-gates source: "
            "policies/code-mode-tool-orchestration-policy.md",
            manifest.stdout,
        )

    def test_every_related_group_deploys_the_policy(self) -> None:
        for group in INSTALL_GROUPS:
            with self.subTest(group=group):
                home, env = self.isolated_env(f"{group}-home")
                result = self.run_installer(INSTALLER, env, "install", group)
                self.assertEqual(0, result.returncode, result.stderr)
                target = home / ".codex" / "templates" / INSTALLED_POLICY
                self.assertTrue(target.is_file(), target)
                self.assertEqual(POLICY_SOURCE.read_bytes(), target.read_bytes())

    def test_installed_skills_resolve_the_installed_policy_reference(self) -> None:
        home, env = self.isolated_env("all-home")
        installed = self.run_installer(INSTALLER, env, "install", "--all")
        self.assertEqual(0, installed.returncode, installed.stderr)

        result = self.run_validator(
            ROOT,
            "--installed-skills-root",
            str(home / ".agents" / "skills"),
            "--installed-templates-root",
            str(home / ".codex" / "templates"),
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_force_update_syncs_a_policy_source_change(self) -> None:
        fixture = self.copy_fixture("update-fixture")
        home, env = self.isolated_env("update-home")
        installer = fixture / "install.sh"
        installed = self.run_installer(
            installer, env, "install", "shared-review-gates"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)

        source = fixture / POLICY_SOURCE.relative_to(ROOT)
        target = home / ".codex" / "templates" / INSTALLED_POLICY
        original = target.read_bytes()
        source.write_text(
            source.read_text(encoding="utf-8")
            + "\n<!-- isolated update propagation marker -->\n",
            encoding="utf-8",
        )

        updated = self.run_installer(
            installer, env, "update", "shared-review-gates", "--force"
        )
        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertEqual(source.read_bytes(), target.read_bytes())
        backup = managed_backup_path(
            self.root / "update-home-state",
            home / ".codex" / "templates",
            "templates",
            INSTALLED_POLICY.as_posix(),
        )
        self.assertEqual(original, backup.read_bytes())
        self.assertFalse(target.with_suffix(".md.bak").exists())

    def test_consistency_check_rejects_missing_policy(self) -> None:
        fixture = self.copy_fixture("missing-policy-fixture")
        (fixture / POLICY_SOURCE.relative_to(ROOT)).unlink()
        installed_skills = fixture / "installed" / "skills"
        installed_templates = fixture / "installed" / "templates"
        installed_skills.mkdir(parents=True)
        installed_templates.mkdir(parents=True)
        installed_policy = installed_templates / INSTALLED_POLICY
        installed_policy.parent.mkdir(parents=True)
        installed_policy.write_text("orphaned installed policy\n", encoding="utf-8")

        result = self.run_validator(
            fixture,
            "--installed-skills-root",
            str(installed_skills),
            "--installed-templates-root",
            str(installed_templates),
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing or unsafe policy source", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_consistency_check_rejects_wrong_installed_reference(self) -> None:
        fixture = self.copy_fixture("wrong-reference-fixture")
        skill = fixture / "skills" / "planning" / "SKILL.md"
        skill.write_text(
            skill.read_text(encoding="utf-8").replace(
                "orchestration/policies/code-mode-tool-orchestration-policy.md",
                "orchestration/policies/missing-code-mode-policy.md",
            ),
            encoding="utf-8",
        )

        result = self.run_validator(fixture)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("incomplete Code Mode policy reference pair", result.stdout)

    def test_consistency_check_does_not_execute_fixture_installer(self) -> None:
        fixture = self.copy_fixture("untrusted-installer-fixture")
        marker = fixture / "manifest"
        touch = shutil.which("touch")
        self.assertIsNotNone(touch)
        fixture_installer = fixture / "install.sh"
        fixture_installer.unlink()
        fixture_installer.symlink_to(touch)

        result = self.run_validator(fixture)

        self.assertFalse(marker.exists(), "validator executed fixture install.sh")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_consistency_check_rejects_symlinked_markdown(self) -> None:
        fixture = self.copy_fixture("symlink-markdown-fixture")
        target = fixture / "outside.txt"
        target.write_text("safe target\n", encoding="utf-8")
        (fixture / "blocking.md").symlink_to(target)

        result = self.run_validator(fixture)

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "blocking.md must be a regular non-symlink file",
            result.stdout,
        )

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO creation is unavailable")
    def test_consistency_check_rejects_fifo_markdown_without_blocking(self) -> None:
        fixture = self.copy_fixture("fifo-markdown-fixture")
        os.mkfifo(fixture / "blocking.md")

        result = subprocess.run(
            [
                os.environ.get("PYTHON", "python3"),
                str(VALIDATOR),
                "--repo-root",
                str(fixture),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "blocking.md must be a regular non-symlink file",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
