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
SOURCE_PROFILES = ROOT / "agent-profiles"
PROFILE_NAMES = sorted(path.name for path in SOURCE_PROFILES.glob("*.toml"))


class AgentProfileInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.root / "state"),
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_installer(self, *args: str, env=None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(INSTALLER), *args], cwd=ROOT, env=env or self.env,
            text=True, capture_output=True, check=False,
        )

    def copy_installer_fixture(self, name: str) -> pathlib.Path:
        destination = self.root / name
        destination.mkdir()
        shutil.copy2(INSTALLER, destination / "install.sh")
        for item in ("agent-profiles", "docs", "policies", "skills", "templates", "workflows"):
            shutil.copytree(ROOT / item, destination / item)
        return destination

    def test_all_excludes_opt_in_profiles(self) -> None:
        result = self.run_installer("install", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((self.home / ".codex" / "agents").exists())

    def test_default_and_legacy_skill_targets_are_explicit(self) -> None:
        help_result = self.run_installer("help")
        self.assertEqual(0, help_result.returncode, help_result.stderr)
        self.assertIn("~/.agents/skills/<skill>/ by default", help_result.stdout)
        self.assertIn("CODEX_DEV_SKILLS_TARGET=legacy", help_result.stdout)
        self.assertIn("never moved or removed automatically", help_result.stdout)

        default = self.run_installer("install", "shared-review-gates")
        self.assertEqual(0, default.returncode, default.stderr)
        self.assertTrue(
            (self.home / ".agents" / "skills" / "code-review-gate" / "SKILL.md").is_file()
        )
        legacy_conflict_env = {**self.env, "CODEX_DEV_SKILLS_TARGET": "legacy"}
        legacy_conflict = self.run_installer(
            "install", "shared-review-gates", env=legacy_conflict_env
        )
        self.assertNotEqual(0, legacy_conflict.returncode)
        self.assertIn("alternate discovery root", legacy_conflict.stderr)

        legacy_home = self.root / "legacy-home"
        legacy_home.mkdir()
        legacy_env = {
            **self.env,
            "HOME": str(legacy_home),
            "CODEX_DEV_SKILLS_TARGET": "legacy",
        }
        legacy = self.run_installer("install", "shared-review-gates", env=legacy_env)
        self.assertEqual(0, legacy.returncode, legacy.stderr)
        self.assertTrue(
            (legacy_home / ".codex" / "skills" / "code-review-gate" / "SKILL.md").is_file()
        )
        self.assertFalse((legacy_home / ".agents").exists())

    def test_cross_root_collision_fails_before_install_mutation_and_status_reports_it(self) -> None:
        legacy_skill = self.home / ".codex" / "skills" / "code-review-gate"
        legacy_skill.mkdir(parents=True)
        legacy_skill.joinpath("SKILL.md").write_text("legacy\n", encoding="utf-8")

        refused = self.run_installer("install", "shared-review-gates")
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("alternate discovery root", refused.stderr)
        self.assertIn("Existing installs are not moved or removed automatically", refused.stderr)
        self.assertFalse((self.home / ".agents").exists())
        self.assertFalse((self.home / ".codex" / "templates").exists())
        self.assertFalse((self.root / "state" / "codex-dev-skills").exists())
        self.assertEqual("legacy\n", legacy_skill.joinpath("SKILL.md").read_text(encoding="utf-8"))

        alternate_status = self.run_installer("status")
        self.assertEqual(0, alternate_status.returncode, alternate_status.stderr)
        self.assertIn(
            "Alternate-root managed skill detected: code-review-gate",
            alternate_status.stdout,
        )

        current_skill = self.home / ".agents" / "skills" / "code-review-gate"
        current_skill.mkdir(parents=True)
        current_skill.joinpath("SKILL.md").write_text("current\n", encoding="utf-8")
        status = self.run_installer("status")
        self.assertEqual(0, status.returncode, status.stderr)
        self.assertIn("Codex skills target mode: agents", status.stdout)
        self.assertIn(f"Alternate discovery target: {self.home / '.codex' / 'skills'}", status.stdout)
        self.assertIn("Cross-target skill collision: code-review-gate", status.stdout)

    def test_explicit_install_is_exact_and_idempotent(self) -> None:
        first = self.run_installer("install", "codex-agent-profiles")
        self.assertEqual(0, first.returncode, first.stderr)
        target = self.home / ".codex" / "agents"
        self.assertEqual(PROFILE_NAMES, sorted(path.name for path in target.glob("*.toml")))
        for name in PROFILE_NAMES:
            self.assertEqual((SOURCE_PROFILES / name).read_bytes(), (target / name).read_bytes())
        installed_skill = self.home / ".agents" / "skills" / "loop-engineering"
        self.assertTrue(
            (self.home / ".agents" / "skills" / "code-review-gate" / "SKILL.md").is_file()
        )
        self.assertTrue(
            (
                self.home
                / ".codex"
                / "templates"
                / "orchestration"
                / "agent-routing-integration.template.yaml"
            ).is_file()
        )
        for relative in (
            "scripts/agent_routing.py",
            "scripts/loopctl.py",
            "scripts/memory_contract.py",
            "scripts/memoryctl.py",
            "scripts/profile_preflight.py",
            "references/agent-profile-registry.json",
            "references/memory-contract-v1.md",
        ):
            self.assertTrue((installed_skill / relative).is_file(), relative)
        deployed_validation = subprocess.run(
            [
                os.environ.get("PYTHON", "python3"),
                str(installed_skill / "scripts" / "profile_preflight.py"),
                "--profile-dir", str(target),
                "--destination-root", str(target),
            ],
            cwd=ROOT, env=self.env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(0, deployed_validation.returncode, deployed_validation.stderr)
        second = self.run_installer("install", "codex-agent-profiles")
        self.assertEqual(0, second.returncode, second.stderr)

        status = self.run_installer("status")
        self.assertEqual(0, status.returncode, status.stderr)
        self.assertIn(f"Custom agents target: {target}", status.stdout)
        self.assertIn('"group":"codex-agent-profiles"', status.stdout)
        self.assertEqual(0, self.run_installer("diff", "codex-agent-profiles").returncode)
        target.joinpath(PROFILE_NAMES[-1]).write_text("changed\n", encoding="utf-8")
        self.assertNotEqual(0, self.run_installer("diff", "codex-agent-profiles").returncode)

    def test_project_target_requires_explicit_opt_in(self) -> None:
        target = self.root / "project" / ".codex" / "agents"
        denied_env = {**self.env, "CODEX_CUSTOM_AGENTS_DIR": str(target)}
        denied = self.run_installer("install", "codex-agent-profiles", env=denied_env)
        self.assertNotEqual(0, denied.returncode)
        self.assertIn("requires CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES", denied.stderr)

        allowed_env = {
            **denied_env,
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
        }
        allowed = self.run_installer("install", "codex-agent-profiles", env=allowed_env)
        self.assertEqual(0, allowed.returncode, allowed.stderr)
        self.assertEqual(PROFILE_NAMES, sorted(path.name for path in target.glob("*.toml")))

    def test_user_and_project_deployments_keep_separate_ownership_state(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        project_target = self.root / "project" / ".codex" / "agents"
        project_env = {
            **self.env,
            "CODEX_CUSTOM_AGENTS_DIR": str(project_target),
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
        }
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles", env=project_env).returncode)
        state_files = list((self.root / "state" / "codex-dev-skills").glob("agent-profile-*.tsv"))
        self.assertEqual(2, len(state_files))
        self.assertEqual(0, self.run_installer("uninstall", "codex-agent-profiles", "--yes").returncode)
        self.assertEqual(0, self.run_installer("uninstall", "codex-agent-profiles", "--yes", env=project_env).returncode)

    def test_existing_difference_refuses_then_force_update_backs_up(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target = self.home / ".codex" / "agents" / PROFILE_NAMES[0]
        target.write_text("user modification\n", encoding="utf-8")
        refused = self.run_installer("update", "codex-agent-profiles")
        self.assertNotEqual(0, refused.returncode)
        self.assertEqual("user modification\n", target.read_text(encoding="utf-8"))

        forced = self.run_installer("update", "codex-agent-profiles", "--force")
        self.assertEqual(0, forced.returncode, forced.stderr)
        self.assertEqual("user modification\n", target.with_suffix(".toml.bak").read_text(encoding="utf-8"))
        self.assertEqual((SOURCE_PROFILES / PROFILE_NAMES[0]).read_bytes(), target.read_bytes())

    def test_force_update_backup_collision_is_preflighted_for_whole_group(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target_dir = self.home / ".codex" / "agents"
        first = target_dir / "loop_v2a_fast_explorer.toml"
        second = target_dir / "loop_v2a_balanced_worker.toml"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        second.with_suffix(".toml.bak").write_text("existing backup\n", encoding="utf-8")

        result = self.run_installer("update", "codex-agent-profiles", "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertFalse(first.with_suffix(".toml.bak").exists())

    def test_tampered_sources_fail_before_any_target_mutation(self) -> None:
        cases = {
            "unsafe-sandbox": ("unsafe sandbox", 'sandbox_mode = "read-only"', 'sandbox_mode = "danger-full-access"'),
            "digest-mismatch": ("differs from its TOML source", None, None),
        }
        for mutation, (expected_error, old, new) in cases.items():
            for action in ("install", "update"):
                with self.subTest(mutation=mutation, action=action):
                    fixture = self.copy_installer_fixture(f"fixture-{mutation}-{action}")
                    profile = fixture / "agent-profiles" / "loop_v2a_fast_explorer.toml"
                    if old is None:
                        profile.write_text(profile.read_text(encoding="utf-8") + "\n# digest mismatch\n", encoding="utf-8")
                    else:
                        profile.write_text(profile.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
                    case_home = self.root / f"home-{mutation}-{action}"
                    case_home.mkdir()
                    case_state = self.root / f"state-{mutation}-{action}"
                    env = {**self.env, "HOME": str(case_home), "XDG_STATE_HOME": str(case_state)}
                    result = subprocess.run(
                        [str(fixture / "install.sh"), action, "codex-agent-profiles"],
                        cwd=fixture, env=env, text=True, capture_output=True, check=False,
                    )
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(expected_error, result.stderr)
                    self.assertFalse((case_home / ".codex").exists())
                    self.assertFalse((case_state / "codex-dev-skills").exists())

    def test_install_collision_is_preflighted_before_any_expanded_group_mutation(self) -> None:
        target_dir = self.home / ".codex" / "agents"
        target_dir.mkdir(parents=True)
        collision = target_dir / "loop_v2a_balanced_worker.toml"
        collision.write_text("existing config\n", encoding="utf-8")
        skill = self.home / ".agents" / "skills" / "loop-engineering" / "SKILL.md"
        template = self.home / ".codex" / "templates" / "docs" / "native-runtime-capabilities.md"
        skill.parent.mkdir(parents=True)
        template.parent.mkdir(parents=True)
        skill.write_bytes(b"customized skill\n")
        template.write_bytes(b"customized template\n")
        skill_before = skill.read_bytes()
        template_before = template.read_bytes()
        result = self.run_installer("install", "codex-agent-profiles")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([collision.name], sorted(path.name for path in target_dir.glob("*.toml")))
        self.assertEqual("existing config\n", collision.read_text(encoding="utf-8"))
        self.assertEqual(skill_before, skill.read_bytes())
        self.assertEqual(template_before, template.read_bytes())
        self.assertFalse((self.root / "state" / "codex-dev-skills").exists())

    def test_uninstall_refuses_modified_profile_and_preserves_dependencies(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target = self.home / ".codex" / "agents" / PROFILE_NAMES[0]
        target.write_text("user modification\n", encoding="utf-8")
        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(target.exists())
        self.assertEqual(PROFILE_NAMES, sorted(path.name for path in target.parent.glob("*.toml")))
        self.assertTrue((self.home / ".agents" / "skills" / "loop-engineering").is_dir())

    def test_unmodified_uninstall_removes_profiles_only(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target_dir = self.home / ".codex" / "agents"
        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], list(target_dir.glob("*.toml")))
        self.assertTrue((self.home / ".agents" / "skills" / "loop-engineering").is_dir())

    def test_uninstall_requires_matching_legacy_target_and_preserves_templates(self) -> None:
        legacy_env = {**self.env, "CODEX_DEV_SKILLS_TARGET": "legacy"}
        installed = self.run_installer(
            "install", "shared-review-gates", env=legacy_env
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        state_file = (
            self.root / "state" / "codex-dev-skills" / "installed.jsonl"
        )
        self.assertIn(
            '"target_mode":"legacy"',
            state_file.read_text(encoding="utf-8"),
        )
        legacy_skill = (
            self.home / ".codex" / "skills" / "code-review-gate" / "SKILL.md"
        )
        runtime_template = (
            self.home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "runtime-compatibility-policy.md"
        )
        self.assertTrue(legacy_skill.is_file())
        self.assertTrue(runtime_template.is_file())

        refused = self.run_installer(
            "uninstall", "shared-review-gates", "--yes"
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("wrong skill target", refused.stderr)
        self.assertTrue(legacy_skill.is_file())
        self.assertTrue(runtime_template.is_file())
        self.assertFalse((self.home / ".agents").exists())

        removed = self.run_installer(
            "uninstall", "shared-review-gates", "--yes", env=legacy_env
        )
        self.assertEqual(0, removed.returncode, removed.stderr)
        self.assertFalse(legacy_skill.exists())
        self.assertFalse(runtime_template.exists())

    def test_uninstall_preserves_templates_used_by_alternate_root_dependents(self) -> None:
        installed = self.run_installer("install", "shared-review-gates")
        self.assertEqual(0, installed.returncode, installed.stderr)
        selected_skill = (
            self.home / ".agents" / "skills" / "code-review-gate" / "SKILL.md"
        )
        runtime_template = (
            self.home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "runtime-compatibility-policy.md"
        )
        alternate_dependent = (
            self.home / ".codex" / "skills" / "project-delivery" / "SKILL.md"
        )
        alternate_dependent.parent.mkdir(parents=True)
        alternate_dependent.write_text("legacy dependent\n", encoding="utf-8")

        refused = self.run_installer(
            "uninstall", "shared-review-gates", "--yes"
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("dependent skills remain", refused.stderr)
        self.assertTrue(selected_skill.is_file())
        self.assertTrue(runtime_template.is_file())

    def test_uninstall_uses_recorded_digest_across_source_version_drift(self) -> None:
        target_dir = self.home / ".codex" / "agents"
        target_dir.mkdir(parents=True)
        name = PROFILE_NAMES[0]
        content = b"previous released profile\n"
        (target_dir / name).write_bytes(content)
        state_dir = self.root / "state" / "codex-dev-skills"
        state_dir.mkdir(parents=True)
        digest = hashlib.sha256(content).hexdigest()
        target_key = hashlib.sha256(str(target_dir).encode()).hexdigest()
        (state_dir / f"agent-profile-{target_key}.tsv").write_text(f"{name}\t{digest}\n", encoding="utf-8")

        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((target_dir / name).exists())

    def test_symlink_target_component_fails_closed(self) -> None:
        codex = self.home / ".codex"
        codex.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (codex / "agents").symlink_to(outside, target_is_directory=True)
        result = self.run_installer("install", "codex-agent-profiles")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing symlink target component", result.stderr)
        self.assertEqual([], list(outside.iterdir()))


if __name__ == "__main__":
    unittest.main()
