#!/usr/bin/env python3
"""Repository-only synthetic G1 observations. Never creates a qualification record.

Uses only fresh test-owned roots. Does not accept an existing memory database or
read native memory. Values are observations of a small workload, not upper bounds.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import platform
import plistlib
import subprocess
import sys
import tempfile
import time
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(ROOT / 'tests/fixtures/memory-governance')]
import memory_governance_contract as c
from memory_governance_core import GovernanceCore
import memory_governance_storage as db
from local_ports import SyntheticLocalPorts


def filesystem_observation(root):
    """只回傳 filesystem 類型；probe 失敗保留 unavailable，不猜測。"""
    try:
        if sys.platform == 'darwin':
            output = subprocess.run(['/bin/df', '-P', str(root)], check=True, capture_output=True, timeout=5)
            mountpoint = output.stdout.decode().splitlines()[-1].split(maxsplit=5)[-1]
            output = subprocess.run(['/usr/sbin/diskutil', 'info', '-plist', mountpoint],
                                    check=True, capture_output=True, timeout=5)
            info = plistlib.loads(output.stdout)
            value = info.get('FilesystemType')
            if not value:
                raise ValueError('filesystem-unavailable')
            return {'status': 'observed', 'type': value, 'method': 'df-mountpoint/diskutil-info'}
        output = subprocess.run(['stat', '-f', '-c', '%T', str(root)], check=True, capture_output=True, timeout=5)
        return {'status': 'observed', 'type': output.stdout.decode().strip(), 'method': 'stat-filesystem-type'}
    except (OSError, ValueError, subprocess.SubprocessError, plistlib.InvalidFileException):
        return {'status': 'unavailable', 'type': None, 'method': 'native-filesystem-probe'}


def evaluate():
    with tempfile.TemporaryDirectory(prefix='mg1-g1-observation-') as temporary:
        parent = Path(temporary).resolve()
        root, temp = parent / 'managed', parent / 'sqlite-temp'
        root.mkdir(mode=0o700)
        temp.mkdir(mode=0o700)
        ports = SyntheticLocalPorts(root)
        core = GovernanceCore(ports.host, enabled=True)
        core.initialize()
        item_id = '00000000-0000-4000-8000-000000000003'
        operations, samples, lock_times = [], [], []
        peaks = {key: 0 for key in ('main_bytes', 'journal_bytes', 'temp_bytes', 'managed_bytes', 'total_bytes')}
        sample_count = 0
        observed_names = set()
        locked_original, connect_original = db.locked, db.connect

        def sample():
            nonlocal sample_count
            sizes = {}
            for path in root.iterdir():
                try:
                    sizes[path.name] = path.stat().st_size
                except FileNotFoundError:
                    continue
            entries = list(temp.iterdir())
            if len(sizes) > 32 or len(entries) > 32:
                raise RuntimeError('synthetic-inventory-limit')
            temp_bytes = sum(path.stat().st_size for path in entries)
            observed_names.update(sizes)
            current = {'main_bytes': sizes.get(db.MAIN, 0), 'journal_bytes': sizes.get(db.JOURNAL, 0),
                       'temp_bytes': temp_bytes, 'managed_bytes': sum(sizes.values()),
                       'total_bytes': sum(sizes.values()) + temp_bytes}
            for key, value in current.items():
                peaks[key] = max(peaks[key], value)
            sample_count += 1
            return 0

        @contextlib.contextmanager
        def timed_lock(binding, *, exclusive=False):
            with locked_original(binding, exclusive=exclusive) as directory:
                start = time.monotonic_ns()
                try:
                    yield directory
                finally:
                    if exclusive:
                        lock_times.append(time.monotonic_ns() - start)

        def connect(*args, **kwargs):
            connection = connect_original(*args, **kwargs)
            if kwargs.get('writer'):
                connection.set_progress_handler(sample, 50)
            return connection

        def checkpoint(stage):
            sample()
            samples.append(stage)

        def apply(operation, candidate=None, **kw):
            start = time.monotonic_ns()
            preview = core.preview(operation, item_id, candidate, **kw)
            preview_ns = time.monotonic_ns() - start
            handle = core.authorize(preview)
            start = time.monotonic_ns()
            result = core.execute(handle)
            execute_ns = time.monotonic_ns() - start
            if result['result'] != 'applied':
                raise RuntimeError('synthetic-operation-not-applied: ' + result['result'])
            operations.append({'operation': operation, 'revision': result['proof']['after_revision'],
                               'preview_ns': preview_ns, 'execute_and_readback_ns': execute_ns,
                               'exclusive_lock_ns': lock_times[-1], 'managed_bytes': result['storage']['managed_bytes'],
                               'candidate_bytes': len(c.canonical(candidate)) if candidate else 0})
            return preview, result

        with mock.patch.dict(os.environ, {'SQLITE_TMPDIR': str(temp), 'TMPDIR': str(temp)}), \
             mock.patch.object(db, 'locked', side_effect=timed_lock), \
             mock.patch.object(db, 'connect', side_effect=connect), \
             mock.patch('memory_governance_core._checkpoint', side_effect=checkpoint):
            first = ports.candidate(body='Synthetic capacity fixture. ' * 470)
            apply('add', first)
            apply('update', ports.candidate(2, cue='green', body='Synthetic second revision. ' * 470))
            apply('stop')
            apply('update', ports.candidate(3, cue='red', body='Synthetic stopped revision. ' * 470))
            restored = copy.deepcopy(first)
            restored.update(revision=4, created_at=ports.clock_port.clock().utc_seconds)
            restored['validation'].update(content_digest=c.content_digest(restored), evidence_id='synthetic-restore',
                                          verified_at=restored['created_at'])
            ports.approve(restored)
            apply('restore', restored, restore_revision=1)
            apply('resume')
            for revision in range(5, 11):
                apply('update', ports.candidate(revision, body='Synthetic bounded retained version. ' * 370))
            with core.audit() as audit:
                page = audit.page()
            sample()
        with contextlib.closing(db.connect(ports.registry.binding(), c.DEFAULT_PROFILE)) as connection:
            page_count = connection.execute('PRAGMA page_count').fetchone()[0]
            free_pages = connection.execute('PRAGMA freelist_count').fetchone()[0]
        runtime = db.runtime_facts()
        return {'contract_version': 'mg1-g1-local-observation/v0', 'synthetic_only': True,
                'production_qualified': False, 'human_confirmation_proven': False,
                'source_review_proven': False, 'runtime': runtime,
                'runtime_digest': c.digest(runtime), 'machine_architecture': platform.machine(),
                'filesystem': filesystem_observation(root), 'profile_digest': c.digest(c.DEFAULT_PROFILE),
                'workload': {'items': 1, 'retained_versions': page['items'][0]['retained_versions'],
                             'proofs': len(operations), 'data_limit_bytes': c.DEFAULT_PROFILE['data_limit_bytes']},
                'operations': operations, 'observed_peaks': peaks, 'sample_count': sample_count,
                'sampling': {'method': 'named-files-at-checkpoints-and-every-50-SQLite-VM-operations',
                             'checkpoint_stages': sorted(set(samples)),
                             'managed_names': sorted(observed_names), 'bound_proven': False,
                             'temp_coverage': 'test-owned-directory-only', 'external_temp_coverage': 'unknown',
                             'lock_timing_scope': 'context-body-only',
                             'timing_includes_instrumentation': True},
                'final_pages': {'page_size': 4096, 'page_count': page_count, 'freelist_count': free_pages},
                'not_covered': ['production-authority', 'production-source-reader', 'human-decision-attestation',
                                'complete-temp-envelope', 'true-J-T-G-upper-bounds', '4-GiB-worst-case-lock-time',
                                'maintenance-reserve', 'power-loss', 'physical-ENOSPC', 'G2']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Create a NEW JSON observation file; never overwrite.')
    args = parser.parse_args()
    data = json.dumps(evaluate(), indent=2, sort_keys=True) + '\n'
    if args.output is None:
        print(data, end='')
    else:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(data)


if __name__ == '__main__':
    main()
