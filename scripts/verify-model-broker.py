#!/usr/bin/env python3
"""Opt-in macOS, credential-free CLI -> stdio MCP -> Docker experiment.

Run with project-python and --evidence-root /private/tmp. Requires Codex 0.159.3
and the already installed immutable image below. Retains one private fixture and
at most one container; never pulls, builds, stops, removes, or promotes results.
This synthetic transport probe does not qualify an adapter or repository work.
Host patch enforcement is intentionally outside this generic-metadata probe.
"""
import argparse
import hashlib
import http.server
import importlib.util
import json
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time

IMAGE = 'sha256:4db228bee7e7f1c0de9fc52c1ac8917431efeb7e44842d7746103e1ce9f9f614'
MAX_MESSAGE = 32768
MAX_COMMAND = 4096
TOOL_DESCRIPTION = 'Synthetic isolated worker command; exactly one dispatch.'
# These generic, top-level CLI helpers also appeared in the measured manifest.
# The fixture never invokes them; its only MCP server advertises no resources.
PASSIVE_CLI_TOOLS = {'update_plan', 'request_user_input', 'list_mcp_resources',
    'list_mcp_resource_templates', 'read_mcp_resource'}
DISABLED_FEATURES = ('shell_tool', 'unified_exec', 'view_image', 'apps', 'hooks',
    'plugins', 'remote_plugin', 'multi_agent', 'multi_agent_v2', 'goals', 'memories',
    'code_mode', 'code_mode_host', 'code_mode_only', 'code_mode_prewarm',
    'enable_request_compression', 'browser_use', 'computer_use', 'image_generation',
    'skill_search', 'skill_mcp_dependency_install', 'tool_suggest', 'daemon_auto_start')
# This fixture has no caller-selectable shell command. The wire still validates
# arbitrary bounded strings, but dispatch requires this exact synthetic packet.
WORKER_COMMAND = ('test "${BROKER_SYNTHETIC_CANARY+x}" != x || exit 21; '
    'test ! -e /var/run/docker.sock && test ! -e /control && test ! -e /source '
    '&& test ! -e /sibling || exit 22; '
    'test "$(cat /workspace/sentinel)" = synthetic-worker || exit 23; '
    'printf worker-observed > /workspace/result')


class ProbeError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ProbeError('duplicate-json-key')
        value[key] = item
    return value


def decode(raw):
    if len(raw) > MAX_MESSAGE:
        raise ProbeError('message-too-large')
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ProbeError('nonfinite-json')))


def validate_arguments(arguments):
    if type(arguments) is not dict or set(arguments) != {'cmd'}:
        raise ProbeError('only-cmd-is-accepted')
    command = arguments['cmd']
    if (type(command) is not str or not command.strip() or '\x00' in command
            or len(command.encode()) > MAX_COMMAND):
        raise ProbeError('invalid-command')
    return command


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def packet_store(control):
    # In bridge mode these are frozen copies in the private control directory.
    sys.path.insert(0, str(control))
    from model_packet_store import PacketStore
    return PacketStore(control / 'ledger', 'synthetic-broker')


def clean_environment(home):
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home),
        'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost',
        'PYTHONDONTWRITEBYTECODE': '1'}


def command(argv, env, cwd, timeout=15):
    result = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=timeout, close_fds=True)
    if result.returncode:
        # Do not surface arbitrary stderr, which could contain ambient data.
        raise ProbeError('trusted-command-failed:' + pathlib.Path(argv[0]).name)
    if len(result.stdout.encode()) > 1024 * 1024:
        raise ProbeError('trusted-command-output-too-large')
    return result.stdout.strip()


def audit_client_directory(client):
    if client != client.resolve(strict=True):
        raise ProbeError('client-symlink')
    inspected = []
    for parent in [client, *client.parents]:
        for name in ('.codex', '.agents', '.git', 'AGENTS.md', 'AGENTS.override.md'):
            path = parent / name
            if os.path.lexists(path):
                raise ProbeError('unexpected-client-configuration:' + str(path))
        inspected.append(str(parent))
    for path in ('/etc/codex/config.toml', '/etc/codex/requirements.toml'):
        if os.path.lexists(path):
            raise ProbeError('system-configuration-requires-review')
    return inspected


