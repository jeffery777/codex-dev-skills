"""Offline fixed container/stdio/provider doubles; no listener, Docker or native CLI."""
import base64
import copy
import email.message
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prestart_fixture_test', ROOT / 'scripts/verify-model-app-server-container.py')
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
guest = host.guest
CID = 'c' * 64
CREATED = '2026-10-04T01:00:00Z'
SMALL_BINARY = b'fixed-offline-binary'
ANONYMOUS_ENV = ['PATH=/synthetic/bin', 'SYNTHETIC_SETTING=fixture']
ANONYMOUS_LABELS = {'anonymous.fixture': 'offline-control'}
IMAGE_CONFIG = {'Env': ANONYMOUS_ENV, 'Labels': ANONYMOUS_LABELS, 'Entrypoint': None, 'Volumes': None}


def observed(root, name, uid, gid, *, exited=False):
    return {'Id': CID, 'Created': CREATED, 'Name': '/' + name, 'Image': host.IMAGE, 'RestartCount': 0,
        'Config': {'Image': host.IMAGE, 'Entrypoint': ['/usr/bin/env'], 'Cmd': list(host.WRAPPER_CMD),
            'Env': list(ANONYMOUS_ENV), 'Labels': {**ANONYMOUS_LABELS, 'codex.fixture.run': name},
            'User': str(uid) + ':' + str(gid), 'WorkingDir': '/control', 'Healthcheck': {'Test': ['NONE']},
            **{key: True for key in ('OpenStdin', 'StdinOnce', 'AttachStdin', 'AttachStdout', 'AttachStderr')},
            'Tty': False, 'Volumes': None, 'ExposedPorts': None},
        'HostConfig': {'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False, 'CapDrop': ['ALL'],
            'CapAdd': None, 'SecurityOpt': ['no-new-privileges'], 'PidsLimit': 64, 'Memory': 536870912,
            'MemorySwap': 536870912, 'NanoCpus': 1000000000, 'CpuPeriod': 0, 'CpuQuota': 0, 'Tmpfs': None,
            'LogConfig': {'Type': 'none', 'Config': {}}, 'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}, 'AutoRemove': False, 'PidMode': '',
            'IpcMode': 'private', 'CgroupnsMode': 'private', 'UTSMode': '', 'UsernsMode': '', 'PublishAllPorts': False,
            **{key: None for key in ('Devices', 'DeviceRequests', 'DeviceCgroupRules', 'GroupAdd', 'ExtraHosts',
                                    'Binds', 'Links', 'VolumesFrom', 'PortBindings')}},
        'Mounts': [{'Type': 'bind', 'Source': str(root / name_), 'Destination': destination,
                    'RW': rw, 'Propagation': 'rprivate'} for name_, destination, rw in
                   [('capture', '/fixture', False), ('control', '/control', True)]],
        'NetworkSettings': {'Ports': {}}, 'State': {'Status': 'exited' if exited else 'created', 'Running': False,
            'Pid': 0, 'ExitCode': 0, 'Paused': False, 'Restarting': False, 'Dead': False, 'OOMKilled': False, 'Error': ''}}


class EngineDouble:
    def __init__(self, endpoint, root, create):
        self.endpoint, self.root, self.create = endpoint, root, create
        self.calls = []; self.failures = []; self.trace = []; self.executable = '/fixed/docker'
        self.executable_identity = ('fixed-identity',); self.environment = {'PATH': '/usr/bin:/bin', 'HOME': str(root)}
        self.allowed_cid = None; self.session_closed = False; self.created = False
        self.name = create[create.index('--name') + 1]

    def _executable_snapshot(self):
        return self.executable_identity

    def identity(self):
        self.calls.append(('identity',)); return 'd' * 64

    def image(self, image):
        self.calls.append(('image', image))
        return {'Id': host.IMAGE, 'Os': 'linux', 'Architecture': 'arm64', 'Config': {
            'Env': ANONYMOUS_ENV, 'Labels': ANONYMOUS_LABELS, 'Entrypoint': None, 'Volumes': None}}

    def command(self, *argv):
        self.calls.append(argv)
        if list(argv) != self.create or self.created:
            raise AssertionError('replayed-or-unfixed-create')
        self.created = True
        (self.root / 'cidfile').write_text(CID + '\n'); (self.root / 'cidfile').chmod(0o600)
        return CID.encode()

    def inspect(self, cid):
        self.calls.append(('inspect', cid))
        if cid != CID:
            raise AssertionError('wrong-read-target')
        return observed(self.root, self.name, os.getuid(), os.getgid(), exited=self.session_closed)


