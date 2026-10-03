"""Bounded trusted-parent failover planning. No authorization or runtime proof.

This selector never probes, dispatches, reads credentials, or persists a ledger.
Its strict summaries must be supplied by an independently trusted parent; JSON
validation does not establish the authenticity of authorization or qualification.
Optional host-code guards can read the existing packet ledger and governance
authority for unused/historical sources and resolved unknown effects. No JSON
loader or production adapter is provided.
"""
from __future__ import annotations

import base64
import copy
from contextlib import nullcontext
import hashlib
import json
import re
import sys

from profile_preflight import TIER_RANK

SHA = re.compile(r'[0-9a-f]{64}')
MAX_BYTES = 262144
MAX_HISTORY_BYTES = 8 * MAX_BYTES


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


class UnusedSourceGuard:
    """Host-injected readback for the first, unavailable, never-used source.

    The host selects a real protected PacketStore and its expected packet identity.
    governance_reader.readback_unused_source(binding) must independently verify
    that packet's task/source binding and current authorization and revocation
    state; echoing input is not evidence. The callback must be bounded and
    non-reentrant: while the packet lock is held it must not launch a provider,
    perform writes, or call PacketStore. Only a planning snapshot is returned;
    an executor must revalidate its binding and claim the same packet before any
    dispatch. This code interface registers no production authority or adapter.
    """

    def __init__(self, store, governance_reader, *, packet_identity_sha256):
        from model_packet_store import PacketStore
        if type(store) is not PacketStore or not callable(getattr(governance_reader, 'readback_unused_source', None)):
            raise FailoverError('invalid-unused-source-guard')
        digest(packet_identity_sha256)
        self._store = store
        self._root = store.root
        self._packet_id = store.packet_id
        self._packet_identity = packet_identity_sha256
        self._reader = governance_reader

    def _readback(self, p, source, *, _snapshot=None):
        # Keep absence, a used packet, unknown outcomes and a busy ledger distinct
        # from a prepared empty ledger. None of these failures authorizes fallback.
        try:
            if self._store.root != self._root or self._store.packet_id != self._packet_id:
                return None
            with (self._store.locked() if _snapshot is None else nullcontext(_snapshot[0])) as fd:
                ledger = self._store._read(fd) if _snapshot is None else _snapshot[1]
                if (ledger is None or ledger['identity_sha256'] != self._packet_identity
                        or ledger['revision'] != 0 or ledger['generation'] != 0
                        or ledger['attempts'] or ledger['checkpoint'] is not None
                        or ledger.get('supervisors')):
                    return None
                binding = {'packet_id': self._packet_id,
                    'packet_identity_sha256': self._packet_identity,
                    'revision': ledger['revision'], 'generation': ledger['generation'],
                    'ledger_sha256': identity_digest(ledger), 'task': copy.deepcopy(p['task']),
                    'source_id': source['id'], 'source_identity_sha256': identity_digest(source['identity']),
                    'qualification_sha256': identity_digest(source['qualification']),
                    'qualification_evidence_sha256': source['qualification']['evidence_sha256'],
                    'authorization_sha256': identity_digest(p['authorization']),
                    'availability_sha256': identity_digest(source['availability'])}
                proof = copy.deepcopy(self._reader.readback_unused_source(copy.deepcopy(binding)))
                obj(proof, 'binding authorization_status qualification_status observed_at evidence_sha256')
                digest(proof['evidence_sha256'])
                if (type(proof['binding']) is not dict or proof['binding'] != binding
                        or identity_digest(proof['binding']) != identity_digest(binding)
                        or proof['authorization_status'] != 'granted'
                        or proof['qualification_status'] != 'qualified'
                        or not fresh(proof, p['now'], p['freshness_seconds'])):
                    return None
                return proof
        except Exception:
            # Callback, filesystem and ledger uncertainty all fail closed. Do not
            # expose host exception details or treat them as service failures.
            return None


class _V6UnusedSourceGuard:
    """Private journal capability; caller JSON cannot establish unused facts."""
    def __init__(self, prefix, proof_raw):
        from model_packet_lifecycle import _ValidatedUnusedPrefix
        if type(prefix) is not _ValidatedUnusedPrefix:
            raise FailoverError('invalid-v6-unused-prefix')
        prefix._check()
        self._prefix, self._raw = prefix, proof_raw
        self._store = prefix._store

    def _readback(self, p, source, destination, *, _snapshot=None):
        try:
            return self._prefix._proof(self._raw, p, source, destination, _snapshot)
        except Exception:
            return None


