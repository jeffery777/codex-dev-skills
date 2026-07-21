from __future__ import annotations

import io
import datetime as dt
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gitnexus_adapter as adapter
import gitnexus_hook as hook


HEAD = "a" * 40
INDEXED = "b" * 40
COMMITTER_ENV = {
    "GIT_AUTHOR_NAME": "Hook Test",
    "GIT_AUTHOR_EMAIL": "hook@example.invalid",
    "GIT_COMMITTER_NAME": "Hook Test",
    "GIT_COMMITTER_EMAIL": "hook@example.invalid",
}


def config_document(root: pathlib.Path, *, mode: str = "notify-only") -> dict:
    refresh = None
    if mode == "auto-on-demand":
        refresh = {
            "gitnexus_home_parent": str(root.parent / "isolated-homes"),
            "lock_directory": str(root.parent / "locks"),
            "timeout_seconds": 120,
        }
    return {
        "schema_version": 1,
        "mode": mode,
        "repository": {
            "root": str(root),
            "id": "github.com.Owner.Repository",
            "expected_remote": "https://github.com/Owner/Repository.git",
            "git_executable": None,
        },
        "qualification": {
            "executable": str(root.parent / "package" / "gitnexus"),
            "allow_symlink": False,
            "node_executable": None,
            "allow_node_symlink": False,
            "package_root": str(root.parent / "package"),
            "accepted_executable_sha256": "c" * 64,
            "accepted_package_sha256": "d" * 64,
            "accepted_runtime_sha256": None,
        },
        "refresh": refresh,
    }


def write_config(directory: pathlib.Path, document: dict) -> pathlib.Path:
    path = directory / "hook-config.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o600)
    return path


def hook_config(root: pathlib.Path, *, mode: str = "notify-only") -> hook.HookConfig:
    refresh = None
    if mode == "auto-on-demand":
        home_parent = root.parent / "isolated-homes"
        home_parent.mkdir(exist_ok=True)
        home_parent.chmod(0o700)
        refresh = {
            "gitnexus_home_parent": home_parent,
            "lock_directory": root.parent / "locks",
            "timeout_seconds": 120,
        }
    return hook.HookConfig(
        mode=mode,
        repository_root=root,
        repository_id="github.com.Owner.Repository",
        expected_remote="https://github.com/Owner/Repository.git",
        git_executable=None,
        qualification={},
        refresh=refresh,
    )


def repository_state(root: pathlib.Path) -> adapter.RepositoryState:
    return adapter.RepositoryState(
        root=root,
        canonical_repository_id="github.com.Owner.Repository",
        canonical_remote="github.com/owner/repository",
        head=HEAD,
        branch="main",
        identity={"repository_identity_digest": "e" * 64},
    )


def tracked_snapshot(*, dirty: bool = False) -> adapter.TrackedSnapshot:
    return adapter.TrackedSnapshot(
        head=HEAD,
        tracked_dirty=dirty,
        tracked_derived_present=False,
        outside_derived_dirty=dirty,
        tracked_state_digest="1" * 64,
        protected_state_digest="2" * 64,
        outside_derived_status_digest="3" * 64,
        complete_status_digest="4" * 64,
        worktree_state_digest="5" * 64,
    )


def event(root: pathlib.Path, name: str = "SessionStart") -> dict:
    base = {"cwd": str(root), "hook_event_name": name}
    if name == "SessionStart":
        base["source"] = "startup"
    else:
        base["tool_name"] = "Bash"
    return base


def run_git(root: pathlib.Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        env={**os.environ, **COMMITTER_ENV},
        check=True,
        capture_output=True,
    )


def make_repository(directory: pathlib.Path) -> pathlib.Path:
    root = directory / "integration-repo"
    root.mkdir()
    run_git(root, "init", "-b", "main")
    run_git(root, "remote", "add", "origin", "git@github.com:Owner/Repository.git")
    exclude = root / ".git" / "info" / "exclude"
    exclude.write_text(
        f"{exclude.read_text(encoding='utf-8')}\n.gitnexus/\n", encoding="utf-8"
    )
    (root / "code.py").write_text("print('first')\n", encoding="utf-8")
    run_git(root, "add", "code.py")
    run_git(root, "commit", "-m", "initial")
    return root


