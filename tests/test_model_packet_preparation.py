"""R1 saved preparation uses real private files, but starts no writer."""
import copy
import json
import pathlib
import unittest
from unittest import mock

from tests import test_model_packet_lifecycle as baseline
from tests import test_model_packet_unused_source as unused
from tests.test_model_failover import fixture
from tests.test_model_packet_unused_source import ProofReader
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets


class PreparedLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.f = baseline.LifecycleTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        f = self.f
        for name in ('preparation-reader', 'preparation-backend'):
            (f.root/name).mkdir(mode=0o700)
        f.store = packets.PacketStore(f.root/'packets', 'prepared-packet'); f.store.prepare('a'*64)
        f.request = copy.deepcopy(f.request)
        f.backend = preparation.SavedPreparationBackend(f.root/'preparation-backend')
        f.reader = ProofReader(f.root/'preparation-reader', f.store, f.backend, f.request)
        f.host = self.controller()
        f.reader.save('admit', 'admit-prepared', f.host.admission_payload())
        with f.store.locked() as fd: ledger = f.store._read(fd)
        f.reader.seal('admit', lifecycle._binding(f.store, ledger, 'admit'))
        f.host.admit_new('admit', expected_revision=0, now=110)
        self.execution = None

    def controller(self, backend=None):
        f=self.f
        return preparation.SyntheticPreparedLifecycle(f.store, f.reader, backend if backend is not None else f.backend,
            alias='alias1', host_id='host', backend_id='backend', policy_sha256='d'*64)

    def destination(self, ledger, action, mutate=None):
        f=self.f; execution=json.loads(self.execution)
        binding=dict(lifecycle._binding(f.store,ledger,'current'),action=action,
            execution_sha256=packets.digest(self.execution),target_id=execution['target_id'],
            target_identity_sha256=packets.digest(packets.canonical(execution['target_identity'])))
        payload=copy.deepcopy(execution['failover_payload'])
        if mutate:mutate(payload)
        raw=packets.canonical(dict(schema_version=1,binding=binding,observed_at=110,expires_at=170,payload=payload))
        path=f.reader.root/('destination-'+packets.digest(packets.canonical(binding)));path.write_bytes(raw)
        return path

    def acquire(self, mutate=None):
        f=self.f;ledger,state=f.current();f.request.update(generation=1,attempt_id='a1')
        p=fixture();p['events']=state['events']
        if mutate:mutate(p)
        f.reader.save('acquire','acquire',dict(owner_id='owner',epoch=1),request=f.request,planning=p)
        directory=f.reader.root/'acquire';binding=lifecycle._binding(f.store,ledger,'acquire')
        self.execution=packets.canonical(dict(schema_version=1,binding=binding,
            governance_request_sha256=packets.digest((directory/'request').read_bytes()),
            attempt_id='a1',generation=1,predecessor_sha256=None,target_id='internal',
            target_identity=f.request['target_identity'],failover_payload=p,host_id='host',
            backend_id='backend',runtime_policy_sha256='d'*64,runtime_id='runtime-a1'))
        (directory/'execution').write_bytes(self.execution);f.reader.seal('acquire',binding)
        self.destination(ledger,'acquire')
        return f.host.acquire_attempt('acquire',expected_revision=ledger['revision'],now=110)

    def plan(self, op='prepare'):
        ledger,_=self.f.current()
        return self.f.host.plan_preparation(op,expected_revision=ledger['revision'],now=110)

    def save(self, op, kind, payload, *, post=True, mutate=None):
        f=self.f;ledger,_=f.current();revision=f.save(op,kind,payload)
        self.destination(ledger,kind,mutate)
        if post:
            future=copy.deepcopy(ledger);binding=lifecycle._binding(f.store,ledger,op)
            evidence=f.reader.readback_evidence(binding)
            ref=dict(operation_id=op,kind=kind,binding=binding,committed_at=110)
            ref.update({field+'_sha256':None if getattr(evidence,field) is None else packets.digest(getattr(evidence,field)) for field in lifecycle.FIELDS})
            future['governance']['records'].append(ref);future['revision']+=1
            self.destination(future,kind,mutate)
        return revision

    def prepare(self, op='prepare', *, post=True):
        self.plan_raw=self.plan(op)
        revision=self.save(op,'prepare-intent',dict(plan_bytes=self.plan_raw.decode()),post=post)
        return self.f.host.prepare_reserved(op,expected_revision=revision,now=110)

    def confirmation_payload(self):
        f=self.f;observed=f.backend.observe_preparation(self.plan_raw,now=110,freshness=60)
        descriptor,observation=f.backend.readback_preparation(self.plan_raw,packets.digest(observed))
        return dict(descriptor_bytes=descriptor.decode(),observation_bytes=observation.decode())

    def confirm(self, op='prepared'):
        payload=self.confirmation_payload();revision=self.save(op,'prepared',payload)
        return self.f.host.confirm_prepared(op,expected_revision=revision,now=110)

    def test_real_saved_descriptor_and_mode_leave_owner_unknown_and_no_writer(self):
        _,before=self.acquire();before=copy.deepcopy(before)
        self.prepare();ledger,state=self.confirm()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepared')
        self.assertEqual(ledger['attempts'][0]['status'],'unknown')
        self.assertEqual(state['owner'],before['owner'])
        for key in ('generation','events','stage_floor','quality_stage_floor','required_tier_floors',
                'quality_tier_floors','service_failures','correction_rounds'):
            self.assertEqual(state[key],before[key],key)
        self.assertIsNone(ledger['checkpoint']);self.assertEqual(self.f.backend.prepare_count,1)
        self.assertEqual(len(list(self.f.backend.root.glob('descriptor-*'))),1)
        first=ledger['governance']['records'][0]
        raw=(self.f.store.root/self.f.store.packet_id/('lifecycle-'+first['record_sha256']+'.json')).read_bytes()
        self.assertEqual(json.loads(raw)['kind'],'admit-prepared')
        self.assertEqual(json.loads(raw)['payload'],self.f.host.admission_payload())

    def test_original_six_fields_and_execution_schema_are_preserved(self):
        ledger,_=self.acquire();ref=ledger['governance']['records'][-1]
        self.assertEqual(ref['execution_sha256'],packets.digest(self.execution))
        self.assertIsNone(ref['runtime_sha256']);self.prepare();ledger,_=self.confirm()
        self.assertEqual(ledger['governance']['records'][1],ref)
        self.assertEqual(json.loads(self.execution)['schema_version'],1)
        self.assertIsNone(ledger['governance']['records'][-1]['execution_sha256'])
        self.assertIsNone(ledger['governance']['records'][-1]['runtime_sha256'])

    def test_first_official_schema2_keeps_only_the_legitimate_unused_ttl_exception(self):
        u=unused.UnusedLifecycleTests();u.f=self.f;u.planning=fixture();u.executions={}
        u.planning['targets'][0]['availability']['status']='unavailable'
        u.planning['targets'][0]['qualification']['observed_at']=0
        ledger,raw,_=u.prepare();self.execution=raw
        self.f.host.acquire_attempt('acquire',expected_revision=ledger['revision'],now=110)
        self.prepare();ledger,state=self.confirm()
        self.assertEqual(state['stage_floor'],2);self.assertEqual(json.loads(raw)['schema_version'],2)
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepared')
        self.assertEqual(self.f.backend.prepare_count,1);self.assertEqual(state['events'],[])

    def test_schema3_cannot_invent_actual_history_in_a_new_prepared_packet(self):
        u=unused.UnusedLifecycleTests();u.f=self.f;u.planning=fixture();u.executions={}
        u.planning['targets'][0]['availability']['status']='unavailable'
        ledger,raw,_=u.prepare();value=json.loads(raw)
        value.update(schema_version=3,historical_source_bytes='{}');del value['unused_source_bytes']
        directory=self.f.reader.root/'acquire';(directory/'execution').write_bytes(packets.canonical(value))
        self.f.reader.seal('acquire',lifecycle._binding(self.f.store,ledger,'acquire'))
        with self.assertRaises(ValueError):self.f.host.acquire_attempt('acquire',expected_revision=ledger['revision'],now=110)
        self.assertEqual(self.f.current()[0]['generation'],0);self.assertEqual(self.f.backend.prepare_count,0)

    def test_observation_refresh_uses_a_new_immutable_receipt_without_create(self):
        self.acquire();self.prepare();backend=self.f.backend
        first=backend.observe_preparation(self.plan_raw,now=110,freshness=60)
        later=backend.observe_preparation(self.plan_raw,now=111,freshness=60)
        self.assertNotEqual(first,later)
        d1,o1=backend.readback_preparation(self.plan_raw,packets.digest(first))
        d2,o2=backend.readback_preparation(self.plan_raw,packets.digest(later))
        self.assertEqual(d1,d2);self.assertEqual(o1,first);self.assertEqual(o2,later)
        self.assertEqual(backend.observe_preparation(self.plan_raw,now=111,freshness=60),later)
        self.assertEqual(backend.prepare_count,1)

    def test_backend_artifact_privacy_symlink_and_hardlink_are_rejected(self):
        self.acquire();self.prepare();backend=self.f.backend
        observed=backend.observe_preparation(self.plan_raw,now=110,freshness=60)
        plan=json.loads(self.plan_raw);path=backend.root/('descriptor-'+plan['control_id']+'.json')
        raw=path.read_bytes();path.chmod(0o644)
        with self.assertRaises(ValueError):backend.readback_preparation(self.plan_raw,packets.digest(observed))
        path.chmod(0o600);linked=backend.root/'link'
        import os
        os.link(path,linked)
        with self.assertRaises(ValueError):backend.readback_preparation(self.plan_raw,packets.digest(observed))
        linked.unlink();saved=backend.root/'saved';path.rename(saved);path.symlink_to(saved)
        with self.assertRaises(ValueError):backend.readback_preparation(self.plan_raw,packets.digest(observed))

    def test_live_root_replacement_cannot_reuse_original_identity_or_descriptor(self):
        self.acquire();self.prepare();payload=self.confirmation_payload();f=self.f
        revision=self.save('confirm','prepared',payload)
        import shutil
        old=f.backend.root.with_name('original-backend');f.backend.root.rename(old)
        shutil.copytree(old,f.backend.root)
        # Raw identity, nonce and descriptor are identical, but the actual root
        # is a different instance even for an already constructed controller.
        with self.assertRaisesRegex(lifecycle.LifecycleError,'instance-drift'):
            f.host.confirm_prepared('confirm',expected_revision=revision,now=110)
        with self.assertRaisesRegex(lifecycle.LifecycleError,'instance-drift'):
            preparation.SavedPreparationBackend(f.backend.root)
        self.assertEqual(f.current()[0]['supervisors']['a1']['stage'],'prepare-intent')

    def test_partial_resource_does_not_release_owner_or_repeat_create(self):
        self.acquire();backend=self.f.backend;original=backend._save
        def partial(fd,name,raw):
            if name.startswith('descriptor-'):
                original(fd,name,b'{');raise OSError('partial-create')
            return original(fd,name,raw)
        with mock.patch.object(backend,'_save',side_effect=partial):
            with self.assertRaises(OSError):self.prepare()
        self.f.host.prepare_reserved('prepare',expected_revision=0,now=110)
        ledger,state=self.f.current()
        self.assertEqual(ledger['attempts'][0]['status'],'unknown');self.assertIsNotNone(state['owner'])
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepare-intent')
        with self.assertRaises(ValueError):self.confirmation_payload()

    def test_post_intent_authority_revocation_keeps_intent_and_zero_creates(self):
        self.acquire();f=self.f;raw=self.plan();ledger,_=f.current()
        revision=self.save('prepare','prepare-intent',dict(plan_bytes=raw.decode()))
        original=f.reader.readback_authority
        def revoked(binding):
            value=json.loads(original(binding))
            if binding['revision']==ledger['revision']+1:value['authorization_status']='revoked'
            return packets.canonical(value)
        with mock.patch.object(f.reader,'readback_authority',side_effect=revoked):
            with self.assertRaises(lifecycle.LifecycleError):f.host.prepare_reserved('prepare',expected_revision=revision,now=110)
        ledger,state=f.current()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepare-intent')
        self.assertEqual(f.backend.prepare_count,0);self.assertIsNotNone(state['owner'])

    def test_dirty_source_blocks_resource_creation_and_descriptor_confirmation(self):
        self.acquire();f=self.f;raw=self.plan();revision=self.save('dirty','prepare-intent',dict(plan_bytes=raw.decode()))
        f.reader.dirty=True
        with self.assertRaises(lifecycle.LifecycleError):f.host.prepare_reserved('dirty',expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,0)
        f.reader.dirty=False;self.prepare();payload=self.confirmation_payload()
        revision=self.save('confirm','prepared',payload);f.reader.dirty=True
        with self.assertRaises(lifecycle.LifecycleError):f.host.confirm_prepared('confirm',expected_revision=revision,now=110)
        self.assertEqual(f.current()[0]['supervisors']['a1']['stage'],'prepare-intent')

    def test_completed_operation_replay_uses_only_actual_archives_and_no_callbacks(self):
        self.acquire();self.prepare();self.confirm()
        f=self.f
        with mock.patch.object(f.reader,'locate_objective',side_effect=AssertionError('today')), \
                mock.patch.object(f.reader,'readback_evidence',side_effect=AssertionError('today')), \
                mock.patch.object(f.reader,'readback_authority',side_effect=AssertionError('today')), \
                mock.patch.object(f.reader,'readback_destination',side_effect=AssertionError('today')), \
                mock.patch.object(f.backend,'assert_instance',side_effect=AssertionError('today')), \
                mock.patch.object(f.backend,'readback_preparation',side_effect=AssertionError('today')), \
                mock.patch.object(f.backend,'prepare',side_effect=AssertionError('repeat')):
            for op,method in [('admit',f.host.admit_new),('acquire',f.host.acquire_attempt),
                    ('prepare',f.host.prepare_reserved),('prepared',f.host.confirm_prepared)]:
                ledger,state=method(op,expected_revision=0,now=200)
                self.assertEqual(ledger['revision'],4);self.assertIsNotNone(state['owner'])

    def test_mode_is_closed_for_flat_host_and_mixed_journal(self):
        f=self.f
        flat=lifecycle.SyntheticLifecycle(f.store,f.reader,baseline.SavedBackend(f.root/'backend'),
            alias='alias1',host_id='host',backend_id='backend',policy_sha256='d'*64)
        with self.assertRaisesRegex(lifecycle.LifecycleError,'mode-conflict'):flat.snapshot(now=110)
        ledger,_=f.current();ledger['governance']['records'][0]['kind']='admit'
        with self.assertRaises(lifecycle.LifecycleError):
            with f.store.locked() as fd:f.host._project(fd,ledger,now=110)
        ledger,_=f.current()
        for kind in ('outcome','observe','launch-intent','bootstrap-intent','finish'):
            altered=copy.deepcopy(ledger);altered['governance']['records'][0]['kind']=kind
            with self.assertRaises(lifecycle.LifecycleError):lifecycle.validate_ledger(altered,f.store.packet_id)

    def test_flat_journal_and_backend_json_subclasses_or_other_instance_are_denied(self):
        f=self.f
        with self.assertRaises(lifecycle.LifecycleError):self.controller(backend={})
        class Other(preparation.SavedPreparationBackend):pass
        with self.assertRaises(lifecycle.LifecycleError):self.controller(backend=Other(f.backend.root))
        other_root=f.root/'other-backend';other_root.mkdir(mode=0o700)
        other=preparation.SavedPreparationBackend(other_root)
        with self.assertRaises(lifecycle.LifecycleError):self.controller(other).snapshot(now=110)
        flat_store=packets.PacketStore(f.root/'packets','packet')
        flat=preparation.SyntheticPreparedLifecycle(flat_store,f.reader,f.backend,alias='alias1',
            host_id='host',backend_id='backend',policy_sha256='d'*64)
        with self.assertRaisesRegex(lifecycle.LifecycleError,'mode-conflict'):flat.snapshot(now=110)
        rebuilt=preparation.SavedPreparationBackend(f.backend.root)
        self.assertEqual(rebuilt.instance_sha256,f.backend.instance_sha256)
        self.controller(rebuilt).snapshot(now=110)

    def test_no_future_phase_outcome_or_finish_can_release_owner(self):
        self.acquire();self.prepare();self.confirm();f=self.f
        for kind in ('launch-intent','bootstrap-intent','outcome','health','quality-floor','observe','export-intent','publish','finish','admit'):
            with self.assertRaises(lifecycle.LifecycleError):f.host._append('forbidden',kind,expected_revision=4,now=110)
        ledger,state=f.current()
        self.assertEqual(ledger['revision'],4);self.assertIsNotNone(state['owner'])
        with self.assertRaises(lifecycle.LifecycleError):f.backend.inspect(ledger['supervisors']['a1']['binding'])

    def test_new_operation_cannot_repeat_prepare_or_confirmation(self):
        self.acquire();self.prepare();f=self.f
        revision=self.save('prepare-again','prepare-intent',dict(plan_bytes=self.plan_raw.decode()))
        with self.assertRaises(lifecycle.LifecycleError):f.host.prepare_reserved('prepare-again',expected_revision=revision,now=110)
        self.confirm()
        payload=json.loads((f.reader.root/'prepared'/'record').read_bytes())['payload']
        revision=self.save('confirm-again','prepared',payload)
        with self.assertRaises(lifecycle.LifecycleError):f.host.confirm_prepared('confirm-again',expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,1)
        with self.assertRaises(lifecycle.LifecycleError):f.host.prepare_reserved('prepared',expected_revision=0,now=110)

    def test_pre_intent_write_failure_creates_no_resource(self):
        self.acquire();f=self.f;plan=self.plan()
        revision=self.save('prepare','prepare-intent',dict(plan_bytes=plan.decode()))
        with mock.patch.object(f.store,'_write',side_effect=OSError('durability')):
            with self.assertRaises(OSError):f.host.prepare_reserved('prepare',expected_revision=revision,now=110)
        ledger,state=f.current();self.assertEqual(ledger['supervisors']['a1']['stage'],'reserved')
        self.assertEqual(f.backend.prepare_count,0);self.assertIsNotNone(state['owner'])
        f.host.prepare_reserved('prepare',expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,1)

    def test_post_commit_read_failure_and_missing_live_proof_do_not_replay_prepare(self):
        self.acquire();f=self.f;plan=self.plan()
        revision=self.save('prepare','prepare-intent',dict(plan_bytes=plan.decode()))
        original=f.host._read;calls=0
        def read(fd,now):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('post-commit-read')
            return original(fd,now)
        with mock.patch.object(f.host,'_read',side_effect=read):
            with self.assertRaises(RuntimeError):f.host.prepare_reserved('prepare',expected_revision=revision,now=110)
        ledger,state=f.current();self.assertEqual(ledger['supervisors']['a1']['stage'],'prepare-intent')
        self.assertEqual(f.backend.prepare_count,0);self.assertIsNotNone(state['owner'])
        f.host.prepare_reserved('prepare',expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,0)

    def test_missing_post_intent_destination_retains_intent_without_create(self):
        self.acquire()
        with self.assertRaises(FileNotFoundError):self.prepare(post=False)
        ledger,state=self.f.current()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepare-intent')
        self.assertEqual(self.f.backend.prepare_count,0);self.assertIsNotNone(state['owner'])
        self.f.host.prepare_reserved('prepare',expected_revision=0,now=110)
        self.assertEqual(self.f.backend.prepare_count,0)

    def test_lost_create_reply_independent_confirmation_without_second_create(self):
        self.acquire();f=self.f;original=f.backend.prepare
        def lost(raw):original(raw);raise RuntimeError('reply-lost')
        with mock.patch.object(f.backend,'prepare',side_effect=lost):
            with self.assertRaises(RuntimeError):self.prepare()
        f.host.prepare_reserved('prepare',expected_revision=0,now=110)
        self.assertEqual(f.backend.prepare_count,1)
        ledger,state=self.confirm();self.assertEqual(ledger['supervisors']['a1']['stage'],'prepared')
        self.assertIsNotNone(state['owner'])

    def test_skipped_confirmation_or_absent_resource_keeps_owner_unknown(self):
        self.acquire();f=self.f
        revision=self.save('prepared','prepared',dict(descriptor_bytes='{}',observation_bytes='{}'))
        with self.assertRaises(lifecycle.LifecycleError):f.host.confirm_prepared('prepared',expected_revision=revision,now=110)
        with mock.patch.object(f.backend,'prepare',side_effect=RuntimeError('before-create')):
            with self.assertRaises(RuntimeError):self.prepare()
        with self.assertRaises(FileNotFoundError):self.confirmation_payload()
        ledger,state=f.current()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'prepare-intent')
        self.assertEqual(ledger['attempts'][0]['status'],'unknown');self.assertIsNotNone(state['owner'])

    def test_plan_exact_bytes_types_bounds_and_identity_are_required(self):
        self.acquire();f=self.f
        for i,change in enumerate((lambda p:p.update(nonce='z'*32),lambda p:p.update(control_id='other'),
                lambda p:p['mode'].update(recipe_sha256='0'*64),lambda p:p['mode'].update(backend_instance_sha256='0'*64),
                lambda p:p['binding'].update(prefix_sha256='0'*64),lambda p:p['runtime_binding'].update(execution_request_sha256='0'*64),
                lambda p:p.update(source_sha256='0'*64),lambda p:p.update(acceptance_sha256='0'*64),
                lambda p:p.update(predecessor_sha256='0'*64),lambda p:p.update(schema_version=True),
                lambda p:p.update(extra='unexpected'))):
            op='bad'+str(i);raw=self.plan(op);p=json.loads(raw);change(p)
            revision=self.save(op,'prepare-intent',dict(plan_bytes=packets.canonical(p).decode()))
            with self.assertRaises(ValueError):f.host.prepare_reserved(op,expected_revision=revision,now=110)
        for i,payload in enumerate((dict(plan_bytes={}),dict(plan_bytes='x'*16385),
                dict(plan_bytes=self.plan('noncanonical').decode()+' '),dict(plan_bytes='{}',extra=True))):
            op='bounds'+str(i);revision=self.save(op,'prepare-intent',payload)
            with self.assertRaises(ValueError):f.host.prepare_reserved(op,expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,0);self.assertEqual(f.current()[0]['revision'],2)

    def test_descriptor_observation_and_independent_readback_are_required(self):
        self.acquire();self.prepare();f=self.f;payload=self.confirmation_payload()
        changes=(lambda d,o:d.update(nonce='0'*32),lambda d,o:d.update(instance_id='different'),
            lambda d,o:d['runtime_binding'].update(runtime_id='different'),lambda d,o:d.update(resource_state='stopped'),
            lambda d,o:o.update(descriptor_sha256='0'*64),lambda d,o:o.update(instance_id='different'),
            lambda d,o:o.update(observed_at=111),lambda d,o:o.update(observed_at=0,expires_at=170),
            lambda d,o:o.update(expires_at=110),lambda d,o:o.update(schema_version=True))
        for i,change in enumerate(changes):
            d=json.loads(payload['descriptor_bytes']);o=json.loads(payload['observation_bytes']);change(d,o)
            op='confirmbad'+str(i);revision=self.save(op,'prepared',dict(descriptor_bytes=packets.canonical(d).decode(),observation_bytes=packets.canonical(o).decode()))
            with self.assertRaises(ValueError):f.host.confirm_prepared(op,expected_revision=revision,now=110)
        revision=self.save('good','prepared',payload)
        with mock.patch.object(f.backend,'readback_preparation',return_value=(b'{}',b'{}')):
            with self.assertRaises(lifecycle.LifecycleError):f.host.confirm_prepared('good',expected_revision=revision,now=110)
        self.assertEqual(f.current()[0]['revision'],3)
        f.host.confirm_prepared('good',expected_revision=revision,now=110)

    def test_live_schema1_source_destination_authority_and_context_gate(self):
        self.acquire();f=self.f
        changes=(lambda p:p['targets'][0]['qualification'].update(observed_at=0),
            lambda p:p['targets'][0]['qualification'].update(status='revoked'),
            lambda p:p['targets'][0]['context'].update(client_limit=1299),
            lambda p:p['targets'][0]['context'].update(input_tokens=999),
            lambda p:p['authorization'].update(status='revoked'),
            lambda p:p['secret_check'].update(status='present'))
        for i,change in enumerate(changes):
            op='gate'+str(i);raw=self.plan(op);revision=self.save(op,'prepare-intent',dict(plan_bytes=raw.decode()),mutate=change)
            with self.assertRaises(lifecycle.LifecycleError):f.host.prepare_reserved(op,expected_revision=revision,now=110)
        self.assertEqual(f.backend.prepare_count,0);self.assertEqual(f.current()[0]['revision'],2)

    def test_live_instance_or_full_packet_fence_drift_blocks_confirmation(self):
        self.acquire();self.prepare();f=self.f;payload=self.confirmation_payload()
        revision=self.save('confirm','prepared',payload);original=f.backend.readback_preparation
        def drift(raw,sha):
            result=original(raw,sha);path=f.store.root/f.store.packet_id/'lock'
            path.rename(path.with_name('old-lock'));path.write_bytes(b'');path.chmod(0o600)
            return result
        with mock.patch.object(f.backend,'readback_preparation',side_effect=drift):
            with self.assertRaises(packets.PacketError):f.host.confirm_prepared('confirm',expected_revision=revision,now=110)
        self.assertEqual(f.current()[0]['revision'],3)
        identity=f.backend.root/'backend-identity.json'
        original=identity.read_bytes();v=json.loads(original);v['nonce']='0'*32;identity.write_bytes(packets.canonical(v))
        with self.assertRaises(lifecycle.LifecycleError):f.host.confirm_prepared('confirm',expected_revision=revision,now=110)

    def test_archived_descriptor_corruption_is_not_backfilled_by_backend(self):
        self.acquire();self.prepare();ledger,_=self.confirm();ref=ledger['governance']['records'][-1]
        path=self.f.store.root/self.f.store.packet_id/('lifecycle-'+ref['record_sha256']+'.json')
        original=path.read_bytes();path.write_bytes(original+b' ')
        with mock.patch.object(self.f.backend,'readback_preparation',side_effect=AssertionError('today')):
            with self.assertRaises(ValueError):self.f.host.confirm_prepared('prepared',expected_revision=0,now=110)
