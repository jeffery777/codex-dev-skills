#!/usr/bin/env python3
"""Opt-in B2 synthetic sole-integrator fixture; creates only private UUID sources.

Fixed one-shot recipes, installed exact image, own UUID containers/volumes only.
Never accepts an existing repository, model/provider, arbitrary argv, approved
JSON, production registry, cleanup, retry apply or rollback. Resources retained.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'skills/loop-engineering/scripts'))
import agent_qualification as trust
import model_packet_store as packets
import model_container_backend as containers
import model_packet_supervisor as supervisors
import model_packet_integrator as integration


class RecordingEngine:
    def __init__(self,engine):
        self.engine=engine; self.containers=[]; self.volumes=[]
    def identity(self): return self.engine.identity()
    def image(self,image): return self.engine.image(image)
    def inspect(self,cid): return self.engine.inspect(cid)
    def volume(self,name): return self.engine.volume(name)
    def archive(self,*args,input_bytes=None): return self.engine.archive(*args,input_bytes=input_bytes)
    def command(self,*args):
        raw=self.engine.command(*args)
        if args[:2]==('container','create'): self.containers.append(raw.decode())
        if args[:2]==('volume','create'): self.volumes.append(raw.decode())
        return raw


def await_candidate(supervisor,store,engine,attempt,candidate):
    """Bounded read-only stop poll; physical stop never qualifies a candidate.

    Reconcile once after stop, preserving all supervisor proof and policy gates.
    No retry of launch, bootstrap or apply; no new read beyond 8s/80 reads.
    Each synchronous inspect retains the transport's own bounded timeout;
    results received after the polling deadline cannot advance the candidate.
    """
    if candidate.get('outcome')!='unknown' or candidate.get('reason')!='runtime-proof-unavailable':
        return candidate
    descriptor=store.read_runtime_descriptor(attempt)
    deadline=time.monotonic()+8
    for _ in range(80):
        if time.monotonic()>=deadline: return candidate
        observed=engine.inspect(descriptor['container_id'])
        if (type(observed) is not dict or observed.get('Id')!=descriptor['container_id']
                or observed.get('Created')!=descriptor['created_at']):
            raise packets.PacketError('fixture-container-identity-drift')
        state=observed.get('State')
        if type(state) is not dict: raise packets.PacketError('fixture-container-state-unavailable')
        remaining=deadline-time.monotonic()
        if remaining<=0: return candidate
        if (state.get('Status')=='exited' and state.get('Running') is False
                and type(state.get('Pid')) is int and state['Pid']==0):
            return supervisor.reconcile(attempt)
        time.sleep(min(.1,remaining))
    return candidate


def live_deadline(deadline):
    if time.monotonic()>=deadline:raise packets.PacketError('fixture-live-readback-expired')


def running_control(backend,binding,descriptor,deadline):
    """Bounded USTAR inventory; completion absence alone is not liveness."""
    live_deadline(deadline)
    raw=backend.engine.archive('container','cp',descriptor['container_id']+':/control','-')
    live_deadline(deadline)
    archive=containers.archive
    if type(raw) is not bytes or not 1536<=len(raw)<=archive.MAX_ARCHIVE or len(raw)%512:
        raise packets.PacketError('fixture-live-control-unavailable')
    offset=0;entries={};directory=False
    while offset<len(raw):
        if not any(raw[offset:offset+512]):
            if len(raw)-offset<1024 or any(raw[offset:]):raise packets.PacketError('fixture-live-control-unavailable')
            break
        header=raw[offset:offset+512]
        size=archive._octal(header[124:136])
        end=offset+512+((size+511)//512)*512
        if size>archive.MAX_JSON or end>len(raw):raise packets.PacketError('fixture-live-control-unavailable')
        checked,payload=archive._entry(raw[offset:end]+b'\0'*1024)
        name=archive._text(checked[:100]);mode=archive._octal(checked[100:108])
        if name in (b'control',b'control/'):
            if directory or checked[156:157]!=b'5' or payload or mode not in (0o700,0o755):
                raise packets.PacketError('fixture-live-control-unavailable')
            directory=True
        elif name in (b'control/input.json',b'control/claim.json'):
            if name in entries or checked[156:157] not in (b'0',b'\0') or mode!=0o600 or not payload:
                raise packets.PacketError('fixture-live-control-unavailable')
            entries[name]=payload
        else:raise packets.PacketError('fixture-worker-completion-or-unknown-control')
        offset=end
        if len(entries)>2:raise packets.PacketError('fixture-live-control-unavailable')
    else:raise packets.PacketError('fixture-live-control-unavailable')
    if not directory or set(entries)!={b'control/input.json',b'control/claim.json'}:
        raise packets.PacketError('fixture-live-control-unavailable')
    input_raw=entries[b'control/input.json'];claim_raw=entries[b'control/claim.json']
    input_value=archive.read_control_json(input_raw)
    expected=packets.canonical({'schema_version':1,'input_sha256':packets.digest(input_raw),'input':input_value})
    live_deadline(deadline)
    expected_input=backend.bootstrap_input(binding,descriptor)
    live_deadline(deadline)
    if input_raw!=expected_input or claim_raw!=expected:
        raise packets.PacketError('fixture-live-control-binding-drift')
    return {'input_sha256':packets.digest(input_raw),'claim_sha256':packets.digest(claim_raw),
        'archive_sha256':packets.digest(raw),'completion_absent':True}


def running_observation(backend,binding,descriptor,*,deadline=None):
    """Fixed one-child recipe only; running PID1 is not worker liveness."""
    if deadline is None:deadline=time.monotonic()+8
    live_deadline(deadline)
    observed=backend._observed(binding,descriptor)
    live_deadline(deadline)
    state=observed['State']
    if (state.get('Status')!='running' or state.get('Running') is not True
            or type(state.get('Pid')) is not int or state['Pid']<=0):
        raise packets.PacketError('fixture-old-writer-overlap-unavailable')
    live_deadline(deadline)
    raw=backend.engine.command('container','top',descriptor['container_id'],
        '-eo','pid,ppid,uid,stat,comm')
    live_deadline(deadline)
    if type(raw) is not bytes or not 0<len(raw)<=4096:
        raise packets.PacketError('fixture-worker-process-table-unavailable')
    try: lines=raw.decode('ascii').splitlines()
    except UnicodeError: raise packets.PacketError('fixture-worker-process-table-unavailable') from None
    if len(lines) not in (2,3) or lines[0].split()!=['PID','PPID','UID','STAT','COMMAND']:
        raise packets.PacketError('fixture-worker-process-table-unavailable')
    rows=[]
    for line in lines[1:]:
        fields=line.split()
        if (len(fields)!=5 or any(not re.fullmatch(r'0|[1-9][0-9]{0,9}',x) for x in fields[:3])
                or not re.fullmatch(r'[RSDITtW][<Nsl+L]*',fields[3]) or fields[4]!='python3'):
            raise packets.PacketError('fixture-live-worker-identity-unavailable')
        pid,ppid,uid=map(int,fields[:3])
        if not 0<pid<=2147483647 or not 0<=ppid<=2147483647:
            raise packets.PacketError('fixture-live-worker-identity-unavailable')
        rows.append({'pid':pid,'ppid':ppid,'uid':uid,'stat':fields[3],'command':fields[4]})
    parents=[x for x in rows if x['pid']==state['Pid'] and x['uid']==0]
    workers=[x for x in rows if x['ppid']==state['Pid'] and x['uid']==65534 and x['pid']!=state['Pid']]
    if len(parents)==1 and not workers and len(rows)==1:
        raise packets.PacketError('fixture-old-worker-starting-or-finished')
    if len(parents)!=1 or len(workers)!=1 or len({x['pid'] for x in rows})!=2:
        raise packets.PacketError('fixture-live-worker-identity-unavailable')
    # This hold recipe has exactly one forked worker, no replacement or forks.
    # Live child before/after bounds plus the same PID can establish overlap;
    # workspace bytes alone or absence of completion cannot establish liveness.
    if backend._walk(binding,descriptor).get('example.txt')!=b'holding\n':
        raise packets.PacketError('fixture-old-worker-phase-unavailable')
    live_deadline(deadline)
    control=running_control(backend,binding,descriptor,deadline)
    after=backend._observed(binding,descriptor)
    live_deadline(deadline)
    if after!=observed:raise packets.PacketError('fixture-live-readback-changed')
    return {'Id':observed['Id'],'Created':observed['Created'],
        'State':{key:state[key] for key in ('Status','Running','Pid')},
        'worker_pid':workers[0]['pid'],'process_table':raw.decode('ascii'),'control':control}


def checkpoint_overlap(args,root,engine):
    """S seals C; A stays isolated/live; B resumes C; only B integrates.

    Fixed recipes and synthetic host source only. No model, auth, cleanup,
    stop, inferred quiescence, production adapter or saved-lifecycle override.
    """
    source=integration.SyntheticSource.create(root)
    store=packets.PacketStore(root,'packet-checkpoint-overlap')
    store.prepare(packets.digest(packets.canonical({'scope':'checkpoint-overlap'})))
    requirements=source.requirements('add-update')
    def create(current,recipe):
        backend=containers.OneShotSyntheticContainerBackend(current,endpoint=args.endpoint,
            image_id=args.image,opt_in=True,worker=recipe,_engine=engine)
        supervisor=supervisors.PacketSupervisor(current,backend,host_id=backend.host_id,
            backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)
        return backend,supervisor
    seed,seed_supervisor=create(store,'add-update')
    candidate=seed_supervisor.start('seed','e'*64,'f'*64,expected_revision=0,**requirements)
    candidate=await_candidate(seed_supervisor,store,engine,'seed',candidate)
    if candidate.get('outcome')!='integration-candidate' or candidate.get('patch')!=integration.FIXED_PATCH:
        raise packets.PacketError('fixture-nonempty-checkpoint-unavailable')
    ledger,checkpoint=store.read_checkpoint(); checkpoint_id=ledger['checkpoint']
    if checkpoint!=integration.FIXED_PATCH: raise packets.PacketError('fixture-checkpoint-content-drift')
    with store.locked() as fd:
        checkpoint_manifest=trust._read(fd,checkpoint_id+'.json',packets.MAX_LEDGER)
    old,old_supervisor=create(store,'hold-overlap')
    pending=old_supervisor.start('old','e'*64,'f'*64,expected_revision=ledger['revision'],**requirements)
    if pending!={'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'old'}:
        raise packets.PacketError('fixture-old-writer-not-pending')
    ledger,record=store.supervisor_snapshot('old'); descriptor=store.read_runtime_descriptor('old')
    deadline=time.monotonic()+8; observations=[]
    for _ in range(80):
        if time.monotonic()>=deadline: raise packets.PacketError('fixture-old-worker-effect-unavailable')
        try:observed=running_observation(old,record['binding'],descriptor,deadline=deadline)
        except packets.PacketError as error:
            if str(error) not in ('fixture-old-worker-starting-or-finished','fixture-old-worker-phase-unavailable'):raise
            remaining=deadline-time.monotonic()
            if remaining<=0:raise packets.PacketError('fixture-old-worker-effect-unavailable') from None
            time.sleep(min(.1,remaining));continue
        if time.monotonic()>=deadline: raise packets.PacketError('fixture-old-worker-effect-unavailable')
        observations.append(observed); break
    else: raise packets.PacketError('fixture-old-worker-effect-unavailable')
    private=packets.PacketStore(root,store.packet_id,_trusted_isolation_adapters={
        'overlap':old.isolation_adapter(record['binding'],descriptor)})
    quarantined=private.quarantine('old',expected_revision=ledger['revision'],isolation_adapter_id='overlap')
    if quarantined['checkpoint']!=checkpoint_id: raise packets.PacketError('fixture-quarantine-checkpoint-drift')
    successor,next_supervisor=create(private,'noop')
    result=next_supervisor.start('successor','e'*64,'f'*64,
        expected_revision=quarantined['revision'],**requirements)
    result=await_candidate(next_supervisor,private,engine,'successor',result)
    if result.get('outcome')!='integration-candidate' or result.get('patch')!=checkpoint:
        raise packets.PacketError('fixture-successor-checkpoint-not-preserved')
    next_descriptor=private.read_runtime_descriptor('successor')
    for key in ('container_id','workspace_identity_sha256'):
        if descriptor[key]==next_descriptor[key]: raise packets.PacketError('fixture-successor-boundary-reused')
    if descriptor['control_volume']['name']==next_descriptor['control_volume']['name']:
        raise packets.PacketError('fixture-successor-boundary-reused')
    if result['binding']['predecessor_sha256']!=checkpoint_id:
        raise packets.PacketError('fixture-successor-predecessor-drift')
    if successor._walk(result['binding'],next_descriptor)!={**containers.BASELINE,
            'example.txt':b'new\n','added.txt':b'added\n'}:
        raise packets.PacketError('fixture-successor-content-drift')
    observations.append(running_observation(old,record['binding'],descriptor))
    if len({x['worker_pid'] for x in observations})!=1:
        raise packets.PacketError('fixture-old-worker-process-changed')
    with private.locked() as fd:
        if (trust._read(fd,checkpoint_id+'.json',packets.MAX_LEDGER)!=checkpoint_manifest
                or private._checkpoint_bytes(fd,checkpoint_id,private._read(fd))!=checkpoint):
            raise packets.PacketError('fixture-trusted-checkpoint-changed')
    governance=integration.FixtureGovernance(source)
    authority=governance.issue(next_supervisor,'successor',recipe='add-update')
    integrator=integration.PacketIntegrator(source,governance,next_supervisor)
    stale={}
    for name,operation in [('reconcile',lambda:old_supervisor.reconcile('old')),
            ('admit',lambda:old_supervisor.admit_candidate('old',**requirements)),
            ('publish',lambda:private.publish_checkpoint('old',checkpoint,result['evidence_sha256'])),
            ('integrate',lambda:integrator.integrate('old',authority,operation_id='stale'))]:
        try: operation()
        except packets.PacketError as error:
            expected={'integrate':'qualified-sealed-candidate-required',
                'publish':'packet-attempt-mismatch'}.get(name,'stale-writer-result-rejected')
            if str(error)!=expected: raise
            stale[name]=str(error)
        else: raise packets.PacketError('fixture-stale-writer-accepted')
    with source._locked() as (fd,_):
        if source.snapshot(fd)!=containers.BASELINE: raise packets.PacketError('fixture-stale-source-mutated')
    observations.append(running_observation(old,record['binding'],descriptor))
    if len({x['worker_pid'] for x in observations})!=1:
        raise packets.PacketError('fixture-old-worker-process-changed')
    integrated=integrator.integrate('successor',authority,operation_id='operation')
    if integrated['state']!='applied': raise packets.PacketError('fixture-successor-integration-unavailable')
    observations.append(running_observation(old,record['binding'],descriptor))
    if len({x['worker_pid'] for x in observations})!=1:
        raise packets.PacketError('fixture-old-worker-process-changed')
    with source._locked() as (fd,_):
        if source.snapshot(fd)!={**containers.BASELINE,'example.txt':b'new\n','added.txt':b'added\n'}:
            raise packets.PacketError('fixture-integrated-source-drift')
    with mock.patch.object(integrator,'_write_file',side_effect=AssertionError('replayed-source-write')):
        if integrator.reconcile('operation',authority)!=integrated:
            raise packets.PacketError('fixture-integrated-readback-drift')
    return {'passed':True,'old_stop_claimed':False,'old_running_observations':observations,
        'source':str(source.root),'source_descriptor_sha256':source.descriptor_sha256,
        'seed_checkpoint_sha256':checkpoint_id,'seed_patch_sha256':packets.digest(checkpoint),
        'successor_checkpoint_sha256':result['checkpoint_sha256'],
        'successor_patch_sha256':result['patch_sha256'],'runtime_evidence_sha256':result['evidence_sha256'],
        'authority_sha256':authority.sha,'old_descriptor':descriptor,'successor_descriptor':next_descriptor,
        'stale_rejections':stale,'integration':integrated,'packet':store.packet_id}


def run(args,*,_engine_factory=None):
    fd=trust._directory(args.evidence_root)
    try:
        if os.fstat(fd).st_mode&0o077: raise packets.PacketError('evidence-root-must-be-private')
    finally: os.close(fd)
    root=pathlib.Path(tempfile.mkdtemp(prefix='model-packet-integrator-',dir=args.evidence_root)); root.chmod(0o700)
    receipt={'schema_version':1,'scope':'synthetic-exclusive-source-sole-integrator','production_qualified':False,
        'fixture':str(root),'execution_outcome':'unknown','source_sha256':{},'cases':{},'containers_retained':[],'volumes_retained':[],
        'limitations':['synthetic-validation-and-review-fixture-artifacts-not-formal-code-review',
            'trusted-host-synchronous-nochildren-exclusive-fixture-only','advisory-lock-not-OS-isolation',
            'bounded-per-file-atomic-writes-not-multi-file-transaction','no-company-model-or-production-authority']}
    modules={'store':packets,'supervisor':supervisors,'backend':containers,'integrator':integration}
    for name,module in modules.items(): receipt['source_sha256'][name]=packets.digest(pathlib.Path(module.__file__).read_bytes())
    engine=RecordingEngine((_engine_factory(root) if _engine_factory else containers.LocalDocker(args.endpoint,root)))
    try:
        if getattr(args,'checkpoint_overlap_only',False):
            receipt['scope']='synthetic-live-quarantined-writer-checkpoint-sole-integrator'
            receipt['cases']['checkpoint-overlap']=checkpoint_overlap(args,root,engine)
            receipt['execution_outcome']='measured-synthetic-checkpoint-overlap-passed'
            return receipt
        for case in ['add-update','noop','intent-crash','write-intent-crash','mid-write','commit-crash','reply-lost','revoked-authority']:
            recipe='noop' if case=='noop' else 'add-update'
            source=integration.SyntheticSource.create(root); store=packets.PacketStore(root,'packet-'+case)
            store.prepare(packets.digest(packets.canonical({'scope':receipt['scope'],'case':case})))
            backend=containers.OneShotSyntheticContainerBackend(store,endpoint=args.endpoint,image_id=args.image,opt_in=True,worker=recipe,_engine=engine)
            supervisor=supervisors.PacketSupervisor(store,backend,host_id=backend.host_id,backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)
            requirements=source.requirements(recipe)
            candidate=supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**requirements)
            candidate=await_candidate(supervisor,store,engine,'attempt',candidate)
            if candidate['outcome']!='integration-candidate': raise packets.PacketError('fixture-candidate-unqualified')
            governance=integration.FixtureGovernance(source); authority=governance.issue(supervisor,'attempt',recipe=recipe)
            integrator=integration.PacketIntegrator(source,governance,supervisor)
            expected='applied'; initial='unknown'
            if case=='revoked-authority':
                governance.revoke(authority)
                try: integrator.integrate('attempt',authority,operation_id='operation')
                except packets.PacketError as error:
                    if str(error)!='source-authority-revoked': raise
                else: raise packets.PacketError('revocation-not-rejected')
                with source._locked() as (source_fd,_):
                    if source.snapshot(source_fd)!=containers.BASELINE: raise packets.PacketError('revoked-source-mutated')
                if 'integrations' in store.supervisor_snapshot('attempt')[0]: raise packets.PacketError('revocation-created-intent')
                result={'state':'rejected-revoked','effects':'none'}; expected='rejected-revoked'
            else:
                if case=='intent-crash':
                    target,method=store,'_start_integration_write'; fault=SystemExit('synthetic-crash-after-intent'); expected='not-applied'
                elif case=='write-intent-crash':
                    target,method=integrator,'_write_file'; fault=SystemExit('synthetic-crash-after-write-intent'); expected='unknown'
                elif case=='mid-write':
                    target,method=integrator,'_write_file'; original=integrator._write_file
                    def fault(fd,name,raw,pre):
                        if name=='example.txt': raise OSError('synthetic-mid-write')
                        return original(fd,name,raw,pre)
                    expected='unknown'
                elif case=='commit-crash':
                    target,method=store,'_finish_integration'; fault=SystemExit('synthetic-crash-before-result')
                elif case=='reply-lost':
                    target,method=store,'_finish_integration'; original=store._finish_integration
                    def fault(*argv):
                        original(*argv); raise SystemExit('synthetic-caller-lost-reply')
                else: target=None
                if target:
                    with mock.patch.object(target,method,side_effect=fault):
                        try: initial=integrator.integrate('attempt',authority,operation_id='operation')['state']
                        except SystemExit: initial='lost-reply-or-crash'
                else: initial=integrator.integrate('attempt',authority,operation_id='operation')['state']
                if case=='noop': expected='not-applied'
                # Fresh capability/backend/store; reconcile never reapplies source.
                reopened=integration.SyntheticSource.reopen(source.root,source.descriptor_sha256)
                fresh_store=packets.PacketStore(root,store.packet_id)
                fresh_backend=containers.OneShotSyntheticContainerBackend(fresh_store,endpoint=args.endpoint,image_id=args.image,opt_in=True,worker=recipe,_engine=engine)
                fresh_supervisor=supervisors.PacketSupervisor(fresh_store,fresh_backend,host_id=fresh_backend.host_id,backend_id=fresh_backend.backend_id,policy_sha256=fresh_backend.policy_sha256)
                fresh=integration.PacketIntegrator(reopened,integration.FixtureGovernance(reopened),fresh_supervisor)
                authority=fresh.governance.reopen_authority(authority.authority_id,authority.sha)
                with mock.patch.object(fresh,'_write_file',side_effect=AssertionError('reconcile-applied-source')):
                    result=fresh.reconcile('operation',authority)
                    if result['state']!=expected: raise packets.PacketError('fixture-reconciliation-outcome-mismatch')
                ledger,record,intent=fresh_store.integration_snapshot('operation')
                with fresh_store.locked() as packet_fd:
                    result_raw=trust._read(packet_fd,'integration-result-'+record['result_sha256']+'.json',65536)
                with reopened._locked() as (source_fd,_): image_sha=packets.digest(packets.canonical(integration._manifest(reopened.snapshot(source_fd))))
                try: fresh_store.claim('next','e'*64,'f'*64,expected_revision=ledger['revision'])
                except packets.PacketError as error:
                    if str(error)!='source-integration-next-claim-unqualified': raise
                else: raise packets.PacketError('unqualified-source-continuation-accepted')
                result={**result,'intent_sha256':record['intent_sha256'],'result_sha256':packets.digest(result_raw),
                    'observations':record['observations'],'actual_image_sha256':image_sha}
            receipt['cases'][case]={'passed':result['state']==expected,'initial':initial,'result':result,
                'source':str(source.root),'source_descriptor_sha256':source.descriptor_sha256,
                'checkpoint_sha256':candidate['checkpoint_sha256'],'patch_sha256':candidate['patch_sha256'],
                'runtime_evidence_sha256':candidate['evidence_sha256'],'authority_sha256':authority.sha,'packet':store.packet_id}
        receipt['execution_outcome']='measured-synthetic-sole-integrator-cases-passed'
    except Exception as error:
        receipt['failure_class']=type(error).__name__; receipt['failure_reason']=str(error)[:160]
        raise
    finally:
        receipt['containers_retained']=engine.containers; receipt['volumes_retained']=engine.volumes
        path=root/'integrator-evidence.json'
        with path.open('x') as stream: json.dump(receipt,stream,indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        print(json.dumps({'evidence':str(path),'execution_outcome':receipt['execution_outcome'],
            'cases':{name:value['passed'] for name,value in receipt['cases'].items()},'production_qualified':False}))
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-qualified-container-fixture',action='store_true',required=True)
    parser.add_argument('--checkpoint-overlap-only',action='store_true',help='fixed nonempty checkpoint/live quarantine/successor fixture only')
    parser.add_argument('--endpoint',required=True); parser.add_argument('--image',required=True)
    parser.add_argument('--evidence-root',required=True,type=pathlib.Path)
    args=parser.parse_args(argv)
    if not args.synthetic_qualified_container_fixture: parser.error('explicit synthetic fixture opt-in required')
    run(args)
    return 0


if __name__=='__main__': raise SystemExit(main())
