"""Closed anonymous native v6 host; no provider, credential or production loader.

The real PacketStore transaction owns every physical operation. Saved R1/B1/R2
records and observations cannot authorize this mode. The host reader is still a
synthetic authority; native execution does not qualify that reader for deployment.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import os

import agent_qualification as trust
import model_container_backend as containers
import model_control_archive as archive
import model_native_checkpoint_backend as native
import model_packet_bootstrap as bootstrap
import model_packet_governance as governance
import model_packet_lifecycle as lifecycle
import model_packet_preparation as preparation
import model_packet_store as packets

DOMAIN = 'anonymous-native-v6/1'
PROTOCOL_SHA = packets.digest(b'anonymous-native-v6-journal/1')
RECIPE_SHA = packets.digest(b'anonymous-native-two-attempt/1')
FINAL_PATCH = native.FIXED_PATCH.replace(b'+new\n', b'+done\n')
SOURCE = packets.canonical(containers.tree_manifest(containers.BASELINE))
_ISSUER = object()
DESCRIPTOR_FIELDS = ('schema_version domain plan_sha256 logical_control_id logical_nonce '
                     'runtime_binding physical_binding physical_descriptor')
OBSERVATION_FIELDS = ('schema_version domain plan_sha256 descriptor_sha256 '
                      'evidence_sha256 resource_state observed_at expires_at')
RUNTIME_FIELDS = ('schema_version domain binding runtime_state external_effects observed_at '
                  'expires_at evidence_sha256 descriptor_sha256 input_sha256 launch_ref_sha256')


class _Lease:
    """Non-serializable subject/action lease anchored to the actual stored prefix."""
    def __init__(self, issuer, backend, fence, attempt_id, action):
        if issuer is not _ISSUER or type(fence) is not packets._PlanningContext:
            raise lifecycle.LifecycleError('native-lease-issuer-required')
        self.backend, self.fence, self.attempt_id, self.action = backend, fence, attempt_id, action
        self.active = True
        self.created_cid = None
        self.fd, self.ledger = fence._snapshot()
        self._check()

    def _check(self):
        if not self.active or self.fence._store is not self.backend.store:
            raise lifecycle.LifecycleError('native-lease-expired')
        fd, current = self.fence._snapshot()
        if (current['schema_version'] != 6 or not current['attempts']
                or current['governance']['records'][0]['kind'] != 'admit-native'
                or packets.canonical(current) != packets.canonical(self.ledger)):
            raise lifecycle.LifecycleError('native-lease-prefix-or-mode-drift')
        attempt = next((a for a in current['attempts'] if a['id'] == self.attempt_id), None)
        if attempt is None:
            raise lifecycle.LifecycleError('native-lease-attempt-unavailable')
        supervisor = current['supervisors'][attempt['id']]
        for field in ('execution_request_sha256', 'request_sha256'):
            raw = trust._read(fd, 'lifecycle-'+attempt[field]+'.json', governance.MAX_EVIDENCE)
            if packets.digest(raw) != attempt[field]:
                raise lifecycle.LifecycleError('native-lease-original-bytes-drift')
        if self.action not in {'read', 'prepare', 'bootstrap', 'launch', 'export'}:
            raise lifecycle.LifecycleError('native-lease-action-invalid')
        if self.action != 'read':
            expected = {'prepare':'prepare-intent', 'bootstrap':'bootstrap-intent',
                        'launch':'launch-intent', 'export':'export-intent'}[self.action]
            if (attempt != current['attempts'][-1] or supervisor['stage'] != expected
                    or attempt['generation'] != current['generation']):
                raise lifecycle.LifecycleError('native-lease-owner-or-phase-drift')
        return fd, current, attempt, supervisor

    def _raw(self, name, limit=governance.MAX_EVIDENCE):
        fd, _, _, _ = self._check()
        result = trust._read(fd, name, limit)
        self._check()
        return result

    def _save(self, name, raw):
        fd, _, _, _ = self._check()
        if self.action == 'read':
            raise lifecycle.LifecycleError('native-read-lease-cannot-write')
        try:
            prior = trust._read(fd, name, max(packets.MAX_PATCH, packets.MAX_LEDGER))
        except FileNotFoundError:
            self.backend.store._immutable(fd, name, raw, _lifecycle_token=lifecycle._WRITE_TOKEN)
        else:
            if prior != raw:
                raise lifecycle.LifecycleError('native-artifact-bytes-conflict')
        self._check()

    def plan(self):
        _, _, _, supervisor = self._check()
        raw = supervisor['preparation']['plan_bytes'].encode()
        plan = preparation._artifact(raw, preparation.PLAN_FIELDS)
        if (plan['mode'] != self.backend.mode() or plan['runtime_binding']['attempt_id'] != self.attempt_id
                or plan['source_sha256'] != containers.source_digest()
                or plan['scope'] != 'fixed-native-two-attempt'
                or plan['acceptance_sha256'] != packets.digest(FINAL_PATCH)):
            raise lifecycle.LifecycleError('native-plan-authority-drift')
        return raw, plan

    def driver(self):
        _, _, attempt, _ = self._check()
        return self.backend.drivers['checkpoint' if attempt['predecessor_sha256'] is None else 'successor-checkpoint']

    def physical_binding(self):
        _, _, attempt, _ = self._check()
        _, plan = self.plan()
        request = governance._parse(self._raw('lifecycle-'+attempt['request_sha256']+'.json'))
        base = plan['runtime_binding']; driver = self.driver()
        value = dict(packet_id=base['packet_id'], identity_sha256=base['identity_sha256'],
            attempt_id=attempt['id'], generation=attempt['generation'], request_sha256=attempt['request_sha256'],
            target_sha256=base['target_sha256'], predecessor_sha256=attempt['predecessor_sha256'],
            source_sha256=request['source_sha256'], scope_sha256=packets.digest(plan['scope'].encode()),
            acceptance_sha256=plan['acceptance_sha256'], runtime_id=base['runtime_id'],
            host_id=driver.host_id, backend_id=driver.backend_id, policy_sha256=driver.policy_sha256)
        # Launcher rendering compares exact bytes after a canonical journal read.
        # Establish that same key order before creation, rather than normalizing
        # or weakening the later physical policy comparison.
        return governance._parse(packets.canonical(value))

    def descriptor(self):
        plan_raw, plan = self.plan()
        raw = self._raw('native-'+plan['control_id']+'.descriptor')
        value = preparation._artifact(raw, DESCRIPTOR_FIELDS)
        expected = dict(schema_version=1, domain=DOMAIN, plan_sha256=packets.digest(plan_raw),
            logical_control_id=plan['control_id'], logical_nonce=plan['nonce'],
            runtime_binding=plan['runtime_binding'], physical_binding=self.physical_binding(),
            physical_descriptor=value['physical_descriptor'])
        if value != expected:
            raise lifecycle.LifecycleError('native-descriptor-plan-drift')
        self.backend.store._validate_runtime_descriptor(value['physical_descriptor'], value['physical_binding'])
        _, _, _, supervisor = self._check()
        committed = supervisor['preparation']['descriptor_bytes']
        if committed is not None and committed.encode() != raw:
            raise lifecycle.LifecycleError('native-descriptor-journal-drift')
        return raw, value


class _Engine:
    """Every actual transport operation requires the driver's active lease."""
    def __init__(self, driver, actual):
        self.driver, self.actual = driver, actual

    def _call(self, name, *args, **kwargs):
        lease = self.driver._lease
        if lease is None:
            raise lifecycle.LifecycleError('native-engine-lease-required')
        lease._check()
        if name == 'archive':
            if len(args) != 4 or args[:2] != ('container','cp') or any(type(arg) is not str for arg in args):
                raise lifecycle.LifecycleError('native-archive-argv-denied')
        if name == 'image' and args != (self.driver.image_id,):
            raise lifecycle.LifecycleError('native-image-subject-denied')
        if name == 'volume' and args != ('control-'+lease.physical_binding()['runtime_id'],):
            raise lifecycle.LifecycleError('native-volume-subject-denied')
        if name == 'inspect' or name == 'archive' or name == 'command' and args[:2] in {('container','start'),('container','logs')}:
            cid = lease.created_cid if lease.action == 'prepare' else lease.descriptor()[1]['physical_descriptor']['container_id']
            if name == 'inspect': subject = args[0]
            elif name == 'command': subject = args[2]
            elif args[2] == '-': subject = args[3].split(':',1)[0]
            else: subject = args[2].split(':',1)[0]
            if cid is None or subject != cid:
                raise lifecycle.LifecycleError('native-cid-subject-denied')
            if name == 'archive':
                if args[2] == '-':
                    _, _, _, supervisor = lease._check()
                    if (lease.action != 'bootstrap' or args[3] != cid+':/control'
                            or set(kwargs) != {'input_bytes'}
                            or archive.read_control_file(kwargs['input_bytes'],'input.json')
                            != supervisor['bootstrap']['input_bytes'].encode()):
                        raise lifecycle.LifecycleError('native-archive-write-denied')
                elif (args[3] != '-' or kwargs
                      or args[2] not in {cid+':/control'+suffix for suffix in
                          ('','/input.json','/claim.json','/completion.json')}):
                    raise lifecycle.LifecycleError('native-archive-read-denied')
        if name in {'command', 'archive'}:
            allowed = (name == 'command' and args[:2] in {('volume','create'), ('container','create')}
                       and lease.action == 'prepare'
                       or name == 'command' and args[:2] == ('container','start') and lease.action == 'launch'
                       or name == 'command' and args[:2] == ('container','logs') and lease.action == 'read'
                       or name == 'archive' and args[:2] == ('container','cp')
                       and (args[2] != '-' or lease.action == 'bootstrap'))
            if not allowed:
                raise lifecycle.LifecycleError('native-engine-action-denied')
        result = getattr(self.actual, name)(*args, **kwargs)
        if name == 'command' and args[:2] == ('container','create'):
            cid = result.decode(); packets._sha(cid); lease.created_cid = cid
        lease._check()
        return result

    def identity(self): return self._call('identity')
    def image(self, value): return self._call('image', value)
    def volume(self, value): return self._call('volume', value)
    def inspect(self, value): return self._call('inspect', value)
    def command(self, *args): return self._call('command', *args)
    def archive(self, *args, **kwargs): return self._call('archive', *args, **kwargs)


