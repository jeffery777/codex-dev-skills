"""Persistent synthetic host fault tests; no real provider/runtime qualification."""
import base64
import os
import json
import pathlib
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_packet_store as packets
import model_packet_supervisor as supervisors

PATCH = b'diff --git a/example.txt b/example.txt\n--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new\n'


class PersistentBackend:
    """Reconstructable fake: runtime and export survive a new Python object."""
    def __init__(self, root):
        self.root = root
        self.launch_fault = None
        self.export_fault = None
        self.before_export = None
        self.inspection_change = {}
        self.export_change = {}
        self.launches = self.exports = self.reads = 0

    def _path(self, binding, suffix):
        return self.root/(binding['runtime_id']+suffix)

    def _write(self, path, value):
        with path.open('w') as stream:
            stream.write(json.dumps(value)); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def launch(self, binding):
        self.launches += 1
        path = self._path(binding, '.runtime')
        if path.exists():
            raise AssertionError('duplicate launch')
        self._write(path, {'binding': binding, 'state': 'stopped'})
        if self.launch_fault:
            raise self.launch_fault

    def inspect(self, binding):
        runtime = json.loads(self._path(binding, '.runtime').read_text())
        return {'binding': runtime['binding'], 'runtime_identity_sha256': packets.digest(packets.canonical(runtime['binding'])),
                'state': runtime['state'], 'external_effects': 'excluded',
                'evidence_sha256': 'e'*64, **self.inspection_change}

    def export_patch(self, binding, limit):
        self.exports += 1
        if self.before_export:
            self.before_export(binding)
        reply = {'binding': binding, 'patch': PATCH, 'patch_sha256': packets.digest(PATCH), **self.export_change}
        durable = {**reply, 'patch': base64.b64encode(reply['patch']).decode()}
        self._write(self._path(binding, '.export'), durable)
        if self.export_fault:
            raise self.export_fault
        return reply

    def read_sealed_patch(self, binding, limit):
        self.reads += 1
        value = json.loads(self._path(binding, '.export').read_text())
        value['patch'] = base64.b64decode(value['patch'])
        return value


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.store = packets.PacketStore(self.root, 'packet')
        self.store.prepare('a'*64)
        self.backend = PersistentBackend(self.root)
        self.supervisor = self.new_supervisor()

    def new_supervisor(self, backend=None, **changes):
        return supervisors.PacketSupervisor(packets.PacketStore(self.root, 'packet'), backend or self.backend,
            **{'host_id': 'host', 'backend_id': 'synthetic', 'policy_sha256': 'f'*64, **changes})

    def start(self):
        return self.supervisor.start('attempt', 'b'*64, 'c'*64, expected_revision=0,
            source_sha256='1'*64, scope_sha256='2'*64, acceptance_sha256='3'*64)

    def reserve(self):
        return self.store.reserve_runtime('attempt', 'b'*64, 'c'*64, expected_revision=0,
            source_sha256='1'*64, scope_sha256='2'*64, acceptance_sha256='3'*64,
            host_id='host', backend_id='synthetic', policy_sha256='f'*64, runtime_id='runtime-test')

    def binding(self):
        return self.store.supervisor_snapshot('attempt')[1]['binding']

    def assert_unknown(self, result):
        self.assertEqual(result['outcome'], 'unknown')
        ledger, _ = self.store.supervisor_snapshot('attempt')
        self.assertEqual(ledger['attempts'][-1]['status'], 'unknown')
        self.assertIsNone(ledger['checkpoint'])

    def test_candidate_is_valid_patch_bound_and_reconstructable(self):
        result = self.start()
        self.assertEqual(result['outcome'], 'integration-candidate')
        self.assertEqual(result['patch'], PATCH)
        fresh = PersistentBackend(self.root)
        recovered = self.new_supervisor(fresh).reconcile('attempt')
        self.assertEqual(recovered, result)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 0))
        self.assertEqual(self.store.read_checkpoint()[1], PATCH)

    def test_empty_noop_start_restart_and_candidate_keep_all_bindings(self):
        self.backend.export_change = {'patch': b'', 'patch_sha256': packets.digest(b'')}
        with mock.patch.object(supervisors.subprocess, 'run', side_effect=AssertionError('no parser needed')):
            result = self.start()
            self.assertEqual(result['outcome'], 'integration-candidate')
            self.assertEqual(result['patch'], b'')
            self.assertEqual(result['patch_sha256'], packets.digest(b''))
            fresh = PersistentBackend(self.root)
            recovered = self.new_supervisor(fresh).reconcile('attempt')
            self.assertEqual(recovered, result)
            candidate = self.new_supervisor(fresh).admit_candidate('attempt',
                source_sha256='1'*64, scope_sha256='2'*64, acceptance_sha256='3'*64)
            self.assertEqual(candidate, result)
            self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 0))
        ledger, patch = self.store.read_checkpoint()
        self.assertEqual(patch, b'')
        self.assertIsNotNone(ledger['checkpoint'])
        with self.assertRaisesRegex(packets.PacketError, 'parent-binding-drift'):
            self.supervisor.admit_candidate('attempt', source_sha256='0'*64,
                scope_sha256='2'*64, acceptance_sha256='3'*64)
        self.backend.inspection_change = {'state': 'running'}
        with self.assertRaisesRegex(packets.PacketError, 'runtime-proof-unavailable'):
            self.supervisor.reconcile('attempt')

    def test_empty_noop_export_still_rejects_quarantine_and_digest_mismatch(self):
        import time
        class Adapter:
            def readback_isolation(self, binding):
                now = int(time.time())
                return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                        'evidence_sha256': 'f'*64, 'observed_at': now, 'expires_at': now+30}
        self.backend.export_change = {'patch': b'', 'patch_sha256': packets.digest(b'')}
        def quarantine(_):
            ledger, _ = self.store.supervisor_snapshot('attempt')
            self.store.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fake')
        self.backend.before_export = quarantine
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'fake': Adapter()}):
            with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
                self.start()
        self.assertIsNone(self.store.supervisor_snapshot('attempt')[0]['checkpoint'])
        with self.assertRaisesRegex(packets.PacketError, 'digest-drift'):
            self.supervisor._export_reply(self.binding(),
                {'binding': self.binding(), 'patch': b'', 'patch_sha256': '0'*64})

    def test_replayed_start_and_concurrent_start_never_launch_twice(self):
        self.start()
        with self.assertRaisesRegex(packets.PacketError, 'already-exists'):
            self.start()
        with self.store.locked():
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                self.start()
        self.assertEqual(self.backend.launches, 1)

    def test_two_concurrent_hosts_have_at_most_one_launch(self):
        barrier = threading.Barrier(2)
        errors = []
        def run():
            barrier.wait()
            try:
                self.new_supervisor().start('attempt', 'b'*64, 'c'*64, expected_revision=0,
                    source_sha256='1'*64, scope_sha256='2'*64, acceptance_sha256='3'*64)
            except packets.PacketError as error:
                errors.append(str(error))
        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
            self.assertFalse(thread.is_alive())
        self.assertLessEqual(self.backend.launches, 1)
        self.assertLessEqual(len(list(self.root.glob('*.runtime'))), 1)
        self.assertTrue(errors)
        fresh = PersistentBackend(self.root)
        self.new_supervisor(fresh).reconcile('attempt')
        self.assertEqual(fresh.launches, 0)

    def test_runtime_binding_is_durable_before_launch(self):
        original = self.backend.launch
        def inspect_before_launch(binding):
            ledger = json.loads((self.root/'packet/ledger.json').read_text())
            record = ledger['supervisors']['attempt']
            self.assertEqual(record['stage'], 'launch-intent')
            self.assertEqual(record['binding'], binding)
            self.assertEqual(ledger['schema_version'], 3)
            original(binding)
        with mock.patch.object(self.backend, 'launch', side_effect=inspect_before_launch):
            self.start()

    def test_packet_lock_fences_quarantine_during_launch_call(self):
        original = self.backend.launch
        def launch(binding):
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                self.store.quarantine('attempt', expected_revision=2, isolation_adapter_id='missing')
            original(binding)
        with mock.patch.object(self.backend, 'launch', side_effect=launch):
            self.start()
        self.assertEqual(self.backend.launches, 1)

    def test_fenced_launch_intent_is_rejected_before_backend_call(self):
        import time
        class Adapter:
            def readback_isolation(self, binding):
                now = int(time.time())
                return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                        'evidence_sha256': 'f'*64, 'observed_at': now, 'expires_at': now+30}
        original = self.supervisor.store.supervisor_transition
        def fence(*args, **kwargs):
            ledger, record = original(*args, **kwargs)
            if record['stage'] == 'launch-intent':
                self.store.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fake')
            return ledger, record
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'fake': Adapter()}):
            with mock.patch.object(self.supervisor.store, 'supervisor_transition', side_effect=fence):
                with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
                    self.start()
        self.assertEqual(self.backend.launches, 0)
        self.assertIsNone(self.store.supervisor_snapshot('attempt')[0]['checkpoint'])

    def test_reserved_crash_never_launches_on_restart(self):
        self.reserve()
        fresh = PersistentBackend(self.root)
        self.assert_unknown(self.new_supervisor(fresh).reconcile('attempt'))
        self.assertEqual(fresh.launches, 0)

    def test_crash_at_intent_before_launch_is_unknown_not_retry(self):
        original = self.store._write
        # start uses a distinct PacketStore object; patch the class write.
        def crash(store, fd, ledger):
            original(fd, ledger)
            if ledger.get('supervisors', {}).get('attempt', {}).get('stage') == 'launch-intent':
                raise SystemExit('crash after durable launch intent')
        with mock.patch.object(packets.PacketStore, '_write', autospec=True, side_effect=crash):
            with self.assertRaises(SystemExit):
                self.start()
        self.assert_unknown(self.new_supervisor(PersistentBackend(self.root)).reconcile('attempt'))
        self.assertEqual(self.backend.launches, 0)

    def test_lost_launch_reply_reconciles_original_runtime(self):
        self.backend.launch_fault = OSError('lost reply')
        self.assert_unknown(self.start())
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['outcome'], 'integration-candidate')
        self.assertEqual(self.backend.launches, 1)
        self.assertEqual((fresh.launches, fresh.exports), (0, 1))

    def test_lost_launch_and_export_unknown_history_survives_resolution(self):
        self.backend.launch_fault = OSError('sensitive error excluded from record')
        self.assert_unknown(self.start())
        first_ledger, first = self.store.supervisor_snapshot('attempt')
        first_event = dict(first['observations'][0])
        self.assertEqual(first_event['reason'], 'launch-reply-unknown')
        self.assertEqual(first_event['stage'], 'launch-intent')
        self.assertEqual(first_event['binding_sha256'], packets.digest(packets.canonical(first['binding'])))
        self.assertEqual(first_event['identity_sha256'], 'a'*64)
        self.assertEqual(first_event['runtime_id'], first['binding']['runtime_id'])
        self.assertEqual(first_event['revision'], first_ledger['revision'])
        fresh = PersistentBackend(self.root)
        fresh.export_fault = OSError('lost export')
        self.assert_unknown(self.new_supervisor(fresh).reconcile('attempt'))
        second = self.store.supervisor_snapshot('attempt')[1]
        self.assertEqual(second['observations'][0], first_event)
        self.assertEqual(second['observations'][1]['reason'], 'export-reply-unknown')
        second_event = dict(second['observations'][1])
        recovered = self.new_supervisor(PersistentBackend(self.root)).reconcile('attempt')
        final = packets.PacketStore(self.root, 'packet').supervisor_snapshot('attempt')[1]
        self.assertEqual(final['observations'][:2], [first_event, second_event])
        resolution = final['observations'][2]
        self.assertEqual(resolution['kind'], 'resolved')
        self.assertEqual(resolution['reason'], 'checkpoint-published')
        self.assertEqual(resolution['checkpoint_sha256'], recovered['checkpoint_sha256'])
        self.assertEqual(resolution['evidence_sha256'], recovered['evidence_sha256'])
        self.assertNotIn('sensitive error', json.dumps(final))
        self.assertEqual(sorted(event['revision'] for event in final['observations']),
                         [event['revision'] for event in final['observations']])

    def test_identical_unknown_observation_is_deduplicated_without_revision_change(self):
        self.backend.inspection_change = {'state': 'running'}
        self.assert_unknown(self.start())
        before = (self.root/'packet/ledger.json').read_bytes()
        self.assert_unknown(self.supervisor.reconcile('attempt'))
        self.assertEqual((self.root/'packet/ledger.json').read_bytes(), before)
        self.assertEqual(len(self.store.supervisor_snapshot('attempt')[1]['observations']), 1)

    def test_observation_bound_preserves_history_and_refuses_publication(self):
        self.backend.inspection_change = {'state': 'running'}
        self.assert_unknown(self.start())
        before = (self.root/'packet/ledger.json').read_bytes()
        with mock.patch.object(packets, 'MAX_SUPERVISOR_OBSERVATIONS', 1):
            with self.assertRaisesRegex(packets.PacketError, 'observation-bound'):
                self.store.observe_supervisor_unknown('attempt', 'export-reply-unknown')
            self.assertEqual((self.root/'packet/ledger.json').read_bytes(), before)
            self.backend.inspection_change = {}
            with self.assertRaisesRegex(packets.PacketError, 'observation-bound'):
                self.supervisor.reconcile('attempt')
            ledger, record = self.store.supervisor_snapshot('attempt')
            self.assertIsNone(ledger['checkpoint'])
            self.assertEqual(record['observations'][0]['reason'], 'runtime-proof-unavailable')
            self.assertEqual(record['stage'], 'sealed')
            self.assertEqual(len(record['observations']), 1)
        # Raising the bound does not erase history or relaunch/export; recovery
        # reads the original seal and appends a resolution.
        fresh = PersistentBackend(self.root)
        self.new_supervisor(fresh).reconcile('attempt')
        self.assertEqual((fresh.launches, fresh.exports), (0, 0))
        self.assertEqual(len(self.store.supervisor_snapshot('attempt')[1]['observations']), 2)

    def test_legacy_supervisor_record_is_readable_without_silent_history_upgrade(self):
        self.reserve()
        with self.store.locked() as fd:
            ledger = self.store._read(fd)
            record = ledger['supervisors']['attempt']
            record['schema_version'] = 1
            record.pop('observations')
            self.store._write(fd, ledger)
        legacy = self.store.supervisor_snapshot('attempt')[1]
        self.assertEqual(legacy['schema_version'], 1)
        before = (self.root/'packet/ledger.json').read_bytes()
        with self.assertRaisesRegex(packets.PacketError, 'schema-upgrade-required'):
            self.supervisor.reconcile('attempt')
        self.assertEqual((self.root/'packet/ledger.json').read_bytes(), before)
        self.assertNotIn('observations', self.store.supervisor_snapshot('attempt')[1])

    def test_crash_after_launch_before_receipt_transition(self):
        self.backend.launch_fault = SystemExit('process crash')
        with self.assertRaises(SystemExit):
            self.start()
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['outcome'], 'integration-candidate')
        self.assertEqual(fresh.launches, 0)

    def test_lost_export_reply_reads_original_seal_without_export_again(self):
        self.backend.export_fault = OSError('lost export reply')
        self.assert_unknown(self.start())
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['patch'], PATCH)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 1))

    def test_crash_after_export_reply_before_host_seal(self):
        self.backend.export_fault = SystemExit('crash')
        with self.assertRaises(SystemExit):
            self.start()
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['patch'], PATCH)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 1))

    def test_export_intent_without_artifact_remains_unknown(self):
        with mock.patch.object(self.backend, 'export_patch', side_effect=SystemExit('before export')):
            with self.assertRaises(SystemExit):
                self.start()
        fresh = PersistentBackend(self.root)
        self.assert_unknown(self.new_supervisor(fresh).reconcile('attempt'))
        self.assertEqual((fresh.launches, fresh.exports), (0, 0))

    def test_crash_after_artifact_before_seal_ledger_recovers_local_artifact(self):
        original = packets.PacketStore._write
        def crash(store, fd, ledger):
            if ledger.get('supervisors', {}).get('attempt', {}).get('stage') == 'sealed':
                raise SystemExit('crash before sealing ledger')
            return original(store, fd, ledger)
        with mock.patch.object(packets.PacketStore, '_write', autospec=True, side_effect=crash):
            with self.assertRaises(SystemExit):
                self.start()
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['patch'], PATCH)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 0))

    def test_crash_during_checkpoint_commit_reuses_sealed_artifact(self):
        original = packets.PacketStore._write
        def crash(store, fd, ledger):
            if ledger.get('supervisors', {}).get('attempt', {}).get('stage') == 'published':
                raise SystemExit('crash before checkpoint ledger')
            return original(store, fd, ledger)
        with mock.patch.object(packets.PacketStore, '_write', autospec=True, side_effect=crash):
            with self.assertRaises(SystemExit):
                self.start()
        fresh = PersistentBackend(self.root)
        self.assertEqual(self.new_supervisor(fresh).reconcile('attempt')['patch'], PATCH)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 0))

    def test_running_external_effects_missing_runtime_and_handle_drift_do_not_export(self):
        for change in [{'state': 'running'}, {'external_effects': 'unknown'},
                       {'runtime_identity_sha256': '0'*64}, {'binding': {}}]:
            with self.subTest(change=change):
                self.backend.inspection_change = change
                try:
                    self.store.supervisor_snapshot('attempt')
                except packets.PacketError:
                    result = self.start()
                else:
                    result = self.supervisor.reconcile('attempt')
                self.assert_unknown(result)
                self.assertEqual(self.backend.exports, 0)
        self.backend.inspection_change = {}
        self.backend._path(self.binding(), '.runtime').unlink()
        self.assert_unknown(self.supervisor.reconcile('attempt'))
        self.assertEqual(self.backend.launches, 1)

    def test_host_backend_policy_drift_is_rejected(self):
        self.backend.inspection_change = {'state': 'running'}
        self.start()
        for change in [{'host_id': 'other'}, {'backend_id': 'other'}, {'policy_sha256': '0'*64}]:
            with self.assertRaisesRegex(packets.PacketError, 'host-policy-drift'):
                self.new_supervisor(**change).reconcile('attempt')
        self.assertEqual(self.backend.launches, 1)

    def test_resumed_runtime_during_export_does_not_publish(self):
        self.backend.before_export = lambda _: self.backend.inspection_change.update(state='running')
        self.assert_unknown(self.start())
        self.assertIsNone(self.store.read_checkpoint()[0]['checkpoint'])

    def test_quarantine_during_export_fences_patch(self):
        import time
        def isolated(binding):
            now = int(time.time())
            return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                    'evidence_sha256': 'f'*64, 'observed_at': now, 'expires_at': now+30}
        class Adapter:
            readback_isolation = staticmethod(isolated)
        def quarantine(_):
            ledger, _ = self.store.supervisor_snapshot('attempt')
            self.store.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fake')
        self.backend.before_export = quarantine
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'fake': Adapter()}):
            with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
                self.start()
        ledger, _ = self.store.supervisor_snapshot('attempt')
        self.assertIsNone(ledger['checkpoint'])
        self.assertEqual(ledger['attempts'][-1]['status'], 'quarantined')
        self.assertEqual(list((self.root/'packet').glob('sealed-*.patch')), [])

    def test_successor_generation_after_export_rejects_original_result(self):
        import time
        class Adapter:
            def readback_isolation(self, binding):
                now = int(time.time())
                return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                        'evidence_sha256': 'f'*64, 'observed_at': now, 'expires_at': now+30}
        def successor(_):
            ledger, _ = self.store.supervisor_snapshot('attempt')
            ledger = self.store.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fake')
            self.store.claim('successor', 'b'*64, 'c'*64, expected_revision=ledger['revision'])
        self.backend.before_export = successor
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'fake': Adapter()}):
            with self.assertRaises(packets.PacketError):
                self.start()
            with self.assertRaisesRegex(packets.PacketError, 'stale-writer-result-rejected'):
                self.supervisor.reconcile('attempt')
        self.assertEqual(self.backend.launches, 1)
        self.assertIsNone(self.store.supervisor_snapshot('attempt')[0]['checkpoint'])

    def test_policy_binding_changed_during_export_fails_cas(self):
        def drift(_):
            with self.store.locked() as fd:
                ledger = self.store._read(fd)
                ledger['supervisors']['attempt']['binding']['policy_sha256'] = '0'*64
                ledger['revision'] += 1
                self.store._write(fd, ledger)
        self.backend.before_export = drift
        with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
            self.start()
        self.assertIsNone(self.store.read_checkpoint()[0]['checkpoint'])

    def test_artifact_symlink_and_same_digest_manifest_replacement_rejected(self):
        self.start()
        prefix = self.root/'packet'/('sealed-'+self.binding()['runtime_id'])
        original = pathlib.Path(str(prefix)+'.patch')
        foreign = self.root/'foreign.patch'; foreign.write_bytes(PATCH)
        original.unlink(); original.symlink_to(foreign)
        with self.assertRaises((packets.PacketError, OSError, ValueError)):
            self.supervisor.reconcile('attempt')
        original.unlink(); original.write_bytes(PATCH); original.chmod(0o600)
        manifest = pathlib.Path(str(prefix)+'.json')
        value = json.loads(manifest.read_text())
        value['evidence_sha256'] = '0'*64
        manifest.write_bytes(packets.canonical(value))
        with self.assertRaisesRegex(packets.PacketError, 'binding-drift'):
            self.supervisor.reconcile('attempt')

    def test_oversized_digest_conflict_and_nonpatch_export_fail_closed(self):
        self.backend.export_change = {'patch': b'not a patch', 'patch_sha256': packets.digest(b'not a patch')}
        self.assert_unknown(self.start())
        fresh = PersistentBackend(self.root)
        self.assert_unknown(self.new_supervisor(fresh).reconcile('attempt'))
        self.assertEqual(fresh.exports, 0)
        with self.assertRaises(packets.PacketError):
            supervisors.validate_patch(PATCH+b'\0')
        with mock.patch.object(packets, 'MAX_PATCH', 1):
            with self.assertRaises(packets.PacketError):
                supervisors.validate_patch(PATCH)
        self.backend.export_change = {'patch_sha256': '0'*64}
        with self.assertRaisesRegex(packets.PacketError, 'digest-drift'):
            self.supervisor._export_reply(self.binding(), {'binding': self.binding(), 'patch': PATCH, 'patch_sha256': '0'*64})

    def test_candidate_parent_source_scope_acceptance_drift_rejected(self):
        self.start()
        values = {'source_sha256': '1'*64, 'scope_sha256': '2'*64, 'acceptance_sha256': '3'*64}
        self.assertEqual(self.supervisor.admit_candidate('attempt', **values)['patch'], PATCH)
        for key in values:
            with self.assertRaisesRegex(packets.PacketError, 'parent-binding-drift'):
                self.supervisor.admit_candidate('attempt', **{**values, key: '0'*64})

    def test_checkpoint_patch_or_manifest_missing_and_tamper_reject_replay_admission(self):
        result = self.start()
        checkpoint = result['checkpoint_sha256']
        files = {suffix: self.root/'packet'/(checkpoint+suffix) for suffix in ['.patch', '.json']}
        originals = {suffix: path.read_bytes() for suffix, path in files.items()}
        fresh = PersistentBackend(self.root)
        supervisor = self.new_supervisor(fresh)
        for suffix, path in files.items():
            for change in ['missing', 'tamper']:
                with self.subTest(suffix=suffix, change=change):
                    if change == 'missing':
                        path.unlink()
                    else:
                        path.write_bytes(b'corrupt checkpoint')
                    for operation in [lambda: supervisor.reconcile('attempt'),
                        lambda: supervisor.admit_candidate('attempt', source_sha256='1'*64,
                            scope_sha256='2'*64, acceptance_sha256='3'*64)]:
                        with self.assertRaises((packets.PacketError, OSError, ValueError)):
                            operation()
                    path.write_bytes(originals[suffix]); path.chmod(0o600)
        self.assertEqual((fresh.launches, fresh.exports, fresh.reads), (0, 0, 0))

    def test_foreign_checkpoint_transplant_cannot_replace_supervisor_binding(self):
        result = self.start()
        foreign = packets.PacketStore(self.root, 'foreign')
        foreign.prepare('4'*64)
        foreign.claim('attempt', 'b'*64, 'c'*64, expected_revision=0)
        # Even an identical patch/evidence has a different packet identity.
        other = foreign.publish_checkpoint('attempt', PATCH, 'e'*64)
        for suffix in ['.patch', '.json']:
            (self.root/'packet'/(result['checkpoint_sha256']+suffix)).write_bytes(
                (self.root/'foreign'/(other['checkpoint']+suffix)).read_bytes())
        with self.assertRaisesRegex(packets.PacketError, 'checkpoint-manifest-drift'):
            self.supervisor.reconcile('attempt')
        # Transplant the ledger pointer too: binding/evidence must still match
        # this supervisor's canonical checkpoint identity before file readback.
        with self.store.locked() as fd:
            ledger = self.store._read(fd)
            ledger['checkpoint'] = other['checkpoint']
            ledger['attempts'][-1]['checkpoint_sha256'] = other['checkpoint']
            ledger['supervisors']['attempt']['observations'][-1]['checkpoint_sha256'] = other['checkpoint']
            ledger['revision'] += 1
            self.store._write(fd, ledger)
        with self.assertRaisesRegex(packets.PacketError, 'supervisor-checkpoint-binding-drift'):
            self.supervisor.admit_candidate('attempt', source_sha256='1'*64,
                scope_sha256='2'*64, acceptance_sha256='3'*64)

    def test_candidate_readback_fences_successor_and_holds_lock(self):
        self.start()
        ledger, record = self.store.supervisor_snapshot('attempt')
        original = self.store._checkpoint_bytes
        def read(fd, checkpoint, snapshot):
            self.assertFalse(os.get_inheritable(fd))
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                self.store.claim('other', 'b'*64, 'c'*64, expected_revision=snapshot['revision'])
            return original(fd, checkpoint, snapshot)
        with mock.patch.object(self.store, '_checkpoint_bytes', side_effect=read):
            observed, _, patch = self.store.read_supervisor_candidate('attempt',
                expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))
        self.assertEqual(patch, PATCH)
        self.store.claim('successor', 'b'*64, 'c'*64, expected_revision=observed['revision'])
        with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
            self.store.read_supervisor_candidate('attempt', expected_revision=ledger['revision'],
                record_sha256=packets.digest(packets.canonical(record)))

    def test_local_sealed_digest_tamper_is_not_accepted(self):
        self.start()
        path = self.root/'packet'/('sealed-'+self.binding()['runtime_id']+'.patch')
        path.write_bytes(PATCH+b'tamper')
        with self.assertRaisesRegex(packets.PacketError, 'digest-drift'):
            self.supervisor.reconcile('attempt')


if __name__ == '__main__':
    unittest.main()
