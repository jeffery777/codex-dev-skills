"""Rejection and durable no-replay tests; no Docker, model, or credentials."""
import copy
import importlib.util
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import model_packet_store as packets

spec = importlib.util.spec_from_file_location('broker_probe', ROOT / 'scripts/verify-model-broker.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.store = packets.PacketStore(self.root, 'test-packet')
        self.store.prepare('a' * 64)
        self.dispatch = mock.Mock(return_value={'worker_result': 'observed'})
        self.broker = probe.Broker(self.store, 'b' * 64, self.dispatch)
        self.protocol = probe.Protocol(self.broker)

    def ready(self):
        self.protocol.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2025-03-26', 'capabilities': {},
                'clientInfo': {'name': 'test-client', 'version': '1'}}})
        self.protocol.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def call(self, **params):
        return self.protocol.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'run', 'arguments': {'cmd': probe.WORKER_COMMAND}, **params}})

    def test_init_and_fixed_tool_schema_required_before_dispatch(self):
        with self.assertRaisesRegex(probe.ProbeError, 'initialization-required'):
            self.call()
        self.ready()
        for params in [{'name': 'other'}, {'mount': '/'}, {'argv': ['sh']}, {'credentials': '/home'}]:
            with self.subTest(params=params), self.assertRaises(probe.ProbeError):
                self.call(**params)
        with self.assertRaises(probe.ProbeError):
            self.protocol.handle({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/list', 'params': {'cursor': 'arbitrary'}})
        self.dispatch.assert_not_called()
        self.assertEqual(self.store.read_checkpoint()[0]['attempts'], [])

    def test_model_cannot_supply_host_execution_parameters(self):
        self.ready()
        for key, value in [('argv', ['/bin/sh']), ('mount', '/'), ('engine', 'remote'),
                ('socket', '/var/run/docker.sock'), ('image', 'other'),
                ('credentials', '/home'), ('cwd', '../control'), ('env', {'TOKEN': 'secret'})]:
            with self.subTest(key=key), self.assertRaisesRegex(probe.ProbeError, 'only-cmd'):
                self.call(arguments={'cmd': probe.WORKER_COMMAND, key: value})
        self.dispatch.assert_not_called()
        self.assertEqual(self.store.read_checkpoint()[0]['generation'], 0)

    def test_invalid_command_and_unapproved_packet_do_not_claim(self):
        self.ready()
        for value in ['', ' ', None, [], 7, 'a\x00b', 'x' * 4097, '中' * 1400,
                'docker run -v /:/host image', 'cat /control/sentinel']:
            with self.subTest(value=repr(value)[:60]), self.assertRaises(probe.ProbeError):
                self.call(arguments={'cmd': value})
        self.assertEqual(self.store.read_checkpoint()[0]['attempts'], [])

    def test_transport_metadata_is_ignored_without_weakening_tool_arguments(self):
        self.protocol.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2025-03-26', 'capabilities': {},
                'clientInfo': {'name': 'test-client', 'version': '1'},
                '_meta': {'traceparent': 'synthetic'}}})
        self.protocol.handle({'jsonrpc': '2.0', 'method': 'notifications/initialized',
            'params': {'_meta': {}}})
        result = self.protocol.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list',
            'params': {'_meta': {'traceparent': 'synthetic'}}})
        self.assertEqual(len(result['tools']), 1)
        with self.assertRaisesRegex(probe.ProbeError, 'only-cmd'):
            self.call(arguments={'cmd': probe.WORKER_COMMAND, 'argv': ['sh']},
                _meta={'traceparent': 'synthetic'})
        with self.assertRaisesRegex(probe.ProbeError, 'read-only-call'):
            self.call(_meta={'openai/readOnly': True})
        for metadata in [[], 'value', {'traceparent': 'x' * 4097}]:
            with self.subTest(metadata=type(metadata).__name__), self.assertRaises(probe.ProbeError):
                self.call(_meta=metadata)
        self.call(_meta={'cmd': 'attempted-override', 'mount': '/'})
        self.dispatch.assert_called_once_with()

    def test_lost_response_cannot_repeat_dispatch_after_reopen(self):
        self.ready()
        self.call()  # Drop the response, as if the client disconnected.
        fresh_store = packets.PacketStore(self.root, 'test-packet')
        fresh = probe.Broker(fresh_store, 'b' * 64, self.dispatch)
        with self.assertRaisesRegex(probe.ProbeError, 'replay-rejected'):
            fresh.call({'cmd': probe.WORKER_COMMAND})
        self.dispatch.assert_called_once_with()
        ledger, checkpoint = fresh_store.read_checkpoint()
        self.assertEqual(ledger['attempts'][0]['status'], 'unknown')
        self.assertEqual(ledger['generation'], 1)
        self.assertEqual(checkpoint, b'')

    def test_dispatch_failure_preserves_claim_and_refuses_next_call(self):
        self.ready()
        self.dispatch.side_effect = TimeoutError('reply lost')
        with self.assertRaises(TimeoutError):
            self.call()
        with self.assertRaisesRegex(probe.ProbeError, 'replay-rejected'):
            self.call()
        self.dispatch.assert_called_once_with()
        self.assertEqual(self.store.read_checkpoint()[0]['attempts'][0]['status'], 'unknown')

    def test_json_and_rpc_envelope_reject_ambiguous_or_oversized_input(self):
        for raw in [b'{"id":1,"id":2}', b'{"cmd":NaN}', b' ' * 32769]:
            with self.subTest(raw=raw[:60]), self.assertRaises(ValueError):
                probe.decode(raw)
        for envelope in [[], {'jsonrpc': '1.0', 'id': 1, 'method': 'initialize'},
                {'jsonrpc': '2.0', 'id': True, 'method': 'initialize'},
                {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'argv': ['sh']}]:
            with self.subTest(envelope=envelope), self.assertRaises(ValueError):
                self.protocol.handle(envelope)
        self.dispatch.assert_not_called()


