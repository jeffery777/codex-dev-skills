"""可信 host 的 advisory 預檢與 canary 組合；不接受 argv/config，不建立授權。

MetadataInspection 是 host 明確接受的有限觀察範圍，絕非正文讀取權。
預檢不開啟持久 SQLite、不查 lifecycle、不讀來源 object、不 claim grant。
"""
from __future__ import annotations

from dataclasses import dataclass
import os

import memory_governance_contract as c
import memory_governance_storage as db
from memory_audit import audit_report, _reason
from memory_audit_adapter import (AUDIT_ENVELOPE, AuditQualification, SourceAcceptance,
                                  audit_environment, adapter_fingerprint)
from memory_audit_authority import AuthorityStoreBinding, AuditAuthorityProvider, SCHEMA, target_digest
from memory_audit_dispatch import AuditDispatch, AuditHostFactory
from memory_audit_source import PinnedGitReader


@dataclass(frozen=True)
class MetadataInspection:
    """Host 另行允許已接受兩個目錄的 stat/inventory 與本機環境觀察；無正文權。"""
    target_digest: str
    store: AuthorityStoreBinding
    issued: object
    expires_at: int
    evidence_id: str


@dataclass(frozen=True)
class AuthorityQualification:
    """Authority filesystem 的獨立接受；不得以 managed target 標籤代替。"""
    environment_bytes: bytes
    evidence_id: str
    expires_at: int


def _metadata(binding, check=lambda: None):
    check()
    directory = db.root_fd(binding)
    try:
        check()
        entries = db.inventory(directory, binding)
        check()
        c.require(db.JOURNAL not in entries or entries[db.JOURNAL].st_size == 0, 'recovery-required')
        fs = os.fstatvfs(directory)
        check()
        # Filesystem IDs are opaque OS integers, not bounded application counters.
        return {'device': binding.directory_identity[0], 'filesystem_identity': str(fs.f_fsid),
                'block_size': fs.f_frsize, 'flags': fs.f_flag}
    finally:
        os.close(directory)


def authority_environment(store, *, check=lambda: None):
    """有限 metadata/runtime 觀察，不核發資格；呼叫須有 host 的 metadata 許可。

    不使用 store.files 中由 target 複製的 filesystem/profile/adapter 標籤。
    不開啟 authority DB/lock，只 stat/inventory；SQLite probe 為 :memory:。
    """
    c.require(type(store) is AuthorityStoreBinding, 'read-unavailable')
    filesystem = _metadata(store.files, check)
    check()
    runtime = db.runtime_facts()
    check()
    fingerprint = adapter_fingerprint()
    check()
    return {'contract': 'mg1-authority-environment/v1', 'store_id': store.store_id,
            'target_digest': store.target_digest,
            'directory': list(store.files.directory_identity),
            'main': list(store.files.main_identity), 'lock': list(store.files.lock_identity),
            'filesystem': filesystem, 'runtime': runtime,
            'schema': SCHEMA,
            'ports_fingerprint': fingerprint}


@dataclass(frozen=True)
class AuditPreflightContext:
    """全由 host 接受的程式物件；缺件可為 None，只能診斷，不能自動補齊。"""
    binding: object = None
    repository: object = None
    permits: object = None
    accepted_sources: object = None
    qualification: object = None
    store: object = None
    authority_qualification: object = None
    inspection: object = None
    clock: object = None
    source_revoked: object = None
    qualification_revoked: object = None
    authority_qualification_revoked: object = None
    inspection_revoked: object = None

    def inspection_allowed(self):
        permit = self.inspection
        if not (type(permit) is MetadataInspection
                and permit.target_digest == target_digest(self.binding)
                and permit.store == self.store and type(self.store) is AuthorityStoreBinding
                and self.store.target_digest == target_digest(self.binding)):
            return False
        from memory_governance_host import ClockSample
        c.require(type(permit.issued) is ClockSample, 'read-unavailable')
        c.opaque(permit.evidence_id)
        c.integer(permit.expires_at)
        revoked = self.inspection_revoked(permit.evidence_id)
        sample = self.clock.clock()
        return (type(sample) is ClockSample and sample.process_id == permit.issued.process_id
                and 0 < permit.expires_at - permit.issued.utc_seconds <= 300
                and permit.issued.utc_seconds <= sample.utc_seconds < permit.expires_at
                and 0 <= sample.monotonic_ns - permit.issued.monotonic_ns
                < (permit.expires_at - permit.issued.utc_seconds) * 1_000_000_000
                and revoked is False)

    def check_inspection(self):
        c.require(self.inspection_allowed(), 'read-unavailable')

    def authority_current(self):
        c.require(self.inspection_allowed(), 'qualification-unavailable')
        q = self.authority_qualification
        c.require(type(q) is AuthorityQualification, 'qualification-unavailable')
        c.opaque(q.evidence_id)
        c.integer(q.expires_at)
        environment = c.canonical(authority_environment(self.store, check=self.check_inspection))
        revoked = self.authority_qualification_revoked(q.evidence_id)
        c.require(self.inspection_allowed()
                  and revoked is False
                  and self.clock.clock().utc_seconds < q.expires_at
                  and q.environment_bytes == environment,
                  'qualification-unavailable')


