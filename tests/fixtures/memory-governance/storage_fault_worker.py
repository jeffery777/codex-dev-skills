"""Fresh, bounded synthetic storage worker. Not an installed host or authority API."""
from __future__ import annotations

import contextlib
import errno
import hashlib
import os
from pathlib import Path
import signal
import sqlite3
import stat
import sys
import threading
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
import physical_pressure as pressure

IMAGE_BYTES = 256 * 1024 * 1024
FILL_SECONDS = 30
PHYSICAL_STAGE = 'before-transaction'
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


@contextlib.contextmanager
def fill_deadline():
    """One terminating timer in this fresh worker, including blocked write/fsync calls."""
    if (threading.current_thread() is not threading.main_thread()
            or signal.getsignal(signal.SIGALRM) != signal.SIG_DFL
            or signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0)
            or signal.SIGALRM in signal.pthread_sigmask(signal.SIG_BLOCK, set())
            or signal.SIGALRM in signal.sigpending()):
        raise RuntimeError('filler-deadline-unavailable')
    signal.setitimer(signal.ITIMER_REAL, FILL_SECONDS)
    try:
        yield time.monotonic() + FILL_SECONDS
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def fill_owned_image(data, *, observation=None):
    """One bounded sequence on pre-bound descriptors; no retries of the target transaction."""
    pool = pressure.entries(data, complete=True)
    offsets = [0] * len(pool)
    observation = {} if observation is None else observation
    observation.update(written_bytes=0, os_errors=[], stage=PHYSICAL_STAGE,
                       write_attempts=0, byte_limit=IMAGE_BYTES, deadline_seconds=FILL_SECONDS,
                       write_attempt_limit=pressure.WRITE_ATTEMPTS,
                       deadline_enforcement='worker-default-SIGALRM', os_enospc_observed=False,
                       sync={'result': 'not-attempted'}, pressure_samples={}, stages=[],
                       pressure_ready=False, filler_count=len(pool))
    with fill_deadline() as deadline:
        for entry in pool:
            if pressure.owned(data, entry).st_size != 0:
                raise RuntimeError('physical-filler-not-empty')

        def check():
            if time.monotonic() >= deadline:
                raise TimeoutError('filler-deadline')

        def sample(stage):
            check()
            files = []
            for index, entry in enumerate(pool):
                info = pressure.owned(data, entry)
                if info.st_size != offsets[index]:
                    raise RuntimeError('filler-offset-drift')
                files.append({'index': index, 'logical_bytes': info.st_size,
                              'allocated_bytes': info.st_blocks * 512})
            fs = os.fstatvfs(pool[0]['fd'])
            for entry in pool:
                pressure.owned(data, entry)
            observation['pressure_samples'][stage] = {
                'available_bytes': fs.f_bavail * fs.f_frsize, 'files': files,
                'filler_logical_bytes': sum(value['logical_bytes'] for value in files),
                'filler_allocated_bytes': sum(value['allocated_bytes'] for value in files)}
            observation['phase'] = stage
            emit('filling', observation=observation)
            check()

        def write_stage(index, name, block_sizes, maximum):
            entry = pool[index]
            start = offsets[index]
            if pressure.owned(data, entry).st_size != start:
                raise RuntimeError('filler-offset-drift')
            stage = {'name': name, 'filler_index': index, 'offset_before': start, 'next_offset': start,
                     'written_bytes': 0, 'write_attempts': 0, 'short_writes': 0,
                     'byte_limit': maximum, 'stop': None, 'sync': {'result': 'not-attempted'}}
            observation['stages'].append(stage)
            for block_size in block_sizes:
                block = b'\x5a' * block_size
                while stage['written_bytes'] < maximum and observation['written_bytes'] < IMAGE_BYTES:
                    check()
                    if observation['write_attempts'] >= pressure.WRITE_ATTEMPTS:
                        raise RuntimeError('filler-write-attempt-limit')
                    info = pressure.owned(data, entry)
                    if info.st_size != stage['next_offset']:
                        raise RuntimeError('filler-offset-drift')
                    requested = min(block_size, maximum - stage['written_bytes'],
                                    IMAGE_BYTES - observation['written_bytes'])
                    stage['write_attempts'] += 1
                    observation['write_attempts'] += 1
                    stage['last_requested_bytes'] = requested
                    try:
                        if name == 'bulk':
                            if os.lseek(entry['fd'], 0, os.SEEK_CUR) != stage['next_offset']:
                                raise RuntimeError('filler-offset-drift')
                            count = os.write(entry['fd'], block[:requested])
                        else:
                            count = os.pwrite(entry['fd'], block[:requested], stage['next_offset'])
                    except OSError as error:
                        stage['errno'] = error.errno
                        stage['stop'] = 'enospc' if error.errno == errno.ENOSPC else 'write-error'
                        if error.errno != errno.ENOSPC:
                            raise
                        observation['os_errors'].append({'operation': 'write' if name == 'bulk' else 'pwrite', 'errno': error.errno,
                            'block_size': block_size, 'filler_index': index, 'stage': name,
                            'offset': stage['next_offset']})
                        observation['os_enospc_observed'] = True
                        break
                    if type(count) is not int or not 0 < count <= requested:
                        raise RuntimeError('filler-no-progress')
                    stage['short_writes'] += int(count < requested)
                    stage['written_bytes'] += count
                    stage['next_offset'] += count
                    offsets[index] += count
                    observation['written_bytes'] += count
                    stage['stop'] = None
            if observation['written_bytes'] >= IMAGE_BYTES:
                stage['stop'] = 'total-byte-limit'
            elif stage['written_bytes'] >= maximum:
                stage['stop'] = 'stage-byte-limit'
            return stage

        def sync_stage(stage, before, after):
            sample(before)
            check()
            entry = pool[stage['filler_index']]
            pressure.owned(data, entry)
            stage['sync'] = {'result': 'started'}
            if stage['name'] == 'bulk':
                observation['sync'] = stage['sync']
            try:
                os.fsync(entry['fd'])
            except OSError as error:
                stage['sync'].update(result='failed', errno=error.errno)
                raise
            stage['sync']['result'] = 'succeeded'
            sample(after)

        sample('before_fill')
        bulk = write_stage(0, 'bulk', (1048576, 65536, 4096), IMAGE_BYTES)
        sync_stage(bulk, 'before_sync', 'after_sync')
        for index, name, maximum in ((0, 'tail', pressure.TAIL_BYTES),
                                      (1, 'small_1', pressure.SMALL_BYTES),
                                      (2, 'small_2', pressure.SMALL_BYTES)):
            if observation['written_bytes'] >= IMAGE_BYTES:
                raise RuntimeError('pressure-byte-budget-exhausted')
            stage = write_stage(index, name, (4096,), maximum)
            sync_stage(stage, name + '_before_sync', name + '_after_sync')
        if stage['stop'] != 'enospc':
            raise RuntimeError('pressure-final-probe-not-exhausted')
        observation['available_bytes_after'] = observation['pressure_samples']['small_2_after_sync']['available_bytes']
        observation['pressure_ready'] = True
    return observation


