import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_capability_discovery.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_capability_discovery", SCRIPT)
discovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discovery)


def valid_request(**overrides):
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
                    "optional": [
                        "hostId",
                        "turnLimit",
                        "cursor",
                        "includeOutputs",
                        "maxOutputCharsPerItem",
                    ],
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


class CapabilityDiscoveryTests(unittest.TestCase):
    def test_valid_read_only_metadata_returns_available(self):
        response = discovery.normalize_capability_metadata(valid_request())

        self.assertEqual(response["status"], "available")
        self.assertIsNone(response["failure_class"])
        self.assertEqual(response["capabilities"][0]["classification"], "read-only")
        self.assertEqual(response["capabilities"][0]["required_request_fields"], ["threadId"])
        self.assertIn("hostId", response["capabilities"][0]["optional_request_fields"])
        self.assertIn("did not call", response["result"]["residual_risk"][1])

    def test_valid_state_changing_metadata_is_normalized_without_calling(self):
        request = valid_request()
        capability = request["capabilities"][0]
        capability["action"] = "create-thread"
        capability["tool_or_api"] = "create_thread"
        capability["classification"] = "state-changing"
        capability["request"]["required"] = ["prompt", "target"]
        capability["request"]["optional"] = ["model", "thinking", "target.environment.startingState"]
        capability["response"]["required"] = ["status", "threadId or thread_id or pendingWorktreeId"]

        response = discovery.normalize_capability_metadata(request)

        self.assertEqual(response["status"], "available")
        self.assertEqual(response["capabilities"][0]["classification"], "state-changing")
        self.assertEqual(response["capabilities"][0]["tool_or_api"], "create_thread")
        self.assertIn(
            "target.environment.startingState",
            response["capabilities"][0]["optional_request_fields"],
        )

    def test_send_message_host_id_metadata_is_normalized_without_calling(self):
        request = valid_request()
        capability = request["capabilities"][0]
        capability["action"] = "send-message"
        capability["tool_or_api"] = "send_message_to_thread"
        capability["classification"] = "state-changing"
        capability["request"]["required"] = ["threadId", "prompt"]
        capability["request"]["optional"] = ["hostId", "model", "thinking"]
        capability["response"]["required"] = ["status", "threadId"]

        response = discovery.normalize_capability_metadata(request)

        self.assertEqual(response["status"], "available")
        self.assertEqual(
            response["capabilities"][0]["tool_or_api"],
            "send_message_to_thread",
        )
        self.assertIn("hostId", response["capabilities"][0]["optional_request_fields"])

    def test_fork_thread_optional_only_metadata_is_normalized_without_calling(self):
        request = valid_request()
        capability = request["capabilities"][0]
        capability["action"] = "fork-thread"
        capability["tool_or_api"] = "fork_thread"
        capability["classification"] = "state-changing"
        capability["request"]["required"] = []
        capability["request"]["optional"] = ["threadId", "environment"]
        capability["response"]["required"] = ["status", "threadId"]

        response = discovery.normalize_capability_metadata(request)

        self.assertEqual(response["status"], "available")
        self.assertEqual(response["capabilities"][0]["required_request_fields"], [])
        self.assertEqual(
            response["capabilities"][0]["optional_request_fields"],
            ["threadId", "environment"],
        )

    def test_metadata_reported_unavailable_returns_unavailable(self):
        response = discovery.normalize_capability_metadata(
            valid_request(metadata_source__available=False)
        )

        self.assertEqual(response["status"], "unavailable")
        self.assertEqual(response["failure_class"], "missing_capability_metadata")

    def test_missing_required_capability_field_stops(self):
        request = valid_request()
        request["capabilities"][0]["request"].pop("required")

        response = discovery.normalize_capability_metadata(request)

        self.assertEqual(response["status"], "stopped")
        self.assertIn("capabilities[0].request.required", response["result"]["stop_reason"])

    def test_unknown_classification_stops_instead_of_guessing(self):
        response = discovery.normalize_capability_metadata(
            valid_request(capabilities__0__classification="maybe-read-only")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_contract_evidence")

    def test_unrecognized_source_stops(self):
        response = discovery.normalize_capability_metadata(
            valid_request(metadata_source__source="chat summary")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_contract_evidence")

    def test_invalid_last_verified_stops(self):
        response = discovery.normalize_capability_metadata(
            valid_request(capabilities__0__last_verified="today")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_contract_evidence")

    def test_forbidden_private_runtime_source_hint_stops(self):
        response = discovery.normalize_capability_metadata(
            valid_request(metadata_source__source="runtime-reported schema")
        )
        self.assertEqual(response["status"], "available")

        request = valid_request()
        request["capabilities"][0]["source"] = "runtime-reported schema"
        request["capabilities"][0]["notes"] = "Derived from Desktop logs."

        response = discovery.normalize_capability_metadata(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")


if __name__ == "__main__":
    unittest.main()
