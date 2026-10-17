from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

from tests.test_installer_source_integrity import InstallerFixture, ROOT


class AgentProfileInstallerTests(InstallerFixture):
    def profile_groups(self):
        return ["shared-review-gates", "codex-delivery-workflow", "codex-agent-profiles"]

    def test_explicit_profiles_install_exactly_and_repeat(self):
        for _ in range(2):
            result = self.run_installer("install", "codex-agent-profiles")
            self.assertEqual(0, result.returncode, result.stderr)
        destination = self.home / ".codex/agents"
        sources = list((ROOT / "agent-profiles").glob("*.toml"))
        self.assertEqual(sorted(p.name for p in sources), sorted(p.name for p in destination.iterdir()))
        for source in sources:
            target = destination / source.name
            self.assertEqual(source.read_bytes(), target.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))
        receipt = json.loads(self.receipt.read_text())
        self.assertIn("codex-agent-profiles", receipt["groups"])
        state = next(self.state.glob("agent-profile-*.tsv"))
        self.assertIn(hashlib.sha256(sources[0].read_bytes()).hexdigest(), state.read_text())

    def test_all_does_not_newly_opt_into_profiles(self):
        result = self.run_installer("install", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((self.home / ".codex/agents").exists())
        self.assertNotIn("codex-agent-profiles", json.loads(self.receipt.read_text())["groups"])

    def test_update_all_preserves_previous_profile_opt_in(self):
        self.seed(groups=self.profile_groups())
        result = self.run_installer("update", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_version("0.34.0")
        self.assertIn("codex-agent-profiles", json.loads(self.receipt.read_text())["groups"])

    def test_project_profiles_require_explicit_narrow_target_opt_in(self):
        project = self.case / "project/.codex/agents"
        before = self.snapshot()
        result = self.run_installer("install", "codex-agent-profiles", overrides={"CODEX_CUSTOM_AGENTS_DIR": str(project)})
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())
        result = self.run_installer("install", "codex-agent-profiles", overrides={
            "CODEX_CUSTOM_AGENTS_DIR": str(project), "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES"})
        self.assertEqual(0, result.returncode, result.stderr)
        receipts = list(self.state.glob("managed-*.json"))
        self.assertEqual(1, len(receipts))
        self.assertEqual(str(project), json.loads(receipts[0].read_text())["roots"]["agent_profiles"])

    def test_modified_profile_is_preserved_for_force_and_uninstall(self):
        self.seed(groups=self.profile_groups())
        profile = self.home / ".codex/agents/loop_v2a_fast_explorer.toml"
        profile.write_text("custom profile")
        before = self.snapshot()
        for args in (("update", "--all", "--force"), ("uninstall", "codex-agent-profiles", "--yes")):
            result = self.run_installer(*args)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, self.snapshot())

    def test_unknown_identical_profile_cannot_be_adopted(self):
        target = self.home / ".codex/agents/loop_v2a_fast_explorer.toml"
        target.parent.mkdir(mode=0o700)
        shutil.copy2(ROOT / "agent-profiles" / target.name, target)
        before = self.snapshot()
        result = self.run_installer("install", "codex-agent-profiles")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_profiles_uninstall_preserves_dependencies_and_unmanaged_sibling(self):
        self.seed(groups=self.profile_groups())
        other = self.home / ".codex/agents/custom.toml"
        other.write_text("custom unrelated profile")
        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([other], list(other.parent.iterdir()))
        self.assertTrue((self.home / ".agents/skills/planning/SKILL.md").is_file())
        self.assertNotIn("codex-agent-profiles", json.loads(self.receipt.read_text())["groups"])

    def test_default_uninstall_all_preserves_opt_in_dependency_guard(self):
        self.seed(groups=self.profile_groups())
        before = self.snapshot()
        result = self.run_installer("uninstall", "--all", "--yes")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_profiles_receipt_failure_rolls_back_artifacts_and_all_receipts(self):
        self.seed(groups=self.profile_groups())
        profile_state = self.state / "agent-profile-fixture.tsv"
        profile_state.write_text("historical receipt")
        overrides = self.fake_mv("profile-receipt")
        before = self.snapshot()
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-profile-receipt", result.stderr)
        self.assertEqual(before, self.snapshot(), result.stderr)

    def test_readonly_profile_receipt_refuses_before_payload_apply(self):
        self.seed(groups=self.profile_groups())
        digest = hashlib.sha256(self.roots["agent_profiles"].encode()).hexdigest()
        receipt = self.state / ("agent-profile-" + digest + ".tsv")
        receipt.chmod(0o400)
        before = self.snapshot()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_mapping_reserved_destination_is_not_changed(self):
        root = self.home / ".codex"
        destination = root / "agents"
        destination.mkdir(mode=0o700)
        (destination / "custom.toml").write_text("preserve")
        record = dict(role="loop_v2a_balanced_worker", runtime="cli", provider_id="synthetic",
                      provider_config_sha256="a"*64, model="synthetic", reasoning_effort="medium",
                      base_profile_sha256="b"*64, profile="agents/custom.toml", profile_sha256="c"*64,
                      capability_class="balanced-worker", capability_tier="everyday",
                      task_scopes=["fixture"], quality_evidence="quality.txt",
                      quality_evidence_sha256="d"*64, context_policy="context.json",
                      context_policy_sha256="e"*64, expires_on=None, enabled=False)
        store = root / "agent-model-mapping.json"
        store.write_text(json.dumps(dict(schema_version=1, enabled=True, mappings=[record])))
        store.chmod(0o600)
        before = self.snapshot()
        result = self.run_installer("install", "codex-agent-profiles")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("mapping", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_custom_profile_discovery_alias_is_rejected(self):
        destination = self.case / "project/.codex/agents"
        destination.mkdir(parents=True)
        self.state.parent.mkdir()
        (destination / "alias").symlink_to(self.state.parent, target_is_directory=True)
        result = self.run_installer("install", "codex-agent-profiles", overrides={
            "CODEX_CUSTOM_AGENTS_DIR": str(destination), "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("discovery root", result.stderr)

    def test_switching_only_profile_root_does_not_adopt_common_dependencies(self):
        self.seed("0.34.0")
        before = self.snapshot()
        project = self.case / "project/.codex/agents"
        result = self.run_installer("install", "codex-agent-profiles", overrides={
            "CODEX_CUSTOM_AGENTS_DIR": str(project), "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES"})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unmanaged existing", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_unknown_profile_receipt_is_not_overwritten(self):
        self.seed(groups=self.profile_groups())
        digest = hashlib.sha256(self.roots["agent_profiles"].encode()).hexdigest()
        path = self.state / ("agent-profile-" + digest + ".tsv")
        path.write_text("unknown profile metadata")
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("profile receipt", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_repeated_or_never_opted_in_profile_uninstall_is_safe_noop(self):
        self.seed(groups=self.profile_groups())
        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        digest = hashlib.sha256(self.roots["agent_profiles"].encode()).hexdigest()
        path = self.state / ("agent-profile-" + digest + ".tsv")
        path.write_text("unrelated unmanaged metadata")
        for _ in range(2):
            before = self.snapshot()
            result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
            self.assertEqual(0, result.returncode, result.stderr)
            # The history is append-only; the inventory and unrelated TSV stay intact.
            after = self.snapshot()
            history = str((self.state / "installed.jsonl").relative_to(self.case))
            self.assertEqual({k: v for k, v in before.items() if k != history},
                             {k: v for k, v in after.items() if k != history})
            self.assertEqual("unrelated unmanaged metadata", path.read_text())

    def test_custom_profile_root_still_protects_standard_profile_discovery(self):
        standard = self.home / ".codex/agents"
        standard.mkdir(mode=0o700)
        outside = self.case / "outside-state"
        outside.mkdir(mode=0o700)
        alias = standard / "state-alias"
        alias.symlink_to(outside, target_is_directory=True)
        project = self.case / "project/.codex/agents"
        for state in (standard / "state", outside):
            with self.subTest(state=state):
                before = self.snapshot()
                result = self.run_installer("install", "codex-agent-profiles", overrides={
                    "CODEX_CUSTOM_AGENTS_DIR": str(project), "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
                    "XDG_STATE_HOME": str(state)})
                self.assertNotEqual(0, result.returncode)
                self.assertIn("overlaps a known discovery root", result.stderr)
                self.assertEqual(before, self.snapshot())
                self.assertTrue(alias.is_symlink())
                self.assertEqual([], list(project.iterdir()) if project.exists() else [])
                self.assertFalse((state / "codex-dev-skills").exists())
