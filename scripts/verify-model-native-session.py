#!/usr/bin/env python3
"""Opt-in fixed anonymous two-thread CLI terminal controls on macOS Docker."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import uuid

_paths=list(sys.path)
try:
    _spec=importlib.util.spec_from_file_location('session_control_support',pathlib.Path(__file__).with_name('verify-model-project-hook.py'))
    support=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(support)
    fixture,PROGRAM=support.load_fixture(pathlib.Path(__file__).with_name('model_native_session_fixture.py'))
finally:sys.path[:]=_paths
backend=support.backend

def command(binary,workspace,cidfile,program=PROGRAM):
    argv=support.command(binary,workspace,'positive',cidfile,program)
    return argv[:-1]

def thread_id(value):
    if type(value) is not str or len(value.encode())>1048576:raise ValueError('bounded CLI JSON required')
    lines=value.splitlines()
    if len(lines)>128:raise ValueError('bounded CLI event count required')
    rows=[json.loads(line) for line in lines]
    threads=[x.get('thread_id') for x in rows if type(x) is dict and x.get('type')=='thread.started']
    if len(threads)!=1 or type(threads[0]) is not str or str(uuid.UUID(threads[0]))!=threads[0]:raise ValueError('one canonical CLI thread required')
    return threads[0]

def validate_evidence(value,workspace):
    if (type(value) is not dict or type(value.get('schema')) is not int or value['schema']!=1 or value.get('source_pin')!=fixture.SOURCE_PIN
            or value.get('production_qualified') is not False or value.get('native_session_qualified') is not False
            or value.get('errors')!=[] or type(value.get('streams')) is not dict or set(value['streams'])!={'a','b'}
            or type(value.get('cli')) is not dict or set(value['cli'])!={'a','b'}):raise ValueError('fixed native session envelope required')
    expected_paths=['/etc/codex/config.toml','/etc/codex/requirements.toml','/etc/codex/managed_config.toml','/config.toml','/.codex/config.toml','/workspace/config.toml','/workspace/.codex/config.toml',*[f'/tmp/session-home-{phase}/{name}' for phase in ('a','b') for name in ('config.toml','managed_config.toml','auth.json')]]
    inventory=value.get('inventory')
    if inventory!=[dict(path=p,exists=False,symlink=False,canonical=True) for p in expected_paths] or any(type(row[k]) is not bool for row in inventory for k in ('exists','symlink','canonical')):raise ValueError('fixed startup metadata required')
    streams=value['streams'];a=streams['a'];b=streams['b']
    for row in (a,b):
        if type(row) is not dict or set(row)!={'calls','requests','outputs'} or any(type(row[k]) is not list for k in row) or len(row['calls'])!=len(row['outputs']) or len(row['requests'])!=len(row['calls'])+1:raise ValueError('complete bounded native continuations required')
    if len(a['calls']) not in (4,5) or len(b['calls'])!=1:raise ValueError('fixed session sequence required')
    start=fixture.parse_output(a['outputs'][0]);polled=fixture.parse_output(a['outputs'][1])
    if start['status']!='running' or start['body'].replace('\r\n','\n')!='SESSION_READY\n' or polled!={'status':'running','sid':start['sid'],'body':''}:raise ValueError('live process and destructive poll positive required')
    sid=start['sid'];expected=[fixture.call(0,'exec_command',{'cmd':fixture.TOOL_COMMAND,'tty':True,'login':False,'yield_time_ms':1000,'max_output_tokens':512}),fixture.poll(1,sid),fixture.poll(2,sid,fixture.INPUT)]
    first=fixture.parse_output(a['outputs'][2]);body=first['body']
    if first['status']=='running':
        if len(a['calls'])!=5 or first['sid']!=sid:raise ValueError('bounded live process identity required')
        final=fixture.parse_output(a['outputs'][3]);expected.append(fixture.poll(3,sid));body+=final['body']
    else:
        if len(a['calls'])!=4:raise ValueError('unexpected extra poll')
        final=first
    expected.append(fixture.poll(4,sid))
    body=body.replace('\r\n','\n')
    if a['calls']!=expected or final['status']!='exited' or body not in ('SESSION_ACK\n',fixture.INPUT+'SESSION_ACK\n'):raise ValueError('one exact input/ACK and natural terminal exit required')
    error='write_stdin failed: Unknown process id '+str(sid)
    if a['outputs'][-1]!=error or b['calls']!=[fixture.poll('b',sid,fixture.OTHER_INPUT)] or b['outputs']!=[error]:raise ValueError('cross-thread and closed-ID negative controls required')
    declarations=[];thread_ids=[];ports=[]
    for phase in ('a','b'):
        row=streams[phase];cli=value['cli'][phase]
        if type(cli) is not dict or type(cli.get('exit')) is not int or cli['exit']!=0:raise ValueError('successful native CLI required')
        argv=cli.get('argv')
        if type(argv) is not list or any(type(x) is not str for x in argv):raise ValueError('fixed CLI argv required')
        settings=[argv[i+1] for i,x in enumerate(argv[:-1]) if x=='-c'];providers=[x for x in settings if x.startswith('model_providers.fixture=')]
        if len(providers)!=1:raise ValueError('one fixed anonymous provider required')
        match=backend.re.search(r'base_url="http://127\.0\.0\.1:([1-9][0-9]{0,4})/v1"',providers[0])
        if match is None or argv!=fixture.cli_argv(int(match[1])):raise ValueError('fixed loopback argv required')
        ports.append(int(match[1]))
        thread_ids.append(thread_id(cli.get('stdout')))
        for stage,request in enumerate(row['requests']):
            if type(request) is not dict or request.get('model')!='fixture-direct' or type(request.get('input')) is not list:raise ValueError('fixed native request required')
            if stage:
                call=row['calls'][stage-1];matches=[x for x in request['input'] if type(x) is dict and x.get('type')=='function_call_output' and x.get('call_id')==call['call_id']]
                if len(matches)!=1 or matches[0].get('output')!=row['outputs'][stage-1]:raise ValueError('exact original continuation required')
            declarations.append(backend.manifest.advertised_tools(backend.manifest.canonical(request))['advertised_tools'])
    if thread_ids[0]==thread_ids[1] or ports[0]==ports[1]:raise ValueError('distinct CLI threads and providers required')
    expected_tools={('functions','exec_command','function'),('functions','write_stdin','function'),('functions','apply_patch','custom')}
    if any({(t['namespace'],t['name'],t['type']) for t in row}!=expected_tools or row!=declarations[0] for row in declarations):raise ValueError('fixed advertisement drift')
    marker=workspace/'session-marker'
    if marker.is_symlink() or not marker.is_file() or marker.read_bytes()!=b'session-ack-control\n':raise ValueError('one exact scratch effect required')
    return {'sid':sid,'cli_threads':thread_ids,'input_sent_once':True,'calls':len(a['calls'])+1}

def execute(engine,root,binary,workspace,program=PROGRAM):
    cidfile=root/'cid';argv=command(binary,workspace,cidfile,program)
    (root/'create-intent.json').write_text(json.dumps({'argv':argv,'replayed':False},indent=2)+'\n');backend.check_binary(binary)
    try:cid=engine.call(argv)
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'create-result-unknown','error_type':type(error).__name__,'replayed':False,'started':False}
        if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
            uncertain=cidfile.read_text().strip()
            if backend.re.fullmatch('[a-f0-9]{64}',uncertain):
                recovery['id']=uncertain
                try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',uncertain])
                except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/'unknown-create.json').write_text(json.dumps(recovery,indent=2)+'\n');raise
    if not backend.re.fullmatch('[a-f0-9]{64}',cid) or cidfile.read_text().strip()!=cid:raise ValueError('own session CID required')
    def inspect():return json.loads(engine.call(['docker','inspect','--format',support.support.FORMAT,cid]))
    before=inspect();(root/'before.json').write_text(json.dumps(before,indent=2)+'\n');support.validate_policy(before,cid,argv,binary,workspace,'created');backend.check_binary(binary)
    (root/'start-intent.json').write_text(json.dumps({'id':cid,'replayed':False})+'\n')
    try:
        if engine.call(['docker','start',cid])!=cid:raise ValueError('start CID mismatch')
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'start-result-unknown','id':cid,'error_type':type(error).__name__,'replayed':False,'passed':False}
        try:recovery['exact_readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',cid])
        except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/'unknown-start.json').write_text(json.dumps(recovery,indent=2)+'\n');raise
    status=engine.call(['docker','wait',cid]);after=inspect();(root/'after.json').write_text(json.dumps(after,indent=2)+'\n');support.validate_policy(after,cid,argv,binary,workspace,'exited')
    if status!='0':raise ValueError('session container did not exit naturally')
    raw=engine.call(['docker','logs',cid])
    if len(raw)>32768:raise ValueError('bounded session logs required')
    (root/'output.jsonl').write_text(raw+'\n');path=workspace/'native-session-evidence.json'
    if path.is_symlink() or not path.is_file() or path.stat().st_size>4*1024*1024:raise ValueError('bounded native evidence required')
    checks=validate_evidence(json.loads(path.read_text()),workspace)
    return {'id':cid,'checks':checks,'evidence_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def run(binary_path,evidence_root):
    parent=backend.evidence_root(evidence_root);data=backend.capture_binary(binary_path)
    root=pathlib.Path(tempfile.mkdtemp(prefix='native-session-control-',dir=parent));binary=backend.save_binary(root,data);del data
    workspace=root/'workspace';workspace.mkdir();workspace.chmod(0o777)
    engine=backend.LocalDesktop();identity=engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    result=execute(engine,root,binary,workspace)
    if engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=identity:raise ValueError('engine identity drift')
    receipt={'fixed_native_session_controls_passed':True,'native_session_qualified':False,'production_qualified':False,'root':str(root),'image':backend.IMAGE,'binary_sha256':backend.BINARY_SHA256,'program_sha256':hashlib.sha256(PROGRAM.encode()).hexdigest(),'result':result,'limits':['fixed TTY/live poll/input/natural exit/cross-thread/closed-ID controls only','not non-TTY/nested CLI/full registry/credentials/restart/production observer']}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'root':str(root),'fixed_native_session_controls_passed':True,'production_qualified':False}));return 0

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binary',required=True);p.add_argument('--evidence-root',default='/private/tmp');a=p.parse_args();raise SystemExit(run(a.binary,a.evidence_root))
