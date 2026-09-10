"""G1 本機 POSIX host 組合元件；本模組不登錄或授予 production 能力。

只有 host 程式可注入 ports。候選、CLI、設定檔及量測報告均不是 authority。
Source/authority/qualification 的接受仍屬各 port 的 TCB；相同 OS 使用者不在隔離保證內。
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import os
import time
import uuid
from typing import Protocol

import memory_governance_contract as c
from memory_governance_host import AcceptedPreview, ClockSample, RootBinding, SourceObservation, SourcePort
import memory_governance_storage as db


def _file_identity(value):
    c.require(type(value) is tuple and len(value) == 2
              and all(type(number) is int and number >= 0 for number in value), "invalid-file-identity")


class LocalClock:
    """不修飾系統時間；倒退／到期交由 core 拒絕，不從候選接受時間值。"""

    def __init__(self):
        self._pid = os.getpid()
        self._process_id = str(uuid.uuid4())

    def clock(self) -> ClockSample:
        c.require(os.getpid() == self._pid, "process-changed")
        return ClockSample(time.time_ns() // 1_000_000_000, time.monotonic_ns(), self._process_id)


class SingleRootRegistry:
    """host 擁有的單 root RAM 登錄；不讀 config、不採納庫內自述或重開後新 inode。

初始 RootBinding 必須來自 host 已接受的來源。這裡的 shape/檔案檢查只驗 binding，
不能將由 agent 編輯的 registry 檔案認證為人類授權。
"""

    def __init__(self, binding: RootBinding):
        c.require(type(binding) is RootBinding, "root-binding-mismatch")
        limits = c.profile(c.decode(binding.profile_bytes, 4096))
        scope = c.scope(c.decode(binding.scope_bytes, 4096), c.digest(limits), c.digest(c.POLICY))
        c.require(scope["schema_fingerprint"] == db.SCHEMA_FINGERPRINT, "schema-mismatch")
        c.require(binding.profile_bytes == c.canonical(limits)
                  and binding.scope_bytes == c.canonical(scope), "noncanonical-binding")
        c.opaque(binding.filesystem_id)
        c.digest_text(binding.adapter_fingerprint)
        c.require(type(binding.capabilities) is frozenset
                  and binding.capabilities <= {"initialize", "audit", "recall", "readback", "content-write"},
                  "capability-unavailable")
        c.require((binding.main_identity is None) == (binding.lock_identity is None), "partial-root-binding")
        for identity in (binding.directory_identity, binding.main_identity, binding.lock_identity):
            if identity is not None:
                _file_identity(identity)
        c.require(binding.directory_identity is not None, "invalid-file-identity")
        self._binding = binding

    def binding(self) -> RootBinding:
        return self._binding

    def bind_initialized(self, binding: RootBinding, main: tuple[int, int], lock: tuple[int, int]) -> None:
        c.require(binding == self._binding and binding.main_identity is None
                  and binding.lock_identity is None, "already-initialized-or-drifted")
        _file_identity(main)
        _file_identity(lock)
        rebound = replace(binding, main_identity=main, lock_identity=lock)
        # 不靠 initialize 回傳的 tuple 自證；獨立核對目錄及檔案的 owner/mode/device/inode。
        directory = db.root_fd(rebound)
        try:
            entries = db.inventory(directory, rebound)
            c.require(set(entries) == {db.MAIN, db.LOCK}, "initialization-readback-mismatch")
        finally:
            os.close(directory)
        self._binding = rebound


class LocalAuthorityPort(Protocol):
    def accept_initialization(self, binding: RootBinding) -> bool: ...

    def accept_preview(self, binding: RootBinding, preview_bytes: bytes) -> AcceptedPreview:
        """同 bytes 渲染及當次人類接受；不從 bool 製造 confirmation。"""
        ...

    def authorize_read(self, binding: RootBinding, purpose: str, operation_id: str | None) -> bool: ...

    def external_copies(self, binding: RootBinding) -> dict: ...


class StorageQualificationPort(Protocol):
    def qualify(self, binding: RootBinding, runtime: dict, operation: str) -> bool: ...

    def committed_work_bytes(self, binding: RootBinding) -> int: ...

    def work_budget(self, binding: RootBinding, runtime: dict, files: list[dict],
                    operation: str, candidate_bytes: bytes | None) -> dict:
        """獨立核對接受資格並重算 J/T/G；測量最大值不能自動升為 upper bound。"""
        ...


MAX_ARTIFACT_BYTES = 65536


@dataclass(frozen=True)
class RepositoryArtifact:
    """一次 host 核准來源的完整觀察；不包含可由 caller 選擇的實體 root。"""

    source_id: str
    repository_id: str
    source_revision: str
    path: str
    content: bytes
    status: str


class RepositoryArtifactPort(Protocol):
    def read_artifact(self, binding: RootBinding, provenance_bytes: bytes) -> RepositoryArtifact:
        """每次重查 host 允許集合、撤銷及固定 artifact；只讀核准的 repo/commit/path。

        從 reader 取得完整內容前就須限制 I/O bytes／時間，不能先無界讀取再截斷。
        不得由候選建立 root、fetch、跟隨 symlink、Git config/alternate 或載入程式。
        status 僅為 current/revoked/unavailable；只接受當次有效的固定 revision。
        """
        ...


class SourceReviewPort(Protocol):
    def review_source(self, binding: RootBinding, version_bytes: bytes,
                      artifacts: tuple[RepositoryArtifact, ...]) -> SourceObservation:
        """獨立檢查完整 candidate 的支持證據、敏感性、前提及 policy，不複製自述。

        完整相符 artifact 不是 eligible/safe；validation.evidence_id/verifier 仍須由
        此可信 port 對照當次獨立結果。失效／無法確認就拒絕，不產生人類 decision token。
        """
        ...


class RepositorySource:
    """repo-artifact 的有界內容綁定；reader 和語意／安全 reviewer 皆須另行取得資格。

    這不是通用 Git reader。沒有 human-confirmed-decision adapter，不代簽 attestation。
    不快取來源或正文；每次 core source 檢查都重新呼叫 ports。
    """

    def __init__(self, reader: RepositoryArtifactPort | None = None, reviewer: SourceReviewPort | None = None):
        self._reader = reader
        self._reviewer = reviewer

    def observe_source(self, binding: RootBinding, version_bytes: bytes) -> SourceObservation:
        c.require(self._reader is not None and self._reviewer is not None, "source-port-unavailable")
        limits = c.profile(c.decode(binding.profile_bytes, 4096))
        scope = c.scope(c.decode(binding.scope_bytes, 4096), c.digest(limits), c.digest(c.POLICY))
        value = c.validate_version(c.decode(version_bytes, limits["max_payload_bytes"]), scope, limits)
        c.require(all(provenance["kind"] == "repo-artifact" for provenance in value["provenance"]),
                  "source-kind-unavailable")
        observations = []
        for provenance in value["provenance"]:
            observed = self._reader.read_artifact(binding, c.canonical(provenance, 16384))
            c.require(type(observed) is RepositoryArtifact, "artifact-unavailable")
            c.require(type(observed.status) is str and observed.status == "current", "artifact-not-current")
            c.require(type(observed.content) is bytes and len(observed.content) <= MAX_ARTIFACT_BYTES,
                      "artifact-too-large-or-incomplete")
            reference = provenance["reference"]
            c.require(all(type(text) is str for text in (observed.source_id, observed.repository_id,
                                                       observed.source_revision, observed.path))
                      and observed.source_id == provenance["source_id"]
                      and observed.repository_id == reference["repository_id"] == scope["repository_id"]
                      and observed.source_revision == provenance["source_revision"]
                      and observed.path == reference["path"]
                      and hashlib.sha256(observed.content).hexdigest() == provenance["source_digest"],
                      "artifact-binding-mismatch")
            observations.append(observed)
        return self._reviewer.review_source(binding, version_bytes, tuple(observations))


class LocalHost:
    """組合 HostAuthorityPort；缺 port 明確拒絕，不提供 discovery 或 production factory。

