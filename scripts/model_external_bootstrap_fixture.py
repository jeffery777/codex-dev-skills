"""Fixed anonymous guest: default bootstrap or explicit bounded native cases."""
import base64
import hashlib
import http.server
import importlib.util
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import threading
import time
import zlib

PREFIX = b'ISSUE316-EXTERNAL-BOOTSTRAP:'
FRAME_BYTES = 16384
WRITER_FRAME_BYTES = 32768
HTTP_BYTES = 1048576
HTTP_TOTAL_BYTES = 2097152
RESPONSE_BYTES = 8192
BUNDLE_BYTES = 3145728
COMPRESSED_BYTES = 16384
CASES = ('workspace-write', 'external-write-refusal')
NATIVE_CALL = 'external-native-writer-1'
DIRECT_MODEL = 'fixture-direct'
CATALOG_PATH = '/tmp/registry/catalog.json'
CATALOG_KIND = 'fixed-anonymous-test-catalog'
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp/home',
       'CODEX_HOME': '/tmp/home/.codex', 'TMPDIR': '/tmp/registry',
       'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1,localhost'}
FILES = ('scripts/verify-model-external-bootstrap.py', 'scripts/model_external_bootstrap_fixture.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def argv(boundary, guest, *, port=1, native=False):
    if type(native) is not bool:
        raise ValueError('explicit-native-boolean-required')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('fixed-loopback-port-required')
    # Fixed localhost discard destination; this bootstrap never sends a turn.
    original = guest.cli_argv(port, boundary, 'workspace-write')
    result = original[:4]
    for flag, value in zip(original[4::2], original[5::2]):
        if value.startswith(('permissions.', 'default_permissions=')):
            continue
        if native and value.startswith('model='): continue
        result += [flag, value]
    result += ['-c', 'sandbox_mode="read-only"']
    if native:
        result += ['-c', 'model="' + DIRECT_MODEL + '"', '-c', 'model_catalog_json="' + CATALOG_PATH + '"']
    return result


def catalog_bytes():
    # Fixed synthetic metadata only; no real model, capacity or provider claim.
    model = {'slug': DIRECT_MODEL, 'display_name': 'Synthetic direct fixture',
        'description': 'Anonymous client fixture only',
        'base_instructions': 'Follow only the fixed anonymous test provider.', 'default_reasoning_level': 'low',
        'supported_reasoning_levels': [{'effort': 'low', 'description': 'Fixed fixture setting'}],
        'shell_type': 'unified_exec', 'tool_mode': 'direct', 'visibility': 'list',
        'supported_in_api': True, 'priority': 1, 'support_verbosity': False,
        'apply_patch_tool_type': 'freeform', 'truncation_policy': {'mode': 'bytes', 'limit': 8192},
        'experimental_supported_tools': [], 'input_modalities': ['text'], 'supports_search_tool': False,
        'include_apps_usage_instructions': False, 'context_window': 32768,
        'effective_context_window_percent': 95}
    raw = json.dumps({'models': [model]}, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    if len(raw) > 4096: raise ValueError('external-fixed-catalog-bound')
    return raw


def prepare_catalog(base, receipt):
    raw = catalog_bytes()
    fd = os.open(CATALOG_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    identity = base.guest.file_identity(os.lstat(CATALOG_PATH))
    if base.guest.read_regular(CATALOG_PATH, 4096) != raw:
        raise ValueError('external-catalog-file-readback-drift')
    receipt['catalog_fixture'] = {'source_kind': CATALOG_KIND, 'query_spawn_count': 0,
        'fixture_identity': identity, 'fixture_sha256': hashlib.sha256(raw).hexdigest(),
        'fixture_bytes': len(raw)}


def native_call(case):
    if case not in CASES:
        raise ValueError('fixed-external-case-required')
    command = ("printf '%s\n' 'native-workspace-write-ok' > /workspace/native-write.txt"
               if case == 'workspace-write' else
               "IFS= read -r canary < /inputs/canary || exit 17; "
               "test \"$canary\" = 'fixed-external-canary' || exit 18; "
               "printf '%s\n' 'forbidden-native-write' > /inputs/canary")
    return {'type': 'function_call', 'namespace': 'functions', 'name': 'exec_command', 'call_id': NATIVE_CALL,
            'arguments': json.dumps({'cmd': command, 'workdir': '/workspace', 'shell': '/bin/sh',
                'tty': False, 'yield_time_ms': 10000, 'max_output_tokens': 512,
                'sandbox_permissions': 'use_default'})}


def native_output(output, case, old_guest):
    if type(output) is not str:
        raise ValueError('fixed-native-output-required')
    # Only the fixed denial path differs; preserve the raw carrier separately.
    if case == 'external-write-refusal' and '/control/external-canary' in output:
        raise ValueError('wrong-denial-path')
    validation = output.replace('/inputs/canary', '/control/external-canary')
    if case == 'external-write-refusal':
        header, separator, body = validation.partition('Output:\n')
        if body.startswith('/usr/bin/sh: '):
            validation = header + separator + '/bin/sh: ' + body[len('/usr/bin/sh: '):]
    result = old_guest.writer_output(validation, case)
    result['body'] = output.partition('Output:\n')[2]  # Keep the original diagnostic bytes.
    return result


def response_bytes(stage, case):
    item = native_call(case) if stage == 1 else {'type': 'message', 'role': 'assistant',
        'id': 'external-native-final', 'content': [{'type': 'output_text', 'text': 'Fixed anonymous observation finished.'}]}
    events = [{'type': 'response.created', 'response': {'id': 'external-' + str(stage)}},
              {'type': 'response.output_item.done', 'item': item},
              {'type': 'response.completed', 'response': {'id': 'external-' + str(stage),
               'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
    raw = b''.join(('event: ' + e['type'] + '\ndata: ' + json.dumps(e) + '\n\n').encode() for e in events)
    if len(raw) > RESPONSE_BYTES:
        raise ValueError('fixed-response-byte-bound')
    return raw


def declaration(raw, boundary, case):
    inventory = boundary.manifest.advertised_tools(raw)
    body = boundary.manifest.decode(raw); definitions = []
    def visit(entries, prefix=()):
        for item in entries:
            if item['type'] == 'namespace': visit(item['tools'], (*prefix, item['name']))
            elif (prefix in ((), ('functions',))
                  and (item['name'], item['type']) == ('exec_command', 'function')):
                definitions.append(item)
    visit(body.get('tools', []))
    for item in body.get('input', []):
        if type(item) is dict and item.get('type') == 'additional_tools': visit(item['tools'])
    if len(definitions) != 1:
        raise ValueError('external-native-declaration-required')
    schema = definitions[0]['parameters']; arguments = json.loads(native_call(case)['arguments'])
    properties, required = schema.get('properties', {}), schema.get('required', [])
    if (schema.get('type') != 'object' or type(properties) is not dict or type(required) is not list
            or any(type(key) is not str or key not in arguments for key in required)):
        raise ValueError('external-native-schema-drift')
    for key, argument in arguments.items():
        definition = properties.get(key, {}); kinds = definition.get('type')
        kinds = kinds if type(kinds) is list else [kinds]
        expected = 'boolean' if type(argument) is bool else 'integer' if type(argument) is int else 'string'
        if (expected not in kinds and not (expected == 'integer' and 'number' in kinds)
                or 'enum' in definition and argument not in definition['enum']
                or 'const' in definition and argument != definition['const']):
            raise ValueError('external-native-arguments-drift')
    return inventory


def provider(base, request, receipt):
    """Two reserved requests, bounded memory-only raw observations, no journals."""
    state = {'slots': 0, 'total_bytes': 0, 'failed': False, 'records': [], 'native_output': None}
    receipt['_provider_state'] = state
    case = request['native_case']

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *unused): pass

        def setup(self):
            super().setup(); deadline = time.monotonic() + 5
            self.rfile.close(); self.rfile = io.BufferedReader(base.guest.DeadlineReader(self.connection, deadline))
            self.wfile.close(); self.wfile = base.guest.DeadlineWriter(self.connection, deadline)

        def handle_one_request(self):
            before = state['slots']
            try:
                super().handle_one_request()
            finally:
                # Malformed/unsupported/empty/slow requests cannot disappear.
                if state['slots'] == before:
                    state['failed'] = True

        def send_error(self, *args, **kwargs):
            state['failed'] = True
            return super().send_error(*args, **kwargs)

        def do_POST(self):
            state['slots'] += 1  # Never reuse a partial/failed request slot.
            stage = state['slots']
            try:
                lengths = self.headers.get_all('Content-Length', [])
                if (state['failed'] or stage not in (1, 2) or self.path != '/v1/responses'
                        or self.headers.get_all('Authorization', []) or self.headers.get_all('Transfer-Encoding', [])
                        or len(lengths) != 1 or not re.fullmatch(r'[1-9][0-9]{0,6}', lengths[0])
                        or self.headers.get_all('Content-Encoding', ['identity']) != ['identity']):
                    raise ValueError('fixed-http-shape-required')
                length = int(lengths[0])
                if length > HTTP_BYTES or state['total_bytes'] + length > HTTP_TOTAL_BYTES:
                    raise ValueError('fixed-http-byte-bound')
                state['total_bytes'] += length
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('fixed-http-incomplete')
                response = response_bytes(stage, case)
                # Preserve the bounded failed input before schema checks too.
                state['records'].append({'stage': stage, 'request_base64': base64.b64encode(raw).decode(),
                    'request_sha256': hashlib.sha256(raw).hexdigest(), 'request_bytes': len(raw),
                    'response_base64': base64.b64encode(response).decode(),
                    'response_sha256': hashlib.sha256(response).hexdigest(), 'response_bytes': len(response),
                    'response_sent': False})
                value = base.probe.boundary.manifest.decode(raw)
                advertised = declaration(raw, base.probe.boundary, case)
                if stage == 1:
                    state['declaration'] = advertised
                else:
                    if advertised['advertised_tools'] != state['declaration']['advertised_tools']:
                        raise ValueError('fixed-native-declaration-drift')
                    output = base.probe.boundary.output_text(base.probe.boundary.find_output(value, native_call(case)))
                    state['native_output'] = output
                    try:
                        state['native_result'] = native_output(output, case, base.guest)
                    except ValueError:
                        state['failed'] = True  # Finish observation; never resend the command.
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                self.wfile.write(response); self.wfile.flush()
                state['records'][-1]['response_sent'] = True
            except Exception as error:
                state['failed'] = True
                # Only a short code, never an OS/peer diagnostic or raw request.
                code = str(error)
                receipt['provider_failure_code'] = code if re.fullmatch(r'[a-z][a-z0-9-]{1,80}', code) else 'unknown'
                self.close_connection = True
                try: self.send_error(422)
                except Exception: pass

        def do_GET(self):
            state['failed'] = True; self.close_connection = True; self.send_error(405)

        def finish(self):
            try: super().finish()
            except Exception: state['failed'] = True

    return http.server.HTTPServer(('127.0.0.1', 0), Handler)


def bundle(state):
    """Strict finite observation, independent of the final frame's byte bound."""
    # Avoid base64 inside compressed JSON. UTF-8 roundtrip preserves raw bytes;
    # invalid UTF-8 stays unknown, never normalized or replaced.
    packed = dict(state); packed['records'] = []
    for record in state.get('records', []):
        row = dict(record)
        for name in ('request', 'response'):
            row[name + '_text'] = base64.b64decode(row.pop(name + '_base64'), validate=True).decode('utf-8')
        packed['records'].append(row)
    if 'records' not in state: packed.pop('records')
    raw = json.dumps(packed, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
    if len(raw) > BUNDLE_BYTES:
        raise ValueError('external-bundle-byte-bound')
    compressed = zlib.compress(raw)
    if len(compressed) > COMPRESSED_BYTES:
        raise ValueError('external-compressed-byte-bound')
    return {'encoding': 'zlib-utf8-records-base64', 'raw_bytes': len(raw), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'compressed_bytes': len(compressed), 'compressed_sha256': hashlib.sha256(compressed).hexdigest(),
            'data': base64.b64encode(compressed).decode()}


def workspace_expected(path, case, reader):
    names = sorted(p.name for p in path.iterdir())
    if case == 'workspace-write':
        return names == ['native-write.txt'] and reader(path / 'native-write.txt', 128) == b'native-workspace-write-ok\n'
    return names == []


def run():
    receipt = {'schema_version': 1, 'scope': 'anonymous-external-bootstrap-only',
               'cli_spawn_count': 0, 'cli_wait': 'unknown', 'passed': False,
               'qualified': False, 'production_qualified': False}
    child = capture = server = serving = None
    frame_bound = FRAME_BYTES
    try:
        os.umask(0o077)
        fixture = pathlib.Path('/fixture')
        sys.path.insert(0, str(fixture / 'scripts'))
        sys.path.insert(0, str(fixture / 'skills/loop-engineering/scripts'))
        base = load('external_fixed_host', fixture / 'scripts/verify-model-app-server-container.py')
        guest = base.guest
        request = base.helpers._reload_json(guest.read_regular('/inputs/request.json', 65536))
        case = request.get('native_case')
        if case is not None:
            if case not in CASES:
                raise ValueError('fixed-external-case-required')
            frame_bound = WRITER_FRAME_BYTES
        if (set(request) != {'schema_version', 'run_id', 'uid', 'gid', 'sources'} | ({'native_case'} if case else set())
                or type(request['schema_version']) is not int or request['schema_version'] != 1
                or type(request['uid']) is not int or type(request['gid']) is not int
                or request['uid'] != os.getuid() or request['gid'] != os.getgid()
                or min(os.getuid(), os.getgid()) <= 0
                or type(request['run_id']) is not str or not re.fullmatch(r'[a-f0-9]{32}', request['run_id'])
                or type(request['sources']) is not dict
                or set(request['sources']) != set(base.FILES + FILES)
                or dict(os.environ) != {'PATH': ENV['PATH'], 'HOME': ENV['HOME'], 'LANG': ENV['LANG']}
                or sys.version_info[:3] != (3, 12, 13)):
            raise ValueError('guest-context-drift')
        receipt['run_id'] = request['run_id']
        for name, digest in request['sources'].items():
            if hashlib.sha256(guest.read_regular(fixture / name, 1048576)).hexdigest() != digest:
                raise ValueError('guest-source-drift')
        fd = os.open(fixture / 'codex', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != guest.BINARY_BYTES
                    or before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o500
                    or hashlib.file_digest(stream, 'sha256').hexdigest() != guest.BINARY_SHA
                    or guest.file_identity(before) != guest.file_identity(os.fstat(stream.fileno()))
                    or guest.file_identity(before) != guest.file_identity(os.lstat(fixture / 'codex'))):
                raise ValueError('guest-binary-drift')
        info = os.lstat('/tmp'); capacity = os.statvfs('/tmp')
        rows = [row.split() for row in guest.read_regular('/proc/self/mountinfo', 262144).decode().splitlines()]
        rows = [row for row in rows if len(row) >= 10 and row[4] == '/tmp']
        if (len(rows) != 1 or rows[0][rows[0].index('-') + 1] != 'tmpfs'
                or not {'rw', 'nosuid', 'nodev', 'noexec'} <= set(rows[0][5].split(','))
                or info.st_uid != os.getuid() or info.st_gid != os.getgid()
                or not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
                or capacity.f_blocks * capacity.f_frsize != 16777216
                or list(pathlib.Path('/workspace').iterdir()) or list(pathlib.Path('/tmp').iterdir())
                or guest.read_regular('/inputs/canary', 128) != guest.CANARY_BYTES):
            raise ValueError('guest-private-context-drift')
        receipt['tmpfs'] = {'mountinfo': rows[0], 'capacity_bytes': 16777216, 'uid': info.st_uid,
                            'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode)}
        for name in ('home', 'home/.codex', 'registry', 'codex-daemon-' + str(os.getuid())):
            (pathlib.Path('/tmp') / name).mkdir(mode=0o700)
        port = 1
        if case:
            receipt['native_case'] = case
            prepare_catalog(base, receipt)
            server = provider(base, request, receipt); port = server.server_port
            receipt['_provider_state']['catalog_fixture'] = receipt.pop('catalog_fixture')
            serving = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
            serving.start()
        command = argv(base.probe.boundary, guest, port=port, native=bool(case))
        receipt['cli_argv'] = command
        child = subprocess.Popen(command, cwd='/workspace', env=ENV, stdin=None, stdout=None,
                                 stderr=subprocess.PIPE, close_fds=True, pass_fds=())
        receipt['cli_spawn_count'] = 1; receipt['cli_pid'] = child.pid
        capture = base.probe.transport._StderrCapture(child.stderr); capture.start()
        receipt['cli_exit_code'] = child.wait(timeout=30); receipt['cli_wait'] = 'observed'
        receipt['workspace_empty'] = not list(pathlib.Path('/workspace').iterdir())
        receipt['workspace_expected'] = workspace_expected(pathlib.Path('/workspace'), case, guest.read_regular)
        receipt['canary_preserved'] = guest.read_regular('/inputs/canary', 128) == guest.CANARY_BYTES
        if case:
            record = receipt['_provider_state']['catalog_fixture']
            receipt['catalog_preserved'] = (guest.file_identity(os.lstat(CATALOG_PATH)) == record['fixture_identity']
                and hashlib.sha256(guest.read_regular(CATALOG_PATH, 65536)).hexdigest() == record['fixture_sha256'])
        receipt['passed'] = bool(receipt['cli_exit_code'] == 0 and receipt['workspace_expected']
                                 and receipt['canary_preserved'] and (not case or receipt['catalog_preserved']))
    except Exception as error:
        receipt['failure_class'] = type(error).__name__  # No peer/OS diagnostic strings.
    finally:
        if server is not None:
            stopping = threading.Thread(target=server.shutdown, daemon=True); stopping.start(); stopping.join(6)
            serving.join(1)
            state = receipt.pop('_provider_state')
            state['stopped'] = not serving.is_alive() and not stopping.is_alive()
            server.server_close()
            try:
                if (not state['stopped'] or state['failed'] or state['slots'] != 2 or len(state['records']) != 2
                        or 'native_result' not in state):
                    receipt['passed'] = False
                receipt['provider_port'] = server.server_port
                receipt['provider_bundle'] = bundle(state)
            except Exception as error:
                receipt['passed'] = False; receipt['failure_class'] = 'ProviderObservationBound'
                code = str(error)
                receipt['bundle_failure_code'] = code if code in ('external-bundle-byte-bound', 'external-compressed-byte-bound') else 'unknown'
        if capture is not None:
            capture.finish(time.monotonic() + 2)
            observed = capture.snapshot(); raw = observed.pop('raw')
            # This frame is an observation, never a source/stop/authority receipt.
            if len(raw) > 8192:
                observed['truncated'] = True; receipt['passed'] = False
            observed['raw_base64'] = base64.b64encode(raw[:8192]).decode()
            receipt['cli_stderr'] = observed
            if (not observed['eof'] or not observed['reader_finished'] or observed['overflow']
                    or observed['truncated'] or observed['reader_error']):
                receipt['passed'] = False
        raw = PREFIX + json.dumps(receipt, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'
        if len(raw) > frame_bound:
            receipt['passed'] = False
            raw = PREFIX + b'{"passed":false,"failure_class":"FrameBound"}\n'
        sys.stderr.buffer.write(raw); sys.stderr.buffer.flush()
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
