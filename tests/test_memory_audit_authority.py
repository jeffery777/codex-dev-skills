from __future__ import annotations

import contextlib
from dataclasses import replace
import errno
import io
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import threading
import unittest
from unittest import mock

from tests import test_memory_audit_adapter as fixtures
from tests.test_memory_governance_core import c, db
import memory_audit_authority as a
from memory_audit_dispatch import AuditDispatch, AuditHostFactory
from memory_governance_core import AuditSnapshot
from memory_governance_local import LocalClock
import governancectl


def restart_probe(store, binding, old_request, sender, crash=False):
    provider = a.AuditAuthorityProvider(store, binding, clock=LocalClock())
    try:
        provider.take_grant(old_request)
        sender.send('REPLAYED')
    except c.ContractError:
        sender.send('denied')
    request = provider.accept()
    sender.send(request)
    provider.take_grant(request)
    if crash:
        os._exit(23)  # consumed commit succeeded, caller never receives the grant.
    sender.send(provider.revoked(request.request_id))
    sender.close()


class ConnectionProbe:
    def __init__(self, connection, fault, point, observed):
        self.connection, self.fault, self.point, self.observed = connection, fault, point, observed
        self.committed = False

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def execute(self, sql, parameters=()):
        self.observed.append(sql)
        if ((self.point == 'begin' and sql == 'BEGIN IMMEDIATE')
                or (self.point == 'update' and sql.startswith('UPDATE requests'))
                or (self.point == 'insert' and sql.startswith('INSERT INTO requests'))
                or (self.point == 'readback' and self.committed and sql.startswith('SELECT session_id'))):
            raise self.fault
        return self.connection.execute(sql, parameters)

    def commit(self):
        self.observed.append('commit')
        if self.point == 'commit-before':
            raise self.fault
        result = self.connection.commit()
        self.committed = True
        if self.point == 'commit-after':
            raise self.fault
        return result


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AdapterTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.directory = self.fixture.parent / 'authority'
        self.directory.mkdir(mode=0o700)
        self.store = a.initialize_store(self.directory, self.fixture.binding)
        self.provider = self.new_provider()
        self.connections, self.observed = [], []

    def new_provider(self):
        return a.AuditAuthorityProvider(self.store, self.fixture.binding, clock=self.fixture.ports.clock_port)

    def factory(self, provider):
        f = self.fixture
        return AuditHostFactory(binding=f.binding, repository=f.repo, permits=(f.permit,),
                                accepted_sources=(f.acceptance,), qualification=f.qualification,
                                take_grant=provider.take_grant, clock=f.ports.clock_port,
                                request_revoked=provider.revoked, source_revoked=f.revoked_sources.__contains__,
                                qualification_revoked=f.revoked_qualifications.__contains__)

    def report(self, provider, request, *, enabled=True):
        before = self.fixture.inventory()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            governancectl.main(['audit'] + (['--enabled'] if enabled else []),
                               audit_dispatch=AuditDispatch(self.factory(provider), request))
        self.assertEqual(before, self.fixture.inventory())
        self.assertNotIn('PRIVATE', output.getvalue())
        self.assertNotIn(str(self.fixture.parent), output.getvalue())
        return json.loads(output.getvalue())

    def rows(self):
        with a._connection(self.store) as connection:
            return connection.execute('SELECT request_id,state FROM requests ORDER BY request_id').fetchall()

    @contextlib.contextmanager
    def inject(self, point, fault):
        real_connect = db.connect
        self.connections, self.observed = [], []
        def connect(binding, limits, *, writer=False):
            connection = real_connect(binding, limits, writer=writer)
            if binding.root != self.directory:
                return connection
            self.connections.append(connection)
            return ConnectionProbe(connection, fault, point, self.observed)
        with mock.patch.object(db, 'connect', side_effect=connect):
            yield

    def assert_closed(self):
        self.assertTrue(self.connections)
        for connection in self.connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        with db.locked(self.store.files, exclusive=True):
            pass

    def recovery(self, old_request):
        recovered = self.new_provider()
        with self.assertRaises(c.ContractError):
            recovered.take_grant(old_request)
        self.assertTrue(recovered.revoked(old_request.request_id))
        request = recovered.accept()
        self.assertNotEqual(old_request.request_id, request.request_id)
        self.assertEqual('complete', self.report(recovered, request)['status'])

    def test_actual_cli_and_persistent_lifecycle_memory_stays_readonly(self):
        request = self.provider.accept()
        self.assertEqual([(request.request_id, 'accepted')], self.rows())
        report = self.report(self.provider, request)
        self.assertEqual('complete', report['status'])
        self.assertFalse(report['write_performed'])  # managed memory, not authority bookkeeping.
        self.assertFalse(report['production_qualified'])
        self.assertEqual([(request.request_id, 'consumed')], self.rows())
        self.assertFalse(self.provider.revoked(request.request_id))
        self.provider.revoke(request.request_id)
        self.assertTrue(self.provider.revoked(request.request_id))
        self.assertEqual([(request.request_id, 'revoked')], self.rows())
        self.assertEqual('read-unavailable', self.report(self.provider, request)['reason'])

    def test_off_does_not_touch_or_consume_either_store(self):
        request = self.provider.accept()
        before = {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in self.directory.iterdir()}
        with mock.patch.object(a, '_connection', side_effect=AssertionError('touch')):
            self.assertEqual('disabled', self.report(self.provider, request, enabled=False)['status'])
        self.assertEqual(before, {p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in self.directory.iterdir()})
        self.assertEqual('complete', self.report(self.provider, request)['status'])

    def test_two_providers_and_duplicate_accept_do_not_reconstruct_authority(self):
        request = self.provider.accept()
        other = self.new_provider()
        for operation in (lambda: other.take_grant(request), lambda: other.revoke(request.request_id)):
            with self.assertRaises(c.ContractError):
                operation()
        self.assertTrue(other.revoked(request.request_id))
        self.assertEqual('complete', self.report(self.provider, request)['status'])
        with mock.patch.object(a.uuid, 'uuid4', return_value=request.request_id):
            with self.assertRaises(sqlite3.IntegrityError):
                other.accept()
        self.assertEqual([(request.request_id, 'consumed')], self.rows())

    def test_concurrent_consumers_return_exactly_one_grant(self):
        request = self.provider.accept()
        barrier = threading.Barrier(3)
        outcomes = []
        def consume():
            barrier.wait()
            try:
                outcomes.append(self.provider.take_grant(request))
            except c.ContractError:
                outcomes.append(None)
        threads = [threading.Thread(target=consume) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(1, sum(value is not None for value in outcomes))
        self.assertEqual([(request.request_id, 'consumed')], self.rows())

    def test_restart_and_process_loss_cannot_reuse_accepted_or_consumed_requests(self):
        request = self.provider.accept()
        ctx = multiprocessing.get_context('spawn')
        for crash in (False, True):
            with self.subTest(crash=crash):
                receiver, sender = ctx.Pipe(duplex=False)
                process = ctx.Process(target=restart_probe, args=(self.store, self.fixture.binding, request, sender, crash))
                process.start()
                sender.close()
                self.assertTrue(receiver.poll(15))
                self.assertEqual('denied', receiver.recv())
                child_request = receiver.recv()
                if not crash:
                    self.assertFalse(receiver.recv())
                process.join(15)
                self.assertEqual(23 if crash else 0, process.exitcode)
                receiver.close()
                self.assertIn((child_request.request_id, 'consumed'), self.rows())
                self.recovery(child_request)

    def test_take_failures_before_after_commit_never_reissue(self):
        faults = []
        for code in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_BUSY, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_NOMEM):
            error = sqlite3.OperationalError('PRIVATE provider fault')
            error.sqlite_errorcode = code
            faults.append(error)
        faults.extend([OSError(errno.ENOSPC, 'PRIVATE'), OSError(errno.ENOMEM, 'PRIVATE'), RuntimeError('PRIVATE')])
        for point in ('begin', 'update', 'commit-before', 'commit-after', 'readback'):
            for fault in faults:
                with self.subTest(point=point, fault=type(fault).__name__, code=getattr(fault, 'sqlite_errorcode', None)):
                    provider = self.new_provider()
                    request = provider.accept()
                    with self.inject(point, fault):
                        report = self.report(provider, request)
                    self.assertEqual('unavailable', report['status'])
                    self.assertEqual([], report['items'])
                    self.assertTrue(provider._failed)
                    with self.assertRaises(c.ContractError):
                        provider.take_grant(request)
                    self.assert_closed()
                    self.recovery(request)

    def test_accept_unknown_commit_does_not_publish_ram_grant(self):
        for point in ('insert', 'commit-before', 'commit-after', 'readback'):
            provider = self.new_provider()
            with self.subTest(point=point), self.inject(point, OSError(errno.EIO, 'PRIVATE')):
                with self.assertRaises(OSError):
                    provider.accept()
            self.assertTrue(provider._failed)
            self.assertEqual({}, provider._pending)
            self.assert_closed()
        fresh = self.new_provider()
        self.assertEqual('complete', self.report(fresh, fresh.accept())['status'])

    def test_owner_revoke_failure_denies_live_grants_without_claiming_durability(self):
        for point in ('begin', 'update', 'commit-before', 'commit-after', 'readback'):
            provider = self.new_provider()
            request = provider.accept()
            provider.take_grant(request)
            with self.subTest(point=point), self.inject(point, OSError(errno.ENOSPC, 'PRIVATE')):
                with self.assertRaises(OSError):
                    provider.revoke(request.request_id)
            self.assertTrue(provider.revoked(request.request_id))
            self.assertTrue(provider._failed)
            self.assert_closed()
            self.recovery(request)

    def test_failed_revoke_at_final_disclosure_clears_already_read_items(self):
        request = self.provider.accept()
        original = AuditSnapshot.validate_disclosure
        reached = []
        def final(snapshot):
            if snapshot._closed:
                reached.append(True)
                with self.inject('commit-before', OSError(errno.EIO, 'PRIVATE')):
                    with self.assertRaises(OSError):
                        self.provider.revoke(request.request_id)
            return original(snapshot)
        with mock.patch.object(AuditSnapshot, 'validate_disclosure', final):
            report = self.report(self.provider, request)
        self.assertTrue(reached)
        self.assertEqual([], report['items'])
        self.assertIsNone(report['snapshot_digest'])
        self.assertEqual('unavailable', report['status'])
        self.assert_closed()
        self.recovery(request)

    def test_busy_lock_and_read_failure_disable_provider_and_release_resources(self):
        request = self.provider.accept()
        with db.locked(self.store.files, exclusive=True):
            self.assertEqual('busy', self.report(self.provider, request)['reason'])
        self.recovery(request)
        provider = self.new_provider()
        request = provider.accept()
        provider.take_grant(request)
        with mock.patch.object(a, '_connection', side_effect=sqlite3.OperationalError('PRIVATE')):
            self.assertTrue(provider.revoked(request.request_id))
        self.assertTrue(provider.revoked(request.request_id))

    def test_mismatch_expiry_pid_and_close_refuse(self):
        for field, value in (('principal_id', '00000000-0000-0000-0000-000000000001'), ('scope_digest', '0' * 64)):
            provider = self.new_provider()
            request = provider.accept()
            with self.assertRaises(c.ContractError):
                provider.take_grant(replace(request, **{field: value}))
            self.assertEqual('read-unavailable', self.report(provider, request)['reason'])
        provider = self.new_provider()
        request = provider.accept()
        sample = provider.clock.clock()
        with mock.patch.object(provider.clock, 'clock', return_value=replace(sample, utc_seconds=sample.utc_seconds + 301)):
            self.assertEqual('read-unavailable', self.report(provider, request)['reason'])
        provider = self.new_provider()
        request = provider.accept()
        with mock.patch.object(a.os, 'getpid', return_value=provider._pid + 1):
            with self.assertRaises(c.ContractError):
                provider.take_grant(request)
        provider.close()
        self.assertEqual('read-unavailable', self.report(provider, request)['reason'])
        with self.assertRaises(c.ContractError):
            a.AuditAuthorityProvider(self.store, replace(self.fixture.binding, adapter_fingerprint='different'), clock=provider.clock)

    def test_store_identity_permissions_sidecar_and_schema_fail_closed(self):
        for fault in ('main-replaced', 'mode', 'journal', 'extra', 'schema', 'symlink', 'hardlink'):
            with self.subTest(fault=fault):
                directory = self.fixture.parent / fault
                directory.mkdir(mode=0o700)
                store = a.initialize_store(directory, self.fixture.binding)
                provider = a.AuditAuthorityProvider(store, self.fixture.binding, clock=self.provider.clock)
                request = provider.accept()
                main = directory / db.MAIN
                if fault == 'main-replaced':
                    saved = self.fixture.parent / 'old-main'
                    main.rename(saved)
                    main.write_bytes(saved.read_bytes())
                    main.chmod(0o600)
                elif fault == 'mode':
                    main.chmod(0o644)
                elif fault == 'journal':
                    (directory / db.JOURNAL).write_bytes(b'PRIVATE hot journal')
                    (directory / db.JOURNAL).chmod(0o600)
                elif fault == 'extra':
                    (directory / 'unknown').write_text('PRIVATE')
                elif fault == 'schema':
                    with contextlib.closing(sqlite3.connect(main)) as connection:
                        connection.execute('CREATE TABLE extra (x)')
                elif fault == 'symlink':
                    saved = self.fixture.parent / 'link-target'
                    main.rename(saved)
                    main.symlink_to(saved)
                else:
                    os.link(main, self.fixture.parent / 'hard-link')
                self.assertEqual('unavailable', self.report(provider, request)['status'])
                self.assertTrue(provider._failed)

    def test_bounded_rows_and_no_implicit_repair_or_initialization(self):
        request = self.provider.accept()
        with mock.patch.object(a, 'MAX_REQUESTS', 1):
            with self.assertRaisesRegex(c.ContractError, 'resource-limit'):
                self.provider.accept()
        self.assertEqual([(request.request_id, 'accepted')], self.rows())
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        with self.assertRaises(c.ContractError):
            a.initialize_store(self.directory, self.fixture.binding)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir()})
        missing = self.fixture.parent / 'missing'
        with self.assertRaises(OSError):
            a.initialize_store(missing, self.fixture.binding)
        self.assertFalse(missing.exists())

    def test_failed_initialization_retains_files_and_closes_connection(self):
        directory = self.fixture.parent / 'partial-init'
        directory.mkdir(mode=0o700)
        connect = sqlite3.connect
        observed, connections = [], []
        def fail_commit(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connections.append(connection)
            return ConnectionProbe(connection, OSError(errno.ENOSPC, 'PRIVATE'), 'commit-before', observed)
        with mock.patch.object(a.sqlite3, 'connect', side_effect=fail_commit):
            with self.assertRaises(OSError):
                a.initialize_store(directory, self.fixture.binding)
        self.assertIn('commit', observed)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        self.assertTrue((directory / db.MAIN).exists())
        self.assertTrue((directory / db.LOCK).exists())
        with self.assertRaisesRegex(c.ContractError, 'root-not-empty'):
            a.initialize_store(directory, self.fixture.binding)

    def test_persisted_row_tamper_and_file_size_limit_revoke_existing_authority(self):
        request = self.provider.accept()
        self.provider.take_grant(request)
        with contextlib.closing(sqlite3.connect(self.directory / db.MAIN)) as connection:
            connection.execute("UPDATE requests SET scope_digest=? WHERE request_id=?", ('0' * 64, request.request_id))
            connection.commit()
        self.assertTrue(self.provider.revoked(request.request_id))
        self.assertTrue(self.provider._failed)
        provider = self.new_provider()
        request = provider.accept()
        with open(self.directory / db.MAIN, 'r+b') as stream:
            stream.truncate(a.LIMITS['data_limit_bytes'] + 4096)
        self.assertEqual('unavailable', self.report(provider, request)['status'])
        self.assertTrue(provider._failed)

    def test_pending_revoke_and_take_race_cannot_revive(self):
        request = self.provider.accept()
        barrier = threading.Barrier(3)
        result = []
        def take():
            barrier.wait()
            try:
                result.append(self.provider.take_grant(request))
            except c.ContractError:
                result.append(None)
        def revoke():
            barrier.wait()
            self.provider.revoke(request.request_id)
        threads = [threading.Thread(target=take), threading.Thread(target=revoke)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(1, len(result))
        self.assertTrue(self.provider.revoked(request.request_id))
        self.assertEqual([(request.request_id, 'revoked')], self.rows())
        with self.assertRaises(c.ContractError):
            self.provider.take_grant(request)


if __name__ == '__main__':
    unittest.main()
