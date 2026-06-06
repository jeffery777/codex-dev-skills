import copy
import importlib.util
import pathlib
import unittest


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


if __name__ == "__main__":
    unittest.main()
