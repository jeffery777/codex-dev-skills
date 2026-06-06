import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_executor.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_executor", SCRIPT)
executor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(executor)


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
    request = executor.example_request()
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


def valid_shell_evidence(**overrides):
    evidence = copy.deepcopy(executor.example_request()["executor_shell_evidence"])
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def successful_runner(payload):
    return {
        "status": "created",
        "thread_id": "thread_123",
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "echo": payload["target"]["repo"],
    }


class CreateThreadExecutorTests(unittest.TestCase):
    def test_complete_non_live_injected_callable_envelope_returns_ready(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(), runner=successful_runner
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertTrue(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertEqual(response["execution_kind"], "injected-callable-adapter")
        self.assertEqual(response["result"]["returned_thread_id"], "thread_123")
        self.assertEqual(response["result"]["returned_status"], "created")
        self.assertIn("injected adapter", response["runtime_call_performed_meaning"])
        self.assertTrue(
            any("CLI default remains non-live" in item for item in response["result"]["residual_risk"])
        )

    def test_cli_default_without_runner_returns_fallback(self):
        response = executor.execute_create_thread_with_injected_adapter(valid_request())

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "injected_callable_runner_missing")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertFalse(response["runtime_call_performed"])

    def test_missing_shell_evidence_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(executor_shell_evidence={}), runner=successful_runner
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("executor_shell_evidence", response["result"]["stop_reason"])

    def test_fallback_or_stopped_shell_evidence_blocks(self):
        cases = (
            ("fallback", "executor_shell_evidence_fallback"),
            ("stopped", "shell_stopped"),
        )
        for status, expected_failure in cases:
            with self.subTest(status=status):
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(
                        executor_shell_evidence=valid_shell_evidence(
                            status=status,
                            failure_class="shell_stopped",
                            result__stop_reason="shell stopped",
                        )
                    ),
                    runner=successful_runner,
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
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(**{path: value}), runner=successful_runner
                )

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
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(**{path: ""}), runner=successful_runner
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_prompt_summary_or_body_stops(self):
        for path, expected in (("prompt__summary", "prompt.summary"), ("prompt__body", "prompt.body")):
            with self.subTest(path=path):
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(**{path: ""}), runner=successful_runner
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(authorization__external_write_authorized=True),
            runner=successful_runner,
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(authorization__destructive_action_approved=value),
                    runner=successful_runner,
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_before_execution_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(boundaries__runtime_call_performed=True),
            runner=successful_runner,
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(boundaries__desktop_private_runtime_state_read=True),
            runner=successful_runner,
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_prior_evidence_cannot_replace_call_site_validation_or_handling(self):
        cases = (
            (
                "call_site_validation__target_validation__satisfied_by_prior_evidence",
                "target_validation_substituted",
            ),
            (
                "call_site_validation__permission_failure_handling__satisfied_by_prior_evidence",
                "permission_handling_substituted",
            ),
            (
                "call_site_validation__response_validation__satisfied_by_prior_evidence",
                "response_validation_substituted",
            ),
        )
        for path, failure_class in cases:
            with self.subTest(path=path):
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(**{path: True}), runner=successful_runner
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_human_implementation_marker_returns_fallback(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(authorization__human_implementation_marker=""),
            runner=successful_runner,
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_implementation_marker_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_injected_callable_auth_or_permission_failure_is_classified_and_returned(self):
        def auth_runner(_payload):
            raise executor.CreateThreadAdapterAuthError("login required")

        def permission_runner(_payload):
            raise executor.CreateThreadAdapterPermissionError("permission denied")

        def permission_response_runner(_payload):
            return {"status": "permission-denied", "message": "runtime permission denied"}

        cases = (
            (auth_runner, "adapter_auth_failure"),
            (permission_runner, "adapter_permission_failure"),
            (permission_response_runner, "adapter_permission_or_auth_failure"),
        )
        for runner, failure_class in cases:
            with self.subTest(failure_class=failure_class):
                response = executor.execute_create_thread_with_injected_adapter(
                    valid_request(), runner=runner
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)
                self.assertEqual(
                    response["result"]["permission_or_auth_failure"]["failure_class"],
                    failure_class,
                )

    def test_injected_callable_malformed_response_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(), runner=lambda _payload: ["not", "an", "object"]
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_response_shape_invalid")

    def test_missing_returned_thread_id_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(),
            runner=lambda _payload: {
                "status": "created",
                "desktop_runtime_call_performed": False,
                "private_runtime_state_read": False,
                "external_write_performed": False,
            },
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "returned_thread_id_invalid")

    def test_invalid_returned_status_stops(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(),
            runner=lambda _payload: {
                "status": "done",
                "thread_id": "thread_123",
                "desktop_runtime_call_performed": False,
                "private_runtime_state_read": False,
                "external_write_performed": False,
            },
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "returned_status_invalid")

    def test_no_desktop_private_runtime_looking_path_or_source_hint_is_accepted(self):
        response = executor.execute_create_thread_with_injected_adapter(
            valid_request(prompt__body="Inspect Desktop private runtime state first."),
            runner=successful_runner,
        )
        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

        reason = executor._request_path_rejection_reason("/tmp/runtime-state/request.json")
        self.assertIsNotNone(reason)
        self.assertIn("runtime-looking", reason)

    def test_no_forbidden_thread_tool_call_shapes_are_introduced(self):
        source = SCRIPT.read_text(encoding="utf-8")

        forbidden_patterns = (
            "def fork_" + "thread",
            "def send_message_" + "to_thread",
            "def read_" + "thread",
            "fork_" + "thread(",
            "send_message_" + "to_thread(",
            "read_" + "thread(",
        )
        for pattern in forbidden_patterns:
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