def worker_options(workspace, volumes):
    options = ['run', '-d', '--no-healthcheck', '--pull=never', '--network=none',
        '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
        '--pids-limit=32', '--memory=128m', '--memory-swap=128m', '--cpus=1',
        '--user=65534:65534', '--workdir=/workspace',
        '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m', '--log-driver=none']
    for volume in sorted(volumes):
        options += ['--tmpfs', volume + ':ro,noexec,nosuid,nodev,size=1m']
    return options + ['--mount', f'type=bind,src={workspace},dst=/workspace',
        '--entrypoint=/bin/sh', IMAGE, '-c', WORKER_COMMAND]


def validate_inspect(value, workspace, volumes, *, stopped):
    host, config, state = value['HostConfig'], value['Config'], value['State']
    expected_tmpfs = {'/tmp': 'rw,noexec,nosuid,nodev,size=8m', **{
        volume: 'ro,noexec,nosuid,nodev,size=1m' for volume in volumes}}
    if (value['Image'] != IMAGE or host['NetworkMode'] != 'none'
            or host['ReadonlyRootfs'] is not True or host['Privileged'] is not False
            or host['CapDrop'] != ['ALL'] or host.get('CapAdd')
            or host['SecurityOpt'] != ['no-new-privileges']
            or host['PidsLimit'] != 32 or host['Memory'] != 128 * 1024 * 1024
            or host['MemorySwap'] != host['Memory'] or host['NanoCpus'] != 1000000000
            or host['Tmpfs'] != expected_tmpfs or host.get('Devices')
            or host.get('VolumesFrom') or host['AutoRemove'] is not False
            or host['RestartPolicy']['Name'] != 'no'
            or config['User'] != '65534:65534' or config['WorkingDir'] != '/workspace'
            or config['Entrypoint'] != ['/bin/sh'] or config['Cmd'] != ['-c', WORKER_COMMAND]
            or config['Healthcheck']['Test'] != ['NONE']):
        raise ProbeError('worker-policy-readback-mismatch')
    mounts = value['Mounts']
    binds = [entry for entry in mounts if entry.get('Type') == 'bind']
    if (len(binds) != 1 or binds[0].get('Source') != str(workspace)
            or binds[0].get('Destination') != '/workspace' or binds[0].get('RW') is not True
            or any(entry.get('Type') not in {'bind', 'tmpfs'} for entry in mounts)
            or any(entry.get('Type') == 'tmpfs' and entry.get('Destination') not in expected_tmpfs
                for entry in mounts)):
        raise ProbeError('worker-mount-readback-mismatch')
    if any(entry.startswith('BROKER_SYNTHETIC_CANARY=') for entry in config['Env']):
        raise ProbeError('worker-environment-canary-leak')
    if stopped and (state['Running'] is not False or state['Status'] != 'exited'
            or state['ExitCode'] != 0 or state.get('OOMKilled') is not False
            or not state.get('FinishedAt') or state['FinishedAt'].startswith('0001-')):
        raise ProbeError('worker-stop-not-established')


class Broker:
    """Fixed synthetic packet: claimed before dispatch, never replayed."""
    def __init__(self, store, target, dispatch):
        self.store, self.target, self.dispatch = store, target, dispatch

    def call(self, arguments):
        cmd = validate_arguments(arguments)
        if cmd != WORKER_COMMAND:
            raise ProbeError('command-outside-synthetic-packet')
        claim = self.store.claim('attempt-1', digest(arguments), self.target, expected_revision=0)
        if not claim['claimed']:
            raise ProbeError('replay-rejected-outcome-unknown')
        try:
            return self.dispatch()
        finally:
            # Only the supervising probe may checkpoint after independent stop
            # readback. A lost MCP response leaves the durable attempt unknown.
            self.store.retain_unknown('attempt-1')


