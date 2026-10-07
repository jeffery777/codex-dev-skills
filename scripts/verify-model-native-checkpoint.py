#!/usr/bin/env python3
"""Opt-in anonymous native checkpoint/fresh-consumer control; retained scratch only."""
import argparse
import ast
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
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
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/loop-engineering/scripts'))
sys.path.insert(0,str(ROOT/'scripts'))
import model_native_checkpoint_backend as native
import model_native_checkpoint_fixture as guest
import model_packet_store as packets
import model_packet_supervisor as supervisors
import model_control_archive as archive
import model_packet_integrator as integration

IMAGE = native.IMAGE
PACKET = 'packet-native-checkpoint'


@contextmanager
def private_directory(root, expected_fd=None):
    """Authenticate the complete namespace before writes or captured-code loads.

    Other host UIDs cannot replace trusted/sticky ancestors. The held descriptor
    also detects pathname drift; same-UID host code remains in the trusted base.
    """
    fd = None
    try:
        fd = packets.trust._directory(root)
        value = os.fstat(fd)
        if stat.S_IMODE(value.st_mode) != 0o700:
            raise packets.PacketError('native-private-evidence-root-required')
        if expected_fd is not None:
            held = os.fstat(expected_fd)
            packets.trust._check(held, directory=True)
            if (stat.S_IMODE(held.st_mode) != 0o700
                    or (held.st_dev, held.st_ino) != (value.st_dev, value.st_ino)):
                raise packets.PacketError('native-private-evidence-root-drift')
    except (OSError, packets.trust.Untrusted) as error:
        if fd is not None:
            os.close(fd)
        raise packets.PacketError('native-private-evidence-root-untrusted') from error
    except BaseException:
        if fd is not None:
            os.close(fd)
        raise
    try:
        yield fd
    finally:
        os.close(fd)


def load_external():
    spec = importlib.util.spec_from_file_location('checkpoint_external_host',ROOT/'scripts/verify-model-external-bootstrap.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def save(root, name, value):
    raw = packets.canonical(value)
    fd = os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    return native.read_file(root/name,1048576,0o600)[1]


def read(root, name, ref=None):
    raw, actual = native.read_file(root/name,1048576,0o600)
    if ref is not None and actual != ref: raise packets.PacketError('native-private-reference-drift')
    return native.containers._json(raw)


def sync_file(path, mode):
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid()
                or before.st_nlink!=1 or stat.S_IMODE(before.st_mode)!=mode):
            raise packets.PacketError('native-final-capture-mode-drift')
        os.fsync(fd)
        if native.identity(os.fstat(fd))!=native.identity(os.lstat(path)):
            raise packets.PacketError('native-final-capture-identity-drift')
    finally: os.close(fd)


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try: os.fsync(fd)
    finally: os.close(fd)


