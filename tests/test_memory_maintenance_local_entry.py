"""Isolated mechanism tests; simulated acceptance is never formal human evidence."""
from contextlib import closing, redirect_stdout
from copy import deepcopy
import io
import os
from pathlib import Path
import tempfile
import sqlite3
import unittest
from unittest import mock

from tests.test_memory_maintenance_entry import c, db, ITEM
from tests.test_memory_governance_local import local_fixture
import memory_maintenance_binding as binding_module
import memory_maintenance_local as entry
import memory_maintenance_qualification as q
import memory_governance_core as core_module
from memory_maintenance_operator import OperatorTerminal, display_safe


class SimulatedOperator:
    evidence_id = 'test-only-not-human-evidence'
    def __init__(self, *, actor='human'):
        self.actor = actor
        self.actions = []
        self.reject = None
    def check(self):
        pass
    def accept(self, action, data):
        self.actions.append((action, data))
        return action != self.reject
    accept_preview = OperatorTerminal.accept_preview


class LocalEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='local-entry-mechanisms-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        fixture = self.parent / 'fixture'
        fixture.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(fixture, git_root=self.parent / 'source')
        self.workspace = self.parent / 'workspace'
        self.ui = SimulatedOperator()
        # Existing test interpreter need not be the qualified operator runtime.
        # This mock excludes runtime qualification from these mechanism claims.
        patch = mock.patch.object(q, 'verify_runtime')
        patch.start()
        self.addCleanup(patch.stop)

    def initialize(self):
        return q.initialize_local(self.workspace, self.parent / 'source', 'synthetic-repository',
                                  self.ui, entry.fingerprint())

    def test_initialize_disabled_descriptor_exclusive_and_fresh_readback(self):
        result = self.initialize()
        self.assertEqual('applied', result['outcome'])
        local = binding_module.load(self.workspace, entry.fingerprint(), enabled=False)
        self.assertFalse(c.decode(local.data)['enabled'])
        self.assertEqual(['CREATE', 'INITIALIZE'], [a for a, _ in self.ui.actions])
        with db.locked(local.binding), closing(db.connect(local.binding, c.decode(local.binding.profile_bytes))) as connection:
            self.assertLessEqual(connection.execute('PRAGMA page_count').fetchone()[0], db.INITIAL_PAGE_LIMIT)
            self.assertEqual(0, connection.execute('PRAGMA cache_spill').fetchone()[0])
        before = local.data
        with self.assertRaises(c.ContractError):
            self.initialize()
        self.assertEqual(before, binding_module.load(self.workspace, entry.fingerprint(), enabled=False).data)

    def test_create_rejection_and_initial_capacity_refusal_do_not_create(self):
        self.ui.reject = 'CREATE'
        with self.assertRaises(c.ContractError):
            self.initialize()
        self.assertFalse(self.workspace.exists())
        with mock.patch.object(q.os, 'fstatvfs', return_value=type('Space', (), {'f_bavail': 0, 'f_frsize': 4096})()):
            with self.assertRaisesRegex(c.ContractError, 'insufficient-space'):
                self.initialize()
        self.assertFalse(self.workspace.exists())

    def test_five_operations_use_fixed_entry_and_revoke_old_descriptor(self):
        self.initialize()
        local = binding_module.load(self.workspace, entry.fingerprint(), enabled=False)
        binding_module.set_enabled(local, True)
        with self.assertRaisesRegex(c.ContractError, 'descriptor-drift'):
            local.check(enabled=False)
        local = binding_module.load(self.workspace, entry.fingerprint())
        old = self.ports.candidate(1)
        changed = self.ports.candidate(2, cue='green')
        for operation, candidate, revision in [('add', old, None), ('update', changed, None),
                ('stop', None, None), ('resume', None, None), ('restore', None, 1)]:
            result = entry.run_operation(local, {'operation': operation, 'item_id': ITEM,
                'candidate': candidate, 'restore_revision': revision}, self.ui)
            self.assertEqual('applied', result['outcome'], result)
            self.assertTrue(result['verification']['current_only_verified'])
            self.assertFalse(result['full_mg1_qualified'])
        self.assertEqual(3, result['verification']['revision'])
        binding_module.set_enabled(local, False)
        with self.assertRaises(c.ContractError):
            binding_module.load(self.workspace, entry.fingerprint())

    def test_descriptor_rejects_mode_symlink_and_code_drift(self):
        self.initialize()
        with self.assertRaisesRegex(c.ContractError, 'qualification-unavailable'):
            binding_module.load(self.workspace, 'f' * 64, enabled=False)
        path = self.workspace / binding_module.NAME
        os.chmod(path, 0o644)
        with self.assertRaisesRegex(c.ContractError, 'unsafe-descriptor'):
            binding_module.load(self.workspace, entry.fingerprint(), enabled=False)
        os.chmod(path, 0o600)
        renamed = self.workspace / 'saved-binding.json'
        path.rename(renamed)
        path.symlink_to(renamed)
        with self.assertRaises(OSError):
            binding_module.load(self.workspace, entry.fingerprint(), enabled=False)

    def test_sqlite_full_before_and_after_commit_classified_by_fresh_readback(self):
        self.initialize()
        local = binding_module.load(self.workspace, entry.fingerprint(), enabled=False)
        binding_module.set_enabled(local, True)
        local = binding_module.load(self.workspace, entry.fingerprint())
        proposal = {'operation': 'add', 'item_id': ITEM, 'candidate': self.ports.candidate(1), 'restore_revision': None}
        for stage, expected in [('after-item-write', 'not-applied'), ('before-commit', 'not-applied'), ('after-commit', 'applied')]:
            def fault(actual):
                if actual == stage:
                    error = sqlite3.OperationalError('test-only controlled SQLITE_FULL')
                    error.sqlite_errorcode = sqlite3.SQLITE_FULL
                    raise error
            with mock.patch.object(core_module, '_checkpoint', side_effect=fault):
                result = entry.run_operation(local, proposal, self.ui)
            self.assertEqual(expected, result['outcome'], result)
            self.assertEqual('complete' if expected == 'applied' else 'not-applied', result['status'])
        with db.locked(local.binding), closing(db.connect(local.binding, c.decode(local.binding.profile_bytes))) as connection:
            self.assertEqual(1, connection.execute('SELECT count(*) FROM proofs').fetchone()[0])

    def test_stop_matching_cue_without_git_source(self):
        self.initialize()
        local = binding_module.load(self.workspace, entry.fingerprint(), enabled=False)
        binding_module.set_enabled(local, True)
        local = binding_module.load(self.workspace, entry.fingerprint())
        other = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        for item in (ITEM, other):
            result = entry.run_operation(local, {'operation': 'add', 'item_id': item,
                'candidate': self.ports.candidate(1), 'restore_revision': None}, self.ui)
            self.assertEqual('applied', result['outcome'], result)
        source = self.parent / 'source'
        source.rename(self.parent / 'unavailable-source')
        result = entry.run_operation(local, {'operation': 'stop', 'item_id': ITEM,
            'candidate': None, 'restore_revision': None}, self.ui)
        self.assertEqual('applied', result['outcome'], result)
        self.assertEqual('stopped', result['verification']['item_status'])

    def test_default_off_does_not_read_scope_proposal_or_terminal(self):
        with mock.patch.object(entry, 'OperatorTerminal', side_effect=AssertionError('touched')):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, entry.main(['run', '--workspace', '/no-root', '--proposal', '/no-proposal']))
        self.assertEqual('disabled', c.decode(output.getvalue().encode())['status'])

    def test_no_pipeline_and_no_display_spoofing(self):
        with mock.patch('memory_maintenance_operator.os.isatty', return_value=False):
            for actor in ('human', 'agent'):
                with self.assertRaisesRegex(c.ContractError, 'operator-terminal-unavailable'):
                    OperatorTerminal(actor=actor).__enter__()
        for value in ['\u202e', '\u2066', '\u0085']:
            with self.assertRaisesRegex(c.ContractError, 'unsafe-display'):
                display_safe(c.canonical({'body': value}))

    def test_agent_acceptance_keeps_exact_digest_and_actor_evidence(self):
        ui = OperatorTerminal(actor='agent')
        self.assertTrue(ui.evidence_id.startswith('agent-operator-'))
        ui.fd = 123  # Test-only mocked terminal; not runtime or actor attestation.
        data = c.canonical({'scope': 'test-only'})
        token = 'REVIEW ' + c.digest(c.decode(data)) + '\n'
        with mock.patch.object(ui, 'check'), mock.patch.object(ui, 'write') as write, \
             mock.patch('memory_maintenance_operator.termios.tcflush'), \
             mock.patch('memory_maintenance_operator.os.read', return_value=b'\n'):
            self.assertFalse(ui.accept('REVIEW', data))
            self.assertEqual(data + b'\n', write.call_args_list[0].args[0])
            self.assertIn('已取得使用者委派的 agent', write.call_args_list[1].args[0].decode())
        with mock.patch.object(ui, 'check'), mock.patch.object(ui, 'write'), \
             mock.patch('memory_maintenance_operator.termios.tcflush'), \
             mock.patch('memory_maintenance_operator.os.read', side_effect=[bytes([b]) for b in token.encode()]):
            self.assertTrue(ui.accept('REVIEW', data))

    def test_agent_flag_alone_is_not_acceptance_and_default_off_is_zero_touch(self):
        output = io.StringIO()
        with mock.patch.object(entry, 'OperatorTerminal', side_effect=AssertionError('touched')), redirect_stdout(output):
            self.assertEqual(0, entry.main(['run', '--actor', 'agent', '--workspace', '/no-root']))
        self.assertEqual('disabled', c.decode(output.getvalue().encode())['status'])
        output = io.StringIO()
        with mock.patch('memory_maintenance_operator.os.isatty', return_value=False), redirect_stdout(output):
            self.assertEqual(2, entry.main(['run', '--enabled', '--actor', 'agent', '--workspace', '/no-root']))
        result = c.decode(output.getvalue().encode())
        self.assertEqual(('not-applied', 'agent', 'operator-terminal-unavailable'),
                         (result['outcome'], result['acceptance_actor'], result['reason']))

    def test_main_preserves_returned_applied_result_on_terminal_close_error(self):
        class ClosingFault(SimulatedOperator):
            def __enter__(self):
                return self
            def __exit__(self, *_):
                raise OSError('test-only close fault')
        returned = {'status': 'complete', 'outcome': 'applied', 'proof': {'test': 'returned-readback'}}
        output = io.StringIO()
        with mock.patch.object(entry, 'OperatorTerminal', ClosingFault), \
             mock.patch.object(entry, '_load_proposal', return_value={'operation': 'stop'}), \
             mock.patch.object(binding_module, 'load'), \
             mock.patch.object(entry, 'run_operation', return_value=returned), redirect_stdout(output):
            self.assertEqual(2, entry.main(['run', '--enabled', '--workspace', str(self.workspace),
                                          '--proposal', str(self.parent / 'proposal.json')]))
        result = c.decode(output.getvalue().encode())
        self.assertEqual('applied', result['outcome'])
        self.assertEqual(returned['proof'], result['proof'])

    def test_main_init_low_capacity_before_mutation_is_not_applied(self):
        class Terminal(SimulatedOperator):
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
        output = io.StringIO()
        with mock.patch.object(entry, 'OperatorTerminal', Terminal), \
             mock.patch.object(q.os, 'fstatvfs', return_value=type('Space', (), {'f_bavail': 0, 'f_frsize': 4096})()), \
             redirect_stdout(output):
            self.assertEqual(2, entry.main(['init', '--enabled', '--workspace', str(self.workspace),
                '--repository', str(self.parent / 'source'), '--repository-id', 'synthetic-repository']))
        result = c.decode(output.getvalue().encode())
        self.assertEqual(('not-applied', 'insufficient-space'), (result['outcome'], result['reason']))
        self.assertFalse(self.workspace.exists())

    def test_disk_bounds_maximum_and_page_shape(self):
        for size in (0, 4096, q.DATA_LIMIT):
            journal, growth, required = q.disk_bounds(size, q.DATA_LIMIT)
            self.assertEqual(size // 4096 * 4104 + 131072, journal)
            self.assertEqual(q.DATA_LIMIT - size, growth)
            self.assertLessEqual(required, 269090816)
        with self.assertRaises(c.ContractError):
            q.disk_bounds(4097, q.DATA_LIMIT)


if __name__ == '__main__':
    unittest.main()
