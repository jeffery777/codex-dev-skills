#!/usr/bin/env python3
"""正式單專案 operator 入口；default-off，不自動接觸任何既有 memory。

本機讀寫需人類或已受使用者委派的 agent 當次接受、qualified storage、綁定
descriptor 與既有五操作核心。Actor 標籤本身不授權，agent 不冒充人工接受。
本入口不提供可注入的測試 confirmation，也不恢復持久 grant。
"""
from __future__ import annotations

import argparse
from contextlib import closing
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from memory_governance_host import RootBinding
from memory_governance_local import LocalClock, LocalHost, SingleRootRegistry
from memory_audit_adapter import SourceAcceptance
from memory_audit_source import ArtifactPermit, PinnedGitReader
import memory_maintenance_binding as b
from memory_maintenance_operator import OperatorTerminal
from memory_maintenance_authority import MaintenanceAuthorityProvider, intent
from memory_maintenance_dispatch import (MaintenanceDispatch, MaintenanceHostFactory,
    MaintenanceQualification, maintenance_environment)
from memory_maintenance import maintenance_report, reason

LOCAL_FILES = ('memory_maintenance_local.py', 'memory_maintenance_binding.py',
    'memory_maintenance_operator.py', 'memory_maintenance_qualification.py',
    'memory_maintenance_authority.py', 'memory_maintenance_dispatch.py',
    'memory_maintenance.py', 'memory_maintenance_preflight.py', 'governancectl.py',
    'memory_governance_contract.py', 'memory_governance_core.py',
    'memory_governance_host.py', 'memory_governance_storage.py', 'memory_governance_local.py',
    'memory_audit_adapter.py', 'memory_audit_source.py', 'memory_audit.py')


def fingerprint():
    return c.digest({name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                     for name in LOCAL_FILES})


def emit(value):
    print(c.canonical(value).decode(), flush=True)


def _absolute(value):
    path = Path(value)
    c.require(path.is_absolute() and '..' not in path.parts, 'unsafe-root')
    return path


def _load_proposal(path):
    fd = b.directory(path.parent, private=False)
    try:
        data, _ = b.read_file(fd, path.name, 20000)
        value = c.decode(data, 20000)
        c.fields(value, {'operation', 'item_id', 'candidate', 'restore_revision'})
        c.g1_operation(value['operation'])
        c.uuid(value['item_id'])
        # Host creates restore candidate from the actual retained content after accepted read scope.
        if value['operation'] == 'restore':
            c.require(value['candidate'] is None, 'unexpected-candidate')
            c.integer(value['restore_revision'], 1)
        else:
            intent(value)
        return value
    finally:
        os.close(fd)


def _read_versions(local, value):
    binding = local.binding
    scope, limits = c.decode(binding.scope_bytes), c.decode(binding.profile_bytes)
    with db.locked(binding), closing(db.connect(binding, limits)) as connection:
        connection.execute('BEGIN')
        snapshot = db.snapshot(connection, scope, limits)
        target = db.load_item(connection, value['item_id'], scope, limits)
        if value['operation'] == 'stop':
            return snapshot.digest, target, []
        # Current-only recall verification may match other active items sharing cues.
        rows = connection.execute("SELECT item_id FROM items WHERE status='active' ORDER BY item_id").fetchmany(17)
        c.require(len(rows) <= 16, 'source-review-limit')
        versions = [db.load_item(connection, row[0], scope, limits)['versions'][-1] for row in rows]
        if value['operation'] == 'resume' and target is not None:
            versions.append(target['versions'][-1])
        return snapshot.digest, target, versions


def _candidate(binding, value, target, now, verifier):
    operation = value['operation']
    if operation not in {'add', 'update', 'restore'}:
        return None
    if operation == 'restore':
        c.require(target is not None, 'item-unavailable')
        retained = next((v for v in target['versions'] if v['revision'] == value['restore_revision']), None)
        c.require(retained is not None, 'restore-source-unavailable')
        candidate = deepcopy(retained)
        candidate['revision'] = target['current_revision'] + 1
    else:
        candidate = deepcopy(value['candidate'])
    candidate.update(created_at=now, retired_at=None)
    candidate['validation'] = {'content_digest': c.content_digest(candidate),
        'evidence_id': 'review-' + uuid.uuid4().hex, 'verified_at': now,
        'verifier_fingerprint': verifier, 'policy_fingerprint': c.digest(c.POLICY),
        'eligibility': 'eligible'}
    c.validate_version(candidate, c.decode(binding.scope_bytes), c.decode(binding.profile_bytes), candidate=True)
    return candidate


