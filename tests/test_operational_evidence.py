from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "skills" / "loop-engineering" / "scripts" / "operational_evidence.py"
)
SPEC = importlib.util.spec_from_file_location("operational_evidence", MODULE_PATH)
evidence = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(evidence)

COMMIT = "1" * 40
NOW = "2026-07-29T02:00:00Z"
AUTHORITY = {
    "used_as_authorization": False,
    "used_as_completion_evidence": False,
    "external_write_authorized": False,
    "promotion_authorized": False,
}


def document(kind: str, document_id: str, payload: dict) -> dict:
    return evidence.seal_document(
        {
            "contract_version": evidence.CONTRACT_VERSION,
            "kind": kind,
            "document_id": document_id,
            "run_id": "run-121",
            "objective_id": "issue-121",
            "source_revision": {
                "repository_id": "github.com.jeffery777.codex-dev-skills",
                "commit_sha": COMMIT,
            },
            "observed_at": NOW,
            "producer": {"kind": "agent", "id": "test-producer"},
            "payload": payload,
            "authority_invariants": copy.deepcopy(AUTHORITY),
        }
    )


def reference(value: dict) -> dict:
    return {
        "document_id": value["document_id"],
        "document_digest": value["document_digest"],
    }


def valid_documents() -> list[dict]:
    artifact_set = document(
        "artifact-reference-set",
        "artifacts-1",
        {
            "artifacts": [
                {
                    "artifact_id": "verification-1",
                    "artifact_kind": "verification",
                    "locator_kind": "repository-relative-path",
                    "locator": "docs/loops/issue-121/verification.md",
                    "content_sha256": "a" * 64,
                    "media_type": "text/markdown",
                }
            ]
        },
    )
    environment = document(
        "environment-fingerprint",
        "environment-1",
        {
            "runtime_surface": "codex-desktop",
            "os_family": "macos",
            "architecture": "arm64",
            "python": {"major": 3, "minor": 12},
            "execution_mode": "current-session",
            "sandbox_mode": "workspace-write",
            "redaction_applied": True,
            "prohibited_fields_present": False,
        },
    )
    failure = document(
        "failure-summary",
        "failure-1",
        {
            "iteration_sequence": 1,
            "phase": "verification",
            "category": "verification",
            "code": "verification-failed",
            "retry": "manual",
            "artifact_ids": ["verification-1"],
        },
    )
    iteration = document(
        "iteration-summary",
        "iteration-1",
        {
            "sequence": 1,
            "phase": "verification",
            "result": "work-recorded",
            "task_id": "P2-fixtures-eval",
            "started_at": "2026-07-29T01:00:00Z",
            "ended_at": NOW,
            "artifact_ids": ["verification-1"],
            "failure_summaries": [reference(failure)],
        },
    )
    run = document(
        "run-receipt",
        "run-receipt-1",
        {
            "started_at": "2026-07-29T01:00:00Z",
            "ended_at": NOW,
            "execution_mode": "current-session",
            "outcome": "work-recorded",
            "iteration_summaries": [reference(iteration)],
            "environment_fingerprint": reference(environment),
            "artifact_reference_set": reference(artifact_set),
            "failure_summaries": [reference(failure)],
            "verification_observation": "passed",
            "review_observation": "required",
            "human_gate_observation": "pending",
        },
    )
    return [run, iteration, failure, environment, artifact_set]


def reseal(value: dict) -> dict:
    return evidence.seal_document(value)


def refresh_run_reference(documents: list[dict], kind: str) -> None:
    run = documents[0]
    target = next(item for item in documents if item["kind"] == kind)
    plural = {
        "iteration-summary": "iteration_summaries",
        "failure-summary": "failure_summaries",
    }[kind]
    run["payload"][plural] = [reference(target)]
    documents[0] = reseal(run)


