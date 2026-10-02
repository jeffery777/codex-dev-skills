#!/usr/bin/env python3
"""Opt-in synthetic container probe. This never qualifies a production adapter.

Run with scripts/project-python. Uses an already installed immutable image;
retains bounded test containers and evidence, without pulling or cleanup.
Socket negatives require existing image python3/socket and working loopback
controls. Missing tools or incomplete observations remain unknown (exit 2).
Exit 0 covers only the recorded synthetic cases, never production qualification.
"""
import argparse
import fcntl
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import time


def run_command(argv, *, timeout=30):
    """The trusted engine launcher never forwards an inheritable host FD."""
    return subprocess.check_output(argv, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL, close_fds=True).strip()


def filesystem_probe(workspace, targets, host_fd, *, reader='cat', mover='mv', linker='ln'):
    """Fixed synthetic operations, with working-tool controls before negatives.

    All arguments come from the trusted fixture launcher, never a model. The
    optional tool names permit counterexamples for unavailable test tools.
    """
    work = shlex.quote(str(workspace))
    read, move, link = map(shlex.quote, (reader, mover, linker))
    script = [f'work={work}',
        'record() { printf "%s\\t%s\\n" "$1" "$2" >> "$work/probe-results.tsv"; }',
        'printf positive > "$work/read-positive"',
        f'if test "$({read} "$work/read-positive" 2>/dev/null)" = positive; then reader_ok=yes; '
            'record reader_positive passed; else reader_ok=no; record reader_positive unknown; fi',
        'printf rename-positive > "$work/rename-from"',
        f'if {move} "$work/rename-from" "$work/rename-to" 2>/dev/null '
            f'&& test "$({read} "$work/rename-to" 2>/dev/null)" = rename-positive '
            '&& test ! -e "$work/rename-from"; then move_ok=yes; record rename_positive passed; '
            'else move_ok=no; record rename_positive unknown; fi',
        'printf link-positive > "$work/link-from"',
        f'if {link} "$work/link-from" "$work/link-to" 2>/dev/null '
            '&& printf hard-linked > "$work/link-to" '
            f'&& test "$({read} "$work/link-from" 2>/dev/null)" = hard-linked; '
            'then link_ok=yes; record link_positive passed; '
            'else link_ok=no; record link_positive unknown; fi',
        f'if {link} -s "$work/read-positive" "$work/symlink-positive" 2>/dev/null '
            f'&& test "$({read} "$work/symlink-positive" 2>/dev/null)" = positive; '
            'then symlink_ok=yes; record symlink_positive passed; '
            'else symlink_ok=no; record symlink_positive unknown; fi']
    for name, target in targets.items():
        if name not in {'source', 'checkpoint', 'sibling'}:
            raise ValueError('unexpected synthetic target')
        script += [f'target={shlex.quote(str(target))}',
            f'if test "$reader_ok" != yes; then record {name}_read unknown; '
                f'elif {read} "$target" >/dev/null 2>&1; then record {name}_read failed; '
                f'elif test ! -e "$target"; then record {name}_read passed; '
                f'else record {name}_read unknown; fi',
            f'if test "$reader_ok" != yes; then record {name}_write unknown; '
                f'elif (printf forbidden > "$target") 2>/dev/null; then record {name}_write failed; '
                f'elif test ! -e "$target"; then record {name}_write passed; '
                f'else record {name}_write unknown; fi',
            f'printf rename-negative > "$work/rename-{name}"',
            f'if test "$move_ok" != yes; then record {name}_rename unknown; '
                f'elif {move} "$work/rename-{name}" "$target" 2>/dev/null; then record {name}_rename failed; '
                f'elif test "$({read} "$work/rename-{name}" 2>/dev/null)" = rename-negative '
                f'&& test ! -e "$target"; then record {name}_rename passed; '
                f'else record {name}_rename unknown; fi',
            f'if test "$link_ok" != yes; then record {name}_link unknown; '
                f'elif {link} "$target" "$work/foreign-hard-{name}" 2>/dev/null; then record {name}_link failed; '
                f'elif test ! -e "$target" && test ! -e "$work/foreign-hard-{name}"; '
                f'then record {name}_link passed; else record {name}_link unknown; fi',
            f'if test "$symlink_ok" != yes; then record {name}_symlink unknown; '
                f'elif ! {link} -s "$target" "$work/foreign-sym-{name}" 2>/dev/null; '
                f'then record {name}_symlink unknown; '
                f'elif {read} "$work/foreign-sym-{name}" >/dev/null 2>&1 '
                f'|| (printf forbidden > "$work/foreign-sym-{name}") 2>/dev/null; '
                f'then record {name}_symlink failed; '
                f'elif test -L "$work/foreign-sym-{name}" && test ! -e "$work/foreign-sym-{name}"; '
                f'then record {name}_symlink passed; else record {name}_symlink unknown; fi']
    if type(host_fd) is not int or host_fd < 64:
        raise ValueError('invalid synthetic host descriptor')
    script += ['exec 9< "$work/read-positive"',
        f'if test "$reader_ok" = yes && test "$({read} /proc/$$/fd/9 2>/dev/null)" = positive; '
            'then record descriptor_positive passed; '
            f'if test ! -e /proc/$$/fd/{host_fd} && ! {read} /proc/$$/fd/{host_fd} >/dev/null 2>&1; '
            'then record host_descriptor_not_forwarded passed; '
            'else record host_descriptor_not_forwarded failed; fi; '
            'else record descriptor_positive unknown; record host_descriptor_not_forwarded unknown; fi',
        'printf nested-background > "$work/nested-positive"',
        f'if test "$({read} "$work/nested-positive" 2>/dev/null)" = nested-background; '
            'then record nested_background_positive passed; else record nested_background_positive unknown; fi']
    return '\n'.join(script)