class Protocol:
    def __init__(self, broker):
        self.broker, self.initialized, self.ready = broker, False, False

    def handle(self, value):
        if type(value) is not dict or set(value) - {'jsonrpc', 'id', 'method', 'params'}:
            raise ProbeError('invalid-rpc-envelope')
        if value.get('jsonrpc') != '2.0' or type(value.get('method')) is not str:
            raise ProbeError('invalid-rpc-envelope')
        method, params = value['method'], value.get('params', {})
        if type(params) is not dict:
            raise ProbeError('invalid-rpc-params')
        # MCP request metadata is transport context, never worker arguments.
        # Codex's traced pagination can attach it even to tools/list. It cannot
        # override name, cmd, packet, target, or the fixed launcher configuration.
        meta = params.get('_meta', {})
        if type(meta) is not dict or len(canonical(meta)) > 4096:
            raise ProbeError('invalid-rpc-metadata')
        params = {key: item for key, item in params.items() if key != '_meta'}
        if method == 'notifications/initialized':
            if 'id' in value or params or not self.initialized or self.ready:
                raise ProbeError('invalid-initialized-notification')
            self.ready = True
            return None
        if type(value.get('id')) not in {str, int} or len(str(value['id'])) > 80:
            raise ProbeError('invalid-rpc-id')
        if method == 'initialize':
            if self.initialized or set(params) != {'protocolVersion', 'capabilities', 'clientInfo'}:
                raise ProbeError('invalid-initialize')
            info = params['clientInfo']
            if (type(params['protocolVersion']) is not str or type(params['capabilities']) is not dict
                    or type(info) is not dict or set(info) - {'name', 'version', 'title'}
                    or not {'name', 'version'} <= set(info)
                    or any(type(item) is not str or len(item) > 200 for item in info.values())):
                raise ProbeError('invalid-initialize')
            self.initialized = True
            return {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}},
                'serverInfo': {'name': 'synthetic-broker', 'version': '1'}}
        if not self.ready:
            raise ProbeError('initialization-required')
        if method == 'tools/list' and not params:
            return {'tools': [{'name': 'run', 'description': TOOL_DESCRIPTION,
                'inputSchema': {'type': 'object', 'properties': {'cmd': {'type': 'string',
                    'minLength': 1, 'maxLength': MAX_COMMAND}}, 'required': ['cmd'],
                    'additionalProperties': False}}]}
        if method == 'tools/call' and set(params) == {'name', 'arguments'} and params['name'] == 'run':
            if meta.get('openai/readOnly') is True:
                raise ProbeError('read-only-call-cannot-dispatch-worker')
            result = self.broker.call(params['arguments'])
            return {'content': [{'type': 'text', 'text': json.dumps(result)}], 'isError': False}
        raise ProbeError('unsupported-method-or-params')


def rpc_shape(value):
    """Bounded wire shape diagnostic: never retain metadata or argument values."""
    def keys(item):
        return sorted(str(key)[:80] for key in item)[:16] if type(item) is dict else []
    params = value.get('params', {}) if type(value) is dict else {}
    method = value.get('method') if type(value) is dict else None
    return {'method': method if method in {'initialize', 'notifications/initialized',
            'tools/list', 'tools/call'} else 'unsupported',
        'envelope_keys': keys(value), 'params_keys': keys(params),
        'client_info_keys': keys(params.get('clientInfo')) if type(params) is dict else [],
        'metadata_keys': keys(params.get('_meta')) if type(params) is dict else []}


