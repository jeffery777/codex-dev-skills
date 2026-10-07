"""Durability/replay tests only; no runtime quiescence qualification."""
import json
import pathlib
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_packet_store as packets


class PacketStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.store = packets.PacketStore(self.root, 'packet-1')
        self.store.prepare('a'*64)

    def claim(self, attempt='attempt-1', revision=0):
        return self.store.claim(attempt, 'b'*64, 'c'*64, expected_revision=revision)

    def test_replay_survives_reopen_without_revision_or_clock_reset(self):
        self.assertTrue(self.claim()['claimed'])
        fresh = packets.PacketStore(self.root, 'packet-1')
        result = fresh.claim('attempt-1', 'b'*64, 'c'*64, expected_revision=0)
        self.assertFalse(result['claimed'])
        self.assertEqual(result['attempt']['status'], 'claimed')
        with self.assertRaisesRegex(packets.PacketError, 'predecessor-outcome-unknown'):
            fresh.claim('attempt-2', 'b'*64, 'c'*64, expected_revision=1)

    def test_checkpoint_from_another_packet_cannot_be_adopted(self):
        self.claim()
        foreign = self.store.publish_checkpoint('attempt-1', b'foreign patch', 'd'*64)
        other = packets.PacketStore(self.root, 'packet-2')
        other.prepare('a'*64)
        other.claim('attempt-1', 'b'*64, 'c'*64, expected_revision=0)
        folder = self.root / 'packet-2'
        for suffix in ['.json', '.patch']:
            (folder / (foreign['checkpoint'] + suffix)).write_bytes(
                (self.root / 'packet-1' / (foreign['checkpoint'] + suffix)).read_bytes())
            (folder / (foreign['checkpoint'] + suffix)).chmod(0o600)
        with other.locked() as fd:
            ledger = other._read(fd)
            ledger['attempts'][0]['status'] = 'checkpointed'
            ledger['attempts'][0]['checkpoint_sha256'] = foreign['checkpoint']
            ledger['attempts'][0]['execution_outcome'] = 'checkpoint-captured'
            ledger['checkpoint'] = foreign['checkpoint']
            other._write(fd, ledger)
        with self.assertRaisesRegex(packets.PacketError, 'checkpoint-authority-binding-mismatch'):
            other.read_checkpoint()

    def test_same_identifier_different_request_or_target_is_rejected(self):
        self.claim()
        for request, target in [('d'*64, 'c'*64), ('b'*64, 'd'*64)]:
            with self.assertRaisesRegex(packets.PacketError, 'attempt-identity-conflict'):
                self.store.claim('attempt-1', request, target, expected_revision=1)

    def test_unknown_retained_and_does_not_unlock_next_attempt(self):
        self.claim()
        ledger = self.store.retain_unknown('attempt-1')
        self.assertEqual(ledger['attempts'][-1]['status'], 'unknown')
        self.assertEqual(self.store.retain_unknown('attempt-1'), ledger)
        with self.assertRaisesRegex(packets.PacketError, 'predecessor-outcome-unknown'):
            self.claim('attempt-2', ledger['revision'])

    def test_checkpoint_preserves_partial_changes_and_lineage(self):
        self.claim()
        ledger = self.store.publish_checkpoint('attempt-1', b'synthetic partial patch', 'd'*64)
        fresh = packets.PacketStore(self.root, 'packet-1')
        observed, patch = fresh.read_checkpoint()
        self.assertEqual(observed, ledger)
        self.assertEqual(patch, b'synthetic partial patch')
        self.assertEqual(self.store.publish_checkpoint('attempt-1', patch, 'd'*64), ledger)
        attempt = self.claim('attempt-2', ledger['revision'])['attempt']
        self.assertEqual(attempt['predecessor_sha256'], ledger['checkpoint'])

    def test_checkpoint_conflict_never_overwrites_existing_artifact(self):
        self.claim()
        self.store.publish_checkpoint('attempt-1', b'first', 'd'*64)
        with self.assertRaisesRegex(packets.PacketError, 'checkpoint-identity-conflict'):
            self.store.publish_checkpoint('attempt-1', b'other', 'd'*64)
        self.assertEqual(self.store.read_checkpoint()[1], b'first')

    def test_crash_before_ledger_publication_reuses_exact_immutable_artifacts(self):
        self.claim()
        original = self.store._write
        with mock.patch.object(self.store, '_write', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        self.assertEqual(self.claim()['attempt']['status'], 'claimed')
        with mock.patch.object(self.store, '_write', wraps=original):
            self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        self.assertEqual(self.store.read_checkpoint()[1], b'partial')

    def test_revision_conflict_and_identity_conflict(self):
        with self.assertRaisesRegex(packets.PacketError, 'packet-revision-conflict'):
            self.claim(revision=5)
        with self.assertRaisesRegex(packets.PacketError, 'packet-identity-conflict'):
            self.store.prepare('f'*64)

    def test_busy_lock_does_not_wait_or_claim(self):
        with self.store.locked():
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                self.claim()
        self.assertEqual(self.store.read_checkpoint()[0]['attempts'], [])

    def test_duplicate_json_or_corrupt_lineage_fail_closed(self):
        path = self.root/'packet-1/ledger.json'
        raw = path.read_bytes()
        for bad in [b'{"schema_version":1,"schema_version":1}', b'{}']:
            path.write_bytes(bad)
            with self.assertRaises(packets.PacketError):
                self.claim()
        path.write_bytes(raw)
        self.claim()
        ledger = json.loads(path.read_bytes())
        ledger['attempts'][0]['predecessor_sha256'] = 'e'*64
        path.write_text(json.dumps(ledger))
        with self.assertRaises(packets.PacketError):
            self.claim()

    def test_patch_drift_is_not_used_as_handoff(self):
        self.claim()
        ledger = self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        (self.root/'packet-1'/(ledger['checkpoint']+'.patch')).write_bytes(b'drift')
        with self.assertRaisesRegex(packets.PacketError, 'checkpoint-patch-drift'):
            self.store.read_checkpoint()
        with self.assertRaisesRegex(packets.PacketError, 'checkpoint-patch-drift'):
            self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)

    def test_missing_current_checkpoint_cannot_reset_lineage(self):
        self.claim()
        self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        path = self.root/'packet-1/ledger.json'
        value = json.loads(path.read_bytes()); value['checkpoint'] = None
        path.write_text(json.dumps(value))
        with self.assertRaises(packets.PacketError):
            self.store.read_checkpoint()
        with self.assertRaises(packets.PacketError):
            self.claim('attempt-2', value['revision'])

    def test_crash_with_partial_staging_file_does_not_poison_final_name(self):
        self.claim()
        original = packets.os.link
        def crash(source, destination, **kwargs):
            fd = kwargs['src_dir_fd']
            corrupt = packets.os.open(source, packets.os.O_WRONLY, dir_fd=fd)
            packets.os.ftruncate(corrupt, 1); packets.os.close(corrupt)
            raise OSError('synthetic crash before atomic publish')
        with mock.patch.object(packets.os, 'link', side_effect=crash):
            with self.assertRaises(OSError):
                self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        with mock.patch.object(packets.os, 'link', wraps=original):
            self.store.publish_checkpoint('attempt-1', b'partial', 'd'*64)
        self.assertEqual(self.store.read_checkpoint()[1], b'partial')

    def test_packet_child_git_directory_is_rejected(self):
        (self.root/'packet-1/.git').mkdir()
        with self.assertRaisesRegex(packets.PacketError, 'repository-controlled-packet'):
            self.claim()

    def test_symlink_nonprivate_and_git_roots_rejected(self):
        alias = self.root/'alias'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises((packets.PacketError, OSError, ValueError)):
            packets.PacketStore(alias, 'other').prepare('a'*64)
        self.root.chmod(0o755)
        with self.assertRaisesRegex(packets.PacketError, 'private'):
            self.store.prepare('a'*64)
        self.root.chmod(0o700)
        (self.root/'.git').mkdir()
        with self.assertRaises(ValueError):
            self.store.prepare('a'*64)

    def test_invalid_identifier_and_patch_bound(self):
        for identifier in ['../outside', 'a/b', '', '.git']:
            with self.assertRaises(packets.PacketError):
                packets.PacketStore(self.root, identifier)
        self.claim()
        with mock.patch.object(packets, 'MAX_PATCH', 1):
            with self.assertRaisesRegex(packets.PacketError, 'invalid-packet-patch'):
                self.store.publish_checkpoint('attempt-1', b'xx', 'd'*64)

    def isolated(self, binding):
        now = int(time.time())
        return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                'evidence_sha256': 'f'*64, 'observed_at': now, 'expires_at': now+30}

    def test_quarantine_without_qualified_host_does_not_clear_unknown(self):
        self.claim(); self.store.retain_unknown('attempt-1')
        with self.assertRaisesRegex(packets.PacketError, 'qualified-isolation-adapter-unavailable'):
            self.store.quarantine('attempt-1', expected_revision=2, isolation_adapter_id='missing')
        self.assertEqual(self.store.read_checkpoint()[0]['attempts'][-1]['status'], 'unknown')

    def test_isolated_unknown_recovers_previous_checkpoint_and_fences_late_result(self):
        self.claim(); first = self.store.publish_checkpoint('attempt-1', b'trusted checkpoint', 'd'*64)
        self.claim('attempt-2', first['revision']); pending = self.store.retain_unknown('attempt-2')
        adapter = SimpleNamespace(readback_isolation=mock.Mock(side_effect=self.isolated))
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'synthetic': adapter}):
            isolated = self.store.quarantine('attempt-2', expected_revision=pending['revision'], isolation_adapter_id='synthetic')
            self.assertEqual(isolated['attempts'][-1]['execution_outcome'], 'unknown')
            self.assertEqual(isolated['checkpoint'], first['checkpoint'])
            with self.assertRaisesRegex(packets.PacketError, 'stale-writer-result-rejected'):
                self.store.publish_checkpoint('attempt-2', b'late untrusted edits', 'd'*64)
            successor = self.claim('attempt-3', isolated['revision'])
            self.assertEqual(successor['attempt']['generation'], 3)
            self.assertEqual(successor['attempt']['predecessor_sha256'], first['checkpoint'])
            self.assertEqual(self.store.read_checkpoint()[1], b'trusted checkpoint')
            with self.assertRaisesRegex(packets.PacketError, 'packet-attempt-mismatch'):
                self.store.publish_checkpoint('attempt-2', b'late edits', 'd'*64)
        self.assertEqual(adapter.readback_isolation.call_count, 3)

    def test_revoked_isolation_blocks_successor_even_after_persisted_quarantine(self):
        self.claim()
        adapter = SimpleNamespace(readback_isolation=self.isolated)
        with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'synthetic': adapter}):
            ledger = self.store.quarantine('attempt-1', expected_revision=1, isolation_adapter_id='synthetic')
        with self.assertRaisesRegex(packets.PacketError, 'qualified-isolation-adapter-unavailable'):
            self.claim('attempt-2', ledger['revision'])
        self.assertEqual(len(self.store.read_checkpoint()[0]['attempts']), 1)

    def test_revoked_or_stale_isolation_after_claim_blocks_artifact_publication(self):
        for stale in [False, True]:
            with self.subTest(stale=stale):
                store = packets.PacketStore(self.root, 'stale' if stale else 'revoked')
                store.prepare('a'*64)
                store.claim('old', 'b'*64, 'c'*64, expected_revision=0)
                adapter = SimpleNamespace(readback_isolation=mock.Mock(side_effect=self.isolated))
                with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'synthetic': adapter}):
                    ledger = store.quarantine('old', expected_revision=1, isolation_adapter_id='synthetic')
                    store.claim('new', 'b'*64, 'c'*64, expected_revision=ledger['revision'])
                    if stale:
                        adapter.readback_isolation.side_effect = lambda binding: {**self.isolated(binding), 'observed_at': 0}
                    else:
                        packets.PACKET_ISOLATION_ADAPTERS.pop('synthetic')
                    before = (self.root / store.packet_id / 'ledger.json').read_bytes()
                    with self.assertRaises(packets.PacketError):
                        store.publish_checkpoint('new', b'rejected patch', 'd'*64)
                    self.assertEqual((self.root / store.packet_id / 'ledger.json').read_bytes(), before)
                    self.assertEqual(list((self.root / store.packet_id).glob('*.patch')), [])

    def test_false_stale_or_wrong_binding_isolation_never_releases_claim(self):
        self.claim()
        for change in [{'status': 'unknown'}, {'external_effects': 'unknown'}, {'generation': 99},
                       {'packet_id': 'other'}, {'observed_at': 0}, {'expires_at': 0}]:
            adapter = SimpleNamespace(readback_isolation=lambda binding: {**self.isolated(binding), **change})
            with mock.patch.dict(packets.PACKET_ISOLATION_ADAPTERS, {'synthetic': adapter}):
                with self.assertRaises(packets.PacketError):
                    self.store.quarantine('attempt-1', expected_revision=1, isolation_adapter_id='synthetic')
            self.assertEqual(self.store.read_checkpoint()[0]['attempts'][0]['status'], 'claimed')

    def test_same_task_generation_is_durable_and_cannot_be_forged(self):
        self.claim()
        path = self.root/'packet-1/ledger.json'
        value = json.loads(path.read_bytes()); value['generation'] = 99
        path.write_text(json.dumps(value))
        with self.assertRaises(packets.PacketError):
            self.store.read_checkpoint()


    def reserve(self, attempt='attempt-1', revision=0):
        return self.store.reserve_runtime(attempt, 'b'*64, 'c'*64, expected_revision=revision,
            source_sha256='1'*64, scope_sha256='2'*64, acceptance_sha256='3'*64,
            host_id='host', backend_id='synthetic', policy_sha256='f'*64, runtime_id='runtime-test')

    def test_explicit_atomic_new_claim_reservation_upgrade_preserves_v2_checkpoint(self):
        self.claim()
        old = self.store.publish_checkpoint('attempt-1', b'legacy patch', 'd'*64)
        self.assertEqual(old['schema_version'], 2)
        result = self.reserve('attempt-2', old['revision'])
        self.assertEqual(result['ledger']['schema_version'], 3)
        self.assertEqual(result['ledger']['attempts'][0], old['attempts'][0])
        binding = result['ledger']['supervisors']['attempt-2']['binding']
        self.assertEqual(binding['predecessor_sha256'], old['checkpoint'])
        reopened = packets.PacketStore(self.root, 'packet-1')
        self.assertEqual(reopened.read_checkpoint()[1], b'legacy patch')
        self.assertEqual(reopened.supervisor_snapshot('attempt-2')[1]['stage'], 'reserved')

    def test_existing_v2_pending_attempt_cannot_receive_runtime_or_stop_proof(self):
        self.claim()
        before = (self.root/'packet-1/ledger.json').read_bytes()
        with self.assertRaisesRegex(packets.PacketError, 'already-exists'):
            self.reserve(revision=1)
        with self.assertRaisesRegex(packets.PacketError, 'unavailable'):
            self.store.supervisor_snapshot('attempt-1')
        self.assertEqual((self.root/'packet-1/ledger.json').read_bytes(), before)
        self.store.retain_unknown('attempt-1')
        with self.assertRaisesRegex(packets.PacketError, 'already-exists'):
            self.reserve(revision=2)
        self.assertEqual(self.store.read_checkpoint()[0]['schema_version'], 2)

    def test_supervisor_claim_crash_does_not_leave_unbound_v3_attempt(self):
        with mock.patch.object(self.store, '_write', side_effect=OSError('crash before atomic ledger')):
            with self.assertRaises(OSError):
                self.reserve()
        ledger, _ = self.store.read_checkpoint()
        self.assertEqual(ledger['attempts'], [])
        self.assertEqual(ledger['schema_version'], 2)

    def test_supervisor_record_cas_and_json_injection_are_rejected(self):
        self.reserve()
        ledger, record = self.store.supervisor_snapshot('attempt-1')
        with self.assertRaisesRegex(packets.PacketError, 'revision-conflict'):
            self.store.supervisor_transition('attempt-1', 'launch-intent', expected_revision=999,
                record_sha256=packets.digest(packets.canonical(record)))
        path = self.root/'packet-1/ledger.json'; original = path.read_bytes()
        for field, value in [('module', 'os'), ('host_command', 'echo hi'), ('mount', '/'), ('stopped', True)]:
            mutated = json.loads(original)
            mutated['supervisors']['attempt-1']['binding'][field] = value
            path.write_text(json.dumps(mutated))
            with self.assertRaises(packets.PacketError):
                self.store.supervisor_snapshot('attempt-1')
        path.write_bytes(original)
        duplicate = original.replace(b'"stage":"reserved"', b'"stage":"reserved","stage":"published"')
        path.write_bytes(duplicate)
        with self.assertRaises(packets.PacketError):
            self.store.supervisor_snapshot('attempt-1')

    def test_supervised_attempt_cannot_use_legacy_publish_bypass(self):
        self.reserve()
        with self.assertRaisesRegex(packets.PacketError, 'publication-fence'):
            self.store.publish_checkpoint('attempt-1', b'forged', 'd'*64)
        self.assertIsNone(self.store.read_checkpoint()[0]['checkpoint'])


