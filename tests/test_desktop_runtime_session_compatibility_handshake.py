import copy
import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_session_compatibility_handshake.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_session_compatibility_handshake", SCRIPT)
handshake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handshake)


def valid_request(**overrides):
    today = dt.date.today().isoformat()
    request = {
        "requested_action": "build-session-compatibility-handshake",
        "target_action": "read-thread",
        "expected": {
            "repo_commit": "fb5e3483c7f6630de991413a4e64eeb0aaa14790",
            "handshake_helper_version": "0.1.0",
            "status_helper_version": "0.1.0",
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
        },
        "old_contract": {
            "action": "read-thread",
            "tool_or_api": "read_thread",
            "classification": "read-only",
            "required_request_fields": ["thread_id"],
            "minimum_response_fields": ["status", "thread_id"],
            "capability_source": "runtime-reported schema",
            "contract_version": "version unavailable",
            "last_verified": today,
            "repo_commit": "fb5e3483c7f6630de991413a4e64eeb0aaa14790",
        },
        "metadata_request": {
            "requested_action": "normalize-runtime-capability-metadata",
            "metadata_source": {
                "source": "runtime-reported schema",
                "contract_version": "version unavailable",
                "last_verified": today,
                "available": True,
            },
            "capabilities": [
                {
                    "action": "read-thread",
                    "tool_or_api": "read_thread",
                    "classification": "read-only",
                    "request": {
                        "required": ["thread_id"],
                        "optional": ["include_metadata"],
                    },
                    "response": {
                        "required": ["status", "thread_id"],
                        "errors": ["message"],
                    },
                    "source": "runtime-reported schema",
                    "contract_version": "version unavailable",
                    "last_verified": today,
                }
            ],
        },
        "session_identity": {
            "marker_type": "current-session",
            "marker": "current-session scoped",
        },
    }
    for path, value in overrides.items():
        current = request
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[int(part)] if isinstance(current, list) else current[part]
        if isinstance(current, list):
            current[int(parts[-1])] = value
        else:
            current[parts[-1]] = value
    return request


def step_output(response, name):
    for step in response["steps"]:
        if step["name"] == name:
            return step["output"]
    return None


class SessionCompatibilityHandshakeTests(unittest.TestCase):
    def test_compatible_first_use_handshake_creates_validated_ready_status(self):
        response = handshake.build_session_compatibility_handshake(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_calls_performed"])
        self.assertFalse(response["cache_read_performed"])
        self.assertFalse(response["cache_write_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["later_runtime_path_blocked"])
        self.assertEqual(response["session_compatibility_status"]["comparison_result"], "compatible")
        self.assertEqual(response["validated_status"]["status"], "ready")
        self.assertIn("first-use handshake evidence only", response["summary"]["recommended_next_step"])

    def test_fallback_comparison_produces_fallback_and_blocks_later_runtime_path(self):
        request = valid_request(metadata_request__metadata_source__available=False)

        response = handshake.build_session_compatibility_handshake(request)

        self.assertEqual(response["status"], "fallback")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertEqual(step_output(response, "contract-comparison")["status"], "fallback")
        self.assertEqual(response["session_compatibility_status"]["comparison_result"], "fallback")
        self.assertEqual(response["validated_status"]["status"], "fallback")

    def test_stopped_comparison_produces_stopped_and_blocks_later_runtime_path(self):
        request = valid_request(
            metadata_request__capabilities__0__request__required=["thread_id", "include_metadata"]
        )

        response = handshake.build_session_compatibility_handshake(request)

        self.assertEqual(response["status"], "stopped")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertEqual(step_output(response, "contract-comparison")["status"], "stopped")
        self.assertEqual(response["session_compatibility_status"]["comparison_result"], "stopped")
        self.assertEqual(response["validated_status"]["status"], "stopped")

    def test_wrapper_version_mismatch_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(old_contract__repo_commit="different")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")
        self.assertEqual(response["steps"], [])

    def test_handshake_helper_version_mismatch_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(expected__handshake_helper_version="9.9.9")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_status_helper_version_mismatch_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(expected__status_helper_version="9.9.9")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_expected_schema_hash_mismatch_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(expected__schema_hash="sha256:wrong")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "contract_evidence_mismatch")
        self.assertEqual(response["validated_status"]["failure_class"], "contract_evidence_mismatch")

    def test_expected_normalized_contract_evidence_mismatch_stops(self):
        today = dt.date.today().isoformat()
        response = handshake.build_session_compatibility_handshake(
            valid_request(
                expected__normalized_contract_evidence={
                    "action": "read-thread",
                    "tool_or_api": "read_thread",
                    "classification": "read-only",
                    "required_request_fields": ["thread_id"],
                    "minimum_response_fields": ["status", "thread_id", "title"],
                    "capability_source": "runtime-reported schema",
                    "contract_version": "version unavailable",
                    "last_verified": today,
                }
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "contract_evidence_mismatch")

    def test_missing_session_marker_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(session_identity__marker="")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_session_marker")
        self.assertEqual(response["validated_status"]["failure_class"], "missing_session_marker")

    def test_explicit_current_session_scoped_marker_is_accepted(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(
                session_identity__marker_type="current-session",
                session_identity__marker="current-session scoped",
            )
        )

        self.assertEqual(response["status"], "ready")
        self.assertEqual(
            response["session_compatibility_status"]["session_identity"]["marker"],
            "current-session scoped",
        )

    def test_status_cannot_replace_authorization_or_validation(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(authorization={"thread_action_authorized": True})
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "authorization_out_of_scope")
        self.assertIn("thread_action_authorized", response["result"]["stop_reason"])

    def test_private_runtime_state_metadata_stops(self):
        response = handshake.build_session_compatibility_handshake(
            valid_request(metadata_request__capabilities__0__notes="Derived from Desktop private runtime state.")
        )

        self.assertEqual(response["status"], "stopped")
        discovery = step_output(response, "capability-discovery")
        self.assertEqual(discovery["failure_class"], "forbidden_private_runtime_state")

    def test_no_cache_read_write_or_runtime_call_symbols(self):
        response = handshake.build_session_compatibility_handshake(valid_request())

        self.assertFalse(hasattr(handshake, "create_thread"))
        self.assertFalse(hasattr(handshake, "fork_thread"))
        self.assertFalse(hasattr(handshake, "send_message_to_thread"))
        self.assertFalse(hasattr(handshake, "read_thread"))
        self.assertFalse(response["runtime_calls_performed"])
        self.assertFalse(response["cache_read_performed"])
        self.assertFalse(response["cache_write_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertIn(
            "This helper did not read or write a compatibility cache.",
            response["result"]["residual_risk"],
        )

    def test_request_is_not_mutated(self):
        request = valid_request()
        original = copy.deepcopy(request)

        handshake.build_session_compatibility_handshake(request)

        self.assertEqual(request, original)


if __name__ == "__main__":
    unittest.main()
