#!/usr/bin/env python3
"""Opt-in fixed anonymous nested CLI controls on the local macOS Docker engine."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import uuid

_paths=list(sys.path)
try:
    _spec=importlib.util.spec_from_file_location('nested_control_support',pathlib.Path(__file__).with_name('verify-model-native-session.py'))
    base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(base)
    fixture,SOURCE=base.support.load_fixture(pathlib.Path(__file__).with_name('model_nested_cli_fixture.py'))
finally:sys.path[:]=_paths
backend=base.backend
PROGRAM='FIXTURE_SOURCE='+repr(SOURCE)+'\n'+SOURCE

class CanaryMismatch(ValueError):
    """Observed identity or bytes mismatch, distinct from unavailable readback."""

def command(binary,workspace,cidfile,program=PROGRAM):
    return base.support.command(binary,workspace,'positive',cidfile,program)[:-1]

def canonical(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def canary_record(path):
    info=path.lstat()
    if path.resolve(strict=True)!=path or not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode)!=0o600 or info.st_uid!=os.getuid() or not 0<info.st_size<=1024:raise CanaryMismatch('owned private canary identity changed')
    return {'path':str(path),'dev':info.st_dev,'ino':info.st_ino,'uid':info.st_uid,'mode':info.st_mode,'size':info.st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def create_canaries(root):
    directory=root/'host-canaries';directory.mkdir(mode=0o700)
    rows=[]
    for name in ('source','control','sibling'):
        path=directory/name
        with path.open('xb') as stream:stream.write(('fixed synthetic '+name+' canary\n').encode())
        path.chmod(0o600);rows.append(canary_record(path))
    return rows

def check_canaries(rows):
    if type(rows) is not list or len(rows)!=3 or len({x['path'] for x in rows})!=3:raise ValueError('three independent canaries required')
    if any(canary_record(pathlib.Path(row['path']))!=row for row in rows):raise CanaryMismatch('confirmed host canary drift')

def observations(path):
    """Read complete bounded prefix records; retain a prior violation on truncation."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size>16384:raise ValueError('bounded observation journal required')
    raw=path.read_bytes();lines=raw.splitlines(keepends=True)
    if len(lines)>8:raise ValueError('fixed observation count required')
    result=[]
    for line in lines:
        if not line.endswith(b'\n'):break
        try:row=json.loads(line)
        except (UnicodeError,ValueError):break
        if type(row) is not dict:break
        result.append(row)
    return result

def observation_header(phase,marker,thread):
    return {'schema':1,'source_pin':fixture.SOURCE_PIN,'phase':phase,'call_id':'nested-'+phase+'-1','marker':marker,'marker_matches':marker==(fixture.MARKER if phase=='positive' else None),'thread_env':thread}

def started_thread(raw):
    """Partial CLI output may retain its complete initial identity on timeout."""
    if type(raw) is not str or len(raw.encode())>1048576:raise ValueError('bounded partial CLI output required')
    found=[]
    for line in raw.splitlines(keepends=True):
        if not line.endswith('\n'):break
        try:row=json.loads(line)
        except ValueError:break
        if type(row) is dict and row.get('type')=='thread.started':found.append(row.get('thread_id'))
    if len(found)!=1 or type(found[0]) is not str or str(uuid.UUID(found[0]))!=found[0]:raise ValueError('one original CLI identity required')
    return found[0]

def classify_incomplete(workspace,canaries):
    outcome='unknown'
    try:check_canaries(canaries)
    except CanaryMismatch:outcome='failed'
    except (OSError,ValueError):pass
    try:
        observed=fixture.read_json(workspace/'wrapper-environment.json',8192)
        thread=started_thread(read_text(workspace/'parent-stdout.jsonl'))
        if (type(observed) is dict and type(observed.get('schema')) is int and observed['schema']==1
                and observed.get('source_pin')==fixture.SOURCE_PIN and observed.get('phase')=='parent'
                and observed.get('call_id')=='nested-parent-0' and type(observed.get('native')) is dict
                and observed['native'].get('CODEX_THREAD_ID')==thread
                and 'marker' in observed and (observed['marker'] is None or type(observed['marker']) is str)
                and observed.get('marker_matches') is False and observed.get('marker')!=fixture.MARKER):
            outcome='failed'
    except (OSError,ValueError,KeyError):pass
    for phase in fixture.PHASES[1:]:
        try:
            work=workspace/phase;rows=observations(work/'probe-observations.jsonl')
            if not rows:continue
            thread=started_thread(read_text(work/(phase+'-stdout.jsonl')))
            first=rows[0]
            if type(first.get('schema')) is not int or first.get('marker') is not None and type(first['marker']) is not str or first!=observation_header(phase,first.get('marker'),thread):continue
            if first['marker_matches'] is False:outcome='failed'
            expected=[dict(path=x['path'],operation=op,outcome='denied') for x in canaries for op in ('read','write')]
            if len(rows)>1 and rows[1]=={'scratch':True}:
                for actual,want in zip(rows[2:],expected):
                    if actual==dict(want,outcome='opened'):outcome='failed'
                    elif actual!=want:break
        except (OSError,ValueError,KeyError):pass
    return outcome

