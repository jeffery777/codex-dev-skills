"""B1 real private saved artifacts; no container, writer or provider claim."""
import copy
import json
import unittest
from unittest import mock

from tests import test_model_packet_preparation as prepared
from tests import test_model_packet_lifecycle as baseline
from tests.test_model_packet_unused_source import ProofReader
import model_packet_bootstrap as bootstrap
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets


class BootstrapFixtureTests(unittest.TestCase):
    acquire = prepared.PreparedLifecycleTests.acquire
    destination = prepared.PreparedLifecycleTests.destination
    plan = prepared.PreparedLifecycleTests.plan
    save = prepared.PreparedLifecycleTests.save
    prepare = prepared.PreparedLifecycleTests.prepare
    confirmation_payload = prepared.PreparedLifecycleTests.confirmation_payload
    confirm = prepared.PreparedLifecycleTests.confirm

    def setUp(self):
        self.f = baseline.LifecycleTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        f = self.f
        for name in ('bootstrap-reader', 'bootstrap-backend'):
            (f.root/name).mkdir(mode=0o700)
        f.store = packets.PacketStore(f.root/'packets', 'bootstrap-packet'); f.store.prepare('a'*64)
        f.backend = bootstrap.SavedBootstrapBackend(f.root/'bootstrap-backend')
        f.reader = ProofReader(f.root/'bootstrap-reader', f.store, f.backend, f.request)
        f.host = self.controller(); self.execution = None
        f.reader.save('admit', 'admit-bootstrap-fixture', f.host.admission_payload())
        with f.store.locked() as fd: ledger = f.store._read(fd)
        f.reader.seal('admit', lifecycle._binding(f.store, ledger, 'admit'))
        f.host.admit_new('admit', expected_revision=0, now=110)

    def controller(self, backend=None):
        f = self.f
        return bootstrap.SyntheticBootstrapFixtureLifecycle(f.store, f.reader,
            f.backend if backend is None else backend, alias='alias1', host_id='host',
            backend_id='backend', policy_sha256='d'*64)

    def ready(self):
        self.acquire(); self.prepare(); self.confirm()
        self.input_raw = self.f.host.input_bootstrap(now=110)

    def intent(self, op='bootstrap', *, post=True, input_raw=None):
        raw = self.input_raw if input_raw is None else input_raw
        revision = self.save(op, 'bootstrap-intent', dict(input_bytes=raw.decode()), post=post)
        return self.f.host.bootstrap_prepared(op, expected_revision=revision, now=110)

    def bootstrap_payload(self):
        b = self.f.backend
        proof = b.observe_bootstrap(self.input_raw, now=110, freshness=60)
        _, _, receipt, observation = b.readback_bootstrap(self.input_raw, packets.digest(proof))
        return dict(receipt_bytes=receipt.decode(), observation_bytes=observation.decode())

    def bootstrapped(self, op='bootstrapped', mutate=None):
        payload = self.bootstrap_payload()
        if mutate: mutate(payload)
        revision = self.save(op, 'bootstrapped', payload)
        return self.f.host.confirm_bootstrapped(op, expected_revision=revision, now=110)

    def test_full_saved_chain_preserves_unknown_owner_original_six_and_governance(self):
        self.ready(); before, state = self.f.current(); state = copy.deepcopy(state)
        descriptor = before['supervisors']['a1']['preparation']['descriptor_bytes']
        self.intent(); ledger, after = self.bootstrapped()
        self.assertEqual(ledger['supervisors']['a1']['stage'], 'bootstrapped')
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
        self.assertEqual(after, state); self.assertEqual(ledger['checkpoint'], before['checkpoint'])
        self.assertEqual(ledger['supervisors']['a1']['preparation']['descriptor_bytes'], descriptor)
        self.assertEqual(ledger['governance']['records'][:4], before['governance']['records'])
        self.assertEqual(self.f.backend.bootstrap_count, 1); self.assertEqual(self.f.backend.prepare_count, 1)
        self.assertIsNone(ledger['governance']['records'][-1]['execution_sha256'])
        self.assertIsNone(ledger['governance']['records'][-1]['runtime_sha256'])
        with self.assertRaises(lifecycle.LifecycleError): self.f.backend.inspect({})

    def test_raw_intent_receipt_and_input_are_bound_without_descriptor_cycles(self):
        self.ready(); self.intent(); ledger, _ = self.bootstrapped()
        saved = ledger['supervisors']['a1']['bootstrap']; ref = ledger['governance']['records'][-2]
        self.assertEqual(saved['intent_ref_bytes'].encode(), packets.canonical(ref))
        receipt = json.loads(saved['receipt_bytes']); value = json.loads(saved['input_bytes'])
        self.assertEqual(receipt['intent_ref_sha256'], packets.digest(packets.canonical(ref)))
        self.assertEqual(receipt['input_sha256'], packets.digest(self.input_raw))
        self.assertEqual(value['plan_bytes'], self.plan_raw.decode())
        self.assertNotIn('input_sha256', json.loads(value['descriptor_bytes']))
        self.assertNotIn('receipt_sha256', json.loads(value['descriptor_bytes']))
        self.assertLessEqual(len(self.input_raw), preparation.MAX_ARTIFACT)

    def test_old_operation_replay_has_zero_today_callbacks_even_after_expiry(self):
        self.ready(); self.intent(); before, _ = self.bootstrapped()
        patches = [mock.patch.object(self.f.reader, name, side_effect=AssertionError(name))
            for name in ('locate_objective','readback_authority','readback_evidence','readback_source_state','readback_destination')]
        patches += [mock.patch.object(self.f.backend, name, side_effect=AssertionError(name))
            for name in ('assert_instance','bootstrap','readback_bootstrap')]
        for patch in patches: patch.start(); self.addCleanup(patch.stop)
        for op, method in [('bootstrap',self.f.host.bootstrap_prepared), ('bootstrapped',self.f.host.confirm_bootstrapped)]:
            ledger, _ = method(op, expected_revision=0, now=200)
            self.assertEqual(ledger, before)

    def test_lost_bootstrap_reply_is_not_reexecuted_and_can_independently_confirm(self):
        self.ready(); original = self.f.backend.bootstrap
        def lost(*args): original(*args); raise RuntimeError('lost-reply')
        with mock.patch.object(self.f.backend, 'bootstrap', side_effect=lost):
            with self.assertRaises(RuntimeError): self.intent()
        self.f.host.bootstrap_prepared('bootstrap',expected_revision=0,now=110)
        self.bootstrapped(); self.assertEqual(self.f.backend.bootstrap_count,1)

    def test_precommit_failure_creates_nothing_and_original_operation_can_retry(self):
        self.ready()
        with mock.patch.object(self.f.store,'_write',side_effect=RuntimeError('write-fail')):
            with self.assertRaises(RuntimeError): self.intent()
        self.assertEqual(self.f.backend.bootstrap_count,0)
        self.assertEqual(list(self.f.backend.root.glob('bootstrap-input-*')),[])
        ledger,_ = self.f.current()
        self.f.host.bootstrap_prepared('bootstrap',expected_revision=ledger['revision'],now=110)
        self.assertEqual(self.f.backend.bootstrap_count,1)

    def test_postcommit_gate_failure_keeps_durable_intent_and_no_replay_effect(self):
        self.ready()
        with self.assertRaises(FileNotFoundError): self.intent(post=False)
        ledger,state = self.f.current()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'bootstrap-intent')
        self.assertIsNotNone(state['owner']); self.assertEqual(self.f.backend.bootstrap_count,0)
        self.f.host.bootstrap_prepared('bootstrap',expected_revision=0,now=110)
        self.assertEqual(self.f.backend.bootstrap_count,0)
        with self.assertRaises(FileNotFoundError): self.bootstrap_payload()

    def test_partial_effect_keeps_unknown_and_absent_receipt_cannot_confirm(self):
        self.ready(); original=self.f.backend._save
        def partial(fd,name,raw):
            if name.startswith('bootstrap-intent-'): raise RuntimeError('partial-write')
            return original(fd,name,raw)
        with mock.patch.object(self.f.backend,'_save',side_effect=partial):
            with self.assertRaises(RuntimeError): self.intent()
        self.assertEqual(len(list(self.f.backend.root.glob('bootstrap-input-*'))),1)
        with self.assertRaises(FileNotFoundError): self.bootstrap_payload()
        self.f.host.bootstrap_prepared('bootstrap',expected_revision=0,now=110)
        ledger,state=self.f.current(); self.assertEqual(ledger['attempts'][0]['status'],'unknown')
        self.assertIsNotNone(state['owner']); self.assertEqual(self.f.backend.bootstrap_count,0)

    def test_new_id_cannot_repeat_either_phase_and_old_id_cannot_change_kind(self):
        self.ready(); self.intent()
        with self.assertRaises(lifecycle.LifecycleError): self.intent('repeat')
        self.bootstrapped()
        with self.assertRaises(lifecycle.LifecycleError): self.bootstrapped('again')
        with self.assertRaises(lifecycle.LifecycleError): self.f.host.confirm_bootstrapped('bootstrap',expected_revision=0,now=110)
        self.assertEqual(self.f.backend.bootstrap_count,1)

    def test_future_launch_governance_and_completion_methods_are_denied(self):
        self.ready(); self.intent(); ledger,_=self.bootstrapped()
        for method in (self.f.host.launch_reserved,self.f.host.reconcile,self.f.host.seal,self.f.host.publish,self.f.host.finish_attempt):
            with self.assertRaises(lifecycle.LifecycleError): method('future',expected_revision=ledger['revision'],now=110)
        for kind in ('outcome','resolve','quality-floor','health','cooldown'):
            with self.assertRaises(lifecycle.LifecycleError): self.f.host.record('future',kind,expected_revision=ledger['revision'],now=110)
        self.assertIsNotNone(self.f.current()[1]['owner'])

    def test_raw_input_mutations_and_noncanonical_bytes_are_denied_before_effect(self):
        self.ready()
        for key in ('plan_bytes','descriptor_bytes'):
            value=json.loads(self.input_raw); inner=json.loads(value[key]); inner['schema_version']=True
            value[key]=packets.canonical(inner).decode()
            with self.assertRaises(ValueError): self.intent('bad-'+key,input_raw=packets.canonical(value))
        with self.assertRaises(ValueError): self.intent('noncanonical',input_raw=self.input_raw+b'\n')
        with self.assertRaises(ValueError): self.intent('oversize',input_raw=b' '*(preparation.MAX_ARTIFACT+1))
        self.assertEqual(self.f.backend.bootstrap_count,0)

    def test_receipt_observation_digest_domain_state_and_freshness_mutations_rejected(self):
        self.ready(); self.intent(); original=self.bootstrap_payload()
        changes=[('receipt_bytes','input_sha256','a'*64),('receipt_bytes','intent_ref_sha256','a'*64),
            ('receipt_bytes','domain','other'),('receipt_bytes','state','running'),
            ('observation_bytes','receipt_sha256','a'*64),('observation_bytes','input_sha256','a'*64),
            ('observation_bytes','intent_ref_sha256','a'*64),('observation_bytes','domain','other'),
            ('observation_bytes','state','stopped'),('observation_bytes','observed_at',111),
            ('observation_bytes','expires_at',110),('observation_bytes','schema_version',True)]
        for index,(field,key,value) in enumerate(changes):
            payload=copy.deepcopy(original); parsed=json.loads(payload[field]); parsed[key]=value
            payload[field]=packets.canonical(parsed).decode(); op='invalid'+str(index)
            revision=self.save(op,'bootstrapped',payload)
            with self.assertRaises(ValueError): self.f.host.confirm_bootstrapped(op,expected_revision=revision,now=110)
        self.assertEqual(self.f.current()[0]['supervisors']['a1']['stage'],'bootstrap-intent')

    def test_confirmation_requires_actual_independent_saved_readback(self):
        self.ready(); self.intent()
        with mock.patch.object(self.f.backend,'readback_bootstrap',return_value=(b'{}',)*4):
            with self.assertRaises(lifecycle.LifecycleError): self.bootstrapped()
        self.assertEqual(self.f.current()[0]['supervisors']['a1']['stage'],'bootstrap-intent')

    def test_backend_reconstruction_same_inode_preserves_original_artifacts(self):
        self.ready(); self.intent(); self.bootstrapped(); before,_=self.f.current()
        backend=bootstrap.SavedBootstrapBackend(self.f.backend.root)
        host=self.controller(backend); after,_=host.snapshot(now=110)
        self.assertEqual(before,after); self.assertEqual(backend.instance_sha256,self.f.backend.instance_sha256)
        host.bootstrap_prepared('bootstrap',expected_revision=0,now=200)
        self.assertEqual(backend.bootstrap_count,0)

    def test_cross_mode_and_backend_type_rejected(self):
        for backend in ({},preparation.SavedPreparationBackend(self.f.backend.root)):
            with self.assertRaises(lifecycle.LifecycleError): self.controller(backend)
        class Subclass(bootstrap.SavedBootstrapBackend): pass
        with self.assertRaises(lifecycle.LifecycleError): self.controller(Subclass(self.f.backend.root))
        for cls,backend in [(lifecycle.SyntheticLifecycle,baseline.SavedBackend(self.f.backend.root)),
                (preparation.SyntheticPreparedLifecycle,preparation.SavedPreparationBackend(self.f.backend.root))]:
            host=cls(self.f.store,self.f.reader,backend,alias='alias1',host_id='host',backend_id='backend',policy_sha256='d'*64)
            with self.assertRaises(lifecycle.LifecycleError): host.snapshot(now=110)

    def test_bootstrap_before_prepared_is_denied_and_cannot_count_model_failure(self):
        self.acquire()
        with self.assertRaises(lifecycle.LifecycleError): self.f.host.input_bootstrap(now=110)
        ledger,state=self.f.current()
        with self.assertRaises(lifecycle.LifecycleError): self.f.host.record('outcome','outcome',expected_revision=ledger['revision'],now=110)
        self.assertEqual(state['service_failures'],0); self.assertEqual(state['correction_rounds'],0)

    def test_fresh_observation_is_immutable_and_does_not_repeat_bootstrap(self):
        self.ready(); self.intent(); b=self.f.backend
        first=b.observe_bootstrap(self.input_raw,now=110,freshness=60)
        second=b.observe_bootstrap(self.input_raw,now=111,freshness=60)
        self.assertNotEqual(first,second)
        self.assertEqual(second,b.observe_bootstrap(self.input_raw,now=111,freshness=60))
        self.assertEqual(b.bootstrap_count,1); self.assertEqual(len(list(b.root.glob('bootstrap-observation-*'))),2)

    def test_dirty_source_context_and_current_authority_deny_new_intent(self):
        self.ready(); f=self.f; ledger,_=f.current()
        for op,condition in [('dirty','dirty'),('revoked','authorization')]:
            revision=self.save(op,'bootstrap-intent',dict(input_bytes=self.input_raw.decode()))
            original=getattr(f.reader,condition); setattr(f.reader,condition,True if condition=='dirty' else 'revoked')
            try:
                with self.assertRaises(lifecycle.LifecycleError): f.host.bootstrap_prepared(op,expected_revision=revision,now=110)
            finally: setattr(f.reader,condition,original)
        revision=self.save('context','bootstrap-intent',dict(input_bytes=self.input_raw.decode()),
            mutate=lambda p:p['targets'][0]['context'].update(window=1))
        with self.assertRaises(ValueError): f.host.bootstrap_prepared('context',expected_revision=revision,now=110)
        self.assertEqual(f.backend.bootstrap_count,0)

    def test_reserved_direct_intent_returns_typed_error_before_preparation_lookup(self):
        self.acquire(); revision=self.save('early','bootstrap-intent',dict(input_bytes='{}'))
        with self.assertRaises(lifecycle.LifecycleError):
            self.f.host.bootstrap_prepared('early',expected_revision=revision,now=110)
        self.assertEqual(self.f.backend.bootstrap_count,0)

    def test_failure_at_each_file_write_does_not_release_owner_or_retry(self):
        for prefix in ('bootstrap-input-', 'bootstrap-intent-', 'bootstrap-receipt-'):
            case=BootstrapFixtureTests(); case.setUp()
            try:
                case.ready(); original=case.f.backend._save
                def fail(fd,name,raw):
                    if name.startswith(prefix): raise RuntimeError('bounded-file-failure')
                    return original(fd,name,raw)
                with mock.patch.object(case.f.backend,'_save',side_effect=fail):
                    with self.assertRaises(RuntimeError): case.intent()
                case.f.host.bootstrap_prepared('bootstrap',expected_revision=0,now=110)
                ledger,state=case.f.current()
                self.assertEqual(ledger['attempts'][0]['status'],'unknown'); self.assertIsNotNone(state['owner'])
                with self.assertRaises(FileNotFoundError): case.bootstrap_payload()
                self.assertEqual(case.f.backend.bootstrap_count,0)
            finally: case.doCleanups()

    def test_mid_effect_root_replacement_is_rejected_and_old_artifact_never_adopted(self):
        self.ready(); b=self.f.backend; original=b._save
        def replace(fd,name,raw):
            original(fd,name,raw)
            if name.startswith('bootstrap-input-'):
                b.root.rename(b.root.with_name('old-bootstrap-root')); b.root.mkdir(mode=0o700)
        with mock.patch.object(b,'_save',side_effect=replace):
            with self.assertRaises(lifecycle.LifecycleError): self.intent()
        ledger,state=self.f.current()
        self.assertEqual(ledger['supervisors']['a1']['stage'],'bootstrap-intent')
        self.assertIsNotNone(state['owner']); self.assertEqual(b.bootstrap_count,0)
        with self.assertRaises(lifecycle.LifecycleError): self.bootstrap_payload()

    def test_mid_effect_backend_identity_change_is_rejected(self):
        self.ready(); b=self.f.backend; original=b._save
        def change(fd,name,raw):
            original(fd,name,raw)
            if name.startswith('bootstrap-input-'):
                (b.root/'backend-identity.json').write_bytes(b'{}')
        with mock.patch.object(b,'_save',side_effect=change):
            with self.assertRaises(lifecycle.LifecycleError): self.intent()
        self.assertEqual(self.f.current()[0]['attempts'][0]['status'],'unknown')
        self.assertEqual(b.bootstrap_count,0)

    def test_descriptor_drift_after_prepared_blocks_bootstrap_effect(self):
        self.ready(); b=self.f.backend; plan=json.loads(self.plan_raw)
        path=b.root/('descriptor-'+plan['control_id']+'.json'); path.write_bytes(b'{}')
        with self.assertRaises(lifecycle.LifecycleError): self.intent()
        self.assertEqual(self.f.current()[0]['supervisors']['a1']['stage'],'bootstrap-intent')
        self.assertEqual(b.bootstrap_count,0)

    def test_private_file_symlink_hardlink_and_permission_checks_at_confirmation(self):
        for drift in ('symlink','hardlink','permission'):
            case=BootstrapFixtureTests(); case.setUp()
            try:
                case.ready(); case.intent(); payload=case.bootstrap_payload(); plan=json.loads(case.plan_raw)
                p=case.f.backend.root/('bootstrap-receipt-'+plan['control_id']+'.json')
                if drift=='permission': p.chmod(0o644)
                else:
                    backup=p.with_name('receipt-backup'); p.rename(backup)
                    if drift=='symlink': p.symlink_to(backup)
                    else:
                        import os
                        os.link(backup,p)
                revision=case.save('invalid','bootstrapped',payload)
                with self.assertRaises((lifecycle.LifecycleError,ValueError)):
                    case.f.host.confirm_bootstrapped('invalid',expected_revision=revision,now=110)
                self.assertEqual(case.f.current()[0]['supervisors']['a1']['stage'],'bootstrap-intent')
            finally: case.doCleanups()

    def test_packet_lock_replacement_after_saved_effect_cannot_report_success(self):
        self.ready(); original=self.f.backend.bootstrap
        def replace(*args):
            original(*args)
            path=self.f.store.root/self.f.store.packet_id/'lock'
            path.rename(path.with_name('old-lock')); path.write_bytes(b''); path.chmod(0o600)
        with mock.patch.object(self.f.backend,'bootstrap',side_effect=replace):
            with self.assertRaises(packets.PacketError): self.intent()
        self.assertEqual(self.f.backend.bootstrap_count,1)

    def test_postcommit_revocation_blocks_effect_but_preserves_intent(self):
        self.ready(); f=self.f; original=f.host._read
        def revoke(fd,now):
            result=original(fd,now)
            if result[0]['governance']['records'][-1]['kind']=='bootstrap-intent':
                f.reader.authorization='revoked'
            return result
        with mock.patch.object(f.host,'_read',side_effect=revoke):
            with self.assertRaises(lifecycle.LifecycleError): self.intent()
        self.assertEqual(f.backend.bootstrap_count,0)
        self.assertEqual(f.current()[0]['supervisors']['a1']['stage'],'bootstrap-intent')

    def test_input_and_intent_saved_bytes_drift_block_independent_readback(self):
        for kind in ('bootstrap-input-','bootstrap-intent-'):
            case=BootstrapFixtureTests(); case.setUp()
            try:
                case.ready(); case.intent(); payload=case.bootstrap_payload(); plan=json.loads(case.plan_raw)
                p=case.f.backend.root/(kind+plan['control_id']+'.json'); p.write_bytes(b'{}')
                revision=case.save('invalid','bootstrapped',payload)
                with self.assertRaises(lifecycle.LifecycleError):
                    case.f.host.confirm_bootstrapped('invalid',expected_revision=revision,now=110)
                self.assertIsNotNone(case.f.current()[1]['owner'])
            finally: case.doCleanups()

    def test_preparation_identity_cannot_be_relabelled_to_b1_protocol(self):
        self.ready(); value=json.loads(self.input_raw)
        plan=json.loads(value['plan_bytes']); plan['mode']['protocol_sha256']=preparation.PROTOCOL_SHA
        value['plan_bytes']=packets.canonical(plan).decode()
        with self.assertRaises(ValueError): self.intent('wrong-mode',input_raw=packets.canonical(value))
        self.assertEqual(self.f.backend.bootstrap_count,0)
