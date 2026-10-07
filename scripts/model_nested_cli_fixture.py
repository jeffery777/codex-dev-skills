"""Fixed anonymous nested CLI controls; observer and qualification stay partial."""
import hashlib
import http.server
import json
import os
import pathlib
import resource
import shlex
import signal
import subprocess
import threading
import time
import uuid

SOURCE_PIN='01fc69f4026735edfdf6789820549727a4867b11'
MARKER='fixed-anonymous-nested-control'
ENV_KEYS=['PATH','HOME','CODEX_HOME','NO_PROXY','no_proxy','NESTED_CONTROL_MARKER']
NATIVE_KEYS=['CODEX_THREAD_ID','CODEX_SESSION_ID','CODEX_VERSION','CODEX_PERMISSION_PROFILE']
SHELL_KEYS=['PWD','SHLVL','_','NO_COLOR','TERM','LANG','LC_CTYPE','LC_ALL','COLORTERM','PAGER','GIT_PAGER','GH_PAGER','CODEX_CI']
PHASES=('parent','positive','negative')
CONTROL=pathlib.Path('/tmp/nested-control')
RELEASE=b'fixed-nested-release\n'
STARTUP_CASES=('clean','config-file','dangling-symlink')
STARTUP_TARGET='/workspace/.codex/config.toml'
STARTUP_LINK='fixed-missing-startup-layer.toml'
STARTUP_BYTES=b'model="fixed-startup-layer-canary"\n'
DEFAULT_ATTEMPT='00000000-0000-4000-8000-000000000000'
CATALOG_ARGV=['/fixture/codex','debug','models','--bundled']
DISABLED=['apps','hooks','plugins','remote_plugin','multi_agent','multi_agent_v2','goals','memories','code_mode','code_mode_only','code_mode_prewarm','enable_request_compression','browser_use','computer_use','image_generation','skill_search','skill_mcp_dependency_install','tool_suggest','daemon_auto_start','view_image','sleep_tool','current_time_reminder','request_permissions_tool','send_message_to_user_async','token_budget','deferred_executor']

def model(phase):
    if phase not in PHASES:raise ValueError('fixed phase required')
    return {'parent':'fixture-parent','positive':'fixture-user','negative':'fixture-override'}[phase]

def home(phase):
    model(phase);return pathlib.Path('/tmp/nested-home-'+phase)

def cwd(phase):
    model(phase);return pathlib.Path('/workspace') if phase=='parent' else pathlib.Path('/workspace')/phase

def cli_argv(port,phase):
    if type(port) is not int or not 1<=port<=65535:raise ValueError('fixed loopback port required')
    model(phase)
    settings=['model_provider="fixture"','model_catalog_json="/tmp/nested-control/catalog.json"',
        'model_providers.fixture={name="Fixed anonymous nested CLI",base_url="http://127.0.0.1:'+str(port)+'/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=10000}',
        'approval_policy="never"','shell_environment_policy.inherit="'+('none' if phase=='negative' else 'all')+'"',
        'shell_environment_policy.ignore_default_excludes=false','shell_environment_policy.include_only='+json.dumps(ENV_KEYS),
        'shell_environment_policy.exclude=[]','shell_environment_policy.set={}',
        'shell_environment_policy.experimental_use_profile=false','web_search="disabled"','notify=[]','agents.enabled=false','tools.experimental_request_user_input.enabled=false','features.code_mode_host={enabled=false,disable_in_process_fallback=false}',*['features.'+x+'=false' for x in DISABLED]]
    if phase!='positive':settings.insert(1,'model="'+model(phase)+'"')
    return ['/fixture/codex','exec','--strict-config',*(['--ignore-user-config'] if phase=='parent' else []),'--ignore-rules','--ephemeral','--skip-git-repo-check','--json','--sandbox','danger-full-access',*[a for s in settings for a in ['-c',s]],'Follow only the fixed synthetic provider.']

def config():return 'model="fixture-user"\n'

def call(phase,index,name,args):
    model(phase)
    return {'type':'function_call','namespace':'functions','name':name,'call_id':'nested-'+phase+'-'+str(index),'arguments':json.dumps(args)}

def poll(phase,index,sid):return call(phase,index,'write_stdin',{'session_id':sid,'chars':'','yield_time_ms':1000,'max_output_tokens':1024})

