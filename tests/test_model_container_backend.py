"""Reconstructable fake-daemon tests; no live Docker or provider access."""
import ast
import copy
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_packet_store as packets
import model_packet_supervisor as supervisors
import model_container_backend as containers

IMAGE = 'sha256:'+'a'*64


class FakeDocker:
    """Daemon identities/objects survive a fresh transport and backend object."""
    executable_sha256 = 'b'*64
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.create_fault = self.start_fault = None
        self.before_start = None
        self.daemon = 'c'*64
        self.drift = None

    def identity(self):
        return self.daemon

    def image(self, image):
        return {'Id': image, 'Os': 'linux', 'Architecture': 'arm64', 'Config': {'Env': ['PATH=/usr/local/bin:/usr/bin:/bin']}}

    def inspect(self, cid):
        value = json.loads((self.root/(cid+'.json')).read_bytes())
        if self.drift:
            self.drift(value)
        return value

    def _write(self, cid, value):
        path = self.root/(cid+'.json')
        with path.open('w') as stream:
            json.dump(value, stream); stream.flush(); os.fsync(stream.fileno())

    def command(self, *argv):
        self.calls.append(argv)
        if argv[:2] == ('container', 'create'):
            options = list(argv)
            def option(name):
                return options[options.index(name)+1]
            name = option('--name'); workspace = pathlib.Path(option('--mount').split('src=')[1].split(',')[0])
            cid = packets.digest(name.encode())
            labels = {options[index+1].split('=', 1)[0]: options[index+1].split('=', 1)[1]
                      for index, value in enumerate(options) if value == '--label'}
            value = {'Id': cid, 'Name': '/'+name, 'Created': '2026-10-02T00:00:00.000000000Z',
                'Image': IMAGE, 'RestartCount': 0,
                'Config': {'Image': IMAGE, 'Labels': labels, 'Entrypoint': ['/usr/local/bin/python3'],
                    'Cmd': options[-3:], 'User': '65534:65534', 'WorkingDir': '/workspace',
                    'Healthcheck': {'Test': ['NONE']}, 'Env': ['HOME=/tmp', 'PATH=/usr/local/bin:/usr/bin:/bin'],
                    'OpenStdin': False, 'Tty': False},
                'Mounts': [{'Type': 'bind', 'Source': str(workspace), 'Destination': '/workspace',
                            'RW': True, 'Propagation': 'rprivate'}],
                'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
                    'CapDrop': ['ALL'], 'CapAdd': None, 'SecurityOpt': ['no-new-privileges'], 'PidsLimit': 32,
                    'Memory': 134217728, 'MemorySwap': 134217728, 'NanoCpus': 1000000000, 'CpuPeriod': 0,
                    'CpuQuota': 0, 'Tmpfs': {'/tmp': 'rw,noexec,nosuid,nodev,size=8m'},
                    'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}, 'AutoRemove': False,
                    'VolumesFrom': None, 'Devices': [], 'DeviceRequests': None, 'DeviceCgroupRules': None,
                    'PortBindings': {}, 'PidMode': '', 'IpcMode': 'private', 'CgroupnsMode': 'private',
                    'UTSMode': '', 'UsernsMode': '', 'PublishAllPorts': False, 'GroupAdd': None, 'ExtraHosts': None,
                    'Binds': None, 'Links': None},
                'State': {'Running': False, 'Status': 'created', 'Restarting': False, 'Dead': False, 'Paused': False,
                    'Pid': 0, 'ExitCode': 0, 'OOMKilled': False, 'StartedAt': '0001-01-01T00:00:00Z',
                    'FinishedAt': '0001-01-01T00:00:00Z'}}
            if (self.root/(cid+'.json')).exists():
                raise AssertionError('duplicate create')
            self._write(cid, value)
            if self.create_fault:
                raise self.create_fault
            return cid.encode()
        if argv[:2] == ('container', 'start'):
            cid = argv[2]; value = self.inspect(cid)
            if self.before_start:
                self.before_start(cid, value)
            workspace = pathlib.Path(value['Mounts'][0]['Source'])
            script = value['Config']['Cmd'][-1]
            if script == containers.WORKERS['edit']:
                (workspace/'example.txt').write_text('new\n')
                (workspace/'added.txt').write_text('added\n')
                (workspace/'remove.txt').unlink(missing_ok=True)
            elif script == containers.WORKERS['background']:
                (workspace/'example.txt').write_text('background\n')
                (workspace/'background-started.txt').write_text('active\n')
            value['State'].update(Status='exited', Running=False,
                StartedAt='2026-10-02T00:01:00.000000000Z', FinishedAt='2026-10-02T00:01:01.000000000Z')
            self._write(cid, value)
            if self.start_fault:
                raise self.start_fault
            return cid.encode()
        raise AssertionError('unexpected Docker operation: '+str(argv))


class ExportContractFakeBackend(containers.SyntheticContainerBackend):
    """Offline exporter double only; no real Docker execution qualification.

    Supplies the independently trusted proof needed to exercise seal/fence
    mechanics. The actual shared-daemon backend always returns unknown.
    """
    def inspect(self, binding, descriptor):
        result = super().inspect(binding, descriptor)
        observed = self._observed(binding, descriptor)
        state = observed['State']
        if (state['Status'] == 'exited' and state['Running'] is False and state['Restarting'] is False
                and state['Paused'] is False and state['Dead'] is False and type(state['Pid']) is int
                and state['Pid'] == 0 and type(observed['RestartCount']) is int
                and observed['RestartCount'] == 0 and state['StartedAt'] != '0001-01-01T00:00:00Z'
                and state['FinishedAt'] != '0001-01-01T00:00:00Z'):
            result['state'] = 'stopped'
        return result


