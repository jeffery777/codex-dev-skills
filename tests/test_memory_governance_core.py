from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/loop-engineering/scripts'
sys.path.insert(0, str(SCRIPTS))
import memory_governance_contract as c
from memory_governance_core import GovernanceCore
import memory_governance_storage as db

SPEC = importlib.util.spec_from_file_location('mg1_synthetic_host', Path(__file__).parent / 'fixtures/memory-governance/synthetic_host.py')
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)
ITEM = '00000000-0000-4000-8000-000000000003'


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.host = fixture.SyntheticHost(Path(self.temporary.name))
        self.core = GovernanceCore(self.host, enabled=True)
        self.core.initialize()

    def apply(self, operation, candidate=None, **kw):
        if candidate is not None:
            self.host.approve_source(candidate)
        preview = self.core.preview(operation, ITEM, candidate, **kw)
        result = self.core.execute(self.core.authorize(preview))
        self.assertEqual('applied', result['result'], result)
        return preview, result

    def test_add_update_stop_resume_restore(self):
        first = fixture.version()
        self.apply('add', first)
        self.assertEqual(1, len(self.core.recall(['blue'])['items']))
        self.host.now = 200
        self.apply('update', fixture.version(2, now=200, cue='green'))
        self.assertEqual([], self.core.recall(['blue'])['items'])
        self.assertEqual(1, len(self.core.recall(['green','widget'])['items']))
        self.apply('stop')
        self.assertEqual([], self.core.recall(['green'])['items'])
        self.host.now = 300
        self.apply('update', fixture.version(3, now=300, cue='red'))
        self.assertEqual([], self.core.recall(['red'])['items'])
        self.host.now = 400
        restored = copy.deepcopy(first)
        restored.update(revision=4, created_at=400)
        restored['validation'].update(content_digest=c.content_digest(restored), verified_at=400, evidence_id='fresh-restore')
        self.apply('restore', restored, restore_revision=1)
        self.assertEqual([], self.core.recall(['blue'])['items'])
        self.apply('resume')
        self.assertEqual(1, len(self.core.recall(['blue'])['items']))
        self.assertEqual([], self.core.recall(['green'])['items'])
        with self.core.audit() as audit:
            page = audit.page()
            self.assertTrue(page['enumeration_complete'])
            self.assertEqual(4, page['items'][0]['retained_versions'])

    def test_confirmation_expiry_rejects_bool_equal_to_integer(self):
        with tempfile.TemporaryDirectory() as temporary:
            host = fixture.SyntheticHost(Path(temporary), now=0)
            core = GovernanceCore(host, enabled=True)
            core.initialize()
            candidate = fixture.version(now=0)
            host.approve_source(candidate)
            preview = core.preview('add', ITEM, candidate)
            preview['expires_at'] = 1
            c.g1_preview(preview, preview['scope'], c.decode(host.binding().profile_bytes))
            accepted = host.accept_preview(host.binding(), c.canonical(preview))
            confirmation = c.decode(accepted.confirmation_bytes)
            c.confirmation(confirmation, preview, 0)
            confirmation['expires_at'] = True
            with self.assertRaises(c.ContractError):
                c.confirmation(confirmation, preview, 0)

    def inventory(self):
        import hashlib
        return {p.name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
                for p in self.host.binding().root.iterdir()}

    def test_unqualified_and_disabled_zero_root_touch(self):
        from unittest import mock
        with mock.patch.object(db, 'root_fd', side_effect=AssertionError('root touched')):
            disabled = GovernanceCore(self.host)
            with self.assertRaisesRegex(c.ContractError, 'memory-disabled'):
                disabled.audit()
            self.host.qualified = False
            with self.assertRaisesRegex(c.ContractError, 'qualification-unavailable'):
                GovernanceCore(self.host, enabled=True).audit()

    def test_request_cannot_supply_confirmation_or_eligibility(self):
        from unittest import mock
        candidate = fixture.version()
        with mock.patch.object(db, 'connect', side_effect=AssertionError('writer touched')):
            self.host.accepted = False
            self.core.cancel()
            with self.assertRaises(c.ContractError):
                self.core.authorize({'confirmed': True})
        # Schema-valid eligibility 自述沒有 host 的 approved source 仍拒絕。
        with self.assertRaisesRegex(c.ContractError, 'source-not-adoptable'):
            self.core.preview('add', ITEM, candidate)
        self.host.approve_source(candidate)
        preview = self.core.preview('add', ITEM, candidate)
        with self.assertRaisesRegex(c.ContractError, 'host-unavailable'):
            self.core.authorize(preview)
        self.assertEqual(0, len(self.core.audit().page()['items']))

    def test_tampered_preview_and_handle_replay(self):
        value = fixture.version()
        self.host.approve_source(value)
        preview = self.core.preview('add', ITEM, value)
        modified = copy.deepcopy(preview)
        modified['candidate']['body'] = 'changed'
        with self.assertRaisesRegex(c.ContractError, 'preview-unrecognized'):
            self.core.authorize(modified)
        handle = self.core.authorize(preview)
        before = self.inventory()
        from memory_governance_core import ExecutionHandle
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized'):
            self.core.execute(ExecutionHandle(handle.operation_id))
        self.assertEqual(before, self.inventory())
        self.assertEqual('applied', self.core.execute(handle)['result'])
        after = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized'):
            self.core.execute(handle)
        self.assertEqual(after, self.inventory())

    def test_new_core_cannot_reuse_handle_and_readback_is_independent(self):
        value = fixture.version()
        self.host.approve_source(value)
        preview = self.core.preview('add', ITEM, value)
        handle = self.core.authorize(preview)
        another = GovernanceCore(self.host, enabled=True)
        with self.assertRaisesRegex(c.ContractError, 'handle-unrecognized'):
            another.execute(handle)
        result = self.core.execute(handle)
        unknown = another.readback(result['operation_id'], result['preview_digest'])
        self.assertEqual('state-unknown', unknown['result'])
        self.assertEqual(result['proof'], unknown['proof'])
        self.assertEqual('applied', another.readback(result['operation_id'], result['preview_digest'], preview=preview)['result'])
        result['proof']['after_digest'] = 'a'*64
        read = another.readback(preview['operation_id'], c.digest(preview), preview=preview)
        self.assertEqual('applied', read['result'])
        self.assertNotEqual('a'*64, read['proof']['after_digest'])

    def test_source_before_and_after_commit_drift(self):
        from unittest import mock
        import memory_governance_core as core_module
        candidate = fixture.version()
        self.host.approve_source(candidate)
        preview = self.core.preview('add', ITEM, candidate)
        handle = self.core.authorize(preview)
        before = self.inventory()
        self.host.source_available = False
        with self.assertRaisesRegex(c.ContractError, 'source-not-adoptable'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())
        self.host.source_available = True
        preview = self.core.preview('add', ITEM, candidate)
        handle = self.core.authorize(preview)
        def drift(stage):
            if stage == 'after-commit':
                self.host.source_available = False
        with mock.patch.object(core_module, '_checkpoint', side_effect=drift):
            result = self.core.execute(handle)
        self.assertEqual('committed-but-not-adoptable', result['result'])
        self.assertIsNotNone(result['proof'])
        self.assertEqual([], self.core.recall(['blue'])['items'])
        page = self.core.audit().page()
        self.assertEqual('partial', page['source_coverage'])
        self.assertIsNone(page['items'][0]['summary'])

    def test_resume_rechecks_sources(self):
        self.apply('add', fixture.version())
        self.apply('stop')
        self.host.source_available = False
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'source-not-adoptable'):
            self.core.preview('resume', ITEM)
        self.assertEqual(before, self.inventory())

    def test_sensitivity_unknown_and_prohibited_are_not_adoptable(self):
        value = fixture.version()
        self.host.approve_source(value)
        for safety in ('unknown', 'prohibited'):
            self.host.safety = safety
            with self.subTest(safety=safety), self.assertRaisesRegex(c.ContractError, 'source-not-adoptable'):
                self.core.preview('add', ITEM, value)
        self.host.safety = 'safe'
        self.apply('add', value)
        self.host.safety = 'prohibited'
        # stop 不要求原文重新通過新增資格。
        self.apply('stop')

    def test_revision_conflict_between_independent_cores(self):
        self.apply('add', fixture.version())
        self.host.now = 200
        candidate = fixture.version(2, now=200, cue='green')
        self.host.approve_source(candidate)
        preview = self.core.preview('update', ITEM, candidate)
        handle = self.core.authorize(preview)
        other = GovernanceCore(self.host, enabled=True)
        rival = fixture.version(2, now=200, cue='red')
        self.host.approve_source(rival)
        other.execute(other.authorize(other.preview('update', ITEM, rival)))
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'revision-conflict'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.core.recall(['green'])['items'])

    def test_clock_expiry_and_rollback(self):
        self.apply('add', fixture.version())
        for change in ('expiry', 'utc', 'monotonic', 'process'):
            current = GovernanceCore(self.host, enabled=True)
            self.host.now = 200
            self.host.monotonic = 1000
            preview = current.preview('stop', ITEM)
            handle = current.authorize(preview)
            before = self.inventory()
            if change == 'expiry':
                self.host.now = preview['expires_at']
            elif change == 'utc':
                self.host.now = 199
            elif change == 'monotonic':
                self.host.monotonic = 0
            else:
                import uuid
                self.host.process_id = str(uuid.uuid4())
            with self.subTest(change=change), self.assertRaises(c.ContractError):
                current.execute(handle)
            self.assertEqual(before, self.inventory())
        self.host.now = 99
        with self.assertRaisesRegex(c.ContractError, 'clock-untrusted'):
            GovernanceCore(self.host, enabled=True).audit()

    def test_confirmation_expired_before_host_is_not_requested(self):
        self.apply('add', fixture.version())
        preview = self.core.preview('stop', ITEM)
        self.host.now = preview['expires_at']
        before = self.host.calls.count('accept')
        with self.assertRaisesRegex(c.ContractError, 'expired'):
            self.core.authorize(preview)
        self.assertEqual(before, self.host.calls.count('accept'))

    def test_nonempty_journal_and_unknown_files_never_open_db(self):
        from unittest import mock
        import os
        root = self.host.binding().root
        for filename, code in ((db.JOURNAL, 'recovery-required'), (db.MAIN+'-wal', 'unexpected-managed-file')):
            path = root/filename
            path.write_bytes(b'synthetic-journal-canary')
            os.chmod(path, 0o600)
            before = self.inventory()
            with self.subTest(filename=filename), mock.patch.object(db, 'connect', side_effect=AssertionError('DB opened')):
                with self.assertRaisesRegex(c.ContractError, code):
                    self.core.audit()
            self.assertEqual(before, self.inventory())
            path.unlink()  # 測試擁有的暫存 fixture，非 core recovery。

    def test_audit_and_recall_leave_all_file_bytes_unchanged(self):
        self.apply('add', fixture.version())
        before = self.inventory()
        self.core.audit().page()
        self.core.recall(['WIDGET', 'BLUE'])
        self.assertEqual(before, self.inventory())

    def test_snapshot_lock_and_closed_cursor(self):
        self.apply('add', fixture.version())
        snapshot = self.core.audit()
        rival = GovernanceCore(self.host, enabled=True)
        preview = rival.preview('stop', ITEM)
        handle = rival.authorize(preview)
        with self.assertRaisesRegex(c.ContractError, 'busy'):
            rival.execute(handle)
        with self.assertRaisesRegex(c.ContractError, 'cursor-unavailable'):
            snapshot.page('invented-offset')
        snapshot.close()
        with self.assertRaisesRegex(c.ContractError, 'cursor-unavailable'):
            snapshot.page()
        # 過期 snapshot 不開新 snapshot 混合分頁。
        snapshot = self.core.audit()
        self.host.now += 300
        with self.assertRaisesRegex(c.ContractError, 'cursor-expired'):
            snapshot.page()
        snapshot.close()

    def test_version_limit_is_no_auto_prune(self):
        self.apply('add', fixture.version())
        for revision in range(2,11):
            self.host.now += 1
            self.apply('update', fixture.version(revision, now=self.host.now, cue=f'cue-{revision}'))
        self.host.now += 2592001
        value = fixture.version(11, now=self.host.now)
        self.host.approve_source(value)
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'version-limit'):
            self.core.preview('update', ITEM, value)
        self.assertEqual(before, self.inventory())
        self.assertEqual(10, self.core.audit().page()['items'][0]['retained_versions'])
        self.apply('stop')

    def test_capacity_and_proof_boundaries(self):
        # production 上限不縮成測試預設；admission 使用實際 Snapshot 型別。
        limits = dict(c.DEFAULT_PROFILE)
        from dataclasses import replace
        empty = db.Snapshot('a'*64, 1, 0, 0, 0, 0)
        for count in (9999,10000):
            snapshot = replace(empty, items=count)
            if count == 9999:
                self.core._admit(snapshot, 'add', limits)
            else:
                with self.assertRaisesRegex(c.ContractError, 'item-limit'):
                    self.core._admit(snapshot, 'add', limits)
        for operation in ('add','update','restore','resume','stop'):
            maximum = 33792 if operation == 'stop' else 32768
            self.core._admit(replace(empty, proofs=maximum-1), operation, limits)
            with self.subTest(operation=operation), self.assertRaisesRegex(c.ContractError, 'proof-limit'):
                self.core._admit(replace(empty, proofs=maximum), operation, limits)
        self.host.budget_growth = 4294967296
        self.host.approve_source(fixture.version())
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'insufficient-space'):
            self.core.preview('add', ITEM, fixture.version())
        self.assertEqual(before, self.inventory())

    def test_work_budget_and_external_copy_drift(self):
        self.apply('add', fixture.version())
        for drift in ('budget', 'external'):
            preview = self.core.preview('stop', ITEM)
            handle = self.core.authorize(preview)
            before = self.inventory()
            if drift == 'budget':
                self.host.budget_growth += 4096
            else:
                self.host.copies['coverage'] = 'partial'
            with self.subTest(drift=drift), self.assertRaises(c.ContractError):
                self.core.execute(handle)
            self.assertEqual(before, self.inventory())

    def test_incomplete_postflight_keeps_committed_proof(self):
        from unittest import mock
        import memory_governance_core as core_module
        self.host.approve_source(fixture.version())
        preview = self.core.preview('add', ITEM, fixture.version())
        handle = self.core.authorize(preview)
        committed = False
        measure = db.measure
        def stage(name):
            nonlocal committed
            if name == 'after-commit':
                committed = True
        def limited(*args):
            if committed:
                raise c.ContractError('data-limit-exceeded')
            return measure(*args)
        with mock.patch.object(core_module, '_checkpoint', side_effect=stage), mock.patch.object(db, 'measure', side_effect=limited):
            result = self.core.execute(handle)
        self.assertEqual('committed-capacity-unproven', result['result'])
        self.assertIsNotNone(result['proof'])
        self.assertEqual('applied', self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)['result'])

    def test_projection_or_proof_tampering_fails_closed(self):
        import sqlite3
        self.apply('add', fixture.version())
        root = self.host.binding().root
        with sqlite3.connect(root/db.MAIN) as connection:
            connection.execute("UPDATE current_search SET cue='wrong' WHERE cue='blue'")
        with self.assertRaisesRegex(c.ContractError, 'projection-mismatch'):
            self.core.recall(['wrong'])
        with self.assertRaisesRegex(c.ContractError, 'projection-mismatch'):
            self.core.audit()

    def test_root_binding_mode_and_inode_drift(self):
        from dataclasses import replace
        import os
        binding = self.host.binding()
        self.host._binding = replace(binding, adapter_fingerprint='b'*64)
        with self.assertRaisesRegex(c.ContractError, 'root-binding-drift'):
            self.core.audit()
        self.host._binding = binding
        os.chmod(binding.root/db.MAIN, 0o644)
        with self.assertRaisesRegex(c.ContractError, 'unsafe-managed-file'):
            self.core.audit()
        os.chmod(binding.root/db.MAIN, 0o600)
        path = binding.root/db.MAIN
        original = path.read_bytes()
        path.rename(binding.root/'old.sqlite')
        path.write_bytes(original)
        os.chmod(path, 0o600)
        (binding.root/'old.sqlite').unlink()
        with self.assertRaisesRegex(c.ContractError, 'file-identity-mismatch'):
            self.core.audit()

    def test_readback_of_earlier_operation_after_progress_is_unknown(self):
        preview, result = self.apply('add', fixture.version())
        self.apply('stop')
        read = self.core.readback(result['operation_id'], result['preview_digest'])
        self.assertEqual('state-unknown', read['result'])
        self.assertEqual(result['proof'], read['proof'])

    def test_exception_before_commit_is_verified_not_applied(self):
        from unittest import mock
        import memory_governance_core as core_module
        self.host.approve_source(fixture.version())
        preview = self.core.preview('add', ITEM, fixture.version())
        handle = self.core.authorize(preview)
        def fail(stage):
            if stage == 'before-commit':
                raise OSError('simulated interruption')
        with mock.patch.object(core_module, '_checkpoint', side_effect=fail):
            result = self.core.execute(handle)
        self.assertEqual('not-applied', result['result'])
        self.assertIsNone(result['proof'])
        self.assertEqual([], self.core.audit().page()['items'])

    def test_readback_validates_proof_independently_of_executor_return(self):
        import sqlite3
        preview, result = self.apply('add', fixture.version())
        proof = copy.deepcopy(result['proof'])
        proof['acceptance_epoch'] = 2
        with sqlite3.connect(self.host.binding().root/db.MAIN) as connection:
            connection.execute('UPDATE proofs SET document=?', (c.canonical(proof),))
        read = self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)
        self.assertEqual('integrity-failed', read['result'])
        self.assertIsNone(read['proof'])

    def test_old_operation_id_is_rejected_even_with_fresh_host_confirmation(self):
        from unittest import mock
        first, _ = self.apply('add', fixture.version())
        # 強制 ID generator 碰撞；使用新 host confirmation 仍不可重播持久 ID。
        import memory_governance_core as core_module
        with mock.patch.object(core_module.uuid, 'uuid4', return_value=first['operation_id']):
            preview = self.core.preview('stop', ITEM)
        handle = self.core.authorize(preview)
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'operation-replay'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_reserved_work_and_fresh_free_space_admission(self):
        value = fixture.version()
        self.host.approve_source(value)
        preview = self.core.preview('add', ITEM, value)
        handle = self.core.authorize(preview)
        self.host.committed_bytes = c.MAX_NUMBER
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'insufficient-space'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_schema_drift_rejects_before_mutation(self):
        import sqlite3
        value = fixture.version()
        self.host.approve_source(value)
        preview = self.core.preview('add', ITEM, value)
        handle = self.core.authorize(preview)
        with sqlite3.connect(self.host.binding().root/db.MAIN) as connection:
            connection.execute('CREATE TABLE unexpected(x)')
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'schema-mismatch'):
            self.core.execute(handle)
        self.assertEqual(before, self.inventory())

    def test_init_refuses_existing_and_symlink_roots(self):
        from dataclasses import replace
        with self.assertRaisesRegex(c.ContractError, 'already-initialized'):
            GovernanceCore(self.host, enabled=True).initialize()
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            real = parent/'real'
            real.mkdir(mode=0o700)
            host = fixture.SyntheticHost(real)
            alias = parent/'alias'
            alias.symlink_to(real, target_is_directory=True)
            host._binding = replace(host.binding(), root=alias)
            with self.assertRaisesRegex(c.ContractError, 'unsafe-root'):
                GovernanceCore(host, enabled=True).initialize()
            self.assertEqual([], list(real.iterdir()))

    def test_bound_scope_does_not_adopt_another_roots_metadata(self):
        from dataclasses import replace
        binding = self.host.binding()
        scope = c.decode(binding.scope_bytes)
        scope['principal_id'] = '99999999-0000-4000-8000-000000000001'
        self.host._binding = replace(binding, scope_bytes=c.canonical(scope))
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'metadata-mismatch'):
            GovernanceCore(self.host, enabled=True).audit()
        self.assertEqual(before, self.inventory())

    def test_failed_confirmation_binding_never_produces_handle(self):
        from unittest import mock
        from memory_governance_host import AcceptedPreview
        self.host.approve_source(fixture.version())
        preview = self.core.preview('add', ITEM, fixture.version())
        accepted = self.host.accept_preview(self.host.binding(), c.canonical(preview))
        confirmation = c.decode(accepted.confirmation_bytes)
        confirmation['nonce'] = '00000000-0000-4000-8000-000000000099'
        with mock.patch.object(self.host, 'accept_preview', return_value=AcceptedPreview(accepted.preview_bytes, c.canonical(confirmation))):
            with self.assertRaisesRegex(c.ContractError, 'confirmation-binding'):
                self.core.authorize(preview)
        self.assertIsNone(self.core._handle)

    def test_readback_authority_loss_after_commit_is_explicit_unknown(self):
        from unittest import mock
        import memory_governance_core as core_module
        self.host.approve_source(fixture.version())
        preview = self.core.preview('add', ITEM, fixture.version())
        handle = self.core.authorize(preview)
        def revoke(stage):
            if stage == 'after-commit':
                self.host.readable = False
        with mock.patch.object(core_module, '_checkpoint', side_effect=revoke):
            with self.assertRaisesRegex(c.ContractError, 'state-unknown'):
                self.core.execute(handle)
        self.host.readable = True
        self.assertEqual('applied', self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)['result'])

    def test_capacity_readback_result_is_exclusive(self):
        preview, result = self.apply('add', fixture.version())
        scope = c.decode(self.host.binding().scope_bytes)
        limits = c.decode(self.host.binding().profile_bytes)
        wrong = copy.deepcopy(result)
        wrong['result'] = 'committed-capacity-unproven'
        with self.assertRaisesRegex(c.ContractError, 'invalid-capacity-readback'):
            c.g1_readback(wrong, scope, limits, preview)
        wrong['storage']['coverage'] = 'unknown'
        c.g1_readback(wrong, scope, limits, preview)
        wrong['result'] = 'applied'
        with self.assertRaisesRegex(c.ContractError, 'readback-capacity-unproven'):
            c.g1_readback(wrong, scope, limits, preview)

    def test_postcommit_copy_failure_preserves_proof_without_claiming_capacity_failure(self):
        from unittest import mock
        import memory_governance_core as core_module
        candidate = fixture.version()
        self.host.approve_source(candidate)
        preview = self.core.preview('add', ITEM, candidate)
        handle = self.core.authorize(preview)
        committed = False
        original = self.host.external_copies
        def stage(name):
            nonlocal committed
            if name == 'after-commit':
                committed = True
        def copies(binding):
            if committed:
                raise OSError('synthetic copy inventory unavailable')
            return original(binding)
        with mock.patch.object(core_module, '_checkpoint', side_effect=stage), mock.patch.object(self.host, 'external_copies', side_effect=copies):
            result = self.core.execute(handle)
        self.assertEqual('state-unknown', result['result'])
        self.assertIsNotNone(result['proof'])
        self.assertEqual('complete', result['storage']['coverage'])
        self.assertEqual('unknown', result['external_copies']['coverage'])

    def test_postcommit_copy_drift_and_missing_preview_cannot_be_applied(self):
        from unittest import mock
        import memory_governance_core as core_module
        candidate = fixture.version()
        self.host.approve_source(candidate)
        preview = self.core.preview('add', ITEM, candidate)
        handle = self.core.authorize(preview)
        def drift(name):
            if name == 'after-commit':
                self.host.copies.update(coverage='complete', copies=[{'copy_id': 'new-backup', 'kind': 'backup', 'observation': 'known-present'}])
        with mock.patch.object(core_module, '_checkpoint', side_effect=drift):
            result = self.core.execute(handle)
        self.assertEqual('state-unknown', result['result'])
        self.assertIsNotNone(result['proof'])
        scope = c.decode(self.host.binding().scope_bytes)
        limits = c.decode(self.host.binding().profile_bytes)
        wrong = copy.deepcopy(result)
        wrong['result'] = 'applied'
        for original in (None, preview):
            with self.subTest(preview=original is not None), self.assertRaisesRegex(c.ContractError, 'readback-copy-binding'):
                c.g1_readback(wrong, scope, limits, original)

    def test_readback_wrong_request_digest_does_not_claim_persistent_corruption(self):
        preview, result = self.apply('add', fixture.version())
        before = self.inventory()
        with self.assertRaisesRegex(c.ContractError, 'readback-binding'):
            self.core.readback(preview['operation_id'], 'f'*64)
        self.assertEqual(before, self.inventory())
        self.assertEqual('applied', self.core.readback(preview['operation_id'], c.digest(preview), preview=preview)['result'])

    def test_every_historical_proof_replays_revision_status_and_projection(self):
        import sqlite3
        self.apply('add', fixture.version())
        self.host.now = 200
        self.apply('update', fixture.version(2, now=200, cue='green'))
        self.apply('stop')
        self.apply('resume')
        database = self.host.binding().root/db.MAIN
        with sqlite3.connect(database) as connection:
            originals = dict(connection.execute('SELECT sequence,document FROM proofs'))
        mutations = [(1, {'projection_digest': 'f'*64}),
                     (2, {'before_revision': 0}),
                     (2, {'operation': 'add', 'before_revision': 0, 'after_revision': 1}),
                     (3, {'operation': 'resume'}),
                     (4, {'operation': 'stop'}),
                     (2, {'operation': 'restore', 'restore_source_revision': 2})]
        for sequence, fields in mutations:
            changed = c.decode(originals[sequence])
            changed.update(fields)
            with sqlite3.connect(database) as connection:
                connection.execute('UPDATE proofs SET document=? WHERE sequence=?', (c.canonical(changed), sequence))
            with self.subTest(sequence=sequence, fields=fields), self.assertRaises(c.ContractError):
                self.core.audit()
            with sqlite3.connect(database) as connection:
                connection.execute('UPDATE proofs SET document=? WHERE sequence=?', (originals[sequence], sequence))
        self.assertEqual(1, len(self.core.recall(['green'])['items']))
