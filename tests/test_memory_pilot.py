from __future__ import annotations

import copy
import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import memory_pilot as pilot  # noqa: E402
import memory_pilot_off as off  # noqa: E402
import memory_sqlite as adapter  # noqa: E402
import memory_contract as memory  # noqa: E402
import memory_operation as operation  # noqa: E402
from tests import test_memory_sqlite as fixtures  # noqa: E402
from tests import test_memory_contract as record_fixtures  # noqa: E402


def load_eval_module():
    path = ROOT / "scripts" / "eval-memory-pilot.py"
    spec = importlib.util.spec_from_file_location("memory_pilot_eval", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def envelope(action: str, pilot_class: str = "verified-fact") -> dict:
    result = {
        "profile": pilot.PROFILE, "action": action, "pilot_class": pilot_class,
        "scope": ["skills/loop-engineering"], "tokens": ["evidence", "repository"],
    }
    if action == "invalidate":
        result.pop("pilot_class")
    return result


def profiled_bundle(
    state: pathlib.Path,
    *,
    pilot_class: str = "verified-fact",
    suffix: str = "pilot",
    record_id: str = "record-1",
    supersedes: list[str] | None = None,
    content: str | None = None,
) -> tuple[dict, dict, dict, dict]:
    authority, candidate, _, _ = fixtures.qualified_bundle(state, suffix=suffix)
    record = candidate["record"]
    record["record_id"] = record_id
    record["backend_locator"] = f"opaque-{record_id}"
    record["idempotency"] = {
        "request_id": f"write-request-{suffix}",
        "idempotency_key": f"write-key-{suffix}",
        "sequence": 1,
    }
    record["lifecycle"]["supersedes"] = supersedes or []
    if content is not None:
        record["content"] = content
    record["extensions"][pilot.PILOT_EXTENSION] = {
        "profile": pilot.PROFILE, "pilot_class": pilot_class,
    }
    record["canonical_digest"] = memory.canonical_digest(memory.record_body(record))
    eligibility = record_fixtures.decide_write(record_fixtures.write_input(candidate=record))
    candidate["target_record_id"] = record_id
    candidate["eligibility_receipt_digest"] = eligibility["receipt_digest"]
    authority["payload"].update({
        "candidate_record_digest": record["canonical_digest"],
        "target_record_id": record_id,
        "mutation_candidate_digest": memory.canonical_digest(candidate),
        "eligibility_receipt_digests": [eligibility["receipt_digest"]],
    })
    authority = operation.seal_document(authority)
    context = fixtures.operation_fixtures.validation_context(authority, candidate, eligibility)
    return authority, candidate, eligibility, context


def reseal_bundle(authority: dict, candidate: dict) -> tuple[dict, dict, dict, dict]:
    record = candidate["record"]
    record["canonical_digest"] = memory.canonical_digest(memory.record_body(record))
    eligibility = record_fixtures.decide_write(record_fixtures.write_input(candidate=record))
    candidate["eligibility_receipt_digest"] = eligibility["receipt_digest"]
    authority["payload"].update({
        "candidate_record_digest": record["canonical_digest"],
        "mutation_candidate_digest": memory.canonical_digest(candidate),
        "eligibility_receipt_digests": [eligibility["receipt_digest"]],
    })
    authority = operation.seal_document(authority)
    context = fixtures.operation_fixtures.validation_context(authority, candidate, eligibility)
    return authority, candidate, eligibility, context


class MemoryPilotTests(unittest.TestCase):
    def test_off_is_zero_touch_and_does_not_need_adapter(self):
        with mock.patch.object(adapter, "probe", side_effect=AssertionError("backend touched")):
            result = off.no_memory()
        self.assertEqual("memory-off", result["status"])
        self.assertEqual(0, result["backend_touch_count"])

    def test_envelope_is_versioned_strict_and_private_data_fails_before_backend(self):
        self.assertEqual(envelope("remember"), pilot.validate_envelope(envelope("remember"), action="remember"))
        for value in ("alpha OR beta", "/private/path/secret", "api_key=not-safe", "a@example.com"):
            unsafe = envelope("remember")
            unsafe["tokens"] = [value]
            with mock.patch.object(adapter, "execute_authorized_operation", side_effect=AssertionError("backend touched")):
                with self.assertRaisesRegex(pilot.MemoryPilotError, "request rejected"):
                    pilot.validate_envelope(unsafe, action="remember")
        bad = envelope("remember", "decision")
        bad["pilot_class"] = "durable-lesson"
        with self.assertRaises(pilot.MemoryPilotError):
            pilot.validate_envelope(bad, action="remember")
        for field, value in (("scope", [1, "x"]), ("tokens", [{"x": 1}])):
            malformed = envelope("remember")
            malformed[field] = value
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.validate_envelope(malformed, action="remember")

    def test_remember_rejects_nonminimal_chat_log_path_config_and_credentials(self):
        unsafe_values = (
            "user: hello assistant: done",
            "2026-09-04 INFO build passed",
            "stored at /secret",
            "Bearer ghp_exampletoken",
            "AWS key AKIA1234567890ABCDEF",
            "Slack token xoxb-1234567890abcdef",
            "OpenAI key sk-proj-syntheticexample123456",
            "OpenAI key sk-syntheticexample123456789",
            "OpenAI key sk-svcacct-syntheticexample123456",
            "setting=value",
            "line one\nline two",
            "x" * (pilot.MAX_PILOT_CONTENT_BYTES + 1),
        )
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            for index, value in enumerate(unsafe_values):
                authority, candidate, eligibility, context = profiled_bundle(state, suffix=f"unsafe-{index}")
                candidate["record"]["content"] = value
                candidate["record"]["canonical_digest"] = memory.canonical_digest(memory.record_body(candidate["record"]))
                with mock.patch.object(adapter, "execute_authorized_operation", side_effect=AssertionError("backend touched")):
                    with self.assertRaises(pilot.MemoryPilotError):
                        pilot.remember(
                            envelope("remember"), authority, candidate, eligibility,
                            accepted_authority_receipts=context["accepted_authority_receipts"],
                            accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                            trusted_time=context["trusted_time_value"],
                            accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                            expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
                        )

    def test_remember_preserves_existing_m0_authority_chain_and_invalidate_is_logical(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            receipt = pilot.remember(
                envelope("remember"), authority, candidate, eligibility,
                accepted_authority_receipts=context["accepted_authority_receipts"],
                accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                trusted_time=context["trusted_time_value"],
                accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
            )
            self.assertEqual("applied", receipt["payload"]["outcome"])
            replay = pilot.remember(
                envelope("remember"), authority, candidate, eligibility,
                accepted_authority_receipts=context["accepted_authority_receipts"],
                accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                trusted_time=context["trusted_time_value"],
                accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
            )
            self.assertEqual("idempotent-replay", replay["payload"]["outcome"])
            invalid_authority, invalid_candidate, invalid_eligibility, invalid_context = fixtures.qualified_bundle(state, "invalidate", suffix="pilot-invalidate")
            invalid_authority["payload"]["target_before_digest"] = candidate["record"]["canonical_digest"]
            invalid_authority = operation.seal_document(invalid_authority)
            invalid_context = fixtures.operation_fixtures.validation_context(invalid_authority, invalid_candidate, invalid_eligibility)
            invalidated = pilot.invalidate(
                envelope("invalidate", "constraint"), invalid_authority, invalid_candidate, invalid_eligibility,
                accepted_authority_receipts=invalid_context["accepted_authority_receipts"],
                accepted_eligibility_receipts=invalid_context["accepted_eligibility_receipts"],
                trusted_time=invalid_context["trusted_time_value"],
                accepted_trusted_time_receipts=invalid_context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=candidate["record"]["canonical_digest"], state_root=state, repository_root=ROOT,
            )
            self.assertEqual("applied", invalidated["payload"]["outcome"])
            self.assertEqual(1, adapter.integrity(state, ROOT)["counts"]["records"])

    def test_profile_binding_is_digest_bound_and_scope_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            candidate["record"]["extensions"][pilot.PILOT_EXTENSION]["pilot_class"] = "decision"
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.remember(envelope("remember"), authority, candidate, eligibility,
                    accepted_authority_receipts=context["accepted_authority_receipts"], accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time=context["trusted_time_value"], accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT)

    def test_expired_authority_and_scope_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.remember(envelope("remember"), authority, candidate, eligibility,
                    accepted_authority_receipts=context["accepted_authority_receipts"], accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time=fixtures.operation_fixtures.trusted_time("2026-08-13T02:00:00Z"),
                    accepted_trusted_time_receipts={"receipt_digests": [fixtures.operation_fixtures.trusted_time("2026-08-13T02:00:00Z")["receipt_digest"]]},
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT)
            wrong_scope = envelope("remember")
            wrong_scope["scope"] = ["docs"]
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.remember(wrong_scope, authority, candidate, eligibility,
                    accepted_authority_receipts=context["accepted_authority_receipts"], accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time=context["trusted_time_value"], accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT)

    def test_recall_rejects_raw_fts_and_unavailable_fts_without_adoption(self):
        request = fixtures.query_request()
        raw = copy.deepcopy(request)
        raw["extensions"][adapter.QUERY_EXTENSION]["terms"] = ["alpha OR beta"]
        with mock.patch.object(adapter, "query", side_effect=AssertionError("backend touched")):
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.recall(envelope("recall"), raw, {}, trusted_conformance_receipts={}, trusted_source_digests={}, state_root=ROOT, repository_root=ROOT)
        with mock.patch.object(adapter, "query", side_effect=adapter.MemorySQLiteError("fts5-unavailable")):
            with self.assertRaisesRegex(pilot.MemoryPilotError, "request rejected"):
                pilot.recall(envelope("recall"), request, {}, trusted_conformance_receipts={}, trusted_source_digests={}, state_root=ROOT, repository_root=ROOT)

    def test_recall_adopts_only_matching_profile_with_trusted_v2b_context(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            pilot.remember(
                envelope("remember"), authority, candidate, eligibility,
                accepted_authority_receipts=context["accepted_authority_receipts"],
                accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                trusted_time=context["trusted_time_value"],
                accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
            )
            request = fixtures.query_request()
            retrieval = record_fixtures.retrieval_input(request=request, records=[])
            retrieval["current"]["source_revision_relations"] = {
                candidate["record"]["record_id"]: "exact",
            }
            retrieval["handshake"]["adapter"].update({
                "adapter_id": adapter.ADAPTER_ID,
                "adapter_version": adapter.ADAPTER_VERSION,
            })
            fingerprint = memory.canonical_digest({
                "adapter": retrieval["handshake"]["adapter"],
                "capabilities": retrieval["handshake"]["capabilities"],
            })
            source_ref = next(
                ref for ref in candidate["record"]["provenance"]["source_refs"]
                if ref["kind"] == "repository-artifact"
            )
            result = pilot.recall(
                envelope("recall"), request,
                {key: retrieval[key] for key in ("handshake", "current", "extensions")},
                trusted_conformance_receipts={adapter.ADAPTER_ID: {
                    "receipt_digest": "c" * 64,
                    "adapter_fingerprint": fingerprint,
                }},
                trusted_source_digests={source_ref["locator"]: source_ref["digest"]},
                state_root=state, repository_root=ROOT,
            )
            self.assertEqual([candidate["record"]["canonical_digest"]], result["adopted_record_digests"])
            self.assertEqual(candidate["record"]["content"], result["adopted_context"][0]["content"])
            self.assertEqual("verified-fact", result["adopted_context"][0]["pilot_class"])

    def test_recall_preserves_cross_class_lifecycle_controller_before_class_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            first = profiled_bundle(state, suffix="first", record_id="record-first")
            second = profiled_bundle(
                state, pilot_class="decision", suffix="second", record_id="record-second",
                supersedes=["record-first"],
            )
            for bundle, pilot_class in ((first, "verified-fact"), (second, "decision")):
                authority, candidate, eligibility, context = bundle
                pilot.remember(
                    envelope("remember", pilot_class), authority, candidate, eligibility,
                    accepted_authority_receipts=context["accepted_authority_receipts"],
                    accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time=context["trusted_time_value"],
                    accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
                )
            request = fixtures.query_request()
            retrieval = record_fixtures.retrieval_input(request=request, records=[])
            retrieval["current"]["source_revision_relations"] = {
                "record-first": "exact", "record-second": "exact",
            }
            retrieval["handshake"]["adapter"].update({
                "adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
            })
            fingerprint = memory.canonical_digest({
                "adapter": retrieval["handshake"]["adapter"],
                "capabilities": retrieval["handshake"]["capabilities"],
            })
            trusted_sources = {
                ref["locator"]: ref["digest"]
                for bundle in (first, second)
                for ref in bundle[1]["record"]["provenance"]["source_refs"]
                if ref["kind"] == "repository-artifact"
            }
            result = pilot.recall(
                envelope("recall", "verified-fact"), request,
                {key: retrieval[key] for key in ("handshake", "current", "extensions")},
                trusted_conformance_receipts={adapter.ADAPTER_ID: {
                    "receipt_digest": "c" * 64, "adapter_fingerprint": fingerprint,
                }},
                trusted_source_digests=trusted_sources,
                state_root=state, repository_root=ROOT,
            )
            self.assertEqual([], result["adopted_record_digests"])
            self.assertEqual([], result["adopted_context"])
            dispositions = {item["record_id"]: item for item in result["retrieval_receipt"]["dispositions"]}
            self.assertIn("invalidated-or-superseded-by-related-record", dispositions["record-first"]["reasons"])

    def test_recall_revalidates_pilot_boundary_for_direct_m1_records(self):
        with tempfile.TemporaryDirectory() as directory:
            state = fixtures.secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, _, _ = profiled_bundle(
                state, suffix="direct-m1", record_id="record-direct-m1",
            )
            candidate["record"]["content"] = "user: repository evidence identifies version"
            authority, candidate, eligibility, context = reseal_bundle(authority, candidate)
            receipt = adapter.execute_authorized_operation(
                authority, candidate, eligibility,
                accepted_authority_receipts=context["accepted_authority_receipts"],
                accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                trusted_time_value=context["trusted_time_value"],
                accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
            )
            self.assertEqual("applied", receipt["payload"]["outcome"])
            request = fixtures.query_request()
            retrieval = record_fixtures.retrieval_input(request=request, records=[])
            retrieval["current"]["source_revision_relations"] = {"record-direct-m1": "exact"}
            retrieval["handshake"]["adapter"].update({
                "adapter_id": adapter.ADAPTER_ID, "adapter_version": adapter.ADAPTER_VERSION,
            })
            fingerprint = memory.canonical_digest({
                "adapter": retrieval["handshake"]["adapter"],
                "capabilities": retrieval["handshake"]["capabilities"],
            })
            source_ref = next(
                ref for ref in candidate["record"]["provenance"]["source_refs"]
                if ref["kind"] == "repository-artifact"
            )
            with self.assertRaises(pilot.MemoryPilotError):
                pilot.recall(
                    envelope("recall"), request,
                    {key: retrieval[key] for key in ("handshake", "current", "extensions")},
                    trusted_conformance_receipts={adapter.ADAPTER_ID: {
                        "receipt_digest": "c" * 64, "adapter_fingerprint": fingerprint,
                    }},
                    trusted_source_digests={source_ref["locator"]: source_ref["digest"]},
                    state_root=state, repository_root=ROOT,
                )

    def test_digest_bound_eval_derives_metrics_and_rejects_laundering(self):
        subject = load_eval_module()
        suite = json.loads((ROOT / "evals" / "memory-pilot" / "suite.json").read_text(encoding="utf-8"))
        result = subject.evaluate(suite)
        self.assertEqual("synthetic-pilot-qualified-awaiting-human-decision", result["status"])
        self.assertEqual(0.0, result["outcomes"]["false_authority_rate"])
        self.assertFalse(result["promotion_authorized"])
        self.assertEqual(suite["suite_digest"], result["suite_digest"])
        self.assertRegex(result["observation_digest"], r"^[0-9a-f]{64}$")
        baseline = subject._synthetic_task([])
        self.assertEqual(baseline, subject._synthetic_task([{"content": "Candidate version 0.23.0."}]))
        self.assertNotEqual(baseline, subject._synthetic_task([{"content": "Candidate version 9.9.9."}]))
        tampered = copy.deepcopy(suite)
        tampered["cases"][0]["expected"]["adopted"] = False
        with self.assertRaises(ValueError):
            subject.evaluate(tampered)
        weak_stale = copy.deepcopy(suite)
        weak_stale["cases"][1]["expected"]["retrieved"] = False
        weak_stale["suite_digest"] = subject.oe.canonical_digest(subject._body(weak_stale))
        with self.assertRaises(ValueError):
            subject.evaluate(weak_stale)
        impossible_context = copy.deepcopy(suite)
        impossible_context["metrics"]["bounded_context_reduction"]["minimum_net_tokens"] = 10_000
        impossible_context["suite_digest"] = subject.oe.canonical_digest(subject._body(impossible_context))
        self.assertEqual("not-qualified", subject.evaluate(impossible_context)["status"])
        with mock.patch.object(subject, "evaluate", return_value={"status": "not-qualified"}):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(1, subject.main())

    def test_cli_off_validation_and_remember_routes_with_generic_rejection(self):
        cli = ROOT / "skills" / "loop-engineering" / "scripts" / "memorypilotctl.py"
        process = subprocess.run([sys.executable, str(cli), "off"], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertIn("memory-off", process.stdout)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "unsafe.json"
            path.write_text('{"secret":"abc"}', encoding="utf-8")
            process = subprocess.run([sys.executable, str(cli), "validate-envelope", "remember", str(path)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(1, process.returncode)
        self.assertEqual('{"status":"rejected"}\n', process.stderr)
        with tempfile.TemporaryDirectory() as directory:
            malformed = pathlib.Path(directory) / "mixed.json"
            malformed.write_text(json.dumps({**envelope("remember"), "scope": [1, "x"]}), encoding="utf-8")
            process = subprocess.run([sys.executable, str(cli), "validate-envelope", "remember", str(malformed)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(1, process.returncode)
        self.assertEqual('{"status":"rejected"}\n', process.stderr)
        self.assertNotIn("Traceback", process.stderr)
        with tempfile.TemporaryDirectory() as directory:
            duplicate = pathlib.Path(directory) / "duplicate.json"
            duplicate.write_text('{"profile":"memory-m1-local-pilot/v1","profile":"memory-m1-local-pilot/v1"}', encoding="utf-8")
            process = subprocess.run([sys.executable, str(cli), "validate-envelope", "remember", str(duplicate)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(1, process.returncode)
        self.assertEqual('{"status":"rejected"}\n', process.stderr)
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            state = fixtures.secure_state_root(root)
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            bundle = {
                "envelope": envelope("remember"), "authority": authority,
                "candidate": candidate, "eligibility": eligibility,
                "accepted_authority_receipts": context["accepted_authority_receipts"],
                "accepted_eligibility_receipts": context["accepted_eligibility_receipts"],
                "trusted_time": context["trusted_time_value"],
                "accepted_trusted_time_receipts": context["accepted_trusted_time_receipts"],
                "expected_pre_state_digest": None,
            }
            path = root / "remember.json"
            path.write_text(json.dumps(bundle), encoding="utf-8")
            process = subprocess.run([sys.executable, str(cli), "remember", str(path), "--state-root", str(state), "--repository-root", str(ROOT)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertIn('"outcome": "applied"', process.stdout)

    def test_cli_invalidate_and_recall_routes_are_explicit(self):
        cli = ROOT / "skills" / "loop-engineering" / "scripts" / "memorypilotctl.py"
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            state = fixtures.secure_state_root(root)
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = profiled_bundle(state)
            remember_bundle = {
                "envelope": envelope("remember"), "authority": authority, "candidate": candidate, "eligibility": eligibility,
                "accepted_authority_receipts": context["accepted_authority_receipts"], "accepted_eligibility_receipts": context["accepted_eligibility_receipts"],
                "trusted_time": context["trusted_time_value"], "accepted_trusted_time_receipts": context["accepted_trusted_time_receipts"], "expected_pre_state_digest": None,
            }
            remember_path = root / "remember.json"
            remember_path.write_text(json.dumps(remember_bundle), encoding="utf-8")
            remembered = subprocess.run([sys.executable, str(cli), "remember", str(remember_path), "--state-root", str(state), "--repository-root", str(ROOT)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, remembered.returncode, remembered.stderr)
            ia, ic, ie, ix = fixtures.qualified_bundle(state, "invalidate", suffix="cli-invalidate")
            ia["payload"]["target_before_digest"] = candidate["record"]["canonical_digest"]
            ia = operation.seal_document(ia)
            ix = fixtures.operation_fixtures.validation_context(ia, ic, ie)
            invalidate_bundle = {"envelope": envelope("invalidate"), "authority": ia, "candidate": ic, "eligibility": ie,
                "accepted_authority_receipts": ix["accepted_authority_receipts"], "accepted_eligibility_receipts": ix["accepted_eligibility_receipts"],
                "trusted_time": ix["trusted_time_value"], "accepted_trusted_time_receipts": ix["accepted_trusted_time_receipts"], "expected_pre_state_digest": candidate["record"]["canonical_digest"]}
            invalidate_path = root / "invalidate.json"
            invalidate_path.write_text(json.dumps(invalidate_bundle), encoding="utf-8")
            invalidated = subprocess.run([sys.executable, str(cli), "invalidate", str(invalidate_path), "--state-root", str(state), "--repository-root", str(ROOT)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, invalidated.returncode, invalidated.stderr)
            retrieval = record_fixtures.retrieval_input()
            recall_bundle = {"envelope": envelope("recall"), "query_request": fixtures.query_request(),
                "retrieval_context": {key: retrieval[key] for key in ("handshake", "current", "extensions")},
                "trusted_conformance_receipts": {}, "trusted_source_digests": {}}
            recall_path = root / "recall.json"
            recall_path.write_text(json.dumps(recall_bundle), encoding="utf-8")
            recalled = subprocess.run([sys.executable, str(cli), "recall", str(recall_path), "--state-root", str(state), "--repository-root", str(ROOT)], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, recalled.returncode, recalled.stderr)
            self.assertIn('"adopted_record_digests": []', recalled.stdout)


if __name__ == "__main__":
    unittest.main()