class _ContainerFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve(); self.root.chmod(0o700)
        self.store = packets.PacketStore(self.root, 'packet'); self.store.prepare('d'*64)
        self.engine = FakeDocker(self.root)
        self.backend = self.new_backend()
        self.supervisor = self.new_supervisor(self.backend)

    def new_backend(self, engine=None, worker='edit'):
        return ExportContractFakeBackend(self.store, endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE, worker=worker, opt_in=True, _engine=engine or self.engine)

    def new_supervisor(self, backend):
        return supervisors.PacketSupervisor(self.store, backend, host_id=backend.host_id,
            backend_id=backend.backend_id, policy_sha256=backend.policy_sha256)

    def start(self, supervisor=None, attempt='attempt', revision=0):
        return (supervisor or self.supervisor).start(attempt, 'e'*64, 'f'*64, expected_revision=revision,
            source_sha256=containers.source_digest(), scope_sha256='1'*64, acceptance_sha256='2'*64)

    def record(self):
        return self.store.supervisor_snapshot('attempt')[1]

    def descriptor(self):
        return self.store.read_runtime_descriptor('attempt')

    def assert_unknown(self, result):
        self.assertEqual(result['outcome'], 'unknown')
        self.assertIsNone(self.store.supervisor_snapshot('attempt')[0]['checkpoint'])



