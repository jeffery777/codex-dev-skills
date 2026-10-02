#!/usr/bin/env python3
"""Opt-in macOS synthetic CLI tool-boundary matrix; no real provider or login.

Only fixed calls are emitted. Every fresh case first verifies the same MCP
positive control. Evidence stays outside Git. A stopped no-fork MCP stub is not
proof that every CLI descendant stopped. No agent, Code Mode or stdin-session
call is attempted, and no production qualification is granted.
The normalized UnifiedExec observation mode is explicit opt-in and cannot
satisfy the default required-false feature contract.
"""
import argparse
import hashlib
import http.server
import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model_probe_tools as manifest

CASES = ('mcp-excluded', 'mcp-unknown-server', 'shell', 'shell_command', 'exec_command', 'apply_patch')
TOKEN = 'synthetic-boundary-allowed-ok'
CLI_VERSION = 'codex-cli 0.159.3'
MCP_NAMESPACE = 'mcp__boundary'
STRICT_CONTROL_MODE = 'strict-required-false'
NORMALIZED_CONTROL_MODE = 'normalized-unified-exec-fixed-observation'
REQUIRED_DISABLED_FEATURES = ('shell_tool', 'unified_exec', 'view_image', 'apps', 'hooks',
    'plugins', 'remote_plugin', 'multi_agent', 'multi_agent_v2', 'goals', 'memories',
    'code_mode', 'code_mode_host', 'code_mode_only', 'code_mode_prewarm',
    'enable_request_compression', 'browser_use', 'computer_use', 'image_generation',
    'skill_search', 'skill_mcp_dependency_install', 'tool_suggest', 'daemon_auto_start')
# UTF-8 file bytes read from this immutable upstream revision, not a runtime pin.
NORMALIZATION_SOURCE = {'repository': 'openai/codex',
    'commit': '01fc69f4026735edfdf6789820549727a4867b11',
    'path': 'codex-rs/core/src/config/managed_features.rs',
    'source_sha256': '872e47b4feca6c5d2f4b44f05d5db25ae2aec08293c6fee6dcf9c77186580847'}
NORMALIZATION_LIMITATION = 'unified-exec-user-opt-out-unavailable'
CHECKS = {'cli_exited_successfully', 'configuration_unchanged', 'native_metadata_warning_absent',
    'forbidden_preserved', 'no_workspace_effect', 'only_allowed_stub_call', 'fixed_stub_stopped'}
STUB_SOURCE = r'''import json,os,pathlib,selectors,sys,time
control=pathlib.Path(sys.argv[1])
(control/'stub-pid').write_text(str(os.getpid()))
selector=selectors.DefaultSelector()
selector.register(sys.stdin,selectors.EVENT_READ)
deadline=time.monotonic()+20
buffer=b''
initialized=ready=False
count=0
reason='deadline'
try:
 while time.monotonic()<deadline:
  if not selector.select(min(0.25,max(0,deadline-time.monotonic()))):continue
  chunk=os.read(sys.stdin.fileno(),16384)
  if not chunk:reason='eof';break
  buffer+=chunk
  if len(buffer)>32768:reason='oversized';break
  while b'\n' in buffer:
   raw,buffer=buffer.split(b'\n',1)
   count+=1
   if count>20:raise ValueError('message-limit')
   value=json.loads(raw)
   if type(value) is not dict or value.get('jsonrpc')!='2.0':raise ValueError('envelope')
   method=value.get('method'); params=value.get('params',{})
   if type(params) is not dict:raise ValueError('params')
   params={k:v for k,v in params.items() if k!='_meta'}
   result=None
   if method=='initialize' and not initialized:
    initialized=True
    result={'protocolVersion':'2024-11-05','capabilities':{'tools':{}},'serverInfo':{'name':'boundary','version':'1'}}
   elif method=='notifications/initialized' and initialized and not ready and 'id' not in value:
    ready=True
    continue
   elif ready and method=='tools/list' and not params:
    result={'tools':[{'name':name,'description':'Fixed synthetic '+name+' control',
      'inputSchema':{'type':'object','properties':{},'additionalProperties':False}} for name in ['allowed','excluded']]}
   elif ready and method=='ping' and not params:result={}
   elif ready and method=='tools/call' and set(params)=={'name','arguments'} and params['name'] in ['allowed','excluded'] and params['arguments']=={}:
    with (control/'stub-calls.jsonl').open('a') as stream:
     stream.write(json.dumps({'name':params['name'],'arguments':{},'rpc_id':value.get('id')})+'\n')
    result={'content':[{'type':'text','text':'synthetic-boundary-allowed-ok' if params['name']=='allowed' else 'synthetic-excluded-dispatched'}],'isError':False}
   else:raise ValueError('unsupported-request')
   print(json.dumps({'jsonrpc':'2.0','id':value['id'],'result':result}),flush=True)
except (ValueError,KeyError,TypeError,OSError):reason='protocol-error'
finally:
 selector.close()
 (control/'stub-exit').write_text(reason)
'''


