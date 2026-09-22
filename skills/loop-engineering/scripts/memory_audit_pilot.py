"""明確 opt-in 的固定 synthetic pilot；不載入既有專案、不登錄 production adapter。

此程式內的 seed/source/qualification 接受只是 synthetic TCB，不認證人類身分。
每次建立新的隔離目錄；結束保留資料，RAM 授權不持久化或恢復。
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid
import zlib

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from memory_governance_host import AcceptedPreview, RootBinding, SourceObservation
from memory_governance_local import LocalClock, LocalHost, SingleRootRegistry
from memory_audit import _reason
from memory_audit_adapter import AuditQualification, SourceAcceptance, adapter_fingerprint, audit_environment
from memory_audit_authority import AuditAuthorityProvider, initialize_store, target_digest
from memory_audit_source import ArtifactPermit, GitRepositoryBinding
from memory_audit_preflight import (AuditPreflightContext, AuthorityQualification, MetadataInspection,
                                    authority_environment, canary_report, preflight_report)

ARTIFACT = b'Synthetic pilot widget label blue. No real project data.\n'
REPOSITORY = 'synthetic-pilot-repository'


def _source(root):
    """只在本次新目錄建立三個固定 loose objects；不執行 Git、讀 config 或網路。"""
    root.mkdir(mode=0o700)
    (root / '.git').mkdir(mode=0o700)
    objects = root / '.git/objects'
    objects.mkdir(mode=0o700)
    def write(kind, content):
        raw = kind.encode() + b' ' + str(len(content)).encode() + b'\0' + content
        oid = hashlib.sha1(raw).hexdigest()
        bucket = objects / oid[:2]
        bucket.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(bucket / oid[2:], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(zlib.compress(raw))
        return oid
    blob = write('blob', ARTIFACT)
    tree = write('tree', b'100644 artifact.txt\0' + bytes.fromhex(blob))
    commit = write('commit', f'tree {tree}\nauthor Synthetic <pilot@example.invalid> 1 +0000\ncommitter Synthetic <pilot@example.invalid> 1 +0000\n\nSynthetic pilot\n'.encode())
    return GitRepositoryBinding(root, db.identity(root.stat()), db.identity((root / '.git').stat()),
                                db.identity(objects.stat()), REPOSITORY), ArtifactPermit(
                                    'synthetic-pilot-source', commit, 'artifact.txt', hashlib.sha256(ARTIFACT).hexdigest())


def _candidate(permit, now):
    value = {'revision': 1, 'created_at': now, 'retired_at': None, 'kind': 'fact',
             'body': 'Synthetic pilot widget label blue.', 'summary': 'Synthetic pilot widget',
             'cues': ['blue', 'widget'], 'applicability': {'repository_id': REPOSITORY,
                 'paths': ['artifact.txt'], 'conditions': ['Synthetic pilot only.']}, 'procedure': None,
             'provenance': [{'source_id': permit.source_id, 'kind': 'repo-artifact',
                 'reference': {'repository_id': REPOSITORY, 'path': permit.path},
                 'source_revision': permit.revision, 'source_digest': permit.sha256, 'attestation': None}],
             'validation': {'content_digest': '0' * 64, 'evidence_id': 'synthetic-pilot-source-acceptance',
                 'verified_at': now, 'verifier_fingerprint': c.digest({'fixture': 'synthetic-pilot/v1'}),
                 'eligibility': 'eligible', 'policy_fingerprint': c.digest(c.POLICY)}}
    value['validation']['content_digest'] = c.content_digest(value)
    return value


class _SeedPorts:
    """僅供建立本次固定 fixture，完成後不傳給 audit；不接受外部候選或路徑。"""
    def __init__(self, registry, clock, value, item_id):
        self.registry, self.clock, self.value = registry, clock, value
        self.item_id, self.closed = item_id, False
        self.runtime = db.runtime_facts()

    def qualify(self, binding, runtime, operation):
        return not self.closed and binding == self.registry.binding() and runtime == self.runtime and operation in {
            'initialize', 'authorize', 'add', 'readback'}

    def accept_initialization(self, binding):
        return not self.closed and binding == self.registry.binding()

    def accept_preview(self, binding, preview_bytes):
        preview = c.decode(preview_bytes)
        c.require(not self.closed and binding == self.registry.binding()
                  and preview['operation'] == 'add' and preview['item_id'] == self.item_id
                  and preview['candidate'] == self.value, 'read-unavailable')
        return AcceptedPreview(preview_bytes, c.canonical({
            'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
            'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': self.clock.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-pilot-seed-only'}))

    def observe_source(self, binding, version_bytes):
        c.require(not self.closed and binding == self.registry.binding()
                  and version_bytes == c.canonical(self.value), 'source-unavailable')
        return SourceObservation(c.digest(c.decode(binding.scope_bytes)), c.digest(self.value),
            c.digest(self.value['provenance']), c.digest(c.POLICY),
            self.value['validation']['verifier_fingerprint'], self.value['validation']['evidence_id'],
            self.clock.clock().utc_seconds, 'eligible', 'safe')

    def authorize_read(self, binding, purpose, operation_id):
        return not self.closed and binding == self.registry.binding() and purpose in {'preview', 'readback'}

    def external_copies(self, binding):
        return {'coverage': 'unknown', 'observed_at': self.clock.clock().utc_seconds, 'copies': []}

    def committed_work_bytes(self, binding):
        return 0

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        journal, temp, growth = sum(f['bytes'] for f in files) + 65536, 1048576, 262144
        return {'qualification_id': 'synthetic-pilot-not-production', 'file_snapshot_digest': c.digest(files),
                'journal_bound_bytes': journal, 'temp_bound_bytes': temp, 'growth_bound_bytes': growth,
                'required_work_bytes': (journal + temp + growth + 4095) // 4096 * 4096}


def _prepare(workspace):
    # workspace 僅由 main 的 mkdtemp 建立；沒有 CLI root/JSON/config loader。
    managed, authority = workspace / 'managed', workspace / 'authority'
    managed.mkdir(mode=0o700)
    authority.mkdir(mode=0o700)
    repository, permit = _source(workspace / 'source')
    clock = LocalClock()
    profile = dict(c.DEFAULT_PROFILE, data_limit_bytes=268435456, maintenance_max_bytes=335544320)
    scope = {'principal_id': str(uuid.uuid4()), 'root_id': str(uuid.uuid4()), 'repository_id': REPOSITORY,
             'schema_fingerprint': db.SCHEMA_FINGERPRINT, 'profile_digest': c.digest(profile),
             'policy_fingerprint': c.digest(c.POLICY)}
    binding = RootBinding(managed, db.identity(managed.stat()), None, None, c.canonical(scope),
                          c.canonical(profile), 'synthetic-pilot-fs-' + str(managed.stat().st_dev),
                          adapter_fingerprint(), frozenset({'initialize', 'content-write', 'readback'}))
    registry = SingleRootRegistry(binding)
    value = _candidate(permit, clock.clock().utc_seconds)
    item_id = str(uuid.uuid4())
    seed = _SeedPorts(registry, clock, value, item_id)
    core = GovernanceCore(LocalHost(registry, source=seed, authority=seed, qualification=seed, clock=clock), enabled=True)
    try:
        core.initialize()
        preview = core.preview('add', item_id, value)
        c.require(core.execute(core.authorize(preview))['result'] == 'applied', 'read-unavailable')
    finally:
        seed.closed = True
    binding = replace(registry.binding(), capabilities=frozenset({'audit'}))
    store = initialize_store(authority, binding)
    sample = clock.clock()
    expiry = sample.utc_seconds + 300
    acceptance = SourceAcceptance(c.digest(scope), c.digest(value), c.digest(value['provenance']),
        c.digest(c.POLICY), value['validation']['verifier_fingerprint'], value['validation']['evidence_id'],
        'eligible', 'safe', expiry)
    context = AuditPreflightContext(binding=binding, repository=repository, permits=(permit,),
        accepted_sources=(acceptance,), qualification=AuditQualification(db.binding_digest(binding),
            c.canonical(audit_environment(binding, db.runtime_facts())), 'synthetic-pilot-not-production', expiry),
        store=store,
        inspection=MetadataInspection(target_digest(binding), store, sample, expiry, 'synthetic-pilot-metadata'),
        clock=clock, source_revoked=lambda _: False, qualification_revoked=lambda _: False,
        authority_qualification_revoked=lambda _: False, inspection_revoked=lambda _: False)
    return replace(context, authority_qualification=AuthorityQualification(
        c.canonical(authority_environment(store, check=context.check_inspection)),
        'synthetic-pilot-authority-not-production', expiry))


def _confirm(stream, expected):
    # 有界讀取；EOF、額外字元或不完整行均取消。不是身分認證。
    return stream.readline(len(expected) + 2) == expected + '\n'


class _OutputUnavailable(Exception):
    """固定內部訊號；不得回顯底層 exception 或敏感內容。"""


def _emit(stream, event, **fields):
    try:
        stream.write(json.dumps({'event': event, 'synthetic_only': True,
                                'production_qualified': False, **fields}, ensure_ascii=False) + '\n')
        stream.flush()
    except Exception:
        raise _OutputUnavailable() from None


def main(argv=None, *, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description='固定 synthetic memory-audit pilot；不讀既有專案。')
    parser.add_argument('--create-synthetic', action='store_true', help='建立新的隔離 fixture；結束保留資料')
    args = parser.parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        return _run(args, stdin, stdout)
    except _OutputUnavailable:
        # 不再向故障通道寫入；CLI 的 buffered stdout 在 shutdown 也不可重試原 sink。
        if stdout is sys.stdout:
            try:
                target = stdout.fileno()
                descriptor = os.open(os.devnull, os.O_WRONLY)
                if descriptor != target:
                    try:
                        os.dup2(descriptor, target)
                    finally:
                        os.close(descriptor)
            except Exception:
                pass
        return 2


def _run(args, stdin, stdout):
    if not args.create_synthetic:
        _emit(stdout, 'disabled')
        return 0
    workspace = provider = None
    try:
        _emit(stdout, 'confirm-create', confirmation='CREATE SYNTHETIC',
              scope='建立一筆固定 synthetic memory、固定 Git objects 與獨立 authority store；不讀既有專案；結束不刪資料。')
        if not _confirm(stdin, 'CREATE SYNTHETIC'):
            _emit(stdout, 'cancelled', grant_issued=False)
            return 0
        # 不採納 caller root/TMPDIR；只在 OS 標準暫存根下建立新且不可預測的 0700 目錄。
        workspace = Path(tempfile.mkdtemp(prefix='memory-audit-pilot-', dir='/tmp')).resolve(strict=True)
        _emit(stdout, 'created', workspace=str(workspace), retained=True, fixture_writes=True)
        context = _prepare(workspace)
        _emit(stdout, 'target', managed=str(context.binding.root), authority=str(context.store.files.root),
              source=str(context.repository.root), scope=c.decode(context.binding.scope_bytes),
              target_digest=target_digest(context.binding),
              read_scope='一次 audit；managed metadata、摘要及固定來源；authority lifecycle bookkeeping 會寫入。')
        preflight = preflight_report(enabled=True, context=context)
        _emit(stdout, 'preflight', report=preflight)
        # 未有 request 與未讀內容本來就是 unknown/missing；其餘缺件不得進行。
        checks = preflight['checks']
        required = ('target', 'authority_binding', 'metadata_permission', 'source_acceptance',
                    'target_metadata', 'authority_metadata', 'authority_environment', 'managed_environment')
        c.require(all(checks.get(key, {}).get('status') == 'observed' for key in required), 'read-unavailable')
        token = 'AUDIT ' + target_digest(context.binding)
        _emit(stdout, 'confirm-audit', confirmation=token, expires_at=context.inspection.expires_at)
        if not _confirm(stdin, token):
            _emit(stdout, 'cancelled', grant_issued=False, retained=True)
            return 0
        # 等待期間 target 或資格可能漂移；重查 metadata，仍不查正文或核發權限。
        fresh = preflight_report(enabled=True, context=context)['checks']
        c.require(all(fresh.get(key, {}).get('status') == 'observed' for key in required), 'read-unavailable')
        context.authority_current()
        provider = AuditAuthorityProvider(context.store, context.binding, clock=context.clock)
        request = provider.accept()
        report = canary_report(enabled=True, context=context, provider=provider, request=request)
        _emit(stdout, 'report', report=report, fixture_writes=True, authority_bookkeeping=True)
        return 0 if report['status'] == 'complete' else 2
    except _OutputUnavailable:
        raise
    except KeyboardInterrupt:
        _emit(stdout, 'cancelled', retained=workspace is not None)
        return 130
    except Exception as exc:
        _emit(stdout, 'unavailable', reason=_reason(exc), retained=workspace is not None,
              recovery='重新執行並重新確認；不重試、不恢復舊 grant。')
        return 2
    finally:
        if provider is not None:
            provider.close()


if __name__ == '__main__':
    raise SystemExit(main())
