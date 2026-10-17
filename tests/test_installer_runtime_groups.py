from __future__ import annotations

import ast
import json
import contextlib
import hashlib
import io
import os
import pathlib
import re
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
INSTALLER_VERSION = re.search(
    r'^VERSION="([^"]+)"$', INSTALLER.read_text(encoding="utf-8"), re.MULTILINE
).group(1)
INSTALLER_ENV_OVERRIDES = (
    "CODEX_CLI",
    "CODEX_SKILLS_DIR",
    "CODEX_TEMPLATES_DIR",
    "CODEX_CUSTOM_AGENTS_DIR",
    "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS",
    "CODEX_DEV_SKILLS_TARGET",
)



from tests.test_installer_source_integrity import InstallerFixture


def tree_snapshot(*roots: pathlib.Path) -> tuple[tuple[str, str, int, bytes], ...]:
    entries: list[tuple[str, str, int, bytes]] = []
    for root in roots:
        if not root.exists() and not root.is_symlink():
            continue
        candidates = [root, *sorted(root.rglob("*"))]
        for path in candidates:
            metadata = path.lstat()
            kind = "link" if path.is_symlink() else "dir" if path.is_dir() else "file"
            payload = path.read_bytes() if kind == "file" else b""
            entries.append(
                (str(path), kind, stat.S_IMODE(metadata.st_mode), payload)
            )
    return tuple(entries)


class InstallerBoundaryUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()

    def test_diff_is_readonly_for_existing_partial_missing_and_error_targets(self) -> None:
        for case in ("existing", "partial", "missing", "invalid-group", "invalid-root", "symlink", "profiles"):
            with self.subTest(case=case):
                home, env = self.installer_env(case)
                skills = home / ".agents" / "skills"
                templates = home / ".codex" / "templates"
                if case in ("existing", "partial"):
                    skills.mkdir(parents=True)
                    shutil.copytree(ROOT / "skills" / "code-review", skills / "code-review")
                if case == "existing":
                    templates.mkdir(parents=True)
                if case in ("invalid-root", "symlink"):
                    templates.parent.mkdir()
                    if case == "invalid-root":
                        templates.write_text("not a directory", encoding="utf-8")
                    else:
                        templates.symlink_to(self.root, target_is_directory=True)
                args = ["diff", "not-a-group" if case == "invalid-group" else
                        "codex-agent-profiles" if case == "profiles" else "--all"]
                before = tree_snapshot(home, pathlib.Path(env["XDG_STATE_HOME"]))
                result = subprocess.run(
                    ["bash", "-x", str(INSTALLER), *args], cwd=ROOT, env=env,
                    text=True, capture_output=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before, tree_snapshot(home, pathlib.Path(env["XDG_STATE_HOME"])))
                # Trace also detects transient shell writes removed before the snapshot.
                self.assertNotRegex(result.stderr, r"(?m)^\++ (?:mkdir|mktemp|cp|mv|rm|touch|chmod|chown|tee)(?: |$)")
                if case in ("existing", "partial", "missing", "profiles"):
                    self.assertIn("missing installed", result.stderr)

    def test_diff_reports_matching_different_and_missing_sources_without_writes(self) -> None:
        home, env = self.installer_env("content-diff")
        skills = home / ".agents" / "skills"
        skills.mkdir(parents=True)
        target = skills / "code-review"
        shutil.copytree(ROOT / "skills" / "code-review", target)
        # Exercise the real helper without modifying repository sources.
        source = INSTALLER.read_text(encoding="utf-8").rsplit('main "$@"', 1)[0]
        source = source.replace('ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"', 'ROOT_DIR="$1"')
        source += '\ndiff_skill code-review\n'
        for case in ("matching", "different", "source-missing"):
            with self.subTest(case=case):
                if case == "different":
                    (target / "SKILL.md").write_text("local modification", encoding="utf-8")
                before = tree_snapshot(home)
                result = subprocess.run(
                    ["bash", "-c", source, "installer-test", str(ROOT if case != "source-missing" else self.root / "absent-source")],
                    env=env, text=True, capture_output=True, check=False,
                )
                self.assertEqual(result.returncode == 0, case == "matching", result.stderr)
                self.assertEqual(before, tree_snapshot(home))
                if case == "different":
                    self.assertIn("differ", result.stdout)
                if case == "source-missing":
                    self.assertIn("No such file or directory", result.stderr)

    def test_mutable_chain_uid_mapping_diagnostics_preserve_rejections(self) -> None:
        source = INSTALLER.read_text(encoding="utf-8")
        function = source.split("validate_mutable_directory_chain() {", 1)[1].split("\n}\n", 1)[0]
        program = function.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        cases = (
            ("root", 0, stat.S_IFDIR | 0o755, False),
            ("current", 1000, stat.S_IFDIR | 0o700, False),
            ("foreign", 2000, stat.S_IFDIR | 0o755, True),
            ("overflow", 65534, stat.S_IFDIR | 0o755, True),
            ("writable", 1000, stat.S_IFDIR | 0o777, True),
            ("symlink", 1000, stat.S_IFLNK | 0o777, True),
            ("sticky-root", 0, stat.S_IFDIR | 0o1777, False),
            ("sticky-overflow", 65534, stat.S_IFDIR | 0o1777, True),
        )
        for name, owner, mode, rejected in cases:
            with self.subTest(case=name):
                output = io.StringIO()
                metadata = mock.Mock(st_uid=owner, st_mode=mode)
                def open_proc(path, **kwargs):
                    return io.StringIO("1000 0 1\n" if path.endswith("uid_map") else "65534\n")
                with mock.patch("sys.argv", ["validator", "/home", "audit"]), \
                     mock.patch("sys.platform", "linux"), \
                     mock.patch("os.getuid", return_value=1000), \
                     mock.patch("os.lstat", return_value=metadata), \
                     mock.patch("builtins.open", side_effect=open_proc), \
                     contextlib.redirect_stderr(output):
                    if rejected:
                        with self.assertRaises(SystemExit):
                            exec(program, {})
                    else:
                        exec(program, {})
                if owner not in (0, 1000) and not stat.S_ISLNK(mode):
                    self.assertIn("untrusted owner", output.getvalue())
                    self.assertIn("1000 0 1", output.getvalue())
                    self.assertIn("do not chmod/chown", output.getvalue())
                if owner == 65534:
                    self.assertIn("does not prove the host owner", output.getvalue())

        long_mapping = "".join(f"{i:10d} {i:10d} {1:10d}\n" for i in range(340))
        for case in ("long", "unreadable", "malformed-overflow"):
            with self.subTest(proc_case=case):
                output = io.StringIO()
                def open_proc(path, **kwargs):
                    if case == "unreadable":
                        raise PermissionError("synthetic proc read denied")
                    if path.endswith("uid_map"):
                        return io.StringIO(long_mapping if case == "long" else "1000 0 1\n")
                    return io.StringIO("invalid" if case == "malformed-overflow" else "65534\n")
                with mock.patch("sys.argv", ["validator", "/home", "audit"]), \
                     mock.patch("sys.platform", "linux"), \
                     mock.patch("os.getuid", return_value=1000), \
                     mock.patch("os.lstat", return_value=mock.Mock(st_uid=65534, st_mode=stat.S_IFDIR | 0o755)), \
                     mock.patch("builtins.open", side_effect=open_proc), \
                     contextlib.redirect_stderr(output), self.assertRaises(SystemExit):
                    exec(program, {})
                diagnostic = output.getvalue()
                self.assertIn("untrusted owner", diagnostic)
                if case == "long":
                    self.assertIn("truncated to complete rows", diagnostic)
                    line = next(line for line in diagnostic.splitlines() if "(inside outside length): " in line)
                    shown = ast.literal_eval(line.split("(inside outside length): ", 1)[1])
                    self.assertLessEqual(len(shown), 4096)
                    self.assertGreater(len(shown), 0)
                    expected_rows = [row.split() for row in long_mapping.splitlines()]
                    self.assertTrue(all(row.split() in expected_rows for row in shown.splitlines()))
                elif case == "unreadable":
                    self.assertIn("UID mapping unavailable", diagnostic)
                    self.assertIn("Overflow UID unavailable", diagnostic)
                else:
                    self.assertIn("Overflow UID unavailable", diagnostic)

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
                "CODEX_CLI": str(self.root / "missing-codex"),
            }
        )
        return home, env

    def test_linux_receipt_flag_ioctl_contract_is_abi_sized_and_fail_closed(self) -> None:
        """Linux lacks st_flags, so receipt preflight must not silently degrade."""
        source = INSTALLER.read_text(encoding="utf-8")
        for long_size, expected in ((4, 0x80046601), (8, 0x80086601)):
            request = (2 << 30) | (ord("f") << 8) | 1 | (long_size << 16)
            self.assertEqual(expected, request)
        self.assertIn('if sys.platform.startswith("linux"):', source)
        self.assertIn("long_size = ctypes.sizeof(ctypes.c_long)", source)
        self.assertIn('(2 << 30) | (ord("f") << 8) | 1 | (long_size << 16)', source)
        self.assertIn("fs_immutable_fl = 0x00000010", source)
        self.assertIn("fs_append_fl = 0x00000020", source)
        self.assertIn("fcntl.ioctl(fd, getflags_request, raw_flags, True)", source)
        self.assertIn("file flags cannot be inspected", source)
        self.assertIn("raise SystemExit(1)", source[source.index("file flags cannot be inspected"):])

    def test_linux_ioctl_payload_decodes_native_first_uint_for_all_abi_layouts(self) -> None:
        import struct

        for byteorder in ("little", "big"):
            for long_size in (4, 8):
                for flag in (0x10, 0x20):
                    payload = flag.to_bytes(4, byteorder) + bytes(long_size - 4)
                    decoded = struct.unpack("<I" if byteorder == "little" else ">I", payload[:4])[0]
                    self.assertEqual(flag, decoded)
        source = INSTALLER.read_text(encoding="utf-8")
        self.assertIn('struct.unpack_from("=I", raw_flags)[0]', source)

