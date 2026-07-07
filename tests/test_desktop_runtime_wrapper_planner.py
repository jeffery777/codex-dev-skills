import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_wrapper_planner.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_wrapper_planner", SCRIPT)
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)

DISCOVERY_SCRIPT = ROOT / "scripts" / "desktop_runtime_capability_discovery.py"
DISCOVERY_SPEC = importlib.util.spec_from_file_location(
    "desktop_runtime_capability_discovery_for_planner_tests",
    DISCOVERY_SCRIPT,
)
discovery = importlib.util.module_from_spec(DISCOVERY_SPEC)
DISCOVERY_SPEC.loader.exec_module(discovery)


def valid_request(**overrides):
    request = {
        "action": "plan-thread-action",
        "target_action": "create-thread",
        "runtime_contract": {
            "tool_or_api": "create_thread",
            "underlying_contract_version": "version unavailable",
            "capability_source": "active tool list",
            "last_verified": dt.date.today().isoformat(),
            "wrapper_version": "0.1.0",
        },
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
        },
        "prompt": {
            "summary": "Prepare a bounded implementation prompt.",
            "body": "Read repo files first, implement the scoped change, run tests, and report evidence.",
        },
        "boundaries": {
            "in_scope": ["scripts/desktop_runtime_wrapper_planner.py"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": True,
            "external_write_authorized": False,
        },
    }
    for path, value in overrides.items():
        current = request
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    return request