# Uses only an existing image interpreter and its standard library. No package
# installation, external service, protocol request, or credential is involved.
# If python3/socket is absent, missing records remain unknown, never passed.
NETWORK_PROBE = r'''
import errno, pathlib, socket, sys
work, engine = pathlib.Path(sys.argv[1]), sys.argv[2]
def record(name, outcome):
    with (work / 'probe-results.tsv').open('a') as stream:
        stream.write(name + '\t' + outcome + '\n')
def positive(kind):
    family = socket.AF_UNIX if kind == 'unix' else socket.AF_INET
    mode = socket.SOCK_DGRAM if kind == 'udp' else socket.SOCK_STREAM
    try:
        with socket.socket(family, mode) as server, socket.socket(family, mode) as client:
            server.settimeout(1); client.settimeout(1)
            address = str(work / 'positive-unix.sock') if kind == 'unix' else ('127.0.0.1', 0)
            server.bind(address)
            address = server.getsockname()
            if kind == 'udp':
                client.sendto(b'synthetic', address)
                return server.recvfrom(32)[0] == b'synthetic'
            server.listen(1); client.connect(address)
            child, _ = server.accept()
            with child:
                child.settimeout(1); client.sendall(b'synthetic')
                return child.recv(32) == b'synthetic'
    except OSError:
        return False
for kind in ('tcp', 'udp', 'unix'):
    working = positive(kind)
    record(kind + '_positive', 'passed' if working else 'unknown')
    name = 'engine_socket_denied' if kind == 'unix' else kind + '_egress_denied'
    if not working or (kind == 'unix' and not engine):
        record(name, 'unknown'); continue
    try:
        family = socket.AF_UNIX if kind == 'unix' else socket.AF_INET
        mode = socket.SOCK_DGRAM if kind == 'udp' else socket.SOCK_STREAM
        with socket.socket(family, mode) as client:
            client.settimeout(1)
            address = engine if kind == 'unix' else ('192.0.2.1', 9)
            if kind == 'udp':
                client.sendto(b'synthetic', address)
            else:
                client.connect(address)
        record(name, 'failed')
    except OSError as error:
        denied = {errno.ENOENT, errno.EACCES, errno.EPERM} if kind == 'unix' else {
            errno.ENETUNREACH, errno.ENETDOWN, errno.EACCES, errno.EPERM}
        record(name, 'passed' if error.errno in denied else 'unknown')
'''


PROBE_KEYS = {'reader_positive', 'rename_positive', 'link_positive', 'symlink_positive',
    'descriptor_positive', 'host_descriptor_not_forwarded', 'nested_background_positive',
    'tcp_positive', 'udp_positive', 'unix_positive', 'tcp_egress_denied',
    'udp_egress_denied', 'engine_socket_denied'} | {
        name + '_' + operation for name in ('source', 'checkpoint', 'sibling')
        for operation in ('read', 'write', 'rename', 'link', 'symlink')}


def read_probe_results(path):
    results = {key: 'unknown' for key in sorted(PROBE_KEYS)}
    if not path.exists():
        return results
    if path.is_symlink() or path.stat().st_size > 8192:
        raise ValueError('invalid probe result artifact')
    seen = set()
    for line in path.read_text().splitlines():
        fields = line.split('\t')
        if (len(fields) != 2 or fields[0] not in results or fields[0] in seen
                or fields[1] not in {'passed', 'failed', 'unknown'}):
            raise ValueError('invalid probe result record')
        seen.add(fields[0])
        results[fields[0]] = fields[1]
    return results


