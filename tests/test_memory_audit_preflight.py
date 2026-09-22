from __future__ import annotations

from dataclasses import replace
import errno
import json
import os
import sqlite3
from types import SimpleNamespace
import unittest
from unittest import mock

from tests import test_memory_audit_authority as fixtures
from tests.test_memory_audit_authority import a, c, db
from memory_audit import audit_report
from memory_governance_core import AuditSnapshot
from memory_governance_host import PRODUCTION_ADAPTERS
import memory_audit_preflight as p


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.a = fixtures.AuthorityTests()
        self.addCleanup(self.a.doCleanups)
        self.a.setUp()
        self.f = self.a.fixture
        f = self.f
        self.authority_revoked = set()
        self.ctx = p.AuditPreflightContext(binding=f.binding, repository=f.repo, permits=(f.permit,),
            accepted_sources=(f.acceptance,), qualification=f.qualification, store=self.a.store,
            authority_qualification=p.AuthorityQualification(c.canonical(p.authority_environment(self.a.store)),
                'independently-accepted-synthetic-authority', f.acceptance.expires_at),
            inspection=p.MetadataInspection(a.target_digest(f.binding), self.a.store, f.ports.clock_port.clock(), f.acceptance.expires_at, 'synthetic-metadata'),
            inspection_revoked=lambda _: False,
            clock=f.ports.clock_port, source_revoked=f.revoked_sources.__contains__,
            qualification_revoked=f.revoked_qualifications.__contains__,
            authority_qualification_revoked=self.authority_revoked.__contains__)

    def preflight(self, **kwargs):
        return p.preflight_report(enabled=True, context=kwargs.pop('context', self.ctx), **kwargs)

    def canary(self, provider=None, request=None, context=None):
        provider = provider or self.a.provider
        before = self.f.inventory()
        result = p.canary_report(enabled=True, context=context or self.ctx, provider=provider, request=request)
        self.assertEqual(before, self.f.inventory())
        self.assertFalse(result['production_qualified'])
        self.assertFalse(result['write_performed'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn(str(self.f.parent), json.dumps(result))
        with db.locked(self.f.binding, exclusive=True):
            pass
        return result

    def recover(self, old_request):
        provider = self.a.new_provider()
        self.assertEqual([], self.canary(provider, old_request)['items'])
        request = provider.accept()
        self.assertEqual('complete', self.canary(provider, request)['status'])

    def test_off_zero_touch_even_hostile_inputs(self):
        class Hostile:
            def __getattribute__(self, name):
                raise AssertionError('touch')
        for method in (p.preflight_report, p.canary_report):
            with mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('probe')):
                self.assertEqual('disabled', method(context=Hostile(), provider=Hostile(), request=Hostile())['status'])
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))

    def test_preflight_no_content_no_lifecycle_no_consumption(self):
        request = self.a.provider.accept()
        before = {x.name: (x.stat().st_mtime_ns, x.read_bytes()) for x in self.a.directory.iterdir()}
        pending = dict(self.a.provider._pending)
        with mock.patch.object(a, '_connection', side_effect=AssertionError('lifecycle read')), \
             mock.patch.object(db, 'connect', side_effect=AssertionError('managed read')), \
             mock.patch.object(p.PinnedGitReader, '_directory', side_effect=AssertionError('source read')):
            report = self.preflight(provider=self.a.provider, request=request)
        self.assertEqual('observed', report['checks']['request']['status'])
        self.assertEqual('observed', report['checks']['authority_environment']['status'])
        self.assertEqual('unknown', report['checks']['source_content_coverage']['status'])
        self.assertFalse(report['activation_authorized'])
        self.assertFalse(report['grant_consumed'])
        self.assertEqual(pending, self.a.provider._pending)
        self.assertEqual(before, {x.name: (x.stat().st_mtime_ns, x.read_bytes()) for x in self.a.directory.iterdir()})
        self.assertEqual('complete', self.canary(request=request)['status'])
        self.assertEqual([(request.request_id, 'consumed')], self.a.rows())
        self.assertEqual([], self.canary(request=request)['items'])

    def test_missing_invalid_unknown_and_no_permission_no_metadata(self):
        self.assertEqual('missing', p.preflight_report(enabled=True)['checks']['context']['status'])
        report = self.preflight(context=p.AuditPreflightContext())
        self.assertEqual('missing', report['checks']['target']['status'])
        self.assertEqual('missing', report['checks']['source_acceptance']['status'])
        with mock.patch.object(db, 'root_fd', side_effect=AssertionError('root touch')), \
             mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('environment probe')):
            report = self.preflight(context=replace(self.ctx, inspection=None))
        self.assertEqual('unknown', report['checks']['managed_environment']['status'])
        self.assertEqual('missing', self.preflight(context=replace(self.ctx, authority_qualification=None))['checks']['authority_environment']['status'])
        for field in ('qualification', 'authority_qualification'):
            report = self.preflight(context=replace(self.ctx, **{field: object()}))
            name = 'managed_environment' if field == 'qualification' else 'authority_environment'
            self.assertEqual('invalid', report['checks'][name]['status'])
        with mock.patch.object(db, 'root_fd', side_effect=OSError(errno.ENOSPC, 'PRIVATE')):
            report = self.preflight()
        self.assertEqual('unknown', report['checks']['target_metadata']['status'])
        self.assertNotIn('PRIVATE', json.dumps(report))

    def test_copied_managed_labels_do_not_qualify_authority(self):
        report = self.preflight(context=replace(self.ctx, authority_qualification=None))
        self.assertEqual('missing', report['checks']['authority_environment']['status'])
        q = replace(self.ctx.authority_qualification, environment_bytes=self.f.qualification.environment_bytes)
        ctx = replace(self.ctx, authority_qualification=q)
        self.assertEqual('invalid', self.preflight(context=ctx)['checks']['authority_environment']['status'])
        request = self.a.provider.accept()
        self.assertEqual([], self.canary(request=request, context=ctx)['items'])
        env = p.authority_environment(self.a.store)
        copied = replace(self.a.store, files=replace(self.a.store.files, filesystem_id='PRIVATE',
                         profile_bytes=b'PRIVATE', adapter_fingerprint='PRIVATE'))
        self.assertEqual(env, p.authority_environment(copied))
        self.assertEqual(os.stat(self.a.directory).st_dev, env['filesystem']['device'])

    def test_preflight_cannot_create_request_or_restore_closed_owner(self):
        self.assertEqual('missing', self.preflight()['checks']['request']['status'])
        self.assertEqual([], self.canary()['items'])
        self.assertEqual([], self.a.rows())
        request = self.a.provider.accept()
        self.a.provider.close()
        self.assertEqual('invalid', self.preflight(provider=self.a.provider, request=request)['checks']['request']['status'])
        self.assertEqual([], self.canary(request=request)['items'])
        self.recover(request)

    def test_preflight_then_expiry_revoke_scope_and_fingerprint_drift(self):
        for fault in ('expiry', 'owner-revoke', 'scope', 'fingerprint', 'environment', 'authority-revoke', 'source-revoke'):
            with self.subTest(fault=fault):
                provider = self.a.new_provider()
                request = provider.accept()
                self.assertEqual('observed', self.preflight(provider=provider, request=request)['checks']['request']['status'])
                changed = request
                patch = mock.patch.object(p, 'SCHEMA', p.SCHEMA)
                if fault == 'expiry':
                    sample = self.ctx.clock.clock()
                    patch = mock.patch.object(self.ctx.clock, 'clock', return_value=replace(sample, utc_seconds=sample.utc_seconds + 301))
                elif fault == 'owner-revoke':
                    provider.revoke(request.request_id)
                elif fault == 'scope':
                    changed = replace(request, scope_digest='0' * 64)
                elif fault == 'fingerprint':
                    patch = mock.patch.object(p, 'adapter_fingerprint', return_value='0' * 64)
                elif fault == 'environment':
                    patch = mock.patch.object(p.os, 'fstatvfs', side_effect=OSError(errno.EIO, 'PRIVATE'))
                elif fault == 'authority-revoke':
                    self.authority_revoked.add(self.ctx.authority_qualification.evidence_id)
                else:
                    self.f.revoked_sources.add(self.f.acceptance.evidence_id)
                with patch:
                    report = self.canary(provider, changed)
                if fault == 'source-revoke':
                    self.assertTrue(all(item['summary'] is None for item in report['items']))
                else:
                    self.assertEqual([], report['items'])
                self.authority_revoked.clear()
                self.f.revoked_sources.clear()
                self.recover(request)

    def test_final_disclosure_rechecks_owner_and_authority_qualification(self):
        for fault in ('close', 'revoke', 'authority-revoke', 'authority-identity'):
            provider = self.a.new_provider()
            request = provider.accept()
            original = AuditSnapshot.validate_disclosure
            reached = []
            def final(snapshot):
                if snapshot._closed:
                    reached.append(True)
                    if fault == 'close':
                        provider.close()
                    elif fault == 'revoke':
                        provider.revoke(request.request_id)
                    elif fault == 'authority-revoke':
                        self.authority_revoked.add(self.ctx.authority_qualification.evidence_id)
                    elif fault == 'authority-identity':
                        (self.a.directory / db.LOCK).chmod(0o644)
                    else:
                        self.authority_revoked.add(self.ctx.authority_qualification.evidence_id)
                return original(snapshot)
            with self.subTest(fault=fault), mock.patch.object(AuditSnapshot, 'validate_disclosure', final):
                report = self.canary(provider, request)
            self.assertTrue(reached)
            self.assertEqual([], report['items'])
            self.assertIsNone(report['snapshot_digest'])
            self.authority_revoked.clear()
            (self.a.directory / db.LOCK).chmod(0o600)
            self.recover(request)

    def test_preflight_then_target_file_identity_mismatch(self):
        request = self.a.provider.accept()
        self.preflight(provider=self.a.provider, request=request)
        main = self.f.root / db.MAIN
        saved = self.f.parent / 'old-managed'
        main.rename(saved)
        main.write_bytes(saved.read_bytes())
        main.chmod(0o600)
        self.assertEqual([], p.canary_report(enabled=True, context=self.ctx, provider=self.a.provider, request=request)['items'])
        self.assertEqual('invalid', self.preflight()['checks']['target_metadata']['status'])

    def test_stop_dispatch_retains_data_requires_new_acceptance_to_resume(self):
        request = self.a.provider.accept()
        self.assertEqual('complete', self.canary(request=request)['status'])
        self.assertEqual('adapter-unavailable', audit_report(enabled=True)['reason'])
        self.a.provider.revoke(request.request_id)
        self.assertEqual([], self.canary(request=request)['items'])
        self.a.provider.close()
        self.recover(request)

    def test_metadata_permission_expiry_revoke_mismatch_no_observation(self):
        sample = self.ctx.clock.clock()
        contexts = [replace(self.ctx, inspection=None),
                    replace(self.ctx, inspection=replace(self.ctx.inspection, expires_at=sample.utc_seconds)),
                    replace(self.ctx, inspection=replace(self.ctx.inspection, target_digest='0' * 64)),
                    replace(self.ctx, inspection_revoked=lambda _: True)]
        for ctx in contexts:
            with self.subTest(ctx=ctx.inspection is None), \
                 mock.patch.object(db, 'root_fd', side_effect=AssertionError('metadata touched')), \
                 mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('runtime touched')), \
                 mock.patch.object(self.a.provider, 'pending_current', side_effect=AssertionError('provider touched')):
                result = self.preflight(context=ctx, provider=self.a.provider, request=object())
            self.assertEqual('unknown', result['checks']['target_metadata']['status'])
            self.assertEqual('unknown', result['checks']['request']['status'])

    def test_pending_observation_ram_only_rollback_foreign_fork_and_row_tamper(self):
        request = self.a.provider.accept()
        with a._connection(self.a.store, writer=True) as connection:
            connection.execute("UPDATE requests SET state='revoked'")
            connection.commit()
        report = self.preflight(provider=self.a.provider, request=request)
        self.assertEqual('observed', report['checks']['request']['status'])
        self.assertEqual('unknown', report['checks']['authority_store_contents']['status'])
        self.assertFalse(self.a.new_provider().pending_current(request))
        self.assertFalse(self.a.provider.pending_current(replace(request, scope_digest='0' * 64)))
        sample = self.ctx.clock.clock()
        with mock.patch.object(self.ctx.clock, 'clock', return_value=replace(sample, monotonic_ns=-1)):
            self.assertFalse(self.a.provider.pending_current(request))
        with mock.patch.object(a.os, 'getpid', return_value=self.a.provider._pid + 1):
            self.assertFalse(self.a.provider.pending_current(request))
        self.assertEqual([], self.canary(request=request)['items'])
        self.recover(request)

    def test_expiry_during_last_environment_observation_clears_report(self):
        provider = self.a.provider
        original = AuditSnapshot.validate_disclosure
        environment = p.authority_environment
        sample = self.ctx.clock.clock()
        current = [sample]
        expired = replace(sample, utc_seconds=sample.utc_seconds + 2,
                          monotonic_ns=sample.monotonic_ns + 2_000_000_000)
        reached = []
        def final(snapshot):
            if not snapshot._closed:
                return original(snapshot)
            def observe(store, **kwargs):
                value = environment(store, **kwargs)
                current[0] = expired
                reached.append(True)
                return value
            with mock.patch.object(p, 'authority_environment', side_effect=observe):
                return original(snapshot)
        # 保持授權有效直到指定 observation；不受 runner 是否跨過真實一秒影響。
        with mock.patch.object(self.ctx.clock, 'clock', side_effect=lambda: current[0]):
            request = provider.accept(lifetime_seconds=1)
            with mock.patch.object(AuditSnapshot, 'validate_disclosure', final):
                report = self.canary(provider, request)
        self.assertTrue(reached)
        self.assertEqual([], report['items'])
        self.assertEqual(0, report['counts']['listed'])
        self.assertIsNone(report['snapshot_digest'])

    def test_permission_expiring_in_callback_prevents_metadata_open(self):
        current = [self.ctx.clock.clock()]
        calls = []
        def revoked(_):
            calls.append(True)
            current[0] = replace(current[0], utc_seconds=self.ctx.inspection.expires_at + 1)
            return False
        with mock.patch.object(self.ctx.clock, 'clock', side_effect=lambda: current[0]), \
             mock.patch.object(db, 'root_fd', side_effect=AssertionError('expired metadata open')):
            report = self.preflight(context=replace(self.ctx, inspection_revoked=revoked))
        self.assertTrue(calls)
        self.assertEqual('invalid', report['checks']['metadata_permission']['status'])
        self.assertEqual('unknown', report['checks']['target_metadata']['status'])

    def test_permission_expiring_or_revoked_during_root_open_stops_inventory_and_closes(self):
        for change in ('expiry', 'revoked'):
            with self.subTest(change=change):
                current = [self.ctx.clock.clock()]
                revoked = []
                opened = []
                real = db.root_fd
                def root(binding):
                    fd = real(binding)
                    opened.append(fd)
                    if change == 'expiry':
                        current[0] = replace(current[0], utc_seconds=self.ctx.inspection.expires_at + 1)
                    else:
                        revoked.append(True)
                    return fd
                ctx = replace(self.ctx, inspection_revoked=lambda _: bool(revoked))
                with mock.patch.object(self.ctx.clock, 'clock', side_effect=lambda: current[0]), \
                     mock.patch.object(db, 'root_fd', side_effect=root), \
                     mock.patch.object(db, 'inventory', side_effect=AssertionError('post-expiry inventory')), \
                     mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('post-expiry runtime')):
                    report = self.preflight(context=ctx)
                self.assertTrue(opened)
                self.assertEqual('invalid', report['checks']['target_metadata']['status'])
                for fd in opened:
                    with self.assertRaises(OSError):
                        os.fstat(fd)

    def test_metadata_reuses_device_verified_by_root_fd(self):
        original = os.fstat
        calls = []
        def fstat(fd):
            calls.append(fd)
            return original(fd)
        with mock.patch.object(p.os, 'fstat', side_effect=fstat):
            observation = p._metadata(self.f.binding, self.ctx.check_inspection)
        self.assertEqual(1, len(calls))  # root_fd only; no syscall after final permission check.
        self.assertEqual(self.f.binding.directory_identity[0], observation['device'])

    def test_filesystem_identity_preserves_full_os_integer_without_numeric_limit(self):
        real = os.fstatvfs
        for fsid in (2**64 - 1, -(2**63)):
            with self.subTest(fsid=fsid):
                def facts(fd):
                    value = real(fd)
                    return SimpleNamespace(f_fsid=fsid, f_frsize=value.f_frsize, f_flag=value.f_flag)
                with mock.patch.object(p.os, 'fstatvfs', side_effect=facts):
                    environment = p.authority_environment(self.a.store)
                    self.assertEqual(str(fsid), environment['filesystem']['filesystem_identity'])
                    accepted = replace(self.ctx.authority_qualification, environment_bytes=c.canonical(environment))
                    ctx = replace(self.ctx, authority_qualification=accepted)
                    self.assertEqual('observed', self.preflight(context=ctx)['checks']['authority_environment']['status'])
                    request = self.a.provider.accept()
                    self.assertEqual('complete', self.canary(request=request, context=ctx)['status'])
                # Restoring the actual filesystem identity invalidates the synthetic acceptance.
                self.assertEqual('invalid', self.preflight(context=ctx)['checks']['authority_environment']['status'])

    def test_canary_actual_transaction_fault_cleanup_and_new_acceptance_recovery(self):
        faults = []
        for code in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_BUSY, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_NOMEM):
            error = sqlite3.OperationalError('PRIVATE')
            error.sqlite_errorcode = code
            faults.append(error)
        faults += [OSError(errno.ENOSPC, 'PRIVATE'), OSError(errno.ENOMEM, 'PRIVATE'), RuntimeError('PRIVATE')]
        for point in ('update', 'commit-after', 'readback'):
            for fault in faults:
                with self.subTest(point=point, fault=type(fault).__name__):
                    provider = self.a.new_provider()
                    request = provider.accept()
                    self.preflight(provider=provider, request=request)
                    with self.a.inject(point, fault):
                        report = self.canary(provider, request)
                    self.assertEqual([], report['items'])
                    self.assertEqual('unavailable', report['status'])
                    self.assertTrue(provider._failed)
                    self.a.assert_closed()
                    self.recover(request)


if __name__ == '__main__':
    unittest.main()
