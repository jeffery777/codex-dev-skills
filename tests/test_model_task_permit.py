"""Fixture-domain contracts, using real private files and live Git source reads."""
import copy
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_task_ingress as ingress
import model_task_permit as permits
import model_packet_store as packets
from tests.test_model_task_ingress import InputFixture
from tests.test_model_execution_target import TargetFixture, targets


class FixturePermitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name).resolve()
        self.repo = self.base/'repo'; self.repo.mkdir(mode=0o700)
        self.git('init', '-q'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('remote', 'add', 'origin', 'https://example.invalid/fixture.git')
        (self.repo/'README.md').write_text('original source\n')
        self.git('add', 'README.md'); self.git('commit', '-qm', 'fixture')
        self.request = {'operation': 'start', 'workspace': str(self.repo),
            'expected_head': self.git('rev-parse', 'HEAD'), 'prompt': 'synthetic private prompt',
            'sandbox': 'workspace-write', 'authorization': {'sandbox_ceiling': 'workspace-write'},
            'target_ref': {'id': 'fixture-target'}}
        self.target = TargetFixture(self.base/'targets', prompt=self.request['prompt'],
                                    head=self.request['expected_head'])
        self.request['target_ref'] = self.target.ref
        self.binding = self.target_reader(None, self.request)
        self.input = InputFixture(self.base/'inputs', self.request, scope='fixture-repair',
                                  destinations=[self.binding.identity_sha256])
        self.source = ingress.read_input(self.input.home, self.input.ref,
            {'id': 'T1', 'qualification_scope': 'fixture-repair'},
            {'task': {'acceptance_sha256': self.input.record['acceptance']['sha256']}}, self.request)
        self.root = self.base/'issuer'; self.root.mkdir(mode=0o700)
        self.issuer = permits.FixturePermitIssuer.initialize(self.root, enabled=True,
                                                           target_reader=self.target_reader)
        self.options = {'action': 'fixture-start', 'session_sha256': 'f'*64}
        self.evidence()

    def git(self, *args):
        return subprocess.run(['/usr/bin/git', '-C', str(self.repo), *args],
            check=True, capture_output=True, text=True).stdout.strip()

    def target_reader(self, binding, request):
        # Existing bounded target loader reads the protected fixture originals;
        # its summaries remain operator fixtures, never production qualification.
        with mock.patch.object(targets, 'root', return_value=self.target.home):
            return targets.resolve(binding.reference() if binding else self.target.ref,
                prompt=request['prompt'], expected_head=request['expected_head'],
                executable_sha256=self.target.executable_sha256,
                cli_version=self.target.cli_version, sandbox=request['sandbox'], now=int(time.time()))

    def reopen(self):
        return permits.FixturePermitIssuer(self.root, enabled=True, target_reader=self.target_reader)

    def virtual_clock(self, wall, mono):
        return mock.patch.multiple(permits.time, time=mock.Mock(return_value=wall),
                                   monotonic=mock.Mock(return_value=mono))

    def evidence(self, source=None, request=None, binding=None, options=None):
        source = source or self.source
        constraints = self.issuer._constraints(source, request or self.request,
                                             binding or self.binding, **(options or self.options))
        for kind, name in permits.EVIDENCE.items():
            path = self.root/name
            if kind == 'authorization':
                approved = int(time.time())
                value = {'domain': permits.DOMAIN, 'kind': kind,
                         'scope': self.issuer._grant_scope(source, constraints),
                         'actions': sorted(permits.ACTIONS), 'approved_at': approved,
                         'expires_at': approved + 600}
            else:
                value = {'domain': permits.DOMAIN, 'kind': kind, 'constraints': constraints}
            path.write_bytes(packets.canonical(value))
            path.chmod(0o600)

    def issue(self, **kwargs):
        return self.issuer.issue(self.source, self.request, self.binding, **self.options, **kwargs)

    def readback(self, reference, **kwargs):
        return self.issuer.readback(reference, self.source, self.request, self.binding,
                                   **{**self.options, **kwargs})

    def rejected(self, call):
        with self.assertRaises((ValueError, OSError)):
            call()

    def test_default_off_explicit_root_and_fixture_only_domain(self):
        self.rejected(lambda: permits.FixturePermitIssuer(self.root))
        self.rejected(lambda: permits.FixturePermitIssuer.initialize(self.root))
        self.rejected(lambda: permits.FixturePermitIssuer.initialize(self.root, enabled=True))
        reference = self.issue()
        self.assertEqual(reference['domain'], permits.DOMAIN)
        wrong = {**reference, 'domain': 'production'}
        self.rejected(lambda: self.readback(wrong))
        self.rejected(lambda: self.issuer.issue(self.source, self.request, self.binding,
                                               **{**self.options, 'action': 'start'}))
        self.assertFalse(hasattr(permits, 'ProductionPermitIssuer'))

    def test_issue_readback_revoke_survive_restart_and_keep_only_digests(self):
        reference = self.issue()
        record = self.readback(reference)
        self.assertEqual(record['epoch'], 0)
        self.assertLessEqual(record['expires_at']-record['issued_at'], permits.MAX_TTL)
        persisted = (self.root/permits.JOURNAL).read_text()
        for content in (self.request['prompt'], str(self.repo), 'authorization', 'qualified'):
            self.assertNotIn(content, persisted)
        reopened = self.reopen()
        self.assertEqual(reopened.readback(reference, self.source, self.request, self.binding,
                                          **self.options), record)
        receipt = reopened.revoke(reference)
        self.assertTrue(receipt['revoked']); self.assertEqual(receipt['epoch'], 1)
        self.rejected(lambda: self.readback(reference))
        self.issuer = self.reopen()
        self.rejected(lambda: self.issue())

    def test_reference_alias_and_target_action_session_renewal_cannot_escape_revoke(self):
        reference = self.issue(); self.issuer.revoke(reference)
        # New protected input reference and clock window, same named objective.
        self.input.record['observed_at'] = int(time.time())
        self.input.record['expires_at'] = self.input.record['observed_at']+300
        self.input.refresh()
        self.source = ingress.read_input(self.input.home, self.input.ref,
            {'id': 'T1', 'qualification_scope': 'fixture-repair'},
            {'task': {'acceptance_sha256': self.input.record['acceptance']['sha256']}}, self.request)
        self.binding = replace(self.binding, binding_sha256='a'*64)
        self.options = {'action': 'fixture-read-only', 'session_sha256': '0'*64}
        self.issuer = self.reopen()
        self.rejected(lambda: self.issue())

    def test_expiry_ttl_and_durable_clock_rollback(self):
        for ttl in (0, 61, True, 0.5):
            self.rejected(lambda: self.issue(ttl=ttl))
        reference = self.issue(ttl=10)
        record = self.readback(reference)
        # Observe a time later than issue; rollback remains detectable on reopen.
        with self.virtual_clock(record['issued_at']+5, record['issued_monotonic']+5):
            self.readback(reference)
            self.issuer = self.reopen()
        with self.virtual_clock(record['issued_at']+4, record['issued_monotonic']+6):
            self.rejected(lambda: self.readback(reference))

    def test_expired_input_or_target_and_expiry_during_reads(self):
        reference = self.issue()
        original_until = self.binding.valid_until
        self.binding = replace(self.binding, valid_until=int(time.time()))
        self.rejected(lambda: self.readback(reference))
        self.binding = replace(self.binding, valid_until=original_until)
        with self.virtual_clock(self.input.record['expires_at'], self.issuer.last_monotonic+300):
            self.rejected(lambda: self.issue())
        self.issuer = self.reopen()
        record = self.readback(reference)
        expiry = record['expires_at']
        original = self.issuer._evidence
        def elapsed(fd, constraints, source, now):
            result = original(fd, constraints, source, now)
            permits.time.time.return_value = expiry
            permits.time.monotonic.return_value = record['issued_monotonic']+(expiry-record['issued_at'])
            return result
        with self.virtual_clock(expiry-0.1, record['issued_monotonic']+(expiry-0.1-record['issued_at'])):
            with mock.patch.object(self.issuer, '_evidence', side_effect=elapsed):
                self.rejected(lambda: self.readback(reference))

    def test_live_original_source_target_action_session_and_evidence_drift(self):
        reference = self.issue()
        changed = copy.deepcopy(self.request); changed['prompt'] += ' changed'
        self.rejected(lambda: self.issuer.readback(reference, self.source, changed,
                                                 self.binding, **self.options))
        for field in ('binding_sha256', 'identity_sha256', 'store_sha256', 'task_sha256'):
            old = self.binding; self.binding = replace(self.binding, **{field: '1'*64})
            self.rejected(lambda: self.readback(reference)); self.binding = old
        self.rejected(lambda: self.readback(reference, action='fixture-read-only'))
        self.rejected(lambda: self.readback(reference, session_sha256='1'*64))
        (self.repo/'README.md').write_text('changed source\n')
        self.rejected(lambda: self.readback(reference))
        (self.repo/'README.md').write_text('original source\n')
        acceptance = self.input.home/self.input.record['acceptance']['path']
        old = acceptance.read_bytes(); acceptance.write_bytes(b'changed')
        self.rejected(lambda: self.readback(reference)); acceptance.write_bytes(old)
        path = self.root/permits.EVIDENCE['authorization']
        path.write_bytes(packets.canonical({'status': 'granted', 'qualified': True}))
        self.rejected(lambda: self.readback(reference))

    def test_evidence_inode_replacement_symlink_hardlink_and_public_modes(self):
        reference = self.issue()
        path = self.root/permits.EVIDENCE['authorization']; raw = path.read_bytes()
        alias = self.base/'replacement'; alias.write_bytes(raw); alias.chmod(0o600)
        os.replace(alias, path)
        self.rejected(lambda: self.readback(reference))
        path.rename(self.base/'original-evidence')
        path.symlink_to(self.base/'original-evidence')
        self.rejected(lambda: self.readback(reference))
        path.unlink(); os.link(self.base/'original-evidence', path)
        self.rejected(lambda: self.readback(reference))
        path.unlink(); path.write_bytes(raw); path.chmod(0o644)
        self.rejected(lambda: self.readback(reference))

    def test_changed_root_and_state_identity_rejected_even_on_reopen(self):
        reference = self.issue()
        moved = self.base/'moved'; self.root.rename(moved)
        self.root.mkdir(mode=0o700)
        for name in (permits.ANCHOR, permits.JOURNAL):
            (self.root/name).write_bytes((moved/name).read_bytes()); (self.root/name).chmod(0o600)
        self.rejected(lambda: self.readback(reference))
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))

    def test_journal_replacement_hardlink_partial_missing_and_rollback(self):
        before = (self.root/permits.JOURNAL).read_bytes()
        reference = self.issue()
        journal = self.root/permits.JOURNAL
        journal.write_bytes(before)
        self.rejected(lambda: self.readback(reference))
        journal.write_bytes(before+b'{')
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))
        journal.write_bytes(before)
        replacement = self.base/'journal-copy'; replacement.write_bytes(before); replacement.chmod(0o600)
        os.replace(replacement, journal)
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))
        os.link(journal, self.base/'journal-link')
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))
        journal.unlink()
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))
        self.rejected(lambda: permits.FixturePermitIssuer.initialize(self.root, enabled=True))

    def test_root_symlink_repository_and_environment_cannot_select_trust(self):
        alias = self.base/'alias'; alias.symlink_to(self.root)
        self.rejected(lambda: permits.FixturePermitIssuer(alias, enabled=True))
        private = self.repo/'private'; private.mkdir(mode=0o700)
        self.rejected(lambda: permits.FixturePermitIssuer.initialize(private, enabled=True))
        self.root.chmod(0o755)
        self.rejected(lambda: self.issue())
        self.root.chmod(0o700)
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(private)}):
            reference = self.issue(); self.assertEqual(self.readback(reference)['domain'], permits.DOMAIN)

    def test_revoke_remains_available_after_expiry_and_source_disappears(self):
        reference = self.issue(ttl=10)
        (self.repo/'README.md').unlink()
        now = time.time()+12
        with self.virtual_clock(now, self.issuer.last_monotonic+12):
            self.assertTrue(self.issuer.revoke(reference)['revoked'])
        reopened = self.reopen()
        self.rejected(lambda: reopened.readback(reference, self.source, self.request,
                                               self.binding, **self.options))

    def test_partial_append_is_retained_and_never_admitted(self):
        before = (self.root/permits.JOURNAL).read_bytes()
        def partial(fd, raw):
            os.write(fd, raw[:20]); os.fsync(fd)
            raise OSError('synthetic interrupted write')
        with mock.patch.object(permits, '_write', side_effect=partial):
            self.rejected(lambda: self.issue())
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))
        actual = (self.root/permits.JOURNAL).read_bytes()
        self.assertEqual(actual[:len(before)], before)
        self.assertEqual(len(actual), len(before)+20)
        self.assertFalse(actual.endswith(b'\n'))

    def test_expired_renewal_increments_epoch_and_old_reference_is_fenced(self):
        reference = self.issue(ttl=10)
        record = self.readback(reference)
        with self.virtual_clock(record['expires_at'], record['issued_monotonic']+10):
            renewed = self.issue()
            self.assertEqual(renewed['epoch'], 1)
            self.rejected(lambda: self.readback(reference))
            self.assertEqual(self.readback(renewed)['epoch'], 1)

    def test_one_task_grant_covers_new_session_within_its_bound(self):
        approved = (self.root/permits.EVIDENCE['authorization']).read_bytes()
        reference = self.issue(ttl=10)
        record = self.readback(reference)
        with self.virtual_clock(record['expires_at'], record['issued_monotonic']+10):
            self.options = {'action': 'fixture-read-only', 'session_sha256': '2'*64}
            constraints = self.issuer._constraints(self.source, self.request,
                                                   self.binding, **self.options)
            path = self.root/permits.EVIDENCE['cli-qualification']
            path.write_bytes(packets.canonical({'domain': permits.DOMAIN,
                'kind': 'cli-qualification', 'constraints': constraints}))
            renewed = self.issue()
            self.assertEqual(renewed['epoch'], 1)
            self.assertEqual((self.root/permits.EVIDENCE['authorization']).read_bytes(), approved)
            self.rejected(lambda: self.readback(reference))

    def test_task_grant_action_scope_and_lifetime_are_enforced(self):
        path = self.root/permits.EVIDENCE['authorization']
        original = permits._decode(path.read_bytes())
        for change in ({'actions': ['fixture-start']},
                       {'domain': 'production'}, {'kind': 'cli-qualification'},
                       {'domain': None}, {'kind': False},
                       {'expires_at': original['approved_at'] + permits.MAX_GRANT_LIFETIME + 1},
                       {'scope': {**original['scope'], 'acceptance_sha256': '1'*64}}):
            value = {**original, **change}
            path.write_bytes(packets.canonical(value))
            if change == {'actions': ['fixture-start']}:
                self.rejected(lambda: self.issuer.issue(self.source, self.request,
                    self.binding, action='fixture-read-only',
                    session_sha256=self.options['session_sha256']))
            else:
                self.rejected(lambda: self.issue())
        path.write_bytes(packets.canonical({**original, 'expires_at': original['approved_at']}))
        self.rejected(lambda: self.issue())

    def test_observed_grant_expiry_fences_successor_after_reopen_and_clock_rollback(self):
        path = self.root/permits.EVIDENCE['authorization']
        grant = permits._decode(path.read_bytes())
        grant['expires_at'] = grant['approved_at'] + 15
        path.write_bytes(packets.canonical(grant))
        reference = self.issue(ttl=10)
        permit = self.readback(reference)
        expiry = grant['expires_at']
        elapsed = expiry - permit['issued_at']
        with self.virtual_clock(expiry, permit['issued_monotonic'] + elapsed):
            self.rejected(lambda: self.issue())
            event = permits._decode((self.root/permits.JOURNAL).read_bytes().splitlines()[-1])
            self.assertEqual(event['kind'], 'grant-expire')
        with self.virtual_clock(expiry - 1, permit['issued_monotonic'] + elapsed + 1):
            self.issuer = self.reopen()
            self.rejected(lambda: self.issue())
            self.rejected(lambda: self.readback(reference))

    def test_expired_grant_without_prior_permit_stays_fenced(self):
        path = self.root/permits.EVIDENCE['authorization']
        grant = permits._decode(path.read_bytes())
        grant['expires_at'] = grant['approved_at'] + 5
        path.write_bytes(packets.canonical(grant))
        now = time.time()
        mono = self.issuer.last_monotonic
        with self.virtual_clock(grant['expires_at'], mono + (grant['expires_at'] - now)):
            self.rejected(lambda: self.issue())
        with self.virtual_clock(grant['expires_at'] - 1,
                                mono + (grant['expires_at'] - now) + 1):
            self.issuer = self.reopen()
            self.rejected(lambda: self.issue())

    def test_grant_expiry_during_original_reads_is_fenced(self):
        path = self.root/permits.EVIDENCE['authorization']
        grant = permits._decode(path.read_bytes())
        grant['expires_at'] = grant['approved_at'] + 15
        path.write_bytes(packets.canonical(grant))
        reference = self.issue(ttl=10)
        permit = self.readback(reference)
        expiry = grant['expires_at']
        start_mono = permit['issued_monotonic'] + (expiry - 1 - permit['issued_at'])
        original = self.issuer._evidence
        def cross_expiry(fd, constraints, source, now):
            result = original(fd, constraints, source, now)
            permits.time.time.return_value = expiry
            permits.time.monotonic.return_value = start_mono + 1
            return result
        with self.virtual_clock(expiry - 1, start_mono):
            with mock.patch.object(self.issuer, '_evidence', side_effect=cross_expiry):
                self.rejected(lambda: self.issue())
            event = permits._decode((self.root/permits.JOURNAL).read_bytes().splitlines()[-1])
            self.assertEqual(event['kind'], 'grant-expire')
        with self.virtual_clock(expiry - 1, start_mono + 2):
            self.issuer = self.reopen()
            self.rejected(lambda: self.issue())

    def test_missing_qualification_production_summaries_and_disabled_original_fail_closed(self):
        path = self.root/permits.EVIDENCE['cli-qualification']
        original = path.read_bytes(); path.unlink()
        self.rejected(lambda: self.issue())
        path.write_bytes(packets.canonical({'domain': 'production', 'status': 'qualified'}))
        path.chmod(0o600)
        self.rejected(lambda: self.issue())
        path.write_bytes(original)
        self.input.record['enabled'] = False; self.input.refresh()
        self.rejected(lambda: self.issue())
        self.rejected(lambda: self.issuer.issue({'authorized': True}, self.request,
                                               self.binding, **self.options))

    def test_anchor_same_bytes_inode_replacement_and_partial_revoke_fail_closed(self):
        reference = self.issue()
        anchor = self.root/permits.ANCHOR
        replacement = self.base/'anchor-copy'
        replacement.write_bytes(anchor.read_bytes()); replacement.chmod(0o600)
        os.replace(replacement, anchor)
        self.rejected(lambda: self.readback(reference))
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))

    def test_partial_revoke_blocks_reopen_and_future_readback(self):
        reference = self.issue()
        def partial(fd, raw):
            os.write(fd, raw[:20]); os.fsync(fd)
            raise OSError('synthetic interrupted revoke')
        with mock.patch.object(permits, '_write', side_effect=partial):
            self.rejected(lambda: self.issuer.revoke(reference))
        self.rejected(lambda: self.readback(reference))
        self.rejected(lambda: permits.FixturePermitIssuer(self.root, enabled=True))

    def test_source_changed_during_evidence_reads_is_rejected_before_issue(self):
        original = self.issuer._evidence
        def drift(fd, constraints, source, now):
            result = original(fd, constraints, source, now)
            (self.repo/'README.md').write_text('drift during readback\n')
            return result
        with mock.patch.object(self.issuer, '_evidence', side_effect=drift):
            self.rejected(lambda: self.issue())

    def test_no_target_reader_or_cached_target_after_original_revocation_is_rejected(self):
        reference = self.issue()
        self.issuer.target_reader = None
        self.rejected(lambda: self.readback(reference))
        self.rejected(lambda: self.issue())
        self.issuer.target_reader = self.target_reader
        # Keep cached immutable Binding and change the real protected original.
        self.target.record['enabled'] = False; self.target.refresh()
        self.rejected(lambda: self.readback(reference))
        self.rejected(lambda: self.issue())
        self.target.record['enabled'] = True; self.target.refresh()
        artifact = self.target.home/self.target.record['catalog']['path']
        artifact.write_bytes(b'{}')
        self.rejected(lambda: self.readback(reference))

    def test_monotonic_ttl_and_reopen_cannot_revive_with_slow_wall(self):
        reference = self.issue(ttl=10); record = self.readback(reference)
        with self.virtual_clock(record['issued_at']+8, record['issued_monotonic']+11):
            reopened = self.reopen()
            with self.assertRaisesRegex(permits.PermitError, 'fixture-permit-expired-or-clock-drift'):
                reopened.readback(reference, self.source, self.request, self.binding, **self.options)
        # Even restoring both clocks cannot undo a durable expired epoch.
        with self.virtual_clock(record['issued_at']+2, record['issued_monotonic']+2):
            self.issuer = self.reopen()
            self.rejected(lambda: self.readback(reference))

    def test_wall_expiry_then_rollback_is_durable_across_reopen(self):
        reference = self.issue(ttl=10); record = self.readback(reference)
        with self.virtual_clock(record['expires_at'], record['issued_monotonic']+10):
            self.rejected(lambda: self.readback(reference))
        with self.virtual_clock(record['issued_at']+2, record['issued_monotonic']+2):
            self.issuer = self.reopen()
            self.rejected(lambda: self.readback(reference))

    def test_reopen_unknown_monotonic_epoch_fails_closed_and_fences_reference(self):
        reference = self.issue(); record = self.readback(reference)
        with self.virtual_clock(record['issued_at']+1, record['issued_monotonic']-1):
            self.issuer = self.reopen()
            self.rejected(lambda: self.readback(reference))
        self.issuer = self.reopen()
        self.rejected(lambda: self.readback(reference))

    def test_wall_rollback_within_one_readback_is_durably_fenced(self):
        reference = self.issue(ttl=10); record = self.readback(reference)
        original = self.issuer._evidence
        def rollback_during_originals(fd, constraints, source, now):
            result = original(fd, constraints, source, now)
            permits.time.time.return_value = record['issued_at']+4
            permits.time.monotonic.return_value = record['issued_monotonic']+6
            return result
        with self.virtual_clock(record['issued_at']+5, record['issued_monotonic']+5):
            with mock.patch.object(self.issuer, '_evidence', side_effect=rollback_during_originals):
                with self.assertRaisesRegex(permits.PermitError, 'fixture-clock-rollback-or-epoch-unknown'):
                    self.readback(reference)
            event = permits._decode((self.root/permits.JOURNAL).read_bytes().splitlines()[-1])
            self.assertEqual(event['kind'], 'expire')
            self.assertGreaterEqual(event['observed_at'], record['issued_at']+5)
            self.issuer = self.reopen()
            self.rejected(lambda: self.readback(reference))

    def test_expired_original_reference_can_sticky_revoke_current_task_epoch(self):
        reference = self.issue(ttl=10); record = self.readback(reference)
        with self.virtual_clock(record['expires_at'], record['issued_monotonic']+10):
            self.rejected(lambda: self.readback(reference))
            self.issuer = self.reopen()
            for alias in ({**reference, 'epoch': 1}, {**reference, 'permit_sha256': '1'*64}):
                self.rejected(lambda: self.issuer.revoke(alias))
            receipt = self.issuer.revoke(reference)
            self.assertTrue(receipt['revoked'])
            self.assertEqual(receipt['epoch'], 2)
        with self.virtual_clock(record['issued_at']+12, record['issued_monotonic']+12):
            self.issuer = self.reopen()
            self.rejected(lambda: self.issue())
            self.rejected(lambda: self.readback(reference))

    def test_expired_reference_cannot_revoke_a_renewed_permit(self):
        reference = self.issue(ttl=10); record = self.readback(reference)
        with self.virtual_clock(record['expires_at'], record['issued_monotonic']+10):
            renewed = self.issue()
            self.rejected(lambda: self.issuer.revoke(reference))
            self.assertEqual(self.readback(renewed)['epoch'], 1)

    def test_complete_write_then_fault_is_unknown_and_reopen_reads_durable_state(self):
        original = permits._write
        def complete_then_fault(fd, raw):
            original(fd, raw)
            raise OSError('synthetic lost reply after complete write')
        with mock.patch.object(permits, '_write', side_effect=complete_then_fault):
            self.rejected(lambda: self.issue())
        self.issuer = self.reopen()
        self.rejected(lambda: self.issue())
        fd = permits._root(self.root)
        try:
            tasks, _, _, _ = self.issuer._replay(permits._read(fd, permits.JOURNAL))
        finally:
            os.close(fd)
        value = next(iter(tasks.values()))['permit']
        reference = self.issuer._reference(value)
        self.assertEqual(self.readback(reference), value)


if __name__ == '__main__':
    unittest.main()
