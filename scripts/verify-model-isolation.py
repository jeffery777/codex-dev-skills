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
import hashlib
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


# Fixed supplemental fixture, never a Codex tool or provider. The original
# parent remains alive while a double-forked, reparented child writes its own
# copy. Host release is bounded; no signal, stop or daemon restart is used.
LIFECYCLE_PROBE = r'''
import json, os, pathlib, sys, time
work = pathlib.Path('/workspace')
counter = work / 'run-count'
cycle = int(counter.read_text()) + 1 if counter.exists() else 1
if cycle not in (1, 2): raise RuntimeError('unexpected fixture cycle')
counter.write_text(str(cycle))
prefix = work / ('cycle-' + str(cycle))
parent_session = os.getsid(0)
def save(path, value):
    temporary = pathlib.Path(str(path) + '.tmp')
    temporary.write_text(json.dumps(value)); temporary.replace(path)
first = os.fork()
if first == 0:
    os.setsid()
    second = os.fork()
    if second != 0: os._exit(0)
    for _ in range(100):
        if os.getppid() == 1: break
        time.sleep(.01)
    identity = dict(pid=os.getpid(), ppid=os.getppid(), sid=os.getsid(0),
        parent_session=parent_session)
    save(pathlib.Path(str(prefix) + '-ready.json'), identity)
    for _ in range(300):
        if pathlib.Path(str(prefix) + '-release').exists(): break
        time.sleep(.05)
    else: os._exit(21)
    results = {}
    own = pathlib.Path(str(prefix) + '-own')
    own.write_text('detached-positive')
    results['own_write'] = own.read_text() == 'detached-positive'
    for name, target in zip(('source', 'checkpoint', 'sibling'), sys.argv[1:]):
        try:
            pathlib.Path(target).write_text('forbidden-detached')
            results[name + '_write_denied'] = False
        except OSError:
            results[name + '_write_denied'] = not pathlib.Path(target).exists()
    limits = {}
    for name in ('memory.max', 'pids.max', 'cpu.max'):
        try: limits[name] = (pathlib.Path('/sys/fs/cgroup') / name).read_text().strip()
        except OSError: limits[name] = None
    save(pathlib.Path(str(prefix) + '-limits.json'), limits)
    try: membership = pathlib.Path('/proc/self/cgroup').read_text().strip()
    except OSError: membership = None
    save(pathlib.Path(str(prefix) + '-cgroup.json'), dict(membership=membership))
    save(pathlib.Path(str(prefix) + '-done.json'), results)
    os._exit(0)
os.waitpid(first, 0)
for _ in range(300):
    ready = pathlib.Path(str(prefix) + '-ready.json')
    if ready.exists(): break
    time.sleep(.05)
else: raise RuntimeError('detached child not observed')
identity = json.loads(ready.read_text())
os.kill(identity['pid'], 0)
pathlib.Path(str(prefix) + '-live').write_text('observed')
for _ in range(400):
    done = pathlib.Path(str(prefix) + '-done.json')
    if done.exists(): break
    time.sleep(.05)
else: raise RuntimeError('detached child completion missing')
if not all(json.loads(done.read_text()).values()): raise RuntimeError('boundary failure')
'''


def validate_lifecycle_cycle(workspace, cycle, inspected, *, cpu_limit_unavailable=False):
    """Missing controls never establish detached-process or resource success."""
    prefix = workspace / ('cycle-' + str(cycle))
    def read(suffix):
        path = pathlib.Path(str(prefix) + suffix)
        if path.is_symlink() or path.stat().st_size > 4096:
            raise ValueError('invalid lifecycle observation')
        return json.loads(path.read_text())
    identity = read('-ready.json')
    if (set(identity) != {'pid', 'ppid', 'sid', 'parent_session'}
            or any(type(v) is not int or v <= 0 for v in identity.values())):
        raise ValueError('invalid detached identity')
    done = read('-done.json')
    expected_done = {'own_write', 'source_write_denied', 'checkpoint_write_denied', 'sibling_write_denied'}
    if set(done) != expected_done or any(type(v) is not bool for v in done.values()):
        raise ValueError('invalid detached result')
    limits = read('-limits.json')
    if set(limits) != {'memory.max', 'pids.max', 'cpu.max'}:
        raise ValueError('invalid cgroup observation')
    cpu = limits['cpu.max']
    parts = cpu.split() if type(cpu) is str else []
    cpu_matches = (not cpu_limit_unavailable and len(parts) == 2
        and all(p.isdigit() for p in parts) and int(parts[0]) == int(parts[1]) and int(parts[0]) > 0)
    resource_outcome = 'unknown' if any(v is None for v in limits.values()) or cpu_limit_unavailable else (
        'passed' if limits['memory.max'] == '134217728' and limits['pids.max'] == '32' and cpu_matches else 'failed')
    membership = read('-cgroup.json')
    if membership != {'membership': '0::/'}:
        resource_outcome = 'unknown'
    return {'detached_identity': identity['ppid'] == 1 and identity['sid'] != identity['parent_session'],
        'detached_live_positive': pathlib.Path(str(prefix) + '-live').read_text() == 'observed',
        'detached_copy_written': pathlib.Path(str(prefix) + '-own').read_text() == 'detached-positive',
        'detached_boundary_negatives': all(done.values()),
        'container_exited': stopped_successfully(inspected) and inspected['State'].get('Pid') == 0,
        'resource_readback': resource_outcome, 'observed_limits': limits,
        'observed_cgroup': membership}


