"""Synthetic decision contracts; not live authorization/runtime qualification."""
from __future__ import annotations
import copy
import json
import tempfile
from contextlib import redirect_stdout
from io import StringIO
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import model_failover as failover
import agent_routing
import model_packet_store as packets


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
        # Keep anonymous reader fixtures importable without the unrelated CLI
        # dependency graph; this test still executes the actual entrypoint.
        import loopctl
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

    def test_terminal_policy_outcome_does_not_mask_traversed_revocation(self):
        for index in [0, 2]:
            self.p = fixture(); self.p['targets'][0]['availability']['status'] = 'unavailable'
            event(self.p, target='official'); event(self.p, correction=True)
            self.assertEqual(self.select()['reason'], 'official-quality-method-reset-required')
            self.p['targets'][index]['qualification']['status'] = 'revoked'
            self.assertEqual(self.select()['reason'], 'target-not-qualified-for-task')

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


class SyntheticUnusedGovernance:
    """Synthetic host callback only; echoing a binding is not real governance."""
    def __init__(self):
        self.calls = []
        self.mutate = lambda proof: None

    def readback_unused_source(self, binding):
        self.calls.append(copy.deepcopy(binding))
        proof = {'binding': binding, 'authorization_status': 'granted',
            'qualification_status': 'qualified', 'observed_at': 100, 'evidence_sha256': 'e'*64}
        self.mutate(proof)
        return proof


