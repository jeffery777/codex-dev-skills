"""Fixed anonymous native project-config/hook measurement inside Docker only.

No login, real provider or hook-trust bypass. Trusted user state versus modified
state measures one fixed hook and never qualifies complete trust enforcement.
"""
import hashlib
import http.server
import json
import pathlib
import subprocess
import sys
import threading

SOURCE_PIN='01fc69f4026735edfdf6789820549727a4867b11'
TOOL_COMMAND="printf 'project-tool-control\\n' > tool-marker"
HOOK_COMMAND='python3 /tmp/fixture-control/pre.py'
HOOK_KEY='/workspace/project/.codex/config.toml:pre_tool_use:0:0'
STARTUP_PATHS=('/etc/codex/config.toml','/etc/codex/requirements.toml','/etc/codex/managed_config.toml',
    '/config.toml','/.codex/config.toml','/workspace/config.toml','/workspace/.codex/config.toml',
    '/workspace/project/config.toml','/workspace/project/.codex/config.toml',
    '/tmp/anonymous-home/config.toml','/tmp/anonymous-home/managed_config.toml','/tmp/anonymous-home/auth.json')
HOOK_PROGRAM=r'''
import json,pathlib,sys
raw=sys.stdin.buffer.read(65537)
if len(raw)>65536:raise ValueError('bounded hook stdin required')
value=json.loads(raw)
path=pathlib.Path('/workspace/project/hook-marker.json')
data=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
if len(data)>65536:raise ValueError('bounded hook record required')
with path.open('ab') as stream:stream.write(data)
'''


def hook_hash():
    # Pinned normalized HookHandlerConfig -> TOML -> canonical compact JSON.
    # TOML omits absent optional values, but serializes default async=false.
    identity={'event_name':'pre_tool_use','matcher':'^Bash$',
        'hooks':[{'type':'command','command':HOOK_COMMAND,'timeout':10,'async':False}]}
    return 'sha256:'+hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def project_config():
    # Project state deliberately tries to trust itself in both phases. Only the
    # separately controlled user state may authorize execution in this tuple.
    return ('[hooks]\n[[hooks.PreToolUse]]\nmatcher = "^Bash$"\n[[hooks.PreToolUse.hooks]]\n'
        'type = "command"\ncommand = '+json.dumps(HOOK_COMMAND)+'\ntimeout = 10\n'
        '[hooks.state]\n'+json.dumps(HOOK_KEY)+' = { trusted_hash = '+json.dumps(hook_hash())+' }\n')


def user_config(port,phase):
    if type(port) is not int or not 1<=port<=65535 or phase not in ('positive','negative'):raise ValueError('fixed loopback phase required')
    value='model_provider="fixture"\nmodel="fixture-direct"\nmodel_catalog_json="/tmp/fixture-control/catalog.json"\n'
    value+='[model_providers.fixture]\nname="Fixed anonymous project hook"\nbase_url="http://127.0.0.1:'+str(port)+'/v1"\nwire_api="responses"\nrequires_openai_auth=false\nsupports_websockets=false\nrequest_max_retries=0\nstream_max_retries=0\nstream_idle_timeout_ms=5000\n'
    value+='[projects."/workspace/project"]\ntrust_level="trusted"\n[features]\nhooks=true\n'
    trusted_hash=hook_hash() if phase=='positive' else 'sha256:'+'0'*64
    return value+'[hooks.state]\n'+json.dumps(HOOK_KEY)+' = { trusted_hash = '+json.dumps(trusted_hash)+' }\n'


def cli_argv():
    disabled=['apps','plugins','remote_plugin','multi_agent','multi_agent_v2','goals','memories',
        'code_mode','code_mode_only','code_mode_prewarm','enable_request_compression','browser_use',
        'computer_use','image_generation','skill_search','skill_mcp_dependency_install','tool_suggest',
        'daemon_auto_start','view_image','sleep_tool','current_time_reminder','request_permissions_tool',
        'send_message_to_user_async','token_budget','deferred_executor']
    settings=['approval_policy="never"','shell_environment_policy.inherit="none"','web_search="disabled"',
        'notify=[]','agents.enabled=false','tools.experimental_request_user_input.enabled=false',
        'features.code_mode_host={enabled=false,disable_in_process_fallback=false}',
        *['features.'+name+'=false' for name in disabled]]
    return ['/fixture/codex','exec','--strict-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--json',
        '--sandbox','danger-full-access',*[arg for setting in settings for arg in ['-c',setting]],
        'Follow only the fixed synthetic provider.']


