#!/usr/bin/env python3
"""手動、macOS-only 的新建 synthetic APFS image ENOSPC 實驗；不納入一般 CI。

預設只印 dry-run。--run 只建立本程式自己的 256 MiB image，核對新 mount 後才
填入 filler；絕不接受既有 volume/root。回復只截短自己的 filler，正常 detach 後
保留 image 及報告供檢查，不 force/unlink/repair 任何 managed file。
"""
from __future__ import annotations

import argparse
import errno
import json
import os
from pathlib import Path
import plistlib
import sqlite3
import subprocess
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from local_ports import SyntheticLocalPorts

IMAGE_BYTES = 256 * 1024 * 1024


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, timeout=60).stdout


def run():
    if sys.platform != 'darwin':
        raise RuntimeError('macOS-only')
    parent = Path(tempfile.mkdtemp(prefix='mg1-245-enospc-', dir='/private/tmp')).resolve()
    os.chmod(parent, 0o700)
    if os.statvfs(parent).f_bavail * os.statvfs(parent).f_frsize < 4 * IMAGE_BYTES:
        raise RuntimeError('insufficient-host-headroom: ' + str(parent))
    image, mount = parent / 'synthetic.dmg', parent / 'volume'
    report = {'contract_version': 'mg1-g1-enospc-observation/v0', 'synthetic_only': True,
              'production_qualified': False, 'retained_fixture': str(parent), 'image_bytes_limit': IMAGE_BYTES,
              'expected_mountpoint': str(mount), 'attachment_state': 'not-attempted',
              'status': 'not-run', 'filler_errno': None, 'sqlite_errors': [], 'detached': False}
    mounted, filler, mount_device = False, None, None
    try:
        # No -ov, -srcdevice, existing image, or filesystem target is accepted.
        command('/usr/bin/hdiutil', 'create', '-size', '256m', '-fs', 'APFS', '-layout', 'NONE',
                '-volname', 'MG1Synthetic245', '-nospotlight', '-type', 'UDIF', str(image))
        if not image.is_file() or image.is_symlink() or image.stat().st_size > IMAGE_BYTES + 1048576:
            raise RuntimeError('unexpected-image')
        report['attachment_state'] = 'unknown'
        attached = plistlib.loads(command('/usr/bin/hdiutil', 'attach', '-plist', '-nobrowse',
                                         '-noautoopen', '-noautofsck', '-owners', 'on', '-mountpoint', str(mount), str(image)))
        entities = [entry for entry in attached.get('system-entities', []) if entry.get('mount-point') == str(mount)]
        if len(entities) != 1 or not os.path.ismount(mount) or mount.stat().st_dev == parent.stat().st_dev:
            raise RuntimeError('mount-identity-unconfirmed; inspect retained fixture')
        mounted, mount_device = True, mount.stat().st_dev
        report['attachment_state'] = 'confirmed-mounted'
        info = plistlib.loads(command('/usr/sbin/diskutil', 'info', '-plist', str(mount)))
        if info.get('FilesystemType') != 'apfs' or info.get('MountPoint') != str(mount):
            raise RuntimeError('filesystem-mismatch')
        report['filesystem'] = {'type': info['FilesystemType'], 'total_bytes': info.get('TotalSize')}
        root = mount / 'managed'
        root.mkdir(mode=0o700)
        ports = SyntheticLocalPorts(root)
        core = GovernanceCore(ports.host, enabled=True)
        core.initialize()
        report['runtime'] = db.runtime_facts()
        report['runtime_digest'] = c.digest(report['runtime'])
        filler = os.open(mount / 'synthetic-filler', os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        filler_identity = db.identity(os.fstat(filler))
        preview = core.preview('add', '00000000-0000-4000-8000-000000000003',
                               ports.candidate(body='Synthetic ENOSPC fixture. ' * 480))
        handle = core.authorize(preview)
        original_connect = sqlite3.connect

        class ObservedConnection(sqlite3.Connection):
            def observed(self, method, *args, **kw):
                try:
                    return getattr(super(), method)(*args, **kw)
                except sqlite3.Error as error:
                    report['sqlite_errors'].append({'code': error.sqlite_errorcode, 'name': error.sqlite_errorname})
                    raise

            def execute(self, *args, **kw):
                return self.observed('execute', *args, **kw)

            def executemany(self, *args, **kw):
                return self.observed('executemany', *args, **kw)

            def commit(self):
                return self.observed('commit')

        def connect(*args, **kw):
            return original_connect(*args, **kw, factory=ObservedConnection)

        def fill(stage):
            if stage != 'before-transaction':
                return
            # Space was admitted before this checkpoint; simulate a competing allocation
            # ONLY on the newly attached, bounded image, never on the host filesystem.
            if not os.path.ismount(mount) or mount.stat().st_dev != mount_device or os.fstat(filler).st_dev != mount_device:
                raise RuntimeError('filler-filesystem-drift')
            written = 0
            report['filler_enospc_block_sizes'] = []
            # A large allocation may fail while SQLite-sized pages still fit.
            # Progressively consume that remainder, with the same total byte ceiling.
            for block_size in (1048576, 65536, 4096):
                try:
                    block = b'\x5a' * block_size
                    while written < IMAGE_BYTES:
                        count = os.write(filler, block[:min(len(block), IMAGE_BYTES - written)])
                        if count <= 0:
                            raise RuntimeError('filler-no-progress')
                        written += count
                    os.fsync(filler)
                except OSError as error:
                    if error.errno != errno.ENOSPC:
                        raise
                    report['filler_errno'] = error.errno
                    report['filler_enospc_block_sizes'].append(block_size)
            report['filler_bytes'] = written
            report['available_after_filler'] = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
            if report['filler_errno'] != errno.ENOSPC:
                raise RuntimeError('physical-ENOSPC-not-observed')

        with mock.patch.object(db.sqlite3, 'connect', side_effect=connect), \
             mock.patch('memory_governance_core._checkpoint', side_effect=fill):
            result = core.execute(handle)
        report.update(status='observed', result=result['result'], proof_present=result['proof'] is not None,
                      before_state_matches=result['state_digest'] == preview['before']['digest'],
                      managed_names=sorted(path.name for path in root.iterdir()))
        if not any(error['code'] == sqlite3.SQLITE_FULL for error in report['sqlite_errors']) \
                or result['result'] not in {'not-applied', 'state-unknown'}:
            raise RuntimeError('SQLite-space-failure-not-established')
        try:
            core.execute(handle)
        except c.ContractError as error:
            report['replay_result'] = str(error)
        else:
            raise RuntimeError('consumed-handle-replayed')
        if db.identity(os.fstat(filler)) != filler_identity:
            raise RuntimeError('filler-identity-drift')
    except Exception as error:
        report['status'] = 'incomplete'
        # Preserve diagnostic class without including unrelated command output or runtime state.
        report['failure'] = type(error).__name__
        if isinstance(error, subprocess.CalledProcessError):
            report['failed_command'] = list(error.cmd[:4])
            report['command_returncode'] = error.returncode
            report['diagnostic'] = error.stderr.decode(errors='replace')[:1000]
        else:
            report['diagnostic'] = str(error)[:1000]
    finally:
        if filler is not None:
            # The open descriptor is the exact filler created above; managed DB/proof stay untouched.
            try:
                os.ftruncate(filler, 0)
            except OSError as error:
                report['filler_recovery_failure'] = {'operation': 'truncate-own-filler', 'errno': error.errno}
                report['status'] = 'incomplete'
            finally:
                try:
                    os.close(filler)
                except OSError as error:
                    report['filler_close_failure'] = {'errno': error.errno}
                    report['status'] = 'incomplete'
        if mounted:
            try:
                if not os.path.ismount(mount) or mount.stat().st_dev != mount_device:
                    report['detach_failure'] = 'mount-identity-drift'
                else:
                    command('/usr/bin/hdiutil', 'detach', str(mount))
                    report['detached'] = not os.path.ismount(mount)
                    if report['detached']:
                        report['attachment_state'] = 'confirmed-detached'
                    else:
                        report['detach_failure'] = 'mount-still-present; no-force-used'
            except (OSError, subprocess.SubprocessError):
                report['detach_failure'] = 'normal-detach-failed; no-force-used'
        elif report['attachment_state'] == 'unknown':
            report['recovery_required'] = 'attachment-may-exist; inspect exact image and expected mountpoint; no unverified detach'
        try:
            (parent / 'observation.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
        except OSError as error:
            report['report_save_failure'] = {'errno': error.errno}
            report['status'] = 'incomplete'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        report = {'status': 'dry-run', 'creates': 'new /private/tmp/mg1-245-enospc-*/synthetic.dmg',
                  'filesystem': 'APFS', 'image_bytes': IMAGE_BYTES,
                  'fills': 'newly mounted image only, at most image_bytes',
                  'recovery': 'truncate own filler descriptor; normal detach; retain image',
                  'existing_data_access': False, 'production_qualified': False}
    else:
        report = run()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] in {'dry-run', 'observed'} and not report.get('detach_failure') else 2


if __name__ == '__main__':
    raise SystemExit(main())
