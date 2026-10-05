"""Real durable ledger/Git fixture; reconstructable offline Docker double."""
import ast
import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'skills/loop-engineering/scripts'))
import model_packet_integrator as integration
import model_packet_store as packets
import model_packet_supervisor as supervisors
import model_container_backend as containers
from tests.test_model_container_backend import FakeOneShotDocker, IMAGE


class FixtureDocker(FakeOneShotDocker):
    """Correct fixed add-update double, preserving the out-of-scope baseline."""
    def command(self,*argv):
        try:
            return super().command(*argv)
        finally:
            if argv[:2]==('container','start'):
                value=self.inspect(argv[2])
                line=next(line for line in value['Config']['Cmd'][-1].splitlines() if line.startswith('WORKER='))
                if ast.literal_eval(line.removeprefix('WORKER='))==containers.WORKERS['add-update']:
                    (pathlib.Path(value['Mounts'][0]['Source'])/'remove.txt').write_bytes(containers.BASELINE['remove.txt'])


class UpdateOnlyDocker(FixtureDocker):
    """Offline update-only postimage; live native provenance is verified separately."""
    def command(self,*argv):
        result=super().command(*argv)
        if argv[:2]==('container','start'):
            workspace=pathlib.Path(self.inspect(argv[2])['Mounts'][0]['Source'])
            (workspace/'added.txt').unlink(missing_ok=True)
            (workspace/'remove.txt').write_bytes(containers.BASELINE['remove.txt'])
        return result


class IntegratorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name).resolve(); self.root.chmod(0o700)
        self.source=integration.SyntheticSource.create(self.root)
        self.store=packets.PacketStore(self.root,'packet'); self.store.prepare('d'*64)
        self.engine=FixtureDocker(self.root)

    def fixture(self,recipe='add-update',store=None,engine=None,source=None):
        store=store or self.store; source=source or self.source
        backend=containers.OneShotSyntheticContainerBackend(store,endpoint='unix:///synthetic/docker.sock',image_id=IMAGE,
            opt_in=True,_engine=engine or self.engine,worker=recipe)
        supervisor=supervisors.PacketSupervisor(store,backend,host_id=backend.host_id,backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)
        governance=integration.FixtureGovernance(source)
        return integration.PacketIntegrator(source,governance,supervisor)

    def ready(self,recipe='add-update'):
        integrator=self.fixture(recipe)
        candidate=integrator.supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**self.source.requirements(recipe))
        self.assertEqual(candidate['outcome'],'integration-candidate')
        self.assertEqual(candidate['patch'],integration.FIXED_PATCH if recipe=='add-update' else b'')
        authority=integrator.governance.issue(integrator.supervisor,'attempt',recipe=recipe)
        return integrator,authority

    def image(self):
        return {p.name:p.read_bytes() for p in self.source.source.iterdir() if p.is_file()}

    def snapshot(self):
        return self.store.integration_snapshot('operation')

    def assert_no_intent(self):
        self.assertNotIn('integrations',self.store.supervisor_snapshot('attempt')[0])
        self.assertEqual(self.image(),containers.BASELINE)

    def test_add_update_preserves_head_index_outscope_and_readonly_reconstruction(self):
        integrator,authority=self.ready()
        result=integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(result['state'],'applied')
        self.assertEqual(self.image(),{**containers.BASELINE,'example.txt':b'new\n','added.txt':b'added\n'})
        ledger,record,intent=self.snapshot()
        self.assertEqual(ledger['schema_version'],4)
        self.assertEqual(intent['head'],self.source.descriptor['head'])
        self.assertEqual(intent['index_sha256'],self.source.descriptor['index_sha256'])
        self.assertEqual([v['phase'] for v in record['observations']],['integration-intent','write-intent','applied'])
        source=integration.SyntheticSource.reopen(self.source.root,self.source.descriptor_sha256)
        fresh=self.fixture(store=packets.PacketStore(self.root,'packet'),engine=FixtureDocker(self.root),source=source)
        authority=fresh.governance.reopen_authority(authority.authority_id,authority.sha)
        with mock.patch.object(fresh,'_write_file',side_effect=AssertionError('replay')),mock.patch.object(fresh,'_stage',side_effect=AssertionError('apply')):
            self.assertEqual(fresh.reconcile('operation',authority),result)
            self.assertEqual(fresh.integrate('attempt',authority,operation_id='operation'),result)
        self.assertFalse(any(v[:2] in [('container','start'),('container','create'),('volume','create')] for v in fresh.supervisor.backend.engine.calls))

    def test_noop_keeps_full_authority_gates_and_records_no_effect(self):
        integrator,authority=self.ready('noop')
        result=integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual((result['state'],result['effects'],result['reason']),('not-applied','none','authorized-noop'))
        self.assertEqual(self.image(),containers.BASELINE)
        self.assertFalse(self.snapshot()[1]['writer_started'])
        self.assertEqual(integrator.reconcile('operation',authority),result)
        ledger=self.snapshot()[0]
        with self.assertRaisesRegex(packets.PacketError,'source-integration-next-claim-unqualified'):
            self.store.claim('next','e'*64,'f'*64,expected_revision=ledger['revision'])

    def native_update(self):
        integrator=self.fixture('edit',engine=UpdateOnlyDocker(self.root))
        candidate=integrator.supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,
            **self.source.requirements('native-update'))
        self.assertEqual(candidate['patch'],integration.NATIVE_UPDATE_PATCH)
        authority=integrator.governance.issue(integrator.supervisor,'attempt',recipe='native-update')
        return integrator,authority

    def test_fixed_native_recipe_updates_only_example_and_reconcile_cannot_replay(self):
        integrator,authority=self.native_update()
        previous=os.umask(0o077)
        try: result=integrator.integrate('attempt',authority,operation_id='operation')
        finally: os.umask(previous)
        self.assertEqual(result['state'],'applied')
        self.assertEqual(self.image(),{**containers.BASELINE,'example.txt':b'new\n'})
        self.assertEqual(self.snapshot()[2]['scope_paths'],['example.txt'])
        intent=self.snapshot()[2]
        for scope in (['remove.txt'],['example.txt','added.txt'],['example.txt','remove.txt'],[],('example.txt',)):
            altered=copy.deepcopy(intent); altered['scope_paths']=scope
            with self.subTest(scope=scope),self.assertRaises(packets.PacketError): self.store._validate_integration_intent(altered)
        altered=copy.deepcopy(intent); altered['postimage']['added.txt']={'bytes':6,'sha256':packets.digest(b'added\n')}
        altered['postimage_sha256']=packets.digest(packets.canonical(altered['postimage']))
        with self.assertRaises(packets.PacketError): self.store._validate_integration_intent(altered)
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('replay')):
            self.assertEqual(integrator.reconcile('operation',authority),result)
            self.assertEqual(integrator.integrate('attempt',authority,operation_id='operation'),result)

    def test_native_recipe_revocation_source_drift_and_acceptance_mismatch_create_no_intent(self):
        for case in ('revoked','source-drift','wrong-recipe'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve(); root.chmod(0o700)
                source=integration.SyntheticSource.create(root); store=packets.PacketStore(root,'packet'); store.prepare('d'*64)
                integrator=self.fixture('edit',store=store,source=source,engine=UpdateOnlyDocker(root))
                candidate=integrator.supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**source.requirements('native-update'))
                authority=integrator.governance.issue(integrator.supervisor,'attempt',recipe='native-update')
                if case=='revoked': integrator.governance.revoke(authority)
                elif case=='source-drift': (source.source/'example.txt').write_bytes(b'drift\n')
                else:
                    with self.assertRaises(packets.PacketError): integrator.governance._expected(candidate,'add-update')
                    continue
                before={p.name:p.read_bytes() for p in source.source.iterdir() if p.is_file()}
                with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
                self.assertNotIn('integrations',store.supervisor_snapshot('attempt')[0])
                self.assertEqual({p.name:p.read_bytes() for p in source.source.iterdir() if p.is_file()},before)

    def test_forged_and_revoked_authority_never_create_intent(self):
        integrator,authority=self.ready()
        for forged in [{'approved':True},object(),integration.FixtureGovernance]:
            with self.subTest(forged=type(forged)),self.assertRaises(packets.PacketError):
                integrator.integrate('attempt',forged,operation_id='operation')
        integrator.governance.revoke(authority)
        with self.assertRaisesRegex(packets.PacketError,'revoked'):
            integrator.integrate('attempt',authority,operation_id='operation')
        self.assert_no_intent()

    def test_wrong_binding_and_gate_artifact_tamper_rejected(self):
        integrator,authority=self.ready()
        path=self.source.root/'control'/(authority.authority_id+'.json'); original=path.read_bytes()
        value=json.loads(original); value['scope_paths']=['remove.txt']; path.write_bytes(packets.canonical(value))
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
        path.write_bytes(original)
        value=json.loads(original); gate=self.source.root/'control'/('review-'+value['review_sha256']+'.json')
        gate.write_bytes(gate.read_bytes().replace(b'fixed-scope-matched',b'caller-approved'))
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
        self.assert_no_intent()

    def test_wrong_acceptance_or_fixed_content_cannot_issue_authority(self):
        integrator=self.fixture('noop')
        integrator.supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**self.source.requirements('noop'))
        with self.assertRaises(packets.PacketError): integrator.governance.issue(integrator.supervisor,'attempt',recipe='add-update')
        candidate=integrator.supervisor.admit_candidate('attempt',**self.source.requirements('noop'))
        candidate['patch']=b'caller'; candidate['patch_sha256']=packets.digest(b'caller')
        with self.assertRaises(packets.PacketError): integrator.governance._expected(candidate,'noop')

    def test_source_dirty_head_index_unknown_scope_and_file_types_rejected(self):
        integrator,authority=self.ready()
        example=self.source.source/'example.txt'; original=example.read_bytes()
        for kind in ['dirty','executable','symlink','hardlink','fifo','unknown','git-index','git-head']:
            with self.subTest(kind=kind):
                extra=None; metadata=None
                if kind=='dirty': example.write_bytes(b'dirty\n')
                elif kind=='executable': example.chmod(0o755)
                elif kind=='symlink': example.unlink(); example.symlink_to(self.source.source/'remove.txt')
                elif kind=='hardlink': example.unlink(); os.link(self.source.source/'remove.txt',example)
                elif kind=='fifo': example.unlink(); os.mkfifo(example)
                elif kind=='unknown': extra=self.source.source/'other.txt'; extra.write_bytes(b'outside\n')
                else:
                    metadata=self.source.source/'.git'/('index' if kind=='git-index' else 'HEAD')
                    saved=metadata.read_bytes(); metadata.write_bytes(saved+b'drift')
                with self.assertRaises((packets.PacketError,OSError)): integrator.integrate('attempt',authority,operation_id='operation')
                self.assertNotIn('integrations',self.store.supervisor_snapshot('attempt')[0])
                if metadata: metadata.write_bytes(saved)
                if extra: extra.unlink()
                if kind in {'symlink','hardlink','fifo'}: example.unlink()
                example.write_bytes(original); example.chmod(0o644)

    def test_stage_rejects_deletion_binary_links_submodules_and_extra_targets(self):
        integrator,authority=self.ready()
        patches=[b'diff --git a/remove.txt b/remove.txt\ndeleted file mode 100644\n--- a/remove.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-delete\n',
            integration.FIXED_PATCH+b'--- /dev/null\n+++ b/other.txt\n@@ -0,0 +1 @@\n+outside\n',
            b'diff --git a/added.txt b/added.txt\nnew file mode 120000\n--- /dev/null\n+++ b/added.txt\n@@ -0,0 +1 @@\n+example.txt\n',
            b'diff --git a/added.txt b/added.txt\nnew file mode 160000\n--- /dev/null\n+++ b/added.txt\n@@ -0,0 +1 @@\n+Subproject commit '+b'a'*40+b'\n',
            b'diff --git a/added.txt b/added.txt\nGIT binary patch\nliteral 1\nA\n']
        for patch in patches:
            with self.subTest(patch=patch[:50]),self.assertRaises(packets.PacketError): integrator._stage(containers.BASELINE,patch)
        self.assert_no_intent()

    def test_crash_after_intent_before_write_reconciles_not_applied_without_apply(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_start_integration_write',side_effect=SystemExit('crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(self.snapshot()[1]['state'],'integration-intent')
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('replay')):
            self.assertEqual(integrator.reconcile('operation',authority)['state'],'not-applied')
        self.assertEqual(self.image(),containers.BASELINE)

    def test_crash_after_write_intent_preimage_is_unknown_never_replayed(self):
        integrator,authority=self.ready()
        with mock.patch.object(integrator,'_write_file',side_effect=SystemExit('crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('replay')):
            self.assertEqual(integrator.reconcile('operation',authority)['state'],'unknown')
            self.assertEqual(integrator.integrate('attempt',authority,operation_id='operation')['state'],'unknown')
        self.assertEqual(self.image(),containers.BASELINE)

    def test_mid_apply_unknown_preserved_and_readonly_replay(self):
        integrator,authority=self.ready(); original=integrator._write_file
        def partial(fd,name,raw,expected):
            if name=='example.txt': raise OSError('synthetic midwrite failure')
            original(fd,name,raw,expected)
        with mock.patch.object(integrator,'_write_file',side_effect=partial):
            self.assertEqual(integrator.integrate('attempt',authority,operation_id='operation')['state'],'unknown')
        self.assertEqual(self.image(),{**containers.BASELINE,'added.txt':b'added\n'})
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('retry')):
            self.assertEqual(integrator.reconcile('operation',authority)['state'],'unknown')
        self.assertIn('unknown',[v['phase'] for v in self.snapshot()[1]['observations']])

    def test_crash_after_all_writes_before_checkpoint_recovers_applied(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_finish_integration',side_effect=SystemExit('lost commit')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('retry')):
            self.assertEqual(integrator.reconcile('operation',authority)['state'],'applied')
        self.assertEqual(self.snapshot()[1]['state'],'applied')

    def test_lost_reply_replay_reads_original_result_and_never_writes(self):
        integrator,authority=self.ready(); finish=self.store._finish_integration
        def lost(*args):
            finish(*args); raise SystemExit('caller lost reply')
        with mock.patch.object(self.store,'_finish_integration',side_effect=lost):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('retry')):
            self.assertEqual(integrator.reconcile('operation',authority)['state'],'applied')

    def test_intent_and_result_artifact_tamper_missing_fail_closed(self):
        integrator,authority=self.ready(); integrator.integrate('attempt',authority,operation_id='operation')
        record=self.snapshot()[1]
        for prefix,key in [('integration-intent-','intent_sha256'),('integration-result-','result_sha256')]:
            path=self.root/'packet'/(prefix+record[key]+'.json'); original=path.read_bytes()
            path.write_bytes(original+b' ')
            with self.assertRaises(packets.PacketError): integrator.reconcile('operation',authority)
            path.write_bytes(original); retained=path.with_suffix('.retained'); path.rename(retained)
            with self.assertRaises((packets.PacketError,OSError)): integrator.reconcile('operation',authority)
            retained.rename(path)

    def test_generation_quarantine_and_runtime_restart_fence(self):
        integrator,authority=self.ready()
        with self.store.locked() as fd:
            ledger=self.store._read(fd); ledger['generation']+=1; self.store._write(fd,ledger)
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(self.image(),containers.BASELINE)

    def test_cross_packet_source_lock_and_packet_lock_prevent_overlap(self):
        integrator,authority=self.ready()
        with self.source._locked():
            with self.assertRaisesRegex(packets.PacketError,'source-writer-busy'):
                integrator.integrate('attempt',authority,operation_id='operation')
        other=packets.PacketStore(self.root,'other'); other.prepare('9'*64)
        second=self.fixture(store=other)
        second.supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**self.source.requirements('add-update'))
        authority2=second.governance.issue(second.supervisor,'attempt',recipe='add-update')
        original=integrator._write_file
        def exclusive(*args):
            with self.assertRaisesRegex(packets.PacketError,'source-writer-busy'):
                second.integrate('attempt',authority2,operation_id='other-operation')
            with self.assertRaises(packets.PacketError): self.store.claim('next','e'*64,'f'*64,expected_revision=0)
            original(*args)
        with mock.patch.object(integrator,'_write_file',side_effect=exclusive):
            self.assertEqual(integrator.integrate('attempt',authority,operation_id='operation')['state'],'applied')
        with self.assertRaises(packets.PacketError): second.integrate('attempt',authority2,operation_id='other-operation')

    def test_unknown_then_postimage_resolution_preserves_original_receipt(self):
        integrator,authority=self.ready(); snapshot=self.source.snapshot
        def lost(fd):
            files=snapshot(fd)
            if files=={**containers.BASELINE,'example.txt':b'new\n','added.txt':b'added\n'}:
                raise OSError('lost final readback')
            return files
        with mock.patch.object(self.source,'snapshot',side_effect=lost):
            self.assertEqual(integrator.integrate('attempt',authority,operation_id='operation')['state'],'unknown')
        old=copy.deepcopy(self.snapshot()[1]['observations']); receipt=self.root/'packet'/('integration-result-'+old[-1]['evidence_sha256']+'.json')
        original=receipt.read_bytes()
        self.assertEqual(integrator.reconcile('operation',authority)['state'],'applied')
        self.assertEqual(self.snapshot()[1]['observations'][:-1],old)
        self.assertEqual(receipt.read_bytes(),original)
        receipt.write_bytes(original+b' ')
        with self.assertRaises(packets.PacketError): integrator.reconcile('operation',authority)

    def test_store_strict_schema_image_result_and_history_bounds(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_start_integration_write',side_effect=SystemExit('intent crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        ledger,record,intent=self.snapshot()
        for key,value in [('no_effect',True),('scope_paths',['remove.txt']),('unexpected',True),('preimage_sha256','f'*64)]:
            bad=copy.deepcopy(intent); bad[key]=value
            with self.subTest(key=key),self.assertRaises(packets.PacketError): self.store._validate_integration_intent(bad)
        with self.store.locked() as fd:
            bad=integrator._result(intent,'not-applied','durable-intent-no-write',containers.BASELINE); bad['approved']=True
            with self.assertRaises(packets.PacketError): self.store._finish_integration(fd,ledger,'operation','not-applied',bad)
            bad=copy.deepcopy(ledger); bad['integrations']['operation']['writer_started']=True
            with self.assertRaises(packets.PacketError): self.store._validate_integrations(bad)
            bad=copy.deepcopy(ledger); bad['integrations']['operation']['observations']*=17
            with self.assertRaises(packets.PacketError): self.store._validate_integrations(bad)
        self.assertEqual(self.image(),containers.BASELINE)

    def test_physical_source_replacement_never_writes_new_directory(self):
        integrator,authority=self.ready()
        retained=self.source.root/'retained-source'; self.source.source.rename(retained)
        self.source.source.mkdir(mode=0o700)
        with self.assertRaisesRegex(packets.PacketError,'physical-identity-drift'):
            integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(list(self.source.source.iterdir()),[])
        self.assertNotIn('integrations',self.store.supervisor_snapshot('attempt')[0])

    def test_actual_checkpoint_corruption_rejected_before_intent(self):
        integrator,authority=self.ready()
        ledger=self.store.supervisor_snapshot('attempt')[0]
        checkpoint=self.root/'packet'/(ledger['checkpoint']+'.patch')
        checkpoint.write_bytes(checkpoint.read_bytes()+b'corruption')
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(self.image(),containers.BASELINE)

    def test_reconcile_revocation_after_intent_never_applies(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_start_integration_write',side_effect=SystemExit('intent crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        integrator.governance.revoke(authority)
        with self.assertRaisesRegex(packets.PacketError,'revoked'): integrator.reconcile('operation',authority)
        self.assertEqual(self.image(),containers.BASELINE)
        self.assertEqual(self.snapshot()[1]['state'],'integration-intent')

    def test_manual_duplicate_runtime_start_prevents_integration(self):
        integrator,authority=self.ready()
        descriptor=self.store.read_runtime_descriptor('attempt')
        self.engine.command('container','start',descriptor['container_id'])
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='operation')
        self.assertEqual(self.image(),containers.BASELINE)
        self.assertNotIn('integrations',self.store.supervisor_snapshot('attempt')[0])

    def test_public_snapshot_rejects_rehashed_intent_binding_checkpoint_and_patch_drift(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_start_integration_write',side_effect=SystemExit('intent crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        original,record,intent=self.snapshot()
        bool_binding={**intent['binding'],'generation':True}
        float_binding={**intent['binding'],'generation':float(intent['binding']['generation'])}
        for key,value in [('binding',{'approved':True}),('binding',bool_binding),('binding',float_binding),
                ('checkpoint_sha256','0'*64),('patch_sha256','0'*64)]:
            with self.subTest(key=key,value=value):
                altered=copy.deepcopy(intent); altered[key]=value
                raw=packets.canonical(altered); sha=packets.digest(raw)
                with self.store.locked() as fd:
                    ledger=copy.deepcopy(original)
                    ledger['integrations']['operation']['intent_sha256']=sha
                    ledger['integrations']['operation']['observations'][0]['evidence_sha256']=sha
                    self.store._immutable(fd,'integration-intent-'+sha+'.json',raw)
                    self.store._write(fd,ledger)
                # A reconstructed public reader must reject despite matching
                # artifact/reference/history digests and valid outer schema.
                fresh=packets.PacketStore(self.root,'packet')
                with self.assertRaisesRegex(packets.PacketError,'source-integration-intent-binding-drift'):
                    fresh.integration_snapshot('operation')
                self.assertEqual(self.image(),containers.BASELINE)
        with self.store.locked() as fd: self.store._write(fd,original)
        self.assertEqual(self.snapshot()[2],intent)

    def test_integrate_rejects_current_host_backend_and_policy_drift_before_inspection(self):
        integrator,authority=self.ready()
        for key,drift in [('host_id','different-host'),('backend_id','different-backend'),('policy_sha256','0'*64)]:
            with self.subTest(key=key),mock.patch.object(integrator.supervisor,key,drift):
                with self.assertRaisesRegex(packets.PacketError,'supervisor-host-policy-drift'):
                    integrator.supervisor.admit_candidate('attempt',**self.source.requirements('add-update'))
                with mock.patch.object(integrator.supervisor,'_inspect',side_effect=AssertionError('drift reached backend')):
                    with self.assertRaisesRegex(packets.PacketError,'supervisor-host-policy-drift'):
                        integrator.integrate('attempt',authority,operation_id='operation')
                self.assert_no_intent()

    def test_reconcile_rejects_reconstructed_host_backend_and_policy_drift_without_writes(self):
        integrator,authority=self.ready()
        with mock.patch.object(self.store,'_start_integration_write',side_effect=SystemExit('intent crash')):
            with self.assertRaises(SystemExit): integrator.integrate('attempt',authority,operation_id='operation')
        original=(self.root/'packet'/'ledger.json').read_bytes()
        for key,drift in [('host_id','different-host'),('backend_id','different-backend'),('policy_sha256','0'*64)]:
            with self.subTest(key=key):
                fresh=self.fixture(store=packets.PacketStore(self.root,'packet'),engine=FixtureDocker(self.root))
                identities={'host_id':fresh.supervisor.host_id,'backend_id':fresh.supervisor.backend_id,
                    'policy_sha256':fresh.supervisor.policy_sha256}
                identities[key]=drift
                replacement=supervisors.PacketSupervisor(fresh.store,fresh.supervisor.backend,**identities)
                fresh=integration.PacketIntegrator(self.source,integration.FixtureGovernance(self.source),replacement)
                with self.assertRaisesRegex(packets.PacketError,'supervisor-host-policy-drift'):
                    replacement.admit_candidate('attempt',**self.source.requirements('add-update'))
                with mock.patch.object(replacement,'_inspect',side_effect=AssertionError('drift reached backend')):
                    with self.assertRaisesRegex(packets.PacketError,'supervisor-host-policy-drift'):
                        fresh.reconcile('operation',authority)
                self.assertEqual(self.image(),containers.BASELINE)
                self.assertEqual((self.root/'packet'/'ledger.json').read_bytes(),original)

    def test_no_json_capability_existing_source_or_second_operation(self):
        with self.assertRaises(packets.PacketError): integration.SyntheticSource(self.root,{},None)
        with self.assertRaises(packets.PacketError): integration.SyntheticSource.reopen(self.root,'a'*64)
        with self.assertRaises(packets.PacketError): integration.FixtureAuthority('authority','a'*64,None)
        integrator,authority=self.ready(); integrator.integrate('attempt',authority,operation_id='operation')
        with self.assertRaises(packets.PacketError): integrator.integrate('attempt',authority,operation_id='second-operation')
        self.assertEqual(list(self.snapshot()[0]['integrations']),['operation'])


if __name__=='__main__': unittest.main()
