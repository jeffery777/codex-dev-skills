"""Fixed anonymous guest wrapper; stdout belongs exclusively to its CLI child."""
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

BINARY_SHA = '54a834b6b16d8a01ff80f7f9cee4aedec35a61c90379e088792623bf1b4c1e3d'
BINARY_BYTES = 247459224
BWRAP_SHA = 'c547cbdc762a70ed216789ffaa4c6c0e7d2beabe32245a498f8e365a9fc8dab4'
BWRAP_BYTES = 529168
BWRAP_RELATIVE = 'codex-resources/bwrap'
BWRAP_FLAGS = ('--argv0', '--new-session', '--die-with-parent', '--ro-bind', '--dev', '--bind',
               '--unshare-user', '--unshare-pid', '--as-pid-1', '--unshare-ipc', '--unshare-net', '--proc', '--cap-drop')
CALL = 'packet-admission-1'
WRITER_CALL = 'native-writer-1'
WRITER_CASES = ('workspace-write', 'external-write-refusal')
WRITE_BYTES = b'native-workspace-write-ok\n'
CANARY_BYTES = b'fixed-external-canary\n'
STDERR_LIMIT = 65536
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/control/home',
       'CODEX_HOME': '/control/home/.codex', 'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1,localhost'}


def cli_env(case):
    return dict(ENV) if case is None else {**ENV, 'TMPDIR': '/tmp/registry'}