class SessionDouble:
    def __init__(self, argv, *, cwd, env, limits, fixed_tool, tool_callback, admission_receipt, engine):
        self.engine = engine; self.native = admission_receipt; self.callback = tool_callback; self.wire = []
        self.requests = []; self.argv = argv
        self.assert_intents(cwd)

    def assert_intents(self, cwd):
        root = pathlib.Path(cwd)
        if not (root / 'start-intent.json').is_file() or not (root / 'prestart-policy.json').is_file():
            raise AssertionError('started-before-durable-intent-and-policy')
        if self.argv[-5:] != ['container', 'start', '--attach', '--interactive', CID]:
            raise AssertionError('arbitrary-launch')

    def request(self, method, params):
        self.requests.append((method, params))
        if method == 'initialize':
            return {}
        if method == 'thread/start':
            return {'thread': {'id': 'thread'}, 'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'cwd': '/control/workspace',
                'approvalPolicy': 'never', 'activePermissionProfile': {'id': 'probe', 'extends': None}}
        if method == 'turn/start':
            return {'turn': {'id': 'turn'}}
        raise AssertionError('unexpected-metadata-request')

    def record(self, direction, message):
        self.wire.append({'direction': direction, 'message': message,
            'raw_base64': base64.b64encode((json.dumps(message) + '\n').encode()).decode()})

    def notification(self):
        params = {'arguments': {}, 'callId': host.probe.ADMISSION_CALL, 'threadId': 'thread',
                  'turnId': 'turn', 'tool': 'packet_probe', 'namespace': None}
        envelope = {'id': 22, 'method': 'item/tool/call', 'params': params}
        self.native['_pending_envelope'] = envelope
        self.record('in', envelope)
        result = self.callback(params); self.native.pop('_pending_envelope')
        self.record('out-sent', {'id': 22, 'result': result})
        note = {'method': 'turn/completed', 'params': {'threadId': 'thread', 'turn': {'id': 'turn', 'status': 'completed'}}}
        self.record('in', note)
        return note

    def _drain_available(self, deadline):
        pass

    def _deadline(self):
        return host.time.monotonic() + 1

    def close(self):
        self.engine.session_closed = True
        request = json.loads((self.engine.root / 'control/request.json').read_bytes())
        binary = {'sha256': guest.BINARY_SHA, 'bytes': guest.BINARY_BYTES, 'uid': os.getuid(), 'mode': 0o500}
        receipt = {'run_id': request['run_id'], 'sources': request['sources'], 'passed': True,
            'cli_wait': 'observed', 'cli_exit_code': 0, 'fixture_stopped': True, 'exact_token_confirmed': True,
            'binary': binary, 'binary_after': binary, 'cli_env': guest.ENV, 'cli_argv': guest.cli_argv(12345, host.probe.boundary),
            'cli_pid': 912, 'provider_port': 12345, 'sentinel_preserved': True, 'workspace_unchanged': True, 'requests': []}
        for stage in (1, 2):
            value = {'input': []} if stage == 1 else {'input': [{'type': 'function_call_output',
                'call_id': guest.CALL, 'output': request['accepted_token']}]}
            raw = json.dumps(value).encode(); digest = hashlib.sha256(raw).hexdigest()
            guest.save(self.engine.root / 'control', 'provider-request-' + str(stage) + '.json',
                {'stage': stage, 'sha256': digest, 'raw_base64': base64.b64encode(raw).decode()})
            receipt['requests'].append({'stage': stage, 'sha256': digest})
        guest.save(self.engine.root / 'control', 'cli-spawn-intent.json',
            {'run_id': request['run_id'], 'argv': receipt['cli_argv'], 'env': guest.ENV})
        guest.save(self.engine.root / 'control', 'guest-receipt.json', receipt)
        return {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}


class ContainerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name).resolve(); self.root.chmod(0o700)
        self.binary = self.root / 'binary'; self.binary.write_bytes(SMALL_BINARY); self.binary.chmod(0o500)
        self.args = SimpleNamespace(evidence_root=self.root, binary_path=self.binary, endpoint='unix:///fixed/docker.sock')
        self.engines = []; self.sessions = []
        self.patchers = [mock.patch.object(guest, 'BINARY_BYTES', len(SMALL_BINARY)),
            mock.patch.object(guest, 'BINARY_SHA', hashlib.sha256(SMALL_BINARY).hexdigest()),
            mock.patch.object(host.probe.metadata, 'collect', return_value={'feature_inventory_complete': True,
                'startup_isolation_qualified': False, 'thread_snapshot_verified': False})]
        for patcher in self.patchers:
            patcher.start(); self.addCleanup(patcher.stop)

    def engine(self, endpoint, root, create):
        value = EngineDouble(endpoint, root, create); self.engines.append(value); return value

    def session(self, *args, **kwargs):
        value = SessionDouble(*args, **kwargs, engine=self.engines[-1]); self.sessions.append(value); return value

    def run_fixture(self, **kwargs):
        return host.run(self.args, _engine_factory=self.engine, _session_factory=self.session,
                        _socket=lambda endpoint: {'fixed': endpoint}, **kwargs)

    def evidence(self):
        return json.loads(next(self.root.glob('model-prestart-appserver-*/prestart-appserver-evidence.json')).read_bytes())

    def test_prestart_policy_intent_then_single_admission_and_separate_exits(self):
        value = self.run_fixture()
        self.assertEqual(value['execution_outcome'], 'measured-synthetic-prestart-container-admission-passed')
        self.assertFalse(value['startup_isolation_qualified']); self.assertFalse(value['n3_complete'])
        self.assertEqual(value['transport_client_close']['process_kind'], 'docker-client')
        self.assertEqual(value['container_exit']['State']['Status'], 'exited')
        self.assertEqual(value['guest_receipt']['cli_exit_code'], 0)
        self.assertEqual(value['native']['admission_call']['namespace'], None)
        self.assertEqual(len(self.sessions), 1)
        self.assertIn('--pull=never', self.engines[0].create)
        self.assertEqual(sum(call[:2] == ('container', 'create') for call in self.engines[0].calls), 1)
        self.assertEqual(len(value['source_capture']), 20)

    def test_every_prestart_policy_field_drift_has_zero_starts(self):
        changes = [('Config', 'Env', ANONYMOUS_ENV + ['SECRET=bad']), ('Config', 'User', '0:0'),
            ('Config', 'Labels', {'anonymous.unexpected': 'drift'}), ('Config', 'WorkingDir', '/other'), ('Config', 'StdinOnce', False), ('Config', 'OpenStdin', False),
            ('Config', 'Tty', True), ('Config', 'Entrypoint', ['/bin/sh']), ('Config', 'Cmd', ['bad']),
            ('HostConfig', 'NetworkMode', 'host'), ('HostConfig', 'ReadonlyRootfs', False),
            ('HostConfig', 'CapAdd', ['SYS_ADMIN']), ('HostConfig', 'SecurityOpt', []), ('HostConfig', 'PidMode', 'host'),
            ('HostConfig', 'Devices', [{}]), ('HostConfig', 'PortBindings', {'80/tcp': []}),
            ('HostConfig', 'Memory', 0), ('HostConfig', 'GroupAdd', ['0']), ('State', 'Pid', 1),
            ('State', 'Running', True), ('State', 'Status', 'running')]
        for section, field, changed in changes:
            with self.subTest(section=section, field=field), mock.patch.object(EngineDouble, 'inspect') as inspect:
                inspect.side_effect = lambda cid: self.drift_observed(section, field, changed)
                with self.assertRaises(host.FixtureError): self.run_fixture()
                self.assertEqual(self.sessions, [])

    def drift_observed(self, section, field, changed):
        engine = self.engines[-1]; value = observed(engine.root, engine.name, os.getuid(), os.getgid())
        value[section][field] = changed; return value

    def test_journal_full_bytes_then_fsync_unknown_never_spawns_start(self):
        original = host.helpers._reload_save
        for name in ('create-intent.json', 'prestart-policy.json', 'start-intent.json'):
            def save(root, filename, value):
                ref = original(root, filename, value)
                if filename == name: raise OSError('offline journal readback uncertainty')
                return ref
            with self.subTest(name=name), mock.patch.object(host.helpers, '_reload_save', side_effect=save):
                with self.assertRaises(OSError): self.run_fixture()
                self.assertEqual(self.sessions, [])

    def test_unknown_create_only_reads_exact_cid_and_never_recreates(self):
        original = EngineDouble.command
        def unknown(engine, *args):
            original(engine, *args); engine.failures.append('result-journal-unknown'); raise OSError('fixture unknown reply')
        with mock.patch.object(EngineDouble, 'command', unknown), self.assertRaises(OSError): self.run_fixture()
        engine = self.engines[-1]
        self.assertEqual(sum(call[:2] == ('container', 'create') for call in engine.calls), 1)
        self.assertEqual(engine.calls[-1], ('inspect', CID)); self.assertFalse(self.sessions)

    def test_client_zero_cannot_mask_running_container_nonzero_cli_or_policy_drift(self):
        original_close = SessionDouble.close; original_inspect = EngineDouble.inspect
        for fault in ('running', 'cli', 'container', 'policy', 'missing-receipt', 'close'):
            def close(session):
                value = original_close(session)
                file = session.engine.root / 'control/guest-receipt.json'
                if fault == 'cli':
                    raw = json.loads(file.read_bytes()); raw['cli_exit_code'] = 7; file.write_text(json.dumps(raw))
                if fault == 'missing-receipt': file.rename(file.with_name('retained-guest-receipt.json'))
                if fault == 'close': value['protocol'] = 'unknown'
                return value
            def inspect(engine, cid):
                value = original_inspect(engine, cid)
                if engine.session_closed:
                    if fault == 'running': value['State'].update(Running=True, Status='running', Pid=812)
                    if fault == 'container': value['State']['ExitCode'] = 3
                    if fault == 'policy': value['HostConfig']['NetworkMode'] = 'host'
                return value
            before = len(self.sessions)
            with self.subTest(fault=fault), mock.patch.object(SessionDouble, 'close', close), \
                    mock.patch.object(EngineDouble, 'inspect', inspect), mock.patch.object(host.time, 'sleep'), \
                    self.assertRaises((host.FixtureError, FileNotFoundError)):
                self.run_fixture()
            self.assertEqual(len(self.sessions), before + 1)

    def test_binary_source_symlink_and_missing_closure_fail_before_engine(self):
        linked = self.root / 'linked'; linked.symlink_to(self.binary)
        with self.assertRaises(OSError): host.copy_binary(linked, self.root / 'copy')
        with mock.patch.object(host.helpers, '_reload_read', side_effect=FileNotFoundError('missing closure')), \
                self.assertRaises(FileNotFoundError): self.run_fixture()
        self.assertFalse(self.engines); self.assertFalse(self.sessions)

    def test_private_fixed_image_config_snapshot_drift_has_zero_starts(self):
        original = EngineDouble.image
        for field, changed in [('Env', ANONYMOUS_ENV + ['SYNTHETIC_DRIFT=bad']),
                               ('Labels', {'anonymous.changed': 'bad'}), ('Cmd', ['unexpected-fixed-image-command'])]:
            counts = {}
            def image(engine, image_id):
                value = copy.deepcopy(original(engine, image_id))
                counts[id(engine)] = counts.get(id(engine), 0) + 1
                if counts[id(engine)] > 1: value['Config'][field] = changed
                return value
            with self.subTest(field=field), mock.patch.object(EngineDouble, 'image', image), \
                    self.assertRaisesRegex(host.FixtureError, 'config-snapshot-drift'):
                self.run_fixture()
            self.assertFalse(self.sessions)
            self.assertEqual(sum(call[:2] == ('container', 'create') for call in self.engines[-1].calls), 1)

    def test_private_snapshot_reference_tamper_cannot_start(self):
        original = host.helpers._reload_save
        def save(root, name, value):
            reference = original(root, name, value)
            if name == 'start-intent.json':
                snapshot = root / 'fixed-image-snapshot.json'
                snapshot.rename(snapshot.with_name('retained-fixed-image-snapshot.json'))
                original(root, 'fixed-image-snapshot.json', {'Id': host.IMAGE, 'Config': IMAGE_CONFIG})
            return reference
        with mock.patch.object(host.helpers, '_reload_save', side_effect=save), \
                self.assertRaisesRegex(host.helpers.packets.PacketError, 'reference-drift'):
            self.run_fixture()
        self.assertFalse(self.sessions)