def validate_image_volumes(volumes):
    if volumes is None:
        volumes = {}
    if not isinstance(volumes, dict) or len(volumes) > 16:
        raise ValueError('unbounded image volumes')
    for volume in volumes:
        if (not isinstance(volume, str) or not re.fullmatch(r'/[A-Za-z0-9_/-]+', volume)
                or volume in {'/', '/tmp', '/workspace'}
                or any(part in {'.', '..'} for part in pathlib.PurePosixPath(volume).parts)
                or '/workspace'.startswith(volume.rstrip('/') + '/')
                or volume.startswith('/workspace/')):
            raise ValueError('image volume conflicts with isolation boundary')
    return volumes


def validate_mounts(mounts, workspace, *, tmpfs=None):
    expected_tmpfs = {} if tmpfs is None else tmpfs
    if type(mounts) is not list or any(type(mount) is not dict for mount in mounts):
        raise ValueError('invalid container mount readback')
    binds = [mount for mount in mounts if mount.get('Type') == 'bind']
    if (len(binds) != 1 or binds[0].get('Destination') != '/workspace'
            or binds[0].get('Source') != str(workspace)
            or binds[0].get('RW') is not True or binds[0].get('Propagation') != 'rprivate'):
        raise ValueError('container mount readback does not match isolated fixture')
    destinations = set()
    for mount in mounts:
        destination = mount.get('Destination')
        if type(destination) is not str or destination in destinations:
            raise ValueError('invalid or duplicate container mount destination')
        destinations.add(destination)
        if mount.get('Type') == 'bind':
            continue
        # Docker reports --tmpfs in HostConfig.Tmpfs; engines may additionally
        # list it here. Neither representation may introduce another target.
        if (mount.get('Type') != 'tmpfs' or destination not in expected_tmpfs
                or mount.get('Source', '') not in {'', 'tmpfs'}
                or mount.get('RW') is not expected_tmpfs[destination].startswith('rw,')):
            raise ValueError('unexpected container mount type, target, or access')


def validate_worker(value, workspace, *, image, script, volumes, cpu_limit_unavailable=False):
    """Bind actual inspect policy to the trusted immutable launch parameters.

    Unknown engine field representations fail closed. The explicit CPU escape
    hatch must match an unconfigured limit; it never silently accepts CPU drift
    for the normal --cpus=1 launch.
    """
    if (type(image) is not str or not re.fullmatch(r'sha256:[0-9a-f]{64}', image)
            or type(script) is not str or type(cpu_limit_unavailable) is not bool):
        raise ValueError('invalid expected worker policy')
    volumes = validate_image_volumes(volumes)
    tmpfs = {'/tmp': 'rw,noexec,nosuid,nodev,size=8m', **{
        volume: 'ro,noexec,nosuid,nodev,size=1m' for volume in volumes}}
    try:
        host, config = value['HostConfig'], value['Config']
        validate_mounts(value['Mounts'], workspace, tmpfs=tmpfs)
        cpu = 0 if cpu_limit_unavailable else 1000000000
        if (value['Image'] != image or config['Image'] != image
                or config['Entrypoint'] != ['/bin/sh'] or config['Cmd'] != ['-c', script]
                or config['Healthcheck']['Test'] != ['NONE']
                or host['NetworkMode'] != 'none' or host['ReadonlyRootfs'] is not True
                or host['Privileged'] is not False or config['User'] != '65534:65534'
                or host['CapDrop'] != ['ALL'] or host['CapAdd'] not in (None, [])
                or host['SecurityOpt'] != ['no-new-privileges']
                or type(host['PidsLimit']) is not int or host['PidsLimit'] != 32
                or type(host['Memory']) is not int or host['Memory'] != 128 * 1024 * 1024
                or type(host['NanoCpus']) is not int or host['NanoCpus'] != cpu
                or host['CpuPeriod'] != 0 or host['CpuQuota'] != 0
                or host['Tmpfs'] != tmpfs or host['VolumesFrom'] not in (None, [])
                or host['Devices'] not in (None, []) or host['DeviceRequests'] not in (None, [])
                or host['DeviceCgroupRules'] not in (None, [])):
            raise ValueError('worker policy readback mismatch')
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('incomplete or malformed worker policy readback') from error


