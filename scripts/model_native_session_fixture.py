"""Fixed anonymous two-CLI native terminal controls; no production qualification."""
import hashlib
import http.server
import json
import os
import pathlib
import re
import shlex
import signal
import subprocess
import threading

SOURCE_PIN='01fc69f4026735edfdf6789820549727a4867b11'
INPUT='session-input-control\n'
OTHER_INPUT='cross-thread-reject\n'
CHILD="import pathlib,signal,sys;signal.alarm(20);print('SESSION_READY',flush=True);value=sys.stdin.readline();assert value=='session-input-control\\n';p=pathlib.Path('session-marker');assert not p.exists();p.write_text('session-ack-control\\n');print('SESSION_ACK',flush=True)"
TOOL_COMMAND="python3 -I -S -B -c "+shlex.quote(CHILD)
STDIN_CLOSED='write_stdin failed: stdin is closed for this session; rerun exec_command with tty=true to keep stdin open'
RELEASE=b'non-tty-release-control\n'
NON_TTY_CHILD="""import pathlib,signal,sys,time
signal.alarm(20)
if sys.stdin.readline()!='':raise ValueError('fixed stdin EOF required')
release=pathlib.Path('session-release')
if release.exists() or release.is_symlink():raise ValueError('fresh release required')
print('SESSION_READY',flush=True)
while not release.exists():time.sleep(0.02)
if release.is_symlink() or release.read_bytes()!=b'non-tty-release-control\\n':raise ValueError('fixed release required')
marker=pathlib.Path('session-marker')
if marker.exists() or marker.is_symlink():raise ValueError('fresh marker required')
marker.write_text('session-ack-control\\n')
print('SESSION_ACK',flush=True)
"""
NON_TTY_COMMAND="python3 -I -S -B -c "+shlex.quote(NON_TTY_CHILD)

def publish_release(work):
    staged=work/'session-release-staged'
    with staged.open('xb') as stream:
        stream.write(RELEASE);stream.flush();os.fsync(stream.fileno())
    # Publish complete bytes without replacing an existing final path. Retain
    # both links; a failure is not replayed or cleaned up.
    os.link(staged,work/'session-release',follow_symlinks=False)

def terminal(mode):
    if mode not in ('tty','non-tty'):raise ValueError('fixed terminal mode required')
    return {'cmd':TOOL_COMMAND if mode=='tty' else NON_TTY_COMMAND,'tty':mode=='tty','login':False,'yield_time_ms':1000,'max_output_tokens':512}

def parse_output(value):
    if type(value) is not str or len(value)>8192:raise ValueError('bounded native string carrier required')
    header,separator,body=value.partition('Output:\n')
    if separator!='Output:\n' or len(body.encode())>4096:raise ValueError('bounded native header required')
    lines=header.splitlines()
    if len(lines) not in (3,4) or not re.fullmatch(r'Chunk ID: [A-Za-z0-9_-]{1,128}',lines[0]) or not re.fullmatch(r'Wall time: (0|[1-9][0-9]?)\.[0-9]{4} seconds',lines[1]):raise ValueError('native header identity required')
    if len(lines)==4 and not re.fullmatch(r'Original token count: (0|[1-9][0-9]{0,5})',lines[3]):raise ValueError('bounded token header required')
    match=re.fullmatch(r'Process running with session ID ([1-9][0-9]{3,4})',lines[2])
    if match:
        sid=int(match[1])
        if not 1000<=sid<=99999:raise ValueError('pinned tool process range required')
        return {'status':'running','sid':sid,'body':body}
    if lines[2]!='Process exited with code 0':raise ValueError('natural tool exit 0 required')
    return {'status':'exited','sid':None,'body':body}

def call(index,name,arguments):
    return {'type':'function_call','namespace':'functions','name':name,'call_id':'native-session-'+str(index),'arguments':json.dumps(arguments)}

def poll(index,sid,chars=''):
    return call(index,'write_stdin',{'session_id':sid,'chars':chars,'yield_time_ms':1000,'max_output_tokens':512})

