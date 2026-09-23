from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "docs" / "loops" / "issue-292" / "event_evidence.py"
SPEC = importlib.util.spec_from_file_location("issue_292_event_evidence", PATH)
assert SPEC is not None and SPEC.loader is not None
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)


class Issue292EventEvidenceTests(unittest.TestCase):
    def test_rejects_malformed_and_truncated_jsonl_bytes(self):
        for raw in (b'{"type":"turn.completed"\n', b'{"type":'):
            result = evidence.inspect(raw, b"done\n")
            self.assertEqual("invalid", result["stream_integrity"])
            self.assertIn("malformed_json", {item["error_class"] for item in result["errors"]})

    def test_rejects_non_object_and_final_mismatch(self):
        raw = b'[]\n{"type":"item.completed","item":{"type":"agent_message","text":"actual"}}\n{"type":"turn.completed"}\n'
        result = evidence.inspect(raw, b"different\n")
        self.assertEqual("invalid", result["stream_integrity"])
        self.assertEqual({"non_object_json", "final_message_mismatch"}, {item["error_class"] for item in result["errors"]})

    def test_accepts_normal_pair_without_creating_command_evidence(self):
        raw = b'{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n{"type":"turn.completed","usage":{"input_tokens":1}}\n'
        result = evidence.inspect(raw, b"done\n")
        self.assertEqual("valid", result["stream_integrity"])
        self.assertEqual("completed", result["turn_status"])
        self.assertEqual("not_assessed", result["tool_coverage"])
        self.assertEqual(0, result["command_event_count"])
        self.assertEqual({"input_tokens": 1}, result["usage"])

    def test_turn_failed_is_not_completion(self):
        raw = b'{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n{"type":"turn.failed"}\n'
        result = evidence.inspect(raw, b"done\n")
        self.assertEqual("invalid", result["stream_integrity"])
        self.assertIn("terminal_failure", {item["error_class"] for item in result["errors"]})

    def test_counts_only_completed_nested_command_and_rejects_empty_final(self):
        raw = b'{"type":"item.started","item":{"type":"command_execution"}}\n{"type":"item.completed","item":{"type":"command_execution"}}\n{"type":"item.completed","item":{"type":"agent_message","text":"done"}}\n{"type":"turn.completed"}\n'
        result = evidence.inspect(raw, b"")
        self.assertEqual(1, result["command_event_count"])
        self.assertEqual("invalid", result["stream_integrity"])
        self.assertIn("empty_final_output", {item["error_class"] for item in result["errors"]})


if __name__ == "__main__":
    unittest.main()
