"""Fresh, bounded synthetic storage worker. Not an installed host or authority API."""
from __future__ import annotations

import errno
import hashlib
import os
from pathlib import Path
import sqlite3
import sys
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(Path(__file__).parent)]
import memory_governance_contract as c
import memory_governance_core as core_module
import memory_governance_storage as db
from local_ports import SyntheticLocalPorts
from process_readback_worker import compose
from storage_observer import StorageObserver, bound_worker_descriptors

IMAGE_BYTES = 256 * 1024 * 1024
ITEM = '00000000-0000-4000-8000-000000000003'
FAULTS = {'none', 'page-quota', 'missing-path-cantopen', 'physical', 'reply-loss', 'precommit-loss'}


def emit(event, **data):
    print(c.canonical({'event': event, **data}).decode(), flush=True)


def host_descriptor(ports):
    binding = ports.registry.binding()
    return {
        'root': str(binding.root), 'scope': c.decode(binding.scope_bytes),
        'profile': c.decode(binding.profile_bytes),
        **{key: list(getattr(binding, key)) for key in
           ('directory_identity', 'main_identity', 'lock_identity')},
        'filesystem_id': binding.filesystem_id, 'adapter_fingerprint': binding.adapter_fingerprint,
        'git_root': str(ports.git_root), 'git_identity': list(ports.git_identity),
        'gitdir_identity': list(ports.gitdir_identity),
        'git_config_digest': hashlib.sha256(ports.git_config).hexdigest(),
        'source_revision': ports.source_revision, 'approved': dict(ports.approved),
        'readback_ids': sorted(ports.readback_ids), 'source_current': True, 'readable': True,
        'copies': {'coverage': 'unknown', 'copies': []}, 'clock_offset': 0, 'capacity_unavailable': False,
    }


def fill_owned_image(data):
    """Only an inherited descriptor from this run's image owner; never opens a caller path."""
    c.fields(data, {'fd', 'identity', 'mount', 'mount_identity', 'parent_device'})
    fd, mount = data['fd'], Path(data['mount'])
    expected = tuple(data['identity'])
    if not (3 <= fd < 128 and os.path.ismount(mount)
            and db.identity(mount.stat()) == tuple(data['mount_identity'])
            and mount.stat().st_dev != data['parent_device']
            and db.identity(os.fstat(fd)) == expected and expected[0] == mount.stat().st_dev
            and os.fstat(fd).st_size == 0 and os.fstat(fd).st_nlink == 1):
        raise RuntimeError('physical-fixture-identity-unconfirmed')
    deadline = time.monotonic() + 30
    observation = {'written_bytes': 0, 'os_errors': [], 'stage': 'before-commit',
                   'write_attempts': 0, 'byte_limit': IMAGE_BYTES, 'deadline_seconds': 30}
    for block_size in (1048576, 65536, 4096):
        block = b'\x5a' * block_size
        try:
            while observation['written_bytes'] < IMAGE_BYTES:
                if time.monotonic() >= deadline:
                    raise TimeoutError('filler-deadline')
                if db.identity(os.fstat(fd)) != expected:
                    raise RuntimeError('filler-identity-drift')
                observation['write_attempts'] += 1
                count = os.write(fd, block[:min(block_size, IMAGE_BYTES - observation['written_bytes'])])
                if count <= 0:
                    raise RuntimeError('filler-no-progress')
                observation['written_bytes'] += count
            os.fsync(fd)
        except OSError as error:
            if error.errno != errno.ENOSPC:
                raise
            observation['os_errors'].append({'errno': error.errno, 'block_size': block_size})
    observation['available_bytes_after'] = os.statvfs(mount).f_bavail * os.statvfs(mount).f_frsize
    observation['os_enospc_observed'] = bool(observation['os_errors'])
    return observation


def replay_rejection(core, handle):
    try:
        core.execute(handle)
    except c.ContractError as error:
        return str(error)
    raise RuntimeError('consumed-handle-replayed')


def read(request):
    c.fields(request, {'mode', 'host', 'operation_id', 'preview_digest'})
    ports = compose(request['host'])
    core = core_module.GovernanceCore(ports.host, enabled=True)
    original = db.connect
    connects = []

    def readonly(*args, **kwargs):
        assert not kwargs.get('writer'), 'fresh reader attempted writer'
        connects.append('read-only')
        return original(*args, **kwargs)

    with mock.patch.object(db, 'connect', side_effect=readonly):
        rejected = replay_rejection(core, core_module.ExecutionHandle(request['operation_id']))
        result = core.readback(request['operation_id'], request['preview_digest'])
        try:
            with core.audit() as audit:
                page = audit.page()
            audit_result = {'result': 'readable', 'page': page}
        except c.ContractError as error:
            audit_result = {'result': 'rejected', 'reason': str(error)}
        projection = {}
        if audit_result['result'] == 'readable':
            for cue in ('blue', 'green'):
                projection[cue] = core.recall([cue])['items']
    emit('read', result=result, audit=audit_result, projection=projection, calls=ports.calls,
         connections=connects, replay_rejection=rejected, pid=os.getpid())


def continue_control(request):
    """A separately confirmed normal update, never replay the failed request or old handle."""
    c.fields(request, {'mode', 'host', 'failed_operation_id'})
    ports = compose(request['host'])
    core = core_module.GovernanceCore(ports.host, enabled=True)
    rejected = replay_rejection(core, core_module.ExecutionHandle(request['failed_operation_id']))
    preview = core.preview('update', ITEM, ports.candidate(2, cue='green',
                           body='Synthetic newly confirmed recovery control. ' * 260))
    assert preview['operation_id'] != request['failed_operation_id']
    result = core.execute(core.authorize(preview))
    emit('control', host=host_descriptor(ports), result=result, pid=os.getpid(),
         replay_rejection=rejected, calls=ports.calls)


