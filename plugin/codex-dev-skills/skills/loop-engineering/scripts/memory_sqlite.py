"""Default-disabled SQLite/FTS5 Memory M1 reference adapter.

The module is imported only by the explicit ``sqlitectl.py`` entrypoint or a
direct trusted library caller.  Released memory-off, V2b, V3, and M0 modules do
not import it.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import platform
import re
import sqlite3
import stat
import tempfile
import time
from collections.abc import Mapping, Sequence
from typing import Any

import memory_contract as memory
import memory_operation as operation
import memory_qualification as qualification
import operational_evidence as oe


CONTRACT_VERSION = "loop-memory-sqlite/v0"
ADAPTER_ID = "sqlite-fts5-reference"
ADAPTER_VERSION = "m1-v0"
SCHEMA_VERSION = 1
DATABASE_NAME = "memory.sqlite3"
QUERY_EXTENSION = "dev.jeffery.memory-sqlite/query"
TOKENIZER = "unicode61 remove_diacritics 2"
MAX_QUERY_TERMS = 16
MAX_TERM_BYTES = 64
MAX_DATABASE_BYTES = 64 * 1024 * 1024
BUSY_TIMEOUT_MS = 1_000
OPERATION_TIMEOUT_MS = 5_000
TERM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

SCHEMA_STATEMENTS = (
    "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) STRICT",
    "CREATE TABLE records ("
    "row_id INTEGER PRIMARY KEY, scope_digest TEXT NOT NULL, scope_json TEXT NOT NULL, "
    "record_id TEXT NOT NULL, record_digest TEXT NOT NULL, record_kind TEXT NOT NULL, "
    "lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN "
    "('active','superseded','invalidated','tombstoned','deleted')), "
    "sequence INTEGER NOT NULL CHECK (sequence >= 0), content TEXT NOT NULL, "
    "record_json TEXT NOT NULL, UNIQUE (scope_digest, record_id)) STRICT",
    "CREATE VIRTUAL TABLE records_fts USING fts5(content, tokenize='unicode61 remove_diacritics 2')",
    "CREATE TABLE operations ("
    "scope_digest TEXT NOT NULL, idempotency_key TEXT NOT NULL, request_digest TEXT NOT NULL, "
    "operation TEXT NOT NULL, target_record_id TEXT NOT NULL, receipt_digest TEXT NOT NULL, "
    "receipt_json TEXT NOT NULL, PRIMARY KEY (scope_digest, idempotency_key)) STRICT",
    "CREATE INDEX records_scope_lookup ON records "
    "(scope_digest, scope_json, lifecycle_state, record_kind, record_id, record_digest)",
)


class MemorySQLiteError(ValueError):
    def __init__(self, code: str, message: str = "memory sqlite operation was rejected") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


CLI_REJECTION_ERRORS = (
    OSError,
    sqlite3.DatabaseError,
    MemorySQLiteError,
    memory.MemoryContractError,
    operation.MemoryOperationError,
    qualification.MemoryQualificationError,
    oe.OperationalEvidenceError,
)


def _error(code: str, message: str = "memory sqlite operation was rejected") -> MemorySQLiteError:
    return MemorySQLiteError(code, message)


def _translate(error: Exception, code: str = "invalid-structure") -> MemorySQLiteError:
    return _error(getattr(error, "code", code))


def authority_invariants() -> dict[str, bool]:
    return {
        "used_as_authorization": False,
        "used_as_completion_evidence": False,
        "external_write_authorized": False,
        "verification_performed": False,
        "review_performed": False,
        "acceptance_performed": False,
        "promotion_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        "deploy_authorized": False,
        "activation_authorized": False,
        "efficacy_claimed": False,
    }


def schema_fingerprint() -> str:
    return oe.canonical_digest({
        "schema_version": SCHEMA_VERSION,
        "statements": list(SCHEMA_STATEMENTS),
        "user_version": SCHEMA_VERSION,
    })


def _configure(connection: sqlite3.Connection, *, query_only: bool = False) -> None:
    if hasattr(connection, "enable_load_extension"):
        connection.enable_load_extension(False)
    connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA trusted_schema=OFF")
    if query_only:
        connection.execute("PRAGMA query_only=ON")


def _schema_rows(connection: sqlite3.Connection) -> list[dict[str, str | None]]:
    rows = connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()
    return [
        {"type": row[0], "name": row[1], "table": row[2], "sql": row[3]}
        for row in rows
    ]


def _create_schema(connection: sqlite3.Connection) -> None:
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def _database_bytes(connection: sqlite3.Connection) -> int:
    page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    return page_count * page_size


def _probe_behavior(connection: sqlite3.Connection) -> dict[str, Any]:
    connection.execute(
        "CREATE VIRTUAL TABLE probe_fts USING fts5(content, tokenize='unicode61 remove_diacritics 2')"
    )
    connection.executemany(
        "INSERT INTO probe_fts(rowid, content) VALUES (?, ?)",
        [(1, "alpha café"), (2, "alpha beta"), (3, "beta gamma")],
    )
    token_rows = [
        row[0]
        for row in connection.execute(
            "SELECT rowid FROM probe_fts WHERE probe_fts MATCH ? ORDER BY rowid",
            ('"cafe"',),
        )
    ]
    and_rows = [
        row[0]
        for row in connection.execute(
            "SELECT rowid FROM probe_fts WHERE probe_fts MATCH ? ORDER BY rowid",
            ('"alpha" AND "beta"',),
        )
    ]
    if token_rows != [1] or and_rows != [2]:
        raise _error("fts5-unavailable")
    extension_disabled = False
    try:
        connection.execute("SELECT load_extension(?)", ("m1-synthetic-extension",)).fetchone()
    except sqlite3.DatabaseError as error:
        message = str(error).lower()
        extension_disabled = "not authorized" in message or "no such function" in message
    if not extension_disabled:
        raise _error("extension-loading-unsafe")
    connection.execute("DROP TABLE probe_fts")
    return {
        "tokenizer": TOKENIZER,
        "token_behavior": token_rows,
        "and_behavior": and_rows,
        "extension_loading_disabled": True,
    }


def probe() -> dict[str, Any]:
    """Behavior-probe FTS5 in a fresh temporary database."""
    try:
        with tempfile.TemporaryDirectory(prefix="codex-memory-m1-probe-") as root:
            database = pathlib.Path(root) / "probe.sqlite3"
            connection = sqlite3.connect(database, timeout=BUSY_TIMEOUT_MS / 1_000)
            try:
                _configure(connection)
                behavior = _probe_behavior(connection)
                source_id = str(connection.execute("SELECT sqlite_source_id()").fetchone()[0])
                compile_options = sorted(
                    str(row[0]) for row in connection.execute("PRAGMA compile_options").fetchall()
                )
                _create_schema(connection)
                runtime_schema_digest = oe.canonical_digest(_schema_rows(connection))
            finally:
                connection.close()
    except (OSError, sqlite3.DatabaseError, MemorySQLiteError) as error:
        if isinstance(error, MemorySQLiteError):
            raise
        raise _error("fts5-unavailable") from error

    platform_envelope = {
        "architecture": platform.machine() or "unknown",
        "os": platform.system() or "unknown",
        "python_sqlite_api": {
            "module": "sqlite3",
            "paramstyle": sqlite3.paramstyle,
            "threadsafety": sqlite3.threadsafety,
        },
        "sqlite_version": sqlite3.sqlite_version,
    }
    platform_fingerprint = oe.canonical_digest(platform_envelope)
    capability_envelope = {
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "behavior": behavior,
        "compile_options": compile_options,
        "limits": {
            "busy_timeout_ms": BUSY_TIMEOUT_MS,
            "database_bytes": MAX_DATABASE_BYTES,
            "operation_timeout_ms": OPERATION_TIMEOUT_MS,
            "query_terms": MAX_QUERY_TERMS,
        },
        "platform_fingerprint": platform_fingerprint,
        "schema_fingerprint": schema_fingerprint(),
        "sqlite_source_id": source_id,
    }
    capability_fingerprint = oe.canonical_digest(capability_envelope)
    return {
        "contract_version": CONTRACT_VERSION,
        "kind": "capability-probe",
        "status": "qualified",
        "adapter": {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "schema_fingerprint": schema_fingerprint(),
            "capability_fingerprint": capability_fingerprint,
            "platform_fingerprint": platform_fingerprint,
        },
        "platform": platform_envelope,
        "sqlite": {
            "compile_options": compile_options,
            "source_id": source_id,
            "version": sqlite3.sqlite_version,
        },
        "behavior": behavior,
        "runtime_schema_digest": runtime_schema_digest,
        "authority_invariants": authority_invariants(),
        "probe_digest": oe.canonical_digest(capability_envelope),
    }


def _absolute_no_symlink(path: pathlib.Path, label: str) -> pathlib.Path:
    del label
    if not path.is_absolute():
        raise _error("placement-rejected")
    try:
        if stat.S_ISLNK(path.lstat().st_mode):
            raise _error("placement-rejected")
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise _error("placement-rejected") from error
    current = pathlib.Path(resolved.anchor)
    for part in resolved.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as error:
            raise _error("placement-rejected") from error
        if stat.S_ISLNK(info.st_mode):
            raise _error("placement-rejected")
    return resolved


def _disjoint(left: pathlib.Path, right: pathlib.Path) -> bool:
    return left != right and left not in right.parents and right not in left.parents


def validate_state_root(state_root: pathlib.Path, repository_root: pathlib.Path) -> dict[str, Any]:
    if not hasattr(os, "getuid"):
        raise _error("platform-unsupported")
    root = _absolute_no_symlink(state_root, "state root")
    repository = _absolute_no_symlink(repository_root, "repository root")
    if not root.is_dir() or not repository.is_dir() or not _disjoint(root, repository):
        raise _error("placement-rejected")
    info = root.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink < 2:
        raise _error("placement-rejected")
    identity = {
        "canonical_path": str(root),
        "device": str(info.st_dev),
        "inode": str(info.st_ino),
        "mode": format(stat.S_IMODE(info.st_mode), "04o"),
        "owner": str(info.st_uid),
    }
    return {"path": root, "identity_digest": oe.canonical_digest(identity)}


def _database_path(root: pathlib.Path) -> pathlib.Path:
    return root / DATABASE_NAME


def _validate_database_file(path: pathlib.Path) -> None:
    try:
        info = path.lstat()
    except OSError as error:
        raise _error("database-unavailable") from error
    if (
        stat.S_ISLNK(info.st_mode)
        or not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_mode & 0o077
        or (hasattr(os, "getuid") and info.st_uid != os.getuid())
        or info.st_size > MAX_DATABASE_BYTES
    ):
        raise _error("placement-rejected")


def _metadata(probe_result: Mapping[str, Any]) -> dict[str, str]:
    adapter = probe_result["adapter"]
    return {
        "adapter_id": ADAPTER_ID,
        "adapter_version": ADAPTER_VERSION,
        "capability_fingerprint": adapter["capability_fingerprint"],
        "platform_fingerprint": adapter["platform_fingerprint"],
        "runtime_schema_digest": probe_result["runtime_schema_digest"],
        "schema_fingerprint": adapter["schema_fingerprint"],
    }


def initialize(state_root: pathlib.Path, repository_root: pathlib.Path) -> dict[str, Any]:
    root_info = validate_state_root(state_root, repository_root)
    probe_result = probe()
    database = _database_path(root_info["path"])
    if database.exists() or database.is_symlink():
        raise _error("database-exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(database, flags, 0o600)
    os.close(descriptor)
    try:
        connection = sqlite3.connect(database, timeout=BUSY_TIMEOUT_MS / 1_000)
        try:
            _configure(connection)
            connection.execute("BEGIN IMMEDIATE")
            _create_schema(connection)
            for key, value in sorted(_metadata(probe_result).items()):
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES (?, ?)", (key, value)
                )
            connection.commit()
        finally:
            connection.close()
        os.chmod(database, 0o600)
        _validate_database_file(database)
        checked = integrity(state_root, repository_root, probe_result=probe_result)
    except Exception:
        # The caller owns cleanup of a failed initialization attempt.  Retaining
        # the file preserves evidence and avoids implicit deletion authority.
        raise
    return {
        "contract_version": CONTRACT_VERSION,
        "kind": "initialization-result",
        "status": "initialized",
        "adapter": copy.deepcopy(probe_result["adapter"]),
        "state_root_identity_digest": root_info["identity_digest"],
        "integrity_digest": checked["integrity_digest"],
        "authority_invariants": authority_invariants(),
    }


def _open_checked(
    state_root: pathlib.Path,
    repository_root: pathlib.Path,
    *,
    query_only: bool = False,
    probe_result: Mapping[str, Any] | None = None,
) -> tuple[sqlite3.Connection, dict[str, Any], dict[str, Any]]:
    root_info = validate_state_root(state_root, repository_root)
    live_probe = copy.deepcopy(dict(probe_result)) if probe_result is not None else probe()
    database = _database_path(root_info["path"])
    _validate_database_file(database)
    try:
        connection = sqlite3.connect(database, timeout=BUSY_TIMEOUT_MS / 1_000)
        _configure(connection, query_only=query_only)
        expected = _metadata(live_probe)
        actual = dict(connection.execute("SELECT key, value FROM metadata ORDER BY key").fetchall())
        user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        runtime_schema = oe.canonical_digest(_schema_rows(connection))
        quick_check = connection.execute("PRAGMA quick_check(1)").fetchone()
        if (
            actual != expected
            or user_version != SCHEMA_VERSION
            or runtime_schema != live_probe["runtime_schema_digest"]
            or quick_check != ("ok",)
        ):
            raise _error("schema-mismatch")
    except (sqlite3.DatabaseError, MemorySQLiteError) as error:
        try:
            connection.close()
        except Exception:
            pass
        if isinstance(error, MemorySQLiteError):
            raise
        message = str(error).lower()
        if "locked" in message or "busy" in message:
            raise _error("lock-timeout") from error
        raise _error("integrity-failure") from error
    return connection, root_info, live_probe


def integrity(
    state_root: pathlib.Path,
    repository_root: pathlib.Path,
    *,
    probe_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    connection, root_info, live_probe = _open_checked(
        state_root, repository_root, query_only=True, probe_result=probe_result
    )
    try:
        counts = {
            "operations": int(connection.execute("SELECT count(*) FROM operations").fetchone()[0]),
            "records": int(connection.execute("SELECT count(*) FROM records").fetchone()[0]),
        }
    finally:
        connection.close()
    body = {
        "adapter": copy.deepcopy(live_probe["adapter"]),
        "counts": counts,
        "state_root_identity_digest": root_info["identity_digest"],
        "status": "valid",
    }
    return {
        "contract_version": CONTRACT_VERSION,
        "kind": "integrity-result",
        **body,
        "integrity_digest": oe.canonical_digest(body),
        "authority_invariants": authority_invariants(),
    }


def _query_terms(request: Mapping[str, Any]) -> list[str]:
    extensions = request["extensions"]
    if set(extensions) != {QUERY_EXTENSION}:
        raise _error("query-rejected")
    query = extensions[QUERY_EXTENSION]
    if not isinstance(query, dict) or set(query) != {"match", "terms"} or query["match"] != "all":
        raise _error("query-rejected")
    terms = query["terms"]
    if not isinstance(terms, list) or not 1 <= len(terms) <= MAX_QUERY_TERMS:
        raise _error("query-rejected")
    if terms != sorted(set(terms)):
        raise _error("query-rejected")
    for term in terms:
        if (
            not isinstance(term, str)
            or len(term.encode("utf-8")) > MAX_TERM_BYTES
            or not TERM.fullmatch(term)
        ):
            raise _error("query-rejected")
    return list(terms)


def _scope_digest(repository: Mapping[str, Any], namespace: str) -> str:
    return oe.canonical_digest({"repository": repository, "namespace": namespace})


def _response(request: Mapping[str, Any], records: Sequence[Mapping[str, Any]], probe_result: Mapping[str, Any]) -> dict[str, Any]:
    request_digest = memory.canonical_digest(request)
    response = {
        "contract_version": memory.CONTRACT_VERSION,
        "kind": "query-response",
        "request_id": request["request_id"],
        "operation_id": request["operation_id"],
        "request_digest": request_digest,
        "adapter_id": ADAPTER_ID,
        "status": "ok",
        "records": [copy.deepcopy(dict(record)) for record in records],
        "partial": False,
        "errors": [],
        "response_nonce": f"sqlite-{request_digest[:32]}",
        "extensions": {
            "dev.jeffery.memory-sqlite/fingerprint": {
                "capability_fingerprint": probe_result["adapter"]["capability_fingerprint"],
                "platform_fingerprint": probe_result["adapter"]["platform_fingerprint"],
                "schema_fingerprint": probe_result["adapter"]["schema_fingerprint"],
            }
        },
    }
    response["response_digest"] = memory.canonical_digest(memory.response_body(response))
    return memory.validate_query_response(response, dict(request))


def query(
    request_value: Any,
    state_root: pathlib.Path,
    repository_root: pathlib.Path,
) -> dict[str, Any]:
    try:
        request = memory.validate_query_request(request_value)
        terms = _query_terms(request)
        if request["scope"] != sorted(set(request["scope"])):
            raise _error("query-rejected")
        if any(not memory._path_within(path, request["repository"]["path_scope"]) for path in request["scope"]):
            raise _error("identity-mismatch")
        connection, _, live_probe = _open_checked(
            state_root, repository_root, query_only=True
        )
        deadline = time.monotonic() + OPERATION_TIMEOUT_MS / 1_000
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1_000)
        try:
            match = " AND ".join(f'"{term}"' for term in terms)
            kinds = sorted(request["record_kinds"])
            placeholders = ",".join("?" for _ in kinds)
            sql = (
                "SELECT r.record_json FROM records_fts f "
                "JOIN records r ON r.row_id=f.rowid "
                "WHERE records_fts MATCH ? AND r.scope_digest=? AND r.scope_json=? "
                "AND r.lifecycle_state='active' AND r.record_kind IN (" + placeholders + ") "
                "ORDER BY bm25(records_fts), r.record_id, r.record_digest LIMIT ?"
            )
            parameters: list[Any] = [
                match,
                _scope_digest(request["repository"], request["namespace"]),
                oe.canonical_json(request["scope"]),
                *kinds,
                request["limit"],
            ]
            rows = connection.execute(sql, parameters).fetchall()
            records = [memory.validate_record(json.loads(str(row[0]))) for row in rows]
        except sqlite3.DatabaseError as error:
            code = "timeout" if "interrupted" in str(error).lower() else "integrity-failure"
            raise _error(code) from error
        finally:
            connection.close()
        return _response(request, records, live_probe)
    except (memory.MemoryContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def _adapter_matches(request: Mapping[str, Any], probe_result: Mapping[str, Any]) -> None:
    declared = request["payload"]["adapter"]
    live = probe_result["adapter"]
    if (
        declared["adapter_id"] != ADAPTER_ID
        or declared["adapter_version"] != ADAPTER_VERSION
        or declared["schema_fingerprint"] != live["schema_fingerprint"]
        or declared["capability_fingerprint"] != live["capability_fingerprint"]
    ):
        raise _error("capability-drift")


def _build_receipt(
    request: Mapping[str, Any],
    probe_result: Mapping[str, Any],
    *,
    outcome: str,
    failure_code: str | None,
    pre_state_digest: str | None,
    post_state_digest: str | None,
    original: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = request["payload"]
    transaction_id = f"tx-{request['document_digest'][:48]}"
    return operation.seal_document({
        "contract_version": operation.CONTRACT_VERSION,
        "kind": operation.RECEIPT_KIND,
        "document_id": f"sqlite:{outcome}:{request['document_digest']}",
        "repository": copy.deepcopy(request["repository"]),
        "namespace": request["namespace"],
        "payload": {
            "authorized_request_digest": request["document_digest"],
            "authority_document_digest": source["authority_document_digest"],
            "authority_receipt_digest": source["authority_receipt_digest"],
            "eligibility_receipt_digest": source["eligibility_receipt_digest"],
            "mutation_candidate_digest": source["mutation_candidate_digest"],
            "operation": source["operation"],
            "operation_id": source["operation_id"],
            "request_id": source["request_id"],
            "idempotency_key": source["idempotency_key"],
            "target_record_id": source["target_record_id"],
            "adapter": copy.deepcopy(source["adapter"]),
            "platform_fingerprint": probe_result["adapter"]["platform_fingerprint"],
            "transaction_id": transaction_id,
            "outcome": outcome,
            "failure_code": failure_code,
            "pre_state_digest": pre_state_digest,
            "post_state_digest": post_state_digest,
            "original_applied_receipt_digest": (
                original["document_digest"] if original is not None else None
            ),
            "atomic_state_and_receipt_committed": outcome != "failed",
            "no_partial_success": True,
            "no_uncertain_success": True,
            "no_second_application": True,
        },
        "authority_invariants": operation.authority_invariants(),
    })


def _failed_receipt(
    request: Mapping[str, Any],
    probe_result: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    failure_code: str,
    pre_state_digest: str | None,
) -> dict[str, Any]:
    receipt = _build_receipt(
        request,
        probe_result,
        outcome="failed",
        failure_code=failure_code,
        pre_state_digest=pre_state_digest,
        post_state_digest=None,
    )
    return operation.validate_execution_receipt(receipt, request, **context)


def _public_internal_record(record_value: Any) -> dict[str, Any]:
    record = memory.validate_record(record_value)
    sensitivity = record["sensitivity"]
    if (
        sensitivity["classification"] not in {"public", "internal"}
        or sensitivity["contains_credentials"]
        or sensitivity["contains_pii"]
        or record["content"] is None
        or memory._sensitive_content_indicators(record)
    ):
        raise _error("privacy-rejected")
    return record


def _post_state(record_id: str, record_digest: str, lifecycle_state: str, sequence: int) -> str:
    return oe.canonical_digest({
        "lifecycle_state": lifecycle_state,
        "record_digest": record_digest,
        "record_id": record_id,
        "sequence": sequence,
    })


def execute_authorized_operation(
    authority_value: Any,
    mutation_candidate_value: Any,
    eligibility_receipt_value: Any,
    *,
    accepted_authority_receipts: Any,
    accepted_eligibility_receipts: Any,
    trusted_time_value: Any,
    accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None,
    state_root: pathlib.Path,
    repository_root: pathlib.Path,
    _fault: str | None = None,
) -> dict[str, Any]:
    context = {
        "authority_value": authority_value,
        "mutation_candidate_value": mutation_candidate_value,
        "eligibility_receipt_value": eligibility_receipt_value,
        "accepted_authority_receipts": accepted_authority_receipts,
        "accepted_eligibility_receipts": accepted_eligibility_receipts,
        "trusted_time_value": trusted_time_value,
        "accepted_trusted_time_receipts": accepted_trusted_time_receipts,
        "expected_pre_state_digest": expected_pre_state_digest,
    }
    try:
        request = operation.build_authorized_request(
            authority_value,
            mutation_candidate_value,
            eligibility_receipt_value,
            accepted_authority_receipts=accepted_authority_receipts,
            accepted_eligibility_receipts=accepted_eligibility_receipts,
            trusted_time_value=trusted_time_value,
            accepted_trusted_time_receipts=accepted_trusted_time_receipts,
            expected_pre_state_digest=expected_pre_state_digest,
        )
    except (operation.MemoryOperationError, memory.MemoryContractError) as error:
        raise _translate(error, "authority-rejected") from error

    candidate = memory.validate_mutation_candidate(mutation_candidate_value)
    live_probe = probe()
    _adapter_matches(request, live_probe)
    root_info = validate_state_root(state_root, repository_root)
    if request["payload"]["state_root"]["identity_digest"] != root_info["identity_digest"]:
        raise _error("placement-rejected")

    connection: sqlite3.Connection | None = None
    pre_state = expected_pre_state_digest
    try:
        connection, _, live_probe = _open_checked(
            state_root, repository_root, probe_result=live_probe
        )
        deadline = time.monotonic() + OPERATION_TIMEOUT_MS / 1_000
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1_000)
        connection.execute("BEGIN IMMEDIATE")
        scope_digest = _scope_digest(request["repository"], request["namespace"])
        existing_operation = connection.execute(
            "SELECT request_digest, receipt_json FROM operations "
            "WHERE scope_digest=? AND idempotency_key=?",
            (scope_digest, request["payload"]["idempotency_key"]),
        ).fetchone()
        if existing_operation is not None:
            connection.rollback()
            if existing_operation[0] != request["document_digest"]:
                return _failed_receipt(
                    request, live_probe, context,
                    failure_code="conflicting-replay", pre_state_digest=pre_state,
                )
            original = json.loads(str(existing_operation[1]))
            operation.validate_execution_receipt(original, request, **context)
            replay = _build_receipt(
                request, live_probe, outcome="idempotent-replay", failure_code=None,
                pre_state_digest=pre_state,
                post_state_digest=original["payload"]["post_state_digest"], original=original,
            )
            return operation.validate_execution_receipt(
                replay, request, **context, original_applied_receipt=original
            )

        current = connection.execute(
            "SELECT row_id, record_digest, sequence, content FROM records "
            "WHERE scope_digest=? AND record_id=?",
            (scope_digest, request["payload"]["target_record_id"]),
        ).fetchone()
        current_digest = current[1] if current is not None else None
        if current_digest != expected_pre_state_digest:
            raise _error("transaction-failure")
        if _fault == "before-state":
            raise _error("interrupted")

        operation_kind = request["payload"]["operation"]
        if operation_kind == "upsert":
            record = _public_internal_record(candidate["record"])
            record_json = oe.canonical_json(record)
            scope_json = oe.canonical_json(record["scope"])
            if current is None:
                cursor = connection.execute(
                    "INSERT INTO records(scope_digest, scope_json, record_id, record_digest, "
                    "record_kind, lifecycle_state, sequence, content, record_json) "
                    "VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)",
                    (
                        scope_digest, scope_json, record["record_id"],
                        record["canonical_digest"], record["record_kind"],
                        record["idempotency"]["sequence"], record["content"], record_json,
                    ),
                )
                row_id = int(cursor.lastrowid)
            else:
                row_id = int(current[0])
                connection.execute("DELETE FROM records_fts WHERE rowid=?", (row_id,))
                connection.execute(
                    "UPDATE records SET scope_json=?, record_digest=?, record_kind=?, "
                    "lifecycle_state='active', sequence=?, content=?, record_json=? WHERE row_id=?",
                    (
                        scope_json, record["canonical_digest"], record["record_kind"],
                        record["idempotency"]["sequence"], record["content"], record_json, row_id,
                    ),
                )
            connection.execute(
                "INSERT INTO records_fts(rowid, content) VALUES (?, ?)",
                (row_id, record["content"]),
            )
            post_state = _post_state(
                record["record_id"], record["canonical_digest"], "active",
                record["idempotency"]["sequence"],
            )
        else:
            if current is None:
                raise _error("transaction-failure")
            state = {
                "invalidate": "invalidated",
                "tombstone": "tombstoned",
                "delete": "deleted",
            }[operation_kind]
            row_id, record_digest, sequence, _ = current
            connection.execute("DELETE FROM records_fts WHERE rowid=?", (row_id,))
            connection.execute(
                "UPDATE records SET lifecycle_state=? WHERE row_id=?", (state, row_id)
            )
            post_state = _post_state(
                request["payload"]["target_record_id"], str(record_digest), state, int(sequence)
            )

        if _fault == "before-receipt":
            raise _error("disk-full")
        applied = _build_receipt(
            request, live_probe, outcome="applied", failure_code=None,
            pre_state_digest=pre_state, post_state_digest=post_state,
        )
        operation.validate_execution_receipt(applied, request, **context)
        connection.execute(
            "INSERT INTO operations(scope_digest, idempotency_key, request_digest, operation, "
            "target_record_id, receipt_digest, receipt_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                scope_digest, request["payload"]["idempotency_key"], request["document_digest"],
                operation_kind, request["payload"]["target_record_id"],
                applied["document_digest"], oe.canonical_json(applied),
            ),
        )
        if _database_bytes(connection) > MAX_DATABASE_BYTES:
            raise _error("disk-full")
        if _fault == "before-commit":
            raise _error("commit-uncertain")
        connection.commit()
        return applied
    except MemorySQLiteError as error:
        if connection is not None:
            connection.rollback()
        failure = error.code if error.code in operation.FAILURE_CODES else "transaction-failure"
        return _failed_receipt(
            request, live_probe, context,
            failure_code=failure, pre_state_digest=pre_state,
        )
    except sqlite3.OperationalError as error:
        if connection is not None:
            connection.rollback()
        message = str(error).lower()
        failure = "lock-timeout" if "locked" in message or "busy" in message else (
            "interrupted" if "interrupted" in message else "transaction-failure"
        )
        return _failed_receipt(
            request, live_probe, context,
            failure_code=failure, pre_state_digest=pre_state,
        )
    except sqlite3.DatabaseError:
        if connection is not None:
            connection.rollback()
        return _failed_receipt(
            request, live_probe, context,
            failure_code="integrity-failure", pre_state_digest=pre_state,
        )
    finally:
        if connection is not None:
            connection.close()


def lookup_receipt(
    authority_value: Any,
    mutation_candidate_value: Any,
    eligibility_receipt_value: Any,
    *,
    accepted_authority_receipts: Any,
    accepted_eligibility_receipts: Any,
    trusted_time_value: Any,
    accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None,
    state_root: pathlib.Path,
    repository_root: pathlib.Path,
) -> dict[str, Any]:
    context = {
        "authority_value": authority_value,
        "mutation_candidate_value": mutation_candidate_value,
        "eligibility_receipt_value": eligibility_receipt_value,
        "accepted_authority_receipts": accepted_authority_receipts,
        "accepted_eligibility_receipts": accepted_eligibility_receipts,
        "trusted_time_value": trusted_time_value,
        "accepted_trusted_time_receipts": accepted_trusted_time_receipts,
        "expected_pre_state_digest": expected_pre_state_digest,
    }
    try:
        request = operation.build_authorized_request(
            authority_value,
            mutation_candidate_value,
            eligibility_receipt_value,
            accepted_authority_receipts=accepted_authority_receipts,
            accepted_eligibility_receipts=accepted_eligibility_receipts,
            trusted_time_value=trusted_time_value,
            accepted_trusted_time_receipts=accepted_trusted_time_receipts,
            expected_pre_state_digest=expected_pre_state_digest,
        )
    except (operation.MemoryOperationError, memory.MemoryContractError) as error:
        raise _translate(error, "authority-rejected") from error
    live_probe = probe()
    _adapter_matches(request, live_probe)
    root_info = validate_state_root(state_root, repository_root)
    if request["payload"]["state_root"]["identity_digest"] != root_info["identity_digest"]:
        raise _error("placement-rejected")
    connection, _, _ = _open_checked(
        state_root, repository_root, query_only=True, probe_result=live_probe
    )
    try:
        row = connection.execute(
            "SELECT receipt_json FROM operations WHERE scope_digest=? AND idempotency_key=?",
            (
                _scope_digest(request["repository"], request["namespace"]),
                request["payload"]["idempotency_key"],
            ),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise _error("receipt-unavailable")
    receipt = json.loads(str(row[0]))
    return operation.validate_execution_receipt(receipt, request, **context)


def build_qualification_receipt(
    qualification_input_value: Any,
    safety_observation_value: Any,
    execution_evidence_values: Sequence[Any],
) -> dict[str, Any]:
    source = qualification.validate_qualification_input(qualification_input_value)
    on = source["on_arm"]
    if on is None:
        raise _error("qualification-rejected")
    safety = qualification._safety(safety_observation_value)
    if safety != on["safety_observation"] or any(safety[field] != 0 for field in qualification.FAILURE_FIELDS):
        raise _error("qualification-rejected")
    probe_result = probe()
    if on["adapter"] != probe_result["adapter"]:
        raise _error("capability-drift")
    digests: list[str] = []
    for value in execution_evidence_values:
        evidence = oe._object(value)
        oe._exact(evidence, required={
            "authority", "mutation_candidate", "eligibility_receipt",
            "accepted_authority_receipts", "accepted_eligibility_receipts",
            "trusted_time", "accepted_trusted_time_receipts",
            "expected_pre_state_digest", "execution_receipt",
        })
        context = {
            "authority_value": evidence["authority"],
            "mutation_candidate_value": evidence["mutation_candidate"],
            "eligibility_receipt_value": evidence["eligibility_receipt"],
            "accepted_authority_receipts": evidence["accepted_authority_receipts"],
            "accepted_eligibility_receipts": evidence["accepted_eligibility_receipts"],
            "trusted_time_value": evidence["trusted_time"],
            "accepted_trusted_time_receipts": evidence["accepted_trusted_time_receipts"],
            "expected_pre_state_digest": evidence["expected_pre_state_digest"],
        }
        try:
            request = operation.build_authorized_request(
                evidence["authority"],
                evidence["mutation_candidate"],
                evidence["eligibility_receipt"],
                accepted_authority_receipts=evidence["accepted_authority_receipts"],
                accepted_eligibility_receipts=evidence["accepted_eligibility_receipts"],
                trusted_time_value=evidence["trusted_time"],
                accepted_trusted_time_receipts=evidence["accepted_trusted_time_receipts"],
                expected_pre_state_digest=evidence["expected_pre_state_digest"],
            )
            _adapter_matches(request, probe_result)
            receipt = operation.validate_execution_receipt(
                evidence["execution_receipt"], request, **context
            )
        except (operation.MemoryOperationError, memory.MemoryContractError) as error:
            raise _translate(error, "qualification-rejected") from error
        if (
            receipt["payload"]["outcome"] != "applied"
            or receipt["payload"]["platform_fingerprint"]
            != probe_result["adapter"]["platform_fingerprint"]
        ):
            raise _error("qualification-rejected")
        digests.append(receipt["document_digest"])
    if sorted(set(digests)) != safety["execution_receipt_digests"]:
        raise _error("qualification-rejected")
    receipt = qualification.seal_m1_receipt({
        "contract_version": qualification.CONTRACT_VERSION,
        "kind": qualification.M1_RECEIPT_KIND,
        "qualification_id": source["qualification_id"],
        "common_v3b_bindings": copy.deepcopy(source["common_v3b_bindings"]),
        "adapter": copy.deepcopy(on["adapter"]),
        "safety_observation_digest": oe.canonical_digest(safety),
        "execution_receipt_digests": copy.deepcopy(safety["execution_receipt_digests"]),
        "status": "passed",
    })
    return qualification.validate_m1_qualification_receipt(receipt)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return oe.load_json(path)
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error
