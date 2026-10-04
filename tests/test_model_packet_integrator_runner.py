"""Runner contract test with fixed reconstructable daemon double; no live engine."""
import importlib.util
import ast
import io
import tarfile
import json
import pathlib
import tempfile
import unittest
import sys
from types import SimpleNamespace
from unittest import mock

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_model_packet_integrator import FixtureDocker, IMAGE
spec=importlib.util.spec_from_file_location('integrator_runner',ROOT/'scripts/verify-model-packet-integrator.py')
runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)


class OverlapDocker(FixtureDocker):
    """Fixed reconstructable hold double; never forks or contacts Docker."""
    def command(self,*argv):
        if argv[:2]==('container','top'):
            self.calls.append(argv);value=self.inspect(argv[2]);pid=value['State']['Pid']
            return f'PID PPID UID STAT COMMAND\n{pid} 1 0 S python3\n4242 {pid} 65534 S python3\n'.encode()
        raw=super().command(*argv)
        if argv[:2]==('container','start'):
            value=self.inspect(argv[2])
            worker=ast.literal_eval(next(line.removeprefix('WORKER=')
                for line in value['Config']['Cmd'][-1].splitlines() if line.startswith('WORKER=')))
            if worker==runner.containers.WORKERS['hold-overlap']:
                workspace=pathlib.Path(value['Mounts'][0]['Source'])
                (workspace/'example.txt').write_bytes(b'holding\n')
                (self.root/value['Mounts'][-1]['Name']/'completion.json').unlink()
                value['State'].update(Status='running',Running=True,Pid=42,FinishedAt='0001-01-01T00:00:00Z')
                self._write(argv[2],value)
        return raw