def _review(local, versions, ui, clock, expires, check):
    versions = list({c.digest(v): v for v in versions}.values())
    permits = tuple({(p['source_id'], p['source_revision'], p['reference']['path'], p['source_digest']):
        ArtifactPermit(p['source_id'], p['source_revision'], p['reference']['path'], p['source_digest'])
        for v in versions for p in v['provenance']}.values())
    c.require(versions and len(versions) <= 17 and 1 <= len(permits) <= 16, 'source-review-limit')
    reader = PinnedGitReader(local.binding, local.repository, permits, check=check)
    accepted = []
    for version in versions:
        check()
        artifacts = []
        for source in version['provenance']:
            c.require(source['kind'] == 'repo-artifact', 'source-kind-unavailable')
            artifact = reader.read_artifact(local.binding, c.canonical(source))
            artifacts.append({'source_id': artifact.source_id, 'revision': artifact.source_revision,
                              'path': artifact.path, 'sha256': hashlib.sha256(artifact.content).hexdigest(),
                              'content_utf8': artifact.content.decode('utf-8')})
        review = {'contract_version': 'mg1-local-source-review/v1', 'scope': c.decode(local.binding.scope_bytes),
            'policy': c.POLICY, 'version': version, 'artifacts': artifacts,
            'decision': 'operator independently reviewed support, applicability and sensitivity as eligible and safe',
            'expires_at': expires}
        c.require(ui.accept('REVIEW', c.canonical(review)), 'source-not-accepted')
        check()
        reader.validate_disclosure()
        accepted.append(SourceAcceptance(c.digest(c.decode(local.binding.scope_bytes)), c.digest(version),
            c.digest(version['provenance']), c.digest(c.POLICY), version['validation']['verifier_fingerprint'],
            version['validation']['evidence_id'], 'eligible', 'safe', expires))
    return permits, tuple(accepted), reader


