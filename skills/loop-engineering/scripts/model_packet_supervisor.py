"""Host-injected, default-off supervisor for durable isolated packet attempts.

No JSON configuration, backend registry, process launcher or production adapter
is provided here. A qualified host must implement launch(binding), inspect(binding),
export_patch(binding, limit), and read_sealed_patch(binding, limit). Reservation
launch must be bounded, non-reentrant and must not inherit packet/ledger file
descriptors. A launch timeout is unknown, never evidence that execution stopped.
IDs are minted and fsynced before launch and must locate the SAME runtime after
host restart. inspect must independently establish immutable runtime identity,
quiescence and exclusion of external effects. Export is a bounded sealed patch,
never a command against the worker's Git metadata.
"""
from __future__ import annotations
import copy
import os
import subprocess
import tempfile
import uuid

import model_packet_store as packets


def validate_patch(patch):
    """Parse only, in a fresh trusted directory, without touching parent source.

    Git is used as a syntax parser with user/system config and worker metadata
    excluded. This is neither application nor quality/scope approval.
    """
    if type(patch) is not bytes or len(patch) > packets.MAX_PATCH:
        raise packets.PacketError('invalid-supervisor-git-patch')
    # A stopped read-only/no-change attempt has a valid, sealed empty export.
    # Its proof, binding, digest and publication fences are unchanged.
    if patch == b'':
        return
    if not patch.startswith(b'diff --git ') or b'\x00' in patch:
        raise packets.PacketError('invalid-supervisor-git-patch')
    with tempfile.TemporaryDirectory(prefix='packet-patch-parse-') as directory:
        result = subprocess.run(['git', 'apply', '--numstat', '-'], input=patch,
            cwd=directory, env={'PATH': os.defpath, 'HOME': directory,
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                'LC_ALL': 'C'}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=10, check=False)
    if result.returncode != 0:
        raise packets.PacketError('invalid-supervisor-git-patch')


