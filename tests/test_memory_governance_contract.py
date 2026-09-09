from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/loop-engineering/scripts'))
import memory_governance_contract as c
import memory_governance_storage as db

SPEC = importlib.util.spec_from_file_location('mg1_contract_fixture', ROOT/'tests/fixtures/memory-governance/synthetic_host.py')
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
LIMITS = dict(c.DEFAULT_PROFILE)
SCOPE = {'principal_id': '00000000-0000-4000-8000-000000000001',
         'root_id': '00000000-0000-4000-8000-000000000002',
         'repository_id': 'synthetic-repository', 'schema_fingerprint': db.SCHEMA_FINGERPRINT,
         'profile_digest': c.digest(LIMITS), 'policy_fingerprint': c.digest(c.POLICY)}


class ContractTests(unittest.TestCase):
    def test_canonical_matches_g0_recipe(self):
        import json
        value = {'b': [None, True, 2, '中文'], 'a': {'nested': 'x'}}
        self.assertEqual(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode(), c.canonical(value))
        self.assertEqual(value, c.decode(c.canonical(value)))

    def test_strict_json(self):
        for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.0}', b'{"x":Infinity}', b'"\\ud800"', b'{} trailing', b'"\xff"'):
            with self.subTest(data=data), self.assertRaises(c.ContractError):
                c.decode(data)
        for value in ({1: 'x'}, {'a': -1}, {'a': 2**53}, {'a': float('nan')}, {'a': 1.5}):
            with self.subTest(value=value), self.assertRaises(c.ContractError):
                c.canonical(value)
        cycle = []
        cycle.append(cycle)
        with self.assertRaises(c.ContractError):
            c.canonical(cycle)

    def test_exact_byte_and_complexity_limits(self):
        self.assertEqual(b'"xx"', c.canonical('xx', 4))
        with self.assertRaises(c.ContractError):
            c.canonical('xxx', 4)
        value = None
        for _ in range(34):
            value = [value]
        with self.assertRaises(c.ContractError):
            c.canonical(value)
        with self.assertRaises(c.ContractError):
            c.decode(b' ' * 100, 99)

    def test_profile_presets_and_no_synthetic_defaults(self):
        for size in (268435456, 1073741824, 4294967296):
            profile = {**LIMITS, 'data_limit_bytes': size, 'maintenance_max_bytes': size*5//4}
            self.assertEqual(profile, c.profile(profile))
        for change in ({'max_items': True}, {'max_versions': 11}, {'confirmation_seconds': 301},
                       {'data_limit_bytes': 100}, {'unknown': 1}):
            with self.subTest(change=change), self.assertRaises(c.ContractError):
                c.profile({**LIMITS, **change})

    def test_fact_and_procedure(self):
        c.validate_version(fixture.version(), SCOPE, LIMITS, candidate=True)
        value = copy.deepcopy(fixture.EXAMPLE)
        value['kind'] = 'procedure'
        value['procedure'] = {'prerequisites': ['Synthetic only'], 'steps': ['Validate fixture'],
                              'success_evidence': ['synthetic-source'], 'invalidation_conditions': ['Schema changes']}
        value['validation']['content_digest'] = c.content_digest(value)
        c.validate_version(value, SCOPE, LIMITS)
        for key in value['procedure']:
            bad = copy.deepcopy(value)
            bad['procedure'][key] = []
            bad['validation']['content_digest'] = c.content_digest(bad)
            with self.subTest(key=key), self.assertRaises(c.ContractError):
                c.validate_version(bad, SCOPE, LIMITS)

    def test_version_fields_and_bindings(self):
        paths = [(('revision',), True), (('retired_at',), 1), (('summary',), '中'*342),
                 (('cues',), ['Blue']), (('cues',), ['blue','blue']), (('cues',), ['a'*129]),
                 (('applicability','repository_id'), 'different'), (('applicability','paths'), ['../x']),
                 (('applicability','paths'), ['/x']), (('applicability','paths'), ['a//b']),
                 (('provenance',), []), (('procedure',), {}), (('validation','eligibility'), 'unknown'),
                 (('validation','policy_fingerprint'), 'a'*64), (('validation','verified_at'), 99)]
        for path, new in paths:
            value = fixture.version()
            target = value
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = new
            value['validation']['content_digest'] = c.content_digest(value)
            with self.subTest(path=path,new=new), self.assertRaises(c.ContractError):
                c.validate_version(value, SCOPE, LIMITS, candidate=True)
        value = fixture.version()
        value['extra'] = 'not allowed'
        with self.assertRaises(c.ContractError):
            c.validate_version(value, SCOPE, LIMITS)
        value = fixture.version()
        value['body'] = 'changed without digest'
        with self.assertRaisesRegex(c.ContractError, 'content-digest-mismatch'):
            c.validate_version(value, SCOPE, LIMITS)

    def test_complete_version_boundary_includes_provenance(self):
        value = fixture.version(body='x')
        value['body'] += 'x'*(16384-len(c.canonical(value)))
        value['validation']['content_digest'] = c.content_digest(value)
        self.assertEqual(16384, len(c.canonical(value)))
        c.validate_version(value, SCOPE, LIMITS)
        value['provenance'][0]['reference']['path'] += 'x'
        value['validation']['content_digest'] = c.content_digest(value)
        with self.assertRaises(c.ContractError):
            c.validate_version(value, SCOPE, LIMITS)

    def test_restore_requires_same_semantics_and_new_evidence(self):
        old = fixture.version()
        new = fixture.version(2, now=200)
        c.restore_content(new, old)
        for field, replacement in (('body', 'changed'), ('cues', ['other']), ('summary', 'changed')):
            bad = copy.deepcopy(new)
            bad[field] = replacement
            with self.subTest(field=field), self.assertRaises(c.ContractError):
                c.restore_content(bad, old)
        new['validation']['evidence_id'] = old['validation']['evidence_id']
        with self.assertRaises(c.ContractError):
            c.restore_content(new, old)

    def test_human_source_binding_and_restore_attestation(self):
        old = fixture.version()
        old['provenance'] = [{'source_id': 'decision', 'kind': 'human-confirmed-decision',
                              'reference': {'evidence_id': 'decision-source'}, 'source_revision': 'decision-r1',
                              'source_digest': 'b'*64,
                              'attestation': {'scope_digest': c.digest(SCOPE), 'policy_fingerprint': SCOPE['policy_fingerprint'],
                                              'issuer_fingerprint': 'c'*64, 'accepted_at': 100, 'binding_token': 'token-old'}}]
        old['validation']['content_digest'] = c.content_digest(old)
        c.validate_version(old, SCOPE, LIMITS)
        new = copy.deepcopy(old)
        new.update(revision=2, created_at=200)
        new['provenance'][0]['attestation'].update(accepted_at=200, binding_token='token-new')
        new['validation'].update(content_digest=c.content_digest(new), verified_at=200, evidence_id='new-evidence')
        c.validate_version(new, SCOPE, LIMITS)
        c.restore_content(new, old)
        new['provenance'][0]['attestation']['binding_token'] = 'token-old'
        with self.assertRaisesRegex(c.ContractError, 'restore-stale-attestation'):
            c.restore_content(new, old)

    def test_g2_schema_names_are_known_but_not_executable(self):
        for operation in c.SCHEMA_OPERATIONS-c.G1_OPERATIONS:
            with self.subTest(operation=operation), self.assertRaisesRegex(c.ContractError, 'capability-unavailable'):
                c.g1_operation(operation)
        with self.assertRaisesRegex(c.ContractError, 'invalid-operation'):
            c.g1_operation('purge-everything')