Source port 缺失不阻止精確 stop，沿用既有 G0 語意；需要來源的操作由 core 拒絕。
Core 仍擁有 fresh SQLite readback、單次 handle、TTL 及所有 envelope 檢查。
"""

    def __init__(self, registry: SingleRootRegistry, *, source: SourcePort | None = None,
                 authority: LocalAuthorityPort | None = None,
                 qualification: StorageQualificationPort | None = None,
                 clock: LocalClock | None = None):
        self._registry = registry
        self._source = source
        self._authority = authority
        self._qualification = qualification
        self._clock = LocalClock() if clock is None else clock

    def binding(self) -> RootBinding:
        return self._registry.binding()

    def _call(self, port, method: str, binding: RootBinding, *args):
        c.require(binding == self.binding(), "root-binding-drift")
        c.require(port is not None, "local-port-unavailable")
        return getattr(port, method)(binding, *args)

    def clock(self) -> ClockSample:
        return self._clock.clock()

    def qualify(self, binding: RootBinding, runtime: dict, operation: str) -> bool:
        return self._call(self._qualification, "qualify", binding, runtime, operation)

    def accept_initialization(self, binding: RootBinding) -> bool:
        return self._call(self._authority, "accept_initialization", binding)

    def bind_initialized(self, binding: RootBinding, main: tuple[int, int], lock: tuple[int, int]) -> None:
        self._registry.bind_initialized(binding, main, lock)

    def observe_source(self, binding: RootBinding, version_bytes: bytes):
        return self._call(self._source, "observe_source", binding, version_bytes)

    def accept_preview(self, binding: RootBinding, preview_bytes: bytes) -> AcceptedPreview:
        return self._call(self._authority, "accept_preview", binding, preview_bytes)

    def authorize_read(self, binding: RootBinding, purpose: str, operation_id: str | None) -> bool:
        return self._call(self._authority, "authorize_read", binding, purpose, operation_id)

    def external_copies(self, binding: RootBinding) -> dict:
        return self._call(self._authority, "external_copies", binding)

    def committed_work_bytes(self, binding: RootBinding) -> int:
        return self._call(self._qualification, "committed_work_bytes", binding)

    def work_budget(self, binding: RootBinding, runtime: dict, files: list[dict],
                    operation: str, candidate_bytes: bytes | None) -> dict:
        return self._call(self._qualification, "work_budget", binding, runtime, files, operation, candidate_bytes)
