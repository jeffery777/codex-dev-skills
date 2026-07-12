from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests import test_memory_contract as fixtures


ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "loop-engineering" / "scripts" / "memoryctl.py"


def run_cli(
    command: str,
    document: dict | str,
    *,
    trusted: dict | None = None,
    trusted_sources: dict | None = None,
    trusted_acceptance: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory) / "document.json"
        if isinstance(document, str):
            path.write_text(document, encoding="utf-8")
        else:
            path.write_text(json.dumps(document), encoding="utf-8")
        command_line = [sys.executable, str(CLI), command, str(path)]
        if trusted is not None:
            trusted_path = pathlib.Path(directory) / "trusted.json"
            trusted_path.write_text(json.dumps(trusted), encoding="utf-8")
            command_line.extend(["--trusted-conformance-receipts", str(trusted_path)])
        if trusted_sources is not None:
            sources_path = pathlib.Path(directory) / "trusted-sources.json"
            sources_path.write_text(json.dumps(trusted_sources), encoding="utf-8")
            command_line.extend(["--trusted-source-digests", str(sources_path)])
        if trusted_acceptance is not None:
            acceptance_path = pathlib.Path(directory) / "trusted-acceptance.json"
            acceptance_path.write_text(json.dumps({"receipt_digests": trusted_acceptance}), encoding="utf-8")
            command_line.extend(["--trusted-acceptance-receipt-digests", str(acceptance_path)])
        return subprocess.run(
            command_line,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )


class MemoryCtlTests(unittest.TestCase):
    def test_validate_and_digest_succeed_on_stdout(self):
        document = fixtures.handshake()
        validated = run_cli("validate", document)
        self.assertEqual(0, validated.returncode, validated.stderr)
        self.assertEqual("valid", json.loads(validated.stdout)["status"])
        self.assertEqual("", validated.stderr)
        digested = run_cli("digest", document)
        self.assertEqual(0, digested.returncode, digested.stderr)
        self.assertEqual(fixtures.memory.canonical_digest(document), json.loads(digested.stdout)["canonical_sha256"])

    def test_invalid_duplicate_and_unknown_documents_exit_one_on_stderr(self):
        cases = (
            '{"kind":"query-request","kind":"memory-record"}',
            {"contract_version": fixtures.memory.CONTRACT_VERSION, "kind": "backend-document"},
        )
        for document in cases:
            with self.subTest(document=document):
                result = run_cli("validate", document)
                self.assertEqual(1, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual("rejected", json.loads(result.stderr)["status"])

    def test_deep_json_is_rejected_without_a_traceback(self):
        document = "[" * 1_200 + "0" + "]" * 1_200
        result = run_cli("validate", document)
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        error = json.loads(result.stderr)
        self.assertEqual("rejected", error["status"])
        self.assertNotIn("Traceback", result.stderr)

    def test_lone_unicode_surrogate_is_a_structured_rejection(self):
        result = run_cli("digest", '{"value":"\\ud800"}')
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        error = json.loads(result.stderr)
        self.assertEqual("rejected", error["status"])
        self.assertIn("invalid Unicode scalar", error["errors"][0])
        self.assertNotIn("Traceback", result.stderr)

        handshake = fixtures.handshake()
        handshake["adapter"]["adapter_version"] = "\ud800"
        validated = run_cli("validate", handshake)
        self.assertEqual(1, validated.returncode)
        self.assertEqual("", validated.stdout)
        validation_error = json.loads(validated.stderr)
        self.assertEqual("rejected", validation_error["status"])
        self.assertIn("valid Unicode scalar", validation_error["errors"][0])
        self.assertNotIn("Traceback", validated.stderr)

    def test_decision_commands_emit_receipts_without_authority_escalation(self):
        retrieval = run_cli(
            "decide-retrieval",
            fixtures.retrieval_input(),
            trusted={"fake-memory-adapter-test-only": {
                "receipt_digest": "c" * 64,
                "adapter_fingerprint": fixtures.memory.canonical_digest({
                    "adapter": fixtures.handshake()["adapter"],
                    "capabilities": fixtures.handshake()["capabilities"],
                }),
            }},
            trusted_sources={"skills/loop-engineering/SKILL.md": "e" * 64},
        )
        self.assertEqual(0, retrieval.returncode, retrieval.stderr)
        retrieval_receipt = json.loads(retrieval.stdout)
        self.assertFalse(retrieval_receipt["authority_invariants"]["mutation_authorized"])
        self.assertFalse(retrieval_receipt["authority_invariants"]["completion_proven"])
        self.assertEqual("adopt-as-context", retrieval_receipt["dispositions"][0]["disposition"])
        write_input = fixtures.write_input()
        write = run_cli(
            "decide-write",
            write_input,
            trusted_acceptance=[item["receipt_digest"] for item in write_input["accepted_evidence"]],
        )
        self.assertEqual(0, write.returncode, write.stderr)
        write_receipt = json.loads(write.stdout)
        self.assertTrue(write_receipt["eligible"])
        self.assertFalse(write_receipt["authority_invariants"]["write_performed"])

    def test_conformance_exit_zero_can_only_mean_contract_cases_passed(self):
        transcript = fixtures.conformance_transcript()
        trusted_sources, trusted_acceptance = (
            fixtures.WriteEligibilityAndConformanceTests.conformance_evidence(transcript)
        )
        result = run_cli(
            "conformance",
            transcript,
            trusted_sources=trusted_sources,
            trusted_acceptance=trusted_acceptance,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertTrue(receipt["passed"])
        self.assertFalse(receipt["production_backend_implemented"])

        transcript["cases"][0]["input"]["current"]["seen_response_nonces"] = ["nonce-1"]
        failed = run_cli(
            "conformance",
            transcript,
            trusted_sources=trusted_sources,
            trusted_acceptance=trusted_acceptance,
        )
        self.assertEqual(1, failed.returncode)
        self.assertFalse(json.loads(failed.stdout)["passed"])

        transcript = fixtures.conformance_transcript()
        transcript["cases"][0]["input"] = []
        malformed = run_cli(
            "conformance",
            transcript,
            trusted_sources=trusted_sources,
            trusted_acceptance=trusted_acceptance,
        )
        self.assertEqual(1, malformed.returncode)
        self.assertEqual("", malformed.stdout)
        self.assertEqual("rejected", json.loads(malformed.stderr)["status"])
        self.assertNotIn("Traceback", malformed.stderr)


if __name__ == "__main__":
    unittest.main()