def journal_before_fill(root):
    """Absence is an observed state, not a zero-byte measurement or a suppressed error."""
    try:
        info = (root / db.JOURNAL).lstat()
    except FileNotFoundError:
        return {'state': 'absent', 'bytes': None}
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError('journal-not-regular')
    return {'state': 'present', 'bytes': info.st_size}


def replay_rejection(core, handle):
    try:
        core.execute(handle)
    except c.ContractError as error:
        return str(error)
    raise RuntimeError('consumed-handle-replayed')


def configure_temporary(root, name):
    """Use only the sibling directory created by this trial's originating worker."""
    temporary = root.parent / name
    info = temporary.lstat()
    if (not stat.S_ISDIR(info.st_mode) or temporary.resolve(strict=True) != temporary
            or info.st_dev != root.stat().st_dev or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise RuntimeError('temporary-directory-unconfirmed')
    os.environ['SQLITE_TMPDIR'] = os.environ['TMPDIR'] = str(temporary)
    return temporary


def read(request, fd_limit):
    c.fields(request, {'mode', 'host', 'operation_id', 'preview_digest'})
    temporary = configure_temporary(Path(request['host']['root']), 'reader-temp')
    ports = compose(request['host'])
    core = core_module.GovernanceCore(ports.host, enabled=True)
    observer = StorageObserver(ports.registry.binding().root, temporary, ports.registry.binding(),
                               fd_limit=fd_limit)
    original = db.connect
    connects = []

    def readonly(*args, **kwargs):
        assert not kwargs.get('writer'), 'fresh reader attempted writer'
        connects.append('read-only')
        return original(*args, **kwargs)

    with mock.patch.object(db, 'connect', side_effect=readonly), observer.observing():
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
         connections=connects, replay_rejection=rejected, pid=os.getpid(), measurement=observer.report())