class ResolvedUnknownGuard:
    """Host-only advisory reconciliation of effects AND independently saved cause.

    readback_resolved_unknowns(binding) returns bounded canonical JSON bytes from
    an independent governance reader. It must read saved request/cause/effect
    records and current runtime or isolation evidence; echoing the binding is not
    proof. Callbacks are read-only, bounded, non-reentrant and must not call the
    store, export, reconcile, or dispatch. No JSON loader or adapter is registered.

    The snapshot binds the entire locked ledger and original event prefix. It is
    valid only for planning at that revision; a dispatcher must revalidate and
    archive the EXACT bytes before claiming a schema-3 dispatch. Historical
    readback requires a separate request-SHA-bound archive of those bytes.
    Initial source support is deliberately limited to a bounded immutable source
    artifact with a canonical manifest, independently retained by the host.
    Published recovery requires a descriptor-backed supervisor, its actual seal
    and checkpoint, and fresh stopped-runtime evidence. Legacy publications and
    any packet with source integrations remain unsupported and fail closed.
    """

    def __init__(self, store, governance_reader, *, packet_identity_sha256):
        from model_packet_store import PacketStore
        if type(store) is not PacketStore or not callable(getattr(governance_reader, 'readback_resolved_unknowns', None)):
            raise FailoverError('invalid-resolved-unknown-guard')
        digest(packet_identity_sha256)
        self._store = store
        self._root = store.root
        self._packet_id = store.packet_id
        self._packet_identity = packet_identity_sha256
        self._reader = governance_reader

    def _binding(self, p, ledger):
        return {'packet_id': self._packet_id, 'packet_identity_sha256': self._packet_identity,
            'revision': ledger['revision'], 'generation': ledger['generation'],
            'ledger_sha256': identity_digest(ledger), 'ledger': copy.deepcopy(ledger),
            'task': copy.deepcopy(p['task']), 'planning_sha256': identity_digest(p),
            'events_sha256': identity_digest(p['events']), 'targets_sha256': identity_digest(p['targets']),
            'current_target': p['current_target'], 'policy_sha256': identity_digest(p['policy']),
            'authorization_sha256': identity_digest(p['authorization']),
            'secret_check_sha256': identity_digest(p['secret_check'])}

    @staticmethod
    def _bytes(encoded):
        if type(encoded) is not str or len(encoded) > 2 * MAX_BYTES:
            raise FailoverError('resolved-artifact-bound')
        try:
            raw = base64.b64decode(encoded, validate=True)
        except ValueError:
            raise FailoverError('resolved-artifact-encoding') from None
        if len(raw) > MAX_BYTES:
            raise FailoverError('resolved-artifact-bound')
        return raw

    def _validate_proof(self, raw, p, ledger):
        """Pure validation, also used for pinned historical resolution bytes."""
        from model_packet_store import canonical
        proof = obj(parse_payload(raw), 'schema_version binding authorization_status qualification_status observed_at evidence_sha256 resolutions')
        binding = ResolvedUnknownGuard._binding(self, p, ledger)
        if (type(proof['schema_version']) is not int or proof['schema_version'] != 1
                or proof['binding'] != binding or identity_digest(proof['binding']) != identity_digest(binding)
                or proof['authorization_status'] != 'granted' or proof['qualification_status'] != 'qualified'
                or not fresh(proof, p['now'], p['freshness_seconds'])
                or raw != canonical(proof)):
            raise FailoverError('resolved-outcome-proof-unconfirmed')
        digest(proof['evidence_sha256'])
        if (ledger['packet_id'] != self._packet_id or ledger['identity_sha256'] != self._packet_identity
                or ledger.get('integrations') or len(ledger['attempts']) != len(p['events'])
                or ledger['generation'] != len(p['events'])
                or any(a['status'] not in {'checkpointed', 'quarantined'} for a in ledger['attempts'])):
            raise FailoverError('resolved-outcome-proof-unconfirmed')
        unknowns = []
        targets = {t['id']: t for t in p['targets']}
        for attempt, event in zip(ledger['attempts'], p['events']):
            if (attempt['id'] != event['attempt_id']
                    or attempt['target_sha256'] != identity_digest(targets[event['target_id']]['identity'])
                    or attempt['status'] == 'quarantined' and event['cause'] != 'unknown-write'):
                raise FailoverError('resolved-outcome-lineage-drift')
            if event['cause'] == 'unknown-write':
                unknowns.append((attempt, event))
        if type(proof['resolutions']) is not list or len(proof['resolutions']) != len(unknowns) or not unknowns:
            raise FailoverError('resolved-outcome-coverage-incomplete')
        effective = copy.deepcopy(p)
        for item, (attempt, event) in zip(proof['resolutions'], unknowns):
            obj(item, 'attempt_id request_sha256 target_sha256 event_sha256 request_bytes effect cause')
            if (any(item[key] != attempt[key] for key in ['request_sha256', 'target_sha256'])
                    or item['attempt_id'] != attempt['id'] or item['event_sha256'] != identity_digest(event)):
                raise FailoverError('resolved-outcome-lineage-drift')
            request_raw = ResolvedUnknownGuard._bytes(item['request_bytes'])
            request = parse_payload(request_raw)
            version = request.get('schema_version') if type(request) is dict else None
            obj(request, 'schema_version packet_id packet_identity_sha256 attempt_id generation target_id route_receipt failover_payload authority_contract'
                + (' prior_resolution_sha256' if version == 3 else ''))
            old = request['failover_payload']
            _validate(old, _defer_transitions=version == 3)
            if version == 3:
                digest(request['prior_resolution_sha256'])
            elif any(e['cause'] == 'unknown-write' for e in old['events']):
                raise FailoverError('resolved-original-resolution-archive-required')
            if (hashlib.sha256(request_raw).hexdigest() != attempt['request_sha256']
                    or type(request) is not dict or type(request.get('schema_version')) is not int
                    or request['schema_version'] not in {2, 3}
                    or request.get('packet_id') != self._packet_id
                    or request.get('packet_identity_sha256') != self._packet_identity
                    or request.get('attempt_id') != attempt['id']
                    or type(request.get('generation')) is not int or request['generation'] != attempt['generation']
                    or request.get('target_id') != event['target_id']
                    or request['route_receipt']['source_revision_sha256'] != event['source_sha256']
                    or any(old['task'][key] != p['task'][key] for key in ['id', 'scope', 'acceptance_sha256', 'capability_class'])
                    or old['events'] != p['events'][:attempt['generation']-1]
                    or identity_digest(old['events']) != identity_digest(p['events'][:attempt['generation']-1])):
                raise FailoverError('resolved-request-binding-drift')
            effect = obj(item['effect'], 'path status external_effects observed_at evidence_sha256 isolation runtime initial_source recovery_sha256')
            digest(effect['evidence_sha256']); digest(effect['recovery_sha256'])
            if (effect['status'] != 'resolved' or effect['external_effects'] != 'excluded'
                    or not fresh(effect, p['now'], p['freshness_seconds'])):
                raise FailoverError('resolved-outcome-effects-unconfirmed')
            if attempt['status'] == 'quarantined':
                isolation = obj(effect['isolation'], 'adapter_id proof source_isolated successor_isolated sealed_isolated')
                isolated = isolation['proof']
                expected = {'packet_id': self._packet_id, 'attempt_id': attempt['id'],
                    'generation': attempt['generation'], 'identity_sha256': self._packet_identity,
                    'target_sha256': attempt['target_sha256'], 'checkpoint_sha256': attempt['predecessor_sha256']}
                obj(isolated, 'packet_id attempt_id generation identity_sha256 target_sha256 checkpoint_sha256 schema_version status evidence_sha256 observed_at expires_at external_effects')
                digest(isolated['evidence_sha256']); integer(isolated['expires_at'])
                if (effect['path'] != 'quarantined' or effect['runtime'] is not None
                        or isolation['adapter_id'] != attempt['isolation_adapter']
                        or any(isolation[k] is not True for k in ['source_isolated', 'successor_isolated', 'sealed_isolated'])
                        or any(isolated[k] != value for k, value in expected.items())
                        or type(isolated['generation']) is not int
                        or type(isolated['schema_version']) is not int or isolated['schema_version'] != 1
                        or isolated['status'] != 'isolated' or isolated['external_effects'] != 'excluded'
                        or not fresh(isolated, p['now'], min(60, p['freshness_seconds']))
                        or not p['now'] < isolated['expires_at'] <= p['now']+60):
                    raise FailoverError('resolved-isolation-unconfirmed')
                if attempt['predecessor_sha256'] is not None:
                    if effect['initial_source'] is not None or effect['recovery_sha256'] != attempt['predecessor_sha256']:
                        raise FailoverError('resolved-recovery-drift')
                else:
                    initial = obj(effect['initial_source'], 'manifest_bytes source_bytes')
                    manifest_raw = ResolvedUnknownGuard._bytes(initial['manifest_bytes']); source_raw = ResolvedUnknownGuard._bytes(initial['source_bytes'])
                    obj(parse_payload(manifest_raw), 'schema_version packet_id identity_sha256 attempt_id request_sha256 target_sha256 source_sha256 content_sha256')
                    expected = {'schema_version': 1, 'packet_id': self._packet_id, 'identity_sha256': self._packet_identity,
                        'attempt_id': attempt['id'], 'request_sha256': attempt['request_sha256'],
                        'target_sha256': attempt['target_sha256'], 'source_sha256': event['source_sha256'],
                        'content_sha256': hashlib.sha256(source_raw).hexdigest()}
                    if (not source_raw or manifest_raw != canonical(expected)
                            or effect['recovery_sha256'] != hashlib.sha256(manifest_raw).hexdigest()):
                        raise FailoverError('resolved-initial-source-unconfirmed')
            else:
                record = ledger.get('supervisors', {}).get(attempt['id'])
                if (effect['path'] != 'published' or effect['initial_source'] is not None or effect['isolation'] is not None
                        or record is None or record['schema_version'] not in {3, 4} or record['stage'] != 'published'
                        or effect['recovery_sha256'] != attempt['checkpoint_sha256']):
                    raise FailoverError('resolved-published-proof-unconfirmed')
                runtime = obj(effect['runtime'], 'binding runtime_descriptor_sha256 runtime_identity_sha256 state external_effects observed_at expires_at evidence_sha256')
                digest(runtime['evidence_sha256']); integer(runtime['expires_at'])
                if (runtime['binding'] != record['binding'] or identity_digest(runtime['binding']) != identity_digest(record['binding'])
                        or runtime['runtime_descriptor_sha256'] != record['runtime_descriptor_sha256']
                        or runtime['runtime_identity_sha256'] != record['runtime_descriptor_sha256']
                        or runtime['state'] != 'stopped' or runtime['external_effects'] != 'excluded'
                        or not fresh(runtime, p['now'], min(60, p['freshness_seconds']))
                        or not p['now'] < runtime['expires_at'] <= p['now']+60
                        or record['binding']['source_sha256'] != event['source_sha256']
                        or record['binding']['scope_sha256'] != request['route_receipt']['assigned_scope_sha256']
                        or record['binding']['acceptance_sha256'] != p['task']['acceptance_sha256']):
                    raise FailoverError('resolved-runtime-unconfirmed')
            cause = obj(item['cause'], 'status kind cause observed_at evidence_sha256')
            digest(cause['evidence_sha256']); integer(cause['observed_at'])
            if (cause['status'] != 'confirmed' or cause['cause'] not in {'retriable-service', 'capability', 'auth', 'permission', 'config', 'context', 'secret'}):
                raise FailoverError('resolved-outcome-cause-unconfirmed')
            if (cause['kind'] != event['kind'] or not event['observed_at'] <= cause['observed_at'] <= p['now']
                    or cause['kind'] == 'quality' and cause['cause'] == 'retriable-service'
                    or cause['kind'] == 'service' and cause['cause'] == 'capability'):
                raise FailoverError('resolved-outcome-cause-conflict')
            effective['events'][attempt['generation']-1]['cause'] = cause['cause']
        _validate(effective)
        return proof, effective

    def _readback_locked(self, p, fd, ledger):
        from model_packet_store import canonical
        if ledger is None or ledger.get('integrations'):
            raise FailoverError('resolved-outcome-proof-unconfirmed')
        raw = self._reader.readback_resolved_unknowns(copy.deepcopy(self._binding(p, ledger)))
        proof, effective = self._validate_proof(raw, p, ledger)
        patch_bytes = 0
        for item in proof['resolutions']:
            attempt = next(a for a in ledger['attempts'] if a['id'] == item['attempt_id'])
            if attempt['status'] == 'quarantined':
                current = self._store._isolation_proof(ledger, attempt, attempt['isolation_adapter'])
                if identity_digest(current) != identity_digest(item['effect']['isolation']['proof']):
                    raise FailoverError('resolved-isolation-readback-drift')
                if attempt['predecessor_sha256'] is not None:
                    patch_bytes += len(self._store._checkpoint_bytes(fd, attempt['predecessor_sha256'], ledger))
            else:
                record = ledger['supervisors'][attempt['id']]
                descriptor = self._store._runtime_descriptor(fd, record)
                if hashlib.sha256(canonical(descriptor)).hexdigest() != record['runtime_descriptor_sha256']:
                    raise FailoverError('resolved-runtime-descriptor-drift')
                if record['schema_version'] == 4:
                    self._store._bootstrap_receipt(fd, record)
                sealed = self._store._sealed_bytes(fd, record)
                patch = self._store._checkpoint_bytes(fd, attempt['checkpoint_sha256'], ledger)
                manifest = {'packet_id': self._packet_id, 'identity_sha256': self._packet_identity,
                    'request_sha256': attempt['request_sha256'], 'target_sha256': attempt['target_sha256'],
                    'attempt_id': attempt['id'], 'patch_sha256': record['patch_sha256'],
                    'evidence_sha256': record['evidence_sha256'], 'predecessor_sha256': attempt['predecessor_sha256'],
                    'generation': attempt['generation']}
                if patch != sealed or hashlib.sha256(canonical(manifest)).hexdigest() != attempt['checkpoint_sha256']:
                    raise FailoverError('resolved-seal-checkpoint-drift')
                patch_bytes += len(patch)
            if patch_bytes > 8 * 1024 * 1024:
                raise FailoverError('resolved-artifact-bound')
        return proof, effective, hashlib.sha256(raw).hexdigest()


