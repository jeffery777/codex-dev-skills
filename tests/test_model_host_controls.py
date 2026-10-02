"""Synthetic hook fault controls, without CLI, provider or container access."""
import importlib.util
import inspect
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('dispatch_probe', ROOT / 'scripts/verify-model-dispatch.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class HookControlTests(unittest.TestCase):
    def test_inherited_legacy_managed_configuration_is_rejected(self):
        spec = importlib.util.spec_from_file_location('broker_audit', ROOT / 'scripts/verify-model-broker.py')
        broker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(broker)
        with tempfile.TemporaryDirectory() as directory:
            client = pathlib.Path(directory).resolve()
            with mock.patch.object(broker.os.path, 'lexists',
                    side_effect=lambda path: str(path) == '/etc/codex/managed_config.toml'):
                with self.assertRaisesRegex(broker.ProbeError, 'system-configuration-requires-review'):
                    broker.audit_client_directory(client)

    def test_main_rejects_unrelated_tool_errors_despite_hook_marker(self):
        holder = {}
        class FakeServer:
            def __init__(self, address, handler):
                self.server_port = 12345
                self.handler = handler
                self.context = inspect.getclosurevars(handler.do_POST).nonlocals
                holder['server'] = self
            def serve_forever(self): pass
            def shutdown(self): pass
            def server_close(self): pass

        def fake_run(*args, **kwargs):
            server = holder['server']
            root = server.context['root']
            (root / 'control/hook-invoked').write_text('invoked\ninvoked\n')
            for stage in range(1, 4):
                value = {'tools': [{'type': 'custom', 'name': 'apply_patch'}], 'input': []}
                if stage > 1:
                    value['input'] = [{'type': 'custom_tool_call_output',
                        'call_id': 'fixture-call-' + str(stage - 1),
                        'output': 'Error: synthetic unexpected tool failure; operation never reached filesystem'}]
                raw = json.dumps(value).encode()
                request = object.__new__(server.handler)
                request.path = '/v1/responses'
                request.headers = {'Content-Length': str(len(raw))}
                request.rfile, request.wfile = io.BytesIO(raw), io.BytesIO()
                request.send_response = lambda *unused: None
                request.send_header = lambda *unused: None
                request.end_headers = lambda: None
                request.send_error = lambda *status: self.fail(str(status))
                request.do_POST()
            return SimpleNamespace(returncode=0, stdout='synthetic runtime failure', stderr='')

        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            argv = ['probe', '--evidence-root', directory, '--case', 'patch',
                '--hook-fault', 'invalid-json', '--host-read-only']
            with mock.patch.object(sys, 'argv', argv), \
                    mock.patch.object(probe.shutil, 'which', return_value=sys.executable), \
                    mock.patch.object(probe.http.server, 'ThreadingHTTPServer', FakeServer), \
                    mock.patch.object(probe.subprocess, 'run', side_effect=fake_run), \
                    mock.patch.object(sys, 'stdout', output):
                code = probe.main()
            receipt = json.loads(output.getvalue())
            self.assertNotEqual(code, 0)
            self.assertTrue(receipt['checks']['hook_positive_control'])
            self.assertFalse(receipt['checks']['patch_boundary_observed'])

    def test_unrelated_tool_failure_is_not_a_boundary_denial(self):
        unknown = probe.patch_output_kind('Error: synthetic unexpected tool failure; operation never reached filesystem')
        self.assertEqual(unknown, 'unknown')
        requests = [{}, {'patch_output_kind': unknown}, {'patch_output_kind': unknown}]
        self.assertFalse(probe.patch_boundary_observed(requests, readonly=True, hook_fault='invalid-json'))
        for hook in ['deny', 'exit1', 'exit2-empty', 'timeout', None]:
            self.assertFalse(probe.patch_boundary_observed(requests, readonly=True, hook_fault=hook))

    def test_expected_denial_kinds_are_bound_to_each_operation(self):
        requests = [{}, {'patch_output_kind': 'readonly-denied'}, {'patch_output_kind': 'read-denied'}]
        self.assertTrue(probe.patch_boundary_observed(requests, readonly=True, hook_fault='invalid-json'))
        self.assertFalse(probe.patch_boundary_observed(requests, readonly=False, hook_fault=None))
        self.assertFalse(probe.patch_boundary_observed(requests, readonly=True, hook_fault='deny'))
        deny = [{}, {'patch_output_kind': 'hook-denied'}, {'patch_output_kind': 'hook-denied'}]
        self.assertTrue(probe.patch_boundary_observed(deny, readonly=True, hook_fault='deny'))
        self.assertFalse(probe.patch_boundary_observed(deny, readonly=True, hook_fault='exit1'))

    def test_faults_write_positive_control_before_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            for case, expected in [('deny', 0), ('exit1', 1), ('exit2-empty', 2), ('invalid-json', 0)]:
                with self.subTest(case=case):
                    marker = pathlib.Path(directory) / case
                    result = subprocess.run([sys.executable, '-I', '-c', probe.hook_source(case, marker)],
                        capture_output=True, text=True, timeout=3, close_fds=True)
                    self.assertEqual(result.returncode, expected)
                    self.assertEqual(marker.read_text(), 'invoked\n')
                    if case == 'deny':
                        self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
                    elif case == 'exit2-empty':
                        self.assertEqual(result.stderr, '')
                    elif case == 'invalid-json':
                        with self.assertRaises(json.JSONDecodeError):
                            json.loads(result.stdout)

    def test_timeout_marker_does_not_require_hook_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = pathlib.Path(directory) / 'timeout'
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run([sys.executable, '-I', '-c', probe.hook_source('timeout', marker)],
                    capture_output=True, timeout=1, close_fds=True)
            self.assertEqual(marker.read_text(), 'invoked\n')

    def test_unapproved_case_never_generates_hook_code(self):
        with self.assertRaises(ValueError):
            probe.hook_source('unapproved', pathlib.Path('/synthetic'))


if __name__ == '__main__':
    unittest.main()
