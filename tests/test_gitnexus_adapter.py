from __future__ import annotations

import copy
import datetime as dt
import errno
import importlib.util
import json
import os
import pathlib
import shutil
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
    package = directory / "gitnexus-package"
    package.mkdir(exist_ok=True)
    path = package / "gitnexus"
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def make_cli_executable(directory: pathlib.Path) -> pathlib.Path:
    package = directory / "gitnexus-cli-package"
    package.mkdir(exist_ok=True)
    path = package / "gitnexus-cli"
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


def provenance_kwargs(
    executable: pathlib.Path,
    *,
    runtime_path: pathlib.Path | None = None,
    allow_symlink: bool = False,
    allow_runtime_symlink: bool = False,
) -> dict:
    resolved, _ = adapter.discover_executable(
        executable, allow_symlink=allow_symlink
    )
    runtime = adapter._script_runtime(
        resolved, runtime_path, allow_symlink=allow_runtime_symlink
    )
    package_digest, _ = adapter._package_tree_identity(resolved.parent)
    return {
        "package_root": resolved.parent,
        "accepted_executable_sha256": adapter._executable_identity(resolved)[0],
        "accepted_package_sha256": package_digest,
        "accepted_runtime_sha256": runtime[1] if runtime else None,
    }


def provenance_cli_args(executable: pathlib.Path) -> list[str]:
    trusted = provenance_kwargs(executable)
    arguments = [
        "--package-root",
        str(trusted["package_root"]),
        "--accepted-executable-sha256",
        trusted["accepted_executable_sha256"],
        "--accepted-package-sha256",
        trusted["accepted_package_sha256"],
    ]
    if trusted["accepted_runtime_sha256"] is not None:
        arguments.extend(
            ["--accepted-runtime-sha256", trusted["accepted_runtime_sha256"]]
        )
    return arguments


