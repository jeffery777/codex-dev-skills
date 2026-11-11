"""Behavioral tests use only an offline fake CLI, never a live Codex session."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import pathlib
import queue
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/cli-session-handoff/scripts/app_server_handoff.py"
SPEC = importlib.util.spec_from_file_location("app_server_handoff", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AppServerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name).resolve()
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        self.sentinel = self.workspace / "protected.txt"
        self.sentinel.write_text("preserve me\n")
        self.executable = self.base / "codex"
        source = (ROOT / "tests/fixtures/app-server-handoff/fake_codex.py").read_text()
        self.executable.write_text(source.replace("#!/usr/bin/env python3", "#!" + sys.executable, 1))
        self.executable.chmod(0o700)
        self.store = self.base / "server-state.json"
        patch = mock.patch.dict(os.environ, {"FAKE_APP_SERVER_STORE": str(self.store), "FAKE_APP_SERVER_CASE": "normal"})
        patch.start()
        self.addCleanup(patch.stop)
        self.request = {"schema_version": 1, "operation": "start", "codex_executable": str(self.executable), "workspace": str(self.workspace), "prompt": "Read only", "timeout_seconds": 5, "authorization": {"session_action_authorized": True}}

    def execute(self, case="normal", **updates):
        request = copy.deepcopy(self.request)
        request.update(updates)
        with mock.patch.dict(os.environ, {"FAKE_APP_SERVER_CASE": case}):
            return MODULE.execute(request)

    def calls(self, method):
        state = json.loads(self.store.read_text())
        return [x for x in state["calls"] if x["method"] == method]

    def test_start_and_same_connection_turns_read_back_results(self):
        r = copy.deepcopy(self.request)
        r.pop("prompt")
        r["prompts"] = ["first", "second"]
        result = MODULE.execute(r)
        self.assertEqual("completed", result["status"], result)
        self.assertEqual(["turn_1", "turn_2"], [t["turn_id"] for t in result["results"]])
        self.assertEqual(1, len(self.calls("initialize")))
        self.assertEqual("read-only", result["sandbox"])
        self.assertTrue(result["cwd_verified"])
        self.assertEqual("not_verified", result["desktop_visibility"])
        self.assertIsNone(result["api_project_id"])
        self.assertEqual("preserve me\n", self.sentinel.read_text())

    def test_resume_new_process_and_fork_preserve_identity_boundary(self):
        first = self.execute()
        second = self.execute(operation="resume", thread_id=first["thread_id"])
        self.assertEqual("completed", second["status"], second)
        self.assertEqual(first["thread_id"], second["thread_id"])
        request = copy.deepcopy(self.request)
        request.pop("prompt")
        request.update(operation="fork", thread_id=second["thread_id"])
        fork = MODULE.execute(request)
        self.assertEqual("completed", fork["status"], fork)
        self.assertNotEqual(second["thread_id"], fork["thread_id"])
        self.assertEqual("turn_2", fork["fork_boundary_id"])
        self.assertEqual(2, len(self.calls("turn/start")))

    def test_fork_and_authorized_prompt_use_same_process(self):
        first = self.execute()
        fork = self.execute(operation="fork", thread_id=first["thread_id"])
        self.assertEqual("completed", fork["status"], fork)
        self.assertEqual("turn_2", fork["results"][0]["turn_id"])

    def test_workspace_write_requires_authority_and_sets_exact_root(self):
        denied = self.execute(sandbox="workspace-write", prompt="write-fixture")
        self.assertEqual("workspace_write_authorization_missing", denied["failure_class"])
        self.assertFalse(self.store.exists())
        result = self.execute(sandbox="workspace-write", prompt="write-fixture", authorization={"session_action_authorized": True, "workspace_write_authorized": True, "exclusive_writer": True})
        self.assertEqual("completed", result["status"], result)
        policy = self.calls("turn/start")[0]["params"]["sandboxPolicy"]
        self.assertEqual({"type": "workspaceWrite", "networkAccess": False, "writableRoots": [str(self.workspace)], "excludeSlashTmp": True, "excludeTmpdirEnvVar": True}, policy)
        self.assertEqual("intended fixture result\n", (self.workspace / "result.txt").read_text())
        self.assertEqual("preserve me\n", self.sentinel.read_text())

    def test_read_only_does_not_send_a_write_policy(self):
        result = self.execute(prompt="write-fixture")
        self.assertEqual("completed", result["status"], result)
        self.assertFalse((self.workspace / "result.txt").exists())

    def test_inherited_external_tools_are_disabled_and_inventory_verified(self):
        result = self.execute("inherited_mcp")
        self.assertEqual("completed", result["status"], result)
        self.assertTrue(result["mcp_inventory_verified"])
        argv = json.loads(self.store.read_text())["server_argv"]
        self.assertIn('mcp_servers.local-tools.enabled=false', argv)
        disabled = [argv[n + 1] for n, value in enumerate(argv) if value == "--disable"]
        self.assertTrue({"apps", "plugins", "browser_use", "computer_use", "multi_agent", "multi_agent_v2", "skill_mcp_dependency_install"}.issubset(disabled))

    def test_failed_external_tool_preflight_never_starts_a_server(self):
        for case, failure in [("override_ignored", "external_tools_still_enabled"), ("malformed_mcp", "external_tool_preflight_failed"), ("mcp_bad_name", "external_tool_preflight_failed")]:
            with self.subTest(case=case):
                self.assertEqual(failure, self.execute(case)["failure_class"])
        self.assertFalse(self.store.exists())

    def test_nonempty_or_incomplete_mcp_inventory_stops_before_task(self):
        for case in ("inventory_tools", "inventory_cursor", "inventory_loading"):
            with self.subTest(case=case):
                result = self.execute(case)
                self.assertEqual("external_tool_inventory_unverified", result["failure_class"])
                self.assertIn("thread_id", result)
                self.assertFalse(result["effect_uncertain"])
        self.assertFalse(self.calls("turn/start"))

    def test_explicitly_disabled_empty_servers_are_safe_inventory(self):
        result = self.execute("inventory_disabled")
        self.assertEqual("completed", result["status"], result)
        self.assertTrue(result["mcp_inventory_verified"])

    def test_writer_refusal_does_not_retry_or_start_turn(self):
        first = self.execute()
        result = self.execute("writer", operation="resume", thread_id=first["thread_id"])
        self.assertEqual("writer_conflict", result["failure_class"])
        self.assertFalse(result["effect_uncertain"])
        self.assertEqual(1, len(self.calls("thread/resume")))
        self.assertEqual(1, len(self.calls("turn/start")))

    def test_events_can_precede_turn_start_ack(self):
        self.assertEqual("completed", self.execute("event_before_ack")["status"])

    def test_target_or_permission_mismatch_stops_before_turn(self):
        for case, failure in [("bad_cwd", "cwd_mismatch"), ("bad_sandbox", "sandbox_mismatch")]:
            with self.subTest(case=case):
                result = self.execute(case)
                self.assertEqual(failure, result["failure_class"])
                self.assertIn("thread_id", result)
        self.assertFalse(self.calls("turn/start"))

    def test_failed_or_mismatched_completion_cannot_pass(self):
        for case, failure in [("failed_turn", "turn_failed"), ("wrong_completion", "completion_thread_mismatch"), ("readback_wrong", "thread_id_mismatch")]:
            with self.subTest(case=case):
                self.assertEqual(failure, self.execute(case)["failure_class"])

    def test_fork_does_not_accept_a_different_source(self):
        first = self.execute()
        result = self.execute("fork_source_wrong", operation="fork", thread_id=first["thread_id"])
        self.assertEqual("fork_source_mismatch", result["failure_class"])

    def test_early_exit_and_unusable_output_preserve_created_identity(self):
        for case, failure in [("early_exit", "early_exit"), ("malformed", "malformed_jsonl"), ("oversized", "output_limit")]:
            with self.subTest(case=case):
                result = self.execute(case)
                self.assertEqual(failure, result["failure_class"])
                self.assertIn("thread_id", result)
                self.assertTrue(result["effect_uncertain"])
        self.assertEqual(3, len(self.calls("thread/start")))

    def test_unexpected_approval_does_not_grant_or_retry(self):
        result = self.execute("approval")
        self.assertEqual("client_approval_or_tool_required", result["failure_class"])
        self.assertTrue(result["effect_uncertain"])
        self.assertEqual(1, len(self.calls("turn/start")))

    def test_timeout_is_bounded_and_does_not_replay(self):
        result = self.execute("timeout")
        self.assertEqual("timeout", result["failure_class"])
        self.assertTrue(result["effect_uncertain"])
        self.assertEqual(1, len(self.calls("turn/start")))

    def test_exited_server_with_descendant_pipe_returns_bounded_uncertainty(self):
        with mock.patch.dict(os.environ, {"FAKE_APP_SERVER_CASE": "held_pipe"}):
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--request", "-"],
                input=json.dumps(self.request), capture_output=True, text=True,
                timeout=8,
            )
        self.assertEqual(1, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual("blocked", receipt["status"])
        self.assertEqual("cleanup_unconfirmed", receipt["process_cleanup"])
        self.assertEqual("server_shutdown_failed", receipt["failure_class"])
        self.assertTrue(receipt["effect_uncertain"])
        self.assertIn("thread_id", receipt)
        self.assertEqual(1, len(self.calls("turn/start")))

    def test_response_ids_are_checked(self):
        self.assertEqual("response_id_mismatch", self.execute("wrong_response")["failure_class"])

    def test_authority_types_and_unknown_fields_fail_before_launch(self):
        for update in [{"extra": True}, {"schema_version": True}, {"operation": []}, {"sandbox": {}}, {"timeout_seconds": True}, {"authorization": {"session_action_authorized": 1}}, {"sandbox": "danger-full-access"}, {"thread_id": "unneeded"}]:
            with self.subTest(update=update):
                self.assertEqual("blocked", self.execute(**update)["status"])
        self.assertFalse(self.store.exists())

    def test_head_mismatch_and_recursive_dispatch_stop_before_launch(self):
        result = self.execute(expected_head="a" * 40)
        self.assertEqual("head_mismatch", result["failure_class"])
        with mock.patch.dict(os.environ, {"CODEX_APP_SERVER_HANDOFF_DEPTH": "1"}):
            self.assertEqual("recursive_handoff", self.execute()["failure_class"])
        self.assertFalse(self.store.exists())

    def test_example_and_invalid_json_do_not_start_session(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--example"], capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertEqual("read-only", json.loads(result.stdout)["sandbox"])
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", "-"], input="not-json", capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertEqual("invalid_request", json.loads(result.stdout)["failure_class"])
        self.assertFalse(self.store.exists())

    def test_duplicate_authority_fields_are_not_silently_overwritten(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--request", "-"],
                                input='{"authorization":false,"authorization":true}',
                                capture_output=True, text=True)
        self.assertEqual("invalid_request", json.loads(result.stdout)["failure_class"])
        self.assertFalse(self.store.exists())

    def test_git_probe_errors_are_not_treated_as_non_git_workspaces(self):
        result = subprocess.CompletedProcess([], 128, stdout=b"", stderr=b"fatal: permission denied")
        with mock.patch.object(MODULE.subprocess, "run", return_value=result):
            r = self.execute(sandbox="workspace-write", authorization={"session_action_authorized": True, "workspace_write_authorized": True, "exclusive_writer": True})
        self.assertEqual("git_identity_unavailable", r["failure_class"])
        self.assertFalse(self.store.exists())

    def test_damaged_git_marker_blocks_instead_of_becoming_non_git(self):
        (self.workspace / ".git").write_text("gitdir: missing-metadata\n")
        result = self.execute(sandbox="workspace-write", authorization={"session_action_authorized": True, "workspace_write_authorized": True, "exclusive_writer": True})
        self.assertEqual("git_identity_unavailable", result["failure_class"])
        self.assertFalse(self.store.exists())

    def test_received_identity_ack_survives_later_reader_error(self):
        client = object.__new__(MODULE.Client)
        client.events = queue.Queue()
        ack = {"id": 1, "result": {"thread": {"id": "known_thread"}}}
        client.events.put(ack)
        client.reader_error = "malformed_jsonl"
        client.deadline = 0
        self.assertEqual(ack, client.receive())
        with self.assertRaises(MODULE.HandoffError) as caught:
            client.receive()
        self.assertEqual("malformed_jsonl", caught.exception.kind)

    def test_git_write_requires_matching_head_even_with_authority(self):
        subprocess.run(["git", "init", "-q", str(self.workspace)], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "add", "protected.txt"], check=True)
        subprocess.run(["git", "-C", str(self.workspace), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"], check=True)
        head = subprocess.check_output(["git", "-C", str(self.workspace), "rev-parse", "HEAD"], text=True).strip()
        auth = {"session_action_authorized": True, "workspace_write_authorized": True, "exclusive_writer": True}
        self.assertEqual("expected_head_required_for_write", self.execute(sandbox="workspace-write", authorization=auth)["failure_class"])
        self.assertEqual("head_mismatch", self.execute(sandbox="workspace-write", authorization=auth, expected_head="0" * 40)["failure_class"])
        with mock.patch.dict(os.environ, {"GIT_DIR": "/missing/parent/git", "GIT_WORK_TREE": "/missing/parent/workspace"}):
            result = self.execute(sandbox="workspace-write", authorization=auth, expected_head=head)
        self.assertEqual("completed", result["status"], result)
        self.assertEqual(head, result["source_head"])


if __name__ == "__main__":
    unittest.main()
