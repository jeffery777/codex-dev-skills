"""Host-only synthetic durability tests; no dispatcher/runtime qualification."""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import agent_routing as routing
import model_packet_governance as gov
import model_packet_store as packets
import model_packet_supervisor as supervisors


def factors(**changes):
    value = {'ambiguity': 'moderate', 'reasoning_depth': 'balanced',
        'code_context_volume': 'medium', 'security_data_migration_public_contract_risk': 'routine',
        'write_blast_radius': 'bounded', 'latency_sensitivity': 'medium',
        'cost_token_sensitivity': 'medium', 'independence_parallelizability': 'bounded',
        'verification_burden': 'medium'}
    value.update(changes)
    return value


class SavedHostReader:
    """Independent file-backed host facts, not worker-supplied proof JSON.

    These fixtures qualify storage/projection only. The host creates immutable
    evidence once per operation; retries read its exact saved original bytes.
    Current authority separately consults revocation/qualification/admission.
    """
    def __init__(self, root):
        self.root = root; self.now = 1000
        self.authorization = 'granted'; self.qualification = 'qualified'
        self.objective_status = 'admitted'

    def save(self, operation, request, kind, payload, observed_at):
        directory = self.root / operation; directory.mkdir(mode=0o700)
        task = request['v2_task']
        classification = routing.classify_task(task['factors'], contract_version=2,
            workload_kind=task['workload_kind'], quality_preference=task.get('quality_preference'))
        for name, value in [('request', request), ('classification', classification),
                            ('fact', {'kind': kind, 'payload': payload, 'observed_at': observed_at})]:
            (directory / name).write_bytes(packets.canonical(value))

    def proof(self, binding):
        return packets.canonical({'schema_version': 1, 'binding': binding,
            'authorization_status': self.authorization, 'qualification_status': self.qualification,
            'objective_status': self.objective_status, 'observed_at': self.now,
            'expires_at': self.now + 60})

    def readback_authority(self, binding):
        return self.proof(binding)

    def readback_evidence(self, binding):
        directory = self.root / binding['operation_id']
        request = (directory / 'request').read_bytes()
        classification = (directory / 'classification').read_bytes()
        if not (directory / 'record').exists():
            fact = json.loads((directory / 'fact').read_bytes())
            record = packets.canonical(dict(fact, schema_version=1, binding=binding,
                request_sha256=packets.digest(request), classification_sha256=packets.digest(classification)))
            (directory / 'record').write_bytes(record)
            request_value = json.loads(request)
            authority_binding = dict(binding, request_sha256=packets.digest(request),
                classification_sha256=packets.digest(classification), record_sha256=packets.digest(record),
                objective_sha256=packets.digest(packets.canonical(request_value['objective'])),
                policy_sha256=packets.digest(packets.canonical(request_value['policy'])))
            (directory / 'authority').write_bytes(self.proof(authority_binding))
        return gov.HostEvidence(request, (directory / 'record').read_bytes(), classification,
            (directory / 'authority').read_bytes())


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = pathlib.Path(self.temp.name).resolve()
        self.root = root / 'packets'; self.root.mkdir(mode=0o700)
        host = root / 'host'; host.mkdir(mode=0o700)
        self.reader = SavedHostReader(host)
        self.store = packets.PacketStore(self.root, 'packet')
        self.store.prepare('a' * 64)
        self.governance = gov.ObjectiveGovernance(self.store, self.reader)
        self.now = 1000; self.revision = 0
        self.base = {'schema_version': 1, 'source_sha256': 'a' * 64,
            'objective': {'repository': str(ROOT.resolve()), 'task_id': 'task', 'scope': 'bounded-edit',
                'acceptance_sha256': 'b' * 64, 'authority_id': 'trusted-human-objective'},
            'policy': {'freshness_seconds': 60, 'service_attempt_limit': 2, 'service_elapsed_limit_seconds': 100},
            'v2_task': {'id': 'task', 'factors': factors(), 'workload_kind': 'implementation', 'qualification_scope': 'bounded-edit'},
            'attempt_id': 'admission', 'generation': 0, 'target_id': 'internal', 'stage': 'internal',
            'target_identity': {'provider_id': 'synthetic', 'provider_config_sha256': 'c' * 64,
                'model': 'fixture', 'runtime': 'cli', 'profile_sha256': 'd' * 64,
                'context_policy_sha256': 'e' * 64, 'model_catalog_sha256': 'f' * 64, 'billing': 'internal'}}
        self.admit()

    def request(self, attempt='attempt-1', generation=1, stage='internal', **changes):
        value = copy.deepcopy(self.base)
        value.update(attempt_id=attempt, generation=generation, target_id=stage, stage=stage)
        if stage != 'internal':
            value['target_identity']['model'] = stage
        value.update(changes)
        return value

    def save(self, operation, request, kind, payload):
        self.reader.now = self.now
        self.reader.save(operation, request, kind, payload, self.now)

    def admit(self):
        self.save('admit', self.base, 'admit', {})
        ledger, state = self.governance.admit('admit', expected_revision=0, now=self.now)
        self.revision = ledger['revision']; self.now += 1
        return state

    def append(self, operation, request, kind, payload):
        self.save(operation, request, kind, payload)
        ledger, state = self.governance.append(operation, expected_revision=self.revision, now=self.now)
        self.revision = ledger['revision']; self.now += 1
        return state

    def acquire(self, attempt='attempt-1', generation=1, stage='internal', request=None):
        request = request or self.request(attempt, generation, stage)
        return request, self.append('acquire-' + attempt, request, 'acquire', {'owner_id': 'host-owner', 'epoch': generation})

    def outcome(self, request, cause='retriable-service', kind='service', correction=False, defect='core'):
        event = {'attempt_id': request['attempt_id'], 'task_id': 'task', 'scope': 'bounded-edit',
            'acceptance_sha256': 'b' * 64, 'target_id': request['target_id'], 'observed_at': self.now,
            'kind': kind, 'cause': cause, 'defect_id': defect, 'correction': correction,
            'source_sha256': 'a' * 64, 'transition': None}
        self.append('outcome-' + request['attempt_id'], request, 'outcome', event)
        return event

    def release(self, request, runtime_state='stopped', effects='excluded'):
        return self.append('release-' + request['attempt_id'], request, 'release',
            {'owner_id': 'host-owner', 'epoch': request['generation'], 'runtime_state': runtime_state, 'external_effects': effects})

    def snapshot(self, now=None):
        self.reader.now = self.now if now is None else now
        return self.governance.snapshot(now=self.reader.now)

    def test_new_process_preserves_owner_and_does_not_claim_executor(self):
        request, state = self.acquire(); self.outcome(request)
        self.governance = gov.ObjectiveGovernance(packets.PacketStore(self.root, 'packet'), self.reader)
        ledger, fresh = self.snapshot()
        self.assertEqual(fresh['owner'], state['owner'])
        self.assertEqual(fresh['service_failures'], 1)
        self.assertEqual(ledger['generation'], 0); self.assertEqual(ledger['attempts'], [])
        code = "import pathlib,sys;sys.path.insert(0,sys.argv[1]);import model_packet_store as p;s=p.PacketStore(sys.argv[2],'packet');\nwith s.locked() as fd:\n l=s._read(fd,_governance=True);print(l['schema_version'],l['generation'],len(l['governance']['records']))"
        result = subprocess.run([sys.executable, '-c', code, str(ROOT / 'skills/loop-engineering/scripts'), str(self.root)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), '5 0 3')

    def test_owner_competition_and_busy_lock_fail_closed(self):
        self.acquire()
        with self.assertRaisesRegex(gov.GovernanceError, 'owner-conflict'):
            self.acquire('attempt-2', 2)
        with self.store.locked():
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                self.snapshot()

    def test_healthy_and_elapsed_never_preempt_owner(self):
        request, state = self.acquire()
        self.append('healthy', request, 'health', {'status': 'healthy', 'cooldown_sha256': None})
        self.assertEqual(self.snapshot(now=1200)[1]['owner'], state['owner'])
        with self.assertRaisesRegex(gov.GovernanceError, 'owner-conflict'):
            self.acquire('attempt-2', 2)

    def test_takeover_requires_complete_stop_isolation_effects_and_authority(self):
        request, _ = self.acquire(); self.outcome(request)
        self.save('bad-release', request, 'release', {'owner_id': 'host-owner', 'epoch': 1, 'runtime_state': 'unknown', 'external_effects': 'excluded'})
        with self.assertRaisesRegex(gov.GovernanceError, 'release-not-established'):
            self.governance.append('bad-release', expected_revision=self.revision, now=self.now)
        self.release(request, 'isolated')
        self.reader.authorization = 'revoked'
        with self.assertRaisesRegex(gov.GovernanceError, 'authority-unavailable'):
            self.acquire('attempt-2', 2)
        self.assertIsNone(self.snapshot_after_authority_restore()['owner'])

    def snapshot_after_authority_restore(self):
        self.reader.authorization = 'granted'
        return self.snapshot()[1]

    def test_counts_and_original_events_survive_resolution_release_health_and_reopen(self):
        request, _ = self.acquire(); event = self.outcome(request, 'unknown')
        self.append('resolve', request, 'resolve', {'event_sha256': packets.digest(packets.canonical(event)), 'cause': 'retriable-service'})
        self.release(request)
        request2, _ = self.acquire('attempt-2', 2); self.outcome(request2)
        self.append('healthy', request2, 'health', {'status': 'healthy', 'cooldown_sha256': None})
        state = self.snapshot(now=1100)[1]
        self.assertEqual(state['events'][0], event); self.assertEqual(state['events'][0]['cause'], 'unknown')
        self.assertEqual(state['service_failures'], 2); self.assertTrue(state['service_exhausted'])
        self.assertEqual(state['elapsed_seconds'], 1100 - event['observed_at'])

    def test_unknown_and_prohibited_causes_cannot_be_masked_by_health(self):
        for cause in ['unknown', 'unknown-write', 'auth', 'permission', 'config', 'context', 'secret']:
            with self.subTest(cause=cause):
                root = self.root / cause; root.mkdir(mode=0o700)
                store = packets.PacketStore(root, 'packet'); store.prepare('a' * 64)
                reader = SavedHostReader(self.reader.root / cause); reader.root.mkdir(mode=0o700)
                original = (self.store, self.reader, self.governance, self.now, self.revision)
                self.store, self.reader = store, reader
                self.governance = gov.ObjectiveGovernance(store, reader); self.now = 1000; self.revision = 0
                self.admit(); request, _ = self.acquire(); self.outcome(request, cause); self.release(request)
                self.append('healthy', request, 'health', {'status': 'healthy', 'cooldown_sha256': None})
                with self.assertRaisesRegex(gov.GovernanceError, 'cause-prohibits-owner'):
                    self.acquire('attempt-2', 2)
                self.store, self.reader, self.governance, self.now, self.revision = original

    def test_cooldown_exact_target_and_expiry_only_requires_recheck(self):
        request, owner = self.acquire(); event = self.outcome(request)
        cooldown = {'event_sha256': packets.digest(packets.canonical(event)),
            'target_sha256': packets.digest(packets.canonical(request['target_identity'])),
            'policy_sha256': packets.digest(packets.canonical(request['policy'])),
            'cause': 'retriable-service', 'start': event['observed_at'], 'end': 1050}
        self.append('cooldown', request, 'cooldown', cooldown)
        state = self.snapshot(now=1051)[1]
        self.assertEqual(state['owner'], owner['owner'])
        self.assertEqual(next(iter(state['cooldowns'].values()))['state'], 'recheck-required')
        self.now = 1051; self.release(request)
        with self.assertRaisesRegex(gov.GovernanceError, 'cooldown-recheck-required'):
            self.acquire('attempt-2', 2)
        self.append('recheck', request, 'health', {'status': 'healthy', 'cooldown_sha256': packets.digest(packets.canonical(cooldown))})
        _, state = self.acquire('attempt-3', 2)
        self.assertEqual(state['service_failures'], 1); self.assertEqual(state['generation'], 2)

    def test_cooldown_target_policy_cause_binding_rejected(self):
        request, _ = self.acquire(); event = self.outcome(request)
        cooldown = {'event_sha256': packets.digest(packets.canonical(event)),
            'target_sha256': '0' * 64, 'policy_sha256': packets.digest(packets.canonical(request['policy'])),
            'cause': 'retriable-service', 'start': event['observed_at'], 'end': 1050}
        with self.assertRaisesRegex(gov.GovernanceError, 'cooldown-unconfirmed'):
            self.append('cooldown', request, 'cooldown', cooldown)

    def exhausted_quality(self):
        request, _ = self.acquire(); self.outcome(request, 'capability', 'quality'); self.release(request)
        request, _ = self.acquire('attempt-2', 2)
        event = self.outcome(request, 'capability', 'quality', correction=True)
        return request, event

    def quality_floor(self, request, event, new_factors=None):
        revised = copy.deepcopy(request)
        if new_factors is not None:
            revised['v2_task']['factors'] = new_factors
        return self.append('quality-floor', revised, 'quality-floor',
            {'event_sha256': packets.digest(packets.canonical(event)),
                'original_request_sha256': packets.digest(packets.canonical(request)), 'insufficient_stage': request['stage']})

    def test_quality_stage_and_tier_floor_are_independent_forward_only(self):
        request, event = self.exhausted_quality()
        high = factors(ambiguity='high', reasoning_depth='deep', code_context_volume='large')
        state = self.quality_floor(request, event, high)
        self.assertEqual(state['quality_class'], 'balanced-worker')
        self.assertGreater(routing.TIER_RANK[state['quality_tier_floors']['balanced-worker']], routing.TIER_RANK['everyday'])
        self.assertEqual(state['quality_stage_floor'], 1)
        self.release(request)
        with self.assertRaisesRegex(gov.GovernanceError, 'floor-regression'):
            self.acquire('attempt-3', 3, 'internal-best')
        next_request = self.request('attempt-4', 3, 'internal-best')
        next_request['v2_task']['factors'] = high
        _, state = self.acquire('attempt-4', 3, request=next_request)
        self.assertEqual(state['correction_rounds'], 1)

    def test_class_change_requires_objective_reassessment(self):
        request, event = self.exhausted_quality()
        with self.assertRaisesRegex(gov.GovernanceError, 'classification-objective-reassessment-required'):
            self.quality_floor(request, event, factors(security_data_migration_public_contract_risk='security'))

    def test_service_fallback_does_not_raise_quality_floor_or_allow_stage_reverse(self):
        request, _ = self.acquire(); self.outcome(request); self.release(request)
        request, state = self.acquire('attempt-2', 2, 'official')
        self.assertEqual(state['stage_floor'], 2); self.assertEqual(state['quality_stage_floor'], 0)
        self.assertEqual(state['quality_tier_floors']['balanced-worker'], 'everyday')
        self.outcome(request); self.release(request)
        with self.assertRaisesRegex(gov.GovernanceError, 'floor-regression'):
            self.acquire('attempt-3', 3, 'internal')

    def test_required_tier_survives_release_health_restart_and_service_fallback(self):
        high = factors(ambiguity='high', reasoning_depth='deep', code_context_volume='large')
        request = self.request(); request['v2_task']['factors'] = high
        request, state = self.acquire(request=request)
        self.assertEqual(state['required_tier_floors'], {'balanced-worker': 'advanced'})
        self.assertEqual(state['quality_tier_floors'], {'balanced-worker': 'everyday'})
        event = self.outcome(request); self.release(request)
        # A later health observation carries the original lower V2 request;
        # it cannot lower the requirement already admitted for this objective.
        self.append('healthy-baseline', self.base, 'health', {'status': 'healthy', 'cooldown_sha256': None})
        ledger, before = self.snapshot()
        originals = {path.name: path.read_bytes() for path in (self.root / 'packet').glob('governance-*.json')}
        self.governance = gov.ObjectiveGovernance(packets.PacketStore(self.root, 'packet'), self.reader)
        with self.assertRaisesRegex(gov.GovernanceError, 'floor-regression'):
            self.acquire('attempt-2', 2, 'official')
        fresh_ledger, fresh = self.snapshot()
        self.assertEqual(fresh_ledger, ledger)
        self.assertEqual(fresh['required_tier_floors'], {'balanced-worker': 'advanced'})
        self.assertEqual(fresh['quality_stage_floor'], 0)
        self.assertEqual(fresh['events'], [event]); self.assertEqual(fresh['service_failures'], 1)
        self.assertEqual(fresh['owner_epoch'], before['owner_epoch'])
        self.assertEqual(originals, {path.name: path.read_bytes() for path in (self.root / 'packet').glob('governance-*.json')})
        higher = self.request('attempt-3', 2, 'official'); higher['v2_task']['factors'] = high
        _, state = self.acquire('attempt-3', 2, request=higher)
        self.assertEqual(state['required_tier_floors'], {'balanced-worker': 'advanced'})
        self.assertEqual(state['quality_tier_floors'], {'balanced-worker': 'everyday'})
        self.assertEqual(state['quality_stage_floor'], 0); self.assertEqual(state['generation'], 2)

    def test_invalid_typed_or_generation_lineage_cannot_admit_a_new_required_floor(self):
        high = factors(ambiguity='high', reasoning_depth='deep', code_context_volume='large')
        ledger = self.snapshot()[0]
        for generation, error in [(True, 'integer-invalid'), (2, 'owner-conflict')]:
            with self.subTest(generation=generation):
                request = self.request('invalid-' + str(generation), generation)
                request['v2_task']['factors'] = high
                self.save('invalid-' + str(generation), request, 'acquire', {'owner_id': 'host-owner', 'epoch': 1})
                with self.assertRaisesRegex(gov.GovernanceError, error):
                    self.governance.append('invalid-' + str(generation), expected_revision=self.revision, now=self.now)
                fresh, state = self.snapshot()
                self.assertEqual(fresh, ledger)
                self.assertEqual(state['required_tier_floors'], {'balanced-worker': 'everyday'})
        _, state = self.acquire()
        self.assertEqual(state['generation'], 1)

    def test_cas_competition_is_not_a_new_budget(self):
        request, _ = self.acquire()
        self.save('healthy', request, 'health', {'status': 'healthy', 'cooldown_sha256': None})
        with self.assertRaisesRegex(gov.GovernanceError, 'revision-conflict'):
            self.governance.append('healthy', expected_revision=1, now=self.now)
        self.assertEqual(self.snapshot()[0]['revision'], self.revision)

    def test_operation_replay_requires_exact_saved_bytes(self):
        request, _ = self.acquire()
        ledger = self.snapshot()[0]
        replay, _ = self.governance.append('acquire-attempt-1', expected_revision=0, now=self.now)
        self.assertEqual(ledger, replay)
        path = self.reader.root / 'acquire-attempt-1' / 'request'
        changed = json.loads(path.read_bytes()); changed['target_identity']['model'] = 'different'
        path.write_bytes(packets.canonical(changed))
        with self.assertRaisesRegex(gov.GovernanceError, 'operation-bytes-conflict'):
            self.governance.append('acquire-attempt-1', expected_revision=0, now=self.now)

    def test_crash_before_pointer_leaves_orphan_unadopted(self):
        request = self.request(); self.save('acquire-attempt-1', request, 'acquire', {'owner_id': 'host-owner', 'epoch': 1})
        raw = (self.root / 'packet/ledger.json').read_bytes()
        with mock.patch.object(self.store, '_write', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                self.governance.append('acquire-attempt-1', expected_revision=1, now=self.now)
        self.assertEqual((self.root / 'packet/ledger.json').read_bytes(), raw)
        self.assertIsNone(self.snapshot()[1]['owner'])
        artifacts = list((self.root / 'packet').glob('governance-*.json'))
        self.assertGreater(len(artifacts), 4)
        ledger, state = self.governance.append('acquire-attempt-1', expected_revision=1, now=self.now)
        self.assertEqual(state['generation'], 1); self.assertEqual(ledger['generation'], 0)

    def test_artifact_drift_missing_or_symlink_fails_closed(self):
        ledger = self.snapshot()[0]; ref = ledger['governance']['records'][0]
        path = self.root / 'packet' / ('governance-' + ref['record_sha256'] + '.json')
        original = path.read_bytes(); path.write_bytes(b'{}')
        with self.assertRaisesRegex(gov.GovernanceError, 'artifact-drift'):
            self.snapshot()
        path.write_bytes(original)
        saved = path.with_suffix('.missing')
        os.replace(path, saved)
        with self.assertRaises(FileNotFoundError):
            self.snapshot()
        path.symlink_to(saved)
        with self.assertRaises(OSError):
            self.snapshot()

    def test_legacy_nonempty_bytes_and_proofs_remain_unmodified(self):
        legacy = packets.PacketStore(self.root, 'legacy'); legacy.prepare('a' * 64)
        legacy.claim('old-attempt', 'b' * 64, 'c' * 64, expected_revision=0)
        raw = (self.root / 'legacy/ledger.json').read_bytes()
        governance = gov.ObjectiveGovernance(legacy, self.reader)
        with self.assertRaisesRegex(gov.GovernanceError, 'legacy-unavailable'):
            governance.admit('admit', expected_revision=1, now=self.now)
        with self.assertRaisesRegex(gov.GovernanceError, 'governance-unavailable'):
            governance.snapshot(now=self.now)
        self.assertEqual((self.root / 'legacy/ledger.json').read_bytes(), raw)

    def test_all_old_writer_entrypoints_reject_before_effects(self):
        ledger_raw = (self.root / 'packet/ledger.json').read_bytes()
        calls = [lambda: self.store.prepare('a' * 64),
            lambda: self.store.claim('old', 'b' * 64, 'c' * 64, expected_revision=1),
            lambda: self.store.retain_unknown('old'),
            lambda: self.store.quarantine('old', expected_revision=1, isolation_adapter_id='fixture'),
            lambda: self.store.publish_checkpoint('old', b'patch', 'b' * 64),
            lambda: self.store.create_attempt_directory('old'),
            lambda: self.store.observe_supervisor_unknown('old', 'runtime-proof-unavailable'),
            lambda: self.store.supervisor_transition('old', 'launch-intent', expected_revision=1, record_sha256='b' * 64),
            lambda: self.store.seal_supervisor_patch('old', b'patch', 'b' * 64, expected_revision=1, record_sha256='b' * 64),
            lambda: self.store.read_checkpoint()]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(packets.PacketError, 'governance-executor-unavailable'):
                    call()
        with self.store.locked() as fd:
            ledger = self.store._read(fd, _governance=True)
            with self.assertRaisesRegex(packets.PacketError, 'governance-write-unavailable'):
                self.store._write(fd, ledger)
            downgraded = {'schema_version': 2, 'packet_id': 'packet', 'identity_sha256': 'a' * 64,
                'revision': 0, 'generation': 0, 'attempts': [], 'checkpoint': None}
            with self.assertRaisesRegex(packets.PacketError, 'governance-write-unavailable'):
                self.store._write(fd, downgraded)
            with self.assertRaisesRegex(packets.PacketError, 'governance-executor-unavailable'):
                self.store._immutable(fd, 'legacy-orphan.json', b'{}')
        self.assertEqual((self.root / 'packet/ledger.json').read_bytes(), ledger_raw)
        self.assertFalse((self.root / 'packet/attempt-old').exists())
        self.assertFalse((self.root / 'packet/legacy-orphan.json').exists())

    def test_old_supervisor_cannot_launch_or_reconcile_a_governance_reservation(self):
        backend = mock.Mock(requires_runtime_descriptor=True, requires_runtime_bootstrap=True)
        supervisor = supervisors.PacketSupervisor(self.store, backend,
            host_id='host', backend_id='fixture', policy_sha256='a' * 64)
        with self.assertRaisesRegex(packets.PacketError, 'governance-executor-unavailable'):
            supervisor.start('old', 'b' * 64, 'c' * 64, expected_revision=1,
                source_sha256='a' * 64, scope_sha256='b' * 64, acceptance_sha256='c' * 64)
        with self.assertRaisesRegex(packets.PacketError, 'governance-executor-unavailable'):
            supervisor.reconcile('old')
        backend.prepare.assert_not_called(); backend.launch.assert_not_called()
        backend.inspect.assert_not_called(); backend.export.assert_not_called()

    def test_worker_json_and_self_asserted_digest_are_not_evidence(self):
        with mock.patch.object(self.reader, 'readback_evidence', return_value={'approved': True, 'evidence_sha256': 'a' * 64}):
            with self.assertRaisesRegex(gov.GovernanceError, 'host-evidence-required'):
                self.governance.append('fake', expected_revision=1, now=self.now)

    def test_empty_packet_admission_requires_independent_objective_authority(self):
        store = packets.PacketStore(self.root, 'fresh'); store.prepare('a' * 64)
        governance = gov.ObjectiveGovernance(store, self.reader)
        before = (self.root / 'fresh/ledger.json').read_bytes()
        self.reader.objective_status = 'unknown'
        self.save('denied-admission', self.base, 'admit', {})
        with self.assertRaisesRegex(gov.GovernanceError, 'authority-unavailable'):
            governance.admit('denied-admission', expected_revision=0, now=self.now)
        self.assertEqual((self.root / 'fresh/ledger.json').read_bytes(), before)
        with self.assertRaisesRegex(gov.GovernanceError, 'governance-unavailable'):
            governance.snapshot(now=self.now)
        self.assertEqual(list((self.root / 'fresh').glob('governance-*')), [])

    def test_same_objective_head_drift_never_creates_fresh_budget(self):
        request, _ = self.acquire(); self.outcome(request); self.release(request)
        changed = self.request('attempt-2', 2); changed['source_sha256'] = '1' * 64
        with self.assertRaisesRegex(gov.GovernanceError, 'source-head-conflict'):
            self.acquire('attempt-2', 2, request=changed)
        state = self.snapshot()[1]
        self.assertEqual(state['generation'], 1); self.assertEqual(state['service_failures'], 1)

    def test_crash_after_pointer_and_request_generation_fence(self):
        request = self.request(); self.save('acquire-attempt-1', request, 'acquire', {'owner_id': 'host-owner', 'epoch': 1})
        write = self.store._write
        def crash_after_write(*args, **kwargs):
            write(*args, **kwargs)
            raise OSError('synthetic crash after durable pointer')
        with mock.patch.object(self.store, '_write', side_effect=crash_after_write):
            with self.assertRaises(OSError):
                self.governance.append('acquire-attempt-1', expected_revision=1, now=self.now)
        ledger, owner = self.snapshot()
        self.assertEqual(ledger['revision'], 2); self.assertEqual(owner['generation'], 1)
        replay, state = self.governance.append('acquire-attempt-1', expected_revision=1, now=self.now)
        self.assertEqual(replay, ledger); self.assertEqual(state['owner'], owner['owner'])
        wrong = copy.deepcopy(request); wrong['generation'] = 2
        self.save('wrong-release', wrong, 'release', {'owner_id': 'host-owner', 'epoch': 1, 'runtime_state': 'stopped', 'external_effects': 'excluded'})
        with self.assertRaisesRegex(gov.GovernanceError, 'original-request-drift'):
            self.governance.append('wrong-release', expected_revision=2, now=self.now)

    def test_future_and_expired_current_authority_fail_closed(self):
        binding = self.snapshot()[0]
        for observed, expiry in [(self.now + 1, self.now + 60), (self.now - 60, self.now)]:
            with self.subTest(observed=observed, expiry=expiry):
                def bad_authority(value):
                    proof = json.loads(self.reader.proof(value))
                    proof.update(observed_at=observed, expires_at=expiry)
                    return packets.canonical(proof)
                with mock.patch.object(self.reader, 'readback_authority', side_effect=bad_authority):
                    with self.assertRaisesRegex(gov.GovernanceError, 'authority-stale-or-future'):
                        self.snapshot()
        self.assertEqual(self.snapshot()[0], binding)

    def test_clock_rollback_future_authority_revocation_and_health_are_sticky(self):
        request, _ = self.acquire()
        with self.assertRaisesRegex(gov.GovernanceError, 'clock-rollback-or-future'):
            self.snapshot(now=999)
        for status in ('revoked', 'unknown'):
            self.reader.authorization = status
            with self.assertRaisesRegex(gov.GovernanceError, 'authority-unavailable'):
                self.snapshot()
        self.reader.authorization = 'granted'
        self.append('revoked-health', request, 'health', {'status': 'revoked', 'cooldown_sha256': None})
        with self.assertRaisesRegex(gov.GovernanceError, 'revocation-sticky'):
            self.append('healthy', request, 'health', {'status': 'healthy', 'cooldown_sha256': None})

    def test_typed_fields_and_original_classification_cannot_be_forged(self):
        for field in ('revision', 'generation'):
            with self.subTest(field=field):
                ledger = self.snapshot()[0]; ledger[field] = True
                with self.assertRaises(packets.PacketError):
                    gov.validate_ledger(ledger, 'packet')
        request = self.request(); self.save('forged', request, 'acquire', {'owner_id': 'host-owner', 'epoch': 1})
        path = self.reader.root / 'forged/classification'
        classification = json.loads(path.read_bytes()); classification['capability_tier'] = 'exceptional'
        path.write_bytes(packets.canonical(classification))
        with self.assertRaisesRegex(gov.GovernanceError, 'original-v2-classification-drift'):
            self.governance.append('forged', expected_revision=1, now=self.now)

    def test_pure_projection_keeps_input_immutable(self):
        request, _ = self.acquire(); self.outcome(request)
        with self.store.locked() as fd:
            ledger = self.store._read(fd, _governance=True)
            prefix = self.governance._prefix(fd, ledger)
        before = copy.deepcopy(prefix)
        gov.project(prefix, now=self.now)
        self.assertEqual(prefix, before)


if __name__ == '__main__':
    unittest.main()
