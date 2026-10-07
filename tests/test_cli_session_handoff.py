from __future__ import annotations

import concurrent.futures
import copy
import ctypes
import errno
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "skills"
    / "cli-session-handoff"
    / "scripts"
    / "cli_session_handoff.py"
)
SPEC = importlib.util.spec_from_file_location("cli_session_handoff", SCRIPT)
handoff = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = handoff
SPEC.loader.exec_module(handoff)

SESSION_ID = "0199a213-81c0-7800-8aa1-bbab2a035a53"


def public_help_executable() -> str:
    override = os.environ.get("CODEX_PUBLIC_HELP_EXECUTABLE")
    if override is not None:
        path = pathlib.Path(override)
        if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("CODEX_PUBLIC_HELP_EXECUTABLE must be an absolute executable file")
        return str(path)
    executable = shutil.which("codex")
    if executable is None:
        raise unittest.SkipTest("Codex CLI is unavailable; public-help compatibility smoke skipped")
    return executable


def assert_public_help_shape(
    case: unittest.TestCase, result: subprocess.CompletedProcess[str], command: str
) -> None:
    case.assertEqual(0, result.returncode, result.stderr)
    case.assertRegex(
        result.stdout, rf"(?m)^Usage: {re.escape(command)}(?:\s+[\[<]|\s*$)"
    )


class PublicHelpContractTests(unittest.TestCase):
    def test_zero_exit_root_or_parent_help_cannot_prove_subcommand(self) -> None:
        for output in ("Usage: codex [OPTIONS] [PROMPT]\n", "Usage: codex exec [OPTIONS]\n"):
            with self.subTest(output=output), self.assertRaises(AssertionError):
                assert_public_help_shape(
                    self, subprocess.CompletedProcess([], 0, output, ""), "codex exec resume"
                )

    def test_subcommand_help_cannot_prove_parent_and_nonzero_exit_is_rejected(self) -> None:
        with self.assertRaises(AssertionError):
            assert_public_help_shape(
                self, subprocess.CompletedProcess([], 0, "Usage: codex exec fork <SESSION_ID>\n", ""),
                "codex exec",
            )
        with self.assertRaises(AssertionError):
            assert_public_help_shape(
                self, subprocess.CompletedProcess([], 1, "Usage: codex exec [OPTIONS]\n", "failed"),
                "codex exec",
            )

    def test_explicit_invalid_binary_fails_without_path_fallback(self) -> None:
        for value in ("", "codex", "/nonexistent/issue-249-codex"):
            with self.subTest(value=value), mock.patch.dict(os.environ, CODEX_PUBLIC_HELP_EXECUTABLE=value):
                with mock.patch.object(shutil, "which") as which, self.assertRaises(ValueError):
                    public_help_executable()
                which.assert_not_called()

    def test_explicit_binary_does_not_select_path_binary(self) -> None:
        with mock.patch.dict(os.environ, CODEX_PUBLIC_HELP_EXECUTABLE=sys.executable):
            with mock.patch.object(shutil, "which") as which:
                self.assertEqual(sys.executable, public_help_executable())
            which.assert_not_called()


class ProcessInventoryContractTests(unittest.TestCase):
    def list_children(self, count: int, number: int, *, exists: bool = True) -> set[int]:
        def call(parent, buffer, size):
            self.assertEqual(0, ctypes.get_errno())
            ctypes.set_errno(number)
            if 0 < count < handoff.MAX_TRACKED_DESCENDANTS:
                buffer[0] = 42
            return count

        library = types.SimpleNamespace(proc_listchildpids=mock.Mock(side_effect=call))
        with mock.patch.object(handoff.sys, "platform", "darwin"), mock.patch.object(
            ctypes, "CDLL", return_value=library
        ), mock.patch.object(handoff, "_pid_exists", return_value=exists):
            return handoff._direct_child_pids(21)

    def test_darwin_zero_with_permission_error_is_not_an_empty_inventory(self) -> None:
        for number in (errno.EPERM, errno.EACCES):
            with self.subTest(errno=number), self.assertRaises(OSError) as caught:
                self.list_children(0, number)
            self.assertEqual(number, caught.exception.errno)

    def test_darwin_empty_success_clears_stale_errno_and_missing_pid_is_benign(self) -> None:
        ctypes.set_errno(errno.EPERM)
        self.assertEqual(set(), self.list_children(0, 0))
        self.assertEqual(set(), self.list_children(0, errno.ESRCH))
        self.assertEqual(set(), self.list_children(0, errno.EPERM, exists=False))
        self.assertEqual({42}, self.list_children(1, 0))

    def test_darwin_full_inventory_cannot_claim_complete_coverage(self) -> None:
        for count in (handoff.MAX_TRACKED_DESCENDANTS, handoff.MAX_TRACKED_DESCENDANTS + 1):
            with self.subTest(count=count), self.assertRaises(OSError) as caught:
                self.list_children(count, 0)
            self.assertEqual(errno.EOVERFLOW, caught.exception.errno)

    def test_darwin_identity_error_preserves_errno_without_stale_values(self) -> None:
        def call(*arguments):
            self.assertEqual(0, ctypes.get_errno())
            ctypes.set_errno(errno.EACCES)
            return 0

        library = types.SimpleNamespace(proc_pidinfo=mock.Mock(side_effect=call))
        ctypes.set_errno(errno.ESRCH)
        with mock.patch.object(handoff.sys, "platform", "darwin"), mock.patch.object(
            ctypes, "CDLL", return_value=library
        ), mock.patch.object(handoff, "_pid_exists", return_value=True):
            with self.assertRaises(OSError) as caught:
                handoff._process_identity(21)
        self.assertEqual(errno.EACCES, caught.exception.errno)

    def test_tracker_reports_first_error_stage_without_native_error_text(self) -> None:
        cases = {
            "root-identity": ([OSError(errno.EACCES, "private process data")], set()),
            "parent-identity": ([(1, "root"), OSError(errno.EPERM, "private process data")], set()),
            "child-list": ([(1, "root"), (1, "root")], OSError(errno.EPERM, "private process data")),
            "child-identity": ([(1, "root"), (1, "root"), OSError(errno.EACCES, "private process data")], {42}),
        }
        for stage, (identities, children) in cases.items():
            with self.subTest(stage=stage):
                tracker = handoff.ProcessTreeTracker(21)
                with mock.patch.object(handoff, "_process_identity", side_effect=identities), mock.patch.object(
                    handoff, "_direct_child_pids", **(
                        {"side_effect": children} if isinstance(children, OSError) else {"return_value": children}
                    )
                ):
                    tracker.capture()
                # Later benign disappearance cannot erase the first failed observation.
                with mock.patch.object(handoff, "_process_identity", return_value=None):
                    tracker.capture()
                with self.assertRaises(handoff.HandoffValidationError) as caught:
                    tracker.ensure_available()
                self.assertIn(f"stage={stage}", str(caught.exception))
                self.assertIn("errno=", str(caught.exception))
                self.assertNotIn("private process data", str(caught.exception))

    def test_tracker_live_readback_and_stop_timeout_are_distinct_and_fail_closed(self) -> None:
        tracker = handoff.ProcessTreeTracker(21)
        tracker._known[42] = "child-token"
        with mock.patch.object(handoff, "_process_identity", side_effect=OSError(errno.EPERM, "private")):
            self.assertEqual(set(), tracker.live_descendants())
        with self.assertRaisesRegex(handoff.HandoffValidationError, "stage=live-readback"):
            tracker.ensure_available()
        tracker = handoff.ProcessTreeTracker(21)
        tracker._thread = mock.Mock()
        tracker._thread.is_alive.return_value = True
        tracker.stop()
        with self.assertRaisesRegex(handoff.HandoffValidationError, "stage=tracker-stop-timeout; errno=None"):
            tracker.ensure_available()


