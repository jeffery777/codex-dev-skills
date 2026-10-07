"""Synthetic protected targets only; no live Codex/provider qualification."""
from __future__ import annotations
import copy
import json
import os
import pathlib
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
sys.path.insert(0, str(ROOT/'skills/cli-session-handoff/scripts'))
import model_execution_target as targets


class TargetFixture:
    def __init__(self, home, *, prompt='Synthetic bounded prompt', head='a'*40,
                 executable_sha256='b'*64, cli_version='9.8.7', official=False):
        self.home = home; home.mkdir(mode=0o700, parents=True, exist_ok=True)
        (home/'model-execution').mkdir(mode=0o700, exist_ok=True)
        self.now = int(time.time()); self.prompt = prompt; self.head = head
        self.executable_sha256 = executable_sha256; self.cli_version = cli_version
        self.summary_values = {}
        role = 'loop_v2a_balanced_worker'
        canonical = (ROOT/'agent-profiles'/f'{role}.toml').read_bytes()
        model = 'synthetic-official' if official else 'synthetic-internal'
        effective = canonical.decode().replace('"gpt-6.1-sol"', json.dumps(model)).replace('"medium"', '"low"').encode()
        route_task = {'id': 'T1', 'workload_kind': 'implementation', 'qualification_scope': 'fixture-repair',
            'quality_preference': None, 'factors': {'ambiguity': 'moderate', 'reasoning_depth': 'balanced',
            'code_context_volume': 'medium', 'security_data_migration_public_contract_risk': 'routine',
            'write_blast_radius': 'bounded', 'latency_sensitivity': 'medium', 'cost_token_sensitivity': 'medium',
            'independence_parallelizability': 'independent', 'verification_burden': 'medium'}}
        provider = {'id': 'openai', 'billing': 'chatgpt-subscription', 'base_url': None, 'wire_api': 'responses', 'env_key': None} if official else {'id': 'synthetic', 'billing': 'internal', 'base_url': 'http://127.0.0.1:4000/v1', 'wire_api': 'responses', 'env_key': 'SYNTHETIC_MODEL_KEY'}
        self.record = {'id': 'fixture-target', 'enabled': True, 'expires_at': self.now+1000,
            'task': {'route_task': route_task, 'acceptance_sha256': targets.sha(b'Synthetic acceptance: preserve the original source.\n'), 'prompt_sha256': targets.sha(prompt.encode()),
                     'expected_head': head, 'role': role, 'checkpoint_sha256': None}, 'provider': provider, 'model': model,
            'reasoning_effort': 'low', 'runtime': 'cli', 'canonical_profile': self.artifact('canonical.toml', canonical),
            'effective_profile': self.artifact('effective.toml', effective),
            'catalog': self.artifact('catalog.json', json.dumps({'models': [{'slug': model, 'context_window': 16000}]}).encode()),
            'summaries': {}}
        common = {'schema_version': 1, 'identity_sha256': targets.canonical_sha(targets.identity(self.record)),
                  'task_sha256': targets.canonical_sha(self.record['task']), 'observed_at': self.now, 'expires_at': self.now+900}
        specifics = {'qualification': {'status': 'qualified', 'capability_class': 'balanced-worker', 'capability_tier': 'everyday', 'scope': 'fixture-repair', 'evidence_sha256': 'd'*64},
            'context': {'status': 'qualified', 'input_tokens': 1000, 'output_tokens': 1000, 'reasoning_tokens': 500,
                'margin_tokens': 1000, 'input_limit': 14000, 'output_limit': 2000, 'total_limit': 16000, 'client_limit': 16000, 'compact_limit': 12000},
            'capability': {'status': 'available', 'executable_sha256': executable_sha256, 'cli_version': cli_version,
                'public_config_keys': sorted(targets.PUBLIC_KEYS), 'tool_calling': True, 'streaming': True},
            'authorization': {'status': 'granted', 'authority_ref': 'trusted-host:synthetic', 'sandbox_ceiling': 'workspace-write'},
            'secret_check': {'status': 'excluded', 'evidence_sha256': 'd'*64}}
        for name, spec in specifics.items():
            self.write_summary(name, {**common, **spec}, refresh=False)
        self.refresh()

    def artifact(self, name, raw):
        path = self.home/'model-execution'/name
        path.write_bytes(raw); path.chmod(0o600)
        return {'path': 'model-execution/'+name, 'sha256': targets.sha(raw)}

    def write_summary(self, name, value, refresh=True):
        self.summary_values[name] = value
        self.record['summaries'][name] = self.artifact(name+'.json', json.dumps(value).encode())
        if refresh: self.refresh()

    def refresh(self, enabled=True):
        raw = json.dumps({'schema_version': 1, 'enabled': enabled, 'targets': [self.record]}).encode()
        path = self.home/targets.STORE; path.write_bytes(raw); path.chmod(0o600)
        self.ref = {'schema_version': 1, 'id': self.record['id'], 'store_sha256': targets.sha(raw), 'binding_sha256': targets.canonical_sha(self.record)}

    def resolve(self, **overrides):
        kwargs = {'prompt': self.prompt, 'expected_head': self.head, 'executable_sha256': self.executable_sha256,
                  'cli_version': self.cli_version, 'sandbox': 'read-only', 'now': self.now}
        kwargs.update(overrides)
        return targets.resolve(self.ref, **kwargs)


class ExecutionTargetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else None)
        self.addCleanup(self.temp.cleanup)
        self.home = pathlib.Path(self.temp.name).resolve()/'home'
        self.env = mock.patch.dict(os.environ, {'CODEX_HOME': str(self.home)}); self.env.start(); self.addCleanup(self.env.stop)
        self.f = TargetFixture(self.home)

    def test_valid_company_binding_projects_fixed_configuration(self):
        binding = self.f.resolve()
        self.assertEqual(binding.target_id, 'fixture-target')
        args = targets.config_argv(binding)
        self.assertIn('model_provider="synthetic"', args)
        self.assertIn('model="synthetic-internal"', args)
        self.assertTrue(any('requires_openai_auth=false' in arg for arg in args))
        self.assertNotIn('danger-full-access', ' '.join(args))

    def test_official_subscription_forces_chatgpt_and_credential_exclusion(self):
        self.f = TargetFixture(self.home, official=True); binding = self.f.resolve()
        self.assertIn('forced_login_method="chatgpt"', targets.config_argv(binding))
        env = targets.child_environment(binding, {'PATH': '/bin', 'HOME': '/synthetic', 'OPENAI_API_KEY': 'sentinel',
            'CODEX_API_KEY': 'sentinel', 'SYNTHETIC_MODEL_KEY': 'sentinel', 'AWS_SECRET_ACCESS_KEY': 'sentinel'})
        self.assertNotIn('sentinel', json.dumps(env)); self.assertEqual(env['CODEX_HOME'], str(self.home))

    def test_company_only_approved_key_and_shell_excludes(self):
        binding = self.f.resolve()
        env = targets.child_environment(binding, {'PATH': '/bin', 'SYNTHETIC_MODEL_KEY': 'synthetic-key-value',
            'OPENAI_API_KEY': 'other-key-value', 'PYTHONPATH': '/untrusted', 'GIT_DIR': '/untrusted'})
        self.assertEqual(env['SYNTHETIC_MODEL_KEY'], 'synthetic-key-value')
        self.assertNotIn('OPENAI_API_KEY', env); self.assertNotIn('GIT_DIR', env); self.assertNotIn('PYTHONPATH', env)
        self.assertTrue(any('shell_environment_policy.exclude' in arg for arg in targets.config_argv(binding)))
        with self.assertRaises(targets.TargetError): targets.child_environment(binding, {})

    def test_disabled_revoked_expired_and_unknown_fields(self):
        self.f.refresh(enabled=False)
        with self.assertRaisesRegex(targets.TargetError, 'target-store-disabled'): self.f.resolve()
        self.f.record['enabled'] = False; self.f.refresh()
        with self.assertRaisesRegex(targets.TargetError, 'target-revoked'): self.f.resolve()
        self.f.record['enabled'] = True; self.f.record['expires_at'] = self.f.now; self.f.refresh()
        with self.assertRaisesRegex(targets.TargetError, 'target-expired'): self.f.resolve()
        self.f.ref['flags'] = ['--model', 'untrusted']
        with self.assertRaises(targets.TargetError): self.f.resolve()

    def test_context_unknown_limits_and_boolean_rejected(self):
        original = copy.deepcopy(self.f.summary_values['context'])
        for key, value in [('status', 'unknown'), ('input_tokens', 999999), ('output_tokens', 0), ('reasoning_tokens', 999999), ('client_limit', 999999), ('compact_limit', 14000), ('input_limit', True)]:
            context = {**original, key: value}; self.f.write_summary('context', context)
            with self.subTest(key=key), self.assertRaises(targets.TargetError): self.f.resolve()

    def test_authority_secret_scope_class_version_and_staleness(self):
        for name, key, value in [('authorization', 'status', 'revoked'), ('authorization', 'authority_ref', True),
            ('secret_check', 'status', 'unknown'), ('qualification', 'scope', 'different'),
            ('qualification', 'capability_class', 'deep-reviewer'), ('capability', 'cli_version', 'other'),
            ('capability', 'tool_calling', False), ('capability', 'observed_at', self.f.now-301)]:
            original = copy.deepcopy(self.f.summary_values[name]); self.f.write_summary(name, {**original, key: value})
            with self.subTest(name=name, key=key), self.assertRaises(targets.TargetError): self.f.resolve()
            self.f.write_summary(name, original)

    def test_reference_store_file_profile_and_task_drift(self):
        with self.assertRaises(targets.TargetError): self.f.resolve(prompt='different')
        with self.assertRaises(targets.TargetError): self.f.resolve(expected_head='0'*40)
        with self.assertRaises(targets.TargetError): self.f.resolve(executable_sha256='0'*64)
        path = self.home/self.f.record['effective_profile']['path']; path.write_text('bad')
        with self.assertRaisesRegex(targets.TargetError, 'target-artifact-drift'): self.f.resolve()
        self.f.ref['store_sha256'] = '0'*64
        with self.assertRaisesRegex(targets.TargetError, 'target-store-drift'): self.f.resolve()

    def test_authorization_artifact_changed_during_resolve_is_rejected(self):
        original_artifact = targets._artifact
        changed = []

        def revoke_after_summary_read(home, ref, **kwargs):
            raw = original_artifact(home, ref, **kwargs)
            if ref['path'].endswith('secret_check.json') and not changed:
                self.f.write_summary('authorization', {
                    **self.f.summary_values['authorization'], 'status': 'revoked'
                }, refresh=False)
                changed.append(True)
            return raw

        with mock.patch.object(targets, '_artifact', side_effect=revoke_after_summary_read):
            with self.assertRaisesRegex(targets.TargetError, 'target-artifact-drift'):
                self.f.resolve()
        self.assertEqual(changed, [True])

    def test_profile_cannot_widen_instructions_or_sandbox(self):
        path = self.home/self.f.record['effective_profile']['path']
        raw = path.read_bytes().replace(b'workspace-write', b'danger-full-access')
        self.f.record['effective_profile'] = self.f.artifact('effective.toml', raw); self.f.refresh()
        with self.assertRaisesRegex(targets.TargetError, 'effective-profile-drift'): self.f.resolve()

    def test_provider_transport_billing_auth_and_arbitrary_config_rejected(self):
        original = copy.deepcopy(self.f.record['provider'])
        for key, value in [('base_url', 'http://example.invalid/v1'), ('base_url', 'https://user:secret@example.invalid/v1'),
            ('base_url', 'https://example.invalid/v1?key=secret'), ('billing', 'api'), ('env_key', 'OPENAI_API_KEY'), ('id', 'openai')]:
            self.f.record['provider'] = {**original, key: value}; self.f.refresh()
            with self.subTest(key=key), self.assertRaises(targets.TargetError): self.f.resolve()
        self.f.record['provider'] = {**original, 'headers': {'Authorization': 'Bearer synthetic'}}; self.f.refresh()
        with self.assertRaises(targets.TargetError): self.f.resolve()

    def test_protected_store_symlink_world_write_git_fifo_and_bounds(self):
        path = self.home/targets.STORE; raw = path.read_bytes()
        path.chmod(0o666)
        with self.assertRaises(targets.TargetError): self.f.resolve()
        path.chmod(0o600); moved = self.home/'saved.json'; path.rename(moved); path.symlink_to(moved)
        with self.assertRaises(targets.TargetError): self.f.resolve()
        path.unlink(); path.write_bytes(raw); path.chmod(0o600)
        (self.home/'.git').mkdir()
        with self.assertRaises(targets.TargetError): self.f.resolve()
        (self.home/'.git').rmdir(); path.unlink(); os.mkfifo(path, 0o600)
        with self.assertRaises(targets.TargetError): self.f.resolve()
        path.unlink(); path.write_bytes(b' '*(targets.trust.MAX_STORE_BYTES+1)); path.chmod(0o600)
        with self.assertRaises(targets.TargetError): self.f.resolve()

    def test_planner_identity_and_catalog_snapshot_are_complete(self):
        binding = self.f.resolve(); identity = targets.target_identity(binding)
        self.assertEqual(set(identity), {'provider_id', 'provider_config_sha256', 'model', 'runtime', 'profile_sha256', 'context_policy_sha256', 'model_catalog_sha256', 'billing'})
        self.assertEqual(identity['context_policy_sha256'], self.f.record['summaries']['context']['sha256'])
        identity['model'] = 'changed'
        self.assertEqual(targets.target_identity(binding)['model'], 'synthetic-internal')
        directory = self.home/'snapshot'; directory.mkdir(mode=0o700)
        path = targets.snapshot_catalog(binding, directory)
        self.assertEqual(targets.sha(path.read_bytes()), self.f.record['catalog']['sha256'])
        (self.home/self.f.record['catalog']['path']).write_text('changed after validated read')
        self.assertEqual(path.read_bytes(), binding.catalog_bytes)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError): targets.snapshot_catalog(binding, directory)

    def test_catalog_secret_metadata_and_nonfinite_rejected(self):
        for value in [{'models': [{'slug': self.f.record['model'], 'context_window': 16000, 'api_key': 'synthetic'}]},
                      {'models': [{'slug': self.f.record['model'], 'context_window': 16000, 'description': 'Bearer synthetic-value'}]}]:
            self.f.record['catalog'] = self.f.artifact('catalog.json', json.dumps(value).encode()); self.f.refresh()
            with self.assertRaisesRegex(targets.TargetError, 'target-catalog-contains-secret'): self.f.resolve()

    def test_duplicate_nonfinite_and_private_artifact_paths(self):
        path = self.home/targets.STORE
        for raw in [b'{"schema_version":1,"schema_version":1}', b'{"value":NaN}']:
            path.write_bytes(raw); self.f.ref['store_sha256'] = targets.sha(raw)
            with self.assertRaises(targets.TargetError): self.f.resolve()
        for unsafe in ['model-execution/../auth.json', 'model-execution/.env', 'auth.json', 'model-execution/.git/config']:
            self.f.record['catalog']['path'] = unsafe; self.f.refresh()
            with self.assertRaises(targets.TargetError): self.f.resolve()


if __name__ == '__main__': unittest.main()
