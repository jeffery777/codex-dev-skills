"""Synthetic decision contracts; not live authorization/runtime qualification."""
from __future__ import annotations
import json
import tempfile
from contextlib import redirect_stdout
from io import StringIO
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import model_failover as failover
import loopctl
import agent_routing


def fixture():
    targets = []
    for stage in ['internal', 'internal-best', 'official']:
        identity = {'provider_id': 'openai' if stage == 'official' else stage, 'provider_config_sha256': 'a'*64,
                    'model': stage, 'runtime': 'cli', 'profile_sha256': 'b'*64,
                    'context_policy_sha256': 'c'*64, 'model_catalog_sha256': 'd'*64,
                    'billing': 'chatgpt-subscription' if stage == 'official' else 'internal'}
        targets.append({'id': stage, 'stage': stage, 'identity': identity,
            'qualification': {'status': 'qualified', 'identity_sha256': failover.identity_digest(identity),
                'capability_class': 'balanced-worker', 'capability_tier': 'everyday', 'scopes': ['repair'],
                'observed_at': 100, 'evidence_sha256': 'e'*64},
            'availability': {'status': 'available', 'observed_at': 100, 'evidence_sha256': 'e'*64},
            'executor': {'status': 'public-supported', 'observed_at': 100, 'evidence_sha256': 'e'*64},
            'context': {'status': 'qualified', 'observed_at': 100, 'evidence_sha256': 'e'*64,
                'input_tokens': 1000, 'output_tokens': 100, 'reasoning_tokens': 100, 'margin_tokens': 100,
                'input_limit': 2000, 'output_limit': 500, 'total_limit': 3000, 'client_limit': 3000}})
    return {'schema_version': 1, 'enabled': True, 'now': 110, 'freshness_seconds': 60,
        'task': {'id': 'T1', 'scope': 'repair', 'acceptance_sha256': 'f'*64,
                 'capability_class': 'balanced-worker', 'capability_tier': 'everyday'},
        'policy': {'service_attempt_limit': 3, 'service_elapsed_limit_seconds': 30},
        'targets': targets, 'current_target': 'internal', 'events': [],
        'authorization': {'authority_ref': 'trusted-host-record:synthetic', 'status': 'granted',
            'task_id': 'T1', 'scope': 'repair', 'acceptance_sha256': 'f'*64,
            'target_identity_sha256': [failover.identity_digest(t['identity']) for t in targets], 'observed_at': 100},
        'secret_check': {'status': 'excluded', 'task_id': 'T1', 'scope': 'repair',
            'acceptance_sha256': 'f'*64, 'observed_at': 100, 'evidence_sha256': 'e'*64}}


def route_fixture():
    return {'task': {'id': 'T1', 'workload_kind': 'implementation', 'qualification_scope': 'repair',
        'factors': {'ambiguity': 'moderate', 'reasoning_depth': 'balanced', 'code_context_volume': 'medium',
            'security_data_migration_public_contract_risk': 'routine', 'write_blast_radius': 'bounded',
            'latency_sensitivity': 'medium', 'cost_token_sensitivity': 'medium',
            'independence_parallelizability': 'independent', 'verification_burden': 'medium'}},
        'model_failover': fixture()}


def event(p, kind='quality', cause='capability', defect='A', correction=False, target=None):
    target = target or p['current_target']
    transition = None
    if target != p['current_target']:
        source = next(t for t in p['targets'] if t['id'] == p['current_target'])
        reason = ('internal-unavailable' if source['availability']['status'] == 'unavailable'
                  else 'service-budget-exhausted' if p['events'] and p['events'][-1]['kind'] == 'service'
                  else 'confirmed-capability-escalation')
        transition = {'source_identity_sha256': failover.identity_digest(source['identity']),
                      'reason': reason, 'observed_at': 100+len(p['events']), 'evidence_sha256': 'e'*64}
    p['current_target'] = target
    p['events'].append({'attempt_id': str(len(p['events'])+1), 'task_id': 'T1', 'scope': 'repair',
        'acceptance_sha256': 'f'*64, 'target_id': target, 'observed_at': 100+len(p['events']),
        'kind': kind, 'cause': cause, 'defect_id': defect, 'correction': correction,
        'source_sha256': str(len(p['events']) % 10)*64, 'transition': transition})