def bridge_main(control):
    config = json.loads((control / 'launch.json').read_text())
    env = clean_environment(control / 'engine-home')
    engine = [config['docker'], '--host', config['endpoint']]
    workspace = pathlib.Path(config['workspace'])
    store = packet_store(control)

    def dispatch():
        cid = command(engine + worker_options(workspace, config['volumes']), env, control)
        if not re.fullmatch('[0-9a-f]{64}', cid):
            raise ProbeError('invalid-container-identity')
        (control / 'container-id').write_text(cid)
        initial = json.loads(command(engine + ['inspect', cid], env, control))[0]
        validate_inspect(initial, workspace, config['volumes'], stopped=False)
        waited = command(engine + ['wait', cid], env, control, timeout=15)
        final = json.loads(command(engine + ['inspect', cid], env, control))[0]
        (control / 'worker-inspect.json').write_bytes(canonical(final))
        validate_inspect(final, workspace, config['volumes'], stopped=True)
        if waited != '0':
            raise ProbeError('worker-wait-failed')
        return {'worker_result': 'observed', 'wait_exit': 0, 'stopped': True}

    protocol = Protocol(Broker(store, config['target_sha256'], dispatch))
    # Both request count and line length are bounded; no tool can change config.
    for _ in range(16):
        raw = sys.stdin.buffer.readline(MAX_MESSAGE + 1)
        if not raw:
            return 0
        value = None
        try:
            value = decode(raw)
            with (control / 'bridge-wire-shapes.jsonl').open('ab') as stream:
                stream.write(canonical(rpc_shape(value)) + b'\n')
            result = protocol.handle(value)
            if result is None:
                continue
            response = {'jsonrpc': '2.0', 'id': value['id'], 'result': result}
        except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as error:
            # Never echo command bodies, environment, or arbitrary exception text.
            response = {'jsonrpc': '2.0', 'id': value.get('id') if type(value) is dict else None,
                'error': {'code': -32602, 'message': 'synthetic-broker-rejected'}}
            diagnostic = {'error_type': type(error).__name__,
                'reason': str(error) if isinstance(error, ProbeError) else 'operation-failed',
                **rpc_shape(value)}
            # Shapes only; never log command, client metadata values, or env.
            with (control / 'bridge-errors.jsonl').open('ab') as stream:
                stream.write(canonical(diagnostic) + b'\n')
        print(json.dumps(response), flush=True)
        if len(raw) > MAX_MESSAGE:
            return 1
    return 1


def catalog_tools(entries, namespace=None, depth=0):
    if type(entries) is not list or len(entries) > 64 or depth > 4:
        raise ProbeError('invalid-tool-manifest')
    found = []
    for entry in entries:
        if type(entry) is not dict:
            raise ProbeError('invalid-tool-manifest')
        if entry.get('type') == 'namespace':
            found += catalog_tools(entry.get('tools', []), entry['name'], depth + 1)
        elif entry.get('type') in {'function', 'custom'}:
            found.append((entry, namespace))
        else:
            raise ProbeError('unsupported-tool-manifest-type')
    return found


def select_tools(entries):
    catalog = catalog_tools(entries)
    broker = [(entry, space) for entry, space in catalog
        if entry['type'] == 'function' and TOOL_DESCRIPTION in entry.get('description', '')
        and set(entry.get('parameters', {}).get('properties', {})) == {'cmd'}]
    if len(broker) != 1:
        raise ProbeError('request-tools-not-resolved')
    if any(entry is not broker[0][0] and not (space is None and entry['type'] == 'function'
            and entry['name'] in PASSIVE_CLI_TOOLS) for entry, space in catalog):
        raise ProbeError('unexpected-model-tool')
    return broker[0]