class RuntimeGroupInstallerTests(InstallerFixture):
    def test_fresh_cli_group_installs_common_delivery_and_cli_only(self):
        result = self.run_installer("install", "codex-cli-session-handoff")
        self.assertEqual(0, result.returncode, result.stderr)
        skills = self.home / ".agents/skills"
        self.assertTrue((skills / "cli-session-handoff/SKILL.md").is_file())
        self.assertTrue((skills / "planning/SKILL.md").is_file())
        self.assertFalse((skills / "desktop-project-delivery").exists())
        self.assertFalse((self.home / ".codex/agents").exists())

    def test_desktop_group_and_cli_uninstall_preserve_common_dependencies(self):
        self.seed("0.34.0")
        result = self.run_installer("uninstall", "codex-cli-session-handoff", "--yes")
        self.assertEqual(0, result.returncode, result.stderr)
        skills = self.home / ".agents/skills"
        self.assertFalse((skills / "cli-session-handoff").exists())
        self.assertTrue((skills / "desktop-project-delivery/SKILL.md").is_file())
        self.assertTrue((skills / "planning/SKILL.md").is_file())

    def test_dependency_and_wrong_root_uninstall_refuse_without_mutation(self):
        self.seed("0.34.0")
        before = self.snapshot()
        for overrides in ({}, {"CODEX_DEV_SKILLS_TARGET": "legacy"}):
            result = self.run_installer("uninstall", "shared-review-gates", "--yes", overrides=overrides)
            self.assertNotEqual(0, result.returncode)
            self.assertEqual(before, self.snapshot())

    def test_alternate_root_collision_refuses_new_install(self):
        target = self.home / ".codex/skills/code-review"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("imported")
        before = self.snapshot()
        result = self.run_installer("install", "codex-review-workflow")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("duplicate skill discovery", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_same_bytes_without_receipt_are_not_adopted(self):
        self.seed("0.34.0")
        self.receipt.unlink()
        before = self.snapshot()
        result = self.run_installer("install", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_unsafe_state_chain_fails_before_payload_mutation(self):
        self.seed()
        self.state.chmod(0o777)
        before = self.snapshot()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())

    def test_raw_state_symlink_and_repository_overlap_are_refused(self):
        self.state.mkdir(parents=True, mode=0o700)
        alias = self.case / "state-alias"
        alias.symlink_to(self.state.parent, target_is_directory=True)
        before = self.snapshot()
        for state in (alias, ROOT):
            result = self.run_installer("install", "shared-review-gates", overrides={"XDG_STATE_HOME": str(state)})
            self.assertNotEqual(0, result.returncode)
            self.assertIn("symlink" if state == alias else "overlaps", result.stderr.lower())
            self.assertEqual(before, self.snapshot())

    def test_readonly_history_and_inventory_receipts_fail_before_apply(self):
        self.seed()
        for path in (self.state / "installed.jsonl", self.receipt):
            with self.subTest(path=path.name):
                path.chmod(0o400)
                before = self.snapshot()
                result = self.run_installer("update", "--all")
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(before, self.snapshot())
                path.chmod(0o600)

    @unittest.skipUnless(hasattr(os, "chflags"), "requires file-flag API")
    def test_immutable_receipt_is_not_repaired_or_replaced(self):
        self.seed()
        path = self.state / "installed.jsonl"
        os.chflags(path, stat.UF_IMMUTABLE)
        self.addCleanup(os.chflags, path, 0)
        before = self.snapshot()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())
        self.assertTrue(path.stat().st_flags & stat.UF_IMMUTABLE)

    def test_hardlink_and_nested_symlink_are_preserved(self):
        self.seed()
        path = self.home / ".agents/skills/code-review/SKILL.md"
        duplicate = self.case / "hardlink"
        os.link(path, duplicate)
        before = self.snapshot()
        result = self.run_installer("update", "--all", "--force")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, self.snapshot())
        duplicate.unlink()
        nested = path.parent / "extra"
        nested.symlink_to(self.case, target_is_directory=True)
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(nested.is_symlink())

    def test_history_backups_are_not_reused_or_cleaned(self):
        self.seed()
        backup = self.state / "backups/v1/historical/skills/code-review.bak"
        backup.mkdir(parents=True, mode=0o700)
        marker = backup / "custom.txt"
        marker.write_text("historical recovery data")
        result = self.run_installer("update", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("historical recovery data", marker.read_text())
        self.assert_version("0.34.0")

    def test_lock_collision_preserves_every_target_and_receipt(self):
        self.seed()
        lock = self.state / "backups/v1/.transaction.lock"
        lock.mkdir(parents=True, mode=0o700)
        (lock / "owner").write_text("fixture lock")
        before = self.snapshot()
        result = self.run_installer("update", "--all")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("lock already exists", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_legacy_target_has_a_distinct_bound_inventory(self):
        self.roots["skills"] = str(self.home / ".codex/skills")
        self.env["CODEX_DEV_SKILLS_TARGET"] = "legacy"
        self.seed()
        result = self.run_installer("update", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assert_version("0.34.0")
        self.assertFalse((self.home / ".agents/skills").exists())
        self.assertEqual(self.roots, json.loads(self.receipt.read_text())["roots"])

    def test_plugin_collision_uses_only_fixture_cli_including_symlink(self):
        cli = self.case / "fake-cli"
        cli.write_text('#!/bin/sh\n[ "$*" = "plugin list --json" ] || exit 91\nprintf \'%s\\n\' \'{"installed":[{"name":"codex-dev-skills"}]}\'\n')
        cli.chmod(0o700)
        alias = self.case / "cli-alias"
        alias.symlink_to(cli)
        before = self.snapshot()
        result = self.run_installer("install", "shared-review-gates", overrides={"CODEX_CLI": str(alias)})
        self.assertNotEqual(0, result.returncode)
        self.assertIn("plugin is installed", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_unknown_plugin_list_warns_without_executing_a_real_client(self):
        cli = self.case / "fake-cli"
        cli.write_text("#!/bin/sh\nprintf '%s\\n' '{}'\n")
        cli.chmod(0o700)
        result = self.run_installer("install", "shared-review-gates", overrides={"CODEX_CLI": str(cli)})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("unsupported JSON", result.stderr)
