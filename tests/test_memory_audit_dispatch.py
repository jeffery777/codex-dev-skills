from __future__ import annotations

import contextlib
from dataclasses import replace
import errno
import io
import json
import os
import sqlite3
import threading
import time
import unittest
from unittest import mock
import uuid

from tests import test_memory_audit_adapter as adapter_tests
from tests.test_memory_governance_core import c, db
from memory_audit import audit_report
from memory_audit_adapter import ReadGrant, PORT_FILES
from memory_audit_dispatch import AuditDispatch, AuditHostFactory, AuditRequest
from memory_governance_core import AuditSnapshot
from memory_governance_host import PRODUCTION_ADAPTERS
import governancectl


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = adapter_tests.AdapterTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.grants = {}
        self.taken = []
        self.factory = self.make_factory()

    def take_grant(self, request):
        # Synthetic trusted control plane: pop consumes even before later validation fails.
        self.taken.append(request.request_id)
        grant = self.grants.pop(request.request_id, None)
        c.require(grant is not None, 'read-unavailable')
        return grant

    def make_factory(self, **changes):
        f = self.fixture
        args = dict(binding=f.binding, repository=f.repo, permits=(f.permit,),
                    accepted_sources=(f.acceptance,), qualification=f.qualification,
                    take_grant=self.take_grant, clock=f.ports.clock_port,
                    request_revoked=f.revoked_requests.__contains__,
                    source_revoked=f.revoked_sources.__contains__,
                    qualification_revoked=f.revoked_qualifications.__contains__)
        args.update(changes)
        return AuditHostFactory(**args)

    def request(self):
        f = self.fixture
        request = AuditRequest(c.decode(f.binding.scope_bytes)['principal_id'], str(uuid.uuid4()),
                               c.digest(c.decode(f.binding.scope_bytes)))
        now = f.ports.clock_port.clock()
        self.grants[request.request_id] = ReadGrant(f.binding, request.principal_id, request.request_id,
                                                   now, now.utc_seconds + 300)
        return request

    def dispatch(self, request=None, factory=None):
        return AuditDispatch(factory or self.factory, request or self.request())

    def cli(self, dispatch, *, enabled=True, format='json'):
        before = self.fixture.inventory()
        output = io.StringIO()
        args = ['audit', '--format', format] + (['--enabled'] if enabled else [])
        with contextlib.redirect_stdout(output):
            status = governancectl.main(args, audit_dispatch=dispatch)
        self.assertEqual(before, self.fixture.inventory())
        with db.locked(self.fixture.binding, exclusive=True):
            pass
        self.assertNotIn('PRIVATE', output.getvalue())
        self.assertNotIn(str(self.fixture.root), output.getvalue())
        if format == 'text':
            return status, output.getvalue()
        report = json.loads(output.getvalue())
        self.assertFalse(report['write_performed'])
        self.assertFalse(report['production_qualified'])
        return status, report

    def assert_recovery(self):
        self.assertEqual('complete', self.cli(self.dispatch())[1]['status'])

    def test_cli_real_adapter_fresh_requests_and_both_formats(self):
        with mock.patch('memory_audit.production_host', side_effect=AssertionError('registry used')):
            first, second = self.dispatch(), self.dispatch()
            status, report = self.cli(first)
            self.assertEqual((0, 'complete', 'complete'), (status, report['status'], report['source_coverage']))
            self.assertEqual(self.fixture.value['summary'], report['items'][0]['summary'])
            status, text = self.cli(second, format='text')
            self.assertEqual(0, status)
            self.assertIn('項目列舉完成', text)
        self.assertEqual(2, len(set(self.taken)))
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_off_before_validation_consumption_factory_and_io(self):
        dispatch = self.dispatch()
        with mock.patch.object(self.factory, 'create_host', side_effect=AssertionError('touch')):
            for value in (dispatch, object()):
                self.assertEqual('disabled', self.cli(value, enabled=False)[1]['status'])
        self.assertFalse(dispatch._used)
        self.assertEqual([], self.taken)
        self.assertEqual('complete', self.cli(dispatch)[1]['status'])
        self.assertEqual('adapter-unavailable', self.cli(None)[1]['reason'])
        self.assertEqual('read-unavailable', self.cli(object())[1]['reason'])

    def test_consumed_dispatch_and_new_dispatch_same_request_cannot_replay(self):
        request = self.request()
        dispatch = self.dispatch(request)
        self.assertEqual('complete', self.cli(dispatch)[1]['status'])
        self.assertEqual('read-unavailable', self.cli(dispatch)[1]['reason'])
        self.assertEqual(1, self.taken.count(request.request_id))
        self.assertEqual('read-unavailable', self.cli(self.dispatch(request))[1]['reason'])
        self.assert_recovery()

    def test_principal_scope_mismatch_precedes_control_plane_and_io(self):
        request = self.request()
        for wrong in (replace(request, principal_id=str(uuid.uuid4())),
                      replace(request, scope_digest='0' * 64)):
            self.assertEqual('read-unavailable', self.cli(self.dispatch(wrong))[1]['reason'])
        self.assertEqual([], self.taken)
        self.assert_recovery()

    def test_provider_returned_binding_principal_request_must_match(self):
        for field in ('binding', 'principal_id', 'request_id'):
            request = self.request()
            value = self.grants[request.request_id]
            changes = {field: (replace(value.binding, filesystem_id='different') if field == 'binding'
                               else str(uuid.uuid4()))}
            self.grants[request.request_id] = replace(value, **changes)
            self.assertEqual('read-unavailable', self.cli(self.dispatch(request))[1]['reason'])
            self.assertNotIn(request.request_id, self.grants)
        self.assert_recovery()

    def test_expired_revoked_and_failed_qualification_consume_request(self):
        for cause in ('expired', 'revoked', 'qualification'):
            request = self.request()
            if cause == 'expired':
                self.grants[request.request_id] = replace(self.grants[request.request_id], expires_at=0)
            elif cause == 'revoked':
                self.fixture.revoked_requests.add(request.request_id)
            else:
                self.fixture.revoked_qualifications.add(self.fixture.qualification.evidence_id)
            dispatch = self.dispatch(request)
            self.assertEqual(2, self.cli(dispatch)[0])
            self.assertEqual('read-unavailable', self.cli(dispatch)[1]['reason'])
            self.assertEqual(1, self.taken.count(request.request_id))
            self.fixture.revoked_qualifications.clear()
        self.assert_recovery()

    def test_provider_failure_is_safe_single_attempt_and_new_request_recovers(self):
        for error, reason in ((RuntimeError('PRIVATE'), 'unavailable'),
                              (MemoryError('PRIVATE'), 'resource-limit'),
                              (OSError(errno.EIO, 'PRIVATE'), 'storage-io')):
            dispatch = self.dispatch()
            def fail(request):
                self.take_grant(request)
                raise error
            with mock.patch.object(self.factory, 'take_grant', side_effect=fail) as provider:
                status, report = self.cli(dispatch)
                self.assertEqual((2, 'unavailable', reason), (status, report['status'], report['reason']))
                self.assertEqual('read-unavailable', self.cli(dispatch)[1]['reason'])
                self.assertEqual(1, provider.call_count)
            self.assert_recovery()

    def test_process_drift_and_concurrent_dispatch_never_reacquire(self):
        dispatch = self.dispatch()
        with mock.patch('memory_audit_dispatch.os.getpid', return_value=dispatch._pid + 1):
            self.assertEqual('read-unavailable', self.cli(dispatch)[1]['reason'])
        self.assertEqual([], self.taken)
        entered, release = threading.Event(), threading.Event()
        original = self.factory.take_grant
        def delayed(request):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('provider timeout')
            return original(request)
        results = []
        with mock.patch.object(self.factory, 'take_grant', side_effect=delayed):
            worker = threading.Thread(target=lambda: results.append(audit_report(enabled=True, dispatch=dispatch)))
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                result = audit_report(enabled=True, dispatch=dispatch)
                self.assertEqual('read-unavailable', result['reason'])
            finally:
                release.set()
                worker.join(10)
            self.assertFalse(worker.is_alive())
        self.assertEqual(1, len(self.taken))
        self.assertEqual('complete', results[0]['status'])
        self.assert_recovery()

    def test_no_argv_authority_loader_and_mutually_exclusive_host(self):
        dispatch = self.dispatch()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                governancectl.main(['audit', '--enabled', '--adapter', 'PRIVATE'], audit_dispatch=dispatch)
        self.assertFalse(dispatch._used)
        result = audit_report(enabled=True, host=object(), dispatch=dispatch)
        self.assertEqual('read-unavailable', result['reason'])
        self.assertFalse(dispatch._used)
        self.assertIn('memory_audit_dispatch.py', PORT_FILES)
        self.assertIn('governancectl.py', PORT_FILES)

    def test_faults_after_open_close_sqlite_release_lock_and_new_request_recovers(self):
        errors = []
        for code, reason in ((sqlite3.SQLITE_FULL, 'storage-full'), (sqlite3.SQLITE_BUSY, 'busy'),
                             (sqlite3.SQLITE_IOERR, 'storage-io'), (sqlite3.SQLITE_NOMEM, 'resource-limit')):
            error = sqlite3.OperationalError('PRIVATE')
            error.sqlite_errorcode = code
            errors.append((error, reason))
        errors += [(OSError(errno.ENOSPC, 'PRIVATE'), 'storage-full'),
                   (OSError(errno.ENOMEM, 'PRIVATE'), 'resource-limit'),
                   (RuntimeError('PRIVATE'), 'unavailable')]
        for error, reason in errors:
            with self.subTest(reason=reason, error=type(error).__name__):
                connections = []
                original = db.connect
                def observed_connect(*args, **kwargs):
                    connection = original(*args, **kwargs)
                    connections.append(connection)
                    return connection
                with mock.patch.object(db, 'connect', observed_connect), mock.patch.object(db, 'load_item', side_effect=error) as load:
                    status, report = self.cli(self.dispatch())
                self.assertEqual((2, reason, []), (status, report['reason'], report['items']))
                self.assertTrue(load.called)
                self.assertTrue(connections)
                for connection in connections:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        connection.execute('SELECT 1')
                self.assert_recovery()

    def test_real_reader_fault_closes_fds_and_new_request_recovers(self):
        original = os.read
        observed = set()
        def fail(fd, count):
            observed.add(fd)
            original(fd, min(count, 1))
            raise OSError(errno.EIO, 'PRIVATE')
        with mock.patch('memory_audit_source.os.read', side_effect=fail):
            _, report = self.cli(self.dispatch())
        self.assertTrue(observed)
        self.assertIsNone(report['items'][0]['summary'])
        for fd in observed:
            with self.assertRaises(OSError):
                os.fstat(fd)
        self.assert_recovery()

    def test_partial_on_second_page_full_and_revocation_clears_disclosure(self):
        self.fixture.bulk()
        self.factory = self.make_factory()
        for revoke in (False, True):
            request = self.request()
            original = AuditSnapshot.page
            def fail_second(snapshot, cursor=None):
                if cursor is not None:
                    if revoke:
                        self.fixture.revoked_requests.add(request.request_id)
                    error = sqlite3.OperationalError('PRIVATE')
                    error.sqlite_errorcode = sqlite3.SQLITE_FULL
                    raise error
                return original(snapshot, cursor)
            with mock.patch.object(AuditSnapshot, 'page', fail_second):
                status, report = self.cli(self.dispatch(request))
            self.assertEqual(2, status)
            self.assertEqual(0 if revoke else 256, report['counts']['listed'])
            self.assertEqual('unavailable' if revoke else 'partial', report['status'])
            self.assert_recovery()

    def test_deadline_and_final_authority_exception_release_and_clear(self):
        self.fixture.bulk()
        self.factory = self.make_factory()
        original = AuditSnapshot.page
        def expire(snapshot, cursor=None):
            if cursor is not None:
                snapshot._deadline = time.monotonic() - 1
            return original(snapshot, cursor)
        with mock.patch.object(AuditSnapshot, 'page', expire):
            _, report = self.cli(self.dispatch())
        self.assertEqual(('partial', 'timeout'), (report['status'], report['reason']))
        self.assert_recovery()
        original_disclosure = AuditSnapshot.validate_disclosure
        final_states, connections = [], []
        original_connect = db.connect
        def observed_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            connections.append(connection)
            return connection
        def fail_after_close(snapshot):
            if snapshot._closed:
                final_states.append((snapshot._closed, snapshot._pages, snapshot._count))
                raise RuntimeError('PRIVATE')
            return original_disclosure(snapshot)
        with mock.patch.object(db, 'connect', observed_connect), mock.patch.object(
                AuditSnapshot, 'validate_disclosure', fail_after_close):
            _, report = self.cli(self.dispatch())
        self.assertEqual([(True, 2, 257)], final_states)
        self.assertEqual(('unavailable', []), (report['status'], report['items']))
        self.assertIsNone(report['snapshot_digest'])
        self.assertTrue(connections)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        self.assert_recovery()
