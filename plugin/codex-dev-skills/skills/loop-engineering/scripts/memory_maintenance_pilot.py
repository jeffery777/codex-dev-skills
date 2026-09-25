"""固定 synthetic 維護情境；無既有 root／grant 匯入或 production 註冊。"""
from __future__ import annotations

import argparse
from contextlib import closing
import errno
import sqlite3
import os
from pathlib import Path
import sys
import tempfile
import time
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from memory_governance_host import AcceptedPreview, RootBinding, SourceObservation
from memory_governance_local import LocalClock, LocalHost, SingleRootRegistry, RepositorySource
from memory_audit_source import PinnedGitReader
from memory_audit_pilot import ARTIFACT, REPOSITORY, _source, _candidate, _SeedPorts, _confirm, _emit, _OutputUnavailable

UPDATED_ARTIFACT = b'Synthetic pilot widget label green. No real project data.\n'


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


class _ContentPorts(_MaintenancePorts):
    """只接受兩份固定候選；read/audit 權限來自當次 fixture 接受，不是 production grant。"""
    operations = frozenset({'add', 'update', 'stop', 'resume'})

    def __init__(self, registry, clock, value, item_id, repository, permit, stdin, stdout,
                 updated, updated_repository, updated_permit):
        super().__init__(registry, clock, value, item_id, repository, permit, stdin, stdout)
        self.candidates = {'add': value, 'update': updated}
        self._versions = {c.canonical(value): (value, ARTIFACT),
                          c.canonical(updated): (updated, UPDATED_ARTIFACT)}
        updated_reader = PinnedGitReader(registry.binding(), updated_repository, (updated_permit,), check=self.check)
        self.readers = (self.reader, updated_reader)
        self._sources = {c.canonical(value): self.source,
                         c.canonical(updated): RepositorySource(updated_reader, self)}

    def qualify(self, binding, runtime, operation):
        return (not self.closed and binding == self.registry.binding() and runtime == self.runtime
                and operation in self.operations | {'authorize', 'audit', 'readback', 'recall'})

    def authorize_read(self, binding, purpose, operation_id):
        return not self.closed and binding == self.registry.binding() and purpose in {'audit', 'preview', 'readback', 'recall'}

    def observe_source(self, binding, version_bytes):
        self.check()
        c.require(version_bytes in self._sources, 'source-unavailable')
        return self._sources[version_bytes].observe_source(binding, version_bytes)

    def review_source(self, binding, version_bytes, artifacts):
        self.check()
        c.require(binding == self.registry.binding() and version_bytes in self._versions, 'source-unavailable')
        value, artifact = self._versions[version_bytes]
        c.require(len(artifacts) == 1 and artifacts[0].content == artifact, 'source-unavailable')
        return SourceObservation(c.digest(c.decode(binding.scope_bytes)), c.digest(value),
            c.digest(value['provenance']), c.digest(c.POLICY), value['validation']['verifier_fingerprint'],
            value['validation']['evidence_id'], self.clock.clock().utc_seconds, 'eligible', 'safe')

    def confirmation_change(self, binding, preview):
        before = None
        if preview['operation'] == 'update':
            observed = GovernanceCore(self.host(), enabled=True).recall(['widget'])
            c.require(observed['snapshot_digest'] == preview['before']['digest']
                      and observed['enumeration_complete'] and observed['source_rejected'] == 0
                      and len(observed['items']) == 1 and observed['items'][0]['item_id'] == self.item_id,
                      'preview-before-mismatch')
            before = observed['items'][0]['version']
            c.require(before == self.candidates['add'], 'preview-before-mismatch')
        return {'before': before, 'after': preview['candidate']}

    def accept_preview(self, binding, preview_bytes):
        self.check()
        preview = c.decode(preview_bytes)
        operation = preview['operation']
        c.require(binding == self.registry.binding() and preview['item_id'] == self.item_id
                  and operation in self.operations
                  and preview['candidate'] == self.candidates.get(operation), 'acceptance-unavailable')
        change = self.confirmation_change(binding, preview)
        token = operation.upper() + ' ' + c.digest(preview)
        _emit(self.stdout, 'confirm-operation', preview=preview, confirmation=token, change=change)
        if not _confirm(self.stdin, token):
            raise _Cancelled()
        self.check()
        return AcceptedPreview(preview_bytes, c.canonical({
            'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
            'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': self.clock.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-maintenance-explicit-input'}))


class _RestorePorts(_ContentPorts):
    """當次固定 fixture 的還原；歷史揭露只用於獨立 RESTORE preview。"""
    operations = _ContentPorts.operations | {'restore'}

    def prepare_restore(self):
        self.check()
        c.require('restore' not in self.candidates, 'restore-already-prepared')
        value = c.decode(c.canonical(self.candidates['add']))
        now = self.clock.clock().utc_seconds
        value.update(revision=3, created_at=now)
        value['validation'].update(verified_at=now, evidence_id='synthetic-restore-' + str(uuid.uuid4()))
        value['validation']['content_digest'] = c.content_digest(value)
        key = c.canonical(value)
        self.candidates['restore'] = value
        self._versions[key] = (value, ARTIFACT)
        self._sources[key] = self.source
        return value

    def confirmation_change(self, binding, preview):
        if preview['operation'] != 'restore':
            return super().confirmation_change(binding, preview)
        c.require(preview['target_revisions'] == [1], 'restore-source-unavailable')
        observed = GovernanceCore(self.host(), enabled=True).recall(['widget'])
        c.require(observed['snapshot_digest'] == preview['before']['digest']
                  and observed['enumeration_complete'] and observed['source_rejected'] == 0
                  and len(observed['items']) == 1 and observed['items'][0]['item_id'] == self.item_id
                  and observed['items'][0]['version'] == self.candidates['update'], 'preview-before-mismatch')
        scope, limits = c.decode(binding.scope_bytes), c.profile(c.decode(binding.profile_bytes))
        deadline = time.monotonic() + 10

        def check():
            self.check()
            c.require(binding == self.registry.binding()
                      and self.authorize_read(binding, 'preview', preview['operation_id']), 'read-unavailable')
            c.require(time.monotonic() < deadline, 'preview-timeout')

        # 僅從本 fixture 的可信 binding 讀取；沿用受保護的唯讀 connection 與 proof-chain 驗證。
        # 不把歷史放進 recall，也不在等待人類輸入期間持鎖。
        check()
        with db.locked(binding), closing(db.connect(binding, limits)) as connection:
            connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
            connection.execute('BEGIN')
            snapshot = db.snapshot(connection, scope, limits, check=check)
            c.require(snapshot.digest == preview['before']['digest']
                      and snapshot.epoch == preview['acceptance_epoch'], 'preview-before-mismatch')
            item = db.load_item(connection, self.item_id, scope, limits)
            c.require(item is not None and item['status'] == 'active' and item['current_revision'] == 2
                      and item['revision_high_water'] == 2
                      and [v['revision'] for v in item['versions']] == [1, 2], 'preview-before-mismatch')
            before, retained = item['versions'][-1], item['versions'][0]
            c.require(before == observed['items'][0]['version'], 'preview-before-mismatch')
            c.require(retained == dict(self.candidates['add'], retired_at=before['created_at']),
                      'preview-before-mismatch')
            c.restore_content(preview['candidate'], retained)
            check()
        return {'before': before, 'after': preview['candidate'], 'restore_source': retained,
                'snapshot_digest': snapshot.digest}


def _prepare(workspace, stdin, stdout, *, content=False, restore=False):
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
                          frozenset({'initialize', 'content-write', 'readback', 'recall'} | ({'audit'} if content else set())))
    registry = SingleRootRegistry(binding)
    value, item_id = _candidate(permit, clock.clock().utc_seconds), str(uuid.uuid4())
    seed = _SeedPorts(registry, clock, value, item_id)
    core = GovernanceCore(LocalHost(registry, source=seed, authority=seed, qualification=seed, clock=clock), enabled=True)
    try:
        core.initialize()
        if not content:
            preview = core.preview('add', item_id, value)
            c.require(core.execute(core.authorize(preview))['result'] == 'applied', 'state-unknown')
    finally:
        core.cancel()
        seed.closed = True
    if content:
        updated_repository, updated_permit = _source(workspace / 'source-update', artifact=UPDATED_ARTIFACT)
        updated = _candidate(updated_permit, clock.clock().utc_seconds)
        updated.update(revision=2, body='Synthetic pilot widget label green.',
                       summary='Synthetic pilot green widget', cues=['green', 'widget'])
        updated['validation']['content_digest'] = c.content_digest(updated)
        ports_type = _RestorePorts if restore else _ContentPorts
        return ports_type(registry, clock, value, item_id, repository, permit, stdin, stdout,
                          updated, updated_repository, updated_permit)
    return _MaintenancePorts(registry, clock, value, item_id, repository, permit, stdin, stdout)


def _verify_content(ports, fresh, result, operation, stdout):
    revision = {'add': 1, 'restore': 3}.get(operation, 2)
    before_revision = {'add': 0, 'update': 1, 'restore': 2, 'stop': 2, 'resume': 2}[operation]
    expected = ports.candidates[operation if operation in {'add', 'update', 'restore'} else 'update']
    c.require(result['result'] == 'applied' and result['proof']['before_revision'] == before_revision
              and result['proof']['after_revision'] == revision, 'state-unknown')
    if operation == 'restore':
        c.require(result['proof']['operation'] == 'restore'
                  and result['proof']['restore_source_revision'] == 1, 'state-unknown')
    counts = {}
    for cues in (['blue'], ['green'], ['widget'], ['blue', 'widget'], ['green', 'widget'], ['blue', 'green']):
        recall = fresh.recall(cues)
        count = int(operation != 'stop' and all(cue in expected['cues'] for cue in cues))
        c.require(recall['snapshot_digest'] == result['state_digest'] and recall['enumeration_complete']
                  and recall['source_rejected'] == 0 and len(recall['items']) == count
                  and all(item['item_id'] == ports.item_id and item['version'] == expected for item in recall['items']),
                  'state-unknown')
        counts['+'.join(cues)] = count
    with fresh.audit() as snapshot:
        page = snapshot.page()
        c.require(page['enumeration_complete'] and page['source_coverage'] == 'complete'
                  and page['snapshot_digest'] == result['state_digest'] and len(page['items']) == 1
                  and page['items'][0]['item_id'] == ports.item_id
                  and page['items'][0]['revision'] == page['items'][0]['retained_versions'] == revision
                  and page['items'][0]['status'] == ('stopped' if operation == 'stop' else 'active'), 'state-unknown')
        snapshot.validate_disclosure()
        _emit(stdout, 'audit', operation=operation, report=page)
    _emit(stdout, 'verified', operation=operation, report=result, recall_count=counts['widget'],
          recall_counts=counts, revision=revision, retained=True)


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
        content = args.scenario != 'stop-resume'
        restore = args.scenario == 'add-update-restore'
        _emit(stdout, 'confirm-create', confirmation='CREATE SYNTHETIC',
              scope=('建立空的隔離記憶與固定兩版來源；新增、修改、歷史還原各自確認，還原預覽揭露指定舊版全文；期間盤點及查詢，結束保留 fixture。'
                     if restore else '建立空的隔離記憶與固定兩版來源；新增、修改、停用、恢復各自確認，期間盤點及查詢；結束保留 fixture。'
                     if content else '建立固定來源與一筆 synthetic item；stop/resume 各自確認；結束保留 fixture。'))
        if not _confirm(stdin, 'CREATE SYNTHETIC'):
            _emit(stdout, 'cancelled', retained=False)
            return 0
        workspace = Path(tempfile.mkdtemp(prefix='memory-maintenance-pilot-', dir='/tmp')).resolve(strict=True)
        _emit(stdout, 'created', workspace=str(workspace), retained=True, fixture_writes=True)
        phase, attempted = 'preparation', True
        options = {'content': True, 'restore': True} if restore else {'content': True} if content else {}
        ports = _prepare(workspace, stdin, stdout, **options)
        attempted = False
        _emit(stdout, 'target', scope=c.decode(ports.registry.binding().scope_bytes), item_id=ports.item_id)
        operations = ('add', 'update', 'restore') if restore else ('add', 'update', 'stop', 'resume') if content else ('stop', 'resume')
        for operation in operations:
            phase = operation
            attempted = False
            core = GovernanceCore(ports.host(), enabled=True)
            candidate = ports.prepare_restore() if operation == 'restore' else ports.candidates.get(operation) if content else None
            preview = core.preview(operation, ports.item_id, candidate,
                                   **({'restore_revision': 1} if operation == 'restore' else {}))
            handle = core.authorize(preview)
            attempted = True
            result = core.execute(handle)
            _emit(stdout, 'readback', operation=operation, report=result)
            if result['result'] != 'applied':
                return 2
            # 新 core／新唯讀 connection 再核對 proof 與 current projection，從不重送 mutation。
            fresh = GovernanceCore(ports.host(), enabled=True)
            result = fresh.readback(preview['operation_id'], c.digest(preview))
            if content:
                _verify_content(ports, fresh, result, operation, stdout)
                continue
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
    parser = argparse.ArgumentParser(description='固定 synthetic memory-maintenance pilot')
    parser.add_argument('--create-synthetic', action='store_true')
    parser.add_argument('--scenario', choices=('stop-resume', 'add-update', 'add-update-restore'), default='stop-resume')
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
