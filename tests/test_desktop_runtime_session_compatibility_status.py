import copy
import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_session_compatibility_status.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_session_compatibility_status", SCRIPT)
session_status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(session_status)


def normalized_contract(**overrides):
    today = dt.date.today().isoformat()
    contract = {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["thread_id"],
        "minimum_response_fields": ["status", "thread_id"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": today,
    }
    contract.update(overrides)
    return contract


def valid_request(**overrides):
    today = dt.date.today().isoformat()
    contract = normalized_contract()
    contract_hash = session_status._contract_hash(contract)
    request = {
        "requested_action": "validate-session-compatibility-status",
        "expected": {
            "repo_commit": "9211a0f5eb44dfd17502ecc60bab430b397dfdfd",
            "helper_version": "0.1.0",
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "schema_hash": contract_hash,
        },
        "compatibility_status": {
            "repo_commit": "9211a0f5eb44dfd17502ecc60bab430b397dfdfd",
            "helper_version": "0.1.0",
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "runtime_reported_version": "version unavailable",
            "capability_source": "runtime-reported schema",
            "schema_hash": contract_hash,
            "comparison_result": "compatible",
            "last_verified": today,
            "session_identity": {
                "marker_type": "current-session",
                "marker": "current-session scoped",
            },
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


class SessionCompatibilityStatusTests(unittest.TestCase):
    def test_valid_compatible_status_returns_ready(self):
        response = session_status.validate_session_compatibility_status(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["cache_write_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["later_runtime_path_blocked"])
        self.assertIn("later preflight reference only", response["readiness_meaning"])

    def test_fallback_status_blocks_later_runtime_path(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__comparison_result="fallback")
        )

        self.assertEqual(response["status"], "fallback")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertEqual(response["failure_class"], "session_compatibility_fallback")

    def test_stopped_status_blocks_later_runtime_path(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__comparison_result="stopped")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertTrue(response["later_runtime_path_blocked"])
        self.assertEqual(response["failure_class"], "session_compatibility_stopped")

    def test_wrapper_version_mismatch_stops(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__repo_commit="different")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_helper_version_mismatch_stops(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__helper_version="9.9.9")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_stale_expected_helper_version_stops_even_when_status_matches(self):
        request = valid_request()
        request["expected"]["helper_version"] = "9.9.9"
        request["compatibility_status"]["helper_version"] = "9.9.9"

        response = session_status.validate_session_compatibility_status(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "wrapper_or_helper_version_mismatch")

    def test_schema_hash_mismatch_stops(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__schema_hash="sha256:wrong")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "contract_evidence_mismatch")

    def test_normalized_contract_evidence_mismatch_stops(self):
        request = valid_request()
        request["expected"].pop("schema_hash")
        request["compatibility_status"].pop("schema_hash")
        request["expected"]["normalized_contract_evidence"] = normalized_contract()
        request["compatibility_status"]["normalized_contract_evidence"] = normalized_contract(
            minimum_response_fields=["status", "thread_id", "title"]
        )

        response = session_status.validate_session_compatibility_status(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "contract_evidence_mismatch")

    def test_missing_session_marker_stops(self):
        request = valid_request()
        request["compatibility_status"]["session_identity"]["marker"] = ""

        response = session_status.validate_session_compatibility_status(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_session_marker")

    def test_current_session_requires_explicit_current_scoped_marker(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__session_identity__marker="runtime did not say")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_session_marker")

    def test_status_cannot_replace_authorization_or_target_validation(self):
        request = valid_request()
        request["compatibility_status"]["thread_action_authorized"] = True
        request["compatibility_status"]["target_validated"] = True
        request["compatibility_status"]["response_validated"] = True

        response = session_status.validate_session_compatibility_status(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "authorization_out_of_scope")
        self.assertIn("thread_action_authorized", response["result"]["stop_reason"])
        self.assertIn("target_validated", response["result"]["stop_reason"])
        self.assertIn("response_validated", response["result"]["stop_reason"])

    def test_forbidden_private_runtime_state_hint_stops(self):
        response = session_status.validate_session_compatibility_status(
            valid_request(compatibility_status__notes="Derived from Desktop private runtime state.")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_helper_does_not_define_runtime_thread_calls_or_private_state_readers(self):
        response = session_status.validate_session_compatibility_status(valid_request())

        self.assertFalse(hasattr(session_status, "create_thread"))
        self.assertFalse(hasattr(session_status, "fork_thread"))
        self.assertFalse(hasattr(session_status, "send_message_to_thread"))
        self.assertFalse(hasattr(session_status, "read_thread"))
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["cache_write_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertIn(
            "This helper did not call Desktop thread tools or read Desktop private runtime state.",
            response["result"]["residual_risk"],
        )

    def test_request_is_not_mutated(self):
        request = valid_request()
        original = copy.deepcopy(request)

        session_status.validate_session_compatibility_status(request)

        self.assertEqual(request, original)


if __name__ == "__main__":
    unittest.main()
