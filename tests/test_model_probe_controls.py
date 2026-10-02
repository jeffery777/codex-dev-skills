"""Counterexamples for opt-in sandbox probe evidence, without a sandbox/model."""
import copy
import importlib.util
import fcntl
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


class ReaderControlTests(unittest.TestCase):
    def test_unavailable_reader_cannot_report_access_denied(self):
        for name in ['verify-model-permissions', 'verify-model-dispatch']:
            with self.subTest(probe=name), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                (root / 'reader-sentinel').write_text('reader-ok')
                (root / 'protected').write_text('synthetic')
                spec = importlib.util.spec_from_file_location(name, pathlib.Path(__file__).resolve().parents[1] / 'scripts' / (name + '.py'))
                probe = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(probe)
                missing = str(root / 'missing-reader')
                command = probe.reader_guard(missing) + 'if ' + shlex.quote(missing) + ' protected >/dev/null; then echo violation > violation; fi'
                result = subprocess.run(['/bin/sh', '-c', command], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 12)
                self.assertFalse((root / 'reader-verified').exists())
                self.assertFalse((root / 'violation').exists())
                # With a working reader and no isolation, the same probe must
                # observe the forbidden read, rather than falsely pass.
                result = subprocess.run(['/bin/sh', '-c', probe.reader_guard() + 'if /bin/cat protected >/dev/null; then echo violation > violation; fi'], cwd=root, capture_output=True)
                self.assertEqual(result.returncode, 0)
                self.assertTrue((root / 'reader-verified').exists())
                self.assertTrue((root / 'violation').exists())


class ContainerControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('isolation_probe', pathlib.Path(__file__).resolve().parents[1] / 'scripts/verify-model-isolation.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def test_image_cannot_supply_conflicting_or_unbounded_mounts(self):
        for volumes in [[], {str(i): {} for i in range(17)}, {'/': {}}, {'/workspace': {}},
                        {'/workspace/child': {}}, {'/tmp': {}}, {'/var/../workspace': {}},
                        {'/var:rw': {}}, {'relative': {}}, {42: {}}]:
            with self.subTest(volumes=volumes), self.assertRaises(ValueError):
                self.probe.validate_image_volumes(volumes)
        self.assertEqual(self.probe.validate_image_volumes(None), {})
        self.assertEqual(self.probe.validate_image_volumes({'/var/lib/postgresql/data': {}}), {'/var/lib/postgresql/data': {}})

    def test_mount_readback_rejects_other_writable_sources_and_image_volumes(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = pathlib.Path(directory).resolve()
            bind = {'Type': 'bind', 'Destination': '/workspace', 'Source': str(workspace),
                'RW': True, 'Propagation': 'rprivate'}
            self.probe.validate_mounts([bind], workspace)
            for mounts in [[], [bind, {'Type': 'volume'}], [bind, dict(bind)],
                           [dict(bind, Source='/')], [dict(bind, Destination='/control')],
                           [dict(bind, RW=False)], [dict(bind, Propagation='shared')],
                           [bind, {'Type': 'tmpfs', 'Destination': '/unrequested', 'RW': False}],
                           [bind, {'Type': 'npipe', 'Destination': '/socket'}], [None]]:
                with self.subTest(mounts=mounts), self.assertRaises(ValueError):
                    self.probe.validate_mounts(mounts, workspace)

    def worker_fixture(self):
        # Field shapes match the retained Docker inspect control, with portable
        # synthetic identities. No engine call or local evidence file is needed.
        workspace = pathlib.Path('/private/tmp/synthetic-isolation/worker')
        expected = {'image': 'sha256:' + 'a' * 64, 'script': 'printf synthetic',
            'volumes': {'/synthetic/image-volume': {}}}
        value = {'Image': expected['image'], 'Mounts': [{'Type': 'bind',
            'Source': str(workspace), 'Destination': '/workspace', 'RW': True, 'Propagation': 'rprivate'}],
            'Config': {'Image': expected['image'], 'Entrypoint': ['/bin/sh'],
                'Cmd': ['-c', expected['script']], 'Healthcheck': {'Test': ['NONE']}, 'User': '65534:65534'},
            'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
                'CapDrop': ['ALL'], 'CapAdd': None, 'SecurityOpt': ['no-new-privileges'],
                'PidsLimit': 32, 'Memory': 134217728, 'NanoCpus': 1000000000, 'CpuPeriod': 0, 'CpuQuota': 0,
                'Tmpfs': {'/tmp': 'rw,noexec,nosuid,nodev,size=8m',
                    '/synthetic/image-volume': 'ro,noexec,nosuid,nodev,size=1m'},
                'VolumesFrom': None, 'Devices': [], 'DeviceRequests': None, 'DeviceCgroupRules': None}}
        return workspace, expected, value

    def test_worker_policy_positive_control_and_each_field_drift(self):
        workspace, expected, value = self.worker_fixture()
        self.probe.validate_worker(value, workspace, **expected)
        for path, changed in [
                (('Image',), 'sha256:' + 'b' * 64),
                (('Config', 'Image'), 'mutable:tag'),
                (('Config', 'Entrypoint'), ['/bin/bash']),
                (('Config', 'Cmd'), ['-c', 'different-command']),
                (('Config', 'Healthcheck', 'Test'), ['CMD', '/bin/sh']),
                (('Config', 'User'), '0:0'),
                (('HostConfig', 'NetworkMode'), 'host'),
                (('HostConfig', 'ReadonlyRootfs'), False),
                (('HostConfig', 'Privileged'), True),
                (('HostConfig', 'CapDrop'), []),
                (('HostConfig', 'CapAdd'), ['SYS_ADMIN']),
                (('HostConfig', 'SecurityOpt'), []),
                (('HostConfig', 'SecurityOpt'), ['no-new-privileges', 'seccomp=unconfined']),
                (('HostConfig', 'PidsLimit'), 64),
                (('HostConfig', 'Memory'), 0),
                (('HostConfig', 'NanoCpus'), 0),
                (('HostConfig', 'NanoCpus'), 2000000000),
                (('HostConfig', 'CpuPeriod'), 100000),
                (('HostConfig', 'CpuQuota'), -1),
                (('HostConfig', 'Tmpfs', '/tmp'), 'rw,nosuid,nodev,size=8m'),
                (('HostConfig', 'Tmpfs', '/synthetic/image-volume'), 'rw,noexec,nosuid,nodev,size=1m'),
                (('HostConfig', 'Tmpfs', '/extra'), 'ro,noexec,nosuid,nodev,size=1m'),
                (('HostConfig', 'VolumesFrom'), ['other-container']),
                (('HostConfig', 'Devices'), [{'PathOnHost': '/dev/sda'}]),
                (('HostConfig', 'DeviceRequests'), [{'Count': -1}]),
                (('HostConfig', 'DeviceCgroupRules'), ['a *:* rwm'])]:
            altered = copy.deepcopy(value)
            parent = altered
            for key in path[:-1]:
                parent = parent[key]
            parent[path[-1]] = changed
            with self.subTest(path=path, changed=changed), self.assertRaises(ValueError):
                self.probe.validate_worker(altered, workspace, **expected)

    def test_cpu_exception_is_explicit_and_does_not_disable_other_checks(self):
        workspace, expected, value = self.worker_fixture()
        value['HostConfig']['NanoCpus'] = 0
        with self.assertRaises(ValueError):
            self.probe.validate_worker(value, workspace, **expected)
        self.probe.validate_worker(value, workspace, **expected, cpu_limit_unavailable=True)
        for field, changed in [('NanoCpus', False), ('CapDrop', []), ('SecurityOpt', [])]:
            altered = copy.deepcopy(value)
            altered['HostConfig'][field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.probe.validate_worker(altered, workspace, **expected, cpu_limit_unavailable=True)

    def test_mount_types_tmpfs_targets_and_access_must_match_launch(self):
        workspace, expected, value = self.worker_fixture()
        tmpfs = {'Type': 'tmpfs', 'Source': '', 'Destination': '/synthetic/image-volume', 'RW': False}
        value['Mounts'].append(tmpfs)
        self.probe.validate_worker(value, workspace, **expected)
        for extra in [dict(tmpfs, Destination='/extra', RW=rw) for rw in (True, False)] + [
                {'Type': 'bind', 'Source': '/control', 'Destination': '/control', 'RW': False},
                {'Type': 'volume', 'Source': 'image-volume', 'Destination': '/data'},
                dict(tmpfs)]:
            altered = copy.deepcopy(value)
            altered['Mounts'].append(extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.probe.validate_worker(altered, workspace, **expected)
        for change in [{'RW': True}, {'Type': 'image'}, {'Source': '/host'}]:
            altered = copy.deepcopy(value)
            altered['Mounts'][-1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.probe.validate_worker(altered, workspace, **expected)

    def test_missing_policy_fields_fail_closed(self):
        workspace, expected, value = self.worker_fixture()
        for key in ('CapDrop', 'CapAdd', 'SecurityOpt', 'NanoCpus', 'Tmpfs', 'Devices'):
            altered = copy.deepcopy(value)
            del altered['HostConfig'][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.probe.validate_worker(altered, workspace, **expected)

    def test_file_escape_probes_detect_exposed_targets_without_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            work = root / 'worker'
            work.mkdir()
            targets = {}
            for name in ('source', 'checkpoint', 'sibling'):
                folder = root / name
                folder.mkdir()
                targets[name] = folder / 'sentinel'
                targets[name].write_text(name)
            script = self.probe.filesystem_probe(work, targets, 64)
            result = subprocess.run(['/bin/sh', '-c', script], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = self.probe.read_probe_results(work / 'probe-results.tsv')
            for key in ('reader_positive', 'rename_positive', 'link_positive', 'symlink_positive'):
                self.assertEqual(observed[key], 'passed', key)
            # Unisolated accesses are real counterexamples, including rename,
            # hardlink, and symlink dereference of independently created files.
            for name in targets:
                for operation in ('read', 'write', 'rename', 'link', 'symlink'):
                    self.assertEqual(observed[name + '_' + operation], 'failed')

    def test_missing_probe_tool_leaves_negatives_unknown_and_preserves_targets(self):
        for missing in ('reader', 'mover', 'linker'):
            with self.subTest(tool=missing), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory).resolve()
                work = root / 'worker'
                work.mkdir()
                # A nonexistent target prevents this control test from changing
                # any protected artifact even when unrelated tools are working.
                targets = {'source': root / 'not-mounted/sentinel'}
                script = self.probe.filesystem_probe(work, targets, 64,
                    **{missing: str(root / 'unavailable-tool')})
                result = subprocess.run(['/bin/sh', '-c', script], capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                observed = self.probe.read_probe_results(work / 'probe-results.tsv')
                cases = {'reader': ['source_read', 'source_write', 'source_rename', 'source_link', 'source_symlink'],
                    'mover': ['source_rename'], 'linker': ['source_link', 'source_symlink']}[missing]
                for key in cases:
                    self.assertEqual(observed[key], 'unknown', key)
                self.assertFalse(targets['source'].exists())

    def test_trusted_launcher_closes_a_real_inheritable_host_descriptor(self):
        with tempfile.TemporaryFile() as stream:
            stream.write(b'synthetic-descriptor')
            stream.flush()
            fd = fcntl.fcntl(stream.fileno(), fcntl.F_DUPFD, 64)
            try:
                os.set_inheritable(fd, True)
                os.lseek(fd, 0, os.SEEK_SET)
                self.assertEqual(os.read(fd, 64), b'synthetic-descriptor')
                script = ('import os, errno\ntry:\n os.fstat(' + str(fd)
                    + ')\n print("forwarded")\nexcept OSError as error:\n'
                    ' print("closed" if error.errno == errno.EBADF else "unknown")\n')
                self.assertEqual(self.probe.run_command([sys.executable, '-c', script]), 'closed')
                self.assertEqual(os.fstat(fd).st_size, len(b'synthetic-descriptor'))
            finally:
                os.close(fd)

    def test_partial_or_ambiguous_result_artifacts_cannot_become_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'results'
            self.assertEqual(set(self.probe.read_probe_results(path).values()), {'unknown'})
            path.write_text('reader_positive\tpassed\n')
            self.assertEqual(self.probe.read_probe_results(path)['source_read'], 'unknown')
            for text in ['source_read\tpassed\nsource_read\tfailed\n', 'foreign\tpassed\n',
                    'source_read\tyes\n', 'source_read\tpassed\textra\n']:
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValueError):
                    self.probe.read_probe_results(path)

    def test_zero_exit_status_does_not_prove_container_stopped(self):
        state = {'Running': False, 'Status': 'exited', 'ExitCode': 0, 'OOMKilled': False}
        self.assertTrue(self.probe.stopped_successfully({'State': state}))
        for change in [{'Running': True}, {'Status': 'running'}, {'ExitCode': 1}, {'OOMKilled': True}]:
            with self.subTest(change=change):
                self.assertFalse(self.probe.stopped_successfully({'State': {**state, **change}}))

    def test_unavailable_engine_retains_unknown_preflight_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            argv = ['verify-model-isolation.py', '--engine', 'docker', '--image', 'synthetic',
                '--evidence-root', directory]
            output = io.StringIO()
            with mock.patch.object(sys, 'argv', argv), mock.patch.object(sys, 'stdout', output), \
                    mock.patch.object(self.probe.shutil, 'which', return_value='/synthetic/docker'), \
                    mock.patch.object(self.probe, 'run_command', side_effect=FileNotFoundError):
                self.assertEqual(self.probe.main(), 2)
            summary = json.loads(output.getvalue())
            receipt = json.loads(pathlib.Path(summary['evidence']).read_text())
            self.assertEqual(receipt['execution_outcome'], 'unknown')
            self.assertEqual(receipt['containers_retained'], [])
            self.assertEqual(set(receipt['probe_results'].values()), {'unknown'})
            self.assertFalse(receipt['production_qualified'])


if __name__ == '__main__':
    unittest.main()