class HistoricalSourceGuard:
    """Authenticate original dispatches before a same-class tier increase.

    readback_historical_sources(binding) is a bounded, read-only, non-reentrant
    trusted host callback, called under the real PacketStore lock. It must read
    independently retained original request and authority-record bytes and
    complete outcome events, plus current authorization/revocation state. Never
    reconstruct either original from the new request/classification or accept a
    worker's claimed former tier.

    Each request is bounded JSON containing schema_version=2 or 3, packet_id,
    packet_identity_sha256, attempt_id, generation, target_id, route_receipt and
    failover_payload, plus authority_contract. Its exact bytes must match the
    original claim's request digest. Each separate authority record contains
    request_sha256 and that original authority_contract. The strict contract
    contains schema_version=1, authorization (the original effective summary),
    assigned_scope (literal normalized repository-relative paths, not workflow
    categories), and ownership (owner and disjoint=true). The full V2 route
    binds these fields and its original policy, classification and profile.
    Version 3 additionally pins prior_resolution_sha256, the digest of the exact
    valid-at-dispatch resolution bytes covering every unknown prefix event.
    original_resolutions is a parallel list of None (v2) or independent records
    {request_sha256, resolution_bytes}; a current proof cannot fill missing old
    evidence. There is no legacy artifact reconstruction or migration. At most
    128 entries and 2 MiB total request/authority/resolution bytes are accepted.
    Complete checkpoint patches are independently read
    back with an aggregate 8 MiB limit. Neither this interface nor its snapshot
    receipt registers or authorizes dispatch.
    """

    def __init__(self, store, governance_reader, *, packet_identity_sha256):
        from model_packet_store import PacketStore
        if type(store) is not PacketStore or not callable(getattr(governance_reader, 'readback_historical_sources', None)):
            raise FailoverError('invalid-historical-source-guard')
        digest(packet_identity_sha256)
        self._store = store
        self._root = store.root
        self._packet_id = store.packet_id
        self._packet_identity = packet_identity_sha256
        self._reader = governance_reader

    @staticmethod
    def _original_authority(request, archived_raw, attempt, old, route):
        import agent_routing
        contract = obj(request['authority_contract'], 'schema_version authorization assigned_scope ownership')
        if type(contract['schema_version']) is not int or contract['schema_version'] != 1:
            raise FailoverError('historical-authority-version')
        paths = contract['assigned_scope']; strings(paths)
        for path in paths:
            if (path != path.strip() or any(part in {'', '.', '..'} for part in path.split('/'))
                    or re.search(r'[\\:*?\[\]\x00-\x1f\x7f]', path)):
                raise FailoverError('historical-assigned-path-invalid')
        ownership = obj(contract['ownership'], 'owner disjoint')
        string(ownership['owner'])
        if (ownership['disjoint'] is not True or ownership['owner'] != ownership['owner'].strip()
                or re.search(r'[\x00-\x1f\x7f]', ownership['owner'])):
            raise FailoverError('historical-ownership-invalid')
        digest(route.get('authority_contract_sha256'))
        if (contract['authorization'] != old['authorization']
                or agent_routing._digest(contract['authorization']) != agent_routing._digest(old['authorization'])
                or paths != route['assigned_scope'] or ownership != route['ownership']
                or agent_routing._digest(ownership) != agent_routing._digest(route['ownership'])
                or agent_routing._digest(contract) != route['authority_contract_sha256']):
            raise FailoverError('historical-authority-contract-drift')
        archived = obj(parse_payload(archived_raw), 'request_sha256 authority_contract')
        digest(archived['request_sha256'])
        if (archived['request_sha256'] != attempt['request_sha256']
                or archived['authority_contract'] != contract
                or agent_routing._digest(archived['authority_contract']) != agent_routing._digest(contract)):
            raise FailoverError('historical-independent-authority-drift')

    def _original_dispatches(self, p, ledger, requests, original_authorities, original_resolutions):
        # A single forward replay; never call select_next or a host callback
        # recursively. Requirements come only from already validated originals.
        import agent_routing
        ids = [target['id'] for target in p['targets']]
        requirements = {}; receipts = []; previous_tier = -1
        for index, (attempt, raw, authority_raw) in enumerate(zip(ledger['attempts'], requests, original_authorities)):
            if hashlib.sha256(raw).hexdigest() != attempt['request_sha256']:
                raise FailoverError('historical-request-digest-drift')
            request = parse_payload(raw)
            version = request.get('schema_version') if type(request) is dict else None
            obj(request, 'schema_version packet_id packet_identity_sha256 attempt_id generation target_id route_receipt failover_payload authority_contract'
                + (' prior_resolution_sha256' if version == 3 else ''))
            if (type(version) is not int or version not in {2, 3}
                    or request['packet_id'] != self._packet_id or request['packet_identity_sha256'] != self._packet_identity
                    or request['attempt_id'] != attempt['id'] or type(request['generation']) is not int
                    or request['generation'] != attempt['generation']):
                raise FailoverError('historical-packet-binding-drift')
            old = request['failover_payload']; _validate(old, _defer_transitions=version == 3)
            decision = old
            resolution_proof = None
            archive = original_resolutions[index]
            if version == 3:
                digest(request['prior_resolution_sha256'])
                obj(archive, 'request_sha256 resolution_bytes')
                if (archive['request_sha256'] != attempt['request_sha256']
                        or hashlib.sha256(archive['resolution_bytes']).hexdigest() != request['prior_resolution_sha256']):
                    raise FailoverError('historical-resolution-archive-drift')
                saved = parse_payload(archive['resolution_bytes'])['binding']['ledger']
                expected = {k: copy.deepcopy(v) for k, v in ledger.items()
                            if k in {'schema_version', 'packet_id', 'identity_sha256'}}
                expected.update(schema_version=saved['schema_version'], revision=saved['revision'], generation=index,
                    attempts=copy.deepcopy(ledger['attempts'][:index]),
                    checkpoint=next((a['checkpoint_sha256'] for a in reversed(ledger['attempts'][:index]) if a['checkpoint_sha256']), None))
                if saved['schema_version'] >= 3:
                    expected['supervisors'] = {a['id']: ledger['supervisors'][a['id']] for a in ledger['attempts'][:index]
                                              if a['id'] in ledger.get('supervisors', {})}
                if saved['schema_version'] == 4:
                    expected['integrations'] = {}
                if (type(saved['schema_version']) is not int or saved['schema_version'] not in {2, 3, 4}
                        or type(saved['revision']) is not int or not 2*index <= saved['revision'] < ledger['revision']
                        or saved != expected or identity_digest(saved) != identity_digest(expected)):
                    raise FailoverError('historical-resolution-snapshot-drift')
                resolution_proof, decision = ResolvedUnknownGuard._validate_proof(self, archive['resolution_bytes'], old, saved)
            elif archive is not None:
                raise FailoverError('historical-unbound-resolution-archive')
            if ([target['id'] for target in old['targets']] != ids
                    or old['events'] != p['events'][:index]
                    or identity_digest(old['events']) != identity_digest(p['events'][:index])
                    or old['policy'] != p['policy']
                    or any(old['task'][key] != p['task'][key] for key in ['id', 'scope', 'acceptance_sha256', 'capability_class'])
                    or not previous_tier <= TIER_RANK[old['task']['capability_tier']] <= TIER_RANK[p['task']['capability_tier']]
                    or old['now'] > p['events'][index]['observed_at']
                    or _decision_precondition(decision, resolution_proof) is not None):
                raise FailoverError('historical-task-or-lineage-drift')
            target_index, _, _ = _candidate(decision)
            if target_index is None:
                raise FailoverError('historical-dispatch-not-planned')
            target = old['targets'][target_index]; q = target['qualification']; route = request['route_receipt']
            if (request['target_id'] != target['id'] or p['events'][index]['target_id'] != target['id']
                    or identity_digest(target['identity']) != attempt['target_sha256']
                    or target['identity'] != p['targets'][target_index]['identity']
                    or _destination_problem(old, target_index) is not None):
                raise FailoverError('historical-target-binding-drift')
            if (type(route) is not dict or type(route.get('contract_version')) is not int or route['contract_version'] != 2
                    or route.get('routing_policy_revision') not in agent_routing.SUPPORTED_ROUTING_POLICY_REVISIONS
                    or not agent_routing.validate_route_receipt(route)['valid']
                    or route['task_id'] != old['task']['id'] or route['execution_mode'] != 'custom-agent-profile'
                    or route['selected_profile_digest'] != target['identity']['profile_sha256']
                    or route['selected_capability_tier'] != q['capability_tier']
                    or route['source_revision_sha256'] != p['events'][index]['source_sha256']
                    or any(route['classification'][key] != old['task'][key] for key in ['capability_class', 'capability_tier'])):
                raise FailoverError('historical-classification-or-profile-drift')
            self._original_authority(request, authority_raw, attempt, old, route)
            traversed = {0, ids.index(old['current_target'])} | {ids.index(event['target_id']) for event in old['events']}
            for source_index in sorted(traversed):
                source = old['targets'][source_index]
                required = old['task']['capability_tier']
                prior = requirements.get(source['id'])
                if source_index != target_index and prior is not None and TIER_RANK[prior] < TIER_RANK[required]:
                    required = prior
                if ((prior is not None and source['identity'] != p['targets'][source_index]['identity'])
                        or _qualification_problem(old, source, required_tier=required) is not None):
                    raise FailoverError('historical-source-not-qualified')
            required = old['task']['capability_tier']
            previous_tier = TIER_RANK[required]
            requirements[target['id']] = required
            receipts.append({'attempt_id': attempt['id'], 'generation': attempt['generation'],
                'request_sha256': attempt['request_sha256'], 'target_sha256': attempt['target_sha256'],
                'required_tier': required, 'route_receipt_id': route['route_receipt_id'],
                'routing_policy_revision': route['routing_policy_revision'],
                'classification_sha256': identity_digest(route['classification']),
                'policy_sha256': identity_digest(old['policy']), 'qualification_sha256': identity_digest(q),
                'authority_contract_sha256': route['authority_contract_sha256'],
                'assigned_scope_sha256': route['assigned_scope_sha256'],
                'ownership_sha256': agent_routing._digest(route['ownership']),
                'profile_sha256': target['identity']['profile_sha256']})
            if version == 3:
                receipts[-1]['prior_resolution_sha256'] = request['prior_resolution_sha256']
        return requirements, receipts

    def _readback(self, p, sources, destination, *, _snapshot=None, _resolution=None):
        try:
            if self._store.root != self._root or self._store.packet_id != self._packet_id:
                return None
            with (self._store.locked() if _snapshot is None else nullcontext(_snapshot[0])) as fd:
                ledger = self._store._read(fd) if _snapshot is None else _snapshot[1]
                if (ledger is None or ledger['identity_sha256'] != self._packet_identity
                        or not ledger['attempts'] or len(ledger['attempts']) != len(p['events'])
                        or ledger.get('integrations')
                        or any(attempt['status'] != 'checkpointed' and not (_resolution is not None
                            and attempt['status'] == 'quarantined' and any(item['attempt_id'] == attempt['id']
                            for item in _resolution[0]['resolutions'])) for attempt in ledger['attempts'])
                        or [attempt['id'] for attempt in ledger['attempts']] != [event['attempt_id'] for event in p['events']]):
                    return None
                patch_bytes = 0
                for attempt in ledger['attempts']:
                    if attempt['checkpoint_sha256'] is not None:
                        patch_bytes += len(self._store._checkpoint_bytes(fd, attempt['checkpoint_sha256'], ledger))
                    if patch_bytes > 8 * 1024 * 1024:
                        return None
                binding = {'packet_id': self._packet_id, 'packet_identity_sha256': self._packet_identity,
                    'revision': ledger['revision'], 'generation': ledger['generation'],
                    'ledger_sha256': identity_digest(ledger), 'task': copy.deepcopy(p['task']),
                    'sources': list(sources), 'destination_id': p['targets'][destination]['id'],
                    'planning_sha256': identity_digest(p),
                    'events_sha256': identity_digest(p['events']), 'targets_sha256': identity_digest(p['targets']),
                    'policy_sha256': identity_digest(p['policy']), 'authorization_sha256': identity_digest(p['authorization']),
                    'secret_check_sha256': identity_digest(p['secret_check'])}
                proof = self._reader.readback_historical_sources(copy.deepcopy(binding))
                keys = 'binding authorization_status qualification_status observed_at evidence_sha256 events requests original_authorities'
                if type(proof) is dict and 'original_resolutions' in proof:
                    keys += ' original_resolutions'
                obj(proof, keys)
                requests = proof['requests']; authorities = proof['original_authorities']
                archives = proof.get('original_resolutions', [None] * len(ledger['attempts']))
                if type(archives) is not list or len(archives) != len(ledger['attempts']):
                    return None
                resolution_bytes = []
                for archive in archives:
                    if archive is not None:
                        obj(archive, 'request_sha256 resolution_bytes')
                        digest(archive['request_sha256'])
                        resolution_bytes.append(archive['resolution_bytes'])
                if (any(type(items) is not list or len(items) != len(ledger['attempts'])
                        for items in [requests, authorities])
                        or any(type(raw) is not bytes or len(raw) > MAX_BYTES for raw in requests + authorities + resolution_bytes)
                        or sum(len(raw) for raw in requests + authorities + resolution_bytes) > MAX_HISTORY_BYTES):
                    return None
                # Bound before copying, then validate the independent snapshot.
                # A retained callback object cannot rewrite checked bytes/events.
                proof = copy.deepcopy(proof)
                obj(proof, keys)
                digest(proof['evidence_sha256'])
                requests = proof['requests']; authorities = proof['original_authorities']
                if (any(type(items) is not list or len(items) != len(ledger['attempts'])
                        for items in [requests, authorities])
                        or any(type(raw) is not bytes or len(raw) > MAX_BYTES for raw in requests + authorities + resolution_bytes)
                        or sum(len(raw) for raw in requests + authorities + resolution_bytes) > MAX_HISTORY_BYTES
                        or type(proof['binding']) is not dict or proof['binding'] != binding
                        or identity_digest(proof['binding']) != identity_digest(binding)
                        or proof['authorization_status'] != 'granted' or proof['qualification_status'] != 'qualified'
                        or not fresh(proof, p['now'], p['freshness_seconds'])
                        or type(proof['events']) is not list or proof['events'] != p['events']
                        or identity_digest(proof['events']) != identity_digest(p['events'])):
                    return None
                requirements, receipts = self._original_dispatches(p, ledger, requests, authorities,
                    proof.get('original_resolutions', [None] * len(ledger['attempts'])))
                for source_id in sources:
                    required = requirements.get(source_id)
                    target = next(target for target in p['targets'] if target['id'] == source_id)
                    if (required is None or TIER_RANK[required] >= TIER_RANK[p['task']['capability_tier']]
                            or _qualification_problem(p, target, required_tier=required) is not None):
                        return None
                return {key: proof[key] for key in ['binding', 'authorization_status', 'qualification_status', 'observed_at', 'evidence_sha256']} | {
                    'source_requirements': {source_id: requirements[source_id] for source_id in sources},
                    'original_dispatches': receipts}
        except Exception:
            return None


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