def continue_control(request, fd_limit):
    """A separately confirmed normal update, never replay the failed request or old handle."""
    c.fields(request, {'mode', 'host', 'failed_operation_id'})
    temporary = configure_temporary(Path(request['host']['root']), 'control-temp')
    ports = compose(request['host'])
    core = core_module.GovernanceCore(ports.host, enabled=True)
    observer = StorageObserver(ports.registry.binding().root, temporary, ports.registry.binding(),
                               fd_limit=fd_limit)
    with observer.observing():
        rejected = replay_rejection(core, core_module.ExecutionHandle(request['failed_operation_id']))
        preview = core.preview('update', ITEM, ports.candidate(2, cue='green',
                               body='Synthetic newly confirmed recovery control. ' * 260))
        assert preview['operation_id'] != request['failed_operation_id']
        result = core.execute(core.authorize(preview))
    emit('control', host=host_descriptor(ports), result=result, pid=os.getpid(),
         replay_rejection=rejected, calls=ports.calls, measurement=observer.report())


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
    for name in ('sqlite-temp', 'reader-temp', 'control-temp'):
        (parent / name).mkdir(mode=0o700)
    temporary = configure_temporary(root, 'sqlite-temp')
    ports = SyntheticLocalPorts(root, git_root=parent / 'source')
    core = core_module.GovernanceCore(ports.host, enabled=True)
    core.initialize()
    physical = request['physical']
    observer = StorageObserver(root, temporary, ports.registry.binding(), fd_limit=fd_limit,
                               excluded=(() if physical is None else pressure.descriptors(physical)))
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
            if stage == PHYSICAL_STAGE and fault == 'physical':
                if filling:
                    raise RuntimeError('physical-fault-repeated')
                filling['stage'] = stage
                try:
                    filling['journal_before_fill'] = journal_before_fill(root)
                    if filling['journal_before_fill']['bytes'] not in {None, 0}:
                        raise RuntimeError('nonempty-journal-before-fill; recovery-required')
                    filling.update(fill_owned_image(physical, observation=filling))
                except (OSError, RuntimeError) as error:
                    filling['failure'] = {'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
                                          'reason': str(error)[:1000]}
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
            except (c.ContractError, RuntimeError) as error:
                # The physical checkpoint precedes the core's transaction try block.
                # Preserve fixture failures without manufacturing a transaction outcome.
                result = {'result': str(error)[:1000], 'proof': None, 'state_digest': None}
        rejected = replay_rejection(core, handle)
    emit('completed', outcome=result, errors=errors, quota=quota, filling=filling,
         replay_rejection=rejected, measurement=observer.report(), runtime=db.runtime_facts(), pid=os.getpid())


def main():
    fd_limit = bound_worker_descriptors()
    request = c.decode(sys.stdin.buffer.read(c.MAX_ENVELOPE + 1))
    if request['mode'] == 'read':
        read(request, fd_limit)
    elif request['mode'] == 'continue':
        continue_control(request, fd_limit)
    elif request['mode'] == 'restore':
        c.fields(request, {'mode', 'physical'})
        from enospc_image import restore_pool
        result = restore_pool(request['physical'])
        emit('restore', result=result, pid=os.getpid())
    else:
        assert request['mode'] == 'create'
        create(request, fd_limit)


if __name__ == '__main__':
    main()
