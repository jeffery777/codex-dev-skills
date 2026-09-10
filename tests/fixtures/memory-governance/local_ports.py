"""明確 synthetic TCB。僅 tests 載入；不屬 installed source 或真實 host qualification。"""
from __future__ import annotations

import copy
from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_host import AcceptedPreview, SourceObservation
from memory_governance_local import LocalClock, LocalHost, RepositoryArtifact, RepositorySource, SingleRootRegistry

SPEC = importlib.util.spec_from_file_location('g1_original_fixture', Path(__file__).with_name('synthetic_host.py'))
original = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(original)
ARTIFACT = b'Synthetic widget labels blue, green and red are only test data.\n'


class SyntheticLocalPorts:
    """由測試明確提供 acceptance/source/budget；實際 clock/registry/DB 由正式組合元件執行。"""

    def __init__(self, root, *, git_root=None):
        binding = original.SyntheticHost(root).binding()
        binding = replace(binding, filesystem_id='synthetic-fs-' + str(root.stat().st_dev))
        self.registry = SingleRootRegistry(binding)
        self.clock_port = LocalClock()
        self.host = self.compose()
        self.accepted = self.readable = self.qualified = self.source_current = True
        self.safety = 'safe'
        self.readback_ids = set()
        self.approved = {}
        self.calls = []
        self.runtime = db.runtime_facts()
        self.git_root = git_root
        self.source_revision = 'a' * 40
        if git_root is not None:
            # Only the newly created repository belongs to this fixture; no arbitrary project reader.
            git_root.mkdir(mode=0o700)
            self.git('init', '-q', '-b', 'source', '--template=')
            (git_root / 'artifact.txt').write_bytes(ARTIFACT)
            self.git('add', '--', 'artifact.txt')
            self.git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid',
                     '-c', 'core.hooksPath=/dev/null', 'commit', '-q', '-m', 'Synthetic source')
            self.source_revision = self.git('rev-parse', 'HEAD').decode().strip()
            self.git_identity = db.identity(git_root.stat())
            self.gitdir_identity = db.identity((git_root / '.git').stat())
            self.git_config = (git_root / '.git/config').read_bytes()

    def git(self, *args):
        env = {'PATH': os.defpath, 'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_SYSTEM': '/dev/null',
               'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1',
               'GIT_OPTIONAL_LOCKS': '0', 'GIT_ALLOW_PROTOCOL': ''}
        return subprocess.run(['git', '-C', str(self.git_root), *args], env=env,
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=10).stdout

    def compose(self, *, source=True, authority=True, qualification=True):
        return LocalHost(self.registry, source=RepositorySource(self, self) if source else None,
                         authority=self if authority else None, qualification=self if qualification else None,
                         clock=self.clock_port)

    def reopened(self):
        other = copy.copy(self)
        other.registry = SingleRootRegistry(self.registry.binding())
        other.clock_port = LocalClock()
        other.calls = []
        other.readback_ids = set(self.readback_ids)  # Explicit fixture read authority, never restored mutation authority.
        other.approved = dict(self.approved)
        other.host = other.compose()
        return other

    def candidate(self, revision=1, *, cue='blue', body=None):
        now = self.clock_port.clock().utc_seconds
        value = original.version(revision, now=now, cue=cue, body=body)
        value['provenance'][0].update(source_revision=self.source_revision,
                                      source_digest=hashlib.sha256(ARTIFACT).hexdigest())
        value['provenance'][0]['reference']['path'] = 'artifact.txt'
        value['validation']['content_digest'] = c.content_digest(value)
        self.approve(value)
        return value

    def approve(self, value):
        # Test-owned independent approval data; a caller's schema-valid validation is insufficient.
        self.approved[c.digest(value)] = copy.deepcopy(value['validation'])

    def read_artifact(self, binding, provenance_bytes):
        self.calls.append('artifact')
        provenance = c.decode(provenance_bytes)
        if binding != self.registry.binding() or provenance['source_id'] != 'synthetic-source':
            raise c.ContractError('fixture-source-unavailable')
        content = ARTIFACT
        current = self.source_current
        if self.git_root is not None:
            assert db.identity(self.git_root.stat()) == self.git_identity
            assert db.identity((self.git_root / '.git').stat()) == self.gitdir_identity
            assert (self.git_root / '.git/config').read_bytes() == self.git_config
            current = current and self.git('rev-parse', 'HEAD').decode().strip() == self.source_revision
            # Both object selector and bounded tiny fixture bytes are fixed by test setup, never by provenance.
            content = self.git('cat-file', 'blob', self.source_revision + ':artifact.txt')
            assert content == ARTIFACT
            current = current and self.git('rev-parse', 'HEAD').decode().strip() == self.source_revision
        return RepositoryArtifact('synthetic-source', 'synthetic-repository', self.source_revision,
                                  'artifact.txt', content, 'current' if current else 'revoked')

    def review_source(self, binding, version_bytes, artifacts):
        self.calls.append('review')
        value = c.decode(version_bytes)
        validation = self.approved.get(c.digest(value))
        if validation is None:
            raise c.ContractError('fixture-candidate-not-approved')
        return SourceObservation(c.digest(c.decode(binding.scope_bytes)), c.digest(value),
                                 c.digest(value['provenance']), validation['policy_fingerprint'],
                                 validation['verifier_fingerprint'], validation['evidence_id'],
                                 self.clock_port.clock().utc_seconds, 'eligible', self.safety)

    def qualify(self, binding, runtime, operation):
        self.calls.append('qualify')
        return self.qualified and binding == self.registry.binding() and runtime == self.runtime and operation in {
            'initialize', 'authorize', 'audit', 'recall', 'readback', 'add', 'update', 'restore', 'stop', 'resume'}

    def accept_initialization(self, binding):
        return self.accepted and binding == self.registry.binding()

    def accept_preview(self, binding, preview_bytes):
        self.calls.append('accept')
        if not self.accepted or binding != self.registry.binding():
            raise c.ContractError('fixture-acceptance-denied')
        preview = c.decode(preview_bytes)
        self.readback_ids.add(preview['operation_id'])
        return AcceptedPreview(preview_bytes, c.canonical({
            'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
            'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
            'preview_digest': c.digest(preview), 'confirmed_at': self.clock_port.clock().utc_seconds,
            'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-only-acceptance'}))

    def authorize_read(self, binding, purpose, operation_id):
        self.calls.append('read')
        return self.readable and binding == self.registry.binding() and (
            purpose in {'audit', 'recall', 'preview'} or purpose == 'readback' and operation_id in self.readback_ids)

    def external_copies(self, binding):
        return {'coverage': 'unknown', 'observed_at': self.clock_port.clock().utc_seconds, 'copies': []}

    def committed_work_bytes(self, binding):
        return 0

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        # Synthetic admission values, NOT bounds qualified by the measurement runner.
        journal, temp, growth = sum(f['bytes'] for f in files) + 65536, 1048576, 262144
        return {'qualification_id': 'synthetic-only-not-qualified', 'file_snapshot_digest': c.digest(files),
                'journal_bound_bytes': journal, 'temp_bound_bytes': temp, 'growth_bound_bytes': growth,
                'required_work_bytes': (journal + temp + growth + 4095) // 4096 * 4096}
