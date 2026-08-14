from __future__ import annotations

import copy
import os
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import memory_contract as memory  # noqa: E402
import memory_operation as operation  # noqa: E402
import memory_qualification as qualification  # noqa: E402
import memory_sqlite as adapter  # noqa: E402
from tests import test_memory_contract as memory_fixtures  # noqa: E402
from tests import test_memory_operation as operation_fixtures  # noqa: E402
from tests import test_memory_qualification as qualification_fixtures  # noqa: E402


def secure_state_root(parent: pathlib.Path) -> pathlib.Path:
    root = parent / "state"
    root.mkdir(mode=0o700)
    root.chmod(0o700)
    return root


def qualified_bundle(
    state_root: pathlib.Path,
    operation_kind: str = "upsert",
    *,
    suffix: str | None = None,
) -> tuple[dict, dict, dict, dict]:
    authority, candidate, eligibility, _ = operation_fixtures.bundle(operation_kind)
    suffix = suffix or operation_kind
    candidate["operation_id"] = f"mutation-{suffix}"
    candidate["request_id"] = f"mutation-request-{suffix}"
    candidate["idempotency_key"] = f"mutation-key-{suffix}"
    live = adapter.probe()
    authority["payload"].update({
        "operation_id": candidate["operation_id"],
        "request_id": candidate["request_id"],
        "idempotency_key": candidate["idempotency_key"],
        "mutation_candidate_digest": memory.canonical_digest(candidate),
        "adapter": {
            "adapter_id": adapter.ADAPTER_ID,
            "adapter_version": adapter.ADAPTER_VERSION,
            "schema_fingerprint": live["adapter"]["schema_fingerprint"],
            "capability_fingerprint": live["adapter"]["capability_fingerprint"],
            "required_capabilities": sorted(candidate["required_capabilities"]),
        },
        "state_root": {
            "state_root_class": "approved-machine-local",
            "identity_digest": adapter.validate_state_root(state_root, ROOT)["identity_digest"],
        },
    })
    authority = operation.seal_document(authority)
    context = operation_fixtures.validation_context(authority, candidate, eligibility)
    return authority, candidate, eligibility, context


def execute(
    state_root: pathlib.Path,
    operation_kind: str = "upsert",
    *,
    suffix: str | None = None,
    fault: str | None = None,
) -> tuple[dict, tuple[dict, dict, dict, dict]]:
    bundle = qualified_bundle(state_root, operation_kind, suffix=suffix)
    authority, candidate, eligibility, context = bundle
    receipt = adapter.execute_authorized_operation(
        authority, candidate, eligibility,
        accepted_authority_receipts=context["accepted_authority_receipts"],
        accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
        trusted_time_value=context["trusted_time_value"],
        accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
        expected_pre_state_digest=context["expected_pre_state_digest"],
        state_root=state_root, repository_root=ROOT, _fault=fault,
    )
    return receipt, bundle


def execution_evidence(receipt: dict, bundle: tuple[dict, dict, dict, dict]) -> dict:
    authority, candidate, eligibility, context = bundle
    return {
        "authority": authority,
        "mutation_candidate": candidate,
        "eligibility_receipt": eligibility,
        "accepted_authority_receipts": context["accepted_authority_receipts"],
        "accepted_eligibility_receipts": context["accepted_eligibility_receipts"],
        "trusted_time": context["trusted_time_value"],
        "accepted_trusted_time_receipts": context["accepted_trusted_time_receipts"],
        "expected_pre_state_digest": context["expected_pre_state_digest"],
        "execution_receipt": receipt,
    }


def query_request() -> dict:
    request = memory_fixtures.query_request()
    request["extensions"] = {
        adapter.QUERY_EXTENSION: {"match": "all", "terms": ["evidence", "repository"]}
    }
    return request