class PacketSupervisor:
    """An injected trusted backend; input data cannot select executable code.

    start is the only launch path. reconcile never launches, even for a crash
    before launch or an absent runtime. An ambiguous export is read back from
    the original backend seal; it is never requested again on restart.
    """
    def __init__(self, store, backend, *, host_id, backend_id, policy_sha256):
        packets._id(host_id); packets._id(backend_id); packets._sha(policy_sha256)
        self.store = store
        self.backend = backend
        self.host_id = host_id
        self.backend_id = backend_id
        self.policy_sha256 = policy_sha256
        self.descriptor_required = getattr(backend, 'requires_runtime_descriptor', False)
        self.bootstrap_required = getattr(backend, 'requires_runtime_bootstrap', False)
        if type(self.bootstrap_required) is not bool or self.bootstrap_required and not self.descriptor_required:
            raise packets.PacketError('invalid-runtime-bootstrap-policy')
        if type(self.descriptor_required) is not bool:
            raise packets.PacketError('invalid-runtime-descriptor-policy')

    def _current(self, attempt_id):
        ledger, record = self.store.supervisor_snapshot(attempt_id)
        binding = record['binding']
        if (record['schema_version'] >= 3) != self.descriptor_required or (record['schema_version'] == 4) != self.bootstrap_required:
            raise packets.PacketError('runtime-descriptor-policy-drift')
        if (binding['host_id'] != self.host_id or binding['backend_id'] != self.backend_id
                or binding['policy_sha256'] != self.policy_sha256):
            raise packets.PacketError('supervisor-host-policy-drift')
        if (ledger['attempts'][-1]['id'] != attempt_id
                or ledger['attempts'][-1]['status'] == 'quarantined'
                or ledger['generation'] != binding['generation']):
            raise packets.PacketError('stale-writer-result-rejected')
        self.store.validate_supervisor_fence(attempt_id, expected_revision=ledger['revision'],
            record_sha256=packets.digest(packets.canonical(record)))
        return ledger, record

    def _transition(self, attempt_id, ledger, record, stage):
        return self.store.supervisor_transition(attempt_id, stage,
            expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))

    def _unknown(self, attempt_id, reason):
        # Persistence failure propagates: never report that unknown was saved.
        self.store.observe_supervisor_unknown(attempt_id, reason)
        return {'outcome': 'unknown', 'reason': reason, 'attempt_id': attempt_id}

    def start(self, attempt_id, request_sha256, target_sha256, *, expected_revision,
              source_sha256, scope_sha256, acceptance_sha256):
        self.store.reserve_runtime(attempt_id, request_sha256, target_sha256,
            expected_revision=expected_revision, source_sha256=source_sha256,
            scope_sha256=scope_sha256, acceptance_sha256=acceptance_sha256,
            host_id=self.host_id, backend_id=self.backend_id, policy_sha256=self.policy_sha256,
            runtime_id='runtime-'+uuid.uuid4().hex, runtime_descriptor_required=self.descriptor_required, runtime_bootstrap_required=self.bootstrap_required)
        ledger, record = self._current(attempt_id)
        ledger, record = self._transition(attempt_id, ledger, record, 'launch-intent')
        reply_unknown = False
        unknown_reason = 'launch-reply-unknown'
        # The intent is already durable. Keep the packet lock across the bounded
        # host launch call so quarantine cannot precede a delayed stale launch.
        # Backends must not re-enter PacketStore or run an unbounded worker here.
        with self.store.locked() as fd:
            current = self.store._read(fd)
            self.store._supervisor_fence(current, attempt_id, ledger['revision'],
                packets.digest(packets.canonical(record)))
            if self.descriptor_required:
                try:
                    predecessor = (self.store._checkpoint_bytes(fd, current['checkpoint'], current)
                        if current['checkpoint'] is not None else b'')
                    descriptor = self.backend.prepare(copy.deepcopy(record['binding']), predecessor)
                except Exception:
                    reply_unknown = True
                    unknown_reason = 'prepare-reply-unknown'
                if not reply_unknown:
                    # Persistence failures propagate. A failed descriptor commit
                    # cannot be followed by start or guessed/repeated prepare.
                    ledger, record = self.store._bind_runtime_descriptor(fd, current, attempt_id, descriptor,
                        expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))
                    descriptor = self.store._runtime_descriptor(fd, record)
                    try:
                        if self.bootstrap_required:
                            unknown_reason = 'bootstrap-reply-unknown'
                            input_bytes = self.backend.bootstrap_input(copy.deepcopy(record['binding']), descriptor)
                            if type(input_bytes) is not bytes or not 0 < len(input_bytes) <= 16384:
                                raise packets.PacketError('invalid-runtime-bootstrap-input')
                            input_sha = packets.digest(input_bytes)
                            ledger, record = self.store._bootstrap_transition(fd, ledger, attempt_id, 'intent', input_sha)
                            receipt = self.backend.bootstrap(copy.deepcopy(record['binding']), descriptor, input_bytes)
                            ledger, record = self.store._bootstrap_transition(fd, ledger, attempt_id, 'ready', input_sha, receipt)
                            ledger, record = self.store._bootstrap_transition(fd, ledger, attempt_id, 'start-intent', input_sha)
                        unknown_reason = 'launch-reply-unknown'
                        self.backend.launch(copy.deepcopy(record['binding']), descriptor)
                    except Exception:
                        reply_unknown = True
            else:
                try:
                    self.backend.launch(copy.deepcopy(record['binding']))
                except Exception:
                    reply_unknown = True
        if reply_unknown:
            return self._unknown(attempt_id, unknown_reason)
        self._transition(attempt_id, ledger, record, 'observing')
        return self.reconcile(attempt_id)

    def _call_backend(self, method, binding, *args, descriptor=None):
        call = getattr(self.backend, method)
        return (call(copy.deepcopy(binding), *args, copy.deepcopy(descriptor))
                if self.descriptor_required else call(copy.deepcopy(binding), *args))

    def _inspect(self, binding, descriptor=None):
        proof = self._call_backend('inspect', binding, descriptor=descriptor)
        if (type(proof) is not dict or set(proof) != {'binding', 'runtime_identity_sha256',
                'state', 'external_effects', 'evidence_sha256'}
                or proof['binding'] != binding
                or proof['runtime_identity_sha256'] != packets.digest(packets.canonical(binding))):
            raise packets.PacketError('supervisor-runtime-identity-drift')
        if proof['state'] != 'stopped' or proof['external_effects'] != 'excluded':
            raise packets.PacketError('supervisor-runtime-not-quiescent')
        packets._sha(proof['evidence_sha256'])
        return proof

    def _export_reply(self, binding, reply):
        if (type(reply) is not dict or set(reply) != {'binding', 'patch', 'patch_sha256'}
                or reply['binding'] != binding or type(reply['patch']) is not bytes):
            raise packets.PacketError('supervisor-export-binding-drift')
        packets._sha(reply['patch_sha256'])
        if packets.digest(reply['patch']) != reply['patch_sha256']:
            raise packets.PacketError('supervisor-export-digest-drift')
        validate_patch(reply['patch'])
        return reply['patch']

    def reconcile(self, attempt_id):
        """Inspect original binding and recover only its original sealed patch."""
        ledger, record = self._current(attempt_id)
        if record['stage'] == 'reserved':
            return self._unknown(attempt_id, 'launch-not-established')
        binding = record['binding']
        descriptor = None
        try:
            if self.descriptor_required:
                descriptor = self.store.read_runtime_descriptor(attempt_id)
            proof = self._inspect(binding, descriptor)
        except Exception:
            if record['stage'] == 'published':
                raise packets.PacketError('supervisor-runtime-proof-unavailable') from None
            return self._unknown(attempt_id, 'runtime-proof-unavailable')
        if record['stage'] == 'launch-intent':
            ledger, record = self._transition(attempt_id, ledger, record, 'observing')
        if record['stage'] == 'observing':
            ledger, record = self._transition(attempt_id, ledger, record, 'export-intent')
            try:
                patch = self._export_reply(binding,
                    self._call_backend('export_patch', binding, packets.MAX_PATCH, descriptor=descriptor))
            except Exception:
                return self._unknown(attempt_id, 'export-reply-unknown')
            evidence = proof['evidence_sha256']
        elif record['stage'] == 'export-intent':
            try:
                patch, evidence = self.store.read_supervisor_artifact(attempt_id)
                validate_patch(patch)
            except FileNotFoundError:
                try:
                    patch = self._export_reply(binding,
                        self._call_backend('read_sealed_patch', binding, packets.MAX_PATCH, descriptor=descriptor))
                except Exception:
                    return self._unknown(attempt_id, 'sealed-export-unavailable')
                evidence = proof['evidence_sha256']
        else:
            patch, evidence = self.store.read_supervisor_artifact(attempt_id)
            validate_patch(patch)
        # Detect resumed worker/identity drift during export. Ledger CAS below
        # separately fences quarantine, successor generation and host changes.
        try:
            self._inspect(binding, descriptor)
        except Exception:
            if record['stage'] == 'published':
                raise packets.PacketError('supervisor-runtime-proof-unavailable') from None
            return self._unknown(attempt_id, 'runtime-proof-unavailable')
        if record['stage'] == 'export-intent':
            ledger, record = self.store.seal_supervisor_patch(attempt_id, patch, evidence,
                expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))
        if record['stage'] != 'published':
            ledger = self.store.publish_checkpoint(attempt_id, patch, evidence,
                expected_revision=ledger['revision'], supervisor_sha256=packets.digest(packets.canonical(record)))
        ledger, record = self._current(attempt_id)
        if (record['binding'] != binding or record['evidence_sha256'] != evidence
                or record['patch_sha256'] != packets.digest(patch)):
            raise packets.PacketError('supervisor-candidate-binding-drift')
        ledger, record, patch = self.store.read_supervisor_candidate(attempt_id,
            expected_revision=ledger['revision'], record_sha256=packets.digest(packets.canonical(record)))
        return {'outcome': 'integration-candidate', 'attempt_id': attempt_id,
                'checkpoint_sha256': ledger['checkpoint'], 'binding': copy.deepcopy(record['binding']),
                'patch_sha256': packets.digest(patch),
                'evidence_sha256': record['evidence_sha256'], 'patch': patch}

    def admit_candidate(self, attempt_id, *, source_sha256, scope_sha256, acceptance_sha256):
        """Parent binding gate only; does not apply source or approve quality."""
        for value in [source_sha256, scope_sha256, acceptance_sha256]:
            packets._sha(value)
        _, record = self._current(attempt_id)
        for key, value in [('source_sha256', source_sha256), ('scope_sha256', scope_sha256),
                           ('acceptance_sha256', acceptance_sha256)]:
            if record['binding'][key] != value:
                raise packets.PacketError('candidate-parent-binding-drift')
        if record['stage'] != 'published':
            raise packets.PacketError('candidate-not-sealed')
        candidate = self.reconcile(attempt_id)
        # Read again so a concurrent quarantine/successor cannot admit stale data.
        _, current = self._current(attempt_id)
        if (current['binding'] != record['binding'] or candidate['binding'] != record['binding']
                or current['stage'] != 'published'):
            raise packets.PacketError('candidate-parent-binding-drift')
        return candidate
