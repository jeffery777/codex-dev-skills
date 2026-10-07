"""Host-only durable objective evidence and pure projection, without dispatch.

Only independently trusted host code may inject the reader. It must retrieve
the actual immutable request, V2 classification, outcome/ownership/health and
authority bytes, not generate proof from worker assertions. Readers are bounded,
read-only and non-reentrant while the PacketStore lock is held. No JSON loader,
production adapter, retry journal or running-writer qualification is provided.
The projected owner represents a governance reservation, never process control.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
import pathlib

import agent_qualification as trust
import agent_routing
import model_failover
from model_packet_store import PacketError, PacketStore, canonical, digest, _id, _sha
from profile_preflight import TIER_RANK

LEDGER_VERSION = 5
MAX_RECORDS = 128
MAX_EVIDENCE = 262144
STAGES = ('internal', 'internal-best', 'official')
CAUSES = frozenset({'retriable-service', 'capability', 'unknown', 'unknown-write',
    'auth', 'permission', 'config', 'context', 'secret'})
PROHIBITED = frozenset({'auth', 'permission', 'config', 'context', 'secret'})
_WRITE_TOKEN = object()


class GovernanceError(PacketError):
    pass


@dataclass(frozen=True)
class HostEvidence:
    """Code-only provenance seam; construction alone establishes no authority."""
    request: bytes
    record: bytes
    classification: bytes
    authority: bytes


def _obj(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise GovernanceError('governance-schema-invalid')
    return value


def _int(value, maximum=10**12):
    if type(value) is not int or not 0 <= value <= maximum:
        raise GovernanceError('governance-integer-invalid')
    return value


def _text(value):
    if type(value) is not str or not value.strip() or len(value) > 1024:
        raise GovernanceError('governance-string-invalid')


def _parse(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_EVIDENCE:
        raise GovernanceError('governance-original-bytes-required')
    try:
        value = json.loads(raw, object_pairs_hook=trust._pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if canonical(value) != raw:
            raise ValueError()
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise GovernanceError('governance-bytes-invalid') from None


def _objective(value):
    _obj(value, 'repository task_id scope acceptance_sha256 authority_id')
    for key in ('repository', 'task_id', 'scope', 'authority_id'):
        _text(value[key])
    _sha(value['acceptance_sha256'])
    path = pathlib.Path(value['repository'])
    if not path.is_absolute() or str(path.resolve()) != value['repository']:
        raise GovernanceError('governance-repository-not-canonical')


def _policy(value):
    _obj(value, 'freshness_seconds service_attempt_limit service_elapsed_limit_seconds')
    for key, bound in [('freshness_seconds', 300), ('service_attempt_limit', 20),
                       ('service_elapsed_limit_seconds', 3600)]:
        if _int(value[key], bound) == 0:
            raise GovernanceError('governance-policy-invalid')


def _request(raw, classification_raw):
    request = _obj(_parse(raw), 'schema_version objective policy v2_task attempt_id generation target_id target_identity stage source_sha256')
    if type(request['schema_version']) is not int or request['schema_version'] != 1:
        raise GovernanceError('governance-request-version')
    _objective(request['objective']); _policy(request['policy'])
    _id(request['attempt_id']); _id(request['target_id']); _int(request['generation'], MAX_RECORDS)
    _sha(request['source_sha256'])
    if type(request['stage']) is not str or request['stage'] not in STAGES:
        raise GovernanceError('governance-stage-invalid')
    identity = _obj(request['target_identity'], 'provider_id provider_config_sha256 model runtime profile_sha256 context_policy_sha256 model_catalog_sha256 billing')
    _text(identity['provider_id']); _text(identity['model'])
    for key in ('provider_config_sha256', 'profile_sha256', 'context_policy_sha256', 'model_catalog_sha256'):
        _sha(identity[key])
    if identity['runtime'] not in ('cli', 'desktop') or identity['billing'] not in ('internal', 'chatgpt-subscription', 'api'):
        raise GovernanceError('governance-target-invalid')
    task = request['v2_task']
    if type(task) is not dict or not {'id', 'factors', 'workload_kind', 'qualification_scope'} <= set(task) or set(task) - {'id', 'factors', 'workload_kind', 'qualification_scope', 'quality_preference'}:
        raise GovernanceError('governance-v2-task-invalid')
    if task['id'] != request['objective']['task_id'] or task['qualification_scope'] != request['objective']['scope']:
        raise GovernanceError('governance-task-binding-drift')
    expected = agent_routing.classify_task(task['factors'], contract_version=2,
        workload_kind=task['workload_kind'], quality_preference=task.get('quality_preference'))
    classification = _parse(classification_raw)
    if canonical(classification) != canonical(expected):
        raise GovernanceError('governance-original-v2-classification-drift')
    return request, classification


def _authority(raw, binding, now, freshness):
    proof = _obj(_parse(raw), 'schema_version binding authorization_status qualification_status objective_status observed_at expires_at')
    if (type(proof['schema_version']) is not int or proof['schema_version'] != 1
            or canonical(proof['binding']) != canonical(binding)
            or proof['authorization_status'] != 'granted'
            or proof['qualification_status'] != 'qualified'
            or proof['objective_status'] != 'admitted'):
        raise GovernanceError('governance-authority-unavailable')
    _int(proof['observed_at']); _int(proof['expires_at'])
    if not 0 <= now - proof['observed_at'] <= freshness or not now < proof['expires_at'] <= proof['observed_at'] + freshness:
        raise GovernanceError('governance-authority-stale-or-future')


def _binding(store, ledger, operation_id):
    governance = ledger.get('governance')
    return {'packet_id': store.packet_id, 'identity_sha256': ledger['identity_sha256'],
        'operation_id': operation_id, 'revision': ledger['revision'], 'generation': ledger['generation'],
        'prefix_sha256': digest(canonical(governance['records'])) if governance else digest(canonical([])),
        'objective_sha256': digest(canonical(governance['objective'])) if governance else None,
        'policy_sha256': digest(canonical(governance['policy'])) if governance else None}


def _evidence(evidence, binding, committed_at, objective=None, policy=None):
    if type(evidence) is not HostEvidence:
        raise GovernanceError('governance-host-evidence-required')
    request, classification = _request(evidence.request, evidence.classification)
    record = _obj(_parse(evidence.record), 'schema_version binding request_sha256 classification_sha256 kind observed_at payload')
    if (type(record['schema_version']) is not int or record['schema_version'] != 1
            or canonical(record['binding']) != canonical(binding)
            or record['request_sha256'] != digest(evidence.request)
            or record['classification_sha256'] != digest(evidence.classification)):
        raise GovernanceError('governance-evidence-binding-drift')
    _int(record['observed_at']); _int(committed_at)
    if not 0 <= committed_at - record['observed_at'] <= request['policy']['freshness_seconds']:
        raise GovernanceError('governance-record-stale-or-future')
    if (objective is not None and canonical(request['objective']) != canonical(objective)
            or policy is not None and canonical(request['policy']) != canonical(policy)):
        raise GovernanceError('governance-objective-or-policy-drift')
    auth_binding = dict(binding, request_sha256=digest(evidence.request),
        record_sha256=digest(evidence.record), classification_sha256=digest(evidence.classification),
        objective_sha256=digest(canonical(request['objective'])), policy_sha256=digest(canonical(request['policy'])))
    _authority(evidence.authority, auth_binding, committed_at, request['policy']['freshness_seconds'])
    return {'request': request, 'record': record, 'classification': classification}


def validate_ledger(ledger, packet_id):
    """Strict v5 structure only; artifact/prefix replay is a separate obligation."""
    _obj(ledger, 'schema_version packet_id identity_sha256 revision generation attempts checkpoint supervisors integrations governance')
    if type(ledger['schema_version']) is not int or ledger['schema_version'] != LEDGER_VERSION or ledger['packet_id'] != packet_id:
        raise GovernanceError('governance-ledger-version')
    _sha(ledger['identity_sha256']); _int(ledger['revision'], MAX_RECORDS)
    if type(ledger['generation']) is not int or ledger['generation'] != 0:
        raise GovernanceError('governance-execution-unqualified')
    if ledger['attempts'] != [] or type(ledger['attempts']) is not list or ledger['checkpoint'] is not None or ledger['supervisors'] != {} or type(ledger['supervisors']) is not dict or ledger['integrations'] != {} or type(ledger['integrations']) is not dict:
        raise GovernanceError('governance-execution-unqualified')
    governance = _obj(ledger['governance'], 'schema_version objective policy records')
    if type(governance['schema_version']) is not int or governance['schema_version'] != 1:
        raise GovernanceError('governance-ledger-version')
    _objective(governance['objective']); _policy(governance['policy'])
    refs = governance['records']
    if type(refs) is not list or not 1 <= len(refs) <= MAX_RECORDS or ledger['revision'] != len(refs):
        raise GovernanceError('governance-prefix-invalid')
    seen = set()
    for ref in refs:
        _obj(ref, 'operation_id binding committed_at request_sha256 record_sha256 classification_sha256 authority_sha256')
        _id(ref['operation_id']); _int(ref['committed_at'])
        if ref['operation_id'] in seen:
            raise GovernanceError('governance-operation-duplicate')
        seen.add(ref['operation_id'])
        for key in ('request_sha256', 'record_sha256', 'classification_sha256', 'authority_sha256'):
            _sha(ref[key])
        binding = _obj(ref['binding'], 'packet_id identity_sha256 operation_id revision generation prefix_sha256 objective_sha256 policy_sha256')
        _int(binding['revision'], MAX_RECORDS); _int(binding['generation'], MAX_RECORDS)
        for key in ('identity_sha256', 'prefix_sha256'):
            _sha(binding[key])
        for key in ('objective_sha256', 'policy_sha256'):
            if binding[key] is not None:
                _sha(binding[key])


def project(prefix, *, now):
    """Pure projection of the entire validated prefix; no read, write or authority.

    Original outcome events remain untouched. Resolutions only overlay causes;
    healthy observations and cooldown expiry never reset budgets or reservations.
    """
    _int(now)
    state = {'owner': None, 'owner_epoch': 0, 'generation': 0,
        'stage_floor': 0, 'quality_stage_floor': 0, 'quality_tier_floors': {},
        'required_tier_floors': {}, 'quality_class': None,
        'events': [], 'resolved_causes': {}, 'cooldowns': {}, 'health': {},
        'blocked_reasons': [], 'last_observed_at': 0}
    outcomes = {}; requests = {}; last_commit = -1
    objective = policy = source = None
    for index, entry in enumerate(prefix):
        request, record, classification = (entry[key] for key in ('request', 'record', 'classification'))
        if index == 0:
            objective, policy = request['objective'], request['policy']
            source = request['source_sha256']
        if canonical(request['objective']) != canonical(objective) or canonical(request['policy']) != canonical(policy):
            raise GovernanceError('governance-objective-or-policy-drift')
        if request['source_sha256'] != source:
            raise GovernanceError('governance-source-head-conflict')
        when = record['observed_at']; _int(when)
        if when < state['last_observed_at'] or when > now:
            raise GovernanceError('governance-clock-rollback-or-future')
        commit = entry['committed_at']; _int(commit)
        if commit < last_commit or commit > now:
            raise GovernanceError('governance-clock-rollback-or-future')
        last_commit = commit
        state['last_observed_at'] = when
        kind, payload = record['kind'], record['payload']
        cls, tier = classification['capability_class'], classification['capability_tier']
        if index > 0 and cls != state['quality_class']:
            raise GovernanceError('governance-classification-objective-reassessment-required')
        stage = STAGES.index(request['stage'])
        target = digest(canonical(request['target_identity']))
        attempt = request['attempt_id']; generation = request['generation']
        owner_binding = {'attempt_id': attempt, 'generation': generation,
            'target_sha256': target, 'request_sha256': record['request_sha256']}
        if kind == 'admit':
            _obj(payload, '')
            if index != 0 or generation != 0:
                raise GovernanceError('governance-admission-invalid')
            state['quality_tier_floors'][classification['capability_class']] = classification['capability_tier']
            state['quality_class'] = classification['capability_class']
        elif index == 0:
            raise GovernanceError('governance-admission-missing')
        elif kind == 'acquire':
            _obj(payload, 'owner_id epoch')
            _id(payload['owner_id']); _int(payload['epoch'], MAX_RECORDS)
            floors = [state[key].get(cls) for key in ('required_tier_floors', 'quality_tier_floors')]
            floor = max((value for value in floors if value is not None), key=TIER_RANK.__getitem__, default=None)
            if state['owner'] is not None or generation != state['generation'] + 1 or payload['epoch'] != state['owner_epoch'] + 1 or attempt in requests:
                raise GovernanceError('governance-owner-conflict')
            if classification['capability_class'] != state['quality_class'] or stage < max(state['stage_floor'], state['quality_stage_floor']) or floor is not None and TIER_RANK[classification['capability_tier']] < TIER_RANK[floor]:
                raise GovernanceError('governance-floor-regression')
            if _blocking_causes(outcomes, state['resolved_causes']):
                raise GovernanceError('governance-cause-prohibits-owner')
            if state['health'].get(target, {}).get('status') in ('unknown', 'revoked', 'unavailable'):
                raise GovernanceError('governance-target-health-unavailable')
            if target in state['health'] and when - state['health'][target]['observed_at'] > policy['freshness_seconds']:
                raise GovernanceError('governance-target-health-stale')
            cooldown = state['cooldowns'].get(target)
            if cooldown is not None:
                raise GovernanceError('governance-cooldown-recheck-required')
            state['owner'] = dict(owner_binding, owner_id=payload['owner_id'], epoch=payload['epoch'])
            state['owner_epoch'] = payload['epoch']; state['generation'] = generation
            state['stage_floor'] = max(state['stage_floor'], stage)
            requests[attempt] = (copy.deepcopy(request), record['request_sha256'])
        elif kind in ('outcome', 'release'):
            original = requests.get(attempt)
            if original is None or canonical(original[0]) != canonical(request):
                raise GovernanceError('governance-original-request-drift')
            if state['owner'] is None or any(state['owner'][key] != owner_binding[key] for key in owner_binding):
                raise GovernanceError('governance-owner-binding-drift')
            if kind == 'release':
                _obj(payload, 'owner_id epoch runtime_state external_effects')
                _int(payload['epoch'], MAX_RECORDS)
                if payload['owner_id'] != state['owner']['owner_id'] or payload['epoch'] != state['owner_epoch'] or payload['runtime_state'] not in ('stopped', 'isolated') or payload['external_effects'] != 'excluded':
                    raise GovernanceError('governance-release-not-established')
                if attempt not in outcomes:
                    raise GovernanceError('governance-outcome-missing')
                state['owner'] = None
            else:
                _event(payload, request)
                if attempt in outcomes:
                    raise GovernanceError('governance-outcome-duplicate')
                if state['events'] and payload['observed_at'] < state['events'][-1]['observed_at'] or payload['observed_at'] > when:
                    raise GovernanceError('governance-event-time-drift')
                if payload['correction'] and not any(e['kind'] == 'quality' and e['target_id'] == payload['target_id'] for e in state['events']):
                    raise GovernanceError('governance-correction-without-baseline')
                outcomes[attempt] = copy.deepcopy(payload); state['events'].append(copy.deepcopy(payload))
        elif kind in ('resolve', 'quality-floor', 'cooldown'):
            event = outcomes.get(attempt)
            if event is None or (kind != 'quality-floor' and canonical(requests[attempt][0]) != canonical(request)):
                raise GovernanceError('governance-original-event-required')
            cause = state['resolved_causes'].get(attempt, event['cause'])
            if kind == 'resolve':
                _obj(payload, 'event_sha256 cause')
                if payload['event_sha256'] != digest(canonical(event)) or payload['cause'] not in CAUSES or payload['cause'] in ('unknown', 'unknown-write') or event['cause'] not in ('unknown', 'unknown-write') or attempt in state['resolved_causes']:
                    raise GovernanceError('governance-resolution-invalid')
                if event['kind'] == 'service' and payload['cause'] == 'capability' or event['kind'] == 'quality' and payload['cause'] == 'retriable-service':
                    raise GovernanceError('governance-resolution-kind-drift')
                state['resolved_causes'][attempt] = payload['cause']
            elif kind == 'quality-floor':
                _obj(payload, 'event_sha256 original_request_sha256 insufficient_stage')
                original = requests[attempt][0]
                stage_events = [e for e in state['events'] if e['target_id'] == event['target_id']]
                if (payload['event_sha256'] != digest(canonical(event)) or payload['original_request_sha256'] != requests[attempt][1]
                        or event['kind'] != 'quality' or cause != 'capability' or payload['insufficient_stage'] != original['stage']
                        or any(canonical(request[k]) != canonical(original[k]) for k in ('attempt_id', 'generation', 'target_identity', 'target_id', 'stage'))
                        or not model_failover._quality_exhausted(stage_events)):
                    raise GovernanceError('governance-quality-floor-unconfirmed')
                cls, tier = classification['capability_class'], classification['capability_tier']
                if cls != state['quality_class']:
                    raise GovernanceError('governance-classification-objective-reassessment-required')
                old = state['quality_tier_floors'].get(cls)
                if old is not None and TIER_RANK[tier] < TIER_RANK[old]:
                    raise GovernanceError('governance-floor-regression')
                state['quality_tier_floors'][cls] = tier
                state['quality_class'] = cls
                state['quality_stage_floor'] = max(state['quality_stage_floor'], stage + 1)
            else:
                _obj(payload, 'event_sha256 target_sha256 policy_sha256 cause start end')
                _int(payload['start']); _int(payload['end'])
                if (payload['event_sha256'] != digest(canonical(event)) or payload['target_sha256'] != target
                        or payload['policy_sha256'] != digest(canonical(policy)) or cause != 'retriable-service'
                        or payload['cause'] != cause or not event['observed_at'] <= payload['start'] <= when < payload['end']):
                    raise GovernanceError('governance-cooldown-unconfirmed')
                if target in state['cooldowns']:
                    raise GovernanceError('governance-cooldown-already-pending')
                state['cooldowns'][target] = copy.deepcopy(payload)
        elif kind == 'health':
            _obj(payload, 'status cooldown_sha256')
            if payload['status'] not in ('healthy', 'unavailable', 'unknown', 'revoked'):
                raise GovernanceError('governance-health-invalid')
            if payload['cooldown_sha256'] is not None:
                cooldown = state['cooldowns'].get(target)
                if cooldown is None or payload['cooldown_sha256'] != digest(canonical(cooldown)) or when < cooldown['end'] or payload['status'] != 'healthy' or _blocking_causes(outcomes, state['resolved_causes']):
                    raise GovernanceError('governance-cooldown-recheck-unconfirmed')
                del state['cooldowns'][target]
            if state['health'].get(target, {}).get('status') == 'revoked' and payload['status'] != 'revoked':
                raise GovernanceError('governance-health-revocation-sticky')
            state['health'][target] = dict(payload, observed_at=when)
        else:
            raise GovernanceError('governance-kind-invalid')
        # Retain every admitted V2 requirement from the full evidence prefix.
        # This floor is separate from confirmed quality insufficiency: a service
        # fallback can preserve a higher requirement without raising quality.
        required = state['required_tier_floors'].get(cls)
        if required is None or TIER_RANK[tier] > TIER_RANK[required]:
            state['required_tier_floors'][cls] = tier
    if not prefix:
        raise GovernanceError('governance-unavailable')
    state['blocked_reasons'] = _blocking_causes(outcomes, state['resolved_causes'])
    if any(h['status'] == 'revoked' for h in state['health'].values()):
        state['blocked_reasons'].append('revoked')
    state['service_failures'] = sum(e['kind'] == 'service' for e in state['events'])
    state['correction_rounds'] = sum(e['kind'] == 'quality' and e['correction'] for e in state['events'])
    state['quality_exhausted'] = model_failover._quality_exhausted(state['events'])
    effective = [dict(e, cause=state['resolved_causes'].get(e['attempt_id'], e['cause'])) for e in state['events']]
    state['service_exhausted'] = model_failover._service_exhausted(effective, policy, now)
    state['elapsed_seconds'] = now - state['events'][0]['observed_at'] if state['events'] else 0
    for cooldown in state['cooldowns'].values():
        cooldown['state'] = 'recheck-required' if now >= cooldown['end'] else 'cooling-down'
    return state


def _blocking_causes(outcomes, overlay):
    return sorted({overlay.get(attempt, event['cause']) for attempt, event in outcomes.items()
        if overlay.get(attempt, event['cause']) in PROHIBITED | {'unknown', 'unknown-write'}})


def _event(value, request):
    _obj(value, 'attempt_id task_id scope acceptance_sha256 target_id observed_at kind cause defect_id correction source_sha256 transition')
    for key in ('attempt_id', 'task_id', 'scope', 'target_id', 'defect_id'):
        _text(value[key])
    _sha(value['acceptance_sha256']); _sha(value['source_sha256']); _int(value['observed_at'])
    if (value['attempt_id'] != request['attempt_id'] or value['task_id'] != request['objective']['task_id']
            or value['scope'] != request['objective']['scope'] or value['acceptance_sha256'] != request['objective']['acceptance_sha256']
            or value['source_sha256'] != request['source_sha256']
            or value['target_id'] != request['target_id'] or type(value['correction']) is not bool
            or type(value['kind']) is not str or type(value['cause']) is not str
            or value['kind'] not in ('service', 'quality') or value['cause'] not in CAUSES
            or value['kind'] == 'service' and (value['correction'] or value['cause'] == 'capability')
            or value['kind'] == 'quality' and value['cause'] == 'retriable-service'):
        raise GovernanceError('governance-event-invalid')
    if value['transition'] is not None:
        transition = _obj(value['transition'], 'source_identity_sha256 reason observed_at evidence_sha256')
        _sha(transition['source_identity_sha256']); _sha(transition['evidence_sha256']); _int(transition['observed_at'])
        if transition['reason'] not in ('internal-unavailable', 'service-budget-exhausted', 'confirmed-capability-escalation'):
            raise GovernanceError('governance-transition-invalid')


class ObjectiveGovernance:
    """One existing protected packet; no replacement, migration or dispatch.

    The authority reader must enforce canonical objective identity/uniqueness
    independently across task aliases and packets. Neither task IDs nor this
    module can grant a new objective budget. A production reader is unavailable.
    """
    def __init__(self, store, reader):
        if type(store) is not PacketStore or not callable(getattr(reader, 'readback_evidence', None)) or not callable(getattr(reader, 'readback_authority', None)):
            raise GovernanceError('governance-host-reader-unavailable')
        self._store = store; self._reader = reader
        self._root = store.root; self._packet_id = store.packet_id

    def _ledger(self, fd):
        if self._store.root != self._root or self._store.packet_id != self._packet_id:
            raise GovernanceError('governance-store-binding-drift')
        return self._store._read(fd, _governance=True)

    def _prefix(self, fd, ledger):
        if not ledger or ledger['schema_version'] != LEDGER_VERSION:
            raise GovernanceError('governance-unavailable')
        validate_ledger(ledger, self._packet_id)
        governance = ledger['governance']; prefix = []; refs = []
        for index, ref in enumerate(governance['records']):
            partial = dict(ledger, revision=index, generation=0,
                governance=dict(governance, records=refs))
            if index == 0:
                partial.pop('governance')
            binding = _binding(self._store, partial, ref['operation_id'])
            if canonical(ref['binding']) != canonical(binding):
                raise GovernanceError('governance-prefix-binding-drift')
            raws = []
            for field in ('request', 'record', 'classification', 'authority'):
                raw = trust._read(fd, 'governance-' + ref[field + '_sha256'] + '.json', MAX_EVIDENCE)
                if digest(raw) != ref[field + '_sha256']:
                    raise GovernanceError('governance-artifact-drift')
                raws.append(raw)
            entry = _evidence(HostEvidence(*raws), binding, ref['committed_at'], governance['objective'], governance['policy'])
            entry['committed_at'] = ref['committed_at']; prefix.append(entry)
            project(prefix, now=ref['committed_at'])
            refs.append(ref)
        return prefix

    def _current_authority(self, ledger, now):
        binding = _binding(self._store, ledger, 'read')
        raw = self._reader.readback_authority(copy.deepcopy(binding))
        _authority(raw, binding, now, ledger['governance']['policy']['freshness_seconds'])

    def snapshot(self, *, now):
        _int(now)
        with self._store.locked() as fd:
            ledger = self._ledger(fd)
            prefix = self._prefix(fd, ledger)
            snapshot = project(prefix, now=now)
            self._current_authority(ledger, now)
            return copy.deepcopy(ledger), snapshot

    def admit(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, expected_revision=expected_revision, now=now, admission=True)

    def append(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, expected_revision=expected_revision, now=now, admission=False)

    def _append(self, operation_id, *, expected_revision, now, admission):
        _id(operation_id); _int(expected_revision, MAX_RECORDS); _int(now)
        with self._store.locked() as fd:
            ledger = self._ledger(fd)
            if ledger is None:
                raise GovernanceError('governance-packet-not-prepared')
            if ledger['schema_version'] == LEDGER_VERSION:
                prefix = self._prefix(fd, ledger)
                self._current_authority(ledger, now)
                project(prefix, now=now)
                prior = next((r for r in ledger['governance']['records'] if r['operation_id'] == operation_id), None)
                if prior is not None:
                    evidence = self._reader.readback_evidence(copy.deepcopy(prior['binding']))
                    if type(evidence) is not HostEvidence or any(digest(getattr(evidence, field)) != prior[field + '_sha256'] for field in ('request', 'record', 'classification', 'authority')):
                        raise GovernanceError('governance-operation-bytes-conflict')
                    return copy.deepcopy(ledger), project(prefix, now=now)
                if admission:
                    raise GovernanceError('governance-already-admitted')
            else:
                if not admission or ledger['schema_version'] != 2 or ledger['revision'] != 0 or ledger['generation'] != 0 or ledger['attempts'] or ledger['checkpoint'] is not None:
                    raise GovernanceError('governance-legacy-unavailable')
                prefix = []
            if ledger['revision'] != expected_revision:
                raise GovernanceError('governance-revision-conflict')
            if len(prefix) >= MAX_RECORDS:
                raise GovernanceError('governance-prefix-bound')
            binding = _binding(self._store, ledger, operation_id)
            evidence = self._reader.readback_evidence(copy.deepcopy(binding))
            governance = ledger.get('governance')
            entry = _evidence(evidence, binding, now,
                governance['objective'] if governance else None, governance['policy'] if governance else None)
            if (entry['record']['kind'] == 'admit') != admission:
                raise GovernanceError('governance-operation-kind-conflict')
            entry['committed_at'] = now
            snapshot = project(prefix + [entry], now=now)
            updated = copy.deepcopy(ledger)
            if admission:
                updated.update(schema_version=LEDGER_VERSION, supervisors={}, integrations={},
                    governance={'schema_version': 1, 'objective': entry['request']['objective'],
                        'policy': entry['request']['policy'], 'records': []})
            ref = {'operation_id': operation_id, 'binding': binding, 'committed_at': now}
            for field in ('request', 'record', 'classification', 'authority'):
                raw = getattr(evidence, field); sha = digest(raw)
                # Artifacts are fully durable before the sole ledger CAS pointer.
                self._store._immutable(fd, 'governance-' + sha + '.json', raw, _governance_token=_WRITE_TOKEN)
                ref[field + '_sha256'] = sha
            updated['governance']['records'].append(ref)
            updated['revision'] += 1
            validate_ledger(updated, self._packet_id)
            self._store._write(fd, updated, _governance_token=_WRITE_TOKEN)
            return copy.deepcopy(updated), snapshot
