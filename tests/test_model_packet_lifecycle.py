"""Synthetic host-only v6 flow; no real model, process or provider qualification."""
import copy
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import agent_routing
import model_packet_lifecycle as lifecycle
import model_packet_store as packets
from tests.test_model_failover import fixture, route_fixture


class SavedBackend:
    synthetic_only = True
    requires_runtime_descriptor = False
    requires_runtime_bootstrap = False

    def __init__(self, root):
        self.root = root
        self.now = 110
        self.launch_count = self.export_count = 0
        self.lose_launch_reply = self.lose_export_reply = False

    def _path(self, binding):
        return self.root / binding['runtime_id']

    def launch(self, binding, execution):
        self.launch_count += 1
        self._path(binding).write_bytes(packets.canonical(dict(binding=binding,
            execution=execution.decode(), runtime_state='running', external_effects='excluded')))
        if self.lose_launch_reply:
            raise RuntimeError('synthetic-launch-reply-lost')

    def set_state(self, binding, state, effects='excluded'):
        p = self._path(binding); value = json.loads(p.read_bytes())
        value.update(runtime_state=state, external_effects=effects)
        p.write_bytes(packets.canonical(value))

    def inspect(self, binding):
        value = json.loads(self._path(binding).read_bytes())
        if value['binding'] != binding:
            raise RuntimeError('synthetic-runtime-binding-drift')
        return packets.canonical(dict(schema_version=1, binding=binding,
            runtime_state=value['runtime_state'], external_effects=value['external_effects'],
            observed_at=self.now, expires_at=self.now + 60, evidence_sha256=packets.digest(packets.canonical(value))))

    def export_patch(self, binding, limit):
        self.export_count += 1
        p = self._path(binding).with_suffix('.patch')
        with p.open('xb') as stream:
            stream.write(b'')
        if self.lose_export_reply:
            raise RuntimeError('synthetic-export-reply-lost')

    def read_sealed_patch(self, binding, limit):
        raw = self._path(binding).with_suffix('.patch').read_bytes()
        if len(raw) > limit:
            raise RuntimeError('synthetic-patch-bound')
        return raw


