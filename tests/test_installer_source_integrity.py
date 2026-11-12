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
        self.assert_core_root_rollback("0.34.0", "43c650e1196a3a702e2240bd79dd24539fa893a7")

    def test_formal_core_root_rollback_restores_thirteen_file_set_after_lock_failure(self):
        self.assert_core_root_rollback("0.35.0", "e23e18ed0512ece04ca6b6dceba3a6a1cf59b9fd")

    def assert_core_root_rollback(self, version, revision):
        self.seed(version, snapshot_revision=revision)
        folder = self.case / "core-fault-bin"
        folder.mkdir()
        wrapper = folder / "mv"
        real = shutil.which("mv")
        wrapper.write_text('''#!/bin/bash
if [[ "$1" == *.core.lock.json.tmp.*/value && "$2" == */orchestration/core.lock.json ]]; then
  if [[ ! -f "$HOME/.codex/templates/orchestration/core/docs/releases/v0.1.1.md" ]]; then
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
        self.assertFalse((core_root / "docs/releases/v0.1.1.md").exists())
        self.assertEqual(version == "0.35.0", (core_root / "docs/releases/v0.1.0.md").is_file())
        self.assert_version(version)

    def test_formal_thirteen_to_fourteen_and_back_preserves_profiles_and_retires_note(self):
        self.assert_core_transition("0.35.0", "e23e18ed0512ece04ca6b6dceba3a6a1cf59b9fd", 13)

    def test_development_eleven_to_fourteen_and_back_preserves_profiles_and_retires_notes(self):
        self.assert_core_transition("0.34.0", "43c650e1196a3a702e2240bd79dd24539fa893a7", 11)

    def test_formal_fourteen_to_twenty_and_back_preserves_exact_tree_and_profiles(self):
        for version, revision in (("0.35.1", "6cd58e3a776ef705a9cee17ba7e24c6b21181395"),
                                  ("0.35.2", "73cee30f5aee09c9218505624f1caa433ef72946")):
            with self.subTest(version=version):
                # Each transition owns a fresh home and state directory.
                self.setUp()
                self.assert_core_transition(version, revision, 14)

    def test_formal_twenty_to_twenty_three_and_back_preserves_exact_tree(self):
        self.assert_core_transition("0.36.0", "ec54012c74a4ab3eb42d5f2152e36138ce9e7c35", 20)

    def test_formal_twenty_six_to_current_and_back_preserves_exact_tree(self):
        self.assert_core_transition("0.38.0", "ac3703efa42ad75ecdc52e7e0476dfcde93ac00b", 26)

    def test_formal_twenty_eight_to_thirty_one_and_back_preserves_exact_tree(self):
        self.assert_core_transition("0.38.1", "c88514225129afc02ccdc3734402042b0e2a5194", 28)

    def assert_core_transition(self, version, revision, count, *, target_revision=None):
        target_source = ROOT
        target_version = CURRENT_VERSION
        if target_revision is not None:
            target = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == target_revision)
            target_source = self.fixed_source(target_revision)
            target_version = target["version"]
        catalog = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == revision)
        prior = self.seed(version, groups=list(catalog["groups"]), snapshot_revision=revision)
        old_source = self.case / f"source-{revision}"
        core_root = self.home / ".codex/templates/orchestration/core"
        sentinel = None
        if target_revision is None:
            sentinel = self.home / ".agents/skills/unmanaged-v041-release/notes.txt"
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_bytes(b"unmanaged release fixture; preserve\n")
            sentinel.chmod(0o600)
        prior_files = {p.relative_to(core_root).as_posix(): p.read_bytes()
                       for p in core_root.rglob("*") if p.is_file()}
        prior_directories = sorted(p.relative_to(core_root).as_posix()
                                   for p in core_root.rglob("*") if p.is_dir())
        self.assertEqual(count, len(prior_files))
        if version in {"0.39.0", "0.40.0"} and version != target_version:
            before = self.snapshot()
            refused = self.run_installer("update", "codex-review-workflow", "--source", target_source)
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("requires all managed groups", refused.stderr)
            self.assertEqual(before, self.snapshot())
        result = self.run_installer("update", "--all", "--source", target_source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_version(target_version)
        if sentinel is not None:
            self.assertEqual(b"unmanaged release fixture; preserve\n", sentinel.read_bytes())
            self.assertEqual(0o600, sentinel.stat().st_mode & 0o777)
            installed = self.home / ".agents/skills/cli-session-handoff/scripts/app_server_handoff.py"
            self.assertEqual((target_source / "skills/cli-session-handoff/scripts/app_server_handoff.py").read_bytes(), installed.read_bytes())
        lesson_policy = self.home / ".codex/templates/orchestration/policies/project-agent-knowledge-policy.md"
        self.assertEqual((target_source / "policies/project-agent-knowledge-policy.md").read_bytes(), lesson_policy.read_bytes())
        retro_metadata = self.home / ".agents/skills/dev-retro/agents/openai.yaml"
        self.assertEqual((target_source / "skills/dev-retro/agents/openai.yaml").read_bytes(), retro_metadata.read_bytes())
        self.assertIn("allow_implicit_invocation: false", retro_metadata.read_text())
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual("0.5.0", receipt["source"]["core"]["version"])
        self.assertIn("codex-agent-profiles", receipt["groups"])
        self.assertEqual(31, len([p for p in core_root.rglob("*") if p.is_file()]))
        self.assertTrue((core_root / "docs/releases/v0.4.0.md").is_file())
        self.assertTrue((core_root / "docs/releases/v0.4.1.md").is_file())
        for path in ("contracts/writing.md", "docs/architecture/original-writing-design.md", "docs/releases/v0.5.0.md"):
            self.assertTrue((core_root / path).is_file())
        self.assertTrue((core_root / "docs/companion/plain-writing-examples.md").is_file())
        self.assertTrue((core_root / "docs/releases/v0.3.0.md").is_file())
        self.assertTrue((core_root / "docs/releases/v0.2.0.md").is_file())
        self.assertTrue((core_root / "docs/releases/v0.1.1.md").is_file())
        extra = core_root / "unknown.md"
        extra.write_bytes(b"unmanaged fixture; preserve on refused downgrade\n")
        extra.chmod(0o600)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--source", old_source, "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())
        extra.unlink()  # Remove only this test-owned input to exercise the accepted path.
        if version in {"0.39.0", "0.40.0"} and version != target_version:
            before = self.snapshot()
            refused = self.run_installer("update", "codex-review-workflow", "--source", old_source)
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("requires all managed groups", refused.stderr)
            self.assertEqual(before, self.snapshot())
        result = self.run_installer("update", "--all", "--source", old_source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_version(version)
        if sentinel is not None:
            self.assertEqual(b"unmanaged release fixture; preserve\n", sentinel.read_bytes())
            self.assertEqual(0o600, sentinel.stat().st_mode & 0o777)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(prior["source"]["catalog_sha256"], receipt["source"]["catalog_sha256"])
        self.assertIn("codex-agent-profiles", receipt["groups"])
        self.assertEqual(prior_files, {p.relative_to(core_root).as_posix(): p.read_bytes()
                                      for p in core_root.rglob("*") if p.is_file()})
        self.assertEqual(prior_directories, sorted(p.relative_to(core_root).as_posix()
                                                  for p in core_root.rglob("*") if p.is_dir()))


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

    def test_traceability_mapping_preserves_previous_catalogs_and_real_identity(self):
        revision = "b45f044d6bc5d66d8fe7ea422f26c2d2286b740f"
        prior = json.loads(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{revision}:installer/source-catalogs.json"]))
        self.assertEqual(prior["catalogs"], REGISTRY["catalogs"][:len(prior["catalogs"])])
        added = REGISTRY["catalogs"][len(prior["catalogs"])]
        self.assertEqual(revision, added["reviewed_revision"])
        self.assertEqual("0.39.0", added["version"])
        raw_catalog = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:catalog.yaml"])
        self.assertEqual(hashlib.sha256(raw_catalog).hexdigest(), added["catalog_sha256"])
        old = next(c for c in prior["catalogs"] if c["reviewed_revision"] ==
                   "c2da9d0b1f029b5816df34a9a5a3e9cadbc3aa70")
        self.assertNotEqual(old["catalog_sha256"], added["catalog_sha256"])
        self.assertEqual(old["core"], added["core"])

    def test_manual_retro_mapping_preserves_thirteen_catalogs_and_real_identity(self):
        revision = "9d6c0bdce2f9b4d18f88a97a71110a57796324fa"
        prior = json.loads(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{revision}:installer/source-catalogs.json"]))
        self.assertEqual(13, len(prior["catalogs"]))
        self.assertEqual(prior["catalogs"], REGISTRY["catalogs"][:13])
        added = REGISTRY["catalogs"][13]
        self.assertEqual(revision, added["reviewed_revision"])
        self.assertEqual("0.39.0", added["version"])
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:catalog.yaml"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), added["catalog_sha256"])
        self.assertNotIn(added["catalog_sha256"], [c["catalog_sha256"] for c in prior["catalogs"]])
        self.assertEqual(prior["catalogs"][-1]["core"], added["core"])
        artifact = next(a for a in added["groups"]["codex-delivery-workflow"]["artifacts"]
                        if a["source"] == "skills/dev-retro")
        self.assertIn("agents/openai.yaml", artifact["files"])
        self.assertIn("references/acceptance-cases.md", artifact["files"])

    def test_v039_traceability_to_current_roundtrip_preserves_core_and_profiles(self):
        self.assert_core_transition("0.39.0", "b45f044d6bc5d66d8fe7ea422f26c2d2286b740f", 31)

    def test_manual_retro_install_is_explicit_only_and_same_version_requires_all(self):
        revision = "b45f044d6bc5d66d8fe7ea422f26c2d2286b740f"
        old = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == revision)
        self.seed("0.39.0", groups=list(old["groups"]), snapshot_revision=revision)
        old_source = self.case / f"source-{revision}"
        newer_source = self.fixed_source("9d6c0bdce2f9b4d18f88a97a71110a57796324fa")
        before = self.snapshot()
        result = self.run_installer("update", "codex-delivery-workflow", "--source", newer_source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires all managed groups", result.stderr)
        self.assertEqual(before, self.snapshot())
        result = self.run_installer("update", "--all", "--source", newer_source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_version("0.39.0")
        skill = self.home / ".agents/skills/dev-retro"
        self.assertEqual((newer_source / "skills/dev-retro/agents/openai.yaml").read_bytes(),
                         (skill / "agents/openai.yaml").read_bytes())
        self.assertIn("allow_implicit_invocation: false", (skill / "agents/openai.yaml").read_text())
        for name in ("projectspec-alignment-policy.md", "project-agent-knowledge-policy.md"):
            self.assertEqual((newer_source / "policies" / name).read_bytes(),
                             (self.home / ".codex/templates/orchestration/policies" / name).read_bytes())
        before = self.snapshot()
        result = self.run_installer("update", "codex-delivery-workflow", "--source", old_source)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("requires all managed groups", result.stderr)
        self.assertEqual(before, self.snapshot())
        result = self.run_installer("update", "--all", "--source", old_source)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(skill.exists())
        self.assertTrue((self.home / ".codex/templates/orchestration/policies/projectspec-alignment-policy.md").is_file())

    def test_v039_core_adoption_to_current_roundtrip_preserves_exact_core_and_profiles(self):
        self.assert_core_transition("0.39.0", "c2da9d0b1f029b5816df34a9a5a3e9cadbc3aa70", 31)

    def test_same_version_catalog_change_requires_all_in_both_directions(self):
        revision = "c2da9d0b1f029b5816df34a9a5a3e9cadbc3aa70"
        old = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == revision)
        self.seed("0.39.0", groups=list(old["groups"]), snapshot_revision=revision)
        old_source = self.case / f"source-{revision}"
        newer_revision = "b45f044d6bc5d66d8fe7ea422f26c2d2286b740f"
        newer = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == newer_revision)
        newer_source = self.fixed_source(newer_revision)
        for source, digest in ((newer_source, newer["catalog_sha256"]),
                               (old_source, old["catalog_sha256"])):
            with self.subTest(source=source):
                before = self.snapshot()
                refused = self.run_installer("update", "codex-review-workflow", "--source", source)
                self.assertNotEqual(0, refused.returncode)
                self.assertIn("requires all managed groups", refused.stderr)
                self.assertEqual(before, self.snapshot())
                result = self.run_installer("update", "--all", "--source", source)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assert_version("0.39.0")
                receipt = json.loads(self.receipt.read_text())
                self.assertEqual(digest, receipt["source"]["catalog_sha256"])
                policy = self.home / ".codex/templates/orchestration/policies/projectspec-alignment-policy.md"
                self.assertEqual((source / "policies/projectspec-alignment-policy.md").read_bytes(), policy.read_bytes())

    def test_v039_manual_retro_to_v040_roundtrip_preserves_core_and_profiles(self):
        self.assert_core_transition(
            "0.39.0", "9d6c0bdce2f9b4d18f88a97a71110a57796324fa", 31,
            target_revision="3a9eef152c07ea4722591aaf3602d5356ce9917b",
        )

    def test_v039_manual_retro_upgrade_rollback_restores_exact_payload(self):
        revision = "9d6c0bdce2f9b4d18f88a97a71110a57796324fa"
        catalog = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == revision)
        self.seed("0.39.0", groups=list(catalog["groups"]), snapshot_revision=revision)
        policy = self.home / ".codex/templates/orchestration/policies/project-agent-knowledge-policy.md"
        self.assertNotEqual((ROOT / "policies/project-agent-knowledge-policy.md").read_bytes(), policy.read_bytes())
        # Core is unchanged, so its lock promotion is not a reliable fault seam.
        # Managed receipt promotion follows payload application; prove it is reached.
        overrides = self.fake_mv("receipt")
        before = self.snapshot()  # Every seed file, receipt and profile, including modes.
        core_root = self.home / ".codex/templates/orchestration/core"
        directories = sorted(p.relative_to(core_root).as_posix()
                             for p in core_root.rglob("*") if p.is_dir())
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode, result.stdout)
        self.assertIn("injected-receipt", result.stderr, "fault seam was not reached")
        self.assertEqual(before, self.snapshot(), result.stderr)
        self.assertEqual(directories, sorted(p.relative_to(core_root).as_posix()
                                            for p in core_root.rglob("*") if p.is_dir()))
        self.assert_version("0.39.0")

    def test_v040_release_to_current_roundtrip_preserves_payload_core_profiles_and_unmanaged(self):
        self.assert_core_transition("0.40.0", "3a9eef152c07ea4722591aaf3602d5356ce9917b", 31)

    def test_v040_workflow_bridge_to_current_roundtrip_preserves_payload_core_profiles_and_unmanaged(self):
        self.assert_core_transition("0.40.0", "6dca8dba0524d81a546c7f6dbf4fbe63bd3a66aa", 31)

    def test_v040_app_server_to_current_roundtrip_preserves_payload_core_profiles_and_unmanaged(self):
        self.assert_core_transition("0.40.0", "22836ce081a69903580b165583be1db4f4a3f637", 31)

    def test_v040_diagnostics_to_current_roundtrip_preserves_payload_core_profiles_and_unmanaged(self):
        self.assert_core_transition("0.40.0", "2827df9779787752b435fb91f0a46f5cd8f74b69", 31)

    def test_v040_integrated_handoff_to_current_roundtrip_preserves_payload_core_profiles_and_unmanaged(self):
        self.assert_core_transition("0.40.0", "fc4eaa3e65e3c49b13695602b71d767b042f19be", 31)

    def test_v040_integrated_to_current_receipt_fault_restores_exact_tree(self):
        revision = "fc4eaa3e65e3c49b13695602b71d767b042f19be"
        catalog = next(c for c in REGISTRY["catalogs"] if c["reviewed_revision"] == revision)
        self.seed("0.40.0", groups=list(catalog["groups"]), snapshot_revision=revision)
        sibling = self.home / ".agents/skills/unmanaged-v041-release/notes.txt"
        sibling.parent.mkdir(parents=True, exist_ok=True)
        sibling.write_bytes(b"unmanaged release fixture; preserve\n")
        sibling.chmod(0o600)
        overrides = self.fake_mv("receipt")
        before = self.snapshot()
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode, result.stdout)
        self.assertIn("injected-receipt", result.stderr, "receipt fault seam was not reached")
        self.assertEqual(before, self.snapshot())
        self.assert_version("0.40.0")

    def test_v040_mapping_preserves_fourteen_real_catalogs(self):
        revision = "3a9eef152c07ea4722591aaf3602d5356ce9917b"
        added = REGISTRY["catalogs"][14]
        self.assertEqual(revision, added["reviewed_revision"])
        self.assertEqual("0.40.0", added["version"])
        prior = json.loads(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{revision}:installer/source-catalogs.json"]))
        self.assertEqual(14, len(prior["catalogs"]))
        self.assertEqual(prior["catalogs"], REGISTRY["catalogs"][:14])
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:catalog.yaml"])
        self.assertEqual(added["catalog_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(prior["catalogs"][-1]["core"], added["core"])

    def test_bridge_mapping_preserves_fifteen_real_catalogs_and_payload_identity(self):
        revision = "6dca8dba0524d81a546c7f6dbf4fbe63bd3a66aa"
        prior = json.loads(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{revision}:installer/source-catalogs.json"]))
        self.assertEqual(15, len(prior["catalogs"]))
        self.assertEqual(prior["catalogs"], REGISTRY["catalogs"][:15])
        added = REGISTRY["catalogs"][15]
        self.assertEqual(revision, added["reviewed_revision"])
        self.assertEqual("0.40.0", added["version"])
        raw = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:catalog.yaml"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), added["catalog_sha256"])
        self.assertNotIn(added["catalog_sha256"], [item["catalog_sha256"] for item in prior["catalogs"]])
        self.assertEqual(prior["catalogs"][-1]["core"], added["core"])
        for path in ("scripts/collect-exact-head-merge-readiness.py",
                     "policies/github-exact-head-enforcement-profile.md"):
            with self.subTest(path=path):
                artifact = next(item for item in added["groups"]["shared-review-gates"]["artifacts"]
                                if item["source"] == path)
                previous = next(item for item in prior["catalogs"][-1]["groups"]["shared-review-gates"]["artifacts"]
                                if item["source"] == path)
                data = subprocess.check_output(["git", "-C", str(ROOT), "show", f"{revision}:{path}"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), artifact["files"][""]["sha256"])
                self.assertNotEqual(previous["files"][""]["sha256"], artifact["files"][""]["sha256"])

    def test_v040_bridge_roundtrip_requires_all_and_preserves_core_and_profiles(self):
        old_revision = "3a9eef152c07ea4722591aaf3602d5356ce9917b"
        new_revision = "6dca8dba0524d81a546c7f6dbf4fbe63bd3a66aa"
        old = next(item for item in REGISTRY["catalogs"] if item["reviewed_revision"] == old_revision)
        new = next(item for item in REGISTRY["catalogs"] if item["reviewed_revision"] == new_revision)
        prior = self.seed("0.40.0", groups=list(old["groups"]), snapshot_revision=old_revision)
        old_source = self.case / f"source-{old_revision}"
        new_source = self.fixed_source(new_revision)
        template_root = self.home / ".codex/templates"
        protected_roots = [template_root / "orchestration/core", self.home / ".codex/agents"]
        core_lock = template_root / "orchestration/core.lock.json"

        def protected_snapshot():
            paths = [core_lock]
            for root in protected_roots:
                paths.extend([root, *root.rglob("*")])
            return {path.relative_to(self.home).as_posix():
                    (path.lstat().st_mode, path.read_bytes() if path.is_file() else None)
                    for path in paths}

        protected = protected_snapshot()
        payload_paths = {
            "scripts/collect-exact-head-merge-readiness.py": template_root / "scripts/collect-exact-head-merge-readiness.py",
            "policies/github-exact-head-enforcement-profile.md": template_root / "orchestration/policies/github-exact-head-enforcement-profile.md",
        }
        for path, target in payload_paths.items():
            self.assertEqual((old_source / path).read_bytes(), target.read_bytes())
            self.assertNotEqual((old_source / path).read_bytes(), (new_source / path).read_bytes())
        for source, catalog in ((new_source, new), (old_source, old)):
            with self.subTest(revision=catalog["reviewed_revision"]):
                before = self.snapshot()
                refused = self.run_installer("update", "shared-review-gates", "--source", source)
                self.assertNotEqual(0, refused.returncode)
                self.assertIn("requires all managed groups", refused.stderr)
                self.assertEqual(before, self.snapshot())
                result = self.run_installer("update", "--all", "--source", source)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assert_version("0.40.0")
                receipt = json.loads(self.receipt.read_text())
                self.assertEqual(catalog["catalog_sha256"], receipt["source"]["catalog_sha256"])
                self.assertEqual(catalog["reviewed_revision"], receipt["source"]["revision"])
                self.assertEqual(prior["groups"], receipt["groups"])
                self.assertIn("codex-agent-profiles", receipt["groups"])
                self.assertEqual(prior["source"]["core"], receipt["source"]["core"])
                self.assertEqual(protected, protected_snapshot())
                for path, target in payload_paths.items():
                    self.assertEqual((source / path).read_bytes(), target.read_bytes())

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
