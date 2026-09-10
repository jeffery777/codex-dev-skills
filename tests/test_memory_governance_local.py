from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests.test_memory_governance_core import c, db, GovernanceCore, ITEM
from memory_governance_host import PRODUCTION_ADAPTERS, AcceptedPreview
from memory_governance_local import LocalClock, LocalHost, RepositorySource, SingleRootRegistry

SPEC = importlib.util.spec_from_file_location('mg1_local_fixture', Path(__file__).parent / 'fixtures/memory-governance/local_ports.py')
local_fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(local_fixture)


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mg1-local-test-')
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.root = self.parent / 'managed'
        self.root.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(self.root)
        self.core = GovernanceCore(self.ports.host, enabled=True)
        self.core.initialize()

    def inventory(self):
        return {p.name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()) for p in self.root.iterdir()}

    def apply(self, operation, candidate=None, **kw):
        preview = self.core.preview(operation, ITEM, candidate, **kw)
        handle = self.core.authorize(preview)
        result = self.core.execute(handle)
        self.assertEqual('applied', result['result'], result)
        return preview, handle, result

    def test_real_clock_identity_rollback_and_fork_rejection(self):
        clock = LocalClock()
        first, second = clock.clock(), clock.clock()
        self.assertLessEqual(first.utc_seconds, second.utc_seconds)
        self.assertLessEqual(first.monotonic_ns, second.monotonic_ns)
        self.assertEqual(first.process_id, second.process_id)
        self.assertNotEqual(first.process_id, LocalClock().clock().process_id)
        with mock.patch('memory_governance_local.os.getpid', return_value=os.getpid() + 1):
            with self.assertRaisesRegex(c.ContractError, 'process-changed'):
                clock.clock()
        for attribute, value in (('time_ns', 0), ('monotonic_ns', 0)):
            with self.subTest(attribute=attribute), mock.patch('memory_governance_local.time.' + attribute, return_value=value):
                with self.assertRaisesRegex(c.ContractError, 'clock-untrusted'):
                    self.core.audit()

    def test_registry_one_time_identity_readback_and_no_adoption(self):
        binding = self.ports.registry.binding()
        with self.assertRaisesRegex(c.ContractError, 'already-initialized'):
            self.ports.registry.bind_initialized(binding, binding.main_identity, binding.lock_identity)
        for modified in (replace(binding, main_identity=None),
                         replace(binding, directory_identity=(True, 1)),
                         replace(binding, capabilities=frozenset({'erase-content'}))):
            with self.subTest(modified=modified), self.assertRaises(c.ContractError):
                SingleRootRegistry(modified)
        unbound = replace(binding, main_identity=None, lock_identity=None)
        registry = SingleRootRegistry(unbound)
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'file-identity-mismatch'):
            registry.bind_initialized(unbound, (0, 0), binding.lock_identity)
        self.assertEqual(unbound, registry.binding())
        self.assertEqual(before, self.inventory())
        drifted = replace(binding, directory_identity=(0, 0))
        with self.assertRaisesRegex(c.ContractError, 'root-binding-drift'):
            self.ports.host.authorize_read(drifted, 'audit', None)

    def test_missing_authority_or_qualification_and_denied_initialization_zero_write(self):
        before = self.inventory()
        for kwargs in ({'authority': False}, {'qualification': False}):
            with self.subTest(kwargs=kwargs):
                host = self.ports.compose(**kwargs)
                with self.assertRaises(c.ContractError):
                    GovernanceCore(host, enabled=True).audit()
                self.assertEqual(before, self.inventory())
        root = self.parent / 'denied'
        root.mkdir(mode=0o700)
        ports = local_fixture.SyntheticLocalPorts(root)
        ports.accepted = False
        with self.assertRaisesRegex(c.ContractError, 'initialization-unavailable'):
            GovernanceCore(ports.host, enabled=True).initialize()
        self.assertEqual([], list(root.iterdir()))

    def test_repository_artifact_mismatch_revocation_and_bounds_precede_review(self):
        candidate = self.ports.candidate()
        source = RepositorySource(self.ports, self.ports)
        binding = self.ports.registry.binding()
        valid = self.ports.read_artifact(binding, c.canonical(candidate['provenance'][0]))
        for changed in (replace(valid, content=b'wrong'), replace(valid, source_revision='b' * 40),
                        replace(valid, repository_id='other'), replace(valid, source_id='other'),
                        replace(valid, path='other.txt'), replace(valid, status='revoked'),
                        replace(valid, status='unavailable'), replace(valid, content=b'x' * 65537),
                        replace(valid, content=bytearray(valid.content)), True):
            with self.subTest(changed=type(changed)), mock.patch.object(self.ports, 'read_artifact', return_value=changed), \
                 mock.patch.object(self.ports, 'review_source', side_effect=AssertionError('review should not run')):
                with self.assertRaises(c.ContractError):
                    source.observe_source(binding, c.canonical(candidate))
        for source in (RepositorySource(self.ports, None), RepositorySource(None, self.ports)):
            with mock.patch.object(self.ports, 'read_artifact', side_effect=AssertionError('reader should not run')):
                with self.assertRaisesRegex(c.ContractError, 'source-port-unavailable'):
                    source.observe_source(binding, c.canonical(candidate))

    def test_artifact_match_does_not_authorize_unsupported_or_unsafe_candidate(self):
        candidate = self.ports.candidate()
        candidate['body'] = 'Unsupported inference from a correct source blob.'
        candidate['validation']['content_digest'] = c.content_digest(candidate)
        before = self.inventory()
        with self.assertRaises(c.ContractError):
            self.core.preview('add', ITEM, candidate)
        self.assertEqual(before, self.inventory())
        for safety in ('unknown', 'prohibited'):
            self.ports.safety = safety
            with self.assertRaisesRegex(c.ContractError, 'source-not-adoptable'):
                self.core.preview('add', ITEM, self.ports.candidate())

    def test_human_decision_port_unavailable_before_artifact_io(self):
        candidate = self.ports.candidate()
        binding = self.ports.registry.binding()
        now = candidate['created_at']
        source = candidate['provenance'][0]
        source.update(kind='human-confirmed-decision', reference={'evidence_id': 'synthetic-decision'},
                      source_revision='synthetic-decision-revision',
                      attestation={'scope_digest': c.digest(c.decode(binding.scope_bytes)),
                                   'policy_fingerprint': c.digest(c.POLICY), 'issuer_fingerprint': 'a' * 64,
                                   'accepted_at': now, 'binding_token': 'synthetic-untrusted-token'})
        candidate['validation']['content_digest'] = c.content_digest(candidate)
        with mock.patch.object(self.ports, 'read_artifact', side_effect=AssertionError('unexpected artifact read')):
            with self.assertRaisesRegex(c.ContractError, 'source-kind-unavailable'):
                RepositorySource(self.ports, self.ports).observe_source(binding, c.canonical(candidate))

    def test_source_review_binding_and_storage_qualification_drift_reject(self):
        candidate = self.ports.candidate()
        binding = self.ports.registry.binding()
        observation = RepositorySource(self.ports, self.ports).observe_source(binding, c.canonical(candidate))
        for changed in (replace(observation, verifier_fingerprint='a' * 64),
                        replace(observation, evidence_id='synthetic-wrong-evidence'),
                        replace(observation, policy_fingerprint='a' * 64)):
            with self.subTest(changed=changed), mock.patch.object(self.ports, 'review_source', return_value=changed):
                with self.assertRaisesRegex(c.ContractError, 'source-binding-mismatch'):
                    self.core.preview('add', ITEM, candidate)
        preview = self.core.preview('add', ITEM, candidate)
        handle = self.core.authorize(preview)
        before = self.inventory()
        self.ports.runtime = {**self.ports.runtime, 'sql_fingerprint': 'a' * 64}
        with self.assertRaisesRegex(c.ContractError, 'qualification-unavailable'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_same_qualification_id_cannot_hide_budget_drift(self):
        preview = self.core.preview('add', ITEM, self.ports.candidate())
        handle = self.core.authorize(preview)
        original = self.ports.work_budget
        def changed(*args):
            result = original(*args)
            result['growth_bound_bytes'] += 4096
            result['required_work_bytes'] += 4096
            return result
        before = self.inventory()
        with mock.patch.object(self.ports, 'work_budget', side_effect=changed):
            with self.assertRaisesRegex(c.ContractError, 'storage-drift'):
                self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_confirmation_denial_boolean_tamper_expiry_and_replay(self):
        value = self.ports.candidate()
        preview = self.core.preview('add', ITEM, value)
        before = self.inventory()
        self.ports.accepted = False
        with self.assertRaises(c.ContractError):
            self.core.authorize(preview)
        self.ports.accepted = True
        with mock.patch.object(self.ports, 'accept_preview', return_value=True):
            with self.assertRaisesRegex(c.ContractError, 'acceptance-unavailable'):
                self.core.authorize(preview)
        accepted = self.ports.accept_preview(self.ports.registry.binding(), c.canonical(preview))
        confirmation = c.decode(accepted.confirmation_bytes)
        confirmation['preview_digest'] = '0' * 64
        with mock.patch.object(self.ports, 'accept_preview', return_value=AcceptedPreview(accepted.preview_bytes, c.canonical(confirmation))):
            with self.assertRaises(c.ContractError):
                self.core.authorize(preview)
        handle = self.core.authorize(preview)
        with mock.patch('memory_governance_local.time.time_ns', return_value=preview['expires_at'] * 1_000_000_000):
            with self.assertRaises(c.ContractError):
                self.core.execute(handle)
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized-or-consumed'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_source_revocation_at_execute_and_postcommit(self):
        preview = self.core.preview('add', ITEM, self.ports.candidate())
        handle = self.core.authorize(preview)
        before = self.inventory()
        self.ports.source_current = False
        with self.assertRaises(c.ContractError):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())
        self.ports.source_current = True
        preview = self.core.preview('add', ITEM, self.ports.candidate())
        handle = self.core.authorize(preview)
        def revoke(stage):
            if stage == 'after-commit':
                self.ports.source_current = False
        with mock.patch('memory_governance_core._checkpoint', side_effect=revoke):
            result = self.core.execute(handle)
        self.assertEqual('committed-but-not-adoptable', result['result'])
        self.assertIsNotNone(result['proof'])
        self.assertEqual([], self.core.recall(['blue'])['items'])
        with self.core.audit() as audit:
            self.assertTrue(audit.page()['enumeration_complete'])

    def test_revision_conflict_and_source_absent_stop_preserve_state(self):
        preview = self.core.preview('add', ITEM, self.ports.candidate())
        handle = self.core.authorize(preview)
        other = GovernanceCore(self.ports.host, enabled=True)
        second = other.preview('add', ITEM, self.ports.candidate())
        other.execute(other.authorize(second))
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'revision-conflict'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())
        no_source = GovernanceCore(self.ports.compose(source=False), enabled=True)
        stop = no_source.preview('stop', ITEM)
        self.assertEqual('applied', no_source.execute(no_source.authorize(stop))['result'])
        with self.assertRaises(c.ContractError):
            no_source.preview('resume', ITEM)

    def test_reopen_without_preview_only_reads_proof_and_cannot_replay(self):
        preview, handle, result = self.apply('add', self.ports.candidate())
        fresh = GovernanceCore(self.ports.reopened().host, enabled=True)
        before = self.inventory()
        readback = fresh.readback(preview['operation_id'], c.digest(preview))
        self.assertEqual('state-unknown', readback['result'])
        self.assertEqual(result['proof'], readback['proof'])
        self.assertEqual(before, self.inventory())
        with self.assertRaisesRegex(c.ContractError, 'preview-unrecognized'):
            fresh.authorize(preview)
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized-or-consumed'):
            fresh.execute(handle)

    def test_postcommit_read_authority_loss_does_not_hide_proof(self):
        preview = self.core.preview('add', ITEM, self.ports.candidate())
        handle = self.core.authorize(preview)
        def deny(stage):
            if stage == 'after-commit':
                self.ports.readable = False
        with mock.patch('memory_governance_core._checkpoint', side_effect=deny):
            with self.assertRaisesRegex(c.ContractError, 'state-unknown'):
                self.core.execute(handle)
        self.ports.readable = True
        result = self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)
        self.assertEqual('applied', result['result'])

    def test_git_fixture_end_to_end_history_projection_and_source_drift(self):
        git_root = self.parent / 'source'
        root = self.parent / 'git-managed'
        root.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(root, git_root=git_root)
        self.core = GovernanceCore(self.ports.host, enabled=True)
        self.core.initialize()
        first = self.ports.candidate()
        self.apply('add', first)
        self.apply('update', self.ports.candidate(2, cue='green'))
        self.assertEqual([], self.core.recall(['blue'])['items'])
        self.assertEqual(1, len(self.core.recall(['green'])['items']))
        self.apply('stop')
        self.apply('update', self.ports.candidate(3, cue='red'))
        self.assertEqual([], self.core.recall(['red'])['items'])
        restored = copy.deepcopy(first)
        restored.update(revision=4, created_at=self.ports.clock_port.clock().utc_seconds)
        restored['validation'].update(content_digest=c.content_digest(restored),
                                      evidence_id='synthetic-new-restore', verified_at=restored['created_at'])
        self.ports.approve(restored)
        self.apply('restore', restored, restore_revision=1)
        self.assertEqual([], self.core.recall(['blue'])['items'])
        self.apply('resume')
        self.assertEqual(1, len(self.core.recall(['blue'])['items']))
        self.assertEqual([], self.core.recall(['green'])['items'])
        for revision in range(5, 11):
            self.apply('update', self.ports.candidate(revision))
        with self.assertRaisesRegex(c.ContractError, 'version-limit'):
            self.core.preview('update', ITEM, self.ports.candidate(11))
        with self.core.audit() as audit:
            item = audit.page()['items'][0]
            self.assertEqual(10, item['retained_versions'])
        self.ports.git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
                       '-c', 'core.hooksPath=/dev/null', 'commit', '--allow-empty', '-q', '-m', 'Synthetic drift')
        self.assertEqual([], self.core.recall(['blue'])['items'])
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))


if __name__ == '__main__':
    unittest.main()