class UnusedSourceGuardTests(unittest.TestCase):
    def setUp(self):
        self.p = fixture()
        self.p['targets'][0]['availability']['status'] = 'unavailable'
        self.p['targets'][0]['qualification']['observed_at'] = 0
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        self.root.chmod(0o700)
        self.store = packets.PacketStore(self.root, 'packet-1')
        self.store.prepare('a'*64)
        self.reader = SyntheticUnusedGovernance()
        self.guard = failover.UnusedSourceGuard(self.store, self.reader, packet_identity_sha256='a'*64)

    def select(self):
        result = failover.select_next(self.p, _trusted_unused_source_guard=self.guard)
        self.assertFalse(result['dispatched'])
        return result

    def assertBlocked(self):
        result = self.select()
        self.assertEqual(result['status'], 'blocked')
        self.assertNotIn('unused_source_proof', result)

    def test_unused_source_governance_plans_official_and_records_snapshot_without_writing(self):
        ledger = self.root/'packet-1/ledger.json'
        before = ledger.read_bytes()
        result = self.select()
        self.assertEqual((result['status'], result['reason']), ('planned', 'internal-unavailable'))
        self.assertEqual(result['target']['identity'], self.p['targets'][2]['identity'])
        proof = result['unused_source_proof']
        binding = proof['binding']
        self.assertEqual(binding['packet_id'], 'packet-1')
        self.assertEqual(binding['packet_identity_sha256'], 'a'*64)
        self.assertEqual((binding['revision'], binding['generation']), (0, 0))
        self.assertEqual(binding['task'], self.p['task'])
        self.assertEqual(binding['source_id'], 'internal')
        self.assertEqual(binding['source_identity_sha256'], failover.identity_digest(self.p['targets'][0]['identity']))
        self.assertEqual(binding['qualification_sha256'], failover.identity_digest(self.p['targets'][0]['qualification']))
        self.assertEqual(binding['qualification_evidence_sha256'], 'e'*64)
        self.assertEqual(binding['ledger_sha256'], failover.identity_digest(json.loads(before)))
        self.assertEqual(proof['observed_at'], 100)
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(self.p['targets'][0]['qualification']['observed_at'], 0)

    def test_no_guard_and_schema_one_entrypoints_keep_conservative_behavior(self):
        result = failover.select_next(self.p)
        self.assertEqual(result['reason'], 'target-not-qualified-for-task')
        raw = json.dumps(self.p)
        self.assertEqual(failover.select_next(failover.parse_payload(raw.encode())), result)
        run = subprocess.run([sys.executable, str(ROOT/'skills/loop-engineering/scripts/model_failover.py')],
            input=raw, text=True, capture_output=True)
        self.assertEqual(run.returncode, 1)
        self.assertEqual(json.loads(run.stdout), result)
        route = route_fixture(); route['model_failover'] = self.p
        self.assertEqual(agent_routing.plan_model_failover(route['task'], route['model_failover'])['plan']['status'], 'blocked')

    def test_unused_guard_passes_through_real_v2_api_only_as_host_code(self):
        result = agent_routing.plan_model_failover(route_fixture()['task'], self.p,
            _trusted_unused_source_guard=self.guard)
        self.assertEqual(result['plan']['target']['id'], 'official')
        self.assertIn('unused_source_proof', result['plan'])

    def test_json_proof_and_lookalike_store_cannot_inject_host_code(self):
        for candidate in [True, {}, {'binding': {}, 'unused': True}, SyntheticUnusedGovernance()]:
            with self.subTest(candidate=type(candidate).__name__), self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_unused_source_guard=candidate)
        for key in ['unused_source_proof', '_trusted_unused_source_guard']:
            forged = copy.deepcopy(self.p); forged[key] = {'unused': True}
            with self.subTest(key=key), self.assertRaises(failover.FailoverError):
                failover.select_next(failover.parse_payload(json.dumps(forged).encode()))
        for store, reader in [(self.store, {'readback_unused_source': True}),
                              (mock.Mock(spec=packets.PacketStore), self.reader)]:
            with self.assertRaises(failover.FailoverError):
                failover.UnusedSourceGuard(store, reader, packet_identity_sha256='a'*64)

    def test_source_identity_authority_revocation_and_class_checks_still_apply(self):
        original = copy.deepcopy(self.p)
        for mode in ['revoked', 'unqualified', 'identity', 'authorization', 'scope', 'class', 'tier', 'authority-revoked']:
            self.p = copy.deepcopy(original)
            source = self.p['targets'][0]
            if mode in {'revoked', 'unqualified'}: source['qualification']['status'] = mode
            if mode == 'identity': source['identity']['model'] = 'changed'
            if mode == 'authorization': self.p['authorization']['target_identity_sha256'].pop(0)
            if mode == 'scope': source['qualification']['scopes'] = ['other']
            if mode == 'class': source['qualification']['capability_class'] = 'other'
            if mode == 'tier': source['qualification']['capability_tier'] = 'mechanical'
            if mode == 'authority-revoked': self.p['authorization']['status'] = 'revoked'
            with self.subTest(mode=mode): self.assertBlocked()
        self.assertEqual(self.reader.calls, [])

    def test_missing_stale_revoked_or_malformed_governance_is_blocked(self):
        for key, value in [('observed_at', 0), ('observed_at', 111), ('observed_at', True),
                ('authorization_status', 'revoked'), ('authorization_status', 'unknown'),
                ('qualification_status', 'revoked'), ('qualification_status', 'unqualified'),
                ('qualification_status', 'unknown'), ('evidence_sha256', 'bad')]:
            self.reader.mutate = lambda proof: proof.update({key: value})
            with self.subTest(key=key, value=value): self.assertBlocked()
        for reply in [None, {}, {'unused': True}]:
            with mock.patch.object(self.reader, 'readback_unused_source', return_value=reply):
                self.assertBlocked()
        with mock.patch.object(self.reader, 'readback_unused_source', side_effect=RuntimeError('private host detail')):
            self.assertEqual(self.select()['reason'], 'unused-source-proof-unconfirmed')

    def test_governance_binds_exact_packet_task_source_and_evidence(self):
        for key in ['packet_id', 'packet_identity_sha256', 'revision', 'generation', 'ledger_sha256',
                    'source_id', 'source_identity_sha256', 'qualification_sha256',
                    'qualification_evidence_sha256', 'authorization_sha256', 'availability_sha256']:
            self.reader.mutate = lambda proof: proof['binding'].update({key: 'drifted'})
            with self.subTest(key=key): self.assertBlocked()
        for key in self.p['task']:
            self.reader.mutate = lambda proof: proof['binding']['task'].update({key: 'drifted'})
            with self.subTest(task_key=key): self.assertBlocked()
        for value in [False, 0.0]:
            self.reader.mutate = lambda proof: proof['binding'].update(revision=value)
            with self.subTest(revision_type=type(value).__name__): self.assertBlocked()

    def test_unprepared_identity_drift_busy_and_any_attempt_cannot_mean_unused(self):
        missing = packets.PacketStore(self.root, 'unprepared')
        self.guard = failover.UnusedSourceGuard(missing, self.reader, packet_identity_sha256='a'*64)
        self.assertBlocked()
        self.assertFalse((self.root/'unprepared/ledger.json').exists())
        self.guard = failover.UnusedSourceGuard(self.store, self.reader, packet_identity_sha256='b'*64)
        self.assertBlocked()
        self.guard = failover.UnusedSourceGuard(self.store, self.reader, packet_identity_sha256='a'*64)
        with self.store.locked(): self.assertBlocked()
        self.store.claim('attempt-1', 'b'*64, 'c'*64, expected_revision=0)
        self.assertBlocked()
        self.store.retain_unknown('attempt-1')
        self.assertBlocked()
        self.store.publish_checkpoint('attempt-1', b'synthetic checkpoint', 'd'*64)
        self.assertBlocked()
        self.assertEqual(self.reader.calls, [])

    def test_unused_snapshot_is_not_reused_after_claim_or_revocation(self):
        self.assertEqual(self.select()['status'], 'planned')
        self.reader.mutate = lambda proof: proof.update(qualification_status='revoked')
        self.assertBlocked()
        self.reader.mutate = lambda proof: None
        self.store.claim('attempt-1', 'b'*64, 'c'*64, expected_revision=0)
        self.assertBlocked()
        self.assertEqual(len(self.reader.calls), 2)

    def test_previous_governance_readback_cannot_cover_changed_qualification(self):
        previous = self.select()['unused_source_proof']
        self.p['targets'][0]['qualification']['evidence_sha256'] = 'b'*64
        with mock.patch.object(self.reader, 'readback_unused_source', return_value=previous):
            self.assertBlocked()

    def test_empty_ledger_with_prior_revision_or_corrupt_bytes_is_not_unused(self):
        with self.store.locked() as fd:
            ledger = self.store._read(fd)
            ledger['revision'] = 1
            self.store._write(fd, ledger)
        self.assertBlocked()
        (self.root/'packet-1/ledger.json').write_bytes(b'{"attempts":[]}')
        self.assertBlocked()
        self.assertEqual(self.reader.calls, [])

    def test_exception_is_limited_to_expired_unused_startup_source(self):
        original = copy.deepcopy(self.p)
        for mode in ['available', 'unknown', 'stale-availability', 'future-qualification', 'executed', 'traversed']:
            self.p = copy.deepcopy(original)
            source = self.p['targets'][0]
            if mode in {'available', 'unknown'}: source['availability']['status'] = mode
            if mode == 'stale-availability': source['availability']['observed_at'] = 0
            if mode == 'future-qualification': source['qualification']['observed_at'] = 111
            if mode == 'executed': event(self.p)
            if mode == 'traversed': event(self.p, target='official')
            with self.subTest(mode=mode): self.assertBlocked()
        self.assertEqual(self.reader.calls, [])

    def test_official_destination_still_requires_complete_fresh_evidence(self):
        original = copy.deepcopy(self.p)
        for mode in ['qualification-stale', 'revoked', 'scope', 'tier', 'identity', 'authorization',
                     'availability', 'executor', 'context', 'context-budget', 'billing', 'provider']:
            self.p = copy.deepcopy(original)
            target = self.p['targets'][2]
            if mode == 'qualification-stale': target['qualification']['observed_at'] = 0
            if mode == 'revoked': target['qualification']['status'] = 'revoked'
            if mode == 'scope': target['qualification']['scopes'] = ['other']
            if mode == 'tier': target['qualification']['capability_tier'] = 'mechanical'
            if mode == 'identity': target['identity']['model'] = 'changed'
            if mode == 'authorization': self.p['authorization']['target_identity_sha256'].pop()
            if mode == 'availability': target['availability']['status'] = 'unknown'
            if mode == 'executor': target['executor']['status'] = 'unsupported'
            if mode == 'context': target['context']['observed_at'] = 0
            if mode == 'context-budget': target['context']['client_limit'] = 1
            if mode == 'billing': target['identity']['billing'] = 'api'
            if mode == 'provider': target['identity']['provider_id'] = 'gateway'
            with self.subTest(mode=mode): self.assertBlocked()

    def test_callback_cannot_mutate_validated_selection_or_returned_receipt(self):
        expected = copy.deepcopy(self.p['targets'][2]['identity'])
        retained = []
        def mutate(proof):
            self.p['targets'][2]['identity']['model'] = 'changed-during-readback'
            self.p['task']['acceptance_sha256'] = '0'*64
            retained.append(proof)
        self.reader.mutate = mutate
        result = self.select()
        self.assertEqual(result['target']['identity'], expected)
        self.assertEqual(result['unused_source_proof']['binding']['task']['acceptance_sha256'], 'f'*64)
        retained[0]['binding']['source_id'] = 'changed-after-readback'
        self.assertEqual(result['unused_source_proof']['binding']['source_id'], 'internal')


    def test_caller_owned_context_uses_one_lock_and_preserves_snapshot(self):
        with mock.patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            with self.store.locked() as fd:
                context = self.store.planning_context(fd)
                before = self.store._read(fd)
                out = failover.select_next(self.p, _trusted_unused_source_guard=self.guard,
                    _trusted_locked_context=context)
                self.assertEqual(out['status'], 'planned')
                self.assertEqual(out['unused_source_proof']['binding']['ledger_sha256'], failover.identity_digest(before))
                self.assertEqual(self.store._read(fd), before)
            self.assertEqual(lock.call_count, 1)

    def test_context_rejects_replaced_lock_while_second_store_holds_new_lock(self):
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            lock_path = self.root / 'packet-1/lock'; saved = self.root / 'packet-1/saved-lock'
            lock_path.rename(saved)
            other = packets.PacketStore(self.root, 'packet-1')
            with other.locked():
                with self.assertRaises(failover.FailoverError):
                    failover.select_next(self.p, _trusted_locked_context=context,
                        _trusted_unused_source_guard=self.guard)
            lock_path.unlink(); saved.rename(lock_path)
        self.assertEqual(self.reader.calls, [])

    def test_context_rejects_equivalent_json_with_changed_original_bytes(self):
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            path = self.root / 'packet-1/ledger.json'; original = path.read_bytes()
            path.write_text(json.dumps(json.loads(original), indent=2))
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context,
                    _trusted_unused_source_guard=self.guard)
            path.write_bytes(original)
        self.assertEqual(self.reader.calls, [])

    def test_context_rejects_root_and_ancestor_symlink_replacement(self):
        for which in ('root', 'ancestor'):
            with self.subTest(which=which):
                base = self.root / ('context-' + which); base.mkdir(mode=0o700)
                root = base / 'packets'; root.mkdir(mode=0o700)
                store = packets.PacketStore(root, 'private'); store.prepare('a'*64)
                guard = failover.UnusedSourceGuard(store, self.reader, packet_identity_sha256='a'*64)
                with store.locked() as fd:
                    context = store.planning_context(fd)
                    original = root if which == 'root' else base
                    saved = original.with_name(original.name + '-saved')
                    original.rename(saved); original.symlink_to(saved, target_is_directory=True)
                    try:
                        with self.assertRaises(failover.FailoverError):
                            failover.select_next(self.p, _trusted_locked_context=context,
                                _trusted_unused_source_guard=guard)
                    finally:
                        original.unlink(); saved.rename(original)
        self.assertEqual(self.reader.calls, [])

    def test_context_requires_active_owned_fd_and_expires_at_exit(self):
        with self.assertRaises(packets.PacketError): self.store.planning_context(0)
        with self.store.locked() as fd:
            with self.assertRaises(packets.PacketError): self.store.planning_context(True)
            context = self.store.planning_context(fd)
        with self.assertRaises(failover.FailoverError):
            failover.select_next(self.p, _trusted_locked_context=context)
        with self.store.locked() as fd:
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context)
        self.assertEqual(self.reader.calls, [])

    def test_json_or_other_store_context_cannot_supply_locked_snapshot(self):
        with self.assertRaises(failover.FailoverError):
            failover.select_next(self.p, _trusted_locked_context={'already_locked':True})
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            other = packets.PacketStore(self.root, 'packet-1')
            guard = failover.UnusedSourceGuard(other, self.reader, packet_identity_sha256='a'*64)
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context, _trusted_unused_source_guard=guard)
        self.assertEqual(self.reader.calls, [])

    def test_context_detects_ledger_mutation_before_or_during_callback(self):
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            ledger = self.store._read(fd)
            changed = copy.deepcopy(ledger); changed['identity_sha256'] = 'b'*64
            self.store._write(fd, changed)
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context, _trusted_unused_source_guard=self.guard)
            self.assertEqual(self.reader.calls, [])
            self.store._write(fd, ledger)
            self.reader.mutate = lambda _: self.store._write(fd, changed)
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context, _trusted_unused_source_guard=self.guard)
            self.store._write(fd, ledger)

    def test_context_snapshot_copy_and_failed_nested_lock_do_not_change_lease(self):
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            _, copied = context._snapshot(); copied['identity_sha256'] = 'b'*64
            with self.assertRaises(packets.PacketError):
                with self.store.locked(): pass
            self.assertEqual(failover.select_next(self.p, _trusted_locked_context=context,
                _trusted_unused_source_guard=self.guard)['status'], 'planned')

    def test_context_rejects_packet_path_replacement_and_store_alias_drift(self):
        with self.store.locked() as fd:
            context = self.store.planning_context(fd)
            self.store.packet_id = 'other'
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context)
            self.store.packet_id = 'packet-1'
            original = self.root / 'packet-1'; saved = self.root / 'saved'
            original.rename(saved); original.symlink_to(saved, target_is_directory=True)
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_locked_context=context)
            original.unlink(); saved.rename(original)


