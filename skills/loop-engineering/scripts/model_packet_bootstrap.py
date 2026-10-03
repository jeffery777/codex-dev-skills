"""B1 closed saved-bootstrap fixture; no writer, migration or production loader.

This mode supports phases only through bootstrapped. A future execution mode starts a new
packet and must establish its entire chain anew, never upgrade this journal.
"""
from __future__ import annotations

import agent_qualification as trust
import model_packet_governance as governance
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets

PROTOCOL_SHA = packets.digest(b'synthetic-bootstrap-fixture-journal/B1')
RECIPE_SHA = packets.digest(b'saved-bootstrap-fixture/B1')
DOMAIN = 'saved-bootstrap-fixture/1'
INPUT_FIELDS = 'schema_version domain plan_bytes descriptor_bytes'
OBSERVATION_FIELDS = ('schema_version domain input_sha256 receipt_sha256 '
    'intent_ref_sha256 state observed_at expires_at')


def _input(plan_raw, descriptor_raw):
    plan = preparation._artifact(plan_raw, preparation.PLAN_FIELDS)
    descriptor = preparation._artifact(descriptor_raw, preparation.DESCRIPTOR_FIELDS)
    expected = dict(schema_version=1, plan_sha256=packets.digest(plan_raw),
        runtime_binding=plan['runtime_binding'], mode=plan['mode'], control_id=plan['control_id'],
        nonce=plan['nonce'], instance_id=descriptor['instance_id'], resource_state='created')
    packets._id(descriptor['instance_id'])
    if packets.canonical(descriptor) != packets.canonical(expected):
        raise lifecycle.LifecycleError('bootstrap-descriptor-chain-drift')
    raw = packets.canonical(dict(schema_version=1, domain=DOMAIN,
        plan_bytes=plan_raw.decode(), descriptor_bytes=descriptor_raw.decode()))
    preparation._artifact(raw, INPUT_FIELDS)
    return raw


def _receipt(input_raw, intent_ref_raw):
    return packets.canonical(dict(schema_version=1, domain=DOMAIN,
        input_sha256=packets.digest(input_raw), intent_ref_sha256=packets.digest(intent_ref_raw),
        state='bootstrapped'))


