"""Runner contract test with fixed reconstructable daemon double; no live engine."""
import importlib.util
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


class RunnerTests(unittest.TestCase):
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