def _validate(p, *, _defer_transitions=False):
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
            if not _defer_transitions and not (unavailable or service or quality):
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


def _precondition(p):
    task = p['task']; events = p['events']
    if not p['enabled']:
        return 'blocked', 'policy-disabled'
    if any(e['cause'] == 'unknown-write' for e in events):
        return 'blocked', 'write-outcome-readback-required'
    if events and events[-1]['cause'] in ['auth', 'permission', 'config', 'context', 'secret']:
        return 'blocked', 'non-fallback-failure'
    if events and events[-1]['cause'] == 'unknown':
        return 'diagnose', 'failure-cause-unknown'
    return _authorization_problem(p)


def _authorization_problem(p):
    task = p['task']
    auth = p['authorization']; secret = p['secret_check']
    for summary in [auth, secret]:
        if not fresh(summary, p['now'], p['freshness_seconds']) or any(summary[k] != task[v] for k, v in [('task_id', 'id'), ('scope', 'scope'), ('acceptance_sha256', 'acceptance_sha256')]):
            return 'blocked', 'stale-or-mismatched-authority-or-secret-check'
    if auth['status'] != 'granted' or secret['status'] != 'excluded':
        return 'blocked', 'authorization-or-secret-exclusion-missing'
    return None


def _decision_precondition(p, resolution_proof=None):
    """Apply the identical pure cause gate now and to original dispatch evidence.

    A later event cannot hide a prohibited resolved cause anywhere in the saved
    prefix. Historical replay supplies its pinned proof, never today's readback.
    """
    if problem := _precondition(p):
        return problem
    if resolution_proof is not None and any(item['cause']['cause'] in {'auth', 'permission', 'config', 'context', 'secret'}
                                            for item in resolution_proof['resolutions']):
        return 'blocked', 'non-fallback-failure'
    return None