class ContainerBackendTests(_ContainerFixture):
    def test_daemon_never_bootstraps_original_execution_proof(self):
        backend = containers.SyntheticContainerBackend(self.store, endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE, opt_in=True, _engine=self.engine)
        self.assert_unknown(self.start(self.new_supervisor(backend)))
        binding, descriptor = self.record()['binding'], self.descriptor()
        self.assertEqual(backend.inspect(binding, descriptor)['state'], 'unknown')
        with self.assertRaisesRegex(packets.PacketError, 'not-stopped'):
            backend.export_patch(binding, packets.MAX_PATCH, descriptor)
        fresh = FakeDocker(self.root)
        backend = containers.SyntheticContainerBackend(self.store, endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE, opt_in=True, _engine=fresh)
        self.assert_unknown(self.new_supervisor(backend).reconcile('attempt'))
        self.assertEqual(fresh.calls, [])

    def test_lost_reply_then_manual_same_cid_restart_before_first_inspect_is_unknown(self):
        backend = containers.SyntheticContainerBackend(self.store, endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE, opt_in=True, _engine=self.engine)
        self.engine.start_fault = OSError('lost first start reply')
        self.assert_unknown(self.start(self.new_supervisor(backend)))
        descriptor = self.descriptor(); value = self.engine.inspect(descriptor['container_id'])
        value['State']['StartedAt'] = '2026-10-02T00:02:00Z'
        value['RestartCount'] = 0
        self.engine._write(descriptor['container_id'], value)
        fresh = FakeDocker(self.root)
        backend = containers.SyntheticContainerBackend(self.store, endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE, opt_in=True, _engine=fresh)
        self.assert_unknown(self.new_supervisor(backend).reconcile('attempt'))
        self.assertEqual(fresh.calls, [])
        self.assertEqual(self.record()['observations'][0]['reason'], 'launch-reply-unknown')

    def test_transport_revalidates_executable_for_every_operation(self):
        executable = self.root/'fake-docker'
        script = '#!/bin/sh\nexit 0\n'
        for argv in [('info',), ('image', 'inspect', IMAGE), ('container', 'inspect', 'a'*64),
                     ('container', 'create'), ('container', 'start', 'a'*64)]:
            for mutation in ['replace', 'content', 'mode', 'symlink', 'fifo']:
                with self.subTest(argv=argv, mutation=mutation):
                    if executable.exists() or executable.is_symlink():
                        executable.unlink()
                    executable.write_text(script); executable.chmod(0o700)
                    with mock.patch.object(containers.shutil, 'which', return_value=str(executable)):
                        transport = containers.LocalDocker('unix:///synthetic/docker.sock', self.root)
                    self.assertEqual(transport.command(*argv), b'')
                    if mutation == 'replace':
                        replacement = self.root/'replacement'; replacement.write_text(script); replacement.chmod(0o700)
                        replacement.replace(executable)
                    elif mutation == 'content':
                        executable.write_text(script+'# changed\n')
                    elif mutation == 'mode':
                        executable.chmod(0o777)
                    elif mutation == 'fifo':
                        executable.unlink(); os.mkfifo(executable, 0o600)
                    else:
                        executable.unlink(); executable.symlink_to('/bin/sh')
                    with mock.patch.object(containers.subprocess, 'Popen', side_effect=AssertionError('must not execute')):
                        with self.assertRaises((packets.PacketError, OSError)):
                            transport.command(*argv)

    def test_huge_replacement_rejected_before_content_hash(self):
        executable=self.root/'fake-docker'; executable.write_text('#!/bin/sh\nexit 0\n'); executable.chmod(0o700)
        with mock.patch.object(containers.shutil,'which',return_value=str(executable)):
            transport=containers.LocalDocker('unix:///synthetic/docker.sock',self.root)
        with executable.open('r+b') as stream: stream.truncate(1024*1024*1024)
        with mock.patch.object(containers.hashlib,'file_digest',side_effect=AssertionError('must not hash replacement')):
            with self.assertRaises(packets.PacketError): transport.command('info')

    def test_binary_transport_preserves_bytes_and_bounds_input(self):
        executable=self.root/'fake-docker'; executable.write_text('#!/bin/sh\ncat\n'); executable.chmod(0o700)
        with mock.patch.object(containers.shutil,'which',return_value=str(executable)):
            transport=containers.LocalDocker('unix:///synthetic/docker.sock',self.root)
        raw=b'\x00 archive \n\x00'
        self.assertEqual(transport.archive('fixture',input_bytes=raw),raw)
        with self.assertRaisesRegex(packets.PacketError,'input-bound'):
            transport.archive('fixture',input_bytes=b'x'*(containers.MAX_ENGINE_OUTPUT+1))

    def test_fixed_recipes_and_nested_child_source_are_valid_python(self):
        for name, script in containers.WORKERS.items():
            with self.subTest(worker=name):
                compile(script, '<fixed-worker>', 'exec')
        parsed = ast.parse(containers.WORKERS['background'])
        calls = [node for node in ast.walk(parsed) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute) and node.func.attr == 'Popen']
        self.assertEqual(len(calls), 1)
        child = ast.literal_eval(calls[0].args[0].elts[-1])
        self.assertEqual(child, containers.BACKGROUND_CHILD)
        compile(child, '<fixed-background-child>', 'exec')

    def test_descriptor_is_same_ledger_durable_before_exact_start(self):
        def before(cid, _):
            value = json.loads((self.root/'packet/ledger.json').read_bytes())
            record = value['supervisors']['attempt']
            self.assertEqual(record['schema_version'], 3)
            self.assertEqual(record['stage'], 'launch-intent')
            raw = (self.root/'packet'/('runtime-'+record['runtime_descriptor_sha256']+'.json')).read_bytes()
            self.assertEqual(packets.digest(raw), record['runtime_descriptor_sha256'])
            self.assertEqual(json.loads(raw)['container_id'], cid)
        self.engine.before_start = before
        candidate = self.start()
        self.assertEqual(candidate['outcome'], 'integration-candidate')
        self.assertIn(b'+new', candidate['patch']); self.assertIn(b'new file mode', candidate['patch'])
        self.assertIn(b'deleted file mode', candidate['patch'])
        self.assertEqual([call[:2] for call in self.engine.calls], [('container', 'create'), ('container', 'start')])

    def test_reconstructed_backend_never_create_start_or_export_worker_git(self):
        candidate = self.start(); fresh = FakeDocker(self.root)
        result = self.new_supervisor(self.new_backend(fresh)).reconcile('attempt')
        self.assertEqual(result, candidate); self.assertEqual(fresh.calls, [])

    def test_lost_create_reply_is_unknown_without_descriptor_or_start_on_reconcile(self):
        self.engine.create_fault = OSError('lost create')
        self.assert_unknown(self.start())
        self.assertIsNone(self.record()['runtime_descriptor_sha256'])
        fresh = FakeDocker(self.root)
        self.assert_unknown(self.new_supervisor(self.new_backend(fresh)).reconcile('attempt'))
        self.assertEqual(fresh.calls, [])
        self.assertEqual(len(list(self.root.glob('*.json'))), 1)
        self.assertEqual(self.record()['observations'][0]['reason'], 'prepare-reply-unknown')

    def test_crash_after_create_before_descriptor_never_recreates_or_starts(self):
        self.engine.create_fault = SystemExit('crash')
        with self.assertRaises(SystemExit):
            self.start()
        fresh = FakeDocker(self.root)
        self.assert_unknown(self.new_supervisor(self.new_backend(fresh)).reconcile('attempt'))
        self.assertEqual(fresh.calls, [])

    def test_descriptor_commit_crash_does_not_start(self):
        original = self.store._write
        def crash(fd, value):
            record = value.get('supervisors', {}).get('attempt', {})
            if record.get('runtime_descriptor_sha256'):
                raise SystemExit('before descriptor ledger commit')
            return original(fd, value)
        with mock.patch.object(self.store, '_write', side_effect=crash):
            with self.assertRaises(SystemExit):
                self.start()
        self.assertEqual([call[:2] for call in self.engine.calls], [('container', 'create')])
        self.assert_unknown(self.new_supervisor(self.new_backend(FakeDocker(self.root))).reconcile('attempt'))

    def test_crash_after_descriptor_commit_before_start_preserves_exact_id(self):
        original = self.store._write
        def crash(fd, value):
            original(fd, value)
            record = value.get('supervisors', {}).get('attempt', {})
            if record.get('runtime_descriptor_sha256'):
                raise SystemExit('after descriptor ledger commit')
        with mock.patch.object(self.store, '_write', side_effect=crash):
            with self.assertRaises(SystemExit):
                self.start()
        cid = self.descriptor()['container_id']
        fresh = FakeDocker(self.root)
        self.assert_unknown(self.new_supervisor(self.new_backend(fresh)).reconcile('attempt'))
        self.assertEqual(self.descriptor()['container_id'], cid)
        self.assertEqual(fresh.calls, [])

    def test_crash_after_actual_start_reconciles_without_second_start(self):
        self.engine.start_fault = SystemExit('after actual start')
        with self.assertRaises(SystemExit):
            self.start()
        fresh = FakeDocker(self.root)
        self.assertEqual(self.new_supervisor(self.new_backend(fresh)).reconcile('attempt')['outcome'], 'integration-candidate')
        self.assertEqual(fresh.calls, [])

    def test_created_container_after_descriptor_commit_is_not_stopped_or_started_on_restart(self):
        with mock.patch.object(self.backend, 'launch', side_effect=SystemExit('before start')):
            with self.assertRaises(SystemExit):
                self.start()
        fresh = FakeDocker(self.root)
        self.assert_unknown(self.new_supervisor(self.new_backend(fresh)).reconcile('attempt'))
        self.assertEqual(fresh.calls, [])
        self.assertEqual(self.engine.inspect(self.descriptor()['container_id'])['State']['Status'], 'created')

    def test_lost_start_reply_recovers_original_exact_physical_id_once(self):
        self.engine.start_fault = OSError('lost start')
        self.assert_unknown(self.start()); cid = self.descriptor()['container_id']
        fresh = FakeDocker(self.root)
        result = self.new_supervisor(self.new_backend(fresh)).reconcile('attempt')
        self.assertEqual(result['outcome'], 'integration-candidate'); self.assertEqual(self.descriptor()['container_id'], cid)
        self.assertEqual(fresh.calls, [])
        self.assertEqual(self.record()['observations'][0]['reason'], 'launch-reply-unknown')
        self.assertEqual(self.record()['observations'][-1]['kind'], 'resolved')

    def test_lost_export_reply_reads_backend_seal_without_second_export(self):
        original = self.backend.export_patch
        def lost(*args):
            original(*args)
            raise OSError('lost seal response')
        with mock.patch.object(self.backend, 'export_patch', side_effect=lost):
            self.assert_unknown(self.start())
        fresh_backend = self.new_backend(FakeDocker(self.root))
        with mock.patch.object(fresh_backend, 'export_patch', side_effect=AssertionError('second export')):
            self.assertEqual(self.new_supervisor(fresh_backend).reconcile('attempt')['outcome'], 'integration-candidate')

    def test_running_missing_and_physical_identity_drift_never_publish(self):
        self.engine.start_fault = OSError('lost reply'); self.start()
        cid = self.descriptor()['container_id']; original = self.engine.inspect(cid)
        for transform in [lambda v: v['State'].update(Running=True, Status='running', Pid=55),
                          lambda v: v.update(Id='0'*64), lambda v: v.update(Created='2026-10-01T00:00:00Z')]:
            value = copy.deepcopy(original); transform(value); self.engine._write(cid, value)
            self.assert_unknown(self.supervisor.reconcile('attempt'))
        (self.root/(cid+'.json')).unlink()
        self.assert_unknown(self.supervisor.reconcile('attempt'))
        self.assertEqual(len(self.engine.calls), 2)

    def test_daemon_and_descriptor_artifact_drift_rejected(self):
        self.start(); self.engine.daemon = '0'*64
        with self.assertRaises(packets.PacketError):
            self.supervisor.reconcile('attempt')
        self.engine.daemon = 'c'*64
        path = self.root/'packet'/('runtime-'+self.record()['runtime_descriptor_sha256']+'.json')
        path.write_bytes(b'{}')
        with self.assertRaises(packets.PacketError):
            self.supervisor.reconcile('attempt')

    def test_restart_same_physical_id_startedat_change_rejected(self):
        self.start(); cid = self.descriptor()['container_id']
        value = self.engine.inspect(cid); value['State']['StartedAt'] = '2026-10-02T00:02:00Z'
        self.engine._write(cid, value)
        with self.assertRaises(packets.PacketError):
            self.supervisor.reconcile('attempt')

    def test_noop_empty_patch_and_predecessor_restore(self):
        backend = self.new_backend(worker='noop'); supervisor = self.new_supervisor(backend)
        first = self.start(supervisor); self.assertEqual(first['patch'], b'')
        ledger = self.store.supervisor_snapshot('attempt')[0]
        result = self.start(supervisor, 'next', ledger['revision'])
        self.assertEqual(result['patch'], b'')
        self.assertEqual(result['binding']['predecessor_sha256'], first['checkpoint_sha256'])

    def test_checkpoint_patch_remains_cumulative_across_predecessor_restore(self):
        first = self.start()
        revision = self.store.supervisor_snapshot('attempt')[0]['revision']
        second = self.start(attempt='second', revision=revision)
        self.assertEqual(second['patch'], first['patch'])
        revision = self.store.supervisor_snapshot('second')[0]['revision']
        noop = self.new_backend(worker='noop')
        third = self.start(self.new_supervisor(noop), 'third', revision)
        self.assertEqual(third['patch'], first['patch'])
        self.assertEqual(third['binding']['predecessor_sha256'], second['checkpoint_sha256'])

    def test_policy_drift_each_relevant_boundary_is_rejected(self):
        self.start(); observed = self.engine.inspect(self.descriptor()['container_id'])
        changes = [('Image', None, 'sha256:'+'0'*64), ('Name', None, '/other'),
            ('Config', 'Entrypoint', ['/bin/sh']), ('Config', 'Cmd', ['evil']), ('Config', 'Env', ['AUTH=secret']),
            ('Config', 'Labels', {}), ('Config', 'User', '0'), ('Config', 'WorkingDir', '/'),
            ('Config', 'Healthcheck', {'Test': ['CMD','evil']}), ('Config', 'OpenStdin', True), ('Config', 'Tty', True),
            ('HostConfig', 'NetworkMode', 'host'), ('HostConfig', 'ReadonlyRootfs', False),
            ('HostConfig', 'Privileged', True), ('HostConfig', 'CapAdd', ['SYS_ADMIN']), ('HostConfig', 'CapDrop', []),
            ('HostConfig', 'SecurityOpt', []), ('HostConfig', 'PidsLimit', 0), ('HostConfig', 'Memory', 0),
            ('HostConfig', 'MemorySwap', -1), ('HostConfig', 'NanoCpus', 0), ('HostConfig', 'CpuQuota', 1),
            ('HostConfig', 'Tmpfs', {}), ('HostConfig', 'VolumesFrom', ['other']), ('HostConfig', 'Devices', [{}]),
            ('HostConfig', 'DeviceRequests', [{}]), ('HostConfig', 'DeviceCgroupRules', ['allow']),
            ('HostConfig', 'RestartPolicy', {'Name':'always','MaximumRetryCount':0}), ('HostConfig', 'AutoRemove', True),
            ('HostConfig', 'PortBindings', {'1/tcp':[]}), ('HostConfig', 'PidMode', 'host'),
            ('HostConfig', 'IpcMode', 'host'), ('HostConfig', 'CgroupnsMode', 'host'), ('HostConfig', 'UTSMode', 'host'),
            ('HostConfig', 'UsernsMode', 'host'), ('HostConfig', 'GroupAdd', ['0']), ('HostConfig', 'ExtraHosts', ['host']),
            ('HostConfig', 'Binds', ['/secret:/secret']), ('HostConfig', 'Links', ['other'])]
        for section, key, value in changes:
            with self.subTest(section=section, key=key):
                changed = copy.deepcopy(observed)
                if key is None:
                    changed[section] = value
                else:
                    changed[section][key] = value
                with self.assertRaises(packets.PacketError):
                    containers.validate_policy(changed, image_id=IMAGE, workspace=self.backend._workspace(self.record()['binding']),
                        name=self.record()['binding']['runtime_id'], labels=self.backend._labels(self.record()['binding']),
                        worker='edit', environment=self.backend.environment)

    def test_trusted_walk_rejects_symlink_hardlink_fifo_oversize_and_inode_replacement(self):
        self.start(); binding = self.record()['binding']; descriptor = self.descriptor()
        workspace = self.backend._workspace(binding); file = workspace/'example.txt'; original = file.read_bytes()
        file.unlink(); file.symlink_to(self.root/'outside')
        with self.assertRaises((packets.PacketError, OSError)):
            self.backend._walk(binding, descriptor)
        file.unlink(); file.write_bytes(original)
        outside = self.root/'outside'; outside.write_bytes(b'external\n')
        file.unlink(); os.link(outside, file)
        with self.assertRaises(packets.PacketError):
            self.backend._walk(binding, descriptor)
        file.unlink(); os.mkfifo(file)
        with self.assertRaises(packets.PacketError):
            self.backend._walk(binding, descriptor)
        file.unlink(); file.write_bytes(b'x'*(containers.MAX_FILE_BYTES+1))
        with self.assertRaises(packets.PacketError):
            self.backend._walk(binding, descriptor)
        workspace.rename(workspace.with_name('retained-workspace'))
        workspace.mkdir()
        with self.assertRaisesRegex(packets.PacketError, 'workspace-identity-drift'):
            self.backend._walk(binding, descriptor)

    def test_export_capture_start_drift_and_backend_seal_digest_conflict_rejected(self):
        self.engine.start_fault = OSError('lost reply'); self.start()
        binding = self.record()['binding']; descriptor = self.descriptor()
        original = self.backend._walk
        def resumed(*args):
            value = original(*args)
            state = self.engine.inspect(descriptor['container_id']); state['State']['StartedAt'] = '2026-10-02T00:02:00Z'
            self.engine._write(descriptor['container_id'], state)
            return value
        with mock.patch.object(self.backend, '_walk', side_effect=resumed):
            self.assert_unknown(self.supervisor.reconcile('attempt'))
        self.assertFalse((self.root/'packet'/('backend-'+binding['runtime_id']+'.export')).exists())

    def test_retained_export_digest_and_binding_conflict_are_rejected(self):
        original = self.backend.export_patch
        def lost(*args):
            original(*args)
            raise OSError('lost export')
        with mock.patch.object(self.backend, 'export_patch', side_effect=lost):
            self.start()
        binding, descriptor = self.record()['binding'], self.descriptor()
        prefix = self.root/'packet'/('backend-'+binding['runtime_id'])
        path = pathlib.Path(str(prefix)+'.patch'); original_patch = path.read_bytes()
        path.write_bytes(original_patch+b'tamper')
        with self.assertRaisesRegex(packets.PacketError, 'digest-drift'):
            self.backend.read_sealed_patch(binding, packets.MAX_PATCH, descriptor)
        path.write_bytes(original_patch)
        manifest = pathlib.Path(str(prefix)+'.export'); value = json.loads(manifest.read_bytes())
        value['binding']['generation'] += 1
        manifest.write_bytes(packets.canonical(value))
        with self.assertRaisesRegex(packets.PacketError, 'binding-drift'):
            self.backend.read_sealed_patch(binding, packets.MAX_PATCH, descriptor)

    def test_descriptor_requirement_cannot_silently_upgrade_or_downgrade_backend(self):
        self.start()
        class PlainBackend:
            pass
        with self.assertRaisesRegex(packets.PacketError, 'descriptor-policy-drift'):
            supervisors.PacketSupervisor(self.store, PlainBackend(), host_id=self.backend.host_id,
                backend_id=self.backend.backend_id, policy_sha256=self.backend.policy_sha256).reconcile('attempt')
        store = packets.PacketStore(self.root, 'legacy'); store.prepare('d'*64)
        backend = containers.SyntheticContainerBackend(store, endpoint='unix:///synthetic/socket',
            image_id=IMAGE, opt_in=True, _engine=self.engine)
        store.reserve_runtime('attempt', 'e'*64, 'f'*64, expected_revision=0,
            source_sha256=containers.source_digest(), scope_sha256='1'*64, acceptance_sha256='2'*64,
            host_id=backend.host_id, backend_id=backend.backend_id, policy_sha256=backend.policy_sha256,
            runtime_id='legacy-runtime')
        with self.assertRaisesRegex(packets.PacketError, 'descriptor-policy-drift'):
            supervisors.PacketSupervisor(store, backend, host_id=backend.host_id,
                backend_id=backend.backend_id, policy_sha256=backend.policy_sha256).reconcile('attempt')

    def test_quarantined_running_writer_reconstruction_successor_and_late_fencing(self):
        self.engine.start_fault = OSError('lost reply'); self.start()
        binding, descriptor = self.record()['binding'], self.descriptor()
        value = self.engine.inspect(descriptor['container_id']); value['State'].update(Status='running', Running=True, Pid=55)
        self.engine._write(descriptor['container_id'], value)
        adapter = self.backend.isolation_adapter(binding, descriptor)
        private = packets.PacketStore(self.root, 'packet', _trusted_isolation_adapters={'fixture':adapter})
        ledger = private.supervisor_snapshot('attempt')[0]
        isolated = private.quarantine('attempt', expected_revision=ledger['revision'], isolation_adapter_id='fixture')
        self.assertEqual(isolated['attempts'][-1]['execution_outcome'], 'unknown')
        self.assertEqual(self.engine.inspect(descriptor['container_id'])['State']['Running'], True)
        fresh = FakeDocker(self.root); backend = self.new_backend(fresh)
        reconstructed = packets.PacketStore(self.root, 'packet',
            _trusted_isolation_adapters={'fixture':backend.isolation_adapter(binding, descriptor)})
        backend.store = reconstructed
        supervisor = self.new_supervisor(backend); supervisor.store = reconstructed
        result = self.start(supervisor, 'successor', isolated['revision'])
        self.assertEqual(result['outcome'], 'integration-candidate')
        with self.assertRaises(packets.PacketError):
            self.store.publish_checkpoint('attempt', b'', 'a'*64)
        with self.assertRaises(packets.PacketError):
            supervisor.reconcile('attempt')
        self.assertEqual(packets.PACKET_ISOLATION_ADAPTERS, {})
        # Revocation after persisted quarantine blocks even checkpoint readback.
        fresh.drift = lambda v: v['HostConfig'].update(NetworkMode='host')
        with self.assertRaises(packets.PacketError):
            reconstructed.read_checkpoint()

    def test_payload_unknown_fields_and_unbound_physical_id_never_reach_engine(self):
        self.start(); binding, descriptor = self.record()['binding'], self.descriptor()
        for key in ['module', 'host_command', 'mount', 'stopped']:
            with self.assertRaises(packets.PacketError):
                self.backend.inspect({**binding, key: True}, descriptor)
        forged = {**descriptor, 'container_id': '0'*64}
        with mock.patch.object(self.engine, 'inspect', side_effect=AssertionError('caller selected engine target')):
            with self.assertRaisesRegex(packets.PacketError, 'not-bound'):
                self.backend.inspect(binding, forged)
        extra = {**descriptor, 'stopped': True}
        with self.assertRaises(packets.PacketError):
            self.backend.inspect(binding, extra)

    def test_worker_config_cannot_inject_isolation_adapter_json(self):
        with self.assertRaises(packets.PacketError):
            packets.PacketStore(self.root, 'packet', _trusted_isolation_adapters={
                'fixture': {'synthetic_only':True, 'module':'os', 'stopped':True}})

    def test_constructor_is_opt_in_fixed_image_worker_and_environment_only(self):
        for kwargs in [{'opt_in':False}, {'worker':'host-command'}, {'image_id':'python:latest'}]:
            values = {'endpoint':'unix:///synthetic/socket', 'image_id':IMAGE, 'opt_in':True, '_engine':self.engine, **kwargs}
            with self.assertRaises(packets.PacketError):
                containers.SyntheticContainerBackend(self.store, **values)
        for image_change in [{'Volumes': {'/secret':{}}}, {'Env':['AUTH_TOKEN=secret']}, {'Labels':{'secret':'x'}}]:
            image = self.engine.image(IMAGE); image['Config'].update(image_change)
            with mock.patch.object(self.engine, 'image', return_value=image):
                with self.assertRaises(packets.PacketError):
                    self.new_backend()
        self.assertEqual(packets.PACKET_ISOLATION_ADAPTERS, {})


