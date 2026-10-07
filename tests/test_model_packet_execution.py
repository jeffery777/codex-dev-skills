"""R2 saved fixture chain; no real model, writer, container or OS proof."""
import copy
import json
import unittest
from unittest import mock

from tests import test_model_packet_lifecycle as baseline
from tests import test_model_packet_bootstrap as b1
from tests import test_model_packet_historical_source as historical
from tests import test_model_packet_unused_source as unused
from tests.test_model_failover import fixture
import model_packet_bootstrap as bootstrap
import model_packet_execution as execution
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets


class ExecutedLifecycleTests(unittest.TestCase):
    destination = b1.BootstrapFixtureTests.destination
    plan = b1.BootstrapFixtureTests.plan
    prepare = b1.BootstrapFixtureTests.prepare
    confirmation_payload = b1.BootstrapFixtureTests.confirmation_payload
    confirm = b1.BootstrapFixtureTests.confirm
    intent = b1.BootstrapFixtureTests.intent
    bootstrap_payload = b1.BootstrapFixtureTests.bootstrap_payload
    bootstrapped = b1.BootstrapFixtureTests.bootstrapped

    def setUp(self):
        self.f=baseline.LifecycleTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f
        for name in ('executed-packets','executed-reader','executed-backend'):
            (f.root/name).mkdir(mode=0o700)
        f.store=packets.PacketStore(f.root/'executed-packets','packet');f.store.prepare('a'*64)
        f.backend=execution.SavedExecutionBackend(f.root/'executed-backend')
        f.reader=historical.HistoryReader(f.root/'executed-reader',f.store,f.backend,f.request)
        f.host=self.controller();self.execution=None
        f.reader.save('admit','admit-bootstrap',f.host.admission_payload())
        with f.store.locked() as fd: ledger=f.store._read(fd)
        f.reader.seal('admit',lifecycle._binding(f.store,ledger,'admit'))
        f.host.admit_new('admit',expected_revision=0,now=110)

    def controller(self, backend=None):
        f=self.f
        return execution.SyntheticExecutedLifecycle(f.store,f.reader,f.backend if backend is None else backend,
            alias='alias1',host_id='host',backend_id='backend',policy_sha256='d'*64)

    def acquire(self,op='acquire',attempt='a1',planning=None):
        f=self.f;ledger,state=f.current();f.request.update(generation=ledger['generation']+1,attempt_id=attempt)
        p=copy.deepcopy(planning if planning is not None else fixture());p['events']=copy.deepcopy(state['events'])
        if state['events']:p['current_target']=state['events'][-1]['target_id']
        f.reader.save(op,'acquire',dict(owner_id='owner',epoch=state['owner_epoch']+1),request=f.request,planning=p)
        directory=f.reader.root/op;binding=lifecycle._binding(f.store,ledger,op)
        self.execution=packets.canonical(dict(schema_version=1,binding=binding,
            governance_request_sha256=packets.digest((directory/'request').read_bytes()),attempt_id=attempt,
            generation=f.request['generation'],predecessor_sha256=ledger['checkpoint'],
            target_id=f.request['target_id'],target_identity=f.request['target_identity'],failover_payload=p,
            host_id='host',backend_id='backend',runtime_policy_sha256='d'*64,runtime_id='runtime-'+attempt))
        (directory/'execution').write_bytes(self.execution);f.reader.seal(op,binding)
        self.destination(ledger,'acquire')
        return f.host.acquire_attempt(op,expected_revision=ledger['revision'],now=110)

    def save(self,op,kind,payload,*,post=True,mutate=None,runtime=False):
        f=self.f;ledger,_=f.current()
        binding=ledger['supervisors'][ledger['attempts'][-1]['id']]['binding']
        actual=f.backend.inspect(binding) if runtime else None
        f.reader.save(op,kind,payload,request=f.request,runtime=actual)
        refbinding=lifecycle._binding(f.store,ledger,op);f.reader.seal(op,refbinding)
        self.destination(ledger,kind,mutate)
        if post:
            future=copy.deepcopy(ledger);evidence=f.reader.readback_evidence(refbinding)
            ref=dict(operation_id=op,kind=kind,binding=refbinding,committed_at=110)
            ref.update({field+'_sha256':None if getattr(evidence,field) is None else packets.digest(getattr(evidence,field)) for field in lifecycle.FIELDS})
            future['governance']['records'].append(ref);future['revision']+=1
            self.destination(future,kind,mutate)
        return ledger['revision']

    def chain(self,suffix=''):
        self.prepare('prepare'+suffix);self.confirm('prepared'+suffix)
        self.input_raw=self.f.host.input_bootstrap(now=110)
        self.intent('bootstrap'+suffix);return self.bootstrapped('bootstrapped'+suffix)

    def launch(self,op='launch',*,post=True):
        revision=self.save(op,'launch-intent',{},post=post)
        return self.f.host.launch_reserved(op,expected_revision=revision,now=110)

    def observe(self,op='observe'):
        revision=self.save(op,'observe',{},runtime=True)
        return self.f.host.reconcile(op,expected_revision=revision,now=110)

    def binding(self):
        ledger,_=self.f.current();return ledger['supervisors'][self.f.request['attempt_id']]['binding']

    def stop(self,state='stopped',effects='excluded'):
        self.f.backend.set_state(self.binding(),state,effects)

    def publish(self,suffix=''):
        f=self.f;revision=self.save('export'+suffix,'export-intent',{})
        f.host.seal('export'+suffix,expected_revision=revision,now=110)
        binding=self.binding();actual=f.backend.inspect(binding)
        manifest=packets.canonical(dict(binding=binding,patch_sha256=packets.digest(b''),runtime_sha256=packets.digest(actual)))
        revision=self.save('publish'+suffix,'publish',dict(patch_sha256=packets.digest(b''),checkpoint_sha256=packets.digest(manifest)),runtime=True)
        return f.host.publish('publish'+suffix,expected_revision=revision,now=110)

    def finish(self,result='completed',op='finish'):
        ledger,state=self.f.current();owner=state['owner']
        revision=self.save(op,'finish',dict(result=result,owner_id=owner['owner_id'],epoch=owner['epoch']),runtime=True)
        return self.f.host.finish_attempt(op,expected_revision=revision,now=110)

    def fail(self,suffix='',cause='capability',correction=False,isolated=False):
        self.chain(suffix);self.launch('launch'+suffix)
        self.stop('isolated' if isolated else 'stopped');self.observe('observe'+suffix)
        event=self.f.failure(cause)
        event.update(kind='quality' if cause=='capability' else 'service',defect_id='A',correction=correction)
        revision=self.save('outcome'+suffix,'outcome',event)
        self.f.host.record('outcome'+suffix,'outcome',expected_revision=revision,now=110)
        if not isolated:self.publish(suffix)
        return self.finish('failed','finish'+suffix)

    def history(self):
        h=historical.HistoricalLifecycleTests();h.f=self.f;h.planning=fixture();h.executions={}
        h.u=unused.UnusedLifecycleTests();h.u.f=self.f;h.u.planning=h.planning;h.u.executions=h.executions
        return h

    def test_full_completed_chain_uses_bound_runtime_and_original_execution(self):
        self.acquire();acquired,_=self.f.current();core=copy.deepcopy(acquired['supervisors']['a1']['binding'])
        self.chain();self.launch();binding=self.binding()
        self.assertEqual({k:binding[k] for k in core},core)
        self.assertEqual(binding['domain'],execution.DOMAIN)
        self.assertEqual(binding['execution_request_sha256'],packets.digest(self.execution))
        self.observe();self.stop();self.observe('stopped');self.publish();ledger,state=self.finish()
        self.assertTrue(state['terminal']);self.assertIsNone(state['owner']);self.assertEqual(state['events'],[])
        self.assertEqual(ledger['attempts'][0]['status'],'completed');self.assertIsNotNone(ledger['checkpoint'])
        self.assertEqual(self.f.backend.launch_count,1);self.assertEqual(self.f.backend.export_count,1)

    def test_bootstrap_and_reserved_cannot_emit_outcome_or_fake_runtime(self):
        self.acquire()
        for phase in ('reserved','bootstrapped'):
            if phase=='bootstrapped':self.chain()
            revision=self.save('outcome-'+phase,'outcome',self.f.failure('retriable-service'))
            with self.assertRaises(lifecycle.LifecycleError):self.f.host.record('outcome-'+phase,'outcome',expected_revision=revision,now=110)
            with self.assertRaises((lifecycle.LifecycleError,FileNotFoundError)):self.f.backend.inspect(self.binding())
        self.assertEqual(self.f.current()[1]['service_failures'],0)

    def test_lost_launch_reply_replays_no_effect_and_independently_observes(self):
        self.acquire();self.chain();original=self.f.backend.launch
        def lost(*args):original(*args);raise RuntimeError('lost')
        with mock.patch.object(self.f.backend,'launch',side_effect=lost):
            with self.assertRaises(RuntimeError):self.launch()
        self.f.host.launch_reserved('launch',expected_revision=0,now=110);self.observe()
        self.assertEqual(self.f.backend.launch_count,1)

    def test_partial_launch_missing_genesis_cannot_be_backfilled_by_state_or_outcome(self):
        self.acquire();self.chain();original=self.f.backend._save
        def fail(fd,name,raw):
            if name.startswith('runtime-event-'):raise RuntimeError('partial-genesis')
            return original(fd,name,raw)
        with mock.patch.object(self.f.backend,'_save',side_effect=fail):
            with self.assertRaises(RuntimeError):self.launch()
        binding=self.binding()
        with self.assertRaises(lifecycle.LifecycleError):self.f.backend.inspect(binding)
        with self.assertRaises(lifecycle.LifecycleError):self.f.backend.set_state(binding,'stopped')
        revision=self.save('outcome','outcome',self.f.failure('retriable-service'))
        with self.assertRaises(lifecycle.LifecycleError):self.f.host.record('outcome','outcome',expected_revision=revision,now=110)
        self.f.host.launch_reserved('launch',expected_revision=0,now=110)
        self.assertEqual(self.f.current()[0]['attempts'][0]['status'],'unknown')
        self.assertIsNotNone(self.f.current()[1]['owner']);self.assertEqual(self.f.backend.launch_count,0)

    def test_observed_tail_truncation_cannot_revert_unknown_to_stopped(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe('stopped')
        self.stop('unknown');self.observe('unknown')
        paths=sorted(self.f.backend.root.glob('runtime-event-*'));paths[-1].unlink()
        self.assertEqual(json.loads(self.f.backend.inspect(self.binding()))['runtime_state'],'stopped')
        with self.assertRaises(lifecycle.LifecycleError):self.observe('rollback')
        self.assertIsNotNone(self.f.current()[1]['owner'])

    def test_flat_runtime_domain_and_full_chain_digest_mutations_denied(self):
        self.acquire();self.chain();self.launch();binding=self.binding();raw=self.f.backend.inspect(binding)
        for key,value in [('domain',bootstrap.DOMAIN),('schema_version',1),('event_hashes',[]),('launch_artifact_sha256','bad')]:
            proof=json.loads(raw);proof[key]=value
            with self.assertRaises(ValueError):self.f.host._runtime(packets.canonical(proof),binding,110,60)
        for key in ('plan_sha256','descriptor_sha256','input_sha256','receipt_sha256','bootstrap_intent_ref_sha256','launch_ref_sha256'):
            wrong=copy.deepcopy(binding);wrong[key]='a'*64
            with self.assertRaises((lifecycle.LifecycleError,FileNotFoundError)):self.f.backend.inspect(wrong)

    def test_cross_mode_hosts_and_backends_cannot_adopt_r2(self):
        for backend in ({},bootstrap.SavedBootstrapBackend(self.f.backend.root),preparation.SavedPreparationBackend(self.f.backend.root)):
            with self.assertRaises(lifecycle.LifecycleError):self.controller(backend)
        host=bootstrap.SyntheticBootstrapFixtureLifecycle(self.f.store,self.f.reader,
            bootstrap.SavedBootstrapBackend(self.f.backend.root),alias='alias1',host_id='host',backend_id='backend',policy_sha256='d'*64)
        with self.assertRaises(lifecycle.LifecycleError):host.snapshot(now=110)

    def test_all_committed_effects_and_completion_replay_without_callbacks(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe();self.publish();before,_=self.finish()
        patches=[mock.patch.object(self.f.reader,name,side_effect=AssertionError(name)) for name in
            ('locate_objective','readback_evidence','readback_authority','readback_source_state','readback_destination')]
        patches +=[mock.patch.object(self.f.backend,name,side_effect=AssertionError(name)) for name in
            ('prepare','bootstrap','launch','inspect','export_patch','assert_instance')]
        for patch in patches:patch.start();self.addCleanup(patch.stop)
        for op,method in [('launch',self.f.host.launch_reserved),('export',self.f.host.seal),('publish',self.f.host.publish),('finish',self.f.host.finish_attempt)]:
            ledger,_=method(op,expected_revision=0,now=200);self.assertEqual(ledger,before)

    def test_new_operation_cannot_repeat_launch_or_export(self):
        self.acquire();self.chain();self.launch()
        with self.assertRaises(lifecycle.LifecycleError):self.launch('again')
        self.stop();self.observe();self.publish()
        revision=self.save('export-again','export-intent',{})
        with self.assertRaises(lifecycle.LifecycleError):self.f.host.seal('export-again',expected_revision=revision,now=110)
        self.assertEqual(self.f.backend.launch_count,1);self.assertEqual(self.f.backend.export_count,1)

    def test_current_runtime_changes_during_later_source_gate_block_publish(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe()
        revision=self.save('export','export-intent',{});self.f.host.seal('export',expected_revision=revision,now=110)
        binding=self.binding();actual=self.f.backend.inspect(binding)
        manifest=packets.canonical(dict(binding=binding,patch_sha256=packets.digest(b''),runtime_sha256=packets.digest(actual)))
        revision=self.save('publish','publish',dict(patch_sha256=packets.digest(b''),checkpoint_sha256=packets.digest(manifest)),runtime=True)
        original=self.f.reader.readback_source_state
        def change(objective):
            self.f.backend.set_state(binding,'unknown');return original(objective)
        with mock.patch.object(self.f.reader,'readback_source_state',side_effect=change):
            with self.assertRaises(lifecycle.LifecycleError):self.f.host.publish('publish',expected_revision=revision,now=110)
        self.assertIsNone(self.f.current()[0]['checkpoint'])

    def test_publish_and_finish_runtime_frontiers_are_monotonic_in_archive(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe()
        self.stop();self.publish();ledger,_=self.f.current();binding=self.binding()
        expected=json.loads(self.f.backend.inspect(binding))['event_hashes']
        self.assertEqual(ledger['supervisors']['a1']['runtime_frontier']['event_hashes'],expected)
        self.stop();self.finish();ledger,_=self.f.current()
        self.assertEqual(len(ledger['supervisors']['a1']['runtime_frontier']['event_hashes']),len(expected)+1)

    def test_publish_tail_is_required_before_finish_even_if_last_observe_was_older(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe()
        self.stop();self.publish();sorted(self.f.backend.root.glob('runtime-event-*'))[-1].unlink()
        with self.assertRaises(lifecycle.LifecycleError):self.finish()
        self.assertIsNotNone(self.f.current()[1]['owner'])

    def test_finish_tail_is_required_for_retained_writer_before_new_acquire(self):
        self.acquire();self.fail('1',cause='retriable-service');old,self_state=self.f.current()
        self.assertIsNone(self_state['owner'])
        self.f.backend.set_state(self.binding(),'stopped')
        # Finish a second attempt with a newer proof than its last observation.
        self.acquire('next','a2');self.chain('2');self.launch('launch2');self.stop();self.observe('observe2')
        event=self.f.failure('retriable-service');rev=self.save('outcome2','outcome',event)
        self.f.host.record('outcome2','outcome',expected_revision=rev,now=110);self.publish('2')
        self.stop();self.finish('failed','finish2')
        key=packets.digest(packets.canonical(self.binding()))
        sorted(self.f.backend.root.glob('runtime-event-'+key+'-*'))[-1].unlink()
        with self.assertRaises(lifecycle.LifecycleError):self.acquire('third','a3')
        self.assertEqual(self.f.current()[0]['generation'],2)

    def test_quality_failures_safe_finish_and_hsg_upgrade_use_actual_same_r2_journal(self):
        h=self.history();self.acquire('old1','a1');h.executions['a1']=self.execution;self.fail('1')
        self.acquire('old2','a2');h.executions['a2']=self.execution;before,state=self.fail('2',correction=True)
        h.upgrade();ledger,raw,_=h.prepare();self.execution=raw
        after,upgraded=self.f.host.acquire_attempt('new',expected_revision=ledger['revision'],now=110)
        self.assertEqual(upgraded['events'],state['events']);self.assertEqual(upgraded['correction_rounds'],1)
        self.assertEqual(after['attempts'][-1]['predecessor_sha256'],before['checkpoint'])
        proof=json.loads(json.loads(raw)['historical_source_bytes'])
        self.assertEqual(proof['binding']['domain'],'v6-historical-source/1')
        self.chain('3');self.launch('launch3');self.stop();self.observe('observe3')
        final,_=self.f.current();self.assertEqual(final['generation'],3);self.assertEqual(self.f.backend.launch_count,3)
        self.assertEqual([a['status'] for a in final['attempts'][:2]],['failed','failed'])
        self.assertTrue(all(s['binding']['domain']==execution.DOMAIN for s in final['supervisors'].values()))
        with self.assertRaisesRegex(lifecycle.LifecycleError,'owner-or-terminal-conflict'):
            self.acquire('recovered-source-preempt','a4')
        self.assertEqual(self.f.current()[0],final)

    def test_hsg_mixed_original_tiers_preserve_highest_and_reject_lower_source(self):
        h=self.history();self.acquire('old1','a1');h.executions['a1']=self.execution;self.fail('1')
        self.f.request['v2_task']['factors']['ambiguity']='high'
        h.planning['task']['capability_tier']='senior'
        h.planning['targets'][0]['qualification']['capability_tier']='senior'
        self.acquire('old2','a2',planning=h.planning);h.executions['a2']=self.execution
        self.fail('2',correction=True)
        h.upgrade()
        ledger,raw,_=h.prepare('low','a3',mutate=lambda p:p['targets'][0]['qualification'].update(capability_tier='everyday'))
        self.execution=raw
        with self.assertRaises(ValueError):self.f.host.acquire_attempt('low',expected_revision=ledger['revision'],now=110)
        ledger,raw,_=h.prepare('high','a3');self.execution=raw
        self.f.host.acquire_attempt('high',expected_revision=ledger['revision'],now=110)
        refs=[r for r in ledger['governance']['records'] if r['kind']=='acquire']
        tiers=[json.loads((self.f.store.root/'packet'/('lifecycle-'+r['classification_sha256']+'.json')).read_bytes())['capability_tier'] for r in refs]
        self.assertEqual(tiers,['everyday','senior'])
        self.chain('3');self.launch('launch3');self.assertEqual(self.f.backend.launch_count,3)

    def test_isolated_live_fixture_keeps_predecessor_and_quarantines_then_allows_successor(self):
        self.acquire();before,_=self.f.current();ledger,state=self.fail('1',cause='retriable-service',isolated=True)
        self.assertEqual(ledger['attempts'][0]['status'],'quarantined')
        self.assertEqual(ledger['checkpoint'],before['checkpoint']);self.assertIsNone(state['owner'])
        self.acquire('next','a2');self.chain('2');self.launch('launch2')
        self.assertEqual(self.f.current()[1]['service_failures'],1);self.assertEqual(self.f.backend.launch_count,2)

    def test_runtime_event_gap_and_fake_stopped_genesis_fail_closed(self):
        self.acquire();self.chain();self.launch();self.stop();self.stop('unknown')
        paths=sorted(self.f.backend.root.glob('runtime-event-*'));original=paths[0].read_bytes()
        value=json.loads(original);value['runtime_state']='stopped';paths[0].write_bytes(packets.canonical(value))
        with self.assertRaises(lifecycle.LifecycleError):self.f.backend.inspect(self.binding())
        paths[0].write_bytes(original);paths[1].unlink()
        with self.assertRaises(lifecycle.LifecycleError):self.f.backend.inspect(self.binding())

    def test_archive_runtime_frontier_tampering_cannot_change_projected_history(self):
        self.acquire();self.chain();self.launch();self.observe()
        with self.f.store.locked() as fd:
            ledger=self.f.store._read(fd,_lifecycle_token=lifecycle._WRITE_TOKEN)
            ledger['supervisors']['a1']['runtime_frontier']['event_hashes']=[]
            with self.assertRaises(lifecycle.LifecycleError):self.f.host._project(fd,ledger,now=110)

    def test_first_official_schema2_unused_ttl_can_run_full_new_chain(self):
        u=unused.UnusedLifecycleTests();u.f=self.f;u.planning=fixture();u.executions={}
        u.planning['targets'][0]['availability']['status']='unavailable'
        u.planning['targets'][0]['qualification']['observed_at']=0
        ledger,raw,_=u.prepare();self.execution=raw
        self.f.host.acquire_attempt('acquire',expected_revision=ledger['revision'],now=110)
        self.chain();self.launch();self.stop();self.observe();self.publish();_,state=self.finish()
        self.assertTrue(state['terminal']);self.assertEqual(state['stage_floor'],2)
        self.assertEqual(state['events'],[]);self.assertEqual(json.loads(raw)['schema_version'],2)

    def test_launch_precommit_failure_is_retryable_before_any_saved_effect(self):
        self.acquire();self.chain()
        with mock.patch.object(self.f.store,'_write',side_effect=RuntimeError('precommit')):
            with self.assertRaises(RuntimeError):self.launch()
        self.assertEqual(list(self.f.backend.root.glob('launch-*')),[])
        ledger,_=self.f.current()
        self.f.host.launch_reserved('launch',expected_revision=ledger['revision'],now=110)
        self.assertEqual(self.f.backend.launch_count,1)

    def test_launch_postcommit_missing_destination_keeps_intent_without_effect(self):
        self.acquire();self.chain()
        with self.assertRaises(FileNotFoundError):self.launch(post=False)
        self.f.host.launch_reserved('launch',expected_revision=0,now=110)
        self.assertEqual(self.f.current()[0]['supervisors']['a1']['stage'],'launch-intent')
        self.assertEqual(self.f.backend.launch_count,0)

    def test_lost_export_reply_can_publish_without_repeating_export(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe();original=self.f.backend.export_patch
        def lost(*args):original(*args);raise RuntimeError('export-reply')
        with mock.patch.object(self.f.backend,'export_patch',side_effect=lost):
            with self.assertRaises(RuntimeError):self.publish()
        self.f.host.seal('export',expected_revision=0,now=110)
        binding=self.binding();actual=self.f.backend.inspect(binding)
        manifest=packets.canonical(dict(binding=binding,patch_sha256=packets.digest(b''),runtime_sha256=packets.digest(actual)))
        revision=self.save('publish','publish',dict(patch_sha256=packets.digest(b''),checkpoint_sha256=packets.digest(manifest)),runtime=True)
        self.f.host.publish('publish',expected_revision=revision,now=110);self.finish()
        self.assertEqual(self.f.backend.export_count,1)

    def test_reconstructed_host_and_backend_preserve_immutable_chain(self):
        self.acquire();self.chain();self.launch();self.stop();self.observe();before,_=self.f.current()
        backend=execution.SavedExecutionBackend(self.f.backend.root);host=self.controller(backend)
        after,_=host.snapshot(now=110);self.assertEqual(after,before)
        host.launch_reserved('launch',expected_revision=0,now=200)
        self.assertEqual(backend.launch_count,0)

    def test_old_b1_journal_is_not_adopted_by_full_r2_host(self):
        b=b1.BootstrapFixtureTests();b.setUp();self.addCleanup(b.doCleanups)
        backend=execution.SavedExecutionBackend(b.f.backend.root)
        host=execution.SyntheticExecutedLifecycle(b.f.store,b.f.reader,backend,alias='alias1',host_id='host',backend_id='backend',policy_sha256='d'*64)
        with self.assertRaises(lifecycle.LifecycleError):host.snapshot(now=110)

    def test_running_unknown_or_external_effects_cannot_export_or_release(self):
        self.acquire();self.chain();self.launch();binding=self.binding()
        for state,effects in [('running','excluded'),('unknown','excluded'),('stopped','unknown')]:
            self.f.backend.set_state(binding,state,effects);self.observe('observe-'+state+effects)
            op='export-'+state+effects;revision=self.save(op,'export-intent',{})
            with self.assertRaises(lifecycle.LifecycleError):self.f.host.seal(op,expected_revision=revision,now=110)
        self.assertEqual(self.f.backend.export_count,0);self.assertIsNotNone(self.f.current()[1]['owner'])

    def test_mid_launch_root_replacement_keeps_unknown_and_rejects_result(self):
        self.acquire();self.chain();b=self.f.backend;original=b._save
        def replace(fd,name,raw):
            original(fd,name,raw)
            if name.startswith('launch-'):
                b.root.rename(b.root.with_name('old-execution-root'));b.root.mkdir(mode=0o700)
        with mock.patch.object(b,'_save',side_effect=replace):
            with self.assertRaises(lifecycle.LifecycleError):self.launch()
        self.assertEqual(self.f.current()[0]['attempts'][0]['status'],'unknown')
        self.assertEqual(b.launch_count,0)

    def test_mid_launch_packet_lock_replacement_cannot_report_success(self):
        self.acquire();self.chain();original=self.f.backend.launch
        def replace(*args):
            original(*args)
            p=self.f.store.root/'packet/lock';p.rename(p.with_name('old-lock'));p.write_bytes(b'');p.chmod(0o600)
        with mock.patch.object(self.f.backend,'launch',side_effect=replace):
            with self.assertRaises(packets.PacketError):self.launch()
        self.assertEqual(self.f.backend.launch_count,1)

    def test_postcommit_authority_revocation_blocks_launch_effect(self):
        self.acquire();self.chain();f=self.f;original=f.host._read
        def revoke(fd,now):
            result=original(fd,now)
            if result[0]['governance']['records'][-1]['kind']=='launch-intent':f.reader.authorization='revoked'
            return result
        with mock.patch.object(f.host,'_read',side_effect=revoke):
            with self.assertRaises(lifecycle.LifecycleError):self.launch()
        self.assertEqual(f.backend.launch_count,0);self.assertIsNotNone(f.current()[1]['owner'])

    def test_final_context_insufficiency_blocks_launch_even_after_bootstrap(self):
        self.acquire();self.chain();revision=self.save('launch','launch-intent',{},
            mutate=lambda p:p['targets'][0]['context'].update(window=1))
        with self.assertRaises(ValueError):self.f.host.launch_reserved('launch',expected_revision=revision,now=110)
        self.assertEqual(self.f.backend.launch_count,0)