def _qualification_problem(p, target, *, required_tier=None, check_fresh=True):
    task = p['task']; ident = target['identity']; q = target['qualification']
    required_tier = task['capability_tier'] if required_tier is None else required_tier
    if identity_digest(ident) not in p['authorization']['target_identity_sha256']:
        return 'target-not-authorized'
    if (q['status'] != 'qualified' or q['identity_sha256'] != identity_digest(ident)
            or task['scope'] not in q['scopes'] or q['capability_class'] != task['capability_class']
            or TIER_RANK[q['capability_tier']] < TIER_RANK[required_tier]
            or (q['capability_tier'] == 'exceptional' and required_tier != 'exceptional')
            or check_fresh and not fresh(q, p['now'], p['freshness_seconds'])):
        return 'target-not-qualified-for-task'
    return None


def _candidate(p):
    """Apply only the finite selection policy; this never establishes eligibility."""
    ids = [target['id'] for target in p['targets']]
    current = ids.index(p['current_target']); events = p['events']
    target_index = current; reason = 'internal-first' if not events else 'continue-current-stage'
    av = p['targets'][current]['availability']
    if not fresh(av, p['now'], p['freshness_seconds']):
        return None, 'blocked', 'availability-stale'
    if av['status'] == 'unavailable' and current < 2:
        target_index = 2; reason = 'internal-unavailable'
    elif events:
        latest = events[-1]
        stage_events = [e for e in events if e['target_id'] == ids[current]]
        if latest['kind'] == 'service':
            if latest['cause'] != 'retriable-service':
                return None, 'diagnose', 'service-reclassification-required'
            exhausted = _service_exhausted(stage_events, p['policy'], p['now'])
            if exhausted:
                if current == 2:
                    return None, 'blocked', 'official-service-budget-exhausted'
                target_index = 2; reason = 'service-budget-exhausted'
            else:
                reason = 'service-retry-within-budget'
        else:
            exhausted = _quality_exhausted(stage_events)
            if exhausted:
                if latest['cause'] != 'capability':
                    return None, 'diagnose', 'quality-reclassification-required'
                if current == 2:
                    return None, 'diagnose', 'official-quality-method-reset-required'
                target_index = current + 1; reason = 'confirmed-capability-escalation'
            else:
                reason = 'quality-correction-within-budget'
    return target_index, 'retry' if target_index == current and events else 'planned', reason


