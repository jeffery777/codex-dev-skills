"""Only new isolated synthetic Git/SQLite data; acceptance callbacks are test TCB."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
import uuid

from tests.test_memory_governance_local import local_fixture
from tests.test_memory_governance_core import c, db, GovernanceCore, ITEM
from memory_audit_adapter import SourceAcceptance, ReadGrant
from memory_audit_source import ArtifactPermit, GitRepositoryBinding
from memory_governance_host import AcceptedPreview, PRODUCTION_ADAPTERS
from memory_maintenance_authority import MaintenanceAuthorityProvider, MaintenanceRequest
from memory_maintenance_dispatch import (CAPABILITIES, MaintenanceDispatch, MaintenanceHost, MaintenanceHostFactory,
                                         MaintenanceQualification, maintenance_environment)
from memory_maintenance import maintenance_report, desktop_maintenance
from memory_maintenance_preflight import preflight_report, canary_report
import governancectl
import memory_governance_core as core_module
from memory_governance_local import LocalClock


def restart_probe(binding, request, output):
    provider = MaintenanceAuthorityProvider(binding=binding, clock=LocalClock(),
        accept_request=lambda *_: False, accept_preview=lambda *_: None, request_revoked=lambda _: False)
    try:
        provider.take(request)
    except c.ContractError as exc:
        output.put(str(exc))
    else:
        output.put('unexpected-authority')


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='maintenance-entry-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        managed, source = self.root / 'managed', self.root / 'source'
        managed.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(managed, git_root=source)
        GovernanceCore(self.ports.host, enabled=True).initialize()
        self.binding = replace(self.ports.registry.binding(), capabilities=CAPABILITIES)
        self.repo = GitRepositoryBinding(source, db.identity(source.stat()), db.identity((source / '.git').stat()),
                                        db.identity((source / '.git/objects').stat()), 'synthetic-repository')
        self.permit = ArtifactPermit('synthetic-source', self.ports.source_revision, 'artifact.txt',
                                     hashlib.sha256(local_fixture.ARTIFACT).hexdigest())
        self.revoked, self.source_revoked, self.q_revoked = set(), set(), set()
        self.acceptances, self.confirmations = [], []
        self.callback = lambda *_: None
        self.provider = self.provider_for()
        self.addCleanup(self.provider.close)

    def provider_for(self):
        return MaintenanceAuthorityProvider(binding=self.binding, clock=self.ports.clock_port,
            accept_request=lambda binding, data: binding == self.binding,
            accept_preview=self.confirm, request_revoked=self.revoked.__contains__)

    def confirm(self, binding, data):
        self.confirmations.append(data)
        preview = c.decode(data)
        # Real exclusive lock acquisition proves no DB lock survives while waiting at UI.
        with db.locked(binding, exclusive=True):
            pass
        self.callback(binding, preview)
        return AcceptedPreview(data, c.canonical({'contract_version': 'mg1-confirmation/v1',
            'scope': preview['scope'], 'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': self.ports.clock_port.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-accepted-not-production'}))

    def candidate(self, revision=1, cue='blue', *, restore=None):
        value = self.ports.candidate(revision, cue=cue)
        if restore:
            value = deepcopy(restore)
            value.update(revision=revision, created_at=self.ports.clock_port.clock().utc_seconds, retired_at=None)
            value['validation']['evidence_id'] = 'synthetic-new-restore-evidence'
            value['validation']['verified_at'] = value['created_at']
            value['validation']['content_digest'] = c.content_digest(value)
        acceptance = SourceAcceptance(c.digest(c.decode(self.binding.scope_bytes)), c.digest(value),
            c.digest(value['provenance']), c.digest(c.POLICY), value['validation']['verifier_fingerprint'],
            value['validation']['evidence_id'], 'eligible', 'safe', self.ports.clock_port.clock().utc_seconds + 300)
        self.acceptances = [entry for entry in self.acceptances if entry.version_digest != acceptance.version_digest]
        self.acceptances.append(acceptance)
        return value

    def dispatch(self, operation='add', candidate=None, *, revision=None, request=None, **changes):
        if request is None:
            request = self.provider.accept({'operation': operation, 'item_id': ITEM,
                                            'candidate': candidate, 'restore_revision': revision})
        q = MaintenanceQualification(db.binding_digest(self.binding), operation,
            c.canonical(maintenance_environment(self.binding, db.runtime_facts(), operation)),
            'synthetic-operation-qualification', self.ports.clock_port.clock().utc_seconds + 300)
        args = dict(binding=self.binding, repository=self.repo, permits=(self.permit,),
                    accepted_sources=tuple(self.acceptances), qualification=q, provider=self.provider,
                    source_revoked=self.source_revoked.__contains__, qualification_revoked=self.q_revoked.__contains__,
                    storage=self.ports)
        args.update(changes)
        return MaintenanceDispatch(MaintenanceHostFactory(**args), request)

    def run_entry(self, dispatch, **kwargs):
        result = maintenance_report(enabled=True, dispatch=dispatch, **kwargs)
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertFalse(result['production_qualified'])
        return result

    def state(self):
        with sqlite3.connect(self.binding.root / db.MAIN) as conn:
            return {table: conn.execute('SELECT * FROM ' + table).fetchall()
                    for table in ('items', 'versions', 'current_search', 'proofs')}

    def add(self):
        candidate = self.candidate()
        self.assertEqual('applied', self.run_entry(self.dispatch(candidate=candidate))['outcome'])
        return candidate

    def test_five_operations_same_entry_history_recall_proof_and_audit(self):
        old = self.candidate()
        steps = [('add', old, None), ('update', self.candidate(2, 'green'), None),
                 ('stop', None, None), ('resume', None, None), ('restore', self.candidate(3, restore=old), 1)]
        results = []
        for operation, candidate, revision in steps:
            dispatch = self.dispatch(operation, candidate, revision=revision)
            readers = []
            original = MaintenanceHost.fresh_reader
            def capture(host):
                result = original(host)
                readers.append(result)
                return result
            with mock.patch.object(MaintenanceHost, 'fresh_reader', capture):
                report = self.run_entry(dispatch)
            self.assertEqual(('complete', 'applied'), (report['status'], report['outcome']), report)
            self.assertEqual(operation, report['proof']['operation'])
            self.assertTrue(report['verification']['current_only_verified'])
            results.append(report)
            with GovernanceCore(readers[0], enabled=True).audit() as snapshot:
                page = snapshot.page()
            self.assertTrue(page['enumeration_complete'])
            self.assertEqual(report['proof']['after_digest'], page['snapshot_digest'])
            self.assertEqual(report['verification']['revision'], page['items'][0]['revision'])
            self.assertEqual(report['verification']['retained_versions'], page['items'][0]['retained_versions'])
            self.assertEqual(report['verification']['item_status'], page['items'][0]['status'])
            self.assertEqual('dispatch-consumed', self.run_entry(dispatch)['reason'])
        self.assertEqual([1, 2, 2, 2, 3], [r['verification']['revision'] for r in results])
        self.assertEqual([1, 2, 2, 2, 3], [r['verification']['retained_versions'] for r in results])
        state = self.state()
        self.assertEqual(5, len(state['proofs']))
        versions = [c.decode(row[-1]) for row in state['versions']]
        self.assertEqual(3, len(versions))
        self.assertEqual(old['body'], versions[-1]['body'])
        self.assertEqual(1, results[-1]['proof']['restore_source_revision'])
        self.assertEqual(5, len({c.digest(c.decode(data)) for data in self.confirmations}))
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_default_off_no_touch_and_runtime_unavailable(self):
        dispatch = self.dispatch(candidate=self.candidate())
        with mock.patch.object(dispatch, 'acquire', side_effect=AssertionError('touch')):
            self.assertEqual('disabled', maintenance_report(dispatch=dispatch)['status'])
            self.assertEqual('disabled', desktop_maintenance(dispatch=dispatch)['status'])
            self.assertEqual('disabled', preflight_report(factory=object())['status'])
            self.assertEqual('disabled', canary_report(dispatch=dispatch)['status'])
        self.assertFalse(dispatch._used)
        self.assertEqual('adapter-unavailable', desktop_maintenance(enabled=True)['reason'])
        for args in (['maintenance', '--root', '/tmp'], ['maintenance', '--confirmed=true'],
                     ['maintenance', '--adapter', 'test'], ['maintenance', '--operation', 'erase']):
            with mock.patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                governancectl.main(args)

    def test_cli_and_desktop_share_result_with_separate_dispatches(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = governancectl.main(['maintenance', '--enabled'], maintenance_dispatch=self.dispatch(candidate=self.candidate()))
        self.assertEqual(0, code)
        self.assertEqual('applied', json.loads(output.getvalue())['outcome'])
        result = desktop_maintenance(enabled=True, dispatch=self.dispatch('stop'))
        self.assertEqual('applied', result['outcome'])

    def test_request_identity_scope_operation_root_and_audit_grant_fail_closed(self):
        dispatch = self.dispatch(candidate=self.candidate())
        for wrong in (replace(dispatch.request), replace(dispatch.request, scope_digest='0' * 64),
                      replace(dispatch.request, principal_id=str(uuid.uuid4()))):
            result = self.run_entry(MaintenanceDispatch(dispatch.factory, wrong))
            self.assertEqual('unavailable', result['status'])
        self.assertEqual('applied', self.run_entry(dispatch)['outcome'])
        self.assertEqual('request-consumed-or-unrecognized', self.run_entry(MaintenanceDispatch(dispatch.factory, dispatch.request))['reason'])
        with self.assertRaises(c.ContractError):
            self.dispatch('stop', binding=replace(self.binding, root=self.root / 'other'))
        wrong_op = self.dispatch('stop')
        wrong_op.factory.qualification = replace(wrong_op.factory.qualification, operation='resume')
        self.assertEqual('qualification-unavailable', self.run_entry(wrong_op)['reason'])
        audit = ReadGrant(self.binding, dispatch.request.principal_id, str(uuid.uuid4()), self.ports.clock_port.clock(), 9999999999)
        with self.assertRaises(c.ContractError):
            MaintenanceDispatch(dispatch.factory, audit)

    def test_revocation_expiry_and_qualification_during_confirmation(self):
        for fault in ('revocation', 'expiry', 'qualification'):
            dispatch = self.dispatch(candidate=self.candidate())
            before = self.state()
            def callback(*_):
                if fault == 'revocation':
                    self.revoked.add(dispatch.request.request_id)
                elif fault == 'qualification':
                    self.q_revoked.add('synthetic-operation-qualification')
                else:
                    sample = self.ports.clock_port.clock()
                    self.ports.clock_port.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 301,
                                                                monotonic_ns=sample.monotonic_ns + 301_000_000_000)
            self.callback = callback
            original = self.ports.clock_port.clock
            report = self.run_entry(dispatch)
            self.ports.clock_port.clock = original
            self.assertEqual('not-applied', report['outcome'])
            self.assertFalse(report['mutation_attempted'])
            self.assertEqual(before, self.state())
            self.q_revoked.clear()

    def test_source_drift_and_state_drift_after_preview(self):
        self.add()
        update = self.candidate(2, 'green')
        dispatch = self.dispatch('update', update)
        def drift(*_):
            self.source_revoked.add(update['validation']['evidence_id'])
        self.callback = drift
        before = self.state()
        self.assertEqual('not-applied', self.run_entry(dispatch)['outcome'])
        self.assertEqual(before, self.state())
        self.source_revoked.clear()
        def state_drift(*_):
            self.callback = lambda *_: None
            self.assertEqual('applied', self.run_entry(self.dispatch('stop'))['outcome'])
        self.callback = state_drift
        result = self.run_entry(self.dispatch('update', update))
        self.assertEqual('unknown', result['outcome'])
        self.assertEqual(2, len(self.state()['proofs']))

    def test_stop_without_any_source_or_acceptance(self):
        self.add()
        dispatch = self.dispatch('stop', repository=None, permits=(), accepted_sources=())
        self.assertEqual('applied', self.run_entry(dispatch)['outcome'])

    def test_real_core_transaction_proof_commit_and_readback_faults(self):
        for stage, expected in (('before-transaction', 'not-applied'), ('after-item-write', 'not-applied'),
                                ('before-commit', 'not-applied'), ('after-commit', 'applied'),
                                ('before-readback', 'applied')):
            with self.subTest(stage=stage):
                fixture = EntryTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                dispatch = fixture.dispatch(candidate=fixture.candidate())
                def checkpoint(actual):
                    if actual == stage:
                        raise sqlite3.OperationalError('PRIVATE injected fault')
                with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                    report = fixture.run_entry(dispatch)
                self.assertEqual(expected, report['outcome'], report)
                self.assertEqual('dispatch-consumed', fixture.run_entry(dispatch)['reason'])

    def test_postcommit_new_reader_and_output_failures_never_replay(self):
        dispatch = self.dispatch(candidate=self.candidate())
        with mock.patch.object(GovernanceCore, 'readback', side_effect=OSError('PRIVATE')):
            result = self.run_entry(dispatch)
        self.assertEqual('unknown', result['outcome'])
        self.assertEqual(1, len(self.state()['proofs']))
        result = self.run_entry(self.dispatch('stop'), emit=lambda _: (_ for _ in ()).throw(BrokenPipeError('PRIVATE')))
        self.assertEqual(('output-unavailable', 'applied'), (result['status'], result['outcome']))
        self.assertEqual(2, len(self.state()['proofs']))

    def test_actual_proof_insert_and_commit_failure_with_new_connection_readback(self):
        original = db.connect
        for fault in ('proof', 'commit'):
            dispatch = self.dispatch(candidate=self.candidate())
            connections = []
            class Connection:
                def __init__(self, inner):
                    self.inner = inner
                def execute(self, sql, *args):
                    if fault == 'proof' and sql.startswith('INSERT INTO proofs'):
                        raise sqlite3.OperationalError('PRIVATE proof failure')
                    return self.inner.execute(sql, *args)
                def commit(self):
                    raise sqlite3.OperationalError('PRIVATE commit failure')
                def close(self):
                    return self.inner.close()
            def connect(*args, **kwargs):
                inner = original(*args, **kwargs)
                connections.append(inner)
                return Connection(inner) if kwargs.get('writer') else inner
            with mock.patch.object(db, 'connect', side_effect=connect):
                result = self.run_entry(dispatch)
            self.assertEqual('not-applied', result['outcome'], result)
            self.assertEqual(0, len(self.state()['proofs']))
            for connection in connections:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute('SELECT 1')

    def test_revoke_request_qualification_or_expire_grant_before_transaction_and_commit(self):
        for stage in ('before-transaction', 'after-item-write', 'before-commit'):
            for fault in ('request', 'qualification', 'short-grant', 'source'):
                with self.subTest(stage=stage, fault=fault):
                    fixture = EntryTests()
                    fixture.setUp()
                    self.addCleanup(fixture.doCleanups)
                    candidate = fixture.candidate()
                    request = fixture.provider.accept({'operation': 'add', 'item_id': ITEM,
                        'candidate': candidate, 'restore_revision': None}, lifetime_seconds=2)
                    dispatch = fixture.dispatch(candidate=candidate, request=request)
                    def checkpoint(actual):
                        if actual != stage:
                            return
                        if fault == 'request':
                            fixture.revoked.add(request.request_id)
                        elif fault == 'qualification':
                            fixture.q_revoked.add('synthetic-operation-qualification')
                        elif fault == 'source':
                            fixture.source_revoked.add(candidate['validation']['evidence_id'])
                        else:
                            sample = fixture.ports.clock_port.clock()
                            fixture.ports.clock_port.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 3,
                                monotonic_ns=sample.monotonic_ns + 3_000_000_000)
                    with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                        result = fixture.run_entry(dispatch)
                    # Source revocation alone keeps readback authority; grant/q revocation does not.
                    self.assertEqual('not-applied' if fault == 'source' else 'unknown', result['outcome'])
                    self.assertEqual(0, len(fixture.state()['proofs']))
                    self.assertEqual(0, len(fixture.state()['items']))

    def test_lock_contention_and_copied_core_handle(self):
        dispatch = self.dispatch(candidate=self.candidate())
        with db.locked(self.binding, exclusive=True):
            result = self.run_entry(dispatch)
        self.assertEqual('not-applied', result['outcome'])
        self.assertEqual(0, len(self.state()['proofs']))
        next_dispatch = self.dispatch(candidate=self.candidate())
        host = next_dispatch.acquire()
        core = GovernanceCore(host, enabled=True)
        preview = core.preview('add', ITEM, c.decode(next_dispatch.request.intent_bytes)['candidate'])
        handle = core.authorize(preview)
        with self.assertRaises(c.ContractError):
            core.execute(replace(handle))
        self.assertEqual('applied', core.execute(handle)['result'])
        with self.assertRaises(c.ContractError):
            core.execute(handle)

    def test_preview_bytes_digest_substitution_never_authorizes(self):
        dispatch = self.dispatch(candidate=self.candidate())
        original = self.provider.accept_preview
        def tamper(binding, data):
            accepted = original(binding, data)
            doc = c.decode(accepted.confirmation_bytes)
            doc['preview_digest'] = '0' * 64
            return replace(accepted, confirmation_bytes=c.canonical(doc))
        self.provider.accept_preview = tamper
        self.assertEqual('not-applied', self.run_entry(dispatch)['outcome'])
        self.assertEqual(0, len(self.state()['proofs']))

    def test_concurrent_dispatch_and_provider_take(self):
        dispatch = self.dispatch(candidate=self.candidate())
        entered, release = threading.Event(), threading.Event()
        def wait(*_):
            entered.set()
            self.assertTrue(release.wait(10))
        self.callback = wait
        results = []
        worker = threading.Thread(target=lambda: results.append(self.run_entry(dispatch)))
        worker.start()
        try:
            self.assertTrue(entered.wait(10))
            self.assertEqual('dispatch-consumed', self.run_entry(dispatch)['reason'])
            self.assertEqual('request-consumed-or-unrecognized', self.run_entry(MaintenanceDispatch(dispatch.factory, dispatch.request))['reason'])
        finally:
            release.set()
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual('applied', results[0]['outcome'])
        self.assertEqual(1, len(self.state()['proofs']))

    def test_new_provider_serialization_and_real_fork_cannot_restore_request(self):
        dispatch = self.dispatch(candidate=self.candidate())
        fresh = self.provider_for()
        self.addCleanup(fresh.close)
        with self.assertRaises(c.ContractError):
            fresh.take(dispatch.request)
        # Child process inherits actual objects but PID guard must refuse before storage.
        pid = os.fork()
        if pid == 0:
            result = maintenance_report(enabled=True, dispatch=dispatch)
            os._exit(0 if result['reason'] == 'process-changed' and not result['mutation_attempted'] else 1)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(0, os.waitstatus_to_exitcode(status))
        self.assertEqual(0, len(self.state()['proofs']))
        context = multiprocessing.get_context('spawn')
        output = context.Queue()
        child = context.Process(target=restart_probe, args=(self.binding, dispatch.request, output))
        child.start()
        child.join(15)
        self.assertFalse(child.is_alive())
        self.assertEqual(0, child.exitcode)
        self.assertEqual('request-consumed-or-unrecognized', output.get(timeout=5))
        output.close()
        self.assertEqual('applied', self.run_entry(dispatch)['outcome'])

    def test_preflight_advisory_no_consumption_and_isolated_canary(self):
        dispatch = self.dispatch(candidate=self.candidate())
        before = self.state()
        result = preflight_report(enabled=True, factory=dispatch.factory, request=dispatch.request,
                                  inspection_allowed=lambda *_: True)
        self.assertEqual('advisory-pass', result['status'], result)
        self.assertFalse(result['operation_authorized'])
        self.assertFalse(dispatch._used)
        self.assertEqual(before, self.state())
        result = canary_report(enabled=True, dispatch=dispatch, isolation_accepted=lambda value: value is dispatch)
        self.assertEqual('canary-pass', result['status'], result)
        self.assertFalse(result['production_qualified'])

    def test_preflight_missing_storage_and_wrong_source_acceptance(self):
        for missing in ('storage', 'source'):
            changes = {'storage': None} if missing == 'storage' else {'accepted_sources': ()}
            dispatch = self.dispatch(candidate=self.candidate(), **changes)
            result = preflight_report(enabled=True, factory=dispatch.factory, request=dispatch.request,
                                      inspection_allowed=lambda *_: True)
            expected = 'storage-port-unavailable' if missing == 'storage' else 'source-unavailable'
            self.assertEqual('unavailable', result['status'])
            self.assertIn(expected, [row.get('reason') for row in result['checks']])
            self.assertFalse(dispatch._used)
            if missing == 'storage':
                with mock.patch.object(db, 'connect', side_effect=AssertionError('must not open DB')):
                    self.assertEqual(expected, self.run_entry(dispatch)['reason'])


if __name__ == '__main__':
    unittest.main()