def preflight_report(*, enabled=False, context=None, provider=None, request=None):
    """僅固定診斷；observed 不是 PASS、讀取權或正式資格。off 在所有接觸前返回。"""
    result = {'contract_version': 'mg1-audit-preflight/v1', 'status': 'disabled',
              'advisory_only': True, 'production_qualified': False, 'activation_authorized': False,
              'grant_consumed': False, 'write_performed': False, 'checks': {}}
    if enabled is not True:
        return result
    result['status'] = 'observed'
    checks = result['checks']
    def check(name, action, missing=False):
        if missing:
            checks[name] = {'status': 'missing', 'reason': 'host-acceptance-required'}
            return False
        try:
            action()
            checks[name] = {'status': 'observed', 'reason': 'advisory-only'}
            return True
        except c.ContractError as exc:
            checks[name] = {'status': 'invalid', 'reason': _reason(exc)}
        except Exception as exc:
            checks[name] = {'status': 'unknown', 'reason': _reason(exc)}
        return False
    if type(context) is not AuditPreflightContext:
        checks['context'] = {'status': 'missing' if context is None else 'invalid',
                             'reason': 'host-acceptance-required'}
        return result
    ctx = context
    target_ok = check('target', lambda: target_digest(ctx.binding), ctx.binding is None)
    check('authority_binding', lambda: c.require(type(ctx.store) is AuthorityStoreBinding
          and ctx.store.target_digest == target_digest(ctx.binding), 'read-unavailable'), ctx.store is None)
    def sources():
        PinnedGitReader(ctx.binding, ctx.repository, ctx.permits, check=lambda: None)  # 無 I/O。
        c.require(type(ctx.accepted_sources) is tuple and 0 < len(ctx.accepted_sources)
                  <= AUDIT_ENVELOPE['max_items'], 'source-unavailable')
        seen = set()
        for entry in ctx.accepted_sources:
            c.require(type(entry) is SourceAcceptance, 'source-unavailable')
            for value in (entry.scope_digest, entry.version_digest, entry.provenance_digest,
                          entry.policy_fingerprint):
                c.digest_text(value)
            c.opaque(entry.evidence_id)
            c.opaque(entry.verifier_fingerprint)
            c.integer(entry.expires_at)
            revoked = ctx.source_revoked(entry.evidence_id)
            ctx.check_inspection()
            c.require(entry.version_digest not in seen
                      and entry.scope_digest == c.digest(c.decode(ctx.binding.scope_bytes))
                      and entry.policy_fingerprint == c.digest(c.POLICY)
                      and entry.eligibility == 'eligible' and entry.safety == 'safe'
                      and ctx.clock.clock().utc_seconds < entry.expires_at
                      and revoked is False, 'source-unavailable')
            seen.add(entry.version_digest)
    allowed = target_ok and check('metadata_permission',
        lambda: c.require(ctx.inspection_allowed(), 'read-unavailable'), ctx.inspection is None)
    check('source_acceptance', sources if allowed else lambda: c.require(False, 'read-unavailable'), any(x is None for x in
          (ctx.binding, ctx.repository, ctx.permits, ctx.accepted_sources, ctx.clock, ctx.source_revoked)))
    # 沒有正文讀取權，不能驗證來源 tuples 與 managed versions 的完整涵蓋。
    checks['source_content_coverage'] = {'status': 'unknown', 'reason': 'content-not-inspected'}
    def metadata(binding):
        c.require(ctx.inspection_allowed(), 'read-unavailable')
        return _metadata(binding, ctx.check_inspection)
    if allowed:
        check('target_metadata', lambda: metadata(ctx.binding))
        check('authority_metadata', lambda: metadata(ctx.store.files))
        check('authority_environment', ctx.authority_current, ctx.authority_qualification is None)
        def qualification():
            c.require(ctx.inspection_allowed(), 'read-unavailable')
            q = ctx.qualification
            c.require(type(q) is AuditQualification, 'qualification-unavailable')
            c.opaque(q.evidence_id)
            c.integer(q.expires_at)
            runtime = db.runtime_facts()
            ctx.check_inspection()
            environment = c.canonical(audit_environment(ctx.binding, runtime))
            revoked = ctx.qualification_revoked(q.evidence_id)
            ctx.check_inspection()
            c.require(c.decode(ctx.binding.profile_bytes)['data_limit_bytes'] == AUDIT_ENVELOPE['data_limit_bytes']
                      and runtime['platform'] in {'Darwin', 'Linux'} and runtime['temp_store'] == 'memory'
                      and q.binding_digest == db.binding_digest(ctx.binding)
                      and q.environment_bytes == environment
                      and ctx.clock.clock().utc_seconds < q.expires_at
                      and revoked is False, 'qualification-unavailable')
        check('managed_environment', qualification, ctx.qualification is None)
    else:
        for name in ('target_metadata', 'authority_metadata', 'authority_environment', 'managed_environment'):
            checks[name] = {'status': 'unknown', 'reason': 'metadata-inspection-not-authorized'}
    checks['authority_store_contents'] = {'status': 'unknown', 'reason': 'lifecycle-not-inspected'}
    def pending():
        c.require(ctx.inspection_allowed(), 'read-unavailable')
        c.require(type(provider) is AuditAuthorityProvider and provider.binding == ctx.binding
                  and provider.store == ctx.store, 'read-unavailable')
        c.require(provider.pending_current(request), 'read-unavailable')
    if allowed:
        check('request', pending, provider is None or request is None)
    else:
        checks['request'] = {'status': 'unknown', 'reason': 'metadata-inspection-not-authorized'}
    return result


