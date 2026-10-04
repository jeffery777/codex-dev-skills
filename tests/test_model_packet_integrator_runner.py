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



class ReloadDocker(OverlapDocker):
    """Durable daemon double for the private stages; no CLI or Docker transport."""
    instances=[]
    _allowed=runner._ReloadDocker._allowed
    def __init__(self,endpoint,root,stage,*,image,cid=None,volume=None,deadline=None):
        super().__init__(root)
        self.endpoint=endpoint;self.stage=stage;self.image_id=image;self.cid=cid;self.volume_name=volume
        self.deadline=deadline;self.executable='/synthetic/docker';self.executable_identity=(1,2,'docker')
        self.trace=[];self.failures=[];self.containers=[];self.volumes=[]
        self.instances.append(self)
    def command(self,*argv):
        runner._ReloadDocker._allowed(self,argv,None)
        raw=super().command(*argv)
        if argv[:2]==('container','create'):self.containers.append(raw.decode())
        if argv[:2]==('volume','create'):self.volumes.append(raw.decode())
        return raw
    def archive(self,*argv,input_bytes=None):
        runner._ReloadDocker._allowed(self,argv,input_bytes)
        return super().archive(*argv,input_bytes=input_bytes)
    def inspect(self,cid):
        value=super().inspect(cid)
        if self.stage=='consumer':
            try:runner._reload_running(value,self.cid)
            except Exception as error:self.failures.append(str(error));raise
        return value


class ControllerReloadTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name).resolve();self.root.chmod(0o700)
        self.request={'run_id':'a'*32,'coordinator_pid':runner.os.getpid(),
            'bundle_sha256':'b'*64,'interpreter':runner._reload_interpreter(),
            'endpoint':'unix:///synthetic/docker.sock','image':IMAGE,
            'docker_executable':'/synthetic/docker','docker_identity':[1,2,'docker']}
        ReloadDocker.instances=[]

    def produce(self):
        with mock.patch.object(runner,'_ReloadDocker',ReloadDocker), \
                mock.patch.object(runner.os,'getpid',return_value=101), \
                mock.patch.object(runner.os,'getppid',return_value=self.request['coordinator_pid']):
            runner._reload_produce(self.root,self.request)
        raw,ref=runner._reload_read(self.root,'producer-handoff.json')
        handoff=json.loads(raw);waited=runner.time.monotonic()
        permit={'schema_version':1,'run_id':self.request['run_id'],'producer_pid':101,'producer_exit':0,
            'producer_waited_at':waited,'handoff_ref':ref,'consumer_spawned_after':waited}
        runner._reload_save(self.root,'consumer-permit.json',permit)
        return handoff,permit

    def test_source_closure_private_import_preflight_and_sentinel_not_inherited(self):
        hashes=runner._reload_capture(self.root)
        self.assertGreaterEqual(len(hashes),12)
        self.assertIn('skills/loop-engineering/scripts/local_model_mapping.py',hashes)
        fd=runner.trust._directory(self.root)
        try:identity=runner._reload_identity(runner.os.fstat(fd))[:4]
        finally:runner.os.close(fd)
        request={**self.request,'schema_version':1,'root_identity':identity,'bundle_hashes':hashes,
            'bundle_sha256':runner.packets.digest(runner.packets.canonical(hashes))}
        runner._reload_save(self.root,'reload-request.json',request)
        read,write=runner.os.pipe();sentinel=runner.fcntl.fcntl(read,runner.fcntl.F_DUPFD,100)
        try:
            runner.os.set_inheritable(sentinel,True)
            result=runner._reload_helper(self.root,request,'preflight',sentinel,runner.time.monotonic()+10)
            self.assertEqual(result['exit_code'],0)
            self.assertNotEqual(result['pid'],runner.os.getpid())
            evidence=json.loads((self.root/'preflight-helper-readback.json').read_bytes())
            self.assertFalse(evidence['own_helper_killed'])
            self.assertFalse(evidence['docker_children_stopped_claimed'])
        finally:
            runner.os.close(read);runner.os.close(write);runner.os.close(sentinel)

    def test_bundle_missing_extra_import_and_hash_drift_fail_before_engine(self):
        hashes=runner._reload_capture(self.root);bundle=self.root/'bundle'
        for failure in ('missing','extra-file','hash','dependency'):
            with self.subTest(failure=failure):
                copy_hashes=dict(hashes)
                if failure=='missing':copy_hashes.pop(next(iter(copy_hashes)))
                elif failure=='extra-file':(bundle/'extra.py').write_text('pass');(bundle/'extra.py').chmod(0o600)
                else:
                    path=bundle/runner._RELOAD_RUNNER;original=path.read_bytes()
                    path.write_bytes(original+b'\nimport forbidden_ambient_dependency\n')
                    if failure=='dependency':copy_hashes[runner._RELOAD_RUNNER]=runner.packets.digest(path.read_bytes())
                with mock.patch.object(runner.containers,'LocalDocker') as engine,self.assertRaises(runner.packets.PacketError):
                    runner._reload_validate_bundle(bundle,copy_hashes)
                engine.assert_not_called()
                if failure=='extra-file':(bundle/'extra.py').unlink()
                if failure in ('hash','dependency'):path.write_bytes(original)

    def test_private_refs_reject_symlink_nonregular_identity_and_digest_tamper(self):
        ref=runner._reload_save(self.root,'reference.json',{'fixed':True})
        self.assertEqual(json.loads(runner._reload_ref(self.root,ref)),{'fixed':True})
        for failure in ('digest','identity','traversal'):
            changed=dict(ref)
            if failure=='digest':changed['sha256']='0'*64
            elif failure=='identity':changed['identity']=[0]*8
            else:changed['relative']='../reference.json'
            with self.subTest(failure=failure),self.assertRaises(runner.packets.PacketError):runner._reload_ref(self.root,changed)
        (self.root/'link').symlink_to(self.root/'reference.json')
        with self.assertRaises(OSError):runner._reload_read(self.root,'link')
        runner.os.mkfifo(self.root/'fifo',0o600)
        with self.assertRaisesRegex(runner.packets.PacketError,'regular-file'):runner._reload_read(self.root,'fifo')
        (self.root/'directory').mkdir(mode=0o700)
        with self.assertRaisesRegex(runner.packets.PacketError,'regular-file'):runner._reload_read(self.root,'directory')
        with self.assertRaisesRegex(runner.packets.PacketError,'regular-file'):runner._reload_read(self.root,'reference.json',limit=1)

    def test_original_live_checkpoint_reconstruction_once_unknown_no_authority(self):
        handoff,_=self.produce()
        original=runner.supervisors.PacketSupervisor.reconcile;calls=[]
        def reconcile(supervisor,attempt):calls.append(attempt);return original(supervisor,attempt)
        with mock.patch.object(runner,'_ReloadDocker',ReloadDocker), \
                mock.patch.object(runner.supervisors.PacketSupervisor,'reconcile',reconcile), \
                mock.patch.object(runner.integration.SyntheticSource,'create') as create, \
                mock.patch.object(runner.integration.FixtureGovernance,'issue') as issue, \
                mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'prepare') as prepare, \
                mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'export_patch') as export:
            result=runner._reload_consume(self.root,self.request)
        self.assertEqual(calls,['old']);self.assertEqual(result['stage'],'consumer')
        for blocked in (create,issue,prepare,export):blocked.assert_not_called()
        evidence=json.loads((self.root/'consumer-result.json').read_bytes())
        self.assertEqual(evidence['result'],runner._RELOAD_PENDING)
        self.assertEqual(evidence['observations'],[handoff['observation']]*2)
        self.assertEqual(evidence['ledger_delta'],'deduplicated')
        self.assertFalse(evidence['production_qualified'])
        for call in ReloadDocker.instances[-1].calls:
            self.assertIn(call[:2],[('container','top'),('container','cp')])
        self.assertEqual(len(ReloadDocker.instances[0].containers),2)
        self.assertEqual(len(ReloadDocker.instances[0].volumes),2)

    def test_live_to_stopped_race_and_backend_error_stay_unknown_without_export_intent(self):
        for failure in ('stopped-proof','error','actual-stop'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                oldroot=self.root;self.root=pathlib.Path(tmp).resolve();self.root.chmod(0o700)
                handoff,_=self.produce();inspect=runner.containers.OneShotSyntheticContainerBackend.inspect
                def broken(backend,binding,descriptor):
                    if failure=='error':raise OSError('backend-read-failed')
                    if failure=='actual-stop':
                        value=backend.engine.inspect(descriptor['container_id'])
                        value['State'].update(Status='exited',Running=False,Pid=0)
                        backend.engine._write(descriptor['container_id'],value)
                        return inspect(backend,binding,descriptor)
                    reply=inspect(backend,binding,descriptor);return {**reply,'state':'stopped'}
                with mock.patch.object(runner,'_ReloadDocker',ReloadDocker), \
                        mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'inspect',broken), \
                        mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'export_patch') as export, \
                        self.assertRaisesRegex(runner.packets.PacketError,'consumer-proof-failed'):
                    runner._reload_consume(self.root,self.request)
                export.assert_not_called()
                ledger=json.loads((self.root/runner._RELOAD_PACKET/'ledger.json').read_bytes())
                self.assertEqual(ledger['supervisors']['old']['stage'],'observing')
                self.assertEqual(ledger['checkpoint'],handoff['refs']['checkpoint'])
                self.assertFalse((self.root/'consumer-result.json').exists());self.root=oldroot

    def test_handoff_exit_pid_order_and_required_ref_fail_without_engine(self):
        _,permit=self.produce()
        for failure in ('nonzero','not-exited','same-pid','early','no-handoff','run','expired'):
            changed=runner.copy.deepcopy(permit)
            if failure=='nonzero':changed['producer_exit']=1
            elif failure=='not-exited':changed['producer_exit']=None
            elif failure=='same-pid':changed['producer_pid']=runner.os.getpid()
            elif failure=='early':changed['producer_waited_at']=0;changed['consumer_spawned_after']=0
            elif failure=='no-handoff':changed.pop('handoff_ref')
            elif failure=='run':changed['run_id']='c'*32
            else:changed['producer_waited_at']=runner.time.monotonic()+100;changed['consumer_spawned_after']=changed['producer_waited_at']
            with self.subTest(failure=failure),mock.patch.object(runner,'_ReloadDocker') as engine, \
                    self.assertRaises(runner.packets.PacketError):runner._reload_handoff(self.root,self.request,changed)
            engine.assert_not_called()

    def test_before_consumer_checkpoint_descriptor_ledger_lock_and_source_tamper_fail_without_engine(self):
        for failure in ('patch','descriptor','ledger','lock','source'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                oldroot=self.root;self.root=pathlib.Path(tmp).resolve();self.root.chmod(0o700)
                handoff,_=self.produce()
                if failure=='source':path=self.root/handoff['source_relative']/'source/example.txt'
                else:
                    key={'patch':'patch_ref','descriptor':'descriptor_ref','ledger':'ledger_ref','lock':'lock_ref'}[failure]
                    path=self.root/handoff['refs'][key]['relative']
                path.write_bytes(b'tamper\n')
                with mock.patch.object(runner,'_ReloadDocker') as engine,self.assertRaises(runner.packets.PacketError):
                    runner._reload_consume(self.root,self.request)
                engine.assert_not_called();self.root=oldroot

    def test_engine_policy_image_daemon_drift_does_not_pass(self):
        for failure in ('image','daemon','executable'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                oldroot=self.root;self.root=pathlib.Path(tmp).resolve();self.root.chmod(0o700);self.produce()
                class Drift(ReloadDocker):
                    def __init__(self,*args,**kwargs):
                        super().__init__(*args,**kwargs)
                        if failure=='daemon':self.daemon='d'*64
                        if failure=='executable':self.executable='/other/docker'
                    def image(self,image):
                        value=super().image(image)
                        if failure=='image':value['Id']='sha256:'+'0'*64
                        return value
                with mock.patch.object(runner,'_ReloadDocker',Drift),self.assertRaises(runner.packets.PacketError):
                    runner._reload_consume(self.root,self.request)
                self.assertFalse((self.root/'consumer-result.json').exists());self.root=oldroot

    def test_legal_unknown_observation_append_and_dedup_but_no_other_ledger_change(self):
        self.produce();store=runner.packets.PacketStore(self.root,runner._RELOAD_PACKET)
        before=store.supervisor_snapshot('old')[0]
        self.assertEqual(runner._reload_ledger_delta(before,before),'deduplicated')
        # Remove the existing dedup event in this isolated fixture, then exercise
        # the actual store append operation to obtain the exact lawful event.
        with store.locked() as fd:
            ledger=store._read(fd);ledger['supervisors']['old']['observations']=[];store._write(fd,ledger)
        before=store.supervisor_snapshot('old')[0]
        after=store.observe_supervisor_unknown('old','runtime-proof-unavailable')
        self.assertEqual(runner._reload_ledger_delta(before,after),'appended')
        for field in ('checkpoint','generation','revision'):
            drift=runner.copy.deepcopy(after);drift[field]='drift'
            with self.subTest(field=field),self.assertRaisesRegex(runner.packets.PacketError,'ledger-unexpected-drift'):
                runner._reload_ledger_delta(before,drift)

    def test_consumer_exact_transport_allowlist_denies_all_mutation_and_other_targets(self):
        engine=object.__new__(runner._ReloadDocker)
        engine.stage='consumer';engine.image_id=IMAGE;engine.cid='a'*64;engine.volume_name='original-control'
        allowed=[('info','--format','{{json .ID}}'),('image','inspect',IMAGE),
            ('container','inspect',engine.cid),('volume','inspect',engine.volume_name),
            ('container','top',engine.cid,'-eo','pid,ppid,uid,stat,comm'),
            ('container','cp',engine.cid+':/control','-')]
        for call in allowed:engine._allowed(call,None)
        denied=[('container','stop',engine.cid),('container','start',engine.cid),('container','restart',engine.cid),
            ('container','create'),('volume','create'),('image','pull',IMAGE),('container','inspect','b'*64),
            ('volume','inspect','other'),('container','cp',engine.cid+':/workspace','-'),
            ('container','cp','-',engine.cid+':/control'),('container','cp',engine.cid+':/control/completion.json','-')]
        for call in denied:
            with self.subTest(call=call),self.assertRaisesRegex(runner.packets.PacketError,'command-denied'):engine._allowed(call,None)
        with self.assertRaisesRegex(runner.packets.PacketError,'command-denied'):engine._allowed(allowed[-1],b'archive')

    def test_helper_unknown_spawn_nonzero_partial_and_expired_never_replayed(self):
        for failure in ('spawn','nonzero','partial','timeout','truncated'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700)
                process=mock.Mock(pid=909)
                process.stdout=mock.Mock();process.stdout.fileno.return_value=900
                process.stderr=mock.Mock();process.stderr.fileno.return_value=901
                process.wait.return_value=1 if failure=='nonzero' else 0;process.poll.return_value=process.wait.return_value
                stdout=b'{"stage":"consumer","pid":909,"run_id":"'+self.request['run_id'].encode()+b'"}'
                if failure=='partial':stdout=b'{'
                if failure=='truncated':stdout=b'x'*(runner._RELOAD_HELPER_LIMIT+1)
                actual_read=runner.os.read;replies=iter([stdout,b'',b''])
                def read(fd,size):return next(replies) if fd in (900,901) else actual_read(fd,size)
                with mock.patch.object(runner.subprocess,'Popen',side_effect=OSError('spawn-unknown') if failure=='spawn' else None,
                        return_value=process) as spawn, \
                        mock.patch.object(runner.os,'set_blocking'), \
                        mock.patch.object(runner.select,'select',side_effect=[([] if failure=='timeout' else [900,901],[],[]),([900],[],[])]), \
                        mock.patch.object(runner.os,'read',side_effect=read), \
                        self.assertRaises(Exception):
                    runner._reload_helper(root,self.request,'consumer',100,runner.time.monotonic()+5)
                spawn.assert_called_once()
                self.assertTrue((root/'consumer-helper-readback.json').exists())
        with mock.patch.object(runner.subprocess,'Popen') as spawn,self.assertRaisesRegex(runner.packets.PacketError,'deadline-unavailable'):
            runner._reload_helper(self.root,self.request,'consumer',100,runner.time.monotonic())
        spawn.assert_not_called()

    def test_interpreter_drift_and_conflicting_opt_in_modes_fail_closed(self):
        with mock.patch.object(runner.sys,'version_info',(3,11,0)),self.assertRaisesRegex(runner.packets.PacketError,'interpreter-drift'):
            runner._reload_interpreter()
        with mock.patch.object(runner,'run') as run,self.assertRaises(SystemExit):
            runner.main(['--synthetic-qualified-container-fixture','--controller-reload-only','--checkpoint-overlap-only',
                '--endpoint',self.request['endpoint'],'--image',IMAGE,'--evidence-root',str(self.root)])
        run.assert_not_called()

    def test_raw_transport_audit_requires_original_running_inspect_and_read_only_commands(self):
        now=runner.time.monotonic();cid='a'*64
        handoff={'sealed_at':now-1,'deadline':now+20,'observation':{'process_table':'raw fixed top'},'refs':{'descriptor':{'container_id':cid,
            'created_at':'fixed-created','control_volume':{'name':'original-control'}}}}
        inspected={'Id':cid,'Created':'fixed-created','State':{'Status':'running','Running':True,'Pid':42}}
        argv=[('container','inspect',cid)]*5+[('container','top',cid,'-eo','pid,ppid,uid,stat,comm')]*2
        for index,call in enumerate(argv):
            row={'argv':list(call),'input_bytes':None,'started':now,'reply_base64':'','error':None}
            name='consumer-transport-'+str(index)+'.json'
            runner._reload_save(self.root,name+'.intent',row)
            reply=runner.packets.canonical([inspected]) if call[1]=='inspect' else b'raw fixed top\n'
            runner._reload_save(self.root,name,{**row,'finished':now+.01,'reply_base64':runner.base64.b64encode(reply).decode()})
        audit=runner._reload_audit_trace(self.root,'consumer',len(argv),self.request,handoff)
        self.assertEqual((audit['inspections'],audit['tops']),(5,2))
        path=self.root/'consumer-transport-0.json';original=path.read_bytes();row=json.loads(original)
        for failure in ('stopped','cid','created','error','mutation','expired','oversize'):
            changed=runner.copy.deepcopy(row)
            if failure in ('stopped','cid','created'):
                value=runner.copy.deepcopy(inspected)
                if failure=='stopped':value['State'].update(Status='exited',Running=False,Pid=0)
                elif failure=='cid':value['Id']='b'*64
                else:value['Created']='other'
                changed['reply_base64']=runner.base64.b64encode(runner.packets.canonical([value])).decode()
            elif failure=='error':changed['error']='unknown-partial'
            elif failure=='mutation':changed['argv']=['container','start',cid]
            elif failure=='expired':changed['finished']=handoff['deadline']
            else:changed['reply_base64']=runner.base64.b64encode(b'x'*65537).decode()
            path.write_bytes(runner.packets.canonical(changed))
            with self.subTest(failure=failure),self.assertRaises(runner.packets.PacketError):
                runner._reload_audit_trace(self.root,'consumer',len(argv),self.request,handoff)
        path.write_bytes(original)

    def test_transport_denial_timeout_partial_truncation_and_reserve_are_sticky(self):
        for failure in ('denied','timeout','partial','truncated','reserve'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700)
                engine=object.__new__(runner._ReloadDocker)
                engine.root=root;engine.stage='consumer';engine.image_id=IMAGE;engine.cid='a'*64
                engine.volume_name='control-original';engine.deadline=runner.time.monotonic()+(1 if failure=='reserve' else 25)
                engine.trace=[];engine.trace_bytes=0;engine.failures=[];engine.containers=[];engine.volumes=[]
                engine.executable='/synthetic/docker';engine.endpoint=self.request['endpoint'];engine.executable_identity=('fixed',)
                engine.environment={'HOME':str(root)}
                engine._executable_snapshot=mock.Mock(return_value=('fixed',))
                process=mock.Mock();process.stdout.fileno.return_value=900;process.stdin=None
                process.wait.return_value=1 if failure=='partial' else 0;process.poll.return_value=0
                reply=b'x'*65537 if failure=='truncated' else b'raw-partial'
                call=('container','start',engine.cid) if failure=='denied' else ('container','inspect',engine.cid)
                actual_read=runner.os.read;replies=iter([reply,b''])
                def read(fd,size):return next(replies) if fd==900 else actual_read(fd,size)
                with mock.patch.object(runner.subprocess,'Popen',return_value=process) as spawn, \
                        mock.patch.object(runner.os,'set_blocking'), \
                        mock.patch.object(runner.select,'select',return_value=([] if failure=='timeout' else [process.stdout],[],[])), \
                        mock.patch.object(runner.os,'read',side_effect=read),self.assertRaises(runner.packets.PacketError):
                    engine._transport(call)
                if failure in ('denied','reserve'):spawn.assert_not_called()
                else:spawn.assert_called_once()
                self.assertTrue(engine.failures)
                raw=json.loads((root/'consumer-transport-0.json').read_bytes())
                self.assertIsNotNone(raw['error'])
                if failure in ('partial','truncated'):
                    self.assertEqual(runner.base64.b64decode(raw['reply_base64']),reply)

    def test_consumer_detects_after_reconcile_checkpoint_source_and_worker_drift(self):
        for failure in ('checkpoint','source','worker'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                oldroot=self.root;self.root=pathlib.Path(tmp).resolve();self.root.chmod(0o700)
                handoff,_=self.produce();original=runner.containers.OneShotSyntheticContainerBackend.inspect
                def inspect(backend,binding,descriptor):
                    reply=original(backend,binding,descriptor)
                    if failure=='checkpoint':(self.root/handoff['refs']['patch_ref']['relative']).write_bytes(b'changed\n')
                    elif failure=='source':(self.root/handoff['source_relative']/'source/example.txt').write_bytes(b'changed\n')
                    else:
                        backend.engine.command=lambda *args:b'PID PPID UID STAT COMMAND\n42 1 0 S python3\n4243 42 65534 S python3\n'
                    return reply
                with mock.patch.object(runner,'_ReloadDocker',ReloadDocker), \
                        mock.patch.object(runner.containers.OneShotSyntheticContainerBackend,'inspect',inspect), \
                        self.assertRaises(runner.packets.PacketError):runner._reload_consume(self.root,self.request)
                self.assertFalse((self.root/'consumer-result.json').exists());self.root=oldroot

    def test_coordinator_never_spawns_consumer_without_successful_producer_wait_and_handoff(self):
        for failure in ('unknown-spawn','nonzero','no-handoff'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700);stages=[]
                def helper(home,request,stage,sentinel,deadline):
                    stages.append(stage)
                    if stage=='producer':
                        if failure=='unknown-spawn':raise OSError('spawn-outcome-unknown')
                        if failure=='nonzero':raise runner.packets.PacketError('reload-helper-nonzero')
                    return {'pid':101,'exit_code':0,'waited_at':runner.time.monotonic()}
                engine=mock.Mock(executable='/synthetic/docker',executable_identity=(1,2,'docker'))
                args=SimpleNamespace(evidence_root=root,endpoint=self.request['endpoint'],image=IMAGE)
                with mock.patch.object(runner.containers,'LocalDocker',return_value=engine), \
                        mock.patch.object(runner,'_reload_helper',side_effect=helper),self.assertRaises(Exception):
                    runner.controller_reload(args)
                self.assertEqual(stages,['preflight','producer'])
                receipt=json.loads(next(root.glob('model-controller-reload-*/controller-reload-evidence.json')).read_bytes())
                self.assertEqual(receipt['execution_outcome'],'unknown');self.assertEqual(receipt['cases'],{})
                self.assertFalse(receipt['n3_complete']);self.assertFalse(receipt['runtime_qualified'])


    def transport_doubles(self,root,*,stage='producer'):
        engine=object.__new__(runner._ReloadDocker)
        engine.root=root;engine.stage=stage;engine.image_id=IMAGE;engine.cid='a'*64;engine.volume_name='control-original'
        engine.deadline=runner.time.monotonic()+25;engine.trace=[];engine.trace_bytes=0;engine.failures=[]
        engine.containers=[];engine.volumes=[];engine.executable='/synthetic/docker'
        engine.endpoint=self.request['endpoint'];engine.executable_identity=('fixed',)
        engine.environment={'HOME':str(root)};engine._executable_snapshot=mock.Mock(return_value=('fixed',))
        process=mock.Mock();process.stdout.fileno.return_value=900;process.stdout.closed=False;process.stdin=None
        process.wait.return_value=0;process.poll.return_value=0
        return engine,process

    def call_transport(self,engine,process,*,input_bytes=None,timeout=False):
        actual_read=runner.os.read;replies=iter([b'raw-reply',b''])
        def read(fd,size):return next(replies) if fd==900 else actual_read(fd,size)
        with mock.patch.object(runner.subprocess,'Popen',return_value=process) as spawn, \
                mock.patch.object(runner.os,'set_blocking'), \
                mock.patch.object(runner.select,'select',return_value=([] if timeout else [process.stdout],[],[])), \
                mock.patch.object(runner.os,'read',side_effect=read):
            engine.spawn=spawn
            return engine._transport(('container','inspect',engine.cid),input_bytes=input_bytes)

    def test_transport_intent_write_and_fsync_failures_are_sticky_and_cannot_spawn(self):
        for phase in ('write','fsync'):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700);engine,process=self.transport_doubles(root)
                original_save=runner._reload_save;original_fsync=runner.os.fsync
                target=root/'producer-transport-0.json.intent';faults=[]
                def save(home,name,value):
                    if name==target.name and phase=='write':raise OSError('intent-write-unknown')
                    return original_save(home,name,value)
                def fsync(fd):
                    if phase=='fsync' and target.exists() and runner.os.fstat(fd).st_ino==target.stat().st_ino:
                        faults.append(fd);raise OSError('intent-fsync-unknown')
                    return original_fsync(fd)
                with mock.patch.object(runner,'_reload_save',side_effect=save), \
                        mock.patch.object(runner.os,'fsync',side_effect=fsync),self.assertRaises(OSError):
                    self.call_transport(engine,process)
                engine.spawn.assert_not_called();self.assertTrue(engine.failures)
                result=json.loads((root/'producer-transport-0.json').read_bytes())
                self.assertIsNotNone(result['error']);self.assertEqual(result['reply_base64'],'')
                if phase=='fsync':self.assertEqual(len(faults),1);self.assertTrue(target.exists())

    def test_full_result_bytes_then_fsync_or_readback_failure_remain_sticky_and_immutable(self):
        for phase in ('fsync','readback'):
            with self.subTest(phase=phase),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700);engine,process=self.transport_doubles(root)
                target=root/'producer-transport-0.json';original_fsync=runner.os.fsync;original_read=runner._reload_read
                faults=[]
                def fsync(fd):
                    if phase=='fsync' and target.exists() and runner.os.fstat(fd).st_ino==target.stat().st_ino:
                        faults.append('fsync');raise OSError('result-fsync-unknown')
                    return original_fsync(fd)
                def read(home,name,*args,**kwargs):
                    if phase=='readback' and name==target.name:
                        faults.append('readback');raise OSError('result-readback-unknown')
                    return original_read(home,name,*args,**kwargs)
                with mock.patch.object(runner.os,'fsync',side_effect=fsync), \
                        mock.patch.object(runner,'_reload_read',side_effect=read),self.assertRaises(OSError):
                    self.call_transport(engine,process)
                engine.spawn.assert_called_once();self.assertEqual(faults,[phase])
                self.assertTrue(any('transport-result-journal' in error for error in engine.failures))
                saved=target.read_bytes();value=json.loads(saved)
                self.assertIsNone(value['error'])  # Complete bytes are uncertain, never rewritten.
                self.assertEqual(runner.base64.b64decode(value['reply_base64']),b'raw-reply')
                self.assertIsNotNone(engine.trace[0]['error'])
                with self.assertRaises(FileExistsError):runner._reload_save(root,target.name,{'replacement':True})
                self.assertEqual(target.read_bytes(),saved)

    def test_transport_cleanup_kill_wait_and_each_pipe_close_are_sticky_but_normal_return_survives(self):
        for failure in ('kill','wait','stdout-close','stdin-close','none'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as tmp:
                root=pathlib.Path(tmp).resolve();root.chmod(0o700);engine,process=self.transport_doubles(root)
                if failure in ('kill','wait'):
                    process.poll.return_value=None
                    if failure=='kill':process.kill.side_effect=OSError('kill-unknown')
                    else:process.wait.side_effect=OSError('wait-unknown')
                if failure=='stdout-close':process.stdout.close.side_effect=OSError('stdout-close-unknown')
                if failure=='stdin-close':
                    process.stdin=mock.Mock();process.stdin.closed=False
                    process.stdin.fileno.return_value=901;process.stdin.close.side_effect=OSError('stdin-close-unknown')
                if failure=='none':
                    self.assertEqual(self.call_transport(engine,process),b'raw-reply')
                    self.assertEqual(engine.failures,[]);process.kill.assert_not_called();process.wait.assert_called_once()
                else:
                    with self.assertRaises(runner.packets.PacketError):
                        self.call_transport(engine,process,input_bytes=b'archive' if failure=='stdin-close' else None,
                            timeout=failure in ('kill','wait','stdin-close'))
                    self.assertTrue(engine.failures)
                    phase='transport-cleanup' if failure in ('kill','wait') else 'transport-'+failure
                    self.assertTrue(any(phase in error for error in engine.failures))
                process.stdout.close.assert_called_once()
                value=json.loads((root/'producer-transport-0.json').read_bytes())
                self.assertEqual(value['error'] is None,failure=='none')

    def test_producer_swallowed_result_journal_error_cannot_seal_successful_handoff(self):
        actual_transport=runner._ReloadDocker._transport;original_save=runner._reload_save;faults=[]
        test=self
        class JournalFaultDocker(ReloadDocker):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs);self.trace_bytes=0;self.environment={'HOME':str(self.root)}
                self._executable_snapshot=lambda:self.executable_identity;self.injected=False
            def inspect(self,cid):
                value=super().inspect(cid)
                if not self.injected and value['State']['Running'] is True:
                    self.injected=True
                    _,process=test.transport_doubles(self.root)
                    actual_read=runner.os.read;replies=iter([runner.packets.canonical([value]),b''])
                    def read(fd,size):return next(replies) if fd==900 else actual_read(fd,size)
                    with mock.patch.object(runner.subprocess,'Popen',return_value=process) as spawn, \
                            mock.patch.object(runner.os,'set_blocking'), \
                            mock.patch.object(runner.select,'select',return_value=([process.stdout],[],[])), \
                            mock.patch.object(runner.os,'read',side_effect=read):
                        try:actual_transport(self,('container','inspect',cid))
                        finally:self.spawn=spawn
                return value
        def save(root,name,value):
            result=original_save(root,name,value)
            if name=='producer-transport-0.json':
                faults.append(name);raise OSError('result-readback-after-full-bytes')
            return result
        with mock.patch.object(runner,'_ReloadDocker',JournalFaultDocker), \
                mock.patch.object(runner,'_reload_save',side_effect=save), \
                mock.patch.object(runner.os,'getpid',return_value=101), \
                mock.patch.object(runner.os,'getppid',return_value=self.request['coordinator_pid']), \
                self.assertRaisesRegex(runner.packets.PacketError,'producer-live-proof-unavailable'):
            runner._reload_produce(self.root,self.request)
        engine=ReloadDocker.instances[-1];engine.spawn.assert_called_once()
        self.assertEqual(faults,['producer-transport-0.json']);self.assertTrue(engine.failures)
        self.assertFalse((self.root/'producer-handoff.json').exists())
        result=json.loads((self.root/'producer-transport-0.json').read_bytes())
        self.assertIsNone(result['error'])
        ledger=json.loads((self.root/runner._RELOAD_PACKET/'ledger.json').read_bytes())
        self.assertEqual(ledger['supervisors']['old']['stage'],'observing')
        self.assertEqual(ledger['supervisors']['old']['observations'][-1]['reason'],'runtime-proof-unavailable')



if __name__=='__main__': unittest.main()
