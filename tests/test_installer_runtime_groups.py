from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.sh"
INSTALLER_ENV_OVERRIDES = (
    "CODEX_CLI",
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


def remove_group_world_write(paths: list[pathlib.Path]) -> None:
    for path in paths:
        metadata = path.lstat()
        if metadata.st_uid != os.getuid() or path.is_symlink():
            raise AssertionError(f"refusing test remediation for unsafe path: {path}")
        path.chmod(stat.S_IMODE(metadata.st_mode) & ~0o022)


class RuntimeGroupInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve()

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
            }
        )
        return home, env

    def run_installer(
        self,
        *arguments: str,
        home_name: str,
        env_overrides: dict[str, str] | None = None,
    ) -> tuple[pathlib.Path, subprocess.CompletedProcess[str]]:
        home, env = self.installer_env(home_name)
        if env_overrides:
            env.update(env_overrides)
        result = subprocess.run(
            [str(INSTALLER), *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        return home, result

    def install(self, group: str, home_name: str) -> pathlib.Path:
        home, result = self.run_installer(
            "install", group, home_name=home_name
        )
        self.assertEqual(0, result.returncode, result.stderr)
        return home / ".agents" / "skills"

    def fake_mv_overrides(self, name: str, mode: str) -> dict[str, str]:
        fake_bin = self.root / f"{name}-bin"
        fake_bin.mkdir()
        real_mv = shutil.which("mv")
        self.assertIsNotNone(real_mv)
        fake_mv = fake_bin / "mv"
        fake_mv.write_text(
            "#!/bin/sh\n"
            "case \"${FAKE_MV_MODE:-}\" in\n"
            "  fail-backup)\n"
            "    case \"$2\" in *.bak) echo 'injected backup rename failure' >&2; exit 71 ;; esac\n"
            "    ;;\n"
            "  fail-replace-and-restore)\n"
            "    case \"$1\" in\n"
            "      *.tmp.*/value) echo 'injected replacement failure' >&2; exit 72 ;;\n"
            "      *.bak) echo 'injected restore failure' >&2; exit 73 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  fail-second-replace)\n"
            "    case \"$1\" in\n"
            "      *.task-continuation.tmp.*/value) echo 'injected later replacement failure' >&2; exit 74 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  fail-receipt-replace)\n"
            "    case \"$1:$2\" in\n"
            "      *.receipt.*/value:*/installed.jsonl) echo 'injected receipt replacement failure' >&2; exit 75 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  fail-profile-receipt-replace)\n"
            "    case \"$1:$2\" in\n"
            "      *.receipt.*/value:*/agent-profile-*.tsv) echo 'injected profile receipt replacement failure' >&2; exit 76 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  fail-backup-exdev)\n"
            "    case \"$2\" in\n"
            "      *.bak) echo 'injected EXDEV backup rename failure' >&2; exit 18 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  fail-artifact-apply)\n"
            "    case \"$1\" in\n"
            "      *.tmp.*/value)\n"
            "        : > \"$FAKE_MV_ARTIFACT_MARKER\"\n"
            "        echo 'injected artifact apply seam reached' >&2\n"
            "        exit 80\n"
            "        ;;\n"
            "    esac\n"
            "    ;;\n"
            "  hold-after-lock)\n"
            "    case \"$2\" in\n"
            "      *.bak) sleep 2 ;;\n"
            "    esac\n"
            "    ;;\n"
            "  drift-first-replacement-then-fail-second)\n"
            "    case \"$1:$2\" in\n"
            "      *.closure-triage.tmp.*/value:*/closure-triage)\n"
            f'        "{real_mv}" "$@" || exit $?\n'
            "        printf 'identity drift after replacement\\n' > \"$2/SKILL.md\"\n"
            "        exit 0\n"
            "        ;;\n"
            "      *.task-continuation.tmp.*/value:*/task-continuation)\n"
            "        echo 'injected later replacement failure' >&2\n"
            "        exit 77\n"
            "        ;;\n"
            "    esac\n"
            "    ;;\n"
            "  signal-after-rename)\n"
            "    signal_match=0\n"
            "    case \"${FAKE_MV_SIGNAL_TARGET:-}:$1:$2\" in\n"
            "      artifact-backup:*/closure-triage:*.bak) signal_match=1 ;;\n"
            "      artifact-replace:*.closure-triage.tmp.*/value:*/closure-triage) signal_match=1 ;;\n"
            "      installed-receipt-backup:*/installed.jsonl:*.receipt.*/original) signal_match=1 ;;\n"
            "      installed-receipt-replace:*.receipt.*/value:*/installed.jsonl) signal_match=1 ;;\n"
            "      profile-receipt-backup:*/agent-profile-*.tsv:*.receipt.*/original) signal_match=1 ;;\n"
            "      profile-receipt-replace:*.receipt.*/value:*/agent-profile-*.tsv) signal_match=1 ;;\n"
            "    esac\n"
            "    if [ \"$signal_match\" -eq 1 ] && [ ! -e \"${FAKE_MV_SIGNAL_MARKER:-}\" ]; then\n"
            f'      "{real_mv}" "$@" || exit $?\n'
            "      : > \"$FAKE_MV_SIGNAL_MARKER\"\n"
            "      kill -s \"$FAKE_MV_SIGNAL\" \"$PPID\"\n"
            "      exit 0\n"
            "    fi\n"
            "    ;;\n"
            "  signal-artifact-restore)\n"
            "    case \"$1:$2\" in\n"
            "      *.task-continuation.tmp.*/value:*/task-continuation)\n"
            "        echo 'injected later replacement failure' >&2\n"
            "        exit 78\n"
            "        ;;\n"
            "      *.bak:*/closure-triage)\n"
            f'        "{real_mv}" "$@" || exit $?\n'
            "        : > \"$FAKE_MV_SIGNAL_MARKER\"\n"
            "        kill -s \"$FAKE_MV_SIGNAL\" \"$PPID\"\n"
            "        exit 0\n"
            "        ;;\n"
            "    esac\n"
            "    ;;\n"
            "  signal-receipt-restore)\n"
            "    case \"$1:$2\" in\n"
            "      *.receipt.*/value:*/agent-profile-*.tsv)\n"
            "        echo 'injected profile receipt replacement failure' >&2\n"
            "        exit 79\n"
            "        ;;\n"
            "      *.receipt.*/original:*/installed.jsonl)\n"
            f'        "{real_mv}" "$@" || exit $?\n'
            "        : > \"$FAKE_MV_SIGNAL_MARKER\"\n"
            "        kill -s \"$FAKE_MV_SIGNAL\" \"$PPID\"\n"
            "        exit 0\n"
            "        ;;\n"
            "    esac\n"
            "    ;;\n"
            "esac\n"
            f'exec "{real_mv}" "$@"\n',
            encoding="utf-8",
        )
        fake_mv.chmod(0o755)
        return {
            "FAKE_MV_MODE": mode,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        }

    def artifact_apply_seam_overrides(
        self, name: str
    ) -> tuple[dict[str, str], pathlib.Path]:
        marker = self.root / f"{name}-artifact-apply-fired"
        overrides = self.fake_mv_overrides(name, "fail-artifact-apply")
        overrides["FAKE_MV_ARTIFACT_MARKER"] = str(marker)
        return overrides, marker

    def signal_mv_overrides(
        self, name: str, signal: str, target: str
    ) -> tuple[dict[str, str], pathlib.Path]:
        marker = self.root / f"{name}-{signal}-{target}.signal-fired"
        overrides = self.fake_mv_overrides(name, "signal-after-rename")
        overrides.update(
            {
                "FAKE_MV_SIGNAL": signal,
                "FAKE_MV_SIGNAL_TARGET": target,
                "FAKE_MV_SIGNAL_MARKER": str(marker),
            }
        )
        return overrides, marker

    def failing_receipt_identity_overrides(self, name: str) -> dict[str, str]:
        fake_bin = self.root / f"{name}-python-bin"
        fake_bin.mkdir()
        real_python = shutil.which("python3")
        self.assertIsNotNone(real_python)
        fake_python = fake_bin / "python3"
        fake_python.write_text(
            "#!/bin/sh\n"
            "case \"${FAIL_RECEIPT_IDENTITY:-}:$1:$2\" in\n"
            "  1:-:*/installed.jsonl) echo 'injected receipt identity failure' >&2; exit 91 ;;\n"
            "esac\n"
            f'exec "{real_python}" "$@"\n',
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        return {
            "FAIL_RECEIPT_IDENTITY": "1",
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        }

    def make_legacy_layout_permissive(
        self, *roots: pathlib.Path
    ) -> list[pathlib.Path]:
        selected: list[pathlib.Path] = []
        for root in roots:
            for path in [root, *sorted(root.rglob("*"))]:
                if path.is_symlink():
                    raise AssertionError(f"unexpected symlink in trusted legacy fixture: {path}")
                if path.is_dir():
                    path.chmod(0o775)
                elif path.is_file():
                    executable = bool(path.stat().st_mode & 0o111)
                    path.chmod(0o775 if executable else 0o664)
                else:
                    raise AssertionError(f"unexpected special file in trusted legacy fixture: {path}")
                selected.append(path)
        return selected

    def concurrent_identity_barrier_overrides(
        self,
        name: str,
        role: str,
        target: pathlib.Path,
        barrier: pathlib.Path,
    ) -> dict[str, str]:
        fake_bin = self.root / f"{name}-barrier-bin"
        fake_bin.mkdir(exist_ok=True)
        barrier.mkdir(exist_ok=True)
        real_python = shutil.which("python3")
        real_mv = shutil.which("mv")
        self.assertIsNotNone(real_python)
        self.assertIsNotNone(real_mv)
        fake_python = fake_bin / "python3"
        fake_python.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = - ] && [ \"$2\" = \"$BARRIER_TARGET\" ] && [ \"$3\" = directory ]; then\n"
            "  count_file=\"$BARRIER_DIR/$BARRIER_ROLE.identity-count\"\n"
            "  count=0\n"
            "  [ ! -f \"$count_file\" ] || count=$(sed -n '1p' \"$count_file\")\n"
            "  count=$((count + 1))\n"
            "  printf '%s\\n' \"$count\" > \"$count_file\"\n"
            "  if [ \"$BARRIER_ROLE\" = B ] && [ \"$count\" -eq 2 ]; then\n"
            "    : > \"$BARRIER_DIR/B-apply-ready\"\n"
            "    while [ ! -f \"$BARRIER_DIR/A-replaced\" ]; do sleep 0.01; done\n"
            "  fi\n"
            "fi\n"
            f'exec "{real_python}" "$@"\n',
            encoding="utf-8",
        )
        fake_python.chmod(0o755)
        fake_mv = fake_bin / "mv"
        fake_mv.write_text(
            "#!/bin/sh\n"
            "case \"$BARRIER_ROLE:$1:$2\" in\n"
            "  A:*.closure-triage.tmp.*/value:\"$BARRIER_TARGET\")\n"
            "    while [ ! -f \"$BARRIER_DIR/B-apply-ready\" ]; do sleep 0.01; done\n"
            f'    "{real_mv}" "$@" || exit $?\n'
            "    : > \"$BARRIER_DIR/A-replaced\"\n"
            "    exit 0\n"
            "    ;;\n"
            "esac\n"
            f'exec "{real_mv}" "$@"\n',
            encoding="utf-8",
        )
        fake_mv.chmod(0o755)
        return {
            "BARRIER_DIR": str(barrier),
            "BARRIER_ROLE": role,
            "BARRIER_TARGET": str(target),
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        }

    def test_cli_group_installs_adapter_over_delivery_layer(self) -> None:
        skills = self.install("codex-cli-session-handoff", "cli-home")

        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "code-review-gate" / "SKILL.md").is_file())
        self.assertFalse((skills / "desktop-project-delivery").exists())

    def test_desktop_group_does_not_install_cli_adapter(self) -> None:
        skills = self.install("desktop-delivery-workflow", "desktop-home")

        self.assertTrue((skills / "desktop-project-delivery" / "SKILL.md").is_file())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertFalse((skills / "cli-session-handoff").exists())

    def test_cli_uninstall_preserves_dependencies_and_desktop_groups(
        self,
    ) -> None:
        skills = self.install("desktop-delivery-workflow", "shared-home")
        self.install("codex-review-workflow", "shared-home")
        self.install("codex-cli-session-handoff", "shared-home")

        _, result = self.run_installer(
            "uninstall",
            "codex-cli-session-handoff",
            "--yes",
            home_name="shared-home",
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((skills / "cli-session-handoff").exists())
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "code-review-gate" / "SKILL.md").is_file())
        self.assertTrue(
            (skills / "desktop-project-delivery" / "SKILL.md").is_file()
        )

    def test_dependency_uninstall_refuses_installed_dependents(self) -> None:
        skills = self.install("codex-cli-session-handoff", "protected-home")

        _, result = self.run_installer(
            "uninstall",
            "codex-delivery-workflow",
            "--yes",
            home_name="protected-home",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("still depend on", result.stderr)
        self.assertTrue((skills / "loop-engineering" / "SKILL.md").is_file())
        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())

    def test_installer_environment_does_not_escape_fixture(self) -> None:
        external_skills = self.root / "external" / "skills"
        external_templates = self.root / "external" / "templates"
        external_skills.mkdir(parents=True)
        external_templates.mkdir(parents=True)
        sentinel = external_skills / "sentinel.txt"
        sentinel.write_text("unchanged\n", encoding="utf-8")
        inherited = {
            "CODEX_SKILLS_DIR": str(external_skills),
            "CODEX_TEMPLATES_DIR": str(external_templates),
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
            "CODEX_DEV_SKILLS_TARGET": "agents",
        }

        with mock.patch.dict(os.environ, inherited):
            skills = self.install("codex-cli-session-handoff", "isolated-home")

        self.assertEqual("unchanged\n", sentinel.read_text(encoding="utf-8"))
        self.assertEqual([], list(external_templates.iterdir()))
        self.assertTrue((skills / "cli-session-handoff" / "SKILL.md").is_file())

    def test_umask_002_keeps_state_chain_and_receipts_restrictive_through_force_update(self) -> None:
        home, env = self.installer_env("umask-home")
        command_prefix = ["bash", "-c", 'umask 002; exec "$@"', "installer-umask"]

        def assert_exact_permissions() -> None:
            target_roots = (
                home / ".agents" / "skills",
                home / ".codex" / "templates",
                home / ".codex" / "agents",
            )
            for target_root in target_roots:
                for directory in [target_root, *target_root.rglob("*")]:
                    if directory.is_dir():
                        self.assertEqual(0o700, stat.S_IMODE(directory.stat().st_mode), directory)

            skills_root = home / ".agents" / "skills"
            for installed_file in skills_root.rglob("*"):
                if not installed_file.is_file():
                    continue
                relative = installed_file.relative_to(skills_root)
                source_file = ROOT / "skills" / relative
                expected = 0o700 if source_file.stat().st_mode & 0o111 else 0o600
                self.assertEqual(expected, stat.S_IMODE(installed_file.stat().st_mode), installed_file)

            for installed_file in (home / ".codex" / "templates").rglob("*"):
                if installed_file.is_file():
                    self.assertEqual(0o600, stat.S_IMODE(installed_file.stat().st_mode), installed_file)
            for installed_file in (home / ".codex" / "agents").rglob("*.toml"):
                self.assertEqual(0o600, stat.S_IMODE(installed_file.stat().st_mode), installed_file)

            state_dir = self.root / "umask-home-state" / "codex-dev-skills"
            for directory in [
                self.root / "umask-home-state",
                state_dir,
                state_dir / "backups",
                state_dir / "backups" / "v1",
            ]:
                if directory.exists():
                    self.assertEqual(0o700, stat.S_IMODE(directory.stat().st_mode), directory)
            receipts = [state_dir / "installed.jsonl", *state_dir.glob("agent-profile-*.tsv")]
            self.assertEqual(2, len(receipts))
            for receipt in receipts:
                self.assertEqual(0o600, stat.S_IMODE(receipt.stat().st_mode), receipt)

        installed = subprocess.run(
            [*command_prefix, str(INSTALLER), "install", "codex-agent-profiles"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        assert_exact_permissions()
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        template = home / ".codex" / "templates" / "orchestration" / "policies" / "agent-delegation-policy.md"
        template.write_text("local template edit\n", encoding="utf-8")
        profile = home / ".codex" / "agents" / "loop_v2a_fast_explorer.toml"
        profile.write_text("local profile edit\n", encoding="utf-8")
        updated = subprocess.run(
            [*command_prefix, str(INSTALLER), "update", "codex-agent-profiles", "--force"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, updated.returncode, updated.stderr)
        assert_exact_permissions()

    def test_fresh_install_refuses_unsafe_state_before_any_target_mutation(self) -> None:
        """State ownership is a precondition, not a post-install write check."""
        cases = ("directory-mode", "directory-symlink", "receipt-mode", "receipt-symlink", "receipt-readonly", "receipt-fifo")
        for kind in cases:
            with self.subTest(kind=kind):
                home_name = f"fresh-unsafe-state-{kind}"
                state_base = self.root / f"{home_name}-state"
                state_dir = state_base / "codex-dev-skills"
                state_base.mkdir(mode=0o700)
                external = self.root / f"{home_name}-external-state"
                receipt = state_dir / "installed.jsonl"
                unknown = b"unknown pre-existing state\n"

                if kind == "directory-mode":
                    state_dir.mkdir()
                    state_dir.chmod(0o777)
                    receipt.write_bytes(unknown)
                elif kind == "directory-symlink":
                    external.mkdir()
                    external.joinpath("installed.jsonl").write_bytes(unknown)
                    state_dir.symlink_to(external, target_is_directory=True)
                else:
                    state_dir.mkdir()
                    if kind == "receipt-symlink":
                        external.write_bytes(unknown)
                        receipt.symlink_to(external)
                    elif kind == "receipt-fifo":
                        if not hasattr(os, "mkfifo"):
                            self.skipTest("mkfifo is unavailable")
                        os.mkfifo(receipt)
                    else:
                        receipt.write_bytes(unknown)
                        receipt.chmod(0o666 if kind == "receipt-mode" else 0o400)

                home, refused = self.run_installer(
                    "install",
                    "codex-agent-profiles",
                    home_name=home_name,
                    # Avoid an external `codex plugin list` implementation
                    # creating its own config directory under this fixture HOME.
                    env_overrides={"CODEX_CLI": str(self.root / "missing-codex")},
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertFalse((home / ".agents").exists())
                self.assertFalse((home / ".codex").exists())
                if kind == "directory-symlink":
                    self.assertTrue(state_dir.is_symlink())
                    self.assertEqual(unknown, external.joinpath("installed.jsonl").read_bytes())
                elif kind == "receipt-symlink":
                    self.assertTrue(receipt.is_symlink())
                    self.assertEqual(unknown, external.read_bytes())
                elif kind == "receipt-fifo":
                    self.assertTrue(stat.S_ISFIFO(receipt.lstat().st_mode))
                else:
                    self.assertEqual(unknown, receipt.read_bytes())
                    expected_mode = 0o777 if kind == "directory-mode" else (0o666 if kind == "receipt-mode" else 0o400)
                    inspected = state_dir if kind == "directory-mode" else receipt
                    self.assertEqual(expected_mode, stat.S_IMODE(inspected.stat().st_mode))

    def test_nonforce_update_missing_artifacts_refuses_unsafe_receipts_without_mutation(self) -> None:
        """A missing artifact must not be restored before receipt state is trustworthy."""
        for artifact in ("skill", "template", "profile"):
            with self.subTest(artifact=artifact):
                home_name = f"nonforce-unsafe-{artifact}"
                overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
                home, installed = self.run_installer(
                    "install", "codex-agent-profiles", home_name=home_name,
                    env_overrides=overrides,
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                state_file = state_dir / "installed.jsonl"
                if artifact == "skill":
                    missing = home / ".agents" / "skills" / "closure-triage"
                    shutil.rmtree(missing)
                    unsafe_receipt = state_file
                elif artifact == "template":
                    missing = home / ".codex" / "templates" / "orchestration" / "policies" / "agent-delegation-policy.md"
                    missing.unlink()
                    unsafe_receipt = state_file
                else:
                    missing = home / ".codex" / "agents" / "loop_v2a_fast_explorer.toml"
                    missing.unlink()
                    unsafe_receipt = next(state_dir.glob("agent-profile-*.tsv"))
                unsafe_receipt.chmod(0o400)
                targets_before = tree_snapshot(
                    home / ".agents", home / ".codex"
                )
                receipts_before = {
                    path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                    for path in [state_file, *state_dir.glob("agent-profile-*.tsv")]
                }

                _, refused = self.run_installer(
                    "update", "codex-agent-profiles", home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
                self.assertFalse(missing.exists())
                self.assertEqual(
                    receipts_before,
                    {
                        path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                        for path in receipts_before
                    },
                )

    def test_nonforce_safe_state_supports_default_and_custom_updates_with_restrictive_receipts(self) -> None:
        for mode in ("default", "custom"):
            with self.subTest(mode=mode):
                home_name = f"nonforce-safe-{mode}"
                overrides: dict[str, str] = {
                    "CODEX_CLI": str(self.root / "missing-codex"),
                }
                if mode == "custom":
                    custom_agents = self.root / f"{home_name}-project" / ".codex" / "agents"
                    overrides = {
                        "CODEX_CUSTOM_AGENTS_DIR": str(custom_agents),
                        "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
                    }
                home, installed = self.run_installer(
                    "install", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                profiles = (
                    pathlib.Path(overrides["CODEX_CUSTOM_AGENTS_DIR"])
                    if mode == "custom"
                    else home / ".codex" / "agents"
                )
                missing = profiles / "loop_v2a_fast_explorer.toml"
                missing.unlink()

                _, updated = self.run_installer(
                    "update", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
                )

                self.assertEqual(0, updated.returncode, updated.stderr)
                self.assertTrue(missing.is_file())
                state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                for receipt in [state_dir / "installed.jsonl", *state_dir.glob("agent-profile-*.tsv")]:
                    self.assertEqual(0o600, stat.S_IMODE(receipt.stat().st_mode), receipt)

    def test_hardlinked_installed_receipt_refuses_nonforce_install_and_update_before_targets(self) -> None:
        """Receipts must not alias bytes outside the managed state boundary."""
        for action in ("install", "update"):
            with self.subTest(action=action):
                home_name = f"hardlinked-receipt-{action}"
                overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
                if action == "update":
                    home, installed = self.run_installer(
                        "install", "shared-review-gates", home_name=home_name,
                        env_overrides=overrides,
                    )
                    self.assertEqual(0, installed.returncode, installed.stderr)
                    shutil.rmtree(home / ".agents" / "skills" / "closure-triage")
                else:
                    home, _ = self.installer_env(home_name)
                state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                state_dir.mkdir(parents=True, exist_ok=True)
                receipt = state_dir / "installed.jsonl"
                receipt.unlink(missing_ok=True)
                external = self.root / f"{home_name}-outside-receipt"
                external.write_bytes(b"outside receipt sentinel\n")
                os.link(external, receipt)
                targets_before = tree_snapshot(home / ".agents", home / ".codex")

                _, refused = self.run_installer(
                    action, "shared-review-gates", home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
                self.assertEqual(b"outside receipt sentinel\n", external.read_bytes())
                self.assertEqual(2, receipt.stat().st_nlink)

    def test_force_update_refuses_hardlinked_file_artifacts_without_backup_or_state_mutation(self) -> None:
        cases = ("template", "profile", "skill-child")
        for kind in cases:
            with self.subTest(kind=kind):
                home_name = f"hardlinked-{kind}"
                overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
                group = "codex-agent-profiles" if kind in ("template", "profile") else "shared-review-gates"
                home, installed = self.run_installer(
                    "install", group, home_name=home_name, env_overrides=overrides
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                skills_root = home / ".agents" / "skills"
                templates_root = home / ".codex" / "templates"
                profiles_root = home / ".codex" / "agents"
                if kind == "template":
                    target = templates_root / "orchestration" / "policies" / "agent-delegation-policy.md"
                    backup = managed_backup_path(
                        self.root / f"{home_name}-state", templates_root, "templates",
                        "orchestration/policies/agent-delegation-policy.md",
                    )
                elif kind == "profile":
                    target = profiles_root / "loop_v2a_fast_explorer.toml"
                    backup = managed_backup_path(
                        self.root / f"{home_name}-state", profiles_root, "agent-profiles", target.name
                    )
                else:
                    target = skills_root / "closure-triage" / "SKILL.md"
                    backup = managed_backup_path(
                        self.root / f"{home_name}-state", skills_root, "skills", "closure-triage"
                    )
                external = self.root / f"{home_name}-outside-artifact"
                external.write_bytes(f"outside {kind} sentinel\n".encode())
                target.unlink()
                os.link(external, target)
                snapshot_before = tree_snapshot(home / ".agents", home / ".codex", self.root / f"{home_name}-state")

                _, refused = self.run_installer(
                    "update", group, "--force", home_name=home_name, env_overrides=overrides
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertEqual(snapshot_before, tree_snapshot(home / ".agents", home / ".codex", self.root / f"{home_name}-state"))
                self.assertEqual(f"outside {kind} sentinel\n".encode(), external.read_bytes())
                self.assertEqual(2, target.stat().st_nlink)
                self.assertFalse(backup.exists())

    def set_macos_file_flag_for_test(self, path: pathlib.Path, flag: str) -> None:
        if os.uname().sysname != "Darwin":
            self.skipTest("macOS chflags regression is Darwin-only")
        chflags = shutil.which("chflags")
        if chflags is None:
            self.skipTest("chflags is unavailable")
        enabled = subprocess.run([chflags, flag, str(path)], text=True, capture_output=True, check=False)
        self.assertEqual(0, enabled.returncode, enabled.stderr)
        self.addCleanup(subprocess.run, [chflags, f"no{flag}", str(path)], text=True, capture_output=True, check=False)

    def assert_force_receipt_boundary_refusal_before_artifact_apply(
        self, *, receipt_kind: str, protection: str
    ) -> None:
        """A known-unreplaceable receipt must stop force update before apply."""
        home_name = f"force-receipt-{receipt_kind}-{protection}"
        overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name=home_name,
            env_overrides=overrides,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        skills_root = home / ".agents" / "skills"
        templates_root = home / ".codex" / "templates"
        profiles_root = home / ".codex" / "agents"
        skill = skills_root / "closure-triage" / "SKILL.md"
        template = templates_root / "orchestration" / "policies" / "agent-delegation-policy.md"
        profile = profiles_root / "loop_v2a_fast_explorer.toml"
        skill.write_text("force receipt local skill\n", encoding="utf-8")
        template.write_text("force receipt local template\n", encoding="utf-8")
        profile.write_text("force receipt local profile\n", encoding="utf-8")
        state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
        installed_receipt = state_dir / "installed.jsonl"
        profile_receipt = next(state_dir.glob("agent-profile-*.tsv"))
        receipt = installed_receipt if receipt_kind == "installed" else profile_receipt
        if protection == "readonly":
            receipt.chmod(0o400)
        else:
            self.set_macos_file_flag_for_test(receipt, protection)

        targets_before = tree_snapshot(home / ".agents", home / ".codex")
        receipts_before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            for path in (installed_receipt, profile_receipt)
        }
        backups = (
            managed_backup_path(
                self.root / f"{home_name}-state", skills_root, "skills", "closure-triage"
            ),
            managed_backup_path(
                self.root / f"{home_name}-state", templates_root, "templates",
                "orchestration/policies/agent-delegation-policy.md",
            ),
            managed_backup_path(
                self.root / f"{home_name}-state", profiles_root, "agent-profiles",
                "loop_v2a_fast_explorer.toml",
            ),
        )
        self.assertTrue(all(not backup.exists() for backup in backups))
        seam_overrides, artifact_apply_marker = self.artifact_apply_seam_overrides(home_name)
        overrides.update(seam_overrides)

        _, refused = self.run_installer(
            "update", "codex-agent-profiles", "--force", home_name=home_name,
            env_overrides=overrides,
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn(str(receipt), refused.stderr)
        self.assertNotIn("injected artifact apply seam reached", refused.stderr)
        self.assertFalse(artifact_apply_marker.exists())
        self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
        self.assertEqual(
            receipts_before,
            {
                path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                for path in receipts_before
            },
        )
        self.assertTrue(all(not backup.exists() for backup in backups))
        lock = state_dir / "backups" / "v1" / ".transaction.lock"
        self.assertFalse(lock.exists(), lock)
        self.assertEqual([], list(state_dir.glob(".codex-dev-skills.*.receipt.*")))
        for root in (skills_root, templates_root, profiles_root):
            self.assertEqual([], list(root.rglob(".codex-dev-skills.*.tmp.*")))

    def test_force_update_refuses_readonly_installed_and_profile_receipts_before_artifact_apply(self) -> None:
        for receipt_kind in ("installed", "profile"):
            with self.subTest(receipt_kind=receipt_kind):
                self.assert_force_receipt_boundary_refusal_before_artifact_apply(
                    receipt_kind=receipt_kind, protection="readonly"
                )

    def test_macos_force_update_refuses_protected_receipts_before_artifact_apply(self) -> None:
        for receipt_kind in ("installed", "profile"):
            for protection in ("uchg", "uappnd"):
                with self.subTest(receipt_kind=receipt_kind, protection=protection):
                    self.assert_force_receipt_boundary_refusal_before_artifact_apply(
                        receipt_kind=receipt_kind, protection=protection
                    )

    def test_force_update_with_safe_receipts_still_updates_artifacts_and_receipts(self) -> None:
        home_name = "force-receipt-safe-control"
        overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name=home_name,
            env_overrides=overrides,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        skills_root = home / ".agents" / "skills"
        templates_root = home / ".codex" / "templates"
        profiles_root = home / ".codex" / "agents"
        skill = skills_root / "closure-triage" / "SKILL.md"
        template = templates_root / "orchestration" / "policies" / "agent-delegation-policy.md"
        profile = profiles_root / "loop_v2a_fast_explorer.toml"
        skill.write_text("safe force local skill\n", encoding="utf-8")
        template.write_text("safe force local template\n", encoding="utf-8")
        profile.write_text("safe force local profile\n", encoding="utf-8")
        state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
        receipts_before = {
            path: path.read_bytes()
            for path in [state_dir / "installed.jsonl", *state_dir.glob("agent-profile-*.tsv")]
        }

        _, updated = self.run_installer(
            "update", "codex-agent-profiles", "--force", home_name=home_name,
            env_overrides=overrides,
        )

        self.assertEqual(0, updated.returncode, updated.stderr)
        self.assertNotEqual("safe force local skill\n", skill.read_text(encoding="utf-8"))
        self.assertNotEqual("safe force local template\n", template.read_text(encoding="utf-8"))
        self.assertNotEqual("safe force local profile\n", profile.read_text(encoding="utf-8"))
        for path, before in receipts_before.items():
            if path.name == "installed.jsonl":
                self.assertNotEqual(before, path.read_bytes())
            else:
                self.assertEqual(before, path.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
        self.assertFalse((state_dir / "backups" / "v1" / ".transaction.lock").exists())

    def test_macos_immutable_installed_receipt_refuses_nonforce_install_and_update_before_targets(self) -> None:
        for action in ("install", "update"):
            with self.subTest(action=action):
                home_name = f"immutable-installed-{action}"
                overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
                if action == "update":
                    home, installed = self.run_installer(
                        "install", "shared-review-gates", home_name=home_name,
                        env_overrides=overrides,
                    )
                    self.assertEqual(0, installed.returncode, installed.stderr)
                    shutil.rmtree(home / ".agents" / "skills" / "closure-triage")
                else:
                    home, _ = self.installer_env(home_name)
                    state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                    state_dir.mkdir(parents=True)
                    receipt = state_dir / "installed.jsonl"
                    receipt.write_bytes(b"immutable state receipt\n")
                    receipt.chmod(0o600)
                receipt = self.root / f"{home_name}-state" / "codex-dev-skills" / "installed.jsonl"
                receipt_before = receipt.read_bytes()
                targets_before = tree_snapshot(home / ".agents", home / ".codex")
                self.set_macos_file_flag_for_test(receipt, "uchg")

                _, refused = self.run_installer(
                    action, "shared-review-gates", home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
                self.assertEqual(receipt_before, receipt.read_bytes())

    def test_macos_immutable_profile_receipt_refuses_nonforce_update_before_profile_mutation(self) -> None:
        home_name = "immutable-profile-update"
        overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        missing = home / ".codex" / "agents" / "loop_v2a_fast_explorer.toml"
        missing.unlink()
        state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
        receipt = next(state_dir.glob("agent-profile-*.tsv"))
        receipt_before = receipt.read_bytes()
        targets_before = tree_snapshot(home / ".agents", home / ".codex")
        self.set_macos_file_flag_for_test(receipt, "uchg")

        _, refused = self.run_installer(
            "update", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
        self.assertEqual(receipt_before, receipt.read_bytes())

    def test_macos_append_only_installed_receipt_refuses_nonforce_update_before_targets(self) -> None:
        home_name = "append-only-installed-update"
        overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name=home_name, env_overrides=overrides
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        shutil.rmtree(home / ".agents" / "skills" / "closure-triage")
        receipt = self.root / f"{home_name}-state" / "codex-dev-skills" / "installed.jsonl"
        receipt_before = receipt.read_bytes()
        targets_before = tree_snapshot(home / ".agents", home / ".codex")
        self.set_macos_file_flag_for_test(receipt, "uappnd")

        _, refused = self.run_installer(
            "update", "shared-review-gates", home_name=home_name, env_overrides=overrides
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
        self.assertEqual(receipt_before, receipt.read_bytes())

    def test_macos_append_only_profile_receipt_refuses_nonforce_update_before_profile_mutation(self) -> None:
        home_name = "append-only-profile-update"
        overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        missing = home / ".codex" / "agents" / "loop_v2a_fast_explorer.toml"
        missing.unlink()
        state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
        receipt = next(state_dir.glob("agent-profile-*.tsv"))
        receipt_before = receipt.read_bytes()
        targets_before = tree_snapshot(home / ".agents", home / ".codex")
        self.set_macos_file_flag_for_test(receipt, "uappnd")

        _, refused = self.run_installer(
            "update", "codex-agent-profiles", home_name=home_name, env_overrides=overrides
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertEqual(targets_before, tree_snapshot(home / ".agents", home / ".codex"))
        self.assertEqual(receipt_before, receipt.read_bytes())

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

    def test_raw_managed_backup_intermediate_symlinks_refuse_all_force_paths_without_mutation(self) -> None:
        for intermediate in ("backups", "backups/v1"):
            for mode in ("noop", "missing", "differing"):
                with self.subTest(intermediate=intermediate, mode=mode):
                    home_name = f"managed-link-{intermediate.replace('/', '-')}-{mode}"
                    overrides = {"CODEX_CLI": str(self.root / "missing-codex")}
                    home, installed = self.run_installer("install", "shared-review-gates", home_name=home_name, env_overrides=overrides)
                    self.assertEqual(0, installed.returncode, installed.stderr)
                    skill = home / ".agents" / "skills" / "closure-triage"
                    if mode == "missing":
                        shutil.rmtree(skill)
                    elif mode == "differing":
                        skill.joinpath("SKILL.md").write_text("local edit\n", encoding="utf-8")
                    state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                    external = self.root / f"{home_name}-external"
                    external.mkdir()
                    linked = state_dir / intermediate
                    linked.parent.mkdir(parents=True, exist_ok=True)
                    if linked.exists():
                        shutil.rmtree(linked)
                    linked.symlink_to(external, target_is_directory=True)
                    before = tree_snapshot(home / ".agents", home / ".codex", state_dir)
                    external_before = tree_snapshot(external)
                    _, refused = self.run_installer("update", "shared-review-gates", "--force", home_name=home_name, env_overrides=overrides)
                    self.assertNotEqual(0, refused.returncode)
                    self.assertEqual(before, tree_snapshot(home / ".agents", home / ".codex", state_dir))
                    self.assertEqual(external_before, tree_snapshot(external))
                    self.assertFalse((external / ".transaction.lock").exists())

    def test_differing_existing_skill_fails_before_expanded_group_mutation(self) -> None:
        home, env = self.installer_env("collision-home")
        conflicting = home / ".agents" / "skills" / "loop-engineering"
        conflicting.mkdir(parents=True)
        sentinel = conflicting / "SKILL.md"
        sentinel.write_text("imported local workflow\n", encoding="utf-8")

        result = subprocess.run(
            [str(INSTALLER), "install", "codex-cli-session-handoff"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing to overwrite differing installed or imported artifacts", result.stderr)
        self.assertEqual("imported local workflow\n", sentinel.read_text(encoding="utf-8"))
        self.assertFalse((home / ".agents" / "skills" / "cli-session-handoff").exists())
        self.assertFalse((home / ".codex" / "templates" / "orchestration").exists())
        # A preflight failure must not leave an empty final receipt or probe state.
        self.assertFalse((self.root / "collision-home-state").exists())

    def test_template_collision_fails_before_other_target_roots_are_created(self) -> None:
        home, env = self.installer_env("template-collision-home")
        conflicting = (
            home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "agent-delegation-policy.md"
        )
        conflicting.parent.mkdir(parents=True)
        conflicting.write_text("imported template\n", encoding="utf-8")

        result = subprocess.run(
            [str(INSTALLER), "install", "shared-review-gates"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing to overwrite differing installed or imported artifacts", result.stderr)
        self.assertEqual("imported template\n", conflicting.read_text(encoding="utf-8"))
        self.assertFalse((home / ".agents").exists())
        self.assertFalse((self.root / "template-collision-home-state").exists())

    def test_installed_plugin_refuses_filesystem_install_before_mutation(self) -> None:
        fake_cli = self.root / "fake-codex"
        fake_cli.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '{\"installed\":[{\"name\":\"codex-dev-skills\",\"installed\":true}]}'\n",
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="plugin-collision-home",
            env_overrides={"CODEX_CLI": str(fake_cli)},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("codex-dev-skills plugin is installed", result.stderr)
        self.assertFalse((home / ".agents").exists())
        self.assertFalse((home / ".codex").exists())

    def test_symlinked_cli_is_resolved_for_plugin_collision_check(self) -> None:
        real_cli = self.root / "real-codex"
        real_cli.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '{\"installed\":[{\"name\":\"codex-dev-skills\",\"installed\":true}]}'\n",
            encoding="utf-8",
        )
        real_cli.chmod(0o755)
        linked_cli = self.root / "codex"
        linked_cli.symlink_to(real_cli)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="symlinked-cli-home",
            env_overrides={"CODEX_CLI": str(linked_cli)},
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("codex-dev-skills plugin is installed", result.stderr)
        self.assertNotIn("Ignoring unsafe or unavailable", result.stderr)
        self.assertFalse((home / ".agents").exists())

    def test_update_conflicts_are_preflighted_before_expanded_group_mutation(self) -> None:
        home, installed = self.run_installer(
            "install", "codex-cli-session-handoff", home_name="update-preflight-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        missing_skill = home / ".agents" / "skills" / "closure-triage"
        shutil.rmtree(missing_skill)
        modified_template = (
            home
            / ".codex"
            / "templates"
            / "workflows"
            / "loop-engineering-workflow.md"
        )
        modified_template.write_text("local imported workflow\n", encoding="utf-8")

        _, result = self.run_installer(
            "update", "codex-cli-session-handoff", home_name="update-preflight-home"
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Refusing a partial update", result.stderr)
        self.assertFalse(missing_skill.exists())
        self.assertEqual(
            "local imported workflow\n",
            modified_template.read_text(encoding="utf-8"),
        )

    def test_force_update_backup_collisions_are_preflighted_for_all_artifacts(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="force-preflight-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        first = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        second = home / ".agents" / "skills" / "task-continuation" / "SKILL.md"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        state_root = self.root / "force-preflight-home-state"
        backup = managed_backup_path(
            state_root,
            home / ".agents" / "skills",
            "skills",
            "task-continuation",
        )
        backup.parent.mkdir(parents=True)
        backup.mkdir()

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="force-preflight-home",
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("existing managed backup path", result.stderr)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertFalse(
            managed_backup_path(
                state_root,
                home / ".agents" / "skills",
                "skills",
                "closure-triage",
            ).exists()
        )
        self.assertFalse(first.parent.with_name("closure-triage.bak").exists())

    def test_file_backup_rename_failure_preserves_target_and_cleans_staging(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="file-rename-failure-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        target = (
            home
            / ".codex"
            / "templates"
            / "orchestration"
            / "policies"
            / "agent-delegation-policy.md"
        )
        target.write_text("local template edit\n", encoding="utf-8")

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="file-rename-failure-home",
            env_overrides=self.fake_mv_overrides("file-rename-failure", "fail-backup"),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("failed to create backup for template", result.stderr)
        self.assertEqual("local template edit\n", target.read_text(encoding="utf-8"))
        backup = managed_backup_path(
            self.root / "file-rename-failure-home-state",
            home / ".codex" / "templates",
            "templates",
            "orchestration/policies/agent-delegation-policy.md",
        )
        self.assertFalse(backup.exists())
        self.assertFalse(target.with_suffix(".md.bak").exists())
        self.assertEqual([], list(target.parent.glob(".codex-dev-skills.*.tmp.*")))

    def test_directory_restore_failure_reports_backup_and_cleans_staging(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="dir-restore-failure-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        target = home / ".agents" / "skills" / "closure-triage"
        marker = target / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        backup = managed_backup_path(
            self.root / "dir-restore-failure-home-state",
            home / ".agents" / "skills",
            "skills",
            "closure-triage",
        )

        _, result = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="dir-restore-failure-home",
            env_overrides=self.fake_mv_overrides(
                "dir-restore-failure", "fail-replace-and-restore"
            ),
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("failed to replace skill closure-triage", result.stderr)
        self.assertIn("CRITICAL: failed to restore skill closure-triage", result.stderr)
        self.assertFalse(target.exists())
        self.assertEqual("local skill edit\n", (backup / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual([], list(backup.parent.glob(".codex-dev-skills.*.tmp.*")))

    def test_later_replacement_failure_rolls_back_earlier_artifacts_and_state(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="later-rollback-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        skills_root = home / ".agents" / "skills"
        first = skills_root / "closure-triage" / "SKILL.md"
        second = skills_root / "task-continuation" / "SKILL.md"
        first.write_text("first local edit\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        state_file = self.root / "later-rollback-home-state" / "codex-dev-skills" / "installed.jsonl"
        state_before = state_file.read_bytes()

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="later-rollback-home",
            env_overrides=self.fake_mv_overrides("later-rollback", "fail-second-replace"),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("failed to replace skill task-continuation", refused.stderr)
        self.assertEqual("first local edit\n", first.read_text(encoding="utf-8"))
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))
        self.assertEqual(state_before, state_file.read_bytes())
        self.assertFalse(
            managed_backup_path(
                self.root / "later-rollback-home-state", skills_root, "skills", "closure-triage"
            ).exists()
        )
        self.assertEqual([], list(skills_root.glob(".codex-dev-skills.*.tmp.*")))

    def test_receipt_replace_failure_rolls_back_artifacts_without_success_state(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="receipt-rollback-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        state_file = self.root / "receipt-rollback-home-state" / "codex-dev-skills" / "installed.jsonl"
        state_before = state_file.read_bytes()

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="receipt-rollback-home",
            env_overrides=self.fake_mv_overrides("receipt-rollback", "fail-receipt-replace"),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("failed to replace installer state receipt", refused.stderr)
        self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))
        self.assertEqual(state_before, state_file.read_bytes())

    def test_second_profile_receipt_failure_restores_first_receipt_and_artifact(self) -> None:
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name="profile-receipt-rollback-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        profile = home / ".codex" / "agents" / "loop_v2a_fast_explorer.toml"
        profile.write_text("local profile edit\n", encoding="utf-8")
        state_dir = self.root / "profile-receipt-rollback-home-state" / "codex-dev-skills"
        state_file = state_dir / "installed.jsonl"
        receipt = next(state_dir.glob("agent-profile-*.tsv"))
        state_before = state_file.read_bytes()
        receipt_before = receipt.read_bytes()

        _, refused = self.run_installer(
            "update",
            "codex-agent-profiles",
            "--force",
            home_name="profile-receipt-rollback-home",
            env_overrides=self.fake_mv_overrides(
                "profile-receipt-rollback", "fail-profile-receipt-replace"
            ),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("failed to replace agent profile state receipt", refused.stderr)
        self.assertEqual("local profile edit\n", profile.read_text(encoding="utf-8"))
        self.assertEqual(state_before, state_file.read_bytes())
        self.assertEqual(receipt_before, receipt.read_bytes())

    def test_signal_during_forward_rename_keeps_artifacts_and_receipts_consistent(self) -> None:
        cases = (
            ("INT", "artifact-backup", "shared-review-gates"),
            ("HUP", "artifact-replace", "shared-review-gates"),
            ("TERM", "artifact-replace", "shared-review-gates"),
            ("TERM", "installed-receipt-backup", "shared-review-gates"),
            ("INT", "installed-receipt-replace", "shared-review-gates"),
            ("HUP", "installed-receipt-replace", "shared-review-gates"),
            ("HUP", "profile-receipt-backup", "codex-agent-profiles"),
            ("TERM", "profile-receipt-replace", "codex-agent-profiles"),
            ("INT", "profile-receipt-replace", "codex-agent-profiles"),
        )
        for signal, target_kind, group in cases:
            with self.subTest(signal=signal, target_kind=target_kind):
                home_name = f"signal-{signal.lower()}-{target_kind}-home"
                home, installed = self.run_installer(
                    "install", group, home_name=home_name
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                if target_kind.startswith("profile-receipt"):
                    target_root = home / ".codex" / "agents"
                    relative_target = "loop_v2a_fast_explorer.toml"
                    artifact_kind = "agent-profiles"
                    marker_path = target_root / relative_target
                    source_path = ROOT / "agent-profiles" / relative_target
                    local_edit = "local profile edit\n"
                else:
                    target_root = home / ".agents" / "skills"
                    relative_target = "closure-triage"
                    artifact_kind = "skills"
                    marker_path = target_root / relative_target / "SKILL.md"
                    source_path = ROOT / "skills" / relative_target / "SKILL.md"
                    local_edit = "local skill edit\n"
                marker_path.write_text(local_edit, encoding="utf-8")
                overrides, signal_marker = self.signal_mv_overrides(
                    f"signal-{signal.lower()}-{target_kind}", signal, target_kind
                )

                _, updated = self.run_installer(
                    "update",
                    group,
                    "--force",
                    home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertEqual(0, updated.returncode, updated.stderr)
                self.assertTrue(signal_marker.is_file(), "signal injection did not run")
                self.assertEqual(source_path.read_bytes(), marker_path.read_bytes())
                backup = managed_backup_path(
                    self.root / f"{home_name}-state",
                    target_root,
                    artifact_kind,
                    relative_target,
                )
                backup_marker = backup if backup.is_file() else backup / "SKILL.md"
                self.assertEqual(local_edit, backup_marker.read_text(encoding="utf-8"))
                state_dir = self.root / f"{home_name}-state" / "codex-dev-skills"
                self.assertIn(
                    '"version":"0.15.1","action":"update"',
                    (state_dir / "installed.jsonl").read_text(encoding="utf-8"),
                )
                if target_kind.startswith("profile-receipt"):
                    profile_receipt = next(state_dir.glob("agent-profile-*.tsv"))
                    digest = hashlib.sha256(marker_path.read_bytes()).hexdigest()
                    self.assertIn(f"{relative_target}\t{digest}\n", profile_receipt.read_text(encoding="utf-8"))

    def test_signal_during_artifact_restore_does_not_reenter_recovery(self) -> None:
        for signal in ("INT", "HUP", "TERM"):
            with self.subTest(signal=signal):
                home_name = f"signal-{signal.lower()}-artifact-restore-home"
                home, installed = self.run_installer(
                    "install", "shared-review-gates", home_name=home_name
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                skills_root = home / ".agents" / "skills"
                first = skills_root / "closure-triage" / "SKILL.md"
                second = skills_root / "task-continuation" / "SKILL.md"
                first.write_text("first restore original\n", encoding="utf-8")
                second.write_text("second restore original\n", encoding="utf-8")
                state_root = self.root / f"{home_name}-state"
                state_dir = state_root / "codex-dev-skills"
                state_before = (state_dir / "installed.jsonl").read_bytes()
                signal_marker = self.root / f"{home_name}.signal-fired"
                overrides = self.fake_mv_overrides(
                    f"signal-{signal.lower()}-artifact-restore",
                    "signal-artifact-restore",
                )
                overrides.update(
                    {
                        "FAKE_MV_SIGNAL": signal,
                        "FAKE_MV_SIGNAL_MARKER": str(signal_marker),
                    }
                )

                _, refused = self.run_installer(
                    "update",
                    "shared-review-gates",
                    "--force",
                    home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertTrue(signal_marker.is_file(), "restore signal was not injected")
                self.assertNotIn("CRITICAL:", refused.stderr)
                self.assertEqual("first restore original\n", first.read_text(encoding="utf-8"))
                self.assertEqual("second restore original\n", second.read_text(encoding="utf-8"))
                self.assertEqual(state_before, (state_dir / "installed.jsonl").read_bytes())
                self.assertFalse(
                    managed_backup_path(
                        state_root, skills_root, "skills", "closure-triage"
                    ).exists()
                )
                self.assertEqual([], list(skills_root.glob(".codex-dev-skills.*.tmp.*")))
                self.assertFalse((state_dir / "backups" / "v1" / ".transaction.lock").exists())

    def test_signal_during_receipt_restore_does_not_reenter_recovery(self) -> None:
        for signal in ("INT", "HUP", "TERM"):
            with self.subTest(signal=signal):
                home_name = f"signal-{signal.lower()}-receipt-restore-home"
                home, installed = self.run_installer(
                    "install", "codex-agent-profiles", home_name=home_name
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                profiles_root = home / ".codex" / "agents"
                profile = profiles_root / "loop_v2a_fast_explorer.toml"
                profile.write_text("receipt rollback profile original\n", encoding="utf-8")
                state_root = self.root / f"{home_name}-state"
                state_dir = state_root / "codex-dev-skills"
                state_file = state_dir / "installed.jsonl"
                profile_receipt = next(state_dir.glob("agent-profile-*.tsv"))
                state_before = state_file.read_bytes()
                profile_receipt_before = profile_receipt.read_bytes()
                signal_marker = self.root / f"{home_name}.signal-fired"
                overrides = self.fake_mv_overrides(
                    f"signal-{signal.lower()}-receipt-restore",
                    "signal-receipt-restore",
                )
                overrides.update(
                    {
                        "FAKE_MV_SIGNAL": signal,
                        "FAKE_MV_SIGNAL_MARKER": str(signal_marker),
                    }
                )

                _, refused = self.run_installer(
                    "update",
                    "codex-agent-profiles",
                    "--force",
                    home_name=home_name,
                    env_overrides=overrides,
                )

                self.assertNotEqual(0, refused.returncode)
                self.assertTrue(signal_marker.is_file(), "receipt restore signal was not injected")
                self.assertNotIn("CRITICAL:", refused.stderr)
                self.assertEqual(
                    "receipt rollback profile original\n",
                    profile.read_text(encoding="utf-8"),
                )
                self.assertEqual(state_before, state_file.read_bytes())
                self.assertEqual(profile_receipt_before, profile_receipt.read_bytes())
                self.assertFalse(
                    managed_backup_path(
                        state_root,
                        profiles_root,
                        "agent-profiles",
                        profile.name,
                    ).exists()
                )
                self.assertEqual([], list(state_dir.glob(".codex-dev-skills.*.receipt.*")))
                self.assertFalse((state_dir / "backups" / "v1" / ".transaction.lock").exists())

    def test_receipt_staging_identity_failure_cleans_registered_staging(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="receipt-identity-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        state_dir = self.root / "receipt-identity-home-state" / "codex-dev-skills"
        state_before = (state_dir / "installed.jsonl").read_bytes()

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="receipt-identity-home",
            env_overrides=self.failing_receipt_identity_overrides("receipt-identity"),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("injected receipt identity failure", refused.stderr)
        self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))
        self.assertEqual(state_before, (state_dir / "installed.jsonl").read_bytes())
        self.assertEqual([], list(state_dir.glob(".codex-dev-skills.*.receipt.*")))

    def test_identity_drift_during_rollback_preserves_recoverable_original(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="rollback-identity-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        skills_root = home / ".agents" / "skills"
        first = skills_root / "closure-triage" / "SKILL.md"
        second = skills_root / "task-continuation" / "SKILL.md"
        first.write_text("first recoverable original\n", encoding="utf-8")
        second.write_text("second local edit\n", encoding="utf-8")
        backup = managed_backup_path(
            self.root / "rollback-identity-home-state",
            skills_root,
            "skills",
            "closure-triage",
        )

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="rollback-identity-home",
            env_overrides=self.fake_mv_overrides(
                "rollback-identity", "drift-first-replacement-then-fail-second"
            ),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("refusing to move identity-drifted skill closure-triage", refused.stderr)
        self.assertEqual("identity drift after replacement\n", first.read_text(encoding="utf-8"))
        self.assertEqual(
            "first recoverable original\n",
            (backup / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual("second local edit\n", second.read_text(encoding="utf-8"))

    def test_lock_collision_refuses_force_update_without_touching_targets(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="lock-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        lock = self.root / "lock-home-state" / "codex-dev-skills" / "backups" / "v1" / ".transaction.lock"
        lock.mkdir(parents=True)
        (lock / "owner").write_text("pid=stale\n", encoding="utf-8")

        _, refused = self.run_installer(
            "update", "shared-review-gates", "--force", home_name="lock-home"
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("transaction lock already exists", refused.stderr)
        self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))

    def test_concurrent_force_update_refuses_while_transaction_lock_is_held(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="concurrent-lock-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        _, env = self.installer_env("concurrent-lock-home")
        env.update(self.fake_mv_overrides("concurrent-lock", "hold-after-lock"))
        first = subprocess.Popen(
            [str(INSTALLER), "update", "shared-review-gates", "--force"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        lock = self.root / "concurrent-lock-home-state" / "codex-dev-skills" / "backups" / "v1" / ".transaction.lock"
        try:
            deadline = time.monotonic() + 5
            while not lock.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(lock.is_dir(), "first installer did not acquire its transaction lock")
            _, second = self.run_installer(
                "update", "shared-review-gates", "--force", home_name="concurrent-lock-home"
            )
            self.assertNotEqual(0, second.returncode)
            self.assertIn("transaction lock already exists", second.stderr)
        finally:
            first_stdout, first_stderr = first.communicate(timeout=10)
        self.assertEqual(0, first.returncode, first_stdout + first_stderr)

    def test_concurrent_custom_target_updates_with_distinct_state_roots_fail_closed(self) -> None:
        home, base_env = self.installer_env("cross-state-concurrent-home")
        custom_root = self.root / "cross-state-custom-target"
        skills_root = custom_root / "skills"
        target = skills_root / "closure-triage"
        target_marker = target / "SKILL.md"
        common = {
            **base_env,
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
            "CODEX_SKILLS_DIR": str(skills_root),
            "CODEX_TEMPLATES_DIR": str(custom_root / "templates"),
        }
        installed = subprocess.run(
            [str(INSTALLER), "install", "shared-review-gates"],
            cwd=ROOT,
            env={**common, "XDG_STATE_HOME": str(self.root / "cross-state-A")},
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        target_marker.write_text("shared local edit\n", encoding="utf-8")
        barrier = self.root / "cross-state-barrier"
        processes: dict[str, subprocess.Popen[str]] = {}
        for role in ("A", "B"):
            env = {
                **common,
                "XDG_STATE_HOME": str(self.root / f"cross-state-{role}"),
                **self.concurrent_identity_barrier_overrides(
                    "cross-state", role, target, barrier
                ),
            }
            processes[role] = subprocess.Popen(
                [str(INSTALLER), "update", "shared-review-gates", "--force"],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        outputs: dict[str, tuple[str, str]] = {}
        for role, process in processes.items():
            outputs[role] = process.communicate(timeout=30)

        self.assertEqual(0, processes["A"].returncode, "".join(outputs["A"]))
        self.assertNotEqual(0, processes["B"].returncode)
        self.assertIn("Destination identity changed before applying skill closure-triage", outputs["B"][1])
        self.assertEqual(
            (ROOT / "skills" / "closure-triage" / "SKILL.md").read_bytes(),
            target_marker.read_bytes(),
        )
        backup_a = managed_backup_path(
            self.root / "cross-state-A", skills_root, "skills", "closure-triage"
        )
        backup_b = managed_backup_path(
            self.root / "cross-state-B", skills_root, "skills", "closure-triage"
        )
        self.assertEqual(
            "shared local edit\n",
            (backup_a / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertFalse(backup_b.exists())
        self.assertIn(
            '"version":"0.15.1","action":"update"',
            (self.root / "cross-state-A" / "codex-dev-skills" / "installed.jsonl").read_text(encoding="utf-8"),
        )
        self.assertFalse(
            (self.root / "cross-state-B" / "codex-dev-skills" / "installed.jsonl").exists()
        )
        for role in ("A", "B"):
            lock = (
                self.root
                / f"cross-state-{role}"
                / "codex-dev-skills"
                / "backups"
                / "v1"
                / ".transaction.lock"
            )
            self.assertFalse(lock.exists(), lock)

    def test_injected_exdev_backup_rename_preserves_target_and_state(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="exdev-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")
        state_file = self.root / "exdev-home-state" / "codex-dev-skills" / "installed.jsonl"
        state_before = state_file.read_bytes()

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="exdev-home",
            env_overrides=self.fake_mv_overrides("exdev", "fail-backup-exdev"),
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("failed to create backup for skill closure-triage", refused.stderr)
        self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))
        self.assertEqual(state_before, state_file.read_bytes())

    def test_unsafe_state_root_mode_or_symlink_fails_closed_before_force_update(self) -> None:
        for kind in ("mode", "symlink"):
            with self.subTest(kind=kind):
                home_name = f"unsafe-state-{kind}-home"
                home, installed = self.run_installer(
                    "install", "shared-review-gates", home_name=home_name
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
                marker.write_text("local skill edit\n", encoding="utf-8")
                state_base = self.root / f"{home_name}-state"
                if kind == "mode":
                    state_base.chmod(0o777)
                else:
                    displaced = self.root / f"{home_name}-state-displaced"
                    state_base.rename(displaced)
                    state_base.symlink_to(displaced, target_is_directory=True)

                try:
                    _, refused = self.run_installer(
                        "update", "shared-review-gates", "--force", home_name=home_name
                    )
                finally:
                    if kind == "mode":
                        state_base.chmod(0o700)

                self.assertNotEqual(0, refused.returncode)
                self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))

    def test_v0141_permissive_default_layout_requires_bounded_remediation(self) -> None:
        home_name = "legacy-permissions-home"
        home, installed = self.run_installer(
            "install", "codex-agent-profiles", home_name=home_name
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        state_root = self.root / f"{home_name}-state"
        state_dir = state_root / "codex-dev-skills"
        skills_root = home / ".agents" / "skills"
        templates_root = home / ".codex" / "templates"
        profiles_root = home / ".codex" / "agents"
        skill = skills_root / "closure-triage"
        skill_marker = skill / "SKILL.md"
        template = templates_root / "orchestration" / "policies" / "agent-delegation-policy.md"
        profile = profiles_root / "loop_v2a_fast_explorer.toml"
        original_bytes = {
            "skill": b"v0.14.1 local skill bytes\n",
            "template": b"v0.14.1 local template bytes\n",
            "profile": b"v0.14.1 local profile bytes\n",
        }
        skill_marker.write_bytes(original_bytes["skill"])
        template.write_bytes(original_bytes["template"])
        profile.write_bytes(original_bytes["profile"])
        (state_dir / "installed.jsonl").write_text(
            '{"repo":"codex-dev-skills","version":"0.14.1","action":"install","group":"codex-agent-profiles","target_mode":"agents","installed_at":"fixture"}\n',
            encoding="utf-8",
        )
        parents = [home / ".agents", home / ".codex"]
        for parent in parents:
            parent.chmod(0o775)
        selected = [
            *parents,
            *self.make_legacy_layout_permissive(
                skills_root, templates_root, profiles_root, state_root
            ),
        ]
        before = tree_snapshot(skills_root, templates_root, profiles_root, state_root)
        parent_modes = tuple(
            stat.S_IMODE(path.stat().st_mode)
            for path in (home / ".agents", home / ".codex")
        )

        _, refused = self.run_installer(
            "update", "codex-agent-profiles", "--force", home_name=home_name
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("group/world writ", refused.stderr)
        self.assertEqual(
            before,
            tree_snapshot(skills_root, templates_root, profiles_root, state_root),
        )
        self.assertEqual(
            parent_modes,
            tuple(
                stat.S_IMODE(path.stat().st_mode)
                for path in (home / ".agents", home / ".codex")
            ),
        )

        remove_group_world_write(selected)
        _, updated = self.run_installer(
            "update", "codex-agent-profiles", "--force", home_name=home_name
        )
        self.assertEqual(0, updated.returncode, updated.stderr)

        backups = {
            "skill": managed_backup_path(
                state_root, skills_root, "skills", "closure-triage"
            )
            / "SKILL.md",
            "template": managed_backup_path(
                state_root,
                templates_root,
                "templates",
                "orchestration/policies/agent-delegation-policy.md",
            ),
            "profile": managed_backup_path(
                state_root,
                profiles_root,
                "agent-profiles",
                profile.name,
            ),
        }
        for kind, backup in backups.items():
            self.assertEqual(original_bytes[kind], backup.read_bytes())
        self.assertEqual([], list(skills_root.glob("*.bak")))
        self.assertEqual([], list(templates_root.rglob("*.bak")))
        self.assertEqual([], list(profiles_root.glob("*.bak")))

    def test_permissive_custom_target_fails_before_bounded_remediation(self) -> None:
        home_name = "legacy-custom-permissions-home"
        custom_root = self.root / "legacy-custom-target"
        overrides = {
            "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
            "CODEX_SKILLS_DIR": str(custom_root / "skills"),
            "CODEX_TEMPLATES_DIR": str(custom_root / "templates"),
        }
        _, installed = self.run_installer(
            "install",
            "shared-review-gates",
            home_name=home_name,
            env_overrides=overrides,
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = custom_root / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("custom legacy bytes\n", encoding="utf-8")
        selected = self.make_legacy_layout_permissive(custom_root)
        before = tree_snapshot(custom_root)

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name=home_name,
            env_overrides=overrides,
        )
        self.assertNotEqual(0, refused.returncode)
        self.assertIn("group/world writable", refused.stderr)
        self.assertEqual(before, tree_snapshot(custom_root))

        remove_group_world_write(selected)
        _, updated = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name=home_name,
            env_overrides=overrides,
        )
        self.assertEqual(0, updated.returncode, updated.stderr)
        backup = managed_backup_path(
            self.root / f"{home_name}-state",
            custom_root / "skills",
            "skills",
            "closure-triage",
        )
        self.assertEqual(
            "custom legacy bytes\n",
            (backup / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((custom_root / "skills" / "closure-triage.bak").exists())

    def test_managed_state_root_overlapping_repository_fails_closed(self) -> None:
        home, installed = self.run_installer(
            "install", "shared-review-gates", home_name="overlap-home"
        )
        self.assertEqual(0, installed.returncode, installed.stderr)
        marker = home / ".agents" / "skills" / "closure-triage" / "SKILL.md"
        marker.write_text("local skill edit\n", encoding="utf-8")

        _, refused = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="overlap-home",
            env_overrides={"XDG_STATE_HOME": str(ROOT)},
        )

        self.assertNotEqual(0, refused.returncode)
        self.assertIn("overlaps a protected repository", refused.stderr)
        self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))

    def test_default_and_legacy_skill_roots_have_distinct_managed_backup_slots(self) -> None:
        default_home, default_install = self.run_installer(
            "install", "shared-review-gates", home_name="default-backup-home"
        )
        self.assertEqual(0, default_install.returncode, default_install.stderr)
        default_skill_root = default_home / ".agents" / "skills"
        default_marker = default_skill_root / "closure-triage" / "SKILL.md"
        default_marker.write_text("default skill edit\n", encoding="utf-8")
        _, default_update = self.run_installer(
            "update", "shared-review-gates", "--force", home_name="default-backup-home"
        )
        self.assertEqual(0, default_update.returncode, default_update.stderr)

        legacy_home, legacy_install = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="legacy-backup-home",
            env_overrides={"CODEX_DEV_SKILLS_TARGET": "legacy"},
        )
        self.assertEqual(0, legacy_install.returncode, legacy_install.stderr)
        legacy_skill_root = legacy_home / ".codex" / "skills"
        legacy_marker = legacy_skill_root / "closure-triage" / "SKILL.md"
        legacy_marker.write_text("legacy skill edit\n", encoding="utf-8")
        _, legacy_update = self.run_installer(
            "update",
            "shared-review-gates",
            "--force",
            home_name="legacy-backup-home",
            env_overrides={"CODEX_DEV_SKILLS_TARGET": "legacy"},
        )
        self.assertEqual(0, legacy_update.returncode, legacy_update.stderr)

        default_backup = managed_backup_path(
            self.root / "default-backup-home-state",
            default_skill_root,
            "skills",
            "closure-triage",
        )
        legacy_backup = managed_backup_path(
            self.root / "legacy-backup-home-state",
            legacy_skill_root,
            "skills",
            "closure-triage",
        )
        self.assertNotEqual(default_backup, legacy_backup)
        self.assertEqual("default skill edit\n", (default_backup / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual("legacy skill edit\n", (legacy_backup / "SKILL.md").read_text(encoding="utf-8"))

    def test_common_state_root_keeps_default_legacy_and_custom_backup_slots_distinct(
        self,
    ) -> None:
        common_state = self.root / "common-state"
        roots: list[tuple[pathlib.Path, pathlib.Path, dict[str, str]]] = []
        for mode in ("agents", "legacy", "custom"):
            home_name = f"common-state-{mode}-home"
            overrides = {"XDG_STATE_HOME": str(common_state)}
            if mode == "legacy":
                overrides["CODEX_DEV_SKILLS_TARGET"] = "legacy"
            if mode == "custom":
                custom_base = self.root / "custom-target"
                overrides.update(
                    {
                        "CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS": "YES",
                        "CODEX_SKILLS_DIR": str(custom_base / "skills"),
                        "CODEX_TEMPLATES_DIR": str(custom_base / "templates"),
                    }
                )
            home, installed = self.run_installer(
                "install", "shared-review-gates", home_name=home_name, env_overrides=overrides
            )
            self.assertEqual(0, installed.returncode, installed.stderr)
            skills_root = (
                self.root / "custom-target" / "skills"
                if mode == "custom"
                else home / (".codex/skills" if mode == "legacy" else ".agents/skills")
            )
            marker = skills_root / "closure-triage" / "SKILL.md"
            marker.write_text(f"{mode} skill edit\n", encoding="utf-8")
            _, updated = self.run_installer(
                "update", "shared-review-gates", "--force", home_name=home_name, env_overrides=overrides
            )
            self.assertEqual(0, updated.returncode, updated.stderr)
            roots.append((skills_root, marker, overrides))

        backups = [
            managed_backup_path(common_state, skills_root, "skills", "closure-triage")
            for skills_root, _, _ in roots
        ]
        self.assertEqual(3, len(set(backups)))
        for mode, backup in zip(("agents", "legacy", "custom"), backups):
            self.assertEqual(f"{mode} skill edit\n", (backup / "SKILL.md").read_text(encoding="utf-8"))

    def test_nested_symlink_or_special_file_in_installed_skill_fails_before_force_mutation(
        self,
    ) -> None:
        for kind in ("symlink", "fifo"):
            with self.subTest(kind=kind):
                home_name = f"nested-{kind}-home"
                home, installed = self.run_installer(
                    "install", "shared-review-gates", home_name=home_name
                )
                self.assertEqual(0, installed.returncode, installed.stderr)
                skill = home / ".agents" / "skills" / "closure-triage"
                marker = skill / "SKILL.md"
                marker.write_text("local skill edit\n", encoding="utf-8")
                unsafe = skill / "untrusted-entry"
                if kind == "symlink":
                    external = self.root / f"{kind}-outside"
                    external.write_text("outside\n", encoding="utf-8")
                    unsafe.symlink_to(external)
                else:
                    if not hasattr(os, "mkfifo"):
                        self.skipTest("mkfifo is unavailable")
                    os.mkfifo(unsafe)

                _, refused = self.run_installer(
                    "update", "shared-review-gates", "--force", home_name=home_name
                )
                self.assertNotEqual(0, refused.returncode)
                self.assertEqual("local skill edit\n", marker.read_text(encoding="utf-8"))
                self.assertTrue(unsafe.exists() or unsafe.is_symlink())
                self.assertFalse(
                    managed_backup_path(
                        self.root / f"{home_name}-state",
                        home / ".agents" / "skills",
                        "skills",
                        "closure-triage",
                    ).exists()
                )

    def test_unsupported_plugin_list_warns_and_preserves_filesystem_fallback(self) -> None:
        fake_cli = self.root / "old-codex"
        fake_cli.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
        fake_cli.chmod(0o755)

        home, result = self.run_installer(
            "install",
            "shared-review-gates",
            home_name="old-cli-home",
            env_overrides={"CODEX_CLI": str(fake_cli)},
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("does not expose a readable plugin list", result.stderr)
        self.assertTrue((home / ".agents" / "skills" / "closure-triage" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