class _Physical(native.OneShotNativeFixtureBackend):
    def __init__(self, *args, **kwargs):
        # Constructors perform only the existing fixed local identity/image preflight.
        self._lease = None
        self._preflight = True
        super().__init__(*args, **kwargs)
        self.engine = _Engine(self, self.engine)
        self._preflight = False

    def _capture(self):
        if self._lease is None:
            if self._preflight: return super()._capture()
            raise lifecycle.LifecycleError('native-capture-lease-required')
        self._lease._check()
        result = super()._capture()
        self._lease._check()
        return result

    def _walk(self, *args):
        if self._lease is None: raise lifecycle.LifecycleError('native-workspace-lease-required')
        self._lease._check()
        result = super()._walk(*args)
        self._lease._check()
        return result

    def _binding(self, binding):
        if self._lease is None or self._lease.driver() is not self or binding != self._lease.physical_binding():
            raise lifecycle.LifecycleError('native-physical-binding-not-leased')
        self._lease._check()
        return super()._binding(binding)

    def _packet_fd(self):
        if self._lease is None:
            raise lifecycle.LifecycleError('native-artifact-lease-required')
        return os.dup(self._lease._check()[0])

    def _save(self, binding, suffix, raw):
        self._binding(binding)
        required = 'prepare' if suffix == 'baseline' else 'export' if suffix in {'patch','export'} else None
        if required is None or self._lease.action != required:
            raise lifecycle.LifecycleError('native-artifact-phase-denied')
        self._lease._save('backend-'+binding['runtime_id']+'.'+suffix, raw)

    def _read(self, binding, suffix, limit):
        self._binding(binding)
        return self._lease._raw('backend-'+binding['runtime_id']+'.'+suffix, limit)

    def _admitted_runtime_descriptor(self, binding, descriptor):
        self._binding(binding)
        _, original = self._lease.descriptor()
        if descriptor != original['physical_descriptor']:
            raise lifecycle.LifecycleError('native-physical-descriptor-not-admitted')
        return copy.deepcopy(descriptor)

    def _admitted_bootstrap_digest(self, binding, descriptor, *, stage):
        self._admitted_runtime_descriptor(binding, descriptor)
        _, _, _, supervisor = self._lease._check()
        allowed = {'intent': {'bootstrap-intent'}, 'start-intent':
                   {'launch-intent','observed','export-intent','published','finished'}}
        if stage not in allowed or supervisor['stage'] not in allowed[stage]:
            raise lifecycle.LifecycleError('native-bootstrap-phase-denied')
        saved = supervisor['bootstrap']
        if stage == 'start-intent':
            self._lease.backend._bootstrap_chain(self._lease)
        return packets.digest(saved['input_bytes'].encode())

    def export_patch(self, binding, limit, descriptor):
        expected = {'example.txt':b'new\n' if self.native_case == 'checkpoint' else b'done\n',
                    'remove.txt':b'delete\n'}
        if self._walk(binding, descriptor) != expected:
            raise lifecycle.LifecycleError('native-fixed-postimage-drift')
        return containers.OneShotSyntheticContainerBackend.export_patch(self, binding, limit, descriptor)

    def read_sealed_patch(self, binding, limit, descriptor):
        reply = containers.OneShotSyntheticContainerBackend.read_sealed_patch(self, binding, limit, descriptor)
        if reply['patch'] != (native.FIXED_PATCH if self.native_case == 'checkpoint' else FINAL_PATCH):
            raise lifecycle.LifecycleError('native-fixed-patch-drift')
        return reply


