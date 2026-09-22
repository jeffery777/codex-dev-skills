"""單專案 audit-only trusted host adapter。建構式是 TCB API，不是設定／JSON 入口。

Host 必須另行接受精確 root、principal、要求、來源及環境資格；本模組不產生
這些接受證據，不登錄 production，不授予寫入、初始化或維護能力。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
from types import MappingProxyType

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_host import ClockSample, RootBinding, SourceObservation
from memory_governance_local import LocalClock, LocalHost, RepositorySource, SingleRootRegistry
from memory_audit_source import ArtifactPermit, GitRepositoryBinding, PinnedGitReader

# 有界本機 reference envelope，並非已接受的 production qualification。
AUDIT_ENVELOPE = MappingProxyType({
    'max_pages': 40, 'max_output_bytes': 262144, 'timeout_seconds': 10,
    'artifact_bytes': 65536, 'artifact_timeout_ms': 250, 'artifact_count': 16,
    'max_items': 10000, 'max_versions': 10, 'max_proofs': 33792,
    'data_limit_bytes': 268435456,
})
PORT_FILES = ('memory_audit_pilot.py', 'memory_audit_preflight.py', 'memory_audit_authority.py', 'memory_audit_dispatch.py', 'governancectl.py', 'memory_audit_adapter.py', 'memory_audit_source.py', 'memory_audit.py',
              'memory_governance_core.py', 'memory_governance_contract.py',
              'memory_governance_host.py', 'memory_governance_local.py', 'memory_governance_storage.py')


def adapter_fingerprint():
    # 固定安裝來源，不讀使用者提供的路徑。資格需在更新程式後重新接受。
    return c.digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                     for name in PORT_FILES})


def audit_environment(binding, runtime):
    """只提供待獨立接受的當前觀察；呼叫此函式本身絕不取得資格。"""
    return {'runtime': runtime, 'machine': platform.machine(), 'python_implementation': platform.python_implementation(),
            'filesystem_id': binding.filesystem_id, 'device': binding.directory_identity[0],
            'temp_policy': 'sqlite-memory-no-artifact-temp', 'ports_fingerprint': adapter_fingerprint(),
            'profile_digest': c.digest(c.decode(binding.profile_bytes)), 'envelope': dict(AUDIT_ENVELOPE)}


@dataclass(frozen=True)
class ReadGrant:
    binding: RootBinding
    principal_id: str
    request_id: str
    issued: ClockSample
    expires_at: int


class AuditReadAuthority:
    """每次人類要求建立一個 instance；單次 claim、期限、撤銷與雙時鐘均 fail closed。

    revoked(request_id) 由 host 的可信控制面提供；此模組沒有 issue-grant 或
    confirmed=true 路徑。相同 OS 使用者的任意 Python 不在安全隔離保證內。
    """

    def __init__(self, grant: ReadGrant, *, principal_id, request_id, revoked, clock):
        c.require(type(grant) is ReadGrant and type(grant.issued) is ClockSample, 'read-unavailable')
        c.uuid(principal_id)
        c.uuid(request_id)
        c.integer(grant.expires_at)
        c.require(principal_id == grant.principal_id == c.decode(grant.binding.scope_bytes)['principal_id']
                  and request_id == grant.request_id
                  and 0 < grant.expires_at - grant.issued.utc_seconds <= 300, 'read-unavailable')
        self.grant, self.revoked, self.clock = grant, revoked, clock
        self._claimed = False
        self._pid = os.getpid()
        self._last = grant.issued
        self._invalid = False

    def valid(self, binding):
        try:
            c.require(not self._invalid and binding == self.grant.binding and os.getpid() == self._pid,
                      'read-unavailable')
            revoked = self.revoked(self.grant.request_id)
            sample = self.clock.clock()
            valid = (not self._invalid and binding == self.grant.binding and os.getpid() == self._pid
                     and type(sample) is ClockSample and sample.process_id == self.grant.issued.process_id
                     and self._last.utc_seconds <= sample.utc_seconds < self.grant.expires_at
                     and self._last.monotonic_ns <= sample.monotonic_ns
                     and sample.monotonic_ns - self.grant.issued.monotonic_ns
                     < (self.grant.expires_at - self.grant.issued.utc_seconds) * 1_000_000_000
                     and revoked is False)
            self._last = sample
        except Exception:
            valid = False
        self._invalid = not valid
        return valid

    def claim(self, binding):
        if self._claimed or not self.valid(binding):
            return False
        self._claimed = True
        return True

    def authorize_read(self, binding, purpose, operation_id):
        return (self._claimed and purpose == 'audit' and operation_id is None and self.valid(binding))

    def check(self):
        c.require(self.authorize_read(self.grant.binding, 'audit', None), 'read-unavailable')

    def external_copies(self, binding):
        self.check()
        return {'coverage': 'unknown', 'observed_at': self.clock.clock().utc_seconds, 'copies': []}

    def accept_initialization(self, binding):
        return False

    def accept_preview(self, binding, preview_bytes):
        raise c.ContractError('capability-unavailable')


@dataclass(frozen=True)
class SourceAcceptance:
    scope_digest: str
    version_digest: str
    provenance_digest: str
    policy_fingerprint: str
    verifier_fingerprint: str
    evidence_id: str
    eligibility: str
    safety: str
    expires_at: int


class AcceptedSourceReview:
    """接受資料須由獨立 reviewer 交給 host；不由 candidate.validation 自動建立。"""

    def __init__(self, accepted: tuple[SourceAcceptance, ...], *, revoked, authority):
        c.require(type(accepted) is tuple and len(accepted) <= AUDIT_ENVELOPE['max_items'], 'source-unavailable')
        c.require(all(type(entry) is SourceAcceptance for entry in accepted), 'source-unavailable')
        c.require(len({entry.version_digest for entry in accepted}) == len(accepted), 'source-unavailable')
        self.accepted = MappingProxyType({entry.version_digest: entry for entry in accepted})
        self.revoked, self.authority = revoked, authority
        self._disclosed = set()

    def _valid(self, entry):
        self.authority.check()
        return (self.authority.clock.clock().utc_seconds < entry.expires_at
                and self.revoked(entry.evidence_id) is False
                and entry.eligibility == 'eligible' and entry.safety == 'safe')

    def disclosure_valid(self):
        return all(self._valid(self.accepted[key]) for key in self._disclosed)

    def review_source(self, binding, version_bytes, artifacts):
        value = c.decode(version_bytes, 16384)
        entry = self.accepted.get(c.digest(value))
        c.require(entry is not None and self._valid(entry), 'source-unavailable')
        c.require(binding == self.authority.grant.binding and artifacts
                  and entry.scope_digest == c.digest(c.decode(binding.scope_bytes))
                  and entry.provenance_digest == c.digest(value['provenance'])
                  and entry.policy_fingerprint == c.digest(c.POLICY), 'source-unavailable')
        self._disclosed.add(entry.version_digest)
        return SourceObservation(entry.scope_digest, entry.version_digest, entry.provenance_digest,
                                 entry.policy_fingerprint, entry.verifier_fingerprint, entry.evidence_id,
                                 self.authority.clock.clock().utc_seconds, entry.eligibility, entry.safety)


@dataclass(frozen=True)
class AuditQualification:
    """Host 獨立接受的環境與測試 evidence；observed facts／fixture PASS 不會自動產生本記錄。"""
    binding_digest: str
    environment_bytes: bytes
    evidence_id: str
    expires_at: int


class AuditOnlyHost(LocalHost):
    """每個 instance 只供一個要求／snapshot；失敗後也必須換新 grant 與 host。

    不提供 initialize/write/recall/readback，無持久 registry、動態 import 或 CLI 載入器。
    """

    audit_timeout_seconds = AUDIT_ENVELOPE['timeout_seconds']

    def __init__(self, registry: SingleRootRegistry, *, authority: AuditReadAuthority,
                 repository: GitRepositoryBinding, permits: tuple[ArtifactPermit, ...],
                 source_review: AcceptedSourceReview, qualification: AuditQualification,
                 qualification_revoked):
        binding = registry.binding()
        c.require(binding.capabilities == frozenset({'audit'}) and binding.main_identity is not None
                  and binding.lock_identity is not None and authority.grant.binding == binding
                  and source_review.authority is authority, 'capability-unavailable')
        c.require(type(qualification) is AuditQualification, 'qualification-unavailable')
        c.opaque(qualification.evidence_id)
        c.integer(qualification.expires_at)
        self.authority = authority
        self.reader = PinnedGitReader(binding, repository, permits, check=authority.check)
        self.reviewer, self.qualification = source_review, qualification
        self.qualification_revoked = qualification_revoked
        self._source_invalid = False
        super().__init__(registry, source=RepositorySource(self.reader, source_review), authority=authority,
                         qualification=self, clock=authority.clock)

    def qualify(self, binding, runtime, operation):
        if operation != 'audit' or binding != self.binding() or not self.authority.claim(binding):
            return False
        profile = c.decode(binding.profile_bytes)
        return (profile['data_limit_bytes'] == AUDIT_ENVELOPE['data_limit_bytes']
                and runtime['platform'] in {'Darwin', 'Linux'} and runtime['temp_store'] == 'memory'
                and self.qualification.binding_digest == db.binding_digest(binding)
                and self.qualification.environment_bytes == c.canonical(audit_environment(binding, runtime))
                and self._qualification_current())

    def _qualification_current(self):
        return (self.authority.clock.clock().utc_seconds < self.qualification.expires_at
                and self.qualification_revoked(self.qualification.evidence_id) is False)

    def authorize_read(self, binding, purpose, operation_id):
        if not (self.authority.authorize_read(binding, purpose, operation_id)
                and not self._source_invalid and self._qualification_current()
                and self.reviewer.disclosure_valid()):
            return False
        try:
            if self.reader._observed:
                self.reader.validate_disclosure()
        except (c.ContractError, OSError):
            self._source_invalid = True
            return False
        return True

    def observe_source(self, binding, version_bytes):
        try:
            return super().observe_source(binding, version_bytes)
        except c.ContractError as exc:
            if str(exc) in {'source-identity-mismatch', 'source-integrity-failed'}:
                self._source_invalid = True
            raise

    def bind_initialized(self, binding, main, lock):
        raise c.ContractError('capability-unavailable')

    def committed_work_bytes(self, binding):
        raise c.ContractError('capability-unavailable')

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        raise c.ContractError('capability-unavailable')
