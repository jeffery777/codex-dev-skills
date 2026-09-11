from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

from tests.test_memory_governance_core import c, db, fixture, GovernanceCore, ITEM
from tests.test_memory_governance_local import local_fixture

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'tests/fixtures/memory-governance/process_readback_worker.py'


class ProcessReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mg1-process-readback-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.root = self.parent / 'managed'
        self.root.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(self.root, git_root=self.parent / 'source')
        self.core = GovernanceCore(self.ports.host, enabled=True)
        self.core.initialize()
        self.candidate = self.ports.candidate()
        b = self.ports.registry.binding()
        self.host = {'root': str(self.root), 'scope': c.decode(b.scope_bytes), 'profile': c.decode(b.profile_bytes),
                     **{key: list(getattr(b, key)) for key in ('directory_identity', 'main_identity', 'lock_identity')},
                     'filesystem_id': b.filesystem_id, 'adapter_fingerprint': b.adapter_fingerprint,
                     'git_root': str(self.ports.git_root), 'git_identity': list(self.ports.git_identity),
                     'gitdir_identity': list(self.ports.gitdir_identity),
                     'git_config_digest': hashlib.sha256(self.ports.git_config).hexdigest(),
                     'source_revision': self.ports.source_revision, 'approved': dict(self.ports.approved),
                     'readback_ids': [], 'source_current': True, 'readable': True,
                     'copies': {'coverage': 'unknown', 'copies': []}, 'clock_offset': 0,
                     'capacity_unavailable': False}

    def run_worker(self, request):
        return subprocess.run([str(ROOT / 'scripts/project-python'), str(WORKER)],
                              input=c.canonical(request), capture_output=True, cwd=ROOT, timeout=30,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def write(self, stage='after-commit', *, operation='add', candidate=None, restore_revision=None):
        request = {'mode': 'write', 'host': self.host, 'operation': operation,
                   'candidate': self.candidate if candidate is None and operation == 'add' else candidate,
                   'restore_revision': restore_revision, 'checkpoint': stage}
        child = self.run_worker(request)
        self.assertEqual(74 if stage == 'reply-loss' else 73, child.returncode, child.stderr.decode())
        output = c.decode(child.stdout)
        self.assertEqual({'operation_id', 'preview_digest', 'pid'}, set(output))
        self.assertNotEqual(os.getpid(), output['pid'])
        self.host['readback_ids'].append(output['operation_id'])
        return output

    def inventory(self):
        return {str(path.relative_to(self.parent)): (path.stat().st_ino, path.stat().st_mode,
                path.stat().st_mtime_ns, path.read_bytes()) for path in self.parent.rglob('*') if path.is_file()}

    def read(self, request, *, changes=None, expected='applied', error=None):
        host = {**copy.deepcopy(self.host), **(changes or {})}
        before = self.inventory()
        child = self.run_worker({'mode': 'read', 'host': host,
                                 'operation_id': request['operation_id'], 'preview_digest': request['preview_digest']})
        self.assertEqual(2 if error else 0, child.returncode, child.stderr.decode())
        output = c.decode(child.stdout)
        self.assertEqual(before, self.inventory(), 'reader modified managed or source files')
        self.assertNotEqual(os.getpid(), output['pid'])
        self.assertNotEqual(request['pid'], output['pid'])
        if error:
            self.assertEqual(error, output['error'])
            return output
        self.assertTrue(output['replay_rejected'])
        self.assertEqual(expected, output['result']['result'], output)
        return output

    def test_fresh_reader_after_commit_and_reply_loss_has_no_preview(self):
        first = self.write()
        observed = self.read(first)
        proof = observed['result']['proof']
        self.assertEqual('mg1-readback/v2', observed['result']['contract_version'])
        self.assertEqual('mg1-operation-proof/v2', proof['contract_version'])
        self.assertIn('artifact', observed['calls'])
        self.assertIn('review', observed['calls'])
        self.assertNotIn('accept', observed['calls'])
        self.assertEqual(5, len(proof['readback_basis']))
        self.assertLessEqual(len(c.canonical(proof)), 2048)
        self.assertNotIn(self.candidate['body'].encode(), c.canonical(proof))
        second = self.write('reply-loss', operation='stop')
        self.read(second)
        self.read(first, expected='state-unknown')

    def test_pretransaction_loss_without_proof_is_unknown(self):
        output = self.read(self.write('before-transaction'), expected='state-unknown')
        self.assertIsNone(output['result']['proof'])

    def test_full_copy_inventory_is_compared_without_retaining_identifiers(self):
        self.host['copies'] = {'coverage': 'partial', 'copies': [
            {'copy_id': 'synthetic-copy-' + str(number).zfill(2), 'kind': 'export', 'observation': 'known-present'}
            for number in range(32)]}
        request = self.write()
        result = self.read(request)['result']
        proof_bytes = c.canonical(result['proof'])
        self.assertNotIn(b'synthetic-copy-', proof_bytes)
        self.assertEqual('partial', result['external_copies']['coverage'])
        changed = copy.deepcopy(self.host['copies'])
        changed['copies'][0]['observation'] = 'unknown'
        self.read(request, changes={'copies': changed}, expected='state-unknown')

    def test_after_item_write_loss_leaves_journal_untouched(self):
        output = self.read(self.write('after-item-write'), expected='state-unknown')
        self.assertIsNone(output['result']['proof'])

    def test_precommit_loss_does_not_adopt_uncommitted_basis(self):
        output = self.read(self.write('before-commit'), expected='state-unknown')
        self.assertIsNone(output['result']['proof'])

    def test_fresh_authority_and_capacity_are_independent(self):
        request = self.write()
        for changes, expected in [({'source_current': False}, 'committed-but-not-adoptable'),
                                  ({'approved': {}}, 'committed-but-not-adoptable'),
                                  ({'capacity_unavailable': True}, 'committed-capacity-unproven'),
                                  ({'source_current': False, 'capacity_unavailable': True}, 'committed-capacity-unproven')]:
            with self.subTest(changes=changes):
                self.assertIsNotNone(self.read(request, changes=changes, expected=expected)['result']['proof'])
        self.read(request, changes={'readable': False}, error='read-unavailable')
        self.read(request, changes={'readback_ids': []}, error='read-unavailable')
        self.read(request)

    def test_actual_source_repository_progress_revokes_current_source(self):
        request = self.write()
        (self.ports.git_root / 'artifact.txt').write_bytes(local_fixture.ARTIFACT + b'Synthetic new revision.\n')
        self.ports.git('add', '--', 'artifact.txt')
        self.ports.git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
                       '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '-m', 'Synthetic source advance')
        self.read(request, expected='committed-but-not-adoptable')

    def test_external_copy_change_failure_and_expiry_keep_proof_unknown(self):
        request = self.write()
        changes = [{'copies': {'coverage': 'complete', 'copies': []}},
                   {'copies': {'coverage': 'unknown', 'copies': [
                       {'copy_id': 'synthetic-backup', 'kind': 'backup', 'observation': 'known-present'}]}},
                   {'copies': None}, {'clock_offset': c.DEFAULT_PROFILE['proof_seconds']}]
        for change in changes:
            with self.subTest(change=change):
                self.assertIsNotNone(self.read(request, changes=change, expected='state-unknown')['result']['proof'])
        self.read(request)

    def test_request_root_and_scope_mismatch_are_not_adopted(self):
        request = self.write()
        self.read({**request, 'preview_digest': 'f' * 64}, error='readback-binding')
        self.read(request, changes={'adapter_fingerprint': 'f' * 64}, expected='state-unknown')
        self.read(request, changes={'filesystem_id': 'synthetic-other-fs'}, expected='state-unknown')
        identity = list(self.host['main_identity']); identity[1] += 1
        self.read(request, changes={'main_identity': identity}, error='file-identity-mismatch')
        for key in ('principal_id', 'root_id', 'repository_id', 'policy_fingerprint', 'schema_fingerprint'):
            scope = dict(self.host['scope'])
            scope[key] = ('ffffffff-ffff-4fff-8fff-ffffffffffff' if key.endswith('_id') and key != 'repository_id'
                          else 'synthetic-other' if key == 'repository_id' else 'f' * 64)
            with self.subTest(key=key):
                if key in {'policy_fingerprint', 'schema_fingerprint'}:
                    self.read(request, changes={'scope': scope}, error='policy-fingerprint-mismatch' if key == 'policy_fingerprint' else 'schema-mismatch')
                else:
                    self.read(request, changes={'scope': scope}, expected='integrity-failed')
        self.read(request)

    def test_missing_corrupt_and_legacy_proof_basis_fail_closed(self):
        request = self.write()
        with sqlite3.connect(self.root / db.MAIN) as connection:
            original = connection.execute('SELECT document FROM proofs').fetchone()[0]
        proof = c.decode(original)
        changes = [b'{', c.canonical({k: v for k, v in proof.items() if k != 'readback_basis'}),
                   c.canonical({**proof, 'contract_version': 'mg1-operation-proof/v3'}),
                   c.canonical({**{k: v for k, v in proof.items() if k != 'readback_basis'}, 'contract_version': 'mg1-operation-proof/v1'})]
        for key, value in [('copies_digest', 'bad'), ('scope_digest', 'f' * 64),
                           ('copies_observed_at', proof['recorded_at'] + 1), ('readback_until', proof['recorded_at'])]:
            changes.append(c.canonical({**proof, 'readback_basis': {**proof['readback_basis'], key: value}}))
        for data in changes:
            with self.subTest(data=data[:60]):
                with sqlite3.connect(self.root / db.MAIN) as connection:
                    connection.execute('UPDATE proofs SET document=?', (data,))
                result = self.read(request, expected='integrity-failed')['result']
                self.assertIsNone(result['proof'])
        with sqlite3.connect(self.root / db.MAIN) as connection:
            connection.execute('UPDATE proofs SET document=?', (original,))
        self.read(request)

    def test_lifecycle_round_trips_do_not_revive_historical_operations(self):
        added = self.write()
        add_proof = self.read(added)['result']['proof']
        stopped = self.write(operation='stop')
        stop_proof = self.read(stopped)['result']['proof']
        resumed = self.write(operation='resume')
        current = self.read(resumed)['result']
        self.assertEqual(add_proof['after_digest'], current['state_digest'])
        self.assertEqual(add_proof, self.read(added, expected='state-unknown')['result']['proof'])
        stopped_again = self.write(operation='stop')
        current = self.read(stopped_again)['result']
        self.assertEqual(stop_proof['after_digest'], current['state_digest'])
        self.assertEqual(stop_proof, self.read(stopped, expected='state-unknown')['result']['proof'])
        self.read(resumed, expected='state-unknown')
        for changes in ({'source_current': False}, {'capacity_unavailable': True}):
            with self.subTest(changes=changes):
                self.assertEqual(stop_proof, self.read(stopped, changes=changes,
                                 expected='state-unknown')['result']['proof'])

    def test_later_authorized_revision_advances_without_restoring_old_handle(self):
        first = self.write()
        candidate = self.ports.candidate(2, cue='green')
        self.host['approved'] = dict(self.ports.approved)
        second = self.write(operation='update', candidate=candidate)
        result = self.read(second)['result']
        self.assertEqual(2, result['proof']['after_revision'])
        older = self.read(first, expected='state-unknown')['result']
        self.assertEqual(1, older['proof']['after_revision'])
        third = self.write(operation='stop')
        self.read(third)
        fourth = self.write(operation='resume')
        self.read(fourth)
        self.read(third, expected='state-unknown')
        restored = copy.deepcopy(self.candidate)
        restored.update(revision=3, created_at=self.ports.clock_port.clock().utc_seconds)
        restored['validation'].update(content_digest=c.content_digest(restored),
                                      verified_at=restored['created_at'], evidence_id='synthetic-process-restore')
        self.ports.approve(restored)
        self.host['approved'] = dict(self.ports.approved)
        fifth = self.write(operation='restore', candidate=restored, restore_revision=1)
        self.assertEqual(3, self.read(fifth)['result']['proof']['after_revision'])
        self.read(fourth, expected='state-unknown')


class ProofBasisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mg1-proof-basis-')
        self.addCleanup(self.temp.cleanup)
        self.host = fixture.SyntheticHost(Path(self.temp.name).resolve())
        self.core = GovernanceCore(self.host, enabled=True)
        self.core.initialize()
        value = fixture.version(); self.host.approve_source(value)
        self.preview = self.core.preview('add', ITEM, value)
        self.result = self.core.execute(self.core.authorize(self.preview))

    def test_strict_basis_shapes_and_maximum_encoded_proof(self):
        record = self.result['proof']
        wide = copy.deepcopy(record)
        wide.update(identity_epoch=c.MAX_NUMBER, acceptance_epoch=c.MAX_NUMBER,
                    before_revision=c.MAX_NUMBER-1, after_revision=c.MAX_NUMBER,
                    recorded_at=c.MAX_NUMBER-2592000, operation='restore',
                    restore_source_revision=c.MAX_NUMBER-1, acceptance_evidence_id='x'*64)
        wide['readback_basis'].update(copies_observed_at=c.MAX_NUMBER-2592000, readback_until=c.MAX_NUMBER)
        c.g1_proof(wide)
        self.assertEqual(1324, len(c.canonical(wide)))
        for basis in (None, {}, {**record['readback_basis'], 'unknown': True},
                      {**record['readback_basis'], 'copies_observed_at': True}):
            with self.subTest(basis=basis), self.assertRaises(c.ContractError):
                c.g1_proof({**record, 'readback_basis': basis})
        wide['acceptance_evidence_id'] = 'x' * 2048
        with self.assertRaises(c.ContractError):
            c.g1_proof(wide)

    def test_expiry_is_read_only_and_does_not_extend_mutation_confirmation(self):
        record = self.result['proof']
        self.host.now = record['readback_basis']['readback_until'] - 1
        self.assertEqual('applied', self.core.readback(record['operation_id'], record['preview_digest'])['result'])
        self.host.now += 1
        before = (self.host.binding().root / db.MAIN).read_bytes()
        for original in (None, self.preview):
            result = self.core.readback(record['operation_id'], record['preview_digest'], preview=original)
            self.assertEqual('state-unknown', result['result'])
            self.assertEqual(record, result['proof'])
        self.assertEqual(before, (self.host.binding().root / db.MAIN).read_bytes())
        with self.assertRaisesRegex(c.ContractError, 'preview-unrecognized'):
            GovernanceCore(self.host, enabled=True).authorize(self.preview)
        # 到期 proof 仍保留於歷史；不能阻止另一次獨立有效的 preview/confirmation。
        next_preview = self.core.preview('stop', ITEM)
        next_result = self.core.execute(self.core.authorize(next_preview))
        self.assertEqual('applied', next_result['result'])
        self.assertNotEqual(record['operation_id'], next_result['operation_id'])
        self.assertEqual('state-unknown', self.core.readback(record['operation_id'], record['preview_digest'])['result'])

    def test_caller_preview_cannot_replace_missing_basis(self):
        record = {k: v for k, v in self.result['proof'].items() if k != 'readback_basis'}
        with sqlite3.connect(self.host.binding().root / db.MAIN) as connection:
            connection.execute('UPDATE proofs SET document=?', (c.canonical(record),))
        result = self.core.readback(record['operation_id'], record['preview_digest'], preview=self.preview)
        self.assertEqual('integrity-failed', result['result'])
        self.assertIsNone(result['proof'])

    def test_legacy_schema_is_refused_without_migration(self):
        path = self.host.binding().root / db.MAIN
        with sqlite3.connect(path) as connection:
            meta = c.decode(connection.execute('SELECT document FROM root_meta').fetchone()[0])
            meta['contract_version'] = 'mg1-managed-content/v1'
            connection.execute('UPDATE root_meta SET document=?', (c.canonical(meta),))
        before = path.read_bytes()
        result = self.core.readback(self.result['operation_id'], self.result['preview_digest'])
        self.assertEqual('integrity-failed', result['result'])
        with self.assertRaisesRegex(c.ContractError, 'metadata-mismatch'):
            self.core.preview('stop', ITEM)
        self.assertEqual(before, path.read_bytes())

    def test_legacy_pure_contract_still_requires_preview(self):
        legacy = copy.deepcopy(self.result)
        legacy['contract_version'] = 'mg1-readback/v1'
        legacy['proof']['contract_version'] = 'mg1-operation-proof/v1'
        del legacy['proof']['readback_basis']
        limits = c.decode(self.host.binding().profile_bytes)
        c.g1_readback(legacy, self.preview['scope'], limits, self.preview)
        with self.assertRaisesRegex(c.ContractError, 'readback-copy-binding'):
            c.g1_readback(legacy, self.preview['scope'], limits)

    def test_v2_validator_rejects_wrong_scope_copies_and_expired_applied(self):
        limits = c.decode(self.host.binding().profile_bytes)
        for key, value in [('scope_digest', 'f'*64), ('copies_digest', 'f'*64)]:
            result = copy.deepcopy(self.result)
            result['proof']['readback_basis'][key] = value
            with self.assertRaises(c.ContractError):
                c.g1_readback(result, self.preview['scope'], limits)
        result = copy.deepcopy(self.result)
        result['observed_at'] = result['proof']['readback_basis']['readback_until']
        with self.assertRaisesRegex(c.ContractError, 'readback-copy-binding'):
            c.g1_readback(result, self.preview['scope'], limits)


if __name__ == '__main__':
    unittest.main()