def _destination_problem(p, target_index):
    t = p['targets'][target_index]; ident = t['identity']; ctx = t['context']
    if target_index == 2 and (ident['billing'] != 'chatgpt-subscription' or ident['provider_id'] != 'openai'):
        return 'official-subscription-required'
    problem = _qualification_problem(p, t)
    if problem:
        return problem
    if t['availability']['status'] != 'available' or not fresh(t['availability'], p['now'], p['freshness_seconds']):
        return 'target-availability-unconfirmed'
    if t['executor']['status'] != 'public-supported' or not fresh(t['executor'], p['now'], p['freshness_seconds']):
        return 'public-executor-unavailable'
    if ctx['status'] != 'qualified' or not fresh(ctx, p['now'], p['freshness_seconds']):
        return 'target-context-unqualified'
    output = ctx['output_tokens'] + ctx['reasoning_tokens']
    total = ctx['input_tokens'] + output + ctx['margin_tokens']
    if not all(ctx[k] > 0 for k in ['input_limit', 'output_limit', 'total_limit', 'client_limit', 'margin_tokens', 'output_tokens']) or ctx['input_tokens'] > ctx['input_limit'] or output > ctx['output_limit'] or total > min(ctx['total_limit'], ctx['client_limit']):
        return 'target-context-budget-exceeded'
    return None


