"""Fixed anonymous Linux CLI recipe; no login, arbitrary payload, or qualification.

The host uses fixed_cases() before starting a fresh container. run_fixture() runs
only as the exact Python entrypoint inside its disposable scratch boundary.
"""
import hashlib
import http.server
import json
import pathlib
import shlex
import subprocess
import threading


def fixed_cases():
    """Return the complete immutable recipe, not a worker-selected case subset."""
    binary='/fixture/codex'
    calls=[];expectations=[]
    def add(item,expected):
     item['call_id']='matrix-'+str(len(calls));calls.append(item);expectations.append(expected)
    def patch(name):return '*** Begin Patch\n*** Add File: '+name+'\n+fixed-positive-'+name+'\n*** End Patch'
    def exec_call(command):return {'type':'function_call','name':'exec_command','arguments':json.dumps({'cmd':command,'login':False,'yield_time_ms':1000,'max_output_tokens':1000})}
    for index,namespace in enumerate(['absent',None,'','functions']):
     name='scratch-exec-'+str(index)
     item=exec_call('printf fixed-positive-'+name+' > '+name+"; printf 'matrix-exec-ok\\n'")
     if namespace!='absent':item['namespace']=namespace
     add(item,{'kind':'exec','file':name,'content':'fixed-positive-'+name})
     name='scratch-patch-'+str(index)
     item={'type':'custom_tool_call','name':'apply_patch','input':patch(name)}
     if namespace!='absent':item['namespace']=namespace
     add(item,{'kind':'patch','file':name,'content':'fixed-positive-'+name+'\n'})
    # These names are not equivalent native tool invocations; no unknown tool may write.
    for name,namespace in [('shell',None),('shell_command',None),('execve',None),('exec',None),('wait',None),('request_user_input',None),('request_user_input_async',None),('spawn_agent',None),('spawn_agent','collaboration'),('tool_search',None),('view_image',None),('exec_command','unconfigured'),('allowed','mcp__unconfigured'),('functions.exec_command',None)]:
     item={'type':'function_call','name':name,'arguments':json.dumps({'cmd':'printf forbidden > forbidden-marker','command':'printf forbidden > forbidden-marker'})}
     if namespace is not None:item['namespace']=namespace
     add(item,{'kind':'unsupported','name':name,'namespace':namespace})
    # Implicit patch routes remain writer capabilities, even without standalone dispatch.
    for command_name in ['apply_patch','applypatch']:
     name='scratch-implicit-'+command_name
     add(exec_call(command_name+" <<'PATCH'\n"+patch(name)+'\nPATCH'),{'kind':'patch','file':name,'content':'fixed-positive-'+name+'\n'})
    name='scratch-hidden-arg1'
    add(exec_call(shlex.quote(binary)+' --codex-run-as-apply-patch '+shlex.quote(patch(name))),{'kind':'exec-patch','file':name,'content':'fixed-positive-'+name+'\n'})
    for alias in ['apply_patch','applypatch']:
     name='scratch-arg0-'+alias
     link='/workspace/'+alias
     add(exec_call('ln -s '+shlex.quote(binary)+' '+link+'; '+link+' '+shlex.quote(patch(name))),{'kind':'exec-patch','file':name,'content':'fixed-positive-'+name+'\n'})
    # Explicit escalation must reject before this side effect, despite outer Docker.
    item=exec_call('printf forbidden > forbidden-escalation')
    arguments=json.loads(item['arguments']);arguments['sandbox_permissions']='require_escalated';arguments['justification']='Fixed synthetic negative control';item['arguments']=json.dumps(arguments)
    add(item,{'kind':'escalation-denied'})
    return calls,expectations