def make_cli(directory: pathlib.Path) -> pathlib.Path:
    package = directory / "package"
    package.mkdir()
    executable = package / "gitnexus"
    flags = " ".join(sorted(adapter.REQUIRED_ANALYZE_FLAGS))
    executable.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  /usr/bin/printf 'GitNexus 1.6.9\\n'\n"
        "else\n"
        f"  /usr/bin/printf '%s\\n' '{flags}'\n"
        "fi\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


def qualification_values(executable: pathlib.Path) -> dict:
    resolved, _ = adapter.discover_executable(executable)
    package_digest, _ = adapter._package_tree_identity(resolved.parent)
    runtime = adapter._script_runtime(resolved, None, allow_symlink=False)
    assert runtime is not None
    return {
        "executable": str(executable),
        "allow_symlink": False,
        "node_executable": None,
        "allow_node_symlink": False,
        "package_root": str(resolved.parent),
        "accepted_executable_sha256": adapter._executable_identity(resolved)[0],
        "accepted_package_sha256": package_digest,
        "accepted_runtime_sha256": runtime[1],
    }


def write_valid_metadata(root: pathlib.Path) -> None:
    state = adapter.collect_repository_state(
        root,
        canonical_repository_id="github.com.Owner.Repository",
        expected_remote="https://github.com/Owner/Repository.git",
    )
    metadata = {
        "repoPath": str(root),
        "lastCommit": state.head,
        "indexedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "remoteUrl": "git@github.com:Owner/Repository.git",
        "stats": {
            "files": 1,
            "nodes": 1,
            "edges": 1,
            "communities": 0,
            "processes": 0,
            "embeddings": 0,
        },
        "capabilities": {
            "graph": {"provider": adapter.GRAPH_PROVIDER, "status": "available"},
            "fts": {"provider": adapter.FTS_PROVIDER, "status": "available"},
            "vectorSearch": {
                "provider": adapter.VECTOR_PROVIDER,
                "status": "unavailable",
                "exactScanLimit": 10000,
                "reason": "embeddings-disabled",
            },
        },
        "schemaVersion": adapter.META_SCHEMA_VERSION,
        "cjkSegmentation": "none",
        "cacheKeys": ["c" * 64],
        "branch": "main",
        "fileHashes": {"code.py": "f" * 64},
    }
    index = root / ".gitnexus"
    index.mkdir()
    for name in ("gitnexus.json", "meta.json"):
        (index / name).write_text(json.dumps(metadata), encoding="utf-8")


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temporary.name).resolve()
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.machine = self.directory / "machine"
        self.machine.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_notify_only_config_is_machine_local_and_valid(self) -> None:
        path = write_config(self.machine, config_document(self.root))
        parsed = hook.load_config(path)
        self.assertEqual("notify-only", parsed.mode)
        self.assertEqual(self.root, parsed.repository_root)
        self.assertIsNone(parsed.refresh)

    def test_auto_on_demand_requires_complete_refresh_config(self) -> None:
        document = config_document(self.root, mode="auto-on-demand")
        document["refresh"] = None
        path = write_config(self.machine, document)
        with self.assertRaisesRegex(hook.GitNexusHookError, "refresh-object-required"):
            hook.load_config(path)

    def test_nul_in_path_is_rejected(self) -> None:
        document = config_document(self.root)
        document["repository"]["root"] = "/tmp/repo\x00other"
        path = write_config(self.machine, document)
        with self.assertRaisesRegex(hook.GitNexusHookError, "nul-forbidden"):
            hook.load_config(path)

    def test_config_inside_repository_is_rejected(self) -> None:
        path = write_config(self.root, config_document(self.root))
        with self.assertRaisesRegex(hook.GitNexusHookError, "config-must-be-machine-local"):
            hook.load_config(path)

    def test_group_writable_config_is_rejected(self) -> None:
        path = write_config(self.machine, config_document(self.root))
        path.chmod(0o620)
        with self.assertRaisesRegex(hook.GitNexusHookError, "config-permissions-unsafe"):
            hook.load_config(path)

    def test_duplicate_config_key_is_rejected(self) -> None:
        path = self.machine / "hook-config.json"
        path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        path.chmod(0o600)
        with self.assertRaisesRegex(hook.GitNexusHookError, "json-duplicate-key"):
            hook.load_config(path)

    def test_runtime_digest_is_allowed_for_absolute_shebang(self) -> None:
        document = config_document(self.root)
        document["qualification"]["accepted_runtime_sha256"] = "f" * 64
        path = write_config(self.machine, document)
        parsed = hook.load_config(path)
        self.assertEqual("f" * 64, parsed.qualification["accepted_runtime_sha256"])

    def test_explicit_node_requires_runtime_digest(self) -> None:
        document = config_document(self.root)
        document["qualification"]["node_executable"] = "/usr/bin/node"
        path = write_config(self.machine, document)
        with self.assertRaisesRegex(hook.GitNexusHookError, "node-without-runtime-digest"):
            hook.load_config(path)

    def test_validate_config_does_not_contact_gitnexus(self) -> None:
        path = write_config(self.machine, config_document(self.root))
        output = io.StringIO()
        with mock.patch("sys.stdout", output), mock.patch.object(
            hook, "evaluate_hook"
        ) as evaluate:
            status = hook.hook_main(["--config", str(path), "--validate-config"])
        self.assertEqual(0, status)
        evaluate.assert_not_called()
        self.assertEqual("valid", json.loads(output.getvalue())["status"])

    def test_validate_config_returns_nonzero_for_invalid_config(self) -> None:
        document = config_document(self.root)
        document["mode"] = "unsafe-auto"
        path = write_config(self.machine, document)
        output = io.StringIO()
        with mock.patch("sys.stdout", output):
            status = hook.hook_main(["--config", str(path), "--validate-config"])
        self.assertEqual(2, status)
        result = json.loads(output.getvalue())
        self.assertEqual("invalid", result["status"])
        self.assertEqual("config-mode-unsupported", result["error_code"])


