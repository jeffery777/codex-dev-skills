#!/usr/bin/env python3
"""Opt-in fixed anonymous project-config/hook controls on macOS Docker.

Only verified public CLI bytes and fresh synthetic scratch are mounted. No
login, real provider, pull, stop, removal, restart or complete qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import tomllib
import types


def load_fixture(path):
    """Compile host expectations from the exact captured guest source bytes."""
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 0<info.st_size<=262144:raise ValueError('bounded regular fixture source required')
        raw=stream.read(262145)
    if len(raw)>262144:raise ValueError('bounded fixture source required')
    program=raw.decode('utf-8');module=types.ModuleType('captured_project_hook_fixture')
    module.__file__=str(path)
    exec(compile(program,str(path),'exec'),module.__dict__)
    return module,program

_paths=list(sys.path)
try:
    _spec=importlib.util.spec_from_file_location('project_control_support',pathlib.Path(__file__).with_name('verify-model-isolation-path-controls.py'))
    support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)
    fixture,PROGRAM=load_fixture(pathlib.Path(__file__).with_name('model_project_hook_fixture.py'))
finally:sys.path[:]=_paths
backend=support.backend


def command(binary,workspace,phase,cidfile,program=PROGRAM):
    if phase not in ('positive','negative'):raise ValueError('fixed hook phase required')
    return ['docker','create','--cidfile',str(cidfile),'--pull=never','--read-only','--network=none',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--user=1000:1000','--pids-limit=64',
        '--memory=512m','--cpus=1','--restart=no','--tmpfs=/tmp:rw,noexec,nosuid,size=32m,mode=1777',
        '--mount',f'type=bind,src={binary},dst=/fixture/codex,readonly',
        '--mount',f'type=bind,src={workspace},dst=/workspace','--entrypoint=/usr/bin/env',
        backend.IMAGE,'-i','PATH=/usr/local/bin:/usr/bin:/bin','HOME=/tmp/anonymous-home',
        'CODEX_HOME=/tmp/anonymous-home','python3','-I','-S','-B','-c',program,phase]


def validate_policy(value,cid,argv,binary,workspace,state):
    expected={'id':cid,'image':backend.IMAGE,'entrypoint':['/usr/bin/env'],'command':argv[argv.index(backend.IMAGE)+1:],
        'user':'1000:1000','readonly':True,'network':'none','caps':['ALL'],'security':['no-new-privileges'],
        'restart':{'Name':'no','MaximumRetryCount':0},'pids':64,'memory':536870912,'cpus':1000000000,
        'tmpfs':{'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},'privileged':False,'pid_mode':'','ipc_mode':'private',
        'userns_mode':'','cgroupns_mode':'private','devices':[],'device_requests':None,'volumes_from':None,
        'state':state,'running':False,'pid':0,'exit':0,'oom':False}
    if type(value) is not dict or set(value)!=set(support.FIELDS) or any(type(value[k]) is not type(v) or value[k]!=v for k,v in expected.items()):raise ValueError('fixed hook policy mismatch')
    mounts=value['mounts']
    if (type(mounts) is not list or len(mounts)!=2 or any(m.get('Type')!='bind' or m.get('Propagation')!='rprivate' for m in mounts)
            or {(m.get('Source'),m.get('Destination'),m.get('RW')) for m in mounts}!={(str(binary),'/fixture/codex',False),(str(workspace),'/workspace',True)}):raise ValueError('exact binary/scratch mounts required')


def validate_evidence(value,workspace,phase):
    if (type(value) is not dict or value.get('schema')!=1 or type(value.get('schema')) is not int
            or value.get('phase')!=phase or value.get('source_pin')!=fixture.SOURCE_PIN
            or any(value.get(k) is not False for k in ('production_qualified','startup_isolation_qualified','hook_trust_qualified'))
            or type(value.get('cli_exit')) is not int or value['cli_exit']!=0 or value.get('errors')!=[]
            or type(value.get('requests')) is not list or len(value['requests'])!=2
            or type(value.get('outputs')) is not list or len(value['outputs'])!=1):raise ValueError('fixed hook evidence envelope mismatch')
    expected_call={'type':'function_call','namespace':'functions','name':'exec_command','call_id':'project-hook-0',
        'arguments':json.dumps({'cmd':fixture.TOOL_COMMAND,'login':False,'yield_time_ms':1000,'max_output_tokens':1000})}
    if value.get('call')!=expected_call:raise ValueError('fixed native call mismatch')
    expected_inventory=[dict(path=p,exists=False,symlink=False,canonical=True) for p in fixture.STARTUP_PATHS]
    if (value.get('inventory')!=expected_inventory or any(type(row[k]) is not bool for row in value['inventory'] for k in ('exists','symlink','canonical'))
            or value.get('project_config')!=fixture.project_config() or value.get('argv')!=fixture.cli_argv()):raise ValueError('fixed config/argv/inventory mismatch')
    config=workspace/'project/.codex/config.toml'
    if config.is_symlink() or not config.is_file() or config.stat().st_size>8192 or config.read_text()!=fixture.project_config():raise ValueError('actual project config drift')
    if type(value.get('user_config')) is not str or len(value['user_config'])>8192:raise ValueError('bounded synthetic user config required')
    parsed=tomllib.loads(value['user_config']);url=parsed.get('model_providers',{}).get('fixture',{}).get('base_url','')
    match=backend.re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{0,4})/v1',url)
    if match is None or value['user_config']!=fixture.user_config(int(match[1]),phase):raise ValueError('fixed anonymous user config mismatch')
    for request in value['requests']:
        if type(request) is not dict or request.get('model')!='fixture-direct' or type(request.get('input')) is not list:raise ValueError('fixed request mismatch')
    continuations=[x for x in value['requests'][1]['input'] if type(x) is dict and x.get('type')=='function_call_output' and x.get('call_id')==expected_call['call_id']]
    if len(continuations)!=1 or continuations[0].get('output')!=value['outputs'][0]:raise ValueError('exact native continuation missing')
    declarations=[backend.manifest.advertised_tools(backend.manifest.canonical(request))['advertised_tools'] for request in value['requests']]
    expected={('functions','exec_command','function'),('functions','write_stdin','function'),('functions','apply_patch','custom')}
    if any({(t['namespace'],t['name'],t['type']) for t in row}!=expected for row in declarations) or declarations[0]!=declarations[1]:raise ValueError('fixed advertisement drift')
    text=backend.text_output(value['outputs'][0])
    if text.splitlines().count('Process exited with code 0')!=1 or 'Process running with session ID' in text:raise ValueError('fixed tool did not finish')
    marker=workspace/'project/tool-marker'
    if marker.is_symlink() or not marker.is_file() or marker.read_bytes()!=b'project-tool-control\n':raise ValueError('tool positive readback missing')
    hook=workspace/'project/hook-marker.json'
    if phase=='negative':
        if hook.exists() or hook.is_symlink():raise ValueError('unconfigured hook effect')
    else:
        if hook.is_symlink() or not hook.is_file() or hook.stat().st_size>65536:raise ValueError('bounded hook positive missing')
        payload=json.loads(hook.read_text())
        if type(payload) is not dict or payload.get('hook_event_name')!='PreToolUse' or payload.get('tool_name')!='Bash' or payload.get('tool_input')!={'command':fixture.TOOL_COMMAND}:raise ValueError('fixed hook event identity mismatch')
    return True


def execute(engine,root,binary,workspace,phase,previous=None,program=PROGRAM):
    cidfile=root/(phase+'-cid');argv=command(binary,workspace,phase,cidfile,program)
    (root/(phase+'-create-intent.json')).write_text(json.dumps({'argv':argv,'replayed':False},indent=2)+'\n')
    backend.check_binary(binary)
    try:cid=engine.call(argv)
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'create-result-unknown','error_type':type(error).__name__,'replayed':False,'started':False}
        if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
            uncertain=cidfile.read_text().strip()
            if backend.re.fullmatch('[a-f0-9]{64}',uncertain):
                recovery['id']=uncertain
                try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',uncertain])
                except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/(phase+'-unknown-create.json')).write_text(json.dumps(recovery,indent=2)+'\n')
        raise
    if not backend.re.fullmatch('[a-f0-9]{64}',cid) or cidfile.read_text().strip()!=cid or cid==previous:raise ValueError('own hook CID mismatch')
    def inspect():return json.loads(engine.call(['docker','inspect','--format',support.FORMAT,cid]))
    before=inspect();(root/(phase+'-before.json')).write_text(json.dumps(before,indent=2)+'\n');validate_policy(before,cid,argv,binary,workspace,'created')
    backend.check_binary(binary)
    (root/(phase+'-start-intent.json')).write_text(json.dumps({'id':cid,'replayed':False})+'\n')
    try:
        if engine.call(['docker','start',cid])!=cid:raise ValueError('start CID mismatch')
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'start-result-unknown','id':cid,'error_type':type(error).__name__,'replayed':False,'passed':False}
        try:recovery['exact_readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',cid])
        except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/(phase+'-unknown-start.json')).write_text(json.dumps(recovery,indent=2)+'\n');raise
    status=engine.call(['docker','wait',cid]);after=inspect()
    (root/(phase+'-after.json')).write_text(json.dumps(after,indent=2)+'\n');validate_policy(after,cid,argv,binary,workspace,'exited')
    if status!='0':raise ValueError('hook container did not exit naturally')
    raw=engine.call(['docker','logs',cid])
    if len(raw)>32768:raise ValueError('bounded hook stdout required')
    (root/(phase+'-output.jsonl')).write_text(raw+'\n')
    evidence=workspace/'project-hook-evidence.json'
    if evidence.is_symlink() or not evidence.is_file() or evidence.stat().st_size>4*1024*1024:raise ValueError('bounded hook evidence required')
    value=json.loads(evidence.read_text());validate_evidence(value,workspace,phase)
    return {'id':cid,'phase':phase,'evidence_sha256':hashlib.sha256(evidence.read_bytes()).hexdigest()}


def run(binary_path,evidence_root):
    parent=backend.evidence_root(evidence_root);data=backend.capture_binary(binary_path)
    root=pathlib.Path(tempfile.mkdtemp(prefix='project-hook-control-',dir=parent));binary=backend.save_binary(root,data);del data
    program=PROGRAM
    workspaces=[root/name for name in ('positive','negative')]
    for path in workspaces:path.mkdir();path.chmod(0o777)
    engine=backend.LocalDesktop();identity=engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    positive=execute(engine,root,binary,workspaces[0],'positive',program=program)
    negative=execute(engine,root,binary,workspaces[1],'negative',positive['id'],program=program)
    if engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=identity:raise ValueError('engine identity drift')
    receipt={'fixed_project_hook_controls_passed':True,'startup_isolation_qualified':False,'hook_trust_qualified':False,
        'production_qualified':False,'root':str(root),'image':backend.IMAGE,'binary_sha256':backend.BINARY_SHA256,
        'program_sha256':hashlib.sha256(program.encode()).hexdigest(),
        'phases':[positive,negative],'limits':['fixed trusted-user vs modified-state hook control; no hook-trust bypass',
            'not complete config closure/registry/native session/nested CLI/credentials/production observer']}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'root':str(root),'fixed_project_hook_controls_passed':True,'production_qualified':False}))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binary',required=True);parser.add_argument('--evidence-root',default='/private/tmp')
    args=parser.parse_args();raise SystemExit(run(args.binary,args.evidence_root))