def run_fixture():

    work=pathlib.Path('/workspace')
    home=pathlib.Path('/tmp/anonymous-home');home.mkdir(mode=0o700)
    control=pathlib.Path('/tmp/fixture-control');control.mkdir(mode=0o700)
    env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':str(home),'CODEX_HOME':str(home),
         'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
    binary='/fixture/codex'
    catalog_run=subprocess.run([binary,'debug','models','--bundled'],env=env,cwd=work,
        stdin=subprocess.DEVNULL,capture_output=True,timeout=15,check=True,close_fds=True)
    catalog=json.loads(catalog_run.stdout)
    matches=[m for m in catalog['models'] if m['slug']=='gpt-6-luna']
    if len(matches)!=1 or any(m['slug']=='fixture-direct' for m in catalog['models']):raise ValueError('catalog identity drift')
    original=matches[0]
    fixture=dict(original,slug='fixture-direct',tool_mode='direct',experimental_supported_tools=[],
                 shell_type='unified_exec',apply_patch_tool_type='freeform',supports_search_tool=False)
    catalog['models'].append(fixture)
    catalog_path=control/'catalog.json';catalog_path.write_text(json.dumps(catalog))
    calls,expectations=fixed_cases()
    requests=[];outputs=[];errors=[]
    class Handler(http.server.BaseHTTPRequestHandler):
     def log_message(self,*args):pass
     def setup(self):super().setup();self.connection.settimeout(5)
     def do_POST(self):
      try:
       if self.path!='/v1/responses' or self.headers.get('Authorization') is not None or self.headers.get('Content-Encoding','identity')!='identity':raise ValueError('endpoint/auth/encoding drift')
       size=int(self.headers.get('Content-Length','0'))
       if not 0<size<=2097152 or len(requests)>len(calls):raise ValueError('request bound')
       raw=self.rfile.read(size)
       if len(raw)!=size:raise ValueError('truncated request')
       value=json.loads(raw)
       if value.get('model')!='fixture-direct':raise ValueError('model drift')
       stage=len(requests);requests.append(value)
       if stage:
        call=calls[stage-1];kind='function_call_output' if call['type']=='function_call' else 'custom_tool_call_output'
        matches=[x for x in value.get('input',[]) if x.get('type')==kind and x.get('call_id')==call['call_id']]
        if len(matches)!=1:raise ValueError('missing exact continuation')
        outputs.append(matches[0]['output'])
       item=calls[stage] if stage<len(calls) else {'type':'message','role':'assistant','id':'fixed-final','content':[{'type':'output_text','text':'fixed anonymous matrix completed'}]}
       events=[{'type':'response.created','response':{'id':f'fixture-{stage}'}},{'type':'response.output_item.done','item':item},{'type':'response.completed','response':{'id':f'fixture-{stage}','usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}}]
       self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
       for event in events:self.wfile.write(('event: '+event['type']+'\ndata: '+json.dumps(event)+'\n\n').encode())
      except Exception as error:errors.append(type(error).__name__+':'+str(error));self.send_error(422)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    disabled=['apps','hooks','plugins','remote_plugin','multi_agent','multi_agent_v2','goals',
        'memories','code_mode','code_mode_only','code_mode_prewarm','enable_request_compression',
        'browser_use','computer_use','image_generation','skill_search','skill_mcp_dependency_install',
        'tool_suggest','daemon_auto_start','view_image','sleep_tool','current_time_reminder',
        'request_permissions_tool','send_message_to_user_async','token_budget','deferred_executor']
    settings=['model_provider="fixture"','model="fixture-direct"',
        'model_catalog_json='+json.dumps(str(catalog_path)),
        'model_providers.fixture={name="Fixed anonymous Docker dispatcher",base_url="http://127.0.0.1:'+
            str(server.server_port)+'/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,'+
            'request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}',
        'approval_policy="never"','shell_environment_policy.inherit="none"','web_search="disabled"',
        'notify=[]','agents.enabled=false','tools.experimental_request_user_input.enabled=false','features.code_mode_host={enabled=false,disable_in_process_fallback=false}',
        *['features.'+name+'=false' for name in disabled]]
    args=[arg for setting in settings for arg in ['-c',setting]]
    try:
     result=subprocess.run([binary,'exec','--ignore-user-config','--ignore-rules','--ephemeral','--skip-git-repo-check','--json','--sandbox','danger-full-access',*args,'Follow only the fixed synthetic provider.'],env=env,cwd=work,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=35,close_fds=True)
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
    receipt={'scope':'fixed-native-canonical-excluded-carrier-escalation-matrix','production_qualified':False,'handler_inventory_complete':False,'source_pin':'01fc69f4026735edfdf6789820549727a4867b11','official_catalog_sha256':hashlib.sha256(catalog_run.stdout).hexdigest(),'fixture_catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),'official_entries_preserved':True,'settings':settings,'calls':calls,'expectations':expectations,'requests':requests,'outputs':outputs,'errors':errors,'cli_exit':result.returncode,'cli_stdout':result.stdout,'cli_stderr':result.stderr,'observer_limit':'same UID; not trusted production observer'}
    (work/'dispatch-evidence.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'cli_exit':result.returncode,'requests':len(requests),'outputs':len(outputs),'errors':errors,'production_qualified':False}),flush=True)


if __name__ == "__main__":
    run_fixture()
