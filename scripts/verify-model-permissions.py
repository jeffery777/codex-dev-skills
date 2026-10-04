#!/usr/bin/env python3
"""Opt-in, credential-free native sandbox background probe; no model calls.

Run using project-python on macOS. Evidence and bounded background processes
are retained; this does not qualify Codex exec, builtin tools or an adapter.
"""
import argparse
import errno
import hashlib
import json
import math
import pathlib
import secrets
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import threading
import time


def reader_guard(reader='/bin/cat'):
    """Positive control in the same shell/sandbox as the forbidden read."""
    return ('test "$(' + shlex.quote(reader) + ' reader-sentinel)" = reader-ok || exit 12; '
            'echo verified > reader-verified; ')


NETWORK_CLIENT = r'''
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <errno.h>
#include <time.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif
static double now(void) {
#ifdef __APPLE__
    mach_timebase_info_data_t scale;
    if (mach_timebase_info(&scale) || !scale.denom) return 1e99;
    return (double)mach_absolute_time() * scale.numer / scale.denom / 1e9;
#else
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 1e99;
    return t.tv_sec + t.tv_nsec / 1e9;
#endif
}
int main(int argc, char **argv) {
    if (argc != 5 || strlen(argv[3]) != 32 ||
        strspn(argv[3], "0123456789abcdef") != 32) return 2;
    int udp = !strcmp(argv[1], "udp"), unix_socket = !strcmp(argv[1], "unix");
    if (!udp && !unix_socket && strcmp(argv[1], "tcp")) return 2;
    char *end = NULL;
    double expires = strtod(argv[4], &end);
    if (!end || *end || !isfinite(expires) || expires <= now() || expires-now() > 3.0) return 2;
    struct sockaddr_in internet;
    struct sockaddr_un local;
    memset(&internet, 0, sizeof(internet));
    memset(&local, 0, sizeof(local));
    struct sockaddr *address;
    socklen_t address_len;
    if (unix_socket) {
        if (strlen(argv[2]) >= sizeof(local.sun_path) || argv[2][0] != '/') return 2;
        local.sun_family = AF_UNIX;
#ifdef __APPLE__
        local.sun_len = sizeof(local);
#endif
        strcpy(local.sun_path, argv[2]);
        address = (struct sockaddr *)&local; address_len = sizeof(local);
    } else {
        long port = strtol(argv[2], &end, 10);
        if (!end || *end || port <= 0 || port > 65535) return 2;
        internet.sin_family = AF_INET; internet.sin_port = htons((uint16_t)port);
#ifdef __APPLE__
        internet.sin_len = sizeof(internet);
#endif
        if (inet_pton(AF_INET, "127.0.0.1", &internet.sin_addr) != 1) return 2;
        address = (struct sockaddr *)&internet; address_len = sizeof(internet);
    }
    const char *operation = "socket", *outcome = "unknown";
    int fd = socket(unix_socket ? AF_UNIX : AF_INET, udp ? SOCK_DGRAM : SOCK_STREAM, 0);
    int saved_errno = 0, verified = 0;
    if (fd < 0) { saved_errno = errno; goto output; }
    struct timeval timeout = {0, 600000};
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) ||
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout))) {
        saved_errno = errno; goto done;
    }
    operation = udp ? "sendto" : "connect";
    if (udp) {
        if (sendto(fd, argv[3], 32, 0, address, address_len) != 32) {
            saved_errno = errno; goto done;
        }
    } else {
        if (connect(fd, address, address_len)) { saved_errno = errno; goto done; }
        operation = "send";
        if (send(fd, argv[3], 32, 0) != 32) { saved_errno = errno; goto done; }
    }
    operation = "receive";
    char reply[128], expected[37];
    snprintf(expected, sizeof(expected), "ack:%s", argv[3]);
    ssize_t count = 0;
    if (udp) {
        struct sockaddr_in peer; socklen_t peer_len = sizeof(peer);
        count = recvfrom(fd, reply, sizeof(reply), 0, (struct sockaddr *)&peer, &peer_len);
        verified = count == 36 && peer.sin_family == AF_INET &&
            peer.sin_port == internet.sin_port && peer.sin_addr.s_addr == internet.sin_addr.s_addr;
    } else {
        while (count < 36 && now() < expires) {
            ssize_t size = recv(fd, reply + count, sizeof(reply) - (size_t)count, 0);
            if (size <= 0) { if (size < 0) saved_errno = errno; break; }
            count += size;
        }
        verified = count == 36;
    }
    if (count < 0) saved_errno = errno;
    verified = verified && !memcmp(reply, expected, 36) && now() < expires;
    if (verified) outcome = "connected";
done:
    close(fd);
output:
    if (saved_errno == EACCES || saved_errno == EPERM) outcome = "denied";
    printf("{\"outcome\":\"%s\",\"operation\":\"%s\",\"errno\":%d,"
        "\"nonce\":\"%s\",\"ack_verified\":%s}\n",
        outcome, operation, saved_errno, argv[3], verified ? "true" : "false");
    return 0;
}
'''


