"""固定 restore 入口：歷史全文、重新驗證、版本一致性及故障停止。"""
from __future__ import annotations

from copy import deepcopy
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

from tests import test_memory_content_pilot as content_tests
from tests.test_memory_maintenance_pilot import Interaction, p, core_module, PRODUCTION_ADAPTERS


class RestoreTests(unittest.TestCase):
    setUp = content_tests.ContentTests.setUp
    state = content_tests.ContentTests.state
    versions = content_tests.ContentTests.versions

    def prepare(self, stream=None):
        stream = stream or Interaction()
        root = Path(tempfile.mkdtemp(dir=self.parent))
        ports = p._prepare(root, stream, stream, content=True, restore=True)
        return ports, p.GovernanceCore(ports.host(), enabled=True), stream

    def run_pilot(self, stream=None):
        stream = stream or Interaction()
        create = tempfile.mkdtemp
        def create_here(**kwargs):
            self.assertEqual('/tmp', kwargs['dir'])
            return create(prefix=kwargs['prefix'], dir=self.parent)
        with mock.patch.object(p.tempfile, 'mkdtemp', side_effect=create_here):
            code = p.main(['--create-synthetic', '--scenario', 'add-update-restore'], stdin=stream, stdout=stream)
        return code, stream

    def apply(self, ports, operation):
        core = p.GovernanceCore(ports.host(), enabled=True)
        candidate = ports.prepare_restore() if operation == 'restore' else ports.candidates.get(operation)
        preview = core.preview(operation, ports.item_id, candidate,
                               **({'restore_revision': 1} if operation == 'restore' else {}))
        result = core.execute(core.authorize(preview))
        self.assertEqual('applied', result['result'])
        return preview, result

    def ready(self):
        ports, core, stream = self.prepare()
        self.apply(ports, 'add')
        self.apply(ports, 'update')
        candidate = ports.prepare_restore()
        preview = core.preview('restore', ports.item_id, candidate, restore_revision=1)
        return ports, core, stream, preview

    def test_default_off_and_no_arbitrary_restore_surface(self):
        with mock.patch.object(p, '_prepare', side_effect=AssertionError('prepare')), \
             mock.patch.object(p.db, 'runtime_facts', side_effect=AssertionError('probe')):
            stream = Interaction(answer=lambda _: self.fail('prompt'))
            self.assertEqual(0, p.main(['--scenario', 'add-update-restore'], stdin=stream, stdout=stream))
            self.assertEqual(['disabled'], [e['event'] for e in stream.events])
            for args in (['--root', '/PRIVATE'], ['--restore-revision', '2'], ['--candidate', '{}']):
                with mock.patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                    p.main(args, stdin=stream, stdout=stream)
        ports, core, _ = content_tests.ContentTests.prepare(self)
        self.assertFalse(ports.qualify(ports.registry.binding(), ports.runtime, 'restore'))
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_complete_snapshot_full_history_new_revision_and_current_only(self):
        retained_at_prompt = []
        workspace = []
        def callback(event):
            if event['event'] == 'created':
                workspace.append(Path(event['workspace']))
            if event.get('preview', {}).get('operation') == 'restore':
                with sqlite3.connect(workspace[0] / 'managed' / p.db.MAIN) as conn:
                    retained_at_prompt.append(p.c.decode(conn.execute('SELECT document FROM versions WHERE revision=1').fetchone()[0]))
        code, stream = self.run_pilot(Interaction(callback=callback))
        self.assertEqual(0, code, stream.getvalue())
        prompts = [e for e in stream.events if e['event'] == 'confirm-operation']
        self.assertEqual(['add', 'update', 'restore'], [e['preview']['operation'] for e in prompts])
        self.assertEqual(3, len({e['confirmation'] for e in prompts}))
        event = prompts[-1]
        self.assertEqual([1], event['preview']['target_revisions'])
        self.assertEqual(event['preview']['before']['digest'], event['change']['snapshot_digest'])
        self.assertEqual(retained_at_prompt[0], event['change']['restore_source'])
        self.assertIsNotNone(event['change']['restore_source']['retired_at'])
        self.assertEqual(prompts[1]['change']['after'], event['change']['before'])
        self.assertEqual(event['preview']['candidate'], event['change']['after'])
        old, restored = event['change']['restore_source'], event['change']['after']
        self.assertEqual(3, restored['revision'])
        self.assertIsNone(restored['retired_at'])
        self.assertEqual(old['provenance'], restored['provenance'])
        self.assertNotEqual(old['validation']['evidence_id'], restored['validation']['evidence_id'])
        with sqlite3.connect(workspace[0] / 'managed' / p.db.MAIN) as conn:
            versions = [p.c.decode(r[0]) for r in conn.execute('SELECT document FROM versions ORDER BY revision')]
            proofs = [p.c.decode(r[0]) for r in conn.execute('SELECT document FROM proofs ORDER BY sequence')]
        self.assertEqual(old, versions[0])
        self.assertEqual(dict(event['change']['before'], retired_at=restored['created_at']), versions[1])
        self.assertEqual(restored, versions[2])
        self.assertEqual((2, 3, 1), tuple(proofs[-1][k] for k in ('before_revision', 'after_revision', 'restore_source_revision')))
        verified = [e for e in stream.events if e['event'] == 'verified']
        self.assertEqual([1, 2, 3], [e['revision'] for e in verified])
        self.assertEqual([1, 0, 1], [e['recall_counts']['blue+widget'] for e in verified])
        self.assertEqual([0, 1, 0], [e['recall_counts']['green+widget'] for e in verified])
        self.assertTrue(all(e['recall_counts']['blue+green'] == 0 for e in verified))
        self.assertEqual([1, 2, 3], [e['report']['items'][0]['retained_versions'] for e in stream.events if e['event'] == 'audit'])

    def test_cancel_each_step_preserves_only_confirmed_operations(self):
        for count, operation in enumerate(('add', 'update', 'restore')):
            stream = Interaction(answer=lambda e: 'no\n' if e.get('preview', {}).get('operation') == operation else e['confirmation'] + '\n')
            code, stream = self.run_pilot(stream)
            self.assertEqual(0, code)
            self.assertEqual('cancelled', stream.events[-1]['event'])
            root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
            with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
                self.assertEqual(count, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
                self.assertEqual(count, conn.execute('SELECT count(*) FROM versions').fetchone()[0])

    def test_same_second_restore_rechecks_original_source_and_preserves_stop_resume_revision(self):
        ports, core, _ = self.prepare()
        sample = ports.clock.clock()
        # 固定同一秒即可，不靠人為 +1 造成 future validation。
        ports.clock.clock = lambda: sample
        self.apply(ports, 'add')
        self.apply(ports, 'update')
        with mock.patch.object(ports.reader, 'read_artifact', wraps=ports.reader.read_artifact) as read:
            _, result = self.apply(ports, 'restore')
            self.assertGreaterEqual(read.call_count, 2)
        self.assertEqual(sample.utc_seconds, ports.candidates['restore']['created_at'])
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        self.assertEqual(ports.candidates['restore'], fresh.recall(['blue'])['items'][0]['version'])
        for operation in ('stop', 'resume'):
            _, report = self.apply(ports, operation)
            self.assertEqual(3, report['proof']['before_revision'])
            self.assertEqual(3, report['proof']['after_revision'])
        self.assertEqual(3, len(self.versions(ports)))
        self.assertEqual([], fresh.recall(['green'])['items'])

    def test_target_candidate_and_validation_substitution_rejected(self):
        for fault in ('target-current', 'target-missing', 'evidence', 'future', 'source', 'body'):
            ports, _, _ = self.prepare()
            self.apply(ports, 'add'); self.apply(ports, 'update')
            value = deepcopy(ports.prepare_restore()); target = 1
            if fault == 'target-current': target = 2
            if fault == 'target-missing': target = 4
            if fault == 'evidence': value['validation']['evidence_id'] = ports.candidates['add']['validation']['evidence_id']
            if fault == 'future': value['validation']['verified_at'] += 1000
            if fault == 'source': value['provenance'] = deepcopy(ports.candidates['update']['provenance'])
            if fault == 'body': value['body'] = 'PRIVATE unsubstantiated'
            value['validation']['content_digest'] = p.c.content_digest(value)
            before = self.state(ports)
            with self.assertRaises(p.c.ContractError):
                p.GovernanceCore(ports.host(), enabled=True).preview('restore', ports.item_id, value, restore_revision=target)
            self.assertEqual(before, self.state(ports))

    def test_snapshot_drift_before_display_or_during_confirmation(self):
        for timing in ('before', 'during'):
            ports, core, stream, preview = self.ready()
            if timing == 'before':
                self.apply(ports, 'stop'); before = self.state(ports)
                with self.assertRaises(p.c.ContractError): core.authorize(preview)
                self.assertNotIn('restore', [e['preview']['operation'] for e in stream.events])
            else:
                def answer(e):
                    if e['preview']['operation'] == 'restore':
                        stream.answer = None
                        self.apply(ports, 'stop')
                    return e['confirmation'] + '\n'
                stream.answer = answer
                handle = core.authorize(preview); before = self.state(ports)
                with self.assertRaises(p.c.ContractError): core.execute(handle)
                with self.assertRaisesRegex(p.c.ContractError, 'handle-unrecognized-or-consumed'): core.execute(handle)
            self.assertEqual(before, self.state(ports))

    def test_expiry_original_source_root_and_lock_drift(self):
        for fault in ('expiry', 'source', 'root', 'lock'):
            ports, core, stream, preview = self.ready(); before = self.state(ports)
            if fault == 'expiry':
                def expire(e):
                    sample = ports.clock.clock()
                    ports.clock.clock = lambda: replace(sample, utc_seconds=sample.utc_seconds + 301, monotonic_ns=sample.monotonic_ns + 301000000000)
                stream.callback = expire
                with self.assertRaises(p.c.ContractError): core.authorize(preview)
            else:
                handle = core.authorize(preview)
                if fault == 'source':
                    next((ports.reader.repository.root / '.git/objects').glob('*/*')).write_bytes(b'broken')
                    with self.assertRaises(p.c.ContractError): core.execute(handle)
                elif fault == 'root':
                    binding = ports.registry.binding(); ports.registry._binding = replace(binding, directory_identity=(0, 0))
                    with self.assertRaises(p.c.ContractError): core.execute(handle)
                    ports.registry._binding = binding
                else:
                    with p.db.locked(ports.registry.binding(), exclusive=True), self.assertRaises(p.c.ContractError): core.execute(handle)
                with self.assertRaisesRegex(p.c.ContractError, 'handle-unrecognized-or-consumed'): core.execute(handle)
            self.assertEqual(before, self.state(ports))

    def test_old_confirmation_digest_cannot_authorize_restore(self):
        ports, core, stream, preview = self.ready()
        old = stream.events[0]['confirmation']
        stream.answer = lambda _: old + '\n'
        before = self.state(ports)
        with self.assertRaises(p.c.ContractError): core.authorize(preview)
        self.assertEqual(before, self.state(ports))

    def test_transaction_faults_preserve_atomic_versions_proof_and_no_replay(self):
        for stage, expected in (('after-item-write', 'not-applied'), ('before-commit', 'not-applied'), ('after-commit', 'applied')):
            for failure in (OSError(errno.ENOSPC, 'PRIVATE'), sqlite3.OperationalError('PRIVATE'), MemoryError('PRIVATE')):
                ports, core, _, preview = self.ready(); before = self.state(ports)
                handle = core.authorize(preview)
                def checkpoint(actual):
                    if actual == stage: raise failure
                with mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                    if isinstance(failure, MemoryError):
                        with self.assertRaises(MemoryError): core.execute(handle)
                    else: self.assertEqual(expected, core.execute(handle)['result'])
                with self.assertRaises(p.c.ContractError): core.execute(handle)
                fresh = p.GovernanceCore(ports.host(), enabled=True)
                report = fresh.readback(preview['operation_id'], p.c.digest(preview), preview=preview)
                self.assertEqual(expected, report['result'])
                if expected == 'not-applied': self.assertEqual(before, self.state(ports))
                else:
                    self.assertEqual(3, len(self.versions(ports)))
                    self.assertEqual(3, len(self.state(ports)['proofs']))

    def test_output_loss_before_acceptance_and_after_commit_never_retries(self):
        for event, count in (('confirm-operation', 2), ('readback', 3)):
            def fail(e):
                if e['event'] == event and e.get('operation', e.get('preview', {}).get('operation')) == 'restore':
                    raise OSError(errno.ENOSPC, 'PRIVATE')
            code, stream = self.run_pilot(Interaction(callback=fail))
            self.assertEqual(2, code); self.assertNotIn('PRIVATE', stream.getvalue())
            root = Path(next(e['workspace'] for e in stream.events if e['event'] == 'created'))
            with sqlite3.connect(root / 'managed' / p.db.MAIN) as conn:
                self.assertEqual(count, conn.execute('SELECT count(*) FROM versions').fetchone()[0])
                self.assertEqual(count, conn.execute('SELECT count(*) FROM proofs').fetchone()[0])
            self.assertEqual(['add', 'update'], [e['operation'] for e in stream.events if e['event'] == 'verified'])

    def test_proof_insert_failure_preserves_two_versions_and_projection(self):
        ports, core, _, preview = self.ready()
        before = self.state(ports)
        handle = core.authorize(preview)
        original = p.db.connect
        class ProofFailure:
            def __init__(self, connection): self.connection = connection
            def __getattr__(self, name): return getattr(self.connection, name)
            def execute(self, sql, parameters=()):
                if sql.startswith('INSERT INTO proofs'):
                    failure = sqlite3.OperationalError('PRIVATE')
                    failure.sqlite_errorcode = sqlite3.SQLITE_FULL
                    raise failure
                return self.connection.execute(sql, parameters)
        def connect(*args, **kwargs):
            connection = original(*args, **kwargs)
            return ProofFailure(connection) if kwargs.get('writer') else connection
        with mock.patch.object(p.db, 'connect', side_effect=connect):
            self.assertEqual('not-applied', core.execute(handle)['result'])
        self.assertEqual(before, self.state(ports))
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        self.assertEqual('not-applied', fresh.readback(preview['operation_id'], p.c.digest(preview), preview=preview)['result'])

    @unittest.skipUnless(hasattr(os, 'fork'), 'POSIX process fixture')
    def test_process_exit_after_restore_commit_does_not_revive_grant(self):
        ports, _, _ = self.prepare()
        self.apply(ports, 'add'); self.apply(ports, 'update')
        candidate = ports.prepare_restore()
        evidence_path = self.parent / 'restore-operation.json'
        pid = os.fork()
        if pid == 0:
            try:
                ports.clock = p.LocalClock()
                core = p.GovernanceCore(ports.host(), enabled=True)
                preview = core.preview('restore', ports.item_id, candidate, restore_revision=1)
                evidence_path.write_text(json.dumps({'id': preview['operation_id'], 'digest': p.c.digest(preview)}))
                handle = core.authorize(preview)
                def checkpoint(stage):
                    if stage == 'after-commit': os._exit(77)
                core_module._checkpoint = checkpoint
                core.execute(handle)
            except BaseException:
                os._exit(78)
            os._exit(79)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(77, os.waitstatus_to_exitcode(status))
        evidence = json.loads(evidence_path.read_text())
        fresh = p.GovernanceCore(ports.host(), enabled=True)
        self.assertEqual('applied', fresh.readback(evidence['id'], evidence['digest'])['result'])
        self.assertEqual(candidate, fresh.recall(['blue', 'widget'])['items'][0]['version'])
        self.assertEqual([], fresh.recall(['green'])['items'])
        self.assertEqual(3, len(self.versions(ports))); self.assertEqual(3, len(self.state(ports)['proofs']))
        with self.assertRaises(p.c.ContractError): fresh.execute(core_module.ExecutionHandle(evidence['id']))

    def test_postcommit_readback_audit_or_interrupt_is_unknown(self):
        for fault in ('readback', 'audit', 'interrupt'):
            ports, _, stream = self.prepare()
            original, original_audit = p.GovernanceCore.readback, p.GovernanceCore.audit
            def readback(core, *args, **kwargs):
                if fault == 'readback' and len(self.state(ports)['proofs']) == 3: raise p.c.ContractError('state-unknown')
                return original(core, *args, **kwargs)
            def audit(core):
                if fault == 'audit' and len(self.state(ports)['proofs']) == 3: raise p.c.ContractError('authority-unavailable')
                return original_audit(core)
            def checkpoint(stage):
                if fault == 'interrupt' and stage == 'after-commit' and len(self.state(ports)['proofs']) == 3: raise KeyboardInterrupt()
            with mock.patch.object(p, '_prepare', return_value=ports), \
                 mock.patch.object(p.GovernanceCore, 'readback', readback), \
                 mock.patch.object(p.GovernanceCore, 'audit', audit), \
                 mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
                code, stream = self.run_pilot(stream)
            self.assertEqual(130 if fault == 'interrupt' else 2, code)
            self.assertEqual('restore', stream.events[-1]['phase'])
            self.assertEqual('state-unknown', stream.events[-1]['result'])
            self.assertEqual(3, len(self.versions(ports))); self.assertEqual(3, len(self.state(ports)['proofs']))
            self.assertTrue(ports.closed)
            self.assertEqual(['add', 'update'], [e['operation'] for e in stream.events if e['event'] == 'verified'])