if __name__ == '__main__':
    unittest.main()


class FakeOneShotDocker(FakeDocker):
    def __init__(self, root):
        super().__init__(root); self.bootstrap_fault=None

    def volume(self,name):
        return json.loads((self.root/(name+'.volume')).read_bytes())

    def command(self,*argv):
        if argv[:2]==('volume','create'):
            self.calls.append(argv); name=argv[-1]
            options=list(argv)
            labels={options[i+1].split('=',1)[0]:options[i+1].split('=',1)[1] for i,v in enumerate(options) if v=='--label'}
            value={'Name':name,'Driver':'local','Options':None,'Labels':labels,'Scope':'local',
                'CreatedAt':'2026-10-02T00:00:00Z','Mountpoint':'/control-fake/'+name}
            with (self.root/(name+'.volume')).open('x') as stream: json.dump(value,stream)
            (self.root/name).mkdir()
            return name.encode()
        if argv[:2]==('container','create'):
            cid=super().command(*argv).decode(); value=self.inspect(cid); options=list(argv)
            mounts=[options[i+1] for i,v in enumerate(options) if v=='--mount']
            volume=[value for value in mounts if value.startswith('type=volume')][0].split('src=')[1].split(',')[0]
            value['Mounts'].append({'Type':'volume','Name':volume,'Driver':'local','RW':True,'Destination':'/control','Source':'/control-fake/'+volume})
            value['HostConfig']['Mounts']=[{'Type':'bind','Source':value['Mounts'][0]['Source'],'Target':'/workspace'}, {'Type':'volume','Source':volume,'Target':'/control','ReadOnly':False,'VolumeOptions':{'NoCopy':True}}]
            value['HostConfig']['CapAdd']=['CAP_SETGID','CAP_SETPCAP','CAP_SETUID']; value['Config']['User']='0:0'
            self._write(cid,value); return cid.encode()
        if argv[:2]==('container','start'):
            self.calls.append(argv); cid=argv[2]; value=self.inspect(cid)
            control=self.root/value['Mounts'][-1]['Name']; config=ast.literal_eval(value['Config']['Cmd'][-1].splitlines()[0].removeprefix('CONFIG='))
            code=0
            if (control/'claim.json').exists(): code=73
            else:
                raw=(control/'input.json').read_bytes(); input_value=containers.archive.read_control_json(raw)
                claim={'schema_version':1,'input_sha256':packets.digest(raw),'input':input_value}
                (control/'claim.json').write_bytes(packets.canonical(claim))
                if config['fault']!='none': code=74
                else:
                    workspace=pathlib.Path(value['Mounts'][0]['Source'])
                    if "write_text('new" in value['Config']['Cmd'][-1]:
                        (workspace/'example.txt').write_text('new\n'); (workspace/'added.txt').write_text('added\n'); (workspace/'remove.txt').unlink(missing_ok=True)
                    completion={'schema_version':1,'claim_sha256':packets.digest(packets.canonical(claim)),
                        'input_sha256':packets.digest(raw),'input':input_value,'worker_status':0}
                    (control/'completion.json').write_bytes(packets.canonical(completion))
            value['State'].update(Status='exited',Running=False,Pid=0,ExitCode=code,
                StartedAt='2026-10-02T00:02:00Z',FinishedAt='2026-10-02T00:02:01Z')
            self._write(cid,value)
            if self.start_fault: raise self.start_fault
            return cid.encode()
        return super().command(*argv)

    def archive(self,*argv,input_bytes=None):
        import io,tarfile
        self.calls.append(argv)
        if argv[2]=='-':
            cid=argv[3].split(':')[0]; value=self.inspect(cid); directory=self.root/value['Mounts'][-1]['Name']
            raw=containers.archive.read_control_file(input_bytes,'input.json')
            with (directory/'input.json').open('xb') as stream: stream.write(raw)
            if self.bootstrap_fault: raise self.bootstrap_fault
            return b''
        cid,path=argv[2].split(':',1); value=self.inspect(cid); directory=self.root/value['Mounts'][-1]['Name']
        if path=='/control':
            output=io.BytesIO()
            with tarfile.open(fileobj=output,mode='w',format=tarfile.USTAR_FORMAT) as stream:
                entry=tarfile.TarInfo('control'); entry.type=tarfile.DIRTYPE; entry.mode=0o755; stream.addfile(entry)
                for child in directory.iterdir():
                    entry=tarfile.TarInfo('control/'+child.name); entry.size=child.stat().st_size; entry.mode=0o600
                    stream.addfile(entry,io.BytesIO(child.read_bytes()))
            return output.getvalue()
        name=path.rsplit('/',1)[-1]
        return containers.archive.build_control_file(name,(directory/name).read_bytes())


