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
            self.assertEqual(13, value["files"])
            self.assertEqual("0.1.0", value["core_version"])
            self.assertFalse(value["historical_snapshot"])
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

    def test_history_requires_explicit_selection_and_reports_its_own_identity(self):
        old = "43c650e1196a3a702e2240bd79dd24539fa893a7"
        history_root = self.base / "history"
        history = core.HISTORICAL_SNAPSHOTS[0]
        for name in (*history["files"],):
            target = history_root / "vendor/engineering-workflow-core" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(
                ["git", "-C", str(ROOT), "show", f"{old}:vendor/engineering-workflow-core/{name}"]))
        target = history_root / "vendor/engineering-workflow-core.lock.json"
        target.write_bytes(subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{old}:vendor/engineering-workflow-core.lock.json"]))
        with self.assertRaisesRegex(core.SnapshotError, "unreviewed source"):
            core.validate(history_root)
        result = core.validate(history_root, allow_reviewed_history=True)
        self.assertEqual(history["source"]["revision"], result["core_revision"])
        self.assertEqual(history["set_digest"], result["document_set_sha256"])
        self.assertEqual(11, result["files"])
        self.assertTrue(result["historical_snapshot"])
        lock = json.loads(target.read_text())
        lock["source"]["revision"] = "0" * 40
        target.write_text(json.dumps(lock))
        with self.assertRaisesRegex(core.SnapshotError, "unreviewed source"):
            core.validate(history_root, allow_reviewed_history=True)

    def test_tag_object_is_not_the_commit_and_history_cannot_mix_sets(self):
        original = self.lock.read_bytes()
        for field, value in (("revision", core.CURRENT_SNAPSHOT["source"]["tag_object"]),
                             ("tag_object", core.REVISION), ("tag", "v0.2.0"),
                             ("version", None)):
            self.lock.write_bytes(original)
            self.mutate_lock(lambda lock: lock["source"].update({field: value}))
            self.rejected()
        self.lock.write_bytes(original)
        self.mutate_lock(lambda lock: lock.update(source=core.HISTORICAL_SNAPSHOTS[0]["source"]))
        with self.assertRaises(core.SnapshotError):
            core.validate(self.source, allow_reviewed_history=True)

    def test_mutable_wrong_source_or_lock_identities_cannot_repin_the_snapshot(self):
        changes = (
            lambda x: x["source"].update(revision="main"),
            lambda x: x["source"].update(revision="0" * 40),
            lambda x: x["source"].update(
                revision="b4c37798b6d3a9efd91c8c6d518093f2dd847a98",
                reviewed_head="10e97ddde5e04b085da357138ebdae4d0cb5a0f4",
                pull_request=4,
            ),
            lambda x: x["source"].update(
                revision="345cd601bffbacc777f87fb24f22b5caefa30a3b",
                reviewed_head="fc9bd241cb1a058d349c5952ae80ba74d07c56d0",
                pull_request=8,
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
        for data in ('{"contract":"a","contract":"b"}', original.replace('"version": "0.1.0"', '"version": NaN'), "\ufeff" + original):
            with self.subTest(data=data[:30]):
                self.lock.write_text(data)
                self.rejected()
        self.lock.unlink()
        self.rejected()

    def test_unknown_entries_allow_only_the_bounded_lock_before_document_reads(self):
        for name in (".env", "unexpected-empty", "e\u0301"):
            extra = self.snapshot / name
            if name == "unexpected-empty":
                extra.mkdir()
            else:
                extra.write_text("SYNTHETIC unlisted data")
            with self.subTest(name=name), mock.patch.object(core, "regular_bytes", wraps=core.regular_bytes) as read:
                self.rejected()
                self.assertEqual(1, read.call_count)
                self.assertEqual("engineering-workflow-core.lock.json", read.call_args.args[1])
                self.assertEqual(core.MAX_LOCK_BYTES, read.call_args.args[2])
            if extra.is_dir():
                extra.rmdir()
            else:
                extra.unlink()

    def test_invalid_lock_stops_before_inventory_or_document_reads(self):
        original = self.lock.read_bytes()
        unsupported = json.loads(original)
        unsupported["contract"] = "unsupported/v1"
        unreviewed = json.loads(original)
        unreviewed["source"]["revision"] = "0" * 40
        for data in (b"{", json.dumps(unsupported).encode(), json.dumps(unreviewed).encode()):
            self.lock.write_bytes(data)
            with self.subTest(data=data[:40]), \
                    mock.patch.object(core, "regular_bytes", wraps=core.regular_bytes) as read, \
                    mock.patch.object(core, "inventory") as inventory:
                with self.assertRaises(core.SnapshotError):
                    core.validate(self.source)
                inventory.assert_not_called()
                self.assertEqual(1, read.call_count)
                self.assertEqual("engineering-workflow-core.lock.json", read.call_args.args[1])
                self.assertEqual(core.MAX_LOCK_BYTES, read.call_args.args[2])

    def test_lock_permissions_fail_before_document_reads_in_both_layouts(self):
        destination = self.base / "filesystem"
        orchestration = destination / "orchestration"
        orchestration.mkdir(parents=True)
        shutil.copytree(self.snapshot, orchestration / "core")
        shutil.copyfile(self.lock, orchestration / "core.lock.json")
        for path in orchestration.rglob("*"):
            if path.is_file():
                path.chmod(0o600)
        for root, layout, lock, modes in (
                (self.source, "source", self.lock, (0o000, 0o620, 0o646, 0o755)),
                (destination, "filesystem", orchestration / "core.lock.json", (0o644, 0o400))):
            core.validate(root, layout)  # A valid fixture precedes each negative family.
            for mode in modes:
                lock.chmod(mode)
                with self.subTest(layout=layout, mode=oct(mode)), \
                        mock.patch.object(core, "regular_bytes", wraps=core.regular_bytes) as read, \
                        mock.patch.object(core, "inventory") as inventory:
                    with self.assertRaises((core.SnapshotError, OSError)):
                        core.validate(root, layout)
                    inventory.assert_not_called()
                    self.assertEqual(1, read.call_count)
                    self.assertEqual(lock.name, read.call_args.args[1])
            lock.chmod(0o600 if layout == "filesystem" else 0o644)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_lock_fifo_is_rejected_with_a_bounded_cli_call(self):
        self.lock.unlink()
        os.mkfifo(self.lock, 0o600)
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--root", str(self.source)],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(1, result.returncode)
        self.assertEqual("rejected", json.loads(result.stderr)["status"])
        self.assertIn("must be regular", json.loads(result.stderr)["error"])
        self.assertEqual("", result.stdout)

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
                self.assertEqual(1, read.call_count)
                self.assertEqual("engineering-workflow-core.lock.json", read.call_args.args[1])
                self.assertEqual(core.MAX_LOCK_BYTES, read.call_args.args[2])

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
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("CODEX_", "GIT_"))}
        env.update(HOME=str(home), XDG_STATE_HOME=str(home / "state"), CODEX_CLI=str(self.cli_probe),
                   CODEX_HOME=str(home / ".codex"),
                   PATH=str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", ""))
        return env

    def fixed_source(self, env, revision, name):
        source = self.base / name
        for command in (["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(ROOT), str(source)],
                        ["git", "-C", str(source), "remote", "set-url", "origin",
                         "https://github.com/jeffery777/codex-dev-skills.git"],
                        ["git", "-C", str(source), "checkout", "--quiet", "--detach", revision]):
            subprocess.run(command, env=env, check=True, capture_output=True)
        return source

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
        partial.write_bytes(b"local reviewed receipt-managed candidate\n")
        partial.chmod(0o600)
        core.preflight_destination(templates)
        with self.assertRaises((core.SnapshotError, OSError)):
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
                    self.assertIn("unmanaged existing content", run.stderr)
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

    def test_final_snapshot_failure_never_publishes_success_or_new_receipts(self):
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
                before_receipts = {p.name: (p.stat().st_mode, p.read_bytes())
                                   for p in state.parent.iterdir() if p.is_file()} if state.parent.exists() else {}
                args = ["update" if action == "force" else action, "shared-review-gates"]
                if action == "force":
                    args.append("--force")
                run = subprocess.run(["bash", "-c", injected, "postcondition-test", str(ROOT), *args],
                                     cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
                self.assertNotEqual(0, run.returncode, run.stdout)
                self.assertIn("unexpected snapshot entry: raced.md", run.stderr)
                self.assertEqual(before, state.read_bytes() if state.exists() else None)
                self.assertEqual(before_receipts, {p.name: (p.stat().st_mode, p.read_bytes())
                                                  for p in state.parent.iterdir() if p.is_file()})
                self.assertEqual(b"preserve raced entry\n", (readme.parent / "raced.md").read_bytes())
                if action == "force":
                    self.assertEqual((self.snapshot / "README.md").read_bytes(), readme.read_bytes())

    def test_force_update_refuses_modified_core_without_adoption(self):
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
        before = {p.name: (p.stat().st_mode, p.read_bytes())
                  for p in state.parent.iterdir() if p.is_file()}
        refused = subprocess.run([str(ROOT / "install.sh"), "update", "shared-review-gates", "--force"],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("custom, missing, or unknown managed content", refused.stderr)
        self.assertEqual(local, readme.read_bytes())
        self.assertEqual(before, {p.name: (p.stat().st_mode, p.read_bytes())
                                  for p in state.parent.iterdir() if p.is_file()})
        self.assertFalse(list((templates / "orchestration").rglob(".codex-dev-skills.*")))

    def test_cross_device_staging_refuses_managed_core_upgrade(self):
        home = self.base / "upgrade-core"
        home.mkdir()
        env = self.installer_env(home)
        old_source = self.fixed_source(env, "6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c", "old-source")
        installed = subprocess.run([str(ROOT / "install.sh"), "install", "shared-review-gates",
                                    "--source", str(old_source)],
                                   cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, installed.returncode, installed.stderr)
        templates = home / ".codex/templates"
        state = home / "state/codex-dev-skills"
        def installed_snapshot():
            return {(label, str(p.relative_to(root))): (p.stat().st_mode, p.read_bytes())
                    for label, root in (("templates", templates), ("skills", home / ".agents/skills"),
                                        ("state", state)) for p in root.rglob("*") if p.is_file()}
        before = installed_snapshot()
        injected = (ROOT / "install.sh").read_text().rsplit('main "$@"', 1)[0]
        injected = injected.replace('ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', 'ROOT_DIR="$1"')
        injected += r'''
eval "$(declare -f path_device | sed '1s/path_device/original_path_device/')"
path_device() {
  if [[ "$1" == "$CODEX_TEMPLATES_DIR/orchestration" ]]; then
    printf 'injected-core-device\n' >&2
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
        self.assertIn("cross-filesystem transaction staging for templates orchestration/core:", refused.stderr)
        self.assertEqual(1, refused.stderr.count("injected-core-device"))
        self.assertEqual(before, installed_snapshot())
        self.assertFalse((templates / "orchestration/core").exists())
        self.assertFalse(list((templates / "orchestration").rglob(".codex-dev-skills.*")))
        updated = subprocess.run([str(ROOT / "install.sh"), "update", "shared-review-gates", "--force"],
                                 cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertEqual(core.SET_DIGEST, core.validate(templates, "filesystem")["document_set_sha256"])
        self.assertFalse(list((state / "backups/v1").glob("transaction.*")))
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
        env = self.installer_env(home)
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        source = self.fixed_source(env, revision, "complete-source")
        (source / "vendor/engineering-workflow-core/README.md").write_text("tampered")
        for action in ("install", "update"):
            run = subprocess.run([str(ROOT / "install.sh"), action, "shared-review-gates", "--source", str(source)],
                                 cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertNotEqual(0, run.returncode)
            self.assertIn("source payload differs from reviewed catalog: vendor/engineering-workflow-core", run.stderr)
            self.assertEqual([sentinel], list(home.iterdir()))
            self.assertEqual("keep", sentinel.read_text())
        run = subprocess.run([sys.executable, "-B", str(scripts / "sync-plugin-package.py"), "--write"],
                             cwd=self.source, capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertIn("core_snapshot.validate(ROOT)", run.stderr)
        self.assertIn("SnapshotError: file size does not match lock", run.stderr)
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