class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()

    def select(self):
        r = failover.select_next(self.p)
        self.assertFalse(r['dispatched'])
        return r

    def test_internal_first_and_default_off(self):
        self.assertEqual(self.select()['target']['id'], 'internal')
        self.p['enabled'] = False
        self.assertEqual(self.select()['reason'], 'policy-disabled')

    def test_fresh_unavailable_goes_official(self):
        self.p['targets'][0]['availability']['status'] = 'unavailable'
        self.assertEqual(self.select()['target']['id'], 'official')
        self.p['targets'][0]['availability']['observed_at'] = 0
        self.assertEqual(self.select()['reason'], 'availability-stale')

    def test_service_attempt_and_elapsed_budgets(self):
        event(self.p, 'service', 'retriable-service')
        self.assertEqual(self.select()['status'], 'retry')
        for _ in range(2):
            event(self.p, 'service', 'retriable-service')
        self.assertEqual(self.select()['target']['id'], 'official')
        self.p = fixture(); event(self.p, 'service', 'retriable-service'); self.p['now'] = 130
        self.assertEqual(self.select()['target']['id'], 'official')

    def test_same_core_to_best_then_official_preserves_counts(self):
        event(self.p); event(self.p, correction=True)
        self.assertEqual(self.select()['target']['id'], 'internal-best')
        event(self.p, target='internal-best'); event(self.p, correction=True)
        r = self.select()
        self.assertEqual(r['target']['id'], 'official')
        self.assertEqual(r['lineage_counts']['correction_rounds'], 2)

    def test_a_to_b_to_c_and_source_change_do_not_reset(self):
        event(self.p); event(self.p, defect='B', correction=True)
        self.assertEqual(self.select()['status'], 'retry')
        event(self.p, defect='C', correction=True)
        self.assertEqual(self.select()['target']['id'], 'internal-best')

    def test_unknown_cause_requires_diagnosis(self):
        event(self.p); event(self.p, cause='unknown', correction=True)
        self.assertEqual(self.select()['status'], 'diagnose')

    def test_non_fallback_errors_and_unknown_write(self):
        for cause in ['auth', 'permission', 'config', 'context', 'secret', 'unknown-write']:
            with self.subTest(cause=cause):
                self.p = fixture(); event(self.p, 'service', cause)
                self.assertEqual(self.select()['status'], 'blocked')
        event(self.p, 'service', 'retriable-service')
        self.assertEqual(self.select()['reason'], 'write-outcome-readback-required')

    def test_secret_exclusion_and_authority_are_required(self):
        for status in ['present', 'unknown']:
            self.p['secret_check']['status'] = status
            self.assertEqual(self.select()['status'], 'blocked')
        self.p = fixture(); self.p['authorization']['status'] = 'revoked'
        self.assertEqual(self.select()['status'], 'blocked')
        self.p['authorization']['status'] = True
        with self.assertRaises(failover.FailoverError):
            self.select()

    def test_small_context_and_unknown_metadata(self):
        self.p['targets'][0]['context']['total_limit'] = 1200
        self.assertEqual(self.select()['reason'], 'target-context-budget-exceeded')
        self.p = fixture(); self.p['targets'][0]['context']['status'] = 'unknown'
        self.assertEqual(self.select()['reason'], 'target-context-unqualified')
        self.p['targets'][0]['context']['input_limit'] = None
        with self.assertRaises(failover.FailoverError):
            self.select()

    def test_separate_input_output_client_limits(self):
        for key, value in [('input_limit', 999), ('output_limit', 199), ('client_limit', 1299), ('output_tokens', 0)]:
            self.p = fixture(); self.p['targets'][0]['context'][key] = value
            self.assertEqual(self.select()['status'], 'blocked')

    def test_unqualified_scope_revocation_and_identity_drift(self):
        for key, value in [('status', 'unqualified'), ('status', 'revoked'), ('scopes', ['other']), ('identity_sha256', '0'*64), ('capability_class', 'reviewer')]:
            self.p = fixture(); self.p['targets'][0]['qualification'][key] = value
            self.assertEqual(self.select()['reason'], 'target-not-qualified-for-task')

    def test_target_authorization_and_task_scope(self):
        self.p['authorization']['target_identity_sha256'] = ['0'*64]
        self.assertEqual(self.select()['reason'], 'target-not-authorized')
        self.p = fixture(); self.p['authorization']['scope'] = 'other'
        self.assertEqual(self.select()['status'], 'blocked')

    def test_executor_availability_and_freshness(self):
        for section, key, value in [('executor', 'status', 'unsupported'), ('availability', 'status', 'unknown'), ('qualification', 'observed_at', 0)]:
            self.p = fixture(); self.p['targets'][0][section][key] = value
            self.assertEqual(self.select()['status'], 'blocked')

    def test_subscription_only(self):
        self.p['targets'][0]['availability']['status'] = 'unavailable'
        self.p['targets'][2]['identity']['billing'] = 'api'
        self.assertEqual(self.select()['reason'], 'official-subscription-required')

    def test_gateway_cannot_claim_official_subscription(self):
        self.p['targets'][0]['availability']['status'] = 'unavailable'
        self.p['targets'][2]['identity']['provider_id'] = 'gateway'
        self.assertEqual(self.select()['reason'], 'official-subscription-required')

    def test_loopctl_actual_entrypoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)/'input.json'
            for raw, expected in [(json.dumps(route_fixture()), 0), ('{"enabled":true,"enabled":false}', 1), (' '*(failover.MAX_BYTES+1), 1), (None, 1)]:
                if raw is None:
                    path.unlink()
                else:
                    path.write_text(raw)
                output = StringIO()
                with redirect_stdout(output):
                    code = loopctl.main(['model-failover-plan', str(path)])
                self.assertEqual(code, expected)
                result = json.loads(output.getvalue())
                self.assertFalse(result['dispatched'])
                self.assertEqual(result['plan']['status'] if expected == 0 else result['status'], 'planned' if expected == 0 else 'blocked')

    def test_existing_v2_classifier_binds_failover_task(self):
        document = route_fixture()
        result = agent_routing.plan_model_failover(document['task'], document['model_failover'])
        self.assertEqual(result['classification']['capability_class'], 'balanced-worker')
        self.assertEqual(result['classification']['capability_tier'], 'everyday')
        self.assertEqual(result['plan']['status'], 'planned')
        self.assertFalse(result['dispatched'])
        for key, value in [('capability_class', 'fast-read-explorer'), ('capability_tier', 'mechanical'), ('id', 'other'), ('scope', 'other')]:
            document = route_fixture(); document['model_failover']['task'][key] = value
            with self.subTest(key=key), self.assertRaises(agent_routing.AgentRoutingContractError):
                agent_routing.plan_model_failover(document['task'], document['model_failover'])

    def test_exceptional_target_needs_exceptional_classification(self):
        self.p['targets'][0]['qualification']['capability_tier'] = 'exceptional'
        self.assertEqual(self.select()['status'], 'blocked')
        self.p['task']['capability_tier'] = 'exceptional'
        self.assertEqual(self.select()['status'], 'planned')

    def test_official_stage_has_finite_budget(self):
        event(self.p); event(self.p, correction=True)
        event(self.p, target='internal-best'); event(self.p, correction=True)
        event(self.p, target='official'); event(self.p, correction=True)
        self.assertEqual(self.select()['reason'], 'official-quality-method-reset-required')

    def test_malformed_lineage_no_scope_reset_cycle_or_duplicate(self):
        for mutation in ['scope', 'acceptance', 'duplicate', 'cycle', 'current']:
            self.p = fixture(); event(self.p); event(self.p, correction=True)
            if mutation == 'scope': self.p['events'][1]['scope'] = 'new'
            if mutation == 'acceptance': self.p['events'][1]['acceptance_sha256'] = '0'*64
            if mutation == 'duplicate': self.p['events'][1]['attempt_id'] = '1'
            if mutation == 'cycle': event(self.p, target='official'); event(self.p, target='internal')
            if mutation == 'current': self.p['current_target'] = 'official'
            with self.subTest(mutation=mutation), self.assertRaises(failover.FailoverError):
                self.select()

    def test_historical_offline_transition_survives_company_recovery(self):
        self.p['targets'][0]['availability']['status'] = 'unavailable'
        event(self.p, target='official')
        self.p['targets'][0]['availability']['status'] = 'available'
        self.assertEqual(self.select()['status'], 'retry')
        self.p['events'][0]['transition']['source_identity_sha256'] = '0'*64
        with self.assertRaises(failover.FailoverError): self.select()

    def test_unavailable_source_cannot_bypass_revocation_or_drift(self):
        for mode in ['revoked', 'identity', 'authorization']:
            self.p = fixture(); self.p['targets'][0]['availability']['status'] = 'unavailable'
            if mode == 'revoked': self.p['targets'][0]['qualification']['status'] = 'revoked'
            if mode == 'identity': self.p['targets'][0]['identity']['model'] = 'drifted'
            if mode == 'authorization': self.p['authorization']['target_identity_sha256'].pop(0)
            with self.subTest(mode=mode): self.assertEqual(self.select()['status'], 'blocked')
        self.p = fixture(); event(self.p); event(self.p, correction=True)
        event(self.p, target='internal-best'); event(self.p, correction=True)
        self.p['targets'][0]['qualification']['status'] = 'revoked'
        self.assertEqual(self.select()['status'], 'blocked')

    def test_higher_qualified_tier_is_allowed_but_not_lower_or_invalid(self):
        event(self.p); event(self.p, correction=True)
        q = self.p['targets'][1]['qualification']; q['capability_tier'] = 'advanced'
        self.assertEqual(self.select()['target']['id'], 'internal-best')
        q['capability_tier'] = 'mechanical'
        self.assertEqual(self.select()['status'], 'blocked')
        q['capability_tier'] = 'made-up'
        with self.assertRaises(failover.FailoverError): self.select()
        self.p = fixture(); self.p['task']['capability_tier'] = 'made-up'
        with self.assertRaises(failover.FailoverError): self.select()

    def test_stage_transition_cannot_bypass_policy(self):
        for target in ['internal-best', 'official']:
            self.p = fixture(); event(self.p, target=target)
            with self.assertRaises(failover.FailoverError): self.select()
        self.p = fixture(); self.p['targets'][0]['availability']['status'] = 'unavailable'
        event(self.p, target='official')
        self.assertEqual(self.select()['status'], 'retry')

    def test_kind_cause_and_correction_baseline_validation(self):
        for kind, cause, correction in [('service', 'capability', False), ('quality', 'retriable-service', False), ('quality', 'capability', True)]:
            self.p = fixture(); event(self.p, kind, cause, correction=correction)
            with self.subTest(kind=kind, cause=cause), self.assertRaises(failover.FailoverError):
                self.select()

    def test_parse_payload_public_decoder(self):
        self.assertEqual(failover.parse_payload(json.dumps(fixture()).encode()), fixture())
        for raw in [b'{"a":1,"a":2}', b'{"a":Infinity}', b'\xff', b'['*10000, 'text']:
            with self.assertRaises(failover.FailoverError):
                failover.parse_payload(raw)

    def test_strict_types_unknown_fields_and_list_bounds(self):
        for key, value in [('now', True), ('now', float('nan')), ('events', []), ('schema_version', True)]:
            self.p = fixture(); self.p[key] = value
            if key == 'events': self.p['extra_counter'] = 1
            with self.subTest(key=key), self.assertRaises(failover.FailoverError):
                self.select()
        self.p = fixture(); self.p['events'] = [{}]*129
        with self.assertRaises(failover.FailoverError): self.select()

    def test_cli_rejects_duplicate_nonfinite_and_oversize_json(self):
        script = ROOT/'skills/loop-engineering/scripts/model_failover.py'
        for raw in ['{"enabled":true,"enabled":false}', '{"now":NaN}', ' '* (failover.MAX_BYTES+1)]:
            run = subprocess.run([sys.executable, str(script)], input=raw, text=True, capture_output=True)
            self.assertEqual(run.returncode, 1)
            self.assertFalse(json.loads(run.stdout)['dispatched'])
        run = subprocess.run([sys.executable, str(script)], input=json.dumps(fixture()), text=True, capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)['status'], 'planned')


if __name__ == '__main__':
    unittest.main()
