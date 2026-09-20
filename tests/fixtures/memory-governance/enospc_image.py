#!/usr/bin/env python3
"""macOS-only physical ENOSPC fixture; dry-run unless --run is explicit.

Creates one new 256 MiB APFS image. Never accepts an existing image/volume/root.
Restores space only by truncating its own filler; never repairs SQLite journals.
Normal detach only; retain every image and report, including incomplete trials.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import sys
import tempfile
from xml.parsers.expat import ExpatError

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(Path(__file__).parent)]
import memory_governance_storage as db
from storage_fault_case import run_case, worker

IMAGE_BYTES = 256 * 1024 * 1024
HOST_HEADROOM = 1024 * 1024 * 1024
DIAGNOSTIC_BYTES = 8192


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout


def available(path):
    value = os.statvfs(path)
    return value.f_bavail * value.f_frsize


def command_failure(error, stage):
    """Local-only evidence. Never publish raw command/output or resource identities."""
    result = {'failure_stage': stage, 'command': list(error.cmd),
              'command_returncode': getattr(error, 'returncode', None),
              'command_timed_out': isinstance(error, subprocess.TimeoutExpired)}
    for name in ('stdout', 'stderr'):
        value = getattr(error, name, None) or b''
        if isinstance(value, str):
            value = value.encode('utf-8')
        result[name] = value[:DIAGNOSTIC_BYTES].decode(errors='replace')
        result[name + '_truncated'] = len(value) > DIAGNOSTIC_BYTES
    return result


def preflight():
    """Read-only service/headroom probe; readiness does not prove image creation."""
    result = {'status': 'incomplete', 'creates_resources': False,
              'physical_attempt_started': False, 'production_qualified': False}
    stage = 'platform'
    try:
        if sys.platform != 'darwin':
            raise RuntimeError('macOS-only')
        stage = 'host-headroom'
        result['host_available_bytes'] = available(Path('/private/tmp'))
        if result['host_available_bytes'] < HOST_HEADROOM + IMAGE_BYTES + 1048576:
            raise RuntimeError('insufficient-host-headroom')
        stage = 'disk-management-query'
        info = plistlib.loads(command('/usr/sbin/diskutil', 'info', '-plist', '/'))
        if not isinstance(info, dict) or info.get('Error') or not info.get('DeviceNode'):
            raise RuntimeError('disk-management-response-unconfirmed')
        stage = 'image-framework-query'
        images = plistlib.loads(command('/usr/bin/hdiutil', 'info', '-plist'))
        if not isinstance(images, dict) or not isinstance(images.get('images'), list):
            raise RuntimeError('image-framework-response-unconfirmed')
        result.update(status='ready', disk_management_query_passed=True,
                      image_framework_query_passed=True,
                      image_creation_proven=False)
    except (OSError, RuntimeError, ValueError, ExpatError, subprocess.SubprocessError) as error:
        result.update(failure_stage=stage, failure=type(error).__name__)
        if isinstance(error, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            result.update(command_failure(error, stage))
        else:
            result['diagnostic'] = str(error)[:1000]
    return result


def confirm_image_attachment(image, image_identity, mount, device, image_info):
    info = image.lstat()
    matches = [entry for entry in image_info.get('images', []) if entry.get('image-path') == str(image)]
    if (not stat.S_ISREG(info.st_mode) or db.identity(info) != image_identity or len(matches) != 1
            or not any(entry.get('mount-point') == str(mount) and entry.get('dev-entry') == device
                       for entry in matches[0].get('system-entities', []))):
        raise RuntimeError('image-attachment-binding-unconfirmed')


def confirm_mount(parent, mount, attached, info):
    entries = [entry for entry in attached.get('system-entities', []) if entry.get('mount-point') == str(mount)]
    if (len(entries) != 1 or not os.path.ismount(mount) or mount.is_symlink()
            or mount.stat().st_dev == parent.stat().st_dev):
        raise RuntimeError('mount-identity-unconfirmed')
    device = entries[0].get('dev-entry', '')
    if (not re.fullmatch(r'/dev/disk[0-9]+(?:s[0-9]+)*', device)
            or info.get('DeviceNode') != device or info.get('MountPoint') != str(mount)
            or info.get('FilesystemType') != 'apfs'
            or type(info.get('TotalSize')) is not int or not 0 < info['TotalSize'] <= IMAGE_BYTES):
        raise RuntimeError('filesystem-device-or-size-unconfirmed')
    return db.identity(mount.stat()), device


def restore_filler(fd, identity, mount, mount_identity):
    try:
        if (not os.path.ismount(mount) or db.identity(mount.stat()) != mount_identity
                or db.identity(os.fstat(fd)) != identity or identity[0] != mount_identity[0]
                or os.fstat(fd).st_nlink != 1):
            return {'result': 'refused', 'reason': 'filler-or-mount-identity-drift'}
        before = available(mount)
        size = os.fstat(fd).st_size
        os.ftruncate(fd, 0)
        os.fsync(fd)
        after = available(mount)
        if os.fstat(fd).st_size != 0 or (size and after <= before):
            return {'result': 'unproven', 'reason': 'space-not-observed-restored',
                    'available_before': before, 'available_after': after}
        return {'result': 'restored', 'operation': 'truncate-own-filler', 'released_logical_bytes': size,
                'available_before': before, 'available_after': after}
    except OSError as error:
        return {'result': 'failed', 'operation': 'truncate-own-filler', 'errno': error.errno}


def bounded_restore(physical):
    child = worker({'mode': 'restore', 'physical': physical}, pass_fds=(physical['fd'],), timeout=30)
    events = child['events']
    if child['timed_out'] or child['returncode'] != 0 or len(events) != 1 or events[0].get('event') != 'restore':
        return {'result': 'unproven', 'reason': 'restoration-worker-incomplete',
                'timed_out': child['timed_out'], 'returncode': child['returncode']}
    return events[0]['result']


def run():
    readiness = preflight()
    if readiness['status'] != 'ready':
        return {'status': 'incomplete', 'detached': False, 'preflight': readiness,
                'failure_stage': 'preflight', 'physical_attempt_started': False,
                'synthetic_only': True, 'production_qualified': False}
    parent = Path(tempfile.mkdtemp(prefix='mg1-g1-enospc-', dir='/private/tmp')).resolve()
    os.chmod(parent, 0o700)
    image, mount = parent / 'synthetic.dmg', parent / 'volume'
    report = {'contract_version': 'mg1-g1-enospc-observation/v1', 'synthetic_only': True,
              'production_qualified': False, 'retained_fixture': str(parent), 'image_bytes_limit': IMAGE_BYTES,
              'host_headroom_minimum': HOST_HEADROOM, 'attempt_limit': 1,
              'expected_mountpoint': str(mount), 'attachment_state': 'not-attempted',
              'status': 'incomplete', 'detached': False, 'preflight': readiness,
              'create_configuration': {'size_mib': 256, 'filesystem': 'APFS', 'layout': 'GPTSPUD',
                                       'image_type': 'UDIF', 'verbose': True}}
    mount_identity = filler = filler_identity = physical = None
    restoration_attempted = False
    stage = 'resource-preview'
    try:
        report['host_available_before'] = available(parent)
        if report['host_available_before'] < HOST_HEADROOM + IMAGE_BYTES + 1048576:
            raise RuntimeError('insufficient-host-headroom')
        create_command = ('/usr/bin/hdiutil', 'create', '-size', '256m', '-fs', 'APFS', '-layout', 'GPTSPUD',
                          '-volname', 'MG1Synthetic', '-nospotlight', '-type', 'UDIF', '-verbose', str(image))
        preview = {'command': list(create_command), 'parent_identity': list(db.identity(parent.stat())),
                   'image_must_be_absent': str(image), 'mount_must_be_absent': str(mount),
                   'image_bytes_limit': IMAGE_BYTES, 'host_headroom_minimum': HOST_HEADROOM,
                   'host_available_before': report['host_available_before'], 'attempt_limit': 1}
        if os.path.lexists(image) or os.path.lexists(mount):
            raise RuntimeError('new-resource-already-exists')
        with (parent / 'resource-preview.json').open('x', encoding='utf-8') as output:
            output.write(json.dumps(preview, sort_keys=True, indent=2) + '\n')
        stage = 'image-create'
        command(*create_command)
        if not image.is_file() or image.is_symlink() or image.stat().st_size > IMAGE_BYTES + 1048576:
            raise RuntimeError('unexpected-image')
        report['image_identity'] = list(db.identity(image.stat()))
        report['host_available_after_create'] = available(parent)
        if report['host_available_after_create'] < HOST_HEADROOM:
            raise RuntimeError('insufficient-host-headroom-after-create')
        report['attachment_state'] = 'unknown'
        stage = 'image-attach'
        attached = plistlib.loads(command('/usr/bin/hdiutil', 'attach', '-plist', '-nobrowse',
                                         '-noautoopen', '-noautofsck', '-owners', 'on',
                                         '-mountpoint', str(mount), str(image)))
        stage = 'mount-identity'
        info = plistlib.loads(command('/usr/sbin/diskutil', 'info', '-plist', str(mount)))
        candidate_identity, device = confirm_mount(parent, mount, attached, info)
        stage = 'image-attachment-binding'
        confirm_image_attachment(image, tuple(report['image_identity']), mount, device,
                                 plistlib.loads(command('/usr/bin/hdiutil', 'info', '-plist')))
        mount_identity = candidate_identity
        report['attachment_state'] = 'confirmed-mounted'
        report['mount_identity'] = list(mount_identity)
        report['device_node'] = device
        report['filesystem'] = {'type': info['FilesystemType'], 'total_bytes': info['TotalSize']}
        stage = 'filler-create'
        filler = os.open(mount / 'synthetic-filler', os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        filler_identity = db.identity(os.fstat(filler))
        if filler_identity[0] != mount_identity[0]:
            raise RuntimeError('filler-filesystem-mismatch')
        scenario = mount / 'scenario'
        scenario.mkdir(mode=0o700)
        physical = {'fd': filler, 'identity': list(filler_identity), 'mount': str(mount),
                    'mount_identity': list(mount_identity), 'parent_device': parent.stat().st_dev}

        def recover():
            nonlocal restoration_attempted
            restoration_attempted = True
            report['space_restoration'] = bounded_restore(physical)
            return report['space_restoration']

        stage = 'storage-experiment'
        report['experiment'] = run_case(scenario, 'physical', physical=physical, recover=recover)
        report['status'] = report['experiment']['status']
    except Exception as error:
        report['status'] = 'incomplete'
        report['failure'] = type(error).__name__
        report['failure_stage'] = stage
        if isinstance(error, (subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            report.update(command_failure(error, stage))
        else:
            report['diagnostic'] = str(error)[:1000]
        if stage == 'image-create':
            report['creation_internal_attachment'] = 'unknown; outer attach not attempted; no unverified detach'
    finally:
        if filler is not None:
            if not restoration_attempted:
                # A failure before constructing the verified descriptor forbids even filler mutation.
                report['space_restoration'] = (bounded_restore(physical) if physical is not None else
                                                {'result': 'refused', 'reason': 'filler-binding-incomplete'})
            try:
                os.close(filler)
            except OSError as error:
                report['filler_close_failure'] = {'errno': error.errno}
                report['status'] = 'incomplete'
        if mount_identity is not None:
            try:
                if not os.path.ismount(mount) or db.identity(mount.stat()) != mount_identity:
                    raise RuntimeError('mount-identity-drift; no-detach')
                command('/usr/bin/hdiutil', 'detach', str(mount))
                if os.path.ismount(mount):
                    raise RuntimeError('mount-still-present; no-force-used')
                report['detached'] = True
                report['attachment_state'] = 'confirmed-detached'
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                report['status'] = 'incomplete'
                report['detach_failure'] = type(error).__name__ + '; normal-detach-unconfirmed; no-force-used'
        elif report['attachment_state'] == 'unknown':
            report['recovery_required'] = 'attachment-may-exist; inspect exact image and expected mountpoint; no unverified detach'
        if report.get('space_restoration', {}).get('result') in {'failed', 'refused', 'unproven'}:
            report['status'] = 'incomplete'
        report['host_available_after'] = available(parent)
        try:
            with (parent / 'observation.json').open('x', encoding='utf-8') as output:
                output.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
        except OSError as error:
            report['report_save_failure'] = {'errno': error.errno}
            report['status'] = 'incomplete'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true')
    mode.add_argument('--preflight', action='store_true', help='read-only service/headroom checks; no image created')
    args = parser.parse_args()
    if args.preflight:
        report = preflight()
    elif not args.run:
        report = {'status': 'dry-run', 'creates': 'new /private/tmp/mg1-g1-enospc-*/synthetic.dmg',
                  'filesystem': 'APFS', 'image_bytes': IMAGE_BYTES, 'host_headroom_minimum': HOST_HEADROOM,
                  'layout': 'GPTSPUD', 'image_type': 'UDIF', 'create_verbose': True,
                  'fault_stage': 'before-transaction', 'attempt_limit': 1, 'worker_timeout_seconds': 90,
                  'fills': 'own inherited filler fd on confirmed new mount only; at most image_bytes',
                  'recovery': 'truncate own filler once; fresh readback without repair; normal detach; retain image',
                  'existing_data_access': False, 'production_qualified': False}
    else:
        report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] in {'dry-run', 'ready'} or (report['status'] == 'observed' and report['detached']) else 2


if __name__ == '__main__':
    raise SystemExit(main())
