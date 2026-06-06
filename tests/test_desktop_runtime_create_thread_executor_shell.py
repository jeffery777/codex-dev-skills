import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_executor_shell.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_executor_shell", SCRIPT)
shell = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(shell)


def set_path(value, path, replacement):
    current = value
    parts = path.split("__")
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    if isinstance(current, list):
        current[int(parts[-1])] = replacement
    else:
        current[parts[-1]] = replacement


def valid_request(**overrides):
    request = shell.example_request()
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


def valid_proposal(**overrides):
    proposal = copy.deepcopy(shell.example_request()["executor_boundary_proposal_evidence"])
    for path, value in overrides.items():
        set_path(proposal, path, value)
    return proposal


class CreateThreadExecutorShellTests(unittest.TestCase):
    def test_complete_executor_shell_envelope_returns_ready(self):
        response = shell.validate_executor_shell(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertIn("implementation surface", response["readiness_meaning"])
        self.assertIn("does not authorize or perform a runtime call", response["readiness_meaning"])
        for required in shell.REQUIRED_CALL_SITE_CONTRACT:
            self.assertIn(required, response["required_call_site_contract"])

    def test_missing_executor_boundary_proposal_evidence_stops(self):
        response = shell.validate_executor_shell(valid_request(executor_boundary_proposal_evidence={}))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("executor_boundary_proposal_evidence", response["result"]["stop_reason"])

    def test_fallback_or_stopped_proposal_evidence_blocks(self):
        cases = (
            ("fallback", "executor_boundary_proposal_evidence_fallback"),
            ("stopped", "proposal_stopped"),
        )
        for status, expected_failure in cases:
            with self.subTest(status=status):
                response = shell.validate_executor_shell(
                    valid_request(
                        executor_boundary_proposal_evidence=valid_proposal(
                            status=status,
                            failure_class="proposal_stopped",
                            result__stop_reason="proposal stopped",
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
                response = shell.validate_executor_shell(valid_request(**{path: value}))

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
                response = shell.validate_executor_shell(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_prompt_summary_or_body_stops(self):
        for path, expected in (("prompt__summary", "prompt.summary"), ("prompt__body", "prompt.body")):
            with self.subTest(path=path):
                response = shell.validate_executor_shell(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = shell.validate_executor_shell(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = shell.validate_executor_shell(
                    valid_request(authorization__destructive_action_approved=value)
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_stops(self):
        response = shell.validate_executor_shell(valid_request(boundaries__runtime_call_performed=True))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = shell.validate_executor_shell(
            valid_request(boundaries__desktop_private_runtime_state_read=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_prior_evidence_cannot_replace_call_site_validation_or_handling(self):
        cases = (
            (
                "executor_shell__call_site_contract__target_validation__satisfied_by_prior_evidence",
                "target_validation_substituted",
            ),
            (
                "executor_shell__call_site_contract__permission_failure_handling__satisfied_by_prior_evidence",
                "permission_handling_substituted",
            ),
            (
                "executor_shell__call_site_contract__response_validation__satisfied_by_prior_evidence",
                "response_validation_substituted",
            ),
        )
        for path, failure_class in cases:
            with self.subTest(path=path):
                response = shell.validate_executor_shell(valid_request(**{path: True}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_call_site_validation_permission_or_response_contract_stops(self):
        cases = (
            "executor_shell__call_site_contract__target_identity_rechecked",
            "executor_shell__call_site_contract__authorization_intent_rechecked",
            "executor_shell__call_site_contract__permission_auth_failure_classified_and_returned",
            "executor_shell__call_site_contract__runtime_response_shape_validated",
            "executor_shell__call_site_contract__returned_thread_id_validated",
            "executor_shell__call_site_contract__returned_status_validated",
        )
        for path in cases:
            with self.subTest(path=path):
                response = shell.validate_executor_shell(valid_request(**{path: False}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "call_site_contract_missing")

    def test_missing_human_approval_marker_returns_fallback(self):
        response = shell.validate_executor_shell(valid_request(authorization__human_approval_marker=""))

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_approval_boundary_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_callable_descriptor_execution_allowed_or_runtime_shape_present_stops(self):
        cases = (
            (
                "executor_shell__callable_descriptor__execution_allowed",
                True,
                "runtime_call_authorization_present",
            ),
            (
                "executor_shell__callable_descriptor__runtime_call_shape_present",
                True,
                "direct_runtime_call_shape_present",
            ),
            (
                "executor_shell__runtime_call_authorized",
                True,
                "runtime_call_authorization_present",
            ),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = shell.validate_executor_shell(valid_request(**{path: value}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_proposal_evidence_target_or_prompt_mismatch_stops(self):
        cases = (
            ("target_evidence__repo", "other/name"),
            ("target_evidence__remote", "https://github.com/other/name.git"),
            ("target_evidence__branch", "codex/other"),
            ("target_evidence__expected_head", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),
            ("prompt_evidence__summary", "different summary"),
        )
        for path, value in cases:
            with self.subTest(path=path):
                response = shell.validate_executor_shell(
                    valid_request(executor_boundary_proposal_evidence=valid_proposal(**{path: value}))
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(
                    response["failure_class"], "executor_boundary_proposal_evidence_mismatch"
                )

    def test_private_runtime_looking_source_hint_is_rejected(self):
        response = shell.validate_executor_shell(
            valid_request(prompt__body="Read Desktop logs before validating this shell.")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_no_desktop_private_runtime_looking_request_path_is_accepted(self):
        reason = shell._request_path_rejection_reason("/tmp/runtime-state/request.json")

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