def stopped_successfully(value):
    state = value['State']
    return (state['Running'] is False and state['Status'] == 'exited'
        and state['ExitCode'] == 0 and state.get('OOMKilled') is False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['docker', 'podman'], required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--cpu-limit-unavailable', action='store_true')
    args = parser.parse_args()
    root = args.evidence_root.resolve(strict=True)
    if any((ancestor / '.git').exists() for ancestor in [root, *root.parents]):
        parser.error('evidence must be outside a Git checkout')
    executable = shutil.which(args.engine)
    if not executable or not root.is_dir():
        parser.error('engine and existing evidence directory required')
    engine = [executable] + (['--remote=false'] if args.engine == 'podman' else [])
    engine_socket = ''

    def command(*argv):
        return run_command(engine + list(argv))

    try:
        if args.engine == 'docker':
            context = command('context', 'show')
            endpoint = json.loads(command('context', 'inspect', context))[0]['Endpoints']['docker']['Host']
            if not endpoint.startswith('unix:///'):
                raise ValueError('only a local Docker Unix socket is allowed')
            # Pin the observed endpoint; later context or DOCKER_HOST changes
            # must not redirect this proof to an uninspected daemon.
            engine = [executable, '--host', endpoint]
            engine_socket = endpoint.removeprefix('unix://')
        elif command('info', '--format', '{{.Host.Security.Rootless}}') != 'true':
            raise ValueError('only rootless local Podman is allowed')
        image = command('image', 'inspect', args.image, '--format', '{{.Id}}')
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
            raise ValueError('immutable image identity required')
        volumes = validate_image_volumes(json.loads(command('image', 'inspect', image, '--format', '{{json .Config.Volumes}}')))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        # An unavailable daemon is an unmeasured environment, not successful
        # isolation. Retain a receipt even when no container could be started.
        fixture = pathlib.Path(tempfile.mkdtemp(prefix='model-isolation-', dir=root))
        receipt = {'schema_version': 1, 'scope': 'synthetic-container-isolation-only',
            'phase': 'preflight', 'execution_outcome': 'unknown', 'error_type': type(error).__name__,
            'containers_retained': [], 'production_qualified': False, 'repository_completion': False,
            'probe_results': {key: 'unknown' for key in sorted(PROBE_KEYS)}}
        output = fixture / 'isolation-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), 'phase': 'preflight',
            'execution_outcome': 'unknown', 'error_type': type(error).__name__, 'production_qualified': False}))
        return 2
    fixture = pathlib.Path(tempfile.mkdtemp(prefix='model-isolation-', dir=root))
    for name in ('source', 'checkpoint', 'sibling', 'a', 'b'):
        directory = fixture / name
        directory.mkdir()
        directory.chmod(0o777)  # Synthetic writable mounts for unprivileged UID.
        (directory / 'sentinel').write_text(name)
        (directory / 'sentinel').chmod(0o644)
    receipt = {'schema_version': 1, 'scope': 'synthetic-container-isolation-only',
        'engine': args.engine, 'image': image, 'fixture': str(fixture),
        'containers_retained': [], 'production_qualified': False, 'repository_completion': False,
        'execution_outcome': 'unknown',
        'limitations': ['synthetic files only; no production adapter qualification',
            'network negatives require existing image python3/socket and working local controls',
            'nested shell/background is not nested Codex CLI or detached-process qualification',
            'UDP denial measures send rejection, not an external delivery observation',
            'no preexisting host hardlink is mounted; cross-boundary link creation is measured'],
        'image_volumes_replaced_with_readonly_tmpfs': sorted(volumes),
        'resource_limits': {'memory': '128m', 'pids': 32, 'cpu': None if args.cpu_limit_unavailable else 1}}
    start = time.monotonic()
    host_fd = None
    worker_scripts = {}

    def launch(name, script):
        worker_scripts[name] = script
        options = ['run', '-d', '--no-healthcheck', '--pull=never', '--network=none', '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=32',
            '--memory=128m', '--user=65534:65534',
            '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m']
        for volume in volumes:
            options += ['--tmpfs', volume + ':ro,noexec,nosuid,nodev,size=1m']
        if args.engine == 'podman':
            options += ['--image-volume=ignore']
        if not args.cpu_limit_unavailable:
            options += ['--cpus=1']
        options += (['--volume', f'{fixture / name}:/workspace:Z'] if args.engine == 'podman'
            else ['--mount', f'type=bind,src={fixture / name},dst=/workspace'])
        cid = command(*options, '--entrypoint=/bin/sh', image, '-c', script)
        receipt['containers_retained'].append(cid)
        observed = json.loads(command('inspect', cid))[0]
        validate_worker(observed, fixture / name, image=image, script=script, volumes=volumes,
            cpu_limit_unavailable=args.cpu_limit_unavailable)
        return cid

    try:
        descriptor_path = fixture / 'source/descriptor'
        descriptor_path.write_text('synthetic-open-descriptor')
        original_fd = os.open(descriptor_path, os.O_RDWR)
        try:
            host_fd = fcntl.fcntl(original_fd, fcntl.F_DUPFD, 64)
        finally:
            os.close(original_fd)
        os.set_inheritable(host_fd, True)
        host_fd_positive = os.read(host_fd, 128) == b'synthetic-open-descriptor'
        os.lseek(host_fd, 0, os.SEEK_SET)
        receipt['host_descriptor_number'] = host_fd
        a_script = ('(i=0; while test ! -f /workspace/release; do i=$((i+1)); '
            'test "$i" -lt 200 || exit 10; sleep 0.2; done; '
            'echo old-writer > /workspace/result; '
            'if (echo stale > ' + shlex.quote(str(fixture / 'b/result')) + ') 2>/dev/null; '
            'then echo failed > /workspace/sibling-write; '
            'else echo rejected > /workspace/sibling-write; fi) & '
            'echo initiated > /workspace/started; wait')
        a = launch('a', a_script)
        ready_deadline = time.monotonic() + 5
        while not (fixture / 'a/started').exists():
            if time.monotonic() >= ready_deadline:
                raise OSError('old writer did not become ready within deadline')
            time.sleep(0.05)
        targets = {name: fixture / name / 'sentinel' for name in ('source', 'checkpoint', 'sibling')}
        inner = filesystem_probe('/workspace', targets, host_fd)
        inner += ('\nif command -v python3 >/dev/null 2>&1; then python3 -c '
            + shlex.quote(NETWORK_PROBE) + ' /workspace ' + shlex.quote(engine_socket)
            + ' 2>/workspace/network-probe.stderr; fi\nprintf successor > /workspace/result')
        # The negative operations run in a nested shell/background child. The
        # main container command waits for it, and each socket has a deadline.
        b = launch('b', '/bin/sh -c ' + shlex.quote(inner) + ' & child=$!; wait "$child"')
        b_exit = command('wait', b)
        a_active = command('inspect', a, '--format', '{{.State.Running}}')
        (fixture / 'a/release').touch(exist_ok=False)
        a_exit = command('wait', a)
        final_a, final_b = [json.loads(command('inspect', cid))[0] for cid in (a, b)]
        for name, observed in [('a', final_a), ('b', final_b)]:
            validate_worker(observed, fixture / name, image=image, script=worker_scripts[name], volumes=volumes,
                cpu_limit_unavailable=args.cpu_limit_unavailable)
            (fixture / (name + '-inspect.json')).write_text(json.dumps(observed, indent=2) + '\n')
        receipt['probe_results'] = read_probe_results(fixture / 'b/probe-results.tsv')
        receipt['checks'] = {
            'successor_completed_while_old_active': b_exit == '0' and a_active == 'true',
            'old_result_matches_expectation': (fixture / 'a/result').read_text().strip() == 'old-writer',
            'successor_result_preserved': (fixture / 'b/result').read_text().strip() == 'successor',
            'source_preserved': (fixture / 'source/sentinel').read_text() == 'source',
            'checkpoint_preserved': (fixture / 'checkpoint/sentinel').read_text() == 'checkpoint',
            'sibling_preserved': (fixture / 'sibling/sentinel').read_text() == 'sibling',
            'old_background_sibling_write_rejected': (fixture / 'a/sibling-write').read_text().strip() == 'rejected',
            'host_descriptor_positive': host_fd_positive,
            'host_descriptor_preserved': descriptor_path.read_text() == 'synthetic-open-descriptor',
            'worker_policy_and_mounts_readback': True,
            'old_exited': a_exit == '0' and stopped_successfully(final_a),
            'successor_exited': b_exit == '0' and stopped_successfully(final_b)}
        results = receipt['probe_results']
        receipt['unknown_cases'] = [key for key, outcome in results.items() if outcome == 'unknown']
        if not all(receipt['checks'].values()) or 'failed' in results.values():
            receipt['execution_outcome'] = 'failed'
            return 1
        if receipt['unknown_cases']:
            receipt['execution_outcome'] = 'partial'
            return 2
        receipt['execution_outcome'] = 'measured-synthetic-cases-passed'
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error)
        return 1
    finally:
        if host_fd is not None:
            os.close(host_fd)
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        output = fixture / 'isolation-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), 'execution_outcome': receipt['execution_outcome'],
            'checks': receipt.get('checks', {}), 'probe_results': receipt.get('probe_results', {}),
            'error': receipt.get('error'), 'production_qualified': False}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