def sandbox_argv(executable, workspace, other, home, control, command, *,
                 network=False):
    """Only the fixed host fixture calls this builder; no provider inputs."""
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny',
        ':slash_tmp': 'deny', str(workspace): 'write', str(other): 'deny',
        str(home): 'deny', str(control): 'deny'}
    config = 'permissions.probe.filesystem={' + ','.join(
        json.dumps(key) + '=' + json.dumps(value) for key, value in permissions.items()) + '}'
    return [executable, 'sandbox', '-P', 'probe', '-C', str(workspace), '-c', config,
        '-c', 'permissions.probe.network.enabled=' + ('true' if network else 'false'),
        '--', *command]


def build_network_client(workspace):
    compiler = shutil.which('cc', path='/usr/bin:/bin')
    if compiler is None:
        raise ValueError('fixed-client-compiler-unavailable')
    source, binary = workspace / 'network-client.c', workspace / 'network-client'
    with source.open('x') as stream:
        stream.write(NETWORK_CLIENT)
    if binary.exists() or binary.is_symlink():
        raise ValueError('client-path-not-fresh')
    run = subprocess.run([compiler, '-O1', '-std=c11', str(source), '-o', str(binary)],
        cwd=workspace, env={'PATH': '/usr/bin:/bin'}, capture_output=True, timeout=10)
    if run.returncode != 0 or not binary.is_file() or binary.is_symlink():
        raise ValueError('fixed-client-build-unavailable')
    if sys.platform == 'darwin':
        linked = subprocess.run(['/usr/bin/otool', '-L', str(binary)],
            env={'PATH': '/usr/bin:/bin'}, capture_output=True, text=True, timeout=2)
        lines = linked.stdout.splitlines()
        if (linked.returncode != 0 or not 1 < len(lines) <= 17
                or any(not line.strip().startswith(('/System/', '/usr/lib/')) for line in lines[1:])):
            raise ValueError('non-system-client-library')
    return binary


