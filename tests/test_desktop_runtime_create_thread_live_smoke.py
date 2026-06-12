import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_live_smoke.py"
SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_create_thread_live_smoke", SCRIPT
)
live_smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live_smoke)


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
    request = live_smoke.example_request()
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


DEFAULT_RESPONSE = object()


def successful_callable(response=DEFAULT_RESPONSE, calls=None):
    def runner(payload):
        if calls is not None:
            calls.append(copy.deepcopy(payload))
        if response is DEFAULT_RESPONSE:
            return {
                "thread_id": "thread_123",
                "status": "created",
                "private_runtime_state_read": False,
                "external_write_performed": False,
            }
        return response

    return runner


class CreateThreadLiveSmokeTests(unittest.TestCase):
    def test_cli_default_without_live_callable_returns_fallback(self):
        response = live_smoke.run_create_thread_live_smoke(valid_request())

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "live_create_thread_callable_missing")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])

    def test_missing_human_approval_returns_fallback_without_calling_runner(self):
        calls = []
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(authorization__human_live_smoke_marker=""),
            create_thread_callable=successful_callable(calls=calls),
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_live_smoke_marker_missing")
        self.assertEqual(calls, [])

    def test_wrong_action_or_tool_stops(self):
        cases = (
            ("target_action", "read-thread", "unsupported_thread_tool_path"),
            ("tool_or_api", "read_thread", "unsupported_thread_tool_path"),
            (
                "live_callable_descriptor__target_action",
                "fork-thread",
                "unsupported_thread_tool_path",
            ),
            (
                "live_callable_descriptor__tool_or_api",
                "send_message_" + "to_thread",
                "unsupported_thread_tool_path",
            ),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(**{path: value}),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_unsupported_fork_send_read_descriptors_stop(self):
        cases = (
            ("fork_" + "thread", "fork-thread"),
            ("send_message_" + "to_thread", "send-message"),
            ("read_" + "thread", "read-thread"),
        )
        for tool_name, action_name in cases:
            with self.subTest(tool_name=tool_name):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(
                        live_callable_descriptor__tool_or_api=tool_name,
                        live_callable_descriptor__target_action=action_name,
                    ),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "unsupported_thread_tool_path")

    def test_missing_repo_remote_branch_or_expected_head_stops(self):
        for path, expected in (
            ("target__repo", "target.repo"),
            ("target__remote", "target.remote"),
            ("target__branch", "target.branch"),
            ("target__expected_head", "target.expected_head"),
        ):
            with self.subTest(path=path):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(**{path: ""}),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_smoke_prompt_summary_or_body_stops(self):
        for path, expected in (
            ("smoke_prompt__summary", "smoke_prompt.summary"),
            ("smoke_prompt__body", "smoke_prompt.body"),
        ):
            with self.subTest(path=path):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(**{path: ""}),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(authorization__external_write_authorized=True),
            create_thread_callable=successful_callable(),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(authorization__destructive_action_approved=value),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_before_live_smoke_stops(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(boundaries__runtime_call_performed=True),
            create_thread_callable=successful_callable(),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(boundaries__desktop_private_runtime_state_read=True),
            create_thread_callable=successful_callable(),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_private_runtime_source_hint_stops(self):
        request = valid_request()
        request["runtime_source_hints"] = ["Derived from Desktop private runtime state."]
        response = live_smoke.run_create_thread_live_smoke(
            request,
            create_thread_callable=successful_callable(),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_malformed_live_callable_descriptor_stops(self):
        cases = (
            ({}, "live_callable_descriptor_malformed"),
            ("not an object", "live_callable_descriptor_malformed"),
        )
        for descriptor, failure_class in cases:
            with self.subTest(descriptor=descriptor):
                request = valid_request()
                request["live_callable_descriptor"] = descriptor
                response = live_smoke.run_create_thread_live_smoke(
                    request,
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

        response = live_smoke.run_create_thread_live_smoke(
            valid_request(live_callable_descriptor__live_desktop_runtime=False),
            create_thread_callable=successful_callable(),
        )
        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "live_callable_descriptor_source_unclear")

    def test_prior_evidence_cannot_replace_target_permission_or_response_validation(self):
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
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(**{path: True}),
                    create_thread_callable=successful_callable(),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_permission_auth_failure_from_injected_callable_is_classified_and_returned(self):
        cases = (
            (
                lambda _payload: (_ for _ in ()).throw(
                    live_smoke.CreateThreadLiveSmokeAuthError("login expired")
                ),
                "runtime_auth_failure",
            ),
            (
                lambda _payload: (_ for _ in ()).throw(
                    live_smoke.CreateThreadLiveSmokePermissionError("not allowed")
                ),
                "runtime_permission_failure",
            ),
            (
                lambda _payload: {"status": "permission-denied", "message": "denied"},
                "runtime_permission_or_auth_failure",
            ),
        )
        for runner, failure_class in cases:
            with self.subTest(failure_class=failure_class):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(),
                    create_thread_callable=runner,
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)
                self.assertEqual(
                    response["result"]["permission_or_auth_failure"]["failure_class"],
                    failure_class,
                )

    def test_malformed_runtime_response_stops(self):
        for runtime_response in ("not an object", [], None):
            with self.subTest(runtime_response=runtime_response):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(),
                    create_thread_callable=successful_callable(response=runtime_response),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "runtime_response_shape_invalid")

    def test_missing_returned_thread_id_and_pending_worktree_id_stops(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={
                    "status": "created",
                    "private_runtime_state_read": False,
                    "external_write_performed": False,
                }
            ),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(
            response["failure_class"], "returned_thread_or_pending_worktree_id_invalid"
        )

    def test_invalid_returned_status_stops(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={
                    "thread_id": "thread_123",
                    "status": "finished",
                    "private_runtime_state_read": False,
                    "external_write_performed": False,
                }
            ),
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "returned_status_invalid")

    def test_raw_desktop_thread_id_response_without_status_or_wrapper_flags_returns_ready(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={"threadId": "thread_raw_desktop_123"}
            ),
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertEqual(response["result"]["returned_thread_id"], "thread_raw_desktop_123")
        self.assertIsNone(response["result"]["returned_status"])
        self.assertTrue(response["result"]["prompt_delivered"])

    def test_runtime_response_rejects_explicit_private_state_or_external_write_flags(self):
        cases = (
            (
                {
                    "thread_id": "thread_123",
                    "status": "created",
                    "private_runtime_state_read": "false",
                    "external_write_performed": False,
                },
                "forbidden_private_runtime_state",
            ),
            (
                {
                    "thread_id": "thread_123",
                    "status": "created",
                    "private_runtime_state_read": False,
                    "external_write_performed": True,
                },
                "external_write_request",
            ),
            (
                {
                    "thread_id": "thread_123",
                    "status": "created",
                    "external_write_performed": "false",
                },
                "external_write_request",
            ),
        )
        for runtime_response, failure_class in cases:
            with self.subTest(runtime_response=runtime_response):
                response = live_smoke.run_create_thread_live_smoke(
                    valid_request(),
                    create_thread_callable=successful_callable(response=runtime_response),
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_successful_thread_id_response_returns_ready_and_audit_not_completed(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={
                    "threadId": "thread_camel_123",
                    "status": "created",
                    "private_runtime_state_read": False,
                    "external_write_performed": False,
                }
            ),
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertTrue(response["runtime_call_performed"])
        self.assertTrue(response["desktop_runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertTrue(response["result"]["prompt_delivered"])
        self.assertFalse(response["result"]["audit_task_completed"])
        self.assertFalse(response["result"]["audit_task_completion_required"])
        self.assertEqual(response["result"]["returned_thread_id"], "thread_camel_123")
        self.assertEqual(response["result"]["returned_status"], "created")

    def test_successful_thread_id_legacy_response_still_returns_ready(self):
        calls = []
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(calls=calls),
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertTrue(response["runtime_call_performed"])
        self.assertTrue(response["desktop_runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertTrue(response["result"]["prompt_delivered"])
        self.assertFalse(response["result"]["audit_task_completed"])
        self.assertFalse(response["result"]["audit_task_completion_required"])
        self.assertEqual(response["result"]["returned_thread_id"], "thread_123")
        self.assertEqual(response["result"]["returned_status"], "created")
        self.assertEqual(len(calls), 1)
        self.assertIn("read-only audit", calls[0]["prompt"]["body"].lower())

    def test_successful_pending_worktree_response_returns_ready_with_queued_status(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={
                    "pendingWorktreeId": "pending_123",
                    "status": "queued",
                    "private_runtime_state_read": False,
                    "external_write_performed": False,
                }
            ),
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["result"]["returned_thread_id"])
        self.assertEqual(response["result"]["pendingWorktreeId"], "pending_123")
        self.assertEqual(response["result"]["returned_status"], "queued")

    def test_thread_id_shape_takes_precedence_when_pending_worktree_id_is_also_present(self):
        response = live_smoke.run_create_thread_live_smoke(
            valid_request(),
            create_thread_callable=successful_callable(
                response={
                    "thread_id": "thread_123",
                    "pendingWorktreeId": "pending_123",
                    "status": "created",
                    "private_runtime_state_read": False,
                    "external_write_performed": False,
                }
            ),
        )

        self.assertEqual(response["status"], "ready")
        self.assertEqual(response["result"]["returned_thread_id"], "thread_123")
        self.assertEqual(response["result"]["pendingWorktreeId"], "pending_123")
        self.assertEqual(response["result"]["returned_status"], "created")

    def test_generated_smoke_prompt_includes_read_only_audit_boundaries(self):
        prompt = live_smoke.build_read_only_audit_smoke_prompt()
        body = prompt["body"].lower()

        for phrase in (
            "read-only audit",
            "missing formal merge review evidence",
            "candidate prs",
            "gap type",
            "separate human approval",
            "do not post comments",
            "do not submit reviews",
            "do not edit files",
            "do not commit",
            "do not push",
            "do not open pull requests",
            "do not merge",
            "do not change labels",
            "do not change status",
            "do not perform platform writes",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, body)

    def test_tests_do_not_invoke_live_desktop_runtime_by_default(self):
        response = live_smoke.run_create_thread_live_smoke(valid_request())

        self.assertEqual(response["status"], "fallback")
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])

    def test_no_forbidden_runtime_tool_call_shapes_are_introduced(self):
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
