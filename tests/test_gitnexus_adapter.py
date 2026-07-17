from __future__ import annotations

import copy
import datetime as dt
import errno
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("gitnexus_adapter", SCRIPTS / "gitnexus_adapter.py")
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


COMMITTER_ENV = {
    "GIT_AUTHOR_NAME": "Adapter Test",
    "GIT_AUTHOR_EMAIL": "adapter@example.invalid",
    "GIT_COMMITTER_NAME": "Adapter Test",
    "GIT_COMMITTER_EMAIL": "adapter@example.invalid",
}


def run_git(root: pathlib.Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=root, env={**os.environ, **COMMITTER_ENV}, check=True, capture_output=True)


def make_repo(directory: pathlib.Path) -> pathlib.Path:
    root = directory / "repo"
    root.mkdir()
    run_git(root, "init", "-b", "main")
    run_git(root, "remote", "add", "origin", "git@github.com:Owner/Repository.git")
    exclude = root / ".git" / "info" / "exclude"
    exclude.write_text(f"{exclude.read_text(encoding='utf-8')}\n.gitnexus/\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("policy\n", encoding="utf-8")
    (root / "code.py").write_text("print('safe')\n", encoding="utf-8")
    run_git(root, "add", "-f", "AGENTS.md", "code.py")
    run_git(root, "commit", "-m", "initial")
    return root


def make_executable(directory: pathlib.Path) -> pathlib.Path:
    path = directory / "gitnexus"
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def make_cli_executable(directory: pathlib.Path) -> pathlib.Path:
    path = directory / "gitnexus-cli"
    flags = " ".join(sorted(adapter.REQUIRED_ANALYZE_FLAGS))
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  /usr/bin/printf 'GitNexus 1.6.9\\n'\n"
        "else\n"
        f"  /usr/bin/printf '%s\\n' '{flags}'\n"
        "fi\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def fake_qualification(executable: pathlib.Path) -> adapter.ExecutableQualification:
    digest, identity = adapter._executable_identity(executable)
    body = adapter._qualification_body(
        executable_sha256=digest,
        analyze_flags=sorted(adapter.REQUIRED_ANALYZE_FLAGS),
        symlink_policy="regular-file-only",
        runtime_executable_sha256=None,
    )
    return adapter.ExecutableQualification(
        executable, digest, "1.6.9", tuple(sorted(adapter.REQUIRED_ANALYZE_FLAGS)),
        "regular-file-only", adapter._canonical_digest(body), identity,
    )


def repository_state(root: pathlib.Path) -> adapter.RepositoryState:
    return adapter.collect_repository_state(
        root,
        canonical_repository_id="github.com.Owner.Repository",
        expected_remote="https://github.com/Owner/Repository.git",
    )


def valid_metadata(state: adapter.RepositoryState) -> dict:
    return {
        "repoPath": str(state.root),
        "lastCommit": state.head,
        "indexedAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "remoteUrl": "git@github.com:Owner/Repository.git",
        "stats": {"files": 2, "nodes": 1, "edges": 1, "communities": 0, "processes": 0, "embeddings": 0},
        "capabilities": {
            "graph": {"provider": adapter.GRAPH_PROVIDER, "status": "available"},
            "fts": {"provider": adapter.FTS_PROVIDER, "status": "available"},
            "vectorSearch": {
                "provider": adapter.VECTOR_PROVIDER, "status": "unavailable",
                "exactScanLimit": 10000, "reason": "embeddings-disabled",
            },
        },
        "schemaVersion": 5,
        "cjkSegmentation": "none",
        "cacheKeys": ["c" * 64],
        "branch": "main",
        "fileHashes": {"code.py": "a" * 64},
    }


def write_metadata(root: pathlib.Path, value: dict) -> None:
    directory = root / ".gitnexus"
    directory.mkdir(exist_ok=True)
    for filename in ("gitnexus.json", "meta.json"):
        (directory / filename).write_text(json.dumps(value), encoding="utf-8")


class QualificationTests(unittest.TestCase):
    def test_exact_version_flags_argv_environment_and_fingerprint(self):
        with tempfile.TemporaryDirectory() as raw:
            executable = make_executable(pathlib.Path(raw).resolve())
            calls = []

            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                if argv[-1] == "--version":
                    return subprocess.CompletedProcess(argv, 0, "GitNexus 1.6.9\n", "")
                return subprocess.CompletedProcess(
                    argv, 0,
                    "--index-only --skip-agents-md --skip-skills --branch --name --force\n", "",
                )

            first = adapter.qualify_executable(executable, runner=runner, environment={"HOME": raw, "PATH": "/unsafe", "GIT_DIR": "/unsafe"})
            second = adapter.qualify_executable(executable, runner=runner, environment={"HOME": raw})
            self.assertEqual(first.fingerprint, second.fingerprint)
            resolved = str(executable.resolve())
            self.assertEqual([[resolved, "--version"], [resolved, "analyze", "--help"]], [item[0] for item in calls[:2]])
            self.assertEqual({"HOME": raw}, calls[0][1]["env"])
            self.assertNotIn("shell", calls[0][1])

    def test_version_capability_drift_and_symlink_policy_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            executable = make_executable(directory)
            link = directory / "link"
            link.symlink_to(executable)
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "symlink"):
                adapter.discover_executable(link)
            resolved, policy = adapter.discover_executable(link, allow_symlink=True)
            self.assertEqual(executable.resolve(), resolved)
            self.assertEqual("resolved-symlink", policy)

            def version_drift(argv, **kwargs):
                output = "GitNexus 1.7.0" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "exact version"):
                adapter.qualify_executable(executable, runner=version_drift)

            def flag_drift(argv, **kwargs):
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else "--index-only"
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "flags"):
                adapter.qualify_executable(executable, runner=flag_drift)

    def test_env_node_launcher_is_discovered_bound_and_used_without_inherited_path(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            executable = directory / "gitnexus-entry.js"
            executable.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            node = directory / "node"
            node.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            node.chmod(node.stat().st_mode | stat.S_IXUSR)
            calls = []

            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            qualification = adapter.qualify_executable(
                executable,
                runner=runner,
                environment={"HOME": raw, "PATH": raw},
            )
            self.assertEqual(node.resolve(), qualification.runtime_executable)
            self.assertEqual([str(node.resolve()), str(executable.resolve()), "--version"], calls[0][0])
            self.assertEqual({"HOME": raw}, calls[0][1]["env"])
            node.write_text("#!/bin/sh\n# drift\nexit 0\n", encoding="utf-8")
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "runtime executable drifted"):
                adapter.verify_qualification(qualification)


class IdentitySnapshotMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temp.name).resolve()
        self.root = make_repo(self.directory)
        self.executable = make_executable(self.directory)
        self.qualification = fake_qualification(self.executable)
        self.repository = repository_state(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def assess(self):
        return adapter.assess_metadata(
            self.repository, adapter.collect_tracked_snapshot(self.root), self.qualification
        )

    def test_remote_identity_and_complete_snapshot_are_canonical_and_tamper_evident(self):
        self.assertEqual("https://github.com/Owner/Repository.git", self.repository.canonical_remote)
        self.assertNotIn(str(self.root), json.dumps(self.repository.identity))
        clean = adapter.collect_tracked_snapshot(self.root)
        self.assertFalse(clean.tracked_dirty)
        (self.root / "AGENTS.md").write_text("changed\n", encoding="utf-8")
        dirty = adapter.collect_tracked_snapshot(self.root)
        self.assertTrue(dirty.tracked_dirty)
        self.assertNotEqual(clean.tracked_state_digest, dirty.tracked_state_digest)
        self.assertNotEqual(clean.protected_state_digest, dirty.protected_state_digest)

    def test_remote_normalization_rejects_unsafe_or_ambiguous_forms(self):
        self.assertEqual(
            "https://github.com/Owner/Repository.git",
            adapter.normalize_remote("ssh://git@GitHub.com/Owner/Repository.git"),
        )
        for value in ("repo", "https://user:password@example.com/a/b", "https://example.com/a/b/c", "https://example.com/a/../b"):
            with self.subTest(value=value), self.assertRaises(adapter.GitNexusAdapterError):
                adapter.normalize_remote(value)
        self.assertEqual(
            "https://example.com:8443/a/b.git",
            adapter.normalize_remote("https://example.com:8443/a/b.git"),
        )
        self.assertEqual(
            "https://example.com:2222/a/b.git",
            adapter.normalize_remote("ssh://git@example.com:2222/a/b.git"),
        )
        self.assertEqual(
            "https://example.com/a/b.git",
            adapter.normalize_remote("https://example.com:443/a/b.git"),
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "origin"):
            adapter.collect_repository_state(
                self.root,
                canonical_repository_id="github.com.Owner.Repository",
                expected_remote="https://github.com/Wrong/Repository.git",
            )

    def test_metadata_fresh_stale_dirty_missing_partial_unsupported_incompatible_corrupt_unknown(self):
        write_metadata(self.root, valid_metadata(self.repository))
        self.assertEqual("fresh", self.assess().state)

        value = valid_metadata(self.repository)
        value["lastCommit"] = "2" * 40
        write_metadata(self.root, value)
        self.assertEqual("stale", self.assess().state)

        write_metadata(self.root, valid_metadata(self.repository))
        (self.root / "code.py").write_text("dirty\n", encoding="utf-8")
        self.assertEqual(("stale", "working-tree-dirty"), (self.assess().state, self.assess().reason))
        (self.root / "code.py").write_text("print('safe')\n", encoding="utf-8")

        (self.root / "new-source.py").write_text("untracked\n", encoding="utf-8")
        self.assertEqual(("stale", "working-tree-dirty"), (self.assess().state, self.assess().reason))
        (self.root / "new-source.py").unlink()

        (self.root / ".gitnexus" / "gitnexus.json").unlink()
        (self.root / ".gitnexus" / "meta.json").unlink()
        self.assertEqual("missing", self.assess().state)
        value = valid_metadata(self.repository)
        del value["stats"]
        write_metadata(self.root, value)
        self.assertEqual("partial", self.assess().state)
        value = valid_metadata(self.repository)
        value["schemaVersion"] = 6
        write_metadata(self.root, value)
        self.assertEqual("unsupported", self.assess().state)
        value = valid_metadata(self.repository)
        value["remoteUrl"] = "https://github.com/Wrong/Repository.git"
        write_metadata(self.root, value)
        self.assertEqual("incompatible", self.assess().state)
        value = valid_metadata(self.repository)
        value["unexpected"] = True
        write_metadata(self.root, value)
        self.assertEqual("corrupt", self.assess().state)
        conflicting = copy.copy(adapter.collect_tracked_snapshot(self.root))
        object.__setattr__(conflicting, "head", "3" * 40)
        write_metadata(self.root, valid_metadata(self.repository))
        self.assertEqual("unknown", adapter.assess_metadata(self.repository, conflicting, self.qualification).state)

    def test_metadata_rejects_symlink_unsafe_path_partial_and_capability_drift(self):
        value = valid_metadata(self.repository)
        for unsafe in ("../secret", ".", "./code.py", "a//b", "a\\b"):
            with self.subTest(unsafe=unsafe):
                value = valid_metadata(self.repository)
                value["fileHashes"] = {unsafe: "a" * 64}
                write_metadata(self.root, value)
                self.assertEqual("corrupt", self.assess().state)
        value = valid_metadata(self.repository)
        value["capabilities"]["graph"]["provider"] = "drifted"
        write_metadata(self.root, value)
        self.assertEqual("incompatible", self.assess().state)

    def test_metadata_cache_keys_validate_items_before_deduplication(self):
        invalid_items = (["nested"], {"nested": []}, 7, True)
        for invalid in invalid_items:
            with self.subTest(invalid=invalid):
                value = valid_metadata(self.repository)
                value["cacheKeys"] = [invalid]
                write_metadata(self.root, value)
                assessed = self.assess()
                self.assertEqual(
                    ("corrupt", "metadata-cache-keys-invalid"),
                    (assessed.state, assessed.reason),
                )
        value = valid_metadata(self.repository)
        value["cacheKeys"] = ["duplicate", "duplicate"]
        write_metadata(self.root, value)
        assessed = self.assess()
        self.assertEqual(
            ("corrupt", "metadata-cache-keys-invalid"),
            (assessed.state, assessed.reason),
        )

    def test_primary_legacy_selection_is_fail_closed_and_schema_one_is_incompatible(self):
        value = valid_metadata(self.repository)
        write_metadata(self.root, value)
        primary = self.root / ".gitnexus" / "gitnexus.json"
        legacy = self.root / ".gitnexus" / "meta.json"

        primary.unlink()
        self.assertEqual("fresh", self.assess().state, "legacy is allowed only when primary is absent")

        schema_one = {
            "repoPath": str(self.repository.root),
            "lastCommit": self.repository.head,
            "indexedAt": "2026-07-12T00:00:00Z",
            "remoteUrl": self.repository.canonical_remote,
            "stats": {}, "capabilities": {}, "schemaVersion": 1, "fileHashes": {},
        }
        legacy.write_text(json.dumps(schema_one), encoding="utf-8")
        assessed = self.assess()
        self.assertEqual(("incompatible", "legacy-schema-1-not-qualified"), (assessed.state, assessed.reason))

        write_metadata(self.root, value)
        conflicting = copy.deepcopy(value)
        conflicting["lastCommit"] = "2" * 40
        legacy.write_text(json.dumps(conflicting), encoding="utf-8")
        self.assertEqual("incompatible", self.assess().state)

        primary.write_text("{not-json", encoding="utf-8")
        legacy.write_text(json.dumps(value), encoding="utf-8")
        self.assertEqual("corrupt", self.assess().state, "corrupt primary cannot fall back")
        metadata = self.root / ".gitnexus" / "gitnexus.json"
        metadata.unlink()
        target = self.directory / "outside-meta"
        target.write_text(json.dumps(valid_metadata(self.repository)), encoding="utf-8")
        metadata.symlink_to(target)
        self.assertEqual("corrupt", self.assess().state)

        metadata.unlink()
        (self.root / ".gitnexus" / "meta.json").unlink()
        (self.root / ".gitnexus").rmdir()
        outside_directory = self.directory / "outside-index"
        outside_directory.mkdir()
        (self.root / ".gitnexus").symlink_to(outside_directory, target_is_directory=True)
        self.assertEqual("incompatible", self.assess().state)

    def test_metadata_selection_expired_after_json_parse_cannot_return_fresh(self):
        write_metadata(self.root, valid_metadata(self.repository))
        ticks = iter((*([0.0] * 15), 2.0))
        with (
            mock.patch.object(adapter.time, "monotonic", side_effect=lambda: next(ticks, 2.0)),
            self.assertRaisesRegex(adapter.ProbeDeadlineError, "probe-deadline-expired"),
        ):
            adapter._select_metadata(self.root / ".gitnexus", deadline=1.0)

    def test_metadata_fifo_open_is_nonblocking_and_rejected_before_read(self):
        index_directory = self.root / ".gitnexus"
        index_directory.mkdir()
        fifo = index_directory / "gitnexus.json"
        os.mkfifo(fifo)
        directory_fd = adapter._open_directory_nofollow(index_directory)
        real_open = os.open
        observed_flags = []

        def guarded_open(path, flags, *args, **kwargs):
            observed_flags.append(flags)
            self.assertTrue(flags & os.O_NONBLOCK)
            return real_open(path, flags, *args, **kwargs)

        try:
            with (
                mock.patch.object(adapter.os, "open", side_effect=guarded_open),
                mock.patch.object(adapter.os, "read") as read_mock,
                self.assertRaisesRegex(
                    adapter.GitNexusAdapterError,
                    "opened control input is not a regular file",
                ),
            ):
                adapter._read_regular_at(
                    directory_fd,
                    "gitnexus.json",
                    maximum_bytes=adapter.MAX_METADATA_BYTES,
                    deadline=time.monotonic() + 1.0,
                )
            read_mock.assert_not_called()
        finally:
            os.close(directory_fd)

        self.assertEqual(1, len(observed_flags))

    def test_metadata_reader_fails_closed_before_open_without_nonblocking_support(self):
        class MissingNonblockingOS:
            O_RDONLY = os.O_RDONLY
            O_NOFOLLOW = os.O_NOFOLLOW
            open = mock.Mock()

        unsupported = MissingNonblockingOS()
        with (
            mock.patch.object(adapter, "os", unsupported),
            self.assertRaisesRegex(
                adapter.GitNexusAdapterError,
                "POSIX nonblocking control-file operations are unavailable",
            ),
        ):
            adapter._read_regular_at(
                0,
                "gitnexus.json",
                maximum_bytes=adapter.MAX_METADATA_BYTES,
            )

        unsupported.open.assert_not_called()


class V2bIntegrationTests(unittest.TestCase):
    def test_default_disabled_and_enabled_handshakes_are_honest(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            root = make_repo(directory)
            executable = make_executable(directory)
            qualification = fake_qualification(executable)
            repository = repository_state(root)
            write_metadata(root, valid_metadata(repository))
            metadata = adapter.assess_metadata(repository, adapter.collect_tracked_snapshot(root), qualification)
            disabled = adapter.build_handshake(qualification, metadata, observed_at="2026-07-16T00:00:00Z")
            self.assertEqual("disabled", disabled["status"])
            enabled = adapter.build_handshake(qualification, metadata, enabled=True, observed_at="2026-07-16T00:00:00Z")
            self.assertEqual("degraded", enabled["status"])
            self.assertEqual("unsupported", enabled["capabilities"]["read_query"]["state"])
            for operation in ("write_upsert", "invalidate", "tombstone", "delete"):
                self.assertEqual("unsupported", enabled["capabilities"][operation]["state"])
            forged = copy.copy(qualification)
            object.__setattr__(forged, "fingerprint", "0" * 64)
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "fingerprint"):
                adapter.build_handshake(forged, metadata, enabled=True)

    def test_advisory_receipt_never_copies_or_elevates_adapter_authority(self):
        from tests import test_memory_contract as fixtures

        decision = fixtures.retrieval_input()
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            root = make_repo(directory)
            executable = make_executable(directory)
            qualification = fake_qualification(executable)
            repository = repository_state(root)
            write_metadata(root, valid_metadata(repository))
            metadata = adapter.assess_metadata(
                repository, adapter.collect_tracked_snapshot(root), qualification
            )
            decision["handshake"] = adapter.build_handshake(
                qualification, metadata, enabled=True, observed_at=fixtures.NOW
            )
        decision["response"].update({
            "adapter_id": "gitnexus-local-advisory",
            "status": "unsupported",
            "records": [],
            "errors": [{"code": "unsupported", "message": "structured query unavailable", "retryable": False}],
        })
        fixtures.resign_response(decision["response"])
        receipt = adapter.decide_advisory_retrieval(decision)
        self.assertTrue(receipt["fallback_to_no_memory"])
        self.assertEqual("adapter-degraded", receipt["fallback_reason"])
        self.assertIsNone(receipt["trusted_conformance_digest"])
        self.assertFalse(receipt["authority_invariants"]["mutation_authorized"])
        self.assertFalse(receipt["authority_invariants"]["external_write_authorized"])
        self.assertFalse(receipt["authority_invariants"]["completion_proven"])
        for operation in ("upsert", "invalidate", "tombstone", "delete"):
            disposition = adapter.unsupported_mutation(operation)
            self.assertEqual("unsupported", disposition["status"])
            self.assertFalse(disposition["write_performed"])
        decision["response"].update({"status": "ok", "errors": []})
        fixtures.resign_response(decision["response"])
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "not an adoptable"):
            adapter.decide_advisory_retrieval(decision)


class RefreshControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temp.name).resolve()
        self.root = make_repo(self.directory)
        self.executable = make_executable(self.directory)
        self.qualification = fake_qualification(self.executable)
        self.repository = repository_state(self.root)
        self.gitnexus_home = self.directory / "isolated-gitnexus-home"
        self.gitnexus_home.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def controller(self, runner, *, enabled=True, timeout=10):
        return adapter.RefreshController(
            self.qualification,
            enabled=enabled,
            timeout_seconds=timeout,
            environment={
                "HOME": str(self.directory), "PATH": "/unsafe", "GIT_DIR": "/unsafe",
                "HTTPS_PROXY": "http://proxy.invalid", "OPENAI_API_KEY": "not-forwarded",
                "GITNEXUS_LBUG_EXTENSION_INSTALL": "auto",
            },
            gitnexus_home=self.gitnexus_home,
            lock_directory=self.directory / "locks",
            runner=runner,
        )

    def test_default_disabled_and_head_dirty_preconditions_prevent_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        disabled = self.controller(runner, enabled=False)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "disabled"):
            disabled.refresh(self.repository, expected_head=self.repository.head, explicit_opt_in=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "explicitly opted"):
            self.controller(runner).refresh(self.repository, expected_head=self.repository.head)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "expected HEAD"):
            self.controller(runner).refresh(self.repository, expected_head="2" * 40, explicit_opt_in=True)
        (self.root / "code.py").write_text("dirty\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "dirty"):
            self.controller(runner).refresh(self.repository, expected_head=self.repository.head, explicit_opt_in=True)
        (self.root / "code.py").write_text("print('safe')\n", encoding="utf-8")
        (self.root / "user-untracked.txt").write_text("user change\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "outside the derived index"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_success_uses_only_index_only_structured_argv_and_safe_environment(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "indexed", "")

        result = self.controller(runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual("refreshed", result.status)
        argv, kwargs = calls[0]
        self.assertEqual([str(self.executable), "analyze", "--index-only", "--name"], argv[:4])
        self.assertEqual(6, len(argv))
        self.assertEqual(str(self.repository.root), argv[-1])
        self.assertNotIn("shell", kwargs)
        self.assertEqual("never", kwargs["env"]["GITNEXUS_LBUG_EXTENSION_INSTALL"])
        self.assertEqual(str(self.gitnexus_home.resolve()), kwargs["env"]["GITNEXUS_HOME"])
        self.assertEqual(str(self.gitnexus_home.resolve()), kwargs["env"]["HOME"])
        self.assertNotIn("PATH", kwargs["env"])
        self.assertNotIn("GIT_DIR", kwargs["env"])
        self.assertNotIn("HTTPS_PROXY", kwargs["env"])
        self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
        self.assertEqual(str(self.gitnexus_home.resolve()), kwargs["env"]["TMPDIR"])
        self.assertEqual(str(self.gitnexus_home.resolve()), kwargs["env"]["TMP"])
        self.assertEqual(str(self.gitnexus_home.resolve()), kwargs["env"]["TEMP"])
        self.assertFalse(result.receipt["authority_invariants"]["automatic_refresh_enabled"])
        self.assertNotIn(str(self.root), json.dumps(result.receipt))

    def test_timeout_and_nonzero_exit_fail_closed(self):
        def timeout_runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

        timed = self.controller(timeout_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual(("failed", "refresh-timeout"), (timed.status, timed.reason))

        def failing_runner(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 9, "", "failure")

        failed = self.controller(failing_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual(("failed", "refresh-exit-9"), (failed.status, failed.reason))

    def test_refresh_preflight_qualification_hash_obeys_total_deadline(self):
        self.executable.write_bytes(b"#!/bin/sh\nexit 0\n" + b"#" * (2 * 1024 * 1024))
        self.executable.chmod(self.executable.stat().st_mode | stat.S_IXUSR)
        self.qualification = fake_qualification(self.executable)
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        ticks = iter((0.0, 0.0, 0.0, 0.0, 0.0, 2.0))
        with (
            mock.patch.object(adapter, "_strict_root", return_value=self.root),
            mock.patch.object(adapter.time, "monotonic", side_effect=lambda: next(ticks, 2.0)),
            self.assertRaisesRegex(adapter.ProbeDeadlineError, "probe-deadline-expired"),
        ):
            self.controller(runner, timeout=1).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_refresh_postcondition_deadline_expiry_fails_closed(self):
        ran = {"value": False}

        def runner(argv, **kwargs):
            ran["value"] = True
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(
            adapter.time,
            "monotonic",
            side_effect=lambda: 2.0 if ran["value"] else 0.0,
        ):
            result = self.controller(runner, timeout=1).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertTrue(ran["value"])
        self.assertEqual(
            ("failed", "postcondition-unknown:ProbeDeadlineError"),
            (result.status, result.reason),
        )
        self.assertFalse(result.receipt["authority_invariants"]["automatic_refresh_enabled"])

    def test_unexpected_tracked_and_protected_mutation_is_preserved_and_rejected(self):
        def mutating_runner(argv, **kwargs):
            (self.root / "AGENTS.md").write_text("mutated by tool\n", encoding="utf-8")
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "", "")

        controller = self.controller(mutating_runner)
        result = controller.refresh(self.repository, expected_head=self.repository.head, explicit_opt_in=True)
        self.assertEqual(("failed", "unexpected-repository-mutation"), (result.status, result.reason))
        self.assertEqual("mutated by tool\n", (self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertFalse(controller.auto_capability_enabled)
        self.assertFalse(result.receipt["authority_invariants"]["repository_restore_performed"])
        self.assertFalse(result.receipt["authority_invariants"]["repository_stage_performed"])

    def test_unexpected_untracked_outside_derived_path_is_rejected(self):
        def mutating_runner(argv, **kwargs):
            (self.root / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "", "")

        result = self.controller(mutating_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual("unexpected-repository-mutation", result.reason)
        self.assertTrue((self.root / "unexpected.txt").exists())

    def test_postcondition_requires_fresh_exact_metadata(self):
        def runner(argv, **kwargs):
            value = valid_metadata(repository_state(self.root))
            value["lastCommit"] = "2" * 40
            write_metadata(self.root, value)
            return subprocess.CompletedProcess(argv, 0, "", "")

        result = self.controller(runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual(("failed", "post-refresh-metadata-stale"), (result.status, result.reason))

    def test_refresh_requires_preexisting_exclusion_and_explicit_isolated_home(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        without_home = adapter.RefreshController(
            self.qualification, enabled=True, lock_directory=self.directory / "locks-no-home", runner=runner
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "GITNEXUS_HOME"):
            without_home.refresh(self.repository, expected_head=self.repository.head, explicit_opt_in=True)

        exclude = self.root / ".git" / "info" / "exclude"
        exclude.write_text("# no adapter-owned mutation\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "already contain"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_derived_index_and_registry_symlinks_or_nonempty_home_fail_before_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        outside = self.directory / "outside-index"
        outside.mkdir()
        (self.root / ".gitnexus").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "derived index root"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        (self.root / ".gitnexus").unlink()

        index = self.root / ".gitnexus"
        index.mkdir()
        (index / "unsafe").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "unsafe entry"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        (index / "unsafe").unlink()
        index.rmdir()

        (self.gitnexus_home / "existing-registry").write_text("state\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "must be empty"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_derived_index_unreadable_directory_fails_closed_deterministically(self):
        index = self.root / ".gitnexus"
        (index / "unreadable").mkdir(parents=True)
        real_scandir = os.scandir
        calls = {"count": 0}

        def deny_second_directory(directory_fd):
            calls["count"] += 1
            if calls["count"] == 2:
                raise PermissionError(errno.EACCES, "denied")
            return real_scandir(directory_fd)

        with (
            mock.patch.object(adapter.os, "scandir", side_effect=deny_second_directory),
            self.assertRaisesRegex(adapter.GitNexusAdapterError, "directory cannot be inspected"),
        ):
            adapter._validate_derived_index_tree(self.root)
        self.assertEqual(2, calls["count"])

    def test_derived_index_delayed_entry_traversal_obeys_deadline(self):
        index = self.root / ".gitnexus"
        index.mkdir()
        for number in range(4):
            (index / f"entry-{number}").write_text("derived\n", encoding="utf-8")
        ticks = iter((*([0.0] * 8), 2.0))
        with (
            mock.patch.object(adapter.time, "monotonic", side_effect=lambda: next(ticks, 2.0)),
            self.assertRaisesRegex(adapter.ProbeDeadlineError, "probe-deadline-expired"),
        ):
            adapter._validate_derived_index_tree(self.root, deadline=1.0)

    def test_effective_ignore_negation_fails_before_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        (self.root / ".gitignore").write_text("!.gitnexus/\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "effectively ignore"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_git_control_mutation_is_preserved_and_rejected(self):
        config = self.root / ".git" / "config"

        def runner(argv, **kwargs):
            config.write_text(f"{config.read_text(encoding='utf-8')}\n# unexpected\n", encoding="utf-8")
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "", "")

        result = self.controller(runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual("unexpected-repository-mutation", result.reason)
        self.assertIn("# unexpected", config.read_text(encoding="utf-8"))

    def test_executable_drift_and_root_symlink_fail_before_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.executable.write_text("#!/bin/sh\n# drift\nexit 0\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "drifted"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        link = self.directory / "repo-link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "non-symlink"):
            adapter.collect_repository_state(link, canonical_repository_id="github.com.Owner.Repository")
        parent_link = self.directory / "parent-link"
        parent_link.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "non-symlink"):
            adapter.collect_repository_state(
                parent_link / "repo", canonical_repository_id="github.com.Owner.Repository"
            )
        self.assertEqual([], calls)


class ProcessAndOperatorTests(unittest.TestCase):
    def test_selector_setup_cleanup_failure_reports_group_cleanup_failure(self):
        process = mock.Mock()
        process.stdout = mock.Mock()
        process.stderr = mock.Mock()
        with (
            mock.patch.object(adapter.subprocess, "Popen", return_value=process),
            mock.patch.object(adapter.selectors, "DefaultSelector", side_effect=OSError("selector failed")),
            mock.patch.object(adapter, "_terminate_process_group", return_value=False),
            self.assertRaisesRegex(adapter.ProcessBoundaryError, "process-group-cleanup-failed"),
        ):
            adapter._bounded_process(
                ["gitnexus", "--version"],
                cwd=pathlib.Path("/"),
                env={},
                timeout=1.0,
                maximum_output_bytes=1024,
            )
        process.stdout.close.assert_called_once_with()
        process.stderr.close.assert_called_once_with()

    def test_normal_exit_still_terminates_and_confirms_descendant_group(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            marker = directory / "normal-exit-late-mutation"
            child = (
                "import pathlib,time; time.sleep(0.4); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            parent = (
                "import subprocess,sys; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}])"
            )
            result = adapter._run_refresh_subprocess(
                [sys.executable, "-c", parent],
                cwd=directory,
                env=os.environ,
                timeout=2.0,
            )
            self.assertEqual(0, result.returncode)
            time.sleep(0.6)
            self.assertFalse(marker.exists())

    def test_live_output_limit_cleans_group_before_return(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            marker = directory / "output-limit-late-mutation"
            child = (
                "import pathlib,time; time.sleep(0.4); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            parent = (
                "import os,subprocess,sys; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
                "\nwhile True: os.write(1,b'x'*4096)"
            )
            with self.assertRaisesRegex(adapter.ProcessBoundaryError, "process-output-limit"):
                adapter._bounded_process(
                    [sys.executable, "-c", parent],
                    cwd=directory,
                    env=os.environ,
                    timeout=2.0,
                    maximum_output_bytes=1024,
                )
            time.sleep(0.6)
            self.assertFalse(marker.exists())

    def test_qualification_default_runner_cleans_descendants_for_both_probes(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            marker = directory / "qualification-late-mutation"
            executable = directory / "gitnexus-descendant-cli"
            child = (
                "import pathlib,time; time.sleep(0.4); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            flags = " ".join(sorted(adapter.REQUIRED_ANALYZE_FLAGS))
            executable.write_text(
                f"#!{sys.executable}\n"
                "import subprocess,sys\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}])\n"
                f"print('GitNexus 1.6.9' if sys.argv[-1] == '--version' else {flags!r})\n",
                encoding="utf-8",
            )
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            qualification = adapter.qualify_executable(executable, timeout_seconds=3)
            self.assertEqual("1.6.9", qualification.version)
            time.sleep(0.6)
            self.assertFalse(marker.exists())

    def test_tracked_file_digest_obeys_the_total_deadline_mid_stream(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            root = make_repo(directory)
            large = root / "large.bin"
            large.write_bytes(b"x" * (2 * 1024 * 1024))
            run_git(root, "add", "large.bin")
            ticks = iter((0.0, 0.0, 0.0, 2.0))
            with (
                mock.patch.object(adapter.time, "monotonic", side_effect=lambda: next(ticks, 2.0)),
                self.assertRaisesRegex(adapter.ProbeDeadlineError, "probe-deadline-expired"),
            ):
                adapter._path_entry(root, "large.bin", deadline=1.0)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = pathlib.Path(self.temp.name).resolve()
        self.root = make_repo(self.directory)
        self.executable = make_executable(self.directory)
        self.qualification = fake_qualification(self.executable)
        self.repository = repository_state(self.root)
        self.gitnexus_home = self.directory / "isolated-gitnexus-home"
        self.gitnexus_home.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def controller(self, runner, *, enabled=True, timeout=10):
        return adapter.RefreshController(
            self.qualification,
            enabled=enabled,
            timeout_seconds=timeout,
            environment={"HOME": str(self.directory)},
            gitnexus_home=self.gitnexus_home,
            lock_directory=self.directory / "locks",
            runner=runner,
        )

    def test_refresh_process_group_is_killed_before_timeout_returns(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw)
            marker = directory / "late-mutation"
            child = (
                "import pathlib,time; time.sleep(0.5); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)"
            )
            with self.assertRaisesRegex(adapter.ProcessBoundaryError, "process-timeout"):
                adapter._run_refresh_subprocess(
                    [sys.executable, "-c", parent],
                    cwd=directory,
                    env=os.environ,
                    timeout=0.1,
                )
            time.sleep(0.7)
            self.assertFalse(marker.exists())

    def test_git_evidence_timeout_and_output_are_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw)
            slow = directory / "slow-git"
            slow.write_text("#!/bin/sh\n/bin/sleep 2\n", encoding="utf-8")
            slow.chmod(slow.stat().st_mode | stat.S_IXUSR)
            with mock.patch.object(adapter, "_git_executable", return_value=str(slow)):
                with self.assertRaisesRegex(adapter.ProcessBoundaryError, "process-timeout"):
                    adapter._run_git(directory, ["status"], deadline=time.monotonic() + 0.1)

            noisy = directory / "noisy-git"
            noisy.write_text("#!/bin/sh\n/usr/bin/printf '0123456789abcdef'\n", encoding="utf-8")
            noisy.chmod(noisy.stat().st_mode | stat.S_IXUSR)
            with (
                mock.patch.object(adapter, "_git_executable", return_value=str(noisy)),
                mock.patch.object(adapter, "MAX_GIT_OUTPUT_BYTES", 8),
                self.assertRaisesRegex(adapter.ProcessBoundaryError, "process-output-limit"),
            ):
                adapter._run_git(directory, ["status"])

    def test_operator_qualify_status_and_disable_are_redacted_and_default_disabled(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            executable = make_cli_executable(directory)
            root = make_repo(directory)
            repository = repository_state(root)
            write_metadata(root, valid_metadata(repository))
            with mock.patch("builtins.print") as printer:
                self.assertEqual(0, adapter.operator_main(["qualify", "--executable", str(executable)]))
                qualified = json.loads(printer.call_args.args[0])
            self.assertEqual("qualified", qualified["status"])
            self.assertNotIn(str(executable), json.dumps(qualified))

            arguments = [
                "status", "--executable", str(executable), "--repo-root", str(root),
                "--repository-id", "github.com.Owner.Repository",
                "--expected-remote", "https://github.com/Owner/Repository.git",
            ]
            with mock.patch("builtins.print") as printer:
                self.assertEqual(0, adapter.operator_main(arguments))
                status = json.loads(printer.call_args.args[0])
            self.assertEqual("fresh", status["status"])
            self.assertEqual("disabled", status["handshake"]["status"])
            self.assertNotIn(str(root), json.dumps(status))

            invalid = valid_metadata(repository)
            invalid["cacheKeys"] = [{"nested": []}]
            write_metadata(root, invalid)
            with mock.patch("builtins.print") as printer:
                self.assertEqual(0, adapter.operator_main(arguments))
                rejected = json.loads(printer.call_args.args[0])
            self.assertEqual(
                ("corrupt", "metadata-cache-keys-invalid"),
                (rejected["status"], rejected["reason"]),
            )

            with mock.patch("builtins.print") as printer:
                self.assertEqual(0, adapter.operator_main(["disable"]))
                disabled = json.loads(printer.call_args.args[0])
            self.assertEqual("disabled", disabled["status"])
            self.assertFalse(disabled["repository_write_performed"])

    def test_operator_os_error_is_stable_and_path_redacted(self):
        secret_path = "/machine-local/private/gitnexus"
        with (
            mock.patch.object(
                adapter,
                "_qualification_from_arguments",
                side_effect=OSError(errno.ENOENT, "missing", secret_path),
            ),
            mock.patch("builtins.print") as printer,
        ):
            self.assertEqual(2, adapter.operator_main(["qualify"]))
        result = json.loads(printer.call_args.args[0])
        self.assertEqual("os-enoent", result["error_code"])
        self.assertEqual("operation-failed", result["error"])
        self.assertNotIn(secret_path, json.dumps(result))

    def test_concurrent_lock_and_linked_worktree_boundary_fail_before_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        lock_directory = self.directory / "shared-locks"
        with adapter._root_lock(self.repository.root, lock_directory):
            controller = adapter.RefreshController(
                self.qualification,
                enabled=True,
                gitnexus_home=self.gitnexus_home,
                lock_directory=lock_directory,
                runner=runner,
            )
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "already holds"):
                controller.refresh(
                    self.repository, expected_head=self.repository.head, explicit_opt_in=True
                )

        linked = self.directory / "linked-worktree"
        run_git(self.root, "worktree", "add", "-b", "linked", str(linked))
        linked_state = repository_state(linked)
        linked_home = self.directory / "linked-home"
        linked_home.mkdir()
        linked_controller = adapter.RefreshController(
            self.qualification,
            enabled=True,
            gitnexus_home=linked_home,
            lock_directory=self.directory / "linked-locks",
            runner=runner,
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "linked-worktree"):
            linked_controller.refresh(
                linked_state, expected_head=linked_state.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

    def test_isolated_home_parent_symlink_and_control_file_symlink_are_rejected(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        parent_link = self.directory / "home-parent-link"
        parent_link.symlink_to(self.directory, target_is_directory=True)
        unsafe_home_controller = adapter.RefreshController(
            self.qualification,
            enabled=True,
            gitnexus_home=parent_link / self.gitnexus_home.name,
            lock_directory=self.directory / "home-link-locks",
            runner=runner,
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "non-symlink"):
            unsafe_home_controller.refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )

        exclude = self.root / ".git" / "info" / "exclude"
        outside = self.directory / "outside-exclude"
        outside.write_text(".gitnexus/\n", encoding="utf-8")
        exclude.unlink()
        exclude.symlink_to(outside)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "exclude control file"):
            self.controller(runner).refresh(
                self.repository, expected_head=self.repository.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)


if __name__ == "__main__":
    unittest.main()