class InputTests(unittest.TestCase):
    def test_session_start_input_accepts_documented_fields(self) -> None:
        value = {
            "session_id": "session",
            "transcript_path": None,
            "cwd": "/tmp/repo",
            "hook_event_name": "SessionStart",
            "model": "model",
            "permission_mode": "default",
            "source": "resume",
        }
        parsed = hook._read_hook_input(io.BytesIO(json.dumps(value).encode()))
        self.assertEqual("resume", parsed["source"])

    def test_post_tool_use_rejects_non_bash_tool(self) -> None:
        value = {
            "cwd": "/tmp/repo",
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
        }
        with self.assertRaisesRegex(hook.GitNexusHookError, "post-tool-name-unsupported"):
            hook._read_hook_input(io.BytesIO(json.dumps(value).encode()))

    def test_unknown_input_field_fails_safe(self) -> None:
        value = {
            "cwd": "/tmp/repo",
            "hook_event_name": "SessionStart",
            "source": "startup",
            "private_runtime_state": "forbidden",
        }
        with self.assertRaisesRegex(hook.GitNexusHookError, "field-unknown"):
            hook._read_hook_input(io.BytesIO(json.dumps(value).encode()))

    def test_oversized_input_is_rejected(self) -> None:
        with self.assertRaisesRegex(hook.GitNexusHookError, "hook-input-too-large"):
            hook._read_hook_input(io.BytesIO(b"x" * (hook.MAX_INPUT_BYTES + 1)))


class EvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temporary.name).resolve()
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.repo = repository_state(self.root)
        self.qualification = mock.Mock(fingerprint="6" * 64)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def evaluate(
        self,
        metadata: adapter.MetadataResult,
        *,
        mode: str = "notify-only",
        dirty: bool = False,
        event_name: str = "SessionStart",
    ) -> dict | None:
        with (
            mock.patch.object(hook, "_qualify", return_value=self.qualification),
            mock.patch.object(adapter, "collect_repository_state", return_value=self.repo),
            mock.patch.object(adapter, "collect_tracked_snapshot", return_value=tracked_snapshot(dirty=dirty)),
            mock.patch.object(adapter, "assess_metadata", return_value=metadata),
        ):
            return hook.evaluate_hook(
                hook_config(self.root, mode=mode), event(self.root, event_name)
            )

    def test_fresh_state_is_silent(self) -> None:
        result = self.evaluate(adapter.MetadataResult("fresh", "exact-clean-revision", HEAD, "f" * 64, {}))
        self.assertIsNone(result)

    def test_notify_only_reports_stale_revision(self) -> None:
        result = self.evaluate(
            adapter.MetadataResult("stale", "indexed-revision-stale", INDEXED, "f" * 64, {})
        )
        assert result is not None
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("is stale", message)
        self.assertIn("must not be used", message)
        self.assertIn("disabled", message)

    def test_post_tool_use_suppresses_uncommitted_only_noise(self) -> None:
        result = self.evaluate(
            adapter.MetadataResult("stale", "working-tree-dirty", HEAD, "f" * 64, {}),
            dirty=True,
            event_name="PostToolUse",
        )
        self.assertIsNone(result)

    def test_post_tool_use_reports_revision_change_even_if_dirty(self) -> None:
        result = self.evaluate(
            adapter.MetadataResult("stale", "working-tree-dirty", INDEXED, "f" * 64, {}),
            dirty=True,
            event_name="PostToolUse",
        )
        self.assertIsNotNone(result)

    def test_post_tool_use_reports_corrupt_state_without_revision(self) -> None:
        result = self.evaluate(
            adapter.MetadataResult("corrupt", "metadata-json-invalid", None, None, None),
            event_name="PostToolUse",
        )
        assert result is not None
        self.assertIn("is corrupt", result["hookSpecificOutput"]["additionalContext"])

    def test_dirty_repository_never_reaches_refresh_controller(self) -> None:
        with mock.patch.object(adapter, "RefreshController") as controller:
            result = self.evaluate(
                adapter.MetadataResult("stale", "working-tree-dirty", INDEXED, "f" * 64, {}),
                mode="auto-on-demand",
                dirty=True,
            )
        controller.assert_not_called()
        assert result is not None
        self.assertIn("not safe", result["hookSpecificOutput"]["additionalContext"])

    def test_auto_on_demand_delegates_to_v2c_a_controller(self) -> None:
        refreshed = adapter.RefreshResult(
            "refreshed", "qualified-index-adoptable", {"receipt_digest": "f" * 64}
        )
        controller = mock.Mock()
        controller.refresh.return_value = refreshed
        with (
            mock.patch.object(hook, "_qualify", return_value=self.qualification),
            mock.patch.object(adapter, "collect_repository_state", return_value=self.repo),
            mock.patch.object(adapter, "collect_tracked_snapshot", return_value=tracked_snapshot()),
            mock.patch.object(
                adapter,
                "assess_metadata",
                return_value=adapter.MetadataResult(
                    "stale", "indexed-revision-stale", INDEXED, "f" * 64, {}
                ),
            ),
            mock.patch.object(adapter, "RefreshController", return_value=controller) as constructor,
        ):
            result = hook.evaluate_hook(
                hook_config(self.root, mode="auto-on-demand"), event(self.root)
            )
        constructor.assert_called_once_with(
            self.qualification,
            enabled=True,
            timeout_seconds=120,
            gitnexus_home=mock.ANY,
            lock_directory=self.directory / "locks",
            git_executable=None,
        )
        isolated_home = constructor.call_args.kwargs["gitnexus_home"]
        self.assertEqual(self.directory / "isolated-homes", isolated_home.parent)
        self.assertTrue(isolated_home.name.startswith("gitnexus-v2c-b-"))
        self.assertEqual(0o700, stat.S_IMODE(isolated_home.stat().st_mode))
        controller.refresh.assert_called_once_with(
            self.repo, expected_head=HEAD, explicit_opt_in=True
        )
        assert result is not None
        self.assertIn("refreshed and verified", result["hookSpecificOutput"]["additionalContext"])

    def test_refresh_failure_persists_circuit_breaker_and_prevents_retry(self) -> None:
        failed = adapter.RefreshResult(
            "failed", "unexpected-repository-mutation", {"receipt_digest": "f" * 64}
        )
        controller = mock.Mock()
        controller.refresh.return_value = failed
        constructor = mock.Mock(return_value=controller)
        metadata = adapter.MetadataResult(
            "stale", "indexed-revision-stale", INDEXED, "f" * 64, {}
        )
        with (
            mock.patch.object(hook, "_qualify", return_value=self.qualification),
            mock.patch.object(adapter, "collect_repository_state", return_value=self.repo),
            mock.patch.object(adapter, "collect_tracked_snapshot", return_value=tracked_snapshot()),
            mock.patch.object(adapter, "assess_metadata", return_value=metadata),
            mock.patch.object(adapter, "RefreshController", constructor),
        ):
            first = hook.evaluate_hook(
                hook_config(self.root, mode="auto-on-demand"), event(self.root)
            )
            second = hook.evaluate_hook(
                hook_config(self.root, mode="auto-on-demand"), event(self.root)
            )
        self.assertEqual(1, constructor.call_count)
        assert first is not None and second is not None
        self.assertIn("refresh failed", first["hookSpecificOutput"]["additionalContext"])
        self.assertIn("remains disabled", second["hookSpecificOutput"]["additionalContext"])
        markers = list((self.directory / "isolated-homes").glob(".codex-v2c-b-auto-disabled-*.json"))
        self.assertEqual(1, len(markers))
        self.assertEqual(0o600, stat.S_IMODE(markers[0].stat().st_mode))

    def test_unsafe_home_parent_blocks_auto_refresh(self) -> None:
        config = hook_config(self.root, mode="auto-on-demand")
        assert config.refresh is not None
        config.refresh["gitnexus_home_parent"].chmod(0o777)
        metadata = adapter.MetadataResult(
            "stale", "indexed-revision-stale", INDEXED, "f" * 64, {}
        )
        with (
            mock.patch.object(hook, "_qualify", return_value=self.qualification),
            mock.patch.object(adapter, "collect_repository_state", return_value=self.repo),
            mock.patch.object(adapter, "collect_tracked_snapshot", return_value=tracked_snapshot()),
            mock.patch.object(adapter, "assess_metadata", return_value=metadata),
            mock.patch.object(adapter, "RefreshController") as controller,
        ):
            with self.assertRaisesRegex(hook.GitNexusHookError, "permissions-unsafe"):
                hook.evaluate_hook(config, event(self.root))
        controller.assert_not_called()

    def test_hook_cwd_outside_configured_repository_is_rejected(self) -> None:
        outside = self.directory / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(hook.GitNexusHookError, "hook-cwd-outside-repository"):
            hook.evaluate_hook(hook_config(self.root), event(outside))