class SavedBootstrapBackend(preparation.SavedPreparationBackend):
    """Private immutable fixture files, never an OS or model execution proof."""
    _protocol_sha = PROTOCOL_SHA
    _recipe_sha = RECIPE_SHA

    def __init__(self, root):
        super().__init__(root)
        self.bootstrap_count = 0

    def _bootstrap_input(self, raw):
        value = preparation._artifact(raw, INPUT_FIELDS)
        if value['domain'] != DOMAIN:
            raise lifecycle.LifecycleError('bootstrap-domain-drift')
        plan_raw = preparation._raw(value['plan_bytes'])
        descriptor_raw = preparation._raw(value['descriptor_bytes'])
        plan = self._plan(plan_raw)
        if raw != _input(plan_raw, descriptor_raw):
            raise lifecycle.LifecycleError('bootstrap-input-not-derived')
        return plan, descriptor_raw

    def bootstrap(self, input_raw, intent_ref_raw):
        plan, descriptor_raw = self._bootstrap_input(input_raw)
        ref = governance._obj(governance._parse(intent_ref_raw),
            'operation_id kind binding committed_at request_sha256 record_sha256 classification_sha256 authority_sha256 execution_sha256 runtime_sha256')
        binding = governance._obj(ref['binding'],
            'packet_id identity_sha256 operation_id revision generation prefix_sha256 objective_sha256 policy_sha256')
        packets._id(ref['operation_id']); governance._int(ref['committed_at'])
        governance._int(binding['revision']); governance._int(binding['generation'])
        for field in ('request', 'record', 'classification', 'authority'):
            packets._sha(ref[field+'_sha256'])
        packets._sha(binding['prefix_sha256'])
        if (ref['kind'] != 'bootstrap-intent' or ref['execution_sha256'] is not None
                or ref['runtime_sha256'] is not None or binding['operation_id'] != ref['operation_id']
                or binding['revision'] <= plan['binding']['revision']
                or any(binding[k] != plan['binding'][k] for k in
                    ('packet_id', 'identity_sha256', 'generation', 'objective_sha256', 'policy_sha256'))):
            raise lifecycle.LifecycleError('bootstrap-intent-reference-drift')
        # The authenticated journal ref is supplied by the trusted controller;
        # no worker or JSON factory can select this backend.
        with self._root() as fd:
            control = plan['control_id']
            if self._read(fd, 'descriptor-'+control+'.json') != descriptor_raw:
                raise lifecycle.LifecycleError('bootstrap-independent-descriptor-drift')
            self._save(fd, 'bootstrap-input-'+control+'.json', input_raw)
            self._save(fd, 'bootstrap-intent-'+control+'.json', intent_ref_raw)
            self._save(fd, 'bootstrap-receipt-'+control+'.json', _receipt(input_raw, intent_ref_raw))
        self.bootstrap_count += 1
        return None

    def observe_bootstrap(self, input_raw, *, now, freshness):
        governance._int(now); governance._int(freshness)
        if freshness == 0:
            raise lifecycle.LifecycleError('bootstrap-freshness-required')
        plan, descriptor_raw = self._bootstrap_input(input_raw)
        with self._root() as fd:
            control = plan['control_id']
            actual = self._read(fd, 'bootstrap-input-'+control+'.json')
            intent = self._read(fd, 'bootstrap-intent-'+control+'.json')
            receipt = self._read(fd, 'bootstrap-receipt-'+control+'.json')
            if (actual != input_raw or receipt != _receipt(input_raw, intent)
                    or self._read(fd, 'descriptor-'+control+'.json') != descriptor_raw):
                raise lifecycle.LifecycleError('bootstrap-saved-chain-drift')
            proof = packets.canonical(dict(schema_version=1, domain=DOMAIN,
                input_sha256=packets.digest(input_raw), receipt_sha256=packets.digest(receipt),
                intent_ref_sha256=packets.digest(intent), state='bootstrapped',
                observed_at=now, expires_at=now+freshness))
            name = 'bootstrap-observation-'+packets.digest(proof)+'.json'
            try:
                self._save(fd, name, proof)
            except FileExistsError:
                if self._read(fd, name) != proof:
                    raise lifecycle.LifecycleError('bootstrap-observation-bytes-conflict')
        return proof

    def readback_bootstrap(self, input_raw, observation_sha256):
        packets._sha(observation_sha256)
        plan, descriptor_raw = self._bootstrap_input(input_raw)
        with self._root() as fd:
            control = plan['control_id']
            if self._read(fd, 'descriptor-'+control+'.json') != descriptor_raw:
                raise lifecycle.LifecycleError('bootstrap-independent-descriptor-drift')
            return (self._read(fd, 'bootstrap-input-'+control+'.json'),
                self._read(fd, 'bootstrap-intent-'+control+'.json'),
                self._read(fd, 'bootstrap-receipt-'+control+'.json'),
                self._read(fd, 'bootstrap-observation-'+observation_sha256+'.json'))


