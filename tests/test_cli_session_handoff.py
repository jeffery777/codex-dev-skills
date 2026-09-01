from __future__ import annotations

import concurrent.futures
import copy
import importlib.util
import json
import os
import pathlib
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


class CodexPublicHelpCompatibilityTests(unittest.TestCase):
    """Read-only public CLI shape checks; never starts or resumes a session."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.codex = shutil.which("codex")
        if cls.codex is None:
            raise unittest.SkipTest(
                "Codex CLI is unavailable; public-help compatibility smoke skipped"
            )
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
            )
            argv = handoff.build_argv(request)
            self.assertEqual("-", argv[-1])
            argv[-1] = "--help"

            result = self.run_public_argv(argv)

            with self.subTest(operation=operation):
                self.assertIn("Usage: codex exec", result.stdout)


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
    if version_mode == "stdout-overflow":
        sys.stdout.write("x" * 8192)
        sys.stdout.flush()
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
        for mode in ("timeout", "stdout-overflow"):
            with self.subTest(mode=mode), mock.patch.dict(
                os.environ,
                {"FAKE_CODEX_VERSION_MODE": mode},
            ), mock.patch.object(handoff, "VERSION_TIMEOUT_SECONDS", 0.1):
                response = handoff.execute_handoff(self.request())

            self.assertEqual("fallback", response["status"])
            self.assertEqual(
                "capability_unavailable", response["failure_class"]
            )
            self.assertFalse(
                response["boundaries"]["session_call_performed"]
            )

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