def run_operation(local, proposal, ui, *, on_dispatch=None):
    # Imported only by the enabled path; no arbitrary module names or caller loader.
    from memory_maintenance_qualification import LocalStorage
    clock = LocalClock()
    issued = clock.clock()
    expires = issued.utc_seconds + 300
    operation = proposal['operation']
    def check():
        ui.check()
        local.check(sources=operation != 'stop')
        sample = clock.clock()
        c.require(issued.utc_seconds <= sample.utc_seconds < expires
                  and issued.monotonic_ns <= sample.monotonic_ns
                  < issued.monotonic_ns + 300_000_000_000, 'expired-or-clock-changed')
        c.require(fingerprint() == local.binding.adapter_fingerprint, 'qualification-unavailable')
    check()
    state_digest, target, versions = _read_versions(local, proposal)
    candidate = _candidate(local.binding, proposal, target, issued.utc_seconds, fingerprint())
    value = {**proposal, 'candidate': candidate}
    intent(value)
    if candidate is not None:
        versions.append(candidate)
    if operation != 'stop':
        permits, accepted, source_reader = _review(local, versions, ui, clock, expires, check)
    else:
        permits, accepted, source_reader = (), (), None
    storage = LocalStorage(local.binding, check=check)
    environment = maintenance_environment(local.binding, db.runtime_facts(), operation)
    storage.verify_runtime(db.runtime_facts())
    qualification_view = {'contract_version': 'mg1-local-qualification/v1', 'scope': c.decode(local.binding.scope_bytes),
        'operation': operation, 'environment': environment, 'storage_evidence': storage.evidence(),
        'expires_at': expires, 'full_mg1_qualified': False}
    c.require(ui.accept('QUALIFY', c.canonical(qualification_view)), 'qualification-not-accepted')
    check()
    # Bind all review/preparation reads to one before-state; core takes its own snapshot afterward.
    with db.locked(local.binding), closing(db.connect(local.binding, c.decode(local.binding.profile_bytes))) as connection:
        c.require(db.snapshot(connection, c.decode(local.binding.scope_bytes), c.decode(local.binding.profile_bytes)).digest
                  == state_digest, 'state-conflict')
    provider = MaintenanceAuthorityProvider(binding=local.binding, clock=clock,
        accept_request=lambda binding, data: (check() is None and ui.accept('REQUEST', data)),
        accept_preview=lambda binding, data: ui.accept_preview(binding, data, clock),
        request_revoked=lambda _id: (check() is not None))
    try:
        request = provider.accept(value, lifetime_seconds=max(1, expires - clock.clock().utc_seconds))
        qualification = MaintenanceQualification(db.binding_digest(local.binding), operation,
            c.canonical(environment), ui.evidence_id, expires)
        def source_revoked(_id):
            check()
            if source_reader is not None:
                source_reader.validate_disclosure()
            return False
        factory = MaintenanceHostFactory(binding=local.binding, repository=local.repository,
            permits=permits, accepted_sources=accepted, qualification=qualification, provider=provider,
            source_revoked=source_revoked, qualification_revoked=lambda _id: (check() is not None), storage=storage)
        if on_dispatch is not None:
            on_dispatch()
        result = maintenance_report(enabled=True, dispatch=MaintenanceDispatch(factory, request))
        result.update(local_contract='mg1-local-operation/v1', local_entry_qualified=result['status'] == 'complete',
                      full_mg1_qualified=False)
        return result
    finally:
        provider.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('init', 'enable', 'disable', 'run'))
    parser.add_argument('--enabled', action='store_true')
    parser.add_argument('--actor', choices=('human', 'agent'), default='human',
                        help='操作者標籤；agent 需另有當前使用者委派，此 flag 不授權')
    parser.add_argument('--workspace')
    parser.add_argument('--repository')
    parser.add_argument('--repository-id')
    parser.add_argument('--proposal')
    args = parser.parse_args(argv)
    if not args.enabled:
        emit({'status': 'disabled', 'outcome': 'not-applied', 'write_performed': False})
        return 0
    progress = {'attempted': False}
    result = None
    def attempting():
        progress['attempted'] = True
    try:
        c.require(args.workspace is not None, 'scope-unavailable')
        workspace = _absolute(args.workspace)
        with OperatorTerminal(actor=args.actor) as ui:
            access = {'contract_version': 'mg1-local-inspection/v1', 'command': args.command,
                'workspace': str(workspace), 'repository': args.repository, 'proposal': args.proposal,
                'scope': 'this exact root metadata, selected item history, current active versions, fixed sources and proof/recall verification',
                'same_uid_trusted': True, 'fresh_process_acceptance': True,
                'acceptance_actor': args.actor}
            c.require(ui.accept('INSPECT', c.canonical(access)), 'request-not-accepted')
            if args.command == 'init':
                from memory_maintenance_qualification import initialize_local
                c.require(args.repository is not None and args.repository_id is not None
                          and args.proposal is None, 'scope-unavailable')
                result = initialize_local(workspace, _absolute(args.repository), args.repository_id, ui, fingerprint(),
                                          on_mutation_attempt=attempting)
            else:
                c.require(args.repository is None and args.repository_id is None, 'scope-unavailable')
                proposal = _load_proposal(_absolute(args.proposal)) if args.command == 'run' and args.proposal else None
                c.require((args.command == 'run') == (proposal is not None) and
                          (args.command == 'run' or args.proposal is None), 'scope-unavailable')
                local = b.load(workspace, fingerprint(), enabled=args.command == 'run',
                               sources=args.command == 'run' and proposal['operation'] != 'stop')
                if args.command == 'run':
                    result = run_operation(local, proposal, ui, on_dispatch=attempting)
                else:
                    desired = args.command == 'enable'
                    from memory_maintenance_qualification import LocalStorage
                    if desired:
                        LocalStorage(local.binding, check=lambda: local.check(enabled=False, sources=False)).verify_runtime(db.runtime_facts())
                    view = {'contract_version': 'mg1-local-activation/v1', 'binding': c.decode(local.data), 'enable': desired}
                    c.require(ui.accept(args.command.upper(), c.canonical(view)), 'request-not-accepted')
                    attempting()
                    b.set_enabled(local, desired)
                    b.load(workspace, fingerprint(), enabled=desired, sources=False)
                    result = {'status': 'enabled' if desired else 'disabled', 'outcome': 'applied', 'write_performed': True}
        try:
            result['acceptance_actor'] = args.actor
            emit(result)
        except Exception:
            # A lost sink cannot change or replay a returned mutation outcome.
            return 2
        return 0 if result['status'] in {'complete', 'initialized', 'enabled', 'disabled'} else 2
    except KeyboardInterrupt:
        # Mutation interrupted without a returned readback remains unknown.
        try:
            emit({**(result or {}), 'status': 'interrupted',
                  'outcome': result['outcome'] if result is not None else
                    ('unknown' if progress['attempted'] else 'not-applied'),
                  'acceptance_actor': args.actor,
                  'reason': 'interrupted', 'retry_allowed': False})
        except Exception:
            pass
        return 130
    except Exception as exc:
        try:
            emit({**(result or {}), 'status': 'unavailable',
                  'outcome': result['outcome'] if result is not None else
                    ('unknown' if progress['attempted'] else 'not-applied'),
                  'acceptance_actor': args.actor,
                  'reason': reason(exc), 'retry_allowed': False})
        except Exception:
            pass
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
