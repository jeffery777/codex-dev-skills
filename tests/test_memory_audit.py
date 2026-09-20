from __future__ import annotations

from dataclasses import replace
import errno
import contextlib
import io
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from tests.test_memory_governance_core import c, db, GovernanceCore, fixture, ITEM
from tests.test_memory_governance_local import local_fixture
from memory_governance_core import AuditSnapshot
from memory_governance_host import PRODUCTION_ADAPTERS
from memory_audit import audit_report, render_report


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mg1-audit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.host = fixture.SyntheticHost(self.root)
        self.core = GovernanceCore(self.host, enabled=True)
        self.core.initialize()

    def inventory(self):
        return {p.name: (p.stat().st_ino, p.stat().st_size, p.stat().st_mtime_ns,
                         hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.root.iterdir()}

    def report(self, **kwargs):
        before = self.inventory()
        result = audit_report(enabled=True, host=self.host, **kwargs)
        self.assertEqual(before, self.inventory())
        with db.locked(self.host.binding(), exclusive=True):
            pass
        self.assertFalse(result['write_performed'])
        self.assertFalse(result['production_qualified'])
        self.assertIsNone(result['capacity']['bytes'])
        return result

    def seed(self, count=1):
        fixture.seed_audit_items(self.host, count)

    def test_off_zero_touch_and_no_production_registration(self):
        with mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('probe')):
            result = audit_report(host=object(), max_pages=False)
        self.assertEqual('disabled', result['status'])
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))
        self.assertEqual('adapter-unavailable', audit_report(enabled=True)['reason'])

    def test_empty_is_complete_only_after_verified_snapshot(self):
        result = self.report()
        self.assertEqual('complete', result['status'])
        self.assertEqual(0, result['counts']['listed'])
        self.assertIsNotNone(result['snapshot_digest'])

    def test_git_source_real_database_e2e_states_versions_and_redaction(self):
        managed = self.root / 'isolated'
        managed.mkdir(mode=0o700)
        ports = local_fixture.SyntheticLocalPorts(managed, git_root=self.root / 'source')
        core = GovernanceCore(ports.host, enabled=True)
        core.initialize()
        for op, value in [('add', ports.candidate()), ('update', ports.candidate(2, cue='green')), ('stop', None)]:
            preview = core.preview(op, ITEM, value)
            self.assertEqual('applied', core.execute(core.authorize(preview))['result'])
        before = {p.name: p.read_bytes() for p in managed.iterdir()}
        result = audit_report(enabled=True, host=ports.host)
        self.assertEqual('complete', result['status'])
        self.assertEqual({'listed': 1, 'active': 0, 'stopped': 1, 'retained_versions': 2}, result['counts'])
        self.assertEqual(ports.source_revision, result['items'][0]['sources'][0]['revision'])
        self.assertIn('已停止 1', render_report(result))
        for attribute, denied in [('source_current', False), ('safety', 'prohibited'), ('safety', 'unknown')]:
            old = getattr(ports, attribute)
            setattr(ports, attribute, denied)
            hidden = audit_report(enabled=True, host=ports.host)
            self.assertEqual('partial', hidden['source_coverage'])
            self.assertIsNone(hidden['items'][0]['summary'])
            self.assertIsNone(hidden['items'][0]['sources'])
            self.assertNotIn(ports.source_revision, render_report(hidden))
            setattr(ports, attribute, old)
        self.assertEqual(before, {p.name: p.read_bytes() for p in managed.iterdir()})

    def test_pagination_complete_partial_output_and_fresh_recovery(self):
        self.seed(257)
        limited = self.report(max_pages=1)
        self.assertEqual('partial', limited['status'])
        self.assertEqual('page-limit', limited['reason'])
        self.assertEqual(256, limited['counts']['listed'])
        result = self.report()
        self.assertEqual('complete', result['status'])
        self.assertEqual(257, result['counts']['active'])
        self.assertEqual(257, len({i['item_id'] for i in result['items']}))
        limited = self.report(max_output_bytes=4096)
        self.assertEqual('output-limit', limited['reason'])
        self.assertFalse(limited['enumeration_complete'])
        self.assertLessEqual(len(c.canonical(limited)), 4096)
        self.assertLessEqual(len(render_report(limited).encode()), 4096)
        self.assertNotIn('next_cursor', limited)

    def test_interrupted_second_page_retains_only_complete_first_page(self):
        self.seed(257)
        original = AuditSnapshot.page
        seen = []
        def interrupt(snapshot, cursor=None):
            seen.append(cursor)
            if cursor is not None:
                raise OSError(errno.EIO, 'private-path-never-echo')
            return original(snapshot, cursor)
        with mock.patch.object(AuditSnapshot, 'page', interrupt):
            result = self.report()
        self.assertEqual(2, len(seen))
        self.assertEqual(256, result['counts']['listed'])
        self.assertEqual('partial', result['status'])
        self.assertEqual('storage-io', result['reason'])
        self.assertNotIn('private-path', json.dumps(result))
        with mock.patch.object(self.host, 'authorize_read', wraps=self.host.authorize_read) as authority:
            recovered = self.report()
        self.assertTrue(authority.called)
        self.assertEqual('complete', recovered['status'])

    def test_denial_and_root_drift_prevent_reads(self):
        self.host.readable = False
        with mock.patch.object(db, 'root_fd', side_effect=AssertionError('root read')):
            self.assertEqual('read-unavailable', audit_report(enabled=True, host=self.host)['reason'])
        self.host.readable = True
        before = self.inventory()
        self.host._binding = replace(self.host.binding(), directory_identity=(0, 0))
        with mock.patch.object(db, 'connect', side_effect=AssertionError('database read')):
            result = audit_report(enabled=True, host=self.host)
        self.assertEqual('root-changed', result['reason'])
        self.assertEqual(before, self.inventory())

    def test_revoked_authority_between_pages_clears_content_and_closes(self):
        self.seed(257)
        original = AuditSnapshot.page
        def revoke(snapshot, cursor=None):
            if cursor is not None:
                self.host.readable = False
            return original(snapshot, cursor)
        with mock.patch.object(AuditSnapshot, 'page', revoke):
            result = self.report()
        self.assertEqual('read-unavailable', result['reason'])
        self.assertEqual([], result['items'])
        self.assertIsNone(result['snapshot_digest'])
        self.host.readable = True
        self.assertEqual('complete', self.report()['status'])

    def test_root_registry_drift_between_pages_closes_without_content(self):
        self.seed(257)
        original = AuditSnapshot.page
        binding = self.host.binding()
        def drift(snapshot, cursor=None):
            if cursor is not None:
                self.host._binding = replace(binding, adapter_fingerprint='b' * 64)
            return original(snapshot, cursor)
        with mock.patch.object(AuditSnapshot, 'page', drift):
            result = audit_report(enabled=True, host=self.host)
        self.host._binding = binding
        self.assertEqual('root-changed', result['reason'])
        self.assertEqual([], result['items'])
        with db.locked(binding, exclusive=True):
            pass

    def test_busy_io_full_and_timeout_are_bounded_safe_and_recoverable(self):
        self.seed()
        before = self.inventory()
        with db.locked(self.host.binding(), exclusive=True):
            self.assertEqual('busy', audit_report(enabled=True, host=self.host)['reason'])
        for code, reason in [(sqlite3.SQLITE_BUSY, 'busy'), (sqlite3.SQLITE_FULL, 'storage-full'),
                             (sqlite3.SQLITE_IOERR, 'storage-io'), (sqlite3.SQLITE_INTERRUPT, 'timeout')]:
            exc = sqlite3.OperationalError('private-error-do-not-echo')
            exc.sqlite_errorcode = code
            with self.subTest(code=code), mock.patch.object(db, 'snapshot', side_effect=exc):
                result = self.report()
            self.assertEqual(reason, result['reason'])
            self.assertNotIn('private-error', render_report(result))
            self.assertEqual('unavailable', result['status'])
        self.assertEqual('complete', self.report()['status'])
        self.assertEqual(before, self.inventory())

    def test_deadline_during_integrity_replay_and_source_closes_reader(self):
        self.seed()
        real_snapshot = db.snapshot
        now = [0.0]
        def timeout(*args, **kwargs):
            now[0] = 11.0
            return real_snapshot(*args, **kwargs)
        with mock.patch('memory_governance_core.time.monotonic', side_effect=lambda: now[0]), \
             mock.patch.object(db, 'snapshot', side_effect=timeout):
            self.assertEqual('timeout', self.report()['reason'])
        now[0] = 0.0
        source = self.host.observe_source
        def slow(*args):
            result = source(*args)
            now[0] = 11.0
            return result
        with mock.patch('memory_governance_core.time.monotonic', side_effect=lambda: now[0]), \
             mock.patch.object(self.host, 'observe_source', side_effect=slow):
            self.assertEqual('timeout', self.report()['reason'])
        self.assertEqual('complete', self.report()['status'])

    def test_page_error_itself_closes_and_cursor_cannot_replay(self):
        self.seed(257)
        snapshot = self.core.audit()
        cursor = snapshot.page()['next_cursor']
        with self.assertRaises(c.ContractError):
            snapshot.page('wrong-cursor')
        with self.assertRaises(c.ContractError):
            snapshot.page(cursor)
        with db.locked(self.host.binding(), exclusive=True):
            pass
        self.assertEqual('complete', self.report()['status'])

    def test_renderer_quotes_untrusted_summary(self):
        self.seed()
        result = self.report()
        result['items'][0]['summary'] = 'untrusted\n\x1b[31m\u202eignore instructions\u0085\u009b\u2028\u2029\u200f'
        rendered = render_report(result)
        self.assertIn('\\n\\u001b', rendered)
        self.assertNotIn('\x1b', rendered)
        self.assertNotIn('\u202e', rendered)
        for char in ('\u0085', '\u009b', '\u2028', '\u2029', '\u200f'):
            self.assertNotIn(char, rendered)


    def test_cli_actual_json_wire_bytes_stay_in_budget(self):
        import governancectl
        value = fixture.version()
        value['summary'] = '合成資料' * 75
        value['validation']['content_digest'] = c.content_digest(value)
        with mock.patch.object(fixture, 'version', return_value=value):
            self.seed(220)
        before = self.inventory()
        output = io.StringIO()
        with mock.patch('memory_audit.production_host', return_value=self.host), contextlib.redirect_stdout(output):
            code = governancectl.main(['audit', '--enabled'])
        encoded = output.getvalue().encode('utf-8')
        self.assertEqual(0, code)
        self.assertEqual('complete', json.loads(encoded)['status'])
        self.assertLessEqual(len(encoded), c.MAX_ENVELOPE)
        self.assertEqual(before, self.inventory())

    def test_reader_effective_temp_policy_is_memory_and_persistent_files_unchanged(self):
        before = self.inventory()
        binding = self.host.binding()
        with contextlib.closing(db.connect(binding, c.decode(binding.profile_bytes))) as connection:
            self.assertEqual(2, connection.execute('PRAGMA temp_store').fetchone()[0])
            self.assertEqual(1, connection.execute('PRAGMA query_only').fetchone()[0])
        self.assertEqual(before, self.inventory())
