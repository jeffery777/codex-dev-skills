"""R2 full saved-file lifecycle; no worker, provider, OS or production adapter.

All effect/runtime bindings derive from a new authenticated R2 journal. Flat,
R1 and B1 authority cannot be migrated. Saved fixture observations are not
evidence about real process containment or model service execution.
"""
from __future__ import annotations

import copy
import os

import agent_qualification as trust
import model_packet_bootstrap as bootstrap
import model_packet_governance as governance
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets

PROTOCOL_SHA = packets.digest(b'synthetic-executed-journal/R2')
RECIPE_SHA = packets.digest(b'saved-executed-fixture/R2')
DOMAIN = 'saved-executed-fixture/2'
MAX_EVENTS = 64
START_FIELDS = 'schema_version domain binding execution_sha256 launch_ref_bytes'
EVENT_FIELDS = ('schema_version domain binding_sha256 launch_artifact_sha256 '
    'sequence predecessor_sha256 runtime_state external_effects')
RUNTIME_FIELDS = ('schema_version domain binding runtime_state external_effects '
    'observed_at expires_at evidence_sha256 launch_artifact_sha256 event_hashes')


def _launch_ref(raw, base):
    ref = governance._obj(governance._parse(raw),
        'operation_id kind binding committed_at request_sha256 record_sha256 classification_sha256 authority_sha256 execution_sha256 runtime_sha256')
    binding = governance._obj(ref['binding'],
        'packet_id identity_sha256 operation_id revision generation prefix_sha256 objective_sha256 policy_sha256')
    packets._id(ref['operation_id']); governance._int(ref['committed_at'])
    governance._int(binding['revision']); governance._int(binding['generation'])
    for field in ('request','record','classification','authority'):
        packets._sha(ref[field+'_sha256'])
    for field in ('prefix_sha256','objective_sha256','policy_sha256'):
        packets._sha(binding[field])
    if (ref['kind'] != 'launch-intent' or ref['execution_sha256'] is not None
            or ref['runtime_sha256'] is not None or ref['operation_id'] != binding['operation_id']
            or any(binding[k] != base[k] for k in ('packet_id','identity_sha256','generation'))):
        raise lifecycle.LifecycleError('execution-launch-reference-drift')
    return ref


def _binding(base, plan_raw, descriptor_raw, input_raw, intent_raw, receipt_raw, launch_ref_raw):
    _launch_ref(launch_ref_raw, base)
    plan = preparation._artifact(plan_raw, preparation.PLAN_FIELDS)
    descriptor = preparation._artifact(descriptor_raw, preparation.DESCRIPTOR_FIELDS)
    if base != plan['runtime_binding']:
        raise lifecycle.LifecycleError('execution-acquisition-binding-drift')
    return dict(base, domain=DOMAIN, mode=plan['mode'], control_id=plan['control_id'],
        instance_id=descriptor['instance_id'], plan_sha256=packets.digest(plan_raw),
        descriptor_sha256=packets.digest(descriptor_raw), input_sha256=packets.digest(input_raw),
        bootstrap_intent_ref_sha256=packets.digest(intent_raw), receipt_sha256=packets.digest(receipt_raw),
        launch_ref_sha256=packets.digest(launch_ref_raw))


