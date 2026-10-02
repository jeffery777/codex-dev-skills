"""Protected at-most-once packet records; no model selection or process control.

Only a trusted executor can establish quiescence and publish checkpoints. A
claim survives a crash indefinitely: expiry never proves that a writer stopped.
"""
from __future__ import annotations
from contextlib import contextmanager
import hashlib
import json
import os
import pathlib
import re
import time
import uuid

import agent_qualification as trust

MAX_LEDGER = 262144
MAX_PATCH = 8 * 1024 * 1024
MAX_ATTEMPTS = 128
IDENTIFIER = re.compile(r'[A-Za-z0-9_-]{1,80}\Z')
# Qualified host adapters only. JSON and worker output cannot register one.
PACKET_ISOLATION_ADAPTERS = {}


class PacketError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def _id(value):
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise PacketError('invalid-packet-identifier')


def _sha(value):
    if type(value) is not str or not trust.SHA.fullmatch(value):
        raise PacketError('invalid-packet-digest')


class PacketStore:
    """Root must already be adopted outside Git, owned and mode 0700.

    No method accepts a caller's stopped=true assertion. The trusted executor
    owns completion; this store establishes durability, not runtime truth.
    """
    def __init__(self, root, packet_id):
        _id(packet_id)
        self.root = pathlib.Path(root)
        self.packet_id = packet_id

    @contextmanager
    def locked(self):
        import fcntl
        fd = trust._directory(self.root)
        child = lock = None
        try:
            if os.fstat(fd).st_mode & 0o077:
                raise PacketError('packet-root-must-be-private')
            try:
                os.mkdir(self.packet_id, 0o700, dir_fd=fd)
                os.fsync(fd)
            except FileExistsError:
                pass
            child = os.open(self.packet_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            trust._check(os.fstat(child), directory=True)
            if os.fstat(child).st_mode & 0o077:
                raise PacketError('packet-directory-must-be-private')
            try:
                os.stat('.git', dir_fd=child, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise PacketError('repository-controlled-packet')
            lock = os.open('lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=child)
            trust._check(os.fstat(lock))
            if os.fstat(lock).st_mode & 0o077:
                raise PacketError('packet-lock-must-be-private')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise PacketError('packet-busy') from None
            yield child
        finally:
            if lock is not None:
                os.close(lock)
            if child is not None:
                os.close(child)
            os.close(fd)

    def _read(self, fd):
        try:
            raw = trust._read(fd, 'ledger.json', MAX_LEDGER)
        except FileNotFoundError:
            return None
        try:
            value = json.loads(raw, object_pairs_hook=trust._pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(PacketError('invalid-packet-json')))
            if type(value) is not dict or set(value) != {'schema_version', 'packet_id', 'identity_sha256', 'revision', 'attempts', 'checkpoint', 'generation'}:
                raise PacketError('invalid-packet-ledger')
            if type(value['schema_version']) is not int or value['schema_version'] != 2 or value['packet_id'] != self.packet_id:
                raise PacketError('invalid-packet-ledger')
            _sha(value['identity_sha256'])
            if type(value['revision']) is not int or value['revision'] < 0 or type(value['attempts']) is not list or len(value['attempts']) > MAX_ATTEMPTS:
                raise PacketError('invalid-packet-ledger')
            seen = set()
            previous_checkpoint = None
            for index, attempt in enumerate(value['attempts']):
                if type(attempt) is not dict or set(attempt) != {'id', 'request_sha256', 'target_sha256', 'predecessor_sha256', 'status', 'checkpoint_sha256', 'generation', 'isolation_sha256', 'isolation_adapter', 'execution_outcome'}:
                    raise PacketError('invalid-packet-attempt')
                _id(attempt['id'])
                if attempt['id'] in seen:
                    raise PacketError('duplicate-packet-attempt')
                seen.add(attempt['id'])
                for key in ['request_sha256', 'target_sha256']:
                    _sha(attempt[key])
                for key in ['predecessor_sha256', 'checkpoint_sha256']:
                    if attempt[key] is not None:
                        _sha(attempt[key])
                if type(attempt['generation']) is not int or attempt['generation'] != index+1:
                    raise PacketError('packet-generation-drift')
                if attempt['status'] not in {'claimed', 'checkpointed', 'unknown', 'quarantined'}:
                    raise PacketError('invalid-packet-status')
                expected_outcome = 'checkpoint-captured' if attempt['status'] == 'checkpointed' else 'unknown'
                if attempt['execution_outcome'] != expected_outcome:
                    raise PacketError('invalid-packet-outcome')
                if index < len(value['attempts'])-1 and attempt['status'] not in {'checkpointed', 'quarantined'}:
                    raise PacketError('multiple-pending-attempts')
                if attempt['predecessor_sha256'] != previous_checkpoint or (attempt['status'] == 'checkpointed') != (attempt['checkpoint_sha256'] is not None):
                    raise PacketError('packet-lineage-drift')
                if attempt['status'] == 'quarantined':
                    _sha(attempt['isolation_sha256'])
                    _id(attempt['isolation_adapter'])
                elif attempt['isolation_sha256'] is not None or attempt['isolation_adapter'] is not None:
                    raise PacketError('invalid-isolation-lineage')
                if attempt['checkpoint_sha256'] is not None:
                    previous_checkpoint = attempt['checkpoint_sha256']
            if type(value['generation']) is not int or value['generation'] != len(value['attempts']):
                raise PacketError('packet-generation-drift')
            if value['checkpoint'] is not None:
                _sha(value['checkpoint'])
            latest = next((a['checkpoint_sha256'] for a in reversed(value['attempts']) if a['checkpoint_sha256']), None)
            if value['checkpoint'] != latest:
                raise PacketError('packet-checkpoint-drift')
            return value
        except (ValueError, UnicodeError, RecursionError, TypeError, KeyError):
            raise PacketError('invalid-packet-ledger') from None

    def _write(self, fd, ledger):
        raw = canonical(ledger)
        if len(raw) > MAX_LEDGER:
            raise PacketError('packet-ledger-too-large')
        name = 'write-' + uuid.uuid4().hex
        output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        try:
            with os.fdopen(output, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, 'ledger.json', src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        except BaseException:
            # A crash artifact is harmless; never delete the recovery evidence.
            raise
        if trust._read(fd, 'ledger.json', MAX_LEDGER) != raw:
            raise PacketError('packet-ledger-readback-failed')

    def prepare(self, identity_sha256):
        _sha(identity_sha256)
        with self.locked() as fd:
            ledger = self._read(fd)
            if ledger is None:
                ledger = {'schema_version': 2, 'packet_id': self.packet_id,
                    'identity_sha256': identity_sha256, 'revision': 0, 'generation': 0, 'attempts': [], 'checkpoint': None}
                self._write(fd, ledger)
            elif ledger['identity_sha256'] != identity_sha256:
                raise PacketError('packet-identity-conflict')
            return ledger

    def claim(self, attempt_id, request_sha256, target_sha256, *, expected_revision):
        _id(attempt_id); _sha(request_sha256); _sha(target_sha256)
        if type(expected_revision) is not int or expected_revision < 0:
            raise PacketError('invalid-packet-revision')
        with self.locked() as fd:
            ledger = self._read(fd)
            if ledger is None:
                raise PacketError('packet-not-prepared')
            prior = next((a for a in ledger['attempts'] if a['id'] == attempt_id), None)
            if prior is not None:
                if prior['request_sha256'] != request_sha256 or prior['target_sha256'] != target_sha256:
                    raise PacketError('attempt-identity-conflict')
                return {'claimed': False, 'ledger': ledger, 'attempt': prior}
            if ledger['revision'] != expected_revision:
                raise PacketError('packet-revision-conflict')
            if ledger['attempts'] and ledger['attempts'][-1]['status'] not in {'checkpointed', 'quarantined'}:
                raise PacketError('predecessor-outcome-unknown')
            if len(ledger['attempts']) >= MAX_ATTEMPTS:
                raise PacketError('packet-attempt-bound')
            # Isolation is a live host property, not an everlasting assertion.
            # Recheck every retained unknown writer before a successor claim.
            for old in ledger['attempts']:
                if old['status'] == 'quarantined':
                    self._isolation_proof(ledger, old, old['isolation_adapter'])
            attempt = {'id': attempt_id, 'request_sha256': request_sha256, 'target_sha256': target_sha256,
                'predecessor_sha256': ledger['checkpoint'], 'status': 'claimed', 'checkpoint_sha256': None,
                'generation': ledger['generation']+1, 'isolation_sha256': None, 'isolation_adapter': None,
                'execution_outcome': 'unknown'}
            ledger['generation'] += 1
            ledger['attempts'].append(attempt); ledger['revision'] += 1
            self._write(fd, ledger)
            return {'claimed': True, 'ledger': ledger, 'attempt': attempt}

    def retain_unknown(self, attempt_id):
        _id(attempt_id)
        with self.locked() as fd:
            ledger = self._read(fd)
            if not ledger or not ledger['attempts'] or ledger['attempts'][-1]['id'] != attempt_id:
                raise PacketError('packet-attempt-mismatch')
            attempt = ledger['attempts'][-1]
            if attempt['status'] in {'checkpointed', 'quarantined'}:
                raise PacketError('checkpoint-already-published')
            if attempt['status'] != 'unknown':
                attempt['status'] = 'unknown'; ledger['revision'] += 1
                self._write(fd, ledger)
            return ledger

    def _isolation_proof(self, ledger, attempt, adapter_id):
        adapter = PACKET_ISOLATION_ADAPTERS.get(adapter_id)
        if adapter is None:
            raise PacketError('qualified-isolation-adapter-unavailable')
        binding = {'packet_id': self.packet_id, 'attempt_id': attempt['id'],
            'generation': attempt['generation'], 'identity_sha256': ledger['identity_sha256'],
            'target_sha256': attempt['target_sha256'], 'checkpoint_sha256': attempt['predecessor_sha256']}
        proof = adapter.readback_isolation(dict(binding))
        keys = set(binding) | {'schema_version', 'status', 'evidence_sha256', 'observed_at', 'expires_at', 'external_effects'}
        if type(proof) is not dict or set(proof) != keys or any(proof[k] != v for k, v in binding.items()):
            raise PacketError('isolation-readback-binding-mismatch')
        if type(proof['schema_version']) is not int or proof['schema_version'] != 1 or proof['status'] != 'isolated' or proof['external_effects'] != 'excluded':
            raise PacketError('writer-isolation-not-established')
        _sha(proof['evidence_sha256'])
        now = int(time.time())
        if (type(proof['observed_at']) is not int or type(proof['expires_at']) is not int
                or not 0 <= now-proof['observed_at'] <= 60 or not now < proof['expires_at'] <= now+60):
            raise PacketError('writer-isolation-readback-stale')
        return proof

    def quarantine(self, attempt_id, *, expected_revision, isolation_adapter_id):
        """Trusted supervisor only: revoke acceptance, retain unknown workspace.

        The adapter must independently prove that this writer cannot affect any
        successor, source, sealed checkpoint or external resource. No live file
        capture occurs; recovery uses the previously sealed checkpoint only.
        """
        _id(attempt_id); _id(isolation_adapter_id)
        if type(expected_revision) is not int or expected_revision < 0:
            raise PacketError('invalid-packet-revision')
        with self.locked() as fd:
            ledger = self._read(fd)
            if not ledger or ledger['revision'] != expected_revision:
                raise PacketError('packet-revision-conflict')
            if not ledger['attempts'] or ledger['attempts'][-1]['id'] != attempt_id:
                raise PacketError('packet-attempt-mismatch')
            attempt = ledger['attempts'][-1]
            if attempt['status'] not in {'claimed', 'unknown', 'quarantined'}:
                raise PacketError('packet-attempt-not-pending')
            proof = self._isolation_proof(ledger, attempt, isolation_adapter_id)
            if attempt['status'] == 'quarantined':
                if attempt['isolation_adapter'] != isolation_adapter_id:
                    raise PacketError('isolation-adapter-conflict')
                return ledger
            attempt['status'] = 'quarantined'
            attempt['isolation_sha256'] = digest(canonical(proof))
            attempt['isolation_adapter'] = isolation_adapter_id
            ledger['revision'] += 1
            self._write(fd, ledger)
            return ledger

    def publish_checkpoint(self, attempt_id, patch, evidence_sha256):
        """Trusted executor only, after independently established quiescence.

        No CLI exposes this method or accepts a caller's stop evidence.
        """
        _id(attempt_id); _sha(evidence_sha256)
        if type(patch) is not bytes or len(patch) > MAX_PATCH:
            raise PacketError('invalid-packet-patch')
        with self.locked() as fd:
            ledger = self._read(fd)
            if not ledger or not ledger['attempts'] or ledger['attempts'][-1]['id'] != attempt_id:
                raise PacketError('packet-attempt-mismatch')
            attempt = ledger['attempts'][-1]
            if attempt['status'] == 'quarantined':
                raise PacketError('stale-writer-result-rejected')
            # A prior quarantine is revocable. Recheck under the same lock
            # before accepting any successor artifact, including exact replay.
            for old in ledger['attempts']:
                if old['status'] == 'quarantined':
                    self._isolation_proof(ledger, old, old['isolation_adapter'])
            manifest = {'packet_id': self.packet_id, 'identity_sha256': ledger['identity_sha256'],
                        'request_sha256': attempt['request_sha256'], 'target_sha256': attempt['target_sha256'],
                        'attempt_id': attempt_id, 'patch_sha256': digest(patch),
                        'evidence_sha256': evidence_sha256, 'predecessor_sha256': attempt['predecessor_sha256'],
                        'generation': attempt['generation']}
            checkpoint = digest(canonical(manifest))
            if attempt['status'] == 'checkpointed':
                if attempt['checkpoint_sha256'] != checkpoint:
                    raise PacketError('checkpoint-identity-conflict')
                if self._checkpoint_bytes(fd, checkpoint, ledger) != patch:
                    raise PacketError('checkpoint-patch-drift')
                return ledger
            for name, raw in [(checkpoint+'.patch', patch), (checkpoint+'.json', canonical(manifest))]:
                staging = 'artifact-'+uuid.uuid4().hex
                output = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
                with os.fdopen(output, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                try:
                    # Atomic no-replace publication; a partial staging artifact
                    # cannot poison the immutable final checkpoint name.
                    os.link(staging, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
                except FileExistsError:
                    if trust._read(fd, name, MAX_PATCH) != raw:
                        raise PacketError('checkpoint-artifact-conflict')
                if trust._read(fd, name, MAX_PATCH) != raw:
                    raise PacketError('checkpoint-readback-failed')
            os.fsync(fd)
            attempt['status'] = 'checkpointed'; attempt['checkpoint_sha256'] = checkpoint
            attempt['execution_outcome'] = 'checkpoint-captured'
            ledger['checkpoint'] = checkpoint; ledger['revision'] += 1
            self._write(fd, ledger)
            return ledger

    def _checkpoint_bytes(self, fd, checkpoint, ledger):
        raw = trust._read(fd, checkpoint+'.json', MAX_LEDGER)
        if digest(raw) != checkpoint:
            raise PacketError('checkpoint-manifest-drift')
        manifest = json.loads(raw, object_pairs_hook=trust._pairs)
        if type(manifest) is not dict or set(manifest) != {'packet_id', 'identity_sha256', 'request_sha256', 'target_sha256', 'attempt_id', 'patch_sha256', 'evidence_sha256', 'predecessor_sha256', 'generation'}:
            raise PacketError('invalid-checkpoint-manifest')
        attempt = next((a for a in ledger['attempts'] if a['checkpoint_sha256'] == checkpoint), None)
        if (attempt is None or manifest['packet_id'] != self.packet_id
                or manifest['identity_sha256'] != ledger['identity_sha256']
                or any(manifest[k] != attempt[k] for k in ['request_sha256', 'target_sha256', 'predecessor_sha256', 'generation'])
                or manifest['attempt_id'] != attempt['id']):
            raise PacketError('checkpoint-authority-binding-mismatch')
        _id(manifest['attempt_id']); _sha(manifest['patch_sha256']); _sha(manifest['evidence_sha256'])
        if type(manifest['generation']) is not int or manifest['generation'] < 1:
            raise PacketError('invalid-checkpoint-generation')
        if manifest['predecessor_sha256'] is not None:
            _sha(manifest['predecessor_sha256'])
        patch = trust._read(fd, checkpoint+'.patch', MAX_PATCH)
        if digest(patch) != manifest['patch_sha256']:
            raise PacketError('checkpoint-patch-drift')
        return patch

    def read_checkpoint(self):
        with self.locked() as fd:
            ledger = self._read(fd)
            if ledger is None:
                raise PacketError('packet-not-prepared')
            checkpoint = ledger['checkpoint']
            if checkpoint is None:
                return ledger, b''
            for old in ledger['attempts']:
                if old['status'] == 'quarantined':
                    self._isolation_proof(ledger, old, old['isolation_adapter'])
            return ledger, self._checkpoint_bytes(fd, checkpoint, ledger)

    def create_attempt_directory(self, attempt_id):
        """Create an exclusive durable workspace holder for a claimed attempt."""
        _id(attempt_id)
        with self.locked() as fd:
            ledger = self._read(fd)
            if not ledger or not ledger['attempts'] or ledger['attempts'][-1]['id'] != attempt_id or ledger['attempts'][-1]['status'] != 'claimed':
                raise PacketError('packet-attempt-not-claimed')
            try:
                os.mkdir('attempt-'+attempt_id, 0o700, dir_fd=fd)
            except FileExistsError:
                raise PacketError('attempt-directory-already-exists') from None
            os.fsync(fd)
            return self.root/self.packet_id/('attempt-'+attempt_id)
