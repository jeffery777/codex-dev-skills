"""Test-only sampling; never supplies StorageQualificationPort bounds.

Run fd sampling only in a fresh fixture subprocess with a bounded descriptor limit.
The timestamps bracket the *whole* flock lifetime, including entry/exit inventory.
Even complete interval bracketing is not a worst-case latency qualification.
"""
from __future__ import annotations

import contextlib
import errno
import os
from pathlib import Path
import resource
import stat
import time
from unittest import mock

import memory_governance_storage as db

FD_LIMIT = 128


def bound_worker_descriptors():
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    limit = min(FD_LIMIT, soft)
    resource.setrlimit(resource.RLIMIT_NOFILE, (limit, hard))
    return limit


class StorageObserver:
    def __init__(self, root: Path, temporary: Path, binding, *, fd_limit=None, excluded=()):
        self.root, self.temporary, self.binding = root, temporary, binding
        self.fd_limit, self.excluded = fd_limit, frozenset(excluded)
        if fd_limit is not None:
            assert 0 < fd_limit <= FD_LIMIT
            assert resource.getrlimit(resource.RLIMIT_NOFILE)[0] <= fd_limit
        self.samples = 0
        self.errors = []
        self.names = set()
        self.checkpoints = []
        self.intervals = []
        self.held = {}
        self.peak = {key: 0 for key in (
            'main_bytes', 'journal_bytes', 'wal_bytes', 'shm_bytes', 'named_temp_bytes',
            'other_named_bytes', 'unlinked_fd_bytes', 'other_fd_bytes',
            'sampled_unique_file_bytes', 'main_allocated_bytes')}
        self.first_main = self.root.joinpath(db.MAIN).stat().st_size
        self.origin_ns = time.monotonic_ns()

    def sample(self):
        """Bounded census; short-lived objects between samples remain unknown."""
        try:
            unique, sizes, temp_sizes = {}, {}, {}
            for directory, target in ((self.root, sizes), (self.temporary, temp_sizes)):
                with os.scandir(directory) as entries:
                    for entry in entries:
                        if len(target) >= 32:
                            raise RuntimeError('sample-directory-limit')
                        info = entry.stat(follow_symlinks=False)
                        if not stat.S_ISREG(info.st_mode):
                            raise RuntimeError('sample-nonregular-file')
                        target[entry.name] = info.st_size
                        unique[db.identity(info)] = info.st_size
                        self.names.add(('managed/' if directory == self.root else 'temp/') + entry.name)
            unlinked, other = {}, {}
            if self.fd_limit is not None:
                for fd in range(3, self.fd_limit):
                    if fd in self.excluded:
                        continue
                    try:
                        info = os.fstat(fd)
                    except OSError as error:
                        if error.errno == errno.EBADF:
                            continue
                        raise
                    if stat.S_ISREG(info.st_mode):
                        identity = db.identity(info)
                        if identity not in unique:
                            (unlinked if info.st_nlink == 0 else other)[identity] = info.st_size
                            unique[identity] = info.st_size
            now = {
                'main_bytes': sizes.get(db.MAIN, 0), 'journal_bytes': sizes.get(db.JOURNAL, 0),
                'wal_bytes': sizes.get(db.MAIN + '-wal', 0), 'shm_bytes': sizes.get(db.MAIN + '-shm', 0),
                'named_temp_bytes': sum(temp_sizes.values()),
                'other_named_bytes': sum(size for name, size in sizes.items()
                                         if name not in {db.MAIN, db.LOCK, db.JOURNAL,
                                                         db.MAIN + '-wal', db.MAIN + '-shm'}),
                'unlinked_fd_bytes': sum(unlinked.values()), 'other_fd_bytes': sum(other.values()),
                'sampled_unique_file_bytes': sum(unique.values()),
                'main_allocated_bytes': self.root.joinpath(db.MAIN).stat().st_blocks * 512,
            }
            for key, value in now.items():
                self.peak[key] = max(self.peak[key], value)
            self.samples += 1
        except (OSError, RuntimeError) as error:
            # sqlite progress callbacks must not silently turn sampler failure into a clean report.
            if len(self.errors) < 16:
                self.errors.append({'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
                                    'reason': str(error)[:200]})
        return 0

    def checkpoint(self, stage):
        self.checkpoints.append(stage)
        self.sample()

    @contextlib.contextmanager
    def observing(self):
        flock_original, close_original, connect_original = db.fcntl.flock, db.os.close, db.connect

        def flock(fd, operation):
            own_lock = db.identity(os.fstat(fd)) == self.binding.lock_identity
            before = time.monotonic_ns() - self.origin_ns
            value = flock_original(fd, operation)
            after = time.monotonic_ns() - self.origin_ns
            if own_lock and operation & (db.fcntl.LOCK_EX | db.fcntl.LOCK_SH):
                if fd in self.held:
                    raise RuntimeError('observer-lock-reacquisition')
                event = {'exclusive': bool(operation & db.fcntl.LOCK_EX),
                         'acquire_before_ns': before, 'acquire_after_ns': after,
                         'release_before_ns': None, 'release_after_ns': None}
                self.held[fd] = event
                self.intervals.append(event)
                self.sample()
            return value

        def close(fd):
            event = self.held.get(fd)
            if event is None:
                return close_original(fd)
            self.sample()
            event['release_before_ns'] = time.monotonic_ns() - self.origin_ns
            try:
                value = close_original(fd)
            except OSError:
                event['release_uncertain'] = True
                raise
            else:
                event['release_after_ns'] = time.monotonic_ns() - self.origin_ns
                return value
            finally:
                del self.held[fd]

        def connect(*args, **kwargs):
            connection = connect_original(*args, **kwargs)
            connection.set_progress_handler(self.sample, 50)
            self.sample()
            return connection

        with mock.patch.object(db.fcntl, 'flock', side_effect=flock), \
             mock.patch.object(db.os, 'close', side_effect=close), \
             mock.patch.object(db, 'connect', side_effect=connect):
            self.sample()
            try:
                yield self
            finally:
                self.sample()

    def report(self):
        intervals = []
        for event in self.intervals:
            event = dict(event)
            if event['release_after_ns'] is not None:
                event['held_ns_lower'] = event['release_before_ns'] - event['acquire_after_ns']
                event['held_ns_upper'] = event['release_after_ns'] - event['acquire_before_ns']
            intervals.append(event)
        return {
            'sample_count': self.samples, 'sample_errors': self.errors, 'measured_maxima': self.peak,
            'main_growth_observed_bytes': max(0, self.peak['main_bytes'] - self.first_main),
            'named_files_seen': sorted(self.names), 'checkpoints': sorted(set(self.checkpoints)),
            'lock_intervals': intervals,
            'coverage': {
                'size_method': 'named-files-and-own-fd-metadata-at-boundaries-checkpoints-every-50-VM-ops',
                'fd_limit': self.fd_limit, 'fd_census_coverage': 'bounded-census' if self.fd_limit else 'not-run',
                'aggregate_snapshot_atomicity': 'not-proven',
                'excluded_fds': len(self.excluded), 'temporal_file_coverage': 'sampled-lower-bound',
                'memory_temp_bytes': 'unmeasured', 'short_lived_between_samples': 'unknown',
                'lock_scope': 'flock-acquire-syscall-through-lock-fd-close-syscall',
                'lock_intervals_complete': bool(intervals) and not self.held
                    and all(event['release_after_ns'] is not None for event in intervals),
                'timing_includes_instrumentation': True, 'workload_upper_bound_proven': False,
                'production_qualified': False,
            },
        }
