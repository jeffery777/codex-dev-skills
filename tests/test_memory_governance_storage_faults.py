from __future__ import annotations

import contextlib
import copy
import errno
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

from tests.test_memory_governance_core import c, db, GovernanceCore
from tests.test_memory_governance_local import local_fixture

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/memory-governance'


def load(name):
    spec = importlib.util.spec_from_file_location(name, FIXTURES / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


case = load('storage_fault_case')
observer_module = load('storage_observer')
image_fixture = load('enospc_image')


class StorageFaultTests(unittest.TestCase):
    def run_case(self, fault):
        with tempfile.TemporaryDirectory(prefix='mg1-253-test-') as temporary:
            return case.run_case(Path(temporary).resolve(), fault)

    def assert_fresh_read(self, value):
        self.assertEqual(0, value['returncode'], value['diagnostic'])
        self.assertIs(False, value['timed_out'])
        self.assertTrue(value['files_unchanged'])
        self.assertTrue(value['new_process'])
        self.assertEqual('handle-unrecognized-or-consumed', value['observation']['replay_rejection'])
        self.assertNotIn('accept', value['observation']['calls'])

    def test_page_quota_full_preserves_revision_projection_and_proof_after_reopen(self):
        report = self.run_case('page-quota')
        self.assertEqual('observed', report['status'], report.get('incomplete_reason'))
        self.assertEqual('page-quota-sqlite-full', report['classification'])
        self.assertEqual([{'code': 13, 'method': 'execute', 'name': 'SQLITE_FULL'}], report['completed']['errors'])
        self.assertTrue(report['failed_transaction_unchanged'])
        self.assert_fresh_read(report['fresh_attempt'])
        self.assert_fresh_read(report['fresh_normal'])
        value = report['fresh_attempt']['observation']['result']
        self.assertEqual('state-unknown', value['result'], 'ID-only absence is never not-applied')
        self.assertIsNone(value['proof'])
        self.assertEqual('not-applied', report['completed']['outcome']['result'], 'in-process preview proves before state')
        self.assertEqual(1, report['fresh_normal']['observation']['result']['proof']['after_revision'])
        control = report['recovery_control']
        self.assertTrue(control['new_preview_and_confirmation'])
        self.assert_fresh_read(control['fresh_read'])
        self.assertNotEqual(report['prepared']['operation_id'], control['observation']['result']['operation_id'])
        self.assertEqual(2, control['observation']['result']['proof']['after_revision'])

    def test_actual_cantopen_is_a_separate_missing_path_control(self):
        report = self.run_case('missing-path-cantopen')
        self.assertEqual('observed', report['status'], report.get('incomplete_reason'))
        self.assertEqual('sqlite-cantopen', report['classification'])
        self.assertEqual([{'code': 14, 'method': 'connect', 'name': 'SQLITE_CANTOPEN'}], report['completed']['errors'])
        self.assertTrue(report['failed_transaction_unchanged'])
        self.assertFalse(report['completed']['filling'])
        self.assertFalse(report['production_qualified'])

    def test_reply_loss_never_turns_enospc_exception_into_not_applied(self):
        report = self.run_case('reply-loss')
        self.assertEqual('observed', report['status'], report.get('incomplete_reason'))
        self.assertEqual('injected-enospc-reply-loss', report['classification'])
        self.assertTrue(report['committed_transaction_consistent'])
        self.assertEqual('applied', report['completed']['outcome']['result'])
        self.assertEqual('applied', report['fresh_attempt']['observation']['result']['result'])
        self.assertEqual('state-unknown', report['fresh_normal']['observation']['result']['result'])
        self.assert_fresh_read(report['fresh_attempt'])
        self.assert_fresh_read(report['fresh_normal'])

    def test_normal_control_measures_growth_journal_and_whole_lock_intervals(self):
        report = self.run_case('none')
        self.assertEqual('observed', report['status'], report.get('incomplete_reason'))
        self.assertTrue(report['committed_transaction_consistent'])
        measurement = report['completed']['measurement']
        self.assertGreater(measurement['main_growth_observed_bytes'], 0)
        self.assertGreater(measurement['measured_maxima']['journal_bytes'], 0)
        self.assertIn('managed/managed.sqlite3-journal', measurement['named_files_seen'])
        self.assertEqual([], measurement['sample_errors'])
        self.assertTrue(measurement['coverage']['lock_intervals_complete'])
        exclusive = [entry for entry in measurement['lock_intervals'] if entry['exclusive']]
        self.assertEqual(2, len(exclusive))
        for entry in measurement['lock_intervals']:
            self.assertLessEqual(entry['acquire_before_ns'], entry['acquire_after_ns'])
            self.assertLess(entry['acquire_after_ns'], entry['release_before_ns'])
            self.assertLessEqual(entry['release_before_ns'], entry['release_after_ns'])
            self.assertGreater(entry['held_ns_lower'], 0)
            self.assertGreaterEqual(entry['held_ns_upper'], entry['held_ns_lower'])
        self.assertFalse(measurement['coverage']['workload_upper_bound_proven'])

    def test_process_loss_preserves_nonempty_journal_and_refuses_repair(self):
        report = self.run_case('precommit-loss')
        self.assertEqual(73, report['writer']['returncode'])
        self.assertEqual('incomplete', report['status'])
        self.assertTrue(report['journal_requires_maintenance'])
        self.assertIn('G2-maintenance-required', report['incomplete_reason'])
        self.assertFalse(report['failed_transaction_unchanged'])
        self.assertNotIn('recovery_control', report)
        for value in (report['fresh_attempt'], report['fresh_normal']):
            self.assert_fresh_read(value)
            self.assertEqual([], value['observation']['connections'], 'nonempty journal must block before DB open')
            self.assertEqual('recovery-required', value['observation']['audit']['reason'])
            self.assertEqual('state-unknown', value['observation']['result']['result'])
            self.assertIsNone(value['observation']['result']['state_digest'])

    def test_classification_never_substitutes_cantopen_quota_or_injected_errors(self):
        completed = {'errors': [{'code': 13}], 'quota': {
            'page_count_before': 12, 'profile_max_page_count': 1048576, 'effective_max_page_count': 1048576},
            'filling': {'os_enospc_observed': True}}
        self.assertEqual('physical-sqlite-full', case.classify('physical', completed))
        for field in ('page_count_before', 'effective_max_page_count', 'profile_max_page_count'):
            for value in (None, True, False, 0, -1, '12'):
                with self.subTest(field=field, value=value):
                    changed = copy.deepcopy(completed)
                    changed['quota'][field] = value
                    self.assertEqual('sqlite-full-origin-unproven', case.classify('physical', changed))
            changed = copy.deepcopy(completed)
            del changed['quota'][field]
            self.assertEqual('sqlite-full-origin-unproven', case.classify('physical', changed))
        changed = copy.deepcopy(completed)
        changed['quota']['effective_max_page_count'] = 12
        self.assertEqual('sqlite-full-origin-unproven', case.classify('physical', changed))
        self.assertEqual('page-quota-sqlite-full', case.classify('page-quota', changed))
        for quota in ({}, {'page_count_before': None, 'effective_max_page_count': None},
                      {'page_count_before': True, 'effective_max_page_count': True, 'profile_max_page_count': 1048576},
                      {'page_count_before': 12, 'effective_max_page_count': 12, 'profile_max_page_count': 12}):
            with self.subTest(quota=quota):
                unproven = {**changed, 'quota': quota}
                self.assertEqual('sqlite-full-origin-unproven', case.classify('page-quota', unproven))
        changed = copy.deepcopy(completed)
        changed['errors'] = [{'code': 14}]
        self.assertEqual('sqlite-cantopen', case.classify('physical', changed))
        changed['errors'] = []
        self.assertEqual('os-enospc-only', case.classify('physical', changed))
        changed['filling'] = {'injected_errno': 28}
        self.assertEqual('injected-enospc-reply-loss', case.classify('physical', changed))

    def test_valid_read_event_cannot_hide_abnormal_exit_or_timeout(self):
        original = case.fresh_read
        for position in (0, 1, 2):
            for failure in ({'returncode': 73}, {'returncode': 0, 'timed_out': True}):
                with self.subTest(position=position, failure=failure):
                    calls = []
                    def incomplete_reader(*args):
                        value = original(*args)
                        self.assert_fresh_read(value)
                        if len(calls) == position:
                            value.update(failure)
                        calls.append(value)
                        return value
                    with mock.patch.object(case, 'fresh_read', side_effect=incomplete_reader):
                        report = self.run_case('page-quota')
                    self.assertEqual('incomplete', report['status'])
                    self.assertEqual('recovery-control-readback-unproven' if position == 2 else
                                     'fresh-readback-incomplete-or-mutated', report['incomplete_reason'])
                    self.assertIsNotNone(calls[position]['observation'])

    def test_cli_preserves_incomplete_journal_after_process_exit(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-cli-test-') as temporary:
            owner = Path(temporary).resolve()
            child = subprocess.run([str(ROOT / 'scripts/project-python'), str(FIXTURES / 'storage_fault_case.py'),
                                    '--fault', 'precommit-loss'], cwd=ROOT, capture_output=True, timeout=30,
                                   env={**os.environ, 'TMPDIR': str(owner), 'PYTHONDONTWRITEBYTECODE': '1'})
            self.assertEqual(2, child.returncode, child.stderr.decode())
            report = json.loads(child.stdout)
            retained = Path(report['retained_fixture'])
            self.assertEqual(owner, retained.parent)
            self.assertEqual('incomplete', report['status'])
            self.assertGreater((retained / 'managed' / db.JOURNAL).stat().st_size, 0)
            self.assertEqual(report, json.loads((retained / 'observation.json').read_text()))
            self.assertTrue(report['fresh_attempt']['files_unchanged'])


class MeasurementBoundaryTests(unittest.TestCase):
    def test_lock_measurement_encloses_entry_and_exit_inventory(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-lock-') as temporary:
            parent = Path(temporary).resolve()
            root, temp = parent / 'managed', parent / 'temp'
            root.mkdir(mode=0o700); temp.mkdir(mode=0o700)
            ports = local_fixture.SyntheticLocalPorts(root)
            GovernanceCore(ports.host, enabled=True).initialize()
            binding = ports.registry.binding()
            observer = observer_module.StorageObserver(root, temp, binding)
            original_inventory, original_flock, original_close = db.inventory, db.fcntl.flock, db.os.close
            held_inventory = []

            def inventory(*args, **kwargs):
                value = original_inventory(*args, **kwargs)
                if observer.held:
                    competing = os.open(root / db.LOCK, os.O_RDONLY)
                    try:
                        with self.assertRaises(BlockingIOError):
                            original_flock(competing, db.fcntl.LOCK_EX | db.fcntl.LOCK_NB)
                    finally:
                        original_close(competing)
                    held_inventory.append(time.monotonic_ns() - observer.origin_ns)
                    time.sleep(0.005)
                return value

            with observer.observing(), mock.patch.object(db, 'inventory', side_effect=inventory):
                with db.locked(binding, exclusive=True):
                    pass
            interval, = observer.report()['lock_intervals']
            self.assertEqual(2, len(held_inventory), 'both entry and exit inventory must be covered')
            self.assertLess(interval['acquire_after_ns'], held_inventory[0])
            self.assertLess(held_inventory[-1], interval['release_before_ns'])
            self.assertGreaterEqual(interval['held_ns_lower'], 10_000_000)

    def test_sampler_accounts_for_named_sidecars_and_unlinked_own_fd(self):
        program = """
import json, os, tempfile
from pathlib import Path
from storage_observer import StorageObserver, bound_worker_descriptors
from local_ports import SyntheticLocalPorts
from memory_governance_core import GovernanceCore
limit = bound_worker_descriptors()
with tempfile.TemporaryDirectory(prefix='mg1-253-fd-') as temporary:
    parent = Path(temporary).resolve()
    root, temp = parent/'managed', parent/'temp'
    root.mkdir(mode=0o700); temp.mkdir(mode=0o700)
    ports = SyntheticLocalPorts(root)
    GovernanceCore(ports.host, enabled=True).initialize()
    (root/'managed.sqlite3-wal').write_bytes(b'w'*17)
    (root/'managed.sqlite3-shm').write_bytes(b's'*23)
    (temp/'named-temp').write_bytes(b't'*31)
    fd = os.open(temp/'unlinked-temp', os.O_CREAT|os.O_EXCL|os.O_RDWR, 0o600)
    os.write(fd, b'u'*47)
    os.unlink(temp/'unlinked-temp')
    observer = StorageObserver(root, temp, ports.registry.binding(), fd_limit=limit)
    observer.sample()
    print(json.dumps(observer.report()))
    os.close(fd)
"""
        child = subprocess.run([str(ROOT / 'scripts/project-python'), '-c', program], cwd=ROOT,
                               env={**os.environ, 'PYTHONPATH': str(FIXTURES) + os.pathsep
                                    + str(ROOT / 'skills/loop-engineering/scripts'), 'PYTHONDONTWRITEBYTECODE': '1'},
                               capture_output=True, timeout=15)
        self.assertEqual(0, child.returncode, child.stderr.decode())
        report = json.loads(child.stdout)
        peaks = report['measured_maxima']
        self.assertEqual((17, 23, 31, 47), tuple(peaks[key] for key in
                         ('wal_bytes', 'shm_bytes', 'named_temp_bytes', 'unlinked_fd_bytes')))
        self.assertEqual(peaks['main_bytes'] + 17 + 23 + 31 + 47, peaks['sampled_unique_file_bytes'])
        self.assertEqual('not-proven', report['coverage']['aggregate_snapshot_atomicity'])
        self.assertEqual('unknown', report['coverage']['short_lived_between_samples'])


class ImageSafetyTests(unittest.TestCase):
    def test_dry_run_cannot_create_or_attach(self):
        with mock.patch.object(image_fixture, 'command', side_effect=AssertionError('dry run command')), \
             mock.patch.object(image_fixture.tempfile, 'mkdtemp', side_effect=AssertionError('dry run mkdir')), \
             mock.patch('sys.argv', ['enospc_image.py']), contextlib.redirect_stdout(__import__('io').StringIO()) as output:
            self.assertEqual(0, image_fixture.main())
        report = json.loads(output.getvalue())
        self.assertEqual(268435456, report['image_bytes'])
        self.assertEqual(1073741824, report['host_headroom_minimum'])
        self.assertEqual(1, report['attempt_limit'])
        self.assertFalse(report['existing_data_access'])

    def test_mount_requires_independent_device_exact_node_and_capacity(self):
        parent, mount = Path('/synthetic-parent'), Path('/synthetic-parent/volume')
        attached = {'system-entities': [{'mount-point': str(mount), 'dev-entry': '/dev/disk99s1'}]}
        info = {'DeviceNode': '/dev/disk99s1', 'MountPoint': str(mount),
                'FilesystemType': 'apfs', 'TotalSize': 268435456}
        def stat(path, *args, **kwargs):
            return SimpleNamespace(st_dev=2 if path == mount else 1, st_ino=7)
        with mock.patch.object(Path, 'stat', stat), mock.patch.object(Path, 'is_symlink', return_value=False), \
             mock.patch.object(os.path, 'ismount', return_value=True):
            self.assertEqual(((2, 7), '/dev/disk99s1'), image_fixture.confirm_mount(parent, mount, attached, info))
            for changed in ({'DeviceNode': '/dev/disk1'}, {'TotalSize': 268435457}, {'TotalSize': True},
                            {'FilesystemType': 'hfs'}, {'MountPoint': '/another'}):
                with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                    image_fixture.confirm_mount(parent, mount, attached, {**info, **changed})
            with mock.patch.object(Path, 'stat', return_value=SimpleNamespace(st_dev=1, st_ino=7)), \
                 self.assertRaisesRegex(RuntimeError, 'mount-identity-unconfirmed'):
                image_fixture.confirm_mount(parent, mount, attached, info)

    def test_unknown_attach_preserves_report_and_never_detaches(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-attach-') as temporary:
            parent = Path(temporary).resolve()
            calls = []
            def command(*args):
                calls.append(args[:2])
                if args[1] == 'create':
                    Path(args[-1]).write_bytes(b'synthetic-image-marker')
                    return b''
                raise subprocess.TimeoutExpired(args, 60)
            with mock.patch.object(image_fixture.sys, 'platform', 'darwin'), \
                 mock.patch.object(image_fixture.tempfile, 'mkdtemp', return_value=str(parent)), \
                 mock.patch.object(image_fixture, 'available', return_value=2 * 1024**3), \
                 mock.patch.object(image_fixture, 'command', side_effect=command), \
                 mock.patch.object(image_fixture, 'run_case', side_effect=AssertionError('unconfirmed mount')):
                report = image_fixture.run()
            self.assertEqual('incomplete', report['status'])
            self.assertEqual('unknown', report['attachment_state'])
            self.assertIn('no unverified detach', report['recovery_required'])
            self.assertEqual(['create', 'attach'], [entry[1] for entry in calls])
            self.assertTrue((parent / 'observation.json').is_file())
            self.assertTrue((parent / 'synthetic.dmg').is_file())

    def test_failed_normal_detach_keeps_incomplete_even_with_successful_case(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-detach-') as temporary:
            parent = Path(temporary).resolve()
            mount = parent / 'volume'
            mount.mkdir()
            def command(*args):
                if args[1] == 'create':
                    Path(args[-1]).write_bytes(b'synthetic-image-marker')
                    return b''
                if args[1] == 'attach':
                    return plistlib.dumps({})
                if args[1] == 'info':
                    return plistlib.dumps({'FilesystemType': 'apfs', 'TotalSize': 268435456})
                raise subprocess.CalledProcessError(1, args, stderr=b'synthetic busy')
            with mock.patch.object(image_fixture.sys, 'platform', 'darwin'), \
                 mock.patch.object(image_fixture.tempfile, 'mkdtemp', return_value=str(parent)), \
                 mock.patch.object(image_fixture, 'available', return_value=2 * 1024**3), \
                 mock.patch.object(image_fixture, 'confirm_mount', return_value=(db.identity(mount.stat()), '/dev/disk99s1')), \
                 mock.patch.object(os.path, 'ismount', return_value=True), \
                 mock.patch.object(image_fixture, 'command', side_effect=command) as calls, \
                 mock.patch.object(image_fixture, 'run_case', return_value={'status': 'observed'}), \
                 mock.patch.object(image_fixture, 'bounded_restore', return_value={'result': 'restored'}):
                report = image_fixture.run()
            self.assertFalse(report['detached'])
            self.assertEqual('incomplete', report['status'])
            self.assertIn('no-force-used', report['detach_failure'])
            detach = [entry for entry in calls.call_args_list if entry.args[1] == 'detach']
            self.assertEqual(1, len(detach))
            self.assertNotIn('-force', detach[0].args)

    def test_filler_identity_drift_refuses_truncate(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-restore-') as temporary:
            mount = Path(temporary)
            with (mount / 'filler').open('xb') as filler:
                identity = db.identity(os.fstat(filler.fileno()))
                with mock.patch.object(os.path, 'ismount', return_value=True), \
                     mock.patch.object(os, 'ftruncate', side_effect=AssertionError('must not truncate')):
                    result = image_fixture.restore_filler(filler.fileno(), (identity[0], identity[1] + 1),
                                                          mount, db.identity(mount.stat()))
                self.assertEqual('refused', result['result'])

    def test_restoration_enospc_is_incomplete_without_retry_or_repair(self):
        with tempfile.TemporaryDirectory(prefix='mg1-253-restore-') as temporary:
            mount = Path(temporary)
            with (mount / 'filler').open('xb') as filler:
                identity = db.identity(os.fstat(filler.fileno()))
                with mock.patch.object(os.path, 'ismount', return_value=True), \
                     mock.patch.object(os, 'ftruncate', side_effect=OSError(errno.ENOSPC, 'synthetic')) as truncate:
                    result = image_fixture.restore_filler(filler.fileno(), identity, mount, db.identity(mount.stat()))
                self.assertEqual({'result': 'failed', 'operation': 'truncate-own-filler', 'errno': 28}, result)
                truncate.assert_called_once_with(filler.fileno(), 0)


if __name__ == '__main__':
    unittest.main()
