from __future__ import annotations

import json
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval-memory-contract.py"
SPEC = importlib.util.spec_from_file_location("eval_memory_contract", SCRIPT)
eval_memory = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(eval_memory)


class MemoryContractEvalTests(unittest.TestCase):
    def test_evidence_metric_requires_decision_specific_audit_fields(self) -> None:
        base = {
            "receipt_digest": "a" * 64,
            "authority_invariants": dict(eval_memory.EXPECTED_INVARIANTS["retrieval"]),
            "request_digest": "b" * 64,
            "response_digest": "c" * 64,
            "adapter_fingerprint": "d" * 64,
            "trusted_conformance_digest": None,
            "trusted_source_set_digest": "e" * 64,
            "repository_identity_digest": "f" * 64,
            "dispositions": [{
                "record_id": "record-1",
                "disposition": "quarantine",
                "reasons": ["adapter-disabled"],
                "authority": "advisory-only",
                "confidence_used_as_authority": False,
            }],
        }
        base["receipt_digest"] = eval_memory.memory.canonical_digest({
            key: value for key, value in base.items() if key != "receipt_digest"
        })
        self.assertTrue(eval_memory.evidence_complete(base, "retrieval"))
        for field in ("request_digest", "adapter_fingerprint", "dispositions"):
            incomplete = dict(base)
            del incomplete[field]
            self.assertFalse(eval_memory.evidence_complete(incomplete, "retrieval"))

        tampered = dict(base)
        tampered["request_digest"] = "9" * 64
        self.assertFalse(eval_memory.evidence_complete(tampered, "retrieval"))

        widened = dict(base)
        widened["authority_invariants"] = {
            **base["authority_invariants"],
            "unexpected_authority": False,
        }
        widened["receipt_digest"] = eval_memory.memory.canonical_digest({
            key: value for key, value in widened.items() if key != "receipt_digest"
        })
        self.assertFalse(eval_memory.evidence_complete(widened, "retrieval"))

    def test_incomplete_or_weakened_suite_fails_closed(self) -> None:
        suite = json.loads((ROOT / "evals" / "memory-contract" / "suite.json").read_text())
        variants = []
        missing_threshold = json.loads(json.dumps(suite))
        del missing_threshold["thresholds"]["evidence_completeness_rate"]
        variants.append(missing_threshold)
        empty = json.loads(json.dumps(suite))
        empty["cases"] = []
        variants.append(empty)
        malformed = json.loads(json.dumps(suite))
        del malformed["cases"][0]["expected_fallback"]
        variants.append(malformed)
        reduced = json.loads(json.dumps(suite))
        reduced["cases"] = reduced["cases"][:1]
        variants.append(reduced)
        altered_oracle = json.loads(json.dumps(suite))
        altered_oracle["cases"][0]["expected_outcome"] = "reject"
        variants.append(altered_oracle)
        for index, variant in enumerate(variants):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory) / "suite.json"
                path.write_text(json.dumps(variant), encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--suite", str(path)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(0, result.returncode)

    def test_production_backed_suite_passes(self) -> None:
        result = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual("passed", report["status"])
        self.assertEqual(0, report["metrics"]["false_authority_or_completion_count"])
        self.assertEqual(1.0, report["metrics"]["decision_correctness_rate"])


if __name__ == "__main__":
    unittest.main()
