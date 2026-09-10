from __future__ import annotations

import contextlib
from dataclasses import replace
import errno
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from tests.test_memory_governance_core import c, db, GovernanceCore, ITEM
from tests.test_memory_governance_local import local_fixture
from memory_governance_local import SingleRootRegistry


class LocalFaultTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mg1-local-fault-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.ports = local_fixture.SyntheticLocalPorts(self.root)
        self.core = GovernanceCore(self.ports.host, enabled=True)
        self.core.initialize()

    def prepare(self):
        preview = self.core.preview('add', ITEM, self.ports.candidate(body='Synthetic capacity payload. ' * 450))
        return preview, self.core.authorize(preview)

    def assert_not_replayed(self, handle):
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized-or-consumed'):
            self.core.execute(handle)

    def test_actual_process_loss_without_preview_never_claims_applied_or_changes_files(self):
        repository = Path(__file__).resolve().parents[1]
        worker = repository / 'tests/fixtures/memory-governance/local_crash_worker.py'
        for stage in ('before-transaction', 'after-item-write', 'before-commit', 'after-commit'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory(prefix='mg1-local-process-') as temporary:
                root = Path(temporary).resolve()
                completed = subprocess.run([str(repository / 'scripts/project-python'), str(worker), str(root), stage],
                                           cwd=repository, capture_output=True, timeout=30)
                self.assertEqual(73, completed.returncode, completed.stderr.decode())
                request = c.decode(completed.stdout)
                self.assertEqual({'operation_id', 'preview_digest', 'directory_identity', 'main_identity',
                                  'lock_identity'}, set(request))
                # Explicit test host binding from the originating process, never infer IDs from DB content.
                ports = local_fixture.SyntheticLocalPorts(root)
                ports.registry = SingleRootRegistry(replace(ports.registry.binding(), **{
                    key: tuple(request[key]) for key in ('directory_identity', 'main_identity', 'lock_identity')}))
                ports.readback_ids.add(request['operation_id'])
                fresh = GovernanceCore(ports.compose(), enabled=True)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                result = fresh.readback(request['operation_id'], request['preview_digest'])
                # Source approval also died with the child. A durable proof does not
                # make that source adoptable or reconstruct the missing preview.
                expected = 'committed-but-not-adoptable' if stage == 'after-commit' else 'state-unknown'
                self.assertEqual(expected, result['result'])
                self.assertEqual(stage == 'after-commit', result['proof'] is not None)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
                if (root / db.JOURNAL).exists() and (root / db.JOURNAL).stat().st_size:
                    with mock.patch.object(db, 'connect', side_effect=AssertionError('must not auto recover')):
                        with self.assertRaisesRegex(c.ContractError, 'recovery-required'):
                            fresh.audit()

    def test_available_space_loss_rejects_before_writer(self):
        preview, handle = self.prepare()
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        original = db.connect
        writer_calls = []
        def connect(*args, **kwargs):
            if kwargs.get('writer'):
                writer_calls.append(True)
            return original(*args, **kwargs)
        # Deterministic fstatvfs fault, not an actual filesystem ENOSPC event.
        with mock.patch.object(db.os, 'fstatvfs', return_value=SimpleNamespace(f_bavail=0, f_frsize=4096)), \
             mock.patch.object(db, 'connect', side_effect=connect):
            with self.assertRaisesRegex(c.ContractError, 'insufficient-space'):
                self.core.execute(handle)
        self.assertEqual([], writer_calls)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.assert_not_replayed(handle)
        self.assertEqual('not-applied', self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)['result'])

    def test_actual_sqlite_full_from_test_only_page_quota_rolls_back(self):
        preview, handle = self.prepare()
        connect_original, write_original = db.connect, db.write_item
        errors = []
        def connect(*args, **kwargs):
            connection = connect_original(*args, **kwargs)
            if kwargs.get('writer'):
                # After the production checks, deliberately inject a lower engine page quota.
                # This proves SQLITE_FULL handling, not profile qualification or disk exhaustion.
                pages = connection.execute('PRAGMA page_count').fetchone()[0]
                self.assertEqual(pages, connection.execute('PRAGMA max_page_count=' + str(pages)).fetchone()[0])
            return connection
        def write(*args, **kwargs):
            try:
                return write_original(*args, **kwargs)
            except sqlite3.Error as error:
                errors.append((error.sqlite_errorcode, error.sqlite_errorname))
                raise
        with mock.patch.object(db, 'connect', side_effect=connect), mock.patch.object(db, 'write_item', side_effect=write):
            result = self.core.execute(handle)
        self.assertEqual([(sqlite3.SQLITE_FULL, 'SQLITE_FULL')], errors)
        self.assertEqual('not-applied', result['result'])
        self.assertIsNone(result['proof'])
        self.assertEqual(preview['before']['digest'], result['state_digest'])
        self.assert_not_replayed(handle)
        with self.core.audit() as audit:
            self.assertEqual([], audit.page()['items'])

    def test_enospc_exception_and_reply_loss_follow_fresh_readback(self):
        for stage, expected in (('after-item-write', 'not-applied'), ('before-commit', 'not-applied'),
                                ('after-commit', 'applied')):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory(prefix='mg1-enospc-injection-') as temporary:
                ports = local_fixture.SyntheticLocalPorts(Path(temporary).resolve())
                core = GovernanceCore(ports.host, enabled=True)
                core.initialize()
                preview = core.preview('add', ITEM, ports.candidate())
                handle = core.authorize(preview)
                injected = []
                def fault(observed_stage):
                    if observed_stage == stage:
                        injected.append(stage)
                        raise OSError(errno.ENOSPC, 'Synthetic ENOSPC injection')
                with mock.patch('memory_governance_core._checkpoint', side_effect=fault):
                    result = core.execute(handle)
                self.assertEqual([stage], injected)
                self.assertEqual(expected, result['result'])
                self.assertEqual(expected == 'applied', result['proof'] is not None)
                with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized-or-consumed'):
                    core.execute(handle)

    def test_exclusive_lock_covers_independent_readback_connection(self):
        preview, handle = self.prepare()
        locked_original, connect_original = db.locked, db.connect
        elapsed, connections, held = [], [], []
        @contextlib.contextmanager
        def timed_lock(binding, *, exclusive=False):
            with locked_original(binding, exclusive=exclusive) as directory:
                start = time.monotonic_ns()
                try:
                    yield directory
                finally:
                    if exclusive:
                        elapsed.append(time.monotonic_ns() - start)
        def observe(stage):
            if stage == 'before-readback':
                with self.assertRaisesRegex(c.ContractError, 'busy'):
                    with locked_original(self.ports.registry.binding(), exclusive=True):
                        self.fail('writer lock released before readback')
                held.append(True)
        def connect(*args, **kwargs):
            connection = connect_original(*args, **kwargs)
            connections.append((bool(kwargs.get('writer')), connection))
            return connection
        with mock.patch.object(db, 'locked', side_effect=timed_lock), \
             mock.patch.object(db, 'connect', side_effect=connect), \
             mock.patch('memory_governance_core._checkpoint', side_effect=observe):
            result = self.core.execute(handle)
        self.assertEqual('applied', result['result'])
        self.assertEqual([True], held)
        self.assertEqual(1, len(elapsed))
        self.assertGreater(elapsed[0], 0)
        self.assertEqual([False, True, False], [writer for writer, _ in connections])
        self.assertEqual(3, len({id(connection) for _, connection in connections}))
        for _, connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')


if __name__ == '__main__':
    unittest.main()