def create(request, fd_limit):
    c.fields(request, {'mode', 'parent', 'fault', 'physical'})
    fault = request['fault']
    assert fault in FAULTS
    assert (fault == 'physical') == (request['physical'] is not None)
    parent = Path(request['parent'])
    assert parent.is_absolute() and parent == parent.resolve(strict=True)
    root, temporary = parent / 'managed', parent / 'sqlite-temp'
    # No adoption, overwrite, repair or cleanup of an existing test root.
    root.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    os.environ['SQLITE_TMPDIR'] = os.environ['TMPDIR'] = str(temporary)
    ports = SyntheticLocalPorts(root, git_root=parent / 'source')
    core = core_module.GovernanceCore(ports.host, enabled=True)
    core.initialize()
    physical = request['physical']
    observer = StorageObserver(root, temporary, ports.registry.binding(), fd_limit=fd_limit,
                               excluded=(() if physical is None else (physical['fd'],)))
    with observer.observing():
        normal_preview = core.preview('add', ITEM, ports.candidate(body='Synthetic normal storage control.'))
        normal = core.execute(core.authorize(normal_preview))
        assert normal['result'] == 'applied'
        candidate = ports.candidate(2, cue='green', body='Synthetic storage growth. ' * 480)
        preview = core.preview('update', ITEM, candidate)
        handle = core.authorize(preview)
        emit('prepared', host=host_descriptor(ports), normal=normal,
             operation_id=preview['operation_id'], preview_digest=c.digest(preview),
             before_digest=preview['before']['digest'], expected_after_digest=preview['expected_after_digest'],
             candidate_bytes=len(c.canonical(candidate)), pid=os.getpid())
        errors, quota, filling = [], {}, {}
        sqlite_original, connect_original = sqlite3.connect, db.connect

        def record(error, method):
            errors.append({'code': error.sqlite_errorcode, 'name': error.sqlite_errorname, 'method': method})

        class ObservedConnection(sqlite3.Connection):
            def observed(self, method, *args, **kwargs):
                observer.sample()
                try:
                    return getattr(super(), method)(*args, **kwargs)
                except sqlite3.Error as error:
                    record(error, method)
                    raise
                finally:
                    observer.sample()

            def execute(self, *args, **kwargs):
                return self.observed('execute', *args, **kwargs)

            def executemany(self, *args, **kwargs):
                return self.observed('executemany', *args, **kwargs)

            def commit(self):
                return self.observed('commit')

            def close(self):
                return self.observed('close')

        def observed_sqlite(*args, **kwargs):
            try:
                return sqlite_original(*args, **kwargs, factory=ObservedConnection)
            except sqlite3.Error as error:
                record(error, 'connect')
                raise

        def connect(*args, **kwargs):
            if kwargs.get('writer') and fault == 'missing-path-cantopen':
                # An actual code 14 caused by a missing test-only path, never called physical FULL.
                return observed_sqlite((parent / 'absent' / 'missing.sqlite3').as_uri() + '?mode=rw', uri=True)
            connection = connect_original(*args, **kwargs)
            if kwargs.get('writer'):
                quota['page_count_before'] = connection.execute('PRAGMA page_count').fetchone()[0]
                quota['profile_max_page_count'] = connection.execute('PRAGMA max_page_count').fetchone()[0]
                if fault == 'page-quota':
                    connection.execute('PRAGMA max_page_count=' + str(quota['page_count_before']))
                quota['effective_max_page_count'] = connection.execute('PRAGMA max_page_count').fetchone()[0]
            return connection

        def checkpoint(stage):
            observer.checkpoint(stage)
            if stage == 'before-commit' and fault == 'physical':
                if filling:
                    raise RuntimeError('physical-fault-repeated')
                filling['journal_bytes_before_fill'] = (root / db.JOURNAL).stat().st_size
                try:
                    filling.update(fill_owned_image(physical))
                except (OSError, RuntimeError) as error:
                    filling['failure'] = {'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
                                          'reason': str(error)}
                    raise
                observer.sample()
            if stage == 'after-commit' and fault == 'reply-loss':
                filling['injected_errno'] = errno.ENOSPC
                raise OSError(errno.ENOSPC, 'synthetic reply loss; not physical exhaustion')
            if stage == 'before-commit' and fault == 'precommit-loss':
                os._exit(73)

        with mock.patch.object(db.sqlite3, 'connect', side_effect=observed_sqlite), \
             mock.patch.object(db, 'connect', side_effect=connect), \
             mock.patch.object(core_module, '_checkpoint', side_effect=checkpoint):
            try:
                result = core.execute(handle)
            except c.ContractError as error:
                result = {'result': str(error), 'proof': None, 'state_digest': None}
        rejected = replay_rejection(core, handle)
    emit('completed', outcome=result, errors=errors, quota=quota, filling=filling,
         replay_rejection=rejected, measurement=observer.report(), runtime=db.runtime_facts(), pid=os.getpid())


def main():
    fd_limit = bound_worker_descriptors()
    request = c.decode(sys.stdin.buffer.read(c.MAX_ENVELOPE + 1))
    if request['mode'] == 'read':
        read(request)
    elif request['mode'] == 'continue':
        continue_control(request)
    elif request['mode'] == 'restore':
        c.fields(request, {'mode', 'physical'})
        from enospc_image import restore_filler
        data = request['physical']
        result = restore_filler(data['fd'], tuple(data['identity']), Path(data['mount']),
                                tuple(data['mount_identity']))
        emit('restore', result=result, pid=os.getpid())
    else:
        assert request['mode'] == 'create'
        create(request, fd_limit)


if __name__ == '__main__':
    main()
