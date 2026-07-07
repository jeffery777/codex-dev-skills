import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_contract_compare.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_contract_compare", SCRIPT)
contract_compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract_compare)


def old_contract(action="read-thread", **overrides):
    today = dt.date.today().isoformat()
    tool_by_action = {
        "create-thread": "create_thread",
        "fork-thread": "fork_thread",
        "send-message": "send_message_to_thread",
        "read-thread": "read_thread",
    }
    classification_by_action = {
        "create-thread": "state-changing",
        "fork-thread": "state-changing",
        "send-message": "state-changing",
        "read-thread": "read-only",
    }
    required_by_action = {
        "create-thread": ["prompt", "target"],
        "fork-thread": [],
        "send-message": ["threadId", "prompt"],
        "read-thread": ["threadId"],
    }
    response_by_action = {
        "create-thread": ["status", "threadId or thread_id or pendingWorktreeId"],
        "fork-thread": ["status", "threadId"],
        "send-message": ["status", "threadId"],
        "read-thread": ["status", "threadId"],
    }
    contract = {
        "action": action,
        "tool_or_api": tool_by_action[action],
        "classification": classification_by_action[action],
        "required_request_fields": required_by_action[action],
        "minimum_response_fields": response_by_action[action],
        "capability_source": "active tool list",
        "contract_version": "version unavailable",
        "last_verified": today,
        "wrapper_version": "0.1.0",
    }
    contract.update(overrides)
    return contract


def capability(action="read-thread", **overrides):
    contract = old_contract(action)
    normalized = {
        "action": contract["action"],
        "tool_or_api": contract["tool_or_api"],
        "classification": contract["classification"],
        "required_request_fields": contract["required_request_fields"],
        "optional_request_fields": [],
        "minimum_response_fields": contract["minimum_response_fields"],
        "error_response_fields": ["message"],
        "capability_source": "runtime-reported schema",
        "contract_version": contract["contract_version"],
        "last_verified": contract["last_verified"],
        "discovery_helper_version": "0.1.0",
    }
    normalized.update(overrides)
    return normalized


def evidence(*capabilities, status="available"):
    return {
        "status": status,
        "capabilities": list(capabilities),
    }


def compare_request(action="read-thread", old=None, new_evidence=None, **overrides):
    request = {
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": action,
        "old_contract": old or old_contract(action),
        "new_capability_evidence": new_evidence or evidence(capability(action)),
    }
    request.update(overrides)
    return request


class ContractCompareTests(unittest.TestCase):
    def test_compatible_read_thread_evidence_returns_compatible(self):
        response = contract_compare.compare_contract_evidence(compare_request())

        self.assertEqual(response["status"], "compatible")
        self.assertIsNone(response["failure_class"])
        self.assertEqual(response["contract_comparison"]["new_capability"]["tool_or_api"], "read_thread")
        self.assertIn("did not call", response["result"]["residual_risk"][1])

    def test_new_optional_fields_do_not_change_minimum_contract(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(
                "read-thread",
                new_evidence=evidence(
                    capability(
                        "read-thread",
                        optional_request_fields=[
                            "hostId",
                            "turnLimit",
                            "cursor",
                            "includeOutputs",
                            "maxOutputCharsPerItem",
                        ],
                    )
                ),
            )
        )

        self.assertEqual(response["status"], "compatible")

        response = contract_compare.compare_contract_evidence(
            compare_request(
                "create-thread",
                new_evidence=evidence(
                    capability(
                        "create-thread",
                        optional_request_fields=[
                            "model",
                            "thinking",
                            "target.environment.startingState",
                        ],
                    )
                ),
            )
        )

        self.assertEqual(response["status"], "compatible")

        response = contract_compare.compare_contract_evidence(
            compare_request(
                "send-message",
                new_evidence=evidence(
                    capability(
                        "send-message",
                        optional_request_fields=["hostId", "model", "thinking"],
                    )
                ),
            )
        )

        self.assertEqual(response["status"], "compatible")

    def test_missing_capability_returns_fallback(self):
        response = contract_compare.compare_contract_evidence(
            compare_request("send-message", new_evidence=evidence(capability("read-thread")))
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")
        self.assertIn("send-message", response["result"]["stop_reason"])

    def test_unavailable_capability_returns_fallback(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(new_evidence=evidence(status="unavailable"))
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")

    def test_request_shape_changed_stops(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(
                new_evidence=evidence(
                    capability("read-thread", required_request_fields=["threadId", "includeOutputs"])
                )
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "request_shape_changed")

    def test_response_shape_changed_stops(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(
                new_evidence=evidence(
                    capability("read-thread", minimum_response_fields=["status", "threadId", "title"])
                )
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "response_shape_changed")

    def test_classification_changed_stops(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(
                new_evidence=evidence(capability("read-thread", classification="state-changing"))
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "classification_changed")

    def test_tool_or_api_name_changed_stops(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(new_evidence=evidence(capability("read-thread", tool_or_api="read_thread_v2")))
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "tool_or_api_changed")

    def test_forbidden_private_source_hint_stops(self):
        response = contract_compare.compare_contract_evidence(
            compare_request(
                new_evidence=evidence(
                    capability("read-thread", notes="Derived from Desktop private runtime state.")
                )
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_state_changing_create_thread_evidence_can_compare_without_authorizing_call(self):
        response = contract_compare.compare_contract_evidence(compare_request("create-thread"))

        self.assertEqual(response["status"], "compatible")
        self.assertEqual(response["contract_comparison"]["old_contract"]["classification"], "state-changing")
        self.assertIn(
            "State-changing capabilities remain evidence only",
            response["result"]["residual_risk"][2],
        )

    def test_fork_thread_optional_request_fields_can_compare_without_required_fields(self):
        response = contract_compare.compare_contract_evidence(compare_request("fork-thread"))

        self.assertEqual(response["status"], "compatible")
        self.assertEqual(
            response["contract_comparison"]["old_contract"]["required_request_fields"],
            [],
        )


if __name__ == "__main__":
    unittest.main()
