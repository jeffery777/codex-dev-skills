"""Offline pressure/restore controls. Never creates an image or exhausts a filesystem."""
import contextlib
import copy
import errno
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest import mock

from tests import test_memory_governance_storage_faults as storage_tests
from tests.test_memory_governance_storage_faults import (
    GovernanceCore, c, case, db, image_fixture, local_fixture,
    mocked_physical, observer_module, worker_fixture)


@contextlib.contextmanager
def ordinary_pool(parent, count=3):
    with contextlib.ExitStack() as stack:
        pool = []
        for index in range(count):
            stream = stack.enter_context((parent / ('filler-' + str(index))).open('xb+'))
            os.fchmod(stream.fileno(), 0o600)
            stream.write(b'x' * 512)
            stream.flush()
            pool.append({'fd': stream.fileno(), 'identity': list(db.identity(os.fstat(stream.fileno())))})
        yield {'fillers': pool, 'mount': str(parent), 'mount_identity': list(db.identity(parent.stat())),
               'parent_device': parent.stat().st_dev + 1}


class PressurePoolTests(unittest.TestCase):
    def exercise(self, failure):
        with tempfile.TemporaryDirectory() as temporary:
            return storage_tests.FillerSyncTests().observe(Path(temporary).resolve(), failure)

    def test_short_writes_advance_real_eof_and_share_total_bytes(self):
        result = self.exercise('all-progress')
        self.assertIsNone(result['error'])
        value = result['observation']
        self.assertTrue(value['pressure_ready'])
        self.assertEqual(1024 + 3 * 128, value['written_bytes'])
        stages = value['stages']
        self.assertEqual([0, 1024, 0, 0], [stage['offset_before'] for stage in stages])
        self.assertEqual([1024, 1152, 128, 128], [stage['next_offset'] for stage in stages])
        self.assertEqual([1] * 4, [stage['short_writes'] for stage in stages])
        self.assertEqual(['enospc'] * 4, [stage['stop'] for stage in stages])
        self.assertEqual(['succeeded'] * 4, [stage['sync']['result'] for stage in stages])
        final = value['pressure_samples']['small_2_after_sync']['files']
        self.assertEqual([1152, 128, 128], [entry['logical_bytes'] for entry in final])

    def test_prior_enospc_never_substitutes_for_final_stage_or_budget(self):
        for failure, reason in (('byte-cap', 'byte-budget-exhausted'),
                                ('after-tail-cap', 'byte-budget-exhausted'),
                                ('final-budget', 'final-probe-not-exhausted'),
                                ('write-attempt-cap', 'write-attempt-limit')):
            with self.subTest(failure=failure):
                result = self.exercise(failure)
                self.assertIn(reason, result['error']['reason'])
                self.assertFalse(result['observation']['pressure_ready'])
                self.assertLessEqual(result['observation']['written_bytes'], result['observation']['byte_limit'])
                self.assertLessEqual(result['observation']['write_attempts'], result['observation']['write_attempt_limit'])
                if failure != 'byte-cap':
                    self.assertTrue(result['observation']['os_enospc_observed'])

    def test_tail_errors_and_drift_stop_remaining_stages(self):
        for failure in ('tail-eio', 'tail-sync', 'size-drift', 'supplemental-identity-drift'):
            with self.subTest(failure=failure):
                result = self.exercise(failure)
                self.assertIsNotNone(result['error'])
                self.assertFalse(result['observation']['pressure_ready'])
                self.assertNotIn('small_2_after_sync', result['observation']['pressure_samples'])
                self.assertEqual([0.0, 0.0], result['timer'])

    def test_progress_is_fixed_size_even_at_maximum_write_count(self):
        result = self.exercise('all-progress')
        frames = []
        for value in result['events']:
            value['write_attempts'] = 70000
            for stage in value['stages']:
                stage.update(write_attempts=70000, short_writes=70000)
            frames.append(c.canonical({'event': 'filling', 'observation': value}) + b'\n')
        self.assertEqual(9, len(frames))
        # Reserve most of the existing worker envelope for prepared/completed/readback data.
        self.assertLess(sum(map(len, frames)), c.MAX_ENVELOPE // 4)
        with tempfile.TemporaryDirectory() as temporary:
            child = storage_tests.PhysicalTimingTests().observe_worker(Path(temporary).resolve(), None, [])
        completed = child['events'][-1]
        completed['filling'] = result['observation']
        self.assertLess(sum(map(len, frames)) + sum(len(c.canonical(event)) + 1 for event in child['events']),
                        c.MAX_ENVELOPE)

    def test_descriptor_shape_rejects_duplicates_and_incomplete_pressure(self):
        valid = mocked_physical()
        for change in ('duplicate-fd', 'duplicate-identity', 'boolean-fd', 'too-many', 'missing'):
            with self.subTest(change=change):
                value = copy.deepcopy(valid)
                if change == 'duplicate-fd':
                    value['fillers'][1]['fd'] = value['fillers'][0]['fd']
                elif change == 'duplicate-identity':
                    value['fillers'][1]['identity'] = value['fillers'][0]['identity']
                elif change == 'boolean-fd':
                    value['fillers'][0]['fd'] = True
                elif change == 'too-many':
                    value['fillers'].append({'fd': 124, 'identity': [1, 124]})
                else:
                    value['fillers'].pop()
                with self.assertRaises(c.ContractError):
                    worker_fixture.pressure.entries(value, complete=True)
        valid['fillers'] = valid['fillers'][:1]
        self.assertEqual(1, len(worker_fixture.pressure.entries(valid)))

    def test_coordinator_passes_all_filler_descriptors_and_recovers_after_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            restored = mock.Mock(return_value={'result': 'unproven'})
            with mock.patch.object(case, 'worker', return_value={'events': [], 'returncode': 1}) as child:
                report = case.run_case(Path(temporary).resolve(), 'physical', physical=mocked_physical(), recover=restored)
            self.assertEqual((125, 126, 127), child.call_args.kwargs['pass_fds'])
            restored.assert_called_once_with()
            self.assertNotIn('fresh_attempt', report)

    def test_observer_excludes_every_filler_descriptor(self):
        # Keep the process-wide fd bound in a fresh worker, like the real fixture.
        program = """
import json
from tests.test_memory_governance_pressure_pool import PressurePoolTests
print(json.dumps(PressurePoolTests().observe_filler_descriptors()))
"""
        child = subprocess.run([str(storage_tests.ROOT / 'scripts/project-python'), '-c', program],
                               cwd=storage_tests.ROOT, capture_output=True, text=True, timeout=5)
        self.assertEqual(0, child.returncode, child.stderr)
        measured = json.loads(child.stdout)
        self.assertEqual(1536, measured['included'] - measured['excluded'])
        self.assertEqual(0, measured['excluded'])

    def observe_filler_descriptors(self):
        limit = observer_module.bound_worker_descriptors()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root, temp = parent / 'managed', parent / 'temp'
            root.mkdir(mode=0o700)
            temp.mkdir(mode=0o700)
            ports = local_fixture.SyntheticLocalPorts(root)
            GovernanceCore(ports.host, enabled=True).initialize()
            with ordinary_pool(parent) as physical:
                measured = {}
                for name, excluded in (('included', ()),
                        ('excluded', worker_fixture.pressure.descriptors(physical))):
                    observer = observer_module.StorageObserver(root, temp, ports.registry.binding(),
                        fd_limit=limit, excluded=excluded)
                    observer.sample()
                    self.assertEqual([], observer.errors)
                    measured[name] = observer.report()['measured_maxima']['other_fd_bytes']
                return measured

    def test_pool_restoration_uses_aggregate_capacity_and_empty_allocations(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            with ordinary_pool(parent) as physical, mock.patch.object(os.path, 'ismount', return_value=True), \
                 mock.patch.object(image_fixture, 'available', side_effect=[100, 100, 100, 100, 100, 100, 100, 200]):
                report = image_fixture.restore_pool(physical)
                self.assertEqual('restored', report['result'])
                self.assertTrue(report['final_files_verified_empty'])
                self.assertEqual(1536, report['released_logical_bytes'])
                self.assertTrue(all(os.fstat(entry['fd']).st_size == 0 for entry in physical['fillers']))

    def test_restoration_failure_does_not_skip_other_safe_members(self):
        for failure in ('identity', 'truncate', 'sync', 'no-capacity-increase'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary).resolve()
                with ordinary_pool(parent) as physical:
                    target = physical['fillers'][1]['fd']
                    if failure == 'identity':
                        physical['fillers'][1]['identity'][1] = max(e['identity'][1] for e in physical['fillers']) + 100
                    original_truncate, original_sync = os.ftruncate, os.fsync
                    calls = []
                    def truncate(fd, length):
                        calls.append(fd)
                        if failure == 'truncate' and fd == target:
                            raise OSError(errno.EIO, 'synthetic')
                        return original_truncate(fd, length)
                    def sync(fd):
                        if failure == 'sync' and fd == target:
                            raise OSError(errno.EIO, 'synthetic')
                        return original_sync(fd)
                    with mock.patch.object(os.path, 'ismount', return_value=True), \
                         mock.patch.object(image_fixture, 'available', return_value=100), \
                         mock.patch.object(os, 'ftruncate', side_effect=truncate), \
                         mock.patch.object(os, 'fsync', side_effect=sync):
                        report = image_fixture.restore_pool(physical)
                    self.assertEqual('unproven', report['result'])
                    self.assertIn(physical['fillers'][0]['fd'], calls)
                    self.assertIn(physical['fillers'][2]['fd'], calls)
                    if failure == 'identity':
                        self.assertNotIn(target, calls)

    def test_mount_drift_refuses_every_truncate(self):
        with tempfile.TemporaryDirectory() as temporary:
            with ordinary_pool(Path(temporary).resolve()) as physical, \
                 mock.patch.object(os.path, 'ismount', return_value=False), \
                 mock.patch.object(os, 'ftruncate', side_effect=AssertionError('unsafe truncate')):
                self.assertEqual('refused', image_fixture.restore_pool(physical)['result'])

    def test_partial_creation_recovers_only_bound_subset_and_closes_every_open_fd(self):
        for failed_index, identity_failure in ((1, False), (2, False), (1, True)):
            with self.subTest(index=failed_index, identity=identity_failure), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary).resolve()
                mount = parent / 'volume'
                actual_open, actual_close = os.open, os.close
                opened, closed, restored, commands = [], [], [], []
                def command(*args):
                    commands.append(args[1])
                    if args[1] == 'create':
                        Path(args[-1]).write_bytes(b'fixture')
                    elif args[1] == 'attach':
                        mount.mkdir()
                    return plistlib.dumps({'FilesystemType': 'apfs', 'TotalSize': 268435456})
                def open_file(path, *args, **kwargs):
                    if str(path).endswith('synthetic-filler-' + str(failed_index)) and not identity_failure:
                        raise OSError(errno.EIO, 'synthetic open failure')
                    fd = actual_open(path, *args, **kwargs)
                    opened.append(fd)
                    return fd
                def owned(data, entry):
                    if identity_failure and len(opened) == failed_index + 1:
                        raise RuntimeError('synthetic identity failure')
                    return os.fstat(entry['fd'])
                def close(fd):
                    closed.append(fd)
                    actual_close(fd)
                def restore(data):
                    restored.append(copy.deepcopy(data))
                    return {'result': 'restored'}
                with mock.patch.object(image_fixture, 'preflight', return_value={'status': 'ready'}), \
                     mock.patch.object(image_fixture.tempfile, 'mkdtemp', return_value=str(parent)), \
                     mock.patch.object(image_fixture, 'available', return_value=2 * 1024**3), \
                     mock.patch.object(image_fixture, 'confirm_mount', side_effect=lambda *args: (db.identity(mount.stat()), '/dev/disk99s1')), \
                     mock.patch.object(image_fixture, 'confirm_image_attachment'), \
                     mock.patch.object(image_fixture, 'command', side_effect=command), \
                     mock.patch.object(image_fixture.pressure, 'owned', side_effect=owned), \
                     mock.patch.object(os.path, 'ismount', side_effect=lambda _: 'detach' not in commands), \
                     mock.patch.object(os, 'open', side_effect=open_file), \
                     mock.patch.object(os, 'close', side_effect=close), \
                     mock.patch.object(image_fixture, 'bounded_restore', side_effect=restore), \
                     mock.patch.object(image_fixture, 'run_case', side_effect=AssertionError('partial pool started target')):
                    report = image_fixture.run()
                self.assertEqual('incomplete', report['status'])
                self.assertEqual('filler-create', report['failure_stage'])
                self.assertEqual(1, len(restored))
                self.assertEqual(failed_index, len(restored[0]['fillers']))
                self.assertEqual(opened, closed)
                self.assertTrue(report['detached'])
