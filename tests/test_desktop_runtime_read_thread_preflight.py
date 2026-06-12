import copy
import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_read_thread_preflight.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_read_thread_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)

DISCOVERY_SCRIPT = ROOT / "scripts" / "desktop_runtime_capability_discovery.py"
DISCOVERY_SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_capability_discovery_for_read_preflight_tests",
    DISCOVERY_SCRIPT,
)
discovery = importlib.util.module_from_spec(DISCOVERY_SPEC)
DISCOVERY_SPEC.loader.exec_module(discovery)

COMPARE_SCRIPT = ROOT / "scripts" / "desktop_runtime_contract_compare.py"
COMPARE_SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_contract_compare_for_read_preflight_tests",
    COMPARE_SCRIPT,
)
contract_compare = importlib.util.module_from_spec(COMPARE_SPEC)
COMPARE_SPEC.loader.exec_module(contract_compare)


def read_thread_capability(**overrides):
    today = dt.date.today().isoformat()
    capability = {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["threadId"],
        "optional_request_fields": ["turnLimit", "cursor", "includeOutputs", "maxOutputCharsPerItem"],
        "minimum_response_fields": ["status", "threadId"],
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
    capability = capability or read_thread_capability()
    comparison = {
        "status": status,
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": "read-thread",
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


def discovery_request(**overrides):
    today = dt.date.today().isoformat()
    request = {
        "requested_action": "normalize-runtime-capability-metadata",
        "metadata_source": {
            "source": "active tool list",
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
                    "required": ["threadId"],
                    "optional": ["turnLimit", "cursor", "includeOutputs", "maxOutputCharsPerItem"],
                },
                "response": {
                    "required": ["status", "threadId"],
                    "errors": ["message"],
                },
                "source": "active tool list",
                "contract_version": "version unavailable",
                "last_verified": today,
            }
        ],
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


def comparison_request(capability_evidence_response):
    return {
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": "read-thread",
        "old_contract": read_thread_capability(),
        "new_capability_evidence": capability_evidence_response,
    }


def valid_request(**overrides):
    capability = read_thread_capability()
    request = {
        "requested_action": "preflight-read-thread-runtime-call",
        "target_action": "read-thread",
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
            "thread_id": "thread-123",
        },
        "read_request": {
            "summary": "Check read-only thread evidence readiness.",
            "expected_fields": ["status", "threadId"],
        },
        "capability_evidence": capability_evidence(capability),
        "contract_comparison": contract_comparison(capability),
        "boundaries": {
            "in_scope": ["scripts/desktop_runtime_read_thread_preflight.py"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": False,
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


class ReadThreadPreflightTests(unittest.TestCase):
    def test_discovery_compare_preflight_evidence_chain_returns_ready(self):
        normalized = discovery.normalize_capability_metadata(discovery_request())
        comparison = contract_compare.compare_contract_evidence(comparison_request(normalized))
        request = valid_request(capability_evidence=normalized, contract_comparison=comparison)

        response = preflight.preflight_read_thread(request)

        self.assertEqual(normalized["status"], "available")
        self.assertEqual(comparison["status"], "compatible")
        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_call_performed"])
        self.assertEqual(response["capability_evidence"]["classification"], "read-only")
        self.assertIn("future separately approved read-only runtime call", response["readiness_meaning"])

    def test_missing_capability_returns_fallback(self):
        response = preflight.preflight_read_thread(
            valid_request(capability_evidence=capability_evidence(status="unavailable"))
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")
        self.assertIn(
            "No Desktop thread was opened",
            response["result"]["paste_ready_prompt"],
        )

    def test_missing_comparison_returns_fallback(self):
        request = valid_request()
        request.pop("contract_comparison")

        response = preflight.preflight_read_thread(request)

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "comparison_unavailable")

    def test_contract_comparison_stopped_request_shape_changed_stops(self):
        response = preflight.preflight_read_thread(
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

    def test_state_changing_classification_for_read_thread_stops(self):
        capability = read_thread_capability(classification="state-changing")

        response = preflight.preflight_read_thread(
            valid_request(
                capability_evidence=capability_evidence(capability),
                contract_comparison=contract_comparison(capability),
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "classification_mismatch")

    def test_authorized_runtime_call_is_out_of_scope_for_preflight(self):
        response = preflight.preflight_read_thread(
            valid_request(authorization__thread_action_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "runtime_call_authorization_out_of_scope")

    def test_external_write_authorization_true_stops(self):
        response = preflight.preflight_read_thread(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_missing_thread_id_stops(self):
        response = preflight.preflight_read_thread(valid_request(target__thread_id=""))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("target.thread_id", response["result"]["stop_reason"])

    def test_legacy_thread_id_contract_evidence_still_returns_ready(self):
        capability = read_thread_capability(
            required_request_fields=["thread_id"],
            optional_request_fields=["include_metadata"],
            minimum_response_fields=["status", "thread_id"],
        )

        response = preflight.preflight_read_thread(
            valid_request(
                capability_evidence=capability_evidence(capability),
                contract_comparison=contract_comparison(capability),
                read_request__expected_fields=["status", "thread_id"],
            )
        )

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])

    def test_missing_expected_fields_stops(self):
        response = preflight.preflight_read_thread(valid_request(read_request__expected_fields=[]))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("read_request.expected_fields", response["result"]["stop_reason"])

    def test_forbidden_private_source_hint_stops(self):
        capability = read_thread_capability(notes="Derived from Desktop logs.")

        response = preflight.preflight_read_thread(
            valid_request(capability_evidence=capability_evidence(capability))
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_forbidden_expected_field_hint_stops(self):
        response = preflight.preflight_read_thread(
            valid_request(read_request__expected_fields=["status", "Desktop logs"])
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_helper_does_not_call_read_thread(self):
        response = preflight.preflight_read_thread(valid_request())

        self.assertFalse(hasattr(preflight, "read_thread"))
        self.assertFalse(response["runtime_call_performed"])
        self.assertIn(
            "This helper did not call read_thread or any Desktop thread tool.",
            response["result"]["residual_risk"],
        )


if __name__ == "__main__":
    unittest.main()