class CodexPublicHelpCompatibilityTests(unittest.TestCase):
    """Read-only public CLI shape checks; never starts or resumes a session."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.codex = public_help_executable()
        cls.runtime_temp = tempfile.TemporaryDirectory(prefix="codex-public-help-")
        cls.addClassCleanup(cls.runtime_temp.cleanup)
        cls.runtime_root = pathlib.Path(cls.runtime_temp.name)
        cls.codex_home = cls.runtime_root / "codex-home"
        cls.home = cls.runtime_root / "home"
        cls.config_home = cls.runtime_root / "config"
        cls.cache_home = cls.runtime_root / "cache"
        cls.state_home = cls.runtime_root / "state"
        for path in (
            cls.codex_home,
            cls.home,
            cls.config_home,
            cls.cache_home,
            cls.state_home,
        ):
            path.mkdir()

    def run_public_argv(
        self, argv: list[str]
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        for name in (
            "OPENAI_API_KEY",
            "OPENAI_ORG_ID",
            "OPENAI_PROJECT_ID",
        ):
            env.pop(name, None)
        env.update(
            {
                "HOME": str(self.home),
                "CODEX_HOME": str(self.codex_home),
                "XDG_CONFIG_HOME": str(self.config_home),
                "XDG_CACHE_HOME": str(self.cache_home),
                "XDG_STATE_HOME": str(self.state_home),
            }
        )
        result = subprocess.run(
            argv,
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        created = [
            path.relative_to(self.runtime_root)
            for path in self.runtime_root.rglob("*")
        ]
        self.assertFalse(
            any("sessions" in path.parts for path in created),
            f"public-help smoke created session state: {created}",
        )
        self.assertFalse(
            any(path.suffix == ".jsonl" for path in created),
            f"public-help smoke created JSONL state: {created}",
        )
        return result

    def run_public(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.run_public_argv([self.codex, *arguments])

    def test_version_and_exec_help_shapes(self) -> None:
        version = self.run_public("--version").stdout.strip()
        self.assertRegex(version, r"^codex-cli\s+\S+$")

        exec_help = self.run_public("exec", "--help").stdout
        for marker in ("Usage: codex exec", "resume", "fork", "--json"):
            with self.subTest(command="exec", marker=marker):
                self.assertIn(marker, exec_help)

        resume_help = self.run_public("exec", "resume", "--help").stdout
        for marker in ("Usage: codex exec resume", "[SESSION_ID]", "--json"):
            with self.subTest(command="exec resume", marker=marker):
                self.assertIn(marker, resume_help)

        fork_help = self.run_public("exec", "fork", "--help").stdout
        for marker in ("Usage: codex exec fork", "<SESSION_ID>", "--json"):
            with self.subTest(command="exec fork", marker=marker):
                self.assertIn(marker, fork_help)

    def test_plugin_list_json_shape(self) -> None:
        payload = json.loads(self.run_public("plugin", "list", "--json").stdout)
        self.assertIsInstance(payload, dict)
        self.assertIsInstance(payload.get("installed"), list)
        self.assertIsInstance(payload.get("available"), list)
        for item in payload["installed"]:
            with self.subTest(plugin=item.get("name")):
                self.assertIsInstance(item, dict)
                self.assertTrue(
                    {
                        "pluginId",
                        "name",
                        "version",
                        "installed",
                        "enabled",
                        "source",
                    }.issubset(item)
                )

    def test_production_argv_shapes_are_accepted_by_public_help(self) -> None:
        for operation in ("start", "resume", "fork"):
            request = types.SimpleNamespace(
                executable=pathlib.Path(self.codex),
                sandbox="read-only",
                workspace=ROOT,
                operation=operation,
                session_id=None if operation == "start" else SESSION_ID,
                execution_target=None,
            )
            argv = handoff.build_argv(request)
            self.assertEqual("-", argv[-1])
            argv[-1] = "--help"

            result = self.run_public_argv(argv)

            with self.subTest(operation=operation):
                command = "codex exec" if operation == "start" else f"codex exec {operation}"
                assert_public_help_shape(self, result, command)


FAKE_CODEX = r'''
import json
import os
import pathlib
import subprocess
import sys
import time

SESSION_ID = "0199a213-81c0-7800-8aa1-bbab2a035a53"

if sys.argv[1:] == ["--version"]:
    version_mode = os.environ.get("FAKE_CODEX_VERSION_MODE", "success")
    if version_mode == "timeout":
        time.sleep(30)
        raise SystemExit(0)
    if version_mode in ("stdout-overflow", "stdout-overflow-quick"):
        sys.stdout.write("x" * 8192)
        sys.stdout.flush()
        # Let the controller observe overflow and own termination. Exiting here
        # can instead exercise invalid-version parsing or an exit/signal race.
        if version_mode == "stdout-overflow":
            time.sleep(30)
        raise SystemExit(0)
    print("codex-cli " + os.environ.get("FAKE_CODEX_VERSION", "9.8.7"))
    raise SystemExit(0)

capture = os.environ.get("FAKE_CODEX_CAPTURE")
if capture:
    pathlib.Path(capture).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
pid_capture = os.environ.get("FAKE_CODEX_PID_CAPTURE")
if pid_capture:
    pathlib.Path(pid_capture).write_text(str(os.getpid()), encoding="utf-8")

mode = os.environ.get("FAKE_CODEX_MODE", "success")
workspace = ""
if "--cd" in sys.argv:
    workspace = sys.argv[sys.argv.index("--cd") + 1]
prompt = sys.stdin.read()
prompt_capture = os.environ.get("FAKE_CODEX_PROMPT_CAPTURE")
if prompt_capture:
    pathlib.Path(prompt_capture).write_text(prompt, encoding="utf-8")

if mode == "timeout":
    time.sleep(30)
    raise SystemExit(0)
if mode == "detached-descendant":
    descendant = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        start_new_session=True,
    )
    descendant_capture = os.environ.get("FAKE_CODEX_DESCENDANT_PID_CAPTURE")
    if descendant_capture:
        pathlib.Path(descendant_capture).write_text(
            str(descendant.pid), encoding="utf-8"
        )
    time.sleep(30)
    raise SystemExit(0)
if mode == "stdout-overflow":
    sys.stdout.write("x" * (1024 * 1024 + 8192))
    sys.stdout.flush()
    raise SystemExit(0)
if mode == "stderr-overflow":
    sys.stderr.write("x" * (256 * 1024 + 8192))
    sys.stderr.flush()
    raise SystemExit(0)
if mode == "nonzero":
    raise SystemExit(7)
if mode in {"write-workspace", "write-staged", "write-commit"}:
    pathlib.Path(workspace, "README.md").write_text(
        "changed by child\n", encoding="utf-8"
    )
    pathlib.Path(workspace, "new.txt").write_text(
        "new child file\n", encoding="utf-8"
    )
    if mode in {"write-staged", "write-commit"}:
        subprocess.run(
            ["git", "-C", workspace, "add", "README.md", "new.txt"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    if mode == "write-commit":
        subprocess.run(
            [
                "git",
                "-C",
                workspace,
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-q",
                "-m",
                "child commit",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
if mode == "malformed":
    print("not-json")
    raise SystemExit(0)
if mode == "duplicate-json-key":
    print('{"type":"thread.started","type":"turn.completed"}')
    raise SystemExit(0)
if mode == "terminal-before-session":
    print(json.dumps({"type": "turn.completed"}))
    print(json.dumps({"type": "thread.started", "thread_id": SESSION_ID}))
    raise SystemExit(0)
if mode == "summary-before-session":
    print(
        json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "too early"},
            }
        )
    )
    print(json.dumps({"type": "thread.started", "thread_id": SESSION_ID}))
    print(json.dumps({"type": "turn.completed"}))
    raise SystemExit(0)

events = [
    {
        "type": "thread.started",
        "thread_id": (
            "0199a213-81c0-7800-8aa1-bbab2a035a54"
            if mode == "different-session"
            else SESSION_ID
        ),
    },
    {"type": "turn.started"},
]
if mode == "duplicate-session":
    events.append({"type": "thread.started", "thread_id": SESSION_ID})
if mode != "missing-summary":
    summary = "Completed bounded handoff."
    if mode == "sensitive-summary":
        summary = (
            f"Workspace {workspace}; local /" + "Users/alice/private; "
            "api_key=topsecret; sk-abcdefgh123456; "
            "-----BEGIN PRIVATE KEY-----; "
            "eyJhbGciOiJIUzI1NiJ9.placeholder.signature; "
            "AKIAIOSFODNN7EXAMPLE; "
            "https://user:password@example.invalid/."
        )
    events.append(
        {
            "type": "item.completed",
            "item": {"id": "item_1", "type": "agent_message", "text": summary},
        }
    )
if mode == "turn-failed":
    events.append({"type": "turn.failed", "error": {"message": "failed"}})
else:
    events.append({"type": "turn.completed", "usage": {"input_tokens": 1}})
if mode == "duplicate-terminal":
    events.append({"type": "turn.completed", "usage": {"input_tokens": 1}})
if mode == "summary-after-terminal":
    events.append(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "too late"},
        }
    )

for event in events:
    print(json.dumps(event))
'''


class CliSessionHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = pathlib.Path(self.tempdir.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self._git("init", "-q")
        self._git("config", "user.name", "Test User")
        self._git("config", "user.email", "test@example.invalid")
        (self.workspace / "README.md").write_text("fixture\n", encoding="utf-8")
        self._git("add", "README.md")
        self._git("commit", "-q", "-m", "fixture")
        self._git("remote", "add", "origin", "https://github.com/example/repository.git")
        self.head = self._git("rev-parse", "HEAD").stdout.strip()
        self.executable = self.root / "fake-codex"
        self.executable.write_text(
            f"#!{sys.executable}\n{FAKE_CODEX}", encoding="utf-8"
        )
        self.executable.chmod(
            self.executable.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP
        )
        self.capture = self.root / "argv.json"
        self.prompt_capture = self.root / "prompt.txt"
        self.pid_capture = self.root / "pid.txt"
        self.descendant_pid_capture = self.root / "descendant-pid.txt"

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.workspace), *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def request(self, **overrides: object) -> dict[str, object]:
        request: dict[str, object] = {
            "schema_version": 1,
            "operation": "start",
            "codex_executable": str(self.executable),
            "workspace": str(self.workspace),
            "prompt": (
                "Read AGENTS.md first. Complete only the bounded task. "
                "Do not dispatch another session. Return verification evidence. "
                "Do not commit. Do not push. Do not open pull requests. "
                "Do not merge. Do not perform platform writes."
            ),
            "sandbox": "read-only",
            "timeout_seconds": 10,
            "expected_head": self.head,
            "prompt_boundary_version": handoff.PROMPT_BOUNDARY_VERSION,
            "authorization": {
                "marker": handoff.AUTHORIZATION_MARKER,
                "runtime_session_mutation_authorized": True,
                "sandbox_ceiling": "read-only",
                "external_write_authorized": False,
                "destructive_action_approved": False,
            },
        }
        request.update(overrides)
        return request

    def execute(
        self,
        *,
        mode: str = "success",
        request: dict[str, object] | None = None,
    ) -> dict[str, object]:
        environment = {
            "FAKE_CODEX_MODE": mode,
            "FAKE_CODEX_CAPTURE": str(self.capture),
            "FAKE_CODEX_PROMPT_CAPTURE": str(self.prompt_capture),
            "FAKE_CODEX_PID_CAPTURE": str(self.pid_capture),
            "FAKE_CODEX_DESCENDANT_PID_CAPTURE": str(
                self.descendant_pid_capture
            ),
        }
        with mock.patch.dict(os.environ, environment):
            return handoff.execute_handoff(request or self.request())

    def continuity_assessment(self) -> dict[str, object]:
        metric = {
            "objective_total_tokens": 100,
            "wall_time_seconds": 10,
            "repeated_reads": 0,
            "review_fix_rounds": 2,
            "stale_context_errors": 0,
            "blockers": 0,
            "handoff_bootstrap_tokens": 10,
            "quality_score": 90,
        }
        return {
            "contract_version": "loop-context-continuity/v1",
            "assessment_id": "assessment-1",
            "objective_id": "issue-165",
            "repository_id": "github.com/example/repository",
            "review_fix": {"completed_rounds": 2, "assessment_trigger_rounds": 2},
            "signals": {
                "stale_findings": 1,
                "repeated_reads": 1,
                "phase_boundary": True,
                "compaction_or_token_pressure": False,
                "independent_high_noise_packet": False,
                "current_context_can_reground": True,
                "human_gate_required": False,
            },
            "runtime": {
                "surface": "cli",
                "control_surface": "cli-exec",
                "mode": "non-interactive",
            },
            "worktree": {"state": "clean"},
            "ownership": {
                "source_writer": "source",
                "exclusive_transfer_ready": True,
                "parallel_packet_disjoint": False,
            },
            "checkpoint": {
                "checkpoint_id": "checkpoint-1",
                "objective_id": "issue-165",
                "repository_id": "github.com/example/repository",
                "branch": self._git("branch", "--show-current").stdout.strip(),
                "head_sha": self.head,
                "worktree_state": "clean",
                "completed": ["implementation"],
                "remaining": ["review"],
                "verification": ["focused tests passed"],
                "risks": [],
                "next_packet": "review",
                "source_writer": "source",
                "destination_writer": "destination",
                "source_stop_writing_confirmed": True,
            },
            "lineage": {
                "rollover_id": "rollover-1",
                "prior_rollover_id": None,
                "prior_checkpoint_sha256": None,
                "progress_since_prior_rollover": True,
                "progress_evidence": ["implementation changed since prior checkpoint"],
                "seen_rollovers": [],
                "graph_projection": "absent",
            },
            "comparison": {
                "same_context": dict(metric, objective_total_tokens=120),
                "fresh_rollover": metric,
            },
        }

    def _typed_request(self, *, official=True, sandbox="read-only"):
        from tests.test_model_execution_target import TargetFixture
        request = self.request(sandbox=sandbox)
        request["authorization"]["sandbox_ceiling"] = sandbox
        home = self.root.resolve()/"typed-target-home"
        target = TargetFixture(home, prompt=request["prompt"].rstrip()+"\n\n"+handoff.PROMPT_BOUNDARY_APPENDIX,
            head=self.head, executable_sha256=handoff._sha256_file(self.executable), official=official)
        request["target_ref"] = target.ref
        return request, target

    def _packet_attempt(self, request, packet, attempt_id, revision):
        source_input = self._packet_input
        # Synthetic stop adapter is fixture evidence, never production adoption.
        adapter = types.SimpleNamespace(verify_stopped=lambda *_: True, supports_target=lambda *_: True)
        with mock.patch.dict(handoff.PACKET_STOP_ADAPTERS, {'synthetic': adapter}):
            return handoff.execute_packet_attempt(request, packet, attempt_id, revision,
                stop_adapter_id='synthetic', source_input=source_input)

    def _prepare_packet_input(self, target, request, packet):
        from tests.test_model_task_ingress import InputFixture
        identity = handoff.model_execution_target.identity(target.record)
        f = InputFixture(target.home, request, scope=target.record['task']['route_task']['qualification_scope'],
            destinations=[handoff.model_execution_target.canonical_sha(identity)])
        self._packet_input = f.read(identity=identity)
        packet.prepare(self._packet_input.packet_identity(handoff._canonical_repository_id(self.workspace)))

    def _routed_input(self, target, request):
        from tests.test_model_failover import route_fixture
        from tests.test_model_task_ingress import InputFixture
        with mock.patch.object(handoff.model_execution_target, 'root', return_value=target.home):
            binding = target.resolve(sandbox=request['sandbox'])
        route = route_fixture(); route['task'] = target.record['task']['route_task']
        policy = route['model_failover']
        for key in ('task', 'authorization', 'secret_check'):
            policy[key].update(task_id='T1' if key != 'task' else None,
                scope=binding.scope, acceptance_sha256=binding.acceptance_sha256)
        policy['task'].pop('task_id'); policy['task']['id'] = binding.task_id
        for candidate in policy['targets']:
            candidate['qualification']['scopes'] = [binding.scope]
        selected = policy['targets'][2 if target.record['provider']['billing'] == 'chatgpt-subscription' else 0]
        selected.update(id=binding.target_id, identity=handoff.model_execution_target.target_identity(binding))
        selected['qualification']['identity_sha256'] = handoff.model_execution_target.canonical_sha(selected['identity'])
        if selected['stage'] == 'official':
            policy['targets'][0]['availability']['status'] = 'unavailable'
        else:
            policy['current_target'] = binding.target_id
        policy['authorization']['target_identity_sha256'] = [handoff.model_execution_target.canonical_sha(c['identity']) for c in policy['targets']]
        fixture = InputFixture(target.home, request, scope=binding.scope, destinations=[binding.identity_sha256])
        # The operator prepares the existing protected PacketStore root;
        # neither original-input loader nor executor adopts a missing store.
        (target.home/'model-packets').mkdir(mode=0o700, exist_ok=True)
        return route, fixture, binding

    def test_actual_routing_original_input_to_typed_target_and_packet_chain(self):
        import model_task_execution as execution
        request, target = self._typed_request(official=True)
        route, fixture, binding = self._routed_input(target, request)
        stop = types.SimpleNamespace(supports_target=lambda value: value.identity_sha256 == binding.identity_sha256,
            verify_stopped=lambda *_: True)
        with mock.patch.object(handoff.model_execution_target, 'root', return_value=target.home), mock.patch.dict(handoff.PACKET_STOP_ADAPTERS, {'synthetic': stop}):
            result = execution.execute_next(route['task'], route['model_failover'], request, fixture.ref)
        self.assertTrue(result['dispatched'])
        self.assertEqual(result['execution']['status'], 'completed')
        self.assertEqual(result['execution']['execution_target']['provider_readback'], 'unknown')
        self.assertFalse(result['repository_completion_claimed'])
        self.assertEqual((self.workspace/'README.md').read_text(), 'fixture\n')

    def test_legacy_unknown_locator_is_not_replaced_by_new_ingress(self):
        import model_task_execution as execution
        request, target = self._typed_request(official=True)
        route, fixture, binding = self._routed_input(target, request)
        stable = {'repository': handoff._canonical_repository_id(self.workspace), 'task_id': binding.task_id,
            'scope': binding.scope, 'acceptance_sha256': binding.acceptance_sha256}
        store = handoff.model_packet_store
        packet_id = store.digest(store.canonical(stable))
        directory = target.home/'model-packets'
        packet = store.PacketStore(directory, packet_id)
        packet.prepare(store.digest(store.canonical({**stable, 'source_head': self.head})))
        packet.claim('legacy-attempt', 'a'*64, binding.identity_sha256, expected_revision=0)
        packet.retain_unknown('legacy-attempt')
        before = (directory/packet_id/'ledger.json').read_bytes()
        stop = types.SimpleNamespace(supports_target=lambda *_: True, verify_stopped=lambda *_: True)
        with mock.patch.object(handoff.model_execution_target, 'root', return_value=target.home), mock.patch.dict(handoff.PACKET_STOP_ADAPTERS, {'synthetic': stop}), mock.patch.object(handoff, '_run_child') as run:
            result = execution.execute_next(route['task'], route['model_failover'], request, fixture.ref)
        self.assertIsNone(result['dispatched']); self.assertEqual(result['execution']['status'], 'unknown')
        run.assert_not_called()
        self.assertEqual((directory/packet_id/'ledger.json').read_bytes(), before)
        self.assertEqual([p.name for p in directory.iterdir()], [packet_id])

    def test_packet_without_qualified_stop_adapter_never_starts(self):
        with mock.patch.object(handoff, 'validate_request') as validate:
            with self.assertRaisesRegex(handoff.HandoffValidationError, 'containment is unavailable'):
                handoff.execute_packet_attempt({}, None, 'attempt-1', 0)
        validate.assert_not_called()

    def test_packet_cannot_omit_or_forge_original_input_guard(self):
        adapter = types.SimpleNamespace(supports_target=lambda *_: True)
        with mock.patch.dict(handoff.PACKET_STOP_ADAPTERS, {'synthetic': adapter}), mock.patch.object(handoff, 'validate_request') as validate:
            for source_input in (None, {'granted': True, 'qualified': True}):
                with self.assertRaisesRegex(handoff.HandoffValidationError, 'Original task/source input is required'):
                    handoff.execute_packet_attempt({}, None, 'attempt-1', 0,
                        stop_adapter_id='synthetic', source_input=source_input)
        validate.assert_not_called()

    def test_packet_source_drift_before_launch_retains_claim_without_start(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        capture = handoff._capture_isolated_patch
        def drift(*args):
            patch = capture(*args)
            (self.workspace/'README.md').write_text('source changed before launch\n')
            return patch
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_capture_isolated_patch', side_effect=drift), mock.patch.object(handoff, '_run_child') as run:
            result = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(result['status'], 'unknown')
        run.assert_not_called()
        ledger, patch = packet.read_checkpoint()
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
        self.assertIsNone(ledger['checkpoint']); self.assertEqual(patch, b'')

    def test_packet_source_drift_after_child_rejects_checkpoint_and_retains_unknown(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        def drift(validated, workspace, *, on_started, before_launch):
            before_launch()
            on_started(); (workspace/'new.txt').write_text('private unaccepted result\n')
            (self.workspace/'README.md').write_text('source changed after launch\n')
            return 1, b'', None
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=drift) as run:
            result = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(result['status'], 'unknown'); run.assert_called_once()
        ledger, _ = packet.read_checkpoint()
        self.assertIsNone(ledger['checkpoint'])
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
        self.assertTrue((directory/'synthetic-packet/attempt-attempt-1/workspace/new.txt').is_file())

    def test_packet_launch_source_readback_crossing_expiry_keeps_unknown_without_child(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        ingress = handoff.model_task_ingress; original = ingress._source
        count = 0; expiry = self._packet_input.record['expires_at']
        with mock.patch.object(ingress.time, 'time', return_value=expiry-1) as clock:
            def delayed(source):
                nonlocal count
                result = original(source); count += 1
                if count == 2: clock.return_value = expiry
                return result
            with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(ingress, '_source', side_effect=delayed), mock.patch.object(handoff, '_run_child') as run:
                result = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(result['status'], 'unknown'); run.assert_not_called()
        ledger, _ = packet.read_checkpoint()
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown'); self.assertIsNone(ledger['checkpoint'])

    def test_actual_child_preparation_crossing_input_expiry_never_launches_session(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        expiry = self._packet_input.record['expires_at']; launches = []
        original_snapshot = handoff.model_execution_target.snapshot_catalog
        original_popen = subprocess.Popen
        with mock.patch.object(handoff.model_task_ingress.time, 'time', return_value=expiry-1) as clock:
            def delayed(*args):
                result = original_snapshot(*args); clock.return_value = expiry
                return result
            def observed(argv, **kwargs):
                if pathlib.Path(str(argv[0])).resolve() == self.executable.resolve() and 'exec' in argv:
                    launches.append(argv)
                    raise AssertionError('Expired input attempted an actual session launch')
                return original_popen(argv, **kwargs)
            with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff.model_execution_target, 'snapshot_catalog', side_effect=delayed), mock.patch.object(handoff.subprocess, 'Popen', side_effect=observed):
                result = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(result['status'], 'unknown'); self.assertEqual(launches, [])
        ledger, _ = packet.read_checkpoint()
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown'); self.assertIsNone(ledger['checkpoint'])

    def test_packet_target_changes_during_source_readback_never_launches_session(self):
        for case in ('revoked', 'expired'):
            with self.subTest(case=case):
                request, target = self._typed_request(sandbox='workspace-write')
                if case == 'expired':
                    target.record['expires_at'] = target.now + 10
                    for name, value in list(target.summary_values.items()):
                        target.write_summary(name, {**value, 'expires_at': target.now + 10}, refresh=False)
                    target.refresh(); request['target_ref'] = target.ref
                directory = target.home/('packets-'+case); directory.mkdir(mode=0o700)
                packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
                self._prepare_packet_input(target, request, packet)
                original_source = handoff.model_task_ingress._source
                original_popen = subprocess.Popen
                calls, launches = [], []
                with mock.patch.object(handoff.model_task_ingress.time, 'time', return_value=target.now) as clock:
                    def readback(source):
                        value = original_source(source); calls.append(True)
                        if len(calls) == 3:
                            if case == 'revoked': target.refresh(enabled=False)
                            else: clock.return_value = target.now + 11
                        return value
                    def observe(argv, **kwargs):
                        if pathlib.Path(str(argv[0])).resolve() == self.executable.resolve() and 'exec' in argv:
                            launches.append(True)
                            raise AssertionError('A changed target reached the session boundary')
                        return original_popen(argv, **kwargs)
                    with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff.model_task_ingress, '_source', side_effect=readback), mock.patch.object(handoff.subprocess, 'Popen', side_effect=observe):
                        result = self._packet_attempt(request, packet, 'attempt-1', 0)
                self.assertGreaterEqual(len(calls), 3)
                self.assertEqual(launches, [])
                self.assertEqual(result['status'], 'unknown')
                ledger, _ = packet.read_checkpoint()
                self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
                self.assertIsNone(ledger['checkpoint'])

    def test_packet_input_changes_during_final_target_readback_never_launches_session(self):
        for case in ('revoked', 'expired', 'grant-revoked'):
            with self.subTest(case=case):
                request, target = self._typed_request(sandbox='workspace-write')
                directory = target.home/('packets-input-'+case); directory.mkdir(mode=0o700)
                packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
                self._prepare_packet_input(target, request, packet)
                fixture = self._packet_input
                original_resolve = handoff.model_execution_target.resolve
                original_child = handoff._run_child
                original_popen = subprocess.Popen
                calls, launches = [], []
                stage = {'inside_child': False, 'child_resolves': 0}
                with mock.patch.object(handoff.model_task_ingress.time, 'time', return_value=target.now) as clock:
                    def readback(*args, **kwargs):
                        value = original_resolve(*args, **kwargs); calls.append(True)
                        if stage['inside_child']:
                            stage['child_resolves'] += 1
                        if stage['child_resolves'] == 2:
                            if case == 'grant-revoked':
                                handoff.model_task_ingress.revoke_task(target.home, fixture.reference)
                            elif case == 'revoked':
                                record_path = target.home/fixture.reference['path']
                                record_path.write_bytes(handoff.model_packet_store.canonical({**fixture.record, 'enabled': False}))
                            else:
                                clock.return_value = fixture.record['expires_at']
                        return value
                    def actual_child(*args, **kwargs):
                        stage['inside_child'] = True
                        return original_child(*args, **kwargs)
                    def observe(argv, **kwargs):
                        if pathlib.Path(str(argv[0])).resolve() == self.executable.resolve() and 'exec' in argv:
                            launches.append(True)
                            raise AssertionError('A changed input reached the session boundary')
                        return original_popen(argv, **kwargs)
                    with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff.model_execution_target, 'resolve', side_effect=readback), mock.patch.object(handoff, '_run_child', side_effect=actual_child), mock.patch.object(handoff.subprocess, 'Popen', side_effect=observe):
                        result = self._packet_attempt(request, packet, 'attempt-1', 0)
                self.assertGreaterEqual(len(calls), 4)
                self.assertEqual(stage['child_resolves'], 2)
                self.assertEqual(launches, [])
                self.assertEqual(result['status'], 'unknown')
                ledger, _ = packet.read_checkpoint()
                self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
                self.assertIsNone(ledger['checkpoint'])

    def test_packet_target_summary_expires_during_final_readback_never_launches_session(self):
        request, target = self._typed_request(sandbox='workspace-write')
        value = target.summary_values['qualification']
        target.write_summary('qualification', {**value, 'expires_at': target.now + 10})
        request['target_ref'] = target.ref
        directory = target.home/'packets-summary-expiry'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        original_resolve = handoff.model_execution_target.resolve
        original_child = handoff._run_child
        original_popen = subprocess.Popen
        stage = {'inside_child': False, 'child_resolves': 0}
        launches = []
        with mock.patch.object(handoff.model_task_ingress.time, 'time', return_value=target.now) as clock:
            def readback(*args, **kwargs):
                binding = original_resolve(*args, **kwargs)
                if stage['inside_child']:
                    stage['child_resolves'] += 1
                    if stage['child_resolves'] == 2:
                        clock.return_value = target.now + 11
                return binding
            def actual_child(*args, **kwargs):
                stage['inside_child'] = True
                return original_child(*args, **kwargs)
            def observe(argv, **kwargs):
                if pathlib.Path(str(argv[0])).resolve() == self.executable.resolve() and 'exec' in argv:
                    launches.append(True)
                    raise AssertionError('An expired target summary reached the session boundary')
                return original_popen(argv, **kwargs)
            with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff.model_execution_target, 'resolve', side_effect=readback), mock.patch.object(handoff, '_run_child', side_effect=actual_child), mock.patch.object(handoff.subprocess, 'Popen', side_effect=observe):
                result = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(stage['child_resolves'], 2)
        self.assertEqual(launches, [])
        self.assertEqual(result['status'], 'unknown')
        ledger, _ = packet.read_checkpoint()
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
        self.assertIsNone(ledger['checkpoint'])

    def test_typed_official_start_preserves_executor_and_unknown_provider_readback(self):
        request, target = self._typed_request()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home), "OPENAI_API_KEY": "synthetic-sentinel"}):
            response = self.execute(request=request)
        self.assertEqual(response["status"], "completed")
        self.assertTrue(response["boundaries"]["child_workspace_isolated"])
        self.assertEqual(response["execution_target"]["execution_state"], "completed")
        self.assertEqual(response["execution_target"]["provider_readback"], "unknown")
        self.assertNotIn("synthetic-sentinel", json.dumps(response))
        self.assertNotIn(str(target.home), json.dumps(response))
        self.assertFalse(response["boundaries"]["repository_completion_claimed"])

    def test_typed_company_start_and_fixed_argv(self):
        request, target = self._typed_request(official=False)
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home), "SYNTHETIC_MODEL_KEY": "synthetic-sentinel"}):
            validated = handoff.validate_request(request)
            argv = handoff.build_argv(validated)
            response = self.execute(request=request)
        self.assertIn('model_provider="synthetic"', argv)
        self.assertNotIn("synthetic-sentinel", " ".join(argv))
        self.assertIn("--ignore-user-config", argv)
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["execution_target"]["provider_readback"], "unknown")

    def test_typed_snapshot_excludes_unapproved_tag_objects_and_source_path(self):
        request, target = self._typed_request()
        (self.workspace/'other-ref.txt').write_text('synthetic-unapproved-sentinel')
        self._git('add', 'other-ref.txt')
        self._git('commit', '-qm', 'unapproved ref fixture')
        other = self._git('rev-parse', 'HEAD').stdout.strip()
        self._git('tag', 'unapproved-data')
        self._git('checkout', '--detach', self.head)
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}):
            validated = handoff.validate_request(request)
        with tempfile.TemporaryDirectory() as directory:
            git, isolated = handoff._prepare_isolated_workspace(validated, pathlib.Path(directory))
            def read(*args):
                return subprocess.run([str(git), '-C', str(isolated), *args], capture_output=True, text=True)
            self.assertEqual(read('rev-parse', 'HEAD').stdout.strip(), self.head)
            self.assertEqual(read('tag', '--list').stdout.strip(), '')
            self.assertNotEqual(read('cat-file', '-e', other).returncode, 0)
            self.assertFalse((isolated/'other-ref.txt').exists())
            self.assertFalse((isolated/'.git/FETCH_HEAD').exists())
            self.assertEqual(read('remote').stdout.strip(), '')

    def test_packet_failure_keeps_partial_patch_and_replay_never_launches(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        def partial(validated, workspace, *, on_started, before_launch):
            before_launch()
            on_started()
            (workspace/'README.md').write_text('partial packet work\n')
            (workspace/'new.txt').write_text('partial untracked work\n')
            return 1, b'', None
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=partial) as run:
            receipt = self._packet_attempt(request, packet, 'attempt-1', 0)
            self.assertEqual(receipt['status'], 'failed')
            self.assertEqual(receipt['packet']['status'], 'checkpointed')
            self.assertFalse(receipt['boundaries']['adapter_repository_write_performed'])
            self.assertEqual((self.workspace/'README.md').read_text(), 'fixture\n')
            ledger, patch = packet.read_checkpoint()
            self.assertIn(b'partial packet work', patch)
            self.assertIn(b'partial untracked work', patch)
            replay = self._packet_attempt(request, packet, 'attempt-1', 0)
            self.assertTrue(replay['packet']['replayed'])
            run.assert_called_once()
        self.assertTrue((directory/'synthetic-packet/attempt-attempt-1/workspace/new.txt').exists())

    def test_packet_uncertain_termination_retains_workspace_and_blocks_new_writer(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        def uncertain(validated, workspace, *, on_started, before_launch):
            before_launch()
            on_started(); (workspace/'new.txt').write_text('uncertain partial work')
            raise handoff.HandoffValidationError('termination_error', 'synthetic unproven stop')
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=uncertain) as run:
            receipt = self._packet_attempt(request, packet, 'attempt-1', 0)
            self.assertEqual(receipt['status'], 'unknown')
            with self.assertRaisesRegex(handoff.model_packet_store.PacketError, 'predecessor-outcome-unknown'):
                self._packet_attempt(request, packet, 'attempt-2', 2)
            run.assert_called_once()
        self.assertTrue((directory/'synthetic-packet/attempt-attempt-1/workspace/new.txt').exists())

    def test_packet_real_fake_process_nonzero_retains_changes_without_source_integration(self):
        self.executable.write_text(self.executable.read_text().replace('mode = os.environ.get("FAKE_CODEX_MODE", "success")', 'mode = "write-workspace"')+'\nsys.exit(1)\n')
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}):
            receipt = self._packet_attempt(request, packet, 'attempt-1', 0)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['failure_class'], 'nonzero_exit')
        self.assertEqual(receipt['packet']['status'], 'checkpointed')
        self.assertIn(b'changed by child', packet.read_checkpoint()[1])
        self.assertEqual((self.workspace/'README.md').read_text(), 'fixture\n')

    def test_packet_second_attempt_restores_checkpoint_in_a_new_private_workspace(self):
        request, target = self._typed_request(sandbox='workspace-write')
        directory = target.home/'packets'; directory.mkdir(mode=0o700)
        packet = handoff.model_packet_store.PacketStore(directory, 'synthetic-packet')
        self._prepare_packet_input(target, request, packet)
        paths = []
        def first(validated, workspace, *, on_started, before_launch):
            before_launch()
            paths.append(workspace); on_started()
            (workspace/'new.txt').write_text('first partial content\n')
            return 1, b'', None
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=first):
            self._packet_attempt(request, packet, 'attempt-1', 0)
        ledger, patch = packet.read_checkpoint()
        target.record['task']['checkpoint_sha256'] = ledger['checkpoint']
        for name, value in list(target.summary_values.items()):
            value = dict(value, task_sha256=handoff.model_execution_target.canonical_sha(target.record['task']))
            target.write_summary(name, value, refresh=False)
        target.refresh(); request['target_ref'] = target.ref
        def second(validated, workspace, *, on_started, before_launch):
            before_launch()
            paths.append(workspace); on_started()
            self.assertEqual((workspace/'new.txt').read_text(), 'first partial content\n')
            (workspace/'new.txt').write_text('second repair content\n')
            return 1, b'', None
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=second):
            receipt = self._packet_attempt(request, packet, 'attempt-2', ledger['revision'])
        self.assertEqual(receipt['packet']['status'], 'checkpointed')
        self.assertNotEqual(paths[0], paths[1])
        self.assertEqual((paths[0]/'new.txt').read_text(), 'first partial content\n')
        self.assertIn(b'second repair content', packet.read_checkpoint()[1])
        self.assertFalse((self.workspace/'new.txt').exists())
        ledger, _ = packet.read_checkpoint()
        target.record['task']['checkpoint_sha256'] = ledger['checkpoint']
        for name, value in list(target.summary_values.items()):
            target.write_summary(name, dict(value, task_sha256=handoff.model_execution_target.canonical_sha(target.record['task'])), refresh=False)
        target.refresh(); request['target_ref'] = target.ref
        request['sandbox'] = 'read-only'; request['authorization']['sandbox_ceiling'] = 'read-only'
        def readonly(validated, workspace, *, on_started, before_launch):
            before_launch()
            on_started()
            self.assertEqual((workspace/'new.txt').read_text(), 'second repair content\n')
            return 1, b'', None
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(target.home)}), mock.patch.object(handoff, '_run_child', side_effect=readonly):
            receipt = self._packet_attempt(request, packet, 'attempt-3', ledger['revision'])
        self.assertEqual(receipt['packet']['status'], 'checkpointed')
        self.assertEqual(receipt['failure_class'], 'nonzero_exit')

    def test_typed_start_only_and_raw_override_rejection(self):
        for operation in ["resume", "fork", "fresh-continuation"]:
            request, target = self._typed_request(); request["operation"] = operation
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}):
                result = self.execute(request=request)
            self.assertFalse(result["boundaries"]["session_call_performed"])
            self.assertFalse(result["capability"]["version_probe_performed"])
        request, target = self._typed_request(); request["model"] = "arbitrary"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}): result = self.execute(request=request)
        self.assertFalse(result["capability"]["version_probe_performed"])

    def test_typed_launch_rereads_artifacts_and_rejects_drift(self):
        request, target = self._typed_request()
        prepare = handoff._prepare_isolated_workspace
        def drift(*args, **kwargs):
            result = prepare(*args, **kwargs)
            (target.home/target.record["summaries"]["authorization"]["path"]).write_text("{}")
            return result
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(handoff, "_prepare_isolated_workspace", side_effect=drift):
            result = self.execute(request=request)
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertFalse(result["boundaries"]["session_call_performed"])
        self.assertEqual(result["execution_target"]["execution_state"], "not-started")

    def test_typed_missing_company_key_stops_before_child(self):
        request, target = self._typed_request(official=False)
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}):
            os.environ.pop("SYNTHETIC_MODEL_KEY", None)
            result = self.execute(request=request)
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertFalse(result["boundaries"]["session_call_performed"])
        self.assertEqual(result["message"], "target-credential-unavailable")

    def test_typed_write_reuses_private_clone_and_bounded_patch_apply(self):
        self.executable.write_text(self.executable.read_text().replace('mode = os.environ.get("FAKE_CODEX_MODE", "success")', 'mode = "write-workspace"'))
        request, target = self._typed_request(sandbox="workspace-write")
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}): result = self.execute(request=request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual((self.workspace/"README.md").read_text(), "changed by child\n")
        self.assertEqual((self.workspace/"new.txt").read_text(), "new child file\n")
        self.assertFalse((self.workspace/"typed-model-catalog.json").exists())
        self.assertTrue(result["boundaries"]["child_workspace_isolated"])

    def test_typed_target_revoked_after_child_cannot_integrate_patch(self):
        self.executable.write_text(self.executable.read_text().replace(
            'mode = os.environ.get("FAKE_CODEX_MODE", "success")', 'mode = "write-workspace"'))
        request, target = self._typed_request(sandbox="workspace-write")
        original_run = handoff._run_child

        def revoke_after_child(*args, **kwargs):
            result = original_run(*args, **kwargs)
            target.record["enabled"] = False
            target.refresh()
            return result

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(
            handoff, "_run_child", side_effect=revoke_after_child
        ):
            result = self.execute(request=request)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertTrue(result["boundaries"]["session_call_performed"])
        self.assertFalse(result["boundaries"]["adapter_repository_write_performed"])
        self.assertEqual((self.workspace/"README.md").read_text(), "fixture\n")
        self.assertFalse((self.workspace/"new.txt").exists())

    def test_typed_target_revoked_after_patch_check_cannot_integrate(self):
        self.executable.write_text(self.executable.read_text().replace(
            'mode = os.environ.get("FAKE_CODEX_MODE", "success")', 'mode = "write-workspace"'))
        request, target = self._typed_request(sandbox="workspace-write")
        original_git = handoff._run_isolated_git
        checked = []

        def revoke_after_check(git, argv, **kwargs):
            result = original_git(git, argv, **kwargs)
            if (argv[0] == "-C" and pathlib.Path(argv[1]).resolve() == self.workspace.resolve()
                    and "--check" in argv):
                checked.append(True)
                target.record["enabled"] = False
                target.refresh()
            return result

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(
            handoff, "_run_isolated_git", side_effect=revoke_after_check
        ):
            result = self.execute(request=request)
        self.assertEqual(checked, [True])
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertFalse(result["boundaries"]["adapter_repository_write_performed"])
        self.assertEqual((self.workspace/"README.md").read_text(), "fixture\n")
        self.assertFalse((self.workspace/"new.txt").exists())

    def test_typed_target_revoked_during_final_readback_cannot_integrate(self):
        self.executable.write_text(self.executable.read_text().replace(
            'mode = os.environ.get("FAKE_CODEX_MODE", "success")', 'mode = "write-workspace"'))
        request, target = self._typed_request(sandbox="workspace-write")
        original_git = handoff._run_isolated_git
        original_artifact = handoff.model_execution_target._artifact
        armed = []
        revoked = []

        def after_check(git, argv, **kwargs):
            result = original_git(git, argv, **kwargs)
            if (argv[0] == "-C" and pathlib.Path(argv[1]).resolve() == self.workspace.resolve()
                    and "--check" in argv):
                armed.append(True)
            return result

        def revoke_inside_resolve(*args, **kwargs):
            result = original_artifact(*args, **kwargs)
            if armed and not revoked:
                target.record["enabled"] = False
                target.refresh()
                revoked.append(True)
            return result

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(
            handoff, "_run_isolated_git", side_effect=after_check
        ), mock.patch.object(handoff.model_execution_target, "_artifact", side_effect=revoke_inside_resolve):
            result = self.execute(request=request)
        self.assertEqual(armed, [True])
        self.assertEqual(revoked, [True])
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertFalse(result["boundaries"]["adapter_repository_write_performed"])
        self.assertEqual((self.workspace/"README.md").read_text(), "fixture\n")
        self.assertFalse((self.workspace/"new.txt").exists())

    def test_typed_read_only_revocation_after_child_is_not_completed(self):
        request, target = self._typed_request()
        original_run = handoff._run_child

        def revoke_after_child(*args, **kwargs):
            result = original_run(*args, **kwargs)
            target.record["enabled"] = False
            target.refresh()
            return result

        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(
            handoff, "_run_child", side_effect=revoke_after_child
        ):
            result = self.execute(request=request)
        self.assertEqual(result["failure_class"], "execution_target_rejected")
        self.assertTrue(result["boundaries"]["session_call_performed"])
        self.assertEqual(result["execution_target"]["execution_state"], "started")

    def test_typed_target_expiring_during_final_readback_is_rejected(self):
        request, target = self._typed_request()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}):
            validated = handoff.validate_request(request)
        binding = validated.execution_target
        with mock.patch.object(handoff.model_execution_target, 'resolve', return_value=binding), \
                mock.patch.object(handoff.time, 'time', return_value=binding.valid_until):
            with self.assertRaisesRegex(handoff.HandoffValidationError, 'target-expired-during-readback'):
                handoff._verify_current_execution_target(validated)

    def test_typed_unapproved_executable_or_revocation_prevents_version_process(self):
        for mode in ["executable", "revoked"]:
            request, target = self._typed_request()
            summary = dict(target.summary_values["capability" if mode == "executable" else "authorization"])
            if mode == "executable": summary["executable_sha256"] = "0"*64
            else: summary["status"] = "revoked"
            target.write_summary("capability" if mode == "executable" else "authorization", summary)
            request["target_ref"] = target.ref
            with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(handoff, "_probe_version") as probe:
                result = self.execute(request=request)
            probe.assert_not_called()
            self.assertEqual(result["failure_class"], "execution_target_rejected")
            self.assertFalse(result["capability"]["version_probe_performed"])
            self.assertFalse(result["boundaries"]["session_call_performed"])

    def test_typed_source_project_config_stops_without_read_or_probe(self):
        directory = self.workspace/".codex"; directory.mkdir()
        (directory/"config.toml").write_text("model='synthetic-project-model'\n")
        self._git("add", ".codex/config.toml"); self._git("commit", "-q", "-m", "synthetic project config")
        self.head = self._git("rev-parse", "HEAD").stdout.strip()
        request, target = self._typed_request()
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(handoff, "_probe_version") as probe:
            result = self.execute(request=request)
        probe.assert_not_called()
        self.assertEqual(result["message"], "target-project-config-unqualified")
        self.assertFalse(result["boundaries"]["session_call_performed"])
        # Opt-out retains the prior executor contract.
        result = self.execute(request=self.request())
        self.assertEqual(result["status"], "completed")
        self.assertNotIn("execution_target", result)

    def test_typed_private_clone_project_config_stops_before_child(self):
        request, target = self._typed_request(); prepare = handoff._prepare_isolated_workspace
        def inject(*args, **kwargs):
            git, clone = prepare(*args, **kwargs)
            (clone/".codex").mkdir()
            (clone/".codex"/"config.toml").write_text("model='synthetic-project-model'\n")
            return git, clone
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}), mock.patch.object(handoff, "_prepare_isolated_workspace", side_effect=inject):
            result = self.execute(request=request)
        self.assertEqual(result["message"], "target-project-config-unqualified")
        self.assertFalse(result["boundaries"]["session_call_performed"])
        self.assertEqual(result["execution_target"]["execution_state"], "not-started")

    def test_typed_dirty_source_still_rejected_before_probe(self):
        request, target = self._typed_request()
        (self.workspace/"README.md").write_text("dirty")
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(target.home)}): result = self.execute(request=request)
        self.assertFalse(result["capability"]["version_probe_performed"])
        self.assertFalse(result["boundaries"]["session_call_performed"])

    def test_start_success_uses_fixed_argv_and_emits_bounded_receipt(self) -> None:
        request = self.request()
        response = self.execute(request=request)

        self.assertEqual("completed", response["status"])
        self.assertEqual(SESSION_ID, response["result"]["session_id"])
        self.assertEqual("turn.completed", response["result"]["terminal_event"])
        self.assertEqual("9.8.7", response["capability"]["cli_version"])
        self.assertRegex(
            response["capability"]["executable_sha256"], r"^[0-9a-f]{64}$"
        )
        self.assertRegex(response["target"]["workspace"], r"^git-worktree:[0-9a-f]{12}$")
        self.assertNotIn(str(self.executable), json.dumps(response))
        self.assertNotIn(request["prompt"], json.dumps(response))
        self.assertFalse(response["boundaries"]["shell_used"])
        self.assertTrue(response["boundaries"]["child_workspace_isolated"])
        self.assertTrue(response["boundaries"]["child_summary_omitted"])
        self.assertFalse(
            response["boundaries"]["adapter_repository_write_performed"]
        )
        self.assertTrue(response["boundaries"]["parent_integration_required"])
        self.assertFalse(response["boundaries"]["repository_completion_claimed"])

        argv = json.loads(self.capture.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "-c",
                'shell_environment_policy.inherit="core"',
                "-c",
                "shell_environment_policy.ignore_default_excludes=false",
                "--cd",
            ],
            argv[:9],
        )
        self.assertNotEqual(str(self.workspace.resolve()), argv[9])
        self.assertIn("codex-cli-handoff-", argv[9])
        self.assertFalse(pathlib.Path(argv[9]).exists())
        self.assertEqual(
            ["exec", "--ignore-user-config", "--json", "-"],
            argv[10:],
        )
        delivered_prompt = self.prompt_capture.read_text(encoding="utf-8")
        self.assertEqual(
            "no-publication-no-recursion/v1",
            handoff.PROMPT_BOUNDARY_VERSION,
        )
        self.assertTrue(delivered_prompt.startswith(str(request["prompt"])))
        self.assertTrue(delivered_prompt.endswith(handoff.PROMPT_BOUNDARY_APPENDIX))
        for boundary in (
            "Do not commit.",
            "Do not push.",
            "Do not open pull requests.",
            "Do not merge.",
            "Do not perform platform writes.",
            "Do not dispatch another session.",
            "scripts/project-python",
            "do not replace it with bare system Python",
            "report verification as blocked",
        ):
            self.assertIn(boundary, delivered_prompt)

    def test_resume_requires_exact_uuid_and_uses_resume_argv(self) -> None:
        request = self.request(operation="resume", session_id=SESSION_ID)
        response = self.execute(request=request)

        self.assertEqual("completed", response["status"])
        argv = json.loads(self.capture.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "-c",
                'shell_environment_policy.inherit="core"',
                "-c",
                "shell_environment_policy.ignore_default_excludes=false",
                "--cd",
            ],
            argv[:9],
        )
        self.assertNotEqual(str(self.workspace.resolve()), argv[9])
        self.assertIn("codex-cli-handoff-", argv[9])
        self.assertEqual(
            [
                "exec",
                "resume",
                "--ignore-user-config",
                "--json",
                SESSION_ID,
                "-",
            ],
            argv[10:],
        )

        invalid = self.execute(
            request=self.request(operation="resume", session_id="--last")
        )
        self.assertEqual("stopped", invalid["status"])
        self.assertEqual("target_mismatch", invalid["failure_class"])

        mismatched = self.execute(
            mode="different-session",
            request=self.request(operation="resume", session_id=SESSION_ID),
        )
        self.assertEqual("failed", mismatched["status"])
        self.assertEqual("session_id_mismatch", mismatched["failure_class"])

    def test_fork_requires_source_uuid_and_accepts_new_session_id(self) -> None:
        response = self.execute(
            mode="different-session",
            request=self.request(operation="fork", session_id=SESSION_ID),
        )

        self.assertEqual("completed", response["status"])
        self.assertNotEqual(SESSION_ID, response["result"]["session_id"])
        argv = json.loads(self.capture.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                "exec",
                "fork",
                "--ignore-user-config",
                "--json",
                SESSION_ID,
                "-",
            ],
            argv[10:],
        )

        missing = self.execute(request=self.request(operation="fork"))
        self.assertEqual("stopped", missing["status"])
        self.assertEqual("validation_error", missing["failure_class"])

        invalid = self.execute(
            request=self.request(operation="fork", session_id="--last")
        )
        self.assertEqual("stopped", invalid["status"])
        self.assertEqual("target_mismatch", invalid["failure_class"])

        unchanged = self.execute(
            request=self.request(operation="fork", session_id=SESSION_ID)
        )
        self.assertEqual("failed", unchanged["status"])
        self.assertEqual("session_id_mismatch", unchanged["failure_class"])

    def test_workspace_write_requires_matching_authorized_ceiling(self) -> None:
        denied = self.execute(request=self.request(sandbox="workspace-write"))
        self.assertEqual("stopped", denied["status"])
        self.assertEqual("permission_widening", denied["failure_class"])

        authorization = dict(self.request()["authorization"])
        authorization["sandbox_ceiling"] = "workspace-write"
        allowed = self.execute(
            request=self.request(
                sandbox="workspace-write", authorization=authorization
            )
        )
        self.assertEqual("completed", allowed["status"])

    def test_isolation_failure_does_not_claim_session_call(self) -> None:
        with mock.patch.object(
            handoff,
            "_prepare_isolated_workspace",
            side_effect=handoff.HandoffValidationError(
                "isolation_error",
                "A private execution workspace could not be created.",
            ),
        ):
            response = self.execute()

        self.assertEqual("failed", response["status"])
        self.assertEqual("isolation_error", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_private_workspace_discards_read_only_changes_and_integrates_write(self) -> None:
        read_only = self.execute(mode="write-workspace")
        self.assertEqual("completed", read_only["status"])
        self.assertEqual(
            "fixture\n",
            (self.workspace / "README.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((self.workspace / "new.txt").exists())

        authorization = dict(self.request()["authorization"])
        authorization["sandbox_ceiling"] = "workspace-write"
        workspace_write = self.execute(
            mode="write-workspace",
            request=self.request(
                sandbox="workspace-write",
                authorization=authorization,
            ),
        )
        self.assertEqual("completed", workspace_write["status"])
        self.assertTrue(
            workspace_write["boundaries"]["adapter_repository_write_performed"]
        )
        self.assertEqual(
            "changed by child\n",
            (self.workspace / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "new child file\n",
            (self.workspace / "new.txt").read_text(encoding="utf-8"),
        )

    def test_private_workspace_integrates_staged_child_changes(self) -> None:
        authorization = dict(self.request()["authorization"])
        authorization["sandbox_ceiling"] = "workspace-write"
        response = self.execute(
            mode="write-staged",
            request=self.request(
                sandbox="workspace-write",
                authorization=authorization,
            ),
        )

        self.assertEqual("completed", response["status"])
        self.assertEqual(
            "changed by child\n",
            (self.workspace / "README.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            "new child file\n",
            (self.workspace / "new.txt").read_text(encoding="utf-8"),
        )

    def test_private_workspace_rejects_child_commit(self) -> None:
        authorization = dict(self.request()["authorization"])
        authorization["sandbox_ceiling"] = "workspace-write"
        response = self.execute(
            mode="write-commit",
            request=self.request(
                sandbox="workspace-write",
                authorization=authorization,
            ),
        )

        self.assertEqual("failed", response["status"])
        self.assertEqual("child_boundary_violation", response["failure_class"])
        self.assertEqual(self.head, self._git("rev-parse", "HEAD").stdout.strip())
        self.assertEqual(
            "fixture\n",
            (self.workspace / "README.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((self.workspace / "new.txt").exists())

    def test_workspace_change_before_patch_integration_fails_closed(self) -> None:
        authorization = dict(self.request()["authorization"])
        authorization["sandbox_ceiling"] = "workspace-write"
        original_capture = handoff._capture_isolated_patch

        def capture_then_mutate(*args: object) -> bytes:
            patch = original_capture(*args)
            (self.workspace / "parent.txt").write_text(
                "parent mutation\n", encoding="utf-8"
            )
            return patch

        with mock.patch.object(
            handoff,
            "_capture_isolated_patch",
            side_effect=capture_then_mutate,
        ):
            response = self.execute(
                mode="write-workspace",
                request=self.request(
                    sandbox="workspace-write",
                    authorization=authorization,
                ),
            )

        self.assertEqual("failed", response["status"])
        self.assertEqual("dirty_workspace", response["failure_class"])
        self.assertEqual(
            "fixture\n",
            (self.workspace / "README.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((self.workspace / "new.txt").exists())
        self.assertEqual(
            "parent mutation\n",
            (self.workspace / "parent.txt").read_text(encoding="utf-8"),
        )

    def test_missing_authorization_never_starts_session(self) -> None:
        authorization = dict(self.request()["authorization"])
        authorization["marker"] = ""
        response = self.execute(
            request=self.request(authorization=authorization)
        )

        self.assertEqual("stopped", response["status"])
        self.assertEqual("authorization_missing", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])
        self.assertFalse(self.capture.exists())

    def test_unknown_fields_and_boolean_schema_fail_closed(self) -> None:
        unknown = self.execute(request=self.request(extra_flags=["--unsafe"]))
        self.assertEqual("stopped", unknown["status"])
        self.assertEqual("validation_error", unknown["failure_class"])

        authorization = dict(self.request()["authorization"])
        authorization["extra"] = True
        unknown_authorization = self.execute(
            request=self.request(authorization=authorization)
        )
        self.assertEqual("stopped", unknown_authorization["status"])
        self.assertEqual(
            "validation_error", unknown_authorization["failure_class"]
        )

        boolean_schema = self.execute(request=self.request(schema_version=True))
        self.assertEqual("stopped", boolean_schema["status"])
        self.assertEqual("validation_error", boolean_schema["failure_class"])

        invalid_operation = self.request(operation=["start"])
        invalid_type = handoff.execute_handoff(invalid_operation)
        self.assertEqual("stopped", invalid_type["status"])
        self.assertIsNone(invalid_type["operation"])

        non_string_key = self.request()
        non_string_key[1] = "unexpected"
        invalid_key = handoff.execute_handoff(non_string_key)
        self.assertEqual("stopped", invalid_key["status"])
        self.assertEqual("validation_error", invalid_key["failure_class"])

    def test_dashboard_and_queue_remain_outside_private_clone_executor(self) -> None:
        for operation in ("agents-dashboard", "manual-queue", "queue"):
            with self.subTest(operation=operation):
                response = self.execute(
                    request=self.request(operation=operation, session_id=SESSION_ID)
                )
                self.assertEqual("stopped", response["status"])
                self.assertEqual("validation_error", response["failure_class"])
                self.assertFalse(response["boundaries"]["session_call_performed"])
                self.assertFalse(self.capture.exists())

    def test_untrusted_version_text_is_not_returned(self) -> None:
        marker = "api_key-should-not-echo"
        with mock.patch.dict(
            os.environ,
            {
                "FAKE_CODEX_MODE": "success",
                "FAKE_CODEX_CAPTURE": str(self.capture),
                "FAKE_CODEX_VERSION": marker,
            },
        ):
            response = handoff.execute_handoff(self.request())

        self.assertEqual("fallback", response["status"])
        self.assertEqual("capability_unavailable", response["failure_class"])
        self.assertNotIn(marker, json.dumps(response))

    def test_version_probe_timeout_and_output_are_bounded(self) -> None:
        capture_type = handoff.Capture
        terminate = handoff._terminate_process_group
        for mode, timeout, expected_overflow in (
            ("timeout", 0.1, None),
            ("stdout-overflow", 2, "stdout"),
        ):
            with self.subTest(mode=mode):
                captures = []
                termination_overflows = []

                def record_capture(**kwargs):
                    capture = capture_type(**kwargs)
                    captures.append(capture)
                    return capture

                def record_termination(process, tracker=None):
                    termination_overflows.append(captures[0].overflow_stream)
                    return terminate(process, tracker)

                with mock.patch.dict(
                    os.environ,
                    {"FAKE_CODEX_VERSION_MODE": mode},
                ), mock.patch.object(
                    handoff, "VERSION_TIMEOUT_SECONDS", timeout
                ), mock.patch.object(
                    handoff, "Capture", side_effect=record_capture
                ), mock.patch.object(
                    handoff, "_terminate_process_group", side_effect=record_termination
                ):
                    response = self.execute()

                self.assertTrue(termination_overflows, response)
                self.assertEqual(expected_overflow, termination_overflows[0], response)
                self.assertEqual("fallback", response["status"], response)
                self.assertEqual(
                    "capability_unavailable", response["failure_class"], response
                )
                self.assertTrue(response["capability"]["version_probe_performed"])
                self.assertIsNone(response["capability"]["cli_version"])
                self.assertFalse(response["boundaries"]["session_call_performed"])
                self.assertFalse(self.capture.exists())

    def test_quick_overflow_fixture_preserves_natural_exit(self) -> None:
        environment = {**os.environ, "FAKE_CODEX_VERSION_MODE": "stdout-overflow-quick"}
        result = subprocess.run(
            [str(self.executable), "--version"], env=environment,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=3, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b"x" * 8192, result.stdout)
        self.assertEqual(b"", result.stderr)

    def test_version_probe_identity_permission_error_stops(self) -> None:
        identity = handoff._process_identity
        injected = False

        def deny_first_identity(pid):
            nonlocal injected
            if not injected:
                injected = True
                raise PermissionError(errno.EPERM, "synthetic identity denial")
            return identity(pid)

        with mock.patch.dict(
            os.environ, {"FAKE_CODEX_VERSION_MODE": "timeout"}
        ), mock.patch.object(handoff, "_process_identity", side_effect=deny_first_identity):
            response = self.execute()

        self.assertTrue(injected)
        self.assertEqual("stopped", response["status"], response)
        self.assertEqual("termination_error", response["failure_class"], response)
        self.assertIn("stage=root-identity; errno=1", response["message"])
        self.assertTrue(response["capability"]["version_probe_performed"])
        self.assertFalse(response["boundaries"]["session_call_performed"])
        self.assertFalse(self.capture.exists())

    def test_version_probe_signal_permission_error_stops(self) -> None:
        killpg = handoff.os.killpg
        injected = False

        def deny_first_signal(pid, sig):
            nonlocal injected
            if not injected:
                injected = True
                raise PermissionError(errno.EPERM, "synthetic signal denial")
            return killpg(pid, sig)

        with mock.patch.dict(
            os.environ, {"FAKE_CODEX_VERSION_MODE": "timeout"}
        ), mock.patch.object(
            handoff, "VERSION_TIMEOUT_SECONDS", 0.1
        ), mock.patch.object(handoff.os, "killpg", side_effect=deny_first_signal):
            response = self.execute()

        self.assertTrue(injected)
        self.assertEqual("stopped", response["status"], response)
        self.assertEqual("termination_error", response["failure_class"], response)
        self.assertEqual("The Codex process group could not be signaled.", response["message"])
        self.assertTrue(response["capability"]["version_probe_performed"])
        self.assertFalse(response["boundaries"]["session_call_performed"])
        self.assertFalse(self.capture.exists())

    def test_version_probe_launch_failure_does_not_claim_performed(self) -> None:
        popen = handoff.subprocess.Popen
        denied = False

        def deny_probe(argv, **kwargs):
            nonlocal denied
            if (
                len(argv) == 2
                and argv[1] == "--version"
                and pathlib.Path(argv[0]).resolve() == self.executable.resolve()
            ):
                denied = True
                raise PermissionError(errno.EPERM, "synthetic launch denial")
            return popen(argv, **kwargs)

        with mock.patch.object(handoff.subprocess, "Popen", side_effect=deny_probe):
            response = self.execute()

        self.assertTrue(denied)
        self.assertEqual("fallback", response["status"])
        self.assertEqual("capability_unavailable", response["failure_class"])
        self.assertFalse(response["capability"]["version_probe_performed"])
        self.assertIsNone(response["capability"]["cli_version"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_rollover_rejection_preserves_completed_probe_facts(self) -> None:
        with mock.patch.object(
            handoff, "_claim_rollover",
            side_effect=handoff.HandoffValidationError(
                "continuity_replay_state_unavailable", "synthetic replay-state rejection"
            ),
        ):
            response = self.execute()

        self.assertEqual("stopped", response["status"])
        self.assertEqual("continuity_replay_state_unavailable", response["failure_class"])
        self.assertTrue(response["capability"]["version_probe_performed"])
        self.assertEqual("9.8.7", response["capability"]["cli_version"])
        self.assertEqual(
            hashlib.sha256(self.executable.read_bytes()).hexdigest(),
            response["capability"]["executable_sha256"],
        )
        self.assertEqual(self.head, response["target"]["observed_head"])
        self.assertFalse(response["boundaries"]["session_call_performed"])
        self.assertFalse(self.capture.exists())

    def test_non_posix_host_falls_back_before_runtime_probe(self) -> None:
        with mock.patch.object(handoff.os, "name", "nt"):
            response = handoff.execute_handoff(self.request())

        self.assertEqual("fallback", response["status"])
        self.assertEqual("capability_unavailable", response["failure_class"])
        self.assertFalse(response["capability"]["version_probe_performed"])

    def test_dirty_or_wrong_head_workspace_stops(self) -> None:
        wrong_head = self.execute(request=self.request(expected_head="0" * 40))
        self.assertEqual("target_mismatch", wrong_head["failure_class"])

        (self.workspace / "dirty.txt").write_text("dirty\n", encoding="utf-8")
        dirty = self.execute()
        self.assertEqual("stopped", dirty["status"])
        self.assertEqual("dirty_workspace", dirty["failure_class"])

    def test_ambient_git_targeting_cannot_confuse_workspace_identity(self) -> None:
        other_workspace = self.root / "other-workspace"
        other_workspace.mkdir()
        for args in (
            ("init", "-q"),
            ("config", "user.name", "Other User"),
            ("config", "user.email", "other@example.invalid"),
        ):
            subprocess.run(
                ["git", "-C", str(other_workspace), *args],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        (other_workspace / "README.md").write_text(
            "fixture\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(other_workspace), "add", "README.md"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(other_workspace),
                "commit",
                "-q",
                "-m",
                "other fixture",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        other_head = subprocess.run(
            ["git", "-C", str(other_workspace), "rev-parse", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
        self.assertNotEqual(self.head, other_head)

        hostile_environment = {
            "GIT_DIR": str(other_workspace / ".git"),
            "GIT_WORK_TREE": str(self.workspace),
            "GIT_INDEX_FILE": str(other_workspace / ".git" / "index"),
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.bare",
            "GIT_CONFIG_VALUE_0": "false",
        }
        with mock.patch.dict(os.environ, hostile_environment):
            mismatched = self.execute(
                request=self.request(expected_head=other_head)
            )
            accepted = self.execute(request=self.request(expected_head=self.head))

        self.assertEqual("stopped", mismatched["status"])
        self.assertEqual("target_mismatch", mismatched["failure_class"])
        self.assertFalse(mismatched["boundaries"]["session_call_performed"])
        self.assertEqual("completed", accepted["status"])

    def test_repository_controlled_executable_falls_back(self) -> None:
        repository_executable = self.workspace / "fake-codex"
        repository_executable.write_text(
            f"#!{sys.executable}\n{FAKE_CODEX}", encoding="utf-8"
        )
        repository_executable.chmod(
            repository_executable.stat().st_mode | stat.S_IXUSR
        )
        self._git("add", "fake-codex")
        self._git("commit", "-q", "-m", "fixture executable")
        head = self._git("rev-parse", "HEAD").stdout.strip()
        response = self.execute(
            request=self.request(
                codex_executable=str(repository_executable),
                expected_head=head,
            )
        )

        self.assertEqual("fallback", response["status"])
        self.assertEqual("capability_unavailable", response["failure_class"])

    def test_external_symlink_resolves_without_path_disclosure(self) -> None:
        symlink = self.root / "codex-link"
        symlink.symlink_to(self.executable)
        response = self.execute(
            request=self.request(codex_executable=str(symlink))
        )

        self.assertEqual("completed", response["status"])
        self.assertNotIn(str(symlink), json.dumps(response))
        self.assertNotIn(str(self.executable), json.dumps(response))

    def test_invalid_paths_and_operations_do_not_leak_into_receipt(self) -> None:
        sensitive_name = "private-machine-path-marker"
        missing_workspace = self.root / sensitive_name / "missing"
        response = self.execute(
            request=self.request(workspace=str(missing_workspace))
        )
        serialized = json.dumps(response)
        self.assertEqual("stopped", response["status"])
        self.assertNotIn(sensitive_name, serialized)
        self.assertIsNone(response["target"]["workspace"])

        operation = "api_key=should-not-echo"
        invalid_operation = self.execute(
            request=self.request(operation=operation)
        )
        self.assertIsNone(invalid_operation["operation"])
        self.assertNotIn(operation, json.dumps(invalid_operation))

    def test_malformed_duplicate_and_failed_events_fail_closed(self) -> None:
        cases = (
            ("malformed", "malformed_jsonl"),
            ("duplicate-json-key", "malformed_jsonl"),
            ("terminal-before-session", "malformed_jsonl"),
            ("summary-before-session", "malformed_jsonl"),
            ("summary-after-terminal", "malformed_jsonl"),
            ("duplicate-session", "missing_or_duplicate_session_id"),
            ("duplicate-terminal", "missing_or_duplicate_terminal_event"),
            ("missing-summary", "missing_final_summary"),
            ("turn-failed", "cli_reported_failure"),
        )
        for mode, failure_class in cases:
            with self.subTest(mode=mode):
                response = self.execute(mode=mode)
                self.assertEqual("failed", response["status"])
                self.assertEqual(failure_class, response["failure_class"])
                self.assertTrue(response["boundaries"]["session_call_performed"])

    def test_nonzero_timeout_and_output_limits_fail_closed(self) -> None:
        nonzero = self.execute(mode="nonzero")
        self.assertEqual("failed", nonzero["status"])
        self.assertEqual("nonzero_exit", nonzero["failure_class"])
        self.assertEqual(7, nonzero["result"]["exit_status"])

        with mock.patch.object(handoff, "MIN_TIMEOUT_SECONDS", 1):
            timeout = self.execute(
                mode="timeout", request=self.request(timeout_seconds=1)
            )
        self.assertEqual("failed", timeout["status"])
        self.assertEqual("timeout", timeout["failure_class"])

        for mode in ("stdout-overflow", "stderr-overflow"):
            with self.subTest(mode=mode):
                overflow = self.execute(mode=mode)
                self.assertEqual("failed", overflow["status"])
                self.assertEqual("output_limit", overflow["failure_class"])

    @unittest.skipUnless(os.name == "posix", "process-tree assertion is POSIX-only")
    def test_timeout_terminates_detached_descendant(self) -> None:
        descendant_pid: int | None = None
        try:
            with mock.patch.object(handoff, "MIN_TIMEOUT_SECONDS", 1):
                response = self.execute(
                    mode="detached-descendant",
                    request=self.request(timeout_seconds=1),
                )
            self.assertEqual("failed", response["status"])
            self.assertEqual("timeout", response["failure_class"])
            descendant_pid = int(
                self.descendant_pid_capture.read_text(encoding="utf-8")
            )
            with self.assertRaises(ProcessLookupError):
                os.kill(descendant_pid, 0)
        finally:
            if descendant_pid is not None:
                try:
                    os.killpg(descendant_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    @unittest.skipUnless(os.name == "posix", "process-group assertion is POSIX-only")
    def test_keyboard_interrupt_terminates_child_process_group(self) -> None:
        environment = {
            "FAKE_CODEX_MODE": "timeout",
            "FAKE_CODEX_CAPTURE": str(self.capture),
            "FAKE_CODEX_PROMPT_CAPTURE": str(self.prompt_capture),
            "FAKE_CODEX_PID_CAPTURE": str(self.pid_capture),
        }
        sleep_calls = 0

        def interrupt_once(_seconds: float) -> None:
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 3:
                raise KeyboardInterrupt
            time.sleep(0.05)

        with mock.patch.dict(os.environ, environment), mock.patch.object(
            handoff, "_poll_sleep", side_effect=interrupt_once
        ):
            response = handoff.execute_handoff(self.request())

        self.assertEqual("failed", response["status"])
        self.assertEqual("interrupted", response["failure_class"])
        pid = int(self.pid_capture.read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_executable_measurement_failure_and_change_fail_closed(self) -> None:
        with mock.patch.object(
            handoff,
            "_sha256_file",
            side_effect=handoff.HandoffValidationError(
                "capability_unavailable",
                "Codex executable could not be measured safely.",
            ),
        ):
            unavailable = self.execute()
        self.assertEqual("fallback", unavailable["status"])
        self.assertEqual("capability_unavailable", unavailable["failure_class"])

        with mock.patch.object(
            handoff,
            "_sha256_file",
            side_effect=["a" * 64, "b" * 64],
        ):
            changed = self.execute()
        self.assertEqual("failed", changed["status"])
        self.assertEqual("executable_changed", changed["failure_class"])
        self.assertFalse(changed["boundaries"]["session_call_performed"])

    def test_process_tree_inventory_failure_cannot_return_success(self) -> None:
        original_tracker = handoff.ProcessTreeTracker
        tracker_count = 0

        class FailingTracker(original_tracker):
            def stop(self) -> None:
                super().stop()
                with self._lock:
                    self._error = True

        def tracker_factory(root_pid: int) -> handoff.ProcessTreeTracker:
            nonlocal tracker_count
            tracker_count += 1
            if tracker_count == 1:
                return original_tracker(root_pid)
            return FailingTracker(root_pid)

        with mock.patch.object(
            handoff, "ProcessTreeTracker", side_effect=tracker_factory
        ):
            response = self.execute()

        self.assertEqual("failed", response["status"])
        self.assertEqual("termination_error", response["failure_class"])

    def test_pid_reuse_token_is_not_signaled(self) -> None:
        with mock.patch.object(
            handoff,
            "_process_identity",
            return_value=(1, "replacement-token"),
        ), mock.patch.object(handoff.os, "kill") as kill:
            handoff._signal_pid(
                12345,
                "original-token",
                signal.SIGTERM,
            )

        kill.assert_not_called()

    def test_summary_is_omitted_instead_of_redacted(self) -> None:
        response = self.execute(mode="sensitive-summary")
        summary = response["result"]["final_summary"]

        self.assertEqual("completed", response["status"])
        self.assertEqual(handoff.OMITTED_FINAL_SUMMARY, summary)
        self.assertNotIn("alice", summary)
        self.assertNotIn("topsecret", summary)
        self.assertNotIn("sk-abcdefgh123456", summary)

    def test_summary_omission_covers_common_secret_shapes(self) -> None:
        response = self.execute(mode="sensitive-summary")
        summary = response["result"]["final_summary"]

        self.assertEqual("completed", response["status"])
        self.assertEqual(handoff.OMITTED_FINAL_SUMMARY, summary)

    def test_sparse_checkout_and_submodule_worktrees_fall_back(self) -> None:
        sparse = self._git("sparse-checkout", "init", "--cone")
        self.assertEqual(0, sparse.returncode)
        sparse_response = self.execute()
        self.assertEqual("fallback", sparse_response["status"])
        self.assertEqual(
            "capability_unavailable", sparse_response["failure_class"]
        )
        self._git("sparse-checkout", "disable")

        dependency = self.root / "dependency"
        dependency.mkdir()
        subprocess.run(
            ["git", "-C", str(dependency), "init", "-q"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(dependency), "config", "user.name", "Fixture"],
            check=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(dependency),
                "config",
                "user.email",
                "fixture@example.invalid",
            ],
            check=True,
        )
        (dependency / "dep.txt").write_text("dependency\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(dependency), "add", "dep.txt"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(dependency), "commit", "-q", "-m", "dependency"],
            check=True,
        )
        self._git(
            "-c",
            "protocol.file.allow=always",
            "submodule",
            "add",
            "-q",
            str(dependency),
            "dependency",
        )
        self._git("commit", "-q", "-am", "add submodule")
        submodule_head = self._git("rev-parse", "HEAD").stdout.strip()

        submodule_response = self.execute(
            request=self.request(expected_head=submodule_head)
        )
        self.assertEqual("fallback", submodule_response["status"])
        self.assertEqual(
            "capability_unavailable", submodule_response["failure_class"]
        )

    def test_request_reader_rejects_duplicate_json_keys(self) -> None:
        request_path = self.root / "duplicate-request.json"
        request_path.write_text(
            '{"schema_version":1,"schema_version":1}',
            encoding="utf-8",
        )

        with self.assertRaises(handoff.HandoffValidationError) as context:
            handoff._read_request(str(request_path))
        self.assertEqual("validation_error", context.exception.failure_class)

        oversized_path = self.root / "oversized-request.json"
        oversized_path.write_bytes(b"x" * (handoff.MAX_PROMPT_BYTES * 2 + 1))
        with self.assertRaises(handoff.HandoffValidationError) as oversized:
            handoff._read_request(str(oversized_path))
        self.assertEqual("validation_error", oversized.exception.failure_class)

    def test_sensitive_or_dangerous_prompt_stops_before_session(self) -> None:
        required = (
            " Do not dispatch another session. Do not commit. Do not push. "
            "Do not open pull requests. Do not merge. "
            "Do not perform platform writes."
        )
        for prompt, failure_class in (
            ("Use api_key=topsecret for this task." + required, "sensitive_input"),
            ("Run with danger-full-access." + required, "forbidden_prompt"),
            ("Read ~/.codex/auth.json." + required, "forbidden_prompt"),
        ):
            with self.subTest(prompt=prompt):
                if self.capture.exists():
                    self.capture.unlink()
                response = self.execute(request=self.request(prompt=prompt))
                self.assertEqual("stopped", response["status"])
                self.assertEqual(failure_class, response["failure_class"])
                self.assertFalse(self.capture.exists())

    def test_missing_prompt_boundary_stops_before_session(self) -> None:
        response = self.execute(
            request=self.request(prompt_boundary_version="")
        )

        self.assertEqual("stopped", response["status"])
        self.assertEqual("prompt_boundary_missing", response["failure_class"])
        self.assertFalse(self.capture.exists())

    def test_recursive_handoff_stops_before_version_or_session_call(self) -> None:
        if self.capture.exists():
            self.capture.unlink()
        with mock.patch.dict(os.environ, {handoff.HANDOFF_DEPTH_ENV: "1"}):
            response = handoff.execute_handoff(self.request())

        self.assertEqual("stopped", response["status"])
        self.assertEqual("recursive_handoff", response["failure_class"])
        self.assertFalse(self.capture.exists())

    def test_fresh_continuation_binds_checkpoint_and_uses_new_exec_session(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        response = self.execute(request=request)
        self.assertEqual("completed", response["status"])
        self.assertEqual("rollover-1", response["result"]["rollover_id"])
        self.assertRegex(response["result"]["checkpoint_sha256"], r"^[0-9a-f]{64}$")
        argv = json.loads(self.capture.read_text(encoding="utf-8"))
        self.assertEqual(["exec", "--ignore-user-config", "--json", "-"], argv[10:])
        prompt = self.prompt_capture.read_text(encoding="utf-8")
        self.assertIn("Fresh-context continuation checkpoint", prompt)
        self.assertIn("rollover-1", prompt)
        self.assertTrue(response["boundaries"]["durable_replay_record_written"])
        self.assertEqual(
            response["result"]["session_id"],
            response["result"]["destination_writer_runtime_id"],
        )

    def test_fresh_continuation_negative_paths_do_not_call_cli(self) -> None:
        variants = []
        interactive = self.continuity_assessment()
        interactive["runtime"]["mode"] = "interactive"
        variants.append(interactive)
        missing = self.continuity_assessment()
        missing["runtime"] = {"surface": "cli", "control_surface": "none", "mode": "non-interactive"}
        variants.append(missing)
        not_stopped = self.continuity_assessment()
        not_stopped["checkpoint"]["source_stop_writing_confirmed"] = False
        variants.append(not_stopped)
        for assessment in variants:
            with self.subTest(runtime=assessment["runtime"]):
                if self.capture.exists():
                    self.capture.unlink()
                response = self.execute(
                    request=self.request(
                        operation="fresh-continuation",
                        continuity_assessment=assessment,
                    )
                )
                self.assertEqual("stopped", response["status"])
                self.assertEqual("continuity_contract_rejected", response["failure_class"])
                self.assertFalse(self.capture.exists())

    def test_fresh_continuation_idempotent_replay_is_noop(self) -> None:
        assessment = self.continuity_assessment()
        digest = handoff.context_continuity.checkpoint_sha256(assessment["checkpoint"])
        assessment["lineage"]["seen_rollovers"] = [
            {"rollover_id": "rollover-1", "checkpoint_sha256": digest}
        ]
        response = self.execute(
            request=self.request(
                operation="fresh-continuation", continuity_assessment=assessment
            )
        )
        self.assertEqual("stopped", response["status"])
        self.assertEqual("idempotent_rollover_replay", response["failure_class"])
        self.assertFalse(self.capture.exists())

    def test_fresh_continuation_exact_request_replay_uses_durable_barrier(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        first = self.execute(request=request)
        self.assertEqual("completed", first["status"])
        self.capture.unlink()
        second = self.execute(request=request)
        self.assertEqual("stopped", second["status"])
        self.assertEqual("idempotent_rollover_replay", second["failure_class"])
        self.assertFalse(self.capture.exists())

    def test_fresh_continuation_same_checkpoint_new_id_is_runtime_conflict(self) -> None:
        first_assessment = self.continuity_assessment()
        first = self.execute(
            request=self.request(
                operation="fresh-continuation",
                continuity_assessment=first_assessment,
            )
        )
        self.assertEqual("completed", first["status"])
        self.capture.unlink()
        second_assessment = self.continuity_assessment()
        second_assessment["lineage"]["rollover_id"] = "rollover-2"
        second = self.execute(
            request=self.request(
                operation="fresh-continuation",
                continuity_assessment=second_assessment,
            )
        )
        self.assertEqual("stopped", second["status"])
        self.assertEqual("continuity_replay_conflict", second["failure_class"])
        self.assertFalse(self.capture.exists())

    def test_fresh_continuation_concurrent_same_checkpoint_has_one_winner(self) -> None:
        first = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        second = copy.deepcopy(first)
        second["continuity_assessment"]["lineage"]["rollover_id"] = "rollover-2"
        environment = {
            "FAKE_CODEX_MODE": "success",
            "FAKE_CODEX_CAPTURE": str(self.capture),
            "FAKE_CODEX_PROMPT_CAPTURE": str(self.prompt_capture),
        }
        with mock.patch.dict(os.environ, environment):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(handoff.execute_handoff, (first, second)))
        self.assertEqual(1, sum(item["status"] == "completed" for item in results))
        loser = next(item for item in results if item["status"] != "completed")
        self.assertIn(
            loser["failure_class"],
            {
                "continuity_replay_conflict",
                "continuity_replay_state_busy",
                "continuity_replay_state_unavailable",
            },
        )
        self.assertFalse(loser["boundaries"]["session_call_performed"])

    def test_fresh_continuation_concurrent_same_id_has_one_winner(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        environment = {
            "FAKE_CODEX_MODE": "success",
            "FAKE_CODEX_CAPTURE": str(self.capture),
            "FAKE_CODEX_PROMPT_CAPTURE": str(self.prompt_capture),
        }
        with mock.patch.dict(os.environ, environment):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(
                    pool.map(handoff.execute_handoff, (request, copy.deepcopy(request)))
                )
        self.assertEqual(1, sum(item["status"] == "completed" for item in results))
        loser = next(item for item in results if item["status"] != "completed")
        self.assertIn(
            loser["failure_class"],
            {
                "idempotent_rollover_replay",
                "continuity_replay_state_busy",
                "continuity_replay_state_unavailable",
            },
        )
        self.assertFalse(loser["boundaries"]["session_call_performed"])

    def test_fresh_continuation_rejects_origin_mismatch_and_malformed_enum(self) -> None:
        mismatch = self.continuity_assessment()
        mismatch["repository_id"] = "github.com/other/repository"
        mismatch["checkpoint"]["repository_id"] = "github.com/other/repository"
        malformed = self.continuity_assessment()
        malformed["runtime"]["surface"] = []
        for assessment in (mismatch, malformed):
            with self.subTest(assessment=assessment):
                response = self.execute(
                    request=self.request(
                        operation="fresh-continuation",
                        continuity_assessment=assessment,
                    )
                )
                self.assertEqual("stopped", response["status"])
                self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_rejects_different_origin_host_and_file_remote(self) -> None:
        for remote in (
            "https://evil.example/example/repository.git",
            "file:///tmp/example/repository.git",
            "gh:example/repository.git",
        ):
            with self.subTest(remote=remote):
                self._git("remote", "set-url", "origin", remote)
                response = self.execute(
                    request=self.request(
                        operation="fresh-continuation",
                        continuity_assessment=self.continuity_assessment(),
                    )
                )
                self.assertEqual("stopped", response["status"])
                self.assertEqual("continuity_target_mismatch", response["failure_class"])
                self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_replay_directory_symlink_fails_closed(self) -> None:
        common = pathlib.Path(self._git("rev-parse", "--git-common-dir").stdout.strip())
        if not common.is_absolute():
            common = self.workspace / common
        target = self.root / "attacker-controlled"
        target.mkdir()
        (common / "codex-continuity-rollovers").symlink_to(target, target_is_directory=True)
        response = self.execute(
            request=self.request(
                operation="fresh-continuation",
                continuity_assessment=self.continuity_assessment(),
            )
        )
        self.assertEqual("stopped", response["status"])
        self.assertEqual("continuity_replay_state_unavailable", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_malformed_replay_record_fails_closed(self) -> None:
        common = pathlib.Path(self._git("rev-parse", "--git-common-dir").stdout.strip())
        if not common.is_absolute():
            common = self.workspace / common
        directory = common / "codex-continuity-rollovers"
        directory.mkdir(mode=0o700)
        (directory / "ledger.json").write_text("not-json", encoding="utf-8")
        response = self.execute(
            request=self.request(
                operation="fresh-continuation",
                continuity_assessment=self.continuity_assessment(),
            )
        )
        self.assertEqual("stopped", response["status"])
        self.assertEqual("continuity_replay_conflict", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_stalled_replay_lock_fails_without_waiting(self) -> None:
        import fcntl

        common = pathlib.Path(self._git("rev-parse", "--git-common-dir").stdout.strip())
        if not common.is_absolute():
            common = self.workspace / common
        directory = common / "codex-continuity-rollovers"
        directory.mkdir(mode=0o700)
        lock_descriptor = os.open(directory / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = time.monotonic()
        try:
            response = self.execute(
                request=self.request(
                    operation="fresh-continuation",
                    continuity_assessment=self.continuity_assessment(),
                )
            )
        finally:
            os.close(lock_descriptor)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual("stopped", response["status"])
        self.assertEqual("continuity_replay_state_busy", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_atomic_ledger_replace_failure_allows_safe_retry(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        with mock.patch.object(handoff.os, "replace", side_effect=OSError("fault")):
            failed = self.execute(request=request)
        self.assertEqual("stopped", failed["status"])
        self.assertEqual("continuity_replay_state_unavailable", failed["failure_class"])
        self.assertFalse(failed["boundaries"]["session_call_performed"])
        retried = copy.deepcopy(request)
        retried["continuity_assessment"]["lineage"]["rollover_id"] = "rollover-2"
        response = self.execute(request=retried)
        self.assertEqual("completed", response["status"])

    def test_fresh_continuation_writer_rejects_oversized_ledger(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        with mock.patch.dict(
            os.environ,
            {
                "FAKE_CODEX_MODE": "success",
                "FAKE_CODEX_CAPTURE": str(self.capture),
            },
        ):
            validated = handoff.validate_request(request)
            with mock.patch.object(
                handoff, "_read_rollover_ledger", return_value={
                    "contract": "codex-cli-rollover-replay-ledger/v1",
                    "entries": [],
                }
            ), mock.patch.object(
                handoff.json, "dumps", return_value="x" * (256 * 1024)
            ):
                with self.assertRaisesRegex(
                    handoff.HandoffValidationError, "bounded size"
                ):
                    handoff._claim_rollover(validated)
        self.assertFalse(self.capture.exists())

    def test_fresh_continuation_directory_fsync_failure_stops_before_dispatch(self) -> None:
        with mock.patch.object(handoff.os, "fsync", side_effect=OSError("fault")):
            response = self.execute(
                request=self.request(
                    operation="fresh-continuation",
                    continuity_assessment=self.continuity_assessment(),
                )
            )
        self.assertEqual("stopped", response["status"])
        self.assertEqual("continuity_replay_state_unavailable", response["failure_class"])
        self.assertFalse(response["boundaries"]["session_call_performed"])

    def test_fresh_continuation_retries_parent_fsync_after_initial_failure(self) -> None:
        request = self.request(
            operation="fresh-continuation",
            continuity_assessment=self.continuity_assessment(),
        )
        real_fsync = handoff.os.fsync
        calls = 0

        def fail_first(descriptor: int) -> None:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError("parent fsync fault")
            real_fsync(descriptor)

        with mock.patch.object(handoff.os, "fsync", side_effect=fail_first):
            failed = self.execute(request=request)
        self.assertEqual("stopped", failed["status"])
        self.assertFalse(failed["boundaries"]["session_call_performed"])

        common = pathlib.Path(self._git("rev-parse", "--git-common-dir").stdout.strip())
        if not common.is_absolute():
            common = self.workspace / common
        common_inode = common.stat().st_ino
        synced_inodes: list[int] = []

        def record_fsync(descriptor: int) -> None:
            synced_inodes.append(os.fstat(descriptor).st_ino)
            real_fsync(descriptor)

        retry = copy.deepcopy(request)
        retry["continuity_assessment"]["lineage"]["rollover_id"] = "rollover-2"
        with mock.patch.object(handoff.os, "fsync", side_effect=record_fsync):
            response = self.execute(request=retry)
        self.assertEqual("completed", response["status"])
        self.assertIn(common_inode, synced_inodes)

    def test_fresh_continuation_checkpoint_must_match_worktree_head_and_branch(self) -> None:
        variants = []
        wrong_head = self.continuity_assessment()
        wrong_head["checkpoint"]["head_sha"] = "b" * 40
        variants.append(wrong_head)
        wrong_branch = self.continuity_assessment()
        wrong_branch["checkpoint"]["branch"] = "other-branch"
        variants.append(wrong_branch)
        for assessment in variants:
            with self.subTest(checkpoint=assessment["checkpoint"]):
                if self.capture.exists():
                    self.capture.unlink()
                response = self.execute(
                    request=self.request(
                        operation="fresh-continuation",
                        continuity_assessment=assessment,
                    )
                )
                self.assertEqual("stopped", response["status"])
                self.assertEqual("continuity_target_mismatch", response["failure_class"])
                self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
