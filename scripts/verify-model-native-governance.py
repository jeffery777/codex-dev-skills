#!/usr/bin/env python3
"""Opt-in two-process native v6 experiment; fixed synthetic reader, no qualification.

Repository test fixtures supply anonymous grants only. Every executable source
is captured and independently read before stages; actual Docker/native results
remain distinct from those fixture grants. No credential or real provider entry.
"""
import argparse
import ast
import importlib.util
import os
import pathlib
import sys
import tempfile
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/loop-engineering/scripts'))
import model_native_checkpoint_backend as native
import model_packet_store as packets
import model_packet_native as flow
import model_native_host_control as host_control

EXECUTOR_LOSS_EXIT = 86
# Anonymous experiment budgets include full capture/physical readbacks. These
# are not model service budgets and never authorize continuing a timed-out run.
STAGE_WAIT_SECONDS = {'preflight': 140, 'producer': 140, 'consumer': 220}
SESSION_TTL_SECONDS = 400


def validate_stage_wait(request, name, started, waited):
    """Actual coordinator wait is distinct from runtime/writer evidence."""
    loss = request.get('executor_loss', False)
    if type(loss) is not bool or name not in {'preflight', 'producer', 'consumer'}:
        raise packets.PacketError('native-v6-loss-contract')
    expected = EXECUTOR_LOSS_EXIT if loss and name == 'producer' else 0
    if (type(started.get('pid')) is not int or started['pid'] <= 0
            or type(waited.get('pid')) is not int or waited['pid'] != started['pid']
            or type(waited.get('exit_code')) is not int or waited['exit_code'] != expected
            or waited.get('stderr_eof') is not True or waited.get('stderr_base64') != ''):
        raise packets.PacketError('native-v6-stage-failed:'+name)

HOST_FILES=tuple(dict.fromkeys((*native.SOURCE_FILES,
    'scripts/verify-model-native-governance.py',
    'skills/loop-engineering/scripts/model_packet_execution.py',
    *('tests/'+name+'.py' for name in ('test_model_packet_native','test_model_packet_preparation',
        'test_model_packet_bootstrap','test_model_packet_execution','test_model_packet_lifecycle',
        'test_model_packet_unused_source','test_model_packet_historical_source','test_model_packet_governance',
        'test_model_container_backend','test_model_failover')))))


