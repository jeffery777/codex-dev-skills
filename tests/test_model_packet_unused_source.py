"""Independent saved host fixtures; v6 unused-source TTL is not production routing."""
import copy
import json
import unittest
from unittest import mock

from tests import test_model_packet_lifecycle as baseline
from tests.test_model_failover import fixture
import model_packet_lifecycle as lifecycle
import model_packet_store as packets
import model_failover as failover
import agent_qualification as trust


class ProofReader(baseline.SavedReader):
    def readback_unused_source(self, binding):
        return (self.root / ('unused-' + packets.digest(packets.canonical(binding)))).read_bytes()

    def readback_destination(self, binding):
        return (self.root / ('destination-' + packets.digest(packets.canonical(binding)))).read_bytes()


class UnusedLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f = baseline.LifecycleTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        f = self.f
        f.reader = ProofReader(f.reader.root, f.store, f.backend, f.request)
        f.host = f.controller()
        self.planning = fixture(); self.planning['targets'][0]['availability']['status'] = 'unavailable'
        self.planning['targets'][0]['qualification']['observed_at'] = 0
        self.executions = {}

    def save_destination(self, ledger, execution_raw, action, mutate=None):
        f = self.f; execution = json.loads(execution_raw)
        binding = dict(lifecycle._binding(f.store, ledger, 'current'), action=action,
            execution_sha256=packets.digest(execution_raw), target_id=execution['target_id'],
            target_identity_sha256=packets.digest(packets.canonical(execution['target_identity'])))
        payload = copy.deepcopy(execution['failover_payload'])
        if mutate:
            mutate(payload)
        value = dict(schema_version=1, binding=binding, observed_at=110, expires_at=170, payload=payload)
        path = f.reader.root / ('destination-' + packets.digest(packets.canonical(binding)))
        path.write_bytes(packets.canonical(value))
        return path

    def prepare(self, op='acquire', attempt='a1', mutate=None, proof_mutate=None):
        f = self.f; ledger, state = f.current(); p = copy.deepcopy(self.planning)
        p['events'] = copy.deepcopy(state['events'])
        if p['events']:
            p['current_target'] = p['events'][-1]['target_id']
        if mutate:
            mutate(p)
        f.request.update(attempt_id=attempt, generation=ledger['generation']+1,
            target_id='official', target_identity=p['targets'][2]['identity'], stage='official')
        f.reader.save(op, 'acquire', dict(owner_id='owner', epoch=state['owner_epoch']+1), request=f.request, planning=p)
        binding = lifecycle._binding(f.store, ledger, op)
        directory = f.reader.root / op; request_raw = (directory / 'request').read_bytes()
        execution = dict(schema_version=2, binding=binding, governance_request_sha256=packets.digest(request_raw),
            attempt_id=attempt, generation=f.request['generation'], predecessor_sha256=ledger['checkpoint'],
            target_id='official', target_identity=f.request['target_identity'], failover_payload=p,
            host_id='host', backend_id='backend', runtime_policy_sha256='d'*64, runtime_id='runtime-'+attempt)
        source, destination = p['targets'][0], p['targets'][2]
        decision = copy.deepcopy(p)
        for e in decision['events']:
            e['cause'] = state['resolved_causes'].get(e['attempt_id'], e['cause'])
        proof_binding = dict(binding, domain='v6-unused-source/1', attempt_id=attempt, runtime_id='runtime-'+attempt,
            governance_request_sha256=packets.digest(request_raw), execution_core_sha256=packets.digest(packets.canonical(execution)),
            planning_sha256=packets.digest(packets.canonical(p)), decision_sha256=packets.digest(packets.canonical(decision)),
            source_id=source['id'], source_identity_sha256=packets.digest(packets.canonical(source['identity'])),
            source_qualification_sha256=packets.digest(packets.canonical(source['qualification'])),
            source_availability_sha256=packets.digest(packets.canonical(source['availability'])),
            destination_id=destination['id'], destination_identity_sha256=packets.digest(packets.canonical(destination['identity'])),
            authorization_sha256=packets.digest(packets.canonical(p['authorization'])),
            secret_check_sha256=packets.digest(packets.canonical(p['secret_check'])))
        proof = dict(schema_version=2, binding=proof_binding, authorization_status='granted',
            qualification_status='qualified', observed_at=110, expires_at=170, evidence_sha256='e'*64)
        if proof_mutate:
            proof_mutate(proof)
        raw_proof = packets.canonical(proof)
        execution['unused_source_bytes'] = raw_proof.decode()
        execution_raw = packets.canonical(execution); self.executions[attempt] = execution_raw
        (directory / 'execution').write_bytes(execution_raw)
        (f.reader.root / ('unused-' + packets.digest(packets.canonical(proof_binding)))).write_bytes(raw_proof)
        f.reader.seal(op, binding)
        self.save_destination(ledger, execution_raw, 'acquire')
        return ledger, execution_raw, proof_binding

    def acquire(self, op='acquire', attempt='a1', **kwargs):
        ledger, _, _ = self.prepare(op, attempt, **kwargs)
        return self.f.host.acquire_attempt(op, expected_revision=ledger['revision'], now=110)

    def destination(self, action, mutate=None):
        ledger, _ = self.f.current()
        return self.save_destination(ledger, self.executions[ledger['attempts'][-1]['id']], action, mutate)

    def intent(self, action, op, mutate=None):
        f = self.f; revision = f.save(op, action, {}); ledger, _ = f.current()
        raw = self.executions[ledger['attempts'][-1]['id']]
        self.save_destination(ledger, raw, action, mutate)
        # Save the independently observed post-intent proof before the host
        # transaction; the reader never manufactures observations on demand.
        future = copy.deepcopy(ledger); binding = lifecycle._binding(f.store, ledger, op)
        evidence = f.reader.readback_evidence(binding)
        ref = dict(operation_id=op, kind=action, binding=binding, committed_at=110)
        ref.update({field+'_sha256': packets.digest(getattr(evidence, field))
            if getattr(evidence, field) is not None else None for field in lifecycle.FIELDS})
        future['governance']['records'].append(ref); future['revision'] += 1
        self.save_destination(future, raw, action, mutate)
        method = f.host.launch_reserved if action == 'launch-intent' else f.host.seal
        return method(op, expected_revision=revision, now=110)

    def failed(self, suffix='', *, quality=False, correction=False):
        f = self.f
        self.intent('launch-intent', 'launch'+suffix)
        f.stop(); f.observe('observe'+suffix)
        event = f.failure('retriable-service')
        if quality:
            event.update(kind='quality', cause='capability', defect_id='A', correction=correction)
        event['transition'] = (dict(source_identity_sha256=failover.identity_digest(self.planning['targets'][0]['identity']),
            reason='internal-unavailable', observed_at=110, evidence_sha256='e'*64) if not f.current()[1]['events'] else None)
        f.record_fact('outcome'+suffix, 'outcome', event)
        self.intent('export-intent', 'export'+suffix)
        ledger, _ = f.current(); binding = ledger['supervisors'][f.request['attempt_id']]['binding']
        raw = f.backend.inspect(binding)
        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
        self.destination('publish')
        revision = f.save('publish'+suffix, 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
        f.host.publish('publish'+suffix, expected_revision=revision, now=110)
        self.destination('finish'); return f.finish(op='finish'+suffix)

    def test_first_official_claim_and_retry_preserve_one_history_and_budget(self):
        ledger, state = self.acquire()
        self.assertEqual(ledger['generation'], 1); self.assertEqual(state['stage_floor'], 2)
        before, state = self.failed()
        successor, new = self.acquire('successor', 'a2')
        self.assertEqual(new['service_failures'], 1); self.assertEqual(new['events'], state['events'])
        self.assertEqual(new['required_tier_floors'], state['required_tier_floors'])
        self.assertEqual(new['quality_tier_floors'], state['quality_tier_floors'])
        self.assertEqual(new['stage_floor'], 2); self.assertEqual(new['generation'], 2)
        self.assertEqual(successor['attempts'][-1]['predecessor_sha256'], before['checkpoint'])
        self.assertEqual(self.f.backend.launch_count, 1)
        self.failed('2'); self.acquire('third', 'a3'); self.failed('3')
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('exhausted', 'a4')
        self.assertEqual(self.f.current()[1]['service_failures'], 3)
        self.assertEqual(self.f.current()[0]['generation'], 3)

    def test_original_proof_replay_needs_no_today_readback_and_no_effect_replay(self):
        ledger, _, _ = self.prepare()
        self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        with mock.patch.object(self.f.reader, 'readback_unused_source', side_effect=AssertionError('today readback')):
            self.f.current()
            self.f.host.acquire_attempt('acquire', expected_revision=0, now=110)
        self.assertEqual(self.f.backend.launch_count, 0)

    def test_same_prefix_proof_cannot_authorize_successor(self):
        self.acquire(); self.failed()
        ledger, _, _ = self.prepare('successor', 'a2')
        directory = self.f.reader.root / 'successor'
        execution = json.loads((directory / 'execution').read_bytes())
        execution['unused_source_bytes'] = json.loads(self.executions['a1'])['unused_source_bytes']
        (directory / 'execution').write_bytes(packets.canonical(execution))
        self.f.reader.seal('successor', lifecycle._binding(self.f.store, ledger, 'successor'))
        with self.assertRaises(lifecycle.LifecycleError):
            self.f.host.acquire_attempt('successor', expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.f.current()[0]['generation'], 1)

    def test_sealed_proof_requires_independent_current_readback(self):
        ledger, _, _ = self.prepare()
        with mock.patch.object(self.f.reader, 'readback_unused_source', return_value=b'{}'):
            with self.assertRaises(lifecycle.LifecycleError):
                self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.f.current()[0]['generation'], 0)

    def test_source_ttl_is_the_only_exemption(self):
        for mutate in (lambda p: p['targets'][0]['qualification'].update(status='revoked'),
                lambda p: p['targets'][0]['availability'].update(observed_at=0),
                lambda p: p['targets'][0]['qualification'].update(scopes=['other']),
                lambda p: p['authorization'].update(status='revoked'),
                lambda p: p['secret_check'].update(status='unknown'),
                lambda p: p['targets'][0].update(id='renamed'),
                lambda p: p['targets'][0]['qualification'].update(observed_at=100)):
            with self.subTest(mutate=mutate):
                op = 'negative'+str(len(list(self.f.reader.root.glob('negative*'))))
                with self.assertRaises(ValueError): self.acquire(op, mutate=mutate)
        self.assertEqual(self.f.current()[0]['generation'], 0)

    def test_destination_context_and_subscription_never_use_source_exemption(self):
        for mutate in (lambda p: p['targets'][2]['context'].update(client_limit=1299),
                lambda p: p['targets'][2]['context'].update(observed_at=0),
                lambda p: p['targets'][2]['executor'].update(status='unavailable'),
                lambda p: p['targets'][2]['identity'].update(billing='api')):
            op = 'bad'+str(len(list(self.f.reader.root.glob('bad*'))))
            with self.assertRaises(ValueError): self.acquire(op, mutate=mutate)
        self.assertEqual(self.f.current()[0]['generation'], 0)

    def test_current_destination_gate_prevents_launch_and_keeps_replay_readable(self):
        self.acquire()
        for mutate in (lambda p: p['targets'][2]['qualification'].update(status='revoked'),
                lambda p: p['targets'][0]['qualification'].update(status='revoked'),
                lambda p: p['targets'][2]['context'].update(input_tokens=999),
                lambda p: p['targets'][2]['context'].update(client_limit=1299),
                lambda p: p['targets'][2]['context'].update(observed_at=0),
                lambda p: p['targets'][0]['qualification'].update(observed_at=111)):
            op = 'launch'+str(len(list(self.f.reader.root.glob('launch*'))))
            with self.assertRaises(lifecycle.LifecycleError): self.intent('launch-intent', op, mutate)
            self.f.current()
        self.assertEqual(self.f.backend.launch_count, 0)
        self.intent('launch-intent', 'launch-good')
        self.assertEqual(self.f.backend.launch_count, 1)

    def test_proof_domain_expiry_and_bool_schema_are_rejected(self):
        for mutate in (lambda proof: proof['binding'].update(domain='legacy-unused-source'),
                lambda proof: proof.update(expires_at=110), lambda proof: proof.update(schema_version=True)):
            op = 'proof'+str(len(list(self.f.reader.root.glob('proof*'))))
            with self.assertRaises(ValueError): self.acquire(op, proof_mutate=mutate)

    def test_current_callback_lock_drift_cannot_commit_claim(self):
        ledger, _, _ = self.prepare()
        original = self.f.reader.readback_unused_source
        def drift(binding):
            path = self.f.store.root / 'packet' / 'lock'
            path.rename(path.with_name('old-lock')); path.write_bytes(b''); path.chmod(0o600)
            return original(binding)
        with mock.patch.object(self.f.reader, 'readback_unused_source', side_effect=drift):
            with self.assertRaises(packets.PacketError):
                self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.f.current()[0]['generation'], 0)

    def test_source_previously_acquired_is_not_unused(self):
        f = self.f; f.acquire(); f.start(); f.stop(); f.observe()
        f.record_fact('failure', 'outcome', f.failure('retriable-service'))
        f.publish(); f.finish()
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('official', 'a2')
        self.assertEqual(f.current()[0]['generation'], 1)

    def test_quality_retry_retains_correction_and_stops_after_confirmed_exhaustion(self):
        self.acquire(); self.failed(quality=True)
        self.acquire('successor', 'a2'); _, before = self.failed('2', quality=True, correction=True)
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('third', 'a3')
        after = self.f.current()[1]
        self.assertEqual(after['events'], before['events'])
        self.assertEqual(after['correction_rounds'], 1); self.assertEqual(after['stage_floor'], 2)

    def test_live_destination_revocation_blocks_export_publish_and_finish(self):
        self.acquire(); f = self.f; self.intent('launch-intent', 'launch')
        f.stop(); f.observe()
        revoke = lambda p: p['targets'][2]['qualification'].update(status='revoked')
        future = lambda p: p['targets'][0]['qualification'].update(observed_at=111)
        with self.assertRaises(lifecycle.LifecycleError): self.intent('export-intent', 'bad-export', revoke)
        with self.assertRaises(lifecycle.LifecycleError): self.intent('export-intent', 'future-export', future)
        self.assertEqual(f.backend.export_count, 0)
        self.intent('export-intent', 'export')
        ledger, _ = f.current(); binding = ledger['supervisors']['a1']['binding']; raw = f.backend.inspect(binding)
        manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(raw)))
        self.destination('publish', revoke)
        payload = dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest))
        revision = f.save('bad-publish', 'publish', payload, runtime=True)
        with self.assertRaises(lifecycle.LifecycleError): f.host.publish('bad-publish', expected_revision=revision, now=110)
        self.destination('publish', future)
        revision = f.save('future-publish', 'publish', payload, runtime=True)
        with self.assertRaises(lifecycle.LifecycleError): f.host.publish('future-publish', expected_revision=revision, now=110)
        self.assertIsNone(f.current()[0]['checkpoint'])
        self.destination('publish')
        revision = f.save('publish', 'publish', payload, runtime=True)
        f.host.publish('publish', expected_revision=revision, now=110)
        self.destination('finish', revoke)
        with self.assertRaises(lifecycle.LifecycleError): f.finish(result='completed', op='bad-finish')
        self.destination('finish', future)
        with self.assertRaises(lifecycle.LifecycleError): f.finish(result='completed', op='future-finish')
        self.assertIsNotNone(f.current()[1]['owner'])

    def test_new_claim_live_destination_and_original_archive_fail_closed(self):
        ledger, raw, _ = self.prepare()
        self.save_destination(ledger, raw, 'acquire', lambda p: p['targets'][2]['context'].update(client_limit=1299))
        with self.assertRaises(lifecycle.LifecycleError):
            self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        self.save_destination(ledger, raw, 'acquire')
        self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        current, _ = self.f.current(); ref = next(r for r in current['governance']['records'] if r['kind'] == 'acquire')
        path = self.f.store.root / 'packet' / ('lifecycle-'+ref['execution_sha256']+'.json')
        original = trust._read
        with mock.patch('agent_qualification._read', side_effect=lambda fd, name, limit:
                (_ for _ in ()).throw(packets.PacketError('original archive missing')) if name == path.name
                else original(fd, name, limit)):
            with self.assertRaises(packets.PacketError): self.f.current()

    def test_schema1_official_admission_preserves_original_contract(self):
        f = baseline.LifecycleTests(); self.addCleanup(f.doCleanups)
        original = baseline.SavedReader.save
        def admission(reader, op, kind, payload, **kwargs):
            if kind == 'admit':
                reader.request.update(target_id='official', target_identity=fixture()['targets'][2]['identity'], stage='official')
            return original(reader, op, kind, payload, **kwargs)
        with mock.patch.object(baseline.SavedReader, 'save', admission):
            f.setUp()
        p = fixture(); p['targets'][0]['availability']['status'] = 'unavailable'
        ledger, state = f.acquire(planning=p)
        self.assertEqual(ledger['generation'], 1); self.assertEqual(state['stage_floor'], 2)
        f.controller('alias2').snapshot(now=110)

    def test_future_live_source_qualification_blocks_new_claim(self):
        ledger, raw, _ = self.prepare()
        self.save_destination(ledger, raw, 'acquire', lambda p: p['targets'][0]['qualification'].update(observed_at=111))
        with self.assertRaises(lifecycle.LifecycleError):
            self.f.host.acquire_attempt('acquire', expected_revision=ledger['revision'], now=110)
        self.assertEqual(self.f.current()[0]['generation'], 0)



if __name__ == '__main__':
    unittest.main()
