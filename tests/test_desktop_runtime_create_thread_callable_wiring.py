import copy
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_callable_wiring.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_callable_wiring", SCRIPT)
wiring = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wiring)


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
    request = wiring.example_request()
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


def valid_previous_executor_evidence(**overrides):
    evidence = copy.deepcopy(wiring.example_request()["previous_executor_evidence"])
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


class CreateThreadCallableWiringTests(unittest.TestCase):
    def test_complete_caller_supplied_documented_descriptor_returns_ready(self):
        response = wiring.wire_create_thread_callable_descriptor(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertEqual(
            response["readiness_label"],
            "callable-wiring-readiness-not-desktop-runtime-execution",
        )
        self.assertEqual(
            response["result"]["adapter_contract"]["mode"],
            "explicit-injected-documented-callable-adapter",
        )
        self.assertFalse(response["result"]["adapter_contract"]["live_desktop_runtime"])
        self.assertTrue(
            any("callable wiring readiness only" in item for item in response["result"]["residual_risk"])
        )

    def test_cli_default_without_callable_descriptor_returns_fallback(self):
        request = valid_request()
        request.pop("callable_descriptor")
        response = wiring.wire_create_thread_callable_descriptor(request)

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "callable_descriptor_missing")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertFalse(response["runtime_call_performed"])

    def test_missing_previous_executor_contract_evidence_stops(self):
        request = valid_request()
        request.pop("previous_executor_evidence")
        response = wiring.wire_create_thread_callable_descriptor(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("previous_executor_evidence", response["result"]["stop_reason"])

    def test_fallback_or_stopped_previous_evidence_blocks(self):
        cases = (
            ("fallback", "previous_executor_evidence_fallback"),
            ("stopped", "executor_stopped"),
        )
        for status, expected_failure in cases:
            with self.subTest(status=status):
                response = wiring.wire_create_thread_callable_descriptor(
                    valid_request(
                        previous_executor_evidence=valid_previous_executor_evidence(
                            status=status,
                            failure_class="executor_stopped",
                            result__stop_reason="executor stopped",
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
            ("callable_descriptor__target_action", "read-thread", "unsupported_thread_tool_path"),
            ("callable_descriptor__tool_or_api", "fork_thread", "unsupported_thread_tool_path"),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = wiring.wire_create_thread_callable_descriptor(valid_request(**{path: value}))

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
                response = wiring.wire_create_thread_callable_descriptor(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_missing_prompt_summary_or_body_stops(self):
        for path, expected in (("prompt__summary", "prompt.summary"), ("prompt__body", "prompt.body")):
            with self.subTest(path=path):
                response = wiring.wire_create_thread_callable_descriptor(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_external_write_authorized_true_stops(self):
        response = wiring.wire_create_thread_callable_descriptor(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = wiring.wire_create_thread_callable_descriptor(
                    valid_request(authorization__destructive_action_approved=value)
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_runtime_call_performed_true_before_wiring_stops(self):
        response = wiring.wire_create_thread_callable_descriptor(
            valid_request(boundaries__runtime_call_performed=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_already_performed")

    def test_desktop_private_runtime_state_read_true_stops(self):
        response = wiring.wire_create_thread_callable_descriptor(
            valid_request(boundaries__desktop_private_runtime_state_read=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_prior_evidence_cannot_replace_executor_call_site_validation_or_handling(self):
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
                response = wiring.wire_create_thread_callable_descriptor(valid_request(**{path: True}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_missing_human_wiring_marker_returns_fallback(self):
        response = wiring.wire_create_thread_callable_descriptor(
            valid_request(authorization__human_wiring_marker="")
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_wiring_marker_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_malformed_callable_descriptor_stops(self):
        for descriptor in ({}, "not an object"):
            with self.subTest(descriptor=descriptor):
                request = valid_request()
                request["callable_descriptor"] = descriptor
                response = wiring.wire_create_thread_callable_descriptor(request)

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "callable_descriptor_malformed")

        cases = (
            ("callable_descriptor__descriptor_type", "unknown", "callable_descriptor_malformed"),
            ("callable_descriptor__source_type", "unknown", "callable_descriptor_source_unclear"),
            ("callable_descriptor__caller_supplied", False, "callable_descriptor_source_unclear"),
            ("callable_descriptor__documented_callable", False, "callable_descriptor_source_unclear"),
            ("callable_descriptor__execution_allowed", True, "runtime_call_authorization_present"),
            (
                "callable_descriptor__runtime_lookup_performed",
                True,
                "runtime_callable_lookup_performed",
            ),
            ("callable_descriptor__runtime_call_shape_present", True, "direct_runtime_call_shape_present"),
            ("callable_descriptor__live_desktop_runtime", True, "live_desktop_runtime_not_allowed_by_default"),
            ("callable_descriptor__external_write_authorized", True, "external_write_request"),
            ("callable_descriptor__required_request_fields", ["prompt.body"], "callable_descriptor_malformed"),
            ("callable_descriptor__minimum_response_fields", ["thread_id"], "callable_descriptor_malformed"),
            ("callable_descriptor__source_excerpt", "", "callable_descriptor_source_unclear"),
            ("callable_descriptor__last_verified", "", "callable_descriptor_source_unclear"),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = wiring.wire_create_thread_callable_descriptor(valid_request(**{path: value}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)

    def test_forbidden_thread_tool_descriptors_stop(self):
        cases = (
            ("fork_" + "thread", "fork-thread"),
            ("send_message_" + "to_thread", "send-message"),
            ("read_" + "thread", "read-thread"),
        )
        for tool_name, action_name in cases:
            with self.subTest(tool_name=tool_name):
                response = wiring.wire_create_thread_callable_descriptor(
                    valid_request(
                        callable_descriptor__tool_or_api=tool_name,
                        callable_descriptor__target_action=action_name,
                        callable_descriptor__allowed_target_actions=[action_name],
                    )
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "unsupported_thread_tool_path")

    def test_private_runtime_looking_path_or_source_hint_rejected(self):
        response = wiring.wire_create_thread_callable_descriptor(
            valid_request(callable_descriptor__source_excerpt="Read Desktop private runtime state first.")
        )
        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

        reason = wiring._request_path_rejection_reason("/tmp/runtime-state/descriptor.json")
        self.assertIsNotNone(reason)
        self.assertIn("runtime-looking", reason)

    def test_successful_non_live_wiring_is_not_desktop_runtime_execution(self):
        request = valid_request(
            callable_descriptor__descriptor_type="explicit-non-live-adapter-wiring-contract",
            callable_descriptor__source_type="explicit-non-live-adapter-wiring-contract",
        )
        response = wiring.wire_create_thread_callable_descriptor(request)

        self.assertEqual(response["status"], "ready")
        self.assertEqual(
            response["result"]["adapter_contract"]["mode"],
            "explicit-injected-non-live-test-adapter",
        )
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertIn("wiring readiness", response["readiness_meaning"])

    def test_no_live_desktop_runtime_invocation_in_tests(self):
        response = wiring.wire_create_thread_callable_descriptor(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["desktop_runtime_call_performed"])
        self.assertFalse(response["external_write_performed"])

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
