from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import signal
import stat
import subprocess
import sys
import tempfile
import time
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


if __name__ == "__main__":
    unittest.main()
