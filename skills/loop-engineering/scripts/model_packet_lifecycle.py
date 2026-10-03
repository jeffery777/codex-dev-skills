"""Host-only synthetic v6 lifecycle; no production loader or adapter.

One journal owns governance and actual attempts. Readers and backends are
independently injected trusted host code, bounded and non-reentrant. No model
JSON can select them. Independent readback and replay-bound capabilities allow
schema 2 unused-source TTL and schema 3 original historical-tier exceptions,
within this synthetic host only; production qualification remains unavailable.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import agent_qualification as trust
import agent_routing
import model_packet_governance as governance
import model_packet_store as packets
import model_failover as failover
from model_packet_supervisor import validate_patch

VERSION = 6
_WRITE_TOKEN = object()
_PREFIX_TOKEN = object()
EXECUTION_FIELDS = ('schema_version binding governance_request_sha256 attempt_id generation '
    'predecessor_sha256 target_id target_identity failover_payload host_id backend_id runtime_policy_sha256 runtime_id')
MAX_HISTORICAL_ACQUIRE_BYTES = 8 * 1024 * 1024
FIELDS = ('request', 'record', 'classification', 'authority', 'execution', 'runtime')
KINDS = frozenset({'admit', 'acquire', 'outcome', 'resolve', 'quality-floor',
    'cooldown', 'health', 'launch-intent', 'observe', 'export-intent', 'publish', 'finish'})
GATED_KINDS = frozenset({'acquire', 'launch-intent', 'export-intent', 'publish', 'finish'})
GOVERNANCE_KINDS = frozenset({'admit', 'acquire', 'outcome', 'resolve', 'quality-floor', 'cooldown', 'health'})
PREPARED_KINDS = frozenset({'admit-prepared', 'acquire', 'prepare-intent', 'prepared'})
BOOTSTRAP_FIXTURE_KINDS = frozenset({'admit-bootstrap-fixture', 'acquire',
    'prepare-intent', 'prepared', 'bootstrap-intent', 'bootstrapped'})


class LifecycleError(packets.PacketError):
    pass


@dataclass(frozen=True)
class HostEvidence:
    request: bytes
    record: bytes
    classification: bytes
    authority: bytes
    execution: bytes | None = None
    runtime: bytes | None = None


@dataclass(frozen=True)
class _ValidatedUnusedPrefix:
    """Private replay facts, never a replacement for the actual held ledger.

    Minted before one acquire during forward replay. The fence still reads the
    entire real ledger, including later records when validating old evidence.
    This code capability is synthetic host trust, not an OS authorization token.
    """
    _issuer: object
    _fence: object
    _prefix_raw: bytes
    _source_raw: bytes
    _executions: tuple
    _owner: object
    _execution_raw: bytes
    _decision_raw: bytes

    @property
    def _store(self):
        return self._fence._store

    def _check(self):
        if self._issuer is not _PREFIX_TOKEN or self._owner is not None:
            raise LifecycleError('lifecycle-unused-prefix-unavailable')
        fd, actual = self._fence._snapshot()
        refs = governance._parse(self._prefix_raw)
        if (actual['schema_version'] != VERSION or not refs
                or packets.canonical(actual['governance']['records'][:len(refs)]) != self._prefix_raw
                or len(self._executions) != sum(ref['kind'] == 'acquire' for ref in refs)):
            raise LifecycleError('lifecycle-unused-prefix-drift')
        source = governance._parse(self._source_raw)
        for raw in self._executions:
            value = governance._parse(raw)
            original = value['failover_payload']['targets'][0]
            if (original['id'] != source['id'] or original['identity'] != source['identity']
                    or value['target_id'] == source['id'] or value['target_identity'] == source['identity']):
                raise LifecycleError('lifecycle-source-already-used-or-renamed')
        return fd, actual

    def _proof_binding(self, p, source, destination):
        execution = governance._parse(self._execution_raw)
        original = governance._parse(self._source_raw)
        if (source['id'] != original['id'] or source['identity'] != original['identity']
                or packets.canonical(p) != self._decision_raw or destination == 0):
            raise LifecycleError('lifecycle-unused-source-binding-drift')
        core = dict(execution); core.pop('unused_source_bytes', None)
        return dict(execution['binding'], domain='v6-unused-source/1',
            attempt_id=execution['attempt_id'], runtime_id=execution['runtime_id'],
            governance_request_sha256=execution['governance_request_sha256'],
            execution_core_sha256=packets.digest(packets.canonical(core)),
            planning_sha256=packets.digest(packets.canonical(execution['failover_payload'])),
            decision_sha256=packets.digest(self._decision_raw), source_id=source['id'],
            source_identity_sha256=packets.digest(packets.canonical(source['identity'])),
            source_qualification_sha256=packets.digest(packets.canonical(source['qualification'])),
            source_availability_sha256=packets.digest(packets.canonical(source['availability'])),
            destination_id=p['targets'][destination]['id'],
            destination_identity_sha256=packets.digest(packets.canonical(p['targets'][destination]['identity'])),
            authorization_sha256=packets.digest(packets.canonical(p['authorization'])),
            secret_check_sha256=packets.digest(packets.canonical(p['secret_check'])))

    def _proof(self, raw, p, source, destination, snapshot):
        fd, actual = self._check()
        if snapshot is None or snapshot[0] != fd or packets.canonical(snapshot[1]) != packets.canonical(actual):
            raise LifecycleError('lifecycle-unused-real-snapshot-required')
        value = governance._obj(governance._parse(raw),
            'schema_version binding authorization_status qualification_status observed_at expires_at evidence_sha256')
        expected = self._proof_binding(p, source, destination)
        if (type(value['schema_version']) is not int or value['schema_version'] != 2
                or packets.canonical(value['binding']) != packets.canonical(expected)
                or value['authorization_status'] != 'granted' or value['qualification_status'] != 'qualified'):
            raise LifecycleError('lifecycle-unused-source-proof-unconfirmed')
        governance._int(value['observed_at']); governance._int(value['expires_at']); packets._sha(value['evidence_sha256'])
        if (not 0 <= p['now'] - value['observed_at'] <= p['freshness_seconds']
                or not p['now'] < value['expires_at'] <= value['observed_at'] + p['freshness_seconds']):
            raise LifecycleError('lifecycle-unused-source-proof-stale')
        self._check()
        return dict(proof_sha256=packets.digest(raw), binding=expected, evidence_sha256=value['evidence_sha256'])


@dataclass(frozen=True)
class _ValidatedHistoricalPrefix:
    """Forward-replayed actual acquire evidence, never legacy dispatch artifacts.

    This capability describes the pre-acquire history while its fence always
    checks the real full journal. It does not authorize an old source to run.
    """
    _issuer: object
    _fence: object
    _prefix_raw: bytes
    _acquires: tuple
    _owner: object
    _execution_raw: bytes
    _classification_raw: bytes
    _decision_raw: bytes

    @property
    def _store(self):
        return self._fence._store

    def _check(self):
        if self._issuer is not _PREFIX_TOKEN or self._owner is not None:
            raise LifecycleError('lifecycle-historical-prefix-unavailable')
        fd, actual = self._fence._snapshot()
        refs = governance._parse(self._prefix_raw)
        if (actual['schema_version'] != VERSION or not refs
                or packets.canonical(actual['governance']['records'][:len(refs)]) != self._prefix_raw):
            raise LifecycleError('lifecycle-historical-prefix-drift')
        originals = [ref for ref in refs if ref['kind'] == 'acquire']
        if len(originals) != len(self._acquires):
            raise LifecycleError('lifecycle-historical-acquires-incomplete')
        size = 0
        for ref, (ref_raw, evidence) in zip(originals, self._acquires):
            if packets.canonical(ref) != ref_raw or type(evidence) is not HostEvidence:
                raise LifecycleError('lifecycle-historical-acquire-drift')
            for field in FIELDS:
                raw = getattr(evidence, field)
                size += len(raw) if raw is not None else 0
                if (None if raw is None else packets.digest(raw)) != ref[field+'_sha256']:
                    raise LifecycleError('lifecycle-historical-original-bytes-drift')
        if size > MAX_HISTORICAL_ACQUIRE_BYTES:
            raise LifecycleError('lifecycle-historical-acquires-bound')
        return fd, actual

    def _facts(self, p, sources, destination):
        if packets.canonical(p) != self._decision_raw or not sources or len(set(sources)) != len(sources):
            raise LifecycleError('lifecycle-historical-decision-drift')
        ids = [t['id'] for t in p['targets']]
        if sources != [i for i in ids if i in sources] or p['targets'][destination]['id'] in sources:
            raise LifecycleError('lifecycle-historical-sources-invalid')
        # Every acquired target retains its original identity, including targets
        # whose current qualification already meets the new tier. Otherwise a
        # replacement could inherit another model's failures and stage floor.
        originals = {}
        for ref_raw, evidence in self._acquires:
            request, classification = governance._request(evidence.request, evidence.classification)
            if request['target_id'] not in ids:
                raise LifecycleError('lifecycle-historical-source-identity-or-class-drift')
            source = p['targets'][ids.index(request['target_id'])]
            ref = governance._parse(ref_raw); execution = governance._parse(evidence.execution)
            if (request['target_identity'] != source['identity'] or request['stage'] != source['stage']
                    or classification['capability_class'] != p['task']['capability_class']
                    or execution['target_id'] != source['id'] or execution['target_identity'] != source['identity']):
                raise LifecycleError('lifecycle-historical-source-identity-or-class-drift')
            # Forward replay already verified original authority and selection
            # at the committed time. Never substitute today's observation.
            old = execution['failover_payload']; failover._validate(old, _defer_transitions=True)
            if (old['now'] != ref['committed_at']
                    or old['task']['capability_tier'] != classification['capability_tier']
                    or failover._authorization_problem(old) is not None
                    or failover._destination_problem(old, [t['id'] for t in old['targets']].index(source['id'])) is not None):
                raise LifecycleError('lifecycle-historical-destination-was-unqualified')
            originals.setdefault(source['id'], []).append((classification['capability_tier'], ref['operation_id']))
        facts = []
        for source_id in sources:
            source = p['targets'][ids.index(source_id)]
            requirements = [tier for tier, _ in originals.get(source_id, [])]
            operations = [op for _, op in originals.get(source_id, [])]
            if not requirements:
                raise LifecycleError('lifecycle-historical-source-never-acquired')
            required = max(requirements, key=failover.TIER_RANK.__getitem__)
            if (failover.TIER_RANK[required] >= failover.TIER_RANK[p['task']['capability_tier']]
                    or failover._qualification_problem(p, source, required_tier=required) is not None):
                raise LifecycleError('lifecycle-historical-source-not-qualified')
            facts.append(dict(id=source_id, identity_sha256=packets.digest(packets.canonical(source['identity'])),
                stage=source['stage'], required_tier=required, acquire_operations=operations))
        return facts

    def _proof_binding(self, p, sources, destination):
        facts = self._facts(p, sources, destination)
        execution = governance._parse(self._execution_raw); core = dict(execution); core.pop('historical_source_bytes', None)
        binding = dict(execution['binding'], domain='v6-historical-source/1',
            attempt_id=execution['attempt_id'], runtime_id=execution['runtime_id'],
            governance_request_sha256=execution['governance_request_sha256'],
            classification_sha256=packets.digest(self._classification_raw),
            execution_core_sha256=packets.digest(packets.canonical(core)),
            planning_sha256=packets.digest(packets.canonical(execution['failover_payload'])),
            decision_sha256=packets.digest(self._decision_raw),
            historical_acquires_sha256=packets.digest(packets.canonical([governance._parse(raw) for raw, _ in self._acquires])),
            sources_sha256=packets.digest(packets.canonical(facts)),
            qualifications_sha256=packets.digest(packets.canonical([p['targets'][[t['id'] for t in p['targets']].index(s)]['qualification'] for s in sources])),
            destination_id=p['targets'][destination]['id'],
            destination_identity_sha256=packets.digest(packets.canonical(p['targets'][destination]['identity'])),
            authorization_sha256=packets.digest(packets.canonical(p['authorization'])),
            secret_check_sha256=packets.digest(packets.canonical(p['secret_check'])))
        return binding, facts

    def _proof(self, raw, p, sources, destination, snapshot):
        fd, actual = self._check()
        if snapshot is None or snapshot[0] != fd or packets.canonical(snapshot[1]) != packets.canonical(actual):
            raise LifecycleError('lifecycle-historical-real-snapshot-required')
        value = governance._obj(governance._parse(raw),
            'schema_version binding coverage authorization_status qualification_status observed_at expires_at evidence_sha256')
        expected, facts = self._proof_binding(p, sources, destination)
        if (type(value['schema_version']) is not int or value['schema_version'] != 3
                or packets.canonical(value['binding']) != packets.canonical(expected) or value['coverage'] != 'complete'
                or value['authorization_status'] != 'granted' or value['qualification_status'] != 'qualified'):
            raise LifecycleError('lifecycle-historical-proof-unconfirmed')
        governance._int(value['observed_at']); governance._int(value['expires_at']); packets._sha(value['evidence_sha256'])
        if (not 0 <= p['now'] - value['observed_at'] <= p['freshness_seconds']
                or not p['now'] < value['expires_at'] <= value['observed_at'] + p['freshness_seconds']):
            raise LifecycleError('lifecycle-historical-proof-stale')
        self._check()
        return dict(proof_sha256=packets.digest(raw), binding=expected, evidence_sha256=value['evidence_sha256'],
            source_requirements={v['id']: v['required_tier'] for v in facts})


@dataclass(frozen=True)
class _ValidatedHistoricalDestination:
    _issuer: object
    _prefix: _ValidatedHistoricalPrefix
    _sources: tuple

    def _requirements(self, fd, execution_raw):
        if self._issuer is not _PREFIX_TOKEN or type(self._prefix) is not _ValidatedHistoricalPrefix:
            raise LifecycleError('lifecycle-historical-destination-unavailable')
        actual_fd, _ = self._prefix._check()
        if actual_fd != fd or execution_raw != self._prefix._execution_raw:
            raise LifecycleError('lifecycle-historical-destination-execution-drift')
        p = governance._parse(self._prefix._decision_raw)
        execution = governance._parse(execution_raw)
        index = [t['id'] for t in p['targets']].index(execution['target_id'])
        facts = self._prefix._facts(p, list(self._sources), index)
        return {v['id']: v['required_tier'] for v in facts}


def _binding(store, ledger, operation_id):
    state = ledger.get('governance')
    return dict(packet_id=store.packet_id, identity_sha256=ledger['identity_sha256'],
        operation_id=operation_id, revision=ledger['revision'], generation=ledger['generation'],
        prefix_sha256=packets.digest(packets.canonical(state['records'] if state else [])),
        objective_sha256=packets.digest(packets.canonical(state['objective'])) if state else None,
        policy_sha256=packets.digest(packets.canonical(state['policy'])) if state else None)


def validate_ledger(ledger, packet_id):
    governance._obj(ledger, 'schema_version packet_id identity_sha256 revision generation attempts checkpoint supervisors integrations governance')
    if type(ledger['schema_version']) is not int or ledger['schema_version'] != VERSION or ledger['packet_id'] != packet_id:
        raise LifecycleError('lifecycle-ledger-version')
    packets._sha(ledger['identity_sha256'])
    governance._int(ledger['revision'], governance.MAX_RECORDS)
    governance._int(ledger['generation'], packets.MAX_ATTEMPTS)
    if ledger['integrations'] != {} or type(ledger['integrations']) is not dict:
        raise LifecycleError('lifecycle-integration-unavailable')
    state = governance._obj(ledger['governance'], 'schema_version objective policy locator_sha256 records')
    if type(state['schema_version']) is not int or state['schema_version'] != 2:
        raise LifecycleError('lifecycle-governance-version')
    governance._objective(state['objective']); governance._policy(state['policy'])
    packets._sha(state['locator_sha256'])
    refs = state['records']
    if type(refs) is not list or not 1 <= len(refs) <= governance.MAX_RECORDS or len(refs) != ledger['revision']:
        raise LifecycleError('lifecycle-prefix-invalid')
    seen = set()
    mode = refs[0].get('kind') if type(refs[0]) is dict else None
    allowed = (KINDS if mode == 'admit' else PREPARED_KINDS if mode == 'admit-prepared'
        else BOOTSTRAP_FIXTURE_KINDS if mode == 'admit-bootstrap-fixture' else frozenset())
    for ref in refs:
        governance._obj(ref, 'operation_id kind binding committed_at request_sha256 record_sha256 classification_sha256 authority_sha256 execution_sha256 runtime_sha256')
        packets._id(ref['operation_id']); governance._int(ref['committed_at'])
        if ref['operation_id'] in seen or type(ref['kind']) is not str or ref['kind'] not in allowed:
            raise LifecycleError('lifecycle-operation-invalid')
        seen.add(ref['operation_id'])
        for field in FIELDS:
            sha = ref[field + '_sha256']
            if sha is None and field in ('execution', 'runtime'):
                continue
            packets._sha(sha)
    if type(ledger['attempts']) is not list or type(ledger['supervisors']) is not dict:
        raise LifecycleError('lifecycle-projection-invalid')


def _authority(raw, binding, now, freshness, *, containment=False):
    proof = governance._obj(governance._parse(raw), 'schema_version binding host_recording_status authorization_status qualification_status objective_status observed_at expires_at')
    if (type(proof['schema_version']) is not int or proof['schema_version'] != 2
            or packets.canonical(proof['binding']) != packets.canonical(binding)
            or proof['host_recording_status'] != 'granted' or proof['objective_status'] != 'admitted'):
        raise LifecycleError('lifecycle-authority-unavailable')
    if proof['authorization_status'] not in ('granted', 'revoked') or proof['qualification_status'] not in ('qualified', 'revoked'):
        raise LifecycleError('lifecycle-authority-unavailable')
    if not containment and (proof['authorization_status'] != 'granted' or proof['qualification_status'] != 'qualified'):
        raise LifecycleError('lifecycle-authority-revoked')
    governance._int(proof['observed_at']); governance._int(proof['expires_at'])
    if not 0 <= now - proof['observed_at'] <= freshness or not now < proof['expires_at'] <= proof['observed_at'] + freshness:
        raise LifecycleError('lifecycle-authority-stale')


def _evidence(evidence, binding, now, *, objective=None, policy=None, _kinds=KINDS):
    if type(evidence) is not HostEvidence:
        raise LifecycleError('lifecycle-host-evidence-required')
    request, classification = governance._request(evidence.request, evidence.classification)
    record = governance._obj(governance._parse(evidence.record), 'schema_version binding request_sha256 classification_sha256 kind observed_at payload')
    if (type(record['schema_version']) is not int or record['schema_version'] != 1
            or type(record['kind']) is not str or record['kind'] not in _kinds or packets.canonical(record['binding']) != packets.canonical(binding)
            or record['request_sha256'] != packets.digest(evidence.request)
            or record['classification_sha256'] != packets.digest(evidence.classification)):
        raise LifecycleError('lifecycle-evidence-binding-drift')
    governance._int(record['observed_at'])
    if not 0 <= now - record['observed_at'] <= request['policy']['freshness_seconds']:
        raise LifecycleError('lifecycle-record-stale')
    if (objective is not None and request['objective'] != objective
            or policy is not None and request['policy'] != policy):
        raise LifecycleError('lifecycle-objective-or-policy-drift')
    auth_binding = dict(binding, **{field + '_sha256': packets.digest(getattr(evidence, field))
        if getattr(evidence, field) is not None else None for field in FIELDS if field != 'authority'})
    _authority(evidence.authority, auth_binding, now, request['policy']['freshness_seconds'],
        containment=record['kind'] == 'observe')
    required = {'execution'} if record['kind'] == 'acquire' else {'runtime'} if record['kind'] in ('observe', 'publish', 'finish') else set()
    if any((getattr(evidence, field) is not None) != (field in required) for field in ('execution', 'runtime')):
        raise LifecycleError('lifecycle-evidence-field-conflict')
    for field in ('execution', 'runtime'):
        raw = getattr(evidence, field)
        if raw is not None:
            governance._parse(raw)
    return dict(request=request, record=record, classification=classification,
        evidence=evidence, committed_at=now)


class SyntheticLifecycle:
    """An explicit fixture host; no public CLI constructor or backend registry.

    The reader must locate the same canonical objective across aliases and
    independently retain exact evidence bytes. The backend must independently
    inspect its saved runtime, consume the exact execution bytes and expose a
    read-only seal after export. No descriptor/OS-containment claim is made.
    """
    _kinds = KINDS
    _gated_kinds = GATED_KINDS
    _admission_kind = 'admit'
    _archive_replays = False
    _current_schema1 = False
    _extra_kinds = frozenset({'prepare-intent', 'prepared'})

    def __init__(self, store, reader, backend, *, alias, host_id, backend_id, policy_sha256):
        if type(store) is not packets.PacketStore:
            raise LifecycleError('lifecycle-store-required')
        packets._id(alias); packets._id(host_id); packets._id(backend_id); packets._sha(policy_sha256)
        for value, methods in [(reader, ('locate_objective', 'readback_evidence', 'readback_authority',
                                        'readback_initial_source', 'readback_source_state'))]:
            if getattr(value, 'synthetic_only', False) is not True or any(not callable(getattr(value, name, None)) for name in methods):
                raise LifecycleError('lifecycle-synthetic-capability-required')
        self._validate_backend(backend)
        self.store, self.reader, self.backend = store, reader, backend
        self.alias, self.host_id, self.backend_id, self.policy_sha256 = alias, host_id, backend_id, policy_sha256

    def _validate_backend(self, backend):
        if (getattr(backend, 'synthetic_only', False) is not True
                or any(not callable(getattr(backend, name, None)) for name in ('launch', 'inspect', 'export_patch', 'read_sealed_patch'))):
            raise LifecycleError('lifecycle-synthetic-capability-required')
        if (getattr(backend, 'requires_runtime_descriptor', False) is not False
                or getattr(backend, 'requires_runtime_bootstrap', False) is not False):
            raise LifecycleError('lifecycle-backend-unqualified')

    def _governance_entry(self, entry):
        return entry

    def _extra_projection(self, entry, ref, attempt, supervisor):
        raise LifecycleError('lifecycle-operation-unavailable')

    def _extra_confirmation(self, fd, ledger, entry, now):
        pass

    def _locator(self, objective, identity):
        raw = self.reader.locate_objective(self.alias)
        locator = governance._obj(governance._parse(raw), 'schema_version root packet_id identity_sha256 objective_sha256 authority_id')
        expected = dict(schema_version=1, root=str(self.store.root), packet_id=self.store.packet_id,
            identity_sha256=identity, objective_sha256=packets.digest(packets.canonical(objective)), authority_id=objective['authority_id'])
        if locator != expected or str(self.store.root.resolve()) != str(self.store.root):
            raise LifecycleError('lifecycle-objective-locator-conflict')
        return packets.digest(raw)

    def _runtime(self, raw, binding, now, freshness):
        value = governance._obj(governance._parse(raw), 'schema_version binding runtime_state external_effects observed_at expires_at evidence_sha256')
        if (type(value['schema_version']) is not int or value['schema_version'] != 1
                or packets.canonical(value['binding']) != packets.canonical(binding)
                or value['runtime_state'] not in ('running', 'stopped', 'isolated', 'unknown')
                or value['external_effects'] not in ('excluded', 'unknown')):
            raise LifecycleError('lifecycle-runtime-binding-drift')
        packets._sha(value['evidence_sha256'])
        governance._int(value['observed_at']); governance._int(value['expires_at'])
        if not 0 <= now - value['observed_at'] <= freshness or not now < value['expires_at'] <= value['observed_at'] + freshness:
            raise LifecycleError('lifecycle-runtime-stale')
        return value

    def _project(self, fd, ledger, *, now, _check_projection=True, _unused_checks=None,
                 _historical_checks=None, _historical_caps=None):
        validate_ledger(ledger, self.store.packet_id)
        if ledger['governance']['records'][0]['kind'] != self._admission_kind:
            raise LifecycleError('lifecycle-mode-conflict')
        state = ledger['governance']; refs = []; gov_entries = []; attempts = []; supervisors = {}; checkpoint = None
        terminal = False; snapshot = None; previous_commit = -1; executions = []; original_source = None; acquires = []
        for ref in state['records']:
            if not previous_commit <= ref['committed_at'] <= now:
                raise LifecycleError('lifecycle-clock-rollback-or-future')
            previous_commit = ref['committed_at']
            partial = dict(ledger, revision=len(refs), generation=len(attempts),
                governance=dict(state, records=refs))
            if not refs:
                partial.pop('governance')
            binding = _binding(self.store, partial, ref['operation_id'])
            if ref['binding'] != binding or packets.canonical(ref['binding']) != packets.canonical(binding):
                raise LifecycleError('lifecycle-prefix-binding-drift')
            raws = []
            for field in FIELDS:
                sha = ref[field + '_sha256']
                raw = None if sha is None else trust._read(fd, 'lifecycle-' + sha + '.json', governance.MAX_EVIDENCE)
                if raw is not None and packets.digest(raw) != sha:
                    raise LifecycleError('lifecycle-original-bytes-drift')
                raws.append(raw)
            entry = _evidence(HostEvidence(*raws), binding, ref['committed_at'], objective=state['objective'], policy=state['policy'], _kinds=self._kinds)
            record = entry['record']; request = entry['request']; kind = record['kind']; payload = record['payload']
            if kind != ref['kind'] or terminal:
                raise LifecycleError('lifecycle-terminal-or-kind-conflict')
            if kind in self._gated_kinds and snapshot is not None and 'revoked' in snapshot['blocked_reasons']:
                raise LifecycleError('lifecycle-governance-revoked')
            if kind in GOVERNANCE_KINDS or kind == self._admission_kind:
                gov_entries.append(self._governance_entry(entry))
                snapshot = governance.project(gov_entries, now=ref['committed_at'])
            if kind == self._admission_kind:
                original_source = dict(id=request['target_id'], identity=request['target_identity'])
            if kind == 'acquire':
                execution = governance._parse(entry['evidence'].execution)
                version = execution.get('schema_version') if type(execution) is dict else None
                if type(version) is not int or version not in (1, 2, 3):
                    raise LifecycleError('lifecycle-execution-version')
                governance._obj(execution, EXECUTION_FIELDS + {1: '', 2: ' unused_source_bytes', 3: ' historical_source_bytes'}[version])
                governance._int(execution['generation'], packets.MAX_ATTEMPTS)
                if (packets.canonical(execution['binding']) != packets.canonical(binding) or execution['governance_request_sha256'] != ref['request_sha256']
                        or execution['attempt_id'] != request['attempt_id'] or execution['generation'] != len(attempts) + 1
                        or request['generation'] != execution['generation'] or execution['predecessor_sha256'] != checkpoint
                        or execution['target_id'] != request['target_id'] or execution['target_identity'] != request['target_identity']):
                    raise LifecycleError('lifecycle-execution-request-drift')
                if (execution['host_id'] != self.host_id or execution['backend_id'] != self.backend_id
                        or execution['runtime_policy_sha256'] != self.policy_sha256):
                    raise LifecycleError('lifecycle-host-policy-drift')
                packets._id(execution['runtime_id'])
                if any(v['binding']['runtime_id'] == execution['runtime_id'] for v in supervisors.values()):
                    raise LifecycleError('lifecycle-runtime-id-reused')
                prior = governance.project(gov_entries[:-1], now=ref['committed_at'])
                planning = execution['failover_payload']
                if (packets.canonical(planning['events']) != packets.canonical(prior['events'])
                        or planning['now'] != ref['committed_at']
                        or planning['freshness_seconds'] != state['policy']['freshness_seconds']
                        or planning['policy'] != {k: state['policy'][k] for k in planning['policy']}
                        or planning['task']['acceptance_sha256'] != state['objective']['acceptance_sha256']):
                    raise LifecycleError('lifecycle-execution-history-drift')
                effective = copy.deepcopy(planning)
                for event in effective['events']:
                    event['cause'] = prior['resolved_causes'].get(event['attempt_id'], event['cause'])
                failover._validate(effective)
                source = effective['targets'][0]
                if version == 2 and original_source != dict(id=source['id'], identity=source['identity']):
                    raise LifecycleError('lifecycle-original-source-renamed')
                kwargs = {}
                if version == 2:
                    raw = execution['unused_source_bytes']
                    if type(raw) is not str or not 0 < len(raw.encode('utf-8')) <= 16384:
                        raise LifecycleError('lifecycle-unused-source-bytes-bound')
                    fence = self._fence(fd)
                    cap = _ValidatedUnusedPrefix(_PREFIX_TOKEN, fence, packets.canonical(refs),
                        packets.canonical(original_source), tuple(executions), prior['owner'],
                        entry['evidence'].execution, packets.canonical(effective))
                    kwargs = dict(_trusted_locked_context=fence,
                        _trusted_v6_unused_source_guard=failover._V6UnusedSourceGuard(cap, raw.encode('utf-8')))
                if version == 3:
                    raw = execution['historical_source_bytes']
                    if type(raw) is not str or not 0 < len(raw.encode('utf-8')) <= 16384:
                        raise LifecycleError('lifecycle-historical-source-bytes-bound')
                    fence = self._fence(fd)
                    historical_cap = _ValidatedHistoricalPrefix(_PREFIX_TOKEN, fence, packets.canonical(refs),
                        tuple(acquires), prior['owner'], entry['evidence'].execution,
                        entry['evidence'].classification, packets.canonical(effective))
                    kwargs = dict(_trusted_locked_context=fence,
                        _trusted_v6_historical_source_guard=failover._V6HistoricalSourceGuard(historical_cap, raw.encode('utf-8')))
                route = agent_routing.plan_model_failover(request['v2_task'], effective, **kwargs)
                selected = route['plan']['target']
                if route['plan']['status'] not in ('planned', 'retry') or selected is None or selected['id'] != request['target_id'] or selected['identity'] != request['target_identity'] or selected['stage'] != request['stage']:
                    raise LifecycleError('lifecycle-selection-unconfirmed')
                if version == 2:
                    proof = route['plan'].get('v6_unused_source_proof')
                    if proof is None:
                        raise LifecycleError('lifecycle-unused-proof-not-consumed')
                    if _unused_checks is not None:
                        _unused_checks[ref['operation_id']] = (copy.deepcopy(proof['binding']), raw.encode('utf-8'))
                if version == 3:
                    proof = route['plan'].get('v6_historical_source_proof')
                    if proof is None:
                        raise LifecycleError('lifecycle-historical-proof-not-consumed')
                    if _historical_checks is not None:
                        _historical_checks[ref['operation_id']] = (copy.deepcopy(proof['binding']), raw.encode('utf-8'))
                    if _historical_caps is not None:
                        _historical_caps[ref['execution_sha256']] = _ValidatedHistoricalDestination(
                            _PREFIX_TOKEN, historical_cap, tuple(proof['source_requirements']))
                acquires.append((packets.canonical(ref), entry['evidence']))
                executions.append(entry['evidence'].execution)
                runtime = execution['runtime_id']
                runtime_binding = dict(packet_id=ledger['packet_id'], identity_sha256=ledger['identity_sha256'],
                    attempt_id=request['attempt_id'], generation=request['generation'], runtime_id=runtime,
                    execution_request_sha256=ref['execution_sha256'], target_sha256=packets.digest(packets.canonical(request['target_identity'])),
                    host_id=self.host_id, backend_id=self.backend_id, policy_sha256=self.policy_sha256)
                attempts.append(dict(id=request['attempt_id'], generation=request['generation'],
                    request_sha256=ref['request_sha256'], execution_request_sha256=ref['execution_sha256'],
                    predecessor_sha256=checkpoint, checkpoint_sha256=None, status='reserved'))
                supervisors[request['attempt_id']] = dict(binding=runtime_binding, stage='reserved', runtime_sha256=None)
            elif kind not in GOVERNANCE_KINDS and kind != self._admission_kind:
                if snapshot is None or snapshot['owner'] is None or not attempts or request['attempt_id'] != attempts[-1]['id']:
                    raise LifecycleError('lifecycle-owner-required')
                attempt = attempts[-1]; supervisor = supervisors[attempt['id']]
                if ref['request_sha256'] != attempt['request_sha256'] or request['generation'] != attempt['generation']:
                    raise LifecycleError('lifecycle-original-request-drift')
                if kind in self._extra_kinds:
                    self._extra_projection(entry, ref, attempt, supervisor)
                elif kind in ('launch-intent', 'export-intent'):
                    governance._obj(payload, '')
                    required = 'reserved' if kind == 'launch-intent' else 'observed'
                    if supervisor['stage'] != required:
                        raise LifecycleError('lifecycle-intent-already-established')
                    supervisor['stage'] = kind
                    attempt['status'] = 'unknown'
                elif kind == 'observe':
                    governance._obj(payload, '')
                    proof = self._runtime(entry['evidence'].runtime, supervisor['binding'], ref['committed_at'], state['policy']['freshness_seconds'])
                    if supervisor['stage'] == 'reserved':
                        raise LifecycleError('lifecycle-runtime-not-launched')
                    supervisor['runtime_sha256'] = ref['runtime_sha256']
                    safe = proof['runtime_state'] in ('stopped', 'isolated') and proof['external_effects'] == 'excluded'
                    if supervisor['stage'] in ('launch-intent', 'observed'):
                        supervisor['stage'] = 'observed'
                        attempt['status'] = 'observed' if safe else 'unknown'
                    elif supervisor['stage'] == 'published':
                        attempt['status'] = 'published' if safe else 'unknown'
                    else:
                        attempt['status'] = 'observed' if safe and proof['runtime_state'] == 'isolated' else 'unknown'
                elif kind == 'publish':
                    governance._obj(payload, 'patch_sha256 checkpoint_sha256')
                    packets._sha(payload['patch_sha256']); packets._sha(payload['checkpoint_sha256'])
                    if supervisor['stage'] != 'export-intent' or attempt['status'] != 'unknown':
                        raise LifecycleError('lifecycle-export-intent-required')
                    proof = self._runtime(entry['evidence'].runtime, supervisor['binding'], ref['committed_at'], state['policy']['freshness_seconds'])
                    if proof['runtime_state'] != 'stopped' or proof['external_effects'] != 'excluded':
                        raise LifecycleError('lifecycle-publish-not-stopped')
                    patch = trust._read(fd, 'lifecycle-patch-' + payload['patch_sha256'], packets.MAX_PATCH)
                    if packets.digest(patch) != payload['patch_sha256']:
                        raise LifecycleError('lifecycle-patch-drift')
                    validate_patch(patch)
                    manifest_raw = trust._read(fd, 'lifecycle-checkpoint-' + payload['checkpoint_sha256'] + '.json', governance.MAX_EVIDENCE)
                    manifest = governance._parse(manifest_raw)
                    expected = dict(binding=supervisor['binding'], patch_sha256=payload['patch_sha256'], runtime_sha256=ref['runtime_sha256'])
                    if manifest != expected or packets.digest(manifest_raw) != payload['checkpoint_sha256']:
                        raise LifecycleError('lifecycle-checkpoint-drift')
                    checkpoint = payload['checkpoint_sha256']; attempt['checkpoint_sha256'] = checkpoint
                    supervisor['stage'] = 'published'; attempt['status'] = 'published'
                elif kind == 'finish':
                    governance._obj(payload, 'result owner_id epoch')
                    if payload['result'] not in ('completed', 'failed'):
                        raise LifecycleError('lifecycle-result-unsealed')
                    packets._id(payload['owner_id']); governance._int(payload['epoch'], governance.MAX_RECORDS)
                    owner = snapshot['owner']
                    if payload['owner_id'] != owner['owner_id'] or payload['epoch'] != owner['epoch']:
                        raise LifecycleError('lifecycle-release-owner-drift')
                    proof = self._runtime(entry['evidence'].runtime, supervisor['binding'], ref['committed_at'], state['policy']['freshness_seconds'])
                    quarantined = (supervisor['stage'] in ('observed', 'export-intent') and payload['result'] == 'failed'
                        and proof['runtime_state'] == 'isolated' and attempt['status'] == 'observed')
                    if (proof['external_effects'] != 'excluded' or not quarantined
                            and (supervisor['stage'] != 'published' or proof['runtime_state'] != 'stopped')):
                        raise LifecycleError('lifecycle-release-not-stopped-or-isolated')
                    has_failure = any(e['attempt_id'] == attempt['id'] for e in snapshot['events'])
                    if has_failure != (payload['result'] == 'failed'):
                        raise LifecycleError('lifecycle-terminal-result-conflict')
                    if payload['result'] == 'failed':
                        release = copy.deepcopy(entry)
                        release['record'].update(kind='release', payload=dict(owner_id=payload['owner_id'], epoch=payload['epoch'], runtime_state=proof['runtime_state'], external_effects='excluded'))
                        gov_entries.append(release)
                        snapshot = governance.project(gov_entries, now=ref['committed_at'])
                    else:
                        snapshot = dict(snapshot, owner=None)
                        terminal = True
                    attempt['status'] = 'quarantined' if quarantined else payload['result']
                    supervisor['stage'] = 'finished'
                else:
                    raise LifecycleError('lifecycle-operation-unavailable')
            refs.append(ref)
        if _check_projection and (ledger['generation'] != len(attempts)
                or packets.canonical(ledger['attempts']) != packets.canonical(attempts)
                or packets.canonical(ledger['supervisors']) != packets.canonical(supervisors)
                or ledger['checkpoint'] != checkpoint):
            raise LifecycleError('lifecycle-projection-drift')
        snapshot = dict(governance.project(gov_entries, now=now), terminal=terminal)
        if terminal:
            snapshot['owner'] = None
        return snapshot if _check_projection else (snapshot, attempts, supervisors, checkpoint)

    def _read(self, fd, now):
        ledger = self.store._read(fd, _lifecycle_token=_WRITE_TOKEN)
        if ledger is None or ledger['schema_version'] != VERSION:
            raise LifecycleError('lifecycle-unavailable')
        fence = self._fence(fd)
        snapshot = self._project(fd, ledger, now=now)
        locator = self._locator(ledger['governance']['objective'], ledger['identity_sha256'])
        if locator != ledger['governance']['locator_sha256']:
            raise LifecycleError('lifecycle-objective-locator-drift')
        self._source_archive(fd, ledger)
        fence._snapshot()
        return ledger, snapshot

    def _source_archive(self, fd, ledger):
        first = ledger['governance']['records'][0]
        request = governance._parse(trust._read(fd, 'lifecycle-' + first['request_sha256'] + '.json', governance.MAX_EVIDENCE))
        source = trust._read(fd, 'lifecycle-source-' + request['source_sha256'], packets.MAX_PATCH)
        if packets.digest(source) != request['source_sha256']:
            raise LifecycleError('lifecycle-initial-source-drift')

    def _current(self, ledger, now, kind):
        binding = dict(_binding(self.store, ledger, 'current'), action=kind)
        raw = self.reader.readback_authority(copy.deepcopy(binding))
        _authority(raw, binding, now, ledger['governance']['policy']['freshness_seconds'], containment=kind in ('observe', 'read'))

    def _source(self, request):
        expected = dict(source_sha256=request['source_sha256'], dirty=False,
            scope=request['objective']['scope'], acceptance_sha256=request['objective']['acceptance_sha256'])
        value = governance._parse(self.reader.readback_source_state(copy.deepcopy(request['objective'])))
        if packets.canonical(value) != packets.canonical(expected):
            raise LifecycleError('lifecycle-source-not-clean-or-bound')

    def _destination(self, fd, ledger, execution_raw, now, kind, historical_cap=None):
        execution = governance._parse(execution_raw)
        if execution['schema_version'] == 1 and not self._current_schema1:
            return
        requirements = {}
        if execution['schema_version'] == 3:
            if type(historical_cap) is not _ValidatedHistoricalDestination:
                raise LifecycleError('lifecycle-historical-destination-cap-required')
            requirements = historical_cap._requirements(fd, execution_raw)
        readback = getattr(self.reader, 'readback_destination', None)
        if not callable(readback):
            raise LifecycleError('lifecycle-current-destination-unavailable')
        binding = dict(_binding(self.store, ledger, 'current'), action=kind,
            execution_sha256=packets.digest(execution_raw), target_id=execution['target_id'],
            target_identity_sha256=packets.digest(packets.canonical(execution['target_identity'])))
        value = governance._obj(governance._parse(readback(copy.deepcopy(binding))),
            'schema_version binding observed_at expires_at payload')
        if type(value['schema_version']) is not int or value['schema_version'] != 1 or packets.canonical(value['binding']) != packets.canonical(binding):
            raise LifecycleError('lifecycle-current-destination-binding-drift')
        governance._int(value['observed_at']); governance._int(value['expires_at'])
        freshness = ledger['governance']['policy']['freshness_seconds']
        if not 0 <= now - value['observed_at'] <= freshness or not now < value['expires_at'] <= value['observed_at'] + freshness:
            raise LifecycleError('lifecycle-current-destination-stale')
        p = value['payload']; failover._validate(p, _defer_transitions=True)
        original = execution['failover_payload']
        if (p['now'] != now or p['freshness_seconds'] != freshness or not p['enabled']
                or any(p[k] != original[k] for k in ('task', 'policy', 'current_target', 'events'))
                or [(t['id'], t['stage'], t['identity']) for t in p['targets']]
                    != [(t['id'], t['stage'], t['identity']) for t in original['targets']]
                or failover._authorization_problem(p) is not None):
            raise LifecycleError('lifecycle-current-destination-authority-drift')
        ids = [t['id'] for t in p['targets']]; index = ids.index(execution['target_id'])
        if failover._destination_problem(p, index) is not None:
            raise LifecycleError('lifecycle-current-destination-unqualified')
        traversed = {0, ids.index(p['current_target'])} | {ids.index(e['target_id']) for e in p['events']}
        for source_index in traversed:
            source = p['targets'][source_index]
            if (source['qualification']['observed_at'] > now
                    or failover._qualification_problem(p, source,
                        check_fresh=execution['schema_version'] != 2 or source_index != 0,
                        required_tier=requirements.get(source['id'], p['task']['capability_tier'])) is not None):
                raise LifecycleError('lifecycle-current-source-revoked-or-unqualified')
        # Live observations may raise the reservation, never shrink the saved
        # host estimate to make a smaller context window appear adequate.
        if any(p['targets'][index]['context'][k] < original['targets'][index]['context'][k]
                for k in ('input_tokens', 'output_tokens', 'reasoning_tokens', 'margin_tokens')):
            raise LifecycleError('lifecycle-current-context-reservation-shrunk')

    def _effect_gate(self, fd, ledger, state, request, now, kind, *, execution_raw=None, historical_caps=None):
        # A claim is not an enduring source/containment/authority lease.
        # Recheck under the same fence immediately before effects or adoption.
        fence = self._fence(fd)
        if 'revoked' in state['blocked_reasons']:
            raise LifecycleError('lifecycle-governance-revoked')
        self._current(ledger, now, kind)
        self._source(request)
        if execution_raw is None and ledger['attempts']:
            sha = ledger['attempts'][-1]['execution_request_sha256']
            execution_raw = trust._read(fd, 'lifecycle-' + sha + '.json', governance.MAX_EVIDENCE)
            if packets.digest(execution_raw) != sha:
                raise LifecycleError('lifecycle-execution-bytes-drift')
        if execution_raw is not None:
            self._destination(fd, ledger, execution_raw, now, kind,
                (historical_caps or {}).get(packets.digest(execution_raw)))
        retained = ledger['attempts'] if kind == 'acquire' else ledger['attempts'][:-1]
        for attempt in retained:
            binding = ledger['supervisors'][attempt['id']]['binding']
            proof = self._runtime(self.backend.inspect(copy.deepcopy(binding)), binding, now,
                ledger['governance']['policy']['freshness_seconds'])
            if proof['runtime_state'] not in ('stopped', 'isolated') or proof['external_effects'] != 'excluded':
                raise LifecycleError('lifecycle-retained-writer-unconfirmed')
        fence._snapshot()

    def _fence(self, fd):
        # Private journal-reader token guards I/O, never establishes authority.
        context = packets._PlanningContext(self.store, fd, self.store._planning_lease,
            _lifecycle_token=_WRITE_TOKEN)
        context._snapshot()
        return context

    def snapshot(self, *, now):
        governance._int(now)
        with self.store.locked() as fd:
            ledger, state = self._read(fd, now)
            fence = self._fence(fd)
            self._current(ledger, now, 'read')
            fence._snapshot()
            return copy.deepcopy(ledger), state

    def _append(self, operation_id, kind, *, expected_revision, now, effect=None):
        packets._id(operation_id); governance._int(expected_revision); governance._int(now)
        if kind not in self._kinds:
            raise LifecycleError('lifecycle-operation-invalid')
        with self.store.locked() as fd:
            ledger = self.store._read(fd, _lifecycle_token=_WRITE_TOKEN)
            fence = self._fence(fd)
            if kind == self._admission_kind and ledger is not None and ledger['schema_version'] == 2:
                if ledger['revision'] != 0 or ledger['generation'] != 0 or ledger['attempts'] or ledger['checkpoint'] is not None:
                    raise LifecycleError('lifecycle-nonempty-legacy-unavailable')
                prefix = None
            else:
                if self._archive_replays and ledger is not None and ledger['schema_version'] == VERSION:
                    prefix = self._project(fd, ledger, now=now)
                    self._source_archive(fd, ledger)
                    prior = next((ref for ref in ledger['governance']['records'] if ref['operation_id'] == operation_id), None)
                    if prior is not None:
                        if kind != prior['kind']:
                            raise LifecycleError('lifecycle-operation-bytes-conflict')
                        fence._snapshot()
                        return copy.deepcopy(ledger), prefix
                ledger, prefix = self._read(fd, now)
                self._current(ledger, now, kind)
                fence._snapshot()
                prior = next((ref for ref in ledger['governance']['records'] if ref['operation_id'] == operation_id), None)
                if prior is not None:
                    evidence = self.reader.readback_evidence(copy.deepcopy(prior['binding']))
                    if type(evidence) is not HostEvidence or kind != prior['kind'] or any(
                            (packets.digest(getattr(evidence, field)) if getattr(evidence, field) is not None else None)
                            != prior[field + '_sha256'] for field in FIELDS):
                        raise LifecycleError('lifecycle-operation-bytes-conflict')
                    fence._snapshot()
                    return copy.deepcopy(ledger), prefix
                if kind == self._admission_kind:
                    raise LifecycleError('lifecycle-already-admitted')
            if ledger is None or ledger['revision'] != expected_revision:
                raise LifecycleError('lifecycle-revision-conflict')
            if expected_revision >= governance.MAX_RECORDS:
                raise LifecycleError('lifecycle-prefix-bound')
            fence._snapshot()
            binding = _binding(self.store, ledger, operation_id)
            evidence = self.reader.readback_evidence(copy.deepcopy(binding))
            current = ledger.get('governance')
            entry = _evidence(evidence, binding, now,
                objective=current['objective'] if current else None, policy=current['policy'] if current else None, _kinds=self._kinds)
            if entry['record']['kind'] != kind:
                raise LifecycleError('lifecycle-operation-kind-conflict')
            request = entry['request']
            updated = copy.deepcopy(ledger)
            if kind == self._admission_kind:
                self._source(request)
                source = self.reader.readback_initial_source(copy.deepcopy(request['objective']))
                if type(source) is not bytes or len(source) > packets.MAX_PATCH or packets.digest(source) != request['source_sha256']:
                    raise LifecycleError('lifecycle-initial-source-unconfirmed')
                locator = self._locator(request['objective'], ledger['identity_sha256'])
                updated.update(schema_version=VERSION, supervisors={}, integrations={},
                    governance=dict(schema_version=2, objective=request['objective'], policy=request['policy'],
                        locator_sha256=locator, records=[]))
                self.store._immutable(fd, 'lifecycle-source-' + request['source_sha256'], source,
                    _lifecycle_token=_WRITE_TOKEN)
            elif kind == 'acquire':
                if prefix['owner'] is not None or prefix['terminal']:
                    raise LifecycleError('lifecycle-owner-or-terminal-conflict')
                self._source(request)
                for attempt in ledger['attempts']:
                    old = ledger['supervisors'][attempt['id']]['binding']
                    proof = self._runtime(self.backend.inspect(copy.deepcopy(old)), old, now, current['policy']['freshness_seconds'])
                    if proof['runtime_state'] not in ('stopped', 'isolated') or proof['external_effects'] != 'excluded':
                        raise LifecycleError('lifecycle-retained-writer-unconfirmed')
            elif kind in ('observe', 'publish', 'finish'):
                if not ledger['attempts']:
                    raise LifecycleError('lifecycle-owner-required')
                runtime_binding = ledger['supervisors'][ledger['attempts'][-1]['id']]['binding']
                actual = self.backend.inspect(copy.deepcopy(runtime_binding))
                if type(actual) is not bytes or actual != evidence.runtime:
                    raise LifecycleError('lifecycle-current-runtime-unconfirmed')
                proof = self._runtime(actual, runtime_binding, now, current['policy']['freshness_seconds'])
                if kind == 'publish':
                    patch = self.backend.read_sealed_patch(copy.deepcopy(runtime_binding), packets.MAX_PATCH)
                    validate_patch(patch)
                    payload = entry['record']['payload']
                    manifest = packets.canonical(dict(binding=runtime_binding, patch_sha256=packets.digest(patch),
                        runtime_sha256=packets.digest(actual)))
                    if payload != dict(patch_sha256=packets.digest(patch), checkpoint_sha256=packets.digest(manifest)):
                        raise LifecycleError('lifecycle-seal-bytes-unconfirmed')
                    if proof['runtime_state'] != 'stopped' or proof['external_effects'] != 'excluded':
                        raise LifecycleError('lifecycle-publish-not-stopped')
                    self.store._immutable(fd, 'lifecycle-patch-' + packets.digest(patch), patch, _lifecycle_token=_WRITE_TOKEN)
                    self.store._immutable(fd, 'lifecycle-checkpoint-' + packets.digest(manifest) + '.json', manifest,
                        _lifecycle_token=_WRITE_TOKEN)
            ref = dict(operation_id=operation_id, kind=kind, binding=binding, committed_at=now)
            for field in FIELDS:
                raw = getattr(evidence, field)
                ref[field + '_sha256'] = None if raw is None else packets.digest(raw)
                if raw is not None:
                    self.store._immutable(fd, 'lifecycle-' + packets.digest(raw) + '.json', raw, _lifecycle_token=_WRITE_TOKEN)
            updated['governance']['records'].append(ref); updated['revision'] += 1
            checks = {}; historical_checks = {}; historical_caps = {}
            projected, attempts, supervisors, checkpoint = self._project(fd, updated, now=now, _check_projection=False, _unused_checks=checks,
                _historical_checks=historical_checks, _historical_caps=historical_caps)
            updated.update(attempts=attempts, supervisors=supervisors, checkpoint=checkpoint, generation=len(attempts))
            fence._snapshot()
            if kind == 'acquire' and operation_id in checks:
                expected_binding, expected_raw = checks[operation_id]
                readback = getattr(self.reader, 'readback_unused_source', None)
                if not callable(readback) or readback(copy.deepcopy(expected_binding)) != expected_raw:
                    raise LifecycleError('lifecycle-unused-source-current-readback-unconfirmed')
                fence._snapshot()
            if operation_id in historical_checks:
                expected_binding, expected_raw = historical_checks[operation_id]
                readback = getattr(self.reader, 'readback_v6_historical_sources', None)
                if not callable(readback) or readback(copy.deepcopy(expected_binding)) != expected_raw:
                    raise LifecycleError('lifecycle-historical-source-current-readback-unconfirmed')
                fence._snapshot()
            self._extra_confirmation(fd, updated, entry, now)
            fence._snapshot()
            if kind in self._gated_kinds:
                self._effect_gate(fd, ledger, projected, request, now, kind,
                    execution_raw=evidence.execution if kind == 'acquire' else None, historical_caps=historical_caps)
            self.store._write(fd, updated, _lifecycle_token=_WRITE_TOKEN)
            self._read(fd, now); post = self._fence(fd)
            # Intent is durable before the only side effect. Retry/restart never
            # reaches this callback for an already committed operation.
            if effect is not None:
                effect(fd, updated)
                post._snapshot()
            return copy.deepcopy(updated), projected

    def admit_new(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'admit', expected_revision=expected_revision, now=now)

    def acquire_attempt(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'acquire', expected_revision=expected_revision, now=now)

    def record(self, operation_id, kind, *, expected_revision, now):
        if kind not in GOVERNANCE_KINDS - {'admit', 'acquire'}:
            raise LifecycleError('lifecycle-governance-operation-required')
        return self._append(operation_id, kind, expected_revision=expected_revision, now=now)

    def launch_reserved(self, operation_id, *, expected_revision, now):
        def launch(fd, ledger):
            attempt = ledger['attempts'][-1]
            binding = ledger['supervisors'][attempt['id']]['binding']
            raw = trust._read(fd, 'lifecycle-' + attempt['execution_request_sha256'] + '.json', governance.MAX_EVIDENCE)
            fence = self._fence(fd)
            request = governance._parse(trust._read(fd, 'lifecycle-' + attempt['request_sha256'] + '.json', governance.MAX_EVIDENCE))
            caps = {}
            state = self._project(fd, ledger, now=now, _historical_caps=caps)
            self._effect_gate(fd, ledger, state, request, now, 'launch-intent', historical_caps=caps)
            fence._snapshot()
            if packets.digest(raw) != attempt['execution_request_sha256']:
                raise LifecycleError('lifecycle-execution-bytes-drift')
            self.backend.launch(copy.deepcopy(binding), raw)
        return self._append(operation_id, 'launch-intent', expected_revision=expected_revision, now=now, effect=launch)

    def reconcile(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'observe', expected_revision=expected_revision, now=now)

    def seal(self, operation_id, *, expected_revision, now):
        def export(fd, ledger):
            attempt = ledger['attempts'][-1]; binding = ledger['supervisors'][attempt['id']]['binding']
            fence = self._fence(fd)
            proof = self._runtime(self.backend.inspect(copy.deepcopy(binding)), binding, now, ledger['governance']['policy']['freshness_seconds'])
            if proof['runtime_state'] != 'stopped' or proof['external_effects'] != 'excluded':
                raise LifecycleError('lifecycle-export-not-stopped')
            request = governance._parse(trust._read(fd, 'lifecycle-' + attempt['request_sha256'] + '.json', governance.MAX_EVIDENCE))
            caps = {}
            state = self._project(fd, ledger, now=now, _historical_caps=caps)
            self._effect_gate(fd, ledger, state, request, now, 'export-intent', historical_caps=caps)
            fence._snapshot()
            self.backend.export_patch(copy.deepcopy(binding), packets.MAX_PATCH)
        return self._append(operation_id, 'export-intent', expected_revision=expected_revision, now=now, effect=export)

    def publish(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'publish', expected_revision=expected_revision, now=now)

    def finish_attempt(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'finish', expected_revision=expected_revision, now=now)
