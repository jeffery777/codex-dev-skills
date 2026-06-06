import datetime as dt
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_wrapper_planner.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_wrapper_planner", SCRIPT)
planner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(planner)


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


if __name__ == "__main__":
    unittest.main()