def select_next(payload, *, _trusted_unused_source_guard=None, _trusted_historical_source_guard=None,
                _trusted_resolved_unknown_guard=None, _trusted_locked_context=None,
                _trusted_v6_unused_source_guard=None):
    """Reuse one host-owned transaction; context is never loaded from JSON."""
    snapshot = None
    if _trusted_locked_context is not None:
        from model_packet_store import _PlanningContext
        if type(_trusted_locked_context) is not _PlanningContext:
            raise FailoverError('invalid-locked-planning-context')
        try:
            snapshot = _trusted_locked_context._snapshot()
            for guard in (_trusted_unused_source_guard, _trusted_historical_source_guard,
                          _trusted_resolved_unknown_guard, _trusted_v6_unused_source_guard):
                if guard is not None and getattr(guard, '_store', None) is not _trusted_locked_context._store:
                    raise FailoverError('locked-planning-store-mismatch')
        except Exception:
            raise FailoverError('locked-planning-context-unconfirmed') from None
    result = _select_next(payload,
        _trusted_unused_source_guard=_trusted_unused_source_guard,
        _trusted_historical_source_guard=_trusted_historical_source_guard,
        _trusted_resolved_unknown_guard=_trusted_resolved_unknown_guard,
        _trusted_v6_unused_source_guard=_trusted_v6_unused_source_guard, _snapshot=snapshot)
    if _trusted_locked_context is not None:
        try:
            _trusted_locked_context._snapshot()
        except Exception:
            raise FailoverError('locked-planning-context-unconfirmed') from None
    return result