def run_fixture(phase):
    if phase not in ('positive','negative'):raise ValueError('fixed hook phase required')
    work=pathlib.Path('/workspace/project');home=pathlib.Path('/tmp/anonymous-home')
    control=pathlib.Path('/tmp/fixture-control')
    # Metadata only: unknown pre-existing layers stop before any CLI execution.
    inventory=[dict(path=p,exists=pathlib.Path(p).exists(),symlink=pathlib.Path(p).is_symlink(),
        canonical=pathlib.Path(p).resolve(strict=False)==pathlib.Path(p)) for p in STARTUP_PATHS]
    if any(row['exists'] or row['symlink'] or not row['canonical'] for row in inventory):raise ValueError('unknown pre-existing startup layer')
    work.mkdir();(work/'.git').mkdir();(work/'.codex').mkdir();home.mkdir(mode=0o700);control.mkdir(mode=0o700)
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(home),'CODEX_HOME':str(home),
        'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
    binary='/fixture/codex'
    catalog_run=subprocess.run([binary,'debug','models','--bundled'],env=env,cwd=work,
        stdin=subprocess.DEVNULL,capture_output=True,timeout=15,check=True,close_fds=True)
    catalog=json.loads(catalog_run.stdout);matches=[m for m in catalog['models'] if m['slug']=='gpt-6-luna']
    if len(matches)!=1 or any(m['slug']=='fixture-direct' for m in catalog['models']):raise ValueError('catalog identity drift')
    catalog['models'].append(dict(matches[0],slug='fixture-direct',tool_mode='direct',experimental_supported_tools=[],
        shell_type='unified_exec',apply_patch_tool_type='freeform',supports_search_tool=False))
    catalog_path=control/'catalog.json';catalog_path.write_text(json.dumps(catalog))
    hook_path=control/'pre.py';hook_path.write_text(HOOK_PROGRAM)
    config=project_config();(work/'.codex/config.toml').write_text(config)
    call={'type':'function_call','namespace':'functions','name':'exec_command','call_id':'project-hook-0',
        'arguments':json.dumps({'cmd':TOOL_COMMAND,'login':False,'yield_time_ms':1000,'max_output_tokens':1000})}
    requests=[];outputs=[];errors=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def setup(self):super().setup();self.connection.settimeout(5)
        def do_POST(self):
            try:
                if self.path!='/v1/responses' or self.headers.get('Authorization') is not None or self.headers.get('Content-Encoding','identity')!='identity':raise ValueError('endpoint/auth/encoding drift')
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=2097152 or len(requests)>=2:raise ValueError('fixed request bound')
                raw=self.rfile.read(size)
                if len(raw)!=size:raise ValueError('truncated request')
                value=json.loads(raw)
                if value.get('model')!='fixture-direct':raise ValueError('model drift')
                stage=len(requests);requests.append(value)
                if stage:
                    matches=[x for x in value.get('input',[]) if x.get('type')=='function_call_output' and x.get('call_id')==call['call_id']]
                    if len(matches)!=1:raise ValueError('missing exact continuation')
                    outputs.append(matches[0]['output'])
                item=call if stage==0 else {'type':'message','role':'assistant','id':'project-final','content':[{'type':'output_text','text':'fixed project hook measurement completed'}]}
                events=[{'type':'response.created','response':{'id':f'project-{stage}'}},
                    {'type':'response.output_item.done','item':item},
                    {'type':'response.completed','response':{'id':f'project-{stage}','usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}}]
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                for event in events:self.wfile.write(('event: '+event['type']+'\ndata: '+json.dumps(event)+'\n\n').encode())
            except Exception as error:errors.append(type(error).__name__+':'+str(error));self.send_error(422)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    config_user=user_config(server.server_port,phase);(home/'config.toml').write_text(config_user)
    argv=cli_argv()
    try:result=subprocess.run(argv,env=env,cwd=work,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=35,close_fds=True)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    receipt={'schema':1,'phase':phase,'source_pin':SOURCE_PIN,'production_qualified':False,
        'startup_isolation_qualified':False,'hook_trust_qualified':False,'inventory':inventory,
        'argv':argv,'user_config':config_user,'project_config':config,'call':call,
        'requests':requests,'outputs':outputs,'errors':errors,'cli_exit':result.returncode,
        'cli_stdout':result.stdout,'cli_stderr':result.stderr,
        'official_catalog_sha256':hashlib.sha256(catalog_run.stdout).hexdigest(),
        'fixture_catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        'observer_limit':'provider/CLI/hook share UID; not trusted production observer'}
    (pathlib.Path('/workspace')/'project-hook-evidence.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'phase':phase,'cli_exit':result.returncode,'requests':len(requests),'outputs':len(outputs),'errors':errors,'production_qualified':False}),flush=True)


if __name__=='__main__':run_fixture(sys.argv[1])
