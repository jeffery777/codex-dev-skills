import copy
import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_create_thread_preflight.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_create_thread_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)


def create_thread_capability(**overrides):
    today = dt.date.today().isoformat()
    capability = {
        "action": "create-thread",
        "tool_or_api": "create_thread",
        "classification": "state-changing",
        "required_request_fields": ["prompt", "target"],
        "optional_request_fields": ["model", "thinking"],
        "minimum_response_fields": ["status", "threadId or thread_id or pendingWorktreeId"],
        "error_response_fields": ["message"],
        "capability_source": "active tool list",
        "contract_version": "version unavailable",
        "last_verified": today,
        "discovery_helper_version": "0.1.0",
    }
    capability.update(overrides)
    return capability


def capability_evidence(capability=None, status="available"):
    return {
        "status": status,
        "capabilities": [] if capability is None else [capability],
    }


def contract_comparison(capability=None, status="compatible", **overrides):
    capability = capability or create_thread_capability()
    comparison = {
        "status": status,
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": "create-thread",
        "comparison_helper_version": "0.1.0",
        "failure_class": None,
        "contract_comparison": {
            "compared_fields": [
                "action",
                "tool_or_api",
                "classification",
                "required_request_fields",
                "minimum_response_fields",
            ],
            "old_contract": copy.deepcopy(capability),
            "new_capability": copy.deepcopy(capability),
        },
        "result": {
            "stop_reason": None,
            "residual_risk": [
                "Comparison used caller-supplied evidence only.",
                "This helper did not call or authorize Desktop thread tools.",
            ],
        },
    }
    for path, value in overrides.items():
        current = comparison
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[int(part)] if isinstance(current, list) else current[part]
        if isinstance(current, list):
            current[int(parts[-1])] = value
        else:
            current[parts[-1]] = value
    return comparison


def valid_request(**overrides):
    capability = create_thread_capability()
    request = {
        "requested_action": "preflight-create-thread-runtime-call",
        "target_action": "create-thread",
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
            "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
        },
        "prompt": {
            "summary": "Prepare a bounded Desktop thread prompt.",
            "body": "Read repo files first, do the scoped task, run tests, and report evidence.",
        },
        "capability_evidence": capability_evidence(capability),
        "contract_comparison": contract_comparison(capability),
        "boundaries": {
            "in_scope": ["scripts/desktop_runtime_create_thread_preflight.py"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": True,
            "authorized_thread_action": "create-thread",
            "external_write_authorized": False,
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


class CreateThreadPreflightTests(unittest.TestCase):
    def test_compatible_create_thread_evidence_with_authorization_returns_ready(self):
        response = preflight.preflight_create_thread(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertEqual(response["capability_evidence"]["classification"], "state-changing")
        self.assertIn("future separately approved runtime call", response["readiness_meaning"])

    def test_thread_action_authorization_false_returns_fallback(self):
        response = preflight.preflight_create_thread(
            valid_request(authorization__thread_action_authorized=False)
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "thread_action_not_authorized")
        self.assertIn(
            "No Desktop thread was opened",
            response["result"]["paste_ready_prompt"],
        )

    def test_missing_capability_returns_fallback(self):
        response = preflight.preflight_create_thread(
            valid_request(capability_evidence=capability_evidence(status="unavailable"))
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")

    def test_missing_comparison_returns_fallback(self):
        request = valid_request()
        request.pop("contract_comparison")

        response = preflight.preflight_create_thread(request)

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "comparison_unavailable")

    def test_contract_comparison_stopped_request_shape_changed_stops(self):
        response = preflight.preflight_create_thread(
            valid_request(
                contract_comparison=contract_comparison(
                    status="stopped",
                    failure_class="request_shape_changed",
                    result__stop_reason="Required request fields changed.",
                )
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "request_shape_changed")

    def test_compatible_comparison_with_mismatched_request_shape_stops(self):
        comparison = contract_comparison()
        comparison["contract_comparison"]["new_capability"]["required_request_fields"] = [
            "prompt",
            "repository",
        ]

        response = preflight.preflight_create_thread(
            valid_request(contract_comparison=comparison)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "request_shape_changed")

    def test_classification_read_only_for_create_thread_stops(self):
        capability = create_thread_capability(classification="read-only")

        response = preflight.preflight_create_thread(
            valid_request(
                capability_evidence=capability_evidence(capability),
                contract_comparison=contract_comparison(capability),
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "classification_mismatch")

    def test_external_write_authorization_true_stops(self):
        response = preflight.preflight_create_thread(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_missing_repo_remote_branch_or_expected_head_stops(self):
        for path, expected in (
            ("target__repo", "target.repo"),
            ("target__remote", "target.remote"),
            ("target__branch", "target.branch"),
            ("target__expected_head", "target.expected_head"),
        ):
            with self.subTest(path=path):
                response = preflight.preflight_create_thread(valid_request(**{path: ""}))

                self.assertEqual(response["status"], "stopped")
                self.assertEqual(response["failure_class"], "validation_error")
                self.assertIn(expected, response["result"]["stop_reason"])

    def test_forbidden_private_source_hint_stops(self):
        capability = create_thread_capability(notes="Derived from Desktop logs.")

        response = preflight.preflight_create_thread(
            valid_request(capability_evidence=capability_evidence(capability))
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_helper_does_not_call_create_thread(self):
        response = preflight.preflight_create_thread(valid_request())

        self.assertFalse(hasattr(preflight, "create_thread"))
        self.assertFalse(response["runtime_call_performed"])
        self.assertIn(
            "This helper did not call create_thread or any Desktop thread tool.",
            response["result"]["residual_risk"],
        )


if __name__ == "__main__":
    unittest.main()