def cli_argv(port):
    if type(port) is not int or not 1<=port<=65535:raise ValueError('fixed loopback port required')
    disabled=['apps','hooks','plugins','remote_plugin','multi_agent','multi_agent_v2','goals','memories','code_mode','code_mode_only','code_mode_prewarm','enable_request_compression','browser_use','computer_use','image_generation','skill_search','skill_mcp_dependency_install','tool_suggest','daemon_auto_start','view_image','sleep_tool','current_time_reminder','request_permissions_tool','send_message_to_user_async','token_budget','deferred_executor']
    settings=['model_provider="fixture"','model="fixture-direct"','model_catalog_json="/tmp/session-control/catalog.json"',
        'model_providers.fixture={name="Fixed anonymous native session",base_url="http://127.0.0.1:'+str(port)+'/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=15000}',
        'approval_policy="never"','shell_environment_policy.inherit="none"','web_search="disabled"','notify=[]','agents.enabled=false','tools.experimental_request_user_input.enabled=false','features.code_mode_host={enabled=false,disable_in_process_fallback=false}',*['features.'+x+'=false' for x in disabled]]
    return ['/fixture/codex','exec','--strict-config','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--json','--sandbox','danger-full-access',*[a for s in settings for a in ['-c',s]],'Follow only the fixed synthetic provider.']

