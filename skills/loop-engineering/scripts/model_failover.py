"""Bounded trusted-parent failover planning. No authorization or runtime proof.

This pure selector never probes, dispatches, reads credentials, or persists state.
Its strict summaries must be supplied by an independently trusted parent; JSON
validation does not establish the authenticity of authorization or qualification.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys

from profile_preflight import TIER_RANK

SHA = re.compile(r'[0-9a-f]{64}')
MAX_BYTES = 262144


class FailoverError(ValueError):
    pass


def obj(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise FailoverError('invalid-object-schema')
    return value


def string(value):
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise FailoverError('invalid-string')
    return value


def integer(value, maximum=10**12):
    if type(value) is not int or not 0 <= value <= maximum:
        raise FailoverError('invalid-integer')
    return value


def strings(value):
    if type(value) is not list or not 1 <= len(value) <= 64:
        raise FailoverError('invalid-string-list')
    for item in value:
        string(item)
    if len(set(value)) != len(value):
        raise FailoverError('duplicate-string')


def digest(value):
    if type(value) is not str or not SHA.fullmatch(value):
        raise FailoverError('invalid-digest')


def identity_digest(identity):
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fresh(summary, now, ttl):
    integer(summary['observed_at'])
    return 0 <= now - summary['observed_at'] <= ttl


def _quality_exhausted(events):
    quality = [e for e in events if e['kind'] == 'quality']
    same_core = any(e['correction'] and e['defect_id'] == prior['defect_id']
                    for n, e in enumerate(quality) for prior in quality[:n])
    return same_core or sum(e['correction'] for e in quality) >= 2


def _service_exhausted(events, policy, now):
    consecutive = []
    for e in reversed(events):
        if e['kind'] != 'service' or e['cause'] != 'retriable-service':
            break
        consecutive.append(e)
    return bool(consecutive) and (len(consecutive) >= policy['service_attempt_limit']
        or now - consecutive[-1]['observed_at'] >= policy['service_elapsed_limit_seconds'])


def _validate(p):
    obj(p, 'schema_version enabled now freshness_seconds task policy targets current_target events authorization secret_check')
    if type(p['schema_version']) is not int or p['schema_version'] != 1 or type(p['enabled']) is not bool:
        raise FailoverError('invalid-version-or-enable')
    integer(p['now']); integer(p['freshness_seconds'], 3600)
    if p['freshness_seconds'] == 0:
        raise FailoverError('invalid-freshness')
    task = obj(p['task'], 'id scope acceptance_sha256 capability_class capability_tier')
    for key in ['id', 'scope', 'capability_class', 'capability_tier']:
        string(task[key])
    digest(task['acceptance_sha256'])
    if task['capability_tier'] not in TIER_RANK:
        raise FailoverError('invalid-task-tier')
    policy = obj(p['policy'], 'service_attempt_limit service_elapsed_limit_seconds')
    for key, maximum in [('service_attempt_limit', 20), ('service_elapsed_limit_seconds', 3600)]:
        integer(policy[key], maximum)
        if policy[key] == 0:
            raise FailoverError('invalid-budget')
    if type(p['targets']) is not list or len(p['targets']) != 3:
        raise FailoverError('invalid-policy-chain')
    ids = []
    for index, t in enumerate(p['targets']):
        obj(t, 'id stage identity qualification availability executor context')
        string(t['id']); ids.append(t['id'])
        if t['stage'] != ['internal', 'internal-best', 'official'][index]:
            raise FailoverError('invalid-stage-order')
        ident = obj(t['identity'], 'provider_id provider_config_sha256 model runtime profile_sha256 context_policy_sha256 model_catalog_sha256 billing')
        for key in ['provider_id', 'model']:
            string(ident[key])
        if ident['runtime'] not in ['cli', 'desktop'] or type(ident['runtime']) is not str:
            raise FailoverError('invalid-runtime')
        for key in ['provider_config_sha256', 'profile_sha256', 'context_policy_sha256', 'model_catalog_sha256']:
            digest(ident[key])
        if type(ident['billing']) is not str or ident['billing'] not in ['internal', 'chatgpt-subscription', 'api']:
            raise FailoverError('invalid-billing')
        if index < 2 and ident['billing'] != 'internal':
            raise FailoverError('invalid-internal-billing')
        q = obj(t['qualification'], 'status identity_sha256 capability_class capability_tier scopes observed_at evidence_sha256')
        if type(q['status']) is not str or q['status'] not in ['qualified', 'unqualified', 'revoked']:
            raise FailoverError('invalid-qualification')
        for key in ['identity_sha256', 'evidence_sha256']:
            digest(q[key])
        for key in ['capability_class', 'capability_tier']:
            string(q[key])
        if q['capability_tier'] not in TIER_RANK:
            raise FailoverError('invalid-qualification-tier')
        strings(q['scopes']); integer(q['observed_at'])
        av = obj(t['availability'], 'status observed_at evidence_sha256')
        if type(av['status']) is not str or av['status'] not in ['available', 'unavailable', 'unknown']:
            raise FailoverError('invalid-availability')
        integer(av['observed_at']); digest(av['evidence_sha256'])
        ex = obj(t['executor'], 'status observed_at evidence_sha256')
        if type(ex['status']) is not str or ex['status'] not in ['public-supported', 'unsupported', 'unknown']:
            raise FailoverError('invalid-executor')
        integer(ex['observed_at']); digest(ex['evidence_sha256'])
        ctx = obj(t['context'], 'status observed_at evidence_sha256 input_tokens output_tokens reasoning_tokens margin_tokens input_limit output_limit total_limit client_limit')
        if type(ctx['status']) is not str or ctx['status'] not in ['qualified', 'unknown']:
            raise FailoverError('invalid-context-status')
        integer(ctx['observed_at']); digest(ctx['evidence_sha256'])
        for key in set(ctx) - {'status', 'observed_at', 'evidence_sha256'}:
            integer(ctx[key], 10**8)
    if len(set(ids)) != 3 or type(p['current_target']) is not str or p['current_target'] not in ids:
        raise FailoverError('invalid-current-target')
    auth = obj(p['authorization'], 'authority_ref status task_id scope acceptance_sha256 target_identity_sha256 observed_at')
    string(auth['authority_ref']); string(auth['task_id']); string(auth['scope']); digest(auth['acceptance_sha256'])
    if type(auth['status']) is not str or auth['status'] not in ['granted', 'revoked', 'unknown']:
        raise FailoverError('invalid-authority-summary')
    strings(auth['target_identity_sha256'])
    for item in auth['target_identity_sha256']:
        digest(item)
    integer(auth['observed_at'])
    secret = obj(p['secret_check'], 'status task_id scope acceptance_sha256 observed_at evidence_sha256')
    for key in ['task_id', 'scope']:
        string(secret[key])
    for key in ['acceptance_sha256', 'evidence_sha256']:
        digest(secret[key])
    integer(secret['observed_at'])
    if type(secret['status']) is not str or secret['status'] not in ['excluded', 'present', 'unknown']:
        raise FailoverError('invalid-secret-summary')
    if type(p['events']) is not list or len(p['events']) > 128:
        raise FailoverError('invalid-events')
    attempts = set(); previous_time = -1; previous_stage = 0
    for e in p['events']:
        obj(e, 'attempt_id task_id scope acceptance_sha256 target_id observed_at kind cause defect_id correction source_sha256 transition')
        for key in ['attempt_id', 'task_id', 'scope', 'target_id', 'defect_id']:
            string(e[key])
        digest(e['acceptance_sha256']); digest(e['source_sha256']); integer(e['observed_at'])
        if e['attempt_id'] in attempts or e['target_id'] not in ids:
            raise FailoverError('invalid-attempt-lineage')
        attempts.add(e['attempt_id'])
        stage = ids.index(e['target_id'])
        if stage < previous_stage or e['observed_at'] < previous_time or e['observed_at'] > p['now']:
            raise FailoverError('lineage-cycle-or-time')
        transition = e['transition']
        if transition is not None:
            obj(transition, 'source_identity_sha256 reason observed_at evidence_sha256')
            digest(transition['source_identity_sha256']); digest(transition['evidence_sha256'])
            integer(transition['observed_at'])
            if type(transition['reason']) is not str or transition['reason'] not in ['internal-unavailable', 'service-budget-exhausted', 'confirmed-capability-escalation']:
                raise FailoverError('invalid-transition-reason')
            if stage == previous_stage:
                raise FailoverError('transition-without-stage-change')
        if stage > previous_stage:
            if transition is None or transition['source_identity_sha256'] != identity_digest(p['targets'][previous_stage]['identity']) or not 0 <= e['observed_at'] - transition['observed_at'] <= p['freshness_seconds']:
                raise FailoverError('missing-or-drifted-transition-evidence')
            prior_events = [prior for prior in p['events'][:len(attempts)-1]
                            if prior['target_id'] == ids[previous_stage]]
            unavailable = stage == 2 and transition['reason'] == 'internal-unavailable'
            service = (stage == 2 and transition['reason'] == 'service-budget-exhausted'
                       and _service_exhausted(prior_events, policy, e['observed_at']))
            quality = (stage == previous_stage + 1 and transition['reason'] == 'confirmed-capability-escalation' and bool(prior_events)
                       and prior_events[-1]['kind'] == 'quality'
                       and prior_events[-1]['cause'] == 'capability'
                       and _quality_exhausted(prior_events))
            if not (unavailable or service or quality):
                raise FailoverError('unjustified-stage-transition')
        previous_stage = stage; previous_time = e['observed_at']
        if any(e[k] != task[v] for k, v in [('task_id', 'id'), ('scope', 'scope'), ('acceptance_sha256', 'acceptance_sha256')]):
            raise FailoverError('lineage-task-drift')
        if type(e['kind']) is not str or e['kind'] not in ['service', 'quality'] or type(e['correction']) is not bool:
            raise FailoverError('invalid-event-kind')
        if type(e['cause']) is not str or e['cause'] not in ['retriable-service', 'capability', 'unknown', 'auth', 'permission', 'config', 'context', 'secret', 'unknown-write']:
            raise FailoverError('invalid-cause')
        if e['kind'] == 'service' and (e['correction'] or e['cause'] == 'capability'):
            raise FailoverError('invalid-service-classification')
        if e['kind'] == 'quality' and e['cause'] == 'retriable-service':
            raise FailoverError('invalid-quality-classification')
        if e['kind'] == 'quality' and e['correction'] and not any(prior['kind'] == 'quality' and prior['target_id'] == e['target_id'] for prior in p['events'][:len(attempts)-1]):
            raise FailoverError('correction-without-stage-baseline')
    if p['events'] and p['events'][-1]['target_id'] != p['current_target']:
        raise FailoverError('current-lineage-drift')
    if not p['events'] and p['current_target'] != ids[0]:
        raise FailoverError('missing-stage-lineage')


def select_next(payload):
    """Validate trusted summaries and return a plan, never a dispatch receipt.

    Malformed input raises FailoverError. Well-formed unsafe input returns blocked.
    All timestamps are trusted-parent integer epoch seconds; limits are tokens.
    """
    _validate(payload)
    p = payload; task = p['task']; ids = [t['id'] for t in p['targets']]
    events = p['events']; current = ids.index(p['current_target'])
    counts = {'service_failures': sum(e['kind'] == 'service' for e in events),
              'correction_rounds': sum(e['kind'] == 'quality' and e['correction'] for e in events)}

    def result(status, reason, target=None):
        return {'schema_version': 1, 'status': status, 'reason': reason, 'dispatched': False,
                'target': target, 'lineage_counts': counts}

    def blocked(reason):
        return result('blocked', reason)

    if not p['enabled']:
        return blocked('policy-disabled')
    if any(e['cause'] == 'unknown-write' for e in events):
        return blocked('write-outcome-readback-required')
    if events and events[-1]['cause'] in ['auth', 'permission', 'config', 'context', 'secret']:
        return blocked('non-fallback-failure')
    if events and events[-1]['cause'] == 'unknown':
        return result('diagnose', 'failure-cause-unknown')
    auth = p['authorization']; secret = p['secret_check']
    for summary in [auth, secret]:
        if not fresh(summary, p['now'], p['freshness_seconds']) or any(summary[k] != task[v] for k, v in [('task_id', 'id'), ('scope', 'scope'), ('acceptance_sha256', 'acceptance_sha256')]):
            return blocked('stale-or-mismatched-authority-or-secret-check')
    if auth['status'] != 'granted' or secret['status'] != 'excluded':
        return blocked('authorization-or-secret-exclusion-missing')
    def eligible(t):
        ident = t['identity']; q = t['qualification']
        if identity_digest(ident) not in auth['target_identity_sha256']:
            return 'target-not-authorized'
        if (q['status'] != 'qualified' or q['identity_sha256'] != identity_digest(ident)
            or not fresh(q, p['now'], p['freshness_seconds']) or task['scope'] not in q['scopes']
            or q['capability_class'] != task['capability_class']
            or TIER_RANK[q['capability_tier']] < TIER_RANK[task['capability_tier']]
            or (q['capability_tier'] == 'exceptional' and task['capability_tier'] != 'exceptional')):
            return 'target-not-qualified-for-task'
        return None

    # Revocation or drift is not a retriable service failure. Check every source
    # stage already traversed before allowing another selection or retry.
    traversed = {0, current} | {ids.index(e['target_id']) for e in events}
    for index in sorted(traversed):
        problem = eligible(p['targets'][index])
        if problem:
            return blocked(problem)
    target_index = current; reason = 'internal-first' if not events else 'continue-current-stage'
    av = p['targets'][current]['availability']
    if not fresh(av, p['now'], p['freshness_seconds']):
        return blocked('availability-stale')
    if av['status'] == 'unavailable' and current < 2:
        target_index = 2; reason = 'internal-unavailable'
    elif events:
        latest = events[-1]
        stage_events = [e for e in events if e['target_id'] == ids[current]]
        if latest['kind'] == 'service':
            if latest['cause'] != 'retriable-service':
                return result('diagnose', 'service-reclassification-required')
            exhausted = _service_exhausted(stage_events, p['policy'], p['now'])
            if exhausted:
                if current == 2:
                    return blocked('official-service-budget-exhausted')
                target_index = 2; reason = 'service-budget-exhausted'
            else:
                reason = 'service-retry-within-budget'
        else:
            exhausted = _quality_exhausted(stage_events)
            if exhausted:
                if latest['cause'] != 'capability':
                    return result('diagnose', 'quality-reclassification-required')
                if current == 2:
                    return result('diagnose', 'official-quality-method-reset-required')
                target_index = current + 1; reason = 'confirmed-capability-escalation'
            else:
                reason = 'quality-correction-within-budget'
    t = p['targets'][target_index]; ident = t['identity']; q = t['qualification']; ctx = t['context']
    if target_index == 2 and (ident['billing'] != 'chatgpt-subscription' or ident['provider_id'] != 'openai'):
        return blocked('official-subscription-required')
    problem = eligible(t)
    if problem:
        return blocked(problem)
    if t['availability']['status'] != 'available' or not fresh(t['availability'], p['now'], p['freshness_seconds']):
        return blocked('target-availability-unconfirmed')
    if t['executor']['status'] != 'public-supported' or not fresh(t['executor'], p['now'], p['freshness_seconds']):
        return blocked('public-executor-unavailable')
    if ctx['status'] != 'qualified' or not fresh(ctx, p['now'], p['freshness_seconds']):
        return blocked('target-context-unqualified')
    output = ctx['output_tokens'] + ctx['reasoning_tokens']
    total = ctx['input_tokens'] + output + ctx['margin_tokens']
    if not all(ctx[k] > 0 for k in ['input_limit', 'output_limit', 'total_limit', 'client_limit', 'margin_tokens', 'output_tokens']) or ctx['input_tokens'] > ctx['input_limit'] or output > ctx['output_limit'] or total > min(ctx['total_limit'], ctx['client_limit']):
        return blocked('target-context-budget-exceeded')
    return result('retry' if target_index == current and events else 'planned', reason,
                  {'id': t['id'], 'stage': t['stage'], 'identity': dict(ident), 'qualification_evidence_sha256': q['evidence_sha256']})


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise FailoverError('duplicate-json-key')
        value[key] = item
    return value


def parse_payload(raw):
    """Decode bounded UTF-8 JSON with duplicate and nonfinite rejection."""
    if type(raw) is not bytes:
        raise FailoverError('input-must-be-bytes')
    if len(raw) > MAX_BYTES:
        raise FailoverError('input-too-large')
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(FailoverError('nonfinite-json')))
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, FailoverError):
            raise
        raise FailoverError('invalid-json') from None


def main():
    try:
        output = select_next(parse_payload(sys.stdin.buffer.read(MAX_BYTES + 1)))
        code = 0 if output['status'] in ['planned', 'retry'] else 1
    except (ValueError, UnicodeError, RecursionError) as exc:
        output = {'schema_version': 1, 'status': 'blocked', 'dispatched': False, 'reason': str(exc) if isinstance(exc, FailoverError) else 'invalid-json'}
        code = 1
    print(json.dumps(output, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