def validate_host_inventory():
    """Reject missing static import contracts before capture or Docker lookup."""
    allowed={pathlib.PurePosixPath(name).stem for name in HOST_FILES}|set(sys.stdlib_module_names)|{'tests'}
    for name in HOST_FILES:
        path=ROOT/name
        if not path.is_file() or path.is_symlink():
            raise packets.PacketError('native-v6-host-file-inventory-drift')
        for node in ast.parse(path.read_bytes()).body:
            imports=([item.name.split('.')[0] for item in node.names] if isinstance(node,ast.Import)
                else [node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [])
            if any(module not in allowed for module in imports):
                raise packets.PacketError('native-v6-host-import-inventory-drift')


def old_host():
    spec=importlib.util.spec_from_file_location('native_v6_capture_host',ROOT/native.HOST_SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def host_capture(host,root):
    target=root/'trusted-host';target.mkdir(mode=0o700)
    for name in HOST_FILES:
        original=ROOT/name
        raw,ref=native.read_file(original,1048576,original.stat().st_mode&0o777)
        destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd=os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if native.read_file(original,1048576,original.stat().st_mode&0o777)[1]!=ref:
            raise packets.PacketError('native-v6-host-source-capture-drift')
    for directory,_,_ in os.walk(target,topdown=False):host.sync_directory(pathlib.Path(directory))
    result=native.inspect_tree(target,HOST_FILES,private=True)
    host.save(root,'host-sources.json',result);return result


class RecordedDocker(native.containers.LocalDocker):
    """Private immutable transport evidence; never authority or retry input."""
    def __init__(self,endpoint,root,label,host):
        if label not in {'coordinator','preflight','producer','consumer'}:
            raise packets.PacketError('native-v6-transcript-label-invalid')
        self.transcript_root,self.transcript_label,self.transcript_host=root,label,host
        self.transcript_count=0
        super().__init__(endpoint,root)

    def _transport(self,argv,input_bytes=None):
        if self.transcript_count>=2048:raise packets.PacketError('native-v6-transcript-bound')
        self.transcript_count+=1
        name=self.transcript_label+'-docker-'+str(self.transcript_count).zfill(4)
        self.transcript_host.save(self.transcript_root,name+'-intent.json',dict(argv=list(argv),
            input_sha256=None if input_bytes is None else packets.digest(input_bytes),
            input_bytes=0 if input_bytes is None else len(input_bytes)))
        try:
            raw=super()._transport(argv,input_bytes)
            fd=os.open(self.transcript_root/(name+'.reply'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.transcript_host.sync_directory(self.transcript_root)
            self.transcript_host.save(self.transcript_root,name+'-returned.json',dict(
                reply_sha256=packets.digest(raw),reply_bytes=len(raw)))
            return raw
        except Exception as error:
            self.transcript_host.save(self.transcript_root,name+'-unknown.json',dict(
                outcome='unknown',error_type=type(error).__name__))
            raise


def refs(store):
    """Original immutable files remain identical; subsequent journal growth allowed."""
    with store.locked() as fd:
        return {name:packets.digest(packets.trust._read(fd,name,packets.MAX_LEDGER))
            for name in os.listdir(fd) if name not in {'ledger.json','lock'}
            and not name.startswith('artifact-') and not name.startswith('workspace-')}


def frame(host,h,root,label):
    ledger,_=h.current();attempt=ledger['attempts'][-1]
    with h.store.locked() as fd:
        with h.host._lease(fd,attempt) as lease:
            descriptor=lease.descriptor()[1]['physical_descriptor'];case=lease.driver().native_case
            actual=lease.driver()._observed(lease.physical_binding(),descriptor)
            if actual['State']['ExitCode']!=0 or actual['State']['Status']!='exited':
                raise packets.PacketError('native-v6-execution-not-complete')
            cid=descriptor['container_id']
            raw=lease.driver().engine.command('container','logs',cid)
    # Docker command trims the single trailing newline; restore only this fixed frame delimiter.
    raw+=b'\n'
    fd=os.open(root/(label+'-worker-frame'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    proof=host.worker_observation(raw,{'case':case},descriptor)
    proof.update(cid=cid,case=case,descriptor_sha256=packets.digest(packets.canonical(descriptor)))
    host.save(root,label+'-native-evidence.json',proof)
    return proof


def wait_runtime(h):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        raw=h.host.runtime_evidence(now=110);proof=native.containers._json(raw)
        if proof['runtime_state']=='stopped':return raw
        # Bounded observation only, never start/retry/repair the original CID.
        time.sleep(.1)
    raise packets.PacketError('native-v6-wait-unknown')


def stage(root,name,request_sha):
    host=old_host()
    with host.private_directory(root):
        request=host.read(root,'run-request.json')
        if packets.digest(packets.canonical(request))!=request_sha:
            raise packets.PacketError('native-v6-request-drift')
        if type(request.get('executor_loss', False)) is not bool:
            raise packets.PacketError('native-v6-loss-contract')
        if native.inspect_tree(ROOT,HOST_FILES,private=True)!=host.read(root,'host-sources.json'):
            raise packets.PacketError('native-v6-captured-host-drift')
        native.validate_capsule(root/'capsule',request['capsule_ref'])
        control=host_control.NativeHostControl._from_captured_stage(root/'host-control',request['control_reference'])
        if control._read_session()['issuer_capture_sha256'] != packets.digest(packets.canonical(host.read(root,'host-sources.json'))):
            raise packets.PacketError('native-v6-control-capture-issuance-drift')
        # Only after full namespace/source admission; grants are explicitly synthetic.
        sys.path.insert(0,str(ROOT))  # This repository's tests is a namespace package.
        from tests import test_model_packet_native as fixture
        engine=RecordedDocker(request['endpoint'],root,name,host)
        if engine.executable_identity!=tuple(request['docker_identity']):
            raise packets.PacketError('native-v6-docker-preflight-drift')
        if name=='preflight':
            h=fixture.Harness(root/'state',engine,root/'capsule',request['capsule_ref'],control=control)
            ledger,state=h.current()
            if ledger['schema_version']!=6 or ledger['attempts'] or state['owner'] is not None:
                raise packets.PacketError('native-v6-preflight-state-drift')
            host.save(root,'preflight-result.json',dict(passed=True,scope='anonymous-native-v6-preflight-only',
                source_capture=True,image_policy=True,closed_backend=True,attempt_count=0,
                production_qualified=False,all_qualification_false=True))
        elif name=='producer':
            h=fixture.Harness(root/'state',engine,root/'capsule',request['capsule_ref'],control=control)
            h.acquire();h.chain();h.launch();wait_runtime(h);first=frame(host,h,root,'producer')
            h.observe()
            # Actual fixed 'new' postimage fails the declared final 'done' acceptance.
            # This is fixture quality evidence, never a real model quality qualification.
            if not request.get('executor_loss', False):h.failure()
            ledger,_=h.publish();c=ledger['checkpoint']
            late=None
            if request.get('executor_loss', False):
                # Seal the original generation's late message before losing
                # the executor. It is never rewritten for the successor.
                with h.store.locked() as fd:
                    original=ledger['governance']['records'][-1]
                    raw=packets.trust._read(fd,'lifecycle-'+original['record_sha256']+'.json',packets.MAX_LEDGER)
                rev=h.save('late-publish','publish',native.containers._json(raw)['payload'],runtime=True)
                late=dict(operation_id='late-publish',expected_revision=rev)
            else:
                h.finish(result='failed')
            host.save(root,'handoff.json',dict(request=h.request,execution=h.execution.decode(),
                checkpoint=c,immutable_refs=refs(h.store),first_native=first,
                control_reference_sha256=control.reference_sha256,late_result=late))
            if request.get('executor_loss', False):
                host.save(root,name+'-host-observations.json',control.samples)
                # Deliberate loss after durable C; no finally, owner release or
                # reliance on this process terminating every writer it started.
                os._exit(EXECUTOR_LOSS_EXIT)
        elif name=='consumer':
            waited=host.read(root,'producer-waited.json')
            validate_stage_wait(request,'producer',host.read(root,'producer-started.json'),waited)
            saved=host.read(root,'handoff.json')
            if saved['control_reference_sha256'] != control.reference_sha256:
                raise packets.PacketError('native-v6-handoff-control-drift')
            h=fixture.Harness.reopen(root/'state',engine,root/'capsule',request['capsule_ref'],saved,control=control)
            before,state=h.current()
            recovery=None
            if request.get('executor_loss', False):
                if (before['checkpoint']!=saved['checkpoint'] or state['owner'] is None
                        or state['terminal'] or before['attempts'][-1]['status']!='published'
                        or before['generation']!=1 or state['owner']['attempt_id']!=saved['request']['attempt_id']
                        or state['owner']['generation']!=1 or saved['late_result']!={
                            'operation_id':'late-publish','expected_revision':before['revision']}
                        or any(refs(h.store).get(k)!=v for k,v in saved['immutable_refs'].items())):
                    raise packets.PacketError('native-v6-loss-checkpoint-or-owner-drift')
                # Original descriptor/execution and fresh physical readback are
                # checked by existing lifecycle; process exit is not stop proof.
                h.observe('lost')
                h.failure(kind='service',cause='retriable-service',defect_id='executor-loss-after-checkpoint')
                h.finish('lost',result='failed')
                recovered,_=h.current()
                recovery=dict(executor_exit=waited['exit_code'],stderr_eof=True,
                    checkpoint_preserved=recovered['checkpoint']==saved['checkpoint'],
                    owner_epoch=state['owner']['epoch'],runtime_revalidated=True)
                before,state=h.current()
            if before['checkpoint']!=saved['checkpoint'] or state['owner'] is not None or state['terminal']:
                raise packets.PacketError('native-v6-handoff-owner-conflict')
            h.acquire('2');h.chain('2');ledger,state=h.current();attempt=ledger['attempts'][-1]
            if recovery is not None:
                calls=engine.transcript_count
                with h.store.locked() as fd:
                    try:
                        with h.host._lease(fd,ledger['attempts'][0],action='export'):pass
                    except flow.lifecycle.LifecycleError as error:
                        if str(error)!='native-lease-owner-or-phase-drift':raise
                    else:raise packets.PacketError('native-v6-old-generation-export-accepted')
                if engine.transcript_count!=calls:
                    raise packets.PacketError('native-v6-old-generation-export-effects')
                recovery['old_generation_export_rejected']=True
            with h.store.locked() as fd:
                with h.host._lease(fd,attempt) as lease:
                    preimage=lease.driver()._walk(lease.physical_binding(),lease.descriptor()[1]['physical_descriptor'])
            if preimage!={'example.txt':b'new\n','remove.txt':b'delete\n'} or attempt['predecessor_sha256']!=saved['checkpoint']:
                raise packets.PacketError('native-v6-successor-preimage-drift')
            h.launch('2');wait_runtime(h);second=frame(host,h,root,'consumer');h.observe('2');ledger,_=h.publish('2')
            if second['cid']==saved['first_native']['cid']:
                raise packets.PacketError('native-v6-successor-runtime-reused')
            if ledger['checkpoint']==saved['checkpoint']:
                raise packets.PacketError('native-v6-successor-checkpoint-reused')
            ledger,state=h.finish('2');after=refs(h.store)
            if (not state['terminal'] or state['owner'] is not None or ledger['generation']!=2
                    or len(state['events'])!=1 or state['correction_rounds']!=0
                    or [a['status'] for a in ledger['attempts']]!=['failed','completed']
                    or any(after.get(k)!=v for k,v in saved['immutable_refs'].items())):
                raise packets.PacketError('native-v6-final-journal-drift')
            replay_before=ledger
            h.host.launch_reserved('launch2',expected_revision=0,now=110)
            if h.current()[0]!=replay_before:raise packets.PacketError('native-v6-launch-reconcile-wrote')
            if recovery is not None:
                calls=engine.transcript_count
                try:
                    h.host.publish(saved['late_result']['operation_id'],
                        expected_revision=saved['late_result']['expected_revision'],now=110)
                except flow.lifecycle.LifecycleError as error:
                    if str(error)!='lifecycle-revision-conflict':raise
                else:raise packets.PacketError('native-v6-late-result-accepted')
                if h.current()[0]!=ledger or engine.transcript_count!=calls:
                    raise packets.PacketError('native-v6-late-result-effects')
                recovery.update(late_result_rejected=True,late_result_effects=0)
            host.save(root,'result.json',dict(passed=True,checkpoint=saved['checkpoint'],
                successor_checkpoint=ledger['checkpoint'],predecessor=attempt['predecessor_sha256'],
                immutable_refs_preserved=True,terminal=True,generation=2,
                quality_events=0 if recovery is not None else 1,
                service_events=1 if recovery is not None else 0,correction_rounds=0,
                first_native=saved['first_native'],second_native=second,all_qualification_false=True,
                authority='fixed-synthetic-reader',production_qualified=False,
                control_reference_sha256=control.reference_sha256,live_host_control=True,
                service_elapsed_qualified=False,executor_loss_recovery=recovery))
        else:raise packets.PacketError('native-v6-stage-invalid')
        host.save(root,name+'-host-observations.json',control.samples)


def run(args):
    if args.preflight_only and args.executor_loss:
        raise packets.PacketError('native-v6-loss-requires-execution')
    host=old_host();previous=os.umask(0o077)
    try:
        with host.private_directory(args.evidence_root):
            validate_host_inventory()
            root=pathlib.Path(tempfile.mkdtemp(prefix='model-native-v6-',dir=args.evidence_root))
        with host.private_directory(root) as root_fd:
            (root/'state').mkdir(mode=0o700)
            capsule=host.capture(root,args.binary_path);captured=host_capture(host,root)
            engine=RecordedDocker(args.endpoint,root,'coordinator',host)
            (root/'state/packets').mkdir(mode=0o700)
            store=packets.PacketStore(root/'state/packets','packet-native-v6');store.prepare('a'*64)
            backend=flow.NativeBackend(store,endpoint='unix:///fixed.sock',image_id=native.IMAGE,
                capture_root=root/'capsule',capture_ref=capsule,opt_in=True,_engine=engine)
            objective=dict(repository=str(root/'state'),task_id='T1',scope='fixed-native-two-attempt',
                acceptance_sha256=packets.digest(flow.FINAL_PATCH),authority_id='authority')
            (root/'host-control').mkdir(mode=0o700)
            command=[sys.executable,'-I','-S','-B',str(root/'trusted-host/scripts/verify-model-native-governance.py')]
            environment={'PATH':str(pathlib.Path(engine.executable).parent)+os.pathsep+os.defpath,'HOME':str(root),'LC_ALL':'C'}
            with host_control.CoordinatorSession(root/'host-control',store,backend.mode(),
                    packets.digest(packets.canonical(objective)),packets.digest(packets.canonical(captured)),
                    ttl_seconds=SESSION_TTL_SECONDS) as session:
                request=dict(schema_version=1,endpoint=args.endpoint,capsule_ref=capsule,
                    docker_identity=list(engine.executable_identity),control_reference=session.reference,
                    executor_loss=args.executor_loss)
                host.save(root,'run-request.json',request);digest=packets.digest(packets.canonical(request))
                stages=('preflight',) if args.preflight_only else ('producer','consumer')
                for name in stages:
                    host.run_stage(root,name,command+['_stage',name,str(root),digest],environment,
                        STAGE_WAIT_SECONDS[name],root_fd=root_fd)
                    waited=host.read(root,name+'-waited.json')
                    validate_stage_wait(request,name,host.read(root,name+'-started.json'),waited)
                result=host.read(root,'preflight-result.json' if args.preflight_only else 'result.json');result['fixture']=str(root)
            if not args.preflight_only:
                result['scope']=('anonymous-native-v6-executor-loss-after-checkpoint'
                    if args.executor_loss else 'anonymous-native-v6-two-attempt-governance')
            for name in ('production','native','runtime','adapter','isolation','startup','n1','n2','n3','n4'):
                result[name+'_qualified']=False
            print(packets.canonical(result).decode())
            return 0
    finally:os.umask(previous)


def main():
    if sys.argv[1:2]==['_stage']:
        _,name,root,digest=sys.argv[1:];stage(pathlib.Path(root),name,digest);return 0
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opt-in',action='store_true',required=True)
    parser.add_argument('--preflight-only',action='store_true',help='Capture/import/image contract only; zero attempts or containers.')
    parser.add_argument('--executor-loss',action='store_true',help='Lose the executor after trusted C, before owner release; anonymous fixture only.')
    parser.add_argument('--evidence-root',type=pathlib.Path,required=True)
    parser.add_argument('--binary-path',type=pathlib.Path,required=True)
    parser.add_argument('--endpoint',required=True)
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
