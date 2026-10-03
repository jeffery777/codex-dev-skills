"""Host-only R1 preparation fixture; no worker start, bootstrap or adoption.

The immutable journal mode, logical control and nonce precede one create.
Created/absent fixture files never establish stopped or never-started state.
No JSON loader, Docker/provider adapter or production qualification exists.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import os
import pathlib
import secrets

import agent_qualification as trust
import model_packet_governance as governance
import model_packet_lifecycle as lifecycle
import model_packet_store as packets

MAX_ARTIFACT = 16384
PROTOCOL_SHA = packets.digest(b'synthetic-preparation-journal/R1')
RECIPE_SHA = packets.digest(b'saved-preparation-fixture/R1')
MODE_FIELDS = 'protocol_sha256 recipe_sha256 runtime_policy_sha256 backend_instance_sha256'
PLAN_FIELDS = ('schema_version binding runtime_binding mode control_id nonce source_sha256 '
    'objective_sha256 scope acceptance_sha256 predecessor_sha256')
DESCRIPTOR_FIELDS = 'schema_version plan_sha256 runtime_binding mode control_id nonce instance_id resource_state'
OBSERVATION_FIELDS = 'schema_version plan_sha256 descriptor_sha256 control_id instance_id resource_state observed_at expires_at'


def _artifact(raw, fields):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_ARTIFACT:
        raise lifecycle.LifecycleError('preparation-artifact-bound')
    value = governance._obj(governance._parse(raw), fields)
    if type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise lifecycle.LifecycleError('preparation-artifact-version')
    return value


def _raw(value):
    if type(value) is not str:
        raise lifecycle.LifecycleError('preparation-artifact-bytes-required')
    raw = value.encode('utf-8')
    if not 0 < len(raw) <= MAX_ARTIFACT:
        raise lifecycle.LifecycleError('preparation-artifact-bound')
    return raw


def _nonce(value):
    if (type(value) is not str or len(value) != 32
            or any(c not in '0123456789abcdef' for c in value)):
        raise lifecycle.LifecycleError('preparation-nonce-invalid')


class SavedPreparationBackend:
    """Exact fixed host fixture with private, independently read saved artifacts.

    Its instance identity persists across host restart and binds the actual
    root inode. No process/container is created; R1 cannot inspect a writer.
    """
    synthetic_only = True
    requires_runtime_descriptor = True
    requires_runtime_bootstrap = True

    def __init__(self, root):
        self.root = pathlib.Path(root)
        self.prepare_count = 0
        with self._root() as fd:
            st = os.fstat(fd)
            try:
                raw = self._read(fd, 'backend-identity.json')
            except FileNotFoundError:
                raw = packets.canonical(dict(schema_version=1, nonce=secrets.token_hex(16),
                    device=st.st_dev, inode=st.st_ino))
                self._save(fd, 'backend-identity.json', raw)
                raw = self._read(fd, 'backend-identity.json')
            value = _artifact(raw, 'schema_version nonce device inode')
            _nonce(value['nonce'])
            if (type(value['device']) is not int or type(value['inode']) is not int
                    or value['device'] != st.st_dev or value['inode'] != st.st_ino):
                raise lifecycle.LifecycleError('preparation-backend-instance-drift')
            self._identity_raw = raw
            self._root_identity = (st.st_dev, st.st_ino)
            self.instance_sha256 = packets.digest(raw)

    @contextmanager
    def _root(self):
        fd = trust._directory(self.root)
        try:
            st = os.fstat(fd)
            if st.st_mode & 0o077:
                raise lifecycle.LifecycleError('preparation-backend-not-private')
            expected = getattr(self, '_root_identity', None)
            if expected is not None and (st.st_dev, st.st_ino) != expected:
                raise lifecycle.LifecycleError('preparation-backend-instance-drift')
            if expected is not None and self._read(fd, 'backend-identity.json') != self._identity_raw:
                raise lifecycle.LifecycleError('preparation-backend-instance-drift')
            yield fd
            current = os.stat(self.root, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (st.st_dev, st.st_ino):
                raise lifecycle.LifecycleError('preparation-backend-root-drift')
            if (getattr(self, '_identity_raw', None) is not None
                    and self._read(fd, 'backend-identity.json') != self._identity_raw):
                raise lifecycle.LifecycleError('preparation-backend-instance-drift')
        finally:
            os.close(fd)

    def _read(self, fd, name):
        st = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if st.st_mode & 0o077 or st.st_nlink != 1:
            raise lifecycle.LifecycleError('preparation-backend-artifact-not-private')
        return trust._read(fd, name, MAX_ARTIFACT)

    def _save(self, fd, name, raw):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_ARTIFACT:
            raise lifecycle.LifecycleError('preparation-artifact-bound')
        handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(handle, 'wb', closefd=False) as stream:
                stream.write(raw); stream.flush(); os.fsync(handle)
        finally:
            os.close(handle)
        os.fsync(fd)

    def assert_instance(self):
        with self._root() as fd:
            if self._read(fd, 'backend-identity.json') != self._identity_raw:
                raise lifecycle.LifecycleError('preparation-backend-instance-drift')

    def _plan(self, raw):
        plan = _artifact(raw, PLAN_FIELDS)
        governance._obj(plan['mode'], MODE_FIELDS)
        _nonce(plan['nonce']); packets._id(plan['control_id'])
        if (plan['mode']['protocol_sha256'] != PROTOCOL_SHA
                or plan['mode']['recipe_sha256'] != RECIPE_SHA
                or plan['mode']['backend_instance_sha256'] != self.instance_sha256):
            raise lifecycle.LifecycleError('preparation-backend-plan-drift')
        return plan

    def prepare(self, plan_raw):
        plan = self._plan(plan_raw); self.assert_instance()
        descriptor = packets.canonical(dict(schema_version=1, plan_sha256=packets.digest(plan_raw),
            runtime_binding=plan['runtime_binding'], mode=plan['mode'], control_id=plan['control_id'],
            nonce=plan['nonce'], instance_id='fixture-'+secrets.token_hex(16), resource_state='created'))
        with self._root() as fd:
            self._save(fd, 'descriptor-'+plan['control_id']+'.json', descriptor)
        self.prepare_count += 1
        # A return value is deliberately not a confirmation receipt.
        return None

    def observe_preparation(self, plan_raw, *, now, freshness):
        """Separate bounded host observation; never called by journal replay."""
        governance._int(now); governance._int(freshness)
        if freshness == 0:
            raise lifecycle.LifecycleError('preparation-freshness-required')
        plan = self._plan(plan_raw); self.assert_instance()
        with self._root() as fd:
            raw = self._read(fd, 'descriptor-'+plan['control_id']+'.json')
            descriptor = _artifact(raw, DESCRIPTOR_FIELDS)
            if descriptor['plan_sha256'] != packets.digest(plan_raw):
                raise lifecycle.LifecycleError('preparation-descriptor-plan-drift')
            proof = packets.canonical(dict(schema_version=1, plan_sha256=packets.digest(plan_raw),
                descriptor_sha256=packets.digest(raw), control_id=plan['control_id'],
                instance_id=descriptor['instance_id'], resource_state='created',
                observed_at=now, expires_at=now+freshness))
            # New immutable read-only observation, not another create intent.
            name = 'observation-'+packets.digest(proof)+'.json'
            try:
                self._save(fd, name, proof)
            except FileExistsError:
                if self._read(fd, name) != proof:
                    raise lifecycle.LifecycleError('preparation-observation-bytes-conflict')
        return proof

    def readback_preparation(self, plan_raw, observation_sha256):
        packets._sha(observation_sha256)
        plan = self._plan(plan_raw); self.assert_instance()
        with self._root() as fd:
            return (self._read(fd, 'descriptor-'+plan['control_id']+'.json'),
                self._read(fd, 'observation-'+observation_sha256+'.json'))

    def inspect(self, binding):
        raise lifecycle.LifecycleError('preparation-writer-state-unqualified')


class SyntheticPreparedLifecycle(lifecycle.SyntheticLifecycle):
    """Closed R1 mode; only admit, acquire, prepare and confirm are available."""
    _kinds = lifecycle.PREPARED_KINDS
    _gated_kinds = frozenset({'acquire', 'prepare-intent', 'prepared'})
    _admission_kind = 'admit-prepared'
    _archive_replays = True
    _current_schema1 = True

    def _validate_backend(self, backend):
        if type(backend) is not SavedPreparationBackend:
            raise lifecycle.LifecycleError('preparation-fixed-backend-required')

    def _mode(self):
        return dict(protocol_sha256=PROTOCOL_SHA, recipe_sha256=RECIPE_SHA,
            runtime_policy_sha256=self.policy_sha256, backend_instance_sha256=self.backend.instance_sha256)

    def admission_payload(self):
        return self._mode()

    def _expected_plan(self, ledger, operation_id, nonce, source_sha):
        if not ledger['attempts']:
            raise lifecycle.LifecycleError('preparation-owner-required')
        attempt = ledger['attempts'][-1]; supervisor = ledger['supervisors'][attempt['id']]
        return dict(schema_version=1, binding=lifecycle._binding(self.store, ledger, operation_id),
            runtime_binding=supervisor['binding'], mode=self._mode(),
            control_id='control-'+nonce, nonce=nonce,
            source_sha256=source_sha,
            objective_sha256=packets.digest(packets.canonical(ledger['governance']['objective'])),
            scope=ledger['governance']['objective']['scope'],
            acceptance_sha256=ledger['governance']['objective']['acceptance_sha256'],
            predecessor_sha256=attempt['predecessor_sha256'])

    def plan_preparation(self, operation_id, *, expected_revision, now):
        """Host-only data preparation; no resource effect or journal mutation."""
        packets._id(operation_id); governance._int(expected_revision); governance._int(now)
        with self.store.locked() as fd:
            ledger, state = self._read(fd, now); fence = self._fence(fd)
            if (ledger['revision'] != expected_revision or state['owner'] is None
                    or not ledger['attempts'] or ledger['supervisors'][ledger['attempts'][-1]['id']]['stage'] != 'reserved'
                    or any(ref['operation_id'] == operation_id for ref in ledger['governance']['records'])):
                raise lifecycle.LifecycleError('preparation-plan-phase-conflict')
            self._current(ledger, now, 'read')
            first = ledger['governance']['records'][0]
            request = governance._parse(trust._read(fd, 'lifecycle-'+first['request_sha256']+'.json', governance.MAX_EVIDENCE))
            result = packets.canonical(self._expected_plan(ledger, operation_id, secrets.token_hex(16), request['source_sha256']))
            _artifact(result, PLAN_FIELDS)
            fence._snapshot()
            return result

    def _extra_projection(self, entry, ref, attempt, supervisor):
        kind = entry['record']['kind']; payload = entry['record']['payload']
        if kind == 'prepare-intent':
            governance._obj(payload, 'plan_bytes')
            raw = _raw(payload['plan_bytes']); plan = _artifact(raw, PLAN_FIELDS)
            _nonce(plan['nonce'])
            expected = dict(schema_version=1, binding=ref['binding'], runtime_binding=supervisor['binding'],
                mode=self._mode(), control_id='control-'+plan['nonce'], nonce=plan['nonce'],
                source_sha256=entry['request']['source_sha256'],
                objective_sha256=packets.digest(packets.canonical(entry['request']['objective'])),
                scope=entry['request']['objective']['scope'], acceptance_sha256=entry['request']['objective']['acceptance_sha256'],
                predecessor_sha256=attempt['predecessor_sha256'])
            if supervisor['stage'] != 'reserved' or packets.canonical(plan) != packets.canonical(expected):
                raise lifecycle.LifecycleError('preparation-intent-already-established-or-drift')
            supervisor.update(stage='prepare-intent', preparation=dict(plan_bytes=raw.decode(),
                plan_sha256=packets.digest(raw), descriptor_bytes=None, observation_bytes=None))
            attempt['status'] = 'unknown'
        else:
            governance._obj(payload, 'descriptor_bytes observation_bytes')
            if supervisor['stage'] != 'prepare-intent':
                raise lifecycle.LifecycleError('preparation-confirmation-phase-conflict')
            raw = _raw(payload['descriptor_bytes']); observed = _raw(payload['observation_bytes'])
            saved = supervisor['preparation']; plan_raw = saved['plan_bytes'].encode()
            self._confirmation(plan_raw, raw, observed, ref['committed_at'], entry['request']['policy']['freshness_seconds'])
            saved.update(descriptor_bytes=raw.decode(), observation_bytes=observed.decode())
            supervisor['stage'] = 'prepared'
            # Creating a resource is not evidence that no writer exists.
            attempt['status'] = 'unknown'

    def _confirmation(self, plan_raw, descriptor_raw, observation_raw, now, freshness):
        plan = _artifact(plan_raw, PLAN_FIELDS); descriptor = _artifact(descriptor_raw, DESCRIPTOR_FIELDS)
        packets._id(descriptor['instance_id'])
        expected = dict(schema_version=1, plan_sha256=packets.digest(plan_raw),
            runtime_binding=plan['runtime_binding'], mode=plan['mode'], control_id=plan['control_id'],
            nonce=plan['nonce'], instance_id=descriptor['instance_id'], resource_state='created')
        if packets.canonical(descriptor) != packets.canonical(expected):
            raise lifecycle.LifecycleError('preparation-descriptor-binding-drift')
        value = _artifact(observation_raw, OBSERVATION_FIELDS)
        governance._int(value['observed_at']); governance._int(value['expires_at'])
        expected = dict(schema_version=1, plan_sha256=packets.digest(plan_raw),
            descriptor_sha256=packets.digest(descriptor_raw), control_id=plan['control_id'],
            instance_id=descriptor['instance_id'], resource_state='created',
            observed_at=value['observed_at'], expires_at=value['expires_at'])
        if (packets.canonical(value) != packets.canonical(expected)
                or not 0 <= now-value['observed_at'] <= freshness
                or not now < value['expires_at'] <= value['observed_at']+freshness):
            raise lifecycle.LifecycleError('preparation-observation-stale-or-drift')

    def _extra_confirmation(self, fd, ledger, entry, now):
        if entry['record']['kind'] == 'prepared':
            saved = ledger['supervisors'][entry['request']['attempt_id']]['preparation']
            descriptor, observation = self.backend.readback_preparation(saved['plan_bytes'].encode(),
                packets.digest(saved['observation_bytes'].encode()))
            if (descriptor != saved['descriptor_bytes'].encode() or observation != saved['observation_bytes'].encode()):
                raise lifecycle.LifecycleError('preparation-independent-readback-unconfirmed')

    def _governance_entry(self, entry):
        if entry['record']['kind'] != self._admission_kind:
            return entry
        mode = governance._obj(entry['record']['payload'], MODE_FIELDS)
        if packets.canonical(mode) != packets.canonical(self._mode()):
            raise lifecycle.LifecycleError('preparation-mode-policy-drift')
        normalized = copy.deepcopy(entry)
        normalized['record'].update(kind='admit', payload={})
        return normalized

    def _effect_gate(self, fd, ledger, state, request, now, kind, **kwargs):
        fence = self._fence(fd)
        self.backend.assert_instance()
        fence._snapshot()
        return super()._effect_gate(fd, ledger, state, request, now, kind, **kwargs)

    def admit_new(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, self._admission_kind, expected_revision=expected_revision, now=now)

    def prepare_reserved(self, operation_id, *, expected_revision, now):
        def prepare(fd, ledger):
            fence = self._fence(fd); caps = {}
            state = self._project(fd, ledger, now=now, _historical_caps=caps)
            attempt = ledger['attempts'][-1]
            request = governance._parse(trust._read(fd, 'lifecycle-'+attempt['request_sha256']+'.json', governance.MAX_EVIDENCE))
            self._effect_gate(fd, ledger, state, request, now, 'prepare-intent', historical_caps=caps)
            plan = ledger['supervisors'][attempt['id']]['preparation']['plan_bytes'].encode()
            fence._snapshot()
            self.backend.prepare(plan)
        return self._append(operation_id, 'prepare-intent', expected_revision=expected_revision, now=now, effect=prepare)

    def confirm_prepared(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'prepared', expected_revision=expected_revision, now=now)
