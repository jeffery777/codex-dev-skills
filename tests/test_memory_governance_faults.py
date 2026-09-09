from __future__ import annotations

from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
from unittest import mock

from tests.test_memory_governance_core import c, db, fixture, GovernanceCore, ITEM

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT/'tests/fixtures/memory-governance/crash_worker.py'


class FaultTests(unittest.TestCase):
    def test_abrupt_subprocess_interruption_and_fresh_readback(self):
        for stage in ('before-transaction', 'after-item-write', 'before-commit', 'commit-vm', 'after-commit'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary).resolve()
                root = parent/'root'
                root.mkdir(mode=0o700)
                host = fixture.SyntheticHost(root)
                core = GovernanceCore(host, enabled=True)
                core.initialize()
                output = parent/'synthetic-preview.json'
                completed = subprocess.run([str(ROOT/'scripts/project-python'), str(WORKER), str(root), str(output), stage],
                                           cwd=ROOT, capture_output=True, timeout=30)
                self.assertEqual(73, completed.returncode, completed.stderr.decode())
                preview = c.decode(output.read_bytes())
                host.approve_source(fixture.version())
                fresh = GovernanceCore(host, enabled=True)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                result = fresh.readback(preview['operation_id'], c.digest(preview), preview=preview)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
                if stage == 'after-commit':
                    self.assertEqual('applied', result['result'])
                    self.assertEqual(1, len(fresh.recall(['blue'])['items']))
                elif stage == 'before-transaction':
                    self.assertEqual('not-applied', result['result'])
                else:
                    allowed = ('state-unknown', 'not-applied', 'applied') if stage == 'commit-vm' else ('state-unknown', 'not-applied')
                    self.assertIn(result['result'], allowed)
                    if (root/db.JOURNAL).exists() and (root/db.JOURNAL).stat().st_size:
                        self.assertEqual('state-unknown', result['result'])
                        with mock.patch.object(db, 'connect', side_effect=AssertionError('audit opened journalled DB')):
                            with self.assertRaisesRegex(c.ContractError, 'recovery-required'):
                                fresh.audit()
                        self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir()})
                        # Separate test-fixture recovery only; MG1 G1 has no recovery entrypoint.
                        with sqlite3.connect(root/db.MAIN) as recovery:
                            recovery.execute('SELECT count(*) FROM root_meta').fetchone()
                        # A non-hot journal may remain: fixture removes its own file after SQLite recovery.
                        journal = root/db.JOURNAL
                        if journal.exists():
                            journal.unlink()
                        recovered = fresh.readback(preview['operation_id'], c.digest(preview), preview=preview)
                        self.assertEqual('not-applied', recovered['result'])
                with self.assertRaisesRegex(c.ContractError, 'preview-unrecognized'):
                    fresh.authorize(preview)

    def test_independent_process_cannot_write_while_audit_snapshot_holds_lock(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary).resolve()
            root = parent/'root'
            root.mkdir(mode=0o700)
            host = fixture.SyntheticHost(root)
            core = GovernanceCore(host, enabled=True)
            core.initialize()
            with core.audit():
                completed = subprocess.run([str(ROOT/'scripts/project-python'), str(WORKER), str(root), str(parent/'preview.json'), 'after-commit'],
                                           cwd=ROOT, capture_output=True, timeout=30)
                self.assertNotEqual(73, completed.returncode)
                self.assertIn(b'busy', completed.stderr)
            self.assertEqual([], core.audit().page()['items'])

    def test_multiple_pages_use_one_snapshot_and_stale_cursor_rejects(self):
        with tempfile.TemporaryDirectory() as temporary:
            host = fixture.SyntheticHost(Path(temporary))
            core = GovernanceCore(host, enabled=True)
            core.initialize()
            fixture.seed_audit_items(host)
            with core.audit() as audit:
                first = audit.page()
                self.assertEqual(256, len(first['items']))
                self.assertFalse(first['enumeration_complete'])
                with self.assertRaisesRegex(c.ContractError, 'cursor-unavailable'):
                    audit.page()
                second = audit.page(first['next_cursor'])
                self.assertEqual(1, len(second['items']))
                self.assertEqual(first['snapshot_digest'], second['snapshot_digest'])
                self.assertTrue(second['enumeration_complete'])
                with self.assertRaisesRegex(c.ContractError, 'cursor-unavailable'):
                    audit.page(first['next_cursor'])
