#!/usr/bin/env python3
"""Opt-in synthetic container probe. This never qualifies a production adapter.

Run with scripts/project-python. Uses an already installed immutable image;
retains bounded test containers and evidence, without pulling or cleanup.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import time


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


def validate_mounts(mounts, workspace):
    if not isinstance(mounts, list):
        raise ValueError('invalid container mount readback')
    binds = [m for m in mounts if m.get('Type') == 'bind']
    if (any(m.get('Type') == 'volume' for m in mounts) or len(binds) != 1
            or binds[0].get('Destination') != '/workspace'
            or pathlib.Path(binds[0].get('Source', '')).resolve() != workspace):
        raise ValueError('container mount readback does not match isolated fixture')


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

    def command(*argv):
        return subprocess.check_output(engine + list(argv), text=True, timeout=30).strip()

    if args.engine == 'docker':
        context = command('context', 'show')
        endpoint = json.loads(command('context', 'inspect', context))[0]['Endpoints']['docker']['Host']
        if not endpoint.startswith('unix://'):
            parser.error('only a local Docker Unix socket is allowed')
        # Bind all later calls to the inspected context; DOCKER_HOST must not
        # redirect a local proof to an uninspected remote daemon.
        engine = [executable, '--context', context]
    elif command('info', '--format', '{{.Host.Security.Rootless}}') != 'true':
        parser.error('only rootless local Podman is allowed')
    image = command('image', 'inspect', args.image, '--format', '{{.Id}}')
    if len(image.removeprefix('sha256:')) != 64 or any(c not in '0123456789abcdef' for c in image.removeprefix('sha256:')):
        parser.error('immutable image identity required')
    try:
        volumes = validate_image_volumes(json.loads(command('image', 'inspect', image, '--format', '{{json .Config.Volumes}}')))
    except ValueError as error:
        parser.error(str(error))
    fixture = pathlib.Path(tempfile.mkdtemp(prefix='model-isolation-', dir=root))
    for name in ('source', 'checkpoint', 'a', 'b'):
        directory = fixture / name
        directory.mkdir()
        directory.chmod(0o777)  # Synthetic writable mounts for unprivileged UID.
        (directory / 'sentinel').write_text(name)
    receipt = {'schema_version': 1, 'scope': 'synthetic-container-isolation-only',
        'engine': args.engine, 'image': image, 'fixture': str(fixture),
        'containers_retained': [], 'production_qualified': False,
        'image_volumes_replaced_with_readonly_tmpfs': sorted(volumes),
        'resource_limits': {'memory': '128m', 'pids': 32, 'cpu': None if args.cpu_limit_unavailable else 1}}
    start = time.monotonic()

    def launch(name, script):
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
        mounts = json.loads(command('inspect', cid, '--format', '{{json .Mounts}}'))
        validate_mounts(mounts, fixture / name)
        return cid

    try:
        a = launch('a', '(i=0; while test ! -f /workspace/release; do i=$((i+1)); test \"$i\" -lt 100 || exit 10; sleep 0.2; done; echo old-writer > /workspace/result) & echo initiated > /workspace/started; wait')
        ready_deadline = time.monotonic() + 5
        while not (fixture / 'a/started').exists():
            if time.monotonic() >= ready_deadline:
                raise OSError('old writer did not become ready within deadline')
            time.sleep(0.05)
        b = launch('b', 'test ! -e /var/run/docker.sock && test ! -e /source && test ! -e /checkpoint && test ! -e /sibling || exit 9; for dir in /source /checkpoint /sibling; do if mkdir \"$dir\" 2>/dev/null; then exit 9; fi; done; echo successor > /workspace/result')
        b_exit = command('wait', b)
        a_active = command('inspect', a, '--format', '{{.State.Running}}')
        (fixture / 'a/release').touch(exist_ok=False)
        a_exit = command('wait', a)
        receipt['checks'] = {
            'successor_completed_while_old_active': b_exit == '0' and a_active == 'true',
            'old_result_matches_expectation': (fixture / 'a/result').read_text().strip() == 'old-writer',
            'successor_result_preserved': (fixture / 'b/result').read_text().strip() == 'successor',
            'source_preserved': (fixture / 'source/sentinel').read_text() == 'source',
            'checkpoint_preserved': (fixture / 'checkpoint/sentinel').read_text() == 'checkpoint',
            'forbidden_root_paths_cannot_be_created': b_exit == '0',
            'old_exited': a_exit == '0'}
        return 0 if all(receipt['checks'].values()) else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error)
        return 1
    finally:
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        output = fixture / 'isolation-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), **receipt}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
