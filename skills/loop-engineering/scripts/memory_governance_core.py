"""MG1 G1 單專案管理核心：預設關閉，只有可信 host 可提供能力。

本切片的 production registry 為空；注入 ports 的隔離測試不構成 runtime qualification。
"""
from __future__ import annotations

import contextlib
import copy
from dataclasses import dataclass
from functools import wraps
import os
import sqlite3
import unicodedata
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_host import AcceptedPreview, ClockSample, HostAuthorityPort, RootBinding, SourceObservation


def _boundary(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except c.ContractError:
            raise
        except (OSError, sqlite3.Error) as exc:
            raise c.ContractError("storage-unavailable") from exc
    return call


def _checkpoint(_stage: str) -> None:
    """固定測試故障點；無 CLI/資料驅動 hook，也不載入外部程式。"""


@dataclass(frozen=True, eq=False)
class ExecutionHandle:
    """只有同一 core/process RAM 中的實例可用；序列化／複製不產生權限。"""
    operation_id: str


@dataclass(frozen=True)
class _Accepted:
    preview_bytes: bytes
    confirmation_bytes: bytes
    binding: RootBinding
    process: int


class GovernanceCore:
    def __init__(self, host: HostAuthorityPort | None = None, *, enabled: bool = False):
        self._host = host
        self._enabled = enabled is True
        self._process = os.getpid()
        self._binding = None
        self._last_clock = None
        self._pending = None
        self._handle = None
        self._accepted = None

    def _port(self, method: str, *args):
        c.require(self._enabled and self._host is not None, "memory-disabled")
        c.require(os.getpid() == self._process, "process-changed")
        try:
            return getattr(self._host, method)(*args)
        except Exception as exc:
            raise c.ContractError("host-unavailable") from exc

    def _clock(self, floor: int = 0) -> int:
        sample = self._port("clock")
        c.require(type(sample) is ClockSample, "clock-untrusted")
        c.integer(sample.utc_seconds)
        c.integer(sample.monotonic_ns, 0, 2**63 - 1)
        c.uuid(sample.process_id)
        c.require(sample.utc_seconds >= floor, "clock-untrusted")
        previous = self._last_clock
        if previous is not None:
            c.require(sample.process_id == previous.process_id
                      and sample.utc_seconds >= previous.utc_seconds
                      and sample.monotonic_ns >= previous.monotonic_ns, "clock-untrusted")
        self._last_clock = sample
        return sample.utc_seconds

    def _root(self, capability: str, operation: str) -> tuple[RootBinding, dict, dict]:
        binding = self._port("binding")
        c.require(type(binding) is RootBinding and capability in binding.capabilities, "capability-unavailable")
        limits = c.profile(c.decode(binding.profile_bytes, 4096))
        scope = c.decode(binding.scope_bytes, 4096)
        c.scope(scope, c.digest(limits), c.digest(c.POLICY))
        c.require(scope["schema_fingerprint"] == db.SCHEMA_FINGERPRINT, "schema-mismatch")
        c.opaque(binding.filesystem_id)
        c.digest_text(binding.adapter_fingerprint)
        if self._binding is None:
            self._binding = binding
        c.require(binding == self._binding, "root-binding-drift")
        c.require(self._port("qualify", binding, db.runtime_facts(), operation) is True, "qualification-unavailable")
        return binding, scope, limits

    def _read_authority(self, binding: RootBinding, purpose: str, operation_id: str | None = None):
        c.require(self._port("authorize_read", binding, purpose, operation_id) is True, "read-unavailable")

    def _source(self, binding: RootBinding, scope: dict, value: dict) -> SourceObservation:
        start = self._clock()
        observation = self._port("observe_source", binding, c.canonical(value, 16384))
        end = self._clock()
        c.require(type(observation) is SourceObservation, "source-unavailable")
        c.integer(observation.observed_at)
        c.require(start <= observation.observed_at <= end
                  and value["validation"]["verified_at"] <= end, "source-time-mismatch")
        c.require(observation.scope_digest == c.digest(scope)
                  and observation.version_digest == c.digest(value)
                  and observation.provenance_digest == c.digest(value["provenance"])
                  and observation.policy_fingerprint == scope["policy_fingerprint"]
                  and observation.verifier_fingerprint == value["validation"]["verifier_fingerprint"]
                  and observation.evidence_id == value["validation"]["evidence_id"], "source-binding-mismatch")
        c.require(observation.eligibility == "eligible" and observation.safety == "safe", "source-not-adoptable")
        return observation

    def _copies(self, binding: RootBinding) -> dict:
        start = self._clock()
        copies = self._port("external_copies", binding)
        end = self._clock()
        c.canonical(copies)
        c.external_copies(copies)
        c.require(start <= copies["observed_at"] <= end, "stale-copy-observation")
        return copies

    def _storage(self, directory, binding, limits, operation, candidate):
        files, storage = db.measure(directory, binding, limits)
        committed = c.integer(self._port("committed_work_bytes", binding))
        storage["available_work_bytes"] = max(0, storage["available_work_bytes"] - committed)
        budget = self._port("work_budget", binding, db.runtime_facts(), copy.deepcopy(files), operation,
                            c.canonical(candidate, 16384) if candidate is not None else None)
        c.canonical(budget, 4096)
        c.work_budget(budget, files, limits)
        storage["work_budget"] = copy.deepcopy(budget)
        c.require(c.preflight_capacity_proven(storage, limits), "insufficient-space")
        return files, storage

    @_boundary
    def initialize(self) -> dict:
        binding, scope, limits = self._root("initialize", "initialize")
        c.require(self._port("accept_initialization", binding) is True, "initialization-unavailable")
        now = self._clock()
        main, lock = db.initialize(binding, limits, scope, now)
        self._port("bind_initialized", binding, main, lock)
        rebound = self._port("binding")
        c.require(type(rebound) is RootBinding and rebound.main_identity == main and rebound.lock_identity == lock
                  and all(getattr(rebound, key) == getattr(binding, key)
                          for key in ("root", "directory_identity", "scope_bytes", "profile_bytes", "filesystem_id",
                                      "adapter_fingerprint", "capabilities")), "initialization-readback-mismatch")
        self._binding = rebound
        with db.locked(rebound), contextlib.closing(db.connect(rebound, limits)) as connection:
            connection.execute("BEGIN")
            snapshot = db.snapshot(connection, scope, limits)
            c.require(snapshot.items == snapshot.proofs == 0, "initialization-readback-mismatch")
        return {"status": "initialized", "scope": scope, "state_digest": snapshot.digest,
                "runtime_proven": False}

    def _transition(self, connection, scope, limits, operation, item_id, candidate, restore_revision, now):
        before = db.load_item(connection, item_id, scope, limits)
        if operation == "add":
            c.require(before is None, "identity-conflict")
            after = {"item_id": item_id, "identity_epoch": 1, "status": "active", "current_revision": 1,
                     "revision_high_water": 1, "erased_at": None, "versions": []}
        else:
            c.require(before is not None, "item-unavailable")
            after = copy.deepcopy(before)
        if operation in {"add", "update", "restore"}:
            c.validate_version(candidate, scope, limits, candidate=True)
            c.require(candidate["validation"]["verified_at"] <= now, "future-validation")
            expected = 1 if before is None else before["revision_high_water"] + 1
            c.require(candidate["revision"] == expected, "revision-conflict")
            c.require(len(after["versions"]) < limits["max_versions"], "version-limit")
            if before is not None:
                c.require(candidate["created_at"] >= before["versions"][-1]["created_at"], "revision-time-conflict")
                if operation == "restore":
                    retained = next((v for v in before["versions"] if v["revision"] == restore_revision), None)
                    c.require(retained is not None, "restore-source-unavailable")
                    c.restore_content(candidate, retained)
                after["versions"][-1]["retired_at"] = candidate["created_at"]
            after["versions"].append(copy.deepcopy(candidate))
            after["current_revision"] = after["revision_high_water"] = expected
        elif operation == "stop":
            c.require(before["status"] == "active", "state-conflict")
            after["status"] = "stopped"
        else:
            c.require(before["status"] == "stopped", "state-conflict")
            after["status"] = "active"
        after["projection_digest"] = c.digest(c.projection(after["versions"][-1], after["status"]))
        return before, after

    @staticmethod
    def _admit(snapshot, operation, limits):
        if operation == "add":
            c.require(snapshot.items < limits["max_items"], "item-limit")
        maximum = limits["max_proofs"] + (limits["maintenance_proof_reserve"] if operation == "stop" else 0)
        c.require(snapshot.proofs < maximum, "proof-limit")

    @_boundary
    def preview(self, operation: str, item_id: str, candidate: dict | None = None,
                *, restore_revision: int | None = None) -> dict:
        binding, scope, limits = self._root("content-write", operation)
        c.g1_operation(operation)
        c.uuid(item_id)
        c.require("readback" in binding.capabilities, "capability-unavailable")
        if operation == "restore":
            c.integer(restore_revision, 1)
        else:
            c.require(restore_revision is None, "unexpected-restore-source")
        if operation not in {"add", "update", "restore"}:
            c.require(candidate is None, "unexpected-candidate")
        elif candidate is not None:
            candidate = c.decode(c.canonical(candidate, 16384), 16384)
        now = self._clock()
        if self._pending is not None:
            old = c.decode(self._pending)
            c.require(now >= old["expires_at"], "preview-pending")
        c.require(self._handle is None, "execution-pending")
        operation_id = str(uuid.uuid4())
        self._read_authority(binding, "preview", operation_id)
        with db.locked(binding) as directory, contextlib.closing(db.connect(binding, limits)) as connection:
            connection.execute("BEGIN")
            snapshot = db.snapshot(connection, scope, limits)
            now = self._clock(snapshot.clock_floor)
            self._admit(snapshot, operation, limits)
            before, after = self._transition(connection, scope, limits, operation, item_id, candidate, restore_revision, now)
            if operation != "stop":
                self._source(binding, scope, after["versions"][-1])
            files, storage = self._storage(directory, binding, limits, operation, candidate)
            copies = self._copies(binding)
            issued = self._clock(snapshot.clock_floor)
            expected = db.state_digest(connection, scope, limits,
                                       {"epoch": snapshot.epoch, "reject_before": snapshot.reject_before}, after)
            value = {"contract_version": "mg1-preview/v1", "scope": scope, "operation_id": operation_id,
                     "nonce": str(uuid.uuid4()), "operation": operation, "item_id": item_id,
                     "acceptance_epoch": snapshot.epoch, "issued_at": issued,
                     "expires_at": c.integer(issued + limits["confirmation_seconds"]),
                     "before": {"kind": "logical-state", "digest": snapshot.digest},
                     "expected_after_digest": expected, "candidate": candidate,
                     "target_revisions": [restore_revision] if operation == "restore" else [],
                     "target_proofs": [], "target_markers": [], "managed_files": files, "storage": storage,
                     "external_copies": copies, "phases": {"content": "requested" if candidate is not None else "not-requested",
                                                            "sanitization": "not-requested", "space_reclaim": "not-requested"},
                     "authority": ["content-write", "readback"], "continuation": None, "compact": None}
            c.g1_preview(value, scope, limits)
        self._pending = c.canonical(value)
        return c.decode(self._pending)

    @_boundary
    def authorize(self, preview_value: dict) -> ExecutionHandle:
        binding, scope, limits = self._root("content-write", "authorize")
        data = c.canonical(preview_value)
        c.require(self._pending is not None and data == self._pending and self._handle is None, "preview-unrecognized")
        value = c.g1_preview(c.decode(data), scope, limits)
        c.require(value["issued_at"] <= self._clock() < value["expires_at"], "expired")
        accepted = self._port("accept_preview", binding, data)
        c.require(type(accepted) is AcceptedPreview and accepted.preview_bytes == data, "acceptance-unavailable")
        confirmation = c.decode(accepted.confirmation_bytes, 4096)
        c.confirmation(confirmation, value, self._clock())
        handle = ExecutionHandle(value["operation_id"])
        self._handle = handle
        self._accepted = _Accepted(data, c.canonical(confirmation, 4096), binding, self._process)
        self._pending = None
        return handle

    def cancel(self) -> None:
        """只丟棄本 process RAM 中的未執行提案／handle，不接觸儲存。"""
        self._pending = self._handle = self._accepted = None

    @_boundary
    def execute(self, handle: ExecutionHandle) -> dict:
        c.require(handle is self._handle and self._accepted is not None, "handle-unrecognized-or-consumed")
        accepted = self._accepted
        self._handle = self._accepted = None
        c.require(accepted.process == os.getpid(), "process-changed")
        preview = c.decode(accepted.preview_bytes)
        confirmation = c.decode(accepted.confirmation_bytes, 4096)
        operation = preview["operation"]
        binding, scope, limits = self._root("content-write", operation)
        c.require(binding == accepted.binding and "readback" in binding.capabilities, "root-binding-drift")
        c.g1_preview(preview, scope, limits)
        c.confirmation(confirmation, preview, self._clock())
        with db.locked(binding, exclusive=True) as directory:
            self._read_authority(binding, "readback", preview["operation_id"])
            with contextlib.closing(db.connect(binding, limits)) as connection:
                connection.execute("BEGIN")
                snapshot = db.snapshot(connection, scope, limits)
                c.require(connection.execute("SELECT 1 FROM proofs WHERE operation_id=?", (preview["operation_id"],)).fetchone() is None,
                          "operation-replay")
                c.require(snapshot.digest == preview["before"]["digest"] and snapshot.epoch == preview["acceptance_epoch"]
                          and preview["issued_at"] >= snapshot.reject_before, "revision-conflict")
                now = self._clock(snapshot.clock_floor)
                c.confirmation(confirmation, preview, now)
                self._admit(snapshot, operation, limits)
                source_revision = preview["target_revisions"][0] if operation == "restore" else None
                before, after = self._transition(connection, scope, limits, operation, preview["item_id"],
                                                  preview["candidate"], source_revision, now)
                expected = db.state_digest(connection, scope, limits,
                                           {"epoch": snapshot.epoch, "reject_before": snapshot.reject_before}, after)
                c.require(expected == preview["expected_after_digest"], "after-digest-mismatch")
                if operation != "stop":
                    self._source(binding, scope, after["versions"][-1])
                files, storage = self._storage(directory, binding, limits, operation, preview["candidate"])
                c.require(files == preview["managed_files"] and storage["work_budget"] == preview["storage"]["work_budget"]
                          and storage["filesystem_id"] == preview["storage"]["filesystem_id"], "storage-drift")
                copies = self._copies(binding)
                c.require({k: v for k, v in copies.items() if k != "observed_at"}
                          == {k: v for k, v in preview["external_copies"].items() if k != "observed_at"}, "external-copies-drift")
            # 至此所有驗證皆在 read-only connection；未知授權不開 writer。
            c.require(self._port("qualify", binding, db.runtime_facts(), operation) is True, "qualification-unavailable")
            c.confirmation(confirmation, preview, self._clock(snapshot.clock_floor))
            _checkpoint("before-transaction")
            connection = None
            try:
                connection = db.connect(binding, limits, writer=True)
                connection.execute("BEGIN IMMEDIATE")
                c.require(db.snapshot(connection, scope, limits).digest == snapshot.digest, "revision-conflict")
                db.write_item(connection, after)
                _checkpoint("after-item-write")
                recorded = self._clock(snapshot.clock_floor)
                c.confirmation(confirmation, preview, recorded)
                record = {"contract_version": "mg1-operation-proof/v1", "operation_id": preview["operation_id"],
                          "item_id": preview["item_id"], "identity_epoch": after["identity_epoch"],
                          "acceptance_epoch": snapshot.epoch, "before_revision": before["current_revision"] if before else 0,
                          "after_revision": after["current_revision"], "recorded_at": recorded, "operation": operation,
                          "preview_digest": c.digest(preview), "before_digest": snapshot.digest, "after_digest": expected,
                          "projection_digest": after["projection_digest"], "acceptance_evidence_id": confirmation["host_evidence_id"],
                          "phase": "complete", "sanitization": "not-requested", "space_reclaim": "not-requested",
                          "restore_source_revision": source_revision, "target_revisions": [], "parent_operation_id": None,
                          "witness_kind": None, "witness_digest": None}
                c.g1_proof(record, preview, confirmation)
                connection.execute("INSERT INTO proofs(operation_id,item_id,document) VALUES (?,?,?)",
                                   (record["operation_id"], record["item_id"], c.canonical(record, 2048)))
                _checkpoint("before-commit")
                c.confirmation(confirmation, preview, self._clock(snapshot.clock_floor))
                connection.commit()
                _checkpoint("after-commit")
            except (OSError, sqlite3.Error, c.ContractError):
                # 例外不是未提交證明。關閉後只用新 connection 核對，絕不重送 mutation。
                pass
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except sqlite3.Error:
                        pass
            try:
                _checkpoint("before-readback")
                return self._readback_locked(directory, binding, scope, limits, preview["operation_id"], c.digest(preview), preview)
            except (c.ContractError, OSError, sqlite3.Error) as exc:
                # 包含 readback 授權撤銷或 clock 失去可信度；不得誤報成未執行。
                raise c.ContractError("state-unknown") from exc

    def _readback_locked(self, directory, binding, scope, limits, operation_id, preview_digest, preview=None):
        self._read_authority(binding, "readback", operation_id)
        record = None
        state = None
        result = "state-unknown"
        files = []
        storage = {"filesystem_id": binding.filesystem_id, "managed_bytes": 0, "available_work_bytes": 0,
                   "coverage": "unknown", "work_budget": None}
        copies = {"coverage": "unknown", "observed_at": self._clock(), "copies": []}
        try:
            entries = db.inventory(directory, binding)
            c.require(db.JOURNAL not in entries or entries[db.JOURNAL].st_size == 0, "recovery-required")
            with contextlib.closing(db.connect(binding, limits)) as connection:
                connection.execute("BEGIN")
                try:
                    actual = db.snapshot(connection, scope, limits)
                except c.ContractError as exc:
                    # 已 qualified 的固定 schema/G1-only binding；此純資料驗證邊界
                    # 的契約失敗（含未支援 epoch/G2 rows）不是 host 或 I/O 不確定性。
                    raise c.ContractError("integrity-failed") from exc
                state = actual.digest
                self._clock(actual.clock_floor)
                row = connection.execute("SELECT document FROM proofs WHERE operation_id=?", (operation_id,)).fetchone()
                if row is not None:
                    record = c.g1_proof(c.decode(row[0], 2048))
                    c.require(record["operation_id"] == operation_id, "proof-binding-mismatch")
                    # caller 的錯誤 tuple 不證明 durable proof 自身已損壞。
                    c.require(record["preview_digest"] == preview_digest, "readback-binding")
                    c.g1_proof(record, preview)
                    item = db.load_item(connection, record["item_id"], scope, limits)
                    if state == record["after_digest"]:
                        c.require(item is not None and item["current_revision"] == record["after_revision"]
                                  and item["identity_epoch"] == record["identity_epoch"]
                                  and item["projection_digest"] == record["projection_digest"], "proof-current-mismatch")
                        result = "applied"
                        if record["operation"] != "stop":
                            try:
                                self._source(binding, scope, item["versions"][-1])
                            except c.ContractError:
                                result = "committed-but-not-adoptable"
                elif preview is not None and state == preview["before"]["digest"]:
                    result = "not-applied"
                # 即使較晚的合法操作已前進，仍保留原 proof、回 state-unknown。
            try:
                files, storage = db.measure(directory, binding, limits)
                committed = c.integer(self._port("committed_work_bytes", binding))
                storage["available_work_bytes"] = max(0, storage["available_work_bytes"] - committed)
            except (OSError, c.ContractError):
                storage["coverage"] = "unknown"
                if result in {"applied", "committed-but-not-adoptable"}:
                    result = "committed-capacity-unproven"
            try:
                copies = self._copies(binding)
            except c.ContractError:
                result = "state-unknown"
            # digest 不能還原原始 preview 的外部集合；缺證據只回傳 proof/unknown。
            if result == "applied" and (preview is None or not c.copies_match(copies, preview["external_copies"])):
                result = "state-unknown"
        except c.ContractError as exc:
            if str(exc) == "readback-binding":
                raise
            if str(exc) in {"schema-mismatch", "metadata-mismatch", "integrity-failed", "projection-mismatch",
                            "proof-chain-mismatch", "proof-state-mismatch", "proof-current-mismatch", "proof-binding-mismatch",
                            "proof-sequence-mismatch", "proof-version-mismatch", "proof-lifecycle-mismatch",
                            "proof-projection-mismatch", "proof-time-mismatch", "restore-content-mismatch",
                            "restore-source-mismatch", "restore-stale-attestation", "restore-stale-validation"}:
                result = "integrity-failed"
                record = None
            else:
                result = "state-unknown"
        except (OSError, sqlite3.Error):
            result = "state-unknown"
        observed = self._clock()
        value = {"contract_version": "mg1-readback/v1", "scope": scope, "operation_id": operation_id,
                 "preview_digest": preview_digest, "observed_at": observed, "result": result, "state_digest": state,
                 "proof": record, "related_proofs": [], "deleted_proofs": [], "deleted_markers": [],
                 "managed_files": files, "storage": storage, "external_copies": copies,
                 "sanitization": "not-requested", "space_reclaim": "not-requested", "witness": None, "related_witnesses": []}
        return c.g1_readback(value, scope, limits, preview)

    @_boundary
    def readback(self, operation_id: str, preview_digest: str, *, preview: dict | None = None) -> dict:
        binding, scope, limits = self._root("readback", "readback")
        c.uuid(operation_id)
        c.digest_text(preview_digest)
        if preview is not None:
            c.g1_preview(preview, scope, limits)
            c.require(preview["operation_id"] == operation_id and c.digest(preview) == preview_digest, "readback-binding")
        try:
            with db.locked(binding) as directory:
                return self._readback_locked(directory, binding, scope, limits, operation_id, preview_digest, preview)
        except c.ContractError as exc:
            if str(exc) != "recovery-required":
                raise
            # 非空 journal 時不開 DB、不恢復；仍不能把中斷推論為未提交。
            self._read_authority(binding, "readback", operation_id)
            copies = self._copies(binding)
            result = {"contract_version": "mg1-readback/v1", "scope": scope, "operation_id": operation_id,
                      "preview_digest": preview_digest, "observed_at": self._clock(), "result": "state-unknown",
                      "state_digest": None, "proof": None, "related_proofs": [], "deleted_proofs": [],
                      "deleted_markers": [], "managed_files": [],
                      "storage": {"filesystem_id": binding.filesystem_id, "managed_bytes": 0,
                                  "available_work_bytes": 0, "coverage": "unknown", "work_budget": None},
                      "external_copies": copies, "sanitization": "not-requested", "space_reclaim": "not-requested",
                      "witness": None, "related_witnesses": []}
            return c.g1_readback(result, scope, limits, preview)

    @_boundary
    def audit(self) -> "AuditSnapshot":
        binding, scope, limits = self._root("audit", "audit")
        self._read_authority(binding, "audit")
        return AuditSnapshot(self, binding, scope, limits)

    @_boundary
    def recall(self, cues: list[str]) -> dict:
        binding, scope, limits = self._root("recall", "recall")
        self._read_authority(binding, "recall")
        c.require(type(cues) is list and 1 <= len(cues) <= 16, "invalid-cues")
        normalized = []
        for cue in cues:
            c.text(cue, 128)
            normalized.append(unicodedata.normalize("NFC", cue).casefold().strip())
            c.text(normalized[-1], 128)
        c.require(len(set(normalized)) == len(normalized), "duplicate-cues")
        with db.locked(binding), contextlib.closing(db.connect(binding, limits)) as connection:
            connection.execute("BEGIN")
            snapshot = db.snapshot(connection, scope, limits)
            self._clock(snapshot.clock_floor)
            placeholders = ",".join("?" for _ in normalized)
            rows = connection.execute("SELECT item_id FROM current_search WHERE cue IN (" + placeholders
                                      + ") GROUP BY item_id HAVING count(*)=? ORDER BY item_id LIMIT ?",
                                      (*normalized, len(normalized), limits["max_scan_items"] + 1)).fetchall()
            results = []
            refused = 0
            complete = len(rows) <= limits["max_scan_items"]
            for (item_id,) in rows[:limits["max_scan_items"]]:
                item = db.load_item(connection, item_id, scope, limits)
                c.require(item is not None and item["status"] == "active", "projection-mismatch")
                try:
                    self._source(binding, scope, item["versions"][-1])
                except c.ContractError:
                    refused += 1
                    continue
                result = {"item_id": item_id, "version": item["versions"][-1], "advisory_only": True}
                if len(c.canonical(results, 1_048_576)) + len(c.canonical(result)) > c.MAX_ENVELOPE - 4096:
                    complete = False
                    break
                results.append(result)
            return {"items": results, "enumeration_complete": complete, "source_rejected": refused,
                    "snapshot_digest": snapshot.digest, "advisory_only": True}


class AuditSnapshot:
    """單一唯讀 snapshot 的有界分頁；cursor 不可跨 close/process 或重送。"""
    def __init__(self, core, binding, scope, limits):
        self._core, self._binding, self._scope, self._limits = core, binding, scope, limits
        self._stack = contextlib.ExitStack()
        self._closed = False
        self._process = os.getpid()
        self._cursor = None
        self._last_item = ""
        self._pages = self._count = 0
        try:
            self._stack.enter_context(db.locked(binding))
            self._connection = self._stack.enter_context(contextlib.closing(db.connect(binding, limits)))
            self._connection.execute("BEGIN")
            self._snapshot = db.snapshot(self._connection, scope, limits)
            self._expires = core._clock(self._snapshot.clock_floor) + limits["confirmation_seconds"]
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def close(self):
        self._closed = True
        self._stack.close()

    @_boundary
    def page(self, cursor: str | None = None) -> dict:
        c.require(not self._closed and os.getpid() == self._process and cursor == self._cursor, "cursor-unavailable")
        if self._core._clock(self._snapshot.clock_floor) >= self._expires:
            self.close()
            raise c.ContractError("cursor-expired")
        self._core._read_authority(self._binding, "audit")
        c.require(self._pages < 40, "audit-page-limit")
        rows = self._connection.execute("SELECT item_id FROM items WHERE item_id>? ORDER BY item_id LIMIT ?",
                                        (self._last_item, self._limits["max_scan_items"])).fetchall()
        output = []
        verified = 0
        for (item_id,) in rows:
            item = db.load_item(self._connection, item_id, self._scope, self._limits)
            try:
                self._core._source(self._binding, self._scope, item["versions"][-1])
                summary = item["versions"][-1]["summary"]
                assessment = "eligible" if item["status"] == "active" else "stopped"
                verified += 1
            except c.ContractError:
                summary, assessment = None, "source-unavailable"
            output.append({"item_id": item_id, "revision": item["current_revision"], "status": item["status"],
                           "retained_versions": len(item["versions"]), "summary": summary, "assessment": assessment})
        self._count += len(rows)
        self._pages += 1
        complete = self._count == self._snapshot.items
        self._cursor = None if complete else str(uuid.uuid4())
        if rows:
            self._last_item = rows[-1][0]
        result = {"items": output, "enumeration_complete": complete, "next_cursor": self._cursor,
                  "snapshot_digest": self._snapshot.digest, "source_coverage": "complete" if verified == len(rows) else "partial",
                  "source_verified": verified, "source_checked": len(rows), "advisory_only": True}
        c.canonical(result, 1_048_576)
        if complete:
            self.close()
        return result