def canary_report(*, enabled=False, context=None, provider=None, request=None):
    """新的 host accept 後才傳入 request；不讀取／採納預檢結果，也不自己 accept。

    managed memory 唯讀；provider take 的 authority bookkeeping 另有寫入。
    既有 audit_report 保留逐次及最後 disclosure 驗證與失效內容清空。
    """
    if enabled is not True:
        return audit_report()
    try:
        c.require(type(context) is AuditPreflightContext and type(provider) is AuditAuthorityProvider
                  and provider.binding == context.binding and provider.store == context.store,
                  'read-unavailable')
        ctx = context
        def take(req):
            try:
                ctx.authority_current()
            except Exception:
                provider.close()
                raise
            return provider.take_grant(req)
        def revoked(request_id):
            try:
                ctx.authority_current()
                return provider.revoked(request_id)
            except Exception:
                provider.close()
                return True
        factory = AuditHostFactory(binding=ctx.binding, repository=ctx.repository, permits=ctx.permits,
            accepted_sources=ctx.accepted_sources, qualification=ctx.qualification,
            take_grant=take, clock=ctx.clock, request_revoked=revoked,
            source_revoked=ctx.source_revoked, qualification_revoked=ctx.qualification_revoked)
        return audit_report(enabled=True, dispatch=AuditDispatch(factory, request))
    except Exception as exc:
        # 與既有報告同一安全分類，不回顯輸入或原始 exception。
        from memory_audit import _empty
        result = _empty()
        result['reason'] = _reason(exc)
        return result