class ArchivedDispatchHost:
    """Original bytes/outcomes are archived before the current reclassification."""
    def __init__(self):
        self.requests = []
        self.original_authorities = []
        self.events = []
        self.calls = []
        self.mutate = lambda proof: None

    def readback_historical_sources(self, binding):
        self.calls.append(copy.deepcopy(binding))
        proof = {'binding': binding, 'authorization_status': 'granted',
            'qualification_status': 'qualified', 'observed_at': 110, 'evidence_sha256': 'e'*64,
            'events': copy.deepcopy(self.events), 'requests': list(self.requests),
            'original_authorities': list(self.original_authorities)}
        self.mutate(proof)
        return proof


class HistoricalSourceGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        self.root.chmod(0o700)
        self.packet_number = 0
        self.history()

    def history(self, mutate_request=None, raw_transform=None, claim_target=None):
        self.packet_number += 1
        self.store = packets.PacketStore(self.root, f'packet-{self.packet_number}')
        self.store.prepare('a'*64)
        self.reader = ArchivedDispatchHost()
        self.guard = failover.HistoricalSourceGuard(self.store, self.reader, packet_identity_sha256='a'*64)
        self.p = fixture()
        for target in self.p['targets'][1:]: target['qualification']['capability_tier'] = 'advanced'
        self.route_task = route_fixture()['task']
        # A -> B -> C are independent original outcomes: exactly two corrections.
        for defect in ['A', 'B', 'C']:
            self.capture(defect, correction=defect != 'A', mutate_request=mutate_request,
                         raw_transform=raw_transform, claim_target=claim_target)
        self.p['now'] = 110
        self.p['task']['capability_tier'] = 'advanced'
        self.route_task['factors'].update(ambiguity='high', reasoning_depth='deep', verification_burden='high')

    def capture(self, defect, *, correction=False, target='internal', mutate_request=None,
                raw_transform=None, claim_target=None):
        index = len(self.p['events']); self.p['now'] = 100 + index
        selected = next(item for item in self.p['targets'] if item['id'] == target)
        profile = {'name': 'original-'+target, 'capability_class': 'balanced-worker',
            'capability_tier': selected['qualification']['capability_tier'],
            'available': True, 'config_valid': True, 'model_available': True, 'reasoning_available': True,
            'profile_digest': selected['identity']['profile_sha256'], 'sandbox': 'workspace-write',
            'parent_sandbox_mode': 'workspace-write', 'sandbox_non_widening': True,
            'allowed_workflow_scope': sorted(agent_routing.CLASS_WORKFLOW_SCOPE['balanced-worker'])}
        authority = {'schema_version': 1, 'authorization': copy.deepcopy(self.p['authorization']),
            'assigned_scope': ['src/repair.py'], 'ownership': {'owner': 'original-worker', 'disjoint': True}}
        route = agent_routing.build_route_receipt(task_id='T1', factors=self.route_task['factors'],
            workload_kind='implementation', contract_version=2,
            runtime={'custom_agents_available': True, 'profiles': [profile]},
            assigned_scope=list(authority['assigned_scope']), ownership=copy.deepcopy(authority['ownership']),
            source_revision={'head_sha': str(index)*40},
            authority_contract=authority)
        self.assertTrue(agent_routing.validate_route_receipt(route)['valid'])
        request = {'schema_version': 2, 'packet_id': self.store.packet_id,
            'packet_identity_sha256': 'a'*64, 'attempt_id': str(index+1), 'generation': index+1,
            'target_id': target, 'route_receipt': route, 'failover_payload': copy.deepcopy(self.p),
            'authority_contract': authority}
        if mutate_request is not None: mutate_request(request)
        raw = json.dumps(request, sort_keys=True, separators=(',', ':')).encode()
        if raw_transform is not None: raw = raw_transform(raw)
        revision = self.store.read_checkpoint()[0]['revision']
        self.store.claim(str(index+1), packets.digest(raw), claim_target or failover.identity_digest(selected['identity']),
                         expected_revision=revision)
        self.store.publish_checkpoint(str(index+1), b'original sealed patch '+str(index).encode(), 'd'*64)
        event(self.p, defect=defect, correction=correction, target=target)
        self.p['events'][-1]['source_sha256'] = route['source_revision_sha256']
        self.reader.requests.append(raw)
        # Retain the original authority independently at dispatch capture time;
        # readback never derives it from current requests or reclassification.
        self.reader.original_authorities.append(json.dumps({'request_sha256': packets.digest(raw),
            'authority_contract': copy.deepcopy(request['authority_contract'])},
            sort_keys=True, separators=(',', ':')).encode())
        self.reader.events.append(copy.deepcopy(self.p['events'][-1]))

    def select(self):
        result = agent_routing.plan_model_failover(self.route_task, self.p,
            _trusted_historical_source_guard=self.guard)
        self.assertFalse(result['dispatched'])
        self.assertEqual(result['classification']['capability_tier'], self.p['task']['capability_tier'])
        self.assertFalse(result['plan']['dispatched'])
        return result['plan']

    def assertRejected(self):
        try:
            result = self.select()
        except (failover.FailoverError, agent_routing.AgentRoutingContractError):
            return
        self.assertEqual(result['status'], 'blocked')
        self.assertNotIn('historical_source_proof', result)

    def test_actual_v2_reclassification_uses_original_dispatch_artifacts(self):
        before = self.store.read_checkpoint()[0]
        result = self.select()
        self.assertEqual((result['status'], result['target']['id']), ('planned', 'internal-best'))
        self.assertEqual(result['lineage_counts']['correction_rounds'], 2)
        proof = result['historical_source_proof']
        self.assertEqual(proof['source_requirements'], {'internal': 'everyday'})
        self.assertEqual((proof['binding']['revision'], proof['binding']['generation']), (6, 3))
        self.assertEqual(proof['binding']['events_sha256'], failover.identity_digest(self.reader.events))
        for attempt, raw, receipt in zip(before['attempts'], self.reader.requests, proof['original_dispatches']):
            original = failover.parse_payload(raw)
            self.assertEqual(packets.digest(raw), attempt['request_sha256'])
            self.assertEqual(receipt['target_sha256'], attempt['target_sha256'])
            self.assertEqual(original['route_receipt']['classification']['capability_tier'], 'everyday')
            self.assertEqual(receipt['route_receipt_id'], original['route_receipt']['route_receipt_id'])
            self.assertEqual(receipt['authority_contract_sha256'], agent_routing._digest(original['authority_contract']))
            self.assertEqual(receipt['assigned_scope_sha256'], agent_routing._digest(['src/repair.py']))
            self.assertEqual(original['authority_contract']['authorization']['scope'], 'repair')
        self.assertEqual(self.store.read_checkpoint()[0], before)

    @staticmethod
    def reseal_authority(request):
        route = request['route_receipt']; contract = request['authority_contract']
        route['assigned_scope'] = copy.deepcopy(contract['assigned_scope'])
        route['assigned_scope_sha256'] = agent_routing._digest(route['assigned_scope'])
        route['ownership'] = copy.deepcopy(contract['ownership'])
        route['authority_contract_sha256'] = agent_routing._digest(contract)
        route['route_receipt_id'] = agent_routing._digest({key: value for key, value in route.items() if key != 'route_receipt_id'})

    def test_guard_rejects_authentic_route_validator_gaps(self):
        def mutate(request, mode):
            route = request['route_receipt']
            if mode == 'disjoint': route['ownership']['disjoint'] = False
            if mode == 'owner': route['ownership']['owner'] = ''
            if mode == 'assigned-scope':
                route['assigned_scope'] = []
                route['assigned_scope_sha256'] = agent_routing._digest([])
            if mode == 'missing-authority-sha': route.pop('authority_contract_sha256')
            if mode == 'null-authority-sha': route['authority_contract_sha256'] = None
            if mode == 'wrong-authority-sha': route['authority_contract_sha256'] = '0'*64
            route['route_receipt_id'] = agent_routing._digest({key: value for key, value in route.items() if key != 'route_receipt_id'})
            # The global validator deliberately retains its existing contract.
            self.assertTrue(agent_routing.validate_route_receipt(route)['valid'])
        for mode in ['disjoint', 'owner', 'assigned-scope', 'missing-authority-sha', 'null-authority-sha', 'wrong-authority-sha']:
            with self.subTest(mode=mode):
                self.history(mutate_request=lambda request: mutate(request, mode))
                for attempt, raw in zip(self.store.read_checkpoint()[0]['attempts'], self.reader.requests):
                    self.assertEqual(attempt['request_sha256'], packets.digest(raw))
                self.assertRejected()

    def test_original_authority_must_bind_effective_task_scope_acceptance_and_target(self):
        for key, value in [('task_id', 'another-task'), ('scope', 'another-category'),
                ('acceptance_sha256', '0'*64), ('authority_ref', 'another-authority'),
                ('status', 'revoked'), ('observed_at', 0), ('target_identity_sha256', ['0'*64])]:
            for also_change_effective_summary in [False, True]:
                def mutate(request):
                    request['authority_contract']['authorization'][key] = value
                    if also_change_effective_summary:
                        request['failover_payload']['authorization'][key] = value
                    self.reseal_authority(request)
                    self.assertTrue(agent_routing.validate_route_receipt(request['route_receipt'])['valid'])
                # A different authority_ref in both original summaries is valid:
                # authority identity comes from the independently retained record,
                # not the current parent's reference string.
                if key == 'authority_ref' and also_change_effective_summary:
                    continue
                with self.subTest(key=key, effective=also_change_effective_summary):
                    self.history(mutate_request=mutate)
                    self.assertRejected()

    def test_original_authority_requires_literal_paths_and_disjoint_named_owner(self):
        cases = [('assigned_scope', paths) for paths in [[], [''], ['.'], ['../src/x'], ['/tmp/x'],
            ['src//x'], ['src/./x'], ['src/../x'], ['src\\x'], ['C:/x'], ['src/*'],
            ['src/x\n'], [' '], ['src/x', 'src/x'], [True], ['x'*257]]]
        cases += [('ownership', owner) for owner in [
            {'owner': 'worker', 'disjoint': False}, {'owner': 'worker', 'disjoint': 1},
            {'owner': '', 'disjoint': True}, {'owner': True, 'disjoint': True},
            {'owner': ' worker ', 'disjoint': True}, {'owner': 'worker\nother', 'disjoint': True},
            {'disjoint': True}, {'owner': 'worker', 'disjoint': True, 'extra': True}]]
        for key, value in cases:
            def mutate(request):
                request['authority_contract'][key] = value
                self.reseal_authority(request)
            with self.subTest(key=key, value=value):
                # Both the authenticated original bytes and the independent
                # original authority record contain the same invalid contract.
                self.history(mutate_request=mutate)
                self.assertRejected()

    def test_normalized_unicode_path_is_separate_from_workflow_category(self):
        def mutate(request):
            request['authority_contract']['assigned_scope'] = ['src/修復.py', 'tests/修復測試.py']
            self.reseal_authority(request)
        self.history(mutate_request=mutate)
        self.assertEqual(self.select()['status'], 'planned')

    def test_legacy_artifacts_are_not_upgraded_or_authority_reconstructed(self):
        def legacy(raw):
            request = failover.parse_payload(raw)
            request['schema_version'] = 1
            request.pop('authority_contract')
            return json.dumps(request).encode()
        self.history(raw_transform=legacy)
        self.assertRejected()
        for version in [1, True, 3]:
            self.history(mutate_request=lambda request: request.update(schema_version=version))
            with self.subTest(version=version): self.assertRejected()

    def test_authority_contract_shape_is_strict_even_with_matching_route_hash(self):
        for mode in ['missing', 'extra', 'wrong-version', 'bool-version', 'non-object-summary']:
            def mutate(request):
                contract = request['authority_contract']
                if mode == 'missing': contract.pop('schema_version')
                if mode == 'extra': contract['extra'] = True
                if mode == 'wrong-version': contract['schema_version'] = 2
                if mode == 'bool-version': contract['schema_version'] = True
                if mode == 'non-object-summary': contract['authorization'] = 'granted'
                self.reseal_authority(request)
            self.history(mutate_request=mutate)
            with self.subTest(mode=mode): self.assertRejected()

    def test_independent_original_authority_is_required_and_bound_to_exact_request(self):
        original = list(self.reader.original_authorities)
        for mode in ['missing', 'empty', 'extra', 'reordered', 'json-object', 'request-digest', 'contract', 'extra-field']:
            self.reader.original_authorities = list(original)
            self.reader.mutate = lambda proof: None
            if mode == 'missing': self.reader.mutate = lambda proof: proof.pop('original_authorities')
            if mode == 'empty': self.reader.original_authorities = []
            if mode == 'extra': self.reader.original_authorities.append(original[0])
            if mode == 'reordered': self.reader.original_authorities.reverse()
            if mode == 'json-object': self.reader.original_authorities[0] = failover.parse_payload(original[0])
            if mode in {'request-digest', 'contract', 'extra-field'}:
                record = failover.parse_payload(original[0])
                if mode == 'request-digest': record['request_sha256'] = '0'*64
                if mode == 'contract': record['authority_contract']['authorization']['acceptance_sha256'] = '0'*64
                if mode == 'extra-field': record['extra'] = True
                self.reader.original_authorities[0] = json.dumps(record).encode()
            with self.subTest(mode=mode): self.assertRejected()

    def test_independent_authority_parser_and_combined_bytes_are_bounded(self):
        original = self.reader.original_authorities[0]
        for raw in [b' '*(failover.MAX_BYTES+1), b'{"x":1,"x":2}', b'{"x":NaN}', b'['*10000]:
            self.reader.original_authorities[0] = raw
            with self.subTest(size=len(raw)): self.assertRejected()
        self.reader.original_authorities[0] = original
        request_bytes = sum(map(len, self.reader.requests))
        with mock.patch.object(failover, 'MAX_HISTORY_BYTES', request_bytes): self.assertRejected()

    def test_current_advanced_stage_retains_old_source_without_recursive_readback(self):
        self.capture('D', target='internal-best')
        self.p['now'] = 110
        result = self.select()
        self.assertEqual((result['status'], result['target']['id']), ('retry', 'internal-best'))
        self.assertEqual(result['historical_source_proof']['source_requirements'], {'internal': 'everyday'})
        self.assertEqual(len(self.reader.calls), 1)
        self.assertEqual(result['historical_source_proof']['original_dispatches'][-1]['required_tier'], 'advanced')

    def test_missing_guard_json_assertions_and_low_tier_retry_fail_closed(self):
        result = agent_routing.plan_model_failover(self.route_task, self.p)
        self.assertEqual(result['plan']['status'], 'blocked')
        for candidate in [{}, {'old_required_tier': 'everyday'}, ArchivedDispatchHost()]:
            with self.assertRaises(failover.FailoverError):
                failover.select_next(self.p, _trusted_historical_source_guard=candidate)
        for key in ['old_required_tier', 'historical_source_proof', '_trusted_historical_source_guard']:
            forged = copy.deepcopy(self.p); forged[key] = {'old_required_tier': 'everyday'}
            with self.assertRaises(failover.FailoverError):
                failover.select_next(failover.parse_payload(json.dumps(forged).encode()))
        self.p['events'] = self.p['events'][:1]
        self.assertRejected()  # Same low-tier source would be retried.
        self.assertEqual(self.reader.calls, [])

    def test_current_source_freshness_authority_revocation_scope_and_identity_remain_required(self):
        original = copy.deepcopy(self.p)
        for mode in ['stale', 'revoked', 'unqualified', 'scope', 'class', 'authority-stale', 'authority-revoked', 'identity']:
            self.p = copy.deepcopy(original); source = self.p['targets'][0]
            if mode == 'stale': source['qualification']['observed_at'] = 0
            if mode in {'revoked', 'unqualified'}: source['qualification']['status'] = mode
            if mode == 'scope': source['qualification']['scopes'] = ['other']
            if mode == 'class': source['qualification']['capability_class'] = 'deep-reviewer'
            if mode == 'authority-stale': self.p['authorization']['observed_at'] = 0
            if mode == 'authority-revoked': self.p['authorization']['status'] = 'revoked'
            if mode == 'identity':
                source['identity']['model'] = 'new-model'
                source['qualification']['identity_sha256'] = failover.identity_digest(source['identity'])
                self.p['authorization']['target_identity_sha256'][0] = source['qualification']['identity_sha256']
            with self.subTest(mode=mode): self.assertRejected()

    def test_destination_requires_latest_class_tier_and_all_fresh_checks(self):
        original = copy.deepcopy(self.p)
        for field, key, value in [('qualification', 'capability_tier', 'everyday'), ('qualification', 'observed_at', 0),
                ('qualification', 'capability_class', 'other'), ('qualification', 'status', 'revoked'),
                ('availability', 'status', 'unknown'), ('executor', 'status', 'unsupported'),
                ('context', 'status', 'unknown'), ('context', 'client_limit', 1)]:
            self.p = copy.deepcopy(original)
            self.p['targets'][1][field][key] = value
            with self.subTest(field=field, key=key): self.assertRejected()

    def test_original_bytes_and_route_receipt_cannot_be_replaced_by_new_classification(self):
        raw = self.reader.requests[0]
        self.reader.requests[0] = raw + b' '
        self.assertRejected()
        altered = failover.parse_payload(raw)
        altered['failover_payload']['task']['capability_tier'] = 'advanced'
        altered['route_receipt']['classification'] = agent_routing.classify_task(
            self.route_task['factors'], contract_version=2, workload_kind='implementation')
        self.reader.requests[0] = json.dumps(altered).encode()
        self.assertRejected()

    def test_authentic_but_invalid_original_dispatch_is_rejected(self):
        def mutate(request, mode):
            old = request['failover_payload']; source = old['targets'][0]; route = request['route_receipt']
            if mode == 'classification': route['classification']['capability_tier'] = 'advanced'
            if mode == 'policy-revision': route['routing_policy_revision'] = 'unknown-policy'
            if mode == 'profile':
                route['selected_profile_digest'] = 'c'*64
                route['config_evidence']['profile_digest'] = 'c'*64
                route['config_evidence_sha256'] = agent_routing._digest(route['config_evidence'])
            if mode == 'qualification-stale': source['qualification']['observed_at'] = 0
            if mode == 'qualification-tier': source['qualification']['capability_tier'] = 'mechanical'
            if mode == 'authorization': old['authorization']['status'] = 'revoked'
            if mode == 'context': source['context']['client_limit'] = 1
            if mode == 'policy': old['policy']['service_attempt_limit'] = 2
            if mode == 'prefix' and request['generation'] > 1: old['events'] = []
            if mode == 'task': old['task']['id'] = 'other'
            if mode == 'scope': old['task']['scope'] = 'other'
            if mode == 'acceptance': old['task']['acceptance_sha256'] = '0'*64
            if mode == 'generation': request['generation'] += 1
            if mode == 'attempt': request['attempt_id'] = 'other'
            if mode == 'target': request['target_id'] = 'official'
            route['route_receipt_id'] = agent_routing._digest({key: value for key, value in route.items() if key != 'route_receipt_id'})
        for mode in ['classification', 'policy-revision', 'profile', 'qualification-stale', 'qualification-tier',
                     'authorization', 'context', 'policy', 'prefix', 'task', 'scope', 'acceptance', 'generation', 'attempt', 'target']:
            # The invalid original bytes really ARE the claim's request digest;
            # a digest check alone would incorrectly accept these cases.
            self.history(mutate_request=lambda request: mutate(request, mode))
            with self.subTest(mode=mode): self.assertRejected()
        self.history(claim_target='f'*64)
        self.assertRejected()

    def test_complete_independent_events_cannot_be_deleted_reclassified_or_reordered(self):
        original = copy.deepcopy(self.p)
        for mode in ['delete', 'defect', 'source', 'reorder', 'unknown-write', 'counter']:
            self.p = copy.deepcopy(original)
            if mode == 'delete': self.p['events'].pop()
            if mode == 'defect': self.p['events'][0]['defect_id'] = 'changed'
            if mode == 'source': self.p['events'][0]['source_sha256'] = '0'*64
            if mode == 'reorder': self.p['events'][0]['attempt_id'], self.p['events'][1]['attempt_id'] = '2', '1'
            if mode == 'unknown-write': self.p['events'][0]['cause'] = 'unknown-write'
            if mode == 'counter': self.p['events'][2]['correction'] = False
            with self.subTest(mode=mode): self.assertRejected()

    def test_pending_unknown_busy_and_missing_ledger_never_establish_history(self):
        with self.store.locked(): self.assertRejected()
        self.store.claim('4', 'b'*64, 'c'*64, expected_revision=6)
        self.assertRejected()
        self.store.retain_unknown('4')
        self.assertRejected()
        self.guard = failover.HistoricalSourceGuard(packets.PacketStore(self.root, 'missing'), self.reader, packet_identity_sha256='a'*64)
        self.assertRejected()
        self.assertEqual(self.reader.calls, [])

    def test_earlier_checkpoint_must_still_read_back(self):
        ledger = self.store.read_checkpoint()[0]
        path = self.root/self.store.packet_id/(ledger['attempts'][0]['checkpoint_sha256']+'.patch')
        path.write_bytes(b'changed earlier patch')
        self.assertRejected()
        self.assertEqual(self.reader.calls, [])

    def test_existing_ledger_envelopes_are_validated_by_store_and_unknown_schema_rejected(self):
        self.assertEqual(self.store.read_checkpoint()[0]['schema_version'], 2)
        self.assertEqual(self.select()['status'], 'planned')
        with self.store.locked() as fd:
            ledger = self.store._read(fd)
            ledger.update(schema_version=3, supervisors={})
            self.store._write(fd, ledger)
        self.assertEqual(self.select()['status'], 'planned')
        with self.store.locked() as fd:
            ledger = self.store._read(fd)
            ledger['schema_version'] = 999
            self.store._write(fd, ledger)
        self.assertRejected()

    def test_history_cannot_authorize_same_class_tier_decrease(self):
        self.capture('D', target='internal-best')
        self.p['now'] = 110
        self.p['task']['capability_tier'] = 'senior'
        self.route_task['factors'].update(ambiguity='moderate', verification_burden='medium')
        # Current advanced destination can meet senior, but the archived advanced
        # dispatch means this is a decrease, outside the guard's authority.
        self.assertRejected()

    def test_missing_stale_revoked_drifted_or_failed_governance_is_rejected(self):
        for key, value in [('observed_at', 0), ('observed_at', 111), ('observed_at', True),
                ('authorization_status', 'revoked'), ('qualification_status', 'revoked'),
                ('requests', []), ('requests', ['json-style-request']), ('events', []), ('evidence_sha256', 'bad')]:
            self.reader.mutate = lambda proof: proof.update({key: value})
            with self.subTest(key=key, value=value): self.assertRejected()
        for key in ['revision', 'generation', 'packet_identity_sha256', 'events_sha256', 'targets_sha256', 'task']:
            self.reader.mutate = lambda proof: proof['binding'].update({key: 'drifted'})
            with self.subTest(key=key): self.assertRejected()
        with mock.patch.object(self.reader, 'readback_historical_sources', side_effect=RuntimeError('private host detail')):
            self.assertEqual(self.select()['reason'], 'historical-source-proof-unconfirmed')
        with self.assertRaises(failover.FailoverError):
            failover.HistoricalSourceGuard(mock.Mock(spec=packets.PacketStore), self.reader, packet_identity_sha256='a'*64)
        with self.assertRaises(failover.FailoverError):
            failover.HistoricalSourceGuard(self.store, {'requests': self.reader.requests}, packet_identity_sha256='a'*64)

    def test_original_parser_and_total_bytes_are_bounded(self):
        for transform in [lambda raw: b' '*(failover.MAX_BYTES+1), lambda raw: b'{"x":1,"x":2}',
                          lambda raw: b'{"x":NaN}', lambda raw: b'['*10000]:
            self.history(raw_transform=transform)
            self.assertRejected()
        self.history()
        with mock.patch.object(failover, 'MAX_HISTORY_BYTES', 1): self.assertRejected()

    def test_snapshot_does_not_reuse_previous_governance_or_mutable_input(self):
        original_target = copy.deepcopy(self.p['targets'][1]['identity'])
        def mutate(proof):
            self.p['targets'][1]['identity']['model'] = 'changed-by-callback'
        self.reader.mutate = mutate
        result = self.select()
        self.assertEqual(result['target']['identity'], original_target)
        self.reader.mutate = lambda proof: proof.update(qualification_status='revoked')
        self.assertRejected()


    def test_historical_planner_uses_caller_transaction_without_relocking(self):
        with mock.patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            with self.store.locked() as fd:
                context = self.store.planning_context(fd)
                out = agent_routing.plan_model_failover(self.route_task, self.p,
                    _trusted_historical_source_guard=self.guard, _trusted_locked_context=context)
                self.assertEqual(out['plan']['status'], 'planned')
                self.assertFalse(out['dispatched'])
            self.assertEqual(lock.call_count, 1)