def fixture_server(receipt, canary=None):
    lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *unused):
            pass

        def do_POST(self):
            with lock:
                try:
                    if self.path != '/v1/responses' or self.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ProbeError('unsupported-fixture-request')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 1024 * 1024:
                        raise ProbeError('invalid-fixture-length')
                    value = json.loads(self.rfile.read(length), object_pairs_hook=pairs)
                    # Inspect the entire decoded request before retaining the
                    # narrowed diagnostic record. Never persist the canary.
                    if canary is not None and canary in canonical(value).decode():
                        receipt['canary_in_provider_request'] = True
                    receipt['last_observed_tools'] = value.get('tools', [])
                    broker = select_tools(value.get('tools', []))
                    stage = len(receipt['requests']) + 1
                    if stage > 2:
                        raise ProbeError('fixture-replay-rejected')
                    record = {'stage': stage, 'tools_sha256': digest(value['tools']),
                        'tool_names': [[entry['name'], space] for entry, space in catalog_tools(value['tools'])]}
                    if stage > 1:
                        outputs = [item for item in value.get('input', [])
                            if item.get('call_id') == 'fixture-' + str(stage - 1)
                            and item.get('type') in {'function_call_output', 'custom_tool_call_output'}]
                        if len(outputs) != 1:
                            raise ProbeError('missing-tool-roundtrip')
                        record['output'] = outputs[0]
                    receipt['requests'].append(record)
                    if stage == 1:
                        entry, namespace = broker
                        item = {'call_id': 'fixture-' + str(stage), 'name': entry['name']}
                        if namespace is not None:
                            item['namespace'] = namespace
                        item.update(type='function_call', arguments=json.dumps({'cmd': WORKER_COMMAND}))
                    else:
                        item = {'type': 'message', 'role': 'assistant', 'id': 'fixture-final',
                            'content': [{'type': 'output_text', 'text': 'Synthetic broker probe complete.'}]}
                    events = [
                        {'type': 'response.created', 'response': {'id': 'response-' + str(stage)}},
                        {'type': 'response.output_item.done', 'item': item},
                        {'type': 'response.completed', 'response': {'id': 'response-' + str(stage),
                            'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.end_headers()
                    for event in events:
                        self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())
                except (ValueError, KeyError, TypeError, OSError) as error:
                    receipt['fixture_error'] = str(error) if isinstance(error, ProbeError) else type(error).__name__
                    self.send_error(422)

    return http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)


def settings(client, home, control, executable, port):
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
        str(client): 'read', str(home): 'deny', str(control): 'deny',
        executable: 'read', str(pathlib.Path(executable).parent): 'read'}
    fs = ','.join(json.dumps(key) + '=' + json.dumps(value) for key, value in permissions.items())
    provider = ('model_providers.fixture={name="Synthetic",base_url="http://127.0.0.1:' + str(port)
        + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,'
        'request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
    bridge = ('mcp_servers.broker={command=' + json.dumps(sys.executable) + ',args='
        + json.dumps(['-I', str(control / 'bridge.py'), '--bridge', str(control)])
        + ',startup_timeout_sec=10,tool_timeout_sec=25,enabled_tools=["run"],'
        + 'tools.run.approval_mode="approve"}')
    return ['model_provider="fixture"', provider, 'model="mock-model"',
        'default_permissions="probe"', 'permissions.probe.filesystem={' + fs + '}',
        'permissions.probe.network.enabled=false', 'approval_policy="never"',
        'shell_environment_policy.inherit="none"', 'web_search="disabled"', bridge,
        *['features.' + key + '=false' for key in DISABLED_FEATURES]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path)
    parser.add_argument('--bridge', type=pathlib.Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.bridge is not None:
        return bridge_main(args.bridge)
    if sys.platform != 'darwin' or args.evidence_root is None:
        parser.error('macOS and --evidence-root are required')
    base = args.evidence_root.resolve(strict=True)
    if (not base.is_dir() or not base.is_relative_to('/private/tmp')
            or any((path / '.git').exists() for path in [base, *base.parents])
            or not re.fullmatch(r'[A-Za-z0-9_./-]+', str(base))):
        parser.error('simple evidence path under /private/tmp outside Git required')
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-broker-', dir=base))
    root.chmod(0o700)
    client, home, control, workspace = [root / name for name in ('client', 'home', 'control', 'worker')]
    for directory in (client, home, control, workspace):
        directory.mkdir(mode=0o700)
    (control / 'engine-home').mkdir(mode=0o700)
    (control / 'ledger').mkdir(mode=0o700)
    (client / 'sentinel').write_text('synthetic-client\n')
    (client / 'sentinel').chmod(0o444)
    client.chmod(0o555)
    (workspace / 'sentinel').write_text('synthetic-worker\n')
    (workspace / 'sentinel').chmod(0o644)
    workspace.chmod(0o777)  # Nonroot container; private parent is never mounted.
    (control / 'sentinel').write_text('synthetic-control\n')
    canary = os.urandom(24).hex()
    env = clean_environment(home)
    receipt = {'schema_version': 1, 'scope': 'macos-synthetic-cli-mcp-docker-only',
        'fixture': str(root), 'production_qualified': False, 'repository_completion': False,
        'host_patch_enforcement': 'not-measured-by-this-probe',
        'requests': [], 'execution_outcome': 'unknown', 'containers_retained': [],
        'canary_in_provider_request': False,
        'unknown': ['production-provider', 'subscription-login', 'linux', 'desktop',
            'complete-handler-and-hook-fault-matrix', 'configuration-race-resistance']}
    server = None
    start = time.monotonic()
    try:
        codex = str(pathlib.Path(shutil.which('codex')).resolve(strict=True))
        docker = str(pathlib.Path(shutil.which('docker')).resolve(strict=True))
        receipt['client_ancestors'] = audit_client_directory(client)
        version = command([codex, '--version'], env, client)
        if version != 'codex-cli 0.159.3':
            raise ProbeError('unsupported-cli-version')
        receipt['cli_version'] = version
        receipt['executable_sha256'] = hashlib.sha256(pathlib.Path(codex).read_bytes()).hexdigest()
        features = command([codex, 'features', 'list'], env, client)
        if set(DISABLED_FEATURES) - {line.split()[0] for line in features.splitlines() if line.strip()}:
            raise ProbeError('unsupported-disable-feature')
        # The only ambient-context read is this trusted Docker lookup. Subsequent
        # Docker calls receive a blank HOME and the exact observed Unix endpoint.
        context = command([docker, 'context', 'show'], os.environ.copy(), client)
        observed = json.loads(command([docker, 'context', 'inspect', context], os.environ.copy(), client))
        endpoint = observed[0]['Endpoints']['docker']['Host']
        if not endpoint.startswith('unix:///') or not stat.S_ISSOCK(os.stat(endpoint[7:]).st_mode):
            raise ProbeError('local-unix-docker-required')
        engine = [docker, '--host', endpoint]
        image = json.loads(command(engine + ['image', 'inspect', IMAGE], env, client))[0]
        if image['Id'] != IMAGE:
            raise ProbeError('image-identity-drift')
        source = pathlib.Path(__file__).resolve().parent
        isolation = load_module('isolation_probe', source / 'verify-model-isolation.py')
        volumes = isolation.validate_image_volumes(image['Config'].get('Volumes'))
        for name in ('model_packet_store.py', 'agent_qualification.py'):
            shutil.copyfile(source.parent / 'skills/loop-engineering/scripts' / name, control / name)
        shutil.copyfile(__file__, control / 'bridge.py')
        for path in control.glob('*.py'):
            path.chmod(0o400)
        target = digest({'workspace': str(workspace), 'image': IMAGE, 'endpoint': endpoint,
            'worker_options': worker_options(workspace, volumes)})
        config = {'docker': docker, 'endpoint': endpoint, 'workspace': str(workspace),
            'volumes': volumes, 'target_sha256': target}
        (control / 'launch.json').write_bytes(canonical(config))
        (control / 'launch.json').chmod(0o400)
        store = packet_store(control)
        store.prepare(digest({'scope': receipt['scope'], 'target': target}))
        receipt.update(image=IMAGE, docker_context=context, endpoint=endpoint, target_sha256=target)
        server = fixture_server(receipt, canary)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        overrides = settings(client, home, control, codex, server.server_port)
        argv = [codex, 'exec', '--strict-config', '--ignore-user-config', '--ignore-rules',
            '--skip-git-repo-check', '--ephemeral', '--json', '-C', str(client)]
        for setting in overrides:
            argv += ['-c', setting]
        argv += ['Run the credential-free synthetic boundary fixture.']
        receipt['settings_sha256'] = digest(overrides)
        audit_client_directory(client)
        run = subprocess.run(argv, cwd=client, env={**env, 'BROKER_SYNTHETIC_CANARY': canary},
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=45, close_fds=True)
        # Redact even this synthetic value: evidence should never train callers
        # to record credentials in tool logs. Retain only the leakage boolean.
        receipt['canary_in_client_output'] = canary in run.stdout + run.stderr
        for name, content in [('stdout', run.stdout), ('stderr', run.stderr)]:
            (root / (name + '.log')).write_text(content.replace(canary, '[REDACTED]'))
        cid_path = control / 'container-id'
        stopped = None
        if cid_path.exists():
            cid = cid_path.read_text()
            receipt['containers_retained'].append(cid)
            final = json.loads(command(engine + ['inspect', cid], env, client))[0]
            validate_inspect(final, workspace, volumes, stopped=True)
            stopped = True
            (root / 'trusted-worker-inspect.json').write_bytes(canonical(final))
        requests = receipt['requests']
        broker_reply = canonical(requests[1]['output']).decode() if len(requests) == 2 else ''
        result = workspace / 'result'
        result_ok = ((result.is_file() and not result.is_symlink() and result.stat().st_nlink == 1
            and result.read_bytes() == b'worker-observed') if stopped else None)
        checks = {'cli_exited_successfully': run.returncode == 0,
            'client_sentinel_preserved': (client / 'sentinel').read_text() == 'synthetic-client\n',
            'control_sentinel_preserved': (control / 'sentinel').read_text() == 'synthetic-control\n',
            'worker_result_observed': result_ok, 'worker_stopped_readback': stopped,
            'tool_roundtrip_observed': ('worker_result' in broker_reply and 'observed' in broker_reply)
                if broker_reply else None,
            'canary_preserved': not receipt['canary_in_client_output']
                and not receipt['canary_in_provider_request'] and canary not in canonical(requests).decode()}
        ledger, _ = store.read_checkpoint()
        checks['at_most_once_claimed'] = ((len(ledger['attempts']) == 1 and ledger['generation'] == 1)
            if ledger['attempts'] else None)
        if checks['at_most_once_claimed']:
            replay = store.claim('attempt-1', digest({'cmd': WORKER_COMMAND}), target, expected_revision=0)
            checks['replay_refused'] = replay['claimed'] is False
        else:
            checks['replay_refused'] = None
        receipt['checks'] = checks
        if all(checks.values()):
            ledger = store.publish_checkpoint('attempt-1', result.read_bytes(), digest({'checks': checks, 'container': cid}))
            receipt.update(execution_outcome='synthetic-checkpoint-captured', checkpoint_sha256=ledger['checkpoint'])
            return 0
        return 1
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error) if isinstance(error, ProbeError) else type(error).__name__
        return 1
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        cid_path = control / 'container-id'
        if cid_path.exists() and cid_path.read_text() not in receipt['containers_retained']:
            receipt['containers_retained'].append(cid_path.read_text())
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        # Provider requests contain only synthetic inputs; avoid storing raw logs
        # elsewhere and retain the exact returned tool-output evidence here.
        output = root / 'broker-evidence.json'
        output.write_text(json.dumps(receipt, indent=2).replace(canary, '[REDACTED]') + '\n')
        print(json.dumps({'evidence': str(output), 'checks': receipt.get('checks', {}),
            'error': receipt.get('error'), 'fixture_error': receipt.get('fixture_error'),
            'execution_outcome': receipt['execution_outcome'], 'production_qualified': False,
            'repository_completion': False}))


if __name__ == '__main__':
    raise SystemExit(main())