WRAPPER_COMMAND='/usr/local/bin/python3 -I -S -B /tmp/nested-control/fixture.py wrapper'
PROBE_COMMAND='/usr/local/bin/python3 -I -S -B /tmp/nested-control/fixture.py probe'

def exec_call(phase):
    return call(phase,0 if phase=='parent' else 1,'exec_command',{'cmd':WRAPPER_COMMAND if phase=='parent' else PROBE_COMMAND,'tty':False,'login':False,'yield_time_ms':1000,'max_output_tokens':1024})

def parse_output(value):
    import re
    if type(value) is not str or len(value)>16384:raise ValueError('bounded native string required')
    header,separator,body=value.partition('Output:\n');lines=header.splitlines()
    if separator!='Output:\n' or len(body.encode())>8192 or len(lines) not in (3,4):raise ValueError('bounded native header required')
    if not re.fullmatch(r'Chunk ID: [A-Za-z0-9_-]{1,128}',lines[0]) or not re.fullmatch(r'Wall time: (0|[1-9][0-9]?)\.[0-9]{4} seconds',lines[1]):raise ValueError('fixed native header required')
    if len(lines)==4 and not re.fullmatch(r'Original token count: (0|[1-9][0-9]{0,5})',lines[3]):raise ValueError('bounded token header required')
    match=re.fullmatch(r'Process running with session ID ([1-9][0-9]{3,4})',lines[2])
    if match and 1000<=int(match[1])<=99999:return {'status':'running','sid':int(match[1]),'body':body}
    if lines[2]=='Process exited with code 0':return {'status':'exited','sid':None,'body':body}
    raise ValueError('natural tool exit 0 or live identity required')

def publish_release(work):
    with (work/'nested-release-staged').open('xb') as stream:
        stream.write(RELEASE);stream.flush();os.fsync(stream.fileno())
    os.link(work/'nested-release-staged',work/'nested-release',follow_symlinks=False)

def read_json(path,limit=4*1024*1024):
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=limit:raise ValueError('bounded regular JSON required')
    return json.loads(path.read_text())

def write_json(path,value):
    raw=json.dumps(value,indent=2)+'\n'
    if len(raw.encode())>4*1024*1024:raise ValueError('bounded evidence required')
    with path.open('x') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())

def startup_paths():
    return ['/etc/codex/config.toml','/etc/codex/requirements.toml','/etc/codex/managed_config.toml','/config.toml','/.codex/config.toml','/workspace/config.toml','/workspace/.codex/config.toml',*[str(home(p)/n) for p in PHASES for n in ('config.toml','managed_config.toml','auth.json')],*[str(cwd(p)/'.codex/config.toml') for p in PHASES[1:]]]

class StartupLayerUnknown(ValueError):
    """Only a complete original startup observation can raise this refusal."""

def startup_header(case,attempt):
    if case not in STARTUP_CASES or type(attempt) is not str or str(uuid.UUID(attempt))!=attempt:raise ValueError('fixed startup case and canonical attempt required')
    return {'schema':1,'source_pin':SOURCE_PIN,'case':case,'attempt':attempt}

def startup_row(value):
    path=pathlib.Path(value)
    try:info=path.lstat()
    except FileNotFoundError:exists=False;symlink=False
    else:
        import stat
        symlink=stat.S_ISLNK(info.st_mode)
        if symlink:
            try:path.stat()
            except FileNotFoundError:exists=False
            else:exists=True
        else:exists=True
    return dict(path=value,exists=exists,symlink=symlink,canonical=path.resolve(strict=False)==path)