class OperationalEvidenceDocumentTests(unittest.TestCase):
    def test_public_contract_tables_are_immutable(self):
        with self.assertRaises(TypeError):
            evidence.AUTHORITY_INVARIANTS["external_write_authorized"] = True
        with self.assertRaises(AttributeError):
            evidence.DOCUMENT_KINDS.add("unreviewed-kind")
        with self.assertRaises(TypeError):
            evidence.FAILURE_CODES["verification"] = frozenset()

    def test_all_document_kinds_validate_and_preserve_authority(self):
        for value in valid_documents():
            with self.subTest(kind=value["kind"]):
                validated = evidence.validate_document(value)
                self.assertEqual(AUTHORITY, validated["authority_invariants"])

    def test_valid_set_is_deterministic_and_non_authoritative(self):
        first = evidence.validate_set(valid_documents())
        second = evidence.validate_set(reversed(valid_documents()))
        self.assertEqual("valid", first["status"])
        self.assertEqual(5, first["document_count"])
        self.assertEqual(first["set_digest"], second["set_digest"])
        self.assertEqual(AUTHORITY, first["authority_invariants"])

    def test_unknown_and_missing_fields_fail_closed(self):
        cases = []
        unknown = valid_documents()[3]
        unknown["payload"]["hostname"] = "opaque-host"
        cases.append(reseal(unknown))
        missing = valid_documents()[0]
        del missing["payload"]["review_observation"]
        cases.append(reseal(missing))
        for value in cases:
            with self.subTest(fields=sorted(value["payload"])):
                with self.assertRaisesRegex(
                    evidence.OperationalEvidenceError, "missing or unknown"
                ):
                    evidence.validate_document(value)

    def test_tampered_document_is_rejected_by_digest(self):
        value = valid_documents()[1]
        value["payload"]["result"] = "continue"
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_document(value)
        self.assertEqual("digest-mismatch", caught.exception.code)

    def test_modified_authority_invariant_is_rejected(self):
        for replacement in (True, 0, 1, None, "false"):
            value = valid_documents()[0]
            value["authority_invariants"]["external_write_authorized"] = replacement
            value = reseal(value)
            with self.subTest(replacement=replacement):
                with self.assertRaises(evidence.OperationalEvidenceError):
                    evidence.validate_document(value)

    def test_timestamp_grammar_is_exact_and_timezone_aware(self):
        valid = (
            "2026-07-29T02:00:00Z",
            "2026-07-29T02:00:00.123456+08:00",
        )
        for timestamp in valid:
            value = valid_documents()[0]
            value["observed_at"] = timestamp
            value = reseal(value)
            with self.subTest(valid=timestamp):
                evidence.validate_document(value)

        invalid = (
            "2026-07-29 02:00:00Z",
            "2026-07-29x02:00:00+00:00",
            "2026-07-29T02:00:00",
            "2026-07-29T02:00:00.1234567Z",
            "9999-12-31T23:59:59-23:59",
            "0001-01-01T00:00:00+23:59",
        )
        for timestamp in invalid:
            value = valid_documents()[0]
            value["observed_at"] = timestamp
            value = reseal(value)
            with self.subTest(invalid=timestamp):
                with self.assertRaises(evidence.OperationalEvidenceError):
                    evidence.validate_document(value)

    def test_failure_taxonomy_is_category_compatible(self):
        value = valid_documents()[2]
        value["payload"]["code"] = "review-blocked"
        value = reseal(value)
        with self.assertRaises(evidence.OperationalEvidenceError):
            evidence.validate_document(value)

    def test_environment_requires_explicit_redaction_and_no_prohibited_fields(self):
        for field, value in (
            ("redaction_applied", False),
            ("prohibited_fields_present", True),
        ):
            candidate = valid_documents()[3]
            candidate["payload"][field] = value
            candidate = reseal(candidate)
            with self.subTest(field=field):
                with self.assertRaises(evidence.OperationalEvidenceError) as caught:
                    evidence.validate_document(candidate)
                self.assertEqual("privacy-violation", caught.exception.code)

    def test_artifact_kind_locator_and_duplicate_identity_fail_closed(self):
        incompatible = valid_documents()[4]
        incompatible["payload"]["artifacts"][0]["locator_kind"] = "opaque-id"
        incompatible["payload"]["artifacts"][0]["locator"] = "opaque-artifact"
        incompatible = reseal(incompatible)
        duplicate = valid_documents()[4]
        clone = copy.deepcopy(duplicate["payload"]["artifacts"][0])
        clone["artifact_id"] = "verification-2"
        duplicate["payload"]["artifacts"].append(clone)
        duplicate = reseal(duplicate)
        for value in (incompatible, duplicate):
            with self.assertRaises(evidence.OperationalEvidenceError):
                evidence.validate_document(value)

    def test_private_data_and_raw_logs_are_rejected_without_echo(self):
        prohibited = (
            "/home/example/private.txt",
            "api_key=example-secret",
            "ghp_" + "A" * 36,
            "Traceback (most recent call last)\n  failure",
        )
        for secret in prohibited:
            value = valid_documents()[1]
            value["payload"]["task_id"] = secret
            with self.subTest(kind=secret.split(maxsplit=1)[0]):
                with self.assertRaises(evidence.OperationalEvidenceError) as caught:
                    evidence.validate_document(value)
                self.assertEqual("privacy-violation", caught.exception.code)
                self.assertNotIn(secret, caught.exception.message)
                self.assertNotIn(secret[-16:], caught.exception.message)

    def test_floats_and_oversized_arrays_are_rejected(self):
        floating = valid_documents()[1]
        floating["payload"]["sequence"] = 1.0
        oversized = valid_documents()[1]
        oversized["payload"]["artifact_ids"] = [
            f"artifact-{index}" for index in range(257)
        ]
        for value in (floating, oversized):
            with self.assertRaises(evidence.OperationalEvidenceError):
                evidence.validate_document(value)

    def test_programmatic_documents_obey_the_encoded_size_bound(self):
        value = valid_documents()[0]
        value["unknown"] = "x" * evidence.MAX_STRING_BYTES
        for index in range(256):
            value[f"unknown-{index:03d}"] = "y" * evidence.MAX_STRING_BYTES
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_document(value)
        self.assertEqual("document-size", caught.exception.code)

    def test_object_keys_obey_string_and_privacy_bounds(self):
        oversized = valid_documents()[0]
        oversized["x" * (evidence.MAX_STRING_BYTES + 1)] = None
        private = valid_documents()[0]
        private["/" + "home/example"] = None
        for value in (oversized, private):
            with self.assertRaises(evidence.OperationalEvidenceError):
                evidence.validate_document(value)

    def test_load_json_rejects_duplicate_keys_and_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"kind":"run-receipt","kind":"failure-summary"}')
            with self.assertRaises(evidence.OperationalEvidenceError) as caught:
                evidence.load_json(duplicate)
            self.assertEqual("duplicate-key", caught.exception.code)
            target = root / "target.json"
            target.write_text("{}")
            link = root / "link.json"
            link.symlink_to(target)
            with self.assertRaises(evidence.OperationalEvidenceError) as caught:
                evidence.load_json(link)
            self.assertEqual("file-boundary", caught.exception.code)

    def test_close_failure_is_a_structured_file_boundary_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "document.json"
            path.write_text("{}")
            real_close = evidence.os.close

            def close_and_fail(descriptor):
                real_close(descriptor)
                raise OSError("synthetic close failure")

            with mock.patch.object(
                evidence.os, "close", side_effect=close_and_fail
            ), self.assertRaises(evidence.OperationalEvidenceError) as caught:
                evidence.load_json(path)
            self.assertEqual("file-boundary", caught.exception.code)

    @unittest.skipUnless(hasattr(evidence.os, "O_NONBLOCK"), "requires O_NONBLOCK")
    def test_file_open_is_nonblocking_before_identity_recheck(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "document.json"
            path.write_text("{}")
            real_open = evidence.os.open
            observed_flags = []

            def open_and_observe(candidate, flags):
                observed_flags.append(flags)
                return real_open(candidate, flags)

            with mock.patch.object(
                evidence.os,
                "open",
                side_effect=open_and_observe,
            ):
                evidence.load_json(path)
            self.assertTrue(observed_flags[0] & evidence.os.O_NONBLOCK)


class OperationalEvidenceSetTests(unittest.TestCase):
    def test_set_validation_uses_snapshots_not_mutable_caller_objects(self):
        documents = valid_documents()

        def values():
            for index, value in enumerate(documents):
                if index == 1:
                    documents[0]["payload"]["environment_fingerprint"][
                        "document_digest"
                    ] = "b" * 64
                yield value

        result = evidence.validate_set(values())
        self.assertEqual("valid", result["status"])

    def test_document_set_count_is_bounded_before_unbounded_consumption(self):
        source = valid_documents()[0]

        def values():
            for _ in range(evidence.MAX_SET_DOCUMENTS + 1):
                yield source

        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values())
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_duplicate_document_ids_are_rejected(self):
        values = valid_documents()
        values.append(copy.deepcopy(values[-1]))
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_reference_digest_tampering_is_rejected(self):
        values = valid_documents()
        values[0]["payload"]["environment_fingerprint"]["document_digest"] = "b" * 64
        values[0] = reseal(values[0])
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_identity_conflict_is_rejected(self):
        values = valid_documents()
        values[-1]["objective_id"] = "issue-122"
        values[-1] = reseal(values[-1])
        values[0]["payload"]["artifact_reference_set"] = reference(values[-1])
        values[0] = reseal(values[0])
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_run_and_environment_execution_modes_must_match(self):
        values = valid_documents()
        values[3]["payload"]["execution_mode"] = "sequential-fallback"
        values[3] = reseal(values[3])
        values[0]["payload"]["environment_fingerprint"] = reference(values[3])
        values[0] = reseal(values[0])
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_failure_requires_exactly_one_matching_iteration_owner(self):
        values = valid_documents()
        values[1]["payload"]["failure_summaries"] = []
        values[1] = reseal(values[1])
        refresh_run_reference(values, "iteration-summary")
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_run_level_failure_cannot_have_iteration_owner(self):
        values = valid_documents()
        values[2]["payload"]["iteration_sequence"] = None
        values[2] = reseal(values[2])
        values[1]["payload"]["failure_summaries"] = [reference(values[2])]
        values[1] = reseal(values[1])
        refresh_run_reference(values, "failure-summary")
        refresh_run_reference(values, "iteration-summary")
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)

    def test_artifact_references_must_resolve(self):
        values = valid_documents()
        values[1]["payload"]["artifact_ids"] = ["missing-artifact"]
        values[1] = reseal(values[1])
        refresh_run_reference(values, "iteration-summary")
        with self.assertRaises(evidence.OperationalEvidenceError) as caught:
            evidence.validate_set(values)
        self.assertEqual("relationship-mismatch", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