def read_text(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>1048576:raise ValueError('bounded regular CLI output required')
    return path.read_text()

def validate_stream(row,phase,expected_calls):
    if type(row) is not dict or set(row)!={'calls','requests','outputs','errors'} or row['errors']!=[] or any(type(row[k]) is not list for k in row):raise ValueError('fixed stream required')
    if row['calls']!=expected_calls or len(row['outputs'])!=len(expected_calls) or len(row['requests'])!=len(expected_calls)+1:raise ValueError('complete exact tool cycle required')
    declarations=[]
    for stage,request in enumerate(row['requests']):
        if type(request) is not dict or request.get('model')!=fixture.model(phase) or type(request.get('input')) is not list:raise ValueError('actual fixed request model required')
        if stage:
            call=expected_calls[stage-1];matches=[x for x in request['input'] if type(x) is dict and x.get('type')=='function_call_output' and x.get('call_id')==call['call_id']]
            if len(matches)!=1 or matches[0].get('output')!=row['outputs'][stage-1]:raise ValueError('exact original continuation required')
        declarations.append(backend.manifest.advertised_tools(backend.manifest.canonical(request))['advertised_tools'])
    expected={('functions','exec_command','function'),('functions','write_stdin','function'),('functions','apply_patch','custom')}
    if any({(t['namespace'],t['name'],t['type']) for t in d}!=expected or d!=declarations[0] for d in declarations):raise ValueError('per-turn advertisement drift')
    return declarations[0]

def validate_evidence(value,workspace,canaries):
    check_canaries(canaries)
    if (type(value) is not dict or type(value.get('schema')) is not int or value['schema']!=1 or value.get('source_pin')!=fixture.SOURCE_PIN
            or any(value.get(k) is not False for k in ('handler_inventory_complete','startup_isolation_qualified','nested_cli_qualified','production_qualified'))
            or type(value.get('streams')) is not dict or set(value['streams'])!=set(fixture.PHASES)
            or type(value.get('ports')) is not dict or set(value['ports'])!=set(fixture.PHASES)):
        raise ValueError('fixed partial-qualification envelope required')
    inventory=[dict(path=p,exists=False,symlink=False,canonical=True) for p in fixture.startup_paths()]
    if value.get('inventory')!=inventory or any(type(x[k]) is not bool for x in value['inventory'] for k in ('exists','symlink','canonical')):raise ValueError('fixed startup metadata required')
    if len(set(value['ports'].values()))!=3:raise ValueError('independent provider ports required')
    if fixture.read_json(workspace/'canary-paths.json',8192)!=[x['path'] for x in canaries]:raise ValueError('host-owned canary path binding required')
    parent=value['streams']['parent']
    if type(parent.get('outputs')) is not list or not 2<=len(parent['outputs'])<=25:raise ValueError('bounded parent cycle required')
    first=fixture.parse_output(parent['outputs'][0]);sid=first['sid']
    if first['status']!='running' or first['body']!='NESTED_READY\n':raise ValueError('live wrapper positive required')
    expected=[fixture.exec_call('parent'),*[fixture.poll('parent',i,sid) for i in range(1,len(parent['outputs']))]]
    declarations=[validate_stream(parent,'parent',expected)]
    tail=[fixture.parse_output(x) for x in parent['outputs'][1:]]
    if tail[-1]['status']!='exited' or any(x['status']!='running' or x['sid']!=sid for x in tail[:-1]) or ''.join(x['body'] for x in tail)!='NESTED_ACK\n':raise ValueError('single ACK and natural wrapper exit required')
    release=workspace/'nested-release';staged=workspace/'nested-release-staged'
    for path in (release,staged):
        if path.is_symlink() or not path.is_file() or path.read_bytes()!=fixture.RELEASE:raise ValueError('fixed release required')
    if (release.stat().st_dev,release.stat().st_ino)!=(staged.stat().st_dev,staged.stat().st_ino):raise ValueError('single non-replacing release required')
    threads=[];raw_hashes={}
    for phase in fixture.PHASES:
        work=workspace if phase=='parent' else workspace/phase
        cli=fixture.read_json(work/(phase+'-cli.json'),8192);argv=fixture.cli_argv(value['ports'][phase],phase)
        if (type(cli.get('exit')) is not int or cli['exit']!=0 or cli.get('argv')!=argv or cli.get('timeout')!=(35 if phase=='parent' else 12)
                or type(cli.get('elapsed')) not in (int,float) or not math.isfinite(cli['elapsed']) or not 0<=cli['elapsed']<cli['timeout']):raise ValueError('natural CLI exit within fixed deadline required')
        intent=fixture.read_json(work/(phase+'-spawn-intent.json'),16384)
        if set(intent)!={'argv','replayed','timeout','environment'} or intent.get('argv')!=argv or intent.get('replayed') is not False or intent.get('timeout')!=cli['timeout']:raise ValueError('one non-replayed CLI intent required')
        raw=read_text(work/(phase+'-stdout.jsonl'));thread=base.thread_id(raw);threads.append(thread)
        read_text(work/(phase+'-stderr.txt'))
        raw_hashes[phase]={name:hashlib.sha256((work/(phase+suffix)).read_bytes()).hexdigest() for name,suffix in [('stdout','-stdout.jsonl'),('stderr','-stderr.txt')]}
        if fixture.read_json(work/(phase+'-stream.json'))!=value['streams'][phase]:raise ValueError('original provider readback required')
        if phase!='parent':
            if fixture.read_json(work/'user-config.json',8192)!={'path':str(fixture.home(phase)/'config.toml'),'content':fixture.config()}:raise ValueError('actual controlled user config required')
            row=value['streams'][phase];declarations.append(validate_stream(row,phase,[fixture.poll(phase,0,sid),fixture.exec_call(phase)]))
            if row['outputs'][0]!='write_stdin failed: Unknown process id '+str(sid):raise ValueError('child must reject parent process ID before its own exec')
            result=fixture.read_json(work/'probe.json',8192);output=fixture.parse_output(row['outputs'][1])
            attempts=[dict(path=x['path'],operation=op,outcome='denied') for x in canaries for op in ('read','write')]
            expected_result={'phase':phase,'marker':fixture.MARKER if phase=='positive' else None,'marker_matches':True,'thread_env':thread,'scratch':True,'attempts':attempts}
            if output['status']!='exited' or canonical(json.loads(output['body']))!=canonical(result) or canonical(result)!=canonical(expected_result):raise ValueError('actual child env, scratch and canary controls required')
            expected_observations=[observation_header(phase,expected_result['marker'],thread),{'scratch':True},*attempts]
            journal=work/'probe-observations.jsonl'
            if canonical(observations(journal))!=canonical(expected_observations) or not journal.read_bytes().endswith(b'\n'):raise ValueError('complete original probe observations required')
            marker=work/'probe-marker'
            if marker.is_symlink() or not marker.is_file() or marker.read_bytes()!=b'fixed-nested-probe\n':raise ValueError('child scratch readback required')
    if len(set(threads))!=3 or any(d!=declarations[0] for d in declarations):raise ValueError('distinct threads and common fixed advertisements required')
    observed=fixture.read_json(workspace/'wrapper-environment.json',8192)
    native=observed.get('native')
    if (type(observed.get('schema')) is not int or observed['schema']!=1 or observed.get('source_pin')!=fixture.SOURCE_PIN
            or observed.get('phase')!='parent' or observed.get('call_id')!='nested-parent-0' or observed.get('marker_matches') is not True
            or observed.get('marker')!=fixture.MARKER or observed.get('home')!=str(fixture.home('parent')) or observed.get('codex_home')!=str(fixture.home('parent'))
            or type(native) is not dict or set(native)!=set(fixture.NATIVE_KEYS) or native['CODEX_THREAD_ID']!=threads[0]
            or type(observed.get('keys')) is not list or observed['keys']!=sorted(set(observed['keys'])) or set(observed['keys'])-set(fixture.ENV_KEYS+fixture.NATIVE_KEYS+fixture.SHELL_KEYS)):
        raise ValueError('original wrapper environment/guard readback required')
    for phase in fixture.PHASES:
        work=workspace if phase=='parent' else workspace/phase
        environment=fixture.read_json(work/(phase+'-spawn-intent.json'),16384)['environment']
        expected_env={k:observed[k] for k in ('home','codex_home','marker','native','keys')}
        expected_env.update(home=str(fixture.home(phase)),codex_home=str(fixture.home(phase)))
        if phase=='parent':expected_env={'home':str(fixture.home('parent')),'codex_home':str(fixture.home('parent')),'marker':fixture.MARKER,'native':dict.fromkeys(fixture.NATIVE_KEYS),'keys':sorted(fixture.ENV_KEYS)}
        if environment!=expected_env:raise ValueError('original native guard preservation required')
    return {'sid':sid,'cli_threads':threads,'raw_cli_hashes':raw_hashes,'advertisement_sha256':canonical(declarations[0]),'fixed_nested_cli_controls_passed':True}

def execute(engine,root,binary,workspace,canaries,program=PROGRAM):
    cidfile=root/'cid';argv=command(binary,workspace,cidfile,program)
    fixture.write_json(root/'create-intent.json',{'argv':argv,'replayed':False});backend.check_binary(binary)
    try:cid=engine.call(argv)
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'create-result-unknown','error_type':type(error).__name__,'replayed':False,'started':False}
        if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
            candidate=cidfile.read_text().strip()
            if backend.re.fullmatch('[a-f0-9]{64}',candidate):
                recovery['id']=candidate
                try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',candidate])
                except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        fixture.write_json(root/'unknown-create.json',recovery);raise
    if not backend.re.fullmatch('[a-f0-9]{64}',cid) or cidfile.read_text().strip()!=cid:raise ValueError('own fixed CID required')
    def inspect():return json.loads(engine.call(['docker','inspect','--format',base.support.support.FORMAT,cid]))
    before=inspect();fixture.write_json(root/'before.json',before);base.support.validate_policy(before,cid,argv,binary,workspace,'created');backend.check_binary(binary)
    fixture.write_json(root/'start-intent.json',{'id':cid,'replayed':False})
    try:
        if engine.call(['docker','start',cid])!=cid:raise ValueError('start identity mismatch')
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        recovery={'status':'start-result-unknown','id':cid,'error_type':type(error).__name__,'replayed':False,'passed':False}
        try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',cid])
        except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        fixture.write_json(root/'unknown-start.json',recovery);raise
    status=engine.call(['docker','wait',cid]);after=inspect();fixture.write_json(root/'after.json',after);base.support.validate_policy(after,cid,argv,binary,workspace,'exited')
    raw=engine.call(['docker','logs',cid])
    if len(raw)>32768:raise ValueError('bounded container log required')
    (root/'output.jsonl').write_text(raw+'\n')
    check_canaries(canaries)
    if status!='0':raise ValueError('container natural exit 0 required')
    value=fixture.read_json(workspace/'nested-evidence.json');checks=validate_evidence(value,workspace,canaries);backend.check_binary(binary)
    return {'id':cid,'checks':checks,'evidence_sha256':hashlib.sha256((workspace/'nested-evidence.json').read_bytes()).hexdigest()}