class BoundaryTests(unittest.TestCase):
    def test_provider_input_canary_is_detected_before_diagnostic_projection(self):
        receipt = {'requests': [], 'canary_in_provider_request': False}
        with mock.patch.object(probe.http.server, 'ThreadingHTTPServer',
                side_effect=lambda address, handler: handler):
            handler_class = probe.fixture_server(receipt, 'synthetic-canary-value')
        broker = {'type': 'function', 'name': 'run', 'description': probe.TOOL_DESCRIPTION,
            'parameters': {'properties': {'cmd': {'type': 'string'}}}}
        payload = probe.canonical({'tools': [broker],
            'input': [{'type': 'message', 'content': 'synthetic-canary-value'}]})
        handler = handler_class.__new__(handler_class)
        handler.path = '/v1/responses'
        handler.headers = {'Content-Length': str(len(payload))}
        handler.rfile, handler.wfile = io.BytesIO(payload), io.BytesIO()
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.do_POST()
        self.assertTrue(receipt['canary_in_provider_request'])
        self.assertEqual(len(receipt['requests']), 1)
        self.assertNotIn('synthetic-canary-value', probe.canonical(receipt).decode())

    def test_tool_selection_uses_observed_namespace_and_refuses_unknown_tools(self):
        broker = {'type': 'function', 'name': 'actual_runtime_name',
            'description': probe.TOOL_DESCRIPTION,
            'parameters': {'type': 'object', 'properties': {'cmd': {'type': 'string'}}}}
        tools = [{'type': 'namespace', 'name': 'actual_runtime_namespace', 'tools': [broker]}]
        self.assertEqual(probe.select_tools(tools), (broker, 'actual_runtime_namespace'))
        # Observed generic CLI catalog when the sole MCP server is configured.
        helpers = [{'type': 'function', 'name': name} for name in (
            'list_mcp_resources', 'list_mcp_resource_templates', 'read_mcp_resource', 'request_user_input')]
        self.assertEqual(probe.select_tools(helpers + tools), (broker, 'actual_runtime_namespace'))
        for catalog in [[], tools + [broker], tools + [{'type': 'function', 'name': 'exec_command'}],
                tools + [{'type': 'custom', 'name': 'apply_patch'}], tools + [{'type': 'web_search'}],
                tools + [{'type': 'namespace', 'name': 'foreign_mcp', 'tools': helpers}]]:
            with self.subTest(catalog=catalog), self.assertRaises(probe.ProbeError):
                probe.select_tools(catalog)

    def test_wire_shape_diagnostic_omits_values_and_bounds_keys(self):
        shape = probe.rpc_shape({'jsonrpc': '2.0', 'id': 'secret-value', 'method': 'tools/call',
            'params': {'name': 'secret-value', 'arguments': {'cmd': 'secret-value'},
                '_meta': {'traceparent': 'secret-value'}}})
        self.assertNotIn('secret-value', repr(shape))
        self.assertEqual(shape['params_keys'], ['_meta', 'arguments', 'name'])
        shape = probe.rpc_shape({str(i) * 100: 'secret' for i in range(32)})
        self.assertLessEqual(len(shape['envelope_keys']), 16)
        self.assertTrue(all(len(key) <= 80 for key in shape['envelope_keys']))

    def test_client_configuration_symlink_is_not_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            client = pathlib.Path(directory).resolve()
            (client / '.codex').symlink_to(client / 'does-not-exist')
            with self.assertRaisesRegex(probe.ProbeError, 'unexpected-client-configuration'):
                probe.audit_client_directory(client)

    def test_worker_readback_rejects_hidden_mount_or_running_writer(self):
        workspace = pathlib.Path('/private/tmp/synthetic-worker')
        value = {'Image': probe.IMAGE, 'HostConfig': {
            'NetworkMode': 'none', 'ReadonlyRootfs': True, 'Privileged': False,
            'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'], 'PidsLimit': 32,
            'Memory': 134217728, 'MemorySwap': 134217728, 'NanoCpus': 1000000000,
            'Tmpfs': {'/tmp': 'rw,noexec,nosuid,nodev,size=8m'}, 'AutoRemove': False,
            'RestartPolicy': {'Name': 'no'}}, 'Config': {
            'User': '65534:65534', 'WorkingDir': '/workspace', 'Entrypoint': ['/bin/sh'],
            'Cmd': ['-c', probe.WORKER_COMMAND], 'Healthcheck': {'Test': ['NONE']}, 'Env': []},
            'State': {'Running': False, 'Status': 'exited', 'ExitCode': 0, 'OOMKilled': False,
                'FinishedAt': '2026-10-02T00:00:00Z'},
            'Mounts': [{'Type': 'bind', 'Source': str(workspace), 'Destination': '/workspace', 'RW': True}]}
        probe.validate_inspect(value, workspace, {}, stopped=True)
        for section, key, changed in [('State', 'Running', True), ('State', 'ExitCode', 9),
                ('HostConfig', 'Privileged', True), ('HostConfig', 'NetworkMode', 'host'),
                ('HostConfig', 'ReadonlyRootfs', False), ('HostConfig', 'PidsLimit', 0),
                ('Config', 'Env', ['BROKER_SYNTHETIC_CANARY=synthetic'])]:
            altered = copy.deepcopy(value)
            altered[section][key] = changed
            with self.subTest(section=section, key=key), self.assertRaises(probe.ProbeError):
                probe.validate_inspect(altered, workspace, {}, stopped=True)
        for mount in [{'Type': 'volume', 'Destination': '/data'},
                {'Type': 'bind', 'Source': '/', 'Destination': '/host'},
                {'Type': 'tmpfs', 'Destination': '/control'}]:
            altered = copy.deepcopy(value)
            altered['Mounts'].append(mount)
            with self.subTest(mount=mount), self.assertRaises(probe.ProbeError):
                probe.validate_inspect(altered, workspace, {}, stopped=True)


if __name__ == '__main__':
    unittest.main()
