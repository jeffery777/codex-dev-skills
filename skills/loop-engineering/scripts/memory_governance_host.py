"""MG1 可信呼叫端介面。未提供任何 production adapter 或資料驅動註冊入口。

Ports 屬 host 的 trusted computing base；相同 OS 使用者／任意 Python 執行者不在
隔離保證內。測試可由自己的程式注入 synthetic ports，JSON/CLI 不能建立權限。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Protocol

from memory_governance_contract import ContractError

FileIdentity = tuple[int, int]


@dataclass(frozen=True)
class RootBinding:
    """由 host 登錄的實體目錄、檔案 identity 與不可變契約 bytes。"""

    root: Path
    directory_identity: FileIdentity
    main_identity: FileIdentity | None
    lock_identity: FileIdentity | None
    scope_bytes: bytes
    profile_bytes: bytes
    filesystem_id: str
    adapter_fingerprint: str
    capabilities: frozenset[str]


@dataclass(frozen=True)
class ClockSample:
    utc_seconds: int
    monotonic_ns: int
    process_id: str


@dataclass(frozen=True)
class SourceObservation:
    scope_digest: str
    version_digest: str
    provenance_digest: str
    policy_fingerprint: str
    verifier_fingerprint: str
    evidence_id: str
    observed_at: int
    eligibility: str
    safety: str


@dataclass(frozen=True)
class AcceptedPreview:
    """只能採用合格 host port 的當次回傳；相同 bytes 自身不提供授權。"""

    preview_bytes: bytes
    confirmation_bytes: bytes


class ClockPort(Protocol):
    def clock(self) -> ClockSample:
        """同次 UTC／monotonic 觀察；process_id 重開後更換。"""
        ...


class SourcePort(Protocol):
    def observe_source(self, binding: RootBinding, version_bytes: bytes) -> SourceObservation:
        """獨立重查完整候選、來源、適用前提、撤銷、敏感性與 policy。不得依候選自述。"""
        ...


class ReadbackPort(Protocol):
    def authorize_read(self, binding: RootBinding, purpose: str, operation_id: str | None) -> bool:
        """audit/recall 或精確 operation 的新讀回授權，不新增 mutation 權限。"""
        ...

    def external_copies(self, binding: RootBinding) -> dict:
        """當次有界觀察。無法觀察外部範圍時 coverage=unknown，不填零存在。"""
        ...


class HostAuthorityPort(ClockPort, SourcePort, ReadbackPort, Protocol):
    def binding(self) -> RootBinding:
        """只從 host 擁有的登錄取得 root；不由 record/request 指定路徑。"""
        ...

    def qualify(self, binding: RootBinding, runtime: dict, operation: str) -> bool:
        """核對 adapter/build/schema/固定 SQL/profile/OS/filesystem/temp 與該操作資格。"""
        ...

    def accept_initialization(self, binding: RootBinding) -> bool:
        """新 root 明確建立授權；不含 migration、repair、overwrite 或 activation。"""
        ...

    def bind_initialized(self, binding: RootBinding, main: FileIdentity, lock: FileIdentity) -> None:
        """host 獨立核對已建立檔案，再更新自身可信登錄；不採纳庫內 identity 自述。"""
        ...

    def accept_preview(self, binding: RootBinding, preview_bytes: bytes) -> AcceptedPreview:
        """同 bytes 渲染與目前明確人類意圖；不得以 confirmed=true/argv/舊記憶代替。"""
        ...

    def committed_work_bytes(self, binding: RootBinding) -> int:
        """同 filesystem 上 host 已承諾但尚未分配的其他工作預算；當次重新觀察。"""
        ...

    def work_budget(self, binding: RootBinding, runtime: dict, files: list[dict],
                    operation: str, candidate_bytes: bytes | None) -> dict:
        """從當前受信任 qualification 重新計算 J/T/G；不是只檢查 caller qualification ID。"""
        ...


# 初始接受集合為空。刻意沒有 register/load-plugin/import-path 等資料入口。
# 新增 production adapter 須獨立 reviewed qualification 及明確啟用，不由 G1 測試授予。
PRODUCTION_ADAPTERS: Mapping[str, HostAuthorityPort] = MappingProxyType({})


def production_host(adapter_id: str) -> HostAuthorityPort:
    try:
        return PRODUCTION_ADAPTERS[adapter_id]
    except (KeyError, TypeError) as exc:
        raise ContractError("adapter-unavailable") from exc
