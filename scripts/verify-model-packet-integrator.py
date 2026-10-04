#!/usr/bin/env python3
"""Opt-in B2 synthetic sole-integrator fixture; creates only private UUID sources.

Fixed one-shot recipes, installed exact image, own UUID containers/volumes only.
Never accepts an existing repository, model/provider, arbitrary argv, approved
JSON, production registry, cleanup, retry apply or rollback. Resources retained.
"""
import argparse
import ast
import base64
import copy
import fcntl
import hashlib
import json
import os
import pathlib
import re
import select
import stat
import subprocess
import sys
import tempfile
import time
import uuid
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


# Fixed private helpers only. These references are host-generated, never CLI APIs.
_RELOAD_MODULES = ('agent_qualification', 'model_packet_store', 'model_packet_supervisor',
    'model_packet_integrator', 'model_container_backend', 'model_container_launcher',
    'model_control_archive', 'model_packet_governance', 'agent_routing', 'model_failover',
    'profile_preflight', 'local_model_mapping')
_RELOAD_RUNNER = 'scripts/verify-model-packet-integrator.py'
_RELOAD_FILES = (_RELOAD_RUNNER,) + tuple('skills/loop-engineering/scripts/'+name+'.py'
    for name in _RELOAD_MODULES)
_RELOAD_LIMIT = 1048576
_RELOAD_TRACE_LIMIT = 8388608
_RELOAD_HELPER_LIMIT = 65536
_RELOAD_PACKET = 'packet-controller-reload'
_RELOAD_PENDING = {'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'old'}


def _reload_identity(value):
    return [value.st_dev,value.st_ino,value.st_uid,value.st_mode,value.st_nlink,
        value.st_size,value.st_mtime_ns,value.st_ctime_ns]


def _reload_read(root, relative, limit=_RELOAD_LIMIT, *, private=True):
    """No-follow every component; bounded bytes and stable named file identity."""
    parts=pathlib.PurePosixPath(relative).parts
    if (not parts or pathlib.PurePosixPath(relative).is_absolute()
            or any(part in ('.','..') for part in parts) or '/'.join(parts)!=relative):
        raise packets.PacketError('reload-private-reference-invalid')
    if private:directory=trust._directory(root)
    else:
        root=pathlib.Path(root)
        if not root.is_absolute() or '..' in root.parts:raise packets.PacketError('reload-source-root-invalid')
        directory=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
        try:
            for index,part in enumerate(root.parts[1:]):
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                os.close(directory);directory=child
                trust._check(os.fstat(directory),directory=True,ancestor=index<len(root.parts)-2)
        except BaseException:os.close(directory);raise
    fd=None
    try:
        for part in parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
            value=os.fstat(directory)
            if value.st_uid!=os.getuid() or value.st_mode & (0o077 if private else 0o022):
                raise packets.PacketError('reload-directory-untrusted')
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        before=os.fstat(fd)
        # PacketStore retains its O_EXCL staging hardlink as crash evidence.
        # Permit that fixed immutable layout, binding the observed link count too.
        links={1,2} if (private and len(parts)==2 and parts[0]==_RELOAD_PACKET
            and re.fullmatch(r'(?:runtime-)?[a-f0-9]{64}\.(?:json|patch)',parts[1])) else {1}
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid()
                or before.st_nlink not in links or before.st_mode & (0o077 if private else 0o022)
                or before.st_size>limit):
            raise packets.PacketError('reload-regular-file-required')
        raw=bytearray()
        while len(raw)<=limit:
            chunk=os.read(fd,min(65536,limit+1-len(raw)))
            if not chunk:break
            raw.extend(chunk)
        after=os.fstat(fd);named=os.stat(parts[-1],dir_fd=directory,follow_symlinks=False)
        if (len(raw)>limit or _reload_identity(before)!=_reload_identity(after)
                or _reload_identity(after)!=_reload_identity(named)):
            raise packets.PacketError('reload-file-identity-drift')
        return bytes(raw),{'relative':relative,'sha256':packets.digest(raw),
            'identity':_reload_identity(after)}
    finally:
        if fd is not None:os.close(fd)
        os.close(directory)


def _reload_json(raw):
    return json.loads(raw,object_pairs_hook=trust._pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(packets.PacketError('reload-json-invalid')))