class ProbeError(ValueError):
    pass


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def load_broker():
    path = pathlib.Path(__file__).with_name('verify-model-broker.py')
    spec = importlib.util.spec_from_file_location('tool_boundary_broker_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def environment(home):
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home),
        'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost',
        'PYTHONDONTWRITEBYTECODE': '1'}


def selected_metadata(raw, model):
    value = manifest.decode(raw)
    if type(value) is not dict or type(value.get('models')) is not list:
        raise ProbeError('invalid-bundled-catalog')
    records = [item for item in value['models'] if type(item) is dict and item.get('slug') == model]
    if len(records) != 1 or not {'shell_type', 'apply_patch_tool_type'} <= set(records[0]):
        raise ProbeError('selected-native-metadata-missing')
    return records[0]


def fixed_call(case, control, namespace=MCP_NAMESPACE):
    if case not in CASES:
        raise ProbeError('unknown-fixed-case')
    call = {'call_id': 'boundary-negative-1', 'type': 'function_call'}
    if case.startswith('mcp-'):
        call.update(name='excluded' if case == 'mcp-excluded' else 'allowed',
            namespace=namespace if case == 'mcp-excluded' else 'mcp__unconfigured_boundary', arguments='{}')
    elif case == 'apply_patch':
        call.update(type='custom_tool_call', name='apply_patch', input=
            '*** Begin Patch\n*** Add File: forbidden-marker\n+synthetic-forbidden\n*** End Patch')
    else:
        command = ('printf synthetic-forbidden > forbidden-marker; printf synthetic-forbidden > '
                   + shlex.quote(str(control / 'sentinel')))
        args = ({'command': ['/bin/sh', '-c', command]} if case == 'shell' else
                {'command': command, 'login': False} if case == 'shell_command' else
                {'cmd': command, 'login': False})
        call.update(name=case, arguments=json.dumps(args))
    return call


def find_output(request, call):
    expected = 'custom_tool_call_output' if call['type'] == 'custom_tool_call' else 'function_call_output'
    outputs = [item for item in request.get('input', []) if type(item) is dict
        and item.get('call_id') == call['call_id'] and item.get('type') == expected]
    if len(outputs) != 1:
        raise ProbeError('missing-or-duplicate-exact-call-output')
    return outputs[0].get('output')


def output_text(output):
    """Unwrap only the observed 0.159.3 two-block text carrier, without mutation.

    Its fixed four-decimal timing header must fit the 30-second invocation
    window. It is transport metadata, never evidence of tool success or denial.
    Other layouts remain unknown; this is not a general content-list adapter.
    """
    if type(output) is str:
        return output
    if (type(output) is not list or len(output) != 2
            or any(type(block) is not dict or set(block) != {'type', 'text'}
                or block['type'] != 'input_text' or type(block['text']) is not str
                for block in output)):
        return None
    timing = re.fullmatch(r'Wall time: (0|[1-9][0-9]?)\.([0-9]{4}) seconds\nOutput:', output[0]['text'])
    if (timing is None or int(timing[1]) * 10000 + int(timing[2]) > 300000
            or len(output[1]['text']) > 32768):
        return None
    return output[1]['text']


