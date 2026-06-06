import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE_SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_callable_bundle.py"
BUNDLE_SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_create_thread_callable_bundle", BUNDLE_SCRIPT
)
bundle = importlib.util.module_from_spec(BUNDLE_SPEC)
BUNDLE_SPEC.loader.exec_module(bundle)

EXECUTOR_SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_executor.py"
EXECUTOR_SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_create_thread_executor", EXECUTOR_SCRIPT
)
executor = importlib.util.module_from_spec(EXECUTOR_SPEC)
EXECUTOR_SPEC.loader.exec_module(executor)


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
    request = bundle.example_request()
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


def valid_wiring_evidence(**overrides):
    evidence = copy.deepcopy(bundle.example_request()["callable_wiring_evidence"])
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def valid_shell_evidence(**overrides):
    evidence = copy.deepcopy(bundle.example_request()["executor_shell_evidence"])
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


class CreateThreadCallableBundleTests(unittest.TestCase):
    def test_complete_ready_wiring_evidence_returns_ready_and_executor_request_preview(self):
        response = bundle.assemble_create_thread_callable_bundle(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertFalse(response["live_desktop_runtime"])
        self.assertFalse(response["injected_runner_executed"])
        preview = response["result"]["executor_request_preview"]
        self.assertEqual(preview["requested_action"], bundle.EXPECTED_EXECUTOR_ACTION)
        self.assertEqual(preview["target_action"], "create-thread")
        self.assertEqual(preview["tool_or_api"], "create_thread")
        self.assertFalse(preview["live_desktop_runtime"])
        self.assertFalse(preview["callable_adapter"]["live_desktop_runtime"])
        self.assertEqual(
            response["readiness_label"],
            "executor-request-preview-readiness-not-desktop-runtime-execution",
        )
        self.assertIn("executor request preview readiness only", response["readiness_meaning"])

    def test_generated_preview_is_acceptable_to_executor_cli_default_and_does_not_run(self):
        response = bundle.assemble_create_thread_callable_bundle(valid_request())
        preview = response["result"]["executor_request_preview"]
        executor_response = executor.execute_create_thread_with_injected_adapter(preview)

        self.assertEqual(executor_response["status"], "fallback")
        self.assertEqual(executor_response["failure_class"], "injected_callable_runner_missing")
        self.assertFalse(executor_response["runtime_call_performed"])
        self.assertFalse(executor_response["desktop_runtime_call_performed"])

    def test_cli_default_without_wiring_evidence_returns_fallback(self):
        request = valid_request()
        request.pop("callable_wiring_evidence")
        response = bundle.assemble_create_thread_callable_bundle(request)

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "callable_wiring_evidence_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

        minimal_default = {
            "requested_action": bundle.REQUESTED_ACTION,
            "target_action": "create-thread",
            "tool_or_api": "create_thread",
        }
        minimal_response = bundle.assemble_create_thread_callable_bundle(minimal_default)

        self.assertEqual(minimal_response["status"], "fallback")
        self.assertEqual(minimal_response["failure_class"], "callable_wiring_evidence_missing")
        self.assertTrue(minimal_response["later_runtime_path_blocked"])

    def test_missing_or_malformed_wiring_evidence_blocks(self):
        for evidence, expected_failure in (
            ({}, "callable_wiring_evidence_missing"),
            ("not an object", "callable_wiring_evidence_malformed"),
        ):
            with self.subTest(evidence=evidence):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(callable_wiring_evidence=evidence)
                )

                self.assertIn(response["status"], {"fallback", "stopped"})
                self.assertEqual(response["failure_class"], expected_failure)
                self.assertTrue(response["later_runtime_path_blocked"])

    def test_fallback_or_stopped_wiring_evidence_blocks(self):
        cases = (
            ("fallback", "callable_wiring_evidence_fallback"),
            ("stopped", "wiring_stopped"),
        )
        for status, expected_failure in cases:
            with self.subTest(status=status):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(
                        callable_wiring_evidence=valid_wiring_evidence(
                            status=status,
                            failure_class="wiring_stopped",
                            result__stop_reason="wiring stopped",
                        )
                    )
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], expected_failure)
                self.assertTrue(response["later_runtime_path_blocked"])

    def test_wrong_action_or_tool_stops(self):
        cases = (
            ("target_action", "read-thread", "unsupported_thread_tool_path"),
            ("tool_or_api", "read_thread", "unsupported_thread_tool_path"),
            (
                "callable_wiring_evidence__target_action",
                "read-thread",
                "unsupported_thread_tool_path",
            ),
            (
                "callable_wiring_evidence__tool_or_api",
                "send_message_" + "to_thread",
                "unsupported_thread_tool_path",
            ),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(**{path: value})
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
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(**{path: ""})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_prompt_summary_or_body_stops(self):
        for path, expected in (("prompt__summary", "prompt.summary"), ("prompt__body", "prompt.body")):
            with self.subTest(path=path):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(**{path: ""})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = bundle.assemble_create_thread_callable_bundle(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(authorization__destructive_action_approved=value)
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_before_bundling_stops(self):
        response = bundle.assemble_create_thread_callable_bundle(
            valid_request(boundaries__runtime_call_performed=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = bundle.assemble_create_thread_callable_bundle(
            valid_request(boundaries__desktop_private_runtime_state_read=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_prior_evidence_cannot_replace_executor_call_site_validation_or_handling(self):
        cases = (
            (
                "call_site_validation_plan__target_validation__satisfied_by_prior_evidence",
                "target_validation_substituted",
            ),
            (
                "call_site_validation_plan__permission_failure_handling__satisfied_by_prior_evidence",
                "permission_handling_substituted",
            ),
            (
                "call_site_validation_plan__response_validation__satisfied_by_prior_evidence",
                "response_validation_substituted",
            ),
        )
        for path, failure_class in cases:
            with self.subTest(path=path):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(**{path: True})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_human_bundle_marker_returns_fallback(self):
        response = bundle.assemble_create_thread_callable_bundle(
            valid_request(authorization__human_bundle_marker="")
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_bundle_marker_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_malformed_wiring_evidence_stops(self):
        cases = (
            ("callable_wiring_evidence__requested_action", "unknown", "callable_wiring_evidence_mismatch"),
            ("callable_wiring_evidence__runtime_call_performed", True, "runtime_call_already_performed"),
            (
                "callable_wiring_evidence__desktop_runtime_call_performed",
                True,
                "live_desktop_runtime_not_allowed_by_default",
            ),
            (
                "callable_wiring_evidence__result__executor_request_patch__callable_adapter__mode",
                "unknown",
                "callable_adapter_unclear",
            ),
            (
                "callable_wiring_evidence__result__executor_request_patch__callable_adapter__live_desktop_runtime",
                True,
                "live_desktop_runtime_not_allowed_by_default",
            ),
            (
                "callable_wiring_evidence__result__executor_request_patch__callable_adapter__external_write_authorized",
                True,
                "external_write_request",
            ),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(**{path: value})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_generated_executor_request_cannot_include_runner_callable_object_or_direct_runtime_shape(self):
        response = bundle.assemble_create_thread_callable_bundle(valid_request())
        preview = response["result"]["executor_request_preview"]
        forbidden = {
            "runner",
            "callable_object",
            "runtime_callable",
            "direct_runtime_call",
            "runtime_call_shape",
            "callable_descriptor",
            "adapter_registration",
        }
        self.assertFalse(forbidden.intersection(bundle._iter_keys(preview)))

        bad_evidence = valid_wiring_evidence(
            result__executor_request_patch__callable_adapter__runner="call me"
        )
        bad_response = bundle.assemble_create_thread_callable_bundle(
            valid_request(callable_wiring_evidence=bad_evidence)
        )
        self.assertEqual(bad_response["status"], "stopped")
        self.assertEqual(bad_response["failure_class"], "direct_runtime_call_shape_present")

    def test_descriptor_for_unsupported_thread_tools_stops(self):
        cases = (
            ("fork_" + "thread", "fork-thread"),
            ("send_message_" + "to_thread", "send-message"),
            ("read_" + "thread", "read-thread"),
        )
        for tool_name, action_name in cases:
            with self.subTest(tool_name=tool_name):
                response = bundle.assemble_create_thread_callable_bundle(
                    valid_request(
                        callable_wiring_evidence__tool_or_api=tool_name,
                        callable_wiring_evidence__target_action=action_name,
                    )
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "unsupported_thread_tool_path")

    def test_private_runtime_looking_path_or_source_hint_rejected(self):
        response = bundle.assemble_create_thread_callable_bundle(
            valid_request(prompt__body="Read Desktop private runtime state first.")
        )
        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

        reason = bundle._request_path_rejection_reason("/tmp/runtime-state/request.json")
        self.assertIsNotNone(reason)
        self.assertIn("runtime-looking", reason)

    def test_successful_bundle_labels_preview_readiness_not_desktop_execution(self):
        response = bundle.assemble_create_thread_callable_bundle(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["injected_runner_executed"])
        self.assertIn("preview readiness", response["readiness_meaning"])
        self.assertTrue(
            any(
                "executor request preview readiness only" in item
                for item in response["result"]["residual_risk"]
            )
        )

    def test_no_live_desktop_runtime_invocation_in_tests(self):
        response = bundle.assemble_create_thread_callable_bundle(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["external_write_performed"])
        self.assertFalse(response["result"]["executor_request_preview"]["live_desktop_runtime"])

    def test_no_forbidden_runtime_tool_call_shapes_are_introduced(self):
        source = BUNDLE_SCRIPT.read_text(encoding="utf-8")
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
        source = BUNDLE_SCRIPT.read_text(encoding="utf-8").lower()
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