class BootstrapSchemaTests(unittest.TestCase):
    setUp=PacketStoreTests.setUp
    # Only dedicated migration cases; fixture methods are reused below.
    def test_schema4_reservation_is_explicit_and_legacy_attempt_cannot_upgrade(self):
        arguments=dict(source_sha256='d'*64,scope_sha256='e'*64,acceptance_sha256='f'*64,
            host_id='host',backend_id='backend',policy_sha256='0'*64,runtime_id='runtime',runtime_descriptor_required=True)
        self.store.reserve_runtime('attempt','b'*64,'c'*64,expected_revision=0,**arguments)
        original=(self.root/'packet-1/ledger.json').read_bytes()
        with self.store.locked() as fd:
            ledger=self.store._read(fd)
            with self.assertRaises(packets.PacketError):
                self.store._bootstrap_transition(fd,ledger,'attempt','intent','1'*64)
        self.assertEqual((self.root/'packet-1/ledger.json').read_bytes(),original)
        other=packets.PacketStore(self.root,'packet-new'); other.prepare('a'*64)
        other.reserve_runtime('attempt','b'*64,'c'*64,expected_revision=0,runtime_bootstrap_required=True,**arguments)
        _,record=other.supervisor_snapshot('attempt'); self.assertEqual(record['schema_version'],4); self.assertIsNone(record['bootstrap'])