def _select_next(payload, *, _trusted_unused_source_guard=None, _trusted_historical_source_guard=None,
                 _trusted_resolved_unknown_guard=None, _snapshot=None, _trusted_v6_unused_source_guard=None):
    """Validate trusted summaries and return a plan, never a dispatch receipt.

    Guard objects are host code, never JSON. Resolution and historical callbacks
    share ONE locked ledger; all snapshots are advisory and default off.
    """
    p = copy.deepcopy(payload)
    if _trusted_unused_source_guard is not None and _trusted_v6_unused_source_guard is not None:
        raise FailoverError('unused-source-modes-conflict')
    for guard, expected_type, error in [(_trusted_unused_source_guard, UnusedSourceGuard, 'invalid-unused-source-guard'),
            (_trusted_historical_source_guard, HistoricalSourceGuard, 'invalid-historical-source-guard'),
            (_trusted_resolved_unknown_guard, ResolvedUnknownGuard, 'invalid-resolved-unknown-guard'),
            (_trusted_v6_unused_source_guard, _V6UnusedSourceGuard, 'invalid-v6-unused-source-guard')]:
        if guard is not None and type(guard) is not expected_type:
            raise FailoverError(error)
    _validate(p, _defer_transitions=_trusted_resolved_unknown_guard is not None)
    kwargs = {'_trusted_unused_source_guard': _trusted_unused_source_guard,
              '_trusted_historical_source_guard': _trusted_historical_source_guard,
              '_trusted_v6_unused_source_guard': _trusted_v6_unused_source_guard}
    if not any(e['cause'] == 'unknown-write' for e in p['events']) or _trusted_resolved_unknown_guard is None:
        _validate(p)
        return _select_validated(p, **kwargs, _snapshot=_snapshot)
    guard = _trusted_resolved_unknown_guard
    try:
        if (guard._store.root != guard._root or guard._store.packet_id != guard._packet_id
                or _trusted_historical_source_guard is not None and
                (_trusted_historical_source_guard._store is not guard._store
                 or _trusted_historical_source_guard._packet_identity != guard._packet_identity)):
            raise FailoverError('resolved-guard-snapshot-mismatch')
        with (guard._store.locked() if _snapshot is None else nullcontext(_snapshot[0])) as fd:
            ledger = guard._store._read(fd) if _snapshot is None else _snapshot[1]
            proof, effective, sha = guard._readback_locked(p, fd, ledger)
            return _select_validated(p, **kwargs, _effective=effective,
                _resolution=(proof, sha), _snapshot=(fd, ledger))
    except Exception as exc:
        reason = str(exc) if isinstance(exc, FailoverError) and str(exc) in {
            'resolved-outcome-cause-unconfirmed', 'resolved-outcome-cause-conflict'} else 'resolved-outcome-proof-unconfirmed'
        return {'schema_version': 1, 'status': 'blocked', 'reason': reason, 'dispatched': False,
            'target': None, 'lineage_counts': {'service_failures': sum(e['kind'] == 'service' for e in p['events']),
                'correction_rounds': sum(e['kind'] == 'quality' and e['correction'] for e in p['events'])}}


def _select_validated(p, *, _trusted_unused_source_guard=None, _trusted_historical_source_guard=None,
                      _effective=None, _resolution=None, _snapshot=None, _trusted_v6_unused_source_guard=None):
    decision = p if _effective is None else _effective
    task = p['task']; ids = [t['id'] for t in p['targets']]
    events = p['events']; current = ids.index(p['current_target'])
    unused_source_proof = historical_source_proof = v6_unused_source_proof = None
    counts = {'service_failures': sum(e['kind'] == 'service' for e in events),
              'correction_rounds': sum(e['kind'] == 'quality' and e['correction'] for e in events)}

    def result(status, reason, target=None):
        output = {'schema_version': 1, 'status': status, 'reason': reason, 'dispatched': False,
                  'target': target, 'lineage_counts': counts}
        for key, proof in [('unused_source_proof', unused_source_proof), ('historical_source_proof', historical_source_proof),
                           ('v6_unused_source_proof', v6_unused_source_proof)]:
            if proof is not None and status in {'planned', 'retry'}:
                output[key] = copy.deepcopy(proof)
        if _resolution is not None and status in {'planned', 'retry'}:
            proof, sha = _resolution
            output['resolved_unknown_proof'] = {'resolution_sha256': sha,
                'binding': {k: v for k, v in proof['binding'].items() if k != 'ledger'},
                'evidence_sha256': proof['evidence_sha256'],
                'resolutions': [{'attempt_id': item['attempt_id'], 'event_sha256': item['event_sha256'],
                    'effect_sha256': identity_digest(item['effect']), 'cause_sha256': identity_digest(item['cause'])}
                    for item in proof['resolutions']]}
        return output

    if problem := _decision_precondition(decision, None if _resolution is None else _resolution[0]):
        return result(*problem)
    target_index, status, reason = _candidate(decision)

    # A prospective destination is not selected until every traversed source and
    # the destination itself pass. Only a source that will not be retried can use
    # historical requirements. No proof extends its current freshness/revocation.
    historical_sources = []
    traversed = {0, current} | {ids.index(e['target_id']) for e in events}
    for index in sorted(traversed):
        source = p['targets'][index]; q = source['qualification']; av = source['availability']
        problem = _qualification_problem(p, source)
        if problem is None:
            continue
        if (index == current == 0 and not events and _trusted_unused_source_guard is not None
                and q['observed_at'] <= p['now'] and not fresh(q, p['now'], p['freshness_seconds'])
                and av['status'] == 'unavailable' and fresh(av, p['now'], p['freshness_seconds'])
                and _qualification_problem(p, source, check_fresh=False) is None):
            unused_source_proof = _trusted_unused_source_guard._readback(p, source, _snapshot=_snapshot)
            if unused_source_proof is None:
                return result('blocked', 'unused-source-proof-unconfirmed')
        elif (index == 0 and target_index is not None and target_index != index
                and _trusted_v6_unused_source_guard is not None
                and q['observed_at'] <= p['now'] and not fresh(q, p['now'], p['freshness_seconds'])
                and av['status'] == 'unavailable' and fresh(av, p['now'], p['freshness_seconds'])
                and _qualification_problem(p, source, check_fresh=False) is None):
            v6_unused_source_proof = _trusted_v6_unused_source_guard._readback(p, source, target_index, _snapshot=_snapshot)
            if v6_unused_source_proof is None:
                return result('blocked', 'v6-unused-source-proof-unconfirmed')
        elif (target_index is not None and index != target_index and _trusted_historical_source_guard is not None
                and TIER_RANK[q['capability_tier']] < TIER_RANK[task['capability_tier']]
                and _qualification_problem(p, source, required_tier=q['capability_tier']) is None):
            historical_sources.append(source['id'])
        else:
            return result('blocked', problem)
    if target_index is None:
        return result(status, reason)
    if historical_sources:
        historical_source_proof = _trusted_historical_source_guard._readback(p, historical_sources, target_index,
            _snapshot=_snapshot, _resolution=_resolution)
        if historical_source_proof is None:
            return result('blocked', 'historical-source-proof-unconfirmed')
    if problem := _destination_problem(p, target_index):
        return result('blocked', problem)
    t = p['targets'][target_index]; ident = t['identity']; q = t['qualification']
    return result(status, reason,
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