def run_fixture(mode='tty'):
    tool=terminal(mode)
    work=pathlib.Path('/workspace');control=pathlib.Path('/tmp/session-control');control.mkdir(mode=0o700)
    homes=[pathlib.Path('/tmp/session-home-'+x) for x in ('a','b')]
    paths=['/etc/codex/config.toml','/etc/codex/requirements.toml','/etc/codex/managed_config.toml','/config.toml','/.codex/config.toml','/workspace/config.toml','/workspace/.codex/config.toml',*[str(h/n) for h in homes for n in ('config.toml','managed_config.toml','auth.json')]]
    inventory=[{'path':p,'exists':pathlib.Path(p).exists(),'symlink':pathlib.Path(p).is_symlink(),'canonical':pathlib.Path(p).resolve(strict=False)==pathlib.Path(p)} for p in paths]
    if any(x['exists'] or x['symlink'] or not x['canonical'] for x in inventory):raise ValueError('unknown pre-existing layer')
    for home in homes:home.mkdir(mode=0o700)
    def environment(home):return {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(home),'CODEX_HOME':str(home),'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
    result=subprocess.run(['/fixture/codex','debug','models','--bundled'],env=environment(homes[0]),cwd=work,stdin=subprocess.DEVNULL,capture_output=True,timeout=15,check=True,close_fds=True)
    catalog=json.loads(result.stdout);models=[m for m in catalog['models'] if m['slug']=='gpt-6-luna']
    if len(models)!=1 or any(m['slug']=='fixture-direct' for m in catalog['models']):raise ValueError('catalog drift')
    catalog['models'].append(dict(models[0],slug='fixture-direct',tool_mode='direct',experimental_supported_tools=[],shell_type='unified_exec',apply_patch_tool_type='freeform',supports_search_tool=False));(control/'catalog.json').write_text(json.dumps(catalog))
    state={'a':{'calls':[],'requests':[],'outputs':[]},'b':{'calls':[],'requests':[],'outputs':[]}};errors=[];sid_ready=threading.Event();b_ready=threading.Event();b_finished=threading.Event();sid_holder=[];results={}
    def next_call(phase):
        stream=state[phase];stage=len(stream['outputs'])
        if phase=='b':
            if stage==0:
                b_ready.set()
                if not sid_ready.wait(8):raise ValueError('A process identity unavailable')
                return poll('b',sid_holder[0],OTHER_INPUT)
            if stage!=1 or stream['outputs'][0]!='write_stdin failed: Unknown process id '+str(sid_holder[0]):raise ValueError('cross-thread rejection missing')
            b_finished.set();return None
        if stage==0:return call(0,'exec_command',tool)
        if stage==1:
            value=parse_output(stream['outputs'][0])
            if value['status']!='running' or value['body'].replace('\r\n','\n')!='SESSION_READY\n':raise ValueError('fixed live positive missing')
            sid_holder.append(value['sid']);sid_ready.set()
            if not b_finished.wait(8):raise ValueError('cross-thread exact continuation unavailable')
            return poll(1,value['sid'])
        if stage==2:
            value=parse_output(stream['outputs'][1])
            if value['status']!='running' or value['sid']!=sid_holder[0] or value['body']!='':raise ValueError('poll consumed output incorrectly')
            return poll(2,sid_holder[0],INPUT)
        if mode=='non-tty':
            if stage==3:
                if stream['outputs'][2]!=STDIN_CLOSED:raise ValueError('non-TTY input rejection missing')
                return poll(3,sid_holder[0])
            if stage==4:
                if parse_output(stream['outputs'][3])!={'status':'running','sid':sid_holder[0],'body':''}:raise ValueError('non-TTY rejection did not preserve live process')
                publish_release(work)
                return poll(4,sid_holder[0])
            if stage==5:
                value=parse_output(stream['outputs'][4])
                if value['status']=='running':
                    if value['sid']!=sid_holder[0]:raise ValueError('process identity changed')
                    return poll(5,sid_holder[0])
                return poll(6,sid_holder[0])
            if stage==6 and stream['calls'][-1]['call_id']=='native-session-5':
                if parse_output(stream['outputs'][5])['status']!='exited':raise ValueError('bounded non-TTY did not finish')
                return poll(6,sid_holder[0])
            if stage not in (6,7) or stream['outputs'][-1]!='write_stdin failed: Unknown process id '+str(sid_holder[0]):raise ValueError('terminated process was not rejected')
            return None
        if stage==3:
            value=parse_output(stream['outputs'][2])
            if value['status']=='running':
                if value['sid']!=sid_holder[0]:raise ValueError('process identity changed')
                return poll(3,sid_holder[0])
            return poll(4,sid_holder[0])
        if stage==4 and stream['calls'][-1]['call_id']=='native-session-3':
            if parse_output(stream['outputs'][3])['status']!='exited':raise ValueError('bounded terminal did not finish')
            return poll(4,sid_holder[0])
        if stage not in (4,5) or stream['outputs'][-1]!='write_stdin failed: Unknown process id '+str(sid_holder[0]):raise ValueError('terminated process was not rejected')
        return None
    servers=[];threads=[]
    def make_handler(phase):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def setup(self):super().setup();self.connection.settimeout(5)
            def do_POST(self):
                try:
                    stream=state[phase]
                    if self.path!='/v1/responses' or self.headers.get('Authorization') is not None or self.headers.get('Content-Encoding','identity')!='identity':raise ValueError('fixed endpoint/auth/encoding required')
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=2097152 or len(stream['requests'])>=(8 if mode=='non-tty' else 7):raise ValueError('fixed request bound')
                    raw=self.rfile.read(size)
                    if len(raw)!=size:raise ValueError('truncated request')
                    request=json.loads(raw)
                    if request.get('model')!='fixture-direct' or type(request.get('input')) is not list:raise ValueError('fixed request identity required')
                    if stream['calls']:
                        last=stream['calls'][-1];matches=[x for x in request['input'] if type(x) is dict and x.get('type')=='function_call_output' and x.get('call_id')==last['call_id']]
                        if len(matches)!=1:raise ValueError('exact continuation missing')
                        stream['outputs'].append(matches[0]['output'])
                    stream['requests'].append(request)
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    def event(value):self.wfile.write(('event: '+value['type']+'\ndata: '+json.dumps(value)+'\n\n').encode());self.wfile.flush()
                    event({'type':'response.created','response':{'id':phase+'-'+str(len(stream['requests']))}})
                    item=next_call(phase)
                    if item is None:item={'type':'message','role':'assistant','id':phase+'-final','content':[{'type':'output_text','text':'fixed anonymous terminal control completed'}]}
                    else:stream['calls'].append(item)
                    event({'type':'response.output_item.done','item':item});event({'type':'response.completed','response':{'id':phase+'-'+str(len(stream['requests'])),'usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}})
                except Exception as error:errors.append(phase+':'+type(error).__name__+':'+str(error))
        return Handler
    for phase in ('a','b'):
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),make_handler(phase));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();servers.append(server);threads.append(thread)
    def launch(phase,index,timeout):
        try:
            argv=cli_argv(servers[index].server_port);p=subprocess.run(argv,env=environment(homes[index]),cwd=work,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=timeout,close_fds=True)
            results[phase]={'argv':argv,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        except Exception as error:errors.append(phase+':'+type(error).__name__)
    b_thread=threading.Thread(target=launch,args=('b',1,30),daemon=True);b_thread.start()
    try:
        if not b_ready.wait(8):raise ValueError('B provider entry missing')
        launch('a',0,35);b_thread.join(timeout=5)
        if b_thread.is_alive():raise ValueError('B did not finish within bound')
    finally:
        for server in servers:server.shutdown();server.server_close()
        for thread in threads:thread.join(timeout=2)
    evidence={'schema':2,'terminal_mode':mode,'source_pin':SOURCE_PIN,'production_qualified':False,'native_session_qualified':False,'inventory':inventory,'streams':state,'cli':results,'errors':errors,'observer_limit':'provider/CLI/terminals share UID; not trusted production observer','official_catalog_sha256':hashlib.sha256(result.stdout).hexdigest()}
    (work/'native-session-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'errors':errors,'cli_exits':{k:v['exit'] for k,v in results.items()},'production_qualified':False}),flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:] not in ([],['non-tty']):raise ValueError('fixed terminal mode argument required')
    signal.signal(signal.SIGALRM,lambda *_:os._exit(124));signal.alarm(50);run_fixture('non-tty' if sys.argv[1:] else 'tty')