def validate_lifecycle_top(raw, active):
    """Engine PID-namespace mapping is separate from worker marker claims."""
    if type(raw) is not str or len(raw.encode()) > 8192:
        raise ValueError('unbounded process readback')
    lines = [line.split() for line in raw.splitlines()]
    if not lines or lines[0] != ['PID', 'PPID', 'COMMAND'] or len(lines) != 3:
        raise ValueError('unexpected process inventory')
    processes = []
    for row in lines[1:]:
        if len(row) != 3 or not row[0].isdigit() or not row[1].isdigit() or row[2] != 'python3':
            raise ValueError('unexpected fixture process')
        processes.append((int(row[0]), int(row[1])))
    parent = active['State']['Pid']
    if type(parent) is not int or parent <= 0:
        raise ValueError('missing init process identity')
    children = [pid for pid, ppid in processes if ppid == parent and pid != parent]
    if len(children) != 1 or len(set(pid for pid, _ in processes)) != 2 or not any(pid == parent for pid, _ in processes):
        raise ValueError('detached runtime process not observed')
    return dict(init_host_pid=parent, detached_host_pid=children[0])


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


def inspect_evidence(value):
    """Persist only validation fields, never image environment or diagnostics."""
    def select(obj, fields):
        if type(obj) is not dict:
            raise ValueError('invalid inspect evidence object')
        return {key: obj[key] for key in fields.split() if key in obj}
    result = select(value, 'Id Image RestartCount')
    result['Config'] = select(value['Config'], 'Image Entrypoint Cmd User')
    result['Config']['Healthcheck'] = select(value['Config']['Healthcheck'], 'Test')
    result['HostConfig'] = select(value['HostConfig'],
        'NetworkMode ReadonlyRootfs Privileged CapDrop CapAdd SecurityOpt PidsLimit Memory NanoCpus '
        'CpuPeriod CpuQuota Tmpfs VolumesFrom Devices DeviceRequests DeviceCgroupRules RestartPolicy CgroupnsMode')
    result['State'] = select(value['State'], 'Running Status ExitCode OOMKilled Pid StartedAt FinishedAt')
    result['Mounts'] = [select(mount, 'Type Source Destination RW Propagation') for mount in value['Mounts']]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['docker', 'podman'], required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--cpu-limit-unavailable', action='store_true')
    parser.add_argument('--lifecycle', action='store_true',
        help='Also run fixed double-fork and two-start fixture; no daemon restart')
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
        engine_identity = {'client_version': command('--version'),
            'engine_executable_sha256': hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest()}
        if args.engine == 'docker':
            engine_identity['server_version'] = command('version', '--format', '{{.Server.Version}}')
            engine_identity['daemon_id_sha256'] = hashlib.sha256(command('info', '--format', '{{.ID}}').encode()).hexdigest()
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
    for name in ('source', 'checkpoint', 'sibling', 'a', 'b') + (('c',) if args.lifecycle else ()):
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
    receipt['qualification_identity'] = {
        'probe_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        'engine_executable': executable,
        **engine_identity,
        'fixed_tools': ['/bin/sh', 'cat', 'mv', 'ln', 'python3/socket', 'python3/os.fork/os.setsid'],
        'image_id': image, 'endpoint_sha256': hashlib.sha256(engine_socket.encode()).hexdigest()}
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
            (fixture / (name + '-inspect.json')).write_text(json.dumps(inspect_evidence(observed), indent=2) + '\n')
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
        if args.lifecycle:
            targets = [str(fixture / name / 'sentinel') for name in ('source', 'checkpoint', 'sibling')]
            c_script = 'exec python3 -I -S -c ' + shlex.quote(LIFECYCLE_PROBE) + ' ' + ' '.join(map(shlex.quote, targets))
            c = launch('c', c_script)
            lifecycle_cycles = []
            started_at = None
            for cycle in (1, 2):
                if cycle == 2:
                    before = json.loads(command('inspect', c))[0]
                    validate_worker(before, fixture / 'c', image=image, script=c_script, volumes=volumes,
                        cpu_limit_unavailable=args.cpu_limit_unavailable)
                    if (before['Id'] != c or not stopped_successfully(before)
                            or before['State'].get('Pid') != 0
                            or before['HostConfig'].get('RestartPolicy') != {'Name': 'no', 'MaximumRetryCount': 0}
                            or before['HostConfig'].get('CgroupnsMode') != 'private'):
                        raise ValueError('own fixture identity or exited state drift')
                    if command('start', c) != c:
                        raise ValueError('own fixture second start identity drift')
                prefix = fixture / 'c' / ('cycle-' + str(cycle))
                deadline = time.monotonic() + 8
                while not pathlib.Path(str(prefix) + '-live').exists():
                    if time.monotonic() > deadline:
                        raise OSError('detached live positive unavailable')
                    time.sleep(.05)
                active = json.loads(command('inspect', c))[0]
                validate_worker(active, fixture / 'c', image=image, script=c_script, volumes=volumes,
                    cpu_limit_unavailable=args.cpu_limit_unavailable)
                if active['Id'] != c or active['State']['Running'] is not True:
                    raise ValueError('detached fixture not running')
                if (active['HostConfig'].get('RestartPolicy') != {'Name': 'no', 'MaximumRetryCount': 0}
                        or active['HostConfig'].get('CgroupnsMode') != 'private'):
                    raise ValueError('unexpected fixture restart or cgroup namespace policy')
                current_start = active['State'].get('StartedAt')
                if type(current_start) is not str or not current_start or current_start == started_at:
                    raise ValueError('fixture start identity did not advance')
                started_at = current_start
                top_raw = command('top', c, '-eo', 'pid,ppid,comm')
                process_identity = validate_lifecycle_top(top_raw, active)
                (fixture / ('c-top-' + str(cycle) + '.txt')).write_text(top_raw + '\n')
                pathlib.Path(str(prefix) + '-release').touch(exist_ok=False)
                exit_code = command('wait', c)
                observed = json.loads(command('inspect', c))[0]
                validate_worker(observed, fixture / 'c', image=image, script=c_script, volumes=volumes,
                    cpu_limit_unavailable=args.cpu_limit_unavailable)
                if observed['Id'] != c or exit_code != '0':
                    raise ValueError('own fixture completion drift')
                (fixture / ('c-inspect-' + str(cycle) + '.json')).write_text(json.dumps(inspect_evidence(observed), indent=2) + '\n')
                measured = validate_lifecycle_cycle(fixture / 'c', cycle, observed,
                    cpu_limit_unavailable=args.cpu_limit_unavailable)
                measured['host_canaries_preserved'] = all(
                    (fixture / name / 'sentinel').read_text() == name for name in ('source', 'checkpoint', 'sibling'))
                if not measured['host_canaries_preserved']:
                    raise ValueError('protected canary changed during own fixture cycle')
                measured['runtime_identity'] = dict(container_id=c, started_at=current_start,
                    finished_at=observed['State'].get('FinishedAt'), **process_identity)
                lifecycle_cycles.append(measured)
            receipt['lifecycle_cycles'] = lifecycle_cycles
            receipt['limitations'] += ['two starts of only the same own fixture; no daemon or host restart',
                'cgroup values are readback controls, not CPU/memory/PID exhaustion or resource enforcement proof',
                'private cgroup namespace hides ancestor controls; no complete effective resource hierarchy proof',
                'fixed double-fork writer is not native Codex or complete tool/credential qualification']
            for cycle, measured in enumerate(lifecycle_cycles, 1):
                for name, value in measured.items():
                    if type(value) is bool:
                        receipt['checks']['cycle_' + str(cycle) + '_' + name] = value
                outcome = measured['resource_readback']
                results['cycle_' + str(cycle) + '_resource_readback'] = outcome
            receipt['checks']['protected_sources_after_second_start'] = all(
                (fixture / name / 'sentinel').read_text() == name for name in ('source', 'checkpoint', 'sibling'))
            receipt['checks']['exact_two_runs'] = (fixture / 'c/run-count').read_text() == '2'
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