class SQLiteCapabilityAndPlacementTests(unittest.TestCase):
    def test_probe_is_behavior_based_deterministic_and_extension_safe(self):
        first = adapter.probe()
        second = adapter.probe()
        self.assertEqual(first, second)
        self.assertEqual("qualified", first["status"])
        self.assertTrue(first["behavior"]["extension_loading_disabled"])
        self.assertEqual([1], first["behavior"]["token_behavior"])
        self.assertTrue(first["sqlite"]["source_id"])
        self.assertTrue(first["runtime_schema_digest"])
        self.assertEqual(adapter.schema_fingerprint(), first["adapter"]["schema_fingerprint"])

    def test_initialize_and_integrity_require_secure_disjoint_root(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = pathlib.Path(directory)
            state = secure_state_root(parent)
            initialized = adapter.initialize(state, ROOT)
            self.assertEqual("initialized", initialized["status"])
            database = state / adapter.DATABASE_NAME
            self.assertTrue(database.is_file())
            self.assertEqual(0, database.stat().st_mode & 0o077)
            checked = adapter.integrity(state, ROOT)
            self.assertEqual({"operations": 0, "records": 0}, checked["counts"])
            with self.assertRaisesRegex(adapter.MemorySQLiteError, "rejected"):
                adapter.initialize(state, ROOT)

            unsafe = parent / "unsafe"
            unsafe.mkdir(mode=0o755)
            unsafe.chmod(0o755)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.validate_state_root(unsafe, ROOT)
            link = parent / "linked"
            link.symlink_to(state, target_is_directory=True)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.validate_state_root(link, ROOT)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.validate_state_root(ROOT, ROOT)

            os.truncate(database, adapter.MAX_DATABASE_BYTES + 1)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.integrity(state, ROOT)

    def test_schema_drift_fails_closed_without_repair(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            database = state / adapter.DATABASE_NAME
            connection = sqlite3.connect(database)
            connection.execute("PRAGMA user_version=2")
            connection.close()
            with self.assertRaisesRegex(adapter.MemorySQLiteError, "rejected"):
                adapter.integrity(state, ROOT)
            connection = sqlite3.connect(database)
            self.assertEqual(2, connection.execute("PRAGMA user_version").fetchone()[0])
            connection.close()


class SQLiteQueryAndOperationTests(unittest.TestCase):
    def test_applied_query_and_exact_replay_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            applied, bundle = execute(state)
            self.assertEqual("applied", applied["payload"]["outcome"])
            replayed, _ = execute(state)
            self.assertEqual("idempotent-replay", replayed["payload"]["outcome"])
            self.assertEqual(applied["document_digest"], replayed["payload"]["original_applied_receipt_digest"])
            response = adapter.query(query_request(), state, ROOT)
            self.assertEqual(["record-1"], [record["record_id"] for record in response["records"]])
            looked_up = adapter.lookup_receipt(
                bundle[0], bundle[1], bundle[2],
                accepted_authority_receipts=bundle[3]["accepted_authority_receipts"],
                accepted_eligibility_receipts=bundle[3]["accepted_eligibility_receipts"],
                trusted_time_value=bundle[3]["trusted_time_value"],
                accepted_trusted_time_receipts=bundle[3]["accepted_trusted_time_receipts"],
                expected_pre_state_digest=bundle[3]["expected_pre_state_digest"],
                state_root=state, repository_root=ROOT,
            )
            self.assertEqual(applied, looked_up)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.lookup_receipt(
                    bundle[0], bundle[1], bundle[2],
                    accepted_authority_receipts={"receipt_digests": ["0" * 64]},
                    accepted_eligibility_receipts=bundle[3]["accepted_eligibility_receipts"],
                    trusted_time_value=bundle[3]["trusted_time_value"],
                    accepted_trusted_time_receipts=bundle[3]["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=bundle[3]["expected_pre_state_digest"],
                    state_root=state, repository_root=ROOT,
                )
            checked = adapter.integrity(state, ROOT)
            self.assertEqual({"operations": 1, "records": 1}, checked["counts"])

    def test_lock_timeout_is_bounded_and_cannot_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            blocker = sqlite3.connect(state / adapter.DATABASE_NAME)
            try:
                blocker.execute("BEGIN EXCLUSIVE")
                started = adapter.time.monotonic()
                failed, _ = execute(state)
                elapsed = adapter.time.monotonic() - started
            finally:
                blocker.rollback()
                blocker.close()
            self.assertEqual("failed", failed["payload"]["outcome"])
            self.assertEqual("lock-timeout", failed["payload"]["failure_code"])
            self.assertFalse(failed["payload"]["atomic_state_and_receipt_committed"])
            self.assertLess(elapsed, adapter.OPERATION_TIMEOUT_MS / 1_000)
            self.assertEqual(
                {"operations": 0, "records": 0}, adapter.integrity(state, ROOT)["counts"]
            )

    def test_structured_query_rejects_sql_and_fts_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            execute(state)
            for term in ('alpha" OR 1=1 --', "alpha OR beta", "alpha*", "' UNION SELECT"):
                request = query_request()
                request["extensions"][adapter.QUERY_EXTENSION]["terms"] = [term]
                with self.assertRaises(adapter.MemorySQLiteError):
                    adapter.query(request, state, ROOT)
            request = query_request()
            request["extensions"][adapter.QUERY_EXTENSION]["raw_sql"] = "SELECT * FROM records"
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.query(request, state, ROOT)

    def test_repository_namespace_revision_and_path_are_isolated(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            execute(state)
            for mutate in (
                lambda request: request.update(namespace="other"),
                lambda request: request["repository"]["source_revision"].update(commit_sha="2" * 40),
                lambda request: request.update(scope=["docs"]),
            ):
                request = query_request()
                mutate(request)
                if request["repository"]["source_revision"]["commit_sha"] == "2" * 40:
                    body = copy.deepcopy(request["repository"])
                    body.pop("repository_identity_digest")
                    request["repository"]["repository_identity_digest"] = memory.canonical_digest(body)
                try:
                    response = adapter.query(request, state, ROOT)
                except (adapter.MemorySQLiteError, memory.MemoryContractError):
                    continue
                self.assertEqual([], response["records"])

    def test_conflicting_replay_lifecycle_and_logical_delete_preserve_history(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            applied, bundle = execute(state)
            authority, candidate, eligibility, context = bundle
            changed = copy.deepcopy(candidate)
            changed["request_id"] = "different-request"
            authority = copy.deepcopy(authority)
            authority["payload"]["request_id"] = changed["request_id"]
            authority["payload"]["mutation_candidate_digest"] = memory.canonical_digest(changed)
            authority = operation.seal_document(authority)
            conflict = adapter.execute_authorized_operation(
                authority, changed, eligibility,
                accepted_authority_receipts=context["accepted_authority_receipts"],
                accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                trusted_time_value=context["trusted_time_value"],
                accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
            )
            self.assertEqual("conflicting-replay", conflict["payload"]["failure_code"])

            deleted, _ = execute(state, "delete", suffix="delete")
            self.assertEqual("applied", deleted["payload"]["outcome"])
            self.assertEqual([], adapter.query(query_request(), state, ROOT)["records"])
            checked = adapter.integrity(state, ROOT)
            self.assertEqual({"operations": 2, "records": 1}, checked["counts"])
            self.assertNotIn("purge", repr((applied, deleted)).lower())

    def test_transaction_faults_roll_back_state_and_receipt(self):
        for fault, expected in (
            ("before-state", "interrupted"),
            ("before-receipt", "disk-full"),
            ("before-commit", "commit-uncertain"),
        ):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                state = secure_state_root(pathlib.Path(directory))
                adapter.initialize(state, ROOT)
                failed, _ = execute(state, fault=fault)
                self.assertEqual("failed", failed["payload"]["outcome"])
                self.assertEqual(expected, failed["payload"]["failure_code"])
                self.assertFalse(failed["payload"]["atomic_state_and_receipt_committed"])
                self.assertEqual(
                    {"operations": 0, "records": 0},
                    adapter.integrity(state, ROOT)["counts"],
                )

    def test_database_limit_rejects_and_rolls_back_before_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            with mock.patch.object(
                adapter, "_database_bytes", return_value=adapter.MAX_DATABASE_BYTES + 1
            ):
                failed, _ = execute(state)
            self.assertEqual("failed", failed["payload"]["outcome"])
            self.assertEqual("disk-full", failed["payload"]["failure_code"])
            self.assertFalse(failed["payload"]["atomic_state_and_receipt_committed"])
            self.assertEqual(
                {"operations": 0, "records": 0},
                adapter.integrity(state, ROOT)["counts"],
            )

    def test_untrusted_authority_and_sensitive_record_fail_before_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            authority, candidate, eligibility, context = qualified_bundle(state)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.execute_authorized_operation(
                    authority, candidate, eligibility,
                    accepted_authority_receipts={"receipt_digests": ["0" * 64]},
                    accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time_value=context["trusted_time_value"],
                    accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
                )
            sensitive = copy.deepcopy(candidate)
            sensitive["record"]["sensitivity"]["classification"] = "confidential"
            sensitive["record"]["canonical_digest"] = memory.canonical_digest(
                memory.record_body(sensitive["record"])
            )
            authority = copy.deepcopy(authority)
            authority["payload"]["candidate_record_digest"] = sensitive["record"]["canonical_digest"]
            authority["payload"]["mutation_candidate_digest"] = memory.canonical_digest(sensitive)
            authority = operation.seal_document(authority)
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.execute_authorized_operation(
                    authority, sensitive, eligibility,
                    accepted_authority_receipts=context["accepted_authority_receipts"],
                    accepted_eligibility_receipts=context["accepted_eligibility_receipts"],
                    trusted_time_value=context["trusted_time_value"],
                    accepted_trusted_time_receipts=context["accepted_trusted_time_receipts"],
                    expected_pre_state_digest=None, state_root=state, repository_root=ROOT,
                )
            self.assertEqual({"operations": 0, "records": 0}, adapter.integrity(state, ROOT)["counts"])

    def test_m1_qualification_receipt_binds_exact_live_tuple(self):
        with tempfile.TemporaryDirectory() as directory:
            state = secure_state_root(pathlib.Path(directory))
            adapter.initialize(state, ROOT)
            applied, applied_bundle = execute(state)
            result, verified = qualification_fixtures.v3b_pair()
            source = qualification_fixtures.qualification_input(result, verified, with_on=True)
            source = copy.deepcopy(source)
            source["on_arm"]["adapter"] = copy.deepcopy(adapter.probe()["adapter"])
            source["on_arm"]["safety_observation"]["execution_receipt_digests"] = [applied["document_digest"]]
            expected_receipt = qualification.seal_m1_receipt({
                "contract_version": qualification.CONTRACT_VERSION,
                "kind": qualification.M1_RECEIPT_KIND,
                "qualification_id": source["qualification_id"],
                "common_v3b_bindings": copy.deepcopy(source["common_v3b_bindings"]),
                "adapter": copy.deepcopy(source["on_arm"]["adapter"]),
                "safety_observation_digest": qualification.oe.canonical_digest(
                    source["on_arm"]["safety_observation"]
                ),
                "execution_receipt_digests": [applied["document_digest"]],
                "status": "passed",
            })
            source["on_arm"]["m1_qualification_receipt_digest"] = expected_receipt["receipt_digest"]
            source = qualification.seal_input(source)
            receipt = adapter.build_qualification_receipt(
                source, source["on_arm"]["safety_observation"],
                [execution_evidence(applied, applied_bundle)],
            )
            self.assertEqual(expected_receipt, receipt)
            changed = copy.deepcopy(source["on_arm"]["safety_observation"])
            changed["privacy_failures"] = 1
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.build_qualification_receipt(
                    source, changed, [execution_evidence(applied, applied_bundle)]
                )
            forged = execution_evidence(applied, applied_bundle)
            forged["execution_receipt"] = copy.deepcopy(applied)
            forged["execution_receipt"]["payload"]["post_state_digest"] = "0" * 64
            with self.assertRaises(adapter.MemorySQLiteError):
                adapter.build_qualification_receipt(
                    source, source["on_arm"]["safety_observation"], [forged]
                )


if __name__ == "__main__":
    unittest.main()
