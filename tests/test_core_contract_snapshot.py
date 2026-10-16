from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-core-contract-snapshot.py"
SPEC = importlib.util.spec_from_file_location("core_snapshot_test", SCRIPT)
core = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(core)


class CoreSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="core-snapshot-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.cli_probe = self.base / "codex-probe"
        self.cli_probe.write_text("#!/bin/sh\nprintf '%s\\n' '{\"installed\":[]}'\n")
        self.cli_probe.chmod(0o700)
        self.source = self.base / "source"
        self.source.mkdir()
        shutil.copytree(ROOT / "vendor", self.source / "vendor")
        self.snapshot = self.source / "vendor/engineering-workflow-core"
        self.lock = self.source / "vendor/engineering-workflow-core.lock.json"

    def mutate_lock(self, change):
        value = json.loads(self.lock.read_text())
        change(value)
        self.lock.write_text(json.dumps(value))

    def rejected(self):
        with self.assertRaises((core.SnapshotError, OSError, UnicodeError)):
            core.validate(self.source)

    def test_fixed_source_and_generated_plugin_have_the_same_identity(self):
        for root in (ROOT, ROOT / "plugin/codex-dev-skills"):
            value = core.validate(root)
            self.assertEqual(core.REVISION, value["core_revision"])
            self.assertEqual(core.SET_DIGEST, value["document_set_sha256"])
            self.assertEqual(11, value["files"])
            self.assertIs(False, value["runtime_qualified"])
            self.assertIs(False, value["authorization_granted"])

    def test_published_handoff_algorithm_is_separate_from_codex_set_algorithm(self):
        value = json.loads(self.lock.read_text())
        rows = value["document_set"]["files"]
        upstream = "".join(r["path"] + "\t" + r["sha256"] + "\n"
                           for r in rows if r["path"].endswith(".md"))
        self.assertEqual(core.MARKDOWN_DIGEST, core.sha256(upstream.encode()))
        self.assertNotEqual(core.MARKDOWN_DIGEST, core.sha256(upstream.rstrip("\n").encode()))
        self.assertNotEqual(core.MARKDOWN_DIGEST, core.canonical_set(rows))
        self.assertEqual(core.SET_DIGEST, core.canonical_set(rows))
        self.assertEqual(core.LICENSE_DIGEST, core.sha256((self.snapshot / "LICENSE").read_bytes()))

    def test_mutable_wrong_source_or_lock_identities_cannot_repin_the_snapshot(self):
        changes = (
            lambda x: x["source"].update(revision="main"),
            lambda x: x["source"].update(revision="0" * 40),
            lambda x: x["source"].update(
                revision="b4c37798b6d3a9efd91c8c6d518093f2dd847a98",
                reviewed_head="10e97ddde5e04b085da357138ebdae4d0cb5a0f4",
                pull_request=4,
            ),
            lambda x: x["source"].update(repository="someone/another-core"),
            lambda x: x["source"].update(reviewed_head="0" * 40),
            lambda x: x["source"].update(version="unverified"),
            lambda x: x["consumer"].update(repository="someone/another-adapter"),
            lambda x: x["upstream_markdown_set"].update(algorithm="canonical-json"),
            lambda x: x["document_set"].update(sha256="0" * 64),
        )
        original = self.lock.read_bytes()
        for change in changes:
            with self.subTest(change=change):
                self.lock.write_bytes(original)
                self.mutate_lock(change)
                self.rejected()

    def test_paths_modes_sizes_duplicates_and_rewritten_hashes_are_rejected(self):
        cases = (
            ("path", "../outside.md"), ("path", "/etc/passwd"),
            ("path", "contracts//workflow.md"), ("path", "README.MD"),
            ("mode", "100755"), ("size_bytes", True),
            ("size_bytes", core.MAX_FILE_BYTES + 1), ("sha256", "0" * 64),
        )
        original = self.lock.read_bytes()
        for key, value in cases:
            with self.subTest(key=key, value=value):
                self.lock.write_bytes(original)
                self.mutate_lock(lambda x: x["document_set"]["files"][0].update({key: value}))
                self.rejected()
        self.lock.write_bytes(original)
        self.mutate_lock(lambda x: x["document_set"]["files"].reverse())
        self.rejected()
        self.lock.write_bytes(original)
        self.mutate_lock(lambda x: x["document_set"]["files"].__setitem__(1, x["document_set"]["files"][0]))
        self.rejected()

    def test_missing_or_ambiguous_json_does_not_load_another_lock(self):
        original = self.lock.read_text()
        for data in ('{"contract":"a","contract":"b"}', original.replace("null", "NaN"), "\ufeff" + original):
            with self.subTest(data=data[:30]):
                self.lock.write_text(data)
                self.rejected()
        self.lock.unlink()
        self.rejected()

    def test_unknown_entries_are_rejected_before_lock_or_document_byte_reads(self):
        for name in (".env", "unexpected-empty", "e\u0301"):
            extra = self.snapshot / name
            if name == "unexpected-empty":
                extra.mkdir()
            else:
                extra.write_text("SYNTHETIC unlisted data")
            with self.subTest(name=name), mock.patch.object(core, "regular_bytes", wraps=core.regular_bytes) as read:
                self.rejected()
                read.assert_not_called()
            if extra.is_dir():
                extra.rmdir()
            else:
                extra.unlink()

    def test_case_alias_cannot_hide_changed_bytes_on_case_insensitive_filesystems(self):
        alias = self.snapshot / "README.MD"
        canonical = self.snapshot / "README.md"
        if alias.exists():
            self.assertTrue(alias.samefile(canonical))
            alias.write_text("SYNTHETIC case alias tamper")
            self.rejected()
        else:
            alias.write_text("SYNTHETIC colliding name")
            with mock.patch.object(core, "regular_bytes", wraps=core.regular_bytes) as read:
                self.rejected()
                read.assert_not_called()

    def test_missing_tampered_notice_or_document_and_executable_mode_fail(self):
        for name in ("contracts/workflow.md", "docs/provenance/upstream-notices.md", "LICENSE"):
            path = self.snapshot / name
            original = path.read_bytes()
            with self.subTest(name=name, case="missing"):
                path.unlink()
                self.rejected()
            path.write_bytes(b"!" + original[1:])
            with self.subTest(name=name, case="same-size tamper"):
                self.rejected()
            path.write_bytes(original)
        path = self.snapshot / "README.md"
        path.chmod(0o755)
        self.rejected()

    def test_symlink_file_lock_directory_and_root_fail(self):
        path = self.snapshot / "README.md"
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(ROOT / "vendor/engineering-workflow-core/README.md")
        self.rejected()
        path.unlink()
        path.write_bytes(original)
        lock_bytes = self.lock.read_bytes()
        self.lock.unlink()
        self.lock.symlink_to(ROOT / "vendor/engineering-workflow-core.lock.json")
        self.rejected()
        self.lock.unlink()
        self.lock.write_bytes(lock_bytes)
        outside = self.base / "outside"
        (self.source / "vendor").rename(outside)
        (self.source / "vendor").symlink_to(outside, target_is_directory=True)
        self.rejected()
        alias = self.base / "alias"
        alias.symlink_to(ROOT, target_is_directory=True)
        with self.assertRaises(core.SnapshotError):
            core.validate(alias)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_special_file_is_rejected_without_blocking(self):
        path = self.snapshot / "README.md"
        path.unlink()
        os.mkfifo(path)
        self.rejected()

    def test_oversize_lock_and_file_are_rejected(self):
        self.lock.write_bytes(b" " * (core.MAX_LOCK_BYTES + 1))
        self.rejected()
        shutil.copyfile(ROOT / "vendor/engineering-workflow-core.lock.json", self.lock)
        (self.snapshot / "README.md").write_bytes(b"x" * (core.MAX_FILE_BYTES + 1))
        self.rejected()

    def test_local_link_and_anchor_boundary_does_not_follow_provenance_urls(self):
        for target in ("../outside.md", "/etc/passwd", "missing.md", "#absent"):
            with self.subTest(target=target), self.assertRaises(core.SnapshotError):
                core.check_links({"README.md": "[bad](" + target + ")"})
        core.check_links({"README.md": '# Title\n<a id="ok"></a>\n[ok](#ok)\n[origin](https://example.invalid/unavailable)'})

    def installer_env(self, home):
        env = os.environ.copy()
        for key in ("CODEX_CLI", "CODEX_SKILLS_DIR", "CODEX_TEMPLATES_DIR",
                    "CODEX_CUSTOM_AGENTS_DIR", "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS",
                    "CODEX_DEV_SKILLS_TARGET"):
            env.pop(key, None)
        env.update(HOME=str(home), XDG_STATE_HOME=str(home / "state"), CODEX_CLI=str(self.cli_probe),
                   PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""))
        return env

    def test_default_custom_and_legacy_filesystem_installs_have_a_standalone_valid_snapshot(self):
        for variant in ("default", "custom", "legacy"):
            with self.subTest(variant=variant):
                home = self.base / variant
                home.mkdir()
                env = self.installer_env(home)
                templates = home / ".codex/templates"
                if variant == "custom":
                    templates = home / "chosen/templates"
                    env.update(CODEX_TEMPLATES_DIR=str(templates), CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS="YES")
                if variant == "legacy":
                    env["CODEX_DEV_SKILLS_TARGET"] = "legacy"
                group = "codex-delivery-workflow" if variant == "default" else "shared-review-gates"
                run = subprocess.run([str(ROOT / "install.sh"), "install", group],
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
                self.assertEqual(0, run.returncode, run.stderr)
                self.assertEqual(core.SET_DIGEST, core.validate(templates, "filesystem")["document_set_sha256"])
                self.assertEqual((ROOT / "vendor/engineering-workflow-core.lock.json").read_bytes(),
                                 (templates / "orchestration/core.lock.json").read_bytes())
                native = templates / "docs/native-runtime-capabilities.md"
                self.assertEqual((ROOT / "docs/native-runtime-capabilities.md").read_bytes(), native.read_bytes())
                native_reference = "${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/docs/native-runtime-capabilities.md"
                for name, count in (("engineering-workflow-contract.md", 1), ("reusable-workflow-details.md", 2)):
                    policy = templates / "orchestration/policies" / name
                    text = policy.read_text()
                    self.assertEqual(count, text.count(native_reference))
                    self.assertEqual(count, text.count("(source/plugin)](../docs/native-runtime-capabilities.md"))
                for path in core.FILES:
                    installed = templates / "orchestration/core" / path
                    self.assertEqual((self.snapshot / path).read_bytes(), installed.read_bytes())
                    self.assertEqual(0o600, stat.S_IMODE(installed.stat().st_mode))
                run = subprocess.run([sys.executable, "-B", str(templates / "scripts/validate-core-contract-snapshot.py"),
                                      "--root", str(templates), "--layout", "filesystem"],
                                     cwd=home, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(0, run.returncode, run.stderr)
                self.assertIs(False, json.loads(run.stdout)["runtime_qualified"])
                (templates / "orchestration/core/README.md").chmod(0o644)
                with self.assertRaisesRegex(core.SnapshotError, "0600"):
                    core.validate(templates, "filesystem")

    def test_destination_preflight_allows_only_safe_partial_listed_resources(self):
        templates = self.base / "templates"
        core.preflight_destination(templates)  # No target creation.
        self.assertFalse(templates.exists())
        snapshot = templates / "orchestration/core"
        snapshot.mkdir(parents=True)
        partial = snapshot / "README.md"
        partial.write_bytes(b"local reviewed force-update candidate\n")
        partial.chmod(0o600)
        core.preflight_destination(templates)
        with self.assertRaises(core.SnapshotError):
            core.validate(templates, "filesystem")  # Preflight is not full acceptance.
        for kind in ("symlink", "directory", "oversize", "mode"):
            partial.unlink() if partial.is_file() or partial.is_symlink() else partial.rmdir()
            if kind == "symlink":
                partial.symlink_to(self.snapshot / "README.md")
            elif kind == "directory":
                partial.mkdir()
            else:
                partial.write_bytes(b"x" * (core.MAX_FILE_BYTES + 1) if kind == "oversize" else b"keep")
                partial.chmod(0o600 if kind == "oversize" else 0o644)
            with self.subTest(kind=kind), self.assertRaises((core.SnapshotError, OSError)):
                core.preflight_destination(templates)

    def test_install_update_and_force_reject_invalid_destination_before_mutation(self):
        def snapshot_tree(root):
            return [(p.relative_to(root).as_posix(), stat.S_IMODE(p.stat().st_mode),
                     p.read_bytes() if p.is_file() else None) for p in sorted(root.rglob("*"))]

        for action in ("install", "update", "force"):
            for case in ("unknown-entry", "same-bytes-wrong-mode"):
                with self.subTest(action=action, case=case):
                    home = self.base / (action + case)
                    snapshot = home / ".codex/templates/orchestration/core"
                    snapshot.mkdir(parents=True)
                    path = snapshot / ("unlisted.md" if case == "unknown-entry" else "README.md")
                    path.write_bytes(b"preserve unknown bytes" if case == "unknown-entry" else
                                     (self.snapshot / "README.md").read_bytes())
                    path.chmod(0o600 if case == "unknown-entry" else 0o644)
                    before = snapshot_tree(home)
                    args = ["update" if action == "force" else action, "shared-review-gates"]
                    if action == "force":
                        args.append("--force")
                    run = subprocess.run([str(ROOT / "install.sh"), *args], cwd=ROOT,
                                         env=self.installer_env(home), capture_output=True, text=True, timeout=20)
                    self.assertNotEqual(0, run.returncode, run.stdout)
                    self.assertIn("unexpected snapshot entry" if case == "unknown-entry" else "0600", run.stderr)
                    self.assertEqual(before, snapshot_tree(home))

    def test_destination_preflight_bounds_aggregate_bytes_and_rejects_ancestor_links(self):
        templates = self.base / "bounded-templates"
        snapshot = templates / "orchestration/core"
        snapshot.mkdir(parents=True)
        for name in ("LICENSE", "README.md", "contracts/workflow.md"):
            path = snapshot / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"x" * (100 * 1024))
            path.chmod(0o600)
        with self.assertRaisesRegex(core.SnapshotError, "total size"):
            core.preflight_destination(templates)
        alias = self.base / "linked-templates"
        alias.mkdir()
        (alias / "orchestration").symlink_to(templates / "orchestration", target_is_directory=True)
        with self.assertRaises(OSError):
            core.preflight_destination(alias)

    def test_final_snapshot_failure_never_publishes_success_and_force_rolls_back(self):
        # Inject drift at the real postcondition boundary, then invoke the real
        # validator. No source edits or persistent consumer installation.
        injected = (ROOT / "install.sh").read_text().rsplit('main "$@"', 1)[0]
        injected = injected.replace('ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', 'ROOT_DIR="$1"')
        injected += r'''
eval "$(declare -f verify_installed_core | sed '1s/verify_installed_core/original_verify_installed_core/')"
verify_installed_core() {
  (umask 077; printf 'preserve raced entry\n' > "$CODEX_TEMPLATES_DIR/orchestration/core/raced.md")
  original_verify_installed_core "$@"
}
shift
main "$@"
'''
        for action in ("install", "update", "force"):
            with self.subTest(action=action):
                home = self.base / ("postcondition-" + action)
                home.mkdir()
                env = self.installer_env(home)
                state = home / "state/codex-dev-skills/installed.jsonl"
                readme = home / ".codex/templates/orchestration/core/README.md"
                before = None
                if action != "install":
                    installed = subprocess.run([str(ROOT / "install.sh"), "install", "shared-review-gates"],
                                               cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
                    self.assertEqual(0, installed.returncode, installed.stderr)
                    before = state.read_bytes()
                if action == "force":
                    readme.write_bytes(b"local bytes to restore\n")
                args = ["update" if action == "force" else action, "shared-review-gates"]
                if action == "force":
                    args.append("--force")
                run = subprocess.run(["bash", "-c", injected, "postcondition-test", str(ROOT), *args],
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
                self.assertNotEqual(0, run.returncode, run.stdout)
                self.assertIn("unexpected snapshot entry: raced.md", run.stderr)
                self.assertEqual(before, state.read_bytes() if state.exists() else None)
                self.assertEqual(b"preserve raced entry\n", (readme.parent / "raced.md").read_bytes())
                if action == "force":
                    self.assertEqual(b"local bytes to restore\n", readme.read_bytes())

    def test_force_update_of_modified_core_uses_closed_set_and_preserves_backup(self):
        home = self.base / "force-core"
        home.mkdir()
        env = self.installer_env(home)
        args = [str(ROOT / "install.sh"), "install", "shared-review-gates"]
        installed = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, installed.returncode, installed.stderr)
        templates = home / ".codex/templates"
        readme = templates / "orchestration/core/README.md"
        local = b"reviewed local modification\n"
        readme.write_bytes(local)
        state = home / "state/codex-dev-skills/installed.jsonl"
        before = state.read_bytes()
        injected = (ROOT / "install.sh").read_text().rsplit('main "$@"', 1)[0]
        injected = injected.replace('ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', 'ROOT_DIR="$1"')
        injected += r'''
eval "$(declare -f path_device | sed '1s/path_device/original_path_device/')"
path_device() {
  if [[ "$1" == "$CODEX_TEMPLATES_DIR/orchestration" ]]; then
    printf 'synthetic-other-device\n'
  else
    original_path_device "$@"
  fi
}
main update shared-review-gates --force
'''
        refused = subprocess.run(["bash", "-c", injected, "staging-device-test", str(ROOT)],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("cross-filesystem Core staging", refused.stderr)
        self.assertEqual(local, readme.read_bytes())
        self.assertEqual(before, state.read_bytes())
        self.assertFalse(list((templates / "orchestration").rglob(".codex-dev-skills.*")))
        updated = subprocess.run([str(ROOT / "install.sh"), "update", "shared-review-gates", "--force"],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertEqual(core.SET_DIGEST, core.validate(templates, "filesystem")["document_set_sha256"])
        backups = list((home / "state/codex-dev-skills/backups/v1").glob("*/templates/orchestration/core/README.md.bak"))
        self.assertEqual(1, len(backups))
        self.assertEqual(local, backups[0].read_bytes())
        self.assertFalse(list((templates / "orchestration").rglob(".codex-dev-skills.*")))

    def test_invalid_source_preflight_does_not_create_targets_or_promote_a_plugin(self):
        scripts = self.source / "scripts"
        scripts.mkdir()
        shutil.copy2(SCRIPT, scripts / SCRIPT.name)
        for name in ("sync-plugin-package.py",):
            shutil.copy2(ROOT / "scripts" / name, scripts / name)
        shutil.copy2(ROOT / "install.sh", self.source / "install.sh")
        (self.snapshot / "README.md").write_text("tampered")
        home = self.base / "untouched-home"
        home.mkdir()
        sentinel = home / "existing"
        sentinel.write_text("keep")
        for action in ("install", "update"):
            run = subprocess.run([str(self.source / "install.sh"), action, "shared-review-gates"],
                                 cwd=self.source, env=self.installer_env(home), capture_output=True, text=True)
            self.assertNotEqual(0, run.returncode)
            self.assertEqual([sentinel], list(home.iterdir()))
            self.assertEqual("keep", sentinel.read_text())
        run = subprocess.run([sys.executable, "-B", str(scripts / "sync-plugin-package.py"), "--write"],
                             cwd=self.source, capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertFalse((self.source / "plugin").exists())

    def test_wrong_explicit_root_cannot_borrow_valid_cwd_or_another_installation(self):
        empty = self.base / "empty"
        empty.mkdir()
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), "--root", str(empty)],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertNotIn('"status": "verified"', run.stdout)

    def test_existing_hermes_resource_closure_keeps_core_without_qualifying_runtime(self):
        spec = importlib.util.spec_from_file_location("hermes_closure", ROOT / "scripts/hermes-package.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        files = module.package()
        for name in core.FILES:
            self.assertEqual((self.snapshot / name).read_bytes(),
                             files["vendor/engineering-workflow-core/" + name])
        target = self.base / "hermes-package"
        module.install(target, files)
        self.assertEqual(core.SET_DIGEST, core.validate(target)["document_set_sha256"])
        self.assertEqual([], module.compare(target, files))


if __name__ == "__main__":
    unittest.main()