def positive_output(output):
    output = output_text(output)
    if output == TOKEN:
        return True
    if type(output) is not str:
        return False
    try:
        value = manifest.decode(output.encode())
    except ValueError:
        return False
    return (type(value) is dict and set(value) == {'content', 'isError'} and value['isError'] is False
        and value['content'] == [{'type': 'text', 'text': TOKEN}])


def negative_outcome(output, call):
    """Only exact known dispatch/sandbox denials qualify; generic errors do not."""
    output = output_text(output)
    if type(output) is not str:
        return 'unknown'
    name = call['name']; namespace = call.get('namespace')
    names = {name, 'functions.' + name} if namespace is None else {namespace + '.' + name, namespace + name}
    prefix = 'unsupported custom tool call: ' if call['type'] == 'custom_tool_call' else 'unsupported call: '
    if output in {prefix + name for name in names}:
        return 'unsupported-handler'
    if call['name'] == 'apply_patch' and output == (
            'patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings'):
        return 'readonly-patch-denied'
    return 'unknown'


def stub_calls(control):
    path = control / 'stub-calls.jsonl'
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 32768:
        raise ProbeError('invalid-stub-log')
    result = [manifest.decode(line) for line in path.read_bytes().splitlines()]
    if any(type(item) is not dict or set(item) != {'name', 'arguments', 'rpc_id'} for item in result):
        raise ProbeError('invalid-stub-log')
    return result


