from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
SOURCE_PROFILES = ROOT / "agent-profiles"
PROFILE_NAMES = sorted(path.name for path in SOURCE_PROFILES.glob("*.toml"))


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
            "scripts/operational_evidence.py",
            "scripts/evidencectl.py",
            "scripts/improvement_lineage.py",
            "scripts/improvementctl.py",
            "scripts/improvement_proposal.py",
            "scripts/proposalctl.py",
            "scripts/candidate_evaluation.py",
            "scripts/evaluationctl.py",
            "scripts/memory_contract.py",
            "scripts/memoryctl.py",
            "scripts/profile_preflight.py",
            "references/agent-profile-registry.json",
            "references/memory-contract-v1.md",
            "references/operational-evidence-v0.md",
            "references/improvement-lineage-v0.md",
            "references/improvement-proposal-v0.md",
            "references/candidate-evaluation-v0.md",
            "references/obsidian-reference-profile-v0.json",
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

    def test_update_adds_new_profile_to_prior_managed_profile_set(self) -> None:
        installed = self.run_installer("install", "codex-agent-profiles")
        self.assertEqual(0, installed.returncode, installed.stderr)
        target = self.home / ".codex" / "agents"
        senior_name = "loop_v2a_senior_worker.toml"
        target.joinpath(senior_name).unlink()

        state_dir = self.root / "state" / "codex-dev-skills"
        receipt = next(state_dir.glob("agent-profile-*.tsv"))
        receipt.write_text(
            "".join(
                line
                for line in receipt.read_text(encoding="utf-8").splitlines(keepends=True)
                if not line.startswith(f"{senior_name}\t")
            ),
            encoding="utf-8",
        )
        installed_state = state_dir / "installed.jsonl"
        installed_state.write_text(
            installed_state.read_text(encoding="utf-8").replace(
                '"version":"0.15.0"', '"version":"0.14.2"'
            ),
            encoding="utf-8",
        )

        updated = self.run_installer("update", "codex-agent-profiles", "--force")

        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertEqual(PROFILE_NAMES, sorted(path.name for path in target.glob("*.toml")))
        expected_digest = hashlib.sha256(
            SOURCE_PROFILES.joinpath(senior_name).read_bytes()
        ).hexdigest()
        self.assertIn(
            f"{senior_name}\t{expected_digest}\n",
            receipt.read_text(encoding="utf-8"),
        )
        self.assertIn(
            '"version":"0.15.0","action":"update"',
            installed_state.read_text(encoding="utf-8"),
        )

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

    def test_default_and_custom_profile_roots_receive_distinct_managed_backup_slots(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        default_target = self.home / ".codex" / "agents" / PROFILE_NAMES[0]
        default_target.write_text("default root edit\n", encoding="utf-8")
        self.assertEqual(
            0,
            self.run_installer("update", "codex-agent-profiles", "--force").returncode,
        )

        custom_root = self.root / "project" / ".codex" / "agents"
        custom_env = {
            **self.env,
            "CODEX_CUSTOM_AGENTS_DIR": str(custom_root),
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
        }
        self.assertEqual(
            0,
            self.run_installer("install", "codex-agent-profiles", env=custom_env).returncode,
        )
        custom_target = custom_root / PROFILE_NAMES[0]
        custom_target.write_text("custom root edit\n", encoding="utf-8")
        updated = self.run_installer("update", "codex-agent-profiles", "--force", env=custom_env)
        self.assertEqual(0, updated.returncode, updated.stderr)

        default_backup = managed_backup_path(
            self.root / "state", self.home / ".codex" / "agents", "agent-profiles", PROFILE_NAMES[0]
        )
        custom_backup = managed_backup_path(
            self.root / "state", custom_root, "agent-profiles", PROFILE_NAMES[0]
        )
        self.assertNotEqual(default_backup, custom_backup)
        self.assertEqual("default root edit\n", default_backup.read_text(encoding="utf-8"))
        self.assertEqual("custom root edit\n", custom_backup.read_text(encoding="utf-8"))

    def test_existing_difference_refuses_then_force_update_backs_up(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target = self.home / ".codex" / "agents" / PROFILE_NAMES[0]
        target.write_text("user modification\n", encoding="utf-8")
        refused = self.run_installer("update", "codex-agent-profiles")
        self.assertNotEqual(0, refused.returncode)
        self.assertEqual("user modification\n", target.read_text(encoding="utf-8"))

        forced = self.run_installer("update", "codex-agent-profiles", "--force")
        self.assertEqual(0, forced.returncode, forced.stderr)
        backup = managed_backup_path(
            self.root / "state",
            self.home / ".codex" / "agents",
            "agent-profiles",
            PROFILE_NAMES[0],
        )
        self.assertEqual("user modification\n", backup.read_text(encoding="utf-8"))
        self.assertFalse(target.with_suffix(".toml.bak").exists())
        self.assertEqual((SOURCE_PROFILES / PROFILE_NAMES[0]).read_bytes(), target.read_bytes())

    def test_force_update_isolates_all_artifact_backups_and_preserves_legacy_skill_backup(
        self,
    ) -> None:
        installed = self.run_installer("install", "codex-agent-profiles")
        self.assertEqual(0, installed.returncode, installed.stderr)

        skills_root = self.home / ".agents" / "skills"
        templates_root = self.home / ".codex" / "templates"
        profiles_root = self.home / ".codex" / "agents"
        skill = skills_root / "closure-triage"
        template = templates_root / "orchestration" / "policies" / "agent-delegation-policy.md"
        profile = profiles_root / PROFILE_NAMES[0]
        (skill / "SKILL.md").write_text("local skill edit\n", encoding="utf-8")
        template.write_text("local template edit\n", encoding="utf-8")
        profile.write_text("local profile edit\n", encoding="utf-8")

        legacy_backup = skills_root / "closure-triage.bak"
        legacy_backup.mkdir()
        legacy_marker = legacy_backup / "SKILL.md"
        legacy_marker.write_text("unknown legacy backup\n", encoding="utf-8")

        updated = self.run_installer("update", "codex-agent-profiles", "--force")
        self.assertEqual(0, updated.returncode, updated.stderr)

        backups = {
            "skill": managed_backup_path(
                self.root / "state", skills_root, "skills", "closure-triage"
            ),
            "template": managed_backup_path(
                self.root / "state",
                templates_root,
                "templates",
                "orchestration/policies/agent-delegation-policy.md",
            ),
            "profile": managed_backup_path(
                self.root / "state", profiles_root, "agent-profiles", profile.name
            ),
        }
        self.assertEqual("local skill edit\n", (backups["skill"] / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual("local template edit\n", backups["template"].read_text(encoding="utf-8"))
        self.assertEqual("local profile edit\n", backups["profile"].read_text(encoding="utf-8"))
        self.assertEqual("unknown legacy backup\n", legacy_marker.read_text(encoding="utf-8"))
        self.assertEqual(
            ["closure-triage.bak"],
            sorted(path.name for path in skills_root.glob("*.bak")),
        )

    def test_checked_validator_turns_internal_die_into_rollback_path(self) -> None:
        fixture = self.copy_installer_fixture("validator-exit-fixture")
        installer = fixture / "install.sh"
        installed = subprocess.run(
            [str(installer), "install", "shared-review-gates"],
            cwd=fixture,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        skills_root = self.home / ".agents" / "skills"
        first = skills_root / "closure-triage" / "SKILL.md"
        second = skills_root / "task-continuation" / "SKILL.md"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        state_file = self.root / "state" / "codex-dev-skills" / "installed.jsonl"
        state_before = state_file.read_bytes()

        script = installer.read_text(encoding="utf-8")
        needle = '    if ! checked_validator validate_source_artifact "$staged" "$expected" "staged $label"; then\n'
        replacement = (
            '    if [[ "${TEST_UNSAFE_STAGED_LABEL:-}" == "$label" ]]; then\n'
            '      rm -rf "$staged"\n'
            '      ln -s "$ROOT_DIR" "$staged"\n'
            '    fi\n'
            + needle
        )
        self.assertEqual(1, script.count(needle))
        installer.write_text(script.replace(needle, replacement), encoding="utf-8")
        env = {**self.env, "TEST_UNSAFE_STAGED_LABEL": "skill task-continuation"}

        refused = subprocess.run(
            [str(installer), "update", "shared-review-gates", "--force"],
            cwd=fixture,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("Source is a symlink for staged skill task-continuation", refused.stderr)
        self.assertIn("Staged artifact became unsafe", refused.stderr)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertEqual(state_before, state_file.read_bytes())
        self.assertFalse(
            managed_backup_path(
                self.root / "state", skills_root, "skills", "closure-triage"
            ).exists()
        )

    def test_profile_receipt_digest_uses_staged_bytes_when_source_drifts(self) -> None:
        fixture = self.copy_installer_fixture("profile-source-drift-fixture")
        installer = fixture / "install.sh"
        installed = subprocess.run(
            [str(installer), "install", "codex-agent-profiles"],
            cwd=fixture,
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        name = "loop_v2a_fast_explorer.toml"
        source = fixture / "agent-profiles" / name
        staged_source_bytes = source.read_bytes()
        target = self.home / ".codex" / "agents" / name
        target.write_text("local profile edit\n", encoding="utf-8")

        script = installer.read_text(encoding="utf-8")
        needle = 'stage_force_update_receipts() {\n  local expanded="$1" group has_profiles=0\n'
        replacement = (
            needle
            + '  if [[ -n "${TEST_DRIFT_PROFILE_SOURCE:-}" ]]; then\n'
            + '    printf "source drift after staging\\n" > "$ROOT_DIR/agent-profiles/$TEST_DRIFT_PROFILE_SOURCE"\n'
            + '  fi\n'
        )
        self.assertEqual(1, script.count(needle))
        installer.write_text(script.replace(needle, replacement), encoding="utf-8")
        env = {**self.env, "TEST_DRIFT_PROFILE_SOURCE": name}

        updated = subprocess.run(
            [str(installer), "update", "codex-agent-profiles", "--force"],
            cwd=fixture,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertEqual(staged_source_bytes, target.read_bytes())
        self.assertNotEqual(source.read_bytes(), target.read_bytes())
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        receipt = next((self.root / "state" / "codex-dev-skills").glob("agent-profile-*.tsv"))
        self.assertIn(f"{name}\t{digest}\n", receipt.read_text(encoding="utf-8"))

    def test_force_update_backup_collision_is_preflighted_for_whole_group(self) -> None:
        self.assertEqual(0, self.run_installer("install", "codex-agent-profiles").returncode)
        target_dir = self.home / ".codex" / "agents"
        first = target_dir / "loop_v2a_fast_explorer.toml"
        second = target_dir / "loop_v2a_balanced_worker.toml"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        backup = managed_backup_path(
            self.root / "state",
            target_dir,
            "agent-profiles",
            second.name,
        )
        backup.parent.mkdir(parents=True)
        backup.write_text("existing backup\n", encoding="utf-8")

        result = self.run_installer("update", "codex-agent-profiles", "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertFalse(
            managed_backup_path(
                self.root / "state",
                target_dir,
                "agent-profiles",
                first.name,
            ).exists()
        )
        self.assertFalse(first.with_suffix(".toml.bak").exists())

    def test_managed_backup_slot_rejects_symlink_and_special_file_before_update(self) -> None:
        for kind in ("symlink", "fifo"):
            with self.subTest(kind=kind):
                case_root = self.root / kind
                case_home = case_root / "home"
                case_state = case_root / "state"
                case_home.mkdir(parents=True)
                env = {**self.env, "HOME": str(case_home), "XDG_STATE_HOME": str(case_state)}
                installed = self.run_installer("install", "codex-agent-profiles", env=env)
                self.assertEqual(0, installed.returncode, installed.stderr)
                target_root = case_home / ".codex" / "agents"
                target = target_root / PROFILE_NAMES[0]
                target.write_text("local profile edit\n", encoding="utf-8")
                backup = managed_backup_path(
                    case_state, target_root, "agent-profiles", target.name
                )
                backup.parent.mkdir(parents=True)
                if kind == "symlink":
                    external = case_root / "external-backup"
                    external.write_text("outside\n", encoding="utf-8")
                    backup.symlink_to(external)
                else:
                    if not hasattr(os, "mkfifo"):
                        self.skipTest("mkfifo is unavailable")
                    os.mkfifo(backup)

                refused = self.run_installer(
                    "update", "codex-agent-profiles", "--force", env=env
                )
                self.assertNotEqual(0, refused.returncode)
                self.assertEqual("local profile edit\n", target.read_text(encoding="utf-8"))

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

    def test_profile_collision_fails_before_dependency_targets_are_created(self) -> None:
        target_dir = self.home / ".codex" / "agents"
        target_dir.mkdir(parents=True)
        collision = target_dir / "loop_v2a_balanced_worker.toml"
        collision.write_text("existing config\n", encoding="utf-8")

        result = self.run_installer("install", "codex-agent-profiles")

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing to overwrite existing agent profile", result.stderr)
        self.assertEqual("existing config\n", collision.read_text(encoding="utf-8"))
        self.assertFalse((self.home / ".agents").exists())
        self.assertFalse((self.home / ".codex" / "templates").exists())
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

    def test_dependency_uninstall_refuses_installed_profiles(self) -> None:
        self.assertEqual(
            0,
            self.run_installer("install", "codex-agent-profiles").returncode,
        )

        result = self.run_installer(
            "uninstall", "codex-delivery-workflow", "--yes"
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("still depend on", result.stderr)
        self.assertTrue(
            (self.home / ".agents" / "skills" / "loop-engineering").is_dir()
        )
        self.assertEqual(
            PROFILE_NAMES,
            sorted(
                path.name
                for path in (self.home / ".codex" / "agents").glob("*.toml")
            ),
        )

    def test_dependency_uninstall_detects_profiles_in_previous_custom_root(self) -> None:
        custom_target = self.root / "project" / ".codex" / "agents"
        custom_env = {
            **self.env,
            "CODEX_CUSTOM_AGENTS_DIR": str(custom_target),
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
        }
        installed = self.run_installer(
            "install", "codex-agent-profiles", env=custom_env
        )
        self.assertEqual(0, installed.returncode, installed.stderr)

        refused = self.run_installer(
            "uninstall", "codex-delivery-workflow", "--yes"
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("still depend on", refused.stderr)
        self.assertTrue(
            (self.home / ".agents" / "skills" / "loop-engineering").is_dir()
        )
        self.assertEqual(
            PROFILE_NAMES,
            sorted(path.name for path in custom_target.glob("*.toml")),
        )

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
