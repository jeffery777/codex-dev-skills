"""Anonymous probe contract tests; HTTP is in-memory, with no native/provider IO."""
import email.message
import importlib.util
import io
import json
import pathlib
import tempfile
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('app_server_probe_under_test', ROOT / 'scripts/verify-model-app-server.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.control = self.root / 'control'
        self.control.mkdir()
        self.receipt = {'requests': [], 'accepted_dynamic_calls': 0, 'positive_control': False}
        # Capture handler without binding any port, let alone invoking a provider.
        with mock.patch.object(probe.http.server, 'HTTPServer') as constructor:
            probe.server(self.root, 'code_mode', self.control, self.receipt)
        self.handler_class = constructor.call_args.args[1]
        self.assertEqual(constructor.call_args.args[0], ('127.0.0.1', 0))

    def post(self, value=None, *, raw=None, path='/v1/responses', headers=None):
        if raw is None:
            raw = json.dumps(value if value is not None else {'input': [], 'tools': []}).encode()
        handler = object.__new__(self.handler_class)
        handler.path = path
        handler.headers = email.message.Message()
        handler.headers['Content-Length'] = str(len(raw))
        for key, val in (headers or {}).items():
            if key in handler.headers:
                del handler.headers[key]
            handler.headers[key] = val
        handler.rfile, handler.wfile = io.BytesIO(raw), io.BytesIO()
        handler.send_response = mock.Mock()
        handler.send_header = mock.Mock()
        handler.end_headers = mock.Mock()
        handler.send_error = mock.Mock()
        handler.do_POST()
        return handler

    def output(self, call_id, text, kind='function_call_output'):
        return {'input': [{'type': kind, 'call_id': call_id, 'output': text}], 'tools': []}

    def seed_positive(self):
        first = self.post()
        first.send_response.assert_called_once_with(200)
        self.receipt['accepted_dynamic_calls'] = 1
        second = self.post(self.output('boundary-positive-1', probe.TOKEN))
        second.send_response.assert_called_once_with(200)
        return second

    def test_code_mode_forces_public_custom_tool_carrier(self):
        call = probe.negative_call('code_mode', self.control)
        self.assertEqual(call['type'], 'custom_tool_call')
        self.assertEqual((call['namespace'], call['name']), ('functions', 'exec'))
        self.assertNotIn('arguments', call)
        self.assertEqual(call['input'], 'text(await tools.exec_command({cmd:"printf synthetic-forbidden > forbidden-marker"}))')
        self.seed_positive()
        self.assertEqual(self.receipt['requests'][1]['forced_call'], call)
        self.assertTrue(self.receipt['positive_control'])

    def test_fixed_negative_calls_are_closed_inventory_and_payloads(self):
        for case in probe.CASES:
            with self.subTest(case=case):
                call = probe.negative_call(case, self.control)
                self.assertEqual(call['call_id'], 'boundary-negative-1')
                self.assertIn(call['type'], {'function_call', 'custom_tool_call'})
                self.assertNotIn('Authorization', json.dumps(call))
                self.assertNotIn('https:', json.dumps(call))
        self.assertEqual(json.loads(probe.negative_call('request_permissions', self.control)['arguments']),
                         {'permissions': {'network': {'enabled': True}}})
        self.assertEqual(probe.negative_call('unknown_dynamic', self.control)['name'], 'unconfigured_packet_probe')
        with self.assertRaises(probe.ProbeError):
            probe.negative_call('planner-selected-command', self.control)

    def test_authorization_wrong_route_encoding_and_oversize_reject_before_recording(self):
        for kwargs in ({'headers': {'Authorization': 'Bearer anonymous'}},
                {'path': '/v1/chat/completions'}, {'headers': {'Content-Encoding': 'gzip'}},
                {'raw': b'x' * (probe.manifest.MAX_REQUEST_BYTES + 1)}):
            with self.subTest(kwargs=list(kwargs)):
                handler = self.post(**kwargs)
                handler.send_error.assert_called_once_with(422)
                handler.send_response.assert_not_called()
                self.assertEqual(self.receipt['requests'], [])
                self.assertEqual(list(self.root.glob('request-*.json')), [])

    def test_truncated_request_duplicate_keys_and_nonfinite_reject(self):
        for raw, headers in [(b'{}', {'Content-Length': '999'}),
                (b'{"input":[],"input":[]}', {}), (b'{"input":[],"x":NaN}', {})]:
            with self.subTest(raw=raw):
                handler = self.post(raw=raw, headers=headers)
                handler.send_error.assert_called_once_with(422)
                self.assertEqual(self.receipt['requests'], [])

    def test_positive_requires_one_exact_output_and_callback_confirmation(self):
        self.post()
        for request in ({'input': []}, self.output('wrong-call-id', probe.TOKEN),
                self.output('boundary-positive-1', probe.TOKEN, 'custom_tool_call_output'),
                {'input': self.output('boundary-positive-1', probe.TOKEN)['input'] * 2}):
            with self.subTest(request=request):
                # Failed requests count as attempts; reset only fixture bookkeeping
                # here to test independently without reconstructing its call table.
                del self.receipt['requests'][1:]
                handler = self.post(request)
                handler.send_error.assert_called_once_with(422)
                self.assertFalse(self.receipt['positive_control'])
        del self.receipt['requests'][1:]
        handler = self.post(self.output('boundary-positive-1', probe.TOKEN))
        handler.send_error.assert_called_once_with(422)
        self.assertFalse(self.receipt['positive_control'])

    def test_negative_requires_exact_custom_call_output_and_known_denial(self):
        self.seed_positive()
        for request in ({'input': []}, self.output('boundary-negative-1', 'unsupported custom tool call: functions.exec'),
                {'input': self.output('boundary-negative-1', 'unsupported custom tool call: functions.exec', 'custom_tool_call_output')['input'] * 2}):
            with self.subTest(request=request):
                del self.receipt['requests'][2:]
                handler = self.post(request)
                handler.send_error.assert_called_once_with(422)
                self.assertNotIn('negative_outcome', self.receipt)
        del self.receipt['requests'][2:]
        handler = self.post(self.output('boundary-negative-1', 'unsupported custom tool call: functions.exec', 'custom_tool_call_output'))
        handler.send_response.assert_called_once_with(200)
        self.assertEqual(self.receipt['negative_outcome'], 'unsupported-handler')

    def test_generic_negative_error_is_unknown(self):
        self.seed_positive()
        handler = self.post(self.output('boundary-negative-1', 'permission denied', 'custom_tool_call_output'))
        handler.send_response.assert_called_once_with(200)
        self.assertEqual(self.receipt['negative_outcome'], 'unknown')

    def test_sse_has_three_fixed_events_and_request_limit(self):
        first = self.post()
        payload = first.wfile.getvalue().decode()
        self.assertEqual([line for line in payload.splitlines() if line.startswith('event:')],
            ['event: response.created', 'event: response.output_item.done', 'event: response.completed'])
        self.receipt['requests'].extend([{}, {}])
        fourth = self.post()
        fourth.send_error.assert_called_once_with(422)
        self.assertEqual(self.receipt['fixture_error'], 'request-limit')

    def test_dynamic_callback_has_bound_identity_and_never_replays(self):
        receipt = {'accepted_dynamic_calls': 0}
        identities = {'threadId': 'thread-1', 'turnId': 'turn-1'}
        callback = probe.fixed_callback(receipt, identities)
        params = dict(identities, callId='boundary-positive-1', arguments={}, tool='packet_probe')
        for key, value in [('threadId', 'other'), ('turnId', 'other'),
                ('callId', 'other'), ('arguments', {'command': 'forbidden'})]:
            with self.subTest(key=key), self.assertRaises(probe.ProbeError):
                callback(dict(params, **{key: value}))
            self.assertEqual(receipt['accepted_dynamic_calls'], 0)
        self.assertEqual(callback(params), {'success': True, 'contentItems': [{'type': 'inputText', 'text': probe.TOKEN}]})
        self.assertEqual(receipt['accepted_dynamic_calls'], 1)
        with self.assertRaises(probe.ProbeError):
            callback(params)
        self.assertEqual(receipt['accepted_dynamic_calls'], 1)
        with self.assertRaises(probe.ProbeError):
            probe.fixed_callback({'accepted_dynamic_calls': 0}, {})(params)

    def passing_receipt(self):
        return {'positive_control': True, 'accepted_dynamic_calls': 1,
            'negative_outcome': 'unsupported-handler', 'turn_status': 'completed',
            'sentinel_preserved': True, 'client_unchanged': True,
            'version_verified': True, 'binary_unchanged': True,
            'fixture_stopped': True,
            'process_readback': {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}}

    def test_pass_requires_version_binary_known_close_and_no_fixture_failure(self):
        good = self.passing_receipt()
        self.assertTrue(probe.passed(good))
        mutations = [('version_verified', False), ('binary_unchanged', False),
            ('positive_control', False), ('accepted_dynamic_calls', 0),
            ('fixture_stopped', False),
            ('accepted_dynamic_calls', True), ('negative_outcome', 'unknown'),
            ('turn_status', 'failed'), ('sentinel_preserved', False), ('client_unchanged', False),
            ('process_readback', {'protocol': 'unknown', 'direct_child': 'unknown', 'descendants': 'unknown'}),
            ('process_readback', dict(good['process_readback'], exit_code=1)),
            ('process_readback', dict(good['process_readback'], exit_code=False)),
            ('failure_class', 'launch_failed'), ('fixture_error', 'invalid_request')]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                self.assertFalse(probe.passed(dict(good, **{key: value})))
        for field in good:
            with self.subTest(missing=field):
                incomplete = dict(good); del incomplete[field]
                self.assertFalse(probe.passed(incomplete))

    def test_code_mode_disabled_denial_is_exact_and_case_specific(self):
        call = probe.negative_call('code_mode', self.control)
        self.assertEqual(probe.deny_outcome('code-mode host is disabled', call, 'code_mode'), 'code-mode-host-disabled')
        for text in ('code-mode host is disabled\n', 'prefix code-mode host is disabled', 'permission denied'):
            self.assertEqual(probe.deny_outcome(text, call, 'code_mode'), 'unknown')
        self.assertEqual(probe.deny_outcome('code-mode host is disabled', call, 'exec_command'), 'unknown')

    def test_positive_token_requires_exact_value(self):
        self.post()
        self.receipt['accepted_dynamic_calls'] = 1
        handler = self.post(self.output('boundary-positive-1', 'prefix-' + probe.TOKEN))
        handler.send_error.assert_called_once_with(422)
        self.assertFalse(self.receipt['positive_control'])

    def test_version_drift_saves_failure_without_starting_app_server(self):
        executable = self.root / 'anonymous-native'
        executable.write_bytes(b'never executed')
        with mock.patch.object(probe, 'server'), \
                mock.patch.object(probe.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=b'codex-cli 0.159.4\n')), \
                mock.patch.object(probe.transport, 'Session') as session:
            root, receipt = probe.run_case(self.root, executable, 'code_mode')
        session.assert_not_called()
        self.assertFalse(receipt['passed'])
        self.assertNotIn('version_verified', receipt)
        self.assertEqual(json.loads((root / 'receipt.json').read_text()), receipt)

    def test_run_case_close_unknown_overrides_success_and_preserves_anonymous_settings(self):
        executable = self.root / 'anonymous-native'
        executable.write_bytes(b'never executed')
        captured = {}
        def service(root, case, control, receipt):
            captured['receipt'] = receipt
            return mock.Mock(server_port=12345)
        session = mock.Mock()
        def request(method, params):
            if method == 'initialize': return {}
            if method == 'thread/start':
                return {'thread': {'id': 'thread-1'}, 'model': 'gpt-6-sol',
                    'modelProvider': 'fixture', 'cwd': params['cwd'], 'approvalPolicy': 'never',
                    'activePermissionProfile': {'id': 'probe', 'extends': None}}
            if method == 'turn/start': return {'turn': {'id': 'turn-1'}}
            self.fail('unexpected request')
        session.request.side_effect = request
        session.close.return_value = {'protocol': 'unknown', 'direct_child': 'unknown', 'descendants': 'unknown'}
        def completion():
            captured['receipt'].update(positive_control=True, accepted_dynamic_calls=1, negative_outcome='unsupported-handler')
            return {'method': 'turn/completed', 'params': {'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'completed'}}}
        session.notification.side_effect = completion
        with mock.patch.object(probe, 'server', side_effect=service), \
                mock.patch.object(probe.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=(probe.VERSION+'\n').encode())), \
                mock.patch.object(probe.transport, 'Session', return_value=session) as constructor:
            root, receipt = probe.run_case(self.root, executable, 'code_mode')
        self.assertFalse(receipt['passed'])
        self.assertTrue(receipt['positive_control'])
        self.assertEqual(json.loads((root / 'receipt.json').read_text()), receipt)
        session.close.assert_called_once()
        self.assertEqual(constructor.call_args.kwargs['fixed_tool'], 'packet_probe')
        env = constructor.call_args.kwargs['env']
        self.assertEqual(set(env), {'PATH', 'HOME', 'CODEX_HOME', 'NO_PROXY'})
        self.assertTrue(pathlib.Path(env['CODEX_HOME']).is_dir())
        self.assertIn('shell_environment_policy.inherit="none"', constructor.call_args.args[0])
        self.assertIn('permissions.probe.network.enabled=false', constructor.call_args.args[0])
        requests = session.request.call_args_list
        self.assertEqual(requests[0].args[1]['capabilities'], {'experimentalApi': True})
        self.assertEqual(requests[1].args[1]['environments'], [])
        self.assertEqual(requests[2].args[1]['environments'], [])
        self.assertEqual(requests[1].args[1]['dynamicTools'][0]['name'], 'packet_probe')
        self.assertFalse(requests[1].args[1]['allowProviderModelFallback'])

    def guard_case(self, *, configuration=None, completion=None):
        """Exercise run_case guards with anonymous in-memory Session/provider."""
        executable = self.root / 'anonymous-guard-native'
        executable.write_bytes(b'never executed')
        captured = {}
        def service(root, case, control, receipt):
            captured['receipt'] = receipt
            return mock.Mock(server_port=12345)
        session = mock.Mock()
        def request(method, params):
            if method == 'initialize': return {}
            if method == 'thread/start':
                started = {'thread': {'id': 'thread-1'}, 'model': 'gpt-6-sol',
                    'modelProvider': 'fixture', 'cwd': params['cwd'], 'approvalPolicy': 'never',
                    'activePermissionProfile': {'id': 'probe', 'extends': None}}
                if configuration is not None:
                    started.update(configuration)
                return started
            if method == 'turn/start': return {'turn': {'id': 'turn-1'}}
            self.fail('unexpected request')
        session.request.side_effect = request
        session.close.return_value = {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}
        def notification():
            captured['receipt'].update(positive_control=True, accepted_dynamic_calls=1, negative_outcome='unsupported-handler')
            params = {'threadId': 'thread-1', 'turn': {'id': 'turn-1', 'status': 'completed'}}
            if completion is not None:
                params.update(completion)
            return {'method': 'turn/completed', 'params': params}
        session.notification.side_effect = notification
        with mock.patch.object(probe, 'server', side_effect=service), \
                mock.patch.object(probe.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=(probe.VERSION+'\n').encode())), \
                mock.patch.object(probe.transport, 'Session', return_value=session):
            root, receipt = probe.run_case(self.root, executable, 'code_mode')
        self.assertEqual(json.loads((root / 'receipt.json').read_text()), receipt)
        session.close.assert_called_once()
        return receipt, session

    def test_thread_configuration_drift_never_starts_turn_and_preserves_receipt(self):
        changes = [('model', 'gpt-other'), ('modelProvider', 'other-provider'),
            ('cwd', str(self.root / 'other')), ('approvalPolicy', 'on-request'),
            ('activePermissionProfile', {'id': 'other', 'extends': None}),
            ('activePermissionProfile', {'id': 'probe', 'extends': 'broad'}),
            ('activePermissionProfile', {'id': 'probe'}), ('activePermissionProfile', None)]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                receipt, session = self.guard_case(configuration={key: value})
                self.assertFalse(receipt['passed'])
                self.assertIn('failure_class', receipt)
                self.assertEqual(receipt['thread_configuration'][key], value)
                self.assertEqual([call.args[0] for call in session.request.call_args_list], ['initialize', 'thread/start'])
                session.notification.assert_not_called()
                self.assertNotIn('turn_status', receipt)

    def test_completion_thread_or_turn_drift_fails_even_with_positive_control(self):
        for change in ({'threadId': 'other-thread'}, {'threadId': None},
                {'turn': {'id': 'other-turn', 'status': 'completed'}},
                {'turn': {'status': 'completed'}}):
            with self.subTest(change=change):
                receipt, session = self.guard_case(completion=change)
                self.assertTrue(receipt['positive_control'])
                self.assertFalse(receipt['passed'])
                self.assertIn('failure_class', receipt)
                self.assertNotIn('turn_status', receipt)
                self.assertEqual([call.args[0] for call in session.request.call_args_list], ['initialize', 'thread/start', 'turn/start'])
                session.notification.assert_called_once()

    def test_exact_thread_and_completion_identities_allow_fixture_pass(self):
        receipt, session = self.guard_case()
        self.assertTrue(receipt['passed'])
        self.assertEqual(receipt['turn_status'], 'completed')
        self.assertFalse(receipt['production_qualified'])
        self.assertFalse(receipt['repository_completion'])

    def test_anonymous_connections_do_not_allocate_unbounded_workers(self):
        # Use the actual server class, suppress socket bind/activation, and
        # replace only request handling. Two accepted requests stay synchronous.
        with mock.patch.object(probe.http.server.HTTPServer, 'server_bind'), \
                mock.patch.object(probe.http.server.HTTPServer, 'server_activate'):
            service = probe.server(self.root, 'code_mode', self.root, {'requests': []})
        self.addCleanup(service.server_close)
        with mock.patch.object(service, 'finish_request') as finish, \
                mock.patch.object(service, 'shutdown_request') as shutdown, \
                mock.patch('threading.Thread') as thread:
            for port in (1, 2):
                service.process_request(mock.Mock(), ('127.0.0.1', port))
            self.assertEqual(finish.call_count, 2)
            self.assertEqual(shutdown.call_count, 2)
            thread.assert_not_called()

    def test_startup_failure_still_saves_sanitized_nonpassing_receipt(self):
        executable = self.root / 'anonymous-native'
        executable.write_bytes(b'never executed')
        with mock.patch.object(probe, 'server') as server, \
                mock.patch.object(probe.subprocess, 'run', return_value=mock.Mock(returncode=0, stdout=(probe.VERSION+'\n').encode())), \
                mock.patch.object(probe.transport, 'Session', side_effect=probe.transport.TransportError('launch_failed')):
            root, receipt = probe.run_case(self.root, executable, 'code_mode')
        saved = json.loads((root / 'receipt.json').read_text())
        self.assertEqual(saved, receipt)
        self.assertFalse(saved['passed'])
        self.assertFalse(saved['production_qualified'])
        self.assertFalse(saved['repository_completion'])
        self.assertEqual(saved['failure_class'], 'launch_failed')
        self.assertFalse(saved['positive_control'])
        server.return_value.shutdown.assert_called_once()
        server.return_value.server_close.assert_called_once()

    def test_continuous_input_cannot_extend_request_deadline(self):
        # Real BufferedReader keeps requesting bytes while the fake peer makes
        # progress. Each byte advances time; activity never resets the budget.
        clock = [0]
        peer = mock.Mock()
        def drip(buffer):
            clock[0] += 1
            buffer[0] = ord('x')
            return 1
        peer.recv_into.side_effect = drip
        reader = io.BufferedReader(probe.DeadlineReader(peer, 5))
        with mock.patch.object(probe.time, 'monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(TimeoutError):
                reader.read(100)
        self.assertEqual(peer.recv_into.call_count, 5)
        self.assertEqual([call.args[0] for call in peer.settimeout.call_args_list], [5, 4, 3, 2, 1])

    def test_output_shares_request_deadline_and_does_not_restart_budget(self):
        peer = mock.Mock()
        writer = probe.DeadlineWriter(peer, 5)
        with mock.patch.object(probe.time, 'monotonic', side_effect=[4, 5]):
            self.assertEqual(writer.write(b'first'), 5)
            with self.assertRaises(TimeoutError):
                writer.write(b'late')
        peer.sendall.assert_called_once_with(b'first')
        peer.settimeout.assert_called_once_with(1)

    def test_unconfirmed_stop_is_bounded_and_cannot_pass(self):
        service, serving, control = mock.Mock(), mock.Mock(), mock.Mock()
        control.is_alive.return_value = True
        with mock.patch.object(probe.threading, 'Thread', return_value=control):
            self.assertFalse(probe.stop_fixture(service, serving))
        control.join.assert_called_once_with(timeout=2)
        serving.join.assert_called_once_with(timeout=2)
        service.server_close.assert_called_once()
        self.assertFalse(probe.passed(dict(self.passing_receipt(), fixture_stopped=False)))

    def test_failed_server_thread_start_closes_without_blocking_shutdown_and_saves_receipt(self):
        executable = self.root / 'anonymous-native'
        executable.write_bytes(b'never executed')
        with mock.patch.object(probe, 'server') as server, \
                mock.patch.object(probe.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = RuntimeError('synthetic-start-failure')
            root, receipt = probe.run_case(self.root, executable, 'code_mode')
        self.assertEqual(json.loads((root / 'receipt.json').read_text()), receipt)
        self.assertFalse(receipt['passed'])
        self.assertFalse(receipt['fixture_stopped'])
        self.assertEqual(receipt['failure_class'], 'RuntimeError')
        server.return_value.shutdown.assert_not_called()
        server.return_value.server_close.assert_called_once()

    def test_unconfirmed_or_failed_stop_still_saves_failure_receipt(self):
        for outcome in (False, OSError('synthetic-close-failure')):
            with self.subTest(outcome=type(outcome).__name__), \
                    mock.patch.object(probe, 'stop_fixture', side_effect=outcome if isinstance(outcome, Exception) else None,
                                      return_value=False):
                receipt, _ = self.guard_case()
                self.assertFalse(receipt['fixture_stopped'])
                self.assertFalse(receipt['passed'])


if __name__ == '__main__':
    unittest.main()
