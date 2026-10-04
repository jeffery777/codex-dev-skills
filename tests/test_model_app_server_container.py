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

    def test_writer_three_requests_exact_call_and_saved_responses(self):
        self.request['native_case'] = 'workspace-write'; tools = writer_tools('workspace-write')
        self.post({'input': [], 'tools': tools}).send_response.assert_called_once_with(200)
        token = {'type': 'function_call_output', 'call_id': guest.CALL, 'output': self.request['accepted_token']}
        second = self.post({'input': [token], 'tools': tools})
        second.send_response.assert_called_once_with(200)
        self.assertIn(guest.WRITER_CALL.encode(), second.wfile.getvalue())
        result = {'type': 'function_call_output', 'call_id': guest.WRITER_CALL, 'output': terminal_output()}
        self.post({'input': [token, result], 'tools': tools}).send_response.assert_called_once_with(200)
        self.assertTrue(self.receipt['writer_output_confirmed'])
        self.assertEqual(len(list(self.root.glob('provider-response-*.json'))), 3)
        self.post({'input': [result], 'tools': tools}).send_error.assert_called_once_with(422)

    def test_native_bootstrap_failure_finishes_without_replaying_or_claiming_denial(self):
        self.request['native_case'] = 'external-write-refusal'; tools = writer_tools('external-write-refusal')
        self.post({'input': [], 'tools': tools})
        token = {'type': 'function_call_output', 'call_id': guest.CALL, 'output': self.request['accepted_token']}
        self.post({'input': [token], 'tools': tools})
        output = 'exec_command failed: bwrap cannot establish sandbox'
        last = self.post({'input': [token, {'type': 'function_call_output', 'call_id': guest.WRITER_CALL,
                                          'output': output}], 'tools': tools})
        last.send_response.assert_called_once_with(200)
        self.assertFalse(self.receipt['writer_output_confirmed']); self.assertEqual(self.receipt['native_output'], output)
        self.assertNotIn(guest.WRITER_CALL.encode(), last.wfile.getvalue())
        self.assertEqual(len(self.receipt['requests']), 3)

    def test_missing_declared_shell_field_stops_before_any_response_tool(self):
        self.request['native_case'] = 'workspace-write'; tools = writer_tools('workspace-write')
        tools[0]['tools'][0]['parameters']['properties'].pop('shell')
        first = self.post({'input': [], 'tools': tools})
        first.send_error.assert_called_once_with(422)
        self.assertEqual(first.wfile.getvalue(), b'')
        self.assertEqual(len(self.receipt['requests']), 1)
        self.assertFalse(list(self.root.glob('provider-response-*.json')))


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
        previous_umask = os.umask(0o077)
        try:
            with mock.patch.dict(os.environ, {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/control/home', 'LANG': 'C.UTF-8'}, clear=True), \
                    mock.patch.object(guest.sys, 'version_info', (3, 12, 13)), \
                    mock.patch.object(guest, 'provider', side_effect=provider or self.provider), \
                    mock.patch.object(guest.threading, 'Thread', SynchronousThread), \
                    mock.patch.object(guest.subprocess, 'Popen', side_effect=child or self.child) as spawn, \
                    mock.patch.object(sys.stdin, 'read', side_effect=AssertionError('wrapper-read-RPC-stdin')):
                result = guest.run_guest(_fixture=self.fixture, _control=self.control)
        finally:
            os.umask(previous_umask)
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

    def test_native_path_shadow_has_zero_provider_and_cli_spawn(self):
        data = b'fixed-offline-bwrap'
        self.fixture.chmod(0o700); resources = self.fixture/'codex-resources'; resources.mkdir(mode=0o700)
        (resources/'bwrap').write_bytes(data); (resources/'bwrap').chmod(0o500)
        resources.chmod(0o500); self.fixture.chmod(0o500)
        (self.control/'external-canary').write_bytes(guest.CANARY_BYTES)
        self.request.update(native_case='workspace-write', canary_ref={}, bwrap_sha256=hashlib.sha256(data).hexdigest())
        (self.control/'request.json').write_bytes(guest.canonical(self.request))
        provider = mock.Mock()
        with mock.patch.object(guest, 'BWRAP_BYTES', len(data)), \
                mock.patch.object(guest, 'BWRAP_SHA', hashlib.sha256(data).hexdigest()), \
                mock.patch.object(guest.os.path, 'lexists', return_value=True):
            result, spawn = self.run_guest(provider=provider)
        self.assertEqual(result, 1); spawn.assert_not_called(); provider.assert_not_called()
        receipt = json.loads((self.control/'guest-receipt.json').read_bytes())
        self.assertEqual(receipt['failure_reason'], 'guest-system-bwrap-shadow')
        self.assertEqual(receipt['cli_spawn_count'], 0); self.assertFalse(receipt['prerequisites']['passed'])
        self.assertFalse(receipt['passed']); self.assertFalse(receipt['production_qualified'])


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


def writer_tools(case):
    # Independent pinned shell_spec.rs contract with allow_login_shell=false:
    # login is omitted. Never derive the tool schema from the tested arguments.
    properties = {'cmd': {'type': 'string'}, 'workdir': {'type': 'string'}, 'shell': {'type': 'string'},
                  'tty': {'type': 'boolean'}, 'yield_time_ms': {'type': 'number'},
                  'max_output_tokens': {'type': 'number'},
                  'sandbox_permissions': {'type': 'string', 'enum': ['use_default', 'require_escalated']}}
    return [{'type': 'namespace', 'name': 'functions', 'tools': [{'type': 'function', 'name': 'exec_command',
            'parameters': {'type': 'object', 'properties': properties, 'required': ['cmd']}}]}]


def terminal_output(code=0, body=''):
    return 'Chunk ID: fixture\nWall time: 0.1234 seconds\nProcess exited with code ' + str(code) + '\nOutput:\n' + body


def command_wire(output=None):
    native = {'accepted_dynamic_calls': 0, 'accepted_token': 'packet-admission-accepted:fixed', 'wire': []}
    params = {'arguments': {}, 'callId': guest.CALL, 'threadId': 't', 'turnId': 'u', 'tool': 'packet_probe', 'namespace': None}
    envelope = {'id': 20, 'method': 'item/tool/call', 'params': params}; native['_pending_envelope'] = envelope
    reply = host.probe.admission_callback(native, {'threadId': 't', 'turnId': 'u'})(params)
    native.pop('_pending_envelope')
    messages = [('in', envelope), ('out-sent', {'id': 20, 'result': reply}),
        ('in', {'method': 'item/started', 'params': {'threadId': 't', 'turnId': 'u',
            'item': {'type': 'commandExecution', 'id': guest.WRITER_CALL, 'status': 'inProgress'}}}),
        ('in', {'method': 'item/completed', 'params': {'threadId': 't', 'turnId': 'u',
            'item': {'type': 'commandExecution', 'id': guest.WRITER_CALL, 'status': 'completed',
                     'exitCode': 0, 'aggregatedOutput': ''}}}),
        ('in', {'method': 'turn/completed', 'params': {'threadId': 't', 'turn': {'id': 'u', 'status': 'completed'}}})]
    for direction, message in messages:
        native['wire'].append({'direction': direction, 'message': message,
            'raw_base64': base64.b64encode((json.dumps(message) + '\n').encode()).decode()})
    return native


class NativeWriterControls(unittest.TestCase):
    def test_fixed_arguments_and_profile_are_never_privilege_fallback(self):
        for case in guest.WRITER_CASES:
            with self.subTest(case=case):
                call = guest.writer_call(case); args = json.loads(call['arguments'])
                self.assertEqual(args['sandbox_permissions'], 'use_default')
                self.assertEqual(args['shell'], '/bin/sh'); self.assertNotIn('login', args); self.assertFalse(args['tty'])
                argv = guest.cli_argv(1234, host.probe.boundary, case)
                self.assertIn('allow_login_shell=false', argv)
                self.assertIn('features.shell_tool=true', argv); self.assertIn('features.unified_exec=true', argv)
                self.assertFalse(any('danger-full-access' in x or 'externalSandbox' in x for x in argv))
                fs = next(x for x in argv if x.startswith('permissions.probe-writer.filesystem='))
                self.assertIn('"/control/workspace"="write"', fs)
                self.assertIn('":root"="deny"', fs); self.assertIn('"/fixture/codex"="read"', fs)
                self.assertNotIn('"/fixture"=', fs); self.assertNotIn('"/control"=', fs)
                self.assertIn('"/control/external-canary"="read"', fs)
                self.assertEqual(host.native_environments(case), [{'environmentId': 'local',
                    'cwd': '/control/workspace', 'runtimeWorkspaceRoots': ['/control/workspace']}])
        for case in ('arbitrary', ['local'], True):
            with self.subTest(invalid=case), self.assertRaises((guest.FixtureError, TypeError)):
                guest.writer_call(case)

    def test_compatibility_schema_drift_has_no_native_call(self):
        case = 'workspace-write'; value = {'tools': writer_tools(case), 'input': []}
        self.assertFalse(guest.writer_declaration(json.dumps(value).encode(), host.probe.boundary, case)['handler_inventory_complete'])
        for fault in ('missing-shell', 'tty-string', 'required-new', 'default-disallowed'):
            bad = copy.deepcopy(value); schema = bad['tools'][0]['tools'][0]['parameters']
            if fault == 'missing-shell': schema['properties'].pop('shell')
            if fault == 'tty-string': schema['properties']['tty']['type'] = 'string'
            if fault == 'required-new': schema['required'].append('environment_id')
            if fault == 'default-disallowed': schema['properties']['sandbox_permissions']['enum'] = ['require_escalated']
            with self.subTest(fault=fault), self.assertRaises(guest.FixtureError):
                guest.writer_declaration(json.dumps(bad).encode(), host.probe.boundary, case)

    def test_login_argument_is_rejected_by_independent_non_login_schema(self):
        case = 'workspace-write'; value = {'tools': writer_tools(case), 'input': []}
        self.assertNotIn('login', value['tools'][0]['tools'][0]['parameters']['properties'])
        self.assertTrue(guest.writer_declaration(json.dumps(value).encode(), host.probe.boundary, case))
        original = guest.writer_call(case)
        arguments = json.loads(original['arguments']); arguments['login'] = False
        injected = dict(original, arguments=json.dumps(arguments))
        with mock.patch.object(guest, 'writer_call', return_value=injected), self.assertRaises(guest.FixtureError):
            guest.writer_declaration(json.dumps(value).encode(), host.probe.boundary, case)

    def test_native_bootstrap_or_unrelated_failure_never_counts_as_denial(self):
        denial = '/bin/sh: 1: cannot create /control/external-canary: Permission denied\n'
        self.assertEqual(guest.writer_output(terminal_output(2, denial), 'external-write-refusal')['outcome'], 'native-explicit-os-denial')
        self.assertEqual(guest.writer_output(terminal_output(), 'workspace-write')['exit_code'], 0)
        for value in ('exec_command failed: sandbox unavailable', terminal_output(1, 'bwrap: Operation not permitted\n'),
                      terminal_output(17, denial), terminal_output(18, denial),
                      terminal_output(2, denial.replace('cannot create', 'cannot open')),
                      terminal_output(0, denial), terminal_output(2, denial.replace('external-canary', 'other-file')),
                      terminal_output(999, denial), terminal_output(2, ''), terminal_output().replace('Process exited with code 0',
                          'Process running with session ID 12345')):
            with self.subTest(value=value), self.assertRaises(guest.FixtureError): guest.writer_output(value, 'external-write-refusal')

    def test_raw_command_lifecycle_identity_order_and_extra_requests(self):
        result = {'exit_code': 0, 'body': ''}; original = command_wire()
        self.assertTrue(host.probe.admission_wire_confirmed(original))
        self.assertTrue(host.writer_wire(original, 'workspace-write', result))
        for fault in ('call', 'thread', 'turn', 'exit-bool', 'body', 'late', 'duplicate', 'approval', 'raw-drift'):
            bad = copy.deepcopy(original); item = bad['wire'][3]['message']['params']['item']
            if fault == 'call': item['id'] = 'other-call'
            if fault == 'thread': bad['wire'][3]['message']['params']['threadId'] = 'other-thread'
            if fault == 'turn': bad['wire'][3]['message']['params']['turnId'] = 'other-turn'
            if fault == 'exit-bool': item['exitCode'] = False
            if fault == 'body': item['aggregatedOutput'] = 'fake success'
            if fault == 'late': bad['wire'][3], bad['wire'][4] = bad['wire'][4], bad['wire'][3]
            if fault == 'duplicate': bad['wire'].insert(4, copy.deepcopy(bad['wire'][3]))
            if fault == 'approval': bad['wire'].insert(4, {'direction': 'in', 'message': {'id': 50,
                'method': 'item/commandExecution/requestApproval', 'params': {}}, 'raw_base64': ''})
            if fault != 'raw-drift':
                for row in bad['wire']: row['raw_base64'] = base64.b64encode((json.dumps(row['message'])+'\n').encode()).decode()
            else: bad['wire'][3]['raw_base64'] = base64.b64encode(b'{"unrelated":true}\n').decode()
            with self.subTest(fault=fault): self.assertFalse(host.writer_wire(bad, 'workspace-write', result))

    def test_stderr_overflow_drains_all_bytes_but_never_proves_complete(self):
        for size in (0, 10, guest.STDERR_LIMIT, guest.STDERR_LIMIT + 4096):
            state = {'raw': bytearray(), 'total_bytes': 0, 'eof': False, 'overflow': False, 'truncated': False}
            source = io.BytesIO(b'x' * size); guest.stderr_capture(source, state)
            reader = SimpleNamespace(is_alive=lambda: False); value = guest.stderr_record(state, reader)
            with self.subTest(size=size):
                self.assertEqual(source.tell(), size); self.assertTrue(value['eof'])
                self.assertEqual(value['captured_bytes'], min(size, guest.STDERR_LIMIT))
                self.assertEqual(guest.stderr_complete(value), size <= guest.STDERR_LIMIT)
        for fault in ('overflow', 'truncated', 'eof', 'reader_finished', 'reader_error', 'total_bytes'):
            good = {'eof': True, 'reader_finished': True, 'reader_error': False, 'overflow': False,
                    'truncated': False, 'captured_bytes': 0, 'total_bytes': 0}
            good[fault] = False if fault in ('eof', 'reader_finished', 'total_bytes') else True
            with self.subTest(fault=fault): self.assertFalse(guest.stderr_complete(good))


class PrerequisiteControls(unittest.TestCase):
    def test_writer_inert_image_projection_is_typed_bidirectional_and_copy_only(self):
        base = {'Id': host.IMAGE, 'Os': 'linux', 'Architecture': 'arm64', 'Config': {'Env': ANONYMOUS_ENV, 'Labels': ANONYMOUS_LABELS}}
        fields = {**dict.fromkeys(('AttachStderr', 'AttachStdin', 'AttachStdout', 'OpenStdin', 'StdinOnce', 'Tty'), False),
                  **dict.fromkeys(('Domainname', 'Hostname', 'Image', 'User'), ''),
                  **dict.fromkeys(('Entrypoint', 'OnBuild', 'Volumes'), None)}
        for key, empty in fields.items():
            changed = copy.deepcopy(base); changed['Config'][key] = empty; original = copy.deepcopy(changed)
            with self.subTest(key=key):
                self.assertEqual(host.image_policy(base, writer=True), host.image_policy(changed, writer=True))
                self.assertEqual(host.image_policy(changed, writer=True), host.image_policy(base, writer=True))
                self.assertNotEqual(host.image_policy(base), host.image_policy(changed))
                self.assertEqual(changed, original)
            for replacement in (0, 0.0, True, None, '', [], {}, 'nonempty'):
                if type(replacement) is type(empty) and replacement == empty:
                    continue
                altered = copy.deepcopy(base); altered['Config'][key] = replacement
                with self.subTest(key=key, replacement=repr(replacement)):
                    try:
                        result = host.image_policy(altered, writer=True)
                    except host.FixtureError:
                        continue  # Existing entrypoint/on-build/volume policy refuses.
                    self.assertIn(key, result)
                    self.assertIs(type(result[key]), type(replacement)); self.assertEqual(result[key], replacement)
        for key, value in (('Cmd', []), ('WorkingDir', ''), ('Healthcheck', {}), ('UnknownEmpty', None)):
            altered = copy.deepcopy(base); altered['Config'][key] = value
            self.assertIn(key, host.image_policy(altered, writer=True))
            self.assertNotEqual(host.image_policy(altered, writer=True), host.image_policy(base, writer=True))
        for key in ('Env', 'Labels'):
            altered = copy.deepcopy(base); altered['Config'].pop(key)
            with self.subTest(missing=key), self.assertRaises(host.FixtureError): host.image_policy(altered, writer=True)
        changed = copy.deepcopy(base); changed['Config']['Env'] = ['DIFFERENT=setting']
        self.assertNotEqual(host.image_policy(changed, writer=True), host.image_policy(base, writer=True))
        changed = copy.deepcopy(base); changed['Config']['Labels'] = {'different': 'setting'}
        self.assertNotEqual(host.image_policy(changed, writer=True), host.image_policy(base, writer=True))

    def test_fixed_policy_has_no_masked_read_child_or_staging_grant(self):
        import tomllib
        argv = guest.cli_argv(1234, host.probe.boundary, 'workspace-write')
        fs = next(x for x in argv if x.startswith('permissions.probe-writer.filesystem='))
        parsed = tomllib.loads(fs)['permissions']['probe-writer']['filesystem']
        self.assertEqual(parsed, {':root': 'deny', ':minimal': 'read', '/control/workspace': 'write',
            '/control/external-canary': 'read', '/fixture/codex': 'read', '/fixture/codex-resources/bwrap': 'read'})
        self.assertIn('project_doc_max_bytes=0', argv)
        self.assertIn('shell_environment_policy.set={TMPDIR="/tmp/registry"}', argv)
        self.assertEqual(guest.cli_env('workspace-write')['TMPDIR'], '/tmp/registry')
        default = guest.cli_argv(1234, host.probe.boundary)
        self.assertNotIn('project_doc_max_bytes=0', default)
        self.assertFalse(any('shell_environment_policy.set=' in value for value in default))
        self.assertNotIn('TMPDIR', guest.cli_env(None))
        command = json.loads(guest.writer_call('external-write-refusal')['arguments'])['cmd']
        self.assertIn('IFS= read -r canary', command); self.assertIn('exit 17', command); self.assertIn('exit 18', command)

    def test_tmpfs_is_writer_only_exact_and_extra_mounts_are_rejected(self):
        root = pathlib.Path('/fixed'); uid, gid = 501, 20
        expected = 'rw,nosuid,nodev,noexec,size=16777216,mode=0700,uid=501,gid=20'
        self.assertNotIn('--tmpfs', host.create_argv(root, 'fixed', uid, gid))
        argv = host.create_argv(root, 'fixed', uid, gid, writer=True)
        self.assertEqual(argv[argv.index('--tmpfs') + 1], '/tmp:' + expected)
        value = observed(root, 'fixed', uid, gid); value['HostConfig']['Tmpfs'] = {'/tmp': expected}
        self.assertEqual(host.policy(value, root, 'fixed', uid, gid, CID, image_config=IMAGE_CONFIG, writer=True), CREATED)
        for fault in ('missing', 'extra', 'uid', 'mode', 'size', 'noexec', 'mount'):
            bad = copy.deepcopy(value)
            if fault == 'missing': bad['HostConfig']['Tmpfs'] = None
            if fault == 'extra': bad['HostConfig']['Tmpfs']['/other'] = expected
            if fault in ('uid', 'mode', 'size', 'noexec'):
                bad['HostConfig']['Tmpfs']['/tmp'] = expected.replace({'uid': 'uid=501', 'mode': 'mode=0700',
                    'size': 'size=16777216', 'noexec': 'noexec'}[fault], 'wrong')
            if fault == 'mount': bad['Mounts'].append({'Type': 'tmpfs', 'Destination': '/other'})
            with self.subTest(fault=fault), self.assertRaises(host.FixtureError):
                host.policy(bad, root, 'fixed', uid, gid, CID, image_config=IMAGE_CONFIG, writer=True)
        with self.assertRaises(host.FixtureError): host.policy(value, root, 'fixed', uid, gid, CID, image_config=IMAGE_CONFIG)

    def test_fixed_sidecar_copy_inventory_and_unsafe_assets_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp).resolve(); root.chmod(0o700)
            binary = root/'binary'; binary.write_bytes(SMALL_BINARY); binary.chmod(0o500)
            bwrap = root/'bwrap'; bwrap.write_bytes(b'fixed-offline-bwrap'); bwrap.chmod(0o500)
            with mock.patch.object(guest, 'BINARY_BYTES', len(SMALL_BINARY)), \
                    mock.patch.object(guest, 'BINARY_SHA', hashlib.sha256(SMALL_BINARY).hexdigest()), \
                    mock.patch.object(guest, 'BWRAP_BYTES', 1), \
                    mock.patch.object(guest, 'BWRAP_SHA', hashlib.sha256(b'fixed-offline-bwrap').hexdigest()):
                # Deliberate wrong byte limit refuses before returning capture.
                with self.assertRaises(host.FixtureError): host.copy_binary(bwrap, root/'wrong-size-copy', _bwrap=True)
            with mock.patch.object(guest, 'BINARY_BYTES', len(SMALL_BINARY)), \
                    mock.patch.object(guest, 'BINARY_SHA', hashlib.sha256(SMALL_BINARY).hexdigest()), \
                    mock.patch.object(guest, 'BWRAP_BYTES', len(b'fixed-offline-bwrap')), \
                    mock.patch.object(guest, 'BWRAP_SHA', hashlib.sha256(b'fixed-offline-bwrap').hexdigest()):
                sources, reference = host.capture(root, binary, bwrap)
                self.assertEqual(reference['bwrap']['sha256'], guest.BWRAP_SHA)
                host.check_capture(root/'capture', sources, bwrap=True)
                with self.assertRaises(host.FixtureError): host.check_capture(root/'capture', sources)
                linked = root/'linked'; linked.symlink_to(bwrap)
                with self.assertRaises(OSError): host.copy_binary(linked, root/'symlink-copy', _bwrap=True)
                hardlink = root/'hardlink'; os.link(bwrap, hardlink)
                with self.assertRaises(host.FixtureError): host.copy_binary(bwrap, root/'hardlink-copy', _bwrap=True)
                os.unlink(hardlink)
                bwrap.chmod(0o600); bwrap.write_bytes(b'wrong-offline-bwrap'); bwrap.chmod(0o500)
                with self.assertRaises(host.FixtureError): host.copy_binary(bwrap, root/'wrong-hash-copy', _bwrap=True)

    def test_writer_sidecar_selection_refused_before_fixture_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            for case, bwrap in [('workspace-write', None), (None, root/'bwrap')]:
                args = SimpleNamespace(native_workspace_case=case, bwrap_path=bwrap, evidence_root=root,
                                       binary_path=root/'binary', endpoint='unix:///fixed/socket')
                with self.subTest(case=case), self.assertRaises(host.FixtureError): host.run(args)
                self.assertEqual(list(root.iterdir()), [])

    def test_prerequisite_raw_unknown_timeout_and_false_exit_never_pass(self):
        def stream(raw):
            return {'raw_base64': base64.b64encode(raw).decode(), 'captured_prefix_sha256': hashlib.sha256(raw).hexdigest(),
                'captured_bytes': len(raw), 'total_bytes': len(raw), 'eof': True, 'overflow': False,
                'truncated': False, 'reader_finished': True, 'reader_error': False}
        flags = b'--argv0 --new-session --die-with-parent --ro-bind --dev --bind --unshare-user --unshare-pid --as-pid-1 --unshare-ipc --unshare-net --proc --cap-drop'
        def phase(argv, stdout, stderr):
            return {'argv': argv, 'pid': 123, 'wait': 'observed', 'timeout': False, 'complete': True, 'exit_code': 0,
                    'stdout': stream(stdout), 'stderr': stream(stderr)}
        value = {'scope': 'fixed-bwrap-prerequisites-only', 'passed': True, 'native_qualified': False,
            'canary_preserved': True, 'postimage_confirmed': True,
            'help': phase(['/fixture/codex-resources/bwrap', '--help'], flags, b''),
            'probe': phase(guest.prerequisite_argv(), b'namespace-prerequisite-ok\n',
                          b'/bin/sh: 1: cannot create /control/prerequisite/canary: Read-only file system\n')}
        self.assertTrue(guest.prerequisites_confirmed(value))
        for fault in ('raw', 'overflow', 'eof', 'timeout', 'wait', 'false-exit', 'command', 'help', 'denial', 'canary'):
            bad = copy.deepcopy(value)
            if fault == 'raw': bad['probe']['stdout']['raw_base64'] = base64.b64encode(b'wrong').decode()
            if fault == 'overflow': bad['probe']['stdout']['overflow'] = True
            if fault == 'eof': bad['probe']['stdout']['eof'] = False
            if fault == 'timeout': bad['probe']['timeout'] = True
            if fault == 'wait': bad['probe']['wait'] = 'terminated'
            if fault == 'false-exit': bad['probe']['exit_code'] = False
            if fault == 'command': bad['probe']['argv'][-1] = 'other-command'
            if fault == 'help': bad['help']['stdout'] = stream(b'--unshare-user --unshare-net')
            if fault == 'denial': bad['probe']['stderr'] = stream(b'namespace failed\n')
            if fault == 'canary': bad['canary_preserved'] = False
            with self.subTest(fault=fault): self.assertFalse(guest.prerequisites_confirmed(bad))

    def test_bounded_fixed_diagnostic_has_separate_raw_streams_and_timeout(self):
        for timeout in (False, True):
            child = SimpleNamespace(pid=123, stdout=io.BytesIO(b'fixed-stdout'), stderr=io.BytesIO(b'fixed-stderr'), kill=mock.Mock())
            child.wait = mock.Mock(side_effect=[subprocess.TimeoutExpired(['fixed'], 5), -9] if timeout else [0])
            with self.subTest(timeout=timeout), mock.patch.object(guest.subprocess, 'Popen', return_value=child) as spawn:
                result = guest.bounded_command(['fixed'])
                self.assertEqual(result['complete'], not timeout)
                self.assertEqual(base64.b64decode(result['stdout']['raw_base64']), b'fixed-stdout')
                self.assertEqual(base64.b64decode(result['stderr']['raw_base64']), b'fixed-stderr')
                self.assertEqual(child.kill.call_count, int(timeout))
                self.assertEqual(spawn.call_args.kwargs['stdin'], subprocess.DEVNULL)
                self.assertEqual(spawn.call_args.kwargs['pass_fds'], ())