class TemplateTests(unittest.TestCase):
    def test_inactive_hook_template_uses_supported_events(self) -> None:
        path = ROOT / "templates" / "hooks" / "gitnexus-v2c-b" / "hooks.json.template"
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual({"SessionStart", "PostToolUse"}, set(document["hooks"]))
        self.assertEqual("^Bash$", document["hooks"]["PostToolUse"][0]["matcher"])
        for groups in document["hooks"].values():
            for group in groups:
                for handler in group["hooks"]:
                    self.assertEqual("command", handler["type"])
                    self.assertIn("--config", handler["command"])
                    self.assertIn("__ABSOLUTE_PYTHON3_EXECUTABLE__", handler["command"])

    def test_template_defaults_to_notify_only(self) -> None:
        path = ROOT / "templates" / "hooks" / "gitnexus-v2c-b" / "config.json.template"
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("notify-only", document["mode"])
        self.assertIsNone(document["refresh"])
        self.assertEqual(
            "__ABSOLUTE_NODE_EXECUTABLE__",
            document["qualification"]["node_executable"],
        )
        self.assertEqual(
            "__64_HEX_CALLER_ACCEPTED_RUNTIME_DIGEST__",
            document["qualification"]["accepted_runtime_sha256"],
        )


class LiveBoundaryIntegrationTests(unittest.TestCase):
    def test_post_tool_hook_observes_clean_head_change_without_parsing_command(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            root = make_repository(directory)
            executable = make_cli(directory)
            write_valid_metadata(root)
            machine = directory / "machine"
            machine.mkdir()
            document = config_document(root)
            document["qualification"] = qualification_values(executable)
            config = hook.load_config(write_config(machine, document))

            self.assertIsNone(hook.evaluate_hook(config, event(root)))

            (root / "code.py").write_text("print('second')\n", encoding="utf-8")
            run_git(root, "add", "code.py")
            run_git(root, "commit", "-m", "advance head")
            result = hook.evaluate_hook(config, event(root, "PostToolUse"))

            assert result is not None
            message = result["hookSpecificOutput"]["additionalContext"]
            self.assertIn("indexed-revision-stale", message)
            self.assertIn("must not be used", message)


if __name__ == "__main__":
    unittest.main()
