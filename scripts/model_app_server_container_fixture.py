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
CALL = 'packet-admission-1'
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/control/home',
       'CODEX_HOME': '/control/home/.codex', 'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1,localhost'}


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


def cli_argv(port, boundary):
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
                   '/control/workspace': 'read', '/control/home': 'deny', '/control': 'deny',
                   '/fixture/codex': 'read', '/fixture': 'read'}
    fs = ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in permissions.items())
    provider = ('model_providers.fixture={name="Anonymous container fixture",base_url="http://127.0.0.1:'
                + str(port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,'
                'request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
    settings = ['model_provider="fixture"', provider, 'model="gpt-6-sol"', 'model_reasoning_effort="low"',
                'default_permissions="probe"', 'permissions.probe.filesystem={' + fs + '}',
                'permissions.probe.network.enabled=false', 'approval_policy="never"', 'web_search="disabled"',
                'shell_environment_policy.inherit="none"', 'notify=[]', 'agents.enabled=false',
                'features.code_mode_host={enabled=false,disable_in_process_fallback=false}',
                *['features.' + key + '=false' for key in sorted(set(boundary.REQUIRED_DISABLED_FEATURES)
                  | {'hooks', 'apps', 'plugins', 'multi_agent_v2', 'image_generation', 'memories'})
                  if key != 'code_mode_host']]
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
                if not 0 < length <= 1048576 or len(receipt['requests']) >= 2:
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
                if stage == 1:
                    item = {'type': 'function_call', 'name': 'packet_probe', 'arguments': '{}', 'call_id': CALL}
                else:
                    output = boundary.find_output(value, {'type': 'function_call', 'call_id': CALL})
                    if boundary.output_text(output) != request['accepted_token']:
                        raise FixtureError('guest-exact-token-missing')
                    receipt['exact_token_confirmed'] = True
                    item = {'type': 'message', 'role': 'assistant', 'id': 'container-admission-final',
                            'content': [{'type': 'output_text', 'text': 'Admission acknowledged; no integration requested.'}]}
                events = [{'type': 'response.created', 'response': {'id': 'container-' + str(stage)}},
                          {'type': 'response.output_item.done', 'item': item},
                          {'type': 'response.completed', 'response': {'id': 'container-' + str(stage),
                           'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                self.send_response(200); self.send_header('Content-Type', 'text/event-stream'); self.end_headers()
                for event in events:
                    self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())
                self.wfile.flush()
            except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
                receipt['provider_error'] = type(error).__name__ + ':' + str(error)[:100]
                self.send_error(422)
    return http.server.HTTPServer(('127.0.0.1', 0), Handler)


def verify_capture(request, fixture, control):
    if (set(request) != {'schema_version', 'run_id', 'accepted_token', 'uid', 'gid', 'sources', 'binary_sha256'}
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
    return {'sha256': digest, 'bytes': before.st_size, 'uid': before.st_uid, 'mode': stat.S_IMODE(before.st_mode)}


def run_guest(*, _fixture=None, _control=None):
    fixture = pathlib.Path('/fixture') if _fixture is None else _fixture
    control = pathlib.Path('/control') if _control is None else _control
    receipt = {'scope': 'fixed-anonymous-prestart-container', 'requests': [], 'exact_token_confirmed': False,
               'fixture_stopped': False, 'cli_wait': 'unknown', 'production_qualified': False}
    service = thread = child = None
    try:
        request = json.loads(read_regular(control / 'request.json', 1048576))
        receipt['run_id'] = request['run_id']
        receipt['binary'] = verify_capture(request, fixture, control)
        receipt['sources'] = request['sources']; receipt['wrapper_env'] = dict(os.environ)
        sys.path.insert(0, str(fixture / 'scripts'))
        spec = importlib.util.spec_from_file_location('fixed_guest_boundary', fixture / 'scripts/verify-model-tool-boundary.py')
        boundary = importlib.util.module_from_spec(spec); spec.loader.exec_module(boundary)
        for name in ('home', 'home/.codex', 'workspace'):
            (control / name).mkdir(mode=0o700)
        (control / 'sentinel').write_bytes(b'synthetic-only'); (control / 'sentinel').chmod(0o600)
        service = provider(control, request, receipt, boundary)
        thread = threading.Thread(target=service.serve_forever, daemon=True); thread.start()
        argv = cli_argv(service.server_port, boundary)
        receipt['provider_port'] = service.server_port
        receipt['cli_argv'] = argv; receipt['cli_env'] = ENV
        save(control, 'cli-spawn-intent.json', {'run_id': request['run_id'], 'argv': argv, 'env': ENV})
        # RPC stdin/stdout go directly to this exact child. The wrapper never
        # reads stdin, emits diagnostics to stdout, retries or kills the CLI.
        child = subprocess.Popen(argv, cwd='/control/workspace', env=dict(ENV),
                                 stdin=None, stdout=None, stderr=subprocess.DEVNULL, close_fds=True, pass_fds=())
        receipt['cli_pid'] = child.pid
        code = child.wait(timeout=60)
        receipt['cli_wait'] = 'observed'; receipt['cli_exit_code'] = code
        if code != 0:
            raise FixtureError('guest-cli-nonzero')
        receipt['binary_after'] = verify_capture(request, fixture, control)
        receipt['sentinel_preserved'] = read_regular(control / 'sentinel', 32) == b'synthetic-only'
        receipt['workspace_unchanged'] = not list((control / 'workspace').iterdir())
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as error:
        receipt['failure_class'] = type(error).__name__; receipt['failure_reason'] = str(error)[:100]
    finally:
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
                  and receipt['fixture_stopped'] and receipt['exact_token_confirmed'] and len(receipt['requests']) == 2
                  and receipt.get('sentinel_preserved') and receipt.get('workspace_unchanged')
                  and 'failure_class' not in receipt and 'provider_error' not in receipt)
        receipt['passed'] = bool(passed)
        save(control, 'guest-receipt.json', receipt)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(run_guest())
