from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
OLD = "6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c"
REGISTRY = json.loads((ROOT / "installer/source-catalogs.json").read_text())
CURRENT_CATALOG_DIGEST = hashlib.sha256((ROOT / "catalog.yaml").read_bytes()).hexdigest()
CURRENT_CATALOGS = [c for c in REGISTRY["catalogs"] if c["catalog_sha256"] == CURRENT_CATALOG_DIGEST]
if len(CURRENT_CATALOGS) != 1:
    raise AssertionError("fixture requires one reviewed current catalog")
CURRENT_VERSION = CURRENT_CATALOGS[0]["version"]
spec = importlib.util.spec_from_file_location("installer_inventory", ROOT / "scripts/installer-inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InstallerFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(prefix="installer-integrity-")
        cls.root = Path(cls.workspace.name).resolve()
        cls.old = cls.root / "old-source"
        for command in (["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(ROOT), str(cls.old)],
                        ["git", "-C", str(cls.old), "remote", "set-url", "origin", "https://github.com/jeffery777/codex-dev-skills.git"],
                        ["git", "-C", str(cls.old), "checkout", "--quiet", "--detach", OLD]):
            subprocess.run(command, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.temporary.cleanup)
        self.case = Path(self.temporary.name)
        self.home = self.case / "home"
        self.home.mkdir(mode=0o700)
        (self.home / ".codex").mkdir(mode=0o700)
        self.state = self.case / "state/codex-dev-skills"
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(("CODEX_", "GIT_"))}
        self.env.update(HOME=str(self.home), XDG_STATE_HOME=str(self.case / "state"),
                        CODEX_HOME=str(self.home / ".codex"), CODEX_CLI=str(self.case / "no-client"), PYTHONDONTWRITEBYTECODE="1")
        self.roots = {"skills": str(self.home / ".agents/skills"), "templates": str(self.home / ".codex/templates"),
                      "agent_profiles": str(self.home / ".codex/agents")}
        digest = hashlib.sha256("\0".join(self.roots.values()).encode()).hexdigest()
        self.receipt = self.state / f"managed-{digest}.json"

    def run_installer(self, *args, overrides=None):
        result = subprocess.run(["bash", str(ROOT / "install.sh"), *map(str, args)], cwd=ROOT,
                                env={**self.env, **(overrides or {})}, text=True, capture_output=True)
        return result

    def fixed_source(self, revision):
        self.assertIn(revision, [c["reviewed_revision"] for c in REGISTRY["catalogs"]])
        source = self.case / f"source-{revision}"
        for command in (["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(ROOT), str(source)],
                        ["git", "-C", str(source), "remote", "set-url", "origin", "https://github.com/jeffery777/codex-dev-skills.git"],
                        ["git", "-C", str(source), "checkout", "--quiet", "--detach", revision]):
            subprocess.run(command, check=True, capture_output=True)
        return source

    def seed(self, version="0.33.1", groups=None, legacy=False, snapshot_revision=None):
        digest = hashlib.sha256("\0".join(self.roots.values()).encode()).hexdigest()
        self.receipt = self.state / f"managed-{digest}.json"
        candidates = [c for c in REGISTRY["catalogs"] if c["version"] == version]
        if snapshot_revision is not None:
            candidates = [c for c in candidates if c["reviewed_revision"] == snapshot_revision]
        elif version == CURRENT_VERSION:
            candidates = [c for c in candidates if c["catalog_sha256"] == CURRENT_CATALOG_DIGEST]
        if len(candidates) != 1:
            raise AssertionError("fixture requires one exact reviewed payload snapshot")
        catalog = candidates[0]
        groups = groups or [g for g in catalog["groups"] if g != "codex-agent-profiles"]
        items = inventory.artifacts(catalog, inventory.expand(catalog, groups))
        if catalog["catalog_sha256"] == CURRENT_CATALOG_DIGEST:
            source = ROOT
        elif catalog["reviewed_revision"] == OLD:
            source = self.old
        else:
            source = self.fixed_source(catalog["reviewed_revision"])
        for item in items:
            target = Path(self.roots[item["kind"]]) / item["relative"]
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if item["type"] == "directory":
                shutil.copytree(source / item["source"], target)
            else:
                shutil.copy2(source / item["source"], target)
        for path in self.home.rglob("*"):
            path.chmod(0o700 if path.is_dir() or path.stat().st_mode & 0o111 else 0o600)
        self.state.mkdir(parents=True, mode=0o700)
        history = "".join(json.dumps(dict(repo="codex-dev-skills", version=version, action="install",
                                        group=g, target_mode="agents")) + "\n" for g in groups)
        (self.state / "installed.jsonl").write_text(history)
        receipt = dict(schema=1, roots=self.roots, groups=sorted(groups), artifacts=items,
                       source=dict(repository="jeffery777/codex-dev-skills", revision=catalog["reviewed_revision"],
                                   version=version, catalog_sha256=catalog["catalog_sha256"], core=catalog["core"]))
        if not legacy:
            self.receipt.write_text(json.dumps(receipt, sort_keys=True) + "\n")
            if "codex-agent-profiles" in groups:
                digest = hashlib.sha256(self.roots["agent_profiles"].encode()).hexdigest()
                path = self.state / ("agent-profile-" + digest + ".tsv")
                path.write_text("".join(item["relative"] + "\t" + item["files"][""]["sha256"] + "\n"
                                        for item in items if item["kind"] == "agent_profiles"))
                path.chmod(0o600)
        return receipt

    def snapshot(self):
        return {str(p.relative_to(self.case)): (p.lstat().st_mode, p.read_bytes())
                for p in self.case.rglob("*") if p.is_file() and not p.is_symlink()}

    def assert_version(self, version):
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(version, receipt["source"]["version"])
        inventory.check_payload(receipt["artifacts"], receipt["roots"])
        self.assertEqual([], list((self.state / "backups/v1").glob("transaction.*")))

    def fake_mv(self, mode):
        folder = self.case / "fake-bin"
        folder.mkdir()
        real = shutil.which("mv")
        program = '''#!/bin/bash
case "$FAIL_MODE:$1:$2" in
  apply:*.tmp.*/value:*) echo injected-apply >&2; exit 73 ;;
  receipt:*.receipt.*/value:*/managed-*.json) echo injected-receipt >&2; exit 74 ;;
  history-receipt:*.receipt.*/value:*/installed.jsonl) echo injected-history-receipt >&2; exit 74 ;;
  profile-receipt:*.receipt.*/value:*/agent-profile-*.tsv) echo injected-profile-receipt >&2; exit 74 ;;
  later:*.code-review.tmp.*/value:*) echo injected-later >&2; exit 73 ;;
  exdev:*:*.bak) echo injected-EXDEV >&2; exit 18 ;;
  hold:*:*.bak) if [ ! -e "$HOLD_MARKER" ]; then : > "$HOLD_MARKER"; sleep 2; fi ;;
  drift-rollback:*.closure-triage.tmp.*/value:*) "REAL_MV" "$@" || exit $?; printf 'custom concurrent edit' > "$2/SKILL.md"; exit 0 ;;
  drift-rollback:*.code-review.tmp.*/value:*) echo injected-later >&2; exit 73 ;;
  retire:*core.lock.json:*.bak) echo injected-retirement >&2; exit 75 ;;
  restore:*.tmp.*/value:*) echo injected-apply >&2; exit 76 ;;
  restore:*.bak:*) echo injected-restore >&2; exit 77 ;;
  drift:*state-preflight*:*.renamed) printf 'late custom bytes' > "$DRIFT_TARGET" ;;
  signal:*.tmp.*/value:*) "REAL_MV" "$@" || exit $?; echo injected-signal >&2; kill -"${FAIL_SIGNAL:-TERM}" "$PPID"; exit 0 ;;
  restore-receipt:*.receipt.*/value:*/managed-*.json) echo injected-receipt >&2; exit 74 ;;
  restore-receipt:*.receipt.*/original:*/installed.jsonl) echo injected-receipt-restore >&2; exit 74 ;;
  signal-restore:*.code-review.tmp.*/value:*) echo injected-later >&2; exit 73 ;;
  signal-restore:*.bak:*) "REAL_MV" "$@" || exit $?; echo injected-signal-restore >&2; kill -"${FAIL_SIGNAL:-TERM}" "$PPID"; exit 0 ;;
  signal-receipt-restore:*.receipt.*/value:*/managed-*.json) echo injected-receipt >&2; exit 74 ;;
  signal-receipt-restore:*.receipt.*/original:*/installed.jsonl) "REAL_MV" "$@" || exit $?; echo injected-signal-receipt-restore >&2; kill -"${FAIL_SIGNAL:-TERM}" "$PPID"; exit 0 ;;
esac
exec "REAL_MV" "$@"
'''.replace("REAL_MV", real)
        (folder / "mv").write_text(program)
        (folder / "mv").chmod(0o700)
        return dict(PATH=str(folder) + os.pathsep + self.env["PATH"], FAIL_MODE=mode)


class SourceIntegrityInstallerTests(InstallerFixture):
    def test_catalog_generation_rejects_duplicate_and_empty_sets_before_writing(self):
        spec = importlib.util.spec_from_file_location("catalog_generator", ROOT / "scripts/sync-installer-catalogs.py")
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        target = self.case / "generated.json"
        target.write_text("preserved sentinel\n")
        for revisions in ((), ("first", "second")):
            with self.subTest(revisions=revisions), mock.patch.object(generator, "REVISIONS", revisions), \
                    mock.patch.object(generator, "OUTPUT", target), \
                    mock.patch.object(generator, "snapshot", return_value={"catalog_sha256": "a" * 64}), \
                    mock.patch.object(sys, "argv", ["sync-installer-catalogs.py"]):
                with self.assertRaisesRegex(ValueError, "ambiguous or empty"):
                    generator.main()
                self.assertEqual("preserved sentinel\n", target.read_text())

    def test_duplicate_catalog_digests_cannot_select_a_source_by_order(self):
        registry = self.case / "duplicate-catalogs.json"
        value = json.loads((ROOT / "installer/source-catalogs.json").read_text())
        value["catalogs"].append(value["catalogs"][0])
        registry.write_text(json.dumps(value))
        with mock.patch.object(inventory, "REGISTRY", registry):
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                inventory.reviewed_catalogs()

    def test_same_version_core_snapshot_transition_preserves_profiles_and_directory_inventory(self):
        development = "43c650e1196a3a702e2240bd79dd24539fa893a7"
        old_catalog = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == development)
        prior = self.seed("0.34.0", groups=list(old_catalog["groups"]), snapshot_revision=development)
        old_source = self.case / f"source-{development}"
        split_source = self.fixed_source("f18b202595aea27c9d872c480d2e1b067340b163")
        before = self.snapshot()
        result = self.run_installer("update", "codex-review-workflow", "--source", split_source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires all managed groups", result.stderr)
        self.assertEqual(before, self.snapshot())
        result = self.run_installer("update", "--all", "--source", split_source)
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual("0.34.0", receipt["source"]["version"])
        self.assertEqual("0.1.0", receipt["source"]["core"]["version"])
        self.assertNotEqual(prior["source"]["catalog_sha256"], receipt["source"]["catalog_sha256"])
        self.assertIn("codex-agent-profiles", receipt["groups"])
        core_root = self.home / ".codex/templates/orchestration/core"
        self.assertTrue((core_root / "docs/releases/v0.1.0.md").is_file())
        result = self.run_installer("update", "--all", "--source", old_source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(prior["source"]["catalog_sha256"], json.loads(self.receipt.read_text())["source"]["catalog_sha256"])
        self.assertFalse((core_root / "docs/releases").exists())
        self.assert_version("0.34.0")
        result = self.run_installer("uninstall", "codex-review-workflow", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((core_root / "docs/releases").exists())
        self.assertTrue((core_root / "contracts/workflow.md").is_file())
        before = self.snapshot()
        result = self.run_installer("uninstall", "--all", "--yes")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("still depend", result.stderr)
        self.assertEqual(before, self.snapshot())
        result = self.run_installer("uninstall", "codex-agent-profiles", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn("codex-agent-profiles", json.loads(self.receipt.read_text())["groups"])
        self.assertTrue((core_root / "contracts/workflow.md").is_file())
        result = self.run_installer("uninstall", "--all", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(core_root.exists())

    def test_core_root_rollback_restores_old_directory_set_after_lock_failure(self):
        development = "43c650e1196a3a702e2240bd79dd24539fa893a7"
        self.seed("0.34.0", snapshot_revision=development)
        folder = self.case / "core-fault-bin"
        folder.mkdir()
        wrapper = folder / "mv"
        real = shutil.which("mv")
        wrapper.write_text('''#!/bin/bash
if [[ "$1" == *.core.lock.json.tmp.*/value && "$2" == */orchestration/core.lock.json ]]; then
  if [[ ! -f "$HOME/.codex/templates/orchestration/core/docs/releases/v0.1.0.md" ]]; then
    echo core-root-seam-not-reached >&2; exit 79
  fi
  echo injected-after-core-root >&2; exit 78
fi
exec "''' + real + '''" "$@"
''')
        wrapper.chmod(0o700)
        before = self.snapshot()
        core_root = self.home / ".codex/templates/orchestration/core"
        directories = sorted(p.relative_to(core_root).as_posix() for p in core_root.rglob("*") if p.is_dir())
        result = self.run_installer("update", "--all", overrides={"PATH": str(folder) + os.pathsep + self.env["PATH"]})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-after-core-root", result.stderr)
        self.assertEqual(before, self.snapshot(), result.stderr)
        self.assertEqual(directories, sorted(p.relative_to(core_root).as_posix() for p in core_root.rglob("*") if p.is_dir()))
        self.assertFalse((core_root / "docs/releases").exists())
        self.assert_version("0.34.0")

    def test_preexisting_unowned_empty_core_root_is_preserved(self):
        self.seed()
        core_root = self.home / ".codex/templates/orchestration/core"
        core_root.mkdir(mode=0o700)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unmanaged existing content", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(core_root.is_dir())
        self.assertEqual([], list(core_root.iterdir()))

    def test_selected_source_guards_reject_payload_catalog_and_repository_drift(self):
        self.seed()
        cases = (("skills/code-review/SKILL.md", "bytes", "source payload differs"),
                 ("agent-profiles/loop_v2a_mechanical_reader.toml", "bytes", "source payload differs"),
                 ("skills/code-review/SKILL.md", "missing", "source payload differs"),
                 ("skills/code-review/SKILL.md", "mode", "source payload differs"),
                 ("catalog.yaml", "bytes", "source catalog differs from fixed Git revision"))
        for relative, mutation, diagnostic in cases:
            with self.subTest(relative=relative, mutation=mutation):
                path = self.old / relative
                original, mode = path.read_bytes(), path.stat().st_mode & 0o777
                try:
                    if mutation == "missing": path.unlink()
                    elif mutation == "mode": path.chmod(mode ^ 0o100)
                    else: path.write_bytes(original + b"\nfixture source tamper\n")
                    before = self.snapshot()
                    result = self.run_installer("update", "--all", "--source", self.old)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn(diagnostic, result.stderr)
                    self.assertEqual(before, self.snapshot())
                finally:
                    path.write_bytes(original)
                    path.chmod(mode)
        subprocess.run(["git", "-C", str(self.old), "remote", "set-url", "origin", "https://invalid.example/fixture.git"], check=True)
        try:
            before = self.snapshot()
            result = self.run_installer("update", "--all", "--source", self.old)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("source origin does not match", result.stderr)
            self.assertEqual(before, self.snapshot())
        finally:
            subprocess.run(["git", "-C", str(self.old), "remote", "set-url", "origin", "https://github.com/jeffery777/codex-dev-skills.git"], check=True)
        source = self.case / "unsupported-source"
        source.mkdir(mode=0o700)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--source", source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("non-zero exit status 128", result.stderr)
        self.assertEqual(before, self.snapshot())
        # A local fixture-only Git object graph reaches the unsupported-catalog
        # guard without running hooks, fetching data or committing the candidate.
        (source / "catalog.yaml").write_text("fixture: unsupported catalog\n")
        fixture_env = {**self.env, "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                       "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid"}
        def git_fixture(*args, text=None):
            return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                                   "-C", str(source), *args], input=text, text=True,
                                  env=fixture_env, capture_output=True, check=True).stdout.strip()
        git_fixture("-c", "init.templateDir=", "init", "--quiet")
        git_fixture("remote", "add", "origin", "https://github.com/jeffery777/codex-dev-skills.git")
        blob = git_fixture("hash-object", "-w", "catalog.yaml")
        tree = git_fixture("mktree", text=f"100644 blob {blob}\tcatalog.yaml\n")
        commit = git_fixture("commit-tree", tree, text="fixture unsupported catalog\n")
        git_fixture("update-ref", "HEAD", commit)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--source", source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unsupported source catalog", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_upgrade_repeat_and_downgrade_reconcile_all_files_and_core(self):
        self.seed()
        sibling = self.home / ".agents/skills/unmanaged/notes.txt"
        sibling.parent.mkdir()
        sibling.write_text("preserve")
        for source, version in ((ROOT, CURRENT_VERSION), (ROOT, CURRENT_VERSION), (self.old, "0.33.1")):
            result = self.run_installer("update", "--all", "--source", source)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assert_version(version)
            self.assertEqual("preserve", sibling.read_text())
        self.assertFalse((self.home / ".codex/templates/orchestration/core.lock.json").exists())
        self.assertFalse((self.home / ".codex/templates/orchestration/core").exists())

    def test_custom_extra_and_exec_drift_are_preserved_even_force_and_uninstall(self):
        self.seed()
        target = self.home / ".agents/skills/code-review/SKILL.md"
        target.write_text("custom")
        before = self.snapshot()
        for command in (("update", "--all", "--force"), ("uninstall", "--all", "--yes")):
            result = self.run_installer(*command)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, self.snapshot())
        target.write_bytes((self.old / "skills/code-review/SKILL.md").read_bytes())
        target.chmod(target.stat().st_mode ^ 0o100)
        before = self.snapshot()
        self.assertNotEqual(0, self.run_installer("update", "--all").returncode)
        self.assertEqual(before, self.snapshot())

    def test_extra_skill_files_and_unknown_identical_targets_are_not_adopted(self):
        self.seed()
        (self.home / ".agents/skills/code-review/notes.pyc").write_text("unknown")
        before = self.snapshot()
        self.assertNotEqual(0, self.run_installer("update", "--all", "--force").returncode)
        self.assertEqual(before, self.snapshot())
        self.receipt.unlink()
        result = self.run_installer("install", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("unmanaged existing", result.stderr)

    def test_legacy_bootstrap_requires_receipt_and_exact_prior_source(self):
        self.seed(legacy=True)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--previous-source", self.old)
        self.assertNotEqual(0, result.returncode, result.stderr)
        self.assertIn("no verifiable target-root binding", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_apply_and_receipt_failure_restore_payload_and_receipts(self):
        self.seed()
        for mode in ("apply", "later", "history-receipt", "receipt", "exdev", "signal"):
            with self.subTest(mode=mode):
                overrides = self.fake_mv(mode)
                before = self.snapshot()
                result = self.run_installer("update", "--all", overrides=overrides)
                self.assertIn("injected", result.stderr, "fault seam was not reached")
                if mode == "signal" and result.returncode == 0:
                    # Signals inside rename critical sections are intentionally
                    # ignored; a complete verified commit is also consistent.
                    self.assert_version(CURRENT_VERSION)
                else:
                    self.assertNotEqual(0, result.returncode, result.stdout)
                    self.assertEqual(before, self.snapshot(), result.stderr)
                shutil.rmtree(self.case / "fake-bin")

    def test_downgrade_retirement_failure_restores_all_files(self):
        self.seed(CURRENT_VERSION)
        overrides = self.fake_mv("retire")
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--source", self.old, overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot(), result.stderr)

    def test_failed_restore_retains_originals_outside_discovery(self):
        self.seed()
        overrides = self.fake_mv("restore")
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("CRITICAL", result.stderr)
        backups = list((self.state / "backups/v1").rglob("*.bak"))
        self.assertTrue(backups)
        for backup in backups:
            self.assertFalse(backup.is_relative_to(self.home / ".agents/skills"))

    def test_known_discovery_state_and_reverse_alias_are_rejected(self):
        for suffix in (".agents/skills", ".codex/plugins", ".grok/skills", ".grok/commands", ".grok/plugins", ".grok/bundled/skills", ".cursor/skills"):
            with self.subTest(suffix=suffix):
                result = self.run_installer("install", "shared-review-gates", overrides=dict(XDG_STATE_HOME=str(self.home / suffix / "state")))
                self.assertNotEqual(0, result.returncode)
                self.assertIn("discovery root", result.stderr)
        skills = self.home / ".agents/skills"
        skills.mkdir(parents=True)
        self.state.parent.mkdir()
        (skills / "state-alias").symlink_to(self.state.parent, target_is_directory=True)
        result = self.run_installer("install", "shared-review-gates")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("discovery root", result.stderr)

    def test_uninstall_uses_owned_inventory_and_preserves_siblings(self):
        self.seed()
        sibling = self.home / ".agents/skills/other"
        sibling.mkdir()
        (sibling / "notes.txt").write_text("preserve")
        result = self.run_installer("uninstall", "--all", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], json.loads(self.receipt.read_text())["groups"])
        self.assertEqual("preserve", (sibling / "notes.txt").read_text())

    def test_receipt_parser_rejects_duplicate_and_path_traversal_without_writes(self):
        self.seed()
        self.receipt.write_text('{"schema":1,"schema":1}')
        before = self.snapshot()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("duplicate JSON", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_partial_cross_version_scope_requires_all(self):
        self.seed()
        before = self.snapshot()
        result = self.run_installer("update", "codex-review-workflow")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires all managed groups", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_same_version_install_and_update_are_safe_noops(self):
        self.seed(CURRENT_VERSION)
        for command in ("install", "update"):
            result = self.run_installer(command, "--all")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assert_version(CURRENT_VERSION)

    def test_verified_identity_drift_during_state_probe_is_preserved(self):
        self.seed()
        target = self.home / ".agents/skills/code-review/SKILL.md"
        overrides = {**self.fake_mv("drift"), "DRIFT_TARGET": str(target)}
        receipt_before = self.receipt.read_bytes()
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("late custom bytes", target.read_text())
        self.assertEqual(receipt_before, self.receipt.read_bytes())
        self.assertIn("Verified installed identity changed", result.stderr)

    def test_wrong_repository_revision_groups_and_paths_are_rejected(self):
        receipt = self.seed()
        for mutation in (lambda r: r["source"].update(repository="other/repo"),
                         lambda r: r["source"].update(revision="main"),
                         lambda r: r["groups"].append(r["groups"][0]),
                         lambda r: r["artifacts"][0].update(relative="../outside")):
            value = json.loads(json.dumps(receipt))
            mutation(value)
            self.receipt.write_text(json.dumps(value))
            before = self.snapshot()
            result = self.run_installer("update", "--all")
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, self.snapshot())

    def test_unknown_core_file_blocks_downgrade(self):
        self.seed(CURRENT_VERSION)
        extra = self.home / ".codex/templates/orchestration/core/notes.txt"
        extra.write_text("preserve unknown Core note")
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--source", self.old)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_custom_target_reverse_alias_is_rejected(self):
        skills = self.case / "project/skills"
        skills.mkdir(parents=True)
        self.state.parent.mkdir()
        (skills / "state-alias").symlink_to(self.state.parent, target_is_directory=True)
        result = self.run_installer("install", "shared-review-gates", overrides=dict(
            CODEX_SKILLS_DIR=str(skills), CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS="YES"))
        self.assertNotEqual(0, result.returncode)
        self.assertIn("discovery root", result.stderr)

    def test_ownership_receipt_drift_during_state_probe_is_preserved(self):
        self.seed()
        overrides = {**self.fake_mv("drift"), "DRIFT_TARGET": str(self.receipt)}
        before_payload = (self.home / ".agents/skills/code-review/SKILL.md").read_bytes()
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Verified receipt identity changed", result.stderr)
        self.assertEqual("late custom bytes", self.receipt.read_text())
        self.assertEqual(before_payload, (self.home / ".agents/skills/code-review/SKILL.md").read_bytes())

    def test_rollback_identity_drift_preserves_custom_and_official_original(self):
        self.seed()
        original = (self.old / "skills/closure-triage/SKILL.md").read_bytes()
        result = self.run_installer("update", "--all", overrides=self.fake_mv("drift-rollback"))
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-later", result.stderr)
        self.assertIn("CRITICAL", result.stderr)
        self.assertEqual("custom concurrent edit", (self.home / ".agents/skills/closure-triage/SKILL.md").read_text())
        backups = list((self.state / "backups/v1").rglob("closure-triage.bak"))
        self.assertEqual(1, len(backups))
        self.assertEqual(original, (backups[0] / "SKILL.md").read_bytes())

    def test_receipt_restore_failure_preserves_original_receipt(self):
        self.seed()
        history = (self.state / "installed.jsonl").read_bytes()
        result = self.run_installer("update", "--all", overrides=self.fake_mv("restore-receipt"))
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-receipt-restore", result.stderr)
        self.assertIn("CRITICAL", result.stderr)
        originals = list(self.state.glob(".codex-dev-skills.installed.jsonl.receipt.*/original"))
        self.assertEqual(1, len(originals))
        self.assertEqual(history, originals[0].read_bytes())

    def test_signals_during_artifact_and_receipt_restore_do_not_reenter_rollback(self):
        self.seed()
        for mode, signal in (("signal-restore", "INT"), ("signal-restore", "HUP"), ("signal-receipt-restore", "TERM")):
            with self.subTest(mode=mode, signal=signal):
                overrides = {**self.fake_mv(mode), "FAIL_SIGNAL": signal}
                before = self.snapshot()
                result = self.run_installer("update", "--all", overrides=overrides)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("injected-signal", result.stderr)
                self.assertEqual(before, self.snapshot(), result.stderr)
                shutil.rmtree(self.case / "fake-bin")

    def test_cooperating_concurrent_update_respects_one_lock(self):
        self.seed()
        marker = self.case / "held"
        overrides = {**self.fake_mv("hold"), "HOLD_MARKER": str(marker)}
        process = subprocess.Popen(["bash", str(ROOT / "install.sh"), "update", "--all"], cwd=ROOT,
                                   env={**self.env, **overrides}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 40
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertTrue(marker.exists(), "lock-hold fault seam not reached")
            result = self.run_installer("update", "--all")
            self.assertNotEqual(0, result.returncode)
            self.assertIn("lock already exists", result.stderr)
            stdout, stderr = process.communicate(timeout=90)
            self.assertEqual(0, process.returncode, stderr)
            self.assert_version(CURRENT_VERSION)
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=30)
