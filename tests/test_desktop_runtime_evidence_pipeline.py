import copy
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "desktop_runtime_evidence_pipeline.py"
SPEC = importlib.util.spec_from_file_location("desktop_runtime_evidence_pipeline", SCRIPT)
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


def valid_request(**overrides):
    request = pipeline.example_request()
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


def step_outputs(response, name, target_action=None):
    outputs = []
    for step in response["steps"]:
        if step["name"] != name:
            continue
        if target_action is not None and step["target_action"] != target_action:
            continue
        outputs.append(step["output"])
    return outputs


class DesktopRuntimeEvidencePipelineTests(unittest.TestCase):
    def test_discovery_compare_preflight_pipeline_returns_ready_without_runtime_calls(self):
        response = pipeline.build_evidence_pipeline(valid_request())

        self.assertEqual(response["status"], "ready")
        self.assertIsNone(response["failure_class"])
        self.assertFalse(response["runtime_calls_performed"])
        self.assertEqual(len(response["steps"]), 5)
        self.assertEqual(response["summary"]["status"], "ready")
        self.assertEqual(response["summary"]["readiness_counts"]["ready"], 2)
        self.assertIn("evidence only", response["summary"]["recommended_next_step"])

        discovery = step_outputs(response, "capability-discovery")[0]
        self.assertEqual(discovery["status"], "available")

        create_comparison = step_outputs(response, "contract-comparison", "create-thread")[0]
        read_comparison = step_outputs(response, "contract-comparison", "read-thread")[0]
        self.assertEqual(create_comparison["status"], "compatible")
        self.assertEqual(read_comparison["status"], "compatible")

        create_preflight = step_outputs(response, "runtime-call-preflight", "create-thread")[0]
        read_preflight = step_outputs(response, "runtime-call-preflight", "read-thread")[0]
        self.assertEqual(create_preflight["status"], "ready")
        self.assertEqual(read_preflight["status"], "ready")
        self.assertFalse(create_preflight["runtime_call_performed"])
        self.assertFalse(read_preflight["runtime_call_performed"])

    def test_missing_old_contract_returns_pipeline_fallback(self):
        request = valid_request()
        request["old_contracts"].pop("create-thread")

        response = pipeline.build_evidence_pipeline(request)

        self.assertEqual(response["status"], "fallback")
        self.assertEqual(response["failure_class"], "missing_old_contract")
        self.assertEqual(response["summary"]["readiness_counts"]["fallback"], 1)
        self.assertEqual(
            response["summary"]["target_results"][0]["reason"],
            "Contract comparison helper returned fallback.",
        )
        create_preflight = step_outputs(response, "runtime-call-preflight", "create-thread")[0]
        self.assertEqual(create_preflight["status"], "fallback")
        self.assertEqual(create_preflight["failure_class"], "comparison_unavailable")
        self.assertIn("No Desktop thread was opened", create_preflight["result"]["paste_ready_prompt"])

    def test_changed_request_shape_stops_pipeline_before_ready_claim(self):
        request = valid_request()
        request["metadata_request"]["capabilities"][0]["request"]["required"] = [
            "prompt",
            "repository",
        ]

        response = pipeline.build_evidence_pipeline(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "request_shape_changed")
        self.assertEqual(response["summary"]["readiness_counts"]["stopped"], 1)
        self.assertEqual(response["summary"]["target_results"][0]["status"], "stopped")
        create_comparison = step_outputs(response, "contract-comparison", "create-thread")[0]
        create_preflight = step_outputs(response, "runtime-call-preflight", "create-thread")[0]
        self.assertEqual(create_comparison["status"], "stopped")
        self.assertEqual(create_preflight["status"], "stopped")
        self.assertFalse(create_preflight["runtime_call_performed"])

    def test_read_thread_authorization_true_stops_as_out_of_scope(self):
        request = valid_request()
        request["authorization"]["thread_action_authorized"]["read-thread"] = True

        response = pipeline.build_evidence_pipeline(request)

        self.assertEqual(response["status"], "stopped")
        read_preflight = step_outputs(response, "runtime-call-preflight", "read-thread")[0]
        self.assertEqual(read_preflight["failure_class"], "runtime_call_authorization_out_of_scope")

    def test_external_write_authorization_must_be_explicit_false(self):
        request = valid_request()
        request["authorization"]["external_write_authorized"] = "false"

        response = pipeline.build_evidence_pipeline(request)

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "external_write_request")
        self.assertEqual(response["steps"], [])

    def test_pipeline_request_is_not_mutated(self):
        request = valid_request()
        original = copy.deepcopy(request)

        pipeline.build_evidence_pipeline(request)

        self.assertEqual(request, original)

    def test_single_target_action_runs_only_selected_preflight(self):
        request = valid_request(target_actions=["read-thread"])

        response = pipeline.build_evidence_pipeline(request)

        self.assertEqual(response["status"], "ready")
        self.assertEqual(len(response["steps"]), 3)
        self.assertEqual(response["summary"]["readiness_counts"]["ready"], 1)
        self.assertEqual(response["summary"]["target_results"][0]["target_action"], "read-thread")
        self.assertEqual(step_outputs(response, "runtime-call-preflight", "create-thread"), [])
        read_preflight = step_outputs(response, "runtime-call-preflight", "read-thread")[0]
        self.assertEqual(read_preflight["status"], "ready")

    def test_invalid_target_action_entry_stops_with_clear_validation_error(self):
        response = pipeline.build_evidence_pipeline(valid_request(target_actions=[{"action": "read-thread"}]))

        self.assertEqual(response["status"], "stopped")
        self.assertEqual(response["failure_class"], "validation_error")
        self.assertEqual(response["summary"]["primary_reason"], "target_actions[0] must be a non-empty string.")
        self.assertEqual(response["steps"], [])

    def test_cli_target_action_override_filters_request(self):
        request = valid_request()
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump(request, handle)
            handle.flush()
            output = io.StringIO()
            with redirect_stdout(output):
                rc = pipeline.main(["--request", handle.name, "--target-action", "read-thread"])

        response = json.loads(output.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(response["target_actions"], ["read-thread"])
        self.assertEqual(len(response["steps"]), 3)
        self.assertEqual(response["summary"]["target_results"][0]["target_action"], "read-thread")

    def test_cli_example_target_action_override_filters_example(self):
        output = io.StringIO()
        with redirect_stdout(output):
            rc = pipeline.main(["--example", "--target-action", "create-thread"])

        request = json.loads(output.getvalue())
        self.assertEqual(rc, 0)
        self.assertEqual(request["target_actions"], ["create-thread"])

    def test_cli_duplicate_target_action_override_exits_before_example_output(self):
        output = io.StringIO()
        errors = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with redirect_stdout(output), redirect_stderr(errors):
                pipeline.main(
                    [
                        "--example",
                        "--target-action",
                        "read-thread",
                        "--target-action",
                        "read-thread",
                    ]
                )

        self.assertEqual(raised.exception.code, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("Duplicate target_action: read-thread", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