class SyntheticBootstrapFixtureLifecycle(preparation.SyntheticPreparedLifecycle):
    """Closed B1: prepare and bootstrap only; execution remains unavailable."""
    _kinds = lifecycle.BOOTSTRAP_FIXTURE_KINDS
    _gated_kinds = frozenset({'acquire', 'prepare-intent', 'prepared', 'bootstrap-intent', 'bootstrapped'})
    _extra_kinds = frozenset({'prepare-intent', 'prepared', 'bootstrap-intent', 'bootstrapped'})
    _admission_kind = 'admit-bootstrap-fixture'

    def _validate_backend(self, backend):
        if type(backend) is not SavedBootstrapBackend:
            raise lifecycle.LifecycleError('bootstrap-fixed-backend-required')

    def _mode(self):
        return dict(protocol_sha256=PROTOCOL_SHA, recipe_sha256=RECIPE_SHA,
            runtime_policy_sha256=self.policy_sha256, backend_instance_sha256=self.backend.instance_sha256)

    def input_bootstrap(self, *, now):
        governance._int(now)
        with self.store.locked() as fd:
            ledger, state = self._read(fd, now); fence = self._fence(fd)
            if state['owner'] is None or not ledger['attempts']:
                raise lifecycle.LifecycleError('bootstrap-owner-required')
            supervisor = ledger['supervisors'][ledger['attempts'][-1]['id']]
            if supervisor['stage'] != 'prepared':
                raise lifecycle.LifecycleError('bootstrap-prepared-required')
            self._current(ledger, now, 'read')
            saved = supervisor['preparation']
            raw = _input(saved['plan_bytes'].encode(), saved['descriptor_bytes'].encode())
            fence._snapshot()
            return raw

    def _extra_projection(self, entry, ref, attempt, supervisor):
        kind = entry['record']['kind']; payload = entry['record']['payload']
        if kind in ('prepare-intent', 'prepared'):
            return super()._extra_projection(entry, ref, attempt, supervisor)
        if kind == 'bootstrap-intent':
            governance._obj(payload, 'input_bytes')
            if supervisor['stage'] != 'prepared':
                raise lifecycle.LifecycleError('bootstrap-prepared-required')
            saved = supervisor['preparation']
            raw = preparation._raw(payload['input_bytes'])
            if raw != _input(saved['plan_bytes'].encode(), saved['descriptor_bytes'].encode()):
                raise lifecycle.LifecycleError('bootstrap-intent-already-established-or-drift')
            supervisor.update(stage=kind, bootstrap=dict(input_bytes=raw.decode(),
                intent_ref_bytes=packets.canonical(ref).decode(), receipt_bytes=None, observation_bytes=None))
        elif kind == 'bootstrapped':
            governance._obj(payload, 'receipt_bytes observation_bytes')
            if supervisor['stage'] != 'bootstrap-intent':
                raise lifecycle.LifecycleError('bootstrap-confirmation-phase-conflict')
            saved = supervisor['bootstrap']
            receipt = preparation._raw(payload['receipt_bytes'])
            observation = preparation._raw(payload['observation_bytes'])
            if receipt != _receipt(saved['input_bytes'].encode(), saved['intent_ref_bytes'].encode()):
                raise lifecycle.LifecycleError('bootstrap-receipt-binding-drift')
            proof = preparation._artifact(observation, OBSERVATION_FIELDS)
            governance._int(proof['observed_at']); governance._int(proof['expires_at'])
            expected = dict(schema_version=1, domain=DOMAIN,
                input_sha256=packets.digest(saved['input_bytes'].encode()), receipt_sha256=packets.digest(receipt),
                intent_ref_sha256=packets.digest(saved['intent_ref_bytes'].encode()), state='bootstrapped',
                observed_at=proof['observed_at'], expires_at=proof['expires_at'])
            now = ref['committed_at']; freshness = entry['request']['policy']['freshness_seconds']
            if (packets.canonical(proof) != packets.canonical(expected)
                    or not 0 <= now-proof['observed_at'] <= freshness
                    or not now < proof['expires_at'] <= proof['observed_at']+freshness):
                raise lifecycle.LifecycleError('bootstrap-observation-stale-or-drift')
            saved.update(receipt_bytes=receipt.decode(), observation_bytes=observation.decode())
            supervisor['stage'] = kind
        else:
            raise lifecycle.LifecycleError('bootstrap-operation-unavailable')
        attempt['status'] = 'unknown'

    def _extra_confirmation(self, fd, ledger, entry, now):
        super()._extra_confirmation(fd, ledger, entry, now)
        if entry['record']['kind'] == 'bootstrapped':
            saved = ledger['supervisors'][entry['request']['attempt_id']]['bootstrap']
            expected = tuple(saved[field].encode() for field in
                ('input_bytes', 'intent_ref_bytes', 'receipt_bytes', 'observation_bytes'))
            actual = self.backend.readback_bootstrap(expected[0], packets.digest(expected[-1]))
            if actual != expected:
                raise lifecycle.LifecycleError('bootstrap-independent-readback-unconfirmed')

    def bootstrap_prepared(self, operation_id, *, expected_revision, now):
        def bootstrap(fd, ledger):
            fence = self._fence(fd); caps = {}
            state = self._project(fd, ledger, now=now, _historical_caps=caps)
            attempt = ledger['attempts'][-1]
            request = governance._parse(trust._read(fd, 'lifecycle-'+attempt['request_sha256']+'.json', governance.MAX_EVIDENCE))
            self._effect_gate(fd, ledger, state, request, now, 'bootstrap-intent', historical_caps=caps)
            saved = ledger['supervisors'][attempt['id']]['bootstrap']
            fence._snapshot()
            self.backend.bootstrap(saved['input_bytes'].encode(), saved['intent_ref_bytes'].encode())
        return self._append(operation_id, 'bootstrap-intent', expected_revision=expected_revision, now=now, effect=bootstrap)

    def confirm_bootstrapped(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'bootstrapped', expected_revision=expected_revision, now=now)