def run(binary_path,evidence_root):
    parent=backend.evidence_root(evidence_root);data=backend.capture_binary(binary_path)
    root=pathlib.Path(tempfile.mkdtemp(prefix='native-nested-control-',dir=parent));binary=backend.save_binary(root,data);del data
    workspace=root/'workspace';workspace.mkdir();workspace.chmod(0o777);canaries=create_canaries(root)
    fixture.write_json(root/'host-canaries.json',canaries);fixture.write_json(workspace/'canary-paths.json',[x['path'] for x in canaries])
    engine=backend.LocalDesktop();identity=engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    try:
        result=execute(engine,root,binary,workspace,canaries)
        if engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=identity:raise ValueError('engine identity drift')
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        outcome=classify_incomplete(workspace,canaries)
        fixture.write_json(root/'incomplete.json',{'root':str(root),'outcome':outcome,'error_type':type(error).__name__,'error':str(error),'lifecycle':'unknown','replayed':False,'production_qualified':False})
        print(json.dumps({'root':str(root),'outcome':outcome,'production_qualified':False}));return 1
    receipt={'fixed_nested_cli_controls_passed':True,'handler_inventory_complete':False,'startup_isolation_qualified':False,'nested_cli_qualified':False,'production_qualified':False,'root':str(root),'image':backend.IMAGE,'binary_sha256':backend.BINARY_SHA256,'source_sha256':hashlib.sha256(SOURCE.encode()).hexdigest(),'program_sha256':hashlib.sha256(PROGRAM.encode()).hexdigest(),'engine':identity,'result':result,'canaries':canaries,'limits':['fixed user model/argv override/native marker/child tool continuations/unmounted host paths only','same UID provider/CLI/wrapper/probe; not trusted production observer','not complete config/layers/registry/descendants/credentials/restart/Desktop/production qualification']}
    fixture.write_json(root/'receipt.json',receipt);print(json.dumps({'root':str(root),'fixed_nested_cli_controls_passed':True,'production_qualified':False}));return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binary',required=True);parser.add_argument('--evidence-root',default='/private/tmp');args=parser.parse_args();raise SystemExit(run(args.binary,args.evidence_root))
