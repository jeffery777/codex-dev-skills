from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import errno
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest import mock
import uuid
import zlib

from tests.test_memory_governance_local import local_fixture
from tests.test_memory_governance_core import c, db, GovernanceCore, ITEM
from memory_audit import audit_report, render_report
from memory_audit_adapter import (AcceptedSourceReview, AuditOnlyHost, AuditQualification, AuditReadAuthority,
                                  ReadGrant, SourceAcceptance, adapter_fingerprint, audit_environment)
from memory_audit_source import ArtifactPermit, GitRepositoryBinding, PinnedGitReader
from memory_governance_core import AuditSnapshot
from memory_governance_host import PRODUCTION_ADAPTERS
from memory_governance_local import SingleRootRegistry


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mg1-audit-adapter-')
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.root, self.git = self.parent / 'managed', self.parent / 'source'
        self.root.mkdir(mode=0o700)
        self.ports = local_fixture.SyntheticLocalPorts(self.root, git_root=self.git)
        # Only fixture setup can initialize/write. The actual adapter below receives audit only.
        original = self.ports.registry.binding()
        profile = c.decode(original.profile_bytes)
        profile.update(data_limit_bytes=268435456, maintenance_max_bytes=335544320)
        scope = c.decode(original.scope_bytes)
        scope['profile_digest'] = c.digest(profile)
        self.ports.registry = SingleRootRegistry(replace(original, profile_bytes=c.canonical(profile),
                                                        scope_bytes=c.canonical(scope)))
        self.ports.host = self.ports.compose()
        core = GovernanceCore(self.ports.host, enabled=True)
        core.initialize()
        self.value = self.ports.candidate()
        preview = core.preview('add', ITEM, self.value)
        self.assertEqual('applied', core.execute(core.authorize(preview))['result'])
        self.binding = replace(self.ports.registry.binding(), capabilities=frozenset({'audit'}),
                               adapter_fingerprint=adapter_fingerprint())
        self.revoked_requests, self.revoked_sources, self.revoked_qualifications = set(), set(), set()
        self.repo = GitRepositoryBinding(self.git, db.identity(self.git.stat()),
                                        db.identity((self.git / '.git').stat()),
                                        db.identity((self.git / '.git/objects').stat()), 'synthetic-repository')
        self.permit = ArtifactPermit('synthetic-source', self.ports.source_revision, 'artifact.txt',
                                     hashlib.sha256(local_fixture.ARTIFACT).hexdigest())
        self.acceptance = SourceAcceptance(c.digest(c.decode(self.binding.scope_bytes)), c.digest(self.value),
                                          c.digest(self.value['provenance']), c.digest(c.POLICY),
                                          self.value['validation']['verifier_fingerprint'],
                                          self.value['validation']['evidence_id'], 'eligible', 'safe',
                                          self.ports.clock_port.clock().utc_seconds + 300)
        self.qualification = AuditQualification(db.binding_digest(self.binding),
            c.canonical(audit_environment(self.binding, db.runtime_facts())),
            'synthetic-audit-only-not-production', self.acceptance.expires_at)

    def host(self, *, accepted=None, qualification=None, grant=None, permits=None, repository=None):
        clock = self.ports.clock_port
        if grant is None:
            grant = ReadGrant(self.binding, c.decode(self.binding.scope_bytes)['principal_id'], str(uuid.uuid4()),
                              clock.clock(), clock.clock().utc_seconds + 300)
        authority = AuditReadAuthority(grant, principal_id=grant.principal_id, request_id=grant.request_id,
                                       revoked=self.revoked_requests.__contains__, clock=clock)
        review = AcceptedSourceReview((self.acceptance,) if accepted is None else accepted,
                                       revoked=self.revoked_sources.__contains__, authority=authority)
        return AuditOnlyHost(SingleRootRegistry(self.binding), authority=authority,
                             repository=repository or self.repo, permits=permits or (self.permit,),
                             source_review=review, qualification=qualification or self.qualification,
                             qualification_revoked=self.revoked_qualifications.__contains__)

    def inventory(self):
        return {p.name: (p.stat().st_ino, p.stat().st_mtime_ns, p.read_bytes()) for p in self.root.iterdir()}

    def report(self, host=None, **kwargs):
        before = self.inventory()
        result = audit_report(enabled=True, host=host or self.host(), **kwargs)
        self.assertEqual(before, self.inventory())
        with db.locked(self.binding, exclusive=True):
            pass
        self.assertFalse(result['write_performed'])
        self.assertFalse(result['production_qualified'])
        return result

    def test_real_git_sqlite_adapter_end_to_end_and_single_request(self):
        host = self.host()
        result = self.report(host)
        self.assertEqual(('complete', 'complete'), (result['status'], result['source_coverage']))
        self.assertEqual(self.value['summary'], result['items'][0]['summary'])
        self.assertEqual(self.permit.revision, result['items'][0]['sources'][0]['revision'])
        self.assertIsNone(result['capacity']['bytes'])
        self.assertEqual('unknown', result['external_copies'])
        self.assertEqual('qualification-unavailable', self.report(host)['reason'])
        self.assertEqual('complete', self.report()['status'])

    def test_off_zero_touch_and_no_mutation_capability(self):
        host = self.host()
        with mock.patch.object(host, 'binding', side_effect=AssertionError('touch')):
            self.assertEqual('disabled', audit_report(host=host)['status'])
        self.assertFalse(host.authority._claimed)
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))
        core = GovernanceCore(host, enabled=True)
        for call in (core.initialize, lambda: core.recall(['blue']), lambda: core.preview('stop', ITEM),
                     lambda: host.bind_initialized(self.binding, (1, 2), (1, 3))):
            with self.assertRaisesRegex(c.ContractError, 'capability-unavailable'):
                call()
        for purpose in ('initialize', 'readback', 'preview', 'recall', 'content-write'):
            self.assertFalse(host.authorize_read(self.binding, purpose, None))

    def test_direct_core_disabled_and_process_drift_never_touch_host(self):
        class UntouchableHost:
            @property
            def audit_timeout_seconds(self):
                raise AssertionError('host property touched before authority boundary')

        host = UntouchableHost()
        for core in (GovernanceCore(host), GovernanceCore(None, enabled=True)):
            with self.assertRaisesRegex(c.ContractError, 'memory-disabled'):
                core.audit()
        core = GovernanceCore(host, enabled=True)
        with mock.patch('memory_governance_core.os.getpid', return_value=core._process + 1):
            with self.assertRaisesRegex(c.ContractError, 'process-changed'):
                core.audit()

    def test_authority_scope_principal_request_expiry_revocation_rollback(self):
        host = self.host()
        grant = host.authority.grant
        for principal, request in ((str(uuid.uuid4()), grant.request_id), (grant.principal_id, str(uuid.uuid4()))):
            with self.assertRaisesRegex(c.ContractError, 'read-unavailable'):
                AuditReadAuthority(grant, principal_id=principal, request_id=request, revoked=lambda _: False,
                                   clock=self.ports.clock_port)
        for delta in (-1, 301):
            with self.assertRaises(c.ContractError):
                self.host(grant=replace(grant, expires_at=grant.issued.utc_seconds + delta))
        self.revoked_requests.add(grant.request_id)
        with mock.patch.object(db, 'root_fd', side_effect=AssertionError('unauthorized root access')):
            self.assertEqual('qualification-unavailable', audit_report(enabled=True, host=host)['reason'])
        for change in ('rollback', 'utc-expiry', 'monotonic-expiry', 'process'):
            authority = self.host().authority
            sample = authority.grant.issued
            changed = {'rollback': replace(sample, utc_seconds=sample.utc_seconds - 1),
                       'utc-expiry': replace(sample, utc_seconds=sample.utc_seconds + 300),
                       'monotonic-expiry': replace(sample, monotonic_ns=sample.monotonic_ns + 300_000_000_000),
                       'process': replace(sample, process_id=str(uuid.uuid4()))}[change]
            with mock.patch.object(authority.clock, 'clock', return_value=changed):
                self.assertFalse(authority.valid(self.binding))
        self.assertEqual('complete', self.report()['status'])

    def test_environment_qualification_rejects_every_changed_dimension(self):
        observed = c.decode(self.qualification.environment_bytes)
        for key in observed:
            changed = dict(observed)
            changed[key] = None
            q = replace(self.qualification, environment_bytes=c.canonical(changed))
            with self.subTest(dimension=key), mock.patch.object(db, 'root_fd', side_effect=AssertionError('root')):
                self.assertEqual('qualification-unavailable', audit_report(enabled=True, host=self.host(qualification=q))['reason'])
        for key in observed['runtime']:
            changed = {**observed, 'runtime': {**observed['runtime'], key: None}}
            q = replace(self.qualification, environment_bytes=c.canonical(changed))
            self.assertEqual('qualification-unavailable', self.report(self.host(qualification=q))['reason'])
        self.revoked_qualifications.add(self.qualification.evidence_id)
        self.assertEqual('qualification-unavailable', self.report()['reason'])
        self.revoked_qualifications.clear()
        self.assertEqual('complete', self.report()['status'])

    def test_independent_source_acceptance_and_sensitive_content_redaction(self):
        for accepted in ((), (replace(self.acceptance, safety='prohibited'),),
                         (replace(self.acceptance, safety='unknown'),),
                         (replace(self.acceptance, version_digest='a' * 64),),
                         (replace(self.acceptance, verifier_fingerprint='a' * 64),),
                         (replace(self.acceptance, evidence_id='independent-different-evidence'),)):
            result = self.report(self.host(accepted=accepted))
            self.assertEqual('partial', result['source_coverage'])
            self.assertIsNone(result['items'][0]['summary'])
            self.assertIsNone(result['items'][0]['sources'])
            self.assertNotIn(self.permit.revision, render_report(result))
        self.assertEqual('complete', self.report()['source_coverage'])

    def test_allowlist_rejection_precedes_filesystem_and_git_config_is_not_executed(self):
        host = self.host()
        self.assertTrue(host.authority.claim(self.binding))
        provenance = self.value['provenance'][0]
        for change in ({'source_id': 'other'}, {'source_revision': 'b' * 40}, {'source_digest': 'b' * 64},
                       {'reference': {'repository_id': 'other', 'path': 'artifact.txt'}},
                       {'reference': {'repository_id': 'synthetic-repository', 'path': '../escape'}}):
            with mock.patch('memory_audit_source.os.open', side_effect=AssertionError('unapproved I/O')):
                with self.assertRaises(c.ContractError):
                    host.reader.read_artifact(self.binding, c.canonical({**provenance, **change}))
        (self.git / '.git/config').write_text('invalid config; reader must never parse or execute it')
        (self.git / 'artifact.txt').write_text('UNTRUSTED WORKTREE CONTENT')
        self.assertEqual('complete', self.report()['source_coverage'])

    def test_missing_object_symlink_corruption_and_new_authority_recovery(self):
        oid = self.ports.git('rev-parse', self.permit.revision + ':artifact.txt').decode().strip()
        path = self.git / '.git/objects' / oid[:2] / oid[2:]
        original = path.read_bytes()
        saved = self.parent / 'object.saved'
        path.rename(saved)
        result = self.report()
        self.assertEqual('partial', result['source_coverage'])
        self.assertIsNone(result['items'][0]['summary'])
        path.symlink_to(saved)
        result = self.report()
        self.assertIsNone(result['items'][0]['summary'])
        path.unlink()  # Fixture-owned temporary fault only.
        saved.rename(path)
        path.chmod(0o600)
        path.write_bytes(zlib.compress(b'blob 4\0evil'))
        result = self.report()
        self.assertEqual([], result['items'])
        path.write_bytes(original)
        self.assertEqual('complete', self.report()['source_coverage'])

    def test_source_byte_and_decompression_bounds_and_timeout(self):
        host = self.host()
        host.reader.max_bytes = 1  # Narrower test envelope; never a larger production allowance.
        self.assertEqual([], self.report(host)['items'])
        host = self.host()
        with mock.patch.object(host.reader, '_object', side_effect=c.ContractError('source-timeout')):
            result = self.report(host)
        self.assertEqual('partial', result['source_coverage'])
        self.assertIsNone(result['items'][0]['summary'])
        self.assertEqual('complete', self.report()['status'])

    def test_root_source_identity_drift_and_corrupt_sqlite_never_repair(self):
        host = self.host(repository=replace(self.repo, git_identity=(0, 0)))
        self.assertEqual([], self.report(host)['items'])
        host = self.host()
        drifted = replace(self.binding, main_identity=(0, 0))
        with mock.patch.object(host, 'binding', return_value=drifted):
            self.assertEqual([], self.report(host)['items'])
        path = self.root / db.MAIN
        original = path.read_bytes()
        path.write_bytes(b'not a sqlite database')
        result = self.report()
        self.assertEqual('unavailable', result['status'])
        self.assertEqual([], result['items'])
        path.write_bytes(original)
        self.assertEqual('complete', self.report()['status'])

    def test_real_coordination_and_sqlite_locks_release_without_retry(self):
        with db.locked(self.binding, exclusive=True):
            result = audit_report(enabled=True, host=self.host())
            self.assertEqual('busy', result['reason'])
        with closing(sqlite3.connect(self.root / db.MAIN, isolation_level=None)) as blocker:
            blocker.execute('BEGIN EXCLUSIVE')
            started = time.monotonic()
            result = audit_report(enabled=True, host=self.host())
            self.assertEqual('busy', result['reason'])
            self.assertLess(time.monotonic() - started, 2)
            blocker.rollback()
        self.assertEqual('complete', self.report()['status'])

    def test_injected_io_enospc_enomem_no_leak_no_retry_and_recovery(self):
        for code in (errno.EIO, errno.ENOSPC, errno.ENOMEM):
            host = self.host()
            with mock.patch.object(db, 'connect', side_effect=OSError(code, 'PRIVATE PATH CONTENT')) as connect:
                result = self.report(host)
                self.assertEqual(1, connect.call_count)
            self.assertEqual('unavailable', result['status'])
            self.assertNotIn('PRIVATE', json.dumps(result))
            self.assertEqual({errno.ENOSPC: 'storage-full', errno.ENOMEM: 'resource-limit',
                              errno.EIO: 'storage-io'}[code], result['reason'])
            self.assertEqual('complete', self.report()['status'])

    def test_revocation_with_io_and_at_final_output_clears_disclosure(self):
        for cause in ('io', 'last-page', 'source', 'qualification'):
            host = self.host()
            original = AuditSnapshot.page
            def fail(snapshot, cursor=None):
                result = original(snapshot, cursor)
                if cause == 'source':
                    self.revoked_sources.add(self.acceptance.evidence_id)
                elif cause == 'qualification':
                    self.revoked_qualifications.add(self.qualification.evidence_id)
                else:
                    self.revoked_requests.add(host.authority.grant.request_id)
                if cause == 'io':
                    raise OSError(errno.EIO, 'PRIVATE')
                return result
            with mock.patch.object(AuditSnapshot, 'page', fail):
                result = self.report(host)
            self.assertEqual([], result['items'])
            self.assertIsNone(result['snapshot_digest'])
            self.revoked_sources.clear()
            self.revoked_qualifications.clear()
            self.assertEqual('complete', self.report()['status'])

    def test_closed_snapshot_cursor_and_grant_cannot_replay(self):
        host = self.host()
        snapshot = GovernanceCore(host, enabled=True).audit()
        snapshot.close()
        with self.assertRaisesRegex(c.ContractError, 'cursor-unavailable'):
            snapshot.page()
        self.assertEqual('qualification-unavailable', self.report(host)['reason'])
        self.assertEqual('complete', self.report()['status'])

    def test_object_decompression_bomb_and_cooperative_read_deadline(self):
        oid = self.ports.git('rev-parse', self.permit.revision + ':artifact.txt').decode().strip()
        path = self.git / '.git/objects' / oid[:2] / oid[2:]
        original = path.read_bytes()
        path.chmod(0o600)
        path.write_bytes(zlib.compress(b'blob 1000000\0' + b'x' * 1_000_000))
        result = self.report()
        self.assertIsNone(result['items'][0]['summary'])
        path.write_bytes(original)
        host = self.host()
        self.assertTrue(host.authority.claim(self.binding))
        with mock.patch('memory_audit_source.time.monotonic', side_effect=[0, 1]):
            with self.assertRaisesRegex(c.ContractError, 'source-timeout'):
                host.reader.read_artifact(self.binding, c.canonical(self.value['provenance'][0]))
        self.assertEqual('complete', self.report()['source_coverage'])

    def test_mid_source_revocation_stops_io_and_closes_descriptors(self):
        host = self.host()
        original = os.read
        observed_fds = set()
        def revoke(fd, count):
            observed_fds.add(fd)
            result = original(fd, count)
            self.revoked_requests.add(host.authority.grant.request_id)
            return result
        with mock.patch('memory_audit_source.os.read', side_effect=revoke):
            result = self.report(host)
        self.assertEqual([], result['items'])
        self.assertTrue(observed_fds)
        for fd in observed_fds:
            with self.assertRaises(OSError):
                os.fstat(fd)
        self.assertEqual('complete', self.report()['status'])

    def test_source_replacement_after_valid_page_clears_content(self):
        host = self.host()
        original = AuditSnapshot.page
        def replace_source(snapshot, cursor=None):
            result = original(snapshot, cursor)
            self.git.rename(self.parent / 'old-source')
            self.git.mkdir()
            return result
        with mock.patch.object(AuditSnapshot, 'page', replace_source):
            result = self.report(host)
        self.assertEqual([], result['items'])
        self.git.rmdir()  # Only the empty temporary replacement belongs to this fixture.
        (self.parent / 'old-source').rename(self.git)
        self.assertEqual('complete', self.report()['source_coverage'])

    def test_memory_error_closes_connection_and_new_grant_recovers(self):
        host = self.host()
        with mock.patch.object(db, 'load_item', side_effect=MemoryError('PRIVATE CONTENT')):
            result = self.report(host)
        self.assertEqual('resource-limit', result['reason'])
        self.assertEqual([], result['items'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual('complete', self.report()['status'])

    def bulk(self, count=257):
        # Separate temporary database; real proof replay and paging, synthetic fixture authority.
        self.root = self.parent / 'bulk'
        self.root.mkdir(mode=0o700)
        now = self.ports.clock_port.clock().utc_seconds
        seed_host = local_fixture.original.SyntheticHost(self.root, now=now)
        seed_host._binding = replace(seed_host.binding(), profile_bytes=self.binding.profile_bytes,
                                     scope_bytes=self.binding.scope_bytes)
        GovernanceCore(seed_host, enabled=True).initialize()
        self.value.update(created_at=now)
        self.value['validation']['verified_at'] = now
        with mock.patch.object(local_fixture.original, 'version', return_value=self.value):
            local_fixture.original.seed_audit_items(seed_host, count)
        self.binding = replace(seed_host.binding(), capabilities=frozenset({'audit'}),
                               adapter_fingerprint=adapter_fingerprint())
        self.acceptance = replace(self.acceptance, version_digest=c.digest(self.value))
        self.qualification = replace(self.qualification, binding_digest=db.binding_digest(self.binding),
                                    environment_bytes=c.canonical(audit_environment(self.binding, db.runtime_facts())))

    def test_actual_adapter_page_output_limits_safe_partial_and_fresh_recovery(self):
        self.bulk()
        result = self.report(max_pages=1)
        self.assertEqual(('partial', 'page-limit', 256),
                         (result['status'], result['reason'], result['counts']['listed']))
        small = self.report(max_output_bytes=4096)
        self.assertEqual('output-limit', small['reason'])
        self.assertLessEqual(len(c.canonical(small)), 4096)
        self.assertLessEqual(len(render_report(small).encode()), 4096)
        self.assertEqual('complete', self.report()['status'])

    def test_partial_requires_live_authority_and_unchanged_integrity_even_with_io_error(self):
        self.bulk()
        for revoke in (False, True):
            host = self.host()
            original = AuditSnapshot.page
            def fail_second(snapshot, cursor=None):
                if cursor is not None:
                    if revoke:
                        self.revoked_requests.add(host.authority.grant.request_id)
                    raise OSError(errno.EIO, 'PRIVATE')
                return original(snapshot, cursor)
            with mock.patch.object(AuditSnapshot, 'page', fail_second):
                result = self.report(host)
            self.assertEqual(0 if revoke else 256, result['counts']['listed'])
            self.assertEqual('unavailable' if revoke else 'partial', result['status'])
        self.assertEqual('complete', self.report()['status'])

    def test_actual_snapshot_timeout_releases_reader_and_preserves_safe_page(self):
        self.bulk()
        host = self.host()
        original = AuditSnapshot.page
        def timeout_second(snapshot, cursor=None):
            if cursor is not None:
                snapshot._deadline = time.monotonic() - 1
            return original(snapshot, cursor)
        with mock.patch.object(AuditSnapshot, 'page', timeout_second):
            result = self.report(host)
        self.assertEqual(('partial', 'timeout', 256),
                         (result['status'], result['reason'], result['counts']['listed']))
        self.assertEqual('complete', self.report()['status'])

    def test_prior_valid_object_cannot_be_rebound_by_later_failed_read(self):
        self.bulk(2)
        oid = self.ports.git('rev-parse', self.permit.revision + ':artifact.txt').decode().strip()
        path = self.git / '.git/objects' / oid[:2] / oid[2:]
        original_bytes = path.read_bytes()
        for damaged in (zlib.compress(b'blob 1000000\0' + b'x' * 1_000_000), b'incomplete-zlib'):
            host = self.host()
            original = host.reader.read_artifact
            calls = 0
            def corrupt_on_second(binding, provenance):
                nonlocal calls
                calls += 1
                if calls == 2:
                    path.chmod(0o600)
                    path.write_bytes(damaged)
                return original(binding, provenance)
            with mock.patch.object(host.reader, 'read_artifact', side_effect=corrupt_on_second):
                result = self.report(host)
            self.assertEqual([], result['items'])
            self.assertIsNone(result['snapshot_digest'])
            self.assertTrue(host._source_invalid)
            path.write_bytes(original_bytes)
            self.assertEqual('complete', self.report()['source_coverage'])

    def test_cli_uses_actual_adapter_and_requires_new_host_for_new_request(self):
        import contextlib
        import io
        import governancectl
        for format in ('json', 'text'):
            output = io.StringIO()
            with mock.patch('memory_audit.production_host', return_value=self.host()), contextlib.redirect_stdout(output):
                status = governancectl.main(['audit', '--enabled', '--format', format])
            self.assertEqual(0, status)
            self.assertIn('complete' if format == 'json' else '項目列舉完成', output.getvalue())