def observe_startup(work,case,attempt):
    header=startup_header(case,attempt);journal=work/'startup-observations.jsonl'
    with journal.open('x'):pass
    def observe(row):
        fd=os.open(journal,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        with os.fdopen(fd,'w') as stream:
            stream.write(json.dumps(row)+'\n');stream.flush();os.fsync(stream.fileno())
    observe(header);inventory=[]
    for value in startup_paths():
        row=startup_row(value);observe(row);inventory.append(row)
    blocked=any(x['exists'] or x['symlink'] or not x['canonical'] for x in inventory)
    write_json(work/'startup-result.json',dict(header,status='blocked' if blocked else 'clear',journal_sha256=hashlib.sha256(journal.read_bytes()).hexdigest()))
    if blocked:raise StartupLayerUnknown('unknown startup layer')
    return inventory

def env(phase):return {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(home(phase)),'CODEX_HOME':str(home(phase)),'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost','NESTED_CONTROL_MARKER':MARKER}

def probe():
    work=pathlib.Path.cwd();phase=work.name
    if phase not in PHASES[1:]:raise ValueError('fixed child cwd required')
    expected=MARKER if phase=='positive' else None
    marker=os.environ.get('NESTED_CONTROL_MARKER')
    journal=work/'probe-observations.jsonl'
    with journal.open('x'):pass
    def observe(value):
        fd=os.open(journal,os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        with os.fdopen(fd,'w') as stream:
            stream.write(json.dumps(value)+'\n');stream.flush();os.fsync(stream.fileno())
    observe({'schema':1,'source_pin':SOURCE_PIN,'phase':phase,'call_id':'nested-'+phase+'-1','marker':marker,'marker_matches':marker==expected,'thread_env':os.environ.get('CODEX_THREAD_ID')})
    scratch=work/'probe-marker';fd=os.open(scratch,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(b'fixed-nested-probe\n')
    fd=os.open(scratch,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        if stream.read()!=b'fixed-nested-probe\n':raise ValueError('scratch read positive failed')
    fd=os.open(scratch,os.O_WRONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'wb') as stream:stream.write(b'fixed-nested-probe\n')
    observe({'scratch':True})
    attempts=[]
    for path in read_json(pathlib.Path('/workspace/canary-paths.json'),8192):
        for operation,flags in [('read',os.O_RDONLY),('write',os.O_WRONLY)]:
            try:
                fd=os.open(path,flags|os.O_NOFOLLOW)
                with os.fdopen(fd,'rb' if operation=='read' else 'wb') as stream:
                    attempt={'path':path,'operation':operation,'outcome':'opened'};attempts.append(attempt);observe(attempt)
                    if operation=='read':stream.read(32)
                    else:stream.write(b'fixed-nested-canary-violation\n')
            except (FileNotFoundError,PermissionError):
                # A later I/O denial does not revoke an already-observed open.
                if not attempts or attempts[-1].get('path')!=path or attempts[-1].get('operation')!=operation:
                    attempt={'path':path,'operation':operation,'outcome':'denied'};attempts.append(attempt);observe(attempt)
    result={'phase':phase,'marker':marker,'marker_matches':marker==expected,'thread_env':os.environ.get('CODEX_THREAD_ID'),'scratch':True,'attempts':attempts}
    write_json(work/'probe.json',result);print(json.dumps(result),flush=True)

def raw_launch(phase,port,env,timeout):
    work=cwd(phase);argv=cli_argv(port,phase)
    environment={'home':env.get('HOME'),'codex_home':env.get('CODEX_HOME'),'marker':env.get('NESTED_CONTROL_MARKER'),'native':{k:env.get(k) for k in NATIVE_KEYS},'keys':sorted(env)}
    write_json(work/(phase+'-spawn-intent.json'),{'argv':argv,'replayed':False,'timeout':timeout,'environment':environment})
    started=time.monotonic()
    with (work/(phase+'-stdout.jsonl')).open('xb') as out,(work/(phase+'-stderr.txt')).open('xb') as err:
        result=subprocess.run(argv,env=env,cwd=work,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=timeout,close_fds=True)
    elapsed=time.monotonic()-started
    if result.returncode!=0 or elapsed>=timeout:raise ValueError('CLI natural exit within deadline required')
    for name in (phase+'-stdout.jsonl',phase+'-stderr.txt'):
        path=work/name
        if path.is_symlink() or path.stat().st_size>1048576:raise ValueError('bounded raw CLI required')
    value={'argv':argv,'exit':result.returncode,'elapsed':elapsed,'timeout':timeout}
    write_json(work/(phase+'-cli.json'),value);return value

def wrapper():
    signal.signal(signal.SIGALRM,lambda *_:os._exit(124));signal.alarm(32)
    observed={'schema':1,'source_pin':SOURCE_PIN,'phase':'parent','call_id':'nested-parent-0','marker':os.environ.get('NESTED_CONTROL_MARKER'),'marker_matches':os.environ.get('NESTED_CONTROL_MARKER')==MARKER,'home':os.environ.get('HOME'),'codex_home':os.environ.get('CODEX_HOME'),'native':{k:os.environ.get(k) for k in NATIVE_KEYS},'keys':sorted(os.environ)}
    write_json(pathlib.Path('/workspace/wrapper-environment.json'),observed)
    if observed['marker_matches'] is not True:raise ValueError('native parent environment inheritance missing')
    if set(os.environ)-set(ENV_KEYS+NATIVE_KEYS+SHELL_KEYS):raise ValueError('unknown native environment key; no stripping/retry')
    release=pathlib.Path('/workspace/nested-release')
    if release.exists() or release.is_symlink():raise ValueError('fresh release required')
    print('NESTED_READY',flush=True);deadline=time.monotonic()+6
    while not release.exists():
        if time.monotonic()>=deadline:raise ValueError('release deadline')
        time.sleep(0.02)
    if release.is_symlink() or release.read_bytes()!=RELEASE:raise ValueError('fixed release required')
    ports=read_json(CONTROL/'ports.json',8192)
    for phase in PHASES[1:]:
        if (home(phase)/'config.toml').is_symlink() or (home(phase)/'config.toml').read_text()!=config():raise ValueError('actual user model config drift')
        write_json(cwd(phase)/'user-config.json',{'path':str(home(phase)/'config.toml'),'content':(home(phase)/'config.toml').read_text()})
        # Preserve the native synthetic marker and native guard variables;
        # only assign this fresh child's HOME identity. No marker injection.
        env=dict(os.environ)
        env.update(HOME=str(home(phase)),CODEX_HOME=str(home(phase)))
        raw_launch(phase,ports[phase],env,12)
        state=read_json(cwd(phase)/(phase+'-stream.json'))
        result=read_json(cwd(phase)/'probe.json')
        if state.get('errors')!=[] or result.get('marker_matches') is not True or any(x.get('outcome')!='denied' for x in result.get('attempts',[])):raise ValueError('child positive/negative control failed')
    print('NESTED_ACK',flush=True)

def run_fixture(case='clean',attempt=DEFAULT_ATTEMPT):
    resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,4*1024*1024))
    work=pathlib.Path('/workspace');CONTROL.mkdir(mode=0o700)
    inventory=observe_startup(work,case,attempt)
    for phase in PHASES:
        home(phase).mkdir(mode=0o700)
        if phase!='parent':
            cwd(phase).mkdir(mode=0o700);(home(phase)/'config.toml').write_text(config())
    (CONTROL/'fixture.py').write_text(FIXTURE_SOURCE)
    write_json(work/'first-cli-intent.json',dict(startup_header(case,attempt),argv=CATALOG_ARGV,environment=env('parent'),timeout=12,replayed=False))
    seed=subprocess.run(CATALOG_ARGV,env=env('parent'),cwd=work,stdin=subprocess.DEVNULL,capture_output=True,timeout=12,check=True,close_fds=True)
    catalog=json.loads(seed.stdout);models=[m for m in catalog['models'] if m['slug']=='gpt-6-luna']
    if len(models)!=1 or any(m['slug'].startswith('fixture-') for m in catalog['models']):raise ValueError('official catalog drift')
    for phase in PHASES:catalog['models'].append(dict(models[0],slug=model(phase),tool_mode='direct',experimental_supported_tools=[],shell_type='unified_exec',apply_patch_tool_type='freeform',supports_search_tool=False))
    (CONTROL/'catalog.json').write_text(json.dumps(catalog))
    streams={p:{'calls':[],'requests':[],'outputs':[],'errors':[]} for p in PHASES};locks={p:threading.Lock() for p in PHASES};sid=[];servers=[];threads=[]
    def next_call(phase):
        state=streams[phase];stage=len(state['outputs'])
        if phase!='parent':
            if stage==0:
                if len(sid)!=1:raise ValueError('parent live identity unavailable')
                return poll(phase,0,sid[0])
            if stage==1:
                if state['outputs'][0]!='write_stdin failed: Unknown process id '+str(sid[0]):raise ValueError('cross-CLI isolation missing')
                return exec_call(phase)
            if stage==2:
                output=parse_output(state['outputs'][1])
                if output['status']!='exited' or json.loads(output['body'])!=read_json(cwd(phase)/'probe.json'):raise ValueError('exact child probe continuation required')
                return None
            raise ValueError('child request sequence exceeded')
        if stage==0:return exec_call(phase)
        if stage==1:
            output=parse_output(state['outputs'][0])
            if output['status']!='running' or output['body']!='NESTED_READY\n':raise ValueError('live nested wrapper required')
            sid.append(output['sid']);publish_release(work)
        if 1<=stage<=25:
            if stage>1:
                output=parse_output(state['outputs'][-1])
                if output['status']=='exited':
                    if ''.join(parse_output(x)['body'] for x in state['outputs'][1:])!='NESTED_ACK\n':raise ValueError('one nested ACK required')
                    return None
                if output['sid']!=sid[0]:raise ValueError('parent tool identity drift')
            if stage==25:raise ValueError('nested wrapper poll limit')
            return poll(phase,stage,sid[0])
        raise ValueError('parent request sequence exceeded')
    def handler(phase):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def setup(self):super().setup();self.connection.settimeout(5)
            def do_POST(self):
                with locks[phase]:
                    state=streams[phase]
                    try:
                        if self.path!='/v1/responses' or self.headers.get('Authorization') is not None or self.headers.get('Content-Encoding','identity')!='identity':raise ValueError('fixed anonymous endpoint required')
                        size=int(self.headers.get('Content-Length','0'))
                        if not 0<size<=2097152 or len(state['requests'])>=(26 if phase=='parent' else 3):raise ValueError('request bound exceeded')
                        raw=self.rfile.read(size)
                        if len(raw)!=size:raise ValueError('truncated request')
                        request=json.loads(raw)
                        if request.get('model')!=model(phase) or type(request.get('input')) is not list:raise ValueError('fixed model identity required')
                        if state['calls']:
                            last=state['calls'][-1];matches=[x for x in request['input'] if type(x) is dict and x.get('type')=='function_call_output' and x.get('call_id')==last['call_id']]
                            if len(matches)!=1:raise ValueError('exact continuation required')
                            state['outputs'].append(matches[0]['output'])
                        state['requests'].append(request);item=next_call(phase)
                        if item is None:
                            write_json(cwd(phase)/(phase+'-stream.json'),state)
                            item={'type':'message','role':'assistant','id':'nested-'+phase+'-final','content':[{'type':'output_text','text':'fixed anonymous nested control completed'}]}
                        else:state['calls'].append(item)
                        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                        def event(value):self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
                        rid='nested-'+phase+'-'+str(len(state['requests']));event({'type':'response.created','response':{'id':rid}});event({'type':'response.output_item.done','item':item});event({'type':'response.completed','response':{'id':rid,'usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}})
                    except Exception as error:state['errors'].append(type(error).__name__+':'+str(error))
        return Handler
    try:
        for phase in PHASES:
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler(phase));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();servers.append(server);threads.append(thread)
        ports={p:s.server_port for p,s in zip(PHASES,servers,strict=True)};write_json(CONTROL/'ports.json',ports)
        raw_launch('parent',ports['parent'],env('parent'),35)
    finally:
        for server in servers:server.shutdown();server.server_close()
        for thread in threads:thread.join(timeout=2)
        write_json(work/'nested-evidence.json',{'schema':1,'source_pin':SOURCE_PIN,'inventory':inventory,'streams':streams,'ports':{p:s.server_port for p,s in zip(PHASES,servers,strict=True)},'official_catalog_sha256':hashlib.sha256(seed.stdout).hexdigest(),'handler_inventory_complete':False,'startup_isolation_qualified':False,'nested_cli_qualified':False,'production_qualified':False,'observer_limit':'provider/CLI/wrapper/probe share UID; fixed fixture only'})
    print(json.dumps({'fixed_fixture_completed':True,'production_qualified':False}),flush=True)

if __name__=='__main__':
    import sys
    signal.signal(signal.SIGALRM,lambda *_:os._exit(124));signal.alarm(50)
    if sys.argv[1:]==['wrapper']:wrapper()
    elif sys.argv[1:]==['probe']:probe()
    else:
        args=sys.argv[1:] or ['clean',DEFAULT_ATTEMPT]
        if len(args)!=2:raise ValueError('fixed fixture entry required')
        header=startup_header(*args)
        try:run_fixture(*args)
        except StartupLayerUnknown:
            print(json.dumps(dict(header,startup_layer_blocked=True)),flush=True)
            raise SystemExit(1)
