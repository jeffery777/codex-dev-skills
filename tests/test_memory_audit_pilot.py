from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
import errno
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.test_memory_audit_authority import ConnectionProbe, a, c, db
import memory_audit_pilot as p
from memory_audit_source import PinnedGitReader
from memory_governance_core import AuditSnapshot
from memory_governance_host import PRODUCTION_ADAPTERS

ROOT = Path(__file__).resolve().parents[1]


class Interaction(io.StringIO):
    def __init__(self, answer=None, callback=None):
        super().__init__()
        self.answer, self.callback, self.response = answer, callback, ''
        self.events = []

    def write(self, text):
        event = json.loads(text)
        self.events.append(event)
        if self.callback:
            self.callback(event)
        if 'confirmation' in event:
            self.response = event['confirmation'] + '\n' if self.answer is None else self.answer(event)
        return super().write(text)

    def readline(self, limit):
        return self.response[:limit]


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pilot-test-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()

    def run_pilot(self, interaction=None):
        interaction = interaction or Interaction()
        original = tempfile.mkdtemp
        def create(**kwargs):
            self.assertEqual('/tmp', kwargs['dir'])
            return original(prefix=kwargs['prefix'], dir=self.parent)
        with mock.patch.object(p.tempfile, 'mkdtemp', side_effect=create):
            result = p.main(['--create-synthetic'], stdin=interaction, stdout=interaction)
        self.assertNotIn('PRIVATE', interaction.getvalue())
        return result, interaction

    def context(self):
        root = Path(tempfile.mkdtemp(dir=self.parent))
        return p._prepare(root)

    def provider(self, ctx):
        provider = a.AuditAuthorityProvider(ctx.store, ctx.binding, clock=ctx.clock)
        self.addCleanup(provider.close)
        return provider

    @staticmethod
    def inventory(root):
        return {x.name: (db.identity(x.stat()), x.stat().st_mtime_ns, x.read_bytes()) for x in root.iterdir()}

    def test_disabled_help_unknown_zero_touch(self):
        with mock.patch.object(p, '_prepare', side_effect=AssertionError('prepare')), \
             mock.patch.object(p.tempfile, 'mkdtemp', side_effect=AssertionError('create')), \
             mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('probe')):
            stream = Interaction(answer=lambda _: self.fail('prompt'))
            self.assertEqual(0, p.main([], stdin=stream, stdout=stream))
            self.assertEqual('disabled', stream.events[0]['event'])
            for argv, code in ((['--help'], 0), (['--root', '/PRIVATE'], 2), (['--resume'], 2), (['--yes'], 2)):
                with mock.patch('sys.stdout', io.StringIO()), mock.patch('sys.stderr', io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        p.main(argv, stdin=stream, stdout=stream)
                self.assertEqual(code, error.exception.code)
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_cancel_before_create(self):
        for answer in ('', '\n', 'no\n', 'CREATE SYNTHETIC', 'CREATE SYNTHETIC extra\n'):
            with self.subTest(answer=answer), mock.patch.object(p.tempfile, 'mkdtemp', side_effect=AssertionError('create')):
                stream = Interaction(answer=lambda _: answer)
                self.assertEqual(0, p.main(['--create-synthetic'], stdin=stream, stdout=stream))
                self.assertFalse(stream.events[-1]['grant_issued'])

    def test_cancel_after_preflight_has_no_request_and_retains_fixture(self):
        for answer in ('', '\n', 'AUDIT wrong\n', 'x' * 1000):
            stream = Interaction(answer=lambda event: 'CREATE SYNTHETIC\n' if event['event'] == 'confirm-create' else answer)
            with self.subTest(answer=answer), mock.patch.object(a.AuditAuthorityProvider, 'accept', side_effect=AssertionError('accept')):
                result, stream = self.run_pilot(stream)
                self.assertEqual(0, result)
                root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
                with sqlite3.connect(root / 'authority' / db.MAIN) as connection:
                    self.assertEqual(0, connection.execute('SELECT count(*) FROM requests').fetchone()[0])
                self.assertTrue((root / 'managed' / db.MAIN).is_file())
                self.assertEqual('cancelled', stream.events[-1]['event'])

    def test_complete_closes_provider_and_managed_unchanged(self):
        providers, before = [], {}
        original = a.AuditAuthorityProvider.accept
        def accept(provider, **kwargs):
            providers.append(provider)
            before.update(self.inventory(provider.binding.root))
            return original(provider, **kwargs)
        with mock.patch.object(a.AuditAuthorityProvider, 'accept', accept):
            result, stream = self.run_pilot()
        self.assertEqual(0, result)
        report = stream.events[-1]['report']
        self.assertEqual('complete', report['status'])
        self.assertEqual(1, report['counts']['listed'])
        self.assertFalse(report['production_qualified'])
        self.assertFalse(report['write_performed'])
        self.assertEqual(before, self.inventory(providers[0].binding.root))
        self.assertTrue(providers[0]._failed)
        with a._connection(providers[0].store) as connection:
            self.assertEqual([('consumed',)], connection.execute('SELECT state FROM requests').fetchall())

    def test_wait_expiry_and_identity_drift_rejected_before_accept(self):
        for change in ('expiry', 'authority-mode', 'managed-mode'):
            ctx = self.context()
            def event(value):
                if value['event'] == 'confirm-audit':
                    if change == 'expiry':
                        sample = ctx.clock.clock()
                        ctx.clock.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 301)
                    else:
                        binding = ctx.store.files if change == 'authority-mode' else ctx.binding
                        (binding.root / db.LOCK).chmod(0o644)
            with self.subTest(change=change), mock.patch.object(p, '_prepare', return_value=ctx), \
                 mock.patch.object(a.AuditAuthorityProvider, 'accept', side_effect=AssertionError('accept')) as accept:
                code, stream = self.run_pilot(Interaction(callback=event))
                accept.assert_not_called()
            self.assertEqual(2, code)
            self.assertEqual('unavailable', stream.events[-1]['event'])

    def test_interrupt_and_output_failure_close_owner(self):
        for phase in ('confirm-create', 'confirm-audit', 'report'):
            for error in (KeyboardInterrupt(), OSError(errno.EIO, 'PRIVATE')):
                owners = []
                original = a.AuditAuthorityProvider.accept
                def accept(owner):
                    owners.append(owner)
                    return original(owner)
                def callback(event):
                    if event['event'] == phase:
                        raise error
                with self.subTest(phase=phase, error=type(error).__name__), \
                     mock.patch.object(a.AuditAuthorityProvider, 'accept', accept):
                    code, _ = self.run_pilot(Interaction(callback=callback))
                self.assertEqual(130 if isinstance(error, KeyboardInterrupt) else 2, code)
                self.assertEqual(phase == 'report', bool(owners))
                self.assertTrue(all(owner._failed for owner in owners))

    def test_persistent_output_fault_stops_writes_and_closes_owner(self):
        for phase in ('disabled', 'confirm-create', 'confirm-audit', 'report'):
            for method in ('write', 'flush'):
                owners = []
                original = a.AuditAuthorityProvider.accept
                def accept(owner):
                    owners.append(owner)
                    return original(owner)
                class Broken(Interaction):
                    broken = False
                    failures = 0
                    def write(self, text):
                        if json.loads(text)['event'] == phase:
                            self.broken = True
                        if self.broken and method == 'write':
                            self.failures += 1
                            raise OSError(errno.EIO, 'PRIVATE_OUTPUT')
                        return super().write(text)
                    def flush(self):
                        if self.broken and method == 'flush':
                            self.failures += 1
                            raise OSError(errno.EIO, 'PRIVATE_OUTPUT')
                        return super().flush()
                output = Broken()
                with self.subTest(phase=phase, method=method), \
                     mock.patch.object(a.AuditAuthorityProvider, 'accept', accept):
                    if phase == 'disabled':
                        code = p.main([], stdin=output, stdout=output)
                    else:
                        code, _ = self.run_pilot(output)
                self.assertEqual(2, code)
                self.assertEqual(1, output.failures)
                self.assertNotIn('PRIVATE_OUTPUT', output.getvalue())
                self.assertEqual(phase == 'report', bool(owners))
                self.assertTrue(all(owner._failed for owner in owners))

    def test_native_broken_pipe_exit_is_safe_including_shutdown_flush(self):
        reader, writer = os.pipe()
        os.close(reader)  # child 啟動前就確定沒有讀端，不靠 race。
        try:
            result = subprocess.run([sys.executable, str(ROOT / 'skills/loop-engineering/scripts/memory_audit_pilot.py')],
                cwd=self.parent, stdout=writer, stderr=subprocess.PIPE, text=True, timeout=30)
        finally:
            os.close(writer)
        self.assertEqual(2, result.returncode)
        self.assertEqual('', result.stderr)

    def test_bootstrap_failure_retains_partial_and_never_accepts(self):
        for error in (OSError(errno.ENOSPC, 'PRIVATE'), MemoryError('PRIVATE')):
            with mock.patch.object(p, '_source', side_effect=error), \
                 mock.patch.object(a.AuditAuthorityProvider, 'accept', side_effect=AssertionError('accept')):
                code, stream = self.run_pilot()
            self.assertEqual(2, code)
            self.assertTrue(Path(stream.events[1]['workspace']).is_dir())
            self.assertTrue(stream.events[-1]['retained'])

    @contextmanager
    def inject(self, ctx, point, fault):
        real, connections, observed = db.connect, [], []
        def connect(binding, limits, *, writer=False):
            connection = real(binding, limits, writer=writer)
            if binding.root != ctx.store.files.root:
                return connection
            connections.append(connection)
            return ConnectionProbe(connection, fault, point, observed)
        with mock.patch.object(db, 'connect', side_effect=connect):
            yield observed
        self.assertTrue(connections)
        for connection in connections:
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute('SELECT 1')
        for binding in (ctx.binding, ctx.store.files):
            with db.locked(binding, exclusive=True):
                pass

    def test_actual_authority_faults_no_retry_cleanup_and_new_acceptance(self):
        faults = [OSError(errno.ENOSPC, 'PRIVATE'), OSError(errno.ENOMEM, 'PRIVATE'), RuntimeError('PRIVATE')]
        for code in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_BUSY, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_NOMEM):
            fault = sqlite3.OperationalError('PRIVATE')
            fault.sqlite_errorcode = code
            faults.append(fault)
        ctx = self.context()
        for phase in ('accept', 'take'):
            for point in (('insert', 'commit-before', 'commit-after', 'readback') if phase == 'accept' else
                          ('update', 'commit-before', 'commit-after', 'readback')):
                for fault in faults:
                    with self.subTest(phase=phase, point=point, fault=type(fault).__name__):
                        owner = self.provider(ctx)
                        request = owner.accept() if phase == 'take' else None
                        before = self.inventory(ctx.binding.root)
                        with self.inject(ctx, point, fault) as observed:
                            if phase == 'accept':
                                with self.assertRaises(type(fault)):
                                    owner.accept()
                            else:
                                report = p.canary_report(enabled=True, context=ctx, provider=owner, request=request)
                                self.assertEqual('unavailable', report['status'])
                                self.assertEqual([], report['items'])
                                self.assertNotIn('PRIVATE', json.dumps(report))
                        self.assertTrue(owner._failed)
                        self.assertLessEqual(observed.count('commit'), 1)
                        self.assertEqual(before, self.inventory(ctx.binding.root))
                        recovered = self.provider(ctx)
                        if request:
                            with self.assertRaises(c.ContractError):
                                recovered.take_grant(request)
                        fresh = recovered.accept()
                        self.assertEqual('complete', p.canary_report(enabled=True, context=ctx, provider=recovered, request=fresh)['status'])

    def test_source_object_fault_is_safe_and_fresh_request_recovers(self):
        ctx = self.context()
        for error in (OSError(errno.EIO, 'PRIVATE'), MemoryError('PRIVATE')):
            owner = self.provider(ctx)
            with mock.patch.object(PinnedGitReader, '_object', side_effect=error):
                report = p.canary_report(enabled=True, context=ctx, provider=owner, request=owner.accept())
            self.assertNotIn('PRIVATE', json.dumps(report))
            self.assertTrue(all(item['summary'] is None for item in report['items']))
            owner.close()
            fresh = self.provider(ctx)
            self.assertEqual('complete', p.canary_report(enabled=True, context=ctx, provider=fresh, request=fresh.accept())['status'])

    def test_isolated_installed_entry_in_new_process(self):
        from tests.test_plugin_packaging import INSTALLER_ENV_OVERRIDES
        home, cwd = self.parent / 'home', self.parent / 'cwd'
        home.mkdir(); cwd.mkdir()
        env = os.environ.copy()
        for name in (*INSTALLER_ENV_OVERRIDES, 'PYTHONPATH', 'PYTHONHOME'):
            env.pop(name, None)
        env.update(HOME=str(home), XDG_STATE_HOME=str(self.parent / 'state'), PYTHONDONTWRITEBYTECODE='1')
        install = subprocess.run([str(ROOT / 'install.sh'), 'install', 'codex-cli-session-handoff'],
                                 cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(0, install.returncode, install.stderr)
        script = home / '.agents/skills/loop-engineering/scripts/memory_audit_pilot.py'
        self.assertTrue(script.is_file())
        for source in (script, ROOT / 'plugin/codex-dev-skills/skills/loop-engineering/scripts/memory_audit_pilot.py'):
            with self.subTest(source=source):
                process = subprocess.Popen([sys.executable, str(source), '--create-synthetic'], cwd=cwd,
                    env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                events = []
                try:
                    while line := process.stdout.readline():
                        event = json.loads(line); events.append(event)
                        if event['event'] == 'created':
                            # 測試只清除此 subprocess 自行建立的 fixture；操作入口本身不刪資料。
                            import shutil
                            self.addCleanup(shutil.rmtree, event['workspace'])
                        if 'confirmation' in event:
                            process.stdin.write(event['confirmation'] + '\n'); process.stdin.flush()
                    self.assertEqual(0, process.wait(timeout=30), process.stderr.read())
                    self.assertEqual('complete', events[-1]['report']['status'])
                    self.assertTrue(Path(next(e['workspace'] for e in events if e['event'] == 'created')).is_dir())
                finally:
                    if process.poll() is None:
                        process.kill(); process.wait()
                    process.stdin.close(); process.stdout.close(); process.stderr.close()

    def test_final_disclosure_close_and_revoke_clear_content(self):
        ctx = self.context()
        for action in ('close', 'revoke'):
            owner = self.provider(ctx)
            request = owner.accept()
            original = AuditSnapshot.validate_disclosure
            reached = []
            def validate(snapshot):
                if snapshot._closed:
                    reached.append(True)
                    owner.close() if action == 'close' else owner.revoke(request.request_id)
                return original(snapshot)
            with mock.patch.object(AuditSnapshot, 'validate_disclosure', validate):
                report = p.canary_report(enabled=True, context=ctx, provider=owner, request=request)
            self.assertTrue(reached)
            self.assertEqual([], report['items'])
            self.assertIsNone(report['snapshot_digest'])


if __name__ == '__main__':
    unittest.main()