class NativeBackend:
    """Exact host injection only; independently closed physical recipes."""
    synthetic_only = True
    requires_runtime_descriptor = requires_runtime_bootstrap = True

    def __init__(self, store, *, endpoint, image_id, capture_root, capture_ref, opt_in=False, _engine=None):
        if type(store) is not packets.PacketStore or opt_in is not True:
            raise lifecycle.LifecycleError('native-host-opt-in-required')
        self.store = store
        self.drivers = {case:_Physical(store, endpoint=endpoint, image_id=image_id, capture_root=capture_root,
            capture_ref=capture_ref, native_case=case, opt_in=True, _engine=_engine)
            for case in ('checkpoint','successor-checkpoint')}
        self.host_id = self.drivers['checkpoint'].host_id
        self.backend_id = 'anonymous-native-v6-v1'
        self.policy_sha256 = packets.digest(packets.canonical(dict(domain=DOMAIN,
            drivers={k:v.policy_sha256 for k,v in self.drivers.items()}, protocol=PROTOCOL_SHA, recipe=RECIPE_SHA)))
        with store.locked() as fd:
            self._inode = (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        self.instance_sha256 = packets.digest(packets.canonical(dict(policy=self.policy_sha256,
            packet=store.packet_id, inode=self._inode)))

    def mode(self):
        return dict(protocol_sha256=PROTOCOL_SHA, recipe_sha256=RECIPE_SHA,
            runtime_policy_sha256=self.policy_sha256, backend_instance_sha256=self.instance_sha256)

    @contextmanager
    def _transaction(self, fence, attempt_id, action):
        lease = _Lease(_ISSUER, self, fence, attempt_id, action)
        driver = lease.driver()
        if driver._lease is not None or self._inode != (os.fstat(lease.fd).st_dev, os.fstat(lease.fd).st_ino):
            raise lifecycle.LifecycleError('native-transaction-reentry-or-instance-drift')
        driver._lease = lease
        try:
            yield lease
            lease._check()
        finally:
            lease.active = False
            driver._lease = None

    def _save(self, lease, suffix, raw):
        _, plan = lease.plan()
        lease._save('native-'+plan['control_id']+'.'+suffix, raw)

    def _read(self, lease, suffix):
        _, plan = lease.plan()
        return lease._raw('native-'+plan['control_id']+'.'+suffix)

    def prepare(self, lease):
        plan_raw, plan = lease.plan(); _, _, attempt, _ = lease._check()
        predecessor = b''
        if attempt['predecessor_sha256'] is not None:
            raw = lease._raw('lifecycle-checkpoint-'+attempt['predecessor_sha256']+'.json')
            manifest = governance._parse(raw)
            if packets.digest(raw) != attempt['predecessor_sha256']:
                raise lifecycle.LifecycleError('native-predecessor-checkpoint-drift')
            predecessor = lease._raw('lifecycle-patch-'+manifest['patch_sha256'], packets.MAX_PATCH)
            if packets.digest(predecessor) != manifest['patch_sha256'] or predecessor != native.FIXED_PATCH:
                raise lifecycle.LifecycleError('native-predecessor-patch-drift')
        physical = lease.physical_binding(); descriptor = lease.driver().prepare(physical, predecessor)
        raw = packets.canonical(dict(schema_version=1, domain=DOMAIN, plan_sha256=packets.digest(plan_raw),
            logical_control_id=plan['control_id'], logical_nonce=plan['nonce'],
            runtime_binding=plan['runtime_binding'], physical_binding=physical, physical_descriptor=descriptor))
        self._save(lease, 'descriptor', raw)

    def preparation_evidence(self, lease, now, freshness):
        raw, descriptor = lease.descriptor()
        observed = lease.driver()._observed(descriptor['physical_binding'], descriptor['physical_descriptor'])
        if observed['State']['Status'] != 'created' or observed['State']['Running'] is not False:
            raise lifecycle.LifecycleError('native-preparation-not-created')
        proof = packets.canonical(dict(schema_version=1, domain=DOMAIN,
            plan_sha256=descriptor['plan_sha256'], descriptor_sha256=packets.digest(raw),
            evidence_sha256=packets.digest(packets.canonical(observed)), resource_state='created',
            observed_at=now, expires_at=now+freshness))
        return raw, proof

    def input_bootstrap(self, lease):
        _, descriptor = lease.descriptor()
        return lease.driver().bootstrap_input(descriptor['physical_binding'], descriptor['physical_descriptor'])

    def bootstrap(self, lease):
        _, _, _, supervisor = lease._check(); _, descriptor = lease.descriptor()
        saved = supervisor['bootstrap']; raw = saved['input_bytes'].encode()
        result = lease.driver().bootstrap(descriptor['physical_binding'], descriptor['physical_descriptor'], raw)
        self._save(lease, 'bootstrap-input', raw)
        self._save(lease, 'bootstrap-intent', saved['intent_ref_bytes'].encode())
        self._save(lease, 'bootstrap-receipt', packets.canonical(result))

    def _bootstrap_chain(self, lease):
        _, _, _, supervisor = lease._check(); _, descriptor = lease.descriptor()
        saved = supervisor['bootstrap']; raw = saved['input_bytes'].encode()
        intent = saved['intent_ref_bytes'].encode()
        expected = packets.canonical(dict(schema_version=1,
            descriptor_sha256=packets.digest(packets.canonical(descriptor['physical_descriptor'])),
            input_sha256=packets.digest(raw),
            volume_sha256=descriptor['physical_descriptor']['control_volume']['identity_sha256']))
        actual = (self._read(lease,'bootstrap-input'), self._read(lease,'bootstrap-intent'),
                  self._read(lease,'bootstrap-receipt'))
        if actual != (raw, intent, expected) or saved['receipt_bytes'] is not None and saved['receipt_bytes'].encode() != expected:
            raise lifecycle.LifecycleError('native-bootstrap-original-chain-drift')
        return actual

    def bootstrap_evidence(self, lease, now, freshness):
        raw, intent, receipt = self._bootstrap_chain(lease)
        if raw != self.input_bootstrap(lease):
            raise lifecycle.LifecycleError('native-bootstrap-readback-drift')
        _, descriptor = lease.descriptor()
        actual = archive.read_control_file(lease.driver().engine.archive('container','cp',
            descriptor['physical_descriptor']['container_id']+':/control/input.json','-'), 'input.json')
        if actual != raw:
            raise lifecycle.LifecycleError('native-bootstrap-physical-input-drift')
        proof = packets.canonical(dict(schema_version=1, domain=DOMAIN, input_sha256=packets.digest(raw),
            receipt_sha256=packets.digest(receipt), intent_ref_sha256=packets.digest(intent),
            state='bootstrapped', observed_at=now, expires_at=now+freshness))
        return receipt, proof

    def launch(self, lease):
        _, descriptor = lease.descriptor()
        lease.driver().launch(descriptor['physical_binding'], descriptor['physical_descriptor'])

    def inspect(self, lease, now, freshness):
        descriptor_raw, descriptor = lease.descriptor(); _, _, _, supervisor = lease._check()
        if supervisor['stage'] not in {'launch-intent','observed','export-intent','published','finished'}:
            raise lifecycle.LifecycleError('native-runtime-launch-intent-required')
        raw, _, _ = self._bootstrap_chain(lease)
        actual = lease.driver().inspect(descriptor['physical_binding'], descriptor['physical_descriptor'])
        return packets.canonical(dict(schema_version=1, domain=DOMAIN, binding=supervisor['binding'],
            runtime_state=actual['state'], external_effects=actual['external_effects'], observed_at=now,
            expires_at=now+freshness, evidence_sha256=actual['evidence_sha256'],
            descriptor_sha256=packets.digest(descriptor_raw), input_sha256=packets.digest(raw),
            launch_ref_sha256=supervisor['binding']['launch_ref_sha256']))

    def export_patch(self, lease):
        _, descriptor = lease.descriptor()
        return lease.driver().export_patch(descriptor['physical_binding'], packets.MAX_PATCH,
                                           descriptor['physical_descriptor'])

    def read_sealed_patch(self, lease):
        _, descriptor = lease.descriptor()
        return lease.driver().read_sealed_patch(descriptor['physical_binding'], packets.MAX_PATCH,
                                                descriptor['physical_descriptor'])['patch']


class NativeLifecycle(preparation.SyntheticPreparedLifecycle):
    """One v6 selection/rework/owner journal, with actual closed native effects."""
    _kinds = lifecycle.NATIVE_KINDS
    _gated_kinds = frozenset({'acquire','prepare-intent','prepared','bootstrap-intent','bootstrapped',
                            'launch-intent','export-intent','publish','finish'})
    _extra_kinds = frozenset({'prepare-intent','prepared','bootstrap-intent','bootstrapped'})
    _admission_kind = 'admit-native'
    _launch_stage = 'bootstrapped'

    def _validate_backend(self, backend):
        if type(backend) is not NativeBackend:
            raise lifecycle.LifecycleError('native-fixed-backend-required')

    def _mode(self): return self.backend.mode()

    @contextmanager
    def _lease(self, fd, attempt, action='read'):
        with self.backend._transaction(self._fence(fd), attempt['id'], action) as lease:
            yield lease

    def _confirmation(self, plan_raw, descriptor_raw, observation_raw, now, freshness):
        plan = preparation._artifact(plan_raw, preparation.PLAN_FIELDS)
        value = preparation._artifact(descriptor_raw, DESCRIPTOR_FIELDS)
        if (value['domain'] != DOMAIN or value['plan_sha256'] != packets.digest(plan_raw)
                or value['logical_control_id'] != plan['control_id'] or value['logical_nonce'] != plan['nonce']
                or value['runtime_binding'] != plan['runtime_binding']):
            raise lifecycle.LifecycleError('native-preparation-confirmation-drift')
        proof = preparation._artifact(observation_raw, OBSERVATION_FIELDS)
        expected = dict(schema_version=1, domain=DOMAIN, plan_sha256=packets.digest(plan_raw),
            descriptor_sha256=packets.digest(descriptor_raw), evidence_sha256=proof['evidence_sha256'],
            resource_state='created', observed_at=proof['observed_at'], expires_at=proof['expires_at'])
        packets._sha(proof['evidence_sha256'])
        self._fresh(proof, now, freshness)
        if proof != expected:
            raise lifecycle.LifecycleError('native-preparation-observation-drift')

    @staticmethod
    def _fresh(proof, now, freshness):
        governance._int(proof['observed_at']); governance._int(proof['expires_at'])
        if not 0 <= now-proof['observed_at'] <= freshness or not now < proof['expires_at'] <= proof['observed_at']+freshness:
            raise lifecycle.LifecycleError('native-observation-stale')

    def _extra_projection(self, entry, ref, attempt, supervisor):
        kind = entry['record']['kind']; payload = entry['record']['payload']
        if kind in {'prepare-intent','prepared'}:
            return super()._extra_projection(entry, ref, attempt, supervisor)
        if kind == 'bootstrap-intent':
            governance._obj(payload, 'input_bytes')
            if supervisor['stage'] != 'prepared':
                raise lifecycle.LifecycleError('native-bootstrap-prepared-required')
            raw = preparation._raw(payload['input_bytes']); saved = supervisor['preparation']
            original = governance._parse(preparation._raw(saved['descriptor_bytes']))
            descriptor = original['physical_descriptor']
            physical = original['physical_binding']
            expected = packets.canonical(dict(schema_version=1, binding=physical, nonce=descriptor['nonce'],
                volume=descriptor['control_volume']['name'], descriptor_sha256=packets.digest(packets.canonical(descriptor)),
                container_id=descriptor['container_id'], launcher_sha256=descriptor['launcher_sha256']))
            if raw != expected:
                raise lifecycle.LifecycleError('native-bootstrap-input-not-original')
            supervisor.update(stage=kind, bootstrap=dict(input_bytes=raw.decode(),
                intent_ref_bytes=packets.canonical(ref).decode(), receipt_bytes=None, observation_bytes=None))
        else:
            governance._obj(payload, 'receipt_bytes observation_bytes')
            if supervisor['stage'] != 'bootstrap-intent':
                raise lifecycle.LifecycleError('native-bootstrap-confirmation-phase-conflict')
            saved = supervisor['bootstrap']; descriptor = governance._parse(
                preparation._raw(supervisor['preparation']['descriptor_bytes']))
            receipt = preparation._raw(payload['receipt_bytes'])
            expected = packets.canonical(dict(schema_version=1,
                descriptor_sha256=packets.digest(packets.canonical(descriptor['physical_descriptor'])),
                input_sha256=packets.digest(saved['input_bytes'].encode()),
                volume_sha256=descriptor['physical_descriptor']['control_volume']['identity_sha256']))
            proof = preparation._artifact(preparation._raw(payload['observation_bytes']), bootstrap.OBSERVATION_FIELDS)
            observation = dict(schema_version=1, domain=DOMAIN, input_sha256=packets.digest(saved['input_bytes'].encode()),
                receipt_sha256=packets.digest(receipt), intent_ref_sha256=packets.digest(saved['intent_ref_bytes'].encode()),
                state='bootstrapped', observed_at=proof['observed_at'], expires_at=proof['expires_at'])
            self._fresh(proof, ref['committed_at'], entry['request']['policy']['freshness_seconds'])
            if receipt != expected or proof != observation:
                raise lifecycle.LifecycleError('native-bootstrap-confirmation-chain-drift')
            saved.update(receipt_bytes=receipt.decode(), observation_bytes=payload['observation_bytes'])
            supervisor['stage'] = kind
        attempt['status'] = 'unknown'

    def _extra_confirmation(self, fd, ledger, entry, now):
        kind = entry['record']['kind']
        if kind not in {'prepared','bootstrapped'}: return
        attempt = ledger['attempts'][-1]; saved = ledger['supervisors'][attempt['id']]
        # Candidate ledger has not been committed. Mint only from the actual prefix.
        with self._lease(fd, attempt) as lease:
            freshness = entry['request']['policy']['freshness_seconds']
            actual = (self.backend.preparation_evidence(lease, now, freshness) if kind == 'prepared'
                      else self.backend.bootstrap_evidence(lease, now, freshness))
            expected = tuple(saved['preparation' if kind == 'prepared' else 'bootstrap'][field].encode()
                             for field in (('descriptor_bytes','observation_bytes') if kind == 'prepared'
                                           else ('receipt_bytes','observation_bytes')))
            if actual != expected:
                raise lifecycle.LifecycleError('native-independent-confirmation-drift')

    def _effect_gate(self, fd, ledger, state, request, now, kind, **kwargs):
        # Avoid Prepared's unleased assert_instance; the physical lease rechecks
        # packet inode, capsule, daemon, image and complete descriptor policy.
        lifecycle.SyntheticLifecycle._effect_gate(self, fd, ledger, state, request, now, kind, **kwargs)
        if kind in {'export-intent','publish','finish'}:
            attempt = ledger['attempts'][-1]
            actual = self._inspect_runtime(fd, ledger, attempt)
            proof = self._runtime(actual, ledger['supervisors'][attempt['id']]['binding'], now,
                                  ledger['governance']['policy']['freshness_seconds'])
            entry = kwargs.get('current_entry')
            if (proof['runtime_state'] != 'stopped' or proof['external_effects'] != 'excluded'
                    or entry is not None and kind in {'publish','finish'} and actual != entry['evidence'].runtime):
                raise lifecycle.LifecycleError('native-final-runtime-readback-drift')

    def prepare_reserved(self, operation_id, *, expected_revision, now):
        def effect(fd, ledger):
            self._physical_effect(fd, ledger, now, 'prepare', self.backend.prepare)
        return self._append(operation_id, 'prepare-intent', expected_revision=expected_revision, now=now, effect=effect)

    def _physical_effect(self, fd, ledger, now, action, callback):
        attempt = ledger['attempts'][-1]; caps = {}
        state = self._project(fd, ledger, now=now, _historical_caps=caps)
        request = governance._parse(trust._read(fd, 'lifecycle-'+attempt['request_sha256']+'.json', governance.MAX_EVIDENCE))
        kind = {'prepare':'prepare-intent','bootstrap':'bootstrap-intent','launch':'launch-intent','export':'export-intent'}[action]
        self._effect_gate(fd, ledger, state, request, now, kind, historical_caps=caps)
        with self._lease(fd, attempt, action) as lease: callback(lease)

    def preparation_evidence(self, *, now):
        return self._evidence_readback(now, 'preparation_evidence')

    def bootstrap_evidence(self, *, now):
        return self._evidence_readback(now, 'bootstrap_evidence')

    def _evidence_readback(self, now, method):
        with self.store.locked() as fd:
            ledger, _ = self._read(fd, now); self._current(ledger, now, 'read')
            with self._lease(fd, ledger['attempts'][-1]) as lease:
                return getattr(self.backend, method)(lease, now, ledger['governance']['policy']['freshness_seconds'])

    def input_bootstrap(self, *, now):
        with self.store.locked() as fd:
            ledger, _ = self._read(fd, now); self._current(ledger, now, 'read')
            if ledger['supervisors'][ledger['attempts'][-1]['id']]['stage'] != 'prepared':
                raise lifecycle.LifecycleError('native-input-prepared-required')
            with self._lease(fd, ledger['attempts'][-1]) as lease: return self.backend.input_bootstrap(lease)

    def bootstrap_prepared(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'bootstrap-intent', expected_revision=expected_revision, now=now,
            effect=lambda fd, ledger:self._physical_effect(fd, ledger, now, 'bootstrap', self.backend.bootstrap))

    def confirm_bootstrapped(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'bootstrapped', expected_revision=expected_revision, now=now)

    def _launch_projection(self, entry, ref, attempt, supervisor):
        base = copy.deepcopy(supervisor['binding']); p = supervisor['preparation']; b = supervisor['bootstrap']
        supervisor['acquisition_binding'] = base
        supervisor['binding'] = dict(base, domain=DOMAIN,
            plan_sha256=packets.digest(p['plan_bytes'].encode()), descriptor_sha256=packets.digest(p['descriptor_bytes'].encode()),
            input_sha256=packets.digest(b['input_bytes'].encode()), intent_ref_sha256=packets.digest(b['intent_ref_bytes'].encode()),
            receipt_sha256=packets.digest(b['receipt_bytes'].encode()), launch_ref_sha256=packets.digest(packets.canonical(ref)))

    def launch_reserved(self, operation_id, *, expected_revision, now):
        return self._append(operation_id, 'launch-intent', expected_revision=expected_revision, now=now,
            effect=lambda fd, ledger:self._physical_effect(fd, ledger, now, 'launch', self.backend.launch))

    def _observe_allowed(self, stage):
        return stage in {'launch-intent','observed','export-intent','published'}

    def _before_governance(self, entry, attempts, supervisors):
        if entry['record']['kind'] == 'outcome' and (not attempts
                or entry['request']['attempt_id'] != attempts[-1]['id']
                or supervisors[attempts[-1]['id']]['runtime_sha256'] is None):
            raise lifecycle.LifecycleError('native-outcome-before-observation')

    def _runtime(self, raw, binding, now, freshness):
        value = governance._obj(governance._parse(raw), RUNTIME_FIELDS)
        if (type(value['schema_version']) is not int or value['schema_version'] != 1 or value['domain'] != DOMAIN
                or binding.get('domain') != DOMAIN or value['binding'] != binding
                or value['runtime_state'] not in {'stopped','unknown'} or value['external_effects'] != 'excluded'
                or any(value[k] != binding[k] for k in ('descriptor_sha256','input_sha256','launch_ref_sha256'))):
            raise lifecycle.LifecycleError('native-runtime-domain-or-chain-drift')
        packets._sha(value['evidence_sha256']); self._fresh(value, now, freshness)
        return value

    def _inspect_runtime(self, fd, ledger, attempt):
        # Stable original commit time makes independent confirmation byte-exact;
        # callers still validate freshness against their current operation time.
        now = ledger['governance']['records'][-1]['committed_at']
        with self._lease(fd, attempt) as lease:
            return self.backend.inspect(lease, now, ledger['governance']['policy']['freshness_seconds'])

    def runtime_evidence(self, *, now):
        with self.store.locked() as fd:
            ledger, _ = self._read(fd, now); self._current(ledger, now, 'read')
            return self._inspect_runtime(fd, ledger, ledger['attempts'][-1])

    def _read_sealed_patch(self, fd, ledger, attempt):
        with self._lease(fd, attempt) as lease: return self.backend.read_sealed_patch(lease)

    def _export_patch(self, fd, ledger, attempt):
        now = ledger['governance']['records'][-1]['committed_at']
        return self._physical_effect(fd, ledger, now, 'export', self.backend.export_patch)
