#!/usr/bin/env python3
"""Opt-in fixed-worker N3-B1 Docker fixture; never production qualification.

Creates only UUID-named containers with an already-installed exact Python image.
No pull, stop, remove, daemon restart, existing-container inventory, provider,
credential, model dispatch, arbitrary argv/mount or source integration is exposed.
All resources and protected packet evidence are retained for independent review.
"""
import argparse
import copy
import json
import os
import pathlib
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/'skills/loop-engineering/scripts'))
import agent_qualification as trust
import model_packet_store as packets
import model_packet_supervisor as supervisors
import model_container_backend as containers


class FaultTransport:
    """One fixed lost-response fault; the underlying engine call is performed once."""
    def __init__(self, engine, fault=None):
        self.engine = engine; self.fault = fault; self.created = []; self.started = []; self.volumes=[]

    def identity(self):
        return self.engine.identity()

    def image(self, image_id):
        return self.engine.image(image_id)

    def inspect(self, cid):
        return self.engine.inspect(cid)

    def volume(self, name):
        return self.engine.volume(name)

    def archive(self,*argv,input_bytes=None):
        value=self.engine.archive(*argv,input_bytes=input_bytes)
        if self.fault=='bootstrap' and argv[2]=='-':
            self.fault=None
            raise OSError('synthetic-lost-bootstrap-response')
        return value

    def command(self, *argv):
        result = self.engine.command(*argv)
        operation = argv[:2]
        if operation == ('volume','create'):
            self.volumes.append(result.decode())
        if operation == ('container', 'create'):
            cid = result.decode(); packets._sha(cid); self.created.append(cid)
        elif operation == ('container', 'start'):
            self.started.append(argv[2])
        if operation == ('container', self.fault):
            self.fault = None
            raise OSError('synthetic-lost-response')
        return result


