"""Original v6 actual-acquire history; host-only synthetic tier continuation."""
import copy
import json
import unittest
from unittest import mock

from tests import test_model_packet_lifecycle as baseline
from tests import test_model_packet_unused_source as unused
from tests.test_model_failover import fixture
import agent_routing
import model_packet_lifecycle as lifecycle
import model_packet_store as packets
import model_failover as failover


class HistoryReader(unused.ProofReader):
    def readback_v6_historical_sources(self, binding):
        return (self.root / ('historical-' + packets.digest(packets.canonical(binding)))).read_bytes()


class HistoricalLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.u = unused.UnusedLifecycleTests(); self.u.setUp(); self.addCleanup(self.u.doCleanups)
        self.f = self.u.f; f = self.f
        f.reader = HistoryReader(f.reader.root, f.store, f.backend, f.request)
        f.host = f.controller()
        self.u.planning = fixture(); self.planning = self.u.planning
        self.executions = self.u.executions

    def base_acquire(self, op, attempt, stage='internal', mutate=None):
        f = self.f; p = copy.deepcopy(self.planning)
        p['current_target'] = f.current()[1]['events'][-1]['target_id'] if f.current()[1]['events'] else 'internal'
        f.request.update(target_id=stage, target_identity=p['targets'][['internal', 'internal-best', 'official'].index(stage)]['identity'], stage=stage)
        if mutate: mutate(p)
        result = f.acquire(op, attempt, planning=p)
        self.executions[attempt] = (f.reader.root / op / 'execution').read_bytes()
        return result

    def failed(self, suffix, *, correction=False, cause='capability', kind='quality'):
        f = self.f; raw = self.executions[f.request['attempt_id']]; execution = json.loads(raw)
        v3 = execution['schema_version'] == 3
        if v3: self.u.intent('launch-intent', 'launch'+suffix)
        else: f.start('launch'+suffix)
        f.stop(); f.observe('observe'+suffix)
        event = f.failure(cause); event.update(kind=kind, defect_id='A', correction=correction)
        prior = f.current()[1]['events']; previous = prior[-1]['target_id'] if prior else 'internal'
        if f.request['target_id'] != previous:
            event['transition'] = dict(source_identity_sha256=failover.identity_digest(
                execution['failover_payload']['targets'][['internal', 'internal-best', 'official'].index(previous)]['identity']),
                reason='confirmed-capability-escalation', observed_at=110, evidence_sha256='e'*64)
        f.record_fact('outcome'+suffix, 'outcome', event)
        if v3:
            self.u.intent('export-intent', 'export'+suffix)
            ledger, _ = f.current(); binding = ledger['supervisors'][f.request['attempt_id']]['binding']
            manifest = packets.canonical(dict(binding=binding, patch_sha256=packets.digest(b''), runtime_sha256=packets.digest(f.backend.inspect(binding))))
            self.u.destination('publish')
            revision = f.save('publish'+suffix, 'publish', dict(patch_sha256=packets.digest(b''), checkpoint_sha256=packets.digest(manifest)), runtime=True)
            f.host.publish('publish'+suffix, expected_revision=revision, now=110)
            self.u.destination('finish')
        else: f.publish(suffix)
        return f.finish(op='finish'+suffix)

    def exhaust_internal(self):
        self.base_acquire('old1', 'a1'); self.failed('1')
        self.base_acquire('old2', 'a2'); return self.failed('2', correction=True)

    def exhaust_best(self):
        self.exhaust_internal()
        self.base_acquire('old3', 'a3', 'internal-best'); self.failed('3')
        self.base_acquire('old4', 'a4', 'internal-best'); return self.failed('4', correction=True)

    def upgrade(self, destination='internal-best'):
        f = self.f
        f.request['v2_task']['factors'].update(ambiguity='high', reasoning_depth='deep', code_context_volume='large')
        self.planning['task']['capability_tier'] = 'advanced'
        self.planning['targets'][['internal', 'internal-best', 'official'].index(destination)]['qualification']['capability_tier'] = 'advanced'

    def prepare(self, op='new', attempt='a3', stage='internal-best', mutate=None, proof_mutate=None):
        f = self.f; ledger, state = f.current(); p = copy.deepcopy(self.planning)
        p['events'] = copy.deepcopy(state['events']); p['current_target'] = p['events'][-1]['target_id'] if p['events'] else 'internal'
        if mutate: mutate(p)
        destination = p['targets'][['internal', 'internal-best', 'official'].index(stage)]
        f.request.update(attempt_id=attempt, generation=ledger['generation']+1,
            target_id=stage, target_identity=destination['identity'], stage=stage)
        f.reader.save(op, 'acquire', dict(owner_id='owner', epoch=state['owner_epoch']+1), request=f.request, planning=p)
        binding = lifecycle._binding(f.store, ledger, op); directory = f.reader.root / op
        request_raw = (directory / 'request').read_bytes(); classification_raw = (directory / 'classification').read_bytes()
        execution = dict(schema_version=3, binding=binding, governance_request_sha256=packets.digest(request_raw),
            attempt_id=attempt, generation=f.request['generation'], predecessor_sha256=ledger['checkpoint'],
            target_id=stage, target_identity=f.request['target_identity'], failover_payload=p,
            host_id='host', backend_id='backend', runtime_policy_sha256='d'*64, runtime_id='runtime-'+attempt)
        refs = [r for r in ledger['governance']['records'] if r['kind'] == 'acquire']
        facts = []; qualifications = []
        traversed = {0, ['internal','internal-best','official'].index(p['current_target'])} | {['internal','internal-best','official'].index(e['target_id']) for e in p['events']}
        for index in sorted(traversed):
            source = p['targets'][index]
            if source['id'] == stage or failover.TIER_RANK[source['qualification']['capability_tier']] >= failover.TIER_RANK[p['task']['capability_tier']]: continue
            originals = [r for r in refs if json.loads((f.store.root / 'packet' / ('lifecycle-'+r['request_sha256']+'.json')).read_bytes())['target_id'] == source['id']]
            tiers = [json.loads((f.store.root / 'packet' / ('lifecycle-'+r['classification_sha256']+'.json')).read_bytes())['capability_tier'] for r in originals]
            facts.append(dict(id=source['id'], identity_sha256=failover.identity_digest(source['identity']), stage=source['stage'],
                required_tier=max(tiers, key=failover.TIER_RANK.__getitem__) if tiers else 'everyday', acquire_operations=[r['operation_id'] for r in originals]))
            qualifications.append(source['qualification'])
        decision = copy.deepcopy(p)
        for event in decision['events']: event['cause'] = state['resolved_causes'].get(event['attempt_id'], event['cause'])
        proof_binding = dict(binding, domain='v6-historical-source/1', attempt_id=attempt, runtime_id='runtime-'+attempt,
            governance_request_sha256=packets.digest(request_raw), classification_sha256=packets.digest(classification_raw),
            execution_core_sha256=packets.digest(packets.canonical(execution)), planning_sha256=packets.digest(packets.canonical(p)),
            decision_sha256=packets.digest(packets.canonical(decision)), historical_acquires_sha256=packets.digest(packets.canonical(refs)),
            sources_sha256=packets.digest(packets.canonical(facts)), qualifications_sha256=packets.digest(packets.canonical(qualifications)),
            destination_id=stage, destination_identity_sha256=failover.identity_digest(destination['identity']),
            authorization_sha256=packets.digest(packets.canonical(p['authorization'])), secret_check_sha256=packets.digest(packets.canonical(p['secret_check'])))
        proof = dict(schema_version=3, binding=proof_binding, coverage='complete', authorization_status='granted',
            qualification_status='qualified', observed_at=110, expires_at=170, evidence_sha256='e'*64)
        if proof_mutate: proof_mutate(proof)
        raw_proof = packets.canonical(proof); execution['historical_source_bytes'] = raw_proof.decode()
        execution_raw = packets.canonical(execution); self.executions[attempt] = execution_raw
        (directory / 'execution').write_bytes(execution_raw)
        (f.reader.root / ('historical-'+packets.digest(packets.canonical(proof_binding)))).write_bytes(raw_proof)
        f.reader.seal(op, binding); self.u.save_destination(ledger, execution_raw, 'acquire')
        return ledger, execution_raw, proof_binding

    def acquire(self, op='new', attempt='a3', stage='internal-best', **kwargs):
        ledger, _, _ = self.prepare(op, attempt, stage, **kwargs)
        return self.f.host.acquire_attempt(op, expected_revision=ledger['revision'], now=110)

    def test_upgrade_best_uses_original_internal_requirement_without_budget_reset(self):
        before, state = self.exhaust_internal(); self.upgrade()
        after, new = self.acquire()
        self.assertEqual(new['events'], state['events']); self.assertEqual(new['correction_rounds'], 1)
        self.assertEqual(new['required_tier_floors'], {'balanced-worker':'advanced'})
        self.assertEqual(new['stage_floor'], 1); self.assertEqual(new['generation'], 3)
        self.assertEqual(after['attempts'][-1]['predecessor_sha256'], before['checkpoint'])
        self.u.intent('launch-intent', 'new-launch'); self.assertEqual(self.f.backend.launch_count, 3)

    def test_upgrade_official_and_retry_keep_two_historical_sources_and_all_floors(self):
        _, state = self.exhaust_best(); self.upgrade('official')
        _, new = self.acquire('official', 'a5', 'official')
        self.assertEqual(new['events'], state['events']); self.assertEqual(new['stage_floor'], 2)
        self.failed('5', kind='service', cause='retriable-service')
        _, retry = self.acquire('retry', 'a6', 'official')
        self.assertEqual(retry['correction_rounds'], 2); self.assertEqual(retry['service_failures'], 1)
        self.assertEqual(retry['required_tier_floors'], {'balanced-worker':'advanced'})
        self.assertEqual(retry['generation'], 6)

    def test_replay_never_asks_today_reader_or_relaunches(self):
        self.exhaust_internal(); self.upgrade(); self.acquire()
        with mock.patch.object(self.f.reader, 'readback_v6_historical_sources', side_effect=AssertionError('today')):
            self.f.current(); self.f.host.acquire_attempt('new', expected_revision=0, now=110)
        self.assertEqual(self.f.backend.launch_count, 2)

    def test_never_acquired_source_has_no_historical_entitlement(self):
        self.planning['targets'][0]['availability']['status'] = 'unavailable'; self.upgrade('official')
        with self.assertRaises(ValueError): self.acquire('no-history', 'a1', 'official')
        self.assertEqual(self.f.current()[0]['generation'], 0)

    def test_tier_upgrade_alone_cannot_skip_quality_threshold_or_retry_destination(self):
        self.base_acquire('old1','a1'); self.failed('1'); self.upgrade()
        with self.assertRaises(lifecycle.LifecycleError): self.acquire('too-early','a2')
        self.assertEqual(self.f.current()[0]['generation'], 1)

    def test_missing_original_acquire_archive_cannot_be_backfilled_by_today_proof(self):
        self.exhaust_internal(); self.upgrade(); ledger, _, _ = self.prepare()
        original = next(r for r in ledger['governance']['records'] if r['kind']=='acquire')
        path = self.f.store.root/'packet'/('lifecycle-'+original['authority_sha256']+'.json')
        path.rename(path.with_suffix('.missing'))
        with self.assertRaises(FileNotFoundError): self.f.host.acquire_attempt('new', expected_revision=ledger['revision'], now=110)

    def test_independent_claim_readback_and_full_coverage_are_required(self):
        self.exhaust_internal(); self.upgrade(); ledger, _, _ = self.prepare()
        with mock.patch.object(self.f.reader,'readback_v6_historical_sources',return_value=b'{}'):
            with self.assertRaises(lifecycle.LifecycleError): self.f.host.acquire_attempt('new',expected_revision=ledger['revision'],now=110)
        for i, mutate in enumerate((lambda x:x.update(coverage='partial'),lambda x:x.update(schema_version=True),
                lambda x:x.update(expires_at=110),lambda x:x['binding'].update(domain='legacy-historical-source'))):
            with self.subTest(i=i):
                with self.assertRaises(ValueError): self.acquire('bad-proof'+str(i), proof_mutate=mutate)
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_source_freshness_revocation_scope_class_and_identity_are_not_exempt(self):
        self.exhaust_internal(); self.upgrade()
        changes=(lambda p:p['targets'][0]['qualification'].update(observed_at=0),
            lambda p:p['targets'][0]['qualification'].update(observed_at=111),
            lambda p:p['targets'][0]['qualification'].update(status='revoked'),
            lambda p:p['targets'][0]['qualification'].update(scopes=['other']),
            lambda p:p['targets'][0]['qualification'].update(capability_class='security-reviewer'),
            lambda p:p['targets'][0]['identity'].update(model='renamed'),
            lambda p:p['authorization'].update(status='revoked'),lambda p:p['secret_check'].update(status='present'))
        for i, change in enumerate(changes):
            with self.subTest(i=i):
                with self.assertRaises(ValueError): self.acquire('source'+str(i),mutate=change)
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_current_source_and_destination_gate_at_launch_export_publish_finish(self):
        self.exhaust_internal(); self.upgrade(); self.acquire()
        stale=lambda p:p['targets'][0]['qualification'].update(observed_at=0)
        with self.assertRaises(lifecycle.LifecycleError):self.u.intent('launch-intent','stale-launch',stale)
        self.u.intent('launch-intent','good-launch'); self.f.stop();self.f.observe('new-observe')
        with self.assertRaises(lifecycle.LifecycleError):self.u.intent('export-intent','stale-export',stale)
        self.u.intent('export-intent','good-export')
        ledger,_=self.f.current();binding=ledger['supervisors']['a3']['binding'];manifest=packets.canonical(dict(binding=binding,patch_sha256=packets.digest(b''),runtime_sha256=packets.digest(self.f.backend.inspect(binding))))
        self.u.destination('publish',stale);revision=self.f.save('publish-new','publish',dict(patch_sha256=packets.digest(b''),checkpoint_sha256=packets.digest(manifest)),runtime=True)
        with self.assertRaises(lifecycle.LifecycleError):self.f.host.publish('publish-new',expected_revision=revision,now=110)
        self.u.destination('publish');self.f.host.publish('publish-new',expected_revision=revision,now=110)
        self.u.destination('finish',stale)
        with self.assertRaises(lifecycle.LifecycleError):self.f.finish(result='completed',op='bad-finish')
        self.u.destination('finish');self.f.finish(result='completed',op='good-finish')

    def test_current_destination_full_context_executor_subscription_and_no_reservation_shrink(self):
        self.exhaust_internal();self.upgrade();self.acquire()
        changes=(lambda p:p['targets'][1]['context'].update(client_limit=1299),
            lambda p:p['targets'][1]['context'].update(input_tokens=999),
            lambda p:p['targets'][1]['executor'].update(status='unsupported'),
            lambda p:p['targets'][1]['qualification'].update(capability_tier='everyday'),
            lambda p:p['targets'][1]['qualification'].update(observed_at=0))
        for i,change in enumerate(changes):
            with self.assertRaises(lifecycle.LifecycleError):self.u.intent('launch-intent','bad-destination'+str(i),change)
        self.assertEqual(self.f.backend.launch_count,2)

    def test_new_prefix_requires_new_proof_and_host_callback_drift_blocks_commit(self):
        self.exhaust_internal();self.upgrade();ledger,_,_=self.prepare()
        original=self.f.reader.readback_v6_historical_sources
        def drift(binding):
            path=self.f.store.root/'packet'/'lock';path.rename(path.with_name('old-lock'));path.write_bytes(b'');path.chmod(0o600)
            return original(binding)
        with mock.patch.object(self.f.reader,'readback_v6_historical_sources',side_effect=drift):
            with self.assertRaises(packets.PacketError):self.f.host.acquire_attempt('new',expected_revision=ledger['revision'],now=110)
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_guard_modes_cannot_be_combined_or_loaded_from_json(self):
        with self.assertRaises(failover.FailoverError):failover.select_next(fixture(),_trusted_v6_historical_source_guard={})
        with self.assertRaises(failover.FailoverError):failover.select_next(fixture(),_trusted_v6_historical_source_guard={},_trusted_v6_unused_source_guard={})

    def test_nonfallback_outcome_cannot_gain_another_model_from_historical_tier(self):
        for cause in ('auth','permission','config','context','secret'):
            with self.subTest(cause=cause):
                f=baseline.LifecycleTests();f.setUp()
                try:
                    f.acquire();f.start();f.stop();f.observe();f.record_fact('outcome','outcome',f.failure(cause));f.publish();f.finish()
                    p=fixture();p['events']=f.current()[1]['events'];p['task']['capability_tier']='advanced';p['targets'][2]['qualification']['capability_tier']='advanced'
                    self.assertEqual(failover.select_next(p)['status'],'blocked')
                finally:f.doCleanups()

    def test_highest_original_requirement_cannot_use_an_earlier_lower_acquire(self):
        self.base_acquire('old1','a1');self.failed('1')
        self.upgrade('internal');self.base_acquire('old2','a2');self.failed('2',correction=True)
        self.planning['targets'][0]['qualification']['capability_tier']='everyday'
        self.upgrade('internal-best')
        with self.assertRaises(lifecycle.LifecycleError):self.acquire()
        self.assertEqual(self.f.current()[1]['required_tier_floors'],{'balanced-worker':'advanced'})
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_predecessor_and_resolved_unknown_causes_survive_historical_continuation(self):
        self.base_acquire('old1','a1');self.failed('1',cause='unknown')
        original=self.f.current()[1]['events'][0]
        self.f.record_fact('resolve','resolve',dict(event_sha256=packets.digest(packets.canonical(original)),cause='capability'))
        self.base_acquire('old2','a2');self.failed('2',correction=True)
        self.upgrade();before,state=self.f.current();after,new=self.acquire()
        self.assertEqual(new['events'][0]['cause'],'unknown')
        self.assertEqual(new['resolved_causes'],state['resolved_causes'])
        self.assertEqual(after['attempts'][-1]['predecessor_sha256'],before['checkpoint'])
        self.assertEqual(new['service_failures'],0);self.assertEqual(new['correction_rounds'],1)

    def test_gratuitous_schema3_proof_and_pending_owner_never_grant_a_claim(self):
        self.base_acquire('old1','a1');self.upgrade()
        with self.assertRaises(lifecycle.LifecycleError):self.acquire('pending','a2')
        self.assertEqual(self.f.current()[1]['owner']['attempt_id'],'a1')
        self.f.request.update(attempt_id='a1',generation=1,target_id='internal',target_identity=self.planning['targets'][0]['identity'],stage='internal')
        self.f.request['v2_task']['factors']=copy.deepcopy(baseline.route_fixture()['task']['factors'])
        self.planning.clear();self.planning.update(fixture())
        self.failed('1');self.base_acquire('old2','a2');self.failed('2',correction=True)
        self.upgrade()
        self.planning['targets'][0]['qualification']['capability_tier']='advanced'
        with self.assertRaises(lifecycle.LifecycleError):self.acquire('gratuitous','a3')
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_official_subscription_destination_and_exhaustion_remain_strict(self):
        self.exhaust_best();self.upgrade('official')
        with self.assertRaises(ValueError):self.acquire('api','a5','official',mutate=lambda p:p['targets'][2]['identity'].update(billing='api'))
        self.acquire('official','a5','official')
        for i in range(5,8):
            self.failed(str(i),kind='service',cause='retriable-service')
            if i<7:self.acquire('retry'+str(i),'a'+str(i+1),'official')
        with self.assertRaises(lifecycle.LifecycleError):self.acquire('exhausted','a8','official')
        state=self.f.current()[1];self.assertEqual(state['service_failures'],3)
        self.assertEqual(state['correction_rounds'],2);self.assertEqual(state['stage_floor'],2)

    def test_claim_proof_cannot_be_reused_at_a_successor_prefix(self):
        self.exhaust_best();self.upgrade('official');self.acquire('official','a5','official')
        old=json.loads(self.executions['a5'])['historical_source_bytes'];self.failed('5',kind='service',cause='retriable-service')
        ledger,raw,_=self.prepare('successor','a6','official');execution=json.loads(raw);execution['historical_source_bytes']=old
        path=self.f.reader.root/'successor'/'execution';path.write_bytes(packets.canonical(execution))
        self.f.reader.seal('successor',lifecycle._binding(self.f.store,ledger,'successor'))
        with self.assertRaises(lifecycle.LifecycleError):self.f.host.acquire_attempt('successor',expected_revision=ledger['revision'],now=110)
        self.assertEqual(self.f.current()[0]['generation'],5)

    def test_post_intent_missing_live_proof_keeps_durable_intent_without_launch(self):
        self.exhaust_internal();self.upgrade();self.acquire()
        revision=self.f.save('intent','launch-intent',{});self.u.destination('launch-intent')
        with self.assertRaises(FileNotFoundError):self.f.host.launch_reserved('intent',expected_revision=revision,now=110)
        ledger,_=self.f.current();self.assertEqual(ledger['supervisors']['a3']['stage'],'launch-intent')
        self.f.host.launch_reserved('intent',expected_revision=revision,now=110)
        self.assertEqual(self.f.backend.launch_count,2)

    def test_execution_version_size_and_historical_manifest_binding_are_strict(self):
        self.exhaust_internal();self.upgrade()
        for i,change in enumerate((lambda e:e.update(schema_version=True),lambda e:e.update(unused_source_bytes='{}'),
                lambda e:e.update(historical_source_bytes='x'*16385),lambda e:e.update(generation=True))):
            op='typed'+str(i);ledger,raw,_=self.prepare(op);execution=json.loads(raw);change(execution)
            (self.f.reader.root/op/'execution').write_bytes(packets.canonical(execution));self.f.reader.seal(op,lifecycle._binding(self.f.store,ledger,op))
            with self.assertRaises(ValueError):self.f.host.acquire_attempt(op,expected_revision=ledger['revision'],now=110)
        for i,change in enumerate((lambda p:p['binding'].update(historical_acquires_sha256='0'*64),
                lambda p:p['binding'].update(classification_sha256='0'*64),lambda p:p['binding'].update(sources_sha256='0'*64))):
            with self.assertRaises(ValueError):self.acquire('manifest'+str(i),proof_mutate=change)
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_quarantined_original_acquire_retains_history_and_prior_checkpoint(self):
        self.base_acquire('old1','a1');before,_=self.failed('1')
        self.base_acquire('old2','a2');self.f.start('launch2')
        binding=self.f.current()[0]['supervisors']['a2']['binding']
        self.f.backend.set_state(binding,'isolated');self.f.observe('isolated2')
        event=self.f.failure('capability');event.update(kind='quality',defect_id='A',correction=True)
        self.f.record_fact('outcome2','outcome',event);self.f.finish(op='finish2')
        self.upgrade();after,state=self.acquire()
        self.assertEqual(after['attempts'][1]['status'],'quarantined')
        self.assertEqual(after['attempts'][-1]['predecessor_sha256'],before['checkpoint'])
        self.assertEqual(state['correction_rounds'],1)
        self.f.backend.set_state(binding,'running')
        with self.assertRaises(lifecycle.LifecycleError):self.u.intent('launch-intent','isolation-lost')
        self.assertEqual(self.f.backend.launch_count,2)

    def test_original_acquire_aggregate_has_an_explicit_bound(self):
        self.exhaust_internal();self.upgrade()
        with mock.patch.object(lifecycle,'MAX_HISTORICAL_ACQUIRE_BYTES',1):
            with self.assertRaises(lifecycle.LifecycleError):self.acquire()
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_all_acquired_sources_keep_identity_even_without_tier_exemption(self):
        self.exhaust_best();self.upgrade('official')
        def replacement(p):
            source=p['targets'][1];source['identity']['model']='replacement-best'
            sha=failover.identity_digest(source['identity'])
            source['qualification'].update(capability_tier='advanced',identity_sha256=sha)
            p['authorization']['target_identity_sha256'][1]=sha
        with self.assertRaisesRegex(lifecycle.LifecycleError,'selection-unconfirmed'):
            self.acquire('replacement','a5','official',mutate=replacement)
        self.assertEqual(self.f.current()[0]['generation'],4)
        self.assertEqual(self.f.backend.launch_count,4)
        self.acquire('valid-official','a5','official')
        self.u.intent('launch-intent','valid-launch')
        self.assertEqual(self.f.backend.launch_count,5)