class SavedReader:
    """Independent immutable host files, never worker-supplied proof JSON."""
    synthetic_only = True

    def __init__(self, root, store, backend, request):
        self.root, self.store, self.backend, self.request = root, store, backend, request
        self.now = 110
        self.authorization = 'granted'
        self.qualification = 'qualified'
        self.dirty = False
        self.locator = dict(schema_version=1, root=str(store.root), packet_id=store.packet_id,
            identity_sha256='a'*64, objective_sha256=packets.digest(packets.canonical(request['objective'])),
            authority_id=request['objective']['authority_id'])

    def locate_objective(self, alias):
        if alias not in ('alias1', 'alias2'):
            raise RuntimeError('synthetic-objective-alias-unavailable')
        return packets.canonical(self.locator)

    def readback_initial_source(self, objective):
        return b'initial source\n'

    def readback_source_state(self, objective):
        return packets.canonical(dict(source_sha256=self.request['source_sha256'], dirty=self.dirty,
            scope=objective['scope'], acceptance_sha256=objective['acceptance_sha256']))

    def authority(self, binding):
        return packets.canonical(dict(schema_version=2, binding=binding, host_recording_status='granted',
            authorization_status=self.authorization, qualification_status=self.qualification,
            objective_status='admitted', observed_at=self.now, expires_at=self.now + 60))

    def readback_authority(self, binding):
        return self.authority(binding)

    def save(self, op, kind, payload, request=None, planning=None, runtime=None):
        directory = self.root / op; directory.mkdir(mode=0o700)
        request = copy.deepcopy(request or self.request)
        classification = agent_routing.classify_task(request['v2_task']['factors'], contract_version=2,
            workload_kind=request['v2_task']['workload_kind'])
        for name, raw in [('request', packets.canonical(request)), ('classification', packets.canonical(classification)),
                ('fact', packets.canonical(dict(kind=kind, payload=payload, observed_at=self.now))),
                ('planning', packets.canonical(planning) if planning is not None else b''),
                ('runtime', runtime or b'')]:
            (directory / name).write_bytes(raw)

    def seal(self, op, binding):
        directory = self.root / op
        request = (directory / 'request').read_bytes(); classification = (directory / 'classification').read_bytes()
        fact = json.loads((directory / 'fact').read_bytes())
        record = packets.canonical(dict(fact, schema_version=1, binding=binding,
            request_sha256=packets.digest(request), classification_sha256=packets.digest(classification)))
        (directory / 'record').write_bytes(record)
        fields = dict(request=request, record=record, classification=classification,
            execution=(directory / 'execution').read_bytes() if (directory / 'execution').exists() else None,
            runtime=(directory / 'runtime').read_bytes() or None)
        authority_binding = dict(binding, **{k+'_sha256': packets.digest(v) if v is not None else None for k,v in fields.items()})
        (directory / 'authority').write_bytes(self.authority(authority_binding))

    def readback_evidence(self, binding):
        directory = self.root / binding['operation_id']
        return lifecycle.HostEvidence(*(None if name == 'execution' and not (directory / name).exists()
            else ((directory / name).read_bytes() or None) for name in lifecycle.FIELDS))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        for name in ('packets', 'reader', 'backend'):
            (self.root / name).mkdir(mode=0o700)
        self.store = packets.PacketStore(self.root / 'packets', 'packet')
        self.store.prepare('a'*64)
        self.backend = SavedBackend(self.root / 'backend')
        task = route_fixture()['task']
        self.request = dict(schema_version=1,
            objective=dict(repository=str(self.root), task_id='T1', scope='repair', acceptance_sha256='f'*64, authority_id='authority'),
            policy=dict(freshness_seconds=60, service_attempt_limit=3, service_elapsed_limit_seconds=30),
            v2_task=task, attempt_id='a1', generation=0, target_id='internal', target_identity=fixture()['targets'][0]['identity'],
            stage='internal', source_sha256=packets.digest(b'initial source\n'))
        self.reader = SavedReader(self.root / 'reader', self.store, self.backend, self.request)
        self.host = self.controller()
        self.reader.save('admit', 'admit', {})
        with self.store.locked() as fd:
            original = self.store._read(fd)
        self.reader.seal('admit', lifecycle._binding(self.store, original, 'admit'))
        self.host.admit_new('admit', expected_revision=0, now=110)

    def controller(self, alias='alias1', store=None):
        return lifecycle.SyntheticLifecycle(store or self.store, self.reader, self.backend,
            alias=alias, host_id='host', backend_id='backend', policy_sha256='d'*64)

    def current(self):
        return self.host.snapshot(now=110)

    def save(self, op, kind, payload, runtime=False):
        ledger, _ = self.current()
        binding = ledger['supervisors'][ledger['attempts'][-1]['id']]['binding'] if ledger['attempts'] else None
        self.reader.save(op, kind, payload, request=self.request,
            runtime=self.backend.inspect(binding) if runtime else None)
        self.reader.seal(op, lifecycle._binding(self.store, ledger, op))
        return ledger['revision']

    def acquire(self, op='acquire', attempt='a1', planning=None, runtime=None):
        ledger, state = self.current(); self.request['generation'] = ledger['generation'] + 1
        self.request['attempt_id'] = attempt
        planning = planning or fixture(); planning['events'] = copy.deepcopy(state['events'])
        self.reader.save(op, 'acquire', dict(owner_id='owner', epoch=state['owner_epoch']+1), request=self.request, planning=planning)
        directory = self.reader.root / op; request = (directory / 'request').read_bytes()
        binding = lifecycle._binding(self.store, ledger, op)
        execution = dict(schema_version=1, binding=binding, governance_request_sha256=packets.digest(request),
            attempt_id=attempt, generation=self.request['generation'], predecessor_sha256=ledger['checkpoint'],
            target_id=self.request['target_id'], target_identity=self.request['target_identity'], failover_payload=planning,
            host_id='host', backend_id='backend', runtime_policy_sha256='d'*64, runtime_id=runtime or 'runtime-'+attempt)
        (directory / 'execution').write_bytes(packets.canonical(execution))
        self.reader.seal(op, binding)
        return self.host.acquire_attempt(op, expected_revision=ledger['revision'], now=110)

    def start(self, op='launch'):
        revision = self.save(op, 'launch-intent', {})
        return self.host.launch_reserved(op, expected_revision=revision, now=110)

    def observe(self, op='observe'):
        revision = self.save(op, 'observe', {}, runtime=True)
        return self.host.reconcile(op, expected_revision=revision, now=110)

    def stop(self):
        ledger, _ = self.current(); binding = ledger['supervisors'][ledger['attempts'][-1]['id']]['binding']
        self.backend.set_state(binding, 'stopped')
        return binding

    def publish(self, suffix=''):
        revision = self.save('export'+suffix, 'export-intent', {})
        self.host.seal('export'+suffix, expected_revision=revision, now=110)
        ledger, _ = self.current(); binding = ledger['supervisors'][ledger['attempts'][-1]['id']]['binding']
        raw = self.backend.inspect(binding)
        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
        revision = self.save('publish'+suffix, 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
        return self.host.publish('publish'+suffix, expected_revision=revision, now=110)

    def test_full_normal_completion_is_terminal_without_fake_failure(self):
        self.acquire(); self.start(); self.stop(); self.observe(); self.publish()
        revision = self.save('finish', 'finish', dict(result='completed', owner_id='owner', epoch=1), runtime=True)
        ledger, state = self.host.finish_attempt('finish', expected_revision=revision, now=110)
        self.assertTrue(state['terminal']); self.assertIsNone(state['owner'])
        self.assertEqual(state['events'], []); self.assertEqual(state['service_failures'], 0)
        self.assertEqual(ledger['generation'], 1)
        self.assertEqual(self.backend.launch_count, 1); self.assertEqual(self.backend.export_count, 1)

    def test_legacy_read_write_and_artifact_paths_cannot_bypass_v6(self):
        with self.store.locked() as fd:
            with self.assertRaises(packets.PacketError): self.store._read(fd)
            with self.assertRaises(packets.PacketError): self.store.planning_context(fd)
            with self.assertRaises(packets.PacketError): self.store._immutable(fd, 'bypass', b'{}')
            with self.assertRaises(packets.PacketError): self.store._write(fd, dict(schema_version=2))
        self.assertFalse((self.store.root / 'packet/bypass').exists())

    def test_aliases_keep_one_owner_and_do_not_create_budget(self):
        self.acquire()
        other = self.controller('alias2')
        ledger, state = other.snapshot(now=110)
        self.assertEqual(state['generation'], 1)
        self.assertEqual(state['owner']['attempt_id'], 'a1')
        with self.assertRaises(lifecycle.LifecycleError):
            self.acquire('conflict', attempt='a2')
        fork = packets.PacketStore(self.store.root, 'fork'); fork.prepare('a'*64)
        other = self.controller('alias2', store=fork)
        with self.assertRaises(lifecycle.LifecycleError):
            other.admit_new('admit', expected_revision=0, now=110)

    def test_lost_launch_reply_never_relaunches_on_retry_or_reconcile(self):
        self.acquire(); self.backend.lose_launch_reply = True
        with self.assertRaises(RuntimeError): self.start()
        self.controller().launch_reserved('launch', expected_revision=2, now=110)
        self.observe()
        self.assertEqual(self.backend.launch_count, 1)
        self.assertIsNotNone(self.current()[1]['owner'])


    def failure(self, cause='unknown'):
        return dict(attempt_id=self.request['attempt_id'], task_id='T1', scope='repair',
            acceptance_sha256='f'*64, target_id=self.request['target_id'], observed_at=110,
            kind='service', cause=cause, defect_id='service', correction=False,
            source_sha256=self.request['source_sha256'], transition=None)

    def record_fact(self, op, kind, payload):
        revision = self.save(op, kind, payload)
        return self.host.record(op, kind, expected_revision=revision, now=110)

    def finish(self, result='failed', op='finish'):
        _, state = self.current()
        owner = state['owner']
        revision = self.save(op, 'finish', dict(result=result, owner_id=owner['owner_id'], epoch=owner['epoch']), runtime=True)
        return self.host.finish_attempt(op, expected_revision=revision, now=110)

    def test_unknown_recovery_failure_release_and_successor_keep_checkpoint_and_history(self):
        self.acquire(); self.start()
        binding = self.current()[0]['supervisors']['a1']['binding']
        self.backend.set_state(binding, 'unknown', 'unknown'); self.observe('unknown')
        original = self.failure(); self.record_fact('outcome', 'outcome', original)
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('too-early', 'a2')
        self.request['generation'] = 1; self.request['attempt_id'] = 'a1'
        self.stop(); self.observe('stopped')
        self.record_fact('resolve', 'resolve', dict(event_sha256=packets.digest(packets.canonical(original)), cause='retriable-service'))
        self.publish(); before, state = self.finish()
        self.assertIsNone(state['owner']); self.assertEqual(state['service_failures'], 1)
        self.assertEqual(state['events'][0]['cause'], 'unknown')
        successor, new = self.acquire('successor', 'a2')
        self.assertEqual(successor['attempts'][-1]['predecessor_sha256'], before['checkpoint'])
        self.assertEqual(new['service_failures'], 1); self.assertEqual(new['generation'], 2)
        self.assertEqual(self.backend.launch_count, 1)
        self.controller('alias2').acquire_attempt('successor', expected_revision=0, now=110)
        self.assertEqual(self.backend.launch_count, 1)

    def test_unknown_external_effects_cannot_publish_or_release_owner(self):
        self.acquire(); self.start(); binding = self.stop()
        self.backend.set_state(binding, 'stopped', 'unknown'); self.observe()
        revision = self.save('export', 'export-intent', {})
        with self.assertRaises(lifecycle.LifecycleError): self.host.seal('export', expected_revision=revision, now=110)
        self.assertEqual(self.backend.export_count, 0)
        self.assertIsNotNone(self.current()[1]['owner'])

    def test_lost_export_reply_can_read_saved_seal_without_export_replay(self):
        self.acquire(); self.start(); self.stop(); self.observe()
        self.backend.lose_export_reply = True
        revision = self.save('export', 'export-intent', {})
        with self.assertRaises(RuntimeError): self.host.seal('export', expected_revision=revision, now=110)
        self.controller().seal('export', expected_revision=revision, now=110)
        self.observe('post-export')
        ledger, _ = self.current(); binding = ledger['supervisors']['a1']['binding']; raw = self.backend.inspect(binding)
        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
        revision = self.save('publish', 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
        self.host.publish('publish', expected_revision=revision, now=110)
        self.assertEqual(self.backend.export_count, 1)
        self.assertTrue(self.finish('completed')[1]['terminal'])

    def test_revocation_allows_host_observation_but_blocks_new_effects(self):
        self.acquire(); self.start(); self.stop()
        self.reader.authorization = 'revoked'
        self.observe('containment')
        self.assertIsNotNone(self.current()[1]['owner'])
        revision = self.save('export', 'export-intent', {})
        with self.assertRaises(lifecycle.LifecycleError): self.host.seal('export', expected_revision=revision, now=110)
        self.assertEqual(self.backend.export_count, 0)

    def test_dirty_source_and_backend_policy_drift_fail_before_launch(self):
        self.reader.dirty = True
        with self.assertRaises(lifecycle.LifecycleError): self.acquire()
        self.assertEqual(self.current()[0]['generation'], 0)
        self.reader.dirty = False; self.acquire('clean')
        changed = lifecycle.SyntheticLifecycle(self.store, self.reader, self.backend, alias='alias1',
            host_id='other', backend_id='backend', policy_sha256='d'*64)
        with self.assertRaises(lifecycle.LifecycleError): changed.snapshot(now=110)
        self.assertEqual(self.backend.launch_count, 0)

    def test_original_evidence_or_projection_tampering_is_not_repaired(self):
        self.acquire()
        path = self.store.root / 'packet/ledger.json'; raw = path.read_bytes(); ledger = json.loads(raw)
        ledger['attempts'][0]['status'] = 'completed'; path.write_bytes(packets.canonical(ledger))
        with self.assertRaises(lifecycle.LifecycleError): self.current()
        path.write_bytes(raw)
        ref = self.current()[0]['governance']['records'][-1]
        artifact = self.store.root / ('packet/lifecycle-' + ref['execution_sha256'] + '.json')
        artifact.write_bytes(b'{}')
        with self.assertRaises(lifecycle.LifecycleError): self.current()
        self.assertEqual(self.backend.launch_count, 0)

    def test_acquire_same_operation_different_original_execution_bytes_is_rejected(self):
        ledger, _ = self.acquire()
        p = self.reader.root / 'acquire/execution'; v = json.loads(p.read_bytes()); v['runtime_id'] = 'other'
        p.write_bytes(packets.canonical(v))
        with self.assertRaises(lifecycle.LifecycleError):
            self.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.backend.launch_count, 0)


    def test_isolated_writer_releases_to_prior_checkpoint_and_isolation_loss_blocks_next(self):
        self.acquire(); self.start()
        binding = self.current()[0]['supervisors']['a1']['binding']
        self.backend.set_state(binding, 'isolated'); self.observe()
        self.record_fact('failure', 'outcome', self.failure('retriable-service'))
        before, state = self.finish()
        self.assertEqual(before['attempts'][0]['status'], 'quarantined')
        self.assertIsNone(before['checkpoint']); self.assertIsNone(state['owner'])
        self.backend.set_state(binding, 'running')
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('unsafe', 'a2')
        self.backend.set_state(binding, 'isolated')
        successor, state = self.acquire('safe', 'a2')
        self.assertIsNone(successor['attempts'][-1]['predecessor_sha256'])
        self.assertEqual(state['service_failures'], 1)
        self.assertEqual(self.backend.export_count, 0)

    def test_crash_before_claim_commit_leaves_orphan_artifacts_without_owner(self):
        with mock.patch.object(self.store, '_write', side_effect=OSError('synthetic-fsync-failed')):
            with self.assertRaises(OSError): self.acquire()
        ledger, state = self.current()
        self.assertEqual(ledger['generation'], 0); self.assertIsNone(state['owner'])
        self.assertEqual(self.backend.launch_count, 0)
        ledger, state = self.host.acquire_attempt('acquire', expected_revision=1, now=110)
        self.assertEqual(ledger['generation'], 1)

    def test_intent_commit_lost_reply_before_launch_never_dispatches_on_restart(self):
        self.acquire(); revision = self.save('launch', 'launch-intent', {})
        original = self.store._write
        def commit_then_lose(fd, ledger, **kwargs):
            original(fd, ledger, **kwargs)
            raise OSError('synthetic-ledger-reply-lost')
        with mock.patch.object(self.store, '_write', side_effect=commit_then_lose):
            with self.assertRaises(OSError):
                self.host.launch_reserved('launch', expected_revision=revision, now=110)
        ledger, state = self.controller().launch_reserved('launch', expected_revision=revision, now=110)
        self.assertEqual(self.backend.launch_count, 0)
        self.assertEqual(ledger['supervisors']['a1']['stage'], 'launch-intent')
        self.assertIsNotNone(state['owner'])

    def test_quality_lineage_floor_and_health_recovery_do_not_reset_or_preempt(self):
        for index in (1, 2):
            if index == 1: self.acquire()
            else: self.acquire('acquire2', 'a2')
            self.start('launch'+str(index)); self.stop(); self.observe('observe'+str(index))
            event = self.failure('capability')
            event.update(kind='quality', defect_id='A', correction=index == 2)
            self.record_fact('outcome'+str(index), 'outcome', event)
            if index == 2:
                owner = self.current()[1]['owner']
                self.record_fact('floor', 'quality-floor', dict(event_sha256=packets.digest(packets.canonical(event)),
                    original_request_sha256=owner['request_sha256'], insufficient_stage='internal'))
            self.publish(str(index)); self.finish(op='finish'+str(index))
        before, state = self.current()
        self.assertEqual(state['correction_rounds'], 1)
        self.assertEqual(state['quality_stage_floor'], 1)
        self.request.update(target_id='internal-best', target_identity=fixture()['targets'][1]['identity'], stage='internal-best')
        after, state = self.acquire('best', 'a3')
        owner = copy.deepcopy(state['owner'])
        self.record_fact('health', 'health', dict(status='healthy', cooldown_sha256=None))
        rebuilt = self.controller('alias2').snapshot(now=110)[1]
        self.assertEqual(rebuilt['owner'], owner)
        self.assertEqual(rebuilt['quality_stage_floor'], 1)
        self.assertEqual(rebuilt['correction_rounds'], 1)
        self.assertEqual(after['attempts'][-1]['predecessor_sha256'], before['checkpoint'])


    def test_actual_request_cannot_increase_policy_or_exceed_target_context(self):
        planning = fixture(); planning['policy']['service_attempt_limit'] = 20
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('budget-reset', planning=planning)
        planning = fixture(); planning['targets'][0]['context']['input_limit'] = 1
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('context-overflow', planning=planning)
        self.assertEqual(self.current()[0]['generation'], 0)
        self.assertEqual(self.backend.launch_count, 0)

    def test_expired_or_prohibited_failure_never_authorizes_successor(self):
        self.acquire(); self.start(); self.stop(); self.observe()
        self.record_fact('failure', 'outcome', self.failure('auth'))
        self.publish(); self.finish()
        with self.assertRaises(packets.PacketError): self.acquire('forbidden', 'a2')
        self.assertEqual(self.current()[1]['service_failures'], 1)
        self.assertEqual(self.current()[0]['generation'], 1)

    def test_complete_failure_journal_cannot_be_omitted_by_actual_request(self):
        self.acquire(); self.start(); self.stop(); self.observe()
        self.record_fact('failure', 'outcome', self.failure('retriable-service'))
        self.publish(); self.finish()
        ledger, state = self.current(); self.request.update(generation=2, attempt_id='a2')
        op = 'missing-history'; planning = fixture()
        self.reader.save(op, 'acquire', dict(owner_id='owner', epoch=2), request=self.request, planning=planning)
        directory = self.reader.root / op; raw = (directory / 'request').read_bytes()
        binding = lifecycle._binding(self.store, ledger, op)
        execution = dict(schema_version=1, binding=binding, governance_request_sha256=packets.digest(raw),
            attempt_id='a2', generation=2, predecessor_sha256=ledger['checkpoint'], target_id='internal',
            target_identity=self.request['target_identity'], failover_payload=planning, host_id='host',
            backend_id='backend', runtime_policy_sha256='d'*64, runtime_id='runtime-a2')
        (directory / 'execution').write_bytes(packets.canonical(execution)); self.reader.seal(op, binding)
        with self.assertRaises(lifecycle.LifecycleError): self.host.acquire_attempt(op, expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.current()[1]['events'], state['events'])
        self.assertEqual(self.current()[0]['generation'], 1)

    def fresh_case(self):
        case = LifecycleTests('test_full_normal_completion_is_terminal_without_fake_failure')
        case.setUp(); self.addCleanup(case.doCleanups)
        return case

    def isolated_predecessor(self):
        self.acquire(); self.start()
        old = self.current()[0]['supervisors']['a1']['binding']
        self.backend.set_state(old, 'isolated'); self.observe()
        self.record_fact('failure', 'outcome', self.failure('retriable-service')); self.finish()
        self.acquire('second', 'a2')
        return old

    def test_retained_writer_loss_blocks_each_effect_and_adoption(self):
        for stage in ('launch', 'export', 'publish', 'finish'):
            with self.subTest(stage=stage):
                case = self.fresh_case(); old = case.isolated_predecessor()
                if stage != 'launch':
                    case.start('launch2'); case.stop(); case.observe('observe2')
                if stage == 'publish':
                    revision = case.save('export2', 'export-intent', {})
                    case.host.seal('export2', expected_revision=revision, now=110)
                elif stage == 'finish':
                    case.publish('2')
                before = case.current()[0]; counts = (case.backend.launch_count, case.backend.export_count)
                case.backend.set_state(old, 'running')
                with self.assertRaisesRegex(lifecycle.LifecycleError, 'retained-writer-unconfirmed'):
                    if stage == 'launch': case.start('launch2')
                    elif stage == 'export': case.publish('2')
                    elif stage == 'publish':
                        binding = before['supervisors']['a2']['binding']; raw = case.backend.inspect(binding)
                        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
                        revision = case.save('publish2', 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
                        case.host.publish('publish2', expected_revision=revision, now=110)
                    else: case.finish('completed', 'finish2')
                after, state = case.current()
                self.assertEqual(after['revision'], before['revision'])
                self.assertEqual(after['checkpoint'], before['checkpoint'])
                self.assertIsNotNone(state['owner']); self.assertFalse(state['terminal'])
                self.assertEqual((case.backend.launch_count, case.backend.export_count), counts)

    def test_source_drift_after_acquire_blocks_launch(self):
        for field in ('dirty', 'source_sha256', 'scope', 'acceptance_sha256'):
            with self.subTest(field=field):
                case = self.fresh_case(); case.acquire(); original = case.reader.readback_source_state
                def drift(objective):
                    value = json.loads(original(objective))
                    value[field] = True if field == 'dirty' else 'other' if field == 'scope' else 'e'*64
                    return packets.canonical(value)
                with mock.patch.object(case.reader, 'readback_source_state', side_effect=drift):
                    with self.assertRaisesRegex(lifecycle.LifecycleError, 'source-not-clean-or-bound'): case.start()
                self.assertEqual(case.backend.launch_count, 0)
                self.assertIsNotNone(case.current()[1]['owner'])

    def test_current_target_revocation_blocks_launch_export_publish_and_finish(self):
        for stage in ('launch', 'export', 'publish', 'finish'):
            with self.subTest(stage=stage):
                case = self.fresh_case(); case.acquire()
                if stage != 'launch': case.start(); case.stop(); case.observe()
                if stage == 'publish':
                    revision = case.save('export', 'export-intent', {})
                    case.host.seal('export', expected_revision=revision, now=110)
                elif stage == 'finish': case.publish()
                case.record_fact('revoked', 'health', dict(status='revoked', cooldown_sha256=None))
                counts = (case.backend.launch_count, case.backend.export_count); before = case.current()[0]
                with self.assertRaisesRegex(lifecycle.LifecycleError, 'governance-revoked'):
                    if stage == 'launch': case.start()
                    elif stage == 'export': case.publish()
                    elif stage == 'publish':
                        binding = before['supervisors']['a1']['binding']; raw = case.backend.inspect(binding)
                        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
                        revision = case.save('publish', 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
                        case.host.publish('publish', expected_revision=revision, now=110)
                    else: case.finish('completed')
                self.assertEqual(case.current()[0]['revision'], before['revision'])
                self.assertEqual((case.backend.launch_count, case.backend.export_count), counts)
                if stage != 'launch': case.observe('containment-after-revocation')
                self.assertIsNotNone(case.current()[1]['owner'])

    def test_historical_source_revocation_blocks_successor(self):
        self.isolated_predecessor(); self.start('launch2'); self.stop(); self.observe('observe2')
        self.record_fact('failure2', 'outcome', self.failure('retriable-service'))
        self.publish('2'); self.finish(op='finish2')
        self.record_fact('revoked', 'health', dict(status='revoked', cooldown_sha256=None))
        self.request.update(target_id='internal-best', target_identity=fixture()['targets'][1]['identity'], stage='internal-best')
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'governance-revoked'): self.acquire('best', 'a3')
        self.assertEqual(self.current()[0]['generation'], 2)

    def test_export_intent_crash_can_quarantine_without_replay(self):
        self.acquire(); self.start(); binding = self.stop(); self.observe()
        revision = self.save('export', 'export-intent', {}); original = self.store._write
        def lose_reply(fd, ledger, **kwargs):
            original(fd, ledger, **kwargs); raise OSError('synthetic-export-intent-reply-lost')
        with mock.patch.object(self.store, '_write', side_effect=lose_reply):
            with self.assertRaises(OSError): self.host.seal('export', expected_revision=revision, now=110)
        self.controller().seal('export', expected_revision=revision, now=110)
        self.backend.set_state(binding, 'isolated'); self.observe('isolated-after-export')
        self.record_fact('failure', 'outcome', self.failure('retriable-service'))
        ledger, state = self.finish()
        self.assertEqual(ledger['attempts'][0]['status'], 'quarantined')
        self.assertIsNone(ledger['checkpoint']); self.assertIsNone(state['owner'])
        self.assertEqual(self.backend.export_count, 0)
        ledger, state = self.acquire('next', 'a2')
        self.assertIsNone(ledger['attempts'][-1]['predecessor_sha256'])
        self.assertEqual(state['service_failures'], 1)

    def test_execution_generation_and_completed_epoch_reject_bool_and_float(self):
        for value in (True, 1.0):
            with self.subTest(field='generation', value=value):
                case = self.fresh_case(); original = case.reader.seal
                def change(op, binding):
                    path = case.reader.root / op / 'execution'; execution = json.loads(path.read_bytes())
                    execution['generation'] = value; path.write_bytes(packets.canonical(execution)); original(op, binding)
                with mock.patch.object(case.reader, 'seal', side_effect=change):
                    with self.assertRaises(packets.PacketError): case.acquire()
                self.assertEqual(case.current()[0]['generation'], 0); self.assertEqual(case.backend.launch_count, 0)
            with self.subTest(field='epoch', value=value):
                case = self.fresh_case(); case.acquire(); case.start(); case.stop(); case.observe(); case.publish()
                revision = case.save('finish', 'finish', dict(result='completed', owner_id='owner', epoch=value), runtime=True)
                with self.assertRaises(packets.PacketError): case.host.finish_attempt('finish', expected_revision=revision, now=110)
                self.assertFalse(case.current()[1]['terminal']); self.assertIsNotNone(case.current()[1]['owner'])

    def test_reused_runtime_id_rejected_before_claim(self):
        self.isolated_predecessor(); self.start('launch2'); self.stop(); self.observe('observe2')
        self.record_fact('failure2', 'outcome', self.failure('retriable-service')); self.publish('2'); self.finish(op='finish2')
        with self.assertRaisesRegex(lifecycle.LifecycleError, 'runtime-id-reused'): self.acquire('third', 'a3', runtime='runtime-a1')
        self.assertEqual(self.current()[0]['generation'], 2)

    def test_authority_callback_lock_drift_prevents_backend_launch(self):
        self.acquire(); revision = self.save('launch', 'launch-intent', {}); original = self.reader.readback_authority
        def replace_lock(binding):
            raw = original(binding)
            if binding['action'] == 'launch-intent' and binding['revision'] == revision + 1:
                lock = self.store.root / 'packet/lock'; lock.unlink(); lock.touch(mode=0o600)
            return raw
        with mock.patch.object(self.reader, 'readback_authority', side_effect=replace_lock):
            with self.assertRaises(packets.PacketError): self.host.launch_reserved('launch', expected_revision=revision, now=110)
        self.assertEqual(self.backend.launch_count, 0)
        ledger, state = self.current(); self.assertEqual(ledger['supervisors']['a1']['stage'], 'launch-intent')
        self.assertIsNotNone(state['owner'])

    def test_same_objective_cannot_admit_nonempty_legacy_or_v5(self):
        # The legacy packet contains an actual unknown claim, not an empty v2.
        legacy = packets.PacketStore(self.store.root, 'legacy'); legacy.prepare('a'*64)
        legacy.claim('used', 'b'*64, 'c'*64, expected_revision=0)
        host = self.controller(store=legacy)
        with self.assertRaises(lifecycle.LifecycleError): host.admit_new('admit', expected_revision=1, now=110)
        self.assertEqual(self.backend.launch_count, 0)
        import model_packet_governance as governance
        from tests.test_model_packet_governance import SavedHostReader
        old_store = packets.PacketStore(self.store.root, 'v5'); old_store.prepare('a'*64)
        root = self.root / 'v5-host'; root.mkdir(mode=0o700)
        old_reader = SavedHostReader(root); old_reader.now = 110
        old_reader.save('admit', self.request, 'admit', {}, 110)
        old = governance.ObjectiveGovernance(old_store, old_reader)
        old.admit('admit', expected_revision=0, now=110)
        request = copy.deepcopy(self.request); request['generation'] = 1
        old_reader.save('reserve', request, 'acquire', dict(owner_id='old-owner', epoch=1), 110)
        old.append('reserve', expected_revision=1, now=110)
        before = (old_store.root / 'v5/ledger.json').read_bytes()
        with self.assertRaises(packets.PacketError):
            self.controller(store=old_store).admit_new('admit', expected_revision=0, now=110)
        self.assertEqual((old_store.root / 'v5/ledger.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