class IntegrationSchemaCompatibilityTests(unittest.TestCase):
    setUp=PacketStoreTests.setUp

    def test_v2_pending_remains_v2_without_integration_upgrade(self):
        self.store.claim('legacy','b'*64,'c'*64,expected_revision=0)
        original=(self.root/'packet-1/ledger.json').read_bytes()
        with self.store.locked() as fd:
            ledger=self.store._read(fd)
            self.assertEqual(ledger['schema_version'],2)
            self.assertNotIn('integrations',ledger)
        with self.assertRaises(packets.PacketError): self.store.integration_snapshot('absent')
        self.assertEqual((self.root/'packet-1/ledger.json').read_bytes(),original)

    def test_schema4_empty_record_keeps_version_on_new_supervised_reservation(self):
        with self.store.locked() as fd:
            ledger=self.store._read(fd); ledger.update(schema_version=4,supervisors={},integrations={}); self.store._write(fd,ledger)
        self.store.reserve_runtime('attempt','b'*64,'c'*64,expected_revision=0,source_sha256='d'*64,
            scope_sha256='e'*64,acceptance_sha256='f'*64,host_id='host',backend_id='backend',policy_sha256='0'*64,runtime_id='runtime')
        ledger,_=self.store.supervisor_snapshot('attempt')
        self.assertEqual(ledger['schema_version'],4); self.assertEqual(ledger['integrations'],{})

    def test_schema4_unknown_namespace_and_nonobject_integrations_rejected(self):
        with self.store.locked() as fd:
            ledger=self.store._read(fd); ledger.update(schema_version=4,supervisors={},integrations=[]); self.store._write(fd,ledger)
            with self.assertRaises(packets.PacketError): self.store._read(fd)
            ledger['integrations']={}; ledger['retry_ledger']={}; self.store._write(fd,ledger)
            with self.assertRaises(packets.PacketError): self.store._read(fd)


if __name__ == '__main__':
    unittest.main()
