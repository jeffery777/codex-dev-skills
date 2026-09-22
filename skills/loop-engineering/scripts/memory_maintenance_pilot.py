"""固定 synthetic stop/resume 操作入口；無既有 root／grant 匯入或 production 註冊。"""
from __future__ import annotations

import argparse
import errno
import sqlite3
import os
from pathlib import Path
import sys
import tempfile
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from memory_governance_host import AcceptedPreview, RootBinding, SourceObservation
from memory_governance_local import LocalClock, LocalHost, SingleRootRegistry, RepositorySource
from memory_audit_source import PinnedGitReader
from memory_audit_pilot import ARTIFACT, REPOSITORY, _source, _candidate, _SeedPorts, _confirm, _emit, _OutputUnavailable


class _Cancelled(Exception):
    pass


class _MaintenancePorts:
    """僅本次新建 fixture 的 synthetic TCB；不使用 audit provider 授予 mutation。"""
    def __init__(self, registry, clock, value, item_id, repository, permit, stdin, stdout):
        self.registry, self.clock, self.value, self.item_id = registry, clock, value, item_id
        self.stdin, self.stdout, self.closed = stdin, stdout, False
        self.runtime = db.runtime_facts()
        self.reader = PinnedGitReader(registry.binding(), repository, (permit,), check=self.check)
        self.source = RepositorySource(self.reader, self)

    def check(self):
        c.require(not self.closed, 'authority-closed')

    def qualify(self, binding, runtime, operation):
        return (not self.closed and binding == self.registry.binding() and runtime == self.runtime
                and operation in {'authorize', 'stop', 'resume', 'readback', 'recall'})

    def accept_initialization(self, binding):
        return False

    def accept_preview(self, binding, preview_bytes):
        self.check()
        preview = c.decode(preview_bytes)
        c.require(binding == self.registry.binding() and preview['operation'] in {'stop', 'resume'}
                  and preview['item_id'] == self.item_id and preview['candidate'] is None, 'acceptance-unavailable')
        token = preview['operation'].upper() + ' ' + c.digest(preview)
        _emit(self.stdout, 'confirm-operation', preview=preview, confirmation=token)
        if not _confirm(self.stdin, token):
            raise _Cancelled()
        # Core 在 port 返回後重验 TTL，execute 在持鎖後重验完整前態、來源及容量。
        self.check()
        return AcceptedPreview(preview_bytes, c.canonical({
            'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
            'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': self.clock.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-maintenance-explicit-input'}))

    def observe_source(self, binding, version_bytes):
        return self.source.observe_source(binding, version_bytes)

    def review_source(self, binding, version_bytes, artifacts):
        self.check()
        c.require(binding == self.registry.binding() and version_bytes == c.canonical(self.value)
                  and len(artifacts) == 1 and artifacts[0].content == ARTIFACT, 'source-unavailable')
        return SourceObservation(c.digest(c.decode(binding.scope_bytes)), c.digest(self.value),
            c.digest(self.value['provenance']), c.digest(c.POLICY),
            self.value['validation']['verifier_fingerprint'], self.value['validation']['evidence_id'],
            self.clock.clock().utc_seconds, 'eligible', 'safe')

    def authorize_read(self, binding, purpose, operation_id):
        return not self.closed and binding == self.registry.binding() and purpose in {'preview', 'readback', 'recall'}

    def external_copies(self, binding):
        self.check()
        return {'coverage': 'unknown', 'observed_at': self.clock.clock().utc_seconds, 'copies': []}

    def committed_work_bytes(self, binding):
        self.check()
        return 0

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        self.check()
        journal, temp, growth = sum(f['bytes'] for f in files) + 65536, 1048576, 262144
        return {'qualification_id': 'synthetic-maintenance-not-production', 'file_snapshot_digest': c.digest(files),
                'journal_bound_bytes': journal, 'temp_bound_bytes': temp, 'growth_bound_bytes': growth,
                'required_work_bytes': (journal + temp + growth + 4095) // 4096 * 4096}

    def host(self):
        return LocalHost(self.registry, source=self, authority=self, qualification=self, clock=self.clock)


def _prepare(workspace, stdin, stdout):
    managed = workspace / 'managed'
    managed.mkdir(mode=0o700)
    repository, permit = _source(workspace / 'source')
    clock = LocalClock()
    profile = dict(c.DEFAULT_PROFILE, data_limit_bytes=268435456, maintenance_max_bytes=335544320)
    scope = {'principal_id': str(uuid.uuid4()), 'root_id': str(uuid.uuid4()), 'repository_id': REPOSITORY,
             'schema_fingerprint': db.SCHEMA_FINGERPRINT, 'profile_digest': c.digest(profile),
             'policy_fingerprint': c.digest(c.POLICY)}
    binding = RootBinding(managed, db.identity(managed.stat()), None, None, c.canonical(scope),
                          c.canonical(profile), 'synthetic-maintenance-fs-' + str(managed.stat().st_dev),
                          c.digest({'fixture': 'synthetic-maintenance/v1'}),
                          frozenset({'initialize', 'content-write', 'readback', 'recall'}))
    registry = SingleRootRegistry(binding)
    value, item_id = _candidate(permit, clock.clock().utc_seconds), str(uuid.uuid4())
    seed = _SeedPorts(registry, clock, value, item_id)
    core = GovernanceCore(LocalHost(registry, source=seed, authority=seed, qualification=seed, clock=clock), enabled=True)
    try:
        core.initialize()
        preview = core.preview('add', item_id, value)
        c.require(core.execute(core.authorize(preview))['result'] == 'applied', 'state-unknown')
    finally:
        core.cancel()
        seed.closed = True
    return _MaintenancePorts(registry, clock, value, item_id, repository, permit, stdin, stdout)


def _cause(exc, kind):
    seen = set()
    while exc is not None and id(exc) not in seen:
        if isinstance(exc, kind):
            return exc
        seen.add(id(exc))
        exc = exc.__cause__
    return None


def _fault(exc):
    """只揭露受限原生分類；不輸出 exception text、檔名或任意 errorname。"""
    sql = _cause(exc, sqlite3.Error)
    if sql is not None:
        code = getattr(sql, 'sqlite_errorcode', None)
        primary = code & 255 if type(code) is int and 0 <= code <= 65535 else None
        names = {sqlite3.SQLITE_FULL: 'SQLITE_FULL', sqlite3.SQLITE_NOMEM: 'SQLITE_NOMEM',
                 sqlite3.SQLITE_CANTOPEN: 'SQLITE_CANTOPEN', sqlite3.SQLITE_IOERR: 'SQLITE_IOERR',
                 sqlite3.SQLITE_BUSY: 'SQLITE_BUSY', sqlite3.SQLITE_LOCKED: 'SQLITE_LOCKED'}
        return {'fault_class': 'sqlite-error', 'sqlite_code': primary,
                'sqlite_name': names.get(primary, 'SQLITE_OTHER')}
    os_error = _cause(exc, OSError)
    if os_error is not None:
        code = os_error.errno
        return {'fault_class': 'os-error',
                'errno': code if type(code) is int and 0 <= code <= 4096 else None,
                'os_name': {errno.ENOSPC: 'ENOSPC', errno.ENOMEM: 'ENOMEM'}.get(code, 'OS_OTHER')}
    return {'fault_class': 'memory-error' if _cause(exc, MemoryError) else 'contract-or-host-unavailable'}


def _run(args, stdin, stdout):
    if not args.create_synthetic:
        _emit(stdout, 'disabled')
        return 0
    workspace = ports = core = None
    attempted = False
    phase = 'create-confirmation'
    try:
        _emit(stdout, 'confirm-create', confirmation='CREATE SYNTHETIC',
              scope='建立固定來源與一筆 synthetic item；stop/resume 各自確認；結束保留 fixture。')
        if not _confirm(stdin, 'CREATE SYNTHETIC'):
            _emit(stdout, 'cancelled', retained=False)
            return 0
        workspace = Path(tempfile.mkdtemp(prefix='memory-maintenance-pilot-', dir='/tmp')).resolve(strict=True)
        _emit(stdout, 'created', workspace=str(workspace), retained=True, fixture_writes=True)
        phase, attempted = 'preparation', True
        ports = _prepare(workspace, stdin, stdout)
        attempted = False
        _emit(stdout, 'target', scope=c.decode(ports.registry.binding().scope_bytes), item_id=ports.item_id)
        for operation in ('stop', 'resume'):
            phase = operation
            attempted = False
            core = GovernanceCore(ports.host(), enabled=True)
            preview = core.preview(operation, ports.item_id)
            handle = core.authorize(preview)
            attempted = True
            result = core.execute(handle)
            _emit(stdout, 'readback', operation=operation, report=result)
            if result['result'] != 'applied':
                return 2
            # 新 core／新唯讀 connection 再核對 proof 與 current projection，從不重送 mutation。
            fresh = GovernanceCore(ports.host(), enabled=True)
            result = fresh.readback(preview['operation_id'], c.digest(preview))
            recall = fresh.recall(['widget'])
            c.require(result['result'] == 'applied' and recall['snapshot_digest'] == result['state_digest']
                      and len(recall['items']) == (0 if operation == 'stop' else 1)
                      and result['proof']['before_revision'] == result['proof']['after_revision'] == 1,
                      'state-unknown')
            _emit(stdout, 'verified', operation=operation, report=result, recall_count=len(recall['items']),
                  revision=1, retained=True)
        return 0
    except KeyboardInterrupt:
        _emit(stdout, 'interrupted', phase=phase, result='state-unknown' if attempted else 'not-attempted', retained=workspace is not None)
        return 130
    except Exception as exc:
        if _cause(exc, _OutputUnavailable):
            raise _OutputUnavailable() from None
        if _cause(exc, _Cancelled):
            _emit(stdout, 'cancelled', retained=workspace is not None, mutation_attempted=False)
            return 0
        _emit(stdout, 'unavailable', phase=phase, **_fault(exc), result='state-unknown' if attempted else 'not-attempted',
              retained=workspace is not None,
              recovery='保留 fixture；不重試或恢復 grant。可信 host 新讀回後，須重新預覽與接受新操作。CLI 不重開既有 root。')
        return 2
    finally:
        if core is not None:
            core.cancel()
        if ports is not None:
            ports.closed = True


def main(argv=None, *, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description='固定 synthetic memory-maintenance stop/resume pilot')
    parser.add_argument('--create-synthetic', action='store_true')
    args = parser.parse_args(argv)
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    try:
        return _run(args, stdin, stdout)
    except _OutputUnavailable:
        if stdout is sys.stdout:
            try:
                descriptor = os.open(os.devnull, os.O_WRONLY)
                try:
                    os.dup2(descriptor, stdout.fileno())
                finally:
                    os.close(descriptor)
            except Exception:
                pass
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
