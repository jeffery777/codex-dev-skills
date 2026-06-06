import copy
import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_authorization_gate.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_authorization_gate", SCRIPT)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


TARGET = {
    "repo": "owner/name",
    "remote": "https://github.com/owner/name.git",
    "branch": "codex/create-thread-runtime-call",
    "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
}

SESSION_IDENTITY = {
    "marker_type": "current-session",
    "marker": "current-session scoped",
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


def valid_preflight(**overrides):
    evidence = {
        "status": "ready",
        "requested_action": "preflight-create-thread-runtime-call",
        "target_action": "create-thread",
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "target_evidence": copy.deepcopy(TARGET),
        "result": {"stop_reason": None},
    }
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def valid_status(**overrides):
    today = dt.date.today().isoformat()
    evidence = {
        "status": "ready",
        "target_action": "create-thread",
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "later_runtime_path_blocked": False,
        "validated_status": {
            "target_action": "create-thread",
            "tool_or_api": "create_thread",
            "schema_hash": "sha256:example",
            "comparison_result": "compatible",
            "last_verified": today,
            "session_identity": copy.deepcopy(SESSION_IDENTITY),
        },
        "result": {"stop_reason": None},
    }
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def valid_cache(**overrides):
    today = dt.date.today().isoformat()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    evidence = {
        "status": "ready",
        "target_action": "create-thread",
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "cache_read_performed": True,
        "later_runtime_path_blocked": False,
        "cache_evidence": {
            "target_action": "create-thread",
            "tool_or_api": "create_thread",
            "schema_hash": "sha256:example",
            "comparison_result": "compatible",
            "last_verified": today,
            "cache_scope": "same-session",
            "same_session_only": True,
            "created_at": now,
            "session_identity": copy.deepcopy(SESSION_IDENTITY),
        },
        "result": {"stop_reason": None},
    }
    for path, value in overrides.items():
        set_path(evidence, path, value)
    return evidence


def valid_request(**overrides):
    request = {
        "requested_action": "authorize-create-thread-runtime-call-envelope",
        "target_action": "create-thread",
        "tool_or_api": "create_thread",
        "target": copy.deepcopy(TARGET),
        "prompt": {
            "summary": "Prepare one create-thread runtime-call implementation slice.",
            "body": "Implement the separately approved runtime-call path and run verification.",
        },
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": "create-thread",
            "human_approval_marker": "human-approval-required-before-runtime-call-implementation",
            "human_approval_scope": "next-step-implementation-only",
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "target_validation": {
            "caller_confirmed": True,
            **copy.deepcopy(TARGET),
        },
        "permission_failure_handling": {
            "requirements_declared": True,
            "satisfied_by_preflight_or_cache": False,
            "requirements": [
                "stop on auth or permission failure",
                "surface runtime error response for human review",
            ],
        },
        "runtime_response_validation": {
            "requirements_declared": True,
            "satisfied_by_preflight_or_cache": False,
            "minimum_response_fields": ["status", "thread_id"],
        },
        "current_session_identity": copy.deepcopy(SESSION_IDENTITY),
        "preflight_evidence": valid_preflight(),
        "session_status_evidence": valid_status(),
        "session_cache_evidence": valid_cache(),
    }
    for path, value in overrides.items():
        set_path(request, path, value)
    return request


class CreateThreadAuthorizationGateTests(unittest.TestCase):
    def test_complete_caller_supplied_envelope_returns_ready(self):
        response = gate.authorize_create_thread_runtime_call_envelope(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["external_write_performed"])
        self.assertIn("does not authorize or perform a runtime call", response["readiness_meaning"])

    def test_missing_exact_target_action_or_tool_api_stops(self):
        cases = (
            ("target_action", "read-thread", "target_action_mismatch"),
            ("tool_or_api", "read_thread", "tool_or_api_mismatch"),
        )
        for path, value, failure_class in cases:
            with self.subTest(path=path):
                response = gate.authorize_create_thread_runtime_call_envelope(
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
                response = gate.authorize_create_thread_runtime_call_envelope(
                    valid_request(**{path: ""})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_fallback_or_stopped_preflight_cache_status_evidence_blocks(self):
        cases = (
            ("preflight_evidence", valid_preflight(status="fallback"), "preflight_evidence_fallback"),
            ("session_status_evidence", valid_status(status="fallback"), "session_status_evidence_fallback"),
            ("session_cache_evidence", valid_cache(status="fallback"), "session_cache_evidence_fallback"),
            ("preflight_evidence", valid_preflight(status="stopped"), "preflight_evidence_stopped"),
            ("session_status_evidence", valid_status(status="stopped"), "session_status_evidence_stopped"),
            ("session_cache_evidence", valid_cache(status="stopped"), "session_cache_evidence_stopped"),
        )
        for path, evidence, failure_class in cases:
            with self.subTest(path=path, status=evidence["status"]):
                response = gate.authorize_create_thread_runtime_call_envelope(
                    valid_request(**{path: evidence})
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], failure_class)
                self.assertTrue(response["later_runtime_path_blocked"])

    def test_stale_or_session_mismatched_cache_evidence_blocks(self):
        yesterday = (
            dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        stale_response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(session_cache_evidence=valid_cache(cache_evidence__expires_at=yesterday))
        )
        mismatch_response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(
                session_cache_evidence=valid_cache(
                    cache_evidence__session_identity__marker="different-session"
                )
            )
        )

        self.assertEqual(stale_response["status"], "stopped")
        self.assertEqual(stale_response["failure_class"], "stale_or_expired_cache")
        self.assertEqual(mismatch_response["status"], "stopped")
        self.assertEqual(mismatch_response["failure_class"], "session_marker_mismatch")

    def test_external_write_authorized_true_stops(self):
        response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_destructive_action_approval_present_or_true_stops(self):
        for value in (True, "approved"):
            with self.subTest(value=value):
                response = gate.authorize_create_thread_runtime_call_envelope(
                    valid_request(authorization__destructive_action_approved=value)
                )

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "destructive_action_approval_present")

    def test_cache_and_preflight_cannot_replace_runtime_call_authorization(self):
        response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(authorization__authorized_runtime_action="")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("authorization.authorized_runtime_action", response["result"]["stop_reason"])

    def test_cache_and_preflight_cannot_replace_target_validation(self):
        response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(target_validation__caller_confirmed=False)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "target_validation_missing")

    def test_cache_and_preflight_cannot_replace_permission_or_response_validation(self):
        permission_response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(permission_failure_handling__satisfied_by_preflight_or_cache=True)
        )
        response_validation_response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(runtime_response_validation__satisfied_by_preflight_or_cache=True)
        )

        self.assertEqual(permission_response["status"], "stopped")
        self.assertEqual(permission_response["failure_class"], "permission_handling_substituted")
        self.assertEqual(response_validation_response["status"], "stopped")
        self.assertEqual(response_validation_response["failure_class"], "response_validation_substituted")

    def test_missing_human_approval_marker_returns_fallback(self):
        response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(authorization__human_approval_marker="")
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "human_approval_boundary_missing")
        self.assertTrue(response["later_runtime_path_blocked"])

    def test_private_runtime_looking_source_hint_is_rejected(self):
        response = gate.authorize_create_thread_runtime_call_envelope(
            valid_request(prompt__body="Inspect Desktop logs before implementation.")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_no_desktop_private_runtime_state_is_read(self):
        response = gate.authorize_create_thread_runtime_call_envelope(valid_request())

        self.assertFalse(response["private_runtime_state_read"])
        self.assertFalse(response["boundary_evidence"]["desktop_private_runtime_state_read"])

    def test_no_desktop_thread_tool_call_functions_are_introduced(self):
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