def valid_discovery_request(action="read-thread", classification="read-only", **overrides):
    today = dt.date.today().isoformat()
    tool_by_action = {
        "create-thread": "create_thread",
        "fork-thread": "fork_thread",
        "send-message": "send_message_to_thread",
        "read-thread": "read_thread",
    }
    required_by_action = {
        "create-thread": ["prompt", "target"],
        "fork-thread": [],
        "send-message": ["threadId", "prompt"],
        "read-thread": ["threadId"],
    }
    optional_by_action = {
        "create-thread": ["model", "thinking", "target.environment.startingState"],
        "fork-thread": ["threadId", "environment"],
        "send-message": ["hostId", "model", "thinking"],
        "read-thread": ["hostId", "turnLimit", "cursor", "includeOutputs", "maxOutputCharsPerItem"],
    }
    response_by_action = {
        "create-thread": ["status", "threadId or thread_id or pendingWorktreeId"],
        "fork-thread": ["status", "threadId"],
        "send-message": ["status", "threadId"],
        "read-thread": ["status", "threadId"],
    }
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
                "action": action,
                "tool_or_api": tool_by_action[action],
                "classification": classification,
                "request": {
                    "required": required_by_action[action],
                    "optional": optional_by_action[action],
                },
                "response": {
                    "required": response_by_action[action],
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


def request_with_capability_evidence(target_action="read-thread", evidence=None, **overrides):
    request = valid_request(target_action=target_action)
    request.pop("runtime_contract")
    request["authorization"]["thread_action_authorized"] = False
    if target_action in {"fork-thread", "send-message", "read-thread"}:
        request["target"]["thread_id"] = "thread-123"
    request["capability_evidence"] = evidence
    for path, value in overrides.items():
        current = request
        parts = path.split("__")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = value
    return request


class PlannerTests(unittest.TestCase):
    def test_valid_request_returns_dry_run(self):
        response = planner.plan_request(valid_request())

        self.assertEqual(response["status"], "dry-run")
        self.assertEqual(response["requested_action"], "plan-thread-action")
        self.assertIsNone(response["failure_class"])
        self.assertIn("runtime_contract.tool_or_api", response["request_shape_relied_on"]["required"])

    def test_missing_required_field_stops(self):
        request = valid_request()
        request["target"].pop("repo")

        response = planner.plan_request(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertIn("target.repo", response["result"]["stop_reason"])

    def test_missing_capability_generates_cli_fallback(self):
        response = planner.plan_request(
            valid_request(
                runtime_contract__available=False,
                runtime_contract__capability_source="unavailable",
            )
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")
        self.assertIn(
            "No Desktop thread was opened/forked/continued/messaged/read",
            response["result"]["paste_ready_prompt"],
        )

    def test_missing_contract_evidence_stops(self):
        response = planner.plan_request(
            valid_request(runtime_contract__capability_source="chat summary")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_contract_evidence")

    def test_external_write_request_stops(self):
        response = planner.plan_request(
            valid_request(authorization__external_write_authorized=True)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_external_write_request_stops_before_missing_capability_fallback(self):
        response = planner.plan_request(
            valid_request(
                authorization__external_write_authorized=True,
                runtime_contract__available=False,
                runtime_contract__capability_source="unavailable",
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_external_write_request_stops_before_capability_evidence_fallback(self):
        evidence = {"status": "unavailable", "capabilities": []}

        response = planner.plan_request(
            request_with_capability_evidence(
                "send-message",
                evidence,
                authorization__external_write_authorized=True,
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")

    def test_forbidden_private_runtime_state_hint_stops(self):
        response = planner.plan_request(
            valid_request(prompt__body="Read the Desktop SQLite database before planning.")
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_forbidden_private_runtime_state_boundary_text_is_allowed(self):
        response = planner.plan_request(
            valid_request(
                prompt__body=(
                    "Do not read Desktop SQLite databases. Keep Desktop private runtime "
                    "state out of scope."
                )
            )
        )

        self.assertEqual(response["status"], "dry-run")

    def test_state_changing_action_without_authorization_falls_back(self):
        response = planner.plan_request(
            valid_request(authorization__thread_action_authorized=False)
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "state_changing_thread_action_not_authorized")
        self.assertIn(
            "No Desktop thread was opened/forked/continued/messaged/read",
            response["result"]["paste_ready_prompt"],
        )

    def test_discovery_output_can_feed_planner(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("read-thread", "read-only")
        )

        response = planner.plan_request(
            request_with_capability_evidence("read-thread", evidence)
        )

        self.assertEqual(response["status"], "dry-run")
        self.assertEqual(response["runtime_contract"]["tool_or_api"], "read_thread")
        self.assertEqual(
            response["runtime_contract"]["normalized_capability"]["classification"],
            "read-only",
        )
        self.assertIn("threadId", response["response_shape_relied_on"]["required"])

    def test_missing_capability_evidence_falls_back(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("read-thread", "read-only")
        )

        response = planner.plan_request(
            request_with_capability_evidence("send-message", evidence)
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_capability")
        self.assertIn("does not include send-message", response["result"]["stop_reason"])

    def test_capability_classification_mismatch_stops(self):
        evidence = {
            "status": "available",
            "capabilities": [
                {
                    "action": "create-thread",
                    "tool_or_api": "create_thread",
                    "classification": "read-only",
                    "required_request_fields": ["prompt", "target"],
                    "optional_request_fields": [],
                    "minimum_response_fields": [
                        "status",
                        "threadId or thread_id or pendingWorktreeId",
                    ],
                    "error_response_fields": ["message"],
                    "capability_source": "active tool list",
                    "contract_version": "version unavailable",
                    "last_verified": dt.date.today().isoformat(),
                }
            ],
        }

        response = planner.plan_request(
            request_with_capability_evidence("create-thread", evidence)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "classification_mismatch")

    def test_capability_shape_unclear_stops(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("read-thread", "read-only")
        )
        evidence["capabilities"][0]["minimum_response_fields"] = []

        response = planner.plan_request(
            request_with_capability_evidence("read-thread", evidence)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "missing_contract_evidence")
        self.assertIn("shape is unclear", response["result"]["stop_reason"])

    def test_state_changing_capability_without_authorization_falls_back(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("create-thread", "state-changing")
        )

        response = planner.plan_request(
            request_with_capability_evidence("create-thread", evidence)
        )

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "state_changing_thread_action_not_authorized")
        self.assertIn(
            "No Desktop thread was opened/forked/continued/messaged/read",
            response["result"]["paste_ready_prompt"],
        )

    def test_fork_thread_optional_only_capability_without_authorization_falls_back(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("fork-thread", "state-changing")
        )

        response = planner.plan_request(
            request_with_capability_evidence("fork-thread", evidence)
        )

        self.assertEqual(evidence["status"], "available")
        self.assertEqual(
            evidence["capabilities"][0]["required_request_fields"],
            [],
        )
        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "state_changing_thread_action_not_authorized")

    def test_forbidden_private_source_hint_in_capability_evidence_stops(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("read-thread", "read-only")
        )
        evidence["capabilities"][0]["notes"] = "Derived from Desktop logs."

        response = planner.plan_request(
            request_with_capability_evidence("read-thread", evidence)
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_forbidden_private_runtime_hint_stops_before_capability_evidence_fallback(self):
        evidence = {"status": "unavailable", "capabilities": []}

        response = planner.plan_request(
            request_with_capability_evidence(
                "read-thread",
                evidence,
                prompt__body="Read the Desktop SQLite database before planning.",
            )
        )

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "forbidden_private_runtime_state")

    def test_read_thread_capability_evidence_dry_run_does_not_call_thread_tool(self):
        evidence = discovery.normalize_capability_metadata(
            valid_discovery_request("read-thread", "read-only")
        )

        response = planner.plan_request(
            request_with_capability_evidence("read-thread", evidence)
        )

        self.assertEqual(response["status"], "dry-run")
        self.assertIn(
            "This first slice does not call a Desktop thread tool.",
            response["result"]["residual_risk"],
        )
        self.assertEqual(response["target_action"], "read-thread")
        self.assertEqual(response["runtime_contract"]["tool_or_api"], "read_thread")


if __name__ == "__main__":
    unittest.main()
