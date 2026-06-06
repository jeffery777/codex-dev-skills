import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_executor_boundary.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_executor_boundary", SCRIPT)
boundary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boundary)


TARGET = {
    "repo": "owner/name",
    "remote": "https://github.com/owner/name.git",
    "branch": "codex/create-thread-executor-boundary",
    "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
}


def set_path(value, path, replacement):
    current = value
    parts = path.split("__")
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    if isinstance(current, list):
        current[int(parts[-1])] = replacement
    else:
        current[parts[-1]] = replacement


def valid_authorization_gate(**overrides):
    evidence = {
        "status": "ready",
        "requested_action": "authorize-create-thread-runtime-call-envelope",
        "target_action": "create-thread",
        "tool_or_api": "create_thread",
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": False,
        "target_evidence": copy.deepcopy(TARGET),
        "authorization_evidence": {
            "authorized_runtime_action": "create-thread",
        },
        "result": {"stop_reason": None},
    }
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def valid_request(**overrides):
    request = {
        "requested_action": "propose-create-thread-runtime-call-executor-boundary",
        "target_action": "create-thread",
        "tool_or_api": "create_thread",
        "target": copy.deepcopy(TARGET),
        "prompt": {
            "summary": "Prepare one create-thread executor boundary proposal.",
            "body": "Document the call-site contract only; do not wire or invoke any runtime tool.",
        },
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": "create-thread",
            "human_approval_marker": (
                "human-approved-create-thread-runtime-call-executor-boundary-proposal-only"
            ),
            "human_approval_scope": "proposal-helper-only-no-runtime-call",
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "executor_contract": {
            "single_tool_path": "create_thread",
            "call_site_rechecks": [
                "target_identity",
                "authorization_intent",
                "permission_auth_failure_result",
                "runtime_response_shape",
                "returned_thread_id",
                "returned_status",
            ],
            "target_validation": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
            },
            "permission_failure_handling": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
                "requirements": [
                    "stop on auth failure",
                    "stop on permission failure",
                    "return the permission/auth failure result for human review",
                ],
            },
            "response_validation": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
                "minimum_response_fields": ["status", "thread_id"],
            },
            "human_approval_boundary": {
                "required_before_executor_use": True,
                "scope": "proposal-helper-only-no-runtime-call",
            },
            "external_writes_blocked": True,
        },
        "authorization_gate_evidence": valid_authorization_gate(),
    }
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


class CreateThreadExecutorBoundaryTests(unittest.TestCase):
    def test_complete_proposal_envelope_returns_ready(self):
        response = boundary.propose_executor_boundary(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertIn("does not authorize or perform a runtime call", response["readiness_meaning"])
        for required in boundary.REQUIRED_EXECUTOR_RECHECKS:
            self.assertIn(required, response["required_executor_rechecks"])

    def test_missing_authorization_gate_evidence_stops(self):
        response = boundary.propose_executor_boundary(valid_request(authorization_gate_evidence={}))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("authorization_gate_evidence", response["result"]["stop_reason"])

    def test_fallback_or_stopped_authorization_gate_evidence_blocks(self):
        cases = (
            ("fallback", "authorization_gate_evidence_fallback"),
            ("stopped", "gate_stopped"),
        )
        for status, expected_failure in cases:
            with self.subTest(status=status):
                response = boundary.propose_executor_boundary(
                    valid_request(
                        authorization_gate_evidence=valid_authorization_gate(
                            status=status,
                            failure_class="gate_stopped",
                            result__stop_reason="gate stopped",
                        )
                    )
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], expected_failure)
                self.assertTrue(response["later_runtime_path_blocked"])

    def test_wrong_action_or_tool_stops(self):
        cases = (
            ("target_action", "read-thread", "target_action_mismatch"),
            ("tool_or_api", "read_thread", "tool_or_api_mismatch"),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = boundary.propose_executor_boundary(valid_request(**{path: value}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_repo_remote_branch_or_expected_head_stops(self):
        for path, expected in (
            ("target__repo", "target.repo"),
            ("target__remote", "target.remote"),
            ("target__branch", "target.branch"),
            ("target__expected_head", "target.expected_head"),
        ):
            with self.subTest(path=path):
                response = boundary.propose_executor_boundary(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_prompt_summary_or_body_stops(self):
        for path, expected in (("prompt__summary", "prompt.summary"), ("prompt__body", "prompt.body")):
            with self.subTest(path=path):
                response = boundary.propose_executor_boundary(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = boundary.propose_executor_boundary(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = boundary.propose_executor_boundary(
                    valid_request(authorization__destructive_action_approved=value)
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_stops(self):
        response = boundary.propose_executor_boundary(
            valid_request(boundaries__runtime_call_performed=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = boundary.propose_executor_boundary(
            valid_request(boundaries__desktop_private_runtime_state_read=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_prior_evidence_cannot_replace_call_site_validation_or_handling(self):
        cases = (
            (
                "executor_contract__target_validation__satisfied_by_prior_evidence",
                "target_validation_substituted",
            ),
            (
                "executor_contract__permission_failure_handling__satisfied_by_prior_evidence",
                "permission_handling_substituted",
            ),
            (
                "executor_contract__response_validation__satisfied_by_prior_evidence",
                "response_validation_substituted",
            ),
        )
        for path, failure_class in cases:
            with self.subTest(path=path):
                response = boundary.propose_executor_boundary(valid_request(**{path: True}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_human_approval_marker_returns_fallback(self):
        response = boundary.propose_executor_boundary(
            valid_request(authorization__human_approval_marker="")
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_approval_boundary_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_private_runtime_looking_source_hint_is_rejected(self):
        response = boundary.propose_executor_boundary(
            valid_request(prompt__body="Read Desktop logs before wiring this boundary.")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_no_desktop_private_runtime_looking_request_path_is_accepted(self):
        reason = boundary._request_path_rejection_reason("/tmp/runtime-state/request.json")

        self.assertIsNotNone(reason)
        self.assertIn("runtime-looking", reason)

    def test_no_desktop_thread_tool_call_shapes_are_introduced(self):
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("def create_thread", source)
        self.assertNotIn("def fork_thread", source)
        self.assertNotIn("def send_message_to_thread", source)
        self.assertNotIn("def read_thread", source)
        call_patterns = (
            "create_" + "thread(",
            "fork_" + "thread(",
            "send_message_" + "to_thread(",
            "read_" + "thread(",
        )
        for pattern in call_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, source)

    def test_no_daemon_mcp_app_server_sidecar_or_background_service_claims_are_introduced(self):
        source = SCRIPT.read_text(encoding="utf-8").lower()
        mcp_server = "mcp " + "server"
        app_server_client = "app-" + "server client"
        background_service = "background " + "service"
        implementation_claims = (
            "implements a " + "daemon",
            "implements an " + mcp_server,
            "implements an " + app_server_client,
            "implements a " + "sidecar",
            "implements a " + background_service,
            "starts a " + "daemon",
            "starts an " + mcp_server,
            "starts an " + app_server_client,
            "starts a " + "sidecar",
            "starts a " + background_service,
        )

        for claim in implementation_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, source)


if __name__ == "__main__":
    unittest.main()
