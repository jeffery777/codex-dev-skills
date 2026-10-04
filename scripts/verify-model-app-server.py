#!/usr/bin/env python3
"""Anonymous public app-server fixture; never provider/containment qualification.

Each case uses an ephemeral thread without execution environments and exactly
one host-controlled dynamic tool. No existing login/config, Docker socket or
real provider is passed to the child. Raw synthetic requests stay outside Git.
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import model_app_server_transport as transport
import model_app_server_metadata as metadata
import model_probe_tools as manifest

spec = importlib.util.spec_from_file_location('appserver_boundary', ROOT / 'scripts/verify-model-tool-boundary.py')
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
VERSION = 'codex-cli 0.159.3'
TOKEN = 'anonymous-dynamic-probe-ok'
CASES = ('shell', 'shell_command', 'exec_command', 'apply_patch', 'view_image',
         'write_stdin', 'code_mode', 'spawn_agent', 'request_permissions', 'unknown_dynamic')


class ProbeError(ValueError):
    pass


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError('fixture-request-deadline')
    return value


class DeadlineReader(io.RawIOBase):
    def __init__(self, connection, deadline):
        self.connection, self.deadline = connection, deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        self.connection.settimeout(remaining(self.deadline))
        return self.connection.recv_into(buffer)


class DeadlineWriter(io.BufferedIOBase):
    def __init__(self, connection, deadline):
        self.connection, self.deadline = connection, deadline

    def writable(self):
        return True

    def write(self, data):
        self.connection.settimeout(remaining(self.deadline))
        self.connection.sendall(data)
        return len(data)


def stop_fixture(service, thread, *, started=True):
    # shutdown() is blocking, so observe it through one fixed daemon helper.
    # Never let an uncertain handler prevent the final failure receipt.
    if thread is None or not started:
        service.server_close()
        return False
    stopped = threading.Event()
    def shutdown():
        try:
            service.shutdown()
        except (OSError, RuntimeError):
            return
        stopped.set()
    control = threading.Thread(target=shutdown, daemon=True)
    try:
        control.start()
        control.join(timeout=2)
    finally:
        service.server_close()
    thread.join(timeout=2)
    return stopped.is_set() and not control.is_alive() and not thread.is_alive()


def deny_outcome(output, call, case):
    if case == 'code_mode' and output == 'code-mode host is disabled':
        return 'code-mode-host-disabled'
    return boundary.negative_outcome(output, call)


def fixed_callback(receipt, identities):
    def callback(params):
        if (params.get('arguments') != {} or params.get('threadId') != identities.get('threadId')
                or params.get('turnId') != identities.get('turnId')
                or params.get('callId') != 'boundary-positive-1'
                or not identities.get('threadId') or not identities.get('turnId')):
            raise ProbeError('unexpected-dynamic-call')
        if receipt['accepted_dynamic_calls'] != 0:
            raise ProbeError('dynamic-call-repeated')
        receipt['accepted_dynamic_calls'] = 1
        return {'success': True, 'contentItems': [{'type': 'inputText', 'text': TOKEN}]}
    return callback


def passed(receipt):
    return (receipt.get('positive_control') is True
            and type(receipt.get('accepted_dynamic_calls')) is int and receipt['accepted_dynamic_calls'] == 1
            and receipt.get('negative_outcome') in {'unsupported-handler', 'readonly-patch-denied', 'code-mode-host-disabled'}
            and receipt.get('turn_status') == 'completed'
            and receipt.get('sentinel_preserved') is True and receipt.get('client_unchanged') is True
            and receipt.get('version_verified') is True and receipt.get('binary_unchanged') is True
            and receipt.get('fixture_stopped') is True
            and type(receipt.get('metadata')) is dict
            and receipt['metadata'].get('feature_inventory_complete') is True
            and receipt['metadata'].get('startup_isolation_qualified') is False
            and receipt['metadata'].get('thread_snapshot_verified') is False
            and type(receipt.get('process_readback')) is dict
            and type(receipt['process_readback'].get('exit_code')) is int
            and receipt['process_readback'] == {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}
            and 'failure_class' not in receipt and 'fixture_error' not in receipt)


def negative_call(case, control):
    if case in ('shell', 'shell_command', 'exec_command', 'apply_patch'):
        return boundary.fixed_call(case, control)
    call = {'type': 'function_call', 'call_id': 'boundary-negative-1', 'arguments': '{}'}
    if case == 'view_image':
        call.update(name='view_image', arguments=json.dumps({'path': str(control / 'sentinel')}))
    elif case == 'write_stdin':
        call.update(name='write_stdin', arguments=json.dumps({'session_id': 1, 'chars': 'synthetic-forbidden'}))
    elif case == 'code_mode':
        call.update(type='custom_tool_call', namespace='functions', name='exec',
                    input='text(await tools.exec_command({cmd:"printf synthetic-forbidden > forbidden-marker"}))')
        call.pop('arguments')
    elif case == 'spawn_agent':
        call.update(name='spawn_agent', arguments=json.dumps({'message': 'Synthetic refusal case. Do not access real providers.'}))
    elif case == 'request_permissions':
        call.update(name='request_permissions', arguments=json.dumps({'permissions': {'network': {'enabled': True}}}))
    elif case == 'unknown_dynamic':
        call.update(name='unconfigured_packet_probe')
    else:
        raise ProbeError('unknown-case')
    return call


def server(root, case, control, receipt):
    lock = threading.Lock()
    calls = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            deadline = time.monotonic() + 5
            self.rfile.close()
            self.rfile = io.BufferedReader(DeadlineReader(self.connection, deadline))
            self.wfile.close()
            self.wfile = DeadlineWriter(self.connection, deadline)

        def log_message(self, *unused):
            pass

        def do_POST(self):
            with lock:
                try:
                    if self.path != '/v1/responses' or self.headers.get('Authorization') is not None or self.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ProbeError('unexpected-provider-request')
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= manifest.MAX_REQUEST_BYTES or len(receipt['requests']) >= 3:
                        raise ProbeError('request-limit')
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ProbeError('truncated-request')
                    request = manifest.decode(raw)
                    stage = len(receipt['requests']) + 1
                    (root / f'request-{stage}.json').write_bytes(raw)
                    record = {'stage': stage, 'advertised': manifest.advertised_tools(raw)}
                    receipt['requests'].append(record)
                    if stage == 1:
                        item = {'type': 'function_call', 'name': 'packet_probe', 'arguments': '{}', 'call_id': 'boundary-positive-1'}
                    elif stage == 2:
                        output = boundary.find_output(request, calls[0])
                        if boundary.output_text(output) != TOKEN or type(receipt['accepted_dynamic_calls']) is not int or receipt['accepted_dynamic_calls'] != 1:
                            raise ProbeError('positive-control-unconfirmed')
                        receipt['positive_control'] = True
                        item = negative_call(case, control)
                    else:
                        output = boundary.find_output(request, calls[1])
                        record['negative_output'] = output
                        receipt['negative_outcome'] = deny_outcome(output, calls[1], case)
                        item = {'type': 'message', 'role': 'assistant', 'id': 'anonymous-final', 'content': [{'type': 'output_text', 'text': 'Anonymous app-server fixture finished.'}]}
                    if stage < 3:
                        calls.append(item)
                        record['forced_call'] = item
                    events = [{'type': 'response.created', 'response': {'id': f'anonymous-{stage}'}},
                              {'type': 'response.output_item.done', 'item': item},
                              {'type': 'response.completed', 'response': {'id': f'anonymous-{stage}', 'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.end_headers()
                    for event in events:
                        self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())
                except (ValueError, KeyError, TypeError, OSError) as error:
                    receipt['fixture_error'] = str(error) if type(error) is ProbeError else type(error).__name__
                    self.send_error(422)

    # The fixed fixture has one sequential three-request conversation. A serial
    # server bounds worker allocation before unauthenticated connections arrive.
    return http.server.HTTPServer(('127.0.0.1', 0), Handler)


def run_case(parent, executable, case):
    root = pathlib.Path(tempfile.mkdtemp(prefix='appserver-' + case + '-', dir=parent))
    root.chmod(0o700)
    home, client, control = [root / name for name in ('home', 'client', 'control')]
    for path in (home, client, control, home / '.codex'):
        path.mkdir(mode=0o700)
    client.chmod(0o500)
    (control / 'sentinel').write_text('synthetic-only')
    receipt = {'case': case, 'production_qualified': False, 'repository_completion': False,
               'accepted_dynamic_calls': 0, 'requests': [], 'positive_control': False,
               'handler_inventory_complete': False, 'real_provider': False, 'existing_login_used': False}
    service = thread = session = None
    service_started = False
    try:
        service = server(root, case, control, receipt)
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        service_started = True
        permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
                       str(client): 'read', str(home): 'deny', str(control): 'deny', str(executable): 'read', str(executable.parent): 'read'}
        fs = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in permissions.items())
        provider = ('model_providers.fixture={name="Anonymous app-server fixture",base_url="http://127.0.0.1:'
                    + str(service.server_port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
        settings = ['model_provider="fixture"', provider, 'model="gpt-6-sol"', 'model_reasoning_effort="low"',
                    'default_permissions="probe"', 'permissions.probe.filesystem={' + fs + '}',
                    'permissions.probe.network.enabled=false', 'approval_policy="never"', 'web_search="disabled"',
                    'shell_environment_policy.inherit="none"', 'notify=[]', 'agents.enabled=false',
                    'features.code_mode_host={enabled=false,disable_in_process_fallback=false}',
                    *['features.' + key + '=false' for key in
                      sorted(set(boundary.REQUIRED_DISABLED_FEATURES) | {'hooks', 'apps', 'plugins',
                             'multi_agent_v2', 'image_generation', 'memories'}) if key != 'code_mode_host']]
        argv = [str(executable), 'app-server', '--stdio', '--strict-config']
        for value in settings:
            argv += ['-c', value]
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home / '.codex'), 'NO_PROXY': '127.0.0.1,localhost'}

        version = subprocess.run([str(executable), '--version'], cwd=str(client), env=env,
                                 capture_output=True, timeout=5, check=False)
        if version.returncode != 0 or version.stdout.decode('utf-8').strip() != VERSION:
            raise ProbeError('unsupported-cli-version')
        receipt['version_verified'] = True
        receipt['cli_version'] = VERSION
        receipt['binary_sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
        identities = {}
        session = transport.Session(argv, cwd=str(client), env=env, limits=transport.Limits(timeout=15, close_timeout=5),
                                    fixed_tool='packet_probe', tool_callback=fixed_callback(receipt, identities))
        session.request('initialize', {'clientInfo': {'name': 'anonymous_packet_probe', 'version': '1'}, 'capabilities': {'experimentalApi': True}})
        started = session.request('thread/start', {'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'allowProviderModelFallback': False,
                    'cwd': str(client), 'ephemeral': True, 'permissions': 'probe', 'approvalPolicy': 'never', 'environments': [],
                    'dynamicTools': [{'type': 'function', 'name': 'packet_probe', 'description': 'Fixed anonymous positive control',
                                     'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}, 'deferLoading': False}]})
        receipt['thread_configuration'] = {key: started.get(key) for key in ('model', 'modelProvider', 'cwd', 'approvalPolicy', 'activePermissionProfile')}
        if receipt['thread_configuration'] != {'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'cwd': str(client),
                'approvalPolicy': 'never', 'activePermissionProfile': {'id': 'probe', 'extends': None}}:
            raise ProbeError('thread-configuration-drift')
        identities['threadId'] = started['thread']['id']
        receipt['metadata'] = metadata.collect(session, cwd=str(client), thread_id=identities['threadId'])
        turn = session.request('turn/start', {'threadId': identities['threadId'], 'environments': [],
                        'input': [{'type': 'text', 'text': 'Anonymous protocol fixture. Do not access real data.'}]})
        identities['turnId'] = turn['turn']['id']
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            note = session.notification()
            if note['method'] == 'turn/completed':
                if note['params'].get('threadId') != identities['threadId'] or note['params']['turn'].get('id') != identities['turnId']:
                    raise ProbeError('turn-identity-drift')
                receipt['turn_status'] = note['params']['turn']['status']
                break
        receipt['sentinel_preserved'] = (control / 'sentinel').read_text() == 'synthetic-only'
        receipt['client_unchanged'] = not list(client.iterdir())
        receipt['binary_unchanged'] = hashlib.sha256(executable.read_bytes()).hexdigest() == receipt['binary_sha256']
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired, transport.TransportError) as error:
        receipt['passed'] = False
        receipt['failure_class'] = getattr(error, 'code', type(error).__name__)
    finally:
        if session is not None:
            try:
                receipt['process_readback'] = session.close()
            except (OSError, ValueError, TypeError, RuntimeError):
                receipt['process_readback'] = {'protocol': 'unknown', 'direct_child': 'unknown', 'descendants': 'unknown'}
        if service is not None:
            try:
                receipt['fixture_stopped'] = stop_fixture(service, thread, started=service_started)
            except (OSError, RuntimeError):
                receipt['fixture_stopped'] = False
        receipt['passed'] = passed(receipt)
        (root / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return root, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--case', choices=CASES, required=True)
    args = parser.parse_args()
    parent = args.evidence_root.resolve(strict=True)
    if not parent.is_dir() or any((p / '.git').exists() for p in (parent, *parent.parents)):
        parser.error('existing evidence directory outside Git required')
    selected = shutil.which('codex')
    if selected is None:
        parser.error('installed Codex CLI required')
    executable = pathlib.Path(selected).resolve(strict=True)
    root, receipt = run_case(parent, executable, args.case)
    print(json.dumps({'evidence': str(root / 'receipt.json'), 'case': args.case, 'passed': receipt['passed'], 'production_qualified': False, 'failure_class': receipt.get('failure_class')}))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