def evaluate_network_case(case):
    """Host observations, not missing replies, decide the negative control."""
    try:
        positive, listener = case['positive'], case['listener']
        negative = case['negative']
        hashes = [case[key] for key in ('positive_nonce_sha256', 'negative_nonce_sha256',
            'positive_filesystem_config_sha256', 'negative_filesystem_config_sha256')]
        if (any(type(value) is not str or len(value) != 64
                or any(char not in '0123456789abcdef' for char in value) for value in hashes)
                or hashes[0] == hashes[1] or hashes[2] != hashes[3]
                or case['client_sha256'] != hashlib.sha256(NETWORK_CLIENT.encode()).hexdigest()
                or case['transport'] not in {'tcp', 'udp', 'unix'}
                or any(type(listener[key]) is not int or listener[key] < 0 for key in
                    ('positive_nonce_count', 'negative_nonce_count', 'negative_accept_count',
                     'late_nonce_count', 'unexpected_count'))
                or any(type(value) not in {int, float} or not math.isfinite(value) for value in
                    [listener['observed_until'], *[phase[key] for phase in (positive, negative)
                        for key in ('started_at', 'finished_at', 'expires_at')]])):
            return 'unknown'
        output = positive['output']
        if (positive['returncode'] != 0 or output['outcome'] != 'connected'
                or output['ack_verified'] is not True
                or output['nonce_sha256'] != case['positive_nonce_sha256']
                or not positive['started_at'] <= positive['finished_at'] < positive['expires_at']
                or listener['positive_nonce_count'] != 1):
            return 'unknown'
        # A trusted negative receipt is decisive even if the observer then
        # stops early. Incomplete observation must never mask an observed
        # escape; it only prevents proving the absence of one.
        if (listener['negative_nonce_count'] > 0
                or (case['transport'] != 'udp' and listener['negative_accept_count'] > 0)):
            return 'failed'
        if (listener['observed_until'] < negative['expires_at']
                or listener['late_nonce_count'] != 0
                or listener['unexpected_count'] != 0
                or listener['overflow'] is not False
                or listener['stopped'] is not True):
            return 'unknown'
        output = negative['output']
        operation = 'sendto' if case['transport'] == 'udp' else 'connect'
        if (negative['returncode'] == 0 and output['outcome'] == 'denied'
                and output['operation'] == operation
                and type(output['errno']) is int and output['errno'] in {errno.EACCES, errno.EPERM}
                and output['ack_verified'] is False
                and output['nonce_sha256'] == case['negative_nonce_sha256']
                and negative['started_at'] <= negative['finished_at'] < negative['expires_at']):
            return 'passed'
    except (KeyError, TypeError, ValueError):
        pass
    return 'unknown'


