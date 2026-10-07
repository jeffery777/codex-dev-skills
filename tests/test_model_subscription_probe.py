"""Subscription smoke-test controls; no login or provider requests."""
import importlib.util
import json
import pathlib
from types import SimpleNamespace
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('subscription_probe', ROOT / 'scripts/verify-model-subscription.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class SubscriptionProbeTests(unittest.TestCase):
    def test_environment_excludes_paid_api_and_endpoint_overrides(self):
        env = probe.environment(pathlib.Path('/synthetic-home'), pathlib.Path('/synthetic-control'))
        self.assertEqual(set(env), {'PATH', 'HOME', 'CODEX_HOME', 'PYTHONDONTWRITEBYTECODE'})
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('OPENAI_BASE_URL', env)

    def test_login_diagnostic_never_adopts_api_or_unknown_login(self):
        for code, text in [(1, 'ChatGPT'), (0, 'Logged in using an API key'), (0, ''),
                (0, 'ChatGPT and API key')]:
            self.assertFalse(probe.login_is_subscription(SimpleNamespace(returncode=code, stdout=text, stderr='')))
        self.assertTrue(probe.login_is_subscription(SimpleNamespace(
            returncode=0, stdout='', stderr='Logged in using ChatGPT')))

    def response(self, extra=None):
        events = [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': probe.MARKER}},
            {'type': 'turn.completed'}]
        if extra is not None:
            events.insert(0, extra)
        return b'\n'.join(json.dumps(event).encode() for event in events)

    def test_tool_events_cannot_be_reported_as_no_tool_success(self):
        self.assertTrue(probe.validate_events(self.response()))
        self.assertTrue(probe.validate_events(self.response(
            {'type': 'item.started', 'item': {'type': 'agent_message', 'text': ''}})))
        for kind in ['mcp_tool_call', 'command_execution', 'file_change']:
            for stage in ['item.started', 'item.updated', 'item.completed']:
                raw = self.response({'type': stage, 'item': {'type': kind}})
                self.assertFalse(probe.validate_events(raw))
                self.assertIn(kind, [item['type'] for item in probe.event_items(probe.parse_events(raw))])
        self.assertTrue(probe.validate_events(self.response(
            {'type': 'item.completed', 'item': {'type': 'error', 'message': 'synthetic diagnostic'}})))

    def test_incomplete_failed_or_malformed_events_remain_unqualified(self):
        for raw in [b'', b'[]', b'null', b'{', b' ' * (1024 * 1024 + 1),
                b'{"type":"item.completed","item":null}']:
            self.assertFalse(probe.validate_events(raw))
        self.assertFalse(probe.validate_events(self.response({'type': 'turn.failed'})))
        self.assertFalse(probe.validate_events(self.response({'type': 'error'})))
        self.assertFalse(probe.validate_events(self.response({'type': 'future.tool', 'item': {'type': 'command_execution'}})))
        self.assertFalse(probe.validate_events(self.response({'type': 'turn.started', 'item': {'type': 'mcp_tool_call'}})))
        self.assertFalse(probe.validate_events(self.response({'type': {'unexpected': 'shape'}})))
        self.assertFalse(probe.validate_events(self.response({'type': 'item.updated', 'item': {'type': []}})))
        self.assertFalse(probe.validate_events(b'{"type":"turn.completed"}'))


if __name__ == '__main__':
    unittest.main()