class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name); self.request = {'accepted_token': 'packet-admission-accepted:fixed'}
        self.receipt = {'requests': [], 'exact_token_confirmed': False}
        with mock.patch.object(guest.http.server, 'HTTPServer') as server:
            guest.provider(self.root, self.request, self.receipt, host.probe.boundary)
        self.handler = server.call_args.args[1]
        self.assertEqual(server.call_args.args[0], ('127.0.0.1', 0))

    def post(self, value, **headers):
        raw = json.dumps(value).encode(); handler = object.__new__(self.handler)
        handler.path = '/v1/responses'; handler.headers = email.message.Message()
        handler.headers['Content-Length'] = str(len(raw))
        for name, value in headers.items(): handler.headers[name] = value
        handler.rfile = io.BytesIO(raw); handler.wfile = io.BytesIO()
        handler.send_response = mock.Mock(); handler.send_header = mock.Mock(); handler.end_headers = mock.Mock()
        handler.send_error = mock.Mock(); handler.do_POST(); return handler

    def test_exact_two_rounds_raw_journals_and_no_extra_or_wrong_token(self):
        self.post({'input': []}).send_response.assert_called_once_with(200)
        call = {'type': 'function_call_output', 'call_id': guest.CALL, 'output': self.request['accepted_token']}
        self.post({'input': [call]}).send_response.assert_called_once_with(200)
        self.assertTrue(self.receipt['exact_token_confirmed'])
        self.assertEqual(len(list(self.root.glob('provider-request-*.json'))), 2)
        self.post({'input': []}).send_error.assert_called_once_with(422)
        self.assertIn('provider_error', self.receipt)

    def test_wrong_token_duplicate_output_auth_or_journal_error_stays_unknown(self):
        self.post({'input': []})
        original = guest.save
        for fault in ('token', 'duplicate', 'auth', 'journal'):
            # Independent handler bookkeeping and independent immutable journal path.
            root = self.root / fault; root.mkdir(); self.receipt['requests'] = [self.receipt['requests'][0]]
            self.receipt.pop('provider_error', None)
            call = {'type': 'function_call_output', 'call_id': guest.CALL,
                    'output': 'bad' if fault == 'token' else self.request['accepted_token']}
            def save(directory, name, value):
                original(root, name, value)
                if fault == 'journal': raise OSError('after durable bytes')
            with mock.patch.object(guest, 'save', side_effect=save):
                handler = self.post({'input': [call, call] if fault == 'duplicate' else [call]},
                                    **({'Authorization': 'Bearer synthetic'} if fault == 'auth' else {}))
            handler.send_error.assert_called_once_with(422); self.assertIn('provider_error', self.receipt)


class GuestWrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve(); self.root.chmod(0o700)
        self.binary = self.root / 'binary'; self.binary.write_bytes(SMALL_BINARY); self.binary.chmod(0o500)
        for patcher in (mock.patch.object(guest, 'BINARY_BYTES', len(SMALL_BINARY)),
                        mock.patch.object(guest, 'BINARY_SHA', hashlib.sha256(SMALL_BINARY).hexdigest())):
            patcher.start(); self.addCleanup(patcher.stop)
        sources, _ = host.capture(self.root, self.binary)
        self.fixture = self.root / 'capture'; self.control = self.root / 'control'; self.control.mkdir(mode=0o700)
        self.request = {'schema_version': 1, 'run_id': 'a' * 32, 'accepted_token': 'packet-admission-accepted:' + 'a' * 32,
            'uid': os.getuid(), 'gid': os.getgid(), 'sources': {name: value['sha256'] for name, value in sources.items()},
            'binary_sha256': guest.BINARY_SHA}
        guest.save(self.control, 'request.json', self.request)
        self.receipt = None

    def provider(self, root, request, receipt, boundary):
        self.receipt = receipt
        return SimpleNamespace(server_port=12345, serve_forever=lambda: None, shutdown=lambda: None, server_close=lambda: None)

    def child(self, *argv, **kwargs):
        self.assertTrue((self.control / 'cli-spawn-intent.json').is_file())
        self.assertEqual(kwargs['stdin'], None); self.assertEqual(kwargs['stdout'], None)
        self.assertEqual(kwargs['env'], guest.ENV); self.assertTrue(kwargs['close_fds']); self.assertEqual(kwargs['pass_fds'], ())
        self.assertEqual(argv[0], guest.cli_argv(12345, host.probe.boundary))
        def wait(timeout):
            self.assertEqual(timeout, 60)
            self.receipt['exact_token_confirmed'] = True
            self.receipt['requests'] = [{'stage': 1}, {'stage': 2}]
            return 0
        return SimpleNamespace(pid=1234, wait=wait)

    def run_guest(self, child=None, provider=None):
        class SynchronousThread:
            def __init__(self, target, daemon): self.target = target
            def start(self): self.target()
            def join(self, timeout): pass
            def is_alive(self): return False
        with mock.patch.dict(os.environ, {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/control/home', 'LANG': 'C.UTF-8'}, clear=True), \
                mock.patch.object(guest.sys, 'version_info', (3, 12, 13)), \
                mock.patch.object(guest, 'provider', side_effect=provider or self.provider), \
                mock.patch.object(guest.threading, 'Thread', SynchronousThread), \
                mock.patch.object(guest.subprocess, 'Popen', side_effect=child or self.child) as spawn, \
                mock.patch.object(sys.stdin, 'read', side_effect=AssertionError('wrapper-read-RPC-stdin')):
            result = guest.run_guest(_fixture=self.fixture, _control=self.control)
        return result, spawn

    def test_wrapper_waits_same_child_naturally_and_never_consumes_rpc_stream(self):
        result, spawn = self.run_guest()
        self.assertEqual(result, 0); spawn.assert_called_once()
        value = json.loads((self.control / 'guest-receipt.json').read_bytes())
        self.assertTrue(value['passed']); self.assertEqual(value['cli_pid'], 1234)
        self.assertEqual(value['cli_wait'], 'observed'); self.assertEqual(value['cli_exit_code'], 0)
        self.assertTrue(value['fixture_stopped'])

    def test_guest_owner_environment_or_source_drift_has_zero_cli_spawn(self):
        self.request['sources']['scripts/model_app_server_container_fixture.py'] = 'b' * 64
        (self.control / 'request.json').write_bytes(guest.canonical(self.request))
        result, spawn = self.run_guest()
        self.assertEqual(result, 1); spawn.assert_not_called()
        value = json.loads((self.control / 'guest-receipt.json').read_bytes())
        self.assertEqual(value['cli_wait'], 'unknown'); self.assertFalse(value['passed'])

    def test_guest_spawn_journal_full_bytes_then_error_never_spawns(self):
        original = guest.save
        def save(root, name, value):
            original(root, name, value)
            if name == 'cli-spawn-intent.json': raise OSError('full bytes then fsync failure')
        with mock.patch.object(guest, 'save', side_effect=save): result, spawn = self.run_guest()
        self.assertEqual(result, 1); spawn.assert_not_called()
        self.assertTrue((self.control / 'cli-spawn-intent.json').is_file())

    def test_nonzero_same_child_or_provider_shutdown_unknown_never_passes(self):
        def child(*argv, **kwargs): return SimpleNamespace(pid=1234, wait=lambda timeout: 7)
        result, spawn = self.run_guest(child=child)
        self.assertEqual(result, 1); spawn.assert_called_once()
        value = json.loads((self.control / 'guest-receipt.json').read_bytes())
        self.assertFalse(value['passed']); self.assertEqual(value['cli_exit_code'], 7)


class WirePolicyTests(unittest.TestCase):
    def test_empty_omitted_tmpfs_is_accepted_but_configured_tmpfs_is_rejected(self):
        root = pathlib.Path('/fixed'); name = 'fixed'
        for representation in ('omitted', 'empty', 'null'):
            value = observed(root, name, 501, 20)
            if representation == 'omitted':
                value['HostConfig'].pop('Tmpfs')
            else:
                value['HostConfig']['Tmpfs'] = {} if representation == 'empty' else None
            with self.subTest(representation=representation):
                self.assertEqual(host.policy(value, root, name, 501, 20, CID, image_config=IMAGE_CONFIG), value['Created'])
        for configured in ({'/extra': 'rw'}, [], False, 'unverified'):
            value = observed(root, name, 501, 20)
            value['HostConfig']['Tmpfs'] = configured
            with self.subTest(configured=configured), self.assertRaises(host.FixtureError):
                host.policy(value, root, name, 501, 20, CID, image_config=IMAGE_CONFIG)

    def test_docker_stdio_peer_malformed_partial_duplicates_extra_and_namespace_are_unknown(self):
        # Only a fixed Python stdio peer runs. It is neither Docker nor Codex.
        for fault in ('extra', 'namespace', 'duplicate', 'malformed', 'partial'):
            params = {'arguments': {'extra': 1} if fault == 'extra' else {}, 'threadId': 't', 'turnId': 'u',
                      'callId': host.probe.ADMISSION_CALL, 'tool': 'packet_probe', 'namespace': 'bad' if fault == 'namespace' else None}
            envelope = {'id': 31, 'method': 'item/tool/call', 'params': params}
            frames = json.dumps(envelope) + '\n'
            if fault == 'malformed': frames = 'Docker banner pollution\n'
            if fault == 'partial': frames = '{"id":'
            if fault == 'duplicate': frames += json.dumps(envelope) + '\n'
            source = "import json,sys\nr=json.loads(sys.stdin.readline());print(json.dumps({'id':r['id'],'result':{}}),flush=True)\nsys.stdin.readline()\nsys.stdout.write(" + repr(frames) + ");sys.stdout.flush()\n"
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                native = {'accepted_dynamic_calls': 0, 'accepted_token': 'packet-admission-accepted:fixed'}
                session = host.probe.AdmissionSession([sys.executable, '-I', '-S', '-B', '-c', source], cwd=directory,
                    env={'PATH': '/usr/bin:/bin', 'HOME': directory}, limits=host.probe.transport.Limits(timeout=1, close_timeout=1),
                    fixed_tool='packet_probe', tool_callback=host.probe.admission_callback(native, {'threadId': 't', 'turnId': 'u'}),
                    admission_receipt=native)
                try:
                    session.request('initialize', {'clientInfo': {}, 'capabilities': {'experimentalApi': True}})
                    with self.assertRaises(host.probe.transport.TransportError): session.notification()
                finally:
                    close = session.close()
                self.assertEqual(close['protocol'], 'unknown')
                self.assertLessEqual(native['accepted_dynamic_calls'], 1)
                native['wire'] = session.wire
                self.assertFalse(host.probe.admission_wire_confirmed(native))

    def test_engine_allowlist_denies_exec_recreate_reattach_other_cid_and_archive_stdin(self):
        engine = object.__new__(host.Engine); engine.fixed_create = ('container', 'create', 'fixed')
        engine.create_used = False; engine.allowed_cid = CID
        engine._allowed(engine.fixed_create, None)
        for argv in (engine.fixed_create, ('container', 'start', CID), ('container', 'exec', CID, 'sh'),
                     ('container', 'inspect', 'd' * 64), ('container', 'cp', CID + ':/control', '-')):
            with self.subTest(argv=argv), self.assertRaises(host.FixtureError): engine._allowed(argv, None)
        with self.assertRaises(host.FixtureError): engine._allowed(('container', 'inspect', CID), b'archive')

    def test_full_policy_rejects_wrong_cid_created_restart_mount_image_and_nullable_state(self):
        root = pathlib.Path('/fixed'); name = 'fixed'; original = observed(root, name, 501, 20)
        changes = [('Id', 'd' * 64), ('Created', False), ('RestartCount', 1), ('Image', 'sha256:' + 'd' * 64)]
        for key, value in changes:
            altered = copy.deepcopy(original); altered[key] = value
            with self.subTest(key=key), self.assertRaises(host.FixtureError): host.policy(altered, root, name, 501, 20, CID, image_config=IMAGE_CONFIG)
        for alteration in ('mount', 'running', 'restartcount-type'):
            altered = copy.deepcopy(original)
            if alteration == 'mount': altered['Mounts'].append(dict(altered['Mounts'][0], Destination='/host-parent'))
            if alteration == 'running': altered['State']['Running'] = None
            if alteration == 'restartcount-type': altered['RestartCount'] = False
            with self.subTest(alteration=alteration), self.assertRaises(host.FixtureError): host.policy(altered, root, name, 501, 20, CID, image_config=IMAGE_CONFIG)
        with self.assertRaises(host.FixtureError): host.policy(original, root, name, 501, 20, CID, 'different-created', image_config=IMAGE_CONFIG)
