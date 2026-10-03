"""Bounded fixture counterexamples; no Codex, real provider, or engine calls."""
import copy
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('model_tool_boundary',
    pathlib.Path(__file__).resolve().parents[1] / 'scripts/verify-model-tool-boundary.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def successful_receipt(observation=False):
    states = {name: False for name in probe.REQUIRED_DISABLED_FEATURES}
    states['unified_exec'] = observation
    return {**probe.control_contract(observation), 'case': 'mcp-excluded',
        'cli_version': probe.CLI_VERSION, 'requested_disabled_features': {
            name: False for name in probe.REQUIRED_DISABLED_FEATURES},
        'effective_feature_states': states, 'strict_required_false_satisfied': not observation,
        'handler_inventory_complete': False, 'production_qualified': False, 'repository_completion': False,
        'unknown': [probe.NORMALIZATION_LIMITATION] if observation else [],
        'positive_control': True, 'negative_outcome': 'unsupported-handler', 'requests': [{}, {}, {}],
        'checks': {key: True for key in probe.CHECKS}, 'stub_calls': [{'name': 'allowed'}]}


def typed_output(text, timing='0.0008'):
    return [{'type': 'input_text', 'text': f'Wall time: {timing} seconds\nOutput:'},
        {'type': 'input_text', 'text': text}]


class BoundaryTests(unittest.TestCase):
    def test_environment_never_inherits_ambient_provider_credentials_or_proxy(self):
        with mock.patch.dict(os.environ, {'OPENAI_API_KEY': 'synthetic', 'HTTPS_PROXY': 'synthetic',
                'CODEX_HOME': '/ambient', 'HOME': '/ambient'}, clear=True):
            actual = probe.environment(pathlib.Path('/private/tmp/fresh'))
        self.assertNotIn('OPENAI_API_KEY', actual)
        self.assertNotIn('HTTPS_PROXY', actual)
        self.assertEqual(actual['HOME'], '/private/tmp/fresh')
        self.assertEqual(actual['CODEX_HOME'], actual['HOME'])

    def test_catalog_missing_duplicate_or_generic_metadata_cannot_fallback(self):
        record = {'slug': 'native-model', 'shell_type': 'unified_exec', 'apply_patch_tool_type': 'freeform'}
        self.assertEqual(probe.selected_metadata(json.dumps({'models': [record]}).encode(), 'native-model'), record)
        for value in [{}, {'models': []}, {'models': [record, record]}, {'models': [{'slug': 'native-model'}]}]:
            with self.subTest(value=value), self.assertRaises(probe.ProbeError):
                probe.selected_metadata(json.dumps(value).encode(), 'native-model')

    def test_fixed_calls_cannot_accept_arbitrary_payload_or_run_deferred_families(self):
        control = pathlib.Path('/private/tmp/fixed/control')
        for case in probe.CASES:
            call = probe.fixed_call(case, control)
            self.assertEqual(call['call_id'], 'boundary-negative-1')
            self.assertNotIn('spawn_agent', json.dumps(call))
            if case in ['shell', 'shell_command', 'exec_command', 'apply_patch']:
                self.assertNotIn('namespace', call)
            if case != 'apply_patch': json.loads(call['arguments'])
        for case in ['CodeMode', 'spawn_agent', 'write_stdin', 'arbitrary; command']:
            with self.assertRaises(probe.ProbeError): probe.fixed_call(case, control)

    def test_exact_call_id_type_and_single_output_are_required(self):
        call = {'call_id': 'expected', 'type': 'function_call'}
        output = {'type': 'function_call_output', 'call_id': 'expected', 'output': probe.TOKEN}
        self.assertEqual(probe.find_output({'input': [output]}, call), probe.TOKEN)
        for inputs in [[], [dict(output, call_id='other')], [output, output],
                       [dict(output, type='custom_tool_call_output')]]:
            with self.subTest(inputs=inputs), self.assertRaises(probe.ProbeError):
                probe.find_output({'input': inputs}, call)

    def test_observed_mcp_flattened_denial_requires_exact_namespace_and_name(self):
        for case in ('mcp-excluded', 'mcp-unknown-server'):
            call=probe.fixed_call(case, pathlib.Path('/private/tmp/fixed/control'))
            exact='unsupported call: '+call['namespace']+call['name']
            self.assertEqual(probe.negative_outcome(exact,call),'unsupported-handler')
            for wrong in (exact+' extra',exact+'\n','unsupported call: '+call['name'],
                    'unsupported call: mcp__another'+call['name'],'CodeMode host disabled'):
                with self.subTest(case=case,wrong=wrong):
                    self.assertEqual(probe.negative_outcome(wrong,call),'unknown')

    def test_positive_control_requires_exact_output_not_substring_or_error(self):
        self.assertTrue(probe.positive_output(probe.TOKEN))
        valid = {'content': [{'type': 'text', 'text': probe.TOKEN}], 'isError': False}
        self.assertTrue(probe.positive_output(json.dumps(valid)))
        for output in [probe.TOKEN+' extra', {'text': probe.TOKEN}, json.dumps(dict(valid, isError=True)),
                json.dumps(dict(valid, isError=0)), json.dumps(dict(valid, error='failed')), 'invalid JSON']:
            with self.subTest(output=output): self.assertFalse(probe.positive_output(output))

    def test_observed_typed_carrier_unwraps_without_mutating_exact_payload(self):
        call = probe.fixed_call('exec_command', pathlib.Path('/private/tmp/fixed/control'))
        denial = 'unsupported call: functions.exec_command'
        for timing in ['0.0000', '0.0008', '1.2345', '29.9999', '30.0000']:
            positive = typed_output(probe.TOKEN, timing)
            before = copy.deepcopy(positive)
            with self.subTest(timing=timing):
                self.assertTrue(probe.positive_output(positive))
                self.assertEqual(probe.negative_outcome(typed_output(denial, timing), call), 'unsupported-handler')
                self.assertEqual(positive, before)
        patch = probe.fixed_call('apply_patch', pathlib.Path('/private/tmp/fixed/control'))
        patch_denial = 'patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings'
        self.assertEqual(probe.negative_outcome(typed_output(patch_denial), patch), 'readonly-patch-denied')
        structured = json.dumps({'content': [{'type': 'text', 'text': probe.TOKEN}], 'isError': False})
        self.assertTrue(probe.positive_output(typed_output(structured)))
        for body in [probe.TOKEN+' extra', probe.TOKEN+'\n', 'error: '+probe.TOKEN,
                'CodeMode host disabled', 'unsupported call: another_tool', 'timeout',
                'Wall time: 0.0008 seconds\nOutput:',
                json.dumps({'content': [{'type': 'text', 'text': probe.TOKEN}], 'isError': True})]:
            with self.subTest(body=body):
                self.assertFalse(probe.positive_output(typed_output(body)))
                self.assertEqual(probe.negative_outcome(typed_output(body), call), 'unknown')
        self.assertFalse(probe.positive_output(typed_output(denial)))
        self.assertEqual(probe.negative_outcome(typed_output(probe.TOKEN), call), 'unknown')

    def test_typed_carrier_rejects_extra_missing_duplicate_wrong_types_and_layouts(self):
        call = probe.fixed_call('exec_command', pathlib.Path('/private/tmp/fixed/control'))
        for body in [probe.TOKEN, 'unsupported call: exec_command']:
            good = typed_output(body)
            invalid = [[], good[:1], good[1:], good+good[1:], good+good[:1], list(reversed(good)),
                [good[1], good[1]], tuple(good), {'content': good},
                [dict(good[0], extra=True), good[1]], [good[0], dict(good[1], extra=True)],
                [dict(good[0], type='text'), good[1]], [good[0], dict(good[1], type='output_text')],
                [dict(good[0], text=None), good[1]], [good[0], dict(good[1], text=[body])],
                [good[0], None], [good[0], body], typed_output(body+'x'*32768)]
            for header in ['Output:', 'Wall time: 0.0008 seconds\nOutput:\n',
                    'Wall time: 0.0008 seconds\r\nOutput:', 'Wall time: 0.0008 seconds\nOutput: extra',
                    'Wall time: 0.0008 seconds\nOutput:\n'+body, 'prefix\n'+good[0]['text']]:
                invalid.append([{'type': 'input_text', 'text': header}, good[1]])
            for output in invalid:
                with self.subTest(body=body, output=output):
                    self.assertIsNone(probe.output_text(output))
                    self.assertFalse(probe.positive_output(output))
                    self.assertEqual(probe.negative_outcome(output, call), 'unknown')

    def test_typed_carrier_timing_rejects_nonfinite_out_of_range_and_noncanonical_formats(self):
        call = probe.fixed_call('exec_command', pathlib.Path('/private/tmp/fixed/control'))
        for timing in ['NaN', 'nan', 'Infinity', 'inf', '-inf', '1e-4', '-0.0001', '+0.0008',
                '-0.0000', '00.0008', '0', '.0008', '0.008', '0.00080', '30.0001', '31.0000',
                '99.9999', '100.0000', ' 0.0008', '0.0008 ', '０.0008', '0.０００８']:
            with self.subTest(timing=timing):
                self.assertFalse(probe.positive_output(typed_output(probe.TOKEN, timing)))
                self.assertEqual(probe.negative_outcome(
                    typed_output('unsupported call: exec_command', timing), call), 'unknown')

    def test_fixture_keeps_raw_typed_outputs_and_requires_exact_call_and_allowed_stub(self):
        # Exercise the real request handler without a listener or CLI process.
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            for failure in [None, 'duplicate', 'wrong-call', 'wrong-type', 'stub-missing', 'stub-extra']:
                receipt = {'requests': []}
                with mock.patch.object(probe.http.server, 'ThreadingHTTPServer') as server:
                    probe.fixture_server(root, root, 'native-model', 'exec_command', receipt)
                handler = server.call_args.args[1]

                def post(inputs):
                    raw = json.dumps({'model': 'native-model', 'input': inputs, 'tools': []}).encode()
                    request = mock.Mock(path='/v1/responses',
                        headers={'Content-Length': str(len(raw))}, rfile=io.BytesIO(raw), wfile=io.BytesIO())
                    handler.do_POST(request)
                    return request

                post([])
                positive = typed_output(probe.TOKEN)
                output = {'type': 'function_call_output', 'call_id': 'boundary-positive-1', 'output': positive}
                inputs = [output]
                if failure == 'duplicate': inputs.append(copy.deepcopy(output))
                if failure == 'wrong-call': output['call_id'] = 'other'
                if failure == 'wrong-type': output['type'] = 'custom_tool_call_output'
                calls = [] if failure == 'stub-missing' else [{'name': 'allowed'}]
                if failure == 'stub-extra': calls.append({'name': 'excluded'})
                with mock.patch.object(probe, 'stub_calls', return_value=calls):
                    request = post(inputs)
                with self.subTest(failure=failure):
                    if failure:
                        request.send_error.assert_called_once_with(422)
                        self.assertNotIn('positive_control', receipt)
                        continue
                    request.send_response.assert_called_once_with(200)
                    self.assertTrue(receipt['positive_control'])
                    self.assertEqual(receipt['requests'][1]['output'], positive)
                    self.assertEqual(json.loads((root/'request-2.json').read_bytes())['input'][0]['output'], positive)
                    negative = typed_output('unsupported call: exec_command')
                    post([{'type': 'function_call_output', 'call_id': 'boundary-negative-1', 'output': negative}])
                    self.assertEqual(receipt['negative_outcome'], 'unsupported-handler')
                    self.assertEqual(receipt['requests'][2]['output'], negative)

    def test_schema_argument_timeout_and_generic_errors_never_pass_as_denials(self):
        call = probe.fixed_call('exec_command', pathlib.Path('/private/tmp/fixed/control'))
        self.assertEqual(probe.negative_outcome('unsupported call: exec_command', call), 'unsupported-handler')
        self.assertEqual(probe.negative_outcome('unsupported call: functions.exec_command', call), 'unsupported-handler')
        for output in ['invalid arguments', 'missing field cmd', 'failed to parse arguments', 'timeout',
                'Operation not permitted', 'unsupported call: another_tool', '', None, {'error': 'denied'}]:
            with self.subTest(output=output): self.assertEqual(probe.negative_outcome(output, call), 'unknown')
        patch = probe.fixed_call('apply_patch', pathlib.Path('/private/tmp/fixed/control'))
        self.assertEqual(probe.negative_outcome(
            'patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings', patch),
            'readonly-patch-denied')

    def test_result_requires_positive_control_no_effects_exact_denial_and_fresh_bindings(self):
        good = successful_receipt()
        self.assertEqual(probe.evaluate(good), 'passed')
        for key, value in [('positive_control', False), ('negative_outcome', 'unknown'),
                ('requests', [{}, {}]), ('error', 'timeout'), ('fixture_error', 'argument-error')]:
            bad = copy.deepcopy(good); bad[key] = value
            with self.subTest(key=key): self.assertEqual(probe.evaluate(bad), 'unknown')
        for key in good['checks']:
            bad = copy.deepcopy(good); bad['checks'][key] = None
            with self.subTest(check=key): self.assertEqual(probe.evaluate(bad), 'unknown')
            del bad['checks'][key]
            with self.subTest(missing_check=key): self.assertEqual(probe.evaluate(bad), 'unknown')
        bad = copy.deepcopy(good); bad['checks']['forbidden_preserved'] = False
        self.assertEqual(probe.evaluate(bad), 'failed')
        bad = copy.deepcopy(good); bad['stub_calls'].append({'name': 'excluded'})
        self.assertEqual(probe.evaluate(bad), 'failed')
        bad = copy.deepcopy(good); bad['positive_control'] = False; bad['stub_calls'] = []
        bad['checks']['only_allowed_stub_call'] = False
        self.assertEqual(probe.evaluate(bad), 'unknown')

    def test_feature_readback_requires_every_disabled_feature_with_actual_false(self):
        raw = b'shell_tool stable false\ncode_mode experimental false\n'
        self.assertEqual(probe.feature_state(raw, ['shell_tool', 'code_mode']), {'shell_tool': False, 'code_mode': False})
        for wrong in [raw.replace(b'false', b'true', 1), b'shell_tool stable false\n',
                      raw+b'shell_tool stable false\n', b'shell_tool stable unknown\n']:
            with self.assertRaises(probe.ProbeError): probe.feature_state(wrong, ['shell_tool', 'code_mode'])

    def test_normalized_mode_requires_explicit_opt_in_exact_version_and_complete_vector(self):
        names = probe.REQUIRED_DISABLED_FEATURES
        self.assertEqual(len(names), 23)
        broker, _ = probe.load_broker()
        self.assertEqual(names, broker.DISABLED_FEATURES)
        states = {name: name == 'unified_exec' for name in names}
        raw = ''.join(f'{name} stable {str(value).lower()}\n' for name, value in states.items()).encode()
        with self.assertRaises(probe.ProbeError): probe.feature_state(raw, names)
        self.assertEqual(probe.feature_state(raw, names, cli_version=probe.CLI_VERSION,
            allow_normalized_unified_exec_fixture=True), states)
        invalid = [dict(states, unified_exec=False), dict(states, shell_tool=True),
            dict(states, code_mode=True), dict(states, unified_exec=1),
            {key: value for key, value in states.items() if key != 'unified_exec'},
            {key: value for key, value in states.items() if key != 'view_image'}]
        for value in invalid:
            with self.subTest(states=value), self.assertRaises(probe.ProbeError):
                probe.validate_feature_states(value, names, allow_normalized_unified_exec_fixture=True)
        for version in [None, 'codex-cli 0.159.2', 'codex-cli 0.159.4', '0.159.3']:
            with self.subTest(version=version), self.assertRaises(probe.ProbeError):
                probe.feature_state(raw, names, cli_version=version,
                    allow_normalized_unified_exec_fixture=True)
        with self.assertRaises(probe.ProbeError):
            probe.feature_state(raw, names, allow_normalized_unified_exec_fixture=1)

    def test_observation_receipt_cannot_pass_strict_evaluation_or_hide_binding_drift(self):
        good = successful_receipt(observation=True)
        self.assertEqual(probe.evaluate(good, allow_normalized_unified_exec_fixture=True), 'measured-case-passed')
        self.assertEqual(probe.evaluate(good), 'unknown')
        self.assertEqual(probe.evaluate(successful_receipt(), allow_normalized_unified_exec_fixture=True), 'unknown')
        changes = [('control_mode', probe.STRICT_CONTROL_MODE), ('allow_normalized_unified_exec_fixture', False),
            ('fixed_observation_only', False), ('strict_required_false_satisfied', True),
            ('normalization_source', dict(probe.NORMALIZATION_SOURCE, source_sha256='0'*64)),
            ('requested_disabled_features', dict(good['requested_disabled_features'], unified_exec=True)),
            ('requested_disabled_features', dict(good['requested_disabled_features'], unified_exec=0)),
            ('effective_feature_states', dict(good['effective_feature_states'], unified_exec=False)),
            ('effective_feature_states', dict(good['effective_feature_states'], shell_tool=True)),
            ('cli_version', 'codex-cli 0.159.4'), ('unknown', []), ('production_qualified', True),
            ('handler_inventory_complete', True), ('repository_completion', True),
            ('positive_control', False), ('negative_outcome', 'unknown')]
        for key, value in changes:
            bad = copy.deepcopy(good); bad[key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(probe.evaluate(bad, allow_normalized_unified_exec_fixture=True), 'unknown')
        for key in probe.control_contract(True):
            bad = copy.deepcopy(good); del bad[key]
            with self.subTest(missing=key):
                self.assertEqual(probe.evaluate(bad, allow_normalized_unified_exec_fixture=True), 'unknown')
        bad = copy.deepcopy(good); bad['checks']['forbidden_preserved'] = False
        self.assertEqual(probe.evaluate(bad, allow_normalized_unified_exec_fixture=True), 'failed')

    def run_mock_case(self, observation, states, version=probe.CLI_VERSION):
        """Exercise receipt creation with no listener, Codex process, or MCP launch."""
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve(); executable = base/'codex'
            executable.write_bytes(b'synthetic-executable-identity')
            catalog = json.dumps({'models': [{'slug': 'native-model', 'shell_type': 'unified_exec',
                'apply_patch_tool_type': 'freeform'}]}).encode()
            raw = ''.join(f'{name} stable {str(value).lower()}\n' for name, value in states.items()).encode()
            runs = [subprocess.CompletedProcess([], 0, stdout=version.encode()),
                subprocess.CompletedProcess([], 0, stdout=catalog),
                subprocess.CompletedProcess([], 0, stdout=raw)]
            broker, server, process = mock.Mock(), mock.Mock(server_port=12345), mock.Mock(pid=12345)
            process.poll.return_value = 0
            def complete_fixed_calls(*args, **kwargs):
                receipt = listener.call_args.args[4]
                receipt.update(requests=[{}, {}, {}], positive_control=True, negative_outcome='unsupported-handler')
                return process
            with mock.patch.object(probe.subprocess, 'run', side_effect=runs), \
                    mock.patch.object(probe, 'fixture_server', return_value=server) as listener, \
                    mock.patch.object(probe.threading, 'Thread'), \
                    mock.patch.object(probe.subprocess, 'Popen', side_effect=complete_fixed_calls) as launch, \
                    mock.patch.object(probe, 'configuration_fingerprint', return_value={'fixed': 'synthetic'}), \
                    mock.patch.object(probe, 'stub_stopped', return_value=True), \
                    mock.patch.object(probe, 'stub_calls', return_value=[{'name': 'allowed'}]):
                receipt, output = probe.run_case(base, 'mcp-excluded', 'native-model', executable, broker,
                    executable, allow_normalized_unified_exec_fixture=observation)
            self.assertEqual(json.loads(output.read_bytes()), receipt)
            return receipt, launch.call_args

    def test_run_case_binds_requested_false_actual_true_and_observation_only_receipt(self):
        states = {name: name == 'unified_exec' for name in probe.REQUIRED_DISABLED_FEATURES}
        receipt, invocation = self.run_mock_case(True, states)
        self.assertEqual(receipt['outcome'], 'measured-case-passed')
        self.assertEqual(receipt['control_mode'], probe.NORMALIZED_CONTROL_MODE)
        self.assertTrue(receipt['fixed_observation_only'])
        self.assertFalse(receipt['strict_required_false_satisfied'])
        self.assertFalse(receipt['production_qualified'])
        self.assertFalse(receipt['handler_inventory_complete'])
        self.assertEqual(receipt['effective_feature_states'], states)
        self.assertNotIn('effective_disabled_features', receipt)
        self.assertEqual(receipt['requested_disabled_features'], {name: False for name in states})
        self.assertEqual(receipt['normalization_source'], probe.NORMALIZATION_SOURCE)
        self.assertIn(probe.NORMALIZATION_LIMITATION, receipt['unknown'])
        self.assertEqual(receipt['not_run'], ['agent', 'write_stdin', 'CodeMode'])
        for name in states:
            self.assertIn(f'features.{name}=false', invocation.args[0])
        self.assertNotIn('features.unified_exec=true', invocation.args[0])

    def test_run_case_stops_before_cli_for_wrong_mode_vector_or_version(self):
        states = {name: name == 'unified_exec' for name in probe.REQUIRED_DISABLED_FEATURES}
        scenarios = [(False, states, probe.CLI_VERSION),
            (True, dict(states, unified_exec=False), probe.CLI_VERSION),
            (True, dict(states, shell_tool=True), probe.CLI_VERSION),
            (True, {key: value for key, value in states.items() if key != 'unified_exec'}, probe.CLI_VERSION),
            (True, states, 'codex-cli 0.159.4')]
        for observation, actual, version in scenarios:
            with self.subTest(observation=observation, actual=actual, version=version):
                receipt, invocation = self.run_mock_case(observation, actual, version)
                self.assertIsNone(invocation)
                self.assertEqual(receipt['outcome'], 'unknown')
                self.assertFalse(receipt['strict_required_false_satisfied'])
                self.assertEqual(receipt['cli_version'], version)
                if version == probe.CLI_VERSION:
                    self.assertEqual(receipt['effective_feature_states'], actual)
        receipt, invocation = self.run_mock_case(False, dict.fromkeys(states, False))
        self.assertIsNotNone(invocation)
        self.assertEqual(receipt['outcome'], 'passed')
        self.assertEqual(receipt['control_mode'], probe.STRICT_CONTROL_MODE)
        self.assertTrue(receipt['strict_required_false_satisfied'])

    def test_cli_observation_flag_defaults_off_and_is_forwarded_to_each_fixed_case(self):
        args = ['--evidence-root', '/private/tmp', '--metadata-model', 'native-model']
        self.assertFalse(probe.argument_parser().parse_args(args).allow_normalized_unified_exec_fixture)
        self.assertTrue(probe.argument_parser().parse_args(
            args+['--allow-normalized-unified-exec-fixture']).allow_normalized_unified_exec_fixture)
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve()
            for observation in [False, True]:
                argv = ['--evidence-root', str(base), '--metadata-model', 'native-model']
                if observation: argv.append('--allow-normalized-unified-exec-fixture')
                receipt = successful_receipt(observation)
                receipt['outcome'] = 'measured-case-passed' if observation else 'passed'
                with mock.patch.object(probe.sys, 'platform', 'darwin'), \
                        mock.patch.object(pathlib.Path, 'is_relative_to', return_value=True) as private_tmp, \
                        mock.patch.object(probe.shutil, 'which', return_value=sys.executable), \
                        mock.patch.object(probe, 'load_broker', return_value=(mock.Mock(), pathlib.Path(sys.executable))), \
                        mock.patch.object(probe, 'run_case', return_value=(receipt, base/'synthetic.json')) as run, \
                        mock.patch('builtins.print') as output:
                    self.assertEqual(probe.main(argv), 0)
                private_tmp.assert_called_once_with('/private/tmp')
                self.assertEqual([call.args[1] for call in run.call_args_list], list(probe.CASES))
                self.assertTrue(all(call.kwargs == {'allow_normalized_unified_exec_fixture': observation}
                    for call in run.call_args_list))
                for call in output.call_args_list:
                    summary = json.loads(call.args[0])
                    self.assertEqual(summary['control_mode'], receipt['control_mode'])
                    self.assertIs(summary['fixed_observation_only'], observation)
                    self.assertFalse(summary['production_qualified'])

    def test_configuration_fingerprint_rejects_symlinks_and_new_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve(); home = root/'home'; home.mkdir()
            source = root/'source.py'; source.write_text('fixed')
            audit = lambda work: [str(work)]
            before = probe.configuration_fingerprint(root, home, [source], audit)
            source.write_text('drifted')
            self.assertNotEqual(before, probe.configuration_fingerprint(root, home, [source], audit))
            alias = root/'alias'; alias.symlink_to(source)
            with self.assertRaises(probe.ProbeError): probe.configuration_fingerprint(root, home, [alias], audit)
            (home/'config.toml').write_text('')
            with self.assertRaises(probe.ProbeError): probe.configuration_fingerprint(root, home, [source], audit)

    def test_pid_absence_is_bounded_to_the_stub_and_uncertainty_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            control = pathlib.Path(directory)
            self.assertIsNone(probe.stub_stopped(control))
            (control/'stub-pid').write_text('12345')
            with mock.patch.object(probe.os, 'kill', side_effect=ProcessLookupError):
                self.assertIs(probe.stub_stopped(control), True)
            with mock.patch.object(probe.os, 'kill', side_effect=PermissionError):
                self.assertIsNone(probe.stub_stopped(control))
            with mock.patch.object(probe.os, 'kill', return_value=None):
                self.assertIs(probe.stub_stopped(control), False)

    def test_fixed_stub_protocol_roundtrip_eof_and_excluded_call_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            control = pathlib.Path(directory).resolve(); stub = control/'stub.py'
            stub.write_text(probe.STUB_SOURCE)
            requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'allowed', 'arguments': {}}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'excluded', 'arguments': {}}}]
            result = subprocess.run([sys.executable, '-I', '-S', '-B', str(stub), str(control)],
                input=''.join(json.dumps(item)+'\n' for item in requests).encode(), capture_output=True,
                env=probe.environment(control), timeout=5, check=True)
            replies = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([item['id'] for item in replies], [1, 2, 3, 4])
            self.assertEqual(replies[2]['result']['content'][0]['text'], probe.TOKEN)
            self.assertEqual([item['name'] for item in probe.stub_calls(control)], ['allowed', 'excluded'])
            self.assertEqual((control/'stub-exit').read_text(), 'eof')
            self.assertIs(probe.stub_stopped(control), True)

    def test_listener_permission_failure_retains_unknown_receipt_before_cli_or_stub_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve(); executable = base/'codex'
            executable.write_bytes(b'synthetic-executable-identity')
            catalog = json.dumps({'models': [{'slug': 'native-model', 'shell_type': 'unified_exec',
                'apply_patch_tool_type': 'freeform'}]}).encode()
            broker = mock.Mock()
            runs = [subprocess.CompletedProcess([], 0, stdout=probe.CLI_VERSION.encode()),
                    subprocess.CompletedProcess([], 0, stdout=catalog)]
            with mock.patch.object(probe.subprocess, 'run', side_effect=runs), \
                    mock.patch.object(probe, 'fixture_server', side_effect=PermissionError), \
                    mock.patch.object(probe.subprocess, 'Popen') as launch:
                receipt, output = probe.run_case(base, 'mcp-excluded', 'native-model', executable, broker, executable)
            launch.assert_not_called()
            self.assertEqual(receipt['phase'], 'loopback-listener-start')
            self.assertEqual(receipt['outcome'], 'unknown')
            self.assertEqual(receipt['error'], 'PermissionError')
            self.assertEqual(receipt['requests'], [])
            self.assertFalse((output.parent/'control/stub-pid').exists())
            self.assertEqual(json.loads(output.read_bytes()), receipt)

    def test_server_thread_start_failure_closes_without_waiting_and_saves_unknown_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve(); executable = base/'codex'
            executable.write_bytes(b'synthetic-executable-identity')
            catalog = json.dumps({'models': [{'slug': 'native-model', 'shell_type': 'unified_exec',
                'apply_patch_tool_type': 'freeform'}]}).encode()
            broker = mock.Mock()
            server = mock.Mock()
            server.shutdown.side_effect = AssertionError('must not wait on an unstarted server')
            runs = [subprocess.CompletedProcess([], 0, stdout=probe.CLI_VERSION.encode()),
                    subprocess.CompletedProcess([], 0, stdout=catalog)]
            with mock.patch.object(probe.subprocess, 'run', side_effect=runs), \
                    mock.patch.object(probe, 'fixture_server', return_value=server), \
                    mock.patch.object(probe.threading, 'Thread') as thread, \
                    mock.patch.object(probe.subprocess, 'Popen') as launch:
                thread.return_value.start.side_effect = RuntimeError('synthetic thread failure')
                receipt, output = probe.run_case(base, 'mcp-excluded', 'native-model', executable, broker, executable)
            thread.assert_called_once_with(target=server.serve_forever, daemon=True)
            thread.return_value.start.assert_called_once_with()
            server.serve_forever.assert_not_called()
            server.shutdown.assert_not_called()
            server.server_close.assert_called_once_with()
            launch.assert_not_called()
            self.assertEqual(receipt['phase'], 'loopback-listener-start')
            self.assertEqual(receipt['outcome'], 'unknown')
            self.assertEqual(receipt['error'], 'fixture-server-thread-start-failed')
            self.assertEqual(receipt['requests'], [])
            self.assertFalse((output.parent/'control/stub-pid').exists())
            self.assertEqual(json.loads(output.read_bytes()), receipt)

    def test_unrelated_runtime_error_is_not_reclassified_as_thread_start_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve(); executable = base/'codex'
            executable.write_bytes(b'synthetic-executable-identity')
            catalog = json.dumps({'models': [{'slug': 'native-model', 'shell_type': 'unified_exec',
                'apply_patch_tool_type': 'freeform'}]}).encode()
            broker, server = mock.Mock(), mock.Mock()
            runs = [subprocess.CompletedProcess([], 0, stdout=probe.CLI_VERSION.encode()),
                    subprocess.CompletedProcess([], 0, stdout=catalog)]
            with mock.patch.object(probe.subprocess, 'run', side_effect=runs), \
                    mock.patch.object(probe, 'fixture_server', return_value=server), \
                    mock.patch.object(probe.threading, 'Thread'), \
                    mock.patch.object(probe, 'settings', side_effect=RuntimeError('unrelated runtime failure')), \
                    mock.patch.object(probe.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, '^unrelated runtime failure$'):
                    probe.run_case(base, 'mcp-excluded', 'native-model', executable, broker, executable)
            server.shutdown.assert_called_once_with()
            server.server_close.assert_called_once_with()
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