class SavedExecutionBackend(bootstrap.SavedBootstrapBackend):
    """Exact bounded host fixture: immutable launch/events and one empty patch."""
    _protocol_sha = PROTOCOL_SHA
    _recipe_sha = RECIPE_SHA
    _domain = DOMAIN

    def __init__(self, root):
        super().__init__(root)
        self.now = 110
        self.launch_count = self.export_count = 0

    def _parts(self, fd, binding, launch_ref_raw):
        packets._id(binding['control_id'])
        control = binding['control_id']
        input_raw = self._read(fd,'bootstrap-input-'+control+'.json')
        plan, descriptor_raw = self._bootstrap_input(input_raw)
        value = preparation._artifact(input_raw,bootstrap.INPUT_FIELDS)
        plan_raw = preparation._raw(value['plan_bytes'])
        intent = self._read(fd,'bootstrap-intent-'+control+'.json')
        receipt = self._read(fd,'bootstrap-receipt-'+control+'.json')
        if (self._read(fd,'descriptor-'+control+'.json') != descriptor_raw
                or receipt != bootstrap._receipt(input_raw,intent,domain=DOMAIN)):
            raise lifecycle.LifecycleError('execution-bootstrap-chain-drift')
        expected = _binding(plan['runtime_binding'],plan_raw,descriptor_raw,input_raw,intent,receipt,launch_ref_raw)
        if packets.canonical(binding) != packets.canonical(expected):
            raise lifecycle.LifecycleError('execution-full-binding-drift')
        return packets.digest(packets.canonical(binding))

    def _chain(self, fd, binding):
        key = packets.digest(packets.canonical(binding))
        raw = self._read(fd,'launch-'+key+'.json')
        value = preparation._artifact(raw,START_FIELDS)
        if (value['domain'] != DOMAIN or value['binding'] != binding
                or value['execution_sha256'] != binding['execution_request_sha256']):
            raise lifecycle.LifecycleError('execution-launch-artifact-drift')
        self._parts(fd,binding,preparation._raw(value['launch_ref_bytes']))
        return key, packets.digest(raw)

    def _events(self, fd, key, launch_sha):
        prefix = 'runtime-event-'+key+'-'
        names = sorted(name for name in os.listdir(fd) if name.startswith(prefix))
        if len(names) > MAX_EVENTS:
            raise lifecycle.LifecycleError('execution-event-bound')
        previous = None; latest = None; hashes = []
        for sequence,name in enumerate(names):
            if name != prefix+str(sequence).zfill(6)+'.json':
                raise lifecycle.LifecycleError('execution-event-prefix-drift')
            raw = self._read(fd,name); event = preparation._artifact(raw,EVENT_FIELDS)
            if (event['domain'] != DOMAIN or event['binding_sha256'] != key
                    or event['launch_artifact_sha256'] != launch_sha
                    or type(event['sequence']) is not int or event['sequence'] != sequence
                    or event['predecessor_sha256'] != previous
                    or event['runtime_state'] not in ('running','stopped','isolated','unknown')
                    or event['external_effects'] not in ('excluded','unknown')
                    or sequence == 0 and (event['runtime_state'] != 'running'
                        or event['external_effects'] != 'excluded')):
                raise lifecycle.LifecycleError('execution-event-chain-drift')
            previous = packets.digest(raw); latest = event; hashes.append(previous)
        return len(names),previous,latest,hashes

    def _observe(self, fd, binding, state, effects, *, _genesis=False):
        if state not in ('running','stopped','isolated','unknown') or effects not in ('excluded','unknown'):
            raise lifecycle.LifecycleError('execution-fixture-state-invalid')
        key,launch_sha = self._chain(fd,binding)
        sequence,previous,_,_ = self._events(fd,key,launch_sha)
        if sequence == 0 and not _genesis or _genesis and (sequence != 0 or state != 'running' or effects != 'excluded'):
            raise lifecycle.LifecycleError('execution-running-genesis-required')
        if sequence >= MAX_EVENTS:
            raise lifecycle.LifecycleError('execution-event-bound')
        raw = packets.canonical(dict(schema_version=1,domain=DOMAIN,binding_sha256=key,
            launch_artifact_sha256=launch_sha,sequence=sequence,predecessor_sha256=previous,
            runtime_state=state,external_effects=effects))
        self._save(fd,'runtime-event-'+key+'-'+str(sequence).zfill(6)+'.json',raw)

    def launch(self, binding, execution_raw, launch_ref_raw):
        execution = governance._parse(execution_raw)
        if (packets.digest(execution_raw) != binding['execution_request_sha256']
                or any(execution[k] != binding[k] for k in
                    ('attempt_id','generation','runtime_id','host_id','backend_id'))
                or execution['runtime_policy_sha256'] != binding['policy_sha256']
                or packets.digest(packets.canonical(execution['target_identity'])) != binding['target_sha256']):
            raise lifecycle.LifecycleError('execution-launch-request-drift')
        ref = _launch_ref(launch_ref_raw,binding)
        if ref['request_sha256'] != execution['governance_request_sha256']:
            raise lifecycle.LifecycleError('execution-launch-original-request-drift')
        with self._root() as fd:
            key = self._parts(fd,binding,launch_ref_raw)
            raw = packets.canonical(dict(schema_version=1,domain=DOMAIN,binding=binding,
                execution_sha256=packets.digest(execution_raw),launch_ref_bytes=launch_ref_raw.decode()))
            self._save(fd,'launch-'+key+'.json',raw)
            self._observe(fd,binding,'running','excluded',_genesis=True)
        self.launch_count += 1
        return None

    def set_state(self, binding, state, effects='excluded'):
        """Explicit trusted fixture observation; never called by journal replay."""
        with self._root() as fd:
            self._observe(fd,binding,state,effects)

    def inspect(self, binding):
        governance._int(self.now)
        with self._root() as fd:
            key,launch_sha = self._chain(fd,binding)
            _,latest_sha,event,hashes = self._events(fd,key,launch_sha)
            if event is None:
                raise lifecycle.LifecycleError('execution-runtime-unconfirmed')
            raw = packets.canonical(dict(schema_version=2,domain=DOMAIN,binding=binding,
                runtime_state=event['runtime_state'],external_effects=event['external_effects'],
                observed_at=self.now,expires_at=self.now+60,evidence_sha256=latest_sha,
                launch_artifact_sha256=launch_sha,event_hashes=hashes))
        return raw

    def export_patch(self, binding, limit):
        governance._int(limit)
        with self._root() as fd:
            key,launch_sha = self._chain(fd,binding); _,_,event,_ = self._events(fd,key,launch_sha)
            if event is None or event['runtime_state'] != 'stopped' or event['external_effects'] != 'excluded':
                raise lifecycle.LifecycleError('execution-export-not-stopped')
            handle = os.open('patch-'+key,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
            try:
                os.fsync(handle)
            finally:
                os.close(handle)
            os.fsync(fd)
        self.export_count += 1
        return None

    def read_sealed_patch(self, binding, limit):
        governance._int(limit)
        with self._root() as fd:
            key,_ = self._chain(fd,binding); raw = self._read(fd,'patch-'+key)
            if raw != b'':
                raise lifecycle.LifecycleError('execution-fixed-patch-drift')
        return raw


class SyntheticExecutedLifecycle(bootstrap.SyntheticBootstrapFixtureLifecycle):
    """New R2 mode with full chain binding and governed model continuation."""
    _kinds = lifecycle.EXECUTED_KINDS
    _gated_kinds = frozenset({'acquire','prepare-intent','prepared','bootstrap-intent',
        'bootstrapped','launch-intent','export-intent','publish','finish'})
    _admission_kind = 'admit-bootstrap'
    _domain = DOMAIN
    _launch_stage = 'bootstrapped'

    def _validate_backend(self, backend):
        if type(backend) is not SavedExecutionBackend:
            raise lifecycle.LifecycleError('execution-fixed-backend-required')

    def _mode(self):
        return dict(protocol_sha256=PROTOCOL_SHA,recipe_sha256=RECIPE_SHA,
            runtime_policy_sha256=self.policy_sha256,backend_instance_sha256=self.backend.instance_sha256)

    def _launch_projection(self, entry, ref, attempt, supervisor):
        prepared = supervisor['preparation']; saved = supervisor['bootstrap']
        base = copy.deepcopy(supervisor['binding'])
        supervisor['binding'] = _binding(base,prepared['plan_bytes'].encode(),
            prepared['descriptor_bytes'].encode(),saved['input_bytes'].encode(),
            saved['intent_ref_bytes'].encode(),saved['receipt_bytes'].encode(),packets.canonical(ref))
        supervisor['acquisition_binding'] = base

    def _observe_allowed(self, stage):
        return stage in ('launch-intent','observed','export-intent','published')

    def _before_governance(self, entry, attempts, supervisors):
        if entry['record']['kind'] == 'outcome':
            if (not attempts or entry['request']['attempt_id'] != attempts[-1]['id']
                    or supervisors[attempts[-1]['id']]['runtime_sha256'] is None):
                raise lifecycle.LifecycleError('execution-outcome-before-observed-start')

    def _runtime(self, raw, binding, now, freshness):
        value = governance._obj(governance._parse(raw),RUNTIME_FIELDS)
        if (type(value['schema_version']) is not int or value['schema_version'] != 2
                or value['domain'] != DOMAIN or binding.get('domain') != DOMAIN
                or packets.canonical(value['binding']) != packets.canonical(binding)
                or value['runtime_state'] not in ('running','stopped','isolated','unknown')
                or value['external_effects'] not in ('excluded','unknown')):
            raise lifecycle.LifecycleError('execution-runtime-domain-or-binding-drift')
        packets._sha(value['evidence_sha256']); packets._sha(value['launch_artifact_sha256'])
        hashes = value['event_hashes']
        if type(hashes) is not list or not 1 <= len(hashes) <= MAX_EVENTS:
            raise lifecycle.LifecycleError('execution-runtime-event-bound')
        for sha in hashes:
            packets._sha(sha)
        if len(set(hashes)) != len(hashes) or hashes[-1] != value['evidence_sha256']:
            raise lifecycle.LifecycleError('execution-runtime-event-digest-drift')
        governance._int(value['observed_at']); governance._int(value['expires_at'])
        if not 0 <= now-value['observed_at'] <= freshness or not now < value['expires_at'] <= value['observed_at']+freshness:
            raise lifecycle.LifecycleError('execution-runtime-stale')
        return value

    def _runtime_projection(self, proof, supervisor):
        old = supervisor.get('runtime_frontier')
        if old is not None and (proof['launch_artifact_sha256'] != old['launch_artifact_sha256']
                or proof['event_hashes'][:len(old['event_hashes'])] != old['event_hashes']):
            raise lifecycle.LifecycleError('execution-runtime-prefix-rollback')
        supervisor['runtime_frontier'] = dict(launch_artifact_sha256=proof['launch_artifact_sha256'],
            event_hashes=copy.deepcopy(proof['event_hashes']))

    def _inspect_runtime(self, fd, ledger, attempt):
        supervisor = ledger['supervisors'][attempt['id']]; binding = supervisor['binding']
        actual = self.backend.inspect(copy.deepcopy(binding))
        proof = governance._parse(actual)
        self._runtime(actual,binding,proof['observed_at'],ledger['governance']['policy']['freshness_seconds'])
        # This frontier is reconstructed from all authenticated runtime refs,
        # including publish/finish, by the original-time journal projection.
        old = supervisor.get('runtime_frontier')
        if old is not None:
            if (proof['launch_artifact_sha256'] != old['launch_artifact_sha256']
                    or proof['event_hashes'][:len(old['event_hashes'])] != old['event_hashes']):
                raise lifecycle.LifecycleError('execution-runtime-prefix-rollback')
        return actual

    def _effect_gate(self, fd, ledger, state, request, now, kind, *, current_entry=None, **kwargs):
        super()._effect_gate(fd,ledger,state,request,now,kind,current_entry=current_entry,**kwargs)
        if kind in ('export-intent','publish','finish'):
            fence = self._fence(fd)
            binding = ledger['supervisors'][ledger['attempts'][-1]['id']]['binding']
            actual = self._inspect_runtime(fd,ledger,ledger['attempts'][-1])
            proof = self._runtime(actual,binding,now,ledger['governance']['policy']['freshness_seconds'])
            if current_entry is not None and kind in ('publish','finish') and actual != current_entry['evidence'].runtime:
                raise lifecycle.LifecycleError('execution-final-runtime-readback-drift')
            allowed = ('stopped','isolated') if kind == 'finish' else ('stopped',)
            if proof['runtime_state'] not in allowed or proof['external_effects'] != 'excluded':
                raise lifecycle.LifecycleError('execution-effect-runtime-unconfirmed')
            fence._snapshot()

    def launch_reserved(self, operation_id, *, expected_revision, now):
        def launch(fd, ledger):
            fence = self._fence(fd); caps = {}
            state = self._project(fd,ledger,now=now,_historical_caps=caps)
            attempt = ledger['attempts'][-1]; supervisor = ledger['supervisors'][attempt['id']]
            raw = trust._read(fd,'lifecycle-'+attempt['execution_request_sha256']+'.json',governance.MAX_EVIDENCE)
            request = governance._parse(trust._read(fd,'lifecycle-'+attempt['request_sha256']+'.json',governance.MAX_EVIDENCE))
            self._effect_gate(fd,ledger,state,request,now,'launch-intent',historical_caps=caps)
            ref = ledger['governance']['records'][-1]
            if packets.digest(raw) != attempt['execution_request_sha256']:
                raise lifecycle.LifecycleError('execution-original-bytes-drift')
            fence._snapshot()
            self.backend.launch(copy.deepcopy(supervisor['binding']),raw,packets.canonical(ref))
        return self._append(operation_id,'launch-intent',expected_revision=expected_revision,now=now,effect=launch)
