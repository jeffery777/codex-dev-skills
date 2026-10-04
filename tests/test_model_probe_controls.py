"""Counterexamples for opt-in sandbox probe evidence, without a sandbox/model."""
import copy
import errno
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


class NativeNetworkControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('native_network_probe',
            pathlib.Path(__file__).resolve().parents[1] / 'scripts/verify-model-permissions.py')
        cls.probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.probe)

    def fixture(self, transport='tcp'):
        probe = self.probe
        return {'transport': transport, 'client_sha256': probe.hashlib.sha256(
                probe.NETWORK_CLIENT.encode()).hexdigest(),
            'positive_nonce_sha256': 'a' * 64, 'negative_nonce_sha256': 'b' * 64,
            'positive_filesystem_config_sha256': 'c' * 64,
            'negative_filesystem_config_sha256': 'c' * 64,
            'positive': {'started_at': 1.0, 'finished_at': 1.5, 'expires_at': 2.0,
                'returncode': 0, 'output': {'outcome': 'connected', 'ack_verified': True,
                    'nonce_sha256': 'a' * 64}},
            'negative': {'started_at': 3.0, 'finished_at': 3.5, 'expires_at': 4.0,
                'returncode': 0, 'output': {'outcome': 'denied',
                    'operation': 'sendto' if transport == 'udp' else 'connect',
                    'errno': errno.EPERM, 'ack_verified': False, 'nonce_sha256': 'b' * 64}},
            'listener': {'positive_nonce_count': 1, 'negative_nonce_count': 0,
                'negative_accept_count': 0, 'late_nonce_count': 0, 'unexpected_count': 0,
                'overflow': False, 'stopped': True, 'observed_until': 4.1}}

    def test_only_explicit_syscall_denials_after_positive_control_pass(self):
        for transport in ('tcp', 'udp', 'unix'):
            for value in (errno.EPERM, errno.EACCES):
                case = self.fixture(transport)
                case['negative']['output']['errno'] = value
                self.assertEqual(self.probe.evaluate_network_case(case), 'passed')
            for value in (errno.ECONNREFUSED, errno.ECONNRESET, errno.ETIMEDOUT, None, True):
                case = self.fixture(transport)
                case['negative']['output']['errno'] = value
                self.assertEqual(self.probe.evaluate_network_case(case), 'unknown')
            case = self.fixture(transport)
            case['negative']['output']['operation'] = 'receive'
            self.assertEqual(self.probe.evaluate_network_case(case), 'unknown')

    def test_received_negative_or_accepted_stream_is_a_counterexample(self):
        for transport in ('tcp', 'udp', 'unix'):
            case = self.fixture(transport)
            case['listener']['negative_nonce_count'] = 1
            self.assertEqual(self.probe.evaluate_network_case(case), 'failed')
        for transport in ('tcp', 'unix'):
            case = self.fixture(transport)
            case['listener']['negative_accept_count'] = 1
            case['negative']['output']['operation'] = 'receive'
            self.assertEqual(self.probe.evaluate_network_case(case), 'failed')

    def test_missing_duplicate_expired_or_unfinished_observations_are_unknown(self):
        changes = [
            (('listener', 'positive_nonce_count'), 0),
            (('listener', 'positive_nonce_count'), 2),
            (('listener', 'positive_nonce_count'), True),
            (('listener', 'late_nonce_count'), 1),
            (('listener', 'unexpected_count'), 1),
            (('listener', 'overflow'), True),
            (('listener', 'stopped'), False),
            (('listener', 'observed_until'), 3.9),
            (('listener', 'observed_until'), float('nan')),
            (('positive', 'finished_at'), 2.0),
            (('negative', 'finished_at'), 4.0),
            (('positive', 'returncode'), 1),
            (('negative', 'output', 'nonce_sha256'), 'a' * 64),
            (('negative_filesystem_config_sha256',), 'd' * 64),
            (('client_sha256',), 'e' * 64),
        ]
        for path, value in changes:
            case = self.fixture()
            field = case
            for key in path[:-1]:
                field = field[key]
            field[path[-1]] = value
            with self.subTest(path=path):
                self.assertEqual(self.probe.evaluate_network_case(case), 'unknown')
        case = self.fixture()
        del case['negative']
        self.assertEqual(self.probe.evaluate_network_case(case), 'unknown')

    def test_decisive_negative_receipts_survive_incomplete_observation(self):
        for transport in ('tcp', 'udp', 'unix'):
            counters = ['negative_nonce_count']
            if transport != 'udp':
                counters.append('negative_accept_count')
            for counter in counters:
                for key, value in [('observed_until', 3.8), ('observed_until', None),
                        ('observed_until', float('nan')), ('stopped', False),
                        ('late_nonce_count', 1), ('unexpected_count', 1), ('overflow', True)]:
                    case = self.fixture(transport)
                    case['listener'][counter] = 1
                    case['listener'][key] = value
                    with self.subTest(transport=transport, counter=counter, key=key):
                        self.assertEqual(self.probe.evaluate_network_case(case), 'failed')
                case = self.fixture(transport)
                case['listener'][counter] = 1
                del case['listener']['observed_until']
                self.assertEqual(self.probe.evaluate_network_case(case), 'failed')
                # Corrupt identity or an unverified positive control still
                # cannot establish which fixture the negative receipt proves.
                for path, value in [(('positive', 'returncode'), 1),
                        (('negative_nonce_sha256',), 'a' * 64),
                        (('listener', counter), True)]:
                    case = self.fixture(transport)
                    case['listener'][counter] = 1
                    field = case
                    for key in path[:-1]:
                        field = field[key]
                    field[path[-1]] = value
                    self.assertEqual(self.probe.evaluate_network_case(case), 'unknown')

    def test_sandbox_policy_changes_only_network_toggle(self):
        paths = [pathlib.Path('/private/tmp/network-control') / name
            for name in ('a', 'b', 'home', 'control')]
        command = ['/fixed/client', 'tcp', '12345', 'a' * 32, '4']
        positive = self.probe.sandbox_argv('/fixed/codex', *paths, command,
            network=True)
        negative = self.probe.sandbox_argv('/fixed/codex', *paths, command,
            network=False)
        self.assertEqual([i for i, values in enumerate(zip(positive, negative))
            if values[0] != values[1]], [9])
        self.assertEqual(positive[7], negative[7])

    def test_runner_preserves_confirmed_failure_when_listener_stop_is_unknown(self):
        # Inject host observations without starting a thread, socket or client.
        # Exercise the outer runner, including its evaluator and finally path.
        for observed, negative_received, identity_drift, expected in [
                (True, True, False, 'failed'),
                (True, False, False, 'unknown'),
                (False, True, False, 'failed'),
                (False, False, False, 'unknown'),
                (True, True, True, 'unknown')]:
            with self.subTest(observed=observed, negative_received=negative_received,
                    identity_drift=identity_drift):
                now, observers = [10.0], []
                binary = mock.MagicMock()
                binary.__str__.return_value = '/fixed/client'
                binary.read_bytes.side_effect = [b'fixed-client',
                    b'changed-client' if identity_drift else b'fixed-client']

                class LiveObserver:
                    def __init__(self, *, target, daemon):
                        closure = dict(zip(target.__code__.co_freevars,
                            (cell.cell_contents for cell in target.__closure__)))
                        self.state, self.phase = closure['state'], closure['phase']
                        observers.append(self)
                    def start(self):
                        pass
                    def join(self, *, timeout):
                        if observed:
                            self.state['observed_until'] = now[0]
                    def is_alive(self):
                        return True

                def run_client(argv, **kwargs):
                    observer = observers[-1]
                    negative = 'negative' in observer.phase
                    if negative:
                        observer.state['negative_nonce_count'] = int(negative_received)
                        observer.state['negative_accept_count'] = int(negative_received)
                    else:
                        observer.state['positive_nonce_count'] = 1
                    payload = {'outcome': 'connected', 'operation': 'receive',
                        'errno': 0, 'nonce': argv[-2], 'ack_verified': True}
                    return subprocess.CompletedProcess(argv, 0,
                        json.dumps(payload).encode(), b'')

                def advance(seconds):
                    now[0] += seconds

                listener = mock.MagicMock()
                listener.getsockname.return_value = ('127.0.0.1', 12345)
                paths = [pathlib.Path('/private/tmp/network-runner') / name
                    for name in ('a', 'b', 'home', 'control')]
                with mock.patch.object(self.probe, 'build_network_client', return_value=binary), \
                        mock.patch.object(self.probe.socket, 'socket', return_value=listener), \
                        mock.patch.object(self.probe.threading, 'Thread', LiveObserver), \
                        mock.patch.object(self.probe.subprocess, 'run', side_effect=run_client), \
                        mock.patch.object(self.probe.time, 'monotonic', side_effect=lambda: now[0]), \
                        mock.patch.object(self.probe.time, 'sleep', side_effect=advance):
                    cases = self.probe.native_network_controls('/fixed/codex', *paths, {})
                self.assertEqual(len(cases), 1)
                self.assertEqual(len(observers), 1)
                self.assertEqual(cases[0]['outcome'], expected)
                self.assertTrue(cases[0]['listener_lifecycle_unknown'])
                self.assertFalse(cases[0]['listener']['stopped'])
                self.assertEqual(cases[0]['client_identity_unchanged'], not identity_drift)
                self.assertEqual(cases[0]['listener']['negative_nonce_count'], int(negative_received))
                listener.close.assert_called_once()

    def test_non_system_library_or_missing_compiler_cannot_be_measured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with mock.patch.object(self.probe.shutil, 'which', return_value=None):
                with self.assertRaises(ValueError):
                    self.probe.build_network_client(root)
            def build_then_inventory(argv, **kwargs):
                if argv[0] == '/usr/bin/otool':
                    return subprocess.CompletedProcess(argv, 0,
                        'binary:\n\t/host/private/libfixture.dylib (compatibility version 1.0.0)\n', '')
                (root / 'network-client').write_bytes(b'fixed-client-fixture')
                return subprocess.CompletedProcess(argv, 0, b'', b'')
            with mock.patch.object(self.probe.sys, 'platform', 'darwin'), \
                    mock.patch.object(self.probe.shutil, 'which', return_value='/fixed/cc'), \
                    mock.patch.object(self.probe.subprocess, 'run', side_effect=build_then_inventory):
                with self.assertRaisesRegex(ValueError, 'non-system-client-library'):
                    self.probe.build_network_client(root)

    def test_unrestricted_real_clients_cannot_report_network_isolation(self):
        original_run = subprocess.run
        def without_sandbox(argv, **kwargs):
            command = argv[argv.index('--') + 1:] if '--' in argv else argv
            return original_run(command, **kwargs)
        with tempfile.TemporaryDirectory(prefix='native-network-', dir='/tmp') as directory:
            root = pathlib.Path(directory).resolve()
            paths = [root / name for name in ('a', 'b', 'home', 'control')]
            for path in paths:
                path.mkdir()
            with mock.patch.object(self.probe.subprocess, 'run', side_effect=without_sandbox):
                cases = self.probe.native_network_controls('/fixed/codex', *paths,
                    {'PATH': '/usr/bin:/bin', 'HOME': str(paths[2])})
            self.assertEqual([case['outcome'] for case in cases], ['failed'] * 3)
            self.assertTrue(all(case['listener']['negative_nonce_count'] == 1 for case in cases))


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

    def lifecycle_fixture(self, directory):
        root = pathlib.Path(directory)
        values = {'-ready.json': {'pid': 7, 'ppid': 1, 'sid': 6, 'parent_session': 1},
            '-done.json': dict(own_write=True, source_write_denied=True,
                checkpoint_write_denied=True, sibling_write_denied=True),
            '-limits.json': {'memory.max': '134217728', 'pids.max': '32', 'cpu.max': '100000 100000'},
            '-cgroup.json': {'membership': '0::/'}}
        for suffix, value in values.items():
            (root / ('cycle-1' + suffix)).write_text(json.dumps(value))
        (root / 'cycle-1-live').write_text('observed')
        (root / 'cycle-1-own').write_text('detached-positive')
        state = {'State': dict(Running=False, Status='exited', ExitCode=0, OOMKilled=False, Pid=0)}
        return root, state, values

    def test_detached_marker_cannot_replace_independent_runtime_process_inventory(self):
        active = {'State': {'Pid': 100}}
        self.assertEqual(self.probe.validate_lifecycle_top('PID PPID COMMAND\n100 20 python3\n101 100 python3', active),
            dict(init_host_pid=100, detached_host_pid=101))
        for raw in ['PID PPID COMMAND\n100 20 python3',
                'PID PPID COMMAND\n100 20 python3\n101 20 python3',
                'PID PPID COMMAND\n100 20 python3\n100 100 python3',
                'PID PPID COMMAND\n100 20 python3\n101 100 sh',
                'PID PPID COMMAND\n100 20 python3\n101 100 python3\n102 100 python3',
                'x' * 8193]:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                self.probe.validate_lifecycle_top(raw, active)

    def test_saved_inspect_preserves_validation_but_excludes_environment_and_diagnostics(self):
        workspace, expected, value = self.worker_fixture()
        value['Id'] = 'fixed-container'
        value['State'] = dict(Running=False, Status='exited', ExitCode=0, OOMKilled=False,
            Pid=0, StartedAt='synthetic-start', FinishedAt='synthetic-finish', Error='CREDENTIAL_SENTINEL')
        value['Config']['Env'] = ['CREDENTIAL_SENTINEL=excluded']
        value['Config']['Labels'] = {'private': 'CREDENTIAL_SENTINEL'}
        value['Config']['Healthcheck']['unneeded'] = 'CREDENTIAL_SENTINEL'
        value['LogPath'] = '/synthetic/CREDENTIAL_SENTINEL'
        value['HostConfig']['unneeded'] = 'CREDENTIAL_SENTINEL'
        value['Mounts'][0]['unneeded'] = 'CREDENTIAL_SENTINEL'
        saved = self.probe.inspect_evidence(value)
        self.assertNotIn('CREDENTIAL_SENTINEL', json.dumps(saved))
        self.assertNotIn('Env', saved['Config'])
        self.probe.validate_worker(saved, workspace, **expected)
        self.assertTrue(self.probe.stopped_successfully(saved))
        self.assertEqual(saved['Id'], value['Id'])

    def test_detached_positive_and_cgroup_readback_have_independent_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root, state, values = self.lifecycle_fixture(directory)
            result = self.probe.validate_lifecycle_cycle(root, 1, state)
            self.assertTrue(result['detached_identity']); self.assertEqual(result['resource_readback'], 'passed')
            for value in [None, '0::/unmatched']:
                (root / 'cycle-1-cgroup.json').write_text(json.dumps({'membership': value}))
                self.assertEqual(self.probe.validate_lifecycle_cycle(root, 1, state)['resource_readback'], 'unknown')
            (root / 'cycle-1-cgroup.json').write_text(json.dumps(values['-cgroup.json']))
            for value, expected in [(None, 'unknown'), ('64', 'failed')]:
                limits = dict(values['-limits.json'], **{'pids.max': value})
                (root / 'cycle-1-limits.json').write_text(json.dumps(limits))
                self.assertEqual(self.probe.validate_lifecycle_cycle(root, 1, state)['resource_readback'], expected)
            (root / 'cycle-1-limits.json').write_text(json.dumps(values['-limits.json']))
            self.assertEqual(self.probe.validate_lifecycle_cycle(root, 1, state,
                cpu_limit_unavailable=True)['resource_readback'], 'unknown')

    def test_detached_missing_attempts_or_non_detached_identity_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root, state, values = self.lifecycle_fixture(directory)
            for change in [{'ppid': 7}, {'sid': 1}]:
                (root / 'cycle-1-ready.json').write_text(json.dumps({**values['-ready.json'], **change}))
                self.assertFalse(self.probe.validate_lifecycle_cycle(root, 1, state)['detached_identity'])
            (root / 'cycle-1-ready.json').write_text(json.dumps(values['-ready.json']))
            done = dict(values['-done.json']); done.pop('source_write_denied')
            (root / 'cycle-1-done.json').write_text(json.dumps(done))
            with self.assertRaises(ValueError): self.probe.validate_lifecycle_cycle(root, 1, state)
            (root / 'cycle-1-done.json').write_text(json.dumps(values['-done.json']))
            (root / 'cycle-1-own').write_text('')
            self.assertFalse(self.probe.validate_lifecycle_cycle(root, 1, state)['detached_copy_written'])
            state['State']['Pid'] = 101
            self.assertFalse(self.probe.validate_lifecycle_cycle(root, 1, state)['container_exited'])


if __name__ == '__main__':
    unittest.main()
