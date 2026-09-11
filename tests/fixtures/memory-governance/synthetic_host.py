"""Synthetic test TCB only. Never installed, discovered or loaded by governancectl."""
from __future__ import annotations

import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import uuid

import memory_governance_contract as c
from memory_governance_host import AcceptedPreview, ClockSample, RootBinding, SourceObservation
import memory_governance_storage as db

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = json.loads((ROOT / 'docs/loops/issue-213/g0-production-cases.json').read_text())['version_examples'][0]


def version(revision=1, *, now=100, cue='blue', body=None, evidence=None):
    value = copy.deepcopy(EXAMPLE)
    value.update(revision=revision, created_at=now, retired_at=None,
                 cues=[cue, 'widget'], body=body or f'Synthetic widget label {cue}.')
    value['validation'].update(content_digest=c.content_digest(value), verified_at=now,
                               evidence_id=evidence or f'synthetic-validation-{revision}')
    return value


class SyntheticHost:
    """Deliberately simulated qualification/source/acceptance; no real human or backend certification."""
    def __init__(self, root: Path, *, now=100):
        self.now = now
        self.monotonic = 0
        self.process_id = str(uuid.uuid4())
        self.qualified = self.accepted = self.readable = self.source_available = True
        self.safety = 'safe'
        self.approved = set()
        self.calls = []
        self.copies = {'coverage': 'unknown', 'observed_at': now, 'copies': []}
        limits = dict(c.DEFAULT_PROFILE)
        scope = {'principal_id': '00000000-0000-4000-8000-000000000001',
                 'root_id': '00000000-0000-4000-8000-000000000002',
                 'repository_id': 'synthetic-repository', 'schema_fingerprint': db.SCHEMA_FINGERPRINT,
                 'profile_digest': c.digest(limits), 'policy_fingerprint': c.digest(c.POLICY)}
        physical = root.resolve(strict=True)
        os.chmod(physical, 0o700)
        self._binding = RootBinding(physical, db.identity(physical.stat()), None, None,
                                    c.canonical(scope), c.canonical(limits), 'synthetic-filesystem', 'a'*64,
                                    frozenset({'initialize', 'audit', 'recall', 'readback', 'content-write'}))
        self.committed_bytes = 0
        self.budget_growth = 262144
        self.budget_temp = 1048576
        self.budget_id = 'synthetic-only-not-qualified'

    def binding(self):
        self.calls.append('binding')
        return self._binding

    def qualify(self, binding, runtime, operation):
        self.calls.append('qualify')
        return self.qualified and binding == self._binding and runtime == db.runtime_facts()

    def clock(self):
        self.monotonic += 1
        return ClockSample(self.now, self.monotonic, self.process_id)

    def accept_initialization(self, binding):
        return self.accepted and binding == self._binding

    def bind_initialized(self, binding, main, lock):
        assert db.identity((binding.root/db.MAIN).stat()) == main
        assert db.identity((binding.root/db.LOCK).stat()) == lock
        self._binding = replace(binding, main_identity=main, lock_identity=lock)

    def approve_source(self, value):
        self.approved.add(c.digest(value))

    def observe_source(self, binding, version_bytes):
        self.calls.append('source')
        value = c.decode(version_bytes)
        scope = c.decode(binding.scope_bytes)
        eligible = self.source_available and c.digest(value) in self.approved
        return SourceObservation(c.digest(scope), c.digest(value), c.digest(value['provenance']),
                                 scope['policy_fingerprint'], value['validation']['verifier_fingerprint'],
                                 value['validation']['evidence_id'], self.now,
                                 'eligible' if eligible else 'unknown', self.safety)

    def authorize_read(self, binding, purpose, operation_id):
        self.calls.append('read')
        return self.readable and binding == self._binding

    def external_copies(self, binding):
        result = copy.deepcopy(self.copies)
        result['observed_at'] = self.now
        return result

    def accept_preview(self, binding, preview_bytes):
        self.calls.append('accept')
        if not self.accepted:
            raise RuntimeError('synthetic denied')
        preview = c.decode(preview_bytes)
        confirmation = {'contract_version': 'mg1-confirmation/v1', 'scope': preview['scope'],
                        'operation_id': preview['operation_id'], 'nonce': preview['nonce'],
                        'preview_digest': c.digest(preview), 'confirmed_at': self.now,
                        'expires_at': preview['expires_at'], 'host_evidence_id': 'synthetic-acceptance'}
        return AcceptedPreview(preview_bytes, c.canonical(confirmation))

    def committed_work_bytes(self, binding):
        return self.committed_bytes

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        total = sum(f['bytes'] for f in files)
        journal, temp, growth = total + 65536, self.budget_temp, self.budget_growth
        return {'qualification_id': self.budget_id, 'file_snapshot_digest': c.digest(files),
                'journal_bound_bytes': journal, 'temp_bound_bytes': temp, 'growth_bound_bytes': growth,
                'required_work_bytes': (journal + temp + growth + 4095)//4096*4096}


def seed_audit_items(host, count=257):
    """獨立 bulk fixture，只供 paging tests；不宣稱經過 host acceptance 的真實操作。

    用明確 SQL／標準 JSON recipe 建立相容版本、投影及 proof chain，避免每次分頁測試
    重跑數百次已另有覆蓋的 mutation。core 仍須獨立完整驗證讀回。
    """
    import hashlib
    import sqlite3
    value = version()
    host.approve_source(value)
    scope = c.decode(host.binding().scope_bytes)
    state = {'scope': scope, 'epoch': 1, 'reject_before': host.now, 'items': []}
    def digest_state():
        return hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    before = digest_state()
    projection_digest = c.digest(c.projection(value, 'active'))
    with sqlite3.connect(host.binding().root/db.MAIN) as connection:
        connection.execute('PRAGMA foreign_keys=ON')
        for number in range(1, count+1):
            item_id = f'00000000-0000-4000-8000-{number:012x}'
            operation_id = f'10000000-0000-4000-8000-{number:012x}'
            state['items'].append({'item_id': item_id, 'identity_epoch': 1, 'status': 'active',
                                   'current_revision': 1, 'revision_high_water': 1, 'erased_at': None,
                                   'versions': [{'revision': 1, 'version_digest': c.digest(value)}],
                                   'projection_digest': projection_digest})
            after = digest_state()
            proof = {'contract_version': 'mg1-operation-proof/v2', 'operation_id': operation_id, 'item_id': item_id,
                     'identity_epoch': 1, 'acceptance_epoch': 1, 'before_revision': 0, 'after_revision': 1,
                     'recorded_at': host.now, 'operation': 'add', 'preview_digest': c.digest({'synthetic-seed': number}),
                     'before_digest': before, 'after_digest': after, 'projection_digest': projection_digest,
                     'acceptance_evidence_id': 'synthetic-bulk-fixture', 'phase': 'complete',
                     'sanitization': 'not-requested', 'space_reclaim': 'not-requested',
                     'restore_source_revision': None, 'target_revisions': [], 'parent_operation_id': None,
                     'witness_kind': None, 'witness_digest': None,
                     'readback_basis': {'scope_digest': c.digest(scope), 'binding_digest': db.binding_digest(host.binding()),
                                        'copies_digest': c.digest({'coverage': 'unknown', 'copies': []}),
                                        'copies_observed_at': host.now, 'readback_until': host.now + 2592000}}
            connection.execute('INSERT INTO items VALUES (?,?,?,?,?,?)', (item_id,1,'active',1,1,None))
            connection.execute('INSERT INTO versions VALUES (?,?,?)', (item_id,1,c.canonical(value)))
            connection.executemany('INSERT INTO current_search VALUES (?,?,?,?)',
                                   [(item_id,1,cue,value['summary']) for cue in value['cues']])
            connection.execute('INSERT INTO proofs(operation_id,item_id,document) VALUES (?,?,?)',
                               (operation_id,item_id,c.canonical(proof)))
            before = after