class FixtureError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def file_identity(value):
    return (value.st_dev, value.st_ino, value.st_uid, value.st_gid, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise FixtureError('guest-regular-file-required')
        raw = bytearray()
        while len(raw) <= limit:
            part = os.read(fd, min(65536, limit + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
        if len(raw) > limit or file_identity(os.fstat(fd)) != file_identity(before) or file_identity(os.stat(path, follow_symlinks=False)) != file_identity(before):
            raise FixtureError('guest-file-readback-drift')
        return bytes(raw)
    finally:
        os.close(fd)


def save(root, name, value):
    raw = canonical(value)
    if len(raw) > 1048576:
        raise FixtureError('guest-journal-bound')
    fd = os.open(root / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    if read_regular(root / name, 1048576) != raw:
        raise FixtureError('guest-journal-readback-drift')


def writer_call(case):
    if case not in WRITER_CASES:
        raise FixtureError('fixed-native-writer-case-required')
    command = ("printf '%s\\n' 'native-workspace-write-ok' > /control/workspace/native-write.txt"
               if case == 'workspace-write' else
               "IFS= read -r canary < /control/external-canary || exit 17; "
               "test \"$canary\" = 'fixed-external-canary' || exit 18; "
               "printf '%s\\n' 'forbidden-native-write' > /control/external-canary")
    return {'type': 'function_call', 'namespace': 'functions', 'name': 'exec_command', 'call_id': WRITER_CALL,
            'arguments': json.dumps({'cmd': command, 'workdir': '/control/workspace', 'shell': '/bin/sh',
                'tty': False, 'yield_time_ms': 10000, 'max_output_tokens': 512,
                'sandbox_permissions': 'use_default'})}


def writer_output(output, case):
    """Only the fixed native terminal carrier; generic failures are unknown."""
    if case not in WRITER_CASES or type(output) is not str or len(output.encode()) > 8192:
        raise FixtureError('bounded-native-output-required')
    header, separator, body = output.partition('Output:\n')
    lines = header.splitlines()
    if (separator != 'Output:\n' or len(lines) not in (3, 4)
            or not re.fullmatch(r'Chunk ID: [A-Za-z0-9_-]{1,128}', lines[0])
            or not re.fullmatch(r'Wall time: (0|[1-9][0-9]?)\.[0-9]{4} seconds', lines[1])
            or len(lines) == 4 and not re.fullmatch(r'Original token count: (0|[1-9][0-9]{0,5})', lines[3])):
        raise FixtureError('native-terminal-header-unconfirmed')
    code = re.fullmatch(r'Process exited with code (0|[1-9][0-9]{0,2})', lines[2])
    if code is None:
        raise FixtureError('native-natural-exit-required')
    code = int(code[1])
    if code > 255:
        raise FixtureError('native-exit-code-out-of-range')
    if case == 'workspace-write':
        if code != 0 or body != '':
            raise FixtureError('native-workspace-write-unconfirmed')
    elif code in (0, 17, 18) or not re.fullmatch(
            r'(?:/bin/sh|sh): [1-9][0-9]*: cannot create /control/external-canary: '
            r'(?:Permission denied|Read-only file system)\n', body):
        raise FixtureError('native-explicit-os-denial-unconfirmed')
    return {'exit_code': code, 'body': body, 'outcome': 'native-workspace-write'
            if case == 'workspace-write' else 'native-explicit-os-denial'}


def writer_declaration(raw, boundary, case):
    inventory = boundary.manifest.advertised_tools(raw)
    value = boundary.manifest.decode(raw); definitions = []
    def visit(entries, prefix=()):
        for item in entries:
            if item['type'] == 'namespace':
                visit(item['tools'], (*prefix, item['name']))
            elif ('.'.join(prefix), item['name'], item['type']) == ('functions', 'exec_command', 'function'):
                definitions.append(item)
    visit(value.get('tools', []))
    for item in value.get('input', []):
        if type(item) is dict and item.get('type') == 'additional_tools':
            visit(item['tools'])
    if len(definitions) != 1:
        raise FixtureError('native-exec-declaration-unconfirmed')
    schema = definitions[0]['parameters']; arguments = json.loads(writer_call(case)['arguments'])
    properties = schema.get('properties', {}); required = schema.get('required', [])
    if (schema.get('type') != 'object' or type(properties) is not dict or type(required) is not list
            or any(type(key) is not str or key not in arguments for key in required)):
        raise FixtureError('native-exec-schema-drift')
    for key, argument in arguments.items():
        description = properties.get(key, {}); kinds = description.get('type')
        kinds = kinds if type(kinds) is list else [kinds]
        expected = 'boolean' if type(argument) is bool else 'integer' if type(argument) is int else 'string'
        if (expected not in kinds and not (expected == 'integer' and 'number' in kinds)
                or 'enum' in description and argument not in description['enum']
                or 'const' in description and argument != description['const']):
            raise FixtureError('native-exec-argument-schema-drift')
    return inventory


def cli_argv(port, boundary, case=None):
    if case is not None and case not in WRITER_CASES:
        raise FixtureError('fixed-native-writer-case-required')
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
                   '/control/workspace': 'read', '/control/home': 'deny', '/control': 'deny',
                   '/fixture/codex': 'read', '/fixture': 'read'}
    if case is not None:
        # The default root deny already excludes capture/control. Explicit
        # parent masks would hide the exact helper/canary read grants in bwrap.
        permissions = {':root': 'deny', ':minimal': 'read', '/control/workspace': 'write',
                       '/fixture/codex': 'read', '/fixture/' + BWRAP_RELATIVE: 'read',
                       '/control/external-canary': 'read'}
    fs = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in permissions.items())
    provider = ('model_providers.fixture={name="Anonymous container fixture",base_url="http://127.0.0.1:'
                + str(port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,'
                'request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
    settings = ['model_provider="fixture"', provider, 'model="gpt-6-sol"', 'model_reasoning_effort="low"',
                'default_permissions="' + ('probe' if case is None else 'probe-writer') + '"',
                'permissions.' + ('probe' if case is None else 'probe-writer') + '.filesystem={' + fs + '}',
                'permissions.' + ('probe' if case is None else 'probe-writer') + '.network.enabled=false',
                'approval_policy="never"', 'web_search="disabled"',
                'shell_environment_policy.inherit="none"', 'notify=[]', 'agents.enabled=false',
                'features.code_mode_host={enabled=false,disable_in_process_fallback=false}',
                *['features.' + key + '=false' for key in sorted(set(boundary.REQUIRED_DISABLED_FEATURES)
                  | {'hooks', 'apps', 'plugins', 'multi_agent_v2', 'image_generation', 'memories'})
                  if key != 'code_mode_host' and not (case is not None and key in ('shell_tool', 'unified_exec'))]]
    if case is not None:
        settings += ['features.shell_tool=true', 'features.unified_exec=true', 'allow_login_shell=false',
                     'project_doc_max_bytes=0', 'shell_environment_policy.set={TMPDIR="/tmp/registry"}']
    argv = ['/fixture/codex', 'app-server', '--stdio', '--strict-config']
    for value in settings:
        argv += ['-c', value]
    return argv


class DeadlineReader(io.RawIOBase):
    def __init__(self, connection, deadline):
        self.connection, self.deadline = connection, deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('guest-provider-deadline')
        self.connection.settimeout(remaining)
        return self.connection.recv_into(buffer)


class DeadlineWriter(io.BufferedIOBase):
    def __init__(self, connection, deadline):
        self.connection, self.deadline = connection, deadline

    def writable(self):
        return True

    def write(self, data):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('guest-provider-deadline')
        self.connection.settimeout(remaining)
        self.connection.sendall(data)
        return len(data)


def provider(root, request, receipt, boundary):
    """Two serial localhost requests only; raw bytes precede every reply."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *unused):
            pass

        def setup(self):
            super().setup()
            deadline = time.monotonic() + 5
            self.rfile.close(); self.rfile = io.BufferedReader(DeadlineReader(self.connection, deadline))
            self.wfile.close(); self.wfile = DeadlineWriter(self.connection, deadline)

        def do_POST(self):
            try:
                if (self.path != '/v1/responses' or self.headers.get('Authorization') is not None
                        or self.headers.get('Content-Encoding', 'identity') != 'identity'):
                    raise FixtureError('guest-provider-route-drift')
                length = int(self.headers.get('Content-Length', '0'))
                case = request.get('native_case')
                if not 0 < length <= 1048576 or len(receipt['requests']) >= (3 if case is not None else 2):
                    raise FixtureError('guest-provider-request-bound')
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise FixtureError('guest-provider-partial-request')
                value = boundary.manifest.decode(raw)
                stage = len(receipt['requests']) + 1
                record = {'stage': stage, 'sha256': hashlib.sha256(raw).hexdigest(),
                          'raw_base64': base64.b64encode(raw).decode()}
                # Base64 overhead shares the fixed 1 MiB journal bound.
                if len(canonical(record)) > 1048576:
                    raise FixtureError('guest-provider-journal-bound')
                save(root, 'provider-request-' + str(stage) + '.json', record)
                receipt['requests'].append({'stage': stage, 'sha256': record['sha256']})
                if case is not None:
                    inventory = writer_declaration(raw, boundary, case)
                    previous = receipt.get('native_advertisement')
                    if previous is not None and inventory['advertised_tools'] != previous['advertised_tools']:
                        raise FixtureError('native-exec-declaration-drift')
                    receipt['native_advertisement'] = inventory
                if stage == 1:
                    item = {'type': 'function_call', 'name': 'packet_probe', 'arguments': '{}', 'call_id': CALL}
                elif stage == 2:
                    output = boundary.find_output(value, {'type': 'function_call', 'call_id': CALL})
                    if boundary.output_text(output) != request['accepted_token']:
                        raise FixtureError('guest-exact-token-missing')
                    receipt['exact_token_confirmed'] = True
                    if case is not None:
                        item = writer_call(case)
                    else:
                        item = {'type': 'message', 'role': 'assistant', 'id': 'container-admission-final',
                                'content': [{'type': 'output_text', 'text': 'Admission acknowledged; no integration requested.'}]}
                else:
                    output = boundary.output_text(boundary.find_output(value, writer_call(case)))
                    receipt['native_output'] = output
                    try:
                        receipt['native_result'] = writer_output(output, case)
                        receipt['writer_output_confirmed'] = True
                    except FixtureError:
                        # Finish this fixed conversation without retrying the command.
                        receipt['writer_output_confirmed'] = False
                    item = {'type': 'message', 'role': 'assistant', 'id': 'container-admission-final',
                            'content': [{'type': 'output_text', 'text': 'Fixed native observation finished; no integration requested.'}]}
                events = [{'type': 'response.created', 'response': {'id': 'container-' + str(stage)}},
                          {'type': 'response.output_item.done', 'item': item},
                          {'type': 'response.completed', 'response': {'id': 'container-' + str(stage),
                           'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                response = b''.join(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode() for event in events)
                if case is not None:
                    save(root, 'provider-response-' + str(stage) + '.json', {'stage': stage,
                        'raw_base64': base64.b64encode(response).decode(), 'sha256': hashlib.sha256(response).hexdigest()})
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                self.wfile.write(response)
                self.wfile.flush()
            except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
                receipt['provider_error'] = type(error).__name__ + ':' + str(error)[:100]
                self.send_error(422)
    return http.server.HTTPServer(('127.0.0.1', 0), Handler)


def verify_capture(request, fixture, control):
    expected = {'schema_version', 'run_id', 'accepted_token', 'uid', 'gid', 'sources', 'binary_sha256'}
    case = request.get('native_case')
    if case is not None:
        expected |= {'native_case', 'canary_ref', 'bwrap_sha256'}
    if (set(request) != expected or case is not None and case not in WRITER_CASES
            or request['schema_version'] != 1 or request['binary_sha256'] != BINARY_SHA
            or request['accepted_token'] != 'packet-admission-accepted:' + request['run_id']
            or type(request['run_id']) is not str or not re.fullmatch(r'[a-f0-9]{32}', request['run_id'])
            or type(request['sources']) is not dict or len(request['sources']) != 20 or type(request['uid']) is not int or type(request['gid']) is not int
            or os.getuid() != request['uid'] or os.getgid() != request['gid'] or os.getuid() == 0
            or dict(os.environ) != {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/control/home', 'LANG': 'C.UTF-8'} or sys.version_info[:3] != (3, 12, 13)):
        raise FixtureError('guest-context-drift')
    for directory in (fixture, control):
        info = os.lstat(directory)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) not in (0o500, 0o700):
            raise FixtureError('guest-directory-owner-mode-drift')
    for name, digest in request['sources'].items():
        relative = pathlib.PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise FixtureError('guest-source-path-drift')
        raw = read_regular(fixture / name, 1048576)
        info = os.lstat(fixture / name)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o500 or hashlib.sha256(raw).hexdigest() != digest:
            raise FixtureError('guest-source-capture-drift')
    binary = fixture / 'codex'
    fd = os.open(binary, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid() or before.st_nlink != 1
                or before.st_size != BINARY_BYTES or stat.S_IMODE(before.st_mode) != 0o500):
            raise FixtureError('guest-binary-identity-drift')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != BINARY_SHA or file_identity(os.fstat(fd)) != file_identity(before) or file_identity(os.stat(binary, follow_symlinks=False)) != file_identity(before):
            raise FixtureError('guest-binary-fingerprint-drift')
    finally:
        os.close(fd)
    result = {'sha256': digest, 'bytes': before.st_size, 'uid': before.st_uid, 'mode': stat.S_IMODE(before.st_mode)}
    if case is not None:
        path = fixture / BWRAP_RELATIVE; info = os.lstat(path)
        if (request['bwrap_sha256'] != BWRAP_SHA or not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o500
                or info.st_size != BWRAP_BYTES or hashlib.sha256(read_regular(path, BWRAP_BYTES)).hexdigest() != BWRAP_SHA):
            raise FixtureError('guest-bwrap-fingerprint-drift')
        result['bwrap'] = {'sha256': BWRAP_SHA, 'bytes': BWRAP_BYTES, 'identity': file_identity(info)}
    return result


def stderr_capture(stream, state):
    """Drain to EOF, retaining a bounded prefix; overflow never supports PASS."""
    try:
        while True:
            raw = stream.read(4096)
            if not raw:
                state['eof'] = True
                return
            state['total_bytes'] += len(raw)
            remaining = STDERR_LIMIT - len(state['raw'])
            state['raw'].extend(raw[:max(0, remaining)])
            if len(raw) > remaining:
                state['overflow'] = state['truncated'] = True
    except (OSError, ValueError):
        state['reader_error'] = True


def stderr_record(state, reader):
    raw = bytes(state['raw'])
    return {'raw_base64': base64.b64encode(raw).decode(), 'captured_prefix_sha256': hashlib.sha256(raw).hexdigest(),
            'captured_bytes': len(raw), 'total_bytes': state['total_bytes'], 'eof': state['eof'],
            'overflow': state['overflow'], 'truncated': state['truncated'],
            'reader_finished': not reader.is_alive(), 'reader_error': state.get('reader_error', False)}


def stderr_complete(value):
    return (type(value) is dict and value.get('eof') is True and value.get('reader_finished') is True
            and value.get('overflow') is False and value.get('truncated') is False
            and value.get('reader_error') is False and type(value.get('captured_bytes')) is int
            and 0 <= value['captured_bytes'] <= STDERR_LIMIT and type(value.get('total_bytes')) is int
            and value['total_bytes'] == value['captured_bytes'])


def bounded_command(argv):
    """One fixed trusted prerequisite child; incomplete streams never pass."""
    states = [{'raw': bytearray(), 'total_bytes': 0, 'eof': False, 'overflow': False, 'truncated': False}
              for _ in range(2)]
    child = subprocess.Popen(argv, env=cli_env('workspace-write'), cwd='/control', stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, pass_fds=())
    readers = [threading.Thread(target=stderr_capture, args=(stream, state), daemon=True)
               for stream, state in zip((child.stdout, child.stderr), states)]
    for reader in readers:
        reader.start()
    result = {'argv': argv, 'pid': child.pid, 'wait': 'unknown', 'timeout': False}
    try:
        result['exit_code'] = child.wait(timeout=5); result['wait'] = 'observed'
    except subprocess.TimeoutExpired:
        result['timeout'] = True
        child.kill()  # Only this freshly created private diagnostic child.
        try:
            result['exit_code'] = child.wait(timeout=2); result['wait'] = 'terminated'
        except subprocess.TimeoutExpired:
            pass
    for reader in readers:
        reader.join(timeout=2)
    result['stdout'], result['stderr'] = [stderr_record(state, reader) for state, reader in zip(states, readers)]
    result['complete'] = (result['wait'] == 'observed' and not result['timeout']
                          and all(stderr_complete(result[key]) for key in ('stdout', 'stderr')))
    return result


def prerequisite_argv():
    script = ("IFS= read -r canary < /control/prerequisite/canary || exit 20; "
              "test \"$canary\" = 'fixed-prerequisite-canary' || exit 21; "
              "printf '%s\\n' 'fixed-prerequisite-postimage' > /control/prerequisite/work/postimage || exit 22; "
              "if (printf '%s\\n' 'forbidden-prerequisite-write' > /control/prerequisite/canary); then exit 23; fi; "
              "printf '%s\\n' 'namespace-prerequisite-ok'")
    return ['/fixture/' + BWRAP_RELATIVE, '--new-session', '--die-with-parent', '--ro-bind', '/', '/',
            '--dev', '/dev', '--bind', '/control/prerequisite/work', '/control/prerequisite/work',
            '--unshare-user', '--unshare-pid', '--as-pid-1', '--unshare-ipc', '--unshare-net',
            '--proc', '/proc', '--cap-drop', 'ALL', '--', '/bin/sh', '-c', script]


def prerequisites_confirmed(value):
    """Finite fixed raw observations, never a production authority receipt."""
    try:
        if (value.get('scope') != 'fixed-bwrap-prerequisites-only' or value.get('passed') is not True
                or value.get('native_qualified') is not False or value.get('canary_preserved') is not True
                or value.get('postimage_confirmed') is not True):
            return False
        outputs = {}
        for name, argv in (('help', ['/fixture/' + BWRAP_RELATIVE, '--help']), ('probe', prerequisite_argv())):
            phase = value[name]
            if (phase['argv'] != argv or phase['wait'] != 'observed' or phase['timeout'] is not False
                    or phase['complete'] is not True or type(phase['exit_code']) is not int or phase['exit_code'] != 0
                    or type(phase['pid']) is not int or not 1 < phase['pid'] <= 2147483647):
                return False
            outputs[name] = {}
            for key in ('stdout', 'stderr'):
                stream = phase[key]; raw = base64.b64decode(stream['raw_base64'], validate=True)
                if (not stderr_complete(stream) or len(raw) != stream['captured_bytes']
                        or hashlib.sha256(raw).hexdigest() != stream['captured_prefix_sha256']):
                    return False
                outputs[name][key] = raw.decode()
        return (all(re.search(r'(?<![\w-])' + re.escape(flag) + r'(?![\w-])', outputs['help']['stdout']) for flag in BWRAP_FLAGS)
                and outputs['probe']['stdout'] == 'namespace-prerequisite-ok\n'
                and bool(re.fullmatch(r'(?:/bin/sh|sh): [1-9][0-9]*: cannot create /control/prerequisite/canary: '
                    r'(?:Permission denied|Read-only file system)\n', outputs['probe']['stderr'])))
    except (KeyError, TypeError, ValueError, UnicodeError):
        return False


def prerequisites(control, receipt):
    result = {'scope': 'fixed-bwrap-prerequisites-only', 'passed': False, 'native_qualified': False}
    receipt['prerequisites'] = result
    for directory in ENV['PATH'].split(':'):
        if os.path.lexists(directory + '/bwrap'):
            raise FixtureError('guest-system-bwrap-shadow')
    info = os.lstat('/tmp'); capacity = os.statvfs('/tmp')
    rows = [line.split() for line in read_regular('/proc/self/mountinfo', 262144).decode().splitlines()]
    rows = [row for row in rows if len(row) >= 10 and row[4] == '/tmp']
    if (len(rows) != 1 or rows[0][rows[0].index('-') + 1] != 'tmpfs'
            or not {'rw', 'nosuid', 'nodev', 'noexec'} <= set(rows[0][5].split(','))
            or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_gid != os.getgid()
            or stat.S_IMODE(info.st_mode) != 0o700 or capacity.f_blocks * capacity.f_frsize != 16777216):
        raise FixtureError('guest-fixed-tmpfs-staging-unavailable')
    result['tmpfs'] = {'mountinfo_row': rows[0], 'owner': info.st_uid, 'group': info.st_gid,
                       'mode': stat.S_IMODE(info.st_mode), 'capacity_bytes': capacity.f_blocks * capacity.f_frsize}
    for name in ('registry', 'codex-daemon-' + str(os.getuid())):
        path = pathlib.Path('/tmp') / name; path.mkdir(mode=0o700)
        value = os.lstat(path)
        if not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid() or stat.S_IMODE(value.st_mode) != 0o700:
            raise FixtureError('guest-staging-directory-drift')
    help_result = bounded_command(['/fixture/' + BWRAP_RELATIVE, '--help']); result['help'] = help_result
    help_text = base64.b64decode(help_result['stdout']['raw_base64'], validate=True).decode()
    if (not help_result['complete'] or help_result.get('exit_code') != 0
            or any(not re.search(r'(?<![\w-])' + re.escape(flag) + r'(?![\w-])', help_text) for flag in BWRAP_FLAGS)):
        raise FixtureError('guest-bwrap-help-unconfirmed')
    directory = control / 'prerequisite'; directory.mkdir(mode=0o700)
    (directory / 'work').mkdir(mode=0o700)
    canary = directory / 'canary'; canary.write_bytes(b'fixed-prerequisite-canary\n'); canary.chmod(0o600)
    before = file_identity(os.lstat(canary))
    probe = bounded_command(prerequisite_argv()); result['probe'] = probe
    stdout = base64.b64decode(probe['stdout']['raw_base64'], validate=True)
    stderr = base64.b64decode(probe['stderr']['raw_base64'], validate=True).decode()
    result['canary_preserved'] = (file_identity(os.lstat(canary)) == before
        and read_regular(canary, 128) == b'fixed-prerequisite-canary\n')
    result['postimage_confirmed'] = (sorted(p.name for p in (directory / 'work').iterdir()) == ['postimage']
        and read_regular(directory / 'work/postimage', 128) == b'fixed-prerequisite-postimage\n')
    result['passed'] = bool(probe['complete'] and probe.get('exit_code') == 0
        and stdout == b'namespace-prerequisite-ok\n' and re.fullmatch(
            r'(?:/bin/sh|sh): [1-9][0-9]*: cannot create /control/prerequisite/canary: '
            r'(?:Permission denied|Read-only file system)\n', stderr)
        and result['canary_preserved'] and result['postimage_confirmed'])
    if not prerequisites_confirmed(result):
        result['passed'] = False
        raise FixtureError('guest-bwrap-prerequisites-unavailable')
    return result


def run_guest(*, _fixture=None, _control=None):
    fixture = pathlib.Path('/fixture') if _fixture is None else _fixture
    control = pathlib.Path('/control') if _control is None else _control
    receipt = {'scope': 'fixed-anonymous-prestart-container', 'requests': [], 'exact_token_confirmed': False,
               'fixture_stopped': False, 'cli_wait': 'unknown', 'production_qualified': False}
    service = thread = child = stderr_reader = None
    stderr_state = {'raw': bytearray(), 'total_bytes': 0, 'eof': False, 'overflow': False, 'truncated': False}
    try:
        request = json.loads(read_regular(control / 'request.json', 1048576))
        receipt['run_id'] = request['run_id']
        receipt['binary'] = verify_capture(request, fixture, control)
        receipt['sources'] = request['sources']; receipt['wrapper_env'] = dict(os.environ)
        case = request.get('native_case'); receipt['native_case'] = case
        sys.path.insert(0, str(fixture / 'scripts'))
        spec = importlib.util.spec_from_file_location('fixed_guest_boundary', fixture / 'scripts/verify-model-tool-boundary.py')
        boundary = importlib.util.module_from_spec(spec); spec.loader.exec_module(boundary)
        for name in ('home', 'home/.codex', 'workspace'):
            (control / name).mkdir(mode=0o700)
        if case is not None:
            if read_regular(control / 'external-canary', 128) != CANARY_BYTES:
                raise FixtureError('guest-canary-prestart-drift')
            os.umask(0o077)
            receipt['cli_spawn_count'] = 0
            if list((control / 'workspace').iterdir()) or list((control / 'home').iterdir()) != [control / 'home/.codex']:
                raise FixtureError('guest-anonymous-empty-context-required')
            if list((control / 'home/.codex').iterdir()):
                raise FixtureError('guest-anonymous-home-not-empty')
            prerequisites(control, receipt)
        (control / 'sentinel').write_bytes(b'synthetic-only'); (control / 'sentinel').chmod(0o600)
        service = provider(control, request, receipt, boundary)
        thread = threading.Thread(target=service.serve_forever, daemon=True); thread.start()
        argv = cli_argv(service.server_port, boundary, case)
        receipt['provider_port'] = service.server_port
        environment = cli_env(case)
        receipt['cli_argv'] = argv; receipt['cli_env'] = environment
        save(control, 'cli-spawn-intent.json', {'run_id': request['run_id'], 'argv': argv, 'env': environment})
        # RPC stdin/stdout go directly to this exact child. The wrapper never
        # reads stdin, emits diagnostics to stdout, retries or kills the CLI.
        child = subprocess.Popen(argv, cwd='/control/workspace', env=environment,
                                 stdin=None, stdout=None, stderr=subprocess.PIPE if case is not None else subprocess.DEVNULL,
                                 close_fds=True, pass_fds=())
        if case is not None:
            receipt['cli_spawn_count'] = 1
        if case is not None:
            stderr_reader = threading.Thread(target=stderr_capture, args=(child.stderr, stderr_state), daemon=True)
            stderr_reader.start()
        receipt['cli_pid'] = child.pid
        code = child.wait(timeout=60)
        receipt['cli_wait'] = 'observed'; receipt['cli_exit_code'] = code
        if code != 0:
            raise FixtureError('guest-cli-nonzero')
        receipt['binary_after'] = verify_capture(request, fixture, control)
        receipt['sentinel_preserved'] = read_regular(control / 'sentinel', 32) == b'synthetic-only'
        receipt['workspace_unchanged'] = not list((control / 'workspace').iterdir())
        if case is not None:
            receipt['canary_preserved'] = read_regular(control / 'external-canary', 128) == CANARY_BYTES
            receipt['workspace_expected'] = (receipt['workspace_unchanged'] if case == 'external-write-refusal' else
                sorted(p.name for p in (control / 'workspace').iterdir()) == ['native-write.txt']
                and read_regular(control / 'workspace/native-write.txt', 128) == WRITE_BYTES)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        receipt['failure_class'] = type(error).__name__; receipt['failure_reason'] = str(error)[:100]
    finally:
        if stderr_reader is not None:
            stderr_reader.join(timeout=2)
            record = stderr_record(stderr_state, stderr_reader)
            receipt['cli_stderr'] = record
            save(control, 'cli-stderr-capture.json', record)
        if service is not None:
            stopped = threading.Event()
            def shutdown():
                try:
                    service.shutdown(); stopped.set()
                except (OSError, RuntimeError):
                    pass
            helper = threading.Thread(target=shutdown, daemon=True); helper.start(); helper.join(timeout=2)
            try:
                service.server_close()
                thread.join(timeout=2)
                receipt['fixture_stopped'] = stopped.is_set() and not helper.is_alive() and not thread.is_alive()
            except (OSError, RuntimeError):
                receipt['fixture_stopped'] = False
        passed = (receipt['cli_wait'] == 'observed' and receipt.get('cli_exit_code') == 0
                  and receipt['fixture_stopped'] and receipt['exact_token_confirmed']
                  and len(receipt['requests']) == (3 if receipt.get('native_case') is not None else 2)
                  and receipt.get('sentinel_preserved')
                  and (receipt.get('writer_output_confirmed') is True and receipt.get('workspace_expected') is True
                       and receipt.get('canary_preserved') is True and stderr_complete(receipt.get('cli_stderr'))
                       if receipt.get('native_case') is not None else receipt.get('workspace_unchanged'))
                  and 'failure_class' not in receipt and 'provider_error' not in receipt)
        receipt['passed'] = bool(passed)
        save(control, 'guest-receipt.json', receipt)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(run_guest())