class RunnerTests(unittest.TestCase):
    def overlap_args(self,root):
        return SimpleNamespace(evidence_root=root,endpoint='unix:///synthetic/docker.sock',
            image=IMAGE,checkpoint_overlap_only=True)

    def test_nonempty_checkpoint_live_quarantine_and_successor_only_source_integration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve();root.chmod(0o700);engines=[]
            def factory(home): engines.append(OverlapDocker(home));return engines[-1]
            result=runner.run(self.overlap_args(root),_engine_factory=factory)
            self.assertFalse(result['production_qualified'])
            self.assertEqual(set(result['cases']),{'checkpoint-overlap'})
            case=result['cases']['checkpoint-overlap']
            self.assertTrue(case['passed']);self.assertFalse(case['old_stop_claimed'])
            self.assertEqual(case['seed_patch_sha256'],runner.packets.digest(runner.integration.FIXED_PATCH))
            self.assertEqual(case['successor_patch_sha256'],case['seed_patch_sha256'])
            self.assertNotEqual(case['seed_checkpoint_sha256'],case['successor_checkpoint_sha256'])
            self.assertEqual(len(case['old_running_observations']),4)
            self.assertTrue(all(x['State']['Running'] is True for x in case['old_running_observations']))
            self.assertEqual({x['worker_pid'] for x in case['old_running_observations']},{4242})
            self.assertTrue(all(x['control']['completion_absent'] is True for x in case['old_running_observations']))
            self.assertEqual(set(case['stale_rejections']),{'reconcile','admit','publish','integrate'})
            self.assertEqual(case['integration']['state'],'applied')
            source=pathlib.Path(case['source'])/'source'
            self.assertEqual((source/'example.txt').read_bytes(),b'new\n')
            self.assertEqual((source/'added.txt').read_bytes(),b'added\n')
            self.assertEqual((source/'remove.txt').read_bytes(),b'delete\n')
            calls=engines[0].calls
            for pair in [('container','create'),('container','start'),('volume','create')]:
                self.assertEqual(sum(call[:2]==pair for call in calls),3)
            self.assertFalse(any(call[:2] in [('container','stop'),('container','restart'),
                ('container','rm'),('volume','rm'),('image','pull')] for call in calls))

    def test_missing_overlap_after_successor_never_issues_authority_or_writes_source(self):
        class ExpiredDocker(OverlapDocker):
            def __init__(self,root):super().__init__(root);self.started=[]
            def command(self,*argv):
                raw=super().command(*argv)
                if argv[:2]==('container','start'):
                    self.started.append(argv[2])
                    if len(self.started)==3:
                        value=self.inspect(self.started[1]);value['State'].update(Status='exited',Running=False,Pid=0)
                        self._write(self.started[1],value)
                return raw
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve();root.chmod(0o700)
            with mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                    mock.patch.object(runner.integration.PacketIntegrator,'integrate') as integrate, \
                    self.assertRaisesRegex(runner.packets.PacketError,'fixture-old-writer-overlap-unavailable'):
                runner.run(self.overlap_args(root),_engine_factory=ExpiredDocker)
            issue.assert_not_called();integrate.assert_not_called()
            receipt=json.loads(next(root.glob('model-packet-integrator-*/integrator-evidence.json')).read_bytes())
            self.assertEqual(receipt['cases'],{});self.assertEqual(receipt['execution_outcome'],'unknown')

    def test_dead_worker_after_integration_retains_unknown(self):
        class DeadAfterIntegration(OverlapDocker):
            def __init__(self, root):
                super().__init__(root); self.top_reads=0
            def command(self, *argv):
                raw=super().command(*argv)
                if argv[:2]==('container','top'):
                    self.top_reads+=1
                    if self.top_reads==4:
                        raw=raw.replace(b'65534 S python3', b'65534 X python3')
                return raw
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve();root.chmod(0o700)
            with self.assertRaisesRegex(runner.packets.PacketError,'fixture-live-worker-identity-unavailable'):
                runner.run(self.overlap_args(root),_engine_factory=DeadAfterIntegration)
            receipt=json.loads(next(root.glob('model-packet-integrator-*/integrator-evidence.json')).read_bytes())
            self.assertEqual(receipt['cases'],{})
            self.assertEqual(receipt['execution_outcome'],'unknown')

    def test_worker_done_completion_zombie_dead_or_replacement_with_live_root_cannot_pass(self):
        for failure in ('done','completion','root-only','zombie','dead','new-pid'):
            class FinishedDocker(OverlapDocker):
                def __init__(self,root):super().__init__(root);self.started=[];self.changed=False
                def command(self,*argv):
                    if argv[:2]==('container','top') and self.changed:
                        value=self.inspect(argv[2]);pid=value['State']['Pid']
                        if failure=='root-only':return f'PID PPID UID STAT COMMAND\n{pid} 1 0 S python3\n'.encode()
                        if failure in ('zombie','dead','new-pid'):
                            child=4243 if failure=='new-pid' else 4242;state={'zombie':'Z','dead':'X'}.get(failure,'S')
                            return f'PID PPID UID STAT COMMAND\n{pid} 1 0 S python3\n{child} {pid} 65534 {state} python3\n'.encode()
                    raw=super().command(*argv)
                    if argv[:2]==('container','start'):
                        self.started.append(argv[2])
                        if len(self.started)==3:
                            self.changed=True;value=self.inspect(self.started[1]);workspace=pathlib.Path(value['Mounts'][0]['Source'])
                            if failure=='done':(workspace/'example.txt').write_bytes(b'done\n')
                            if failure=='completion':
                                control=self.root/value['Mounts'][-1]['Name'];input_raw=(control/'input.json').read_bytes();claim_raw=(control/'claim.json').read_bytes()
                                completion={'schema_version':1,'claim_sha256':runner.packets.digest(claim_raw),
                                    'input_sha256':runner.packets.digest(input_raw),'input':json.loads(input_raw),'worker_status':0}
                                (control/'completion.json').write_bytes(runner.packets.canonical(completion))
                    return raw
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temporary:
                root=pathlib.Path(temporary).resolve();root.chmod(0o700)
                with mock.patch.object(runner.integration.PacketIntegrator,'integrate') as integrate, \
                        self.assertRaises(runner.packets.PacketError):
                    runner.run(self.overlap_args(root),_engine_factory=FinishedDocker)
                integrate.assert_not_called()
                receipt=json.loads(next(root.glob('model-packet-integrator-*/integrator-evidence.json')).read_bytes())
                self.assertEqual(receipt['cases'],{});self.assertEqual(receipt['execution_outcome'],'unknown')

    def test_expired_top_readback_is_unknown_before_control_or_source_access(self):
        backend=mock.Mock();backend._observed.return_value={'Id':'x','Created':'t',
            'State':{'Status':'running','Running':True,'Pid':42}}
        backend.engine.command.return_value=b'PID PPID UID STAT COMMAND\n42 1 0 S python3\n4242 42 65534 S python3\n'
        with mock.patch.object(runner.time,'monotonic',side_effect=[0,0,0,8]), \
                self.assertRaisesRegex(runner.packets.PacketError,'fixture-live-readback-expired'):
            runner.running_observation(backend,{}, {'container_id':'exact'},deadline=8)
        backend._walk.assert_not_called();backend.engine.archive.assert_not_called()

    def test_live_control_strict_tar_binding_and_completion_negative_controls(self):
        input_raw=runner.packets.canonical({'fixed':'input'})
        claim=runner.packets.canonical({'schema_version':1,'input_sha256':runner.packets.digest(input_raw),
            'input':json.loads(input_raw)})
        def archive(change=None):
            output=io.BytesIO()
            with tarfile.open(fileobj=output,mode='w',format=tarfile.USTAR_FORMAT) as tar:
                directory=tarfile.TarInfo('control');directory.type=tarfile.DIRTYPE;directory.mode=0o755;tar.addfile(directory)
                entries=[('control/input.json',input_raw),('control/claim.json',claim)]
                if change=='completion':entries.append(('control/completion.json',b'{}'))
                if change=='duplicate':entries.append(entries[0])
                for name,payload in entries:
                    if change=='binding' and name.endswith('input.json'):payload=b'{"fixed":"changed"}'
                    if change=='duplicate-json' and name.endswith('input.json'):payload=b'{"fixed":"input","fixed":"input"}'
                    info=tarfile.TarInfo(name);info.mode=0o600;info.size=len(payload)
                    if change=='uid':info.uid=65534
                    if change=='mode':info.mode=0o644
                    if change=='link':info.type=tarfile.SYMTYPE;info.linkname='/outside';info.size=0
                    if change=='path':info.name='control/../input.json'
                    tar.addfile(info,io.BytesIO(payload) if info.isreg() else None)
            return output.getvalue()
        backend=mock.Mock();backend.bootstrap_input.return_value=input_raw
        with mock.patch.object(runner.time,'monotonic',return_value=0):
            backend.engine.archive.return_value=archive()
            good=runner.running_control(backend,{}, {'container_id':'exact'},8)
            self.assertTrue(good['completion_absent'])
            self.assertEqual(good['claim_sha256'],runner.packets.digest(claim))
            for change in ('completion','duplicate','binding','duplicate-json','uid','mode','link','path'):
                backend.engine.archive.return_value=archive(change)
                with self.subTest(change=change),self.assertRaises((runner.packets.PacketError,runner.containers.archive.ArchiveError)):
                    runner.running_control(backend,{}, {'container_id':'exact'},8)
            for raw in (b'',archive()[:512],archive()+b'x'*512,b'x'*66048):
                backend.engine.archive.return_value=raw
                with self.subTest(length=len(raw)),self.assertRaises((runner.packets.PacketError,runner.containers.archive.ArchiveError)):
                    runner.running_control(backend,{}, {'container_id':'exact'},8)

    def test_successor_from_empty_baseline_cannot_pass_or_obtain_authority(self):
        original=runner.containers.OneShotSyntheticContainerBackend.prepare
        def ignore_checkpoint(backend,binding,patch):
            return original(backend,binding,b'' if binding['attempt_id']=='successor' else patch)
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve();root.chmod(0o700)
            with mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'prepare',ignore_checkpoint), \
                    mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                    self.assertRaisesRegex(runner.packets.PacketError,'fixture-successor-checkpoint-not-preserved'):
                runner.run(self.overlap_args(root),_engine_factory=OverlapDocker)
            issue.assert_not_called()

    def test_running_readback_requires_exact_physical_policy_and_typed_pid(self):
        backend=mock.Mock();binding={'exact':'binding'};descriptor={'exact':'descriptor'}
        for state in [{'Status':'exited','Running':False,'Pid':0},
                {'Status':'running','Running':True,'Pid':True},
                {'Status':'running','Running':True,'Pid':0},
                {'Status':'running','Running':1,'Pid':42}]:
            backend._observed.return_value={'Id':'x','Created':'t','State':state}
            with self.subTest(state=state),self.assertRaisesRegex(runner.packets.PacketError,'overlap-unavailable'):
                runner.running_observation(backend,binding,descriptor)
        backend._observed.side_effect=runner.packets.PacketError('runtime-descriptor-identity-drift')
        with self.assertRaisesRegex(runner.packets.PacketError,'runtime-descriptor-identity-drift'):
            runner.running_observation(backend,binding,descriptor)

    def test_unknown_successor_create_start_or_export_never_replays_or_integrates(self):
        original_export=runner.containers.OneShotSyntheticContainerBackend.export_patch
        for phase in ('create','start','export'):
            class LostDocker(OverlapDocker):
                def __init__(self,root):super().__init__(root);self.creates=0;self.starts=0
                def command(self,*argv):
                    if argv[:2]==('container','create'):
                        self.creates+=1
                        if phase=='create' and self.creates==3:self.create_fault=OSError('synthetic-create-reply-lost')
                    if argv[:2]==('container','start'):
                        self.starts+=1
                        if phase=='start' and self.starts==3:self.start_fault=OSError('synthetic-start-reply-lost')
                    return super().command(*argv)
            def lost_export(backend,binding,*argv):
                result=original_export(backend,binding,*argv)
                if phase=='export' and binding['attempt_id']=='successor':raise OSError('synthetic-export-reply-lost')
                return result
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as temporary:
                root=pathlib.Path(temporary).resolve();root.chmod(0o700);engines=[]
                def factory(home):engines.append(LostDocker(home));return engines[-1]
                with mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'export_patch',lost_export), \
                        mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                        mock.patch.object(runner.integration.PacketIntegrator,'integrate') as integrate, \
                        self.assertRaisesRegex(runner.packets.PacketError,'successor-checkpoint-not-preserved'):
                    runner.run(self.overlap_args(root),_engine_factory=factory)
                issue.assert_not_called();integrate.assert_not_called()
                self.assertEqual(engines[0].creates,3)
                self.assertEqual(engines[0].starts,2 if phase=='create' else 3)
                receipt=json.loads(next(root.glob('model-packet-integrator-*/integrator-evidence.json')).read_bytes())
                self.assertEqual(receipt['cases'],{});self.assertEqual(receipt['execution_outcome'],'unknown')

    def test_checkpoint_drift_or_isolation_revocation_prevents_successor_launch(self):
        for failure in ('checkpoint','isolation'):
            class DriftDocker(OverlapDocker):
                def __init__(self,root):super().__init__(root);self.creates=0
                def command(self,*argv):
                    if argv[:2]==('container','create'):self.creates+=1
                    raw=super().command(*argv)
                    if argv[:2]==('container','start') and self.creates==2:
                        if failure=='checkpoint':
                            packet=next(self.root.glob('packet-checkpoint-overlap'))
                            ledger=json.loads((packet/'ledger.json').read_bytes())
                            (packet/(ledger['checkpoint']+'.patch')).write_bytes(b'corrupt\n')
                    return raw
            original=runner.containers.SyntheticContainerBackend.isolation_adapter
            def revoked(backend,binding,descriptor):
                adapter=original(backend,binding,descriptor)
                if failure=='isolation':
                    adapter.readback_isolation=lambda _: (_ for _ in ()).throw(runner.packets.PacketError('synthetic-isolation-revoked'))
                return adapter
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temporary:
                root=pathlib.Path(temporary).resolve();root.chmod(0o700);engines=[]
                def factory(home):engines.append(DriftDocker(home));return engines[-1]
                with mock.patch.object(runner.containers.SyntheticContainerBackend,'isolation_adapter',revoked), \
                        mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                        self.assertRaises(runner.packets.PacketError):
                    runner.run(self.overlap_args(root),_engine_factory=factory)
                issue.assert_not_called();self.assertEqual(engines[0].creates,2)

    def test_authority_revocation_and_unknown_source_write_do_not_pass_or_reapply(self):
        original_issue=runner.integration.FixtureGovernance.issue
        original_write=runner.integration.PacketIntegrator._write_file
        for failure in ('revoke','write'):
            def issue(governance,*argv,**kwargs):
                capability=original_issue(governance,*argv,**kwargs)
                if failure=='revoke':governance.revoke(capability)
                return capability
            writes=[]
            def write(integrator,fd,name,raw,pre):
                writes.append(name)
                original_write(integrator,fd,name,raw,pre)
                if failure=='write':raise OSError('synthetic-write-result-unknown')
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temporary:
                root=pathlib.Path(temporary).resolve();root.chmod(0o700)
                with mock.patch.object(runner.integration.FixtureGovernance,'issue',issue), \
                        mock.patch.object(runner.integration.PacketIntegrator,'_write_file',write), \
                        self.assertRaisesRegex(runner.packets.PacketError,
                            'source-authority-revoked' if failure=='revoke' else 'successor-integration-unavailable'):
                    runner.run(self.overlap_args(root),_engine_factory=OverlapDocker)
                self.assertEqual(len(writes),0 if failure=='revoke' else 1)
                receipt=json.loads(next(root.glob('model-packet-integrator-*/integrator-evidence.json')).read_bytes())
                self.assertEqual(receipt['cases'],{});self.assertEqual(receipt['execution_outcome'],'unknown')

    def pending(self):
        descriptor={'container_id':'a'*64,'created_at':'2026-10-02T00:00:00Z'}
        candidate={'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'attempt'}
        running={'Id':descriptor['container_id'],'Created':descriptor['created_at'],
            'State':{'Status':'running','Running':True,'Pid':42}}
        stopped={**running,'State':{'Status':'exited','Running':False,'Pid':0}}
        store=mock.Mock(); store.read_runtime_descriptor.return_value=descriptor
        supervisor=mock.Mock(); supervisor.reconcile.return_value={'outcome':'integration-candidate'}
        return descriptor,candidate,running,stopped,store,supervisor

    def test_poll_running_to_stop_inspects_only_saved_cid_then_reconciles_once(self):
        descriptor,candidate,running,stopped,store,supervisor=self.pending()
        engine=mock.Mock(); engine.inspect.side_effect=[running,running,stopped]
        with mock.patch.object(runner.time,'monotonic',return_value=0),mock.patch.object(runner.time,'sleep') as sleep:
            result=runner.await_candidate(supervisor,store,engine,'attempt',candidate)
        self.assertEqual(result,supervisor.reconcile.return_value)
        self.assertEqual(engine.method_calls,[mock.call.inspect(descriptor['container_id'])]*3)
        self.assertEqual(store.method_calls,[mock.call.read_runtime_descriptor('attempt')])
        self.assertEqual(supervisor.method_calls,[mock.call.reconcile('attempt')])
        self.assertEqual(sleep.call_args_list,[mock.call(.1)]*2)

    def test_poll_deadline_or_frozen_clock_cap_retains_unknown_without_reconcile(self):
        descriptor,candidate,running,stopped,store,supervisor=self.pending()
        engine=mock.Mock(); engine.inspect.return_value=running
        clock=[0.0]
        def sleep(seconds): clock[0]+=seconds
        with mock.patch.object(runner.time,'monotonic',side_effect=lambda:clock[0]), \
                mock.patch.object(runner.time,'sleep',side_effect=sleep):
            self.assertIs(runner.await_candidate(supervisor,store,engine,'attempt',candidate),candidate)
        self.assertLessEqual(engine.inspect.call_count,80)
        self.assertLessEqual(clock[0],8)
        supervisor.reconcile.assert_not_called()
        engine.reset_mock()
        with mock.patch.object(runner.time,'monotonic',return_value=0),mock.patch.object(runner.time,'sleep'):
            self.assertIs(runner.await_candidate(supervisor,store,engine,'attempt',candidate),candidate)
        self.assertEqual(engine.method_calls,[mock.call.inspect(descriptor['container_id'])]*80)
        supervisor.reconcile.assert_not_called()
        # A slow read returning stop after the deadline cannot qualify it.
        engine.reset_mock(); engine.inspect.return_value=stopped
        with mock.patch.object(runner.time,'monotonic',side_effect=[0,0,8]),mock.patch.object(runner.time,'sleep'):
            self.assertIs(runner.await_candidate(supervisor,store,engine,'attempt',candidate),candidate)
        supervisor.reconcile.assert_not_called()

    def test_poll_wrong_cid_created_descriptor_or_read_failure_cannot_reconcile(self):
        descriptor,candidate,running,stopped,store,supervisor=self.pending()
        for observed in [dict(stopped,Id='b'*64),dict(stopped,Created='different'),None,dict(stopped,State=None)]:
            engine=mock.Mock(); engine.inspect.return_value=observed
            with self.subTest(observed=observed),mock.patch.object(runner.time,'monotonic',return_value=0), \
                    self.assertRaises(runner.packets.PacketError):
                runner.await_candidate(supervisor,store,engine,'attempt',candidate)
            self.assertEqual(engine.method_calls,[mock.call.inspect(descriptor['container_id'])])
        engine=mock.Mock(); store.read_runtime_descriptor.side_effect=runner.packets.PacketError('invalid-runtime-descriptor')
        with self.assertRaisesRegex(runner.packets.PacketError,'invalid-runtime-descriptor'):
            runner.await_candidate(supervisor,store,engine,'attempt',candidate)
        engine.assert_not_called(); self.assertEqual(engine.method_calls,[])
        store.read_runtime_descriptor.side_effect=None
        engine.inspect.side_effect=runner.packets.PacketError('docker-reply-unknown')
        with self.assertRaisesRegex(runner.packets.PacketError,'docker-reply-unknown'):
            runner.await_candidate(supervisor,store,engine,'attempt',candidate)
        supervisor.reconcile.assert_not_called()

    def test_physical_stop_still_requires_full_reconcile_and_never_retries_other_unknown(self):
        descriptor,candidate,running,stopped,store,supervisor=self.pending()
        engine=mock.Mock(); engine.inspect.return_value=stopped
        supervisor.reconcile.return_value=dict(candidate)
        with mock.patch.object(runner.time,'monotonic',return_value=0),mock.patch.object(runner.time,'sleep'):
            self.assertEqual(runner.await_candidate(supervisor,store,engine,'attempt',candidate),candidate)
        supervisor.reconcile.assert_called_once_with('attempt')
        for result in [{'outcome':'integration-candidate'},dict(candidate,reason='launch-reply-unknown'),
                dict(candidate,reason='export-reply-unknown')]:
            engine.reset_mock(); store.reset_mock(); supervisor.reset_mock()
            self.assertIs(runner.await_candidate(supervisor,store,engine,'attempt',result),result)
            self.assertEqual(engine.method_calls,[]); self.assertEqual(store.method_calls,[])
            self.assertEqual(supervisor.method_calls,[])

    def test_runner_poll_expiry_never_issues_authority_or_applies_source(self):
        class RunningDocker(FixtureDocker):
            def __init__(self,root): super().__init__(root); self.started=set()
            def command(self,*argv):
                raw=super().command(*argv)
                if argv[:2]==('container','start'): self.started.add(argv[2])
                return raw
            def inspect(self,cid):
                value=super().inspect(cid)
                if cid in self.started: value['State'].update(Status='running',Running=True,Pid=42)
                return value
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve(); root.chmod(0o700)
            args=SimpleNamespace(evidence_root=root,endpoint='unix:///synthetic/docker.sock',image=IMAGE)
            clock=[0.0]
            def sleep(seconds): clock[0]+=seconds
            with mock.patch.object(runner.time,'monotonic',side_effect=lambda:clock[0]), \
                    mock.patch.object(runner.time,'sleep',side_effect=sleep), \
                    mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                    mock.patch.object(runner.integration.PacketIntegrator,'integrate') as integrate, \
                    self.assertRaisesRegex(runner.packets.PacketError,'fixture-candidate-unqualified'):
                runner.run(args,_engine_factory=RunningDocker)
            issue.assert_not_called(); integrate.assert_not_called()
            saved=list(root.glob('model-packet-integrator-*/integrator-evidence.json'))
            self.assertEqual(len(saved),1)
            receipt=json.loads(saved[0].read_bytes())
            self.assertEqual(receipt['execution_outcome'],'unknown'); self.assertEqual(receipt['cases'],{})
            self.assertEqual(len(receipt['containers_retained']),1)
            self.assertFalse(receipt['production_qualified'])

    def test_delayed_eight_case_double_recovers_without_relaunch_and_rejects_unqualified_stop(self):
        class DelayedDocker(FixtureDocker):
            def __init__(self,root): super().__init__(root); self.pending={}
            def command(self,*argv):
                raw=super().command(*argv)
                if argv[:2]==('container','start'): self.pending[argv[2]]=3
                return raw
            def inspect(self,cid):
                value=super().inspect(cid)
                if self.pending.get(cid,0):
                    self.pending[cid]-=1
                    value['State'].update(Status='running',Running=True,Pid=42)
                return value
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve(); root.chmod(0o700)
            args=SimpleNamespace(evidence_root=root,endpoint='unix:///synthetic/docker.sock',image=IMAGE)
            engines=[]
            def factory(root): engines.append(DelayedDocker(root)); return engines[-1]
            with mock.patch.object(runner.time,'monotonic',return_value=0),mock.patch.object(runner.time,'sleep'):
                receipt=runner.run(args,_engine_factory=factory)
            self.assertEqual(len(receipt['cases']),8)
            self.assertTrue(all(value['passed'] for value in receipt['cases'].values()))
            starts=[call for call in engines[0].calls if call[:2]==('container','start')]
            creates=[call for call in engines[0].calls if call[:2]==('container','create')]
            self.assertEqual(len(starts),8); self.assertEqual(len(creates),8)
            self.assertEqual(len({call[2] for call in starts}),8)
        class InvalidCompletionDocker(DelayedDocker):
            def inspect(self,cid):
                value=super().inspect(cid)
                if value['State']['Status']=='exited': value['State']['ExitCode']=1
                return value
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve(); root.chmod(0o700)
            args=SimpleNamespace(evidence_root=root,endpoint='unix:///synthetic/docker.sock',image=IMAGE)
            with mock.patch.object(runner.time,'monotonic',return_value=0),mock.patch.object(runner.time,'sleep'), \
                    mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                    self.assertRaisesRegex(runner.packets.PacketError,'fixture-candidate-unqualified'):
                runner.run(args,_engine_factory=InvalidCompletionDocker)
            issue.assert_not_called()
            saved=list(root.glob('model-packet-integrator-*/integrator-evidence.json'))
            self.assertEqual(len(saved),1)
            receipt=json.loads(saved[0].read_bytes())
            self.assertEqual(receipt['execution_outcome'],'unknown'); self.assertEqual(receipt['cases'],{})
            self.assertEqual(len(receipt['containers_retained']),1)

    def test_fixed_eight_cases_retained_receipt_and_default_off_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=pathlib.Path(temporary).resolve(); root.chmod(0o700)
            args=SimpleNamespace(evidence_root=root,endpoint='unix:///synthetic/docker.sock',image=IMAGE)
            receipt=runner.run(args,_engine_factory=FixtureDocker)
            self.assertEqual(len(receipt['cases']),8)
            self.assertTrue(all(value['passed'] for value in receipt['cases'].values()))
            self.assertFalse(receipt['production_qualified'])
            self.assertEqual(len(receipt['containers_retained']),8)
            self.assertEqual(len(receipt['volumes_retained']),8)
            self.assertTrue((pathlib.Path(receipt['fixture'])/'integrator-evidence.json').is_file())
        with self.assertRaises(SystemExit): runner.main([])


if __name__=='__main__': unittest.main()
