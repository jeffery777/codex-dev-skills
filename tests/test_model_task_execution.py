"""Shared routing/typed executor binding tests; no live provider calls."""
import copy
import json
import pathlib
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from types import SimpleNamespace
import unittest
from unittest import mock

from tests.test_model_failover import route_fixture
import model_task_execution as execution
import agent_routing
import loopctl


class SharedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.input = route_fixture()
        role = agent_routing.plan_model_failover(self.input['task'], self.input['model_failover'])['classification']['selected_role']
        self.binding = SimpleNamespace(target_id='internal', binding_sha256='a'*64,
            task_id='T1', scope='repair', acceptance_sha256='f'*64, role=role)
        self.adapter = mock.Mock()
        self.adapter.PACKET_STOP_ADAPTERS = {'synthetic': SimpleNamespace(supports_target=lambda binding: True)}
        self.adapter.HandoffValidationError = type('Rejected', (ValueError,), {})
        self.adapter.validate_request.return_value = SimpleNamespace(execution_target=self.binding)
        self.receipt = {'status': 'completed', 'boundaries': {
            'session_call_performed': True, 'repository_completion_claimed': False},
            'execution_target': {'id': 'internal', 'binding_sha256': 'a'*64}}
        self.adapter.execute_packet_attempt.return_value = self.receipt
        self.loader = mock.Mock()
        self.loader.target_identity.return_value = copy.deepcopy(self.input['model_failover']['targets'][0]['identity'])
        self.request = {'operation': 'start', 'target_ref': {'id': 'internal'}}
        self.packet = mock.Mock()
        self.packet.read_checkpoint.return_value = ({'revision': 0}, b'')
        patch = mock.patch.object(execution, '_packet_store', return_value=self.packet)
        patch.start(); self.addCleanup(patch.stop)

    def execute(self):
        with mock.patch.object(execution, '_cli_adapter', return_value=(self.adapter, self.loader)):
            return execution.execute_next(self.input['task'], self.input['model_failover'], self.request)

    def test_one_packet_does_not_claim_repository_completion(self):
        result = self.execute()
        self.assertTrue(result['dispatched'])
        self.assertFalse(result['repository_completion_claimed'])
        self.adapter.execute_packet_attempt.assert_called_once()

    def test_unsupported_or_ambiguous_containment_never_dispatches(self):
        for registry in [
            {'other': SimpleNamespace(supports_target=lambda binding: False)},
            {'first': SimpleNamespace(supports_target=lambda binding: True),
             'second': SimpleNamespace(supports_target=lambda binding: True)},
        ]:
            self.adapter.PACKET_STOP_ADAPTERS = registry
            with self.assertRaisesRegex(execution.ExecutionContractError, 'binding-ambiguous'):
                self.execute()
            self.adapter.execute_packet_attempt.assert_not_called()
            self.packet.read_checkpoint.assert_not_called()

    def test_disabled_policy_does_not_even_resolve_executor(self):
        self.input['model_failover']['enabled'] = False
        result = self.execute()
        self.assertFalse(result['dispatched'])
        self.adapter.validate_request.assert_not_called()
        self.adapter.execute_packet_attempt.assert_not_called()

    def test_missing_containment_never_validates_or_launches(self):
        self.adapter.PACKET_STOP_ADAPTERS = {}
        with self.assertRaisesRegex(execution.ExecutionContractError, 'containment-unavailable'):
            self.execute()
        self.adapter.validate_request.assert_not_called()
        self.adapter.execute_packet_attempt.assert_not_called()

    def test_binding_identity_and_task_mismatch_prevent_dispatch(self):
        for field in ['target_id', 'task_id', 'scope', 'acceptance_sha256', 'role']:
            with self.subTest(field=field):
                previous = getattr(self.binding, field)
                setattr(self.binding, field, 'mismatch')
                with self.assertRaises(execution.ExecutionContractError):
                    self.execute()
                setattr(self.binding, field, previous)
        self.loader.target_identity.return_value['model'] = 'mismatch'
        with self.assertRaisesRegex(execution.ExecutionContractError, 'identity-mismatch'):
            self.execute()
        self.adapter.execute_packet_attempt.assert_not_called()

    def test_desktop_identity_cannot_use_cli_executor(self):
        p = self.input['model_failover']
        import model_failover
        target = p['targets'][0]
        target['identity']['runtime'] = 'desktop'
        target['qualification']['identity_sha256'] = model_failover.identity_digest(target['identity'])
        p['authorization']['target_identity_sha256'][0] = target['qualification']['identity_sha256']
        with self.assertRaisesRegex(execution.ExecutionContractError, 'another-public-adapter'):
            self.execute()
        self.adapter.validate_request.assert_not_called()

    def test_qualified_higher_tier_same_class_is_not_blocked_by_baseline_role(self):
        self.binding.role = 'loop_v2a_senior_worker'
        result = self.execute()
        self.assertTrue(result['dispatched'])

    def test_other_class_and_exceptional_role_cannot_replace_worker(self):
        for role in ['loop_v2a_deep_reviewer', 'loop_v2a_exceptional_researcher']:
            self.binding.role = role
            with self.assertRaisesRegex(execution.ExecutionContractError, 'role-contract-mismatch'):
                self.execute()
        self.adapter.execute_packet_attempt.assert_not_called()

    def test_only_typed_start(self):
        for request in [{'operation': 'resume', 'target_ref': {}}, {'operation': 'start'}, None]:
            self.request = request
            with self.assertRaisesRegex(execution.ExecutionContractError, 'typed-cli-start-required'):
                self.execute()
        self.adapter.execute_packet_attempt.assert_not_called()

    def test_post_entry_fault_is_unknown_and_never_retried(self):
        self.adapter.execute_packet_attempt.side_effect = OSError('synthetic fault')
        result = self.execute()
        self.assertIsNone(result['dispatched'])
        self.assertEqual(result['execution']['status'], 'unknown')
        self.assertTrue(result['execution']['independent_readback_required'])
        self.adapter.execute_packet_attempt.assert_called_once()

    def test_invalid_or_mismatched_receipt_cannot_prove_no_dispatch(self):
        for receipt in [{}, {'boundaries': {'session_call_performed': 'false'}},
                        {**self.receipt, 'execution_target': {'id': 'other', 'binding_sha256': 'a'*64}}]:
            self.adapter.execute_packet_attempt.return_value = receipt
            result = self.execute()
            self.assertIsNone(result['dispatched'])
            self.assertEqual(result['execution']['status'], 'unknown')

    def test_known_prelaunch_rejection_preserves_not_dispatched(self):
        self.adapter.execute_packet_attempt.return_value = {'status': 'stopped', 'boundaries': {
            'session_call_performed': False, 'repository_completion_claimed': False}}
        result = self.execute()
        self.assertFalse(result['dispatched'])

    def test_entrypoint_never_dispatches_invalid_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)/'input.json'
            for raw in [b'{"task":{},"task":{}}', b'{}']:
                path.write_bytes(raw)
                output = StringIO()
                with redirect_stdout(output), mock.patch.object(execution, 'execute_next') as call:
                    self.assertEqual(loopctl.command_model_task_execute(path), 1)
                call.assert_not_called()
                self.assertFalse(json.loads(output.getvalue())['dispatched'])

    def test_entrypoint_keeps_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)/'input.json'
            path.write_text(json.dumps({**self.input, 'cli_request': self.request}))
            output = StringIO()
            self.adapter.execute_packet_attempt.side_effect = OSError('synthetic interruption')
            with redirect_stdout(output), mock.patch.object(execution, '_cli_adapter', return_value=(self.adapter, self.loader)):
                self.assertEqual(loopctl.command_model_task_execute(path), 1)
            self.assertIsNone(json.loads(output.getvalue())['dispatched'])


if __name__ == '__main__':
    unittest.main()
