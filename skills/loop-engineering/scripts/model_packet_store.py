"""Protected at-most-once packet records; no model selection or process control.

Only a trusted executor can establish quiescence and publish checkpoints. A
claim survives a crash indefinitely: expiry never proves that a writer stopped.
"""
from __future__ import annotations
from contextlib import contextmanager
import copy
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
MAX_SUPERVISOR_OBSERVATIONS = 64
UNKNOWN_REASONS = frozenset({'launch-not-established', 'launch-reply-unknown',
    'runtime-proof-unavailable', 'export-reply-unknown', 'sealed-export-unavailable', 'prepare-reply-unknown', 'bootstrap-reply-unknown'})
SUPERVISOR_STAGES = frozenset({'reserved', 'launch-intent', 'observing', 'export-intent', 'sealed', 'published'})
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


class _PlanningContext:
    """Host-only, transaction-scoped legacy snapshot; no dispatch authority.

    Callers must retain the store lock and must not close its yielded dirFD.
    v5/v6 governance requires a separate fully validated journal reader.
    """
    def __init__(self, store, fd, lease):
        self._store = store
        self._root, self._packet_id = store.root, store.packet_id
        self._fd, self._lease = fd, lease
        self._inode = (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
        self._root_inode = (os.fstat(lease[2]).st_dev, os.fstat(lease[2]).st_ino)
        self._lock_inode = (os.fstat(lease[3]).st_dev, os.fstat(lease[3]).st_ino)
        self._ledger_raw = trust._read(fd, 'ledger.json', MAX_LEDGER)
        self._ledger = store._read(fd)
        if canonical(self._ledger) != canonical(json.loads(self._ledger_raw, object_pairs_hook=trust._pairs)):
            raise PacketError('planning-context-prefix-drift')

    def _snapshot(self):
        store = self._store
        if (store.root != self._root or store.packet_id != self._packet_id
                or store._planning_lease is not self._lease
                or self._lease is None or self._lease[1] != self._fd):
            raise PacketError('planning-context-expired-or-mismatched')
        # Walk every ancestor again, rather than stat() through a replaced root.
        root = trust._directory(self._root)
        child = None
        try:
            root_stat = os.fstat(root)
            if ((root_stat.st_dev, root_stat.st_ino) != self._root_inode
                    or root_stat.st_mode & 0o077):
                raise PacketError('planning-context-root-drift')
            child = os.open(self._packet_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            current = os.fstat(child); trust._check(current, directory=True)
            held = os.fstat(self._fd); trust._check(held, directory=True)
            lock = os.fstat(self._lease[3]); trust._check(lock)
            lock_path = os.stat('lock', dir_fd=child, follow_symlinks=False); trust._check(lock_path)
            if ((held.st_dev, held.st_ino) != self._inode
                    or (current.st_dev, current.st_ino) != self._inode
                    or (lock.st_dev, lock.st_ino) != self._lock_inode
                    or (lock_path.st_dev, lock_path.st_ino) != self._lock_inode
                    or (held.st_mode | current.st_mode | lock.st_mode | lock_path.st_mode) & 0o077
                    or trust._read(self._fd, 'ledger.json', MAX_LEDGER) != self._ledger_raw):
                raise PacketError('planning-context-prefix-or-lock-drift')
            if canonical(store._read(self._fd)) != canonical(self._ledger):
                raise PacketError('planning-context-prefix-drift')
            return self._fd, copy.deepcopy(self._ledger)
        finally:
            if child is not None:
                os.close(child)
            os.close(root)


class PacketStore:
    """Root must already be adopted outside Git, owned and mode 0700.

    No method accepts a caller's stopped=true assertion. The trusted executor
    owns completion; this store establishes durability, not runtime truth.
    """
    def __init__(self, root, packet_id, *, _trusted_isolation_adapters=None):
        _id(packet_id)
        self.root = pathlib.Path(root)
        self.packet_id = packet_id
        self._planning_lease = None
        # Synthetic host-owned code injection only. Normal consumers never
        # supply this argument; no JSON loader or production registry is added.
        adapters = {} if _trusted_isolation_adapters is None else _trusted_isolation_adapters
        if type(adapters) is not dict or len(adapters) > 16:
            raise PacketError('invalid-synthetic-isolation-adapters')
        self._trusted_isolation_adapters = dict(adapters)
        for name, adapter in self._trusted_isolation_adapters.items():
            _id(name)
            if (getattr(adapter, 'synthetic_only', False) is not True
                    or not callable(getattr(adapter, 'readback_isolation', None))):
                raise PacketError('invalid-synthetic-isolation-adapter')

    @contextmanager
    def locked(self):
        import fcntl
        fd = trust._directory(self.root)
        child = lock = None
        lease = None
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
            lease = (object(), child, fd, lock)
            self._planning_lease = lease
            yield child
        finally:
            if lease is not None and self._planning_lease is lease:
                self._planning_lease = None
            if lock is not None:
                os.close(lock)
            if child is not None:
                os.close(child)
            os.close(fd)

    def planning_context(self, fd):
        """Read a legacy snapshot under the caller-owned lock, never take a lock."""
        lease = self._planning_lease
        if type(fd) is not int or lease is None or lease[1] != fd:
            raise PacketError('planning-context-lock-required')
        context = _PlanningContext(self, fd, lease)
        context._snapshot()
        return context

    def _read(self, fd, *, _governance=False):
        try:
            raw = trust._read(fd, 'ledger.json', MAX_LEDGER)
        except FileNotFoundError:
            return None
        try:
            value = json.loads(raw, object_pairs_hook=trust._pairs,
                parse_constant=lambda _: (_ for _ in ()).throw(PacketError('invalid-packet-json')))
            if type(value) is dict and type(value.get('schema_version')) is int and value['schema_version'] == 5:
                # Governance reservations are not executor claims. Old readers
                # must not mistake empty actual attempts for a fresh retry, and
                # every old writer must stop before filesystem/runtime effects.
                from model_packet_governance import validate_ledger
                validate_ledger(value, self.packet_id)
                if _governance is not True:
                    raise PacketError('packet-governance-executor-unavailable')
                return value
            keys = {'schema_version', 'packet_id', 'identity_sha256', 'revision', 'attempts', 'checkpoint', 'generation'}
            if type(value) is not dict or type(value.get('schema_version')) is not int:
                raise PacketError('invalid-packet-ledger')
            if value['schema_version'] >= 3:
                keys.add('supervisors')
            if value['schema_version'] == 4:
                keys.add('integrations')
            if set(value) != keys:
                raise PacketError('invalid-packet-ledger')
            if type(value['schema_version']) is not int or value['schema_version'] not in {2, 3, 4} or value['packet_id'] != self.packet_id:
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
            if value['schema_version'] >= 3:
                self._validate_supervisors(value)
            if value['schema_version'] == 4:
                self._validate_integrations(value)
            return value
        except PacketError as error:
            if str(error) == 'packet-governance-executor-unavailable':
                raise
            raise PacketError('invalid-packet-ledger') from None
        except (ValueError, UnicodeError, RecursionError, TypeError, KeyError):
            raise PacketError('invalid-packet-ledger') from None

    def _write(self, fd, ledger, *, _governance_token=None):
        try:
            current = json.loads(trust._read(fd, 'ledger.json', MAX_LEDGER), object_pairs_hook=trust._pairs)
        except FileNotFoundError:
            current = None
        # Keep legacy host repair/write semantics; only the v5 discriminator
        # selects this extra guard. A downgrade cannot escape through _write.
        if ledger.get('schema_version') == 5 or type(current) is dict and current.get('schema_version') == 5:
            from model_packet_governance import _WRITE_TOKEN, validate_ledger
            if _governance_token is not _WRITE_TOKEN:
                raise PacketError('packet-governance-write-unavailable')
            validate_ledger(ledger, self.packet_id)
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

    def claim(self, attempt_id, request_sha256, target_sha256, *, expected_revision, _reservation=None):
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
                if _reservation is not None:
                    raise PacketError('supervisor-attempt-already-exists')
                return {'claimed': False, 'ledger': ledger, 'attempt': prior}
            if ledger['revision'] != expected_revision:
                raise PacketError('packet-revision-conflict')
            if ledger.get('integrations'):
                # This fixture has no qualified continuation against changed source.
                raise PacketError('source-integration-next-claim-unqualified')
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
            if _reservation is not None:
                ledger['schema_version'] = max(3, ledger['schema_version'])
                ledger.setdefault('supervisors', {})[attempt_id] = _reservation
                self._validate_supervisors(ledger)
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
        adapter = self._trusted_isolation_adapters.get(adapter_id) or PACKET_ISOLATION_ADAPTERS.get(adapter_id)
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

    def publish_checkpoint(self, attempt_id, patch, evidence_sha256, *,
                           expected_revision=None, supervisor_sha256=None):
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
            supervised = ledger.get('supervisors', {}).get(attempt_id)
            if supervised is not None:
                if (type(expected_revision) is not int or expected_revision != ledger['revision']
                        or supervisor_sha256 != digest(canonical(supervised))
                        or supervised['stage'] not in {'sealed', 'published'}):
                    raise PacketError('supervisor-publication-fence')
                sealed = self._sealed_bytes(fd, supervised)
                if sealed != patch or supervised['evidence_sha256'] != evidence_sha256:
                    raise PacketError('supervisor-artifact-conflict')
            elif expected_revision is not None or supervisor_sha256 is not None:
                raise PacketError('supervisor-reservation-unavailable')
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
            if supervised is not None:
                self._append_supervisor_observation(ledger, supervised, 'resolved', 'checkpoint-published',
                    stage='published', evidence_sha256=evidence_sha256, checkpoint_sha256=checkpoint)
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
            if supervised is not None:
                supervised['stage'] = 'published'
                self._validate_supervisors(ledger)
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


    def _validate_supervisors(self, ledger):
        records = ledger['supervisors']
        if type(records) is not dict or len(records) > MAX_ATTEMPTS:
            raise PacketError('invalid-supervisor-records')
        attempts = {a['id']: a for a in ledger['attempts']}
        runtime_ids = set()
        binding_keys = {'packet_id', 'attempt_id', 'identity_sha256', 'generation',
            'request_sha256', 'target_sha256', 'predecessor_sha256', 'source_sha256',
            'scope_sha256', 'acceptance_sha256', 'runtime_id', 'host_id', 'backend_id',
            'policy_sha256'}
        for attempt_id, record in records.items():
            if (attempt_id not in attempts or type(record) is not dict
                    or type(record.get('schema_version')) is not int or record['schema_version'] not in {1, 2, 3, 4}
                    or set(record) != ({'schema_version', 'binding', 'stage', 'patch_sha256', 'evidence_sha256'}
                        | ({'observations'} if record['schema_version'] >= 2 else set())
                        | ({'runtime_descriptor_sha256'} if record['schema_version'] >= 3 else set())
                        | ({'bootstrap'} if record['schema_version'] == 4 else set()))):
                raise PacketError('invalid-supervisor-record')
            binding = record['binding']; attempt = attempts[attempt_id]
            if type(binding) is not dict or set(binding) != binding_keys:
                raise PacketError('invalid-supervisor-binding')
            for key in ['packet_id', 'attempt_id', 'runtime_id', 'host_id', 'backend_id']:
                _id(binding[key])
            if binding['runtime_id'] in runtime_ids:
                raise PacketError('duplicate-supervisor-runtime')
            runtime_ids.add(binding['runtime_id'])
            for key in ['identity_sha256', 'request_sha256', 'target_sha256', 'source_sha256',
                        'scope_sha256', 'acceptance_sha256', 'policy_sha256']:
                _sha(binding[key])
            if (binding['packet_id'] != self.packet_id or binding['attempt_id'] != attempt_id
                    or binding['identity_sha256'] != ledger['identity_sha256']
                    or type(binding['generation']) is not int
                    or any(binding[k] != attempt[k] for k in ['generation', 'request_sha256',
                        'target_sha256', 'predecessor_sha256'])):
                raise PacketError('supervisor-binding-drift')
            if record['stage'] not in SUPERVISOR_STAGES:
                raise PacketError('invalid-supervisor-stage')
            sealed = record['stage'] in {'sealed', 'published'}
            for key in ['patch_sha256', 'evidence_sha256']:
                if sealed:
                    _sha(record[key])
                elif record[key] is not None:
                    raise PacketError('invalid-supervisor-artifact')
            if ((record['stage'] == 'published') != (attempt['status'] == 'checkpointed')
                    or attempt['status'] == 'checkpointed' and not sealed):
                raise PacketError('supervisor-publication-drift')
            if record['schema_version'] >= 2:
                self._validate_supervisor_observations(ledger, record, attempt)
            if record['schema_version'] >= 3:
                descriptor = record['runtime_descriptor_sha256']
                if descriptor is not None:
                    _sha(descriptor)
                elif record['stage'] not in {'reserved', 'launch-intent'}:
                    raise PacketError('runtime-descriptor-required')
            if record['schema_version'] == 4:
                bootstrap = record['bootstrap']
                if bootstrap is not None:
                    if (type(bootstrap) is not dict or set(bootstrap) != {'stage', 'input_sha256', 'receipt_sha256', 'chain_sha256'}
                            or bootstrap['stage'] not in {'intent', 'ready', 'start-intent'}):
                        raise PacketError('invalid-runtime-bootstrap')
                    _sha(bootstrap['input_sha256']); _sha(bootstrap['chain_sha256'])
                    if bootstrap['stage'] == 'intent':
                        if bootstrap['receipt_sha256'] is not None:
                            raise PacketError('invalid-runtime-bootstrap')
                    else:
                        _sha(bootstrap['receipt_sha256'])
                if record['stage'] not in {'reserved', 'launch-intent'} and (bootstrap is None or bootstrap['stage'] != 'start-intent'):
                    raise PacketError('runtime-bootstrap-required')

    def _validate_supervisor_observations(self, ledger, record, attempt):
        observations = record['observations']
        if type(observations) is not list or len(observations) > MAX_SUPERVISOR_OBSERVATIONS:
            raise PacketError('invalid-supervisor-observations')
        binding = record['binding']; previous_revision = 0; resolutions = 0
        keys = {'kind', 'reason', 'stage', 'binding_sha256', 'identity_sha256', 'runtime_id',
                'generation', 'revision', 'evidence_sha256', 'checkpoint_sha256'}
        for event in observations:
            if (type(event) is not dict or set(event) != keys
                    or event['stage'] not in SUPERVISOR_STAGES
                    or event['binding_sha256'] != digest(canonical(binding))
                    or any(event[key] != binding[key] for key in ['identity_sha256', 'runtime_id', 'generation'])
                    or type(event['generation']) is not int or type(event['revision']) is not int
                    or not previous_revision < event['revision'] <= ledger['revision']):
                raise PacketError('supervisor-observation-binding-drift')
            previous_revision = event['revision']
            if event['kind'] == 'unknown':
                if (event['reason'] not in UNKNOWN_REASONS or event['stage'] == 'published'
                        or event['evidence_sha256'] is not None or event['checkpoint_sha256'] is not None):
                    raise PacketError('invalid-supervisor-unknown-observation')
            elif event['kind'] == 'resolved':
                resolutions += 1
                if (event['reason'] != 'checkpoint-published' or event['stage'] != 'published'
                        or record['stage'] != 'published'
                        or event['evidence_sha256'] != record['evidence_sha256']
                        or event['checkpoint_sha256'] != attempt['checkpoint_sha256']):
                    raise PacketError('invalid-supervisor-resolution-observation')
                _sha(event['evidence_sha256']); _sha(event['checkpoint_sha256'])
            else:
                raise PacketError('invalid-supervisor-observation-kind')
        if resolutions != (1 if record['stage'] == 'published' else 0):
            raise PacketError('supervisor-resolution-history-drift')

    def _append_supervisor_observation(self, ledger, record, kind, reason, *, stage=None,
                                       evidence_sha256=None, checkpoint_sha256=None):
        if record['schema_version'] < 2:
            raise PacketError('supervisor-observation-schema-upgrade-required')
        binding = record['binding']
        event = {'kind': kind, 'reason': reason, 'stage': stage or record['stage'],
            'binding_sha256': digest(canonical(binding)), 'identity_sha256': binding['identity_sha256'],
            'runtime_id': binding['runtime_id'], 'generation': binding['generation'],
            'revision': ledger['revision']+1, 'evidence_sha256': evidence_sha256,
            'checkpoint_sha256': checkpoint_sha256}
        for old in record['observations']:
            if all(old[key] == value for key, value in event.items() if key != 'revision'):
                return False
        if len(record['observations']) >= MAX_SUPERVISOR_OBSERVATIONS:
            raise PacketError('supervisor-observation-bound')
        record['observations'].append(event)
        return True

    def observe_supervisor_unknown(self, attempt_id, reason):
        """Append a fixed non-sensitive unknown reason without erasing history."""
        _id(attempt_id)
        if type(reason) is not str or reason not in UNKNOWN_REASONS:
            raise PacketError('invalid-supervisor-unknown-reason')
        with self.locked() as fd:
            ledger = self._read(fd)
            record = (ledger or {}).get('supervisors', {}).get(attempt_id)
            if record is None:
                raise PacketError('supervisor-reservation-unavailable')
            self._supervisor_fence(ledger, attempt_id, ledger['revision'], digest(canonical(record)))
            attempt = ledger['attempts'][-1]
            if attempt['status'] == 'checkpointed':
                raise PacketError('checkpoint-already-published')
            appended = self._append_supervisor_observation(ledger, record, 'unknown', reason)
            if appended or attempt['status'] != 'unknown':
                attempt['status'] = 'unknown'; ledger['revision'] += 1
                self._validate_supervisors(ledger)
                self._write(fd, ledger)
            return ledger

    def reserve_runtime(self, attempt_id, request_sha256, target_sha256, *, expected_revision,
                        source_sha256, scope_sha256, acceptance_sha256, host_id,
                        backend_id, policy_sha256, runtime_id, runtime_descriptor_required=False, runtime_bootstrap_required=False):
        """Atomically claim a NEW attempt and persist its prelocatable binding.

        Existing v2 pending attempts are never upgraded or assigned a runtime.
        The host supplies opaque identity tokens, never commands or modules.
        """
        if type(runtime_descriptor_required) is not bool:
            raise PacketError('invalid-runtime-descriptor-policy')
        if type(runtime_bootstrap_required) is not bool or runtime_bootstrap_required and not runtime_descriptor_required:
            raise PacketError('invalid-runtime-bootstrap-policy')
        for identifier in [attempt_id, host_id, backend_id, runtime_id]:
            _id(identifier)
        for sha in [request_sha256, target_sha256, source_sha256, scope_sha256,
                    acceptance_sha256, policy_sha256]:
            _sha(sha)
        # Read is advisory only; claim's revision CAS binds this snapshot.
        with self.locked() as fd:
            ledger = self._read(fd)
            if ledger is None:
                raise PacketError('packet-not-prepared')
            binding = {'packet_id': self.packet_id, 'attempt_id': attempt_id,
                'identity_sha256': ledger['identity_sha256'], 'generation': ledger['generation']+1,
                'request_sha256': request_sha256, 'target_sha256': target_sha256,
                'predecessor_sha256': ledger['checkpoint'], 'source_sha256': source_sha256,
                'scope_sha256': scope_sha256, 'acceptance_sha256': acceptance_sha256,
                'host_id': host_id, 'backend_id': backend_id, 'policy_sha256': policy_sha256,
                'runtime_id': runtime_id}
        record = {'schema_version': 2, 'binding': binding, 'stage': 'reserved',
                  'patch_sha256': None, 'evidence_sha256': None, 'observations': []}
        if runtime_descriptor_required:
            record.update(schema_version=3, runtime_descriptor_sha256=None)
        if runtime_bootstrap_required:
            record.update(schema_version=4, bootstrap=None)
        return self.claim(attempt_id, request_sha256, target_sha256,
                          expected_revision=expected_revision, _reservation=record)

    def supervisor_snapshot(self, attempt_id):
        _id(attempt_id)
        with self.locked() as fd:
            ledger = self._read(fd)
            record = (ledger or {}).get('supervisors', {}).get(attempt_id)
            if record is None:
                raise PacketError('supervisor-reservation-unavailable')
            return ledger, record

    def _supervisor_fence(self, ledger, attempt_id, expected_revision, record_sha256):
        _id(attempt_id); _sha(record_sha256)
        if type(expected_revision) is not int or expected_revision < 0:
            raise PacketError('invalid-packet-revision')
        record = (ledger or {}).get('supervisors', {}).get(attempt_id)
        if (record is None or ledger['revision'] != expected_revision
                or digest(canonical(record)) != record_sha256):
            raise PacketError('supervisor-revision-conflict')
        if (not ledger['attempts'] or ledger['attempts'][-1]['id'] != attempt_id
                or ledger['generation'] != record['binding']['generation']
                or ledger['attempts'][-1]['status'] == 'quarantined'):
            raise PacketError('stale-writer-result-rejected')
        for old in ledger['attempts']:
            if old['status'] == 'quarantined':
                self._isolation_proof(ledger, old, old['isolation_adapter'])
        return record

    def validate_supervisor_fence(self, attempt_id, *, expected_revision, record_sha256):
        with self.locked() as fd:
            self._supervisor_fence(self._read(fd), attempt_id, expected_revision, record_sha256)

    def supervisor_transition(self, attempt_id, stage, *, expected_revision, record_sha256):
        transitions = {'reserved': {'launch-intent'}, 'launch-intent': {'observing'},
                       'observing': {'export-intent'}}
        with self.locked() as fd:
            ledger = self._read(fd)
            record = self._supervisor_fence(ledger, attempt_id, expected_revision, record_sha256)
            if stage not in transitions.get(record['stage'], set()):
                raise PacketError('invalid-supervisor-transition')
            record['stage'] = stage; ledger['revision'] += 1
            self._write(fd, ledger)
            return ledger, record

    def _immutable(self, fd, name, raw, *, _governance_token=None):
        from model_packet_governance import _WRITE_TOKEN
        # Internal legacy methods accepting an already-read ledger cannot seal
        # new evidence into a v5 packet before reaching the final write guard.
        self._read(fd, _governance=_governance_token is _WRITE_TOKEN)
        staging = 'artifact-'+uuid.uuid4().hex
        output = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(output, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        try:
            os.link(staging, name, src_dir_fd=fd, dst_dir_fd=fd, follow_symlinks=False)
        except FileExistsError:
            if trust._read(fd, name, max(MAX_LEDGER, MAX_PATCH)) != raw:
                raise PacketError('supervisor-artifact-conflict')
        if trust._read(fd, name, max(MAX_LEDGER, MAX_PATCH)) != raw:
            raise PacketError('supervisor-artifact-readback-failed')
        os.fsync(fd)

    def seal_supervisor_patch(self, attempt_id, patch, evidence_sha256, *, expected_revision, record_sha256):
        _sha(evidence_sha256)
        if type(patch) is not bytes or len(patch) > MAX_PATCH:
            raise PacketError('invalid-packet-patch')
        with self.locked() as fd:
            ledger = self._read(fd)
            record = self._supervisor_fence(ledger, attempt_id, expected_revision, record_sha256)
            if record['stage'] != 'export-intent':
                raise PacketError('invalid-supervisor-transition')
            manifest = {'schema_version': 1, 'binding': record['binding'],
                        'patch_sha256': digest(patch), 'evidence_sha256': evidence_sha256}
            prefix = 'sealed-'+record['binding']['runtime_id']
            self._immutable(fd, prefix+'.patch', patch)
            self._immutable(fd, prefix+'.json', canonical(manifest))
            record.update(stage='sealed', patch_sha256=digest(patch), evidence_sha256=evidence_sha256)
            ledger['revision'] += 1
            self._write(fd, ledger)
            return ledger, record

    def read_supervisor_artifact(self, attempt_id):
        """Read original immutable export after a crash; never execute a worker."""
        with self.locked() as fd:
            ledger = self._read(fd)
            record = (ledger or {}).get('supervisors', {}).get(attempt_id)
            if record is None:
                raise PacketError('supervisor-reservation-unavailable')
            if record['stage'] in {'sealed', 'published'}:
                return self._sealed_bytes(fd, record), record['evidence_sha256']
            prefix = 'sealed-'+record['binding']['runtime_id']
            raw = trust._read(fd, prefix+'.json', MAX_LEDGER)
            value = json.loads(raw, object_pairs_hook=trust._pairs)
            if (type(value) is not dict or set(value) != {'schema_version', 'binding', 'patch_sha256', 'evidence_sha256'}
                    or type(value['schema_version']) is not int or value['schema_version'] != 1
                    or value['binding'] != record['binding']):
                raise PacketError('supervisor-artifact-binding-drift')
            _sha(value['patch_sha256']); _sha(value['evidence_sha256'])
            patch = trust._read(fd, prefix+'.patch', MAX_PATCH)
            if digest(patch) != value['patch_sha256']:
                raise PacketError('supervisor-artifact-digest-drift')
            return patch, value['evidence_sha256']

    def _sealed_bytes(self, fd, record):
        prefix = 'sealed-'+record['binding']['runtime_id']
        raw = trust._read(fd, prefix+'.json', MAX_LEDGER)
        expected = {'schema_version': 1, 'binding': record['binding'],
                    'patch_sha256': record['patch_sha256'], 'evidence_sha256': record['evidence_sha256']}
        if raw != canonical(expected):
            raise PacketError('supervisor-artifact-binding-drift')
        patch = trust._read(fd, prefix+'.patch', MAX_PATCH)
        if digest(patch) != record['patch_sha256']:
            raise PacketError('supervisor-artifact-digest-drift')
        return patch


    def read_supervisor_candidate(self, attempt_id, *, expected_revision, record_sha256):
        """Read actual checkpoint and seal in one current-generation lock snapshot.

        A sealed export is not proof that the separately published checkpoint is
        intact. Missing, transplanted or corrupt checkpoint files cannot produce
        an integration candidate, including on replay and admission.
        """
        with self.locked() as fd:
            ledger = self._read(fd)
            record = self._supervisor_fence(ledger, attempt_id, expected_revision, record_sha256)
            if record['stage'] != 'published':
                raise PacketError('candidate-not-sealed')
            if record['schema_version'] >= 3:
                self._runtime_descriptor(fd, record)
                if record['schema_version'] == 4:
                    self._bootstrap_receipt(fd, record)
            binding = record['binding']
            expected_manifest = {'packet_id': self.packet_id,
                'identity_sha256': binding['identity_sha256'],
                'request_sha256': binding['request_sha256'], 'target_sha256': binding['target_sha256'],
                'attempt_id': attempt_id, 'patch_sha256': record['patch_sha256'],
                'evidence_sha256': record['evidence_sha256'],
                'predecessor_sha256': binding['predecessor_sha256'], 'generation': binding['generation']}
            checkpoint = ledger['attempts'][-1]['checkpoint_sha256']
            if checkpoint != ledger['checkpoint'] or checkpoint != digest(canonical(expected_manifest)):
                raise PacketError('supervisor-checkpoint-binding-drift')
            sealed = self._sealed_bytes(fd, record)
            patch = self._checkpoint_bytes(fd, checkpoint, ledger)
            if patch != sealed:
                raise PacketError('supervisor-checkpoint-patch-drift')
            return ledger, record, patch


    def _validate_runtime_descriptor(self, descriptor, binding):
        keys = {'schema_version', 'binding', 'container_id', 'daemon_identity_sha256',
                'image_id', 'created_at', 'workspace_sha256', 'workspace_identity_sha256', 'policy_sha256'}
        if type(descriptor) is dict and descriptor.get('schema_version') == 2:
            keys |= {'control_volume', 'nonce', 'launcher_sha256'}
        if (type(descriptor) is not dict or set(descriptor) != keys
                or type(descriptor['schema_version']) is not int or descriptor['schema_version'] not in {1, 2}
                or descriptor['binding'] != binding):
            raise PacketError('invalid-runtime-descriptor')
        for key in ['container_id', 'daemon_identity_sha256', 'workspace_sha256', 'workspace_identity_sha256', 'policy_sha256']:
            _sha(descriptor[key])
        if descriptor['policy_sha256'] != binding['policy_sha256']:
            raise PacketError('runtime-descriptor-policy-drift')
        if (type(descriptor['image_id']) is not str
                or not re.fullmatch(r'sha256:[0-9a-f]{64}', descriptor['image_id'])
                or type(descriptor['created_at']) is not str
                or not re.fullmatch(r'[0-9TZ:.+-]{1,64}', descriptor['created_at'])):
            raise PacketError('invalid-runtime-descriptor')
        if descriptor['schema_version'] == 2:
            _sha(descriptor['nonce']); _sha(descriptor['launcher_sha256'])
            volume = descriptor['control_volume']
            if (type(volume) is not dict or set(volume) != {'name', 'identity_sha256'}):
                raise PacketError('invalid-runtime-volume')
            _id(volume['name']); _sha(volume['identity_sha256'])

    def _bootstrap_transition(self, fd, ledger, attempt_id, stage, input_sha256, receipt=None):
        record = self._supervisor_fence(ledger, attempt_id, ledger['revision'], digest(canonical(ledger['supervisors'][attempt_id])))
        if record['schema_version'] != 4 or record['stage'] != 'launch-intent':
            raise PacketError('runtime-bootstrap-binding-rejected')
        descriptor = self._runtime_descriptor(fd, record)
        if descriptor['schema_version'] != 2:
            raise PacketError('runtime-bootstrap-descriptor-required')
        _sha(input_sha256)
        previous = record['bootstrap']
        expected = {None:'intent', 'intent':'ready', 'ready':'start-intent'}
        if expected.get(None if previous is None else previous['stage']) != stage:
            raise PacketError('invalid-runtime-bootstrap-transition')
        receipt_sha256 = None if previous is None else previous['receipt_sha256']
        if previous is not None and previous['input_sha256'] != input_sha256:
            raise PacketError('runtime-bootstrap-input-drift')
        if stage == 'ready':
            descriptor = self._runtime_descriptor(fd, record)
            if (type(receipt) is not dict or set(receipt) != {'schema_version','descriptor_sha256','input_sha256','volume_sha256'}
                    or receipt != {'schema_version':1,'descriptor_sha256':record['runtime_descriptor_sha256'],
                        'input_sha256':input_sha256,'volume_sha256':descriptor['control_volume']['identity_sha256']}):
                raise PacketError('runtime-bootstrap-receipt-drift')
            raw = canonical(receipt); receipt_sha256 = digest(raw)
            self._immutable(fd, 'bootstrap-'+receipt_sha256+'.json', raw)
        event={'schema_version':1,'stage':stage,'binding_sha256':digest(canonical(record['binding'])),
            'descriptor_sha256':record['runtime_descriptor_sha256'],'input_sha256':input_sha256,
            'receipt_sha256':receipt_sha256,'previous_sha256':None if previous is None else previous['chain_sha256']}
        event_raw=canonical(event); chain_sha=digest(event_raw)
        self._immutable(fd,'bootstrap-event-'+chain_sha+'.json',event_raw)
        record['bootstrap'] = {'stage':stage,'input_sha256':input_sha256,'receipt_sha256':receipt_sha256,'chain_sha256':chain_sha}
        ledger['revision'] += 1; self._validate_supervisors(ledger); self._write(fd, ledger)
        return ledger, record

    def _bootstrap_receipt(self, fd, record):
        if record['schema_version'] != 4 or record['bootstrap'] is None or record['bootstrap']['stage'] not in {'ready','start-intent'}:
            raise PacketError('runtime-bootstrap-not-ready')
        descriptor = self._runtime_descriptor(fd, record)
        bootstrap = record['bootstrap']
        chain_sha=bootstrap['chain_sha256']
        stages=['intent','ready']+(['start-intent'] if bootstrap['stage']=='start-intent' else [])
        for stage in reversed(stages):
            raw=trust._read(fd,'bootstrap-event-'+chain_sha+'.json',MAX_LEDGER)
            if digest(raw)!=chain_sha: raise PacketError('runtime-bootstrap-chain-drift')
            event=json.loads(raw,object_pairs_hook=trust._pairs)
            if type(event)is not dict or set(event)!={'schema_version','stage','binding_sha256','descriptor_sha256','input_sha256','receipt_sha256','previous_sha256'}:
                raise PacketError('runtime-bootstrap-chain-drift')
            previous=event['previous_sha256']
            if stage=='intent':
                if previous is not None: raise PacketError('runtime-bootstrap-chain-drift')
            else: _sha(previous)
            expected_event={'schema_version':1,'stage':stage,'binding_sha256':digest(canonical(record['binding'])),
                'descriptor_sha256':record['runtime_descriptor_sha256'],'input_sha256':bootstrap['input_sha256'],
                'receipt_sha256':None if stage=='intent' else bootstrap['receipt_sha256'],'previous_sha256':previous}
            if raw!=canonical(expected_event): raise PacketError('runtime-bootstrap-chain-drift')
            chain_sha=previous
        raw = trust._read(fd, 'bootstrap-'+bootstrap['receipt_sha256']+'.json', MAX_LEDGER)
        expected = {'schema_version':1,'descriptor_sha256':record['runtime_descriptor_sha256'],
            'input_sha256':bootstrap['input_sha256'],'volume_sha256':descriptor['control_volume']['identity_sha256']}
        if digest(raw) != bootstrap['receipt_sha256'] or raw != canonical(expected):
            raise PacketError('runtime-bootstrap-receipt-drift')
        return expected

    def _bind_runtime_descriptor(self, fd, ledger, attempt_id, descriptor, *, expected_revision, record_sha256):
        """Trusted prepare caller already holds this packet lock; no reentry.

        A container ID is immutable and fsynced in this SAME ledger before start.
        This method never prepares/recreates a runtime and cannot upgrade old
        schema 1/2 pending attempts into descriptor-backed execution.
        """
        record = self._supervisor_fence(ledger, attempt_id, expected_revision, record_sha256)
        if (record['schema_version'] not in {3, 4} or record['stage'] != 'launch-intent'
                or record['runtime_descriptor_sha256'] is not None):
            raise PacketError('runtime-descriptor-binding-rejected')
        self._validate_runtime_descriptor(descriptor, record['binding'])
        raw = canonical(descriptor)
        if len(raw) > MAX_LEDGER:
            raise PacketError('runtime-descriptor-bound')
        sha = digest(raw)
        self._immutable(fd, 'runtime-'+sha+'.json', raw)
        record['runtime_descriptor_sha256'] = sha; ledger['revision'] += 1
        self._validate_supervisors(ledger)
        self._write(fd, ledger)
        self._runtime_descriptor(fd, record)
        return ledger, record

    def _runtime_descriptor(self, fd, record):
        if record['schema_version'] not in {3, 4} or record['runtime_descriptor_sha256'] is None:
            raise PacketError('runtime-descriptor-unavailable')
        sha = record['runtime_descriptor_sha256']
        raw = trust._read(fd, 'runtime-'+sha+'.json', MAX_LEDGER)
        if digest(raw) != sha:
            raise PacketError('runtime-descriptor-digest-drift')
        descriptor = json.loads(raw, object_pairs_hook=trust._pairs)
        self._validate_runtime_descriptor(descriptor, record['binding'])
        return descriptor

    def read_runtime_descriptor(self, attempt_id):
        with self.locked() as fd:
            ledger = self._read(fd)
            record = (ledger or {}).get('supervisors', {}).get(attempt_id)
            if record is None:
                raise PacketError('supervisor-reservation-unavailable')
            self._supervisor_fence(ledger, attempt_id, ledger['revision'], digest(canonical(record)))
            return self._runtime_descriptor(fd, record)


    def _validate_integrations(self, ledger):
        records=ledger['integrations']
        if type(records)is not dict or len(records)>16:
            raise PacketError('invalid-source-integrations')
        candidates=set()
        for operation,record in records.items():
            _id(operation)
            keys={'schema_version','operation_id','attempt_id','generation','candidate_sha256','state',
                'intent_sha256','writer_started','result_sha256','observations'}
            if (type(record)is not dict or set(record)!=keys or type(record['schema_version'])is not int
                    or record['schema_version']!=1 or record['operation_id']!=operation
                    or record['state'] not in {'integration-intent','applied','not-applied','unknown'}
                    or type(record['writer_started'])is not bool):
                raise PacketError('invalid-source-integration-record')
            _id(record['attempt_id']); _sha(record['intent_sha256']); _sha(record['candidate_sha256'])
            if record['candidate_sha256'] in candidates: raise PacketError('duplicate-source-integration-candidate')
            candidates.add(record['candidate_sha256'])
            supervised=ledger['supervisors'].get(record['attempt_id'])
            if (supervised is None or supervised['stage']!='published' or type(record['generation'])is not int
                    or record['generation']!=supervised['binding']['generation']):
                raise PacketError('source-integration-binding-drift')
            expected_candidate={'outcome':'integration-candidate','attempt_id':record['attempt_id'],
                'checkpoint_sha256':next(attempt['checkpoint_sha256'] for attempt in ledger['attempts'] if attempt['id']==record['attempt_id']),'binding':supervised['binding'],
                'patch_sha256':supervised['patch_sha256'],'evidence_sha256':supervised['evidence_sha256']}
            if record['candidate_sha256']!=digest(canonical(expected_candidate)):
                raise PacketError('source-integration-candidate-drift')
            if record['state']=='integration-intent':
                if record['result_sha256']is not None: raise PacketError('invalid-source-integration-result')
            else: _sha(record['result_sha256'])
            observations=record['observations']
            if type(observations)is not list or not 1<=len(observations)<=16:
                raise PacketError('invalid-source-integration-observations')
            previous=0
            for event in observations:
                if (type(event)is not dict or set(event)!={'phase','revision','evidence_sha256'}
                        or event['phase']not in {'integration-intent','write-intent','applied','not-applied','unknown'}
                        or type(event['revision'])is not int or not previous<event['revision']<=ledger['revision']):
                    raise PacketError('invalid-source-integration-observations')
                _sha(event['evidence_sha256']); previous=event['revision']
            phases=[event['phase'] for event in observations]
            if (phases[0]!='integration-intent' or phases.count('integration-intent')!=1
                    or phases.count('write-intent')!=int(record['writer_started'])
                    or ('write-intent' in phases and phases.index('write-intent')!=1)
                    or (record['state']=='integration-intent' and phases[-1]not in {'integration-intent','write-intent'})
                    or (record['state']!='integration-intent' and (phases[-1]!=record['state'] or observations[-1]['evidence_sha256']!=record['result_sha256']))
                    or any(phase in {'applied','not-applied'} for phase in phases[:-1])):
                raise PacketError('invalid-source-integration-observations')

    def _validate_integration_intent(self,value):
        keys={'schema_version','kind','operation_id','binding','candidate_sha256','checkpoint_sha256','patch_sha256',
            'source_descriptor_sha256','source_identity_sha256','head','index_sha256','preimage','postimage',
            'preimage_sha256','postimage_sha256','authority_id','authority_sha256','validation_sha256','review_sha256',
            'integrator_sha256','scope_paths','no_effect'}
        if (type(value)is not dict or set(value)!=keys or type(value['schema_version'])is not int or value['schema_version']!=1
                or value['kind']!='synthetic-synchronous-source-integration' or type(value['no_effect'])is not bool
                or value['scope_paths']!=['added.txt','example.txt'] or type(value['binding'])is not dict
                or not re.fullmatch(r'[a-f0-9]{40}',value['head'])):
            raise PacketError('invalid-source-integration-intent')
        _id(value['operation_id']); _id(value['authority_id'])
        for key in keys:
            if key.endswith('_sha256'): _sha(value[key])
        for key in ['preimage','postimage']:
            manifest=value[key]
            if type(manifest)is not dict or not 1<=len(manifest)<=3 or set(manifest)-{'added.txt','example.txt','remove.txt'}:
                raise PacketError('invalid-source-integration-image')
            total=0
            for entry in manifest.values():
                if type(entry)is not dict or set(entry)!={'sha256','bytes'} or type(entry['bytes'])is not int or not 0<=entry['bytes']<=262144:
                    raise PacketError('invalid-source-integration-image')
                _sha(entry['sha256']); total+=entry['bytes']
            if total>1048576 or digest(canonical(manifest))!=value[key+'_sha256']:
                raise PacketError('invalid-source-integration-image')
        pre,post=value['preimage'],value['postimage']
        if not set(pre)<=set(post) or any(pre[name]!=post[name] for name in pre if name not in value['scope_paths']) or value['no_effect']!=(pre==post):
            raise PacketError('invalid-source-integration-image')

    def _validate_integration_result(self,result,record,intent,state):
        keys={'schema_version','operation_id','candidate_sha256','source_descriptor_sha256','state','reason','observed_image_sha256','effects'}
        reasons={'postimage-readback','authorized-noop','durable-intent-no-write','writer-or-readback-unknown','mixed-or-drift-or-unproven-preimage'}
        if (type(result)is not dict or set(result)!=keys or type(result['schema_version'])is not int or result['schema_version']!=1
                or result['operation_id']!=record['operation_id'] or result['candidate_sha256']!=record['candidate_sha256']
                or result['source_descriptor_sha256']!=intent['source_descriptor_sha256'] or result['state']!=state
                or result['reason']not in reasons or result['effects']!= {'applied':'bounded-add-update','not-applied':'none','unknown':'unknown'}[state]):
            raise PacketError('invalid-source-integration-result')
        image=result['observed_image_sha256']
        if image is not None: _sha(image)
        if state=='applied' and (intent['no_effect'] or image!=intent['postimage_sha256'] or result['reason']!='postimage-readback' or not record['writer_started']):
            raise PacketError('invalid-source-integration-result')
        if state=='not-applied' and (image!=intent['preimage_sha256'] or result['reason'] not in {'authorized-noop','durable-intent-no-write'}
                or (result['reason']=='authorized-noop')!=intent['no_effect'] or (record['writer_started'] and not intent['no_effect'])):
            raise PacketError('invalid-source-integration-result')
        if state=='unknown' and result['reason']not in {'writer-or-readback-unknown','mixed-or-drift-or-unproven-preimage'}:
            raise PacketError('invalid-source-integration-result')

    def _begin_integration(self, fd, ledger, attempt_id, operation_id, intent, *, expected_revision, record_sha256):
        _id(operation_id)
        record=self._supervisor_fence(ledger,attempt_id,expected_revision,record_sha256)
        if record['stage']!='published' or ledger.get('integrations'):
            raise PacketError('source-integration-not-ready-or-already-bound')
        if (type(intent)is not dict or intent.get('operation_id')!=operation_id
                or intent.get('binding')!=record['binding'] or intent.get('checkpoint_sha256')!=ledger['checkpoint']
                or intent.get('patch_sha256')!=record['patch_sha256']):
            raise PacketError('source-integration-intent-binding-drift')
        self._validate_integration_intent(intent)
        raw=canonical(intent)
        if len(raw)>65536: raise PacketError('source-integration-intent-bound')
        sha=digest(raw); self._immutable(fd,'integration-intent-'+sha+'.json',raw)
        integration={'schema_version':1,'operation_id':operation_id,'attempt_id':attempt_id,
            'generation':record['binding']['generation'],'candidate_sha256':intent['candidate_sha256'],
            'state':'integration-intent','intent_sha256':sha,'writer_started':False,'result_sha256':None,
            'observations':[{'phase':'integration-intent','revision':ledger['revision']+1,'evidence_sha256':sha}]}
        ledger['schema_version']=4; ledger['integrations']={operation_id:integration}; ledger['revision']+=1
        self._validate_integrations(ledger); self._write(fd,ledger)
        return ledger,integration

    def _integration_intent(self,fd,record,ledger):
        current=self._integration_fence(ledger,record['operation_id'],ledger['revision'])
        if record!=current: raise PacketError('source-integration-record-drift')
        raw=trust._read(fd,'integration-intent-'+record['intent_sha256']+'.json',65536)
        if digest(raw)!=record['intent_sha256']: raise PacketError('source-integration-intent-drift')
        value=json.loads(raw,object_pairs_hook=trust._pairs)
        if type(value)is not dict or value.get('operation_id')!=record['operation_id'] or value.get('candidate_sha256')!=record['candidate_sha256']:
            raise PacketError('source-integration-intent-drift')
        self._validate_integration_intent(value)
        supervised=ledger['supervisors'][record['attempt_id']]
        attempt=next(attempt for attempt in ledger['attempts'] if attempt['id']==record['attempt_id'])
        if (canonical(value['binding'])!=canonical(supervised['binding']) or value['checkpoint_sha256']!=attempt['checkpoint_sha256']
                or value['patch_sha256']!=supervised['patch_sha256']):
            raise PacketError('source-integration-intent-binding-drift')
        for event in record['observations']:
            if event['phase'] in {'integration-intent','write-intent'}:
                if event['evidence_sha256']!=record['intent_sha256']: raise PacketError('source-integration-history-drift')
            else:
                result_raw=trust._read(fd,'integration-result-'+event['evidence_sha256']+'.json',65536)
                if digest(result_raw)!=event['evidence_sha256']: raise PacketError('source-integration-history-drift')
                result=json.loads(result_raw,object_pairs_hook=trust._pairs)
                self._validate_integration_result(result,record,value,event['phase'])
        return value

    def _integration_fence(self,ledger,operation,expected_revision):
        if ledger is None or ledger['revision']!=expected_revision:
            raise PacketError('source-integration-revision-conflict')
        record=ledger.get('integrations',{}).get(operation)
        if record is None: raise PacketError('source-integration-unavailable')
        supervised=ledger['supervisors'][record['attempt_id']]
        self._supervisor_fence(ledger,record['attempt_id'],expected_revision,digest(canonical(supervised)))
        return record

    def _start_integration_write(self,fd,ledger,operation):
        record=self._integration_fence(ledger,operation,ledger['revision'])
        if record['state']!='integration-intent' or record['writer_started']:
            raise PacketError('source-integration-write-replay-rejected')
        if len(record['observations'])>=16: raise PacketError('source-integration-observation-bound')
        record['writer_started']=True; ledger['revision']+=1
        record['observations'].append({'phase':'write-intent','revision':ledger['revision'],'evidence_sha256':record['intent_sha256']})
        self._validate_integrations(ledger); self._write(fd,ledger)
        return ledger,record

    def _finish_integration(self,fd,ledger,operation,state,result):
        record=self._integration_fence(ledger,operation,ledger['revision'])
        if state not in {'applied','not-applied','unknown'}: raise PacketError('invalid-source-integration-state')
        intent=self._integration_intent(fd,record,ledger)
        self._validate_integration_result(result,record,intent,state)
        raw=canonical(result); sha=digest(raw)
        if len(raw)>65536: raise PacketError('source-integration-result-bound')
        if record['state']==state and record['result_sha256']==sha: return ledger,record
        if record['state']in {'applied','not-applied'}: raise PacketError('source-integration-final-result-conflict')
        if len(record['observations'])>=16: raise PacketError('source-integration-observation-bound')
        self._immutable(fd,'integration-result-'+sha+'.json',raw)
        record['state']=state; record['result_sha256']=sha; ledger['revision']+=1
        record['observations'].append({'phase':state,'revision':ledger['revision'],'evidence_sha256':sha})
        self._validate_integrations(ledger); self._write(fd,ledger)
        return ledger,record

    def integration_snapshot(self,operation):
        _id(operation)
        with self.locked() as fd:
            ledger=self._read(fd)
            if ledger is None: raise PacketError('source-integration-unavailable')
            record=self._integration_fence(ledger,operation,ledger['revision'])
            return ledger,record,self._integration_intent(fd,record,ledger)