def fake_qualification(executable: pathlib.Path) -> adapter.ExecutableQualification:
    def runner(argv, **kwargs):
        output = (
            "GitNexus 1.6.9"
            if argv[-1] == "--version"
            else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
        )
        return subprocess.CompletedProcess(argv, 0, output, "")

    return adapter.qualify_executable(
        executable,
        runner=runner,
        **provenance_kwargs(executable),
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
    def test_gitnexus_executable_path_is_explicit_and_ambient_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            fake = make_cli_executable(directory)
            with mock.patch.dict(os.environ, {"PATH": str(directory)}, clear=False):
                with self.assertRaisesRegex(
                    adapter.GitNexusAdapterError,
                    "explicit GitNexus executable path is required",
                ):
                    adapter.qualify_executable(None)
            self.assertTrue(fake.exists())

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

            trusted = provenance_kwargs(executable)
            first = adapter.qualify_executable(executable, runner=runner, environment={"HOME": raw, "PATH": "/unsafe", "GIT_DIR": "/unsafe"}, **trusted)
            second = adapter.qualify_executable(executable, runner=runner, environment={"HOME": raw}, **trusted)
            self.assertEqual(first.fingerprint, second.fingerprint)
            resolved = str(executable.resolve())
            interpreter = str(first.runtime_executable)
            self.assertEqual([[interpreter, resolved, "--version"], [interpreter, resolved, "analyze", "--help"]], [item[0] for item in calls[:2]])
            self.assertEqual({"HOME": raw}, calls[0][1]["env"])
            self.assertNotIn("shell", calls[0][1])

    def test_caller_owned_package_provenance_is_required_before_execution_and_rechecked(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            executable = make_executable(directory)
            dependency = executable.parent / "dependency.js"
            dependency.write_text("export const value = 1;\n", encoding="utf-8")
            calls = []

            def runner(argv, **kwargs):
                calls.append(argv)
                output = (
                    "GitNexus 1.6.9"
                    if argv[-1] == "--version"
                    else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                )
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "caller-owned.*sha256"
            ):
                adapter.qualify_executable(executable, runner=runner)
            self.assertEqual([], calls)

            trusted = provenance_kwargs(executable)
            qualification = adapter.qualify_executable(
                executable, runner=runner, **trusted
            )
            self.assertEqual(2, len(calls))
            self.assertRegex(qualification.trusted_provenance_digest or "", r"^[0-9a-f]{64}$")

            dependency.write_text("export const value = 2;\n", encoding="utf-8")
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "package tree drifted"
            ):
                adapter.verify_qualification(qualification)

            calls.clear()
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "package tree does not match"
            ):
                adapter.qualify_executable(executable, runner=runner, **trusted)
            self.assertEqual([], calls)

    def test_package_tree_symlinks_are_confined_and_file_only(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            target = package / "target.js"
            target.write_text("export const value = 1;\n", encoding="utf-8")

            contained = package / "contained.js"
            contained.symlink_to("target.js")
            digest, _ = adapter._package_tree_identity(package)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

            contained.unlink()
            contained.symlink_to(target)
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "target must be relative"
            ):
                adapter._package_tree_identity(package)

            contained.unlink()
            outside = directory / "outside.js"
            outside.write_text("outside\n", encoding="utf-8")
            contained.symlink_to("../outside.js")
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "stay inside the package root"
            ):
                adapter._package_tree_identity(package)

            contained.unlink()
            subdirectory = package / "subdirectory"
            subdirectory.mkdir()
            contained.symlink_to("subdirectory", target_is_directory=True)
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "target a regular file"
            ):
                adapter._package_tree_identity(package)

    def test_package_tree_rejects_regular_file_swap_to_symlink_before_open(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            target = package / "target.js"
            target.write_text("trusted\n", encoding="utf-8")
            outside = directory / "outside.js"
            outside.write_text("outside\n", encoding="utf-8")
            real_open = os.open
            swapped = False

            def racing_open(path, flags, *args, **kwargs):
                nonlocal swapped
                if (
                    not swapped
                    and path == "target.js"
                    and kwargs.get("dir_fd") is not None
                    and not flags & getattr(os, "O_DIRECTORY", 0)
                ):
                    swapped = True
                    target.unlink()
                    target.symlink_to(outside)
                return real_open(path, flags, *args, **kwargs)

            with (
                mock.patch.object(adapter.os, "open", side_effect=racing_open),
                self.assertRaisesRegex(
                    adapter.GitNexusAdapterError, "cannot be opened safely"
                ),
            ):
                adapter._package_tree_identity(package)
            self.assertTrue(swapped)

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

            parent = directory / "parent"
            parent.mkdir()
            parent_executable = make_executable(parent)
            parent_link = directory / "parent-link"
            parent_link.symlink_to(parent, target_is_directory=True)
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "parent path"):
                adapter.discover_executable(parent_link / parent_executable.relative_to(parent))

            second_link = directory / "second-link"
            second_link.symlink_to(link)
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "only one"):
                adapter.discover_executable(second_link, allow_symlink=True)

            def version_drift(argv, **kwargs):
                output = "GitNexus 1.7.0" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "exact version"):
                adapter.qualify_executable(
                    executable, runner=version_drift, **provenance_kwargs(executable)
                )

            def flag_drift(argv, **kwargs):
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else "--index-only"
                return subprocess.CompletedProcess(argv, 0, output, "")

            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "flags"):
                adapter.qualify_executable(
                    executable, runner=flag_drift, **provenance_kwargs(executable)
                )

    def test_env_node_launcher_is_discovered_bound_and_used_without_inherited_path(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            executable = package / "gitnexus-entry.js"
            executable.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            node = directory / "node"
            node.write_bytes(b"\x7fELF-test-node-v1")
            node.chmod(node.stat().st_mode | stat.S_IXUSR)
            calls = []

            def runner(argv, **kwargs):
                calls.append((argv, kwargs))
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            qualification = adapter.qualify_executable(
                executable,
                runtime_path=node,
                runner=runner,
                environment={"HOME": raw, "PATH": raw},
                **provenance_kwargs(executable, runtime_path=node),
            )
            self.assertEqual(node.resolve(), qualification.runtime_executable)
            self.assertEqual("regular-file-only", qualification.runtime_symlink_policy)
            self.assertEqual([str(node.resolve()), str(executable.resolve()), "--version"], calls[0][0])
            self.assertEqual({"HOME": raw}, calls[0][1]["env"])
            node.write_bytes(b"\x7fELF-test-node-v2-drift")
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "runtime executable drifted"):
                adapter.verify_qualification(qualification)

    def test_env_dash_s_node_is_explicitly_bound_and_other_env_forms_reject(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            executable = package / "gitnexus-entry.js"
            executable.write_text("#!/usr/bin/env -S node\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            node = directory / "node"
            node.write_bytes(b"\x7fELF-test-node")
            node.chmod(node.stat().st_mode | stat.S_IXUSR)
            calls = []

            def runner(argv, **kwargs):
                calls.append(argv)
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            qualification = adapter.qualify_executable(
                executable,
                runtime_path=node,
                runner=runner,
                environment={"HOME": raw},
                **provenance_kwargs(executable, runtime_path=node),
            )
            self.assertEqual(node, qualification.runtime_executable)
            self.assertEqual([str(node), str(executable), "--version"], calls[0])

            executable.write_text(
                "#!/usr/bin/env -S node --unqualified-option\n",
                encoding="utf-8",
            )
            calls.clear()
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "env launcher"):
                adapter.qualify_executable(
                    executable,
                    runtime_path=node,
                    runner=runner,
                    environment={"HOME": raw},
                    **provenance_kwargs(executable, runtime_path=node),
                )
            self.assertEqual([], calls)

    def test_node_final_symlink_policy_is_fingerprint_bound(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            executable = package / "gitnexus-entry.js"
            executable.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            node = directory / "node-real"
            node.write_bytes(b"\x7fELF-test-node")
            node.chmod(node.stat().st_mode | stat.S_IXUSR)
            node_link = directory / "node-link"
            node_link.symlink_to(node)

            def runner(argv, **kwargs):
                output = "GitNexus 1.6.9" if argv[-1] == "--version" else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                return subprocess.CompletedProcess(argv, 0, output, "")

            direct = adapter.qualify_executable(
                executable, runtime_path=node, runner=runner, environment={"HOME": raw},
                **provenance_kwargs(executable, runtime_path=node)
            )
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "symlink"):
                adapter.qualify_executable(
                    executable,
                    runtime_path=node_link,
                    runner=runner,
                    environment={"HOME": raw},
                    **provenance_kwargs(executable, runtime_path=node),
                )
            linked = adapter.qualify_executable(
                executable,
                runtime_path=node_link,
                allow_runtime_symlink=True,
                runner=runner,
                environment={"HOME": raw},
                **provenance_kwargs(
                    executable,
                    runtime_path=node_link,
                    allow_runtime_symlink=True,
                ),
            )
            self.assertEqual("regular-file-only", direct.runtime_symlink_policy)
            self.assertEqual("resolved-symlink", linked.runtime_symlink_policy)
            self.assertNotEqual(direct.fingerprint, linked.fingerprint)

    def test_env_node_launcher_requires_explicit_runtime_path(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            package = directory / "package"
            package.mkdir()
            executable = package / "gitnexus-entry.js"
            executable.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
            node = directory / "node"
            node.write_bytes(b"\x7fELF-test-node")
            node.chmod(node.stat().st_mode | stat.S_IXUSR)
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError,
                "explicit Node executable path is required",
            ):
                adapter.qualify_executable(
                    executable,
                    runner=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
                    environment={"HOME": raw, "PATH": raw},
                    package_root=package,
                    accepted_executable_sha256=adapter._executable_identity(executable)[0],
                    accepted_package_sha256=adapter._package_tree_identity(package)[0],
                )

    def test_direct_script_interpreter_is_bound_and_symlink_retarget_is_not_followed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            first = directory / "runtime-first"
            second = directory / "runtime-second"
            first.write_bytes(b"\x7fELF-runtime-first")
            second.write_bytes(b"\x7fELF-runtime-second")
            first.chmod(0o700)
            second.chmod(0o700)
            launcher = directory / "runtime-link"
            launcher.symlink_to(first)
            package = directory / "package"
            package.mkdir()
            executable = package / "gitnexus-entry"
            executable.write_text(f"#!{launcher}\n", encoding="utf-8")
            executable.chmod(0o700)
            calls = []

            def runner(argv, **kwargs):
                calls.append(argv)
                output = (
                    "GitNexus 1.6.9"
                    if argv[-1] == "--version"
                    else " ".join(adapter.REQUIRED_ANALYZE_FLAGS)
                )
                return subprocess.CompletedProcess(argv, 0, output, "")

            qualification = adapter.qualify_executable(
                executable, runner=runner, environment={"HOME": raw},
                **provenance_kwargs(executable)
            )
            self.assertEqual(first, qualification.runtime_executable)
            self.assertEqual("bound-shebang", qualification.runtime_launcher)
            launcher.unlink()
            launcher.symlink_to(second)
            adapter.verify_qualification(qualification)
            self.assertEqual(str(first), calls[0][0])


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

    def test_repository_state_rejects_non_commit_head(self):
        fake_head = "a" * 40
        (self.root / ".git" / "refs" / "heads" / "main").write_text(
            fake_head + "\n", encoding="ascii"
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "rev-parse|git"):
            repository_state(self.root)

    def test_repository_state_rejects_enclosing_core_worktree_alias(self):
        outer = self.directory / "outer"
        nested = outer / "nested"
        subprocess.run(["git", "init", "-q", "-b", "main", str(outer)], check=True)
        nested.mkdir()
        subprocess.run(
            ["git", "-C", str(outer), "config", "--local", "core.worktree", str(nested)],
            check=True,
        )
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "local .git marker"):
            adapter.collect_repository_state(
                nested,
                canonical_repository_id="github.com.Owner.Repository",
            )
        (nested / ".git").write_text("gitdir: ../.git\n", encoding="utf-8")
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "local .git marker"):
            adapter.collect_repository_state(
                nested,
                canonical_repository_id="github.com.Owner.Repository",
            )

    def test_git_environment_disables_promisor_lazy_fetch(self):
        self.assertEqual("1", adapter._git_environment()["GIT_NO_LAZY_FETCH"])

    def test_repository_local_content_filter_is_rejected_before_execution(self):
        marker = self.directory / "filter-executed"
        filter_program = self.directory / "clean-filter"
        filter_program.write_text(
            "#!/bin/sh\n"
            f"/usr/bin/touch {marker}\n"
            "/bin/cat\n",
            encoding="utf-8",
        )
        filter_program.chmod(filter_program.stat().st_mode | stat.S_IXUSR)
        (self.root / ".gitattributes").write_text(
            "code.py filter=demo\n", encoding="utf-8"
        )
        run_git(self.root, "config", "--local", "filter.demo.clean", str(filter_program))
        (self.root / "code.py").write_text("changed\n", encoding="utf-8")

        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError,
            "filter/include configuration is unsupported",
        ):
            adapter.collect_tracked_snapshot(self.root)
        self.assertFalse(marker.exists())

    def test_repository_local_config_include_is_rejected_without_reading_filter(self):
        included = self.directory / "external-config"
        included.write_text(
            "[filter \"demo\"]\n\tclean = /machine-local/not-executed\n",
            encoding="utf-8",
        )
        run_git(self.root, "config", "--local", "include.path", str(included))
        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError,
            "filter/include configuration is unsupported",
        ):
            adapter.collect_tracked_snapshot(self.root)

    def test_worktree_scoped_filter_is_rejected_before_execution(self):
        marker = self.directory / "worktree-filter-executed"
        filter_program = self.directory / "worktree-clean-filter"
        filter_program.write_text(
            "#!/bin/sh\n"
            f"/usr/bin/touch {marker}\n"
            "/bin/cat\n",
            encoding="utf-8",
        )
        filter_program.chmod(0o700)
        (self.root / ".gitattributes").write_text(
            "code.py filter=worktree-demo\n", encoding="utf-8"
        )
        run_git(self.root, "config", "--local", "extensions.worktreeConfig", "true")
        run_git(
            self.root,
            "config",
            "--worktree",
            "filter.worktree-demo.clean",
            str(filter_program),
        )
        (self.root / "code.py").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError,
            "filter/include configuration is unsupported",
        ):
            adapter.collect_tracked_snapshot(self.root)
        self.assertFalse(marker.exists())

    def test_explicit_native_git_is_propagated_and_script_wrapper_is_rejected(self):
        real_git_text = shutil.which("git", path=os.defpath)
        self.assertIsNotNone(real_git_text)
        real_git = pathlib.Path(real_git_text).resolve(strict=True)
        wrapper = self.directory / "operator-selected-git"
        wrapper.write_text(
            f"#!{sys.executable}\n"
            "import os, pathlib, sys\n"
            f"os.execv({str(real_git)!r}, [{str(real_git)!r}, *sys.argv[1:]])\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        fake_directory = self.directory / "ambient"
        fake_directory.mkdir()
        fake_git = fake_directory / "git"
        fake_git.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        fake_git.chmod(fake_git.stat().st_mode | stat.S_IXUSR)

        with mock.patch.dict(
            os.environ,
            {"PATH": str(fake_directory), "CODEX_LOOP_GIT_EXECUTABLE": str(fake_git)},
            clear=False,
        ):
            with self.assertRaisesRegex(adapter.GitNexusAdapterError, "bound safely"):
                adapter.collect_repository_state(
                    self.root,
                    canonical_repository_id="github.com.Owner.Repository",
                    expected_remote="https://github.com/Owner/Repository.git",
                    git_executable=wrapper,
                )
            repository = adapter.collect_repository_state(
                self.root,
                canonical_repository_id="github.com.Owner.Repository",
                expected_remote="https://github.com/Owner/Repository.git",
                git_executable=real_git,
            )
            snapshot = adapter.collect_tracked_snapshot(
                self.root,
                git_executable=real_git,
            )

        self.assertEqual(self.repository.head, repository.head)
        self.assertEqual(self.repository.branch, repository.branch)
        self.assertFalse(snapshot.tracked_dirty)

    def test_repository_state_rejects_head_branch_change_between_observations(self):
        run_git(self.root, "switch", "-q", "-c", "other")
        (self.root / "code.py").write_text("print('other')\n", encoding="utf-8")
        run_git(self.root, "add", "code.py")
        run_git(self.root, "commit", "-m", "other branch")
        run_git(self.root, "switch", "-q", "main")
        original_run_git = adapter._run_git
        head_probes = 0

        def switch_after_first_head(root, args, **kwargs):
            nonlocal head_probes
            result = original_run_git(root, args, **kwargs)
            if args == ["rev-parse", "--verify", "HEAD^{commit}"]:
                head_probes += 1
                if head_probes == 1:
                    run_git(self.root, "switch", "-q", "other")
            return result

        with (
            mock.patch.object(adapter, "_run_git", side_effect=switch_after_first_head),
            self.assertRaisesRegex(
                adapter.GitNexusAdapterError,
                "repository identity changed during collection",
            ),
        ):
            repository_state(self.root)
        self.assertEqual(2, head_probes)

    def test_snapshot_uses_no_replace_semantics_for_head_tree(self):
        original_head = self.repository.head
        run_git(self.root, "switch", "-q", "-c", "replacement-target")
        (self.root / "code.py").write_text("print('replacement')\n", encoding="utf-8")
        run_git(self.root, "add", "code.py")
        run_git(self.root, "commit", "-m", "replacement tree")
        replacement_head = run_git(self.root, "rev-parse", "HEAD").stdout.decode().strip()
        run_git(self.root, "switch", "-q", "main")
        run_git(self.root, "checkout", replacement_head, "--", "code.py")
        run_git(self.root, "replace", original_head, replacement_head)

        # Ordinary Git replacement semantics make this tree appear clean.  The
        # adapter must compare against the real HEAD object and fail closed.
        self.assertEqual(b"", run_git(self.root, "status", "--porcelain=v1").stdout)
        snapshot = adapter.collect_tracked_snapshot(self.root)
        self.assertTrue(snapshot.tracked_dirty)

    def test_snapshot_filesystem_integers_are_canonical_strings(self):
        large = (1 << 63) + 123
        self.assertEqual(str(large), adapter._snapshot_integer(large))
        self.assertEqual("-1000000000", adapter._snapshot_integer(-1000000000, signed=True))
        for invalid in (-1, True, 1.5):
            with self.subTest(invalid=invalid), self.assertRaises(
                adapter.GitNexusAdapterError
            ):
                adapter._snapshot_integer(invalid)

    def test_complete_tree_snapshot_enforces_file_and_depth_bounds(self):
        bounded = self.directory / "bounded-tree"
        bounded.mkdir()
        (bounded / "file.txt").write_text("bounded\n", encoding="utf-8")
        with (
            mock.patch.object(adapter, "MAX_SNAPSHOT_FILE_BYTES", 0),
            self.assertRaisesRegex(adapter.GitNexusAdapterError, "file exceeds"),
        ):
            adapter._filesystem_tree_digest(bounded)

        with (
            mock.patch.object(adapter, "MAX_SNAPSHOT_ENTRIES", 0),
            self.assertRaisesRegex(adapter.GitNexusAdapterError, "entry count exceeds"),
        ):
            adapter._filesystem_tree_digest(bounded)

        (bounded / "nested").mkdir()
        with (
            mock.patch.object(adapter, "MAX_SNAPSHOT_DEPTH", 0),
            self.assertRaisesRegex(adapter.GitNexusAdapterError, "depth exceeds"),
        ):
            adapter._filesystem_tree_digest(bounded)

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

    def controller(self, runner, *, enabled=True, timeout=10, git_executable=None):
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
            git_executable=git_executable,
            runner=runner,
        )

    def test_explicit_native_git_is_used_across_refresh_pre_and_postconditions(self):
        real_git_text = shutil.which("git", path=os.defpath)
        self.assertIsNotNone(real_git_text)
        real_git = pathlib.Path(real_git_text).resolve(strict=True)
        def runner(argv, **kwargs):
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, b"", b"")

        result = self.controller(
            runner,
            git_executable=real_git,
        ).refresh(
            self.repository,
            expected_head=self.repository.head,
            explicit_opt_in=True,
        )
        self.assertEqual("refreshed", result.status)

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

    def test_refresh_rejects_snapshot_head_branch_race_before_runner(self):
        run_git(self.root, "switch", "-q", "-c", "other")
        (self.root / "code.py").write_text("print('other')\n", encoding="utf-8")
        run_git(self.root, "add", "code.py")
        run_git(self.root, "commit", "-m", "other branch")
        run_git(self.root, "switch", "-q", "main")
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, "", "")

        original_snapshot = adapter.collect_tracked_snapshot
        raced = False

        def snapshot_with_race(*args, **kwargs):
            nonlocal raced
            original_run_git = adapter._run_git

            def switch_after_head(root, git_args, **git_kwargs):
                nonlocal raced
                result = original_run_git(root, git_args, **git_kwargs)
                if (
                    not raced
                    and git_args == ["rev-parse", "--verify", "HEAD^{commit}"]
                ):
                    raced = True
                    run_git(self.root, "switch", "-q", "other")
                return result

            with mock.patch.object(adapter, "_run_git", side_effect=switch_after_head):
                return original_snapshot(*args, **kwargs)

        with (
            mock.patch.object(
                adapter, "collect_tracked_snapshot", side_effect=snapshot_with_race
            ),
            self.assertRaisesRegex(
                adapter.GitNexusAdapterError,
                "repository identity changed during snapshot",
            ),
        ):
            self.controller(runner).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertTrue(raced)
        self.assertEqual([], calls)

    def test_refresh_rechecks_state_after_final_qualification_before_runner(self):
        run_git(self.root, "switch", "-q", "-c", "other")
        (self.root / "code.py").write_text("print('other')\n", encoding="utf-8")
        run_git(self.root, "add", "code.py")
        run_git(self.root, "commit", "-m", "other branch")
        run_git(self.root, "switch", "-q", "main")
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, "", "")

        original_verify = adapter.verify_qualification
        qualification_checks = 0

        def switch_during_final_qualification(*args, **kwargs):
            nonlocal qualification_checks
            qualification_checks += 1
            if qualification_checks == 2:
                run_git(self.root, "switch", "-q", "other")
            return original_verify(*args, **kwargs)

        with (
            mock.patch.object(
                adapter,
                "verify_qualification",
                side_effect=switch_during_final_qualification,
            ),
            self.assertRaisesRegex(
                adapter.GitNexusAdapterError,
                "refresh repository state changed during preflight",
            ),
        ):
            self.controller(runner).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertEqual(2, qualification_checks)
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
        self.assertEqual(
            [str(self.qualification.runtime_executable), str(self.executable), "analyze", "--index-only", "--name"],
            argv[:5],
        )
        self.assertEqual(7, len(argv))
        self.assertEqual(str(self.repository.root), argv[-1])
        self.assertNotIn("shell", kwargs)
        self.assertEqual("never", kwargs["env"]["GITNEXUS_LBUG_EXTENSION_INSTALL"])
        self.assertEqual("3", kwargs["env"]["GIT_CONFIG_COUNT"])
        self.assertEqual("core.fsmonitor", kwargs["env"]["GIT_CONFIG_KEY_0"])
        self.assertEqual("false", kwargs["env"]["GIT_CONFIG_VALUE_0"])
        self.assertEqual("core.hooksPath", kwargs["env"]["GIT_CONFIG_KEY_1"])
        self.assertEqual("/dev/null", kwargs["env"]["GIT_CONFIG_VALUE_1"])
        self.assertEqual("core.untrackedCache", kwargs["env"]["GIT_CONFIG_KEY_2"])
        self.assertEqual("false", kwargs["env"]["GIT_CONFIG_VALUE_2"])
        self.assertEqual("1", kwargs["env"]["GIT_CONFIG_NOSYSTEM"])
        self.assertEqual("/dev/null", kwargs["env"]["GIT_CONFIG_GLOBAL"])
        self.assertEqual("1", kwargs["env"]["GIT_NO_LAZY_FETCH"])
        self.assertEqual("1", kwargs["env"]["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("0", kwargs["env"]["GIT_OPTIONAL_LOCKS"])
        self.assertEqual("0", kwargs["env"]["GIT_TERMINAL_PROMPT"])
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

    def test_isolated_home_requires_private_mode_and_effective_user_owner(self):
        self.gitnexus_home.chmod(0o777)
        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError, "group- or world-writable"
        ):
            adapter._capture_isolated_home_identity(self.gitnexus_home)

        self.gitnexus_home.chmod(0o700)
        if hasattr(os, "geteuid") and hasattr(self.gitnexus_home.stat(), "st_uid"):
            wrong_effective_uid = self.gitnexus_home.stat().st_uid + 1
            with (
                mock.patch.object(adapter.os, "geteuid", return_value=wrong_effective_uid),
                self.assertRaisesRegex(
                    adapter.GitNexusAdapterError, "owned by the effective user"
                ),
            ):
                adapter._capture_isolated_home_identity(self.gitnexus_home)

    def test_isolated_home_replacement_after_empty_check_fails_before_runner(self):
        calls = []
        displaced = self.directory / "displaced-isolated-home"
        original_empty_check = adapter._require_empty_isolated_home_descriptor
        checks = 0

        def replace_after_empty_check(descriptor):
            nonlocal checks
            original_empty_check(descriptor)
            checks += 1
            if checks == 1:
                self.gitnexus_home.rename(displaced)
                self.gitnexus_home.mkdir(mode=0o700)

        with (
            mock.patch.object(
                adapter,
                "_require_empty_isolated_home_descriptor",
                side_effect=replace_after_empty_check,
            ),
            self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "identity changed during refresh"
            ),
        ):
            self.controller(lambda argv, **kwargs: calls.append(argv)).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertEqual([], calls)

    def test_same_inode_contamination_before_runner_fails_closed(self):
        calls = []
        home_descriptor = os.open(
            self.gitnexus_home, os.O_RDONLY | os.O_DIRECTORY
        )
        original_verify = adapter.verify_qualification
        checks = 0

        def contaminate_after_resource_acquisition(*args, **kwargs):
            nonlocal checks
            checks += 1
            result = original_verify(*args, **kwargs)
            if checks == 2:
                descriptor = os.open(
                    "same-inode-contamination",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=home_descriptor,
                )
                os.close(descriptor)
            return result

        try:
            with (
                mock.patch.object(
                    adapter,
                    "verify_qualification",
                    side_effect=contaminate_after_resource_acquisition,
                ),
                self.assertRaisesRegex(
                    adapter.GitNexusAdapterError, "must be empty"
                ),
            ):
                self.controller(lambda argv, **kwargs: calls.append(argv)).refresh(
                    self.repository,
                    expected_head=self.repository.head,
                    explicit_opt_in=True,
                )
        finally:
            os.close(home_descriptor)
        self.assertEqual(2, checks)
        self.assertEqual([], calls)

    def test_isolated_home_replacement_during_runner_blocks_adoption(self):
        displaced = self.directory / "runner-displaced-isolated-home"

        def runner(argv, **kwargs):
            self.gitnexus_home.rename(displaced)
            self.gitnexus_home.mkdir(mode=0o700)
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "indexed", "")

        result = self.controller(runner).refresh(
            self.repository,
            expected_head=self.repository.head,
            explicit_opt_in=True,
        )
        self.assertEqual(
            ("failed", "postcondition-unknown:GitNexusAdapterError"),
            (result.status, result.reason),
        )
        self.assertFalse(result.receipt["authority_invariants"]["automatic_refresh_enabled"])

    def test_descendant_git_status_cannot_execute_repo_fsmonitor(self):
        marker = self.directory / "fsmonitor-executed"
        hook = self.directory / "fsmonitor.py"
        hook.write_text(
            f"#!{sys.executable}\n"
            "import pathlib\n"
            f"pathlib.Path({str(marker)!r}).write_text('executed\\n', encoding='utf-8')\n"
            "print('0')\n",
            encoding="utf-8",
        )
        hook.chmod(0o700)
        subprocess.run(
            ["git", "-C", str(self.root), "config", "core.fsmonitor", str(hook)],
            check=True,
        )

        def runner(argv, **kwargs):
            self.assertFalse(marker.exists())
            status = subprocess.run(
                ["git", "-C", str(self.root), "status", "--porcelain"],
                check=False,
                capture_output=True,
                env=kwargs["env"],
                text=True,
            )
            self.assertEqual(0, status.returncode)
            self.assertFalse(marker.exists())
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "indexed", "")

        result = self.controller(runner).refresh(
            self.repository,
            expected_head=self.repository.head,
            explicit_opt_in=True,
        )
        self.assertEqual("refreshed", result.status)
        self.assertFalse(marker.exists())

    def test_case_variant_tracked_derived_alias_fails_before_execution(self):
        tracked = self.root / ".GitNexus"
        tracked.mkdir()
        for name in ("gitnexus.json", "meta.json"):
            (tracked / name).write_text("tracked\n", encoding="utf-8")
        run_git(
            self.root,
            "add",
            "-f",
            ".GitNexus/gitnexus.json",
            ".GitNexus/meta.json",
        )
        run_git(self.root, "commit", "-m", "track case-variant derived paths")
        self.repository = repository_state(self.root)
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        real_samefile = pathlib.Path.samefile

        def case_insensitive_samefile(left, right):
            if left.name == ".GitNexus" and right.name == ".gitnexus":
                return True
            return real_samefile(left, right)

        with (
            mock.patch.object(
                pathlib.Path,
                "samefile",
                autospec=True,
                side_effect=case_insensitive_samefile,
            ),
            self.assertRaisesRegex(adapter.GitNexusAdapterError, "derived index"),
        ):
            self.controller(runner).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertEqual([], calls)

    def test_missing_case_variant_tracked_alias_fails_before_execution(self):
        tracked = self.root / ".GitNexus"
        tracked.mkdir()
        tracked_paths = []
        for name in ("gitnexus.json", "meta.json"):
            (tracked / name).write_text("tracked\n", encoding="utf-8")
            tracked_paths.append(f".GitNexus/{name}")
        run_git(self.root, "add", "-f", *tracked_paths)
        run_git(self.root, "commit", "-m", "track missing case-variant paths")
        run_git(self.root, "update-index", "--skip-worktree", *tracked_paths)
        for name in ("gitnexus.json", "meta.json"):
            (tracked / name).unlink()
        tracked.rmdir()
        self.repository = repository_state(self.root)
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "derived index"):
            self.controller(runner).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertEqual([], calls)

    def test_timeout_and_nonzero_exit_fail_closed(self):
        def timeout_runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

        timed = self.controller(timeout_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual(("failed", "refresh-timeout"), (timed.status, timed.reason))

        def recovery_runner(argv, **kwargs):
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "indexed", "")

        recovered = self.controller(recovery_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual("refreshed", recovered.status)

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

    def test_ignored_worktree_and_git_admin_mutations_are_preserved_and_rejected(self):
        exclude = self.root / ".git" / "info" / "exclude"
        exclude.write_text(
            f"{exclude.read_text(encoding='utf-8')}\nignored-user.txt\n",
            encoding="utf-8",
        )
        ignored = self.root / "ignored-user.txt"
        ignored.write_text("user data\n", encoding="utf-8")
        admin = self.root / ".git" / "hooks" / "unexpected-admin-state"

        def mutating_runner(argv, **kwargs):
            ignored.write_text("mutated\n", encoding="utf-8")
            admin.write_text("unexpected\n", encoding="utf-8")
            write_metadata(self.root, valid_metadata(repository_state(self.root)))
            return subprocess.CompletedProcess(argv, 0, "indexed", "")

        result = self.controller(mutating_runner).refresh(
            self.repository, expected_head=self.repository.head, explicit_opt_in=True
        )
        self.assertEqual(
            ("failed", "unexpected-repository-mutation"),
            (result.status, result.reason),
        )
        self.assertEqual("mutated\n", ignored.read_text(encoding="utf-8"))
        self.assertTrue(admin.is_file())

    def test_refresh_rejects_tampered_repository_state_before_runner(self):
        forged_identity = copy.deepcopy(self.repository.identity)
        forged_identity["repository_identity_digest"] = "0" * 64
        forged = adapter.RepositoryState(
            self.repository.root,
            self.repository.canonical_repository_id,
            self.repository.canonical_remote,
            self.repository.head,
            self.repository.branch,
            forged_identity,
        )
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "identity evidence"):
            self.controller(runner).refresh(
                forged, expected_head=forged.head, explicit_opt_in=True
            )
        self.assertEqual([], calls)

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

    def test_tracked_derived_index_collision_fails_before_execution(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        index = self.root / ".gitnexus"
        index.mkdir()
        primary = index / "gitnexus.json"
        legacy = index / "meta.json"
        primary.write_text("tracked primary\n", encoding="utf-8")
        legacy.write_text("tracked legacy\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-f", ".gitnexus"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", "track collision"],
            check=True,
        )
        self.repository = repository_state(self.root)

        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError,
            "tracked paths inside the derived index",
        ):
            self.controller(runner).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )

        self.assertEqual([], calls)
        self.assertEqual("tracked primary\n", primary.read_text(encoding="utf-8"))
        self.assertEqual("tracked legacy\n", legacy.read_text(encoding="utf-8"))
        self.assertEqual(
            "",
            subprocess.run(
                ["git", "-C", str(self.root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
        )

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

    def test_refresh_rejects_local_content_filter_before_runner_or_filter_execution(self):
        calls = []
        marker = self.directory / "refresh-filter-executed"
        filter_program = self.directory / "refresh-clean-filter"
        filter_program.write_text(
            "#!/bin/sh\n"
            f"/usr/bin/touch {marker}\n"
            "/bin/cat\n",
            encoding="utf-8",
        )
        filter_program.chmod(filter_program.stat().st_mode | stat.S_IXUSR)
        (self.root / ".gitattributes").write_text(
            "code.py filter=demo\n", encoding="utf-8"
        )
        run_git(self.root, "config", "--local", "filter.demo.clean", str(filter_program))

        with self.assertRaisesRegex(
            adapter.GitNexusAdapterError,
            "filter/include configuration is unsupported",
        ):
            self.controller(
                lambda argv, **kwargs: calls.append(argv)
            ).refresh(
                self.repository,
                expected_head=self.repository.head,
                explicit_opt_in=True,
            )
        self.assertEqual([], calls)
        self.assertFalse(marker.exists())

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
            qualification = adapter.qualify_executable(
                executable,
                timeout_seconds=3,
                **provenance_kwargs(executable),
            )
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
            trusted_arguments = provenance_cli_args(executable)
            with mock.patch("builtins.print") as printer:
                self.assertEqual(
                    0,
                    adapter.operator_main(
                        ["qualify", "--executable", str(executable), *trusted_arguments]
                    ),
                )
                qualified = json.loads(printer.call_args.args[0])
            self.assertEqual("qualified", qualified["status"])
            self.assertEqual("shebang-resolved", qualified["runtime_symlink_policy"])
            self.assertNotIn(str(executable), json.dumps(qualified))

            arguments = [
                "status", "--executable", str(executable), *trusted_arguments,
                "--repo-root", str(root),
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

    def test_operator_status_rejects_explicit_git_script_wrapper(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = pathlib.Path(raw).resolve()
            executable = make_cli_executable(directory)
            root = make_repo(directory)
            repository = repository_state(root)
            write_metadata(root, valid_metadata(repository))
            trusted_arguments = provenance_cli_args(executable)
            real_git_text = shutil.which("git", path=os.defpath)
            self.assertIsNotNone(real_git_text)
            real_git = pathlib.Path(real_git_text).resolve(strict=True)
            marker = directory / "operator-git-used"
            wrapper = directory / "operator-selected-git"
            wrapper.write_text(
                f"#!{sys.executable}\n"
                "import os, pathlib, sys\n"
                f"pathlib.Path({str(marker)!r}).write_text('used', encoding='utf-8')\n"
                f"os.execv({str(real_git)!r}, [{str(real_git)!r}, *sys.argv[1:]])\n",
                encoding="utf-8",
            )
            wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
            arguments = [
                "status",
                "--executable",
                str(executable),
                *trusted_arguments,
                "--git-executable",
                str(wrapper),
                "--repo-root",
                str(root),
                "--repository-id",
                "github.com.Owner.Repository",
                "--expected-remote",
                "https://github.com/Owner/Repository.git",
            ]
            with mock.patch("builtins.print") as printer:
                self.assertEqual(2, adapter.operator_main(arguments))
                result = json.loads(printer.call_args.args[0])
            self.assertEqual("operation-failed", result["error"])
            self.assertFalse(marker.exists())
            self.assertNotIn(str(wrapper), json.dumps(result))

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

    def test_root_git_executable_path_is_rejected_without_traceback(self):
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "bound safely"):
            adapter._git_executable(pathlib.Path("/"))

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

    def test_lock_directory_and_file_identity_fail_closed(self):
        real_parent = self.directory / "real-lock-parent"
        real_parent.mkdir()
        linked_parent = self.directory / "linked-lock-parent"
        linked_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "cannot be prepared|parent boundary"):
            with adapter._root_lock(self.repository.root, linked_parent / "locks"):
                self.fail("parent symlink lock directory must not be accepted")

        writable = self.directory / "writable-locks"
        writable.mkdir()
        writable.chmod(0o777)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "directory is unsafe"):
            with adapter._root_lock(self.repository.root, writable):
                self.fail("shared-writable lock directory must not be accepted")

        lock_directory = self.directory / "identity-locks"
        with adapter._root_lock(self.repository.root, lock_directory):
            pass
        lock_file = next(lock_directory.glob("*.lock"))
        lock_file.unlink()
        external = self.directory / "external-lock"
        external.write_text("external\n", encoding="utf-8")
        os.link(external, lock_file)
        with self.assertRaisesRegex(adapter.GitNexusAdapterError, "lock file is unsafe"):
            with adapter._root_lock(self.repository.root, lock_directory):
                self.fail("hard-linked lock file must not be accepted")

    def test_lock_parent_replacement_and_cross_process_flock_fail_closed(self):
        parent = self.directory / "replaceable-parent"
        parent.mkdir(mode=0o700)
        lock_directory = parent / "locks"

        def replace_parent(_path):
            displaced = self.directory / "displaced-parent"
            parent.rename(displaced)
            parent.mkdir(mode=0o700)

        with mock.patch.object(
            adapter, "_LOCK_DIRECTORY_VALIDATION_HOOK", replace_parent
        ):
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "cannot be prepared|directory is unsafe"
            ):
                with adapter._root_lock(self.repository.root, lock_directory):
                    self.fail("replaced parent namespace must not be accepted")

        stable = self.directory / "cross-process-locks"
        alternate = self.directory / "alternate-cross-process-locks"
        alternate_tmp = self.directory / "alternate-tmp"
        alternate_tmp.mkdir()
        child_environment = {
            **os.environ,
            "TMPDIR": str(alternate_tmp),
            "TEMP": str(alternate_tmp),
            "TMP": str(alternate_tmp),
        }
        program = (
            "import pathlib,sys\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import gitnexus_adapter as a\n"
            "try:\n"
            f"  with a._root_lock(pathlib.Path({str(self.repository.root)!r}), pathlib.Path({str(alternate)!r})):\n"
            "    print('acquired')\n"
            "except a.GitNexusAdapterError as exc:\n"
            "  print(str(exc))\n"
        )
        with adapter._root_lock(self.repository.root, stable):
            child = subprocess.run(
                [sys.executable, "-c", program],
                check=True,
                capture_output=True,
                text=True,
                env=child_environment,
            )
        self.assertIn("lock is unavailable", child.stdout)
        reacquired = subprocess.run(
            [sys.executable, "-c", program],
            check=True,
            capture_output=True,
            text=True,
            env=child_environment,
        )
        self.assertEqual("acquired", reacquired.stdout.strip())

    def test_different_repositories_cannot_share_home_across_processes(self):
        second_parent = self.directory / "second-project"
        second_parent.mkdir()
        second_root = make_repo(second_parent)
        program = (
            "import pathlib,sys,time\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import gitnexus_adapter as a\n"
            f"home=pathlib.Path({str(self.gitnexus_home)!r})\n"
            f"root=pathlib.Path({str(self.root)!r})\n"
            "with a._isolated_home_resource(home, root):\n"
            "  print('home-locked', flush=True)\n"
            "  time.sleep(2)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", program],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert child.stdout is not None
            self.assertEqual("home-locked", child.stdout.readline().strip())
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "cross-process lock is unavailable"
            ):
                with adapter._isolated_home_resource(
                    self.gitnexus_home, second_root
                ):
                    self.fail("a shared home must serialize different repositories")
        finally:
            child.wait(timeout=5)
            if child.stdout is not None:
                child.stdout.close()
            if child.stderr is not None:
                child.stderr.close()
        self.assertEqual(0, child.returncode)
        with adapter._isolated_home_resource(self.gitnexus_home, second_root):
            pass

    def test_home_lock_deadline_unsafe_file_and_release_fail_closed(self):
        identity = adapter._capture_isolated_home_identity(self.gitnexus_home)
        ticks = iter((0.0, 2.0))
        with (
            mock.patch.object(
                adapter.time,
                "monotonic",
                side_effect=lambda: next(ticks, 2.0),
            ),
            self.assertRaisesRegex(
                adapter.ProbeDeadlineError, "probe-deadline-expired"
            ),
        ):
            with adapter._isolated_home_resource(
                self.gitnexus_home, self.root, deadline=1.0
            ):
                self.fail("expired home acquisition must not yield")

        with adapter._isolated_home_resource(self.gitnexus_home, self.root):
            pass

        lock_file = (
            adapter._lock_directory_path(None)
            / adapter._isolated_home_lock_name(identity)
        )
        lock_file.chmod(0o666)
        try:
            with self.assertRaisesRegex(
                adapter.GitNexusAdapterError, "lock file is unsafe"
            ):
                with adapter._isolated_home_resource(
                    self.gitnexus_home, self.root
                ):
                    self.fail("unsafe home lock file must not be accepted")
        finally:
            lock_file.chmod(0o600)

        with adapter._isolated_home_resource(self.gitnexus_home, self.root):
            pass

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
