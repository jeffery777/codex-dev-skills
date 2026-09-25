"""固定 add/update 入口的授權、版本一致性與失敗恢復驗收。"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import errno
import io
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest import mock

from tests import test_memory_maintenance_pilot as maintenance
from tests.test_memory_maintenance_pilot import Interaction, p, core_module, PRODUCTION_ADAPTERS


class ContentTests(unittest.TestCase):
    setUp = maintenance.MaintenanceTests.setUp
    state = maintenance.MaintenanceTests.state

    def prepare(self, stream=None):
        return maintenance.MaintenanceTests.prepare(self, stream, content=True)

    def run_pilot(self, stream=None):
        return maintenance.MaintenanceTests.run_pilot(self, stream, content=True)

    def apply(self, ports, operation):
        core = p.GovernanceCore(ports.host(), enabled=True)
        preview = core.preview(operation, ports.item_id, ports.candidates.get(operation))
        result = core.execute(core.authorize(preview))
        self.assertEqual('applied', result['result'])
        return preview, result

    def versions(self, ports):
        return [p.c.decode(row[2]) for row in sorted(self.state(ports)['versions'], key=lambda row: row[1])]

    def test_default_off_and_no_arbitrary_input(self):
        with mock.patch.object(p.db, 'runtime_facts', side_effect=AssertionError('probe')), \
             mock.patch.object(p, '_prepare', side_effect=AssertionError('prepare')), \
             mock.patch.object(p.tempfile, 'mkdtemp', side_effect=AssertionError('create')):
            stream = Interaction(answer=lambda _: self.fail('prompt'))
            self.assertEqual(0, p.main(['--scenario', 'add-update'], stdin=stream, stdout=stream))
            self.assertEqual(['disabled'], [e['event'] for e in stream.events])
            for args in (['--scenario', 'restore'], ['--candidate', '{}'], ['--source', '/PRIVATE']):
                with mock.patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                    p.main(args, stdin=stream, stdout=stream)
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_complete_full_previews_current_only_history_and_audit(self):
        code, stream = self.run_pilot()
        self.assertEqual(0, code, stream.getvalue())
        confirmations = [e for e in stream.events if e['event'] == 'confirm-operation']
        self.assertEqual(['add', 'update', 'stop', 'resume'], [e['preview']['operation'] for e in confirmations])
        self.assertEqual(4, len({e['confirmation'] for e in confirmations}))
        first, second = confirmations[:2]
        self.assertIsNone(first['change']['before'])
        self.assertEqual(first['preview']['candidate'], second['change']['before'])
        self.assertEqual(second['preview']['candidate'], second['change']['after'])
        self.assertNotEqual(first['change']['after']['provenance'], second['change']['after']['provenance'])
        verified = [e for e in stream.events if e['event'] == 'verified']
        self.assertEqual([1, 2, 2, 2], [e['revision'] for e in verified])
        self.assertEqual([1, 1, 0, 1], [e['recall_count'] for e in verified])
        self.assertEqual([1, 0, 0, 0], [e['recall_counts']['blue+widget'] for e in verified])
        self.assertEqual([0, 1, 0, 1], [e['recall_counts']['green+widget'] for e in verified])
        self.assertTrue(all(e['recall_counts']['blue+green'] == 0 for e in verified))
        audits = [e['report'] for e in stream.events if e['event'] == 'audit']
        self.assertEqual([1, 2, 2, 2], [e['items'][0]['retained_versions'] for e in audits])
        root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
        with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
            versions = [p.c.decode(row[0]) for row in conn.execute('SELECT document FROM versions ORDER BY revision')]
            proofs = [p.c.decode(row[0]) for row in conn.execute('SELECT document FROM proofs ORDER BY sequence')]
        retired = deepcopy(first['change']['after'])
        retired['retired_at'] = second['change']['after']['created_at']
        self.assertEqual([retired, second['change']['after']], versions)
        self.assertEqual([(0, 1), (1, 2), (2, 2), (2, 2)],
                         [(e['before_revision'], e['after_revision']) for e in proofs])

    def test_cancel_each_operation_retains_only_confirmed_writes(self):
        for index, operation in enumerate(('add', 'update', 'stop', 'resume')):
            with self.subTest(operation=operation):
                stream = Interaction(answer=lambda e: 'no\n' if e.get('preview', {}).get('operation') == operation
                                     else e['confirmation'] + '\n')
                code, stream = self.run_pilot(stream)
                self.assertEqual(0, code)
                self.assertEqual('cancelled', stream.events[-1]['event'])
                root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
                with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
                    self.assertEqual(index, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
                    self.assertEqual(min(index, 2), conn.execute('SELECT count(*) FROM versions').fetchone()[0])
                    self.assertEqual(min(index, 1), conn.execute('SELECT count(*) FROM items').fetchone()[0])

    def test_update_display_bound_to_real_snapshot_and_wait_drift(self):
        for timing in ('before-display', 'during-wait'):
            ports, core, stream = self.prepare()
            self.apply(ports, 'add')
            preview = core.preview('update', ports.item_id, ports.candidates['update'])
            if timing == 'before-display':
                self.apply(ports, 'stop')
                before = self.state(ports)
                with self.assertRaises(p.c.ContractError):
                    core.authorize(preview)
                self.assertEqual(['add', 'stop'], [e['preview']['operation'] for e in stream.events])
            else:
                def answer(event):
                    if event['preview']['operation'] == 'update':
                        self.apply(ports, 'stop')
                    return event['confirmation'] + '\n'
                stream.answer = answer
                handle = core.authorize(preview)
                before = self.state(ports)
                with self.assertRaises(p.c.ContractError):
                    core.execute(handle)
            self.assertEqual(before, self.state(ports))

    def test_candidates_cannot_borrow_unrelated_source(self):
        for operation in ('add', 'update'):
            ports, core, _ = self.prepare()
            if operation == 'update':
                self.apply(ports, 'add')
            before = self.state(ports)
            value = deepcopy(ports.candidates[operation])
            value['body'] = 'Unsubstantiated synthetic fact.'
            value['validation']['content_digest'] = p.c.content_digest(value)
            with self.assertRaises(p.c.ContractError):
                core.preview(operation, ports.item_id, value)
            self.assertEqual(before, self.state(ports))

    def test_update_expiry_source_root_and_lock_drift_consume_or_deny(self):
        for fault in ('expiry', 'source', 'root', 'lock'):
            ports, core, stream = self.prepare()
            self.apply(ports, 'add')
            before = self.state(ports)
            preview = core.preview('update', ports.item_id, ports.candidates['update'])
            if fault == 'expiry':
                def callback(event):
                    sample = ports.clock.clock()
                    ports.clock.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 301,
                                                       monotonic_ns=sample.monotonic_ns + 301000000000)
                stream.callback = callback
                with self.assertRaises(p.c.ContractError):
                    core.authorize(preview)
            else:
                handle = core.authorize(preview)
                if fault == 'source':
                    blob = next((ports.readers[1].repository.root / '.git/objects').glob('*/*'))
                    blob.write_bytes(b'bad object')
                    with self.assertRaises(p.c.ContractError):
                        core.execute(handle)
                elif fault == 'root':
                    binding = ports.registry.binding()
                    ports.registry._binding = replace(binding, directory_identity=(0, 0))
                    with self.assertRaises(p.c.ContractError):
                        core.execute(handle)
                    ports.registry._binding = binding
                else:
                    with p.db.locked(ports.registry.binding(), exclusive=True), self.assertRaises(p.c.ContractError):
                        core.execute(handle)
                with self.assertRaisesRegex(p.c.ContractError, 'handle-unrecognized-or-consumed'):
                    core.execute(handle)
            self.assertEqual(before, self.state(ports))

    def test_add_update_transaction_faults_fresh_readback_and_no_replay(self):
        for operation in ('add', 'update'):
            for stage, expected in (('after-item-write', 'not-applied'), ('before-commit', 'not-applied'), ('after-commit', 'applied')):
                for failure in (OSError(errno.ENOSPC, 'PRIVATE'), sqlite3.OperationalError('PRIVATE'), MemoryError('PRIVATE')):
                    with self.subTest(operation=operation, stage=stage, failure=type(failure).__name__):
                        ports, core, _ = self.prepare()
                        if operation == 'update':
                            self.apply(ports, 'add')
                        before = self.state(ports)
                        preview = core.preview(operation, ports.item_id, ports.candidates[operation])
                        handle = core.authorize(preview)
                        def checkpoint(actual):
                            if actual == stage:
                                raise failure
                        with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                            if isinstance(failure, MemoryError):
                                with self.assertRaises(MemoryError):
                                    core.execute(handle)
                            else:
                                self.assertEqual(expected, core.execute(handle)['result'])
                        with self.assertRaises(p.c.ContractError):
                            core.execute(handle)
                        fresh = p.GovernanceCore(ports.host(), enabled=True)
                        self.assertEqual(expected, fresh.readback(preview['operation_id'], p.c.digest(preview), preview=preview)['result'])
                        if expected == 'not-applied':
                            self.assertEqual(before, self.state(ports))
                            new, _ = self.apply(ports, operation)
                            self.assertNotEqual(preview['operation_id'], new['operation_id'])
                        self.assertEqual(1 if operation == 'add' else 2, len(self.versions(ports)))

    def test_update_proof_insert_failure_rolls_back_entire_version_transition(self):
        ports, core, _ = self.prepare()
        self.apply(ports, 'add')
        before = self.state(ports)
        preview = core.preview('update', ports.item_id, ports.candidates['update'])
        handle = core.authorize(preview)
        original = p.db.connect
        class Failure:
            def __init__(self, connection):
                self.connection = connection
            def __getattr__(self, name):
                return getattr(self.connection, name)
            def execute(self, sql, parameters=()):
                if sql.startswith('INSERT INTO proofs'):
                    raise sqlite3.OperationalError('PRIVATE')
                return self.connection.execute(sql, parameters)
        def connect(*args, **kwargs):
            connection = original(*args, **kwargs)
            return Failure(connection) if kwargs.get('writer') else connection
        with mock.patch.object(p.db, 'connect', side_effect=connect):
            self.assertEqual('not-applied', core.execute(handle)['result'])
        self.assertEqual(before, self.state(ports))

    def test_output_loss_before_add_and_after_update_stops_without_retry(self):
        for event, operation, proof_count in (('confirm-operation', 'add', 0), ('readback', 'update', 2)):
            def fail(value):
                if value['event'] == event and value.get('operation', value.get('preview', {}).get('operation')) == operation:
                    raise OSError(errno.ENOSPC, 'PRIVATE')
            code, stream = self.run_pilot(Interaction(callback=fail))
            self.assertEqual(2, code)
            self.assertNotIn('PRIVATE', stream.getvalue())
            root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
            with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
                self.assertEqual(proof_count, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
                self.assertEqual(proof_count, conn.execute('SELECT count(*) FROM versions').fetchone()[0])

    def test_postupdate_readback_audit_or_interrupt_failure_remains_unknown(self):
        for fault in ('readback', 'audit', 'interrupt'):
            ports, _, stream = self.prepare()
            original = p.GovernanceCore.readback
            original_audit = p.GovernanceCore.audit
            def readback(core, *args, **kwargs):
                if fault == 'readback' and len(self.state(ports)['proofs']) == 2:
                    raise p.c.ContractError('state-unknown')
                return original(core, *args, **kwargs)
            def audit(core):
                if fault == 'audit' and len(self.state(ports)['proofs']) == 2:
                    raise p.c.ContractError('authority-unavailable')
                return original_audit(core)
            def checkpoint(stage):
                if fault == 'interrupt' and stage == 'after-commit' and len(self.state(ports)['proofs']) == 2:
                    raise KeyboardInterrupt()
            with mock.patch.object(p, '_prepare', return_value=ports), \
                 mock.patch.object(p.GovernanceCore, 'readback', readback), \
                 mock.patch.object(p.GovernanceCore, 'audit', audit), \
                 mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                code, stream = self.run_pilot(stream)
            self.assertEqual(130 if fault == 'interrupt' else 2, code)
            self.assertEqual('update', stream.events[-1]['phase'])
            self.assertEqual('state-unknown', stream.events[-1]['result'])
            self.assertEqual(2, len(self.state(ports)['proofs']))
            self.assertEqual(2, len(self.versions(ports)))
            self.assertTrue(ports.closed)
            self.assertEqual(['add'], [e['operation'] for e in stream.events if e['event'] == 'verified'])

    @unittest.skipUnless(hasattr(os, 'fork'), 'POSIX process fixture')
    def test_process_exit_after_update_commit_fresh_readback_no_grant_revival(self):
        ports, _, _ = self.prepare()
        self.apply(ports, 'add')
        tuple_path = self.parent / 'update-operation.json'
        pid = os.fork()
        if pid == 0:
            try:
                ports.clock = p.LocalClock()
                core = p.GovernanceCore(ports.host(), enabled=True)
                preview = core.preview('update', ports.item_id, ports.candidates['update'])
                tuple_path.write_text(json.dumps({'id': preview['operation_id'], 'digest': p.c.digest(preview)}))
                handle = core.authorize(preview)
                def checkpoint(stage):
                    if stage == 'after-commit':
                        os._exit(77)
                core_module._checkpoint = checkpoint
                core.execute(handle)
            except BaseException:
                os._exit(78)
            os._exit(79)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(77, os.waitstatus_to_exitcode(status))
        observed = json.loads(tuple_path.read_text())
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        report = fresh.readback(observed['id'], observed['digest'])
        self.assertEqual('applied', report['result'])
        self.assertEqual([], fresh.recall(['blue'])['items'])
        self.assertEqual(ports.candidates['update'], fresh.recall(['green', 'widget'])['items'][0]['version'])
        with self.assertRaises(p.c.ContractError):
            fresh.execute(core_module.ExecutionHandle(observed['id']))
        self.assertEqual(2, len(self.state(ports)['proofs']))