def capture(root, binary):
    capsule = root/'capsule'; capsule.mkdir(mode=0o700)
    host, child = capsule/'host',capsule/'guest'; host.mkdir(mode=0o700); child.mkdir(mode=0o700)
    original = {}; hashes = {}
    allowed = {pathlib.PurePosixPath(p).stem for p in native.SOURCE_FILES}|set(sys.stdlib_module_names)|{'model_packet_lifecycle'}
    for name in native.SOURCE_FILES:
        path = ROOT/name; fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            before = native.identity(os.fstat(stream.fileno())); raw = stream.read(1048577)
            if before != native.identity(os.fstat(stream.fileno())) or before != native.identity(os.lstat(path)) or len(raw)>1048576:
                raise packets.PacketError('native-source-capture-drift')
        original[name] = before; hashes[name] = packets.digest(raw)
        for node in ast.walk(ast.parse(raw)):
            imports = [a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            if any(n.split('.')[0] not in allowed for n in imports): raise packets.PacketError('native-source-import-closure')
        for tree in (host,child):
            target = tree/name; target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            fd = os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    load_external().base.copy_binary(binary,child/'codex'); (child/'codex').chmod(0o555)
    save(child,'guest-manifest.json',{'schema_version':1,'sources':hashes,'binary_sha256':native.BINARY_SHA})
    for directory,_,files in os.walk(child,topdown=False):
        for name in files:
            path = pathlib.Path(directory)/name
            if name != 'codex': path.chmod(0o444)
            sync_file(path,0o555 if name=='codex' else 0o444)
        pathlib.Path(directory).chmod(0o555)
    for tree in (host,child):
        for directory,_,_ in os.walk(tree,topdown=False):
            if tree == host: pathlib.Path(directory).chmod(0o700)
            fd = os.open(directory,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try: os.fsync(fd)
            finally: os.close(fd)
    for name,before in original.items():
        if native.identity(os.lstat(ROOT/name)) != before or packets.digest((ROOT/name).read_bytes()) != hashes[name]:
            raise packets.PacketError('native-source-changed-after-capture')
    # Create the protected capsule file before capturing its parent directory
    # identity; later writing this file does not add another directory entry.
    fd = os.open(capsule/'capsule.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    value = {'schema_version':1,'root':native.identity(os.lstat(capsule)),
        'host':native.inspect_tree(host,native.SOURCE_FILES,private=True),
        'guest':native.inspect_tree(child,set(native.SOURCE_FILES)|{'codex','guest-manifest.json'},private=False)}
    with os.fdopen(fd,'wb') as stream: stream.write(packets.canonical(value)); stream.flush(); os.fsync(stream.fileno())
    sync_directory(capsule); sync_directory(root)
    ref = native.read_file(capsule/'capsule.json',1048576,0o600)[1]
    native.validate_capsule(capsule,ref); return ref


class Engine(native.containers.LocalDocker):
    """Consumer can only read the original physical runtime and root control files."""
    def __init__(self,endpoint,root,stage,descriptor=None):
        super().__init__(endpoint,root); self.root=root; self.stage=stage; self.descriptor=descriptor
        self.trace=[]; self.failures=[]
    def _transport(self,argv,input_bytes=None):
        if self.stage == 'consumer':
            d=self.descriptor; cid=d['container_id']
            permitted={('info','--format','{{json .ID}}'),('image','inspect',IMAGE),
                ('container','inspect',cid),('volume','inspect',d['control_volume']['name'])}
            permitted.update(('container','cp',cid+':/control/'+name,'-') for name in ('input.json','claim.json','completion.json'))
            if input_bytes is not None or tuple(argv) not in permitted:
                self.failures.append('consumer-command-denied'); raise packets.PacketError('native-consumer-command-denied')
        index=len(self.trace); row={'argv':list(argv),'input_sha256':None if input_bytes is None else packets.digest(input_bytes)}
        save(self.root,self.stage+'-transport-'+str(index)+'.intent.json',row)
        try:
            raw=super()._transport(argv,input_bytes)
            row.update(reply_base64=base64.b64encode(raw).decode(),reply_sha256=packets.digest(raw))
            save(self.root,self.stage+'-transport-'+str(index)+'.json',row); self.trace.append(row); return raw
        except Exception:
            self.failures.append('native-transport-failed'); raise


def requirements(source=None):
    if source is not None: return source.requirements('native-update')
    return {'source_sha256':native.containers.source_digest(),
        'scope_sha256':packets.digest(packets.canonical({'paths':['example.txt'],'kind':'fixed-native-intake'})),
        'acceptance_sha256':packets.digest(native.FIXED_PATCH)}


def reserve_successor(store,value,ledger,binding):
    result=store.reserve_runtime('successor','a'*64,'f'*64,expected_revision=ledger['revision'],
        host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256,
        runtime_id='runtime-'+uuid.uuid4().hex,runtime_descriptor_required=True,runtime_bootstrap_required=True,
        **requirements())
    current,successor=store.supervisor_snapshot('successor')
    if (result['claimed'] is not True or current!=result['ledger'] or successor['stage']!='reserved'
            or successor['binding']['generation']<=binding['generation']):
        raise packets.PacketError('native-successor-generation-unavailable')
    return current


def backend(root, request, store, engine):
    if (engine.executable!=request['docker_executable']
            or list(engine.executable_identity)!=request['docker_identity']):
        raise packets.PacketError('native-pinned-docker-executable-drift')
    value=native.OneShotNativeFixtureBackend(store,endpoint=request['endpoint'],image_id=IMAGE,opt_in=True,
        capture_root=root/'capsule',capture_ref=request['capsule_ref'],native_case=request['case'],_engine=engine)
    supervisor=supervisors.PacketSupervisor(store,value,host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256)
    return value,supervisor


def packet_refs(store):
    # Separate packet layout from the strictly single-link capture tree. Retain
    # PacketStore's exact staging/canonical pair; never repair its crash evidence.
    rows={}; pairs={}
    canonical=re.compile(r'(?:backend-runtime-[a-f0-9]{32}\.[a-z-]{1,32}'
        r'|sealed-runtime-[a-f0-9]{32}\.(?:json|patch)'
        r'|(?:runtime-|bootstrap-|bootstrap-event-|integration-intent-|integration-result-)?[a-f0-9]{64}\.(?:json|patch))')
    with store.locked() as directory:
        before=native.identity(os.fstat(directory)); names=sorted(os.listdir(directory))
        for name in names:
            value=os.stat(name,dir_fd=directory,follow_symlinks=False)
            if stat.S_ISDIR(value.st_mode):
                if not re.fullmatch(r'workspace-runtime-[a-f0-9]{32}',name):
                    raise packets.PacketError('native-packet-extra-directory')
                continue
            staging=re.fullmatch(r'artifact-[a-f0-9]{32}',name) is not None
            if name not in ('ledger.json','lock') and not staging and not canonical.fullmatch(name):
                raise packets.PacketError('native-packet-extra-file')
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=directory)
            try:
                value=os.fstat(fd)
                if (not stat.S_ISREG(value.st_mode) or value.st_uid!=os.getuid()
                        or stat.S_IMODE(value.st_mode)!=0o600 or value.st_size>packets.MAX_LEDGER
                        or value.st_nlink not in ({1} if name in ('ledger.json','lock') else {1,2})):
                    raise packets.PacketError('native-packet-file-shape')
                raw=bytearray()
                while len(raw)<=packets.MAX_LEDGER:
                    chunk=os.read(fd,min(65536,packets.MAX_LEDGER+1-len(raw)))
                    if not chunk: break
                    raw.extend(chunk)
                after=os.fstat(fd); named=os.stat(name,dir_fd=directory,follow_symlinks=False)
                if (len(raw)!=value.st_size or native.identity(value)!=native.identity(after)
                        or native.identity(after)!=native.identity(named)):
                    raise packets.PacketError('native-packet-file-drift')
                rows[name]={'sha256':packets.digest(bytes(raw)),'identity':native.identity(after)}
                if value.st_nlink==2: pairs.setdefault((value.st_dev,value.st_ino),[]).append((name,staging))
            finally: os.close(fd)
        if (native.identity(os.fstat(directory))!=before or sorted(os.listdir(directory))!=names):
            raise packets.PacketError('native-packet-directory-drift')
        for pair in pairs.values():
            if len(pair)!=2 or sorted(stage for _,stage in pair)!=[False,True]:
                raise packets.PacketError('native-packet-hardlink-pair-drift')
    return rows


def control_chain(value, binding, descriptor):
    rows={}
    for name in ('input.json','claim.json','completion.json'):
        raw=archive.read_control_file(value.engine.archive('container','cp',descriptor['container_id']+':/control/'+name,'-'),name)
        rows[name]=raw
    expected={'schema_version':1,'binding':binding,'nonce':descriptor['nonce'],
        'volume':descriptor['control_volume']['name'],'descriptor_sha256':packets.digest(packets.canonical(descriptor)),
        'container_id':descriptor['container_id'],'launcher_sha256':descriptor['launcher_sha256']}
    claim={'schema_version':1,'input_sha256':packets.digest(rows['input.json']),'input':expected}
    completion={'schema_version':1,'claim_sha256':packets.digest(rows['claim.json']),
        'input_sha256':packets.digest(rows['input.json']),'input':expected,'worker_status':0}
    if rows != {'input.json':packets.canonical(expected),'claim.json':packets.canonical(claim),'completion.json':packets.canonical(completion)}:
        raise packets.PacketError('native-protected-chain-drift')
    return {name:packets.digest(raw) for name,raw in rows.items()}


def worker_observation(raw, request, descriptor):
    case = request['case']
    if case not in native.EXECUTION_CASES:
        raise packets.PacketError('native-observation-case-invalid')
    if not raw.startswith(guest.PREFIX) or not raw.endswith(b'\n') or raw.count(b'\n') != 1:
        raise packets.PacketError('native-worker-frame-shape')
    compressed=base64.b64decode(raw[len(guest.PREFIX):-1],validate=True)
    if len(compressed)>32768: raise packets.PacketError('native-worker-frame-bound')
    decoder=zlib.decompressobj(); decoded=decoder.decompress(compressed,1048577)
    if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data or len(decoded)>1048576:
        raise packets.PacketError('native-worker-frame-incomplete')
    receipt=native.containers._json(decoded); external=load_external()
    if (receipt.get('passed') is not True or receipt.get('case') != request['case']
            or receipt.get('nonce') != descriptor['nonce'] or receipt.get('production_qualified') is not False
            or receipt.get('client_close') != {'protocol':'observed','direct_child':'exited','exit_code':0,'descendants':'unknown'}):
        raise packets.PacketError('native-worker-observation-incomplete')
    state=external.decode_bundle(receipt['provider_bundle'])
    if (state.get('failed') is not False or state.get('stopped') is not True or state.get('slots') != 2
            or not guest.output_valid(state.get('native_output')) or len(state.get('records',[])) != 2):
        raise packets.PacketError('native-provider-observation-incomplete')
    bodies=[]; declarations=[]
    for stage,record in enumerate(state['records'],1):
        blobs={}
        for label in ('request','response'):
            blob=base64.b64decode(record[label+'_base64'],validate=True); blobs[label]=blob
            if len(blob) != record[label+'_bytes'] or packets.digest(blob) != record[label+'_sha256']:
                raise packets.PacketError('native-provider-raw-drift')
        if record['stage'] != stage or record['response_sent'] is not True or blobs['response'] != guest.response(stage, case):
            raise packets.PacketError('native-provider-response-drift')
        declarations.append(external.guest.declaration(blobs['request'],external.base.probe.boundary,'workspace-patch'))
        body=external.base.probe.manifest.decode(blobs['request']); bodies.append(body)
        if (body.get('model')!=external.guest.DIRECT_MODEL or body.get('stream') is not True
                or body.get('store') is not False or body.get('tool_choice')!='auto'
                or body.get('parallel_tool_calls') is not True):
            raise packets.PacketError('native-provider-fixed-model-drift')
    if guest.stable_declaration(declarations[0])!=guest.stable_declaration(declarations[1]):
        raise packets.PacketError('native-provider-tool-declaration-drift')
    initial=bodies[0].get('input')
    if (type(initial) is not list or not initial or any(type(item) is not dict
            or item.get('type') not in ('message','additional_tools')
            or item.get('type')=='message' and item.get('role') not in ('developer','user') for item in initial)
            or initial[-1].get('role')!='user'
            or initial[-1].get('content')!=[{'type':'input_text','text':'Perform the fixed anonymous fixture update.'}]):
        raise packets.PacketError('native-provider-initial-history-drift')
    final=bodies[1].get('input')
    if type(final) is not list or final[:-2]!=initial or len(final)!=len(initial)+2:
        raise packets.PacketError('native-provider-tool-history-drift')
    call,output=final[-2:]
    expected_call = guest.native_call(case)
    if ({k:v for k,v in call.items() if k!='id'}!=expected_call
            or {k:v for k,v in output.items() if k!='id'}!={'type':'custom_tool_call_output',
                'call_id':guest.CALL['call_id'],'output':state['native_output']}):
        raise packets.PacketError('native-provider-fixed-call-drift')
    stderr=receipt.get('cli_stderr',{}); stderr_raw=base64.b64decode(stderr.get('raw_base64',''),validate=True)
    if (not external.base.guest.stderr_complete(stderr) or len(stderr_raw)!=stderr.get('captured_bytes')
            or packets.digest(stderr_raw)!=stderr.get('captured_prefix_sha256')):
        raise packets.PacketError('native-cli-stderr-incomplete')
    wire=receipt['wire']; validate_wire(wire,receipt,external,case=case)
    return {'sha256':packets.digest(raw),'wire_messages':len(wire),'http_requests':2,'native_calls':1,
        'complete_settings_fields':14,'worker_statement_is_authority':False}


def validate_wire(wire,receipt,external,*,case='checkpoint'):
    """Closed native activity plus exact outgoing intent/sent pairs, never authority."""
    if case not in native.EXECUTION_CASES:
        raise packets.PacketError('native-wire-case-invalid')
    fixed_diff = '@@ -1 +1 @@\n-new\n+done\n' if case == 'successor-checkpoint' else '@@ -1 +1 @@\n-old\n+new\n'
    thread,turn=receipt['thread_id'],receipt['turn_id']; events={}; settings=[]; items={}; replies={}; pending=None
    start={'model':external.guest.DIRECT_MODEL,'modelProvider':'fixture','allowProviderModelFallback':False,
        'cwd':'/workspace','ephemeral':True,'sandbox':'read-only','approvalPolicy':'never',
        'environments':[],'experimentalRawEvents':False}
    outgoing=[{'id':1,'method':'initialize','params':{'clientInfo':{'name':'external_bootstrap_only','version':'1'},'capabilities':{'experimentalApi':True}}},
        {'method':'initialized'},{'id':2,'method':'thread/start','params':start},
        {'id':3,'method':'thread/settings/update','params':external.settings_update_params(thread,'input-disabled-dispatch')},
        {'id':4,'method':'turn/start','params':guest.turn_params(external,thread)}]
    sent=[]; total=0
    allowed={'configWarning','remoteControl/status/changed','thread/started','thread/settings/updated',
        'thread/status/changed','turn/started','turn/completed','item/started','item/completed',
        'turn/diff/updated','thread/tokenUsage/updated','account/rateLimits/updated'}
    if type(wire) is not list or len(wire)>8192: raise packets.PacketError('native-wire-bound')
    for index,row in enumerate(wire):
        if type(row) is not dict or set(row)!={'direction','message','raw_base64'}:
            raise packets.PacketError('native-wire-shape')
        message=row['message']; rawline=base64.b64decode(row['raw_base64'],validate=True); total+=len(rawline)
        if total>262144 or not rawline.endswith(b'\n') or rawline.count(b'\n')!=1 or external.base.probe.manifest.decode(rawline)!=message:
            raise packets.PacketError('native-wire-raw-drift')
        if row['direction']=='out-intent':
            if pending is not None: raise packets.PacketError('native-outgoing-intent-overlap')
            pending=message; continue
        if row['direction']=='out-sent':
            if pending!=message or index==0 or wire[index-1]['direction']!='out-intent':
                raise packets.PacketError('native-outgoing-intent-unconfirmed')
            pending=None; sent.append(message); events.setdefault(message['method'],[]).append(index); continue
        if row['direction']!='in' or pending is not None: raise packets.PacketError('native-wire-direction-drift')
        if 'id' in message:
            if set(message)!={'id','result'} or type(message['id']) is not int or message['id'] not in (1,2,3,4) or message['id'] in replies:
                raise packets.PacketError('native-unexpected-response')
            if not any(m.get('id')==message['id'] for m in sent): raise packets.PacketError('native-response-before-request')
            replies[message['id']]=message['result']; continue
        method=message.get('method'); params=message.get('params',{})
        if method not in allowed or type(params) is not dict: raise packets.PacketError('native-unexpected-notification')
        if method=='remoteControl/status/changed' and params.get('status')!='disabled':
            raise packets.PacketError('native-remote-control-enabled')
        if method=='thread/started' and params.get('thread',{}).get('id')!=thread: raise packets.PacketError('native-wire-task-drift')
        if method=='thread/settings/updated':
            external.input_settings_match(message,thread,adopted=bool(settings)); settings.append(index)
        if method in ('turn/started','turn/completed'): events.setdefault(method,[]).append(index)
        if method.startswith(('turn/','item/','thread/tokenUsage')) or method=='thread/status/changed':
            if params.get('threadId')!=thread or (method!='thread/status/changed' and
                    (params.get('turn',{}).get('id') if method in ('turn/started','turn/completed') else params.get('turnId'))!=turn):
                raise packets.PacketError('native-wire-task-drift')
        if method in ('item/started','item/completed'):
            item=params.get('item',{}); kind=item.get('type'); name=item.get('id')
            if kind=='fileChange':
                expected={'type':'fileChange','id':guest.CALL['call_id'],
                    'changes':[{'path':'/workspace/example.txt','kind':{'type':'update','move_path':None},'diff':fixed_diff}],
                    'status':'inProgress' if method=='item/started' else 'completed'}
                if item!=expected: raise packets.PacketError('native-file-change-drift')
            elif kind=='userMessage':
                if (set(item)!={'type','id','clientId','content'} or item['clientId'] is not None
                        or item['content']!=[{'type':'text','text':'Perform the fixed anonymous fixture update.','text_elements':[]}]):
                    raise packets.PacketError('native-user-item-drift')
            elif kind=='agentMessage':
                if item!={'type':'agentMessage','id':'native-checkpoint-final','text':'Fixed anonymous update finished.',
                        'delivery':None,'memoryCitation':None,'phase':None,'questions':None}:
                    raise packets.PacketError('native-agent-item-drift')
            else: raise packets.PacketError('native-extra-tool-activity')
            if type(name) is not str or not 0<len(name)<=256: raise packets.PacketError('native-item-identity-invalid')
            key=(kind,method); items.setdefault(key,[]).append((index,item))
        if method=='turn/completed':
            t=params['turn']
            if t.get('status')!='completed' or t.get('error') is not None or t.get('items')!=[items.get(('agentMessage','item/completed'),[(None,None)])[-1][1]]:
                raise packets.PacketError('native-turn-status-drift')
    if pending is not None or sent!=outgoing or set(replies)!={1,2,3,4} or replies[3]!={}:
        raise packets.PacketError('native-outgoing-fixed-sequence-drift')
    started=replies[2]
    if ({k:started.get(k) for k in ('model','modelProvider','cwd','approvalPolicy','instructionSources')}!=
            {'model':external.guest.DIRECT_MODEL,'modelProvider':'fixture','cwd':'/workspace','approvalPolicy':'never','instructionSources':[]}
            or started.get('thread',{}).get('id')!=thread or started.get('sandbox')!={'type':'readOnly','networkAccess':False}
            or replies[4].get('turn',{}).get('id')!=turn):
        raise packets.PacketError('native-start-readback-drift')
    for kind in ('userMessage','fileChange','agentMessage'):
        begin=items.get((kind,'item/started'),[]); end=items.get((kind,'item/completed'),[])
        if len(begin)!=1 or len(end)!=1 or begin[0][0]>=end[0][0] or begin[0][1]['id']!=end[0][1]['id']:
            raise packets.PacketError('native-item-lifecycle-unconfirmed')
    change=items[('fileChange','item/started')][0][0]; end=items[('fileChange','item/completed')][0][0]
    if (len(settings)!=2 or any(len(events.get(name,[]))!=1 for name in ('thread/settings/update','turn/start','turn/started','turn/completed'))
            or not events['thread/settings/update'][0]<settings[0]<events['turn/start'][0]<settings[1]<events['turn/started'][0]<change<end<events['turn/completed'][0]):
        raise packets.PacketError('native-wire-lifecycle-unconfirmed')


def produce(root, request):
    source=integration.SyntheticSource.create(root) if request['source_integration'] else None
    store=packets.PacketStore(root,PACKET); store.prepare(packets.digest(packets.canonical(request)))
    engine=Engine(request['endpoint'],root,'producer'); value,supervisor=backend(root,request,store,engine)
    result=supervisor.start('attempt','e'*64,'f'*64,expected_revision=0,**requirements(source))
    ledger,record=store.supervisor_snapshot('attempt'); binding=record['binding']; descriptor=store.read_runtime_descriptor('attempt')
    deadline=time.monotonic()+50; quarantine=replay=None
    if request['case'] in ('quarantine','claim-replay') and result!={'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'attempt'}:
        raise packets.PacketError('native-live-window-unavailable')
    if request['case']=='quarantine':
        if result != {'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'attempt'}:
            raise packets.PacketError('native-quarantine-window-unavailable')
        while True:
            if time.monotonic()>=deadline: raise packets.PacketError('native-postwrite-window-missed')
            observed=value._observed(binding,descriptor)
            if observed['State']['Running'] is True and value._walk(binding,descriptor)=={'example.txt':b'new\n','remove.txt':b'delete\n'}: break
            if observed['State']['Status']=='exited': raise packets.PacketError('native-postwrite-window-missed')
            time.sleep(.1)
        private=packets.PacketStore(root,PACKET,_trusted_isolation_adapters={'native':value.isolation_adapter(binding,descriptor)})
        ledger,_=private.supervisor_snapshot('attempt')
        ledger=private.quarantine('attempt',expected_revision=ledger['revision'],isolation_adapter_id='native')
        quarantine={'observed_running':True,'postimage_sha256':packets.digest(b'new\n'),
            'checkpoint':ledger['checkpoint'],'writer_stopped_claim':False,'generation':ledger['generation']}
        if ledger['checkpoint'] is not None: raise packets.PacketError('native-quarantine-published-checkpoint')
        ledger=reserve_successor(private,value,ledger,binding)
        quarantine.update(successor_generation=ledger['generation'],successor_launched=False)
    while True:
        if time.monotonic()>=deadline: raise packets.PacketError('native-original-container-not-exited')
        observed=engine.inspect(descriptor['container_id']); value._validate_policy(observed,binding,descriptor)
        if observed['Id']!=descriptor['container_id'] or observed['Created']!=descriptor['created_at']: raise packets.PacketError('native-original-id-drift')
        if observed['State']['Status']=='exited': break
        time.sleep(.1)
    state=observed['State']
    if (state['Running'] is not False or state['ExitCode']!=0 or state['Pid']!=0 or observed['RestartCount']!=0
            or state['Restarting'] is not False or state['Dead'] is not False or state['Paused'] is not False):
        raise packets.PacketError('native-runtime-exit-unavailable')
    chain=control_chain(value,binding,descriptor)
    raw=engine.archive('container','logs',descriptor['container_id']); frame_ref=save(root,'worker-frame.json',{'raw_base64':base64.b64encode(raw).decode()})
    observation=worker_observation(raw,request,descriptor)
    if request['case']=='checkpoint':
        result=supervisor.reconcile('attempt')
        if result.get('outcome')!='integration-candidate' or result.get('patch')!=native.FIXED_PATCH:
            raise packets.PacketError('native-nonempty-checkpoint-unavailable')
        ledger,patch=store.read_checkpoint()
        if patch!=native.FIXED_PATCH: raise packets.PacketError('native-checkpoint-readback-drift')
    elif request['case']=='quarantine':
        try: supervisor.reconcile('attempt')
        except packets.PacketError as error:
            if str(error)!='stale-writer-result-rejected': raise
        else: raise packets.PacketError('native-late-result-not-rejected')
        ledger,patch=store.read_checkpoint()
        if ledger['checkpoint'] is not None or patch!=b'': raise packets.PacketError('native-quarantined-checkpoint-created')
    else:
        # This one newly-created, known-completed scratch CID is the deliberate
        # adversarial control. No old unknown attempt is restarted or repaired.
        first_started=state['StartedAt']; engine.command('container','start',descriptor['container_id'])
        replay_deadline=time.monotonic()+10
        while True:
            if time.monotonic()>=replay_deadline: raise packets.PacketError('native-replay-exit-unavailable')
            observed=engine.inspect(descriptor['container_id']); value._validate_policy(observed,binding,descriptor)
            if observed['Id']!=descriptor['container_id'] or observed['Created']!=descriptor['created_at']:
                raise packets.PacketError('native-original-id-drift')
            if observed['State']['Status']=='exited': break
            time.sleep(.1)
        after=observed['State']
        if (after['ExitCode']!=73 or after['Running'] is not False or after['Pid']!=0
                or after['Restarting'] is not False or after['Dead'] is not False or after['Paused'] is not False
                or observed['RestartCount']!=0 or after['StartedAt']==first_started
                or control_chain(value,binding,descriptor)!=chain
                or engine.archive('container','logs',descriptor['container_id'])!=raw
                or value._walk(binding,descriptor)!={'example.txt':b'new\n','remove.txt':b'delete\n'}):
            raise packets.PacketError('native-replay-claim-not-refused')
        result=supervisor.reconcile('attempt')
        ledger,patch=store.read_checkpoint()
        if result!={'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'attempt'} or ledger['checkpoint'] is not None or patch!=b'':
            raise packets.PacketError('native-replay-checkpoint-not-blocked')
        replay={'original_exit':0,'second_exit':73,'same_cid':True,'claim_chain_unchanged':True,
            'worker_frame_unchanged':True,'native_runs':1,'checkpoint':None}
    if engine.failures: raise packets.PacketError('native-producer-transport-failed')
    save(root,'producer-handoff.json',{'schema_version':1,'run_id':request['run_id'],'pid':os.getpid(),'ppid':os.getppid(),
        'binding':binding,'descriptor':descriptor,'packet_refs':packet_refs(store),'capsule_ref':request['capsule_ref'],
        'checkpoint':ledger['checkpoint'],'patch_sha256':packets.digest(patch),'chain':chain,
        'quarantine':quarantine,'replay':replay,'frame_ref':frame_ref,'observation':observation,'engine_identity':engine.identity(),
        'source_ref':None if source is None else {'relative':source.root.name,'descriptor_sha256':source.descriptor_sha256},
        'docker_identity':list(engine.executable_identity),'finished_at':time.monotonic()})


class Consumer:
    requires_runtime_descriptor=True
    requires_runtime_bootstrap=True
    def __init__(self,value): self.value=value; self.failures=[]
    def inspect(self,*args): return self.value.inspect(*args)
    def read_sealed_patch(self,*args): return self.value.read_sealed_patch(*args)
    def deny(self,*args,**kwargs):
        self.failures.append('consumer-effect-denied'); raise packets.PacketError('native-consumer-effect-denied')
    prepare=bootstrap_input=bootstrap=launch=export_patch=deny


def integrate_checkpoint(root,handoff,store,value):
    """Host-only bounded source port; no worker-supplied source or authority."""
    ref=handoff['source_ref']
    if (type(ref)is not dict or set(ref)!={'relative','descriptor_sha256'}
            or type(ref['relative'])is not str or not re.fullmatch(r'source-fixture-[a-z0-9_]{8}',ref['relative'])):
        raise packets.PacketError('native-source-reference-invalid')
    source=integration.SyntheticSource.reopen(root/ref['relative'],ref['descriptor_sha256'])
    governance=integration.FixtureGovernance(source)
    supervisor=supervisors.PacketSupervisor(store,value,host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256)
    integrator=native.NativeFixturePacketIntegrator(source,governance,supervisor)
    authority=governance.issue(supervisor,'attempt',recipe='native-update')
    before=packet_refs(store)
    result=integrator.integrate('attempt',authority,operation_id='native-source-update')
    ledger,record,intent=store.integration_snapshot('native-source-update')
    after=packet_refs(store)
    if (result['state']!='applied' or result['reason']!='postimage-readback'
            or intent['scope_paths']!=['example.txt'] or ledger['checkpoint']!=handoff['checkpoint']
            or any(after.get(name)!=row for name,row in before.items() if name!='ledger.json')):
        raise packets.PacketError('native-source-integration-readback-drift')
    # Only the integration's two journal artifacts and their exact staging links
    # may be appended. Every original immutable artifact keeps its identity.
    expected={'integration-intent-'+record['intent_sha256']+'.json',
        'integration-result-'+record['result_sha256']+'.json'}
    added=set(after)-set(before)
    if not expected<=added or len(added)!=4:
        raise packets.PacketError('native-source-integration-journal-drift')
    for name in added-expected:
        if not re.fullmatch(r'artifact-[a-f0-9]{32}',name) or not any(after[name]==after[key] for key in expected):
            raise packets.PacketError('native-source-integration-journal-drift')
    with source._locked() as (fd,_):
        if source.snapshot(fd)!=integration._fixed_postimage('native-update'):
            raise packets.PacketError('native-source-postimage-drift')
    # This same-operation call must read its result, never apply/restart again.
    if integrator.reconcile('native-source-update',authority)!=result or packet_refs(store)!=after:
        raise packets.PacketError('native-source-reconcile-mutated-or-drifted')
    return {'result':result,'source_descriptor_sha256':source.descriptor_sha256,
        'intent_sha256':record['intent_sha256'],'result_sha256':record['result_sha256'],
        'checkpoint_unchanged':True,'original_immutable_refs_unchanged':True,
        'source_head_index_unchanged':True,'same_operation_reconcile_readonly':True}


def consume(root,request):
    permit=read(root,'consumer-permit.json'); handoff=read(root,'producer-handoff.json',permit['handoff_ref'])
    start=read(root,'produce-started.json'); wait=read(root,'produce-waited.json')
    if (permit['producer_exit']!=0 or permit['producer_pid']!=handoff['pid'] or handoff['pid']==os.getpid()
            or start['pid']!=handoff['pid'] or wait['pid']!=start['pid'] or wait['exit_code']!=0
            or wait['stderr_eof'] is not True or start['ppid']!=request['coordinator_pid']
            or handoff['ppid']!=request['coordinator_pid'] or os.getppid()!=request['coordinator_pid']
            or permit['run_id']!=request['run_id']
            or not handoff['finished_at']<=permit['waited_at']<=time.monotonic()):
        raise packets.PacketError('native-producer-exit-unproven')
    native.validate_capsule(root/'capsule',request['capsule_ref'])
    store=packets.PacketStore(root,PACKET)
    if packet_refs(store)!=handoff['packet_refs']: raise packets.PacketError('native-consumer-protected-refs-drift')
    engine=Engine(request['endpoint'],root,'consumer',handoff['descriptor']); value,_=backend(root,request,store,engine)
    if engine.identity()!=handoff['engine_identity'] or list(engine.executable_identity)!=handoff['docker_identity']:
        raise packets.PacketError('native-consumer-engine-drift')
    proxy=Consumer(value); supervisor=supervisors.PacketSupervisor(store,proxy,host_id=value.host_id,backend_id=value.backend_id,policy_sha256=value.policy_sha256)
    if request['case']=='checkpoint':
        result=supervisor.reconcile('attempt')
        if result.get('outcome')!='integration-candidate' or result.get('patch')!=native.FIXED_PATCH:
            raise packets.PacketError('native-consumer-checkpoint-drift')
        outcome='same-nonempty-checkpoint'
    elif request['case']=='quarantine':
        try: supervisor.reconcile('attempt')
        except packets.PacketError as error:
            if str(error)!='stale-writer-result-rejected': raise
        else: raise packets.PacketError('native-consumer-stale-result-accepted')
        outcome='quarantined-late-result-rejected'
    else:
        result=supervisor.reconcile('attempt')
        if result!={'outcome':'unknown','reason':'runtime-proof-unavailable','attempt_id':'attempt'}:
            raise packets.PacketError('native-consumer-replay-result-accepted')
        outcome='same-cid-second-start-refused-no-checkpoint'
    ledger,patch=store.read_checkpoint()
    if (ledger['checkpoint']!=handoff['checkpoint'] or packets.digest(patch)!=handoff['patch_sha256']
            or packet_refs(store)!=handoff['packet_refs'] or proxy.failures or engine.failures):
        raise packets.PacketError('native-consumer-mutated-or-drifted')
    integrated=integrate_checkpoint(root,handoff,store,value) if request['source_integration'] else None
    if engine.failures: raise packets.PacketError('native-consumer-integration-transport-failed')
    save(root,'consumer-result.json',{'run_id':request['run_id'],'pid':os.getpid(),'ppid':os.getppid(),
        'producer_pid':handoff['pid'],'outcome':outcome,'checkpoint':ledger['checkpoint'],
        'protected_refs_unchanged':integrated is None,'intake_refs_unchanged_before_integration':True,
        'source_applied':integrated is not None,
        'source_integration':integrated,'production_qualified':False})


def stage(root,stage_name,request_sha):
    request=read(root,'run-request.json')
    if packets.digest(packets.canonical(request))!=request_sha or stage_name not in ('produce','consume'):
        raise packets.PacketError('native-private-stage-binding-invalid')
    native.validate_capsule(root/'capsule',request['capsule_ref'])
    expected=root/'capsule/host'/native.HOST_SCRIPT
    if pathlib.Path(__file__).resolve()!=expected.resolve(): raise packets.PacketError('native-stage-source-not-captured')
    (produce if stage_name=='produce' else consume)(root,request)


def run_stage(root,name,command,environment,timeout,*,root_fd=None):
    """Coordinator records Popen.pid and actual wait; neither comes from a worker."""
    with private_directory(root, root_fd) as held:
        return _run_stage(root,name,command,environment,timeout,held)


def _run_stage(root,name,command,environment,timeout,root_fd):
    save(root,name+'-intent.json',{'stage':name,'argv':command,'coordinator_pid':os.getpid(),'at':time.monotonic()})
    with private_directory(root, root_fd):
        process=subprocess.Popen(command,env=environment,cwd=root,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,close_fds=True)
    save(root,name+'-started.json',{'pid':process.pid,'ppid':os.getpid(),'at':time.monotonic()})
    raw=bytearray(); deadline=time.monotonic()+timeout; eof=False
    os.set_blocking(process.stderr.fileno(),False)
    try:
        while not eof:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise packets.PacketError('native-stage-wait-unknown')
            ready,_,_=select.select([process.stderr],[],[],remaining)
            if not ready: raise packets.PacketError('native-stage-wait-unknown')
            chunk=os.read(process.stderr.fileno(),min(65536,16385-len(raw)))
            if not chunk: eof=True
            else:
                raw.extend(chunk)
                if len(raw)>16384: raise packets.PacketError('native-stage-stderr-bound')
        code=process.wait(timeout=max(.01,deadline-time.monotonic()))
        return save(root,name+'-waited.json',{'pid':process.pid,'exit_code':code,'stderr_eof':True,
            'stderr_base64':base64.b64encode(raw).decode(),'waited_at':time.monotonic()})
    finally:
        # Direct trusted stage process only; no assertion about any runtime it
        # launched, and no consumer permit after a failed/incomplete wait.
        if process.poll() is None: process.kill(); process.wait(timeout=5)
        process.stderr.close()


def run(args):
    previous_umask = os.umask(0o077)
    try:
        with private_directory(args.evidence_root) as parent_fd:
            root=pathlib.Path(tempfile.mkdtemp(prefix='model-native-checkpoint-',dir=args.evidence_root))
            with private_directory(args.evidence_root, parent_fd), private_directory(root) as root_fd:
                return run_private(args, root, root_fd)
    finally:
        os.umask(previous_umask)


def run_private(args, root, root_fd):
    receipt={'schema_version':1,'scope':'anonymous-native-checkpoint-intake-only','passed':False,
        'production_qualified':False,'native_qualified':False,'runtime_qualified':False,'adapter_qualified':False,
        'isolation_qualified':False,'startup_qualified':False,'n1_qualified':False,'n2_qualified':False,
        'n3_qualified':False,'n4_qualified':False,'fixture':str(root)}
    try:
        source_integration=getattr(args,'native_source_integration_only',False)
        if type(source_integration)is not bool or source_integration and args.case!='checkpoint':
            raise packets.PacketError('native-source-checkpoint-case-required')
        if source_integration: receipt['scope']='anonymous-native-checkpoint-synthetic-source-integration'
        ref=capture(root,args.binary_path)
        pinned_engine=native.containers.LocalDocker(args.endpoint,root)
        request={'schema_version':1,'run_id':uuid.uuid4().hex,'case':args.case,'endpoint':args.endpoint,
            'capsule_ref':ref,'coordinator_pid':os.getpid(),'docker_executable':pinned_engine.executable,
            'source_integration':source_integration,
            'docker_identity':list(pinned_engine.executable_identity)}
        save(root,'run-request.json',request); request_sha=packets.digest(packets.canonical(request))
        command=[sys.executable,'-I','-S','-B',str(root/'capsule/host'/native.HOST_SCRIPT)]
        environment={'PATH':str(pathlib.Path(pinned_engine.executable).parent)+os.pathsep+os.defpath,'HOME':str(root),'LC_ALL':'C'}
        run_stage(root,'produce',command+['_stage','produce',str(root),request_sha],environment,100,root_fd=root_fd)
        producer=read(root,'produce-waited.json'); receipt['producer_exit']=producer['exit_code']
        if producer['exit_code']!=0:
            raise packets.PacketError('native-producer-failed')
        handoff=read(root,'producer-handoff.json'); handoff_ref=native.read_file(root/'producer-handoff.json',1048576,0o600)[1]
        if handoff['pid']!=producer['pid'] or handoff['ppid']!=os.getpid():
            raise packets.PacketError('native-independent-producer-identity-drift')
        save(root,'consumer-permit.json',{'run_id':request['run_id'],'producer_exit':0,'producer_pid':producer['pid'],
            'waited_at':producer['waited_at'],'handoff_ref':handoff_ref})
        run_stage(root,'consume',command+['_stage','consume',str(root),request_sha],environment,70,root_fd=root_fd)
        consumer=read(root,'consume-waited.json'); receipt['consumer_exit']=consumer['exit_code']
        if consumer['exit_code']!=0:
            raise packets.PacketError('native-consumer-failed')
        result=read(root,'consumer-result.json'); native.validate_capsule(root/'capsule',ref)
        if result['pid']!=consumer['pid'] or result['ppid']!=os.getpid() or result['pid']==producer['pid']:
            raise packets.PacketError('native-independent-consumer-identity-drift')
        receipt.update(passed=True,case=request['case'],handoff=handoff,consumer=result,
            capsule_ref=ref,producer_and_consumer_distinct=handoff['pid']!=result['pid'])
    except Exception as error:
        receipt['failure_class']=type(error).__name__
        code=str(error); receipt['failure_code']=code if len(code)<=80 and all(c in 'abcdefghijklmnopqrstuvwxyz-' for c in code) else 'unknown'
    finally:
        with private_directory(root, root_fd):
            save(root,'native-checkpoint-evidence.json',receipt)
    return receipt


def main():
    if len(sys.argv)==5 and sys.argv[1]=='_stage':
        stage(pathlib.Path(sys.argv[3]),sys.argv[2],sys.argv[4]); return 0
    parser=argparse.ArgumentParser(); modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--native-checkpoint-only',action='store_true')
    modes.add_argument('--native-source-integration-only',action='store_true',help='fixed checkpoint to private synthetic source only')
    parser.add_argument('--evidence-root',type=pathlib.Path,required=True)
    parser.add_argument('--binary-path',type=pathlib.Path,required=True)
    parser.add_argument('--endpoint',required=True); parser.add_argument('--case',choices=sorted(native.CASES),required=True)
    args=parser.parse_args(); receipt=run(args)
    print(json.dumps({'passed':receipt['passed'],'case':getattr(args,'case',None),'fixture':receipt['fixture'],
        'failure_code':receipt.get('failure_code'),'qualification_flags':False},sort_keys=True))
    return 0 if receipt['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