def run_oneshot(args,fixture,receipt,transports):
    receipt['scope']='synthetic-root-latch-container-backend-only'
    receipt['qualification_identity']={'backend_sha256':containers.CONTRACT_SHA256,
        'launcher_sha256':containers.launcher.contract_digest(),'archive_sha256':containers.ARCHIVE_CONTRACT_SHA256,
        'packet_store_sha256':packets.digest(pathlib.Path(packets.__file__).read_bytes()),
        'supervisor_sha256':packets.digest(pathlib.Path(supervisors.__file__).read_bytes()),
        'independent_review':'pending-for-this-scope'}
    receipt['limitations']=['fixed synthetic recipes only; no real model/provider/production registry',
        'trusted Docker administrator excluded; no daemon restart/cleanup/source integration',
        'single-use body requires claim+completion+descriptor+volume+bootstrap receipt and physical stop']
    def backend(store,worker='edit',fault=None,launcher_fault='none'):
        engine=FaultTransport(containers.LocalDocker(args.endpoint,fixture),fault); transports.append(engine)
        value=containers.OneShotSyntheticContainerBackend(store,endpoint=args.endpoint,image_id=args.image,
            worker=worker,opt_in=True,_engine=engine,launcher_fault=launcher_fault)
        original_inspect=value.inspect
        def inspect(*params):
            try: return original_inspect(*params)
            except Exception as error:
                diagnostic={'failure_class':type(error).__name__,'reason':str(error)[:160]}
                events=receipt.setdefault('bounded_diagnostics',[])
                if diagnostic not in events and len(events)<16: events.append(diagnostic)
                raise
        value.inspect=inspect
        return value,engine
    def supervisor(store,value):
        return supervisors.PacketSupervisor(store,value,host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256)
    def store_for(case):
        store=packets.PacketStore(fixture,case+'-'+uuid.uuid4().hex); store.prepare(packets.digest(case.encode())); return store
    def start(store,value,attempt='attempt',revision=0):
        return value.start(attempt,'a'*64,'b'*64,expected_revision=revision,source_sha256=containers.source_digest(),scope_sha256='c'*64,acceptance_sha256='d'*64)
    def stopped(engine,descriptor):
        deadline=time.monotonic()+8
        while True:
            state=engine.inspect(descriptor['container_id'])['State']
            if state['Status']=='exited' and state['Running'] is False and state['Pid']==0: return state
            if time.monotonic()>deadline: raise packets.PacketError('fixture-stop-not-established')
            time.sleep(.1)
    cases=[('edit','edit',None,'none'),('add-update','add-update',None,'none'),('noop','noop',None,'none'),
        ('background','background',None,'none'),('privileges','privileges',None,'none'),
        ('create-lost','edit','create','none'),('bootstrap-lost','edit','bootstrap','none'),
        ('start-lost','edit','start','none'),('start-lost-restart','edit','start','none'),
        ('claim-crash','edit',None,'claim-created'),('export-lost','edit',None,'none')]
    for case,worker,fault,launcher_fault in cases:
        store=store_for(case); value,engine=backend(store,worker,fault,launcher_fault); sup=supervisor(store,value)
        lost_export=[case=='export-lost']
        if lost_export[0]:
            original=value.export_patch
            def export(*params):
                result=original(*params)
                if lost_export[0]: lost_export[0]=False; raise OSError('synthetic-lost-export-response')
                return result
            value.export_patch=export
        initial=start(store,sup)
        fresh,fresh_engine=backend(store,worker,launcher_fault=launcher_fault); rebuilt=supervisor(store,fresh)
        record=store.supervisor_snapshot('attempt')[1]
        if case=='create-lost':
            result=rebuilt.reconcile('attempt')
            passed=result['outcome']=='unknown' and record['runtime_descriptor_sha256'] is None and not engine.started
        elif case=='bootstrap-lost':
            result=rebuilt.reconcile('attempt')
            passed=result['outcome']=='unknown' and record['bootstrap']['stage']=='intent' and not engine.started
        else:
            descriptor=store.read_runtime_descriptor('attempt'); state=stopped(engine,descriptor)
            if case=='start-lost-restart':
                # Deliberate negative against only this own UUID: second launcher
                # must exit before body even though RestartCount may remain zero.
                before=containers.archive.read_control_file(engine.archive('container','cp',descriptor['container_id']+':/control/claim.json','-'),'claim.json')
                engine.command('container','start',descriptor['container_id']); state=stopped(engine,descriptor)
                after=containers.archive.read_control_file(engine.archive('container','cp',descriptor['container_id']+':/control/claim.json','-'),'claim.json')
                passed=state['ExitCode']==73 and before==after
            if case=='export-lost' and lost_export[0]: sup.reconcile('attempt')
            result=rebuilt.reconcile('attempt')
            if case in {'claim-crash','start-lost-restart'}:
                passed=(case=='claim-crash' or passed) and result['outcome']=='unknown' and store.supervisor_snapshot('attempt')[0]['checkpoint'] is None
            else:
                passed=result['outcome']=='integration-candidate' and len(engine.created)==len(engine.started)==1
                if passed:
                    passed=rebuilt.admit_candidate('attempt',source_sha256=containers.source_digest(),scope_sha256='c'*64,acceptance_sha256='d'*64)==result
                    files=fresh._walk(record['binding'],descriptor)
                    if case=='edit': passed=passed and files=={'example.txt':b'new\n','added.txt':b'added\n'}
                    if case=='add-update': passed=passed and files=={**containers.BASELINE,'example.txt':b'new\n','added.txt':b'added\n'}
                    if case=='noop': passed=passed and result['patch']==b''
                    if case=='background':
                        time.sleep(2.1); files=fresh._walk(record['binding'],descriptor)
                        passed=passed and files.get('background-started.txt')==b'active\n' and 'late.txt' not in files
                    if case=='privileges':
                        for name in ['privileges.json','grandchild.json']:
                            audit=containers.archive.read_control_json(files[name])
                            passed=passed and audit['uid']==audit['gid']==[65534]*3 and not audit['groups'] and not audit['fds'] and audit['control_denied'] is True and audit['nnp']=='1' and all(int(item,16)==0 for item in audit['caps'].values())
        passed=passed and not fresh_engine.created and not fresh_engine.started and not fresh_engine.volumes
        receipt['cases'][case]={'passed':passed,'initial_outcome':initial['outcome'],'result_outcome':result['outcome'],'packet_id':store.packet_id,'record_schema':record['schema_version']}
        if not passed: raise packets.PacketError('synthetic-one-shot-case-failed')
    # Running old root launcher/worker remains isolated; successor owns new volume.
    store=store_for('quarantine'); old,old_engine=backend(store,'hold'); oldsup=supervisor(store,old)
    initial=start(store,oldsup); ledger,record=store.supervisor_snapshot('attempt'); descriptor=store.read_runtime_descriptor('attempt')
    private=packets.PacketStore(fixture,store.packet_id,_trusted_isolation_adapters={'fixture':old.isolation_adapter(record['binding'],descriptor)})
    isolated=private.quarantine('attempt',expected_revision=ledger['revision'],isolation_adapter_id='fixture')
    running=old_engine.inspect(descriptor['container_id'])['State']['Running'] is True
    next_value,next_engine=backend(private,'add-update'); nextsup=supervisor(private,next_value)
    result=start(private,nextsup,'successor',isolated['revision']); stopped(next_engine,private.read_runtime_descriptor('successor'))
    result=nextsup.reconcile('successor'); rejected=False
    try: oldsup.reconcile('attempt')
    except packets.PacketError: rejected=True
    passed=initial['outcome']=='unknown' and running and rejected and result['outcome']=='integration-candidate' and not packets.PACKET_ISOLATION_ADAPTERS
    receipt['cases']['quarantine']={'passed':passed,'old_running':running,'old_stop_claimed':False,'old_result_rejected':rejected,'packet_id':store.packet_id}
    if not passed: raise packets.PacketError('synthetic-one-shot-quarantine-failed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic-fixed-worker', action='store_true', required=True)
    parser.add_argument('--one-shot',action='store_true',help='fixed root-latch synthetic fixture; never production')
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--evidence-root', required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    root_fd = trust._directory(args.evidence_root)
    try:
        if os.fstat(root_fd).st_mode & 0o077:
            parser.error('evidence root must already be private mode 0700')
    finally:
        os.close(root_fd)
    fixture = pathlib.Path(tempfile.mkdtemp(prefix='model-container-backend-', dir=args.evidence_root))
    fixture.chmod(0o700)
    receipt = {'schema_version':1, 'scope':'synthetic-fixed-worker-container-backend-only',
        'production_qualified':False, 'provider_contacted':False, 'source_integrated':False,
        'fixture':str(fixture), 'image_id':args.image, 'execution_outcome':'unknown',
        'cases':{}, 'containers_retained':[], 'limitations':[
            'no daemon/Desktop restart, cleanup, production registry or real model dispatch',
            'fixed synthetic file recipes only; no credential broker or tool bridge qualification',
            'running quarantine proves isolation only, never writer stopped',
            'shared daemon has no original-execution qualifier; all candidates stay unknown',
            'StartedAt/RestartCount cannot qualify same-CID manual restart; export is blocked']}
    transports = []
    sentinel = fixture/'parent-sentinel'; sentinel.write_text('parent-unchanged\n'); sentinel.chmod(0o600)

    def backend_for(store, worker='edit', fault=None):
        transport = FaultTransport(containers.LocalDocker(args.endpoint, fixture), fault)
        transports.append(transport)
        backend = containers.SyntheticContainerBackend(store, endpoint=args.endpoint, image_id=args.image,
            worker=worker, opt_in=True, _engine=transport)
        return backend, transport

    def supervisor_for(store, backend):
        return supervisors.PacketSupervisor(store, backend, host_id=backend.host_id,
            backend_id=backend.backend_id, policy_sha256=backend.policy_sha256)

    def new_store(case):
        store = packets.PacketStore(fixture, case+'-'+uuid.uuid4().hex)
        store.prepare(packets.digest(packets.canonical({'scope':receipt['scope'], 'case':case})))
        return store

    def start(store, supervisor, attempt='attempt', revision=0):
        return supervisor.start(attempt, 'a'*64, 'b'*64, expected_revision=revision,
            source_sha256=containers.source_digest(), scope_sha256='c'*64, acceptance_sha256='d'*64)

    def reconcile(supervisor, attempt='attempt'):
        return supervisor.reconcile(attempt)

    def await_physical_stop(transport, descriptor):
        deadline = time.monotonic()+8
        while True:
            value = transport.inspect(descriptor['container_id'])
            state = value['State']
            if state['Status'] == 'exited' and state['Running'] is False and state['Pid'] == 0:
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(.1)

    try:
        if args.one_shot:
            run_oneshot(args,fixture,receipt,transports)
            receipt['execution_outcome']='measured-synthetic-one-shot-cases-passed'
            return 0
        for case, worker, fault in [('edit','edit',None), ('noop','noop',None),
                                   ('background','background',None), ('create-lost','edit','create'),
                                   ('start-lost','edit','start'), ('export-blocked','edit',None)]:
            store = new_store(case); backend, transport = backend_for(store, worker, fault)
            supervisor = supervisor_for(store, backend)
            if case == 'export-blocked':
                def forbidden_export(*args):
                    raise AssertionError('unqualified execution must not export')
                backend.export_patch = forbidden_export
            initial = start(store, supervisor)
            fresh_backend, fresh_transport = backend_for(store, worker)
            fresh_supervisor = supervisor_for(store, fresh_backend)
            if case == 'create-lost':
                result = fresh_supervisor.reconcile('attempt')
                record = store.supervisor_snapshot('attempt')[1]
                passed = (initial['outcome'] == result['outcome'] == 'unknown'
                    and record['runtime_descriptor_sha256'] is None and len(transport.created) == 1
                    and not transport.started and not fresh_transport.created and not fresh_transport.started)
            else:
                descriptor = store.read_runtime_descriptor('attempt')
                physically_stopped = await_physical_stop(fresh_transport, descriptor)
                result = reconcile(fresh_supervisor)
                record = store.supervisor_snapshot('attempt')[1]
                passed = (result['outcome'] == 'unknown' and physically_stopped
                    and len(transport.created) == len(transport.started) == 1
                    and descriptor['container_id'] == transport.created[0]
                    and not fresh_transport.created and not fresh_transport.started
                    and store.supervisor_snapshot('attempt')[0]['checkpoint'] is None
                    and not (fixture/store.packet_id/('backend-'+record['binding']['runtime_id']+'.export')).exists())
                try:
                    fresh_supervisor.admit_candidate('attempt', source_sha256=containers.source_digest(),
                        scope_sha256='c'*64, acceptance_sha256='d'*64)
                except packets.PacketError:
                    pass
                else:
                    passed = False
                if case == 'edit':
                    files = fresh_backend._walk(record['binding'], descriptor)
                    passed = passed and files == {'example.txt':b'new\n', 'added.txt':b'added\n'}
                if case == 'noop':
                    passed = passed and fresh_backend._walk(record['binding'], descriptor) == containers.BASELINE
                if case == 'background':
                    time.sleep(2.1)
                    files = fresh_backend._walk(record['binding'], descriptor)
                    passed = passed and files.get('background-started.txt') == b'active\n' and 'late.txt' not in files
                if case == 'start-lost':
                    passed = passed and any(event['reason'] == 'launch-reply-unknown' for event in record['observations'])
            receipt['cases'][case] = {'passed':passed, 'initial_outcome':initial['outcome'], 'result':result,
                'packet_id':store.packet_id, 'record_schema':record['schema_version']}
            if not passed:
                raise packets.PacketError('synthetic-case-failed')
        # A live old writer remains private while a successor completes. No stop.
        store = new_store('quarantine'); old_backend, old_transport = backend_for(store, 'hold')
        old_supervisor = supervisor_for(store, old_backend); initial = start(store, old_supervisor)
        ledger, record = store.supervisor_snapshot('attempt'); descriptor = store.read_runtime_descriptor('attempt')
        adapter = old_backend.isolation_adapter(record['binding'], descriptor)
        private = packets.PacketStore(fixture, store.packet_id, _trusted_isolation_adapters={'fixture':adapter})
        isolated = private.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fixture')
        old_running = old_transport.inspect(descriptor['container_id'])['State']['Running'] is True
        next_backend, next_transport = backend_for(private)
        next_supervisor = supervisor_for(private, next_backend)
        result = start(private, next_supervisor, 'successor', isolated['revision'])
        next_descriptor = private.read_runtime_descriptor('successor')
        next_stopped = await_physical_stop(next_transport, next_descriptor)
        result = reconcile(next_supervisor, 'successor')
        late_rejected = False
        try:
            old_supervisor.reconcile('attempt')
        except packets.PacketError:
            late_rejected = True
        passed = (initial['outcome'] == 'unknown' and old_running and late_rejected
            and isolated['attempts'][-1]['execution_outcome'] == 'unknown'
            and result['outcome'] == 'unknown' and next_stopped
            and private.supervisor_snapshot('successor')[0]['checkpoint'] is None
            and not packets.PACKET_ISOLATION_ADAPTERS)
        receipt['cases']['quarantine'] = {'passed':passed, 'old_running_at_quarantine':old_running,
            'old_stop_claimed':False, 'late_result_rejected':late_rejected, 'packet_id':store.packet_id}
        if not passed or sentinel.read_text() != 'parent-unchanged\n':
            raise packets.PacketError('synthetic-quarantine-or-sentinel-failed')
        receipt['execution_outcome'] = 'measured-synthetic-containment-candidate-blocked'
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        receipt['failure_class'] = type(error).__name__
        receipt['failure_reason'] = str(error)[:160]
        return 2
    finally:
        receipt['volumes_retained'] = [name for transport in transports for name in transport.volumes]
        receipt['containers_retained'] = [cid for transport in transports for cid in transport.created]
        path = fixture/'backend-evidence.json'
        with path.open('w') as stream:
            json.dump(receipt, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        print(json.dumps({'evidence':str(path), 'execution_outcome':receipt['execution_outcome'],
            'cases':{name:value['passed'] for name,value in receipt['cases'].items()},
            'production_qualified':False, 'containers_retained':len(receipt['containers_retained'])}))


if __name__ == '__main__':
    sys.exit(main())
