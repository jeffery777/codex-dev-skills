"""Native v6 transaction contracts with a reconstructable daemon double.

The reader deliberately supplies fixed synthetic grants. These tests do not
qualify models, source authority, credentials or OS isolation.
"""
import ast
import copy
import io
import importlib.util
import json
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_packet_native as flow
import model_packet_lifecycle as lifecycle
import model_packet_store as packets
import model_native_checkpoint_backend as native
from tests.test_model_container_backend import FakeOneShotDocker
from tests.test_model_failover import fixture, route_fixture
from tests.test_model_packet_unused_source import ProofReader
from tests import test_model_packet_preparation as prepared_tests
from tests import test_model_packet_bootstrap as bootstrap_tests
from tests import test_model_packet_execution as execution_tests


class NativeDouble(FakeOneShotDocker):
    def image(self, image):
        return dict(Id=image, Os='linux', Architecture='arm64',
            Config={'Env':['PATH=/usr/local/bin:/usr/bin:/bin','PYTHON_VERSION=3.12.9'], 'Cmd':['python3']})

    def command(self, *argv):
        if argv[:2] == ('container','create'):
            cid = super().command(*argv).decode(); value = self.inspect(cid); options = list(argv)
            value['Image'] = value['Config']['Image'] = native.IMAGE
            value['Config']['Env'].append('PYTHON_VERSION=3.12.9')
            source = [options[i+1] for i,v in enumerate(options) if v == '--mount' and 'dst=/fixture' in options[i+1]][0]
            source = source.split('src=')[1].split(',')[0]
            if native.sys.platform == 'darwin': source = '/host_mnt'+source
            value['Mounts'][-1]['Propagation'] = ''
            value['Mounts'].append(dict(Type='bind', Source=source, Destination='/fixture', Mode='', RW=False, Propagation='rprivate'))
            value['HostConfig']['Mounts'][0]['BindOptions'] = {'Propagation':'rprivate'}
            value['HostConfig']['Mounts'][-1].pop('ReadOnly')
            value['HostConfig']['Mounts'].append(dict(Type='bind', Source=source, Target='/fixture', ReadOnly=True, BindOptions={'Propagation':'rprivate'}))
            value['HostConfig'].update(Memory=536870912, MemorySwap=536870912, PidsLimit=64, Tmpfs={'/tmp':native.TMPFS})
            self._write(cid, value); return cid.encode()
        if argv[:2] == ('container','start'):
            self.calls.append(argv); cid=argv[2]; value=self.inspect(cid)
            control=self._control(value)
            if (control/'claim.json').exists():
                value['State']['ExitCode']=73
            else:
                raw=(control/'input.json').read_bytes(); original=native.containers.archive.read_control_json(raw)
                claim=packets.canonical(dict(schema_version=1,input_sha256=packets.digest(raw),input=original))
                (control/'claim.json').write_bytes(claim)
                argv_fixed=ast.literal_eval(ast.parse(value['Config']['Cmd'][-1]).body[1].value)
                post=b'done\n' if argv_fixed[-2]=='successor-checkpoint' else b'new\n'
                (pathlib.Path(value['Mounts'][0]['Source'])/'example.txt').write_bytes(post)
                completion=packets.canonical(dict(schema_version=1,claim_sha256=packets.digest(claim),input_sha256=packets.digest(raw),input=original,worker_status=0))
                (control/'completion.json').write_bytes(completion)
            value['State'].update(Status='exited',Running=False,Pid=0,
                StartedAt='2026-10-05T00:01:00Z',FinishedAt='2026-10-05T00:01:01Z')
            self._write(cid,value)
            if self.start_fault: raise self.start_fault
            return cid.encode()
        return super().command(*argv)

    def _control(self, value):
        return self.root/next(m['Name'] for m in value['Mounts'] if m['Destination']=='/control')

    def archive(self, *argv, input_bytes=None):
        self.calls.append(argv)
        if argv[2]=='-':
            directory=self._control(self.inspect(argv[3].split(':')[0]))
            raw=native.containers.archive.read_control_file(input_bytes,'input.json')
            with (directory/'input.json').open('xb') as stream: stream.write(raw)
            if self.bootstrap_fault: raise self.bootstrap_fault
            return b''
        cid,path=argv[2].split(':',1); directory=self._control(self.inspect(cid))
        if path=='/control':
            output=io.BytesIO()
            with tarfile.open(fileobj=output,mode='w',format=tarfile.USTAR_FORMAT) as stream:
                entry=tarfile.TarInfo('control');entry.type=tarfile.DIRTYPE;entry.mode=0o755;stream.addfile(entry)
                for child in directory.iterdir():
                    entry=tarfile.TarInfo('control/'+child.name);entry.size=child.stat().st_size;entry.mode=0o600
                    stream.addfile(entry,io.BytesIO(child.read_bytes()))
            return output.getvalue()
        name=path.rsplit('/',1)[-1]
        return native.containers.archive.build_control_file(name,(directory/name).read_bytes())