def native_network_controls(executable, workspace, other, home, control, env):
    """Fixed no-fork clients and private host listeners; no models or login."""
    cases = []
    try:
        binary = build_network_client(workspace)
        binary_digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return [{'transport': name, 'outcome': 'unknown', 'error_class': type(error).__name__,
            'production_qualified': False} for name in ('tcp', 'udp', 'unix')]
    for transport in ('tcp', 'udp', 'unix'):
        case = {'transport': transport, 'outcome': 'unknown',
            'client_sha256': hashlib.sha256(NETWORK_CLIENT.encode()).hexdigest(),
            'client_binary_sha256': binary_digest,
            'clock_implementation': time.get_clock_info('monotonic').implementation,
            'production_qualified': False}
        cases.append(case)
        listener, thread = None, None
        stop, lock = threading.Event(), threading.Lock()
        state = {'positive_nonce_count': 0, 'negative_nonce_count': 0,
            'negative_accept_count': 0, 'late_nonce_count': 0,
            'unexpected_count': 0, 'overflow': False, 'stopped': False}
        phase = {}
        positive_nonce, negative_nonce = secrets.token_hex(16), secrets.token_hex(16)
        case['positive_nonce_sha256'] = hashlib.sha256(positive_nonce.encode()).hexdigest()
        case['negative_nonce_sha256'] = hashlib.sha256(negative_nonce.encode()).hexdigest()

        def record_payload(payload):
            """Keep unknown traffic as counts; never persist its raw bytes."""
            with lock:
                key = ('positive' if payload == positive_nonce.encode() else
                    'negative' if payload == negative_nonce.encode() else None)
                if key is None or key not in phase:
                    state['unexpected_count'] += 1
                    return None
                state[key + '_nonce_count'] += 1
                if time.monotonic() >= phase[key]['expires_at']:
                    state['late_nonce_count'] += 1
                    return None
                return b'ack:' + payload

        def serve():
            observations = 0
            try:
                while observations < 8:
                    try:
                        if transport == 'udp':
                            payload, peer = listener.recvfrom(128)
                            reply = record_payload(payload)
                            if reply is not None:
                                listener.sendto(reply, peer)
                        else:
                            connection, _ = listener.accept()
                            with lock:
                                if 'negative' in phase:
                                    state['negative_accept_count'] += 1
                            with connection:
                                connection.settimeout(0.2)
                                payload = b''
                                while len(payload) < 32:
                                    part = connection.recv(33 - len(payload))
                                    if not part:
                                        break
                                    payload += part
                                reply = record_payload(payload)
                                if reply is not None:
                                    connection.sendall(reply)
                        observations += 1
                    except socket.timeout:
                        if stop.is_set():
                            break
                else:
                    state['overflow'] = True
            except OSError:
                state['unexpected_count'] += 1
            finally:
                state['observed_until'] = time.monotonic()
                state['stopped'] = True

        def run_client(name, nonce, network):
            started = time.monotonic()
            bound = {'started_at': started, 'expires_at': started + 2.5}
            with lock:
                phase[name] = bound
            command = [str(binary), transport,
                str(address if transport == 'unix' else address[1]), nonce, str(bound['expires_at'])]
            argv = sandbox_argv(executable, workspace, other, home, control, command,
                network=network)
            result = dict(bound, returncode=None, output={})
            case[name] = result
            # Exclude the phase nonce only; the fixed program and policy stay bound.
            case[name + '_filesystem_config_sha256'] = hashlib.sha256(argv[7].encode()).hexdigest()
            try:
                run = subprocess.run(argv, env=env, capture_output=True, timeout=4)
                result.update(returncode=run.returncode,
                    stdout_sha256=hashlib.sha256(run.stdout).hexdigest(),
                    stderr_sha256=hashlib.sha256(run.stderr).hexdigest())
                if len(run.stdout) <= 4096:
                    output = json.loads(run.stdout)
                    if isinstance(output, dict) and set(output) == {
                            'outcome', 'operation', 'errno', 'nonce', 'ack_verified'} and output['nonce'] == nonce:
                        output['nonce_sha256'] = hashlib.sha256(output.pop('nonce').encode()).hexdigest()
                        result['output'] = output
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                result['error_class'] = type(error).__name__
            result['finished_at'] = time.monotonic()
            return result

        try:
            if transport == 'unix':
                address = str(workspace / 'network-control.sock')
                if len(address.encode()) >= 104:
                    raise ValueError('bounded-unix-path-required')
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            else:
                listener = socket.socket(socket.AF_INET,
                    socket.SOCK_DGRAM if transport == 'udp' else socket.SOCK_STREAM)
                address = ('127.0.0.1', 0)
            listener.bind(address)
            if transport != 'udp':
                listener.listen(2)
            if transport != 'unix':
                address = listener.getsockname()
            listener.settimeout(0.05)
            case['endpoint'] = address
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            positive = run_client('positive', positive_nonce, True)
            with lock:
                positive_received = state['positive_nonce_count'] == 1 and state['late_nonce_count'] == 0
            if (positive['returncode'] == 0 and positive['output'].get('outcome') == 'connected'
                    and positive['output'].get('ack_verified') is True and positive_received
                    and positive['finished_at'] < positive['expires_at']):
                negative = run_client('negative', negative_nonce, False)
                while time.monotonic() < negative['expires_at']:
                    time.sleep(max(0, min(0.05, negative['expires_at'] - time.monotonic())))
            else:
                case['negative_not_run'] = 'positive-control-unverified'
        except (OSError, ValueError, RuntimeError) as error:
            case['error_class'] = type(error).__name__
        finally:
            stop.set()
            if thread is not None:
                thread.join(timeout=1)
            if listener is not None:
                listener.close()
            if thread is not None and thread.is_alive():
                thread.join(timeout=1)
            case['listener'] = dict(state)
            case['outcome'] = evaluate_network_case(case)
            try:
                unchanged = hashlib.sha256(binary.read_bytes()).hexdigest() == binary_digest
            except OSError:
                unchanged = False
            case['client_identity_unchanged'] = unchanged
            if not unchanged:
                case['outcome'] = 'unknown'
            if thread is not None and thread.is_alive():
                # Do not rebind the closures or start another listener while
                # this fixture observer's lifecycle remains unknown.
                case['outcome'] = 'unknown'
                case['listener_lifecycle_unknown'] = True
                return cases
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--network-controls', action='store_true',
        help='Also measure fixed TCP/UDP/private Unix socket positive and negative controls.')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('this qualification probe is macOS-only')
    base = args.evidence_root.resolve(strict=True)
    if not base.is_dir() or any((p / '.git').exists() for p in [base, *base.parents]):
        parser.error('existing evidence directory outside Git required')
    executable = shutil.which('codex')
    if executable is None:
        parser.error('installed Codex CLI required')
    executable = str(pathlib.Path(executable).resolve(strict=True))
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-permissions-', dir=base))
    a, b, home, control = [root / name for name in ['a', 'b', 'codex', 'control']]
    for directory in [a, b, home, control]:
        directory.mkdir()
    (control / 'sentinel').write_text('synthetic-only')
    (a / 'reader-sentinel').write_text('reader-ok')
    # Never inherit host credentials, proxy/auth variables or user configuration.
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home)}
    receipt = {'schema_version': 1, 'scope': 'synthetic-native-background-only',
        'fixture': str(root), 'production_qualified': False,
        'executable_sha256': hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest()}
    start = time.monotonic()

    def invoke(workspace, other, script):
        return subprocess.run(sandbox_argv(executable, workspace, other, home, control,
            ['/bin/sh', '-c', script]), env=env, capture_output=True, text=True, timeout=15)

    try:
        # Root exits promptly; a reparented descendant retains its sandbox.
        child = (reader_guard() + 'echo ready > ready; i=0; while test ! -f release; do '
            'i=$((i+1)); test "$i" -lt 100 || exit 10; sleep 0.2; done; '
            'echo old > result; if echo stale > ' + shlex.quote(str(b / 'result')) +
            '; then echo write-violation > violation; fi; if /bin/cat ' + shlex.quote(str(control / 'sentinel')) +
            ' >/dev/null; then echo read-violation > violation; fi; echo done > done')
        old = invoke(a, b, '(' + child + ') >/dev/null 2>&1 &')
        deadline = time.monotonic() + 5
        while not (a / 'ready').exists():
            if time.monotonic() >= deadline:
                raise OSError('background writer ready deadline exceeded')
            time.sleep(0.05)
        pending = not (a / 'result').exists()
        new = invoke(b, a, 'echo successor > result')
        (a / 'release').touch(exist_ok=False)
        deadline = time.monotonic() + 5
        while not (a / 'done').exists():
            if time.monotonic() >= deadline:
                raise OSError('background writer completion deadline exceeded')
            time.sleep(0.05)
        receipt['checks'] = {'old_root_exited': old.returncode == 0,
            'old_root_exited_before_child_write': pending,
            'reader_positive_control': (a / 'reader-verified').exists(),
            'successor_completed': new.returncode == 0,
            'old_child_later_wrote': (a / 'result').read_text().strip() == 'old',
            'successor_preserved': (b / 'result').read_text().strip() == 'successor',
            'forbidden_access_rejected': not (a / 'violation').exists()}
        if args.network_controls:
            receipt['network_cases'] = native_network_controls(executable, a, b, home, control, env)
            receipt['network_executable_after_sha256'] = hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest()
        return 0 if (all(receipt['checks'].values()) and
            all(case['outcome'] == 'passed' for case in receipt.get('network_cases', [])) and
            (not args.network_controls or receipt['network_executable_after_sha256'] ==
                receipt['executable_sha256'])) else 1
    except (OSError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error)
        return 1
    finally:
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        output = root / 'permissions-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), **receipt}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
