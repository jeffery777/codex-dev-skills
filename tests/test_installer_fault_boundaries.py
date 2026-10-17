from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import unittest

from tests.test_installer_source_integrity import InstallerFixture, ROOT, inventory


class InstallerFaultBoundaryTests(InstallerFixture):
    def command(self, name, body, variables=None):
        directory = self.case / "interceptors"
        directory.mkdir(exist_ok=True)
        actual = sys.executable if name == "python3" else shutil.which(name)
        script = directory / name
        script.write_text('#!/bin/bash\nset -eu\n' + body + '\nexec ' + json.dumps(actual) + ' "$@"\n')
        script.chmod(0o700)
        return {"PATH": str(directory) + os.pathsep + self.env["PATH"],
                "FAULT_MARKER": str(self.case / "injected"), "REAL_COMMAND": actual, **(variables or {})}

    def payload_unchanged(self, receipt):
        inventory.check_payload(receipt["artifacts"], receipt["roots"])

    def profile_receipt(self, receipt):
        digest = hashlib.sha256(self.roots["agent_profiles"].encode()).hexdigest()
        path = self.state / ("agent-profile-" + digest + ".tsv")
        path.write_text("".join(item["relative"] + "\t" + item["files"][""]["sha256"] + "\n"
                                for item in receipt["artifacts"] if item["kind"] == "agent_profiles"))
        path.chmod(0o600)
        return path

    def test_active_late_backup_collision_stops_before_promotion(self):
        receipt = self.seed()
        overrides = self.command("cp", '''
if [[ "$*" == *".tmp."* && ! -e "$FAULT_MARKER" ]]; then
  : > "$FAULT_MARKER"
  for tx in "$XDG_STATE_HOME/codex-dev-skills/backups/v1"/transaction.*; do
    for folder in "$tx/originals"/*/skills; do
      printf 'unknown collision' > "$folder/code-review.bak"
    done
  done
  echo injected-active-slot >&2
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-active-slot", result.stderr)
        self.assertIn("backup path", result.stderr)
        self.payload_unchanged(receipt)
        self.assertEqual(receipt, json.loads(self.receipt.read_text()))
        occupied = list((self.state / "backups/v1").rglob("code-review.bak"))
        self.assertEqual(["unknown collision"], [p.read_text() for p in occupied])

    def staged_interceptor(self, mode):
        body = '''
if [[ "$2" == "verify-staged" && ! -e "$FAULT_MARKER" ]]; then
  input="$(cat)"
  : > "$FAULT_MARKER"
  while IFS=$'\t' read -r kind relative stage; do
    [[ "$kind" == skills && "$relative" == closure-triage ]] || continue
    path="$stage/SKILL.md"
    if [[ "$FAULT_MODE" == symlink ]]; then
      rm "$path"; ln -s "$UNMANAGED" "$path"
    else printf 'unknown staged bytes' > "$path"; fi
  done < <(printf '%s\n' "$input" | tail -n +2)
  echo injected-staged >&2
  printf '%s\n' "$input" | "$REAL_COMMAND" "$@"; exit $?
fi'''
        if mode == "promotion":
            body = '''
if [[ "$2" == "verify-staged" ]]; then
  input="$(cat)"
  while IFS=$'\t' read -r kind relative stage; do
    [[ "$kind" == skills && "$relative" == closure-triage ]] || continue
    printf '%s' "$stage/SKILL.md" > "$ACTIVE_STAGE"
  done < <(printf '%s\n' "$input" | tail -n +2)
  printf '%s\n' "$input" | "$REAL_COMMAND" "$@"; : > "$READY_MARKER"; exit 0
fi
if [[ "$2" == identity && "$3" == "$INSTALLED" && -e "$READY_MARKER" && ! -e "$FAULT_MARKER" ]]; then
  : > "$FAULT_MARKER"
  path="$(cat "$ACTIVE_STAGE")"
  printf 'unknown staged bytes' > "$path"
  echo injected-staged >&2
fi'''
        unknown = self.case / "unmanaged"
        unknown.write_text("unmanaged sentinel")
        return self.command("python3", body, {"FAULT_MODE": mode, "UNMANAGED": str(unknown),
            "INSTALLED": str(self.home / ".agents/skills/closure-triage"), "READY_MARKER": str(self.case / "ready"),
            "ACTIVE_STAGE": str(self.case / "active-stage")})

    def test_staged_byte_symlink_and_late_identity_drift_are_rejected(self):
        receipt = self.seed()
        for mode in ("bytes", "symlink", "promotion"):
            with self.subTest(mode=mode):
                overrides = self.staged_interceptor(mode)
                result = self.run_installer("update", "--all", overrides=overrides)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("injected-staged", result.stderr)
                self.payload_unchanged(receipt)
                self.assertEqual(receipt, json.loads(self.receipt.read_text()))
                self.assertEqual("unmanaged sentinel", (self.case / "unmanaged").read_text())
                stages = list((self.state / "backups/v1").glob("transaction.*/.codex-dev-skills.closure-triage.tmp.*/value/SKILL.md"))
                if mode == "symlink":
                    self.assertTrue(any(p.is_symlink() and p.resolve() == self.case / "unmanaged" for p in stages))
                else:
                    self.assertTrue(any(not p.is_symlink() and p.read_text() == "unknown staged bytes" for p in stages))
                (self.case / "injected").unlink()

    def test_all_receipt_readback_drift_preserves_unknown_and_original(self):
        receipt = self.seed(groups=["shared-review-gates", "codex-delivery-workflow", "codex-agent-profiles"])
        profile = self.profile_receipt(receipt)
        for target in (self.state / "installed.jsonl", self.receipt, profile):
            with self.subTest(target=target.name):
                # Each iteration is isolated: the injected unknown must remain.
                before = target.read_bytes()
                overrides = self.command("mv", '''
if [[ "$1" == *.receipt.*/value && "$2" == "$DRIFT_RECEIPT" ]]; then
  "$REAL_COMMAND" "$@"; printf '\\nunknown receipt edit' >> "$2"
  echo injected-readback >&2; exit 0
fi''', {"DRIFT_RECEIPT": str(target)})
                result = self.run_installer("update", "--all", overrides=overrides)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("injected-readback", result.stderr)
                self.assertIn("CRITICAL", result.stderr)
                self.assertTrue(target.read_bytes().endswith(b"unknown receipt edit"))
                originals = list(self.state.glob(".codex-dev-skills." + target.name + ".receipt.*/original"))
                self.assertTrue(any(p.read_bytes() == before for p in originals))
                self.payload_unchanged(receipt)
                # Restore only this test's deliberately injected fixture state.
                target.write_bytes(before)

    def test_cleanup_preserves_unknown_workspace_data_and_changed_original(self):
        receipt = self.seed()
        overrides = self.command("mv", '''
if [[ "$1" == *.receipt.*/value && "$2" == */managed-*.json ]]; then
  "$REAL_COMMAND" "$@"
  for tx in "$XDG_STATE_HOME/codex-dev-skills/backups/v1"/transaction.*; do
    printf 'unknown workspace note' > "$tx/notes.txt"
    for original in "$tx/originals"/*/skills/closure-triage.bak/SKILL.md; do
      printf 'changed original' > "$original"
    done
  done
  echo injected-cleanup >&2; exit 0
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-cleanup", result.stderr)
        self.assertIn("original changed", result.stderr)
        self.assertTrue(any(p.read_text() == "unknown workspace note" for p in (self.state / "backups/v1").rglob("notes.txt")))
        self.assertTrue(any(p.read_text() == "changed original" for p in (self.state / "backups/v1").rglob("closure-triage.bak/SKILL.md")))

    def test_cleanup_rm_and_unlock_failures_return_nonzero_and_preserve_data(self):
        self.seed()
        overrides = self.command("rm", '''
if [[ "$*" == *".bak"* ]]; then echo injected-rm >&2; exit 73; fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-rm", result.stderr)
        self.assertTrue(list((self.state / "backups/v1").rglob("*.bak")))
        # Payload and receipts committed; retry is a same-source no-op.
        overrides = self.command("rmdir", '''
if [[ "$1" == */.transaction.lock ]]; then echo injected-unlock >&2; exit 74; fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-unlock", result.stderr)
        self.assertTrue((self.state / "backups/v1/.transaction.lock").is_dir())

    def test_hardlinked_receipt_fifo_and_empty_extra_directory_are_preserved(self):
        receipt = self.seed()
        link = self.case / "receipt-link"
        os.link(self.receipt, link)
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(2, self.receipt.stat().st_nlink)
        link.unlink()
        fifo = self.home / ".agents/skills/code-review/custom-pipe"
        os.mkfifo(fifo)
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(stat.S_ISFIFO(fifo.lstat().st_mode))
        fifo.unlink()
        extra = fifo.parent / "empty-custom"
        extra.mkdir()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(extra.is_dir())

    @unittest.skipUnless(hasattr(os, "chflags"), "requires file-flag API")
    def test_append_only_receipts_are_not_modified(self):
        self.seed()
        for path in (self.receipt, self.state / "installed.jsonl"):
            with self.subTest(path=path.name):
                before = path.read_bytes()
                os.chflags(path, stat.UF_APPEND)
                try:
                    result = self.run_installer("update", "--all")
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual(before, path.read_bytes())
                finally:
                    os.chflags(path, 0)

    def test_fixed_old_source_is_data_and_partial_clone_is_rejected(self):
        old_program = self.old / "install.sh"
        before = old_program.read_bytes()
        marker = self.case / "old-program-executed"
        old_program.write_text("#!/bin/sh\ntouch " + str(marker) + "\nexit 91\n")
        try:
            result = self.run_installer("install", "shared-review-gates", "--source", self.old)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertFalse(marker.exists())
            self.assert_version("0.33.1")
            subprocess.run(["git", "-C", str(self.old), "config", "remote.origin.promisor", "true"], check=True)
            result = self.run_installer("update", "--all", "--source", self.old)
            self.assertNotEqual(0, result.returncode)
            self.assertIn("partial/promisor", result.stderr)
        finally:
            old_program.write_bytes(before)
            subprocess.run(["git", "-C", str(self.old), "config", "--unset", "remote.origin.promisor"], check=False)

    def test_receipt_staging_identity_failure_keeps_targets_and_receipts(self):
        receipt = self.seed()
        history = (self.state / "installed.jsonl").read_bytes()
        overrides = self.command("python3", '''
if [[ "$2" == identity && "$3" == *.receipt.*/value ]]; then
  echo injected-staging-identity >&2; exit 75
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-staging-identity", result.stderr)
        self.payload_unchanged(receipt)
        self.assertEqual(receipt, json.loads(self.receipt.read_text()))
        self.assertEqual(history, (self.state / "installed.jsonl").read_bytes())

    def test_umask002_fresh_old_install_and_update_keep_restrictive_modes(self):
        for command, source in (("install", self.old), ("update", ROOT)):
            result = subprocess.run(["bash", str(ROOT / "install.sh"), command, "shared-review-gates", "--source", str(source)],
                                    cwd=ROOT, env=self.env, capture_output=True, text=True,
                                    preexec_fn=lambda: os.umask(0o002))
            self.assertEqual(0, result.returncode, result.stderr)
        for root in (self.home / ".agents/skills", self.home / ".codex/templates", self.state):
            for path in [root, *root.rglob("*")]:
                if path.is_dir():
                    self.assertEqual(0o700, stat.S_IMODE(path.stat().st_mode), path)
                else:
                    expected = 0o700 if path.stat().st_mode & 0o111 else 0o600
                    self.assertEqual(expected, stat.S_IMODE(path.stat().st_mode), path)

    def test_late_whole_skill_retirement_failure_restores_previous_install(self):
        receipt = self.seed("0.34.0")
        overrides = self.command("mv", '''
if [[ "$2" == */code-review.bak ]]; then echo injected-skill-retirement >&2; exit 76; fi''')
        result = self.run_installer("uninstall", "--all", "--yes", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-skill-retirement", result.stderr)
        self.payload_unchanged(receipt)
        self.assertEqual(receipt, json.loads(self.receipt.read_text()))

    def test_backup_slot_appearing_after_staging_rolls_back_prior_replacement(self):
        receipt = self.seed()
        overrides = self.command("python3", '''
if [[ "$2" == verify-staged ]]; then
  "$REAL_COMMAND" "$@"
  for tx in "$XDG_STATE_HOME/codex-dev-skills/backups/v1"/transaction.*; do
    for folder in "$tx/originals"/*/skills; do
      printf 'late unknown backup' > "$folder/code-review.bak"
    done
  done
  echo injected-apply-slot >&2; exit 0
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-apply-slot", result.stderr)
        self.assertIn("created after preflight", result.stderr)
        self.payload_unchanged(receipt)
        self.assertEqual(receipt, json.loads(self.receipt.read_text()))
        self.assertTrue(any(p.read_text() == "late unknown backup" for p in (self.state / "backups/v1").rglob("code-review.bak")))

    def test_workspace_rmdir_failure_reports_committed_cleanup_pending(self):
        self.seed()
        overrides = self.command("rmdir", '''
if [[ "$1" == */transaction.* ]]; then : > "$FAULT_MARKER"; exit 75; fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertTrue((self.case / "injected").exists())
        self.assertIn("cleanup data preserved", result.stderr)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual("0.34.0", receipt["source"]["version"])
        self.payload_unchanged(receipt)

    def test_cleanup_unknown_note_only_preserves_note_after_original_cleanup(self):
        self.seed()
        overrides = self.command("mv", '''
if [[ "$1" == *.receipt.*/value && "$2" == */managed-*.json ]]; then
  "$REAL_COMMAND" "$@"
  for tx in "$XDG_STATE_HOME/codex-dev-skills/backups/v1"/transaction.*; do
    printf 'unknown note only' > "$tx/notes.txt"
  done
  echo injected-note-only >&2; exit 0
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("injected-note-only", result.stderr)
        self.assertIn("cleanup data preserved", result.stderr)
        self.assertEqual(["unknown note only"], [p.read_text() for p in (self.state / "backups/v1").rglob("notes.txt")])
        self.assertEqual([], list((self.state / "backups/v1").rglob("*.bak")))
        self.payload_unchanged(json.loads(self.receipt.read_text()))

    def test_signal_after_history_receipt_promotion_keeps_complete_transaction(self):
        receipt = self.seed(groups=["shared-review-gates", "codex-delivery-workflow", "codex-agent-profiles"])
        history = (self.state / "installed.jsonl").read_bytes()
        profile = self.profile_receipt(receipt)
        profile_before = profile.read_bytes()
        overrides = self.command("mv", '''
if [[ "$1" == *.receipt.*/value && "$2" == */installed.jsonl ]]; then
  "$REAL_COMMAND" "$@"; echo injected-forward-receipt-signal >&2
  kill -HUP "$PPID"; exit 0
fi''')
        result = self.run_installer("update", "--all", overrides=overrides)
        self.assertIn("injected-forward-receipt-signal", result.stderr)
        if result.returncode == 0:
            current = json.loads(self.receipt.read_text())
            self.assertEqual("0.34.0", current["source"]["version"])
            self.payload_unchanged(current)
            expected = "".join(item["relative"] + "\t" + item["files"][""]["sha256"] + "\n"
                               for item in current["artifacts"] if item["kind"] == "agent_profiles")
            self.assertEqual(sorted(expected.splitlines()), sorted(profile.read_text().splitlines()))
            self.assertNotEqual(history, (self.state / "installed.jsonl").read_bytes())
        else:
            self.payload_unchanged(receipt)
            self.assertEqual(receipt, json.loads(self.receipt.read_text()))
            self.assertEqual(history, (self.state / "installed.jsonl").read_bytes())
            self.assertEqual(profile_before, profile.read_bytes())
