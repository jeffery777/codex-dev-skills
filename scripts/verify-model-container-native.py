#!/usr/bin/env python3
"""Opt-in macOS Docker fixture for fixed anonymous native CLI dispatch.

No provider login, network, pull, stop, removal, daemon restart, arbitrary image,
model, command or mounts. Exact recipe checks are limited observations and never
qualify a production dispatcher or a complete runtime handler inventory.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import model_native_container_fixture as fixture
import model_probe_tools as manifest

IMAGE="sha256:3c3afc67f71a5eef90b76ff0cdd68eea7289db310df08e224af4a8cc43630633"
BINARY_SHA256="54a834b6b16d8a01ff80f7f9cee4aedec35a61c90379e088792623bf1b4c1e3d"
CONTEXT="desktop-linux"
ENGINE_ID=re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12} linux')
BINARY_LIMIT=512*1024*1024


def capture_binary(value):
    """Return only verified public bytes; never persist arbitrary source bytes."""
    binary=pathlib.Path(value)
    if not binary.is_absolute() or binary.is_symlink() or binary.resolve(strict=True)!=binary:raise ValueError('fixed absolute regular binary required')
    fd=os.open(binary,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=BINARY_LIMIT:raise ValueError('bounded regular binary required')
        data=stream.read(BINARY_LIMIT+1)
    if len(data)>BINARY_LIMIT or hashlib.sha256(data).hexdigest()!=BINARY_SHA256:raise ValueError('fixed official 0.159.3 Linux arm64 binary required')
    return data


def save_binary(root,data):
    # Private root, trusted sticky ancestors, and a single-file readonly mount
    # exclude other host users and the guest. Host owner/root/daemon are trusted.
    if hashlib.sha256(data).hexdigest()!=BINARY_SHA256:raise ValueError('verified binary bytes required')
    binary=root/'codex'
    with binary.open('xb') as stream:stream.write(data)
    binary.chmod(0o555)
    check_binary(binary)
    return binary


def check_binary(binary):
    info=binary.lstat()
    if (binary.resolve(strict=True)!=binary or not stat.S_ISREG(info.st_mode)
            or info.st_uid!=os.getuid() or info.st_nlink!=1
            or stat.S_IMODE(info.st_mode)!=0o555 or not 0<info.st_size<=BINARY_LIMIT
            or hashlib.sha256(binary.read_bytes()).hexdigest()!=BINARY_SHA256):raise ValueError('protected binary snapshot drift')


def engine_environment():
    # Context metadata and daemon calls must not inherit a remote Docker target.
    return {'PATH':os.environ['PATH'],'HOME':str(pathlib.Path.home())}


def local_endpoint():
    raw=subprocess.check_output(['docker','context','inspect',CONTEXT,'--format','{{json .Endpoints.docker.Host}}'],
        env=engine_environment(),stdin=subprocess.DEVNULL,text=True,timeout=10,close_fds=True)
    expected='unix://'+str(pathlib.Path.home()/'.docker/run/docker.sock')
    if json.loads(raw)!=expected:raise ValueError('verified local Desktop Unix endpoint required')
    return expected


def socket_identity():
    path=pathlib.Path.home()/'.docker/run/docker.sock'
    info=path.lstat()
    if path.resolve(strict=True)!=path or not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():raise ValueError('owned canonical local Desktop socket required')
    return (info.st_dev,info.st_ino,info.st_uid,info.st_mode)


class LocalDesktop:
    """Internal fixed-recipe transport, pinned to a verified Unix socket."""
    def __init__(self):
        self.endpoint=local_endpoint()
        self.socket=socket_identity()
        self.engine_id=None

    def _read(self,argv):
        return subprocess.check_output(['docker','--host',self.endpoint,*argv],env=engine_environment(),
            stdin=subprocess.DEVNULL,text=True,timeout=55,close_fds=True).strip()

    def call(self,argv):
        if argv[0]!='docker' or argv[1] not in ('info','create','inspect','start','wait','logs'):raise ValueError('fixed engine command required')
        if local_endpoint()!=self.endpoint or socket_identity()!=self.socket:raise ValueError('local endpoint identity drift')
        if argv[1] in ('create','start'):
            if self.engine_id is None or self._read(['info','--format','{{.ID}} {{.OSType}}'])!=self.engine_id:raise ValueError('pre-effect engine identity drift')
        value=self._read(argv[1:])
        if argv[1]=='info':
            if not ENGINE_ID.fullmatch(value) or self.engine_id is not None and value!=self.engine_id:raise ValueError('engine identity unavailable or drifted')
            self.engine_id=value
        return value


def advertised(evidence):
    expected={('functions','exec_command','function'),('functions','write_stdin','function'),('functions','apply_patch','custom')}
    records=[manifest.advertised_tools(manifest.canonical(request)) for request in evidence['requests']]
    identities=[{(tool['namespace'],tool['name'],tool['type']) for tool in row['advertised_tools']} for row in records]
    signatures=[[(tool['namespace'],tool['name'],tool['type'],tool['declaration_sha256']) for tool in row['advertised_tools']] for row in records]
    if len(records)!=29 or any(names!=expected for names in identities) or any(s!=signatures[0] for s in signatures):raise ValueError('advertised recipe drift')
    return records


def evidence_root(value):
    path=pathlib.Path(value)
    if sys.platform!='darwin' or path!=pathlib.Path('/private/tmp'):raise ValueError('macOS /private/tmp evidence root required')
    root=path.resolve(strict=True)
    if root!=path:raise ValueError('canonical private temporary evidence root required')
    for parent in (pathlib.Path('/'),pathlib.Path('/private'),root):
        info=parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=0:raise ValueError('trusted temporary ancestors required')
        if parent==root:
            if stat.S_IMODE(info.st_mode)!=0o1777:raise ValueError('sticky system temporary root required')
        elif info.st_mode & 0o022:raise ValueError('non-writable system ancestors required')
    for parent in (root,*root.parents):
        if (parent/'.git').exists():raise ValueError('evidence root inside Git')
    return root


def text_output(value):
 if type(value) is str and len(value)<=32768:return value
 if type(value) is list and len(value)==2 and all(type(x) is dict and set(x)=={'type','text'} and x['type']=='input_text' and type(x['text']) is str for x in value):
  timing=re.fullmatch(r'Wall time: (0|[1-9][0-9]?)\.([0-9]{4}) seconds\nOutput:',value[0]['text'])
  if timing is not None and int(timing[1])*10000+int(timing[2])<=350000 and len(value[1]['text'])<=32768:return value[1]['text']
 raise ValueError('unknown output carrier')

def validate_cases(evidence,workspace):
    expected=dict(zip(("calls","expectations"),fixture.fixed_cases(),strict=True))
    case_checks=[]
    if evidence['calls']!=expected['calls'] or evidence['expectations']!=expected['expectations'] or len(evidence['outputs'])!=28 or len(evidence['requests'])!=29:raise ValueError('fixed host case identity mismatch')
    if [c['call_id'] for c in evidence['calls']]!=['matrix-'+str(i) for i in range(28)]:raise ValueError('fixed case sequence mismatch')
    for stage,request in enumerate(evidence['requests']):
        if type(request) is not dict or request.get('model')!='fixture-direct' or type(request.get('input')) is not list:raise ValueError('fixed request identity mismatch')
        if stage:
            call=evidence['calls'][stage-1]
            kind='function_call_output' if call['type']=='function_call' else 'custom_tool_call_output'
            matches=[item for item in request['input'] if type(item) is dict and item.get('type')==kind and item.get('call_id')==call['call_id']]
            if len(matches)!=1 or matches[0].get('output')!=evidence['outputs'][stage-1]:raise ValueError('host exact continuation mismatch')
    if len(evidence['outputs'])==28:
     for item,expected,raw in zip(evidence['calls'],evidence['expectations'],evidence['outputs'],strict=True):
      text=text_output(raw);kind=expected['kind']
      if kind in ('exec','patch','exec-patch'):
       path=workspace/expected['file'];positive=path.is_file() and not path.is_symlink() and path.stat().st_size==len(expected['content'].encode()) and path.read_bytes()==expected['content'].encode()
       if kind in ('exec','exec-patch'):positive=positive and text.splitlines().count('Process exited with code 0')==1 and 'Process running with session ID' not in text
       if kind=='patch':positive=positive and 'Success. Updated the following files:' in text and expected['file'] in text
      elif kind=='unsupported':
       name=expected['name'];ns=expected['namespace'];flat=name if ns is None else ns+name
       # Pinned ToolName Display concatenates nondefault namespace without a dot.
       positive=text=='unsupported call: '+flat
      elif kind=='escalation-denied':positive='approval policy is Never' in text and 'reject command' in text and 'cannot ask for escalated permissions' in text
      else:raise ValueError('unknown expectation')
      case_checks.append({'call_id':item['call_id'],'kind':kind,'passed':positive})
    return case_checks

def run(args):
    parent=evidence_root(args.evidence_root)
    data=capture_binary(args.binary)
    root=pathlib.Path(tempfile.mkdtemp(prefix='native-container-probe-',dir=parent))
    binary=save_binary(root,data)
    del data
    workspace=root/'workspace';workspace.mkdir(mode=0o777);workspace.chmod(0o777)
    targets=[root/name for name in ['source','control','sibling']]
    for target in targets:target.write_text('host-protected-canary')
    program=pathlib.Path(fixture.__file__).read_text()
    expected=dict(zip(('calls','expectations'),fixture.fixed_cases(),strict=True))
    expected_raw=manifest.canonical(expected)
    (root/'host-recipe.json').write_bytes(expected_raw)

    engine=LocalDesktop()
    call=engine.call
    engine_before=call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    argv=['docker','create','--cidfile',str(root/'container-id'),'--pull=never','--read-only','--network=none','--cap-drop=ALL','--security-opt=no-new-privileges','--user=1000:1000','--pids-limit=64','--memory=512m','--cpus=1','--restart=no','--tmpfs=/tmp:rw,noexec,nosuid,size=32m,mode=1777','--mount',f'type=bind,src={binary},dst=/fixture/codex,readonly','--mount',f'type=bind,src={workspace},dst=/workspace','--entrypoint=/usr/bin/env',IMAGE,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp/anonymous-home','CODEX_HOME=/tmp/anonymous-home','python3','-I','-S','-B','-c',program]
    (root/'create-intent.json').write_text(json.dumps({'image':IMAGE,'binary_sha256':BINARY_SHA256,'argv':argv,'unknown_result_recovery':'inspect exact cidfile only; no create/start replay'},indent=2)+'\n')
    check_binary(binary)
    try:
     cid=call(argv)
    except (OSError,subprocess.SubprocessError) as error:
     recovery={'phase':'create-result-unknown','error_type':type(error).__name__,'root':str(root),'replayed':False,'started':False}
     cidfile=root/'container-id'
     if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
      uncertain=cidfile.read_text().strip()
      if len(uncertain)==64 and all(c in '0123456789abcdef' for c in uncertain):
       recovery['id']=uncertain
       try:recovery['exact_readback']=call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',uncertain])
       except (OSError,subprocess.SubprocessError) as inspect_error:recovery['readback_error_type']=type(inspect_error).__name__
     (root/'unknown-create.json').write_text(json.dumps(recovery,indent=2)+'\n')
     print(json.dumps(recovery),flush=True)
     raise
    if (root/'container-id').read_text().strip()!=cid:raise ValueError('cidfile mismatch')
    if len(cid)!=64 or any(c not in '0123456789abcdef' for c in cid):raise ValueError('invalid own id')
    (root/'created.json').write_text(json.dumps({'id':cid,'image':IMAGE,'binary_sha256':BINARY_SHA256,'argv':argv},indent=2)+'\n')
    fmt='{"image":{{json .Image}},"entrypoint":{{json .Config.Entrypoint}},"command":{{json .Config.Cmd}},"user":{{json .Config.User}},"mounts":{{json .Mounts}},"readonly":{{json .HostConfig.ReadonlyRootfs}},"network":{{json .HostConfig.NetworkMode}},"caps":{{json .HostConfig.CapDrop}},"security":{{json .HostConfig.SecurityOpt}},"restart":{{json .HostConfig.RestartPolicy}},"pids":{{json .HostConfig.PidsLimit}},"memory":{{json .HostConfig.Memory}},"cpus":{{json .HostConfig.NanoCpus}},"tmpfs":{{json .HostConfig.Tmpfs}},"privileged":{{json .HostConfig.Privileged}},"pid_mode":{{json .HostConfig.PidMode}},"ipc_mode":{{json .HostConfig.IpcMode}},"userns_mode":{{json .HostConfig.UsernsMode}},"cgroupns_mode":{{json .HostConfig.CgroupnsMode}},"devices":{{json .HostConfig.Devices}},"device_requests":{{json .HostConfig.DeviceRequests}},"volumes_from":{{json .HostConfig.VolumesFrom}},"state":{{json .State.Status}},"pid":{{json .State.Pid}},"exit":{{json .State.ExitCode}}}'
    def inspect():return json.loads(call(['docker','inspect','--format',fmt,cid]))
    a=inspect(); (root/'before.json').write_text(json.dumps(a,indent=2)+'\n')
    mounts=a['mounts']
    if not (a['image']==IMAGE and a['entrypoint']==['/usr/bin/env'] and a['command']==argv[argv.index(IMAGE)+1:] and a['user']=='1000:1000' and a['readonly'] is True and a['network']=='none' and a['caps']==['ALL'] and a['security']==['no-new-privileges'] and a['restart']['Name']=='no' and a['pids']==64 and a['memory']==536870912 and a['cpus']==1000000000 and a['tmpfs']=={'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'} and len(mounts)==2 and all(m['Type']=='bind' and m['Propagation']=='rprivate' for m in mounts) and {(m['Source'],m['Destination'],m['RW']) for m in mounts}=={(str(binary),'/fixture/codex',False),(str(workspace),'/workspace',True)} and a['privileged'] is False and a['pid_mode']=='' and a['ipc_mode']=='private' and a['userns_mode']=='' and a['cgroupns_mode']=='private' and not a['devices'] and not a['device_requests'] and not a['volumes_from'] and a['state']=='created' and a['pid']==0):raise ValueError('pre-start policy mismatch')
    if call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=engine_before:raise ValueError('pre-start engine identity drift')
    check_binary(binary)
    if call(['docker','start',cid])!=cid:raise ValueError('start readback mismatch')
    exit_status=call(['docker','wait',cid]); logs=call(['docker','logs',cid]);(root/'fixture-output.jsonl').write_text(logs+'\n')
    b=inspect();(root/'after.json').write_text(json.dumps(b,indent=2)+'\n')
    if {k:v for k,v in a.items() if k not in ('state','pid','exit')}!={k:v for k,v in b.items() if k not in ('state','pid','exit')}:raise ValueError('post-run policy drift')
    records=[json.loads(line) for line in logs.splitlines()]
    evidence_path=workspace/'dispatch-evidence.json'
    if not evidence_path.is_file() or evidence_path.is_symlink() or evidence_path.stat().st_size>8*1024*1024:raise ValueError('missing bounded evidence')
    evidence=json.loads(evidence_path.read_text())

    case_checks=validate_cases(evidence,workspace)
    records=advertised(evidence)
    (root/'advertisement.json').write_text(json.dumps(records,indent=2)+'\n')
    engine_after=call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    checks={'natural_exit':exit_status=='0' and b['state']=='exited' and b['pid']==0 and b['exit']==0,'cli_exit':evidence['cli_exit']==0,'exact_continuations':evidence['errors']==[],'all_fixed_cases':len(case_checks)==28 and all(c['passed'] is True for c in case_checks),'no_forbidden_effects':all(not (workspace/name).exists() and not (workspace/name).is_symlink() for name in ['forbidden-marker','forbidden-escalation']),'host_canaries':all(p.read_text()=='host-protected-canary' for p in targets),'advertisement_stable':len(records)==29,'engine_identity_stable':engine_before==engine_after}
    receipt={'fixture_passed':all(value is True for value in checks.values()),'handler_inventory_complete':False,'startup_isolation_qualified':False,'production_qualified':False,'id':cid,'root':str(root),'image':IMAGE,'binary_sha256':BINARY_SHA256,'binary_snapshot':str(binary),'worker_sha256':hashlib.sha256(program.encode()).hexdigest(),'host_case_recipe_sha256':hashlib.sha256(expected_raw).hexdigest(),'engine_identity':engine_before,'checks':checks,'case_checks':case_checks,'observer_limit':'fixed provider and CLI share UID; not trusted production observer','not_run':['full-registry','startup-all-config-fence','native-session','nested-cli','hooks','credentials','company','desktop','production']}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'root':str(root),'fixture_passed':receipt['fixture_passed'],'cases':len(case_checks),'failed_checks':[key for key,value in checks.items() if value is not True],'production_qualified':False}))
    return 0 if receipt['fixture_passed'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',required=True,help='Existing exact official 0.159.3 Linux arm64 binary; no install/download')
    parser.add_argument('--evidence-root',default='/private/tmp')
    return run(parser.parse_args())


if __name__=='__main__':
    raise SystemExit(main())
