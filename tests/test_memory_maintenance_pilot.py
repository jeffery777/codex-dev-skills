from __future__ import annotations

from dataclasses import replace
import errno
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from tests.test_memory_audit_pilot import Interaction
import memory_maintenance_pilot as p
import memory_governance_core as core_module
from memory_governance_host import PRODUCTION_ADAPTERS


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='maintenance-test-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()

    def prepare(self, stream=None):
        stream = stream or Interaction()
        root = Path(tempfile.mkdtemp(dir=self.parent))
        ports = p._prepare(root, stream, stream)
        return ports, p.GovernanceCore(ports.host(), enabled=True), stream

    def run_pilot(self, stream=None):
        stream = stream or Interaction()
        create = tempfile.mkdtemp
        def create_here(**kwargs):
            self.assertEqual('/tmp', kwargs['dir'])
            return create(prefix=kwargs['prefix'], dir=self.parent)
        with mock.patch.object(p.tempfile, 'mkdtemp', side_effect=create_here):
            code = p.main(['--create-synthetic'], stdin=stream, stdout=stream)
        return code, stream

    def state(self, ports):
        binding = ports.registry.binding()
        with sqlite3.connect(binding.root / p.db.MAIN) as conn:
            return {table: conn.execute('SELECT * FROM ' + table).fetchall()
                    for table in ('items', 'versions', 'current_search', 'proofs')}

    def test_disabled_and_no_import_surface(self):
        with mock.patch.object(p, '_prepare', side_effect=AssertionError()), mock.patch.object(p.tempfile, 'mkdtemp', side_effect=AssertionError()):
            output = io.StringIO()
            self.assertEqual(0, p.main([], stdin=None, stdout=output))
            self.assertEqual('disabled', json.loads(output.getvalue())['event'])
            for arg in ('--root', '--json', '--resume', '--yes', '--erase', '--prune', '--compact'):
                with mock.patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                    p.main([arg], stdout=output)
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_complete_preserves_revision_and_requires_separate_acceptance(self):
        code, stream = self.run_pilot()
        self.assertEqual(0, code, stream.getvalue())
        confirmations = [e for e in stream.events if e['event'] == 'confirm-operation']
        self.assertEqual(['stop', 'resume'], [e['preview']['operation'] for e in confirmations])
        self.assertNotEqual(confirmations[0]['confirmation'], confirmations[1]['confirmation'])
        verified = [e for e in stream.events if e['event'] == 'verified']
        self.assertEqual([0, 1], [e['recall_count'] for e in verified])
        self.assertTrue(all(e['revision'] == 1 and e['report']['result'] == 'applied' for e in verified))
        root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
        with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
            self.assertEqual(1, conn.execute('SELECT count(*) FROM versions').fetchone()[0])
            self.assertEqual(3, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])

    def test_cancel_each_confirmation(self):
        for at in ('confirm-create', 'stop', 'resume'):
            def answer(e):
                return 'no\n' if e['event'] == at or e.get('preview', {}).get('operation') == at else e['confirmation'] + '\n'
            code, stream = self.run_pilot(Interaction(answer=answer))
            self.assertEqual(0, code)
            self.assertEqual('cancelled', stream.events[-1]['event'])
            self.assertEqual(0 if at != 'resume' else 1, len([e for e in stream.events if e['event'] == 'verified']))

    def test_expiry_after_wait_never_writes(self):
        ports, core, stream = self.prepare()
        before = self.state(ports)
        original = ports.clock.clock
        def callback(e):
            if e['event'] == 'confirm-operation':
                sample = original()
                ports.clock.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 301,
                                                   monotonic_ns=sample.monotonic_ns + 301000000000)
        stream.callback = callback
        preview = core.preview('stop', ports.item_id)
        with self.assertRaises(p.c.ContractError):
            core.authorize(preview)
        self.assertEqual(before, self.state(ports))

    def test_source_drift_after_resume_acceptance(self):
        ports, core, stream = self.prepare()
        stop = core.preview('stop', ports.item_id)
        self.assertEqual('applied', core.execute(core.authorize(stop))['result'])
        before = self.state(ports)
        preview = core.preview('resume', ports.item_id)
        handle = core.authorize(preview)
        objects = ports.reader.repository.root / '.git/objects'
        blob = next(path for path in objects.glob('*/*') if path.is_file())
        blob.write_bytes(b'bad object')
        with self.assertRaises(p.c.ContractError):
            core.execute(handle)
        self.assertEqual(before, self.state(ports))
        self.assertEqual([], p.GovernanceCore(ports.host(), enabled=True).recall(['widget'])['items'])

    def test_root_drift_and_lock_conflict_consume_handle(self):
        for fault in ('root', 'lock'):
            ports, core, _ = self.prepare()
            preview = core.preview('stop', ports.item_id)
            handle = core.authorize(preview)
            before = self.state(ports)
            if fault == 'root':
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

    def test_state_drift_is_not_replayed(self):
        ports, core, _ = self.prepare()
        preview = core.preview('stop', ports.item_id)
        handle = core.authorize(preview)
        other = p.GovernanceCore(ports.host(), enabled=True)
        other_preview = other.preview('stop', ports.item_id)
        self.assertEqual('applied', other.execute(other.authorize(other_preview))['result'])
        before = self.state(ports)
        with self.assertRaises(p.c.ContractError):
            core.execute(handle)
        self.assertEqual(before, self.state(ports))

    def test_transaction_faults_and_new_acceptance(self):
        for stage, expected in (('after-item-write', 'not-applied'), ('before-commit', 'not-applied'), ('after-commit', 'applied')):
            for failure in (OSError(errno.ENOSPC, 'PRIVATE'), sqlite3.OperationalError('PRIVATE SQLITE_FULL'), MemoryError('PRIVATE')):
                ports, core, _ = self.prepare()
                preview = core.preview('stop', ports.item_id)
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
                observed = fresh.readback(preview['operation_id'], p.c.digest(preview), preview=preview)
                self.assertEqual(expected, observed['result'])
                new = fresh.preview('resume' if expected == 'applied' else 'stop', ports.item_id)
                self.assertNotEqual(preview['operation_id'], new['operation_id'])
                self.assertEqual('applied', fresh.execute(fresh.authorize(new))['result'])

    def test_unknown_readback_never_retries(self):
        ports, core, _ = self.prepare()
        preview = core.preview('stop', ports.item_id)
        handle = core.authorize(preview)
        def checkpoint(stage):
            if stage == 'before-readback':
                raise OSError(errno.ENOSPC, 'PRIVATE')
        with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint), self.assertRaisesRegex(p.c.ContractError, 'state-unknown'):
            core.execute(handle)
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        self.assertEqual('applied', fresh.readback(preview['operation_id'], p.c.digest(preview))['result'])
        self.assertEqual(2, len(self.state(ports)['proofs']))

    def test_output_failure_before_confirmation_does_not_mutate(self):
        def fail(e):
            if e['event'] == 'confirm-operation':
                raise OSError(errno.ENOSPC, 'PRIVATE')
        code, stream = self.run_pilot(Interaction(callback=fail))
        self.assertEqual(2, code)
        self.assertEqual('confirm-operation', stream.events[-1]['event'])
        self.assertNotIn('PRIVATE', stream.getvalue())
        root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
        with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
            self.assertEqual(1, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])

    def test_output_loss_after_commit_retains_proof_and_stops(self):
        def fail(e):
            if e['event'] == 'readback':
                raise OSError(errno.ENOSPC, 'PRIVATE')
        code, stream = self.run_pilot(Interaction(callback=fail))
        self.assertEqual(2, code)
        root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
        with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
            self.assertEqual(2, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
            self.assertEqual(0, conn.execute('SELECT count(*) FROM current_search').fetchone()[0])

    def test_interrupt_after_commit_reports_unknown(self):
        original = p._prepare
        def prepare(*args):
            ports = original(*args)
            def checkpoint(stage):
                if stage == 'after-commit':
                    raise KeyboardInterrupt()
            patcher = mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint)
            patcher.start()
            self.addCleanup(patcher.stop)
            return ports
        with mock.patch.object(p, '_prepare', side_effect=prepare):
            code, stream = self.run_pilot()
        self.assertEqual(130, code)
        self.assertEqual('state-unknown', stream.events[-1]['result'])

    @unittest.skipUnless(hasattr(os, 'fork'), 'POSIX process fixture')
    def test_process_exit_after_commit_fresh_readback_no_grant_revival(self):
        ports, _, _ = self.prepare()
        tuple_path = self.parent / 'operation.json'
        pid = os.fork()
        if pid == 0:
            try:
                ports.clock = p.LocalClock()
                core = p.GovernanceCore(ports.host(), enabled=True)
                preview = core.preview('stop', ports.item_id)
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
        observation = json.loads(tuple_path.read_text())
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        report = fresh.readback(observation['id'], observation['digest'])
        self.assertEqual('applied', report['result'])
        self.assertEqual([], fresh.recall(['widget'])['items'])
        with self.assertRaises(p.c.ContractError):
            fresh.execute(core_module.ExecutionHandle(observation['id']))
        preview = fresh.preview('resume', ports.item_id)
        self.assertEqual('applied', fresh.execute(fresh.authorize(preview))['result'])

    def test_native_error_classification_at_injected_storage_boundary(self):
        # 保留原生 SQLite code/name 與 OS errno；不是物理耗盡證據。
        for failure in (OSError(errno.ENOSPC, 'PRIVATE'), OSError(errno.ENOMEM, 'PRIVATE'), sqlite3.OperationalError('PRIVATE')):
            if isinstance(failure, sqlite3.Error):
                failure.sqlite_errorcode, failure.sqlite_errorname = sqlite3.SQLITE_FULL, 'SQLITE_FULL'
            ports, core, _ = self.prepare()
            with mock.patch.object(p.db, 'connect', side_effect=failure):
                with self.assertRaises(p.c.ContractError) as observed:
                    core.preview('stop', ports.item_id)
            self.assertIs(failure, observed.exception.__cause__)
            if isinstance(failure, sqlite3.Error):
                self.assertEqual('SQLITE_FULL', observed.exception.__cause__.sqlite_errorname)
                self.assertEqual(13, observed.exception.__cause__.sqlite_errorcode)
            else:
                self.assertIn(observed.exception.__cause__.errno, (errno.ENOSPC, errno.ENOMEM))

    def test_proof_insert_failure_rolls_back_item_with_new_readback(self):
        ports, core, _ = self.prepare()
        preview = core.preview('stop', ports.item_id)
        handle = core.authorize(preview)
        before = self.state(ports)
        original = p.db.connect
        observed = []
        class ProofFailure:
            def __init__(self, connection):
                self.connection = connection
            def __getattr__(self, name):
                return getattr(self.connection, name)
            def execute(self, sql, parameters=()):
                if sql.startswith('INSERT INTO proofs'):
                    observed.append('proof-insert')
                    failure = sqlite3.OperationalError('PRIVATE')
                    failure.sqlite_errorcode, failure.sqlite_errorname = sqlite3.SQLITE_FULL, 'SQLITE_FULL'
                    raise failure
                return self.connection.execute(sql, parameters)
        def connect(*args, **kwargs):
            connection = original(*args, **kwargs)
            return ProofFailure(connection) if kwargs.get('writer') else connection
        with mock.patch.object(p.db, 'connect', side_effect=connect):
            self.assertEqual('not-applied', core.execute(handle)['result'])
        self.assertEqual(['proof-insert'], observed)
        self.assertEqual(before, self.state(ports))
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        self.assertEqual('not-applied', fresh.readback(preview['operation_id'], p.c.digest(preview), preview=preview)['result'])

    def test_seed_commit_interrupt_and_memory_failure_are_unknown(self):
        for stage in ('before-commit', 'after-commit', 'before-readback'):
            for failure in (KeyboardInterrupt(), MemoryError('PRIVATE')):
                def checkpoint(actual):
                    if actual == stage:
                        raise failure
                with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                    code, stream = self.run_pilot()
                self.assertEqual(130 if isinstance(failure, KeyboardInterrupt) else 2, code)
                event = stream.events[-1]
                self.assertEqual('preparation', event['phase'])
                self.assertEqual('state-unknown', event['result'])
                root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
                with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
                    self.assertEqual(0 if stage == 'before-commit' else 1, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
                self.assertNotIn('PRIVATE', stream.getvalue())

    def test_cli_reports_safe_os_sqlite_and_memory_classes(self):
        for failure, expected in ((OSError(errno.ENOSPC, 'PRIVATE'), 'os-error'),
                                  (OSError(errno.ENOMEM, 'PRIVATE'), 'os-error'),
                                  (sqlite3.OperationalError('PRIVATE'), 'sqlite-error'),
                                  (MemoryError('PRIVATE'), 'memory-error')):
            if isinstance(failure, sqlite3.Error):
                failure.sqlite_errorcode, failure.sqlite_errorname = sqlite3.SQLITE_CANTOPEN, 'PRIVATE'
            def callback(e):
                if e['event'] == 'target':
                    patcher = mock.patch.object(p.db, 'connect', side_effect=failure)
                    patcher.start()
                    active.append(patcher)
            active = []
            try:
                code, stream = self.run_pilot(Interaction(callback=callback))
            finally:
                for patcher in active:
                    patcher.stop()
            self.assertEqual(2, code)
            self.assertEqual(expected, stream.events[-1]['fault_class'])
            if expected == 'sqlite-error':
                self.assertEqual('SQLITE_CANTOPEN', stream.events[-1]['sqlite_name'])
            self.assertNotIn('PRIVATE', stream.getvalue())
