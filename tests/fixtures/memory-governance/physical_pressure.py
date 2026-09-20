"""Fixed, test-owned pressure descriptors; no path-based mutation or runtime policy."""
from pathlib import Path
import os
import stat

import memory_governance_contract as c
import memory_governance_storage as db

FILLER_COUNT = 3
WRITE_ATTEMPTS = 70000
TAIL_BYTES = 8 * 1024 * 1024
SMALL_BYTES = 4 * 1024 * 1024
PROGRESS_PHASES = ('before_fill', 'before_sync', 'after_sync',
                   'tail_before_sync', 'tail_after_sync',
                   'small_1_before_sync', 'small_1_after_sync',
                   'small_2_before_sync', 'small_2_after_sync')


def entries(data, *, complete=False):
    c.fields(data, {'fillers', 'mount', 'mount_identity', 'parent_device'})
    c.require(type(data['mount']) is str and Path(data['mount']).is_absolute(), 'physical-mount-invalid')
    c.require(type(data['parent_device']) is int and data['parent_device'] >= 0, 'physical-device-invalid')
    def identity(value):
        return (type(value) is list and len(value) == 2
                and all(type(number) is int and number >= 0 for number in value))
    c.require(identity(data['mount_identity']), 'physical-mount-identity-invalid')
    pool = data['fillers']
    c.require(type(pool) is list and 1 <= len(pool) <= FILLER_COUNT
              and (not complete or len(pool) == FILLER_COUNT), 'physical-pool-size-invalid')
    descriptors, identities = set(), set()
    for entry in pool:
        c.fields(entry, {'fd', 'identity'})
        fd = entry['fd']
        c.require(type(fd) is int and 3 <= fd < 128 and identity(entry['identity']), 'physical-filler-invalid')
        key = tuple(entry['identity'])
        c.require(fd not in descriptors and key not in identities, 'physical-pool-alias')
        descriptors.add(fd)
        identities.add(key)
    return pool


def descriptors(data):
    return tuple(entry['fd'] for entry in entries(data))


def owned(data, entry):
    mount = Path(data['mount'])
    info, mounted = os.fstat(entry['fd']), mount.stat()
    if not (os.path.ismount(mount) and not mount.is_symlink()
            and db.identity(mounted) == tuple(data['mount_identity'])
            and mounted.st_dev != data['parent_device']
            and db.identity(info) == tuple(entry['identity']) and info.st_dev == mounted.st_dev
            and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o600):
        raise RuntimeError('physical-fixture-identity-unconfirmed')
    return info