class OneShotBackendTests(_ContainerFixture):
    """Real ledger plus reconstructable daemon double; launcher tested separately."""
    # Avoid re-running inherited B1 exporter-double tests against N3-C.
    def setUp(self):
        super().setUp(); self.engine=FakeOneShotDocker(self.root)
        self.backend=self.oneshot(self.engine); self.supervisor=self.new_supervisor(self.backend)

    def oneshot(self,engine,**kwargs):
        return containers.OneShotSyntheticContainerBackend(self.store,endpoint='unix:///synthetic/docker.sock',
            image_id=IMAGE,opt_in=True,_engine=engine,**kwargs)

    def test_n3c_descriptor_bootstrap_receipt_same_ledger_and_reconstruction(self):
        result=self.start(); self.assertEqual(result['outcome'],'integration-candidate')
        record=self.record(); descriptor=self.descriptor()
        self.assertEqual(record['schema_version'],4); self.assertEqual(descriptor['schema_version'],2)
        self.assertEqual(record['bootstrap']['stage'],'start-intent')
        fresh=FakeOneShotDocker(self.root); result2=self.new_supervisor(self.oneshot(fresh)).reconcile('attempt')
        self.assertEqual(result,result2)
        self.assertFalse(any(call[:2] in [('container','start'),('container','create'),('volume','create')] or call[2:3]==('-',) for call in fresh.calls))

    def test_n3c_cp_lost_reply_never_replays_bootstrap_or_start(self):
        self.engine.bootstrap_fault=OSError('lost cp')
        self.assert_unknown(self.start()); self.assertEqual(self.record()['bootstrap']['stage'],'intent')
        fresh=FakeOneShotDocker(self.root); self.assert_unknown(self.new_supervisor(self.oneshot(fresh)).reconcile('attempt'))
        self.assertFalse(any(call[:2]==('container','start') or call[2:3]==('-',) for call in fresh.calls))

    def test_n3c_start_reply_lost_recovery_and_manual_duplicate_before_first_inspect(self):
        self.engine.start_fault=OSError('lost start')
        self.assert_unknown(self.start()); cid=self.descriptor()['container_id']
        fresh=FakeOneShotDocker(self.root)
        self.assertEqual(self.new_supervisor(self.oneshot(fresh)).reconcile('attempt')['outcome'],'integration-candidate')
        fresh.command('container','start',cid)
        self.assertEqual(fresh.inspect(cid)['State']['ExitCode'],73)
        with self.assertRaises(packets.PacketError): self.supervisor.reconcile('attempt')

    def test_n3c_manual_restart_before_first_inspect_rejects_existing_completion(self):
        self.engine.start_fault=OSError('lost start'); self.assert_unknown(self.start())
        fresh=FakeOneShotDocker(self.root); fresh.command('container','start',self.descriptor()['container_id'])
        self.assert_unknown(self.new_supervisor(self.oneshot(fresh)).reconcile('attempt'))

    def test_n3c_claim_fault_retains_unknown_and_no_restart(self):
        backend=self.oneshot(self.engine,launcher_fault='claim-created')
        self.assert_unknown(self.start(self.new_supervisor(backend)))
        fresh=FakeOneShotDocker(self.root)
        self.assert_unknown(self.new_supervisor(self.oneshot(fresh,launcher_fault='claim-created')).reconcile('attempt'))
        self.assertFalse(any(call[:2]==('container','start') for call in fresh.calls))

    def test_n3c_bootstrap_commit_windows_never_replay_cp_or_start(self):
        for stage in ['intent','ready','start-intent']:
            with self.subTest(stage=stage):
                store=packets.PacketStore(self.root,'packet-'+stage); store.prepare('d'*64)
                engine=FakeOneShotDocker(self.root)
                backend=containers.OneShotSyntheticContainerBackend(store,endpoint='unix:///synthetic/docker.sock',image_id=IMAGE,opt_in=True,_engine=engine)
                sup=supervisors.PacketSupervisor(store,backend,host_id=backend.host_id,backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)
                original=store._write
                def crash(fd,ledger):
                    original(fd,ledger)
                    record=ledger.get('supervisors',{}).get('attempt',{})
                    if (record.get('bootstrap') or {}).get('stage')==stage: raise SystemExit('after bootstrap commit')
                with mock.patch.object(store,'_write',side_effect=crash):
                    with self.assertRaises(SystemExit):
                        sup.start('attempt','e'*64,'f'*64,expected_revision=0,source_sha256=containers.source_digest(),scope_sha256='1'*64,acceptance_sha256='2'*64)
                fresh=FakeOneShotDocker(self.root)
                backend=containers.OneShotSyntheticContainerBackend(store,endpoint='unix:///synthetic/docker.sock',image_id=IMAGE,opt_in=True,_engine=fresh)
                sup=supervisors.PacketSupervisor(store,backend,host_id=backend.host_id,backend_id=backend.backend_id,policy_sha256=backend.policy_sha256)
                self.assertEqual(sup.reconcile('attempt')['outcome'],'unknown')
                self.assertFalse(any(call[:2]==('container','start') or call[2:3]==('-',) for call in fresh.calls))

    def test_n3c_completion_transplant_boolean_schema_and_extra_fields_rejected(self):
        self.engine.start_fault=OSError('lost start'); self.start()
        descriptor=self.descriptor(); directory=self.root/descriptor['control_volume']['name']
        path=directory/'completion.json'; original=path.read_bytes(); original_value=json.loads(original)
        for transform in [lambda value:value.update(schema_version=True),lambda value:value.update(extra='grant'),
                          lambda value:value['input'].update(container_id='0'*64),lambda value:value['input']['binding'].update(generation=99)]:
            value=copy.deepcopy(original_value); transform(value); path.write_bytes(packets.canonical(value))
            self.assert_unknown(self.supervisor.reconcile('attempt'))
        path.write_bytes(original)

    def test_n3c_predecessor_rejects_outside_scope_symlink_and_path_escape_before_apply(self):
        for header,mode in [('diff --git a/other.txt b/other.txt','100644'),
                            ('diff --git a/example.txt b/example.txt','120000'),
                            ('diff --git a/../escape b/../escape','100644')]:
            patch=(header+'\nnew file mode '+mode+'\n--- /dev/null\n+++ b/'+header.split(' b/')[1]+'\n@@ -0,0 +1 @@\n+outside\n').encode()
            with mock.patch.object(containers.subprocess,'run',side_effect=AssertionError('must not apply')):
                with self.assertRaises(packets.PacketError): containers.validate_fixed_predecessor(patch)

    def test_n3c_bootstrap_history_artifact_missing_or_tampered_rejects_candidate(self):
        self.start(); record=self.record(); last=record['bootstrap']['chain_sha256']
        paths=[]
        while last is not None:
            path=self.root/'packet'/('bootstrap-event-'+last+'.json'); paths.append(path)
            last=json.loads(path.read_bytes())['previous_sha256']
        self.assertEqual(len(paths),3)
        for path in paths:
            original=path.read_bytes(); path.write_bytes(b'{}')
            with self.assertRaises(packets.PacketError): self.supervisor.reconcile('attempt')
            path.write_bytes(original)
            moved=path.with_suffix('.missing'); path.replace(moved)
            with self.assertRaises(packets.PacketError): self.supervisor.reconcile('attempt')
            moved.replace(path)

    def test_n3c_zero_timestamp_restartcount_and_bad_exit_never_publish(self):
        self.engine.start_fault=OSError('lost start'); self.start(); descriptor=self.descriptor(); cid=descriptor['container_id']
        original=self.engine.inspect(cid)
        for mutation in [lambda value:value['State'].update(StartedAt='0001-01-01T00:00:00Z'),
                         lambda value:value['State'].update(FinishedAt='0001-01-01T00:00:00Z'),
                         lambda value:value['State'].update(ExitCode=73),lambda value:value.update(RestartCount=True),
                         lambda value:value.update(RestartCount=1),lambda value:value['State'].update(Paused=True)]:
            value=copy.deepcopy(original); mutation(value); self.engine._write(cid,value)
            self.assert_unknown(self.supervisor.reconcile('attempt'))
        self.engine._write(cid,original)

    def test_n3c_volume_and_receipt_drift_reject_candidate(self):
        self.start(); descriptor=self.descriptor(); record=self.record()
        receipt=self.root/'packet'/('bootstrap-'+record['bootstrap']['receipt_sha256']+'.json')
        original=receipt.read_bytes(); receipt.write_bytes(b'{}')
        with self.assertRaises(packets.PacketError): self.supervisor.reconcile('attempt')
        receipt.write_bytes(original)
        path=self.root/(descriptor['control_volume']['name']+'.volume'); metadata=json.loads(path.read_bytes())
        metadata['CreatedAt']='2026-10-03T00:00:00Z'; path.write_bytes(packets.canonical(metadata))
        with self.assertRaises(packets.PacketError): self.supervisor.reconcile('attempt')


