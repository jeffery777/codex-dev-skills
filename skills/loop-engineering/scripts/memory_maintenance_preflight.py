"""Advisory operation-specific preflight 與需新接受的 isolated canary。"""
from __future__ import annotations

import memory_governance_contract as c
import memory_governance_storage as db
from memory_audit_adapter import SourceAcceptance
from memory_audit_source import PinnedGitReader
from memory_maintenance import maintenance_report, reason
from memory_maintenance_authority import MaintenanceRequest, intent
from memory_maintenance_dispatch import MaintenanceHostFactory, maintenance_environment


def preflight_report(*, enabled=False, factory=None, request=None, inspection_allowed=None):
    result = {'status': 'disabled', 'advisory_only': True, 'operation_authorized': False,
              'production_qualified': False, 'checks': []}
    if enabled is not True:
        return result
    def check(name, action):
        try:
            c.require(action() is True, name + '-unavailable')
            result['checks'].append({'name': name, 'status': 'pass'})
            return True
        except Exception as exc:
            result['checks'].append({'name': name, 'status': 'unavailable', 'reason': reason(exc)})
            return False
    if not check('host', lambda: type(factory) is MaintenanceHostFactory and type(request) is MaintenanceRequest):
        result['status'] = 'unavailable'
        return result
    if not check('inspection', lambda: inspection_allowed is not None
                 and inspection_allowed(factory.binding, request) is True):
        result['status'] = 'unavailable'
        return result
    try:
        value = intent(c.decode(request.intent_bytes, 20000))
        result['operation'] = value['operation']
        scope = c.decode(factory.binding.scope_bytes)
        check('scope', lambda: request.scope_digest == c.digest(scope) and request.principal_id == scope['principal_id'])
        def pending():
            factory.provider.pending(request)
            return True
        check('request', pending)
        def qualification():
            q = factory.qualification
            c.require(q.operation == value['operation'] and q.binding_digest == db.binding_digest(factory.binding)
                      and q.environment_bytes == c.canonical(maintenance_environment(factory.binding, db.runtime_facts(), q.operation))
                      and q.expires_at > factory.provider.clock.clock().utc_seconds
                      and factory.qualification_revoked(q.evidence_id) is False, 'qualification-unavailable')
            return True
        check('qualification', qualification)
        check('storage-port', lambda: callable(getattr(factory.storage, 'committed_work_bytes', None))
              and callable(getattr(factory.storage, 'work_budget', None)))
        def sources():
            # Stop remains possible when content source has been revoked; it adopts no content.
            if value['operation'] == 'stop':
                return True
            c.require(bool(factory.accepted_sources) and all(type(entry) is SourceAcceptance
                      and entry.expires_at > factory.provider.clock.clock().utc_seconds
                      and factory.source_revoked(entry.evidence_id) is False
                      and entry.safety == 'safe' and entry.eligibility == 'eligible'
                      for entry in factory.accepted_sources), 'source-unavailable')
            if value['candidate'] is not None:
                candidate = value['candidate']
                c.require(any(entry.version_digest == c.digest(candidate)
                              and entry.scope_digest == c.digest(scope)
                              and entry.provenance_digest == c.digest(candidate['provenance'])
                              and entry.policy_fingerprint == c.digest(c.POLICY)
                              and entry.verifier_fingerprint == candidate['validation']['verifier_fingerprint']
                              and entry.evidence_id == candidate['validation']['evidence_id']
                              for entry in factory.accepted_sources), 'source-unavailable')
            PinnedGitReader(factory.binding, factory.repository, factory.permits, check=lambda: factory.provider.pending(request))
            return True
        check('sources', sources)
        check('confirmation-port', lambda: callable(factory.provider.accept_preview))
        # No database read or mutation. Canonical preview does actual state/source/capacity validation.
    except Exception as exc:
        result['checks'].append({'name': 'intent', 'status': 'unavailable', 'reason': reason(exc)})
    result['status'] = 'advisory-pass' if all(row['status'] == 'pass' for row in result['checks']) else 'unavailable'
    return result


def canary_report(*, enabled=False, dispatch=None, isolation_accepted=None):
    if enabled is not True:
        return {'status': 'disabled', 'production_qualified': False}
    try:
        c.require(isolation_accepted is not None and isolation_accepted(dispatch) is True,
                  'isolation-unavailable')
    except Exception:
        return {'status': 'unavailable', 'reason': 'isolation-unavailable', 'production_qualified': False}
    result = maintenance_report(enabled=True, dispatch=dispatch)
    return {'status': 'canary-pass' if result['status'] == 'complete' else 'unavailable',
            'production_qualified': False, 'result': result}
