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
    parser.add_argument('--endpoint',required=True); parser.add_argument('--image',required=True)
    parser.add_argument('--evidence-root',required=True,type=pathlib.Path)
    args=parser.parse_args(argv)
    if not args.synthetic_qualified_container_fixture: parser.error('explicit synthetic fixture opt-in required')
    run(args)
    return 0


if __name__=='__main__': raise SystemExit(main())