class FixedReader(ProofReader):
    def readback_initial_source(self, objective): return flow.SOURCE


class Harness:
    """Fixed synthetic host authority; optionally uses actual opt-in Docker."""
    def __init__(self, root, engine, capsule, ref, *, control=None):
        self.root=pathlib.Path(root)
        for name in ('packets','reader'): (self.root/name).mkdir(mode=0o700, exist_ok=True)
        self.store=packets.PacketStore(self.root/'packets','packet-native-v6'); self.store.prepare('a'*64)
        self.backend=flow.NativeBackend(self.store,endpoint='unix:///fixed.sock',image_id=native.IMAGE,
            capture_root=capsule,capture_ref=ref,opt_in=True,_engine=engine,control=control)
        p=self.planning()
        self.request=dict(schema_version=1, objective=dict(repository=str(self.root),task_id='T1',
            scope='fixed-native-two-attempt',acceptance_sha256=packets.digest(flow.FINAL_PATCH),authority_id='authority'),
            policy=dict(freshness_seconds=60,service_attempt_limit=3,service_elapsed_limit_seconds=30),
            v2_task=dict(route_fixture()['task'],qualification_scope='fixed-native-two-attempt'),
            attempt_id='a1',generation=0,target_id='internal',target_identity=p['targets'][0]['identity'],
            stage='internal',source_sha256=packets.digest(flow.SOURCE))
        self.reader=FixedReader(self.root/'reader',self.store,self.backend,self.request)
        self.host=self.controller(); self.execution=None
        self.reader.save('admit','admit-native',self.host.admission_payload())
        with self.store.locked() as fd: original=self.store._read(fd)
        self.reader.seal('admit',lifecycle._binding(self.store,original,'admit'))
        self.host.admit_new('admit',expected_revision=0,now=110)

    def controller(self):
        return flow.NativeLifecycle(self.store,self.reader,self.backend,alias='alias1',host_id=self.backend.host_id,
            backend_id=self.backend.backend_id,policy_sha256=self.backend.policy_sha256)

    @classmethod
    def reopen(cls, root, engine, capsule, ref, state, *, control=None):
        """Only the opt-in anonymous verifier uses this fixed saved-reader factory."""
        value=object.__new__(cls);value.root=pathlib.Path(root)
        value.store=packets.PacketStore(value.root/'packets','packet-native-v6')
        value.backend=flow.NativeBackend(value.store,endpoint='unix:///fixed.sock',image_id=native.IMAGE,
            capture_root=capsule,capture_ref=ref,opt_in=True,_engine=engine,control=control)
        value.request=copy.deepcopy(state['request']);value.execution=state['execution'].encode()
        value.reader=FixedReader(value.root/'reader',value.store,value.backend,value.request)
        value.host=value.controller();value.current()
        return value

    def planning(self):
        p=fixture(); scope='fixed-native-two-attempt'; sha=packets.digest(flow.FINAL_PATCH)
        for key in ('task','authorization','secret_check'):
            p[key].update(scope=scope,acceptance_sha256=sha)
        for target in p['targets']:target['qualification']['scopes']=[scope]
        return p

    def current(self): return self.host.snapshot(now=110)

    def destination(self, ledger, action):
        return prepared_tests.PreparedLifecycleTests.destination(type('View',(),{'f':self,'execution':self.execution})(),ledger,action)

    def save(self, op, kind, payload, runtime=False):
        ledger,_=self.current(); actual=self.host.runtime_evidence(now=110) if runtime else None
        self.reader.save(op,kind,payload,request=self.request,runtime=actual)
        binding=lifecycle._binding(self.store,ledger,op);self.reader.seal(op,binding)
        if self.execution is not None:
            self.destination(ledger,kind)
            future=copy.deepcopy(ledger);e=self.reader.readback_evidence(binding)
            ref=dict(operation_id=op,kind=kind,binding=binding,committed_at=110)
            ref.update({field+'_sha256':None if getattr(e,field) is None else packets.digest(getattr(e,field)) for field in lifecycle.FIELDS})
            future['governance']['records'].append(ref);future['revision']+=1
            self.destination(future,kind)
        return ledger['revision']

    def acquire(self, suffix=''):
        ledger,state=self.current(); p=self.planning(); p['events']=copy.deepcopy(state['events'])
        self.request.update(attempt_id='a'+str(ledger['generation']+1),generation=ledger['generation']+1)
        op='acquire'+suffix; self.reader.save(op,'acquire',dict(owner_id='owner',epoch=state['owner_epoch']+1),request=self.request,planning=p)
        directory=self.reader.root/op;binding=lifecycle._binding(self.store,ledger,op)
        self.execution=packets.canonical(dict(schema_version=1,binding=binding,governance_request_sha256=packets.digest((directory/'request').read_bytes()),
            attempt_id=self.request['attempt_id'],generation=self.request['generation'],predecessor_sha256=ledger['checkpoint'],
            target_id='internal',target_identity=self.request['target_identity'],failover_payload=p,
            host_id=self.backend.host_id,backend_id=self.backend.backend_id,runtime_policy_sha256=self.backend.policy_sha256,
            # Fresh protected packet instances must not share daemon-global
            # container/control names. Reopen retains the original instance.
            runtime_id='native-'+self.backend.instance_sha256[:32]+'-'+self.request['attempt_id']))
        (directory/'execution').write_bytes(self.execution);self.reader.seal(op,binding);self.destination(ledger,'acquire')
        return self.host.acquire_attempt(op,expected_revision=ledger['revision'],now=110)

    def chain(self, suffix=''):
        ledger,_=self.current(); op='prepare'+suffix
        plan=self.host.plan_preparation(op,expected_revision=ledger['revision'],now=110)
        rev=self.save(op,'prepare-intent',dict(plan_bytes=plan.decode()))
        self.host.prepare_reserved(op,expected_revision=rev,now=110)
        descriptor,observation=self.host.preparation_evidence(now=110)
        rev=self.save('prepared'+suffix,'prepared',dict(descriptor_bytes=descriptor.decode(),observation_bytes=observation.decode()))
        self.host.confirm_prepared('prepared'+suffix,expected_revision=rev,now=110)
        raw=self.host.input_bootstrap(now=110)
        rev=self.save('bootstrap'+suffix,'bootstrap-intent',dict(input_bytes=raw.decode()))
        self.host.bootstrap_prepared('bootstrap'+suffix,expected_revision=rev,now=110)
        receipt,observation=self.host.bootstrap_evidence(now=110)
        rev=self.save('bootstrapped'+suffix,'bootstrapped',dict(receipt_bytes=receipt.decode(),observation_bytes=observation.decode()))
        return self.host.confirm_bootstrapped('bootstrapped'+suffix,expected_revision=rev,now=110)

    def launch(self, suffix=''):
        rev=self.save('launch'+suffix,'launch-intent',{})
        return self.host.launch_reserved('launch'+suffix,expected_revision=rev,now=110)

    def observe(self, suffix=''):
        rev=self.save('observe'+suffix,'observe',{},runtime=True)
        return self.host.reconcile('observe'+suffix,expected_revision=rev,now=110)

    def publish(self, suffix=''):
        rev=self.save('export'+suffix,'export-intent',{})
        self.host.seal('export'+suffix,expected_revision=rev,now=110)
        with self.store.locked() as fd:
            ledger,_=self.host._read(fd,110); attempt=ledger['attempts'][-1]
            patch=self.host._read_sealed_patch(fd,ledger,attempt)
            actual=self.host._inspect_runtime(fd,ledger,attempt)
            binding=ledger['supervisors'][attempt['id']]['binding']
        manifest=packets.canonical(dict(binding=binding,patch_sha256=packets.digest(patch),runtime_sha256=packets.digest(actual)))
        rev=self.save('publish'+suffix,'publish',dict(patch_sha256=packets.digest(patch),checkpoint_sha256=packets.digest(manifest)),runtime=True)
        return self.host.publish('publish'+suffix,expected_revision=rev,now=110)

    def failure(self, *, kind='quality', cause='capability', defect_id='fixed-final-postimage'):
        # The fixed reader records one independently selected outcome per attempt.
        payload=dict(attempt_id=self.request['attempt_id'],task_id='T1',scope=self.request['objective']['scope'],
            acceptance_sha256=self.request['objective']['acceptance_sha256'],target_id='internal',observed_at=110,
            kind=kind,cause=cause,defect_id=defect_id,correction=False,
            source_sha256=self.request['source_sha256'],transition=None)
        rev=self.save('outcome','outcome',payload)
        return self.host.record('outcome','outcome',expected_revision=rev,now=110)

    def finish(self, suffix='', result='completed'):
        ledger,state=self.current();owner=state['owner']
        rev=self.save('finish'+suffix,'finish',dict(result=result,owner_id=owner['owner_id'],epoch=owner['epoch']),runtime=True)
        return self.host.finish_attempt('finish'+suffix,expected_revision=rev,now=110)


class NativeLifecycleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        root=pathlib.Path(temp.name).resolve();(root/'engine').mkdir(mode=0o700)
        capsule=root/'capsule';capsule.mkdir(mode=0o700);(capsule/'guest').mkdir(mode=0o700)
        self.patcher=mock.patch.object(native,'validate_capsule',return_value={});self.patcher.start();self.addCleanup(self.patcher.stop)
        self.engine=NativeDouble(root/'engine');self.h=Harness(root,self.engine,capsule,{})

    def test_two_native_attempts_share_governance_and_restore_original_checkpoint(self):
        h=self.h;h.acquire();h.chain();h.launch();h.observe();h.failure();first,_=h.publish();c=first['checkpoint']
        h.finish(result='failed');h.host=h.controller();h.acquire('2');h.chain('2')
        ledger,state=h.current();a=ledger['attempts'][-1];self.assertEqual(a['predecessor_sha256'],c)
        self.assertEqual(state['correction_rounds'],0);self.assertEqual(len(state['events']),1)
        runtime=json.loads(h.execution)['runtime_id']
        self.assertEqual((h.store.root/h.store.packet_id/('workspace-'+runtime)/'example.txt').read_bytes(),b'new\n')
        h.launch('2');h.observe('2');second,_=h.publish('2');self.assertNotEqual(second['checkpoint'],c)
        ledger,state=h.finish('2');self.assertTrue(state['terminal']);self.assertIsNone(state['owner'])
        self.assertEqual(ledger['generation'],2);self.assertEqual(ledger['schema_version'],6)
        self.assertEqual([a['status'] for a in ledger['attempts']],['failed','completed'])
        self.assertEqual(sum(c[:2]==('container','start') for c in self.engine.calls),2)

    def test_saved_modes_cannot_accept_native_backend_or_records(self):
        for cls in (prepared_tests.PreparedLifecycleTests, bootstrap_tests.BootstrapFixtureTests, execution_tests.ExecutedLifecycleTests):
            obj=cls();obj.f=self.h
            with self.assertRaises(lifecycle.LifecycleError):obj.controller(backend=self.h.backend)
        with self.h.store.locked() as fd:
            with self.assertRaises(packets.PacketError):self.h.store._read(fd)
            with self.assertRaises(packets.PacketError):self.h.store._immutable(fd,'bypass',b'{}')

    def test_executor_loss_cannot_release_a_writer_that_is_no_longer_confirmed_stopped(self):
        h=self.h;h.acquire();h.chain();h.launch();h.observe();ledger,_=h.publish()
        checkpoint=ledger['checkpoint']
        with h.store.locked() as fd:
            with h.host._lease(fd,ledger['attempts'][-1]) as lease:
                cid=lease.descriptor()[1]['physical_descriptor']['container_id']
        value=self.engine.inspect(cid)
        value['State'].update(Status='running',Running=True,Pid=42,FinishedAt='0001-01-01T00:00:00Z')
        self.engine._write(cid,value)
        starts=sum(call[:2]==('container','start') for call in self.engine.calls)
        with self.assertRaises(packets.PacketError):
            h.observe('lost');h.failure(kind='service',cause='retriable-service',defect_id='executor-loss-after-checkpoint')
            h.finish('lost',result='failed');h.acquire('2');h.chain('2');h.launch('2')
        self.assertEqual(sum(call[:2]==('container','start') for call in self.engine.calls),starts)
        ledger,state=h.current();self.assertEqual(ledger['checkpoint'],checkpoint)
        self.assertIsNotNone(state['owner']);self.assertEqual(ledger['generation'],1)

    def test_published_checkpoint_survives_executor_loss_and_rejects_late_generation(self):
        h=self.h;h.acquire();h.chain();h.launch();h.observe();ledger,state=h.publish()
        checkpoint=ledger['checkpoint'];self.assertIsNotNone(state['owner'])
        with h.store.locked() as fd:
            original=ledger['governance']['records'][-1]
            raw=packets.trust._read(fd,'lifecycle-'+original['record_sha256']+'.json',packets.MAX_LEDGER)
        late_rev=h.save('late-publish','publish',json.loads(raw)['payload'],runtime=True)
        saved=dict(request=h.request,execution=h.execution.decode())
        h=Harness.reopen(h.root,self.engine,h.backend.drivers['checkpoint'].capture_root,{},saved)
        h.observe('lost');h.failure(kind='service',cause='retriable-service',defect_id='executor-loss-after-checkpoint')
        ledger,state=h.finish('lost',result='failed')
        self.assertEqual(ledger['checkpoint'],checkpoint);self.assertIsNone(state['owner'])
        h.acquire('2');h.chain('2');ledger,_=h.current();calls=len(self.engine.calls)
        with h.store.locked() as fd:
            with self.assertRaisesRegex(lifecycle.LifecycleError,'native-lease-owner-or-phase-drift'):
                with h.host._lease(fd,ledger['attempts'][0],action='export'):pass
        self.assertEqual(len(self.engine.calls),calls)
        h.launch('2');h.observe('2');h.publish('2');ledger,state=h.finish('2')
        calls=len(self.engine.calls)
        with self.assertRaisesRegex(lifecycle.LifecycleError,'lifecycle-revision-conflict'):
            h.host.publish('late-publish',expected_revision=late_rev,now=110)
        self.assertEqual(h.current()[0],ledger);self.assertEqual(len(self.engine.calls),calls)
        self.assertTrue(state['terminal']);self.assertEqual(state['events'][0]['kind'],'service')
        self.assertNotEqual(ledger['checkpoint'],checkpoint)

    def test_unleased_lookup_and_artifact_write_have_zero_transport_effects(self):
        h=self.h;h.acquire();h.chain();count=len(self.engine.calls)
        driver=h.backend.drivers['checkpoint']
        for fn in (lambda:driver.engine.inspect('a'*64),lambda:driver._save({},'baseline',b'{}'),
                   lambda:driver._packet_fd()):
            with self.assertRaises(lifecycle.LifecycleError):fn()
        self.assertEqual(len(self.engine.calls),count)

    def test_transaction_exit_and_wrong_action_reject_before_start(self):
        h=self.h;h.acquire();h.chain();count=len(self.engine.calls)
        with h.store.locked() as fd:
            ledger,_=h.host._read(fd,110)
            with h.host._lease(fd,ledger['attempts'][-1]) as lease:
                descriptor=lease.descriptor()[1]['physical_descriptor']
                with self.assertRaises(lifecycle.LifecycleError):lease.driver().engine.command('container','start',descriptor['container_id'])
        with self.assertRaises(packets.PacketError):lease._check()
        self.assertEqual(len(self.engine.calls),count)

    def test_lost_start_reply_is_retained_and_never_replayed(self):
        h=self.h;h.acquire();h.chain();self.engine.start_fault=RuntimeError('lost-reply')
        with self.assertRaises(RuntimeError):h.launch()
        h.host=h.controller();h.host.launch_reserved('launch',expected_revision=0,now=110);h.observe()
        self.assertEqual(sum(c[:2]==('container','start') for c in self.engine.calls),1)

    def test_read_lease_rejects_foreign_cid_and_bootstrap_write_before_transport(self):
        h=self.h;h.acquire();h.chain();count=len(self.engine.calls)
        with h.store.locked() as fd:
            ledger,_=h.host._read(fd,110)
            with h.host._lease(fd,ledger['attempts'][-1]) as lease:
                cid=lease.descriptor()[1]['physical_descriptor']['container_id']
                for callback in (lambda:lease.driver().engine.inspect('f'*64),
                    lambda:lease.driver().engine.archive('container','cp','-',cid+':/control',input_bytes=b'bad'),
                    lambda:lease.driver().engine.archive('container','cp',cid+':/control','/private/host-destination'),
                    lambda:lease.driver().engine.archive('container','cp',cid+':/etc/passwd','-'),
                    lambda:lease.driver().engine.archive('container','cp',cid+':/control','-','--follow-link'),
                    lambda:lease.driver().engine.archive('container','cp',cid+':/control','-',input_bytes=b'bad')):
                    with self.assertRaises(lifecycle.LifecycleError):callback()
        self.assertEqual(len(self.engine.calls),count)

    def test_fresh_packet_namespaces_differ_and_reopen_retains_original_execution(self):
        h=self.h;h.acquire();driver=h.backend.drivers['checkpoint']
        other=h.root/'other';other.mkdir(mode=0o700)
        fresh=Harness(other,self.engine,driver.capture_root,driver.capture_ref);fresh.acquire()
        self.assertNotEqual(json.loads(h.execution)['runtime_id'],json.loads(fresh.execution)['runtime_id'])
        reopened=Harness.reopen(h.root,self.engine,driver.capture_root,driver.capture_ref,
            dict(request=h.request,execution=h.execution.decode()))
        self.assertEqual(reopened.backend.instance_sha256,h.backend.instance_sha256)
        self.assertEqual(reopened.execution,h.execution)
        self.assertEqual(reopened.current(),h.current())

    def test_transport_transcript_preserves_raw_reply_and_unknown_without_retry(self):
        spec=importlib.util.spec_from_file_location('native_v6_host_test',ROOT/'scripts/verify-model-native-governance.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        engine=object.__new__(module.RecordedDocker)
        engine.transcript_root=self.h.root;engine.transcript_label='producer'
        engine.transcript_host=module.old_host();engine.transcript_count=0
        def returned(argv,raw):
            self.assertTrue((self.h.root/'producer-docker-0001-intent.json').is_file())
            return b'bounded raw reply\n'
        with mock.patch.object(native.containers.LocalDocker,'_transport',side_effect=returned) as call:
            self.assertEqual(engine._transport(('container','start','c'*64)),b'bounded raw reply\n')
            self.assertEqual(call.call_count,1)
        self.assertEqual((self.h.root/'producer-docker-0001.reply').read_bytes(),b'bounded raw reply\n')
        with mock.patch.object(native.containers.LocalDocker,'_transport',side_effect=RuntimeError('lost')) as call:
            with self.assertRaises(RuntimeError):engine._transport(('container','start','c'*64))
            self.assertEqual(call.call_count,1)
        self.assertEqual(json.loads((self.h.root/'producer-docker-0002-unknown.json').read_bytes())['outcome'],'unknown')
        self.assertFalse((self.h.root/'producer-docker-0002-returned.json').exists())

    def test_successor_rejects_changed_original_checkpoint_before_creation(self):
        h=self.h;h.acquire();h.chain();h.launch();h.observe();h.failure();ledger,_=h.publish()
        checkpoint=ledger['checkpoint'];h.finish(result='failed');h.acquire('2')
        path=h.store.root/h.store.packet_id/('lifecycle-checkpoint-'+checkpoint+'.json')
        original=path.read_bytes();path.write_bytes(original+b' ');count=len(self.engine.calls)
        try:
            with self.assertRaises((lifecycle.LifecycleError,packets.PacketError)):h.chain('2')
        finally:path.write_bytes(original)
        self.assertEqual(len(self.engine.calls),count)

    def test_changed_original_execution_invalidates_same_transaction_lease(self):
        h=self.h;h.acquire();h.chain();count=len(self.engine.calls)
        with h.store.locked() as fd:
            ledger,_=h.host._read(fd,110)
            with h.host._lease(fd,ledger['attempts'][-1]) as lease:
                path=h.store.root/h.store.packet_id/('lifecycle-'+ledger['attempts'][-1]['execution_request_sha256']+'.json')
                original=path.read_bytes();path.write_bytes(original+b' ')
                with self.assertRaises(lifecycle.LifecycleError):lease.driver().engine.inspect('a'*64)
                path.write_bytes(original)
        self.assertEqual(len(self.engine.calls),count)


if __name__=='__main__': unittest.main()