class ResolutionHost(ArchivedDispatchHost):
    """Synthetic saved cause/effect archive and independently mutable runtime."""
    def __init__(self):
        super().__init__()
        self.records = []
        self.original_resolutions = []
        self.resolution_calls = []
        self.mutate_resolution = lambda proof: None
        self.raw_transform = lambda raw: raw
        self.runtime_state = 'stopped'
        self.external_effects = 'excluded'
        self.now = 100

    def readback_resolved_unknowns(self, binding):
        self.resolution_calls.append(copy.deepcopy(binding))
        proof = {'schema_version': 1, 'binding': binding, 'authorization_status': 'granted',
            'qualification_status': 'qualified', 'observed_at': self.now, 'evidence_sha256': 'e'*64,
            'resolutions': copy.deepcopy(self.records)}
        for item in proof['resolutions']:
            effect = item['effect']; effect['observed_at'] = self.now
            if effect['runtime'] is not None:
                effect['runtime'].update(state=self.runtime_state, external_effects=self.external_effects,
                    observed_at=self.now, expires_at=self.now+30)
            if effect['isolation'] is not None:
                effect['isolation']['proof'].update(observed_at=self.now, expires_at=self.now+30,
                    external_effects=self.external_effects)
        self.mutate_resolution(proof)
        self.last_raw = self.raw_transform(packets.canonical(proof))
        return self.last_raw

    def readback_historical_sources(self, binding):
        proof = super().readback_historical_sources(binding)
        proof['observed_at'] = self.now
        proof['original_resolutions'] = copy.deepcopy(self.original_resolutions)
        return proof