def _reload_save(root,name,value):
    raw=packets.canonical(value)
    if len(raw)>_RELOAD_LIMIT:raise packets.PacketError('reload-artifact-bound')
    fd=trust._directory(root)
    try:
        out=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
        with os.fdopen(out,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.fsync(fd)
    finally:os.close(fd)
    return _reload_read(root,name)[1]


def _reload_ref(root,reference):
    if type(reference)is not dict or set(reference)!={'relative','sha256','identity'}:
        raise packets.PacketError('reload-reference-schema-invalid')
    raw,actual=_reload_read(root,reference['relative'])
    if actual!=reference:raise packets.PacketError('reload-reference-drift')
    return raw


def _reload_interpreter():
    executable=pathlib.Path(sys.executable).resolve(strict=True)
    fd=os.open(executable,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in (0,os.getuid())
                or before.st_mode&0o022 or before.st_size>134217728):
            raise packets.PacketError('reload-interpreter-untrusted')
        with os.fdopen(os.dup(fd),'rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
        after=os.fstat(fd)
        if (_reload_identity(before)!=_reload_identity(after)
                or _reload_identity(after)!=_reload_identity(os.stat(executable,follow_symlinks=False))
                or sys.version_info[:3]!=(3,12,9)):
            raise packets.PacketError('reload-interpreter-drift')
        return {'path':str(executable),'identity':_reload_identity(after),'sha256':digest,
            'version':list(sys.version_info[:3])}
    finally:os.close(fd)


def _reload_capture(root):
    repository=pathlib.Path(__file__).resolve().parents[1]
    bundle=root/'bundle';bundle.mkdir(mode=0o700)
    hashes={};originals={}
    for relative in _RELOAD_FILES:
        raw,reference=_reload_read(repository,relative,private=False)
        originals[relative]=reference;hashes[relative]=packets.digest(raw)
        path=bundle/relative
        parent=bundle
        for part in pathlib.PurePosixPath(relative).parts[:-1]:
            parent=parent/part;parent.mkdir(mode=0o700,exist_ok=True)
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    for relative,reference in originals.items():
        if _reload_read(repository,relative,private=False)[1]!=reference:
            raise packets.PacketError('reload-source-changed-during-capture')
    _reload_validate_bundle(bundle,hashes)
    return hashes


def _reload_validate_bundle(bundle,hashes):
    if type(hashes)is not dict or set(hashes)!=set(_RELOAD_FILES):
        raise packets.PacketError('reload-source-closure-missing')
    # Reject undeclared imports even in deferred branches. Lifecycle is deliberately
    # unavailable; legacy schema 3/4 cannot enter its deferred import branches.
    allowed=set(_RELOAD_MODULES)|set(sys.stdlib_module_names)|{'model_packet_lifecycle'}
    for relative in _RELOAD_FILES:
        raw,_=_reload_read(bundle,relative)
        if packets.digest(raw)!=hashes[relative]:raise packets.PacketError('reload-source-bundle-drift')
        for node in ast.walk(ast.parse(raw)):
            names=([alias.name for alias in node.names] if isinstance(node,ast.Import)
                else [node.module or ''] if isinstance(node,ast.ImportFrom) else [])
            if any(name.split('.')[0] not in allowed for name in names):
                raise packets.PacketError('reload-extra-import-dependency')
    actual=set()
    for directory,dirs,files in os.walk(bundle,followlinks=False):
        for name in dirs:
            if (pathlib.Path(directory)/name).is_symlink():raise packets.PacketError('reload-bundle-symlink')
        actual.update(str((pathlib.Path(directory)/name).relative_to(bundle)) for name in files)
    if actual!=set(_RELOAD_FILES):raise packets.PacketError('reload-source-closure-extra')


class _ReloadDocker(containers.LocalDocker):
    """Trace the real transport, including partial failures; exact consumer reads."""
    def __init__(self,endpoint,root,stage,*,image,cid=None,volume=None,deadline=None):
        super().__init__(endpoint,root)
        self.root=root;self.stage=stage;self.image_id=image;self.cid=cid;self.volume_name=volume
        self.deadline=deadline;self.trace=[];self.trace_bytes=0;self.failures=[]
        self.containers=[];self.volumes=[]

    def _allowed(self,argv,input_bytes):
        if self.stage!='consumer':return
        exact={('info','--format','{{json .ID}}'),('image','inspect',self.image_id),
            ('container','inspect',self.cid),('volume','inspect',self.volume_name),
            ('container','top',self.cid,'-eo','pid,ppid,uid,stat,comm')}
        exact.update(('container','cp',self.cid+':/control'+suffix,'-')
            for suffix in ('','/input.json','/claim.json'))
        if input_bytes is not None or tuple(argv) not in exact:
            raise packets.PacketError('reload-consumer-command-denied')

    def _transport(self,argv,input_bytes=None):
        row={'argv':list(argv),'input_bytes':None if input_bytes is None else len(input_bytes),
            'started':time.monotonic(),'reply_base64':'','error':None}
        name=self.stage+'-transport-'+str(len(self.trace))+'.json';raw=bytearray();process=None
        def failed(error,phase):
            message=phase+':'+type(error).__name__+':'+str(error)[:160]
            self.failures.append(message)
            if row['error'] is None:row['error']=message
        try:
            # Journal errors are sticky even when complete bytes preceded a
            # failed fsync/readback. Never repeat or overwrite that journal.
            _reload_save(self.root,name+'.intent',row)
            self._allowed(argv,input_bytes)
            if self.deadline is not None and self.deadline-time.monotonic()<=12:
                raise packets.PacketError('reload-transport-reserve-unavailable')
            deadline=time.monotonic()+10
            if self._executable_snapshot()!=self.executable_identity:
                raise packets.PacketError('docker-executable-identity-drift')
            if input_bytes is not None and (type(input_bytes)is not bytes or len(input_bytes)>containers.MAX_ENGINE_OUTPUT):
                raise packets.PacketError('docker-input-bound')
            process=subprocess.Popen([self.executable,'--host',self.endpoint,*argv],
                stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=self.environment,
                close_fds=True,pass_fds=(),cwd=self.environment['HOME'])
            os.set_blocking(process.stdout.fileno(),False)
            if process.stdin is not None:os.set_blocking(process.stdin.fileno(),False)
            sent=0;read_open=True
            while read_open or process.stdin is not None and not process.stdin.closed:
                remaining=deadline-time.monotonic()
                if remaining<=0:raise packets.PacketError('docker-reply-unknown')
                if process.stdin is not None and not process.stdin.closed and sent==len(input_bytes):process.stdin.close()
                readers=[process.stdout] if read_open else []
                writers=[process.stdin] if process.stdin is not None and not process.stdin.closed else []
                ready,writable,_=select.select(readers,writers,[],remaining)
                if not ready and not writable:raise packets.PacketError('docker-reply-unknown')
                if writable:sent+=os.write(process.stdin.fileno(),input_bytes[sent:sent+8192])
                if ready:
                    chunk=os.read(process.stdout.fileno(),min(65536,containers.MAX_ENGINE_OUTPUT+1-len(raw)))
                    if not chunk:read_open=False
                    else:
                        raw.extend(chunk)
                        if len(raw)>containers.MAX_ENGINE_OUTPUT:raise packets.PacketError('docker-output-bound')
            if process.wait(timeout=max(.01,deadline-time.monotonic()))!=0:
                raise packets.PacketError('docker-command-rejected')
            if tuple(argv)[:2]==('container','create'):self.containers.append(bytes(raw).strip().decode())
            if tuple(argv)[:2]==('volume','create'):self.volumes.append(bytes(raw).strip().decode())
            return bytes(raw)
        except Exception as error:
            failed(error,'transport-or-intent');raise
        finally:
            finalization_failed=False
            if process is not None:
                try:
                    if process.poll() is None:process.kill();process.wait(timeout=2)
                except Exception as error:
                    failed(error,'transport-cleanup');finalization_failed=True
                # Close both pipes independently; one close failure must not
                # skip the other or disappear behind a successful return.
                for label,stream in [('stdin',process.stdin),('stdout',process.stdout)]:
                    try:
                        if stream is not None and not stream.closed:stream.close()
                    except Exception as error:
                        failed(error,'transport-'+label+'-close');finalization_failed=True
            row['reply_base64']=base64.b64encode(raw).decode();row['finished']=time.monotonic()
            self.trace_bytes+=len(packets.canonical(row))
            self.trace.append(row)
            try:_reload_save(self.root,name,row)
            except Exception as error:
                failed(error,'transport-result-journal');raise
            if self.trace_bytes>_RELOAD_TRACE_LIMIT:
                self.failures.append('reload-trace-bound');raise packets.PacketError('reload-trace-bound')
            if finalization_failed:raise packets.PacketError('reload-transport-finalization-unknown')

    def inspect(self,cid):
        value=super().inspect(cid)
        if self.stage=='consumer':
            try:_reload_running(value,self.cid)
            except Exception as error:self.failures.append(str(error));raise
        return value


def _reload_running(value,cid):
    state=value.get('State',{}) if type(value)is dict else {}
    if (value.get('Id')!=cid or state.get('Status')!='running' or state.get('Running')is not True
            or type(state.get('Pid'))is not int or state['Pid']<=0):
        raise packets.PacketError('reload-original-worker-not-running')


class _ReloadReadBackend:
    """Sticky proof failures cannot be hidden by supervisor's lawful unknown."""
    requires_runtime_descriptor=True
    requires_runtime_bootstrap=True
    def __init__(self,backend):self.backend=backend;self.failures=[];self.inspect_replies=[]
    def inspect(self,*args):
        try:
            reply=self.backend.inspect(*args);self.inspect_replies.append(copy.deepcopy(reply))
            if reply.get('state')!='unknown':raise packets.PacketError('reload-stopped-proof-denied')
            return reply
        except Exception as error:self.failures.append(str(error));raise
    def _deny(self,*args,**kwargs):
        self.failures.append('reload-consumer-backend-effect-denied')
        raise packets.PacketError('reload-consumer-backend-effect-denied')
    prepare=bootstrap=launch=export_patch=read_sealed_patch=_deny


def _reload_baseline(source):
    # Reopen/check only, never create/issue authority or invoke a Git command.
    with source._locked() as (fd,_):
        files=integration._tree(fd)
        metadata=integration._git_metadata(fd)
        if files!=containers.BASELINE or metadata!=source.descriptor['git_metadata_sha256']:
            raise packets.PacketError('reload-source-baseline-drift')
    return {'descriptor_sha256':source.descriptor_sha256,'descriptor':source.descriptor,
        'files':integration._manifest(files),'git_metadata_sha256':metadata}


def _reload_packet_refs(root,store):
    packet=root/store.packet_id
    fd=trust._directory(packet)
    try:
        if os.fstat(fd).st_mode&0o077:raise packets.PacketError('reload-packet-not-private')
    finally:os.close(fd)
    # Verify existence before PacketStore.locked() has any mkdir/O_CREAT opportunity.
    _,lock_ref=_reload_read(root,store.packet_id+'/lock')
    raw,ledger_ref=_reload_read(root,store.packet_id+'/ledger.json')
    ledger=_reload_json(raw)
    if ledger.get('schema_version')!=3 or ledger.get('packet_id')!=_RELOAD_PACKET:
        raise packets.PacketError('reload-legacy-schema-required')
    record=ledger['supervisors']['old'];sha=record['runtime_descriptor_sha256'];checkpoint=ledger['checkpoint']
    if record['stage']!='observing' or not checkpoint:raise packets.PacketError('reload-original-packet-stage-drift')
    descriptor_raw,descriptor_ref=_reload_read(root,store.packet_id+'/runtime-'+sha+'.json')
    descriptor=_reload_json(descriptor_raw)
    if packets.digest(descriptor_raw)!=sha:raise packets.PacketError('reload-descriptor-sha-drift')
    manifest,manifest_ref=_reload_read(root,store.packet_id+'/'+checkpoint+'.json')
    patch,patch_ref=_reload_read(root,store.packet_id+'/'+checkpoint+'.patch')
    if patch!=integration.FIXED_PATCH:raise packets.PacketError('reload-checkpoint-patch-drift')
    return {'ledger':ledger,'ledger_ref':ledger_ref,'lock_ref':lock_ref,'descriptor':descriptor,'descriptor_ref':descriptor_ref,
        'checkpoint':checkpoint,'manifest_ref':manifest_ref,'patch_ref':patch_ref,
        'manifest_sha256':packets.digest(manifest),'patch_sha256':packets.digest(patch),'binding':record['binding']}


def _reload_ledger_delta(before,after):
    """Only the exact lawful unknown observation append/dedup may change C's ledger."""
    if before==after:return 'deduplicated'
    expected=copy.deepcopy(before)
    record=expected['supervisors']['old'];actual=after.get('supervisors',{}).get('old',{})
    observations=record['observations'];new=actual.get('observations')
    binding=record['binding']
    event={'kind':'unknown','reason':'runtime-proof-unavailable','stage':record['stage'],
        'binding_sha256':packets.digest(packets.canonical(binding)),'identity_sha256':binding['identity_sha256'],
        'runtime_id':binding['runtime_id'],'generation':binding['generation'],'revision':expected['revision']+1,
        'evidence_sha256':None,'checkpoint_sha256':None}
    if (type(new)is not list or len(new)!=len(observations)+1 or new[:-1]!=observations or new[-1]!=event):
        raise packets.PacketError('reload-ledger-unexpected-drift')
    record['observations']=new;expected['attempts'][-1]['status']='unknown';expected['revision']+=1
    if expected!=after:raise packets.PacketError('reload-ledger-unexpected-drift')
    return 'appended'


def _reload_backend(store,engine,request):
    backend=containers.OneShotSyntheticContainerBackend(store,endpoint=request['endpoint'],
        image_id=request['image'],opt_in=True,worker='hold-overlap',_engine=engine)
    return backend,supervisors.PacketSupervisor(store,backend,host_id=backend.host_id,
        backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)


def _reload_binding(backend,engine):
    return {'host_id':backend.host_id,'backend_id':backend.backend_id,'policy_sha256':backend.policy_sha256,
        'daemon_identity_sha256':backend.daemon_identity_sha256,'docker_executable':engine.executable,
        'docker_identity':list(engine.executable_identity),'endpoint':engine.endpoint,'image':backend.image_id}


def _reload_produce(root,request):
    engine=_ReloadDocker(request['endpoint'],root,'producer',image=request['image'])
    if engine.executable!=request['docker_executable'] or list(engine.executable_identity)!=request['docker_identity']:
        raise packets.PacketError('reload-docker-executable-drift')
    source=integration.SyntheticSource.create(root);store=packets.PacketStore(root,_RELOAD_PACKET)
    store.prepare(packets.digest(packets.canonical({'scope':'controller-reload'})))
    requirements=source.requirements('add-update')
    seed=containers.OneShotSyntheticContainerBackend(store,endpoint=request['endpoint'],image_id=request['image'],
        opt_in=True,worker='add-update',_engine=engine)
    supervisor=supervisors.PacketSupervisor(store,seed,host_id=seed.host_id,
        backend_id=seed.backend_id,policy_sha256=seed.policy_sha256)
    candidate=supervisor.start('seed','e'*64,'f'*64,expected_revision=0,**requirements)
    candidate=await_candidate(supervisor,store,engine,'seed',candidate)
    if candidate.get('outcome')!='integration-candidate' or candidate.get('patch')!=integration.FIXED_PATCH:
        raise packets.PacketError('reload-seed-checkpoint-unavailable')
    ledger,_=store.read_checkpoint();backend,supervisor=_reload_backend(store,engine,request)
    t0=time.monotonic();deadline=t0+25;engine.deadline=deadline
    pending=supervisor.start('old','e'*64,'f'*64,expected_revision=ledger['revision'],**requirements)
    if pending!=_RELOAD_PENDING:raise packets.PacketError('reload-old-not-pending')
    refs=_reload_packet_refs(root,store);observed=None
    for _ in range(80):
        live_deadline(deadline)
        try:observed=running_observation(backend,refs['binding'],refs['descriptor'],deadline=deadline);break
        except packets.PacketError as error:
            if str(error) not in ('fixture-old-worker-starting-or-finished','fixture-old-worker-phase-unavailable'):raise
            time.sleep(.1)
    if observed is None or engine.failures:raise packets.PacketError('reload-producer-live-proof-unavailable')
    baseline=_reload_baseline(source)
    handoff={'schema_version':1,'stage':'producer','run_id':request['run_id'],'pid':os.getpid(),'ppid':os.getppid(),
        'bundle_sha256':request['bundle_sha256'],'interpreter':_reload_interpreter(),
        'engine_binding':_reload_binding(backend,engine),'packet':_RELOAD_PACKET,'attempt':'old',
        'source_relative':source.root.name,'source_baseline':baseline,'refs':refs,'observation':observed,
        't0':t0,'deadline':deadline,'sealed_at':time.monotonic(),'containers_retained':engine.containers,
        'volumes_retained':engine.volumes,'trace_count':len(engine.trace)}
    live_deadline(deadline);_reload_save(root,'producer-handoff.json',handoff)
    return {'stage':'producer','pid':os.getpid(),'run_id':request['run_id']}


def _reload_handoff(root,request,permit):
    if (type(permit)is not dict or set(permit)!={'schema_version','run_id','producer_pid','producer_exit',
            'producer_waited_at','handoff_ref','consumer_spawned_after'} or permit['schema_version']!=1
            or permit['run_id']!=request['run_id'] or permit['producer_exit']!=0
            or type(permit['producer_pid'])is not int or permit['producer_pid']<=0
            or permit['consumer_spawned_after']!=permit['producer_waited_at']):
        raise packets.PacketError('reload-producer-exit-unproven')
    handoff=_reload_json(_reload_ref(root,permit['handoff_ref']))
    keys={'schema_version','stage','run_id','pid','ppid','bundle_sha256','interpreter','engine_binding',
        'packet','attempt','source_relative','source_baseline','refs','observation','t0','deadline','sealed_at',
        'containers_retained','volumes_retained','trace_count'}
    if (type(handoff)is not dict or set(handoff)!=keys or handoff['schema_version']!=1
            or handoff['stage']!='producer' or handoff['run_id']!=request['run_id']
            or handoff['pid']!=permit['producer_pid'] or handoff['pid']==os.getpid()
            or handoff['ppid']!=request['coordinator_pid'] or handoff['bundle_sha256']!=request['bundle_sha256']
            or handoff['interpreter']!=request['interpreter'] or handoff['packet']!=_RELOAD_PACKET
            or handoff['attempt']!='old' or not re.fullmatch(r'source-fixture-[A-Za-z0-9_]+',handoff['source_relative'])
            or any(type(handoff[key]) not in (int,float) for key in ('t0','deadline','sealed_at'))
            or handoff['deadline']!=handoff['t0']+25 or not handoff['t0']<=handoff['sealed_at']<=permit['producer_waited_at']
            or not permit['producer_waited_at']<=time.monotonic()<handoff['deadline']):
        raise packets.PacketError('reload-handoff-binding-invalid')
    # Validate all original byte/identity references before engine construction.
    for key in ('ledger_ref','lock_ref','descriptor_ref','manifest_ref','patch_ref'):_reload_ref(root,handoff['refs'][key])
    return handoff


def _reload_consume(root,request):
    permit=_reload_json(_reload_read(root,'consumer-permit.json')[0])
    handoff=_reload_handoff(root,request,permit);deadline=handoff['deadline'];refs=handoff['refs']
    store=packets.PacketStore(root,_RELOAD_PACKET)
    before=_reload_packet_refs(root,store)
    if before!=refs:raise packets.PacketError('reload-original-refs-drift')
    source=integration.SyntheticSource.reopen(root/handoff['source_relative'],handoff['source_baseline']['descriptor_sha256'])
    if _reload_baseline(source)!=handoff['source_baseline']:raise packets.PacketError('reload-source-before-drift')
    descriptor=refs['descriptor']
    engine=_ReloadDocker(request['endpoint'],root,'consumer',image=request['image'],cid=descriptor['container_id'],
        volume=descriptor['control_volume']['name'],deadline=deadline)
    backend,_=_reload_backend(store,engine,request)
    if _reload_binding(backend,engine)!=handoff['engine_binding']:raise packets.PacketError('reload-engine-binding-drift')
    first=running_observation(backend,refs['binding'],descriptor,deadline=deadline)
    if first!=handoff['observation']:raise packets.PacketError('reload-original-live-worker-drift')
    proxy=_ReloadReadBackend(backend)
    supervisor=supervisors.PacketSupervisor(store,proxy,host_id=backend.host_id,backend_id=backend.backend_id,
        policy_sha256=backend.policy_sha256)
    result=supervisor.reconcile('old')  # Exactly once, no prepare/start/export/admit.
    if result!=_RELOAD_PENDING or proxy.failures or engine.failures:
        raise packets.PacketError('reload-consumer-proof-failed')
    last=running_observation(backend,refs['binding'],descriptor,deadline=deadline)
    if first!=last:raise packets.PacketError('reload-worker-after-drift')
    after=_reload_packet_refs(root,store);delta=_reload_ledger_delta(before['ledger'],after['ledger'])
    if {k:v for k,v in before.items() if k not in ('ledger','ledger_ref')}!={k:v for k,v in after.items() if k not in ('ledger','ledger_ref')}:
        raise packets.PacketError('reload-checkpoint-or-descriptor-drift')
    if _reload_baseline(source)!=handoff['source_baseline']:raise packets.PacketError('reload-source-after-drift')
    if engine.failures:raise packets.PacketError('reload-consumer-transport-failed')
    live_deadline(deadline)
    value={'schema_version':1,'stage':'consumer','pid':os.getpid(),'ppid':os.getppid(),'run_id':request['run_id'],
        'bundle_sha256':request['bundle_sha256'],'interpreter':_reload_interpreter(),'result':result,
        'ledger_delta':delta,'ledger_after_ref':after['ledger_ref'],'observations':[first,last],
        'inspect_replies':proxy.inspect_replies,'transport_failures':engine.failures,'backend_failures':proxy.failures,
        'trace_count':len(engine.trace),'finished_at':time.monotonic(),'production_qualified':False}
    live_deadline(deadline);_reload_save(root,'consumer-result.json',value)
    return {'stage':'consumer','pid':os.getpid(),'run_id':request['run_id']}


_RELOAD_BOOTSTRAP = '''import hashlib,json,os,pathlib,stat,sys
root=pathlib.Path(sys.argv[1]); stage=sys.argv[2]; sentinel=int(sys.argv[3])
try: os.fstat(sentinel)
except OSError: pass
else: raise RuntimeError("reload-sentinel-fd-inherited")
directory=os.open("/",os.O_RDONLY|os.O_DIRECTORY)
try:
 for part in root.parts[1:]:
  child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
  os.close(directory); directory=child
 root_stat=os.fstat(directory)
 if root_stat.st_uid!=os.getuid() or root_stat.st_mode&0o077: raise RuntimeError("reload-bootstrap-root")
finally: os.close(directory)
def read(relative):
 parts=relative.split("/")
 if not parts or any(p in ("", ".", "..") for p in parts): raise RuntimeError("reload-bootstrap-reference")
 parent=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); fd=None
 try:
  for part in parts[:-1]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
   os.close(parent); parent=child
   value=os.fstat(parent)
   if value.st_uid!=os.getuid() or value.st_mode&0o077: raise RuntimeError("reload-bootstrap-directory")
  fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
  value=os.fstat(fd)
  if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.getuid() or value.st_mode&0o077 or value.st_nlink!=1 or value.st_size>1048576:
   raise RuntimeError("reload-bootstrap-file")
  raw=os.read(fd,1048577); after=os.fstat(fd); named=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
  identity=lambda s:(s.st_dev,s.st_ino,s.st_uid,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
  if len(raw)!=value.st_size or identity(value)!=identity(after) or identity(after)!=identity(named): raise RuntimeError("reload-bootstrap-drift")
  return raw
 finally:
  if fd is not None: os.close(fd)
  os.close(parent)
request_raw=read("reload-request.json")
if hashlib.sha256(request_raw).hexdigest()!=sys.argv[4]: raise RuntimeError("reload-bootstrap-request-drift")
request=json.loads(request_raw)
if request["root_identity"]!=[root_stat.st_dev,root_stat.st_ino,root_stat.st_uid,root_stat.st_mode]: raise RuntimeError("reload-bootstrap-root-drift")
for relative,digest in request["bundle_hashes"].items():
 if hashlib.sha256(read("bundle/"+relative)).hexdigest()!=digest: raise RuntimeError("reload-bootstrap-source-drift")
path=root/"bundle/scripts/verify-model-packet-integrator.py"; raw=read("bundle/scripts/verify-model-packet-integrator.py")
namespace={"__name__":"_private_controller_reload","__file__":str(path)}
exec(compile(raw,str(path),"exec"),namespace)
namespace["_reload_entry"](root,stage)
'''


def _reload_entry(root,stage):
    request=_reload_json(_reload_read(root,'reload-request.json')[0])
    keys={'schema_version','run_id','coordinator_pid','root_identity','bundle_hashes','bundle_sha256',
        'interpreter','endpoint','image','docker_executable','docker_identity'}
    fd=trust._directory(root)
    try:identity=_reload_identity(os.fstat(fd))[:4]
    finally:os.close(fd)
    if (type(request)is not dict or set(request)!=keys or request['schema_version']!=1
            or not re.fullmatch(r'[a-f0-9]{32}',request['run_id']) or os.getppid()!=request['coordinator_pid']
            or request['root_identity']!=identity or request['interpreter']!=_reload_interpreter()
            or request['bundle_sha256']!=packets.digest(packets.canonical(request['bundle_hashes']))
            or stage not in ('preflight','producer','consumer')):
        raise packets.PacketError('reload-private-request-invalid')
    _reload_validate_bundle(root/'bundle',request['bundle_hashes'])
    # Force the implicit immutable/governance dependencies before any engine call.
    for name in _RELOAD_MODULES:
        module=__import__(name)
        if pathlib.Path(module.__file__).resolve()!=root/'bundle/skills/loop-engineering/scripts'/ (name+'.py'):
            raise packets.PacketError('reload-ambient-module-fallback')
    result=({'stage':'preflight','pid':os.getpid(),'run_id':request['run_id']} if stage=='preflight'
        else _reload_produce(root,request) if stage=='producer' else _reload_consume(root,request))
    _reload_validate_bundle(root/'bundle',request['bundle_hashes'])
    print(json.dumps(result,separators=(',',':')),flush=True)


def _reload_helper(root,request,stage,sentinel,deadline):
    """One spawn; bounded private pipes, actual wait, no unknown spawn replay."""
    if deadline-time.monotonic()<=2:raise packets.PacketError('reload-helper-deadline-unavailable')
    process=None;stdout=bytearray();stderr=bytearray();waited=None
    environment={'PATH':str(pathlib.Path(request['docker_executable']).parent)+os.pathsep+os.defpath,
        'HOME':str(root),'LC_ALL':'C','DOCKER_CONFIG':str(root/'.docker-disabled')}
    intent={'stage':stage,'run_id':request['run_id'],'spawn_intent_at':time.monotonic(),
        'argv_flags':['-I','-S','-B'],'close_fds':True,'pass_fds':[],'sentinel_fd':sentinel}
    _reload_save(root,stage+'-helper-intent.json',intent)
    try:
        process=subprocess.Popen([request['interpreter']['path'],'-I','-S','-B','-c',_RELOAD_BOOTSTRAP,
            str(root),stage,str(sentinel),packets.digest(packets.canonical(request))],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,close_fds=True,pass_fds=(),env=environment,cwd=root)
        streams={process.stdout.fileno():stdout,process.stderr.fileno():stderr}
        for fd in streams:os.set_blocking(fd,False)
        while streams:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise packets.PacketError('reload-helper-timeout')
            ready,_,_=select.select(list(streams),[],[],remaining)
            if not ready:raise packets.PacketError('reload-helper-timeout')
            for fd in ready:
                target=streams[fd];chunk=os.read(fd,min(65536,_RELOAD_HELPER_LIMIT+1-len(target)))
                if not chunk:del streams[fd]
                else:
                    target.extend(chunk)
                    if len(target)>_RELOAD_HELPER_LIMIT:raise packets.PacketError('reload-helper-output-bound')
        code=process.wait(timeout=max(.01,deadline-time.monotonic()));waited=time.monotonic()
        if code!=0:raise packets.PacketError('reload-helper-nonzero')
        marker=_reload_json(bytes(stdout))
        if marker!={'stage':stage,'pid':process.pid,'run_id':request['run_id']} or stderr:
            raise packets.PacketError('reload-helper-completion-invalid')
        live_deadline(deadline)
        return {'pid':process.pid,'exit_code':code,'waited_at':waited,'marker':marker}
    finally:
        stopped=False
        if process is not None:
            if process.poll() is None:
                process.kill();stopped=True
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:pass
            process.stdout.close();process.stderr.close()
        _reload_save(root,stage+'-helper-readback.json',{'pid':None if process is None else process.pid,
            'exit_code':None if process is None else process.poll(),'waited_at':waited,'own_helper_killed':stopped,
            'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':base64.b64encode(stderr).decode(),
            'docker_children_stopped_claimed':False})


def _reload_audit_trace(root,stage,count,request,handoff):
    if type(count)is not int or not 1<=count<=512:raise packets.PacketError('reload-trace-count-invalid')
    total=0;inspections=0;tops=0
    policy=object.__new__(_ReloadDocker)
    policy.stage=stage;policy.image_id=request['image'];policy.cid=handoff['refs']['descriptor']['container_id']
    policy.volume_name=handoff['refs']['descriptor']['control_volume']['name']
    for index in range(count):
        name=stage+'-transport-'+str(index)+'.json'
        intent=_reload_json(_reload_read(root,name+'.intent')[0]);raw,_=_reload_read(root,name)
        row=_reload_json(raw);total+=len(raw)
        if (set(row)!={'argv','input_bytes','started','reply_base64','error','finished'}
                or set(intent)!=set(row)-{'finished'} or intent!={**{k:row[k] for k in intent},'reply_base64':'','error':None}
                or row['error']is not None or type(row['argv'])is not list
                or any(type(arg)is not str for arg in row['argv']) or not row['started']<=row['finished']
                or total>_RELOAD_TRACE_LIMIT):
            raise packets.PacketError('reload-raw-transport-proof-invalid')
        reply=base64.b64decode(row['reply_base64'],validate=True)
        if len(reply)>containers.MAX_ENGINE_OUTPUT:raise packets.PacketError('reload-raw-transport-bound')
        if stage=='consumer':
            policy._allowed(row['argv'],row['input_bytes'])
            if not handoff['sealed_at']<=row['started']<=row['finished']<handoff['deadline']:
                raise packets.PacketError('reload-consumer-trace-expired')
            if row['argv'][:2]==['container','inspect']:
                values=_reload_json(reply)
                if type(values)is not list or len(values)!=1:raise packets.PacketError('reload-inspect-raw-invalid')
                _reload_running(values[0],policy.cid)
                if values[0].get('Created')!=handoff['refs']['descriptor']['created_at']:
                    raise packets.PacketError('reload-inspect-created-drift')
                inspections+=1
            if row['argv'][:2]==['container','top']:
                if reply.strip().decode('ascii')!=handoff['observation']['process_table']:
                    raise packets.PacketError('reload-raw-worker-table-drift')
                tops+=1
            if row['argv']==['container','cp',policy.cid+':/control','-']:
                if packets.digest(reply)!=handoff['observation']['control']['archive_sha256']:
                    raise packets.PacketError('reload-raw-control-drift')
    if stage=='consumer' and (inspections<5 or tops!=2):raise packets.PacketError('reload-live-trace-incomplete')
    return {'count':count,'bytes':total,'inspections':inspections,'tops':tops}


def controller_reload(args):
    fd=trust._directory(args.evidence_root)
    try:
        if os.fstat(fd).st_mode&0o077:raise packets.PacketError('evidence-root-must-be-private')
    finally:os.close(fd)
    root=pathlib.Path(tempfile.mkdtemp(prefix='model-controller-reload-',dir=args.evidence_root));root.chmod(0o700)
    receipt={'schema_version':1,'scope':'synthetic-controller-process-reload-live-original-only',
        'fixture':str(root),'execution_outcome':'unknown','production_qualified':False,'runtime_qualified':False,
        'adapter_qualified':False,'n3_complete':False,'cases':{},'limitations':[
            'fixed-private-producer-consumer-not-daemon-or-host-restart','trusted-host-fixed-no-replacement-worker',
            'sentinel-fd-negative-control-not-all-fd-OS-isolation','no-successor-quarantine-or-source-authority',
            'bounded-transport-may-outlive-measurement-deadline-results-remain-unknown',
            'synthetic-artifacts-not-formal-review-or-production-qualification']}
    sentinel=None
    try:
        hashes=_reload_capture(root);interpreter=_reload_interpreter()
        # Construction has no Docker effect. Import preflight precedes first transport.
        engine=containers.LocalDocker(args.endpoint,root)
        fd=trust._directory(root)
        try:identity=_reload_identity(os.fstat(fd))[:4]
        finally:os.close(fd)
        request={'schema_version':1,'run_id':uuid.uuid4().hex,'coordinator_pid':os.getpid(),'root_identity':identity,
            'bundle_hashes':hashes,'bundle_sha256':packets.digest(packets.canonical(hashes)),
            'interpreter':interpreter,'endpoint':args.endpoint,'image':args.image,
            'docker_executable':engine.executable,'docker_identity':list(engine.executable_identity)}
        receipt['request_ref']=_reload_save(root,'reload-request.json',request);receipt['source_sha256']=hashes
        pipe_read,pipe_write=os.pipe()
        try:sentinel=fcntl.fcntl(pipe_read,fcntl.F_DUPFD,100);os.set_inheritable(sentinel,True)
        finally:os.close(pipe_read);os.close(pipe_write)
        _reload_helper(root,request,'preflight',sentinel,time.monotonic()+15)
        producer=_reload_helper(root,request,'producer',sentinel,time.monotonic()+45)
        handoff_raw,handoff_ref=_reload_read(root,'producer-handoff.json');handoff=_reload_json(handoff_raw)
        permit={'schema_version':1,'run_id':request['run_id'],'producer_pid':producer['pid'],
            'producer_exit':producer['exit_code'],'producer_waited_at':producer['waited_at'],
            'handoff_ref':handoff_ref,'consumer_spawned_after':producer['waited_at']}
        _reload_handoff(root,request,permit)
        _reload_validate_bundle(root/'bundle',hashes)
        if _reload_interpreter()!=interpreter:raise packets.PacketError('reload-interpreter-drift')
        _reload_save(root,'consumer-permit.json',permit)
        consumer=_reload_helper(root,request,'consumer',sentinel,handoff['deadline'])
        result=_reload_json(_reload_read(root,'consumer-result.json')[0])
        result_keys={'schema_version','stage','pid','ppid','run_id','bundle_sha256','interpreter','result',
            'ledger_delta','ledger_after_ref','observations','inspect_replies','transport_failures','backend_failures',
            'trace_count','finished_at','production_qualified'}
        if (type(result)is not dict or set(result)!=result_keys or result['schema_version']!=1
                or result['stage']!='consumer' or result['production_qualified']is not False
                or consumer['pid']==producer['pid'] or result.get('pid')!=consumer['pid']
                or result.get('ppid')!=os.getpid() or result.get('run_id')!=request['run_id']
                or result.get('bundle_sha256')!=request['bundle_sha256'] or result.get('interpreter')!=interpreter
                or result.get('result')!=_RELOAD_PENDING or result.get('backend_failures')!=[]
                or result.get('transport_failures')!=[] or not producer['waited_at']<result['finished_at']<handoff['deadline']):
            raise packets.PacketError('reload-consumer-result-invalid')
        if result['observations']!=[handoff['observation'],handoff['observation']]:
            raise packets.PacketError('reload-live-observation-drift')
        trace={stage:_reload_audit_trace(root,stage,count,request,handoff)
            for stage,count in [('producer',handoff['trace_count']),('consumer',result['trace_count'])]}
        store=packets.PacketStore(root,_RELOAD_PACKET);after=_reload_packet_refs(root,store);before=handoff['refs']
        if after['ledger_ref']!=result['ledger_after_ref'] or _reload_ledger_delta(before['ledger'],after['ledger'])!=result['ledger_delta']:
            raise packets.PacketError('reload-coordinator-ledger-drift')
        if {k:v for k,v in before.items() if k not in ('ledger','ledger_ref')}!={k:v for k,v in after.items() if k not in ('ledger','ledger_ref')}:
            raise packets.PacketError('reload-coordinator-checkpoint-drift')
        source=integration.SyntheticSource.reopen(root/handoff['source_relative'],handoff['source_baseline']['descriptor_sha256'])
        if _reload_baseline(source)!=handoff['source_baseline']:raise packets.PacketError('reload-coordinator-source-drift')
        _reload_validate_bundle(root/'bundle',hashes);live_deadline(handoff['deadline'])
        receipt['cases']['controller-reload']={'passed':True,'producer':producer,'consumer':consumer,
            'handoff_ref':handoff_ref,'result':result,'transport_audit':trace,'containers_retained':handoff['containers_retained'],
            'volumes_retained':handoff['volumes_retained']}
        receipt['execution_outcome']='measured-synthetic-controller-reload-passed'
    except Exception as error:
        receipt['failure_class']=type(error).__name__;receipt['failure_reason']=str(error)[:160];raise
    finally:
        if sentinel is not None:os.close(sentinel)
        _reload_save(root,'controller-reload-evidence.json',receipt)
        print(json.dumps({'evidence':str(root/'controller-reload-evidence.json'),
            'execution_outcome':receipt['execution_outcome'],'production_qualified':False}))
    return receipt


def run(args,*,_engine_factory=None):
    if getattr(args,'controller_reload_only',False):
        if _engine_factory is not None:raise packets.PacketError('reload-coordinator-real-private-helpers-required')
        return controller_reload(args)
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
    modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--controller-reload-only',action='store_true',help='fixed producer exit/fresh readonly original live worker reconstruction only')
    modes.add_argument('--checkpoint-overlap-only',action='store_true',help='fixed nonempty checkpoint/live quarantine/successor fixture only')
    parser.add_argument('--endpoint',required=True); parser.add_argument('--image',required=True)
    parser.add_argument('--evidence-root',required=True,type=pathlib.Path)
    args=parser.parse_args(argv)
    if not args.synthetic_qualified_container_fixture: parser.error('explicit synthetic fixture opt-in required')
    run(args)
    return 0


if __name__=='__main__': raise SystemExit(main())
