"""Fixed anonymous guest: RPC passthrough, no turns/tools, private final frame."""
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import time

PREFIX = b'ISSUE316-EXTERNAL-BOOTSTRAP:'
FRAME_BYTES = 16384
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp/home',
       'CODEX_HOME': '/tmp/home/.codex', 'TMPDIR': '/tmp/registry',
       'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1,localhost'}
FILES = ('scripts/verify-model-external-bootstrap.py', 'scripts/model_external_bootstrap_fixture.py')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def argv(boundary, guest):
    # Fixed localhost discard destination; this bootstrap never sends a turn.
    original = guest.cli_argv(1, boundary, 'workspace-write')
    result = original[:4]
    for flag, value in zip(original[4::2], original[5::2]):
        if value.startswith(('permissions.', 'default_permissions=')):
            continue
        result += [flag, value]
    return result + ['-c', 'sandbox_mode="read-only"']


def run():
    receipt = {'schema_version': 1, 'scope': 'anonymous-external-bootstrap-only',
               'cli_spawn_count': 0, 'cli_wait': 'unknown', 'passed': False,
               'qualified': False, 'production_qualified': False}
    child = capture = None
    try:
        os.umask(0o077)
        fixture = pathlib.Path('/fixture')
        sys.path.insert(0, str(fixture / 'scripts'))
        sys.path.insert(0, str(fixture / 'skills/loop-engineering/scripts'))
        base = load('external_fixed_host', fixture / 'scripts/verify-model-app-server-container.py')
        guest = base.guest
        request = base.helpers._reload_json(guest.read_regular('/inputs/request.json', 65536))
        if (set(request) != {'schema_version', 'run_id', 'uid', 'gid', 'sources'}
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
        command = argv(base.probe.boundary, guest)
        receipt['cli_argv'] = command
        child = subprocess.Popen(command, cwd='/workspace', env=ENV, stdin=None, stdout=None,
                                 stderr=subprocess.PIPE, close_fds=True, pass_fds=())
        receipt['cli_spawn_count'] = 1; receipt['cli_pid'] = child.pid
        capture = base.probe.transport._StderrCapture(child.stderr); capture.start()
        receipt['cli_exit_code'] = child.wait(timeout=30); receipt['cli_wait'] = 'observed'
        receipt['workspace_empty'] = not list(pathlib.Path('/workspace').iterdir())
        receipt['canary_preserved'] = guest.read_regular('/inputs/canary', 128) == guest.CANARY_BYTES
        receipt['passed'] = bool(receipt['cli_exit_code'] == 0 and receipt['workspace_empty']
                                 and receipt['canary_preserved'])
    except Exception as error:
        receipt['failure_class'] = type(error).__name__  # No peer/OS diagnostic strings.
    finally:
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
        if len(raw) > FRAME_BYTES:
            raw = PREFIX + b'{"passed":false,"failure_class":"FrameBound"}\n'
        sys.stderr.buffer.write(raw); sys.stderr.buffer.flush()
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(run())