class ResolutionIsolation:
    synthetic_only = True

    def __init__(self, host):
        self.host = host
        self.external_effects = 'excluded'
        self.available = True

    def readback_isolation(self, binding):
        if not self.available:
            raise RuntimeError('revoked synthetic isolation')
        return {**binding, 'schema_version': 1, 'status': 'isolated', 'external_effects': self.external_effects,
            'evidence_sha256': 'e'*64, 'observed_at': self.host.now, 'expires_at': self.host.now+30}


class ResolvedUnknownTests(unittest.TestCase):
    def setUp(self):
        import base64
        self.encode = lambda raw: base64.b64encode(raw).decode()
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve(); self.root.chmod(0o700)
        self.reader = ResolutionHost(); self.adapter = ResolutionIsolation(self.reader)
        self.store = packets.PacketStore(self.root, 'resolution', _trusted_isolation_adapters={'synthetic': self.adapter})
        self.store.prepare('a'*64)
        self.guard = failover.ResolvedUnknownGuard(self.store, self.reader, packet_identity_sha256='a'*64)
        self.hsg = failover.HistoricalSourceGuard(self.store, self.reader, packet_identity_sha256='a'*64)
        self.p = fixture(); self.p['now'] = 100
        self.route_task = route_fixture()['task']
        timer = mock.patch.object(packets.time, 'time', side_effect=lambda: self.reader.now)
        timer.start(); self.addCleanup(timer.stop)

    def ledger(self):
        with self.store.locked() as fd:
            return self.store._read(fd)

    def select(self, historical=False):
        self.reader.now = self.p['now']
        return agent_routing.plan_model_failover(self.route_task, self.p,
            _trusted_resolved_unknown_guard=self.guard,
            _trusted_historical_source_guard=self.hsg if historical else None)['plan']

    def capture(self, path='quarantined', *, kind='quality', cause='capability', defect='A', correction=False,
                schema=3):
        index = len(self.p['events']); self.p['now'] = 100+index; self.reader.now = self.p['now']
        prior_raw = None
        if self.p['events']:
            self.assertIn(self.select()['status'], {'planned', 'retry'})
            prior_raw = self.reader.last_raw
        target = self.p['targets'][0]
        authority = {'schema_version': 1, 'authorization': copy.deepcopy(self.p['authorization']),
            'assigned_scope': ['src/repair.py'], 'ownership': {'owner': 'original-worker', 'disjoint': True}}
        profile = {'name': 'original-internal', 'capability_class': 'balanced-worker', 'capability_tier': 'everyday',
            'available': True, 'config_valid': True, 'model_available': True, 'reasoning_available': True,
            'profile_digest': target['identity']['profile_sha256'], 'sandbox': 'workspace-write',
            'parent_sandbox_mode': 'workspace-write', 'sandbox_non_widening': True,
            'allowed_workflow_scope': sorted(agent_routing.CLASS_WORKFLOW_SCOPE['balanced-worker'])}
        route = agent_routing.build_route_receipt(task_id='T1', factors=self.route_task['factors'],
            workload_kind='implementation', contract_version=2,
            runtime={'custom_agents_available': True, 'profiles': [profile]},
            assigned_scope=authority['assigned_scope'], ownership=authority['ownership'],
            source_revision={'head_sha': str(index)*40}, authority_contract=authority)
        request = {'schema_version': schema if prior_raw else 2, 'packet_id': self.store.packet_id,
            'packet_identity_sha256': 'a'*64, 'attempt_id': str(index+1), 'generation': index+1,
            'target_id': 'internal', 'route_receipt': route, 'failover_payload': copy.deepcopy(self.p),
            'authority_contract': authority}
        if prior_raw and schema == 3: request['prior_resolution_sha256'] = packets.digest(prior_raw)
        raw = packets.canonical(request); request_sha = packets.digest(raw); target_sha = failover.identity_digest(target['identity'])
        revision = self.ledger()['revision']; attempt_id = str(index+1)
        if path == 'published':
            self.store.reserve_runtime(attempt_id, request_sha, target_sha, expected_revision=revision,
                source_sha256=route['source_revision_sha256'], scope_sha256=route['assigned_scope_sha256'],
                acceptance_sha256=self.p['task']['acceptance_sha256'], host_id='host', backend_id='synthetic',
                policy_sha256='f'*64, runtime_id='runtime-'+attempt_id, runtime_descriptor_required=True)
            self.transition(attempt_id, 'launch-intent')
            with self.store.locked() as fd:
                ledger = self.store._read(fd); record = ledger['supervisors'][attempt_id]
                descriptor = {'schema_version': 1, 'binding': record['binding'], 'container_id': '1'*64,
                    'daemon_identity_sha256': '2'*64, 'workspace_sha256': '3'*64, 'workspace_identity_sha256': '4'*64,
                    'image_id': 'sha256:'+'5'*64, 'created_at': '2026-10-03T00:00:00Z', 'policy_sha256': 'f'*64}
                self.store._bind_runtime_descriptor(fd, ledger, attempt_id, descriptor,
                    expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))
            self.transition(attempt_id, 'observing')
            self.store.observe_supervisor_unknown(attempt_id, 'runtime-proof-unavailable')
            self.transition(attempt_id, 'export-intent')
            ledger, record = self.store.supervisor_snapshot(attempt_id)
            self.store.seal_supervisor_patch(attempt_id, b'saved patch', 'e'*64, expected_revision=ledger['revision'],
                record_sha256=packets.digest(packets.canonical(record)))
            ledger, record = self.store.supervisor_snapshot(attempt_id)
            self.store.publish_checkpoint(attempt_id, b'saved patch', 'e'*64, expected_revision=ledger['revision'],
                supervisor_sha256=packets.digest(packets.canonical(record)))
        else:
            self.store.claim(attempt_id, request_sha, target_sha, expected_revision=revision)
            ledger = self.store.retain_unknown(attempt_id)
            self.store.quarantine(attempt_id, expected_revision=ledger['revision'], isolation_adapter_id='synthetic')
        event(self.p, kind=kind, cause='unknown-write', defect=defect, correction=correction)
        e = self.p['events'][-1]; e['source_sha256'] = route['source_revision_sha256']
        ledger = self.ledger(); attempt = ledger['attempts'][-1]
        effect = {'path': path, 'status': 'resolved', 'external_effects': 'excluded', 'observed_at': self.reader.now,
            'evidence_sha256': 'e'*64, 'isolation': None, 'runtime': None, 'initial_source': None,
            'recovery_sha256': attempt['checkpoint_sha256'] or attempt['predecessor_sha256']}
        if path == 'quarantined':
            proof = self.adapter.readback_isolation({'packet_id': self.store.packet_id, 'attempt_id': attempt_id,
                'generation': attempt['generation'], 'identity_sha256': 'a'*64, 'target_sha256': target_sha,
                'checkpoint_sha256': attempt['predecessor_sha256']})
            effect['isolation'] = {'adapter_id': 'synthetic', 'proof': proof, 'source_isolated': True,
                'successor_isolated': True, 'sealed_isolated': True}
            if attempt['predecessor_sha256'] is None:
                source = b'immutable initial source artifact'
                manifest = packets.canonical({'schema_version': 1, 'packet_id': self.store.packet_id,
                    'identity_sha256': 'a'*64, 'attempt_id': attempt_id, 'request_sha256': request_sha,
                    'target_sha256': target_sha, 'source_sha256': e['source_sha256'], 'content_sha256': packets.digest(source)})
                effect['initial_source'] = {'manifest_bytes': self.encode(manifest), 'source_bytes': self.encode(source)}
                effect['recovery_sha256'] = packets.digest(manifest)
        else:
            record = ledger['supervisors'][attempt_id]
            effect['runtime'] = {'binding': record['binding'], 'runtime_descriptor_sha256': record['runtime_descriptor_sha256'],
                'runtime_identity_sha256': record['runtime_descriptor_sha256'], 'state': 'stopped', 'external_effects': 'excluded',
                'observed_at': self.reader.now, 'expires_at': self.reader.now+30, 'evidence_sha256': 'e'*64}
        self.reader.records.append({'attempt_id': attempt_id, 'request_sha256': request_sha, 'target_sha256': target_sha,
            'event_sha256': failover.identity_digest(e), 'request_bytes': self.encode(raw), 'effect': effect,
            'cause': {'status': 'confirmed', 'kind': kind, 'cause': cause, 'observed_at': self.reader.now, 'evidence_sha256': 'd'*64}})
        self.reader.events.append(copy.deepcopy(e)); self.reader.requests.append(raw)
        self.reader.original_authorities.append(packets.canonical({'request_sha256': request_sha, 'authority_contract': authority}))
        self.reader.original_resolutions.append({'request_sha256': request_sha, 'resolution_bytes': prior_raw}
            if prior_raw and schema == 3 else None)

    def transition(self, attempt_id, stage):
        ledger, record = self.store.supervisor_snapshot(attempt_id)
        self.store.supervisor_transition(attempt_id, stage, expected_revision=ledger['revision'],
            record_sha256=packets.digest(packets.canonical(record)))

    def assertBlocked(self):
        out = self.select()
        self.assertEqual(out['status'], 'blocked', out)
        self.assertFalse(out['dispatched']); self.assertNotIn('resolved_unknown_proof', out)
        return out

    def escalate(self):
        self.p['task']['capability_tier'] = 'advanced'
        self.route_task['factors'].update(ambiguity='high', reasoning_depth='deep', verification_burden='high')
        for target in self.p['targets'][1:]: target['qualification']['capability_tier'] = 'advanced'

    def test_quarantine_initial_source_resolution_plans_and_preserves_raw_events_ledger_and_counts(self):
        self.capture(); self.capture(correction=True)
        before = self.ledger(); events = copy.deepcopy(self.p['events']); raws = list(self.reader.requests)
        out = self.select()
        self.assertEqual((out['status'], out['target']['id']), ('planned', 'internal-best'))
        self.assertEqual(out['lineage_counts'], {'service_failures': 0, 'correction_rounds': 1})
        self.assertFalse(out['dispatched']); self.assertEqual(self.ledger(), before)
        self.assertEqual(self.p['events'], events); self.assertEqual(self.reader.requests, raws)
        self.assertTrue(all(e['cause'] == 'unknown-write' for e in self.p['events']))
        self.assertEqual(out['resolved_unknown_proof']['binding']['ledger_sha256'], failover.identity_digest(before))

    def test_published_seal_checkpoint_requires_fresh_actual_runtime(self):
        self.capture('published')
        self.assertEqual(self.select()['status'], 'retry')
        for state in ['running', 'unknown']:
            self.reader.runtime_state = state; self.assertBlocked()
        self.reader.runtime_state = 'stopped'; self.reader.external_effects = 'unknown'; self.assertBlocked()
        self.reader.external_effects = 'excluded'
        (self.root/'resolution'/'sealed-runtime-1.json').write_text('{}')
        self.assertBlocked()

    def test_published_resolution_plans_official_with_original_service_count(self):
        for _ in range(3): self.capture('published', kind='service', cause='retriable-service')
        before = self.ledger()
        out = self.select()
        self.assertEqual((out['status'], out['target']['id'], out['lineage_counts']['service_failures']),
                         ('planned', 'official', 3))
        self.assertFalse(out['dispatched']); self.assertEqual(self.ledger(), before)

    def test_runtime_proof_descriptor_generation_and_freshness_are_bound(self):
        self.capture('published')
        mutations = [lambda p: p['resolutions'][0]['effect']['runtime'].update(runtime_descriptor_sha256='b'*64),
            lambda p: p['resolutions'][0]['effect']['runtime'].update(runtime_identity_sha256='b'*64),
            lambda p: p['resolutions'][0]['effect']['runtime']['binding'].update(generation=2),
            lambda p: p['resolutions'][0]['effect']['runtime'].update(observed_at=0),
            lambda p: p['resolutions'][0]['effect']['runtime'].update(expires_at=100)]
        for mutate in mutations:
            self.reader.mutate_resolution = mutate; self.assertBlocked()
        self.reader.mutate_resolution = lambda p: None
        record = self.ledger()['supervisors']['1']
        (self.root/'resolution'/('runtime-'+record['runtime_descriptor_sha256']+'.json')).write_text('{}')
        self.assertBlocked()

    def test_quarantine_predecessor_is_read_back_without_fabricating_checkpoint(self):
        self.capture('published'); self.capture(correction=True)
        self.assertEqual(self.select()['status'], 'planned')
        attempt = self.ledger()['attempts'][-1]
        self.assertIsNone(attempt['checkpoint_sha256']); self.assertIsNotNone(attempt['predecessor_sha256'])
        (self.root/'resolution'/(attempt['predecessor_sha256']+'.patch')).write_bytes(b'changed')
        self.assertBlocked()

    def test_effect_resolution_does_not_invent_a_retriable_or_capability_cause(self):
        self.capture()
        for cause in ['unknown', 'timeout', 'isolation', 'unknown-write']:
            self.reader.records[0]['cause']['cause'] = cause
            self.assertEqual(self.assertBlocked()['reason'], 'resolved-outcome-cause-unconfirmed')
        self.reader.records[0]['cause'].update(cause='retriable-service')
        self.assertEqual(self.assertBlocked()['reason'], 'resolved-outcome-cause-conflict')
        self.reader.records[0]['cause'].update(cause='auth')
        self.assertEqual(self.assertBlocked()['reason'], 'non-fallback-failure')

    def test_original_service_budget_and_elapsed_time_are_not_reset(self):
        self.capture(kind='service', cause='retriable-service')
        self.capture(kind='service', cause='retriable-service')
        self.capture(kind='service', cause='retriable-service')
        out = self.select(); self.assertEqual(out['target']['id'], 'official')
        self.assertEqual(out['lineage_counts']['service_failures'], 3)
        self.p['policy']['service_attempt_limit'] = 20; self.p['now'] = 131
        out = self.select(); self.assertEqual(out['reason'], 'service-budget-exhausted')

    def test_host_only_default_off_json_forgery_and_wrong_guard_are_rejected(self):
        self.capture()
        self.assertEqual(failover.select_next(self.p)['reason'], 'write-outcome-readback-required')
        for guard in [{}, object()]:
            with self.assertRaises(failover.FailoverError): failover.select_next(self.p, _trusted_resolved_unknown_guard=guard)
        forged = copy.deepcopy(self.p); forged['resolved_unknown_proof'] = {}
        with self.assertRaises(failover.FailoverError): failover.select_next(forged)
        with self.assertRaises(failover.FailoverError):
            failover.ResolvedUnknownGuard(mock.Mock(spec=packets.PacketStore), self.reader, packet_identity_sha256='a'*64)

    def test_incomplete_unknown_coverage_initial_source_and_external_uncertainty_block(self):
        self.capture(); self.capture()
        mutations = [lambda p: p['resolutions'].pop(), lambda p: p['resolutions'].reverse(),
            lambda p: p['resolutions'][0]['effect'].update(external_effects='unknown'),
            lambda p: p['resolutions'][0]['effect'].update(initial_source=None),
            lambda p: p['resolutions'][0]['effect']['initial_source'].update(source_bytes=self.encode(b'changed')),
            lambda p: p['resolutions'][0]['effect']['isolation'].update(source_isolated=False),
            lambda p: p['resolutions'][0]['effect']['isolation'].update(adapter_id='other')]
        for mutate in mutations:
            self.reader.mutate_resolution = mutate; self.assertBlocked()
        self.reader.mutate_resolution = lambda p: None
        self.adapter.available = False; self.assertBlocked()

    def test_resolution_current_bindings_staleness_revocation_and_parser_bounds(self):
        self.capture()
        for key, value in [('packet_id', 'other'), ('packet_identity_sha256', 'b'*64), ('generation', 9),
                           ('revision', 0), ('ledger_sha256', 'b'*64), ('events_sha256', 'b'*64),
                           ('authorization_sha256', 'b'*64), ('targets_sha256', 'b'*64), ('planning_sha256', 'b'*64)]:
            self.reader.mutate_resolution = lambda p, k=key, v=value: p['binding'].update({k:v})
            self.assertBlocked()
        for key, value in [('observed_at', 0), ('authorization_status', 'revoked'), ('qualification_status', 'revoked')]:
            self.reader.mutate_resolution = lambda p, k=key, v=value: p.update({k:v}); self.assertBlocked()
        self.reader.mutate_resolution = lambda p: None
        for raw in [b'{}', b'{"x":1,"x":2}', b'{"x":NaN}', b' '*(failover.MAX_BYTES+1)]:
            self.reader.raw_transform = lambda _, raw=raw: raw; self.assertBlocked()

    def test_current_target_qualification_context_and_auth_remain_required(self):
        self.capture(); self.capture(correction=True)
        for mutate in [lambda p: p['authorization'].update(status='revoked'),
            lambda p: p['secret_check'].update(status='unknown'),
            lambda p: p['targets'][1]['qualification'].update(status='revoked'),
            lambda p: p['targets'][1]['context'].update(input_limit=1),
            lambda p: p['targets'][1]['executor'].update(status='unknown')]:
            saved = copy.deepcopy(self.p); mutate(self.p); self.assertBlocked(); self.p = saved

    def test_historical_same_lock_replays_saved_resolutions_and_preserves_original_artifacts(self):
        self.capture(); self.capture(correction=True); self.escalate()
        before = self.ledger(); originals = list(self.reader.requests)
        with mock.patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            out = self.select(historical=True)
            self.assertEqual(lock.call_count, 1)
        self.assertEqual((out['status'], out['target']['id']), ('planned', 'internal-best'))
        self.assertEqual(out['historical_source_proof']['binding']['ledger_sha256'], out['resolved_unknown_proof']['binding']['ledger_sha256'])
        self.assertEqual(self.ledger(), before); self.assertEqual(self.reader.requests, originals)
        self.assertEqual(out['historical_source_proof']['source_requirements'], {'internal':'everyday'})

    def test_after_fact_current_resolution_cannot_replace_original_dispatch_archive(self):
        self.capture(); self.capture(correction=True); self.escalate()
        self.assertEqual(self.select(historical=True)['status'], 'planned')
        archive = self.reader.original_resolutions[-1]
        saved = archive['resolution_bytes']; archive['resolution_bytes'] = self.reader.last_raw
        self.assertEqual(self.select(historical=True)['status'], 'blocked')
        archive['resolution_bytes'] = saved; archive['request_sha256'] = 'b'*64
        self.assertEqual(self.select(historical=True)['status'], 'blocked')

    def test_legacy_unknown_prefix_is_not_migrated_and_different_store_guard_is_rejected(self):
        self.capture(); self.capture(correction=True, schema=2); self.escalate()
        self.assertEqual(self.select(historical=True)['status'], 'blocked')
        self.hsg = failover.HistoricalSourceGuard(packets.PacketStore(self.root, 'resolution'), self.reader,
            packet_identity_sha256='a'*64)
        self.assertEqual(self.select(historical=True)['status'], 'blocked')

    def test_stale_snapshot_not_reused_after_claim_and_guard_does_not_write(self):
        self.capture()
        self.assertEqual(self.select()['status'], 'retry')
        raw = self.reader.last_raw
        self.capture()
        self.reader.raw_transform = lambda _: raw
        self.assertBlocked()
        self.reader.raw_transform = lambda raw: raw
        with mock.patch.object(self.store, '_write', side_effect=AssertionError('guard must be read only')):
            self.assertEqual(self.select()['status'], 'retry')

    def test_any_source_integration_state_remains_outside_resolution_authority(self):
        self.capture('published')
        original = self.ledger()
        for state in ['integration-intent', 'unknown', 'applied', 'not-applied']:
            ledger = copy.deepcopy(original); ledger.update(schema_version=4)
            ledger['revision'] += 1
            ledger['integrations'] = {'integration': {'schema_version': 1, 'operation_id': 'integration',
                'attempt_id': '1', 'generation': 1, 'candidate_sha256': 'b'*64, 'state': state,
                'intent_sha256': 'c'*64, 'writer_started': state != 'integration-intent',
                'result_sha256': None if state == 'integration-intent' else 'd'*64,
                'observations': [{'phase': 'integration-intent', 'revision': ledger['revision'], 'evidence_sha256': 'c'*64}]}}
            # Exact schema fixture in a real temp PacketStore; no source apply.
            with self.store.locked() as fd: self.store._write(fd, ledger)
            calls = len(self.reader.resolution_calls)
            self.assertBlocked(); self.assertEqual(len(self.reader.resolution_calls), calls)

    def test_claimed_or_unresolved_unknown_ledger_and_busy_lock_block(self):
        self.capture()
        ledger = self.store.claim('pending', 'b'*64, 'c'*64, expected_revision=self.ledger()['revision'])['ledger']
        self.assertBlocked()
        self.store.retain_unknown('pending'); self.assertBlocked()
        with self.store.locked(): self.assertBlocked()

    def test_missing_original_resolution_archive_and_altered_saved_cause_block_hsg(self):
        self.capture(); self.capture(correction=True); self.escalate()
        saved = self.reader.original_resolutions[-1]
        self.reader.original_resolutions[-1] = None
        self.assertEqual(self.select(historical=True)['status'], 'blocked')
        self.reader.original_resolutions[-1] = copy.deepcopy(saved)
        value = failover.parse_payload(saved['resolution_bytes'])
        value['resolutions'][0]['cause']['cause'] = 'auth'
        self.reader.original_resolutions[-1]['resolution_bytes'] = packets.canonical(value)
        self.assertEqual(self.select(historical=True)['status'], 'blocked')

    def _assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch(self, cause):
        self.capture(); self.capture()
        self.reader.records[0]['cause']['cause'] = cause
        self.assertEqual(self.select()['reason'], 'non-fallback-failure')
        original_select = self.select

        def capture_blocked_dispatch():
            # Simulate an executor claiming despite the actual planning block.
            # Capture keeps the original blocked-time resolution bytes intact;
            # only this fixture's admission assertion is bypassed.
            outcome = original_select()
            self.assertEqual((outcome['status'], outcome['reason']), ('blocked', 'non-fallback-failure'))
            return {**outcome, 'status': 'retry'}

        with mock.patch.object(self, 'select', side_effect=capture_blocked_dispatch):
            self.capture(correction=True)
        originals = list(self.reader.requests)
        archives = copy.deepcopy(self.reader.original_resolutions)
        archived = failover.parse_payload(archives[-1]['resolution_bytes'])
        self.assertEqual([r['cause']['cause'] for r in archived['resolutions']], [cause, 'capability'])
        self.assertEqual(failover.parse_payload(originals[-1])['prior_resolution_sha256'],
                         packets.digest(archives[-1]['resolution_bytes']))

        # Today's cause readback may change, but cannot legalize an original
        # dispatch whose own saved planning evidence prohibited fallback.
        self.reader.records[0]['cause']['cause'] = 'capability'
        self.assertEqual(self.select()['status'], 'planned')
        self.escalate()
        outcome = self.select(historical=True)
        self.assertEqual((outcome['status'], outcome['reason']), ('blocked', 'historical-source-proof-unconfirmed'))
        self.assertFalse(outcome['dispatched'])
        self.assertNotIn('historical_source_proof', outcome)
        self.assertEqual(self.reader.requests, originals)
        self.assertEqual(self.reader.original_resolutions, archives)

    def test_historical_auth_cause_cannot_be_cleared_after_dispatch(self):
        self._assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch('auth')

    def test_historical_permission_cause_cannot_be_cleared_after_dispatch(self):
        self._assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch('permission')

    def test_historical_config_cause_cannot_be_cleared_after_dispatch(self):
        self._assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch('config')

    def test_historical_context_cause_cannot_be_cleared_after_dispatch(self):
        self._assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch('context')

    def test_historical_secret_cause_cannot_be_cleared_after_dispatch(self):
        self._assert_historical_nonfallback_cause_cannot_be_cleared_after_dispatch('secret')


    def test_resolution_and_historical_planning_share_caller_transaction(self):
        self.capture(); self.capture(correction=True); self.escalate()
        self.reader.now = self.p['now']
        with mock.patch.object(self.store, 'locked', wraps=self.store.locked) as lock:
            with self.store.locked() as fd:
                context = self.store.planning_context(fd)
                out = agent_routing.plan_model_failover(self.route_task, self.p,
                    _trusted_resolved_unknown_guard=self.guard,
                    _trusted_historical_source_guard=self.hsg,
                    _trusted_locked_context=context)['plan']
                self.assertEqual(out['status'], 'planned')
                self.assertEqual(out['historical_source_proof']['binding']['ledger_sha256'],
                    out['resolved_unknown_proof']['binding']['ledger_sha256'])
            self.assertEqual(lock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