class FixedPredecessorTests(unittest.TestCase):
    UPDATE=b'diff --git a/example.txt b/example.txt\n--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new\n'
    EXTRA=b'\n--- /dev/null\n+++ b/other.txt\n@@ -0,0 +1 @@\n+outside\n'

    def materialize(self,patch):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root=pathlib.Path(temporary.name)
        for name,raw in containers.BASELINE.items(): (root/name).write_bytes(raw)
        process=containers.subprocess.run(['git','apply','-'],input=patch,cwd=root,
            env={'PATH':os.defpath,'HOME':str(root),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'LC_ALL':'C'},
            stdout=containers.subprocess.DEVNULL,stderr=containers.subprocess.DEVNULL,
            timeout=10,close_fds=True)
        return process.returncode,root

    def test_mixed_traditional_patch_is_real_valid_git_but_scope_rejected_before_apply(self):
        patch=self.UPDATE+self.EXTRA
        code,root=self.materialize(patch)
        self.assertEqual(code,0); self.assertEqual((root/'other.txt').read_bytes(),b'outside\n')
        # Validation parses only: ordinary host apply must never be called.
        with mock.patch.object(containers.subprocess,'run',side_effect=AssertionError('must not apply')):
            with self.assertRaises(packets.PacketError): containers.validate_fixed_predecessor(patch)

    def test_actual_targets_header_conflict_noheader_allowed_extra_and_duplicates_reject(self):
        patches=[self.UPDATE.replace(b'+++ b/example.txt',b'+++ b/added.txt'),
                 self.EXTRA.replace(b'other.txt',b'added.txt'),
                 self.UPDATE+self.EXTRA.replace(b'other.txt',b'added.txt'),
                 self.UPDATE+self.UPDATE,self.UPDATE+self.EXTRA]
        for patch in patches:
            with self.subTest(patch=patch):
                with self.assertRaises(packets.PacketError): containers.validate_fixed_predecessor(patch)

    def test_fixed_regular_update_and_cumulative_add_delete_prefix_are_accepted(self):
        add=b'diff --git a/added.txt b/added.txt\nnew file mode 100644\n--- /dev/null\n+++ b/added.txt\n@@ -0,0 +1 @@\n+added\n'
        delete=b'diff --git a/remove.txt b/remove.txt\ndeleted file mode 100644\n--- a/remove.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-delete\n'
        containers.validate_fixed_predecessor(b'')
        containers.validate_fixed_predecessor(self.UPDATE)
        patch=self.UPDATE+add+delete
        containers.validate_fixed_predecessor(patch)
        code,root=self.materialize(patch); self.assertEqual(code,0)
        self.assertEqual({name.name:name.read_bytes() for name in root.iterdir()},
            {'example.txt':b'new\n','added.txt':b'added\n'})

    def test_numstat_output_bound_rejects_large_headerless_target_inventory(self):
        extra=self.EXTRA.replace(b'other.txt',b'added.txt')
        with self.assertRaises(packets.PacketError): containers.validate_fixed_predecessor(self.UPDATE+extra*1000)