def stub_stopped(control):
    """Prove only absence of this fixed no-fork stub PID, never containment."""
    path = control / 'stub-pid'
    if not path.is_file() or path.is_symlink():
        return None
    raw = path.read_text()
    if not re.fullmatch(r'[1-9][0-9]{0,9}', raw):
        return None
    try:
        os.kill(int(raw), 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return None
    return False


def settings(work, home, control, executable, model, catalog, stub, port, disabled):
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
        str(work): 'read', str(home): 'deny', str(control): 'deny', str(executable): 'read',
        str(executable.parent): 'read'}
    fs = ','.join(json.dumps(key) + '=' + json.dumps(value) for key, value in permissions.items())
    provider = ('model_providers.fixture={name="Synthetic tool boundary",base_url="http://127.0.0.1:'
        + str(port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,'
        'request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
    mcp = ('mcp_servers.boundary={command=' + json.dumps(sys.executable) + ',args='
        + json.dumps(['-I', '-S', '-B', str(stub), str(control)]) + ',startup_timeout_sec=5,tool_timeout_sec=5,'
        'enabled_tools=["allowed"],tools.allowed.approval_mode="approve"}')
    return ['model_provider="fixture"', provider, 'model=' + json.dumps(model),
        'model_catalog_json=' + json.dumps(str(catalog)), 'model_reasoning_effort="low"',
        'default_permissions="probe"', 'permissions.probe.filesystem={' + fs + '}',
        'permissions.probe.network.enabled=false', 'approval_policy="never"',
        'shell_environment_policy.inherit="none"', 'web_search="disabled"', mcp,
        *['features.' + name + '=false' for name in disabled]]


def read_feature_states(raw, disabled):
    states = {}
    for line in raw.decode().splitlines():
        fields = line.split()
        if fields and fields[0] in disabled:
            if len(fields) < 3 or fields[-1] not in {'false', 'true'} or fields[0] in states:
                raise ProbeError('invalid-effective-feature-readback')
            states[fields[0]] = fields[-1] == 'true'
    return states


def validate_feature_states(states, disabled, *, cli_version=CLI_VERSION,
                            allow_normalized_unified_exec_fixture=False):
    if (type(allow_normalized_unified_exec_fixture) is not bool or cli_version != CLI_VERSION
            or type(states) is not dict or set(states) != set(disabled)
            or any(type(value) is not bool for value in states.values())):
        raise ProbeError('required-feature-disable-unconfirmed')
    if allow_normalized_unified_exec_fixture:
        if (set(disabled) != set(REQUIRED_DISABLED_FEATURES)
                or states.get('unified_exec') is not True
                or any(value for name, value in states.items() if name != 'unified_exec')):
            raise ProbeError('normalized-unified-exec-observation-unconfirmed')
    elif any(states.values()):
        raise ProbeError('required-feature-disable-unconfirmed')
    return states


def feature_state(raw, disabled, *, cli_version=CLI_VERSION,
                  allow_normalized_unified_exec_fixture=False):
    return validate_feature_states(read_feature_states(raw, disabled), disabled,
        cli_version=cli_version,
        allow_normalized_unified_exec_fixture=allow_normalized_unified_exec_fixture)


def control_contract(allow_normalized_unified_exec_fixture):
    if type(allow_normalized_unified_exec_fixture) is not bool:
        raise ProbeError('invalid-control-mode-opt-in')
    observation = allow_normalized_unified_exec_fixture
    return {'control_mode': NORMALIZED_CONTROL_MODE if observation else STRICT_CONTROL_MODE,
        'allow_normalized_unified_exec_fixture': observation,
        'fixed_observation_only': observation,
        'normalization_source': dict(NORMALIZATION_SOURCE) if observation else None}


def configuration_fingerprint(work, home, paths, audit):
    ancestors = audit(work)
    # These are deliberately absent in the fresh home, even though the public
    # CLI can create unrelated runtime files there. No ambient home is read.
    for name in ['config.toml', 'AGENTS.md', 'AGENTS.override.md', 'auth.json']:
        if os.path.lexists(home / name):
            raise ProbeError('fresh-home-configuration-or-auth-drift')
    files = {}
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ProbeError('bound-input-path-drift')
        files[str(path)] = digest_bytes(path.read_bytes())
    return {'ancestors': ancestors, 'files': files}


def fixture_server(root, control, model, case, receipt):
    lock = threading.Lock()
    calls = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *unused):
            pass

        def do_POST(self):
            with lock:
                try:
                    if (self.path != '/v1/responses' or self.headers.get('Authorization') is not None
                            or self.headers.get('Content-Encoding', 'identity') != 'identity'):
                        raise ProbeError('unexpected-provider-request')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= manifest.MAX_REQUEST_BYTES or len(receipt['requests']) >= 3:
                        raise ProbeError('provider-request-limit')
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ProbeError('provider-request-truncated')
                    stage = len(receipt['requests']) + 1
                    (root / f'request-{stage}.json').write_bytes(raw)
                    request = manifest.decode(raw)
                    advertised = manifest.advertised_tools(raw)
                    if request.get('model') != model:
                        raise ProbeError('provider-model-drift')
                    record = {'stage': stage, 'advertised': advertised}
                    receipt['requests'].append(record)
                    if stage == 1:
                        matches = [entry for entry in advertised['advertised_tools'] if entry['name'] == 'allowed'
                            and entry['type'] == 'function' and entry['namespace'] in
                            {'boundary', 'mcp__boundary', 'mcp__boundary__'}]
                        if len(matches) > 1:
                            raise ProbeError('ambiguous-positive-namespace')
                        namespace = matches[0]['namespace'] if matches else MCP_NAMESPACE
                        item = {'type': 'function_call', 'name': 'allowed', 'namespace': namespace,
                            'arguments': '{}', 'call_id': 'boundary-positive-1'}
                        receipt['positive_identity_source'] = 'structured-advertisement' if matches else 'fixed-fixture-namespace'
                    elif stage == 2:
                        output = find_output(request, calls[0])
                        record['output'] = output
                        if (not positive_output(output) or [item['name'] for item in stub_calls(control)] != ['allowed']):
                            raise ProbeError('positive-control-unconfirmed')
                        receipt['positive_control'] = True
                        item = fixed_call(case, control, calls[0]['namespace'])
                    else:
                        output = find_output(request, calls[1])
                        record['output'] = output
                        receipt['negative_outcome'] = negative_outcome(output, calls[1])
                        item = {'type': 'message', 'role': 'assistant', 'id': 'boundary-final',
                            'content': [{'type': 'output_text', 'text': 'Synthetic boundary fixture finished.'}]}
                    if stage < 3:
                        calls.append(item)
                        record['forced_call'] = item
                        record['advertised_exact'] = any(entry['name'] == item['name']
                            and entry['namespace'] == item.get('namespace') for entry in advertised['advertised_tools'])
                    events = [{'type': 'response.created', 'response': {'id': f'boundary-{stage}'}},
                        {'type': 'response.output_item.done', 'item': item},
                        {'type': 'response.completed', 'response': {'id': f'boundary-{stage}',
                            'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.end_headers()
                    for event in events:
                        self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())
                except (ValueError, KeyError, TypeError, OSError) as error:
                    receipt['fixture_error'] = str(error) if isinstance(error, (ProbeError, manifest.ManifestError)) else type(error).__name__
                    self.send_error(422)

    return http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)


def evaluate(receipt, *, allow_normalized_unified_exec_fixture=False):
    checks = receipt.get('checks', {})
    if (checks.get('forbidden_preserved') is False or checks.get('no_workspace_effect') is False
            or any(call.get('name') != 'allowed' for call in receipt.get('stub_calls', []))):
        return 'failed'
    if (receipt.get('fixture_error') or receipt.get('error') or len(receipt.get('requests', [])) != 3
            or receipt.get('positive_control') is not True or set(checks) != CHECKS
            or not all(value is True for value in checks.values())):
        return 'unknown'
    try:
        contract = control_contract(allow_normalized_unified_exec_fixture)
        if any(key not in receipt or receipt[key] != value or type(receipt[key]) is not type(value)
                for key, value in contract.items()):
            return 'unknown'
        requested = receipt.get('requested_disabled_features')
        if (type(requested) is not dict or set(requested) != set(REQUIRED_DISABLED_FEATURES)
                or any(value is not False for value in requested.values())
                or receipt.get('strict_required_false_satisfied') is not (not allow_normalized_unified_exec_fixture)
                or receipt.get('handler_inventory_complete') is not False
                or receipt.get('production_qualified') is not False
                or receipt.get('repository_completion') is not False
                or (allow_normalized_unified_exec_fixture
                    and NORMALIZATION_LIMITATION not in receipt.get('unknown', []))):
            return 'unknown'
        validate_feature_states(receipt.get('effective_feature_states'), REQUIRED_DISABLED_FEATURES,
            cli_version=receipt.get('cli_version'),
            allow_normalized_unified_exec_fixture=allow_normalized_unified_exec_fixture)
    except (ProbeError, TypeError):
        return 'unknown'
    if receipt.get('negative_outcome') not in {'unsupported-handler', 'readonly-patch-denied'}:
        return 'unknown'
    return 'measured-case-passed' if allow_normalized_unified_exec_fixture else 'passed'


def run_case(base, case, model, executable, broker, broker_path, *,
             allow_normalized_unified_exec_fixture=False):
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-tool-boundary-', dir=base))
    root.chmod(0o700)
    work, home, control = [root / name for name in ['workspace', 'home', 'control']]
    for path in [work, home, control]: path.mkdir(mode=0o700)
    (control / 'sentinel').write_text('synthetic-protected')
    stub = control / 'stub.py'; stub.write_text(STUB_SOURCE); stub.chmod(0o400)
    env = environment(home)
    receipt = {'schema_version': 1, 'scope': 'fixed-synthetic-cli-tool-boundary-only',
        **control_contract(allow_normalized_unified_exec_fixture),
        'requested_disabled_features': {name: False for name in REQUIRED_DISABLED_FEATURES},
        'effective_feature_states': {}, 'strict_required_false_satisfied': False,
        'case': case, 'metadata_model': model, 'fixture': str(root), 'requests': [],
        'phase': 'configuration-preflight',
        'positive_control': False, 'negative_outcome': 'unknown', 'handler_inventory_complete': False,
        'production_qualified': False, 'repository_completion': False,
        'not_run': ['agent', 'write_stdin', 'CodeMode'],
        'unknown': ['complete-runtime-handler-inventory', 'all-cli-descendant-lifecycle',
            'host-provider-egress-containment', 'configuration-races', 'real-provider-and-credentials', 'desktop']}
    if allow_normalized_unified_exec_fixture:
        receipt['unknown'].append(NORMALIZATION_LIMITATION)
    server = process = None
    server_started = False
    source = pathlib.Path(__file__).resolve()
    try:
        broker.audit_client_directory(work)
        version = subprocess.run([str(executable), '--version'], env=env, cwd=work,
            capture_output=True, timeout=10, check=True).stdout.decode().strip()
        receipt['cli_version'] = version
        if version != CLI_VERSION:
            raise ProbeError('unsupported-cli-version')
        receipt['phase'] = 'bundled-catalog-readback'
        catalog_run = subprocess.run([str(executable), 'debug', 'models', '--bundled'],
            env=env, cwd=work, capture_output=True, timeout=10, check=True)
        catalog = control / 'catalog.json'; catalog.write_bytes(catalog_run.stdout); catalog.chmod(0o400)
        metadata = selected_metadata(catalog_run.stdout, model)
        receipt['catalog_sha256'] = digest_bytes(catalog_run.stdout)
        receipt['selected_metadata_sha256'] = manifest.sha(metadata)
        receipt['executable_sha256'] = digest_bytes(executable.read_bytes())
        receipt['phase'] = 'loopback-listener-start'
        server = fixture_server(root, control, model, case, receipt)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        try:
            server_thread.start()
        except RuntimeError:
            raise ProbeError('fixture-server-thread-start-failed') from None
        server_started = True
        overrides = settings(work, home, control, executable, model, catalog, stub, server.server_port, REQUIRED_DISABLED_FEATURES)
        (control / 'settings.json').write_bytes(manifest.canonical(overrides))
        receipt['settings_sha256'] = manifest.sha(overrides)
        config_args = [arg for setting in overrides for arg in ['-c', setting]]
        receipt['phase'] = 'effective-feature-readback'
        features = subprocess.run([str(executable), 'features', 'list', *config_args], env=env,
            cwd=work, capture_output=True, timeout=10, check=True)
        (root / 'features.txt').write_bytes(features.stdout)
        receipt['effective_feature_states'] = read_feature_states(features.stdout, REQUIRED_DISABLED_FEATURES)
        validate_feature_states(receipt['effective_feature_states'], REQUIRED_DISABLED_FEATURES,
            cli_version=version,
            allow_normalized_unified_exec_fixture=allow_normalized_unified_exec_fixture)
        receipt['strict_required_false_satisfied'] = not allow_normalized_unified_exec_fixture
        paths = [source, pathlib.Path(manifest.__file__).resolve(), broker_path.resolve(), executable,
                 pathlib.Path(sys.executable).resolve(), catalog, stub, control / 'settings.json']
        before = configuration_fingerprint(work, home, paths, broker.audit_client_directory)
        receipt['configuration_before'] = before
        receipt['phase'] = 'fixed-cli-invocation'
        argv = [str(executable), 'exec', '--strict-config', '--ignore-user-config', '--ignore-rules',
            '--skip-git-repo-check', '--ephemeral', '--json', '-C', str(work), *config_args,
            'Perform only the fixed credential-free synthetic tool boundary calls.']
        with (root / 'stdout.log').open('wb') as stdout, (root / 'stderr.log').open('wb') as stderr:
            process = subprocess.Popen(argv, env=env, cwd=work, stdin=subprocess.DEVNULL,
                stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True)
            receipt['cli_pid'] = process.pid
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                receipt['error'] = 'cli-timeout-outcome-unknown'
        server.shutdown(); server.server_close(); server = None
        receipt['phase'] = 'post-invocation-readback'
        deadline = time.monotonic() + 5
        while stub_stopped(control) is False and time.monotonic() < deadline:
            time.sleep(0.05)
        after = configuration_fingerprint(work, home, paths, broker.audit_client_directory)
        receipt['configuration_after'] = after
        calls = stub_calls(control)
        receipt['stub_calls'] = calls
        receipt['stub_lifecycle_scope'] = 'only-fixed-no-fork-stub-pid-absence'
        logs = []
        for name in ['stdout.log', 'stderr.log']:
            path = root / name
            if path.stat().st_size > manifest.MAX_REQUEST_BYTES:
                raise ProbeError('cli-diagnostics-too-large')
            logs.append(path.read_bytes())
        receipt['checks'] = {'cli_exited_successfully': process.poll() == 0,
            'configuration_unchanged': before == after,
            'native_metadata_warning_absent': all(b'Model metadata for' not in raw for raw in logs),
            'forbidden_preserved': (control / 'sentinel').read_text() == 'synthetic-protected',
            'no_workspace_effect': not os.path.lexists(work / 'forbidden-marker'),
            'only_allowed_stub_call': [item['name'] for item in calls] == ['allowed'],
            'fixed_stub_stopped': stub_stopped(control)}
        receipt['outcome'] = evaluate(receipt,
            allow_normalized_unified_exec_fixture=allow_normalized_unified_exec_fixture)
        receipt['phase'] = 'completed-readback'
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error) if isinstance(error, (ProbeError, manifest.ManifestError)) else type(error).__name__
        receipt['outcome'] = 'unknown'
    finally:
        if server is not None:
            if server_started:
                server.shutdown()
            server.server_close()
        if process is not None and process.poll() is None:
            receipt['independent_cli_readback_required'] = True
        output = root / 'tool-boundary-evidence.json'
        output.write_bytes(manifest.canonical(receipt) + b'\n')
    return receipt, output


def argument_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--metadata-model', required=True)
    parser.add_argument('--case', choices=CASES, help='Omit to run the six fixed cases sequentially.')
    parser.add_argument('--allow-normalized-unified-exec-fixture', action='store_true',
        help='Opt in to fixed observation only for CLI 0.159.3 normalized UnifiedExec; '
             'does not satisfy the required-false contract or qualify production isolation.')
    return parser


def main(argv=None):
    parser = argument_parser()
    args = parser.parse_args(argv)
    base = args.evidence_root.resolve(strict=True)
    if (sys.platform != 'darwin' or base != args.evidence_root.absolute() or not base.is_dir()
            or not base.is_relative_to('/private/tmp') or not re.fullmatch(r'[A-Za-z0-9_./-]+', str(base))
            or any((parent / '.git').exists() for parent in [base, *base.parents])):
        parser.error('macOS and an existing canonical private/tmp directory outside Git are required')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', args.metadata_model):
        parser.error('literal catalog model slug required')
    executable = pathlib.Path(shutil.which('codex') or '/nonexistent').resolve(strict=True)
    broker, broker_path = load_broker()
    results = []
    for case in [args.case] if args.case else CASES:
        receipt, output = run_case(base, case, args.metadata_model, executable, broker, broker_path,
            allow_normalized_unified_exec_fixture=args.allow_normalized_unified_exec_fixture)
        results.append(receipt['outcome'])
        print(json.dumps({'case': case, 'outcome': receipt['outcome'], 'evidence': str(output),
            'control_mode': receipt['control_mode'], 'fixed_observation_only': receipt['fixed_observation_only'],
            'strict_required_false_satisfied': receipt['strict_required_false_satisfied'],
            'fixture_error': receipt.get('fixture_error'), 'error': receipt.get('error'), 'production_qualified': False}), flush=True)
        if receipt.get('independent_cli_readback_required') or not receipt.get('positive_control'):
            break
    expected = 'measured-case-passed' if args.allow_normalized_unified_exec_fixture else 'passed'
    return 0 if len(results) == (1 if args.case else len(CASES)) and all(result == expected for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
