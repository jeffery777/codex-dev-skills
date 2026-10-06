"""Additional host restrictions for one anonymous native experiment.

This port issues no qualification or model/source authority. Its trusted origin
is the opt-in captured coordinator, not a JSON hash, PID, or private pathname.
The session lock is a liveness condition within that host TCB, not OS identity
attestation. Losing it neither kills a writer nor retracts an in-flight effect.
"""
from __future__ import annotations

import json
import os
import pathlib
import stat
import time
import uuid

import agent_qualification as trust
import model_packet_store as packets

BINDING_FILE = 'native-host-control.json'
PURPOSE = 'anonymous-native-experiment'
MAX_BYTES = 8192
MAX_DRIFT_NS = 5_000_000_000
_TOKEN = object()
_ACTIONS = frozenset({'read', 'admit-native', 'acquire', 'prepare-intent', 'prepared',
    'bootstrap-intent', 'bootstrapped', 'launch-intent', 'observe', 'outcome',
    'export-intent', 'publish', 'finish', 'prepare', 'bootstrap', 'launch', 'export'})


class ControlError(packets.PacketError):
    pass


def _clock():
    wall, mono = time.time_ns(), time.monotonic_ns()
    if any(type(v) is not int or not 0 < v < 2**63 for v in (wall, mono)):
        raise ControlError('native-host-clock-invalid')
    return dict(wall_ns=wall, monotonic_ns=mono)


def _inode(fd):
    value = os.fstat(fd)
    return [value.st_dev, value.st_ino]


def _private_directory(path):
    fd = trust._directory(path)
    if stat.S_IMODE(os.fstat(fd).st_mode) != 0o700:
        os.close(fd)
        raise ControlError('native-host-control-directory-not-private')
    return fd


def _file(fd, name):
    child = os.open(name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
    try:
        value = os.fstat(child)
        trust._check(value)
        if stat.S_IMODE(value.st_mode) != 0o600 or value.st_nlink != 1:
            raise ControlError('native-host-session-file-invalid')
        return child
    except BaseException:
        os.close(child)
        raise


class CoordinatorSession:
    """One live trusted coordinator; never reopen or recover a closed session."""
    def __init__(self, root, store, base_mode, objective_sha256, capture_sha256, *, ttl_seconds=300):
        import fcntl
        if type(store) is not packets.PacketStore or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= 600:
            raise ControlError('native-host-issuance-contract')
        packets._sha(objective_sha256); packets._sha(capture_sha256)
        if type(base_mode) is not dict or set(base_mode) != {
                'protocol_sha256', 'recipe_sha256', 'runtime_policy_sha256', 'backend_instance_sha256'}:
            raise ControlError('native-host-issuance-mode')
        for value in base_mode.values(): packets._sha(value)
        self.root = pathlib.Path(root)
        self.fd = self.session_fd = None
        self.reference = None
        try:
            self.fd = _private_directory(self.root)
            with store.locked() as packet_fd:
                prefix = json.loads(trust._read(packet_fd, 'ledger.json', packets.MAX_LEDGER),
                    object_pairs_hook=trust._pairs)
                if type(prefix) is not dict or prefix.get('schema_version') != 2:
                    raise ControlError('native-host-issuance-requires-unused-packet')
                ledger = store._read(packet_fd)
                if (ledger is None or ledger['schema_version'] != 2 or ledger['revision'] != 0
                        or ledger['attempts'] or ledger['checkpoint'] is not None):
                    raise ControlError('native-host-issuance-requires-unused-packet')
                self.session_fd = os.open('session.json', os.O_RDWR | os.O_CREAT | os.O_EXCL |
                    os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.fd)
                os.set_inheritable(self.session_fd, False)
                fcntl.flock(self.session_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                issued = _clock()
                permit = dict(schema_version=1, purpose=PURPOSE, qualification=False,
                    nonce=uuid.uuid4().hex, issuer_capture_sha256=capture_sha256,
                    packet_id=store.packet_id, packet_inode=_inode(packet_fd),
                    packet_root=str(store.root), identity_sha256=ledger['identity_sha256'],
                    objective_sha256=objective_sha256, base_mode=base_mode,
                    issued=issued, ttl_seconds=ttl_seconds)
                raw = packets.canonical(permit)
                with os.fdopen(os.dup(self.session_fd), 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
                os.fsync(self.fd)
                self.reference = dict(root=str(self.root), root_inode=_inode(self.fd),
                    session_inode=_inode(self.session_fd), permit_sha256=packets.digest(raw))
                binding = packets.canonical(self.reference)
                clock_fd = os.open('clock.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                    os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.fd)
                with os.fdopen(clock_fd, 'wb') as stream:
                    stream.write(packets.canonical(dict(reference_sha256=packets.digest(binding), clock=issued)))
                    stream.flush(); os.fsync(stream.fileno())
                os.fsync(self.fd)
                store._immutable(packet_fd, BINDING_FILE, binding)
            self.control = NativeHostControl(self.root, self.reference, _token=_TOKEN)
        except BaseException:
            self.close()
            raise

    def close(self):
        for name in ('session_fd', 'fd'):
            value = getattr(self, name, None)
            if value is not None:
                os.close(value)
                setattr(self, name, None)

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class NativeHostControl:
    """Non-qualifying restriction capability supplied by a trusted coordinator."""
    def __init__(self, root, reference, *, _token=None):
        if _token is not _TOKEN:
            raise ControlError('native-host-coordinator-reference-required')
        self.root = pathlib.Path(root)
        # Keep original bytes: caller mutation cannot redirect the capability.
        self._reference_raw = packets.canonical(reference)
        self._last_clock = None
        self.samples = []
        self._read_session()

    @classmethod
    def _from_captured_stage(cls, root, reference):
        """Only the captured verifier's verified coordinator request calls this.

        No external JSON loader, provider adapter or qualification entry uses
        this factory. The protected exact reference plus live issuer is required.
        """
        return cls(root, reference, _token=_TOKEN)

    @property
    def reference_sha256(self): return packets.digest(self._reference_raw)

    def _read_session(self):
        import fcntl
        # Strict duplicate-key parsing uses the existing trusted loader.
        reference = json.loads(self._reference_raw, object_pairs_hook=trust._pairs)
        if (type(reference) is not dict or set(reference) != {'root', 'root_inode', 'session_inode', 'permit_sha256'}
                or reference['root'] != str(self.root)):
            raise ControlError('native-host-reference-shape')
        packets._sha(reference['permit_sha256'])
        for name in ('root_inode', 'session_inode'):
            value = reference[name]
            if type(value) is not list or len(value) != 2 or any(type(v) is not int or v < 0 for v in value):
                raise ControlError('native-host-reference-inode-shape')
        fd = _private_directory(self.root)
        child = None
        try:
            if _inode(fd) != reference['root_inode']:
                raise ControlError('native-host-root-drift')
            child = _file(fd, 'session.json')
            if _inode(child) != reference['session_inode']:
                raise ControlError('native-host-session-inode-drift')
            raw = trust._read(fd, 'session.json', MAX_BYTES)
            if packets.digest(raw) != reference['permit_sha256']:
                raise ControlError('native-host-permit-drift')
            try:
                fcntl.flock(child, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise ControlError('native-host-coordinator-session-unavailable')
            permit = json.loads(raw, object_pairs_hook=trust._pairs)
            if (set(permit) != {'schema_version', 'purpose', 'qualification', 'nonce',
                    'issuer_capture_sha256', 'packet_id', 'packet_inode', 'packet_root',
                    'identity_sha256', 'objective_sha256', 'base_mode', 'issued', 'ttl_seconds'}
                    or type(permit['schema_version']) is not int or permit['schema_version'] != 1
                    or permit['purpose'] != PURPOSE or permit['qualification'] is not False):
                raise ControlError('native-host-permit-shape')
            if (type(permit['ttl_seconds']) is not int or not 1 <= permit['ttl_seconds'] <= 600
                    or type(permit['issued']) is not dict or set(permit['issued']) != {'wall_ns', 'monotonic_ns'}
                    or any(type(v) is not int or not 0 < v < 2**63 for v in permit['issued'].values())):
                raise ControlError('native-host-permit-clock-shape')
            return permit
        finally:
            if child is not None: os.close(child)
            os.close(fd)

    def bind(self, fence, base_mode):
        if type(fence) is not packets._PlanningContext:
            raise ControlError('native-host-original-transaction-required')
        fd, ledger = fence._snapshot()
        permit = self._read_session()
        if (trust._read(fd, BINDING_FILE, MAX_BYTES) != self._reference_raw
                or permit['packet_id'] != fence._store.packet_id
                or permit['packet_root'] != str(fence._store.root)
                or permit['packet_inode'] != _inode(fd)
                or permit['identity_sha256'] != ledger['identity_sha256']
                or packets.canonical(permit['base_mode']) != packets.canonical(base_mode)
                or ledger.get('governance') is not None and packets.digest(packets.canonical(
                    ledger['governance']['objective'])) != permit['objective_sha256']):
            raise ControlError('native-host-packet-or-mode-drift')
        fence._snapshot()
        return fd, ledger, permit

    def _watermark(self):
        fd = _private_directory(self.root)
        child = None
        try:
            child = _file(fd, 'clock.json')
            raw = trust._read(fd, 'clock.json', MAX_BYTES)
            value = json.loads(raw, object_pairs_hook=trust._pairs)
            if (type(value) is not dict or set(value) != {'reference_sha256', 'clock'}
                    or value['reference_sha256'] != self.reference_sha256
                    or type(value['clock']) is not dict or set(value['clock']) != {'wall_ns', 'monotonic_ns'}
                    or any(type(v) is not int or not 0 < v < 2**63 for v in value['clock'].values())):
                raise ControlError('native-host-clock-watermark-drift')
            return value['clock']
        finally:
            if child is not None: os.close(child)
            os.close(fd)

    def _persist_clock(self, stamp):
        # One high-water mark, not another retry/ownership journal. The caller
        # holds the packet lock; read-only reconcile never advances this file.
        fd = _private_directory(self.root)
        child = None
        try:
            child = os.open('clock.json', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW |
                os.O_NONBLOCK | os.O_CLOEXEC, 0o600, dir_fd=fd)
            value = os.fstat(child); trust._check(value)
            if stat.S_IMODE(value.st_mode) != 0o600 or value.st_nlink != 1:
                raise ControlError('native-host-clock-watermark-file-drift')
            raw = packets.canonical(dict(reference_sha256=self.reference_sha256, clock=stamp))
            os.ftruncate(child, 0)
            with os.fdopen(os.dup(child), 'wb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.fsync(fd)
        finally:
            if child is not None: os.close(child)
            os.close(fd)

    def _stamp(self, permit):
        sample = _clock(); issued = permit['issued']
        elapsed = sample['monotonic_ns'] - issued['monotonic_ns']
        wall_elapsed = sample['wall_ns'] - issued['wall_ns']
        if (elapsed < 0 or wall_elapsed < 0 or abs(elapsed - wall_elapsed) > MAX_DRIFT_NS
                or elapsed >= permit['ttl_seconds'] * 1_000_000_000
                or self._last_clock is not None and any(sample[k] < self._last_clock[k] for k in sample)):
            raise ControlError('native-host-clock-expired-rollback-or-epoch-unknown')
        watermark = self._watermark()
        if watermark is not None and any(sample[k] < watermark[k] for k in sample):
            raise ControlError('native-host-clock-watermark-rollback')
        self._last_clock = sample
        return sample

    def _revoked(self, fd):
        name = 'native-host-revoked-' + self.reference_sha256
        try:
            raw = trust._read(fd, name, MAX_BYTES)
        except FileNotFoundError:
            return False
        expected = packets.canonical(dict(reference_sha256=self.reference_sha256, purpose=PURPOSE))
        if raw != expected:
            raise ControlError('native-host-revocation-drift')
        return True

    def check(self, fence, base_mode, action, *, persist=False):
        if type(action) is not str or action not in _ACTIONS:
            raise ControlError('native-host-action-invalid')
        fd, ledger, permit = self.bind(fence, base_mode)
        stamp = self._stamp(permit)
        revoked = self._revoked(fd)
        if action != 'read' and revoked:
            raise ControlError('native-host-permit-revoked')
        if persist:
            if action == 'read': raise ControlError('native-host-read-cannot-advance-clock')
            self._persist_clock(stamp)
        fence._snapshot()
        return dict(reference_sha256=self.reference_sha256, prefix_sha256=packets.digest(packets.canonical(ledger)),
            clock=stamp, revoked=revoked, qualification=False)

    def observe(self, fence, base_mode, inspect):
        before = self.check(fence, base_mode, 'read')
        raw = inspect()
        after = self.check(fence, base_mode, 'read')
        if type(raw) is not bytes or len(raw) > MAX_BYTES:
            raise ControlError('native-host-observation-bound')
        if before['prefix_sha256'] != after['prefix_sha256'] or len(self.samples) >= 2048:
            raise ControlError('native-host-observation-prefix-or-count')
        sample = dict(reference_sha256=self.reference_sha256, prefix_sha256=before['prefix_sha256'],
            historical_runtime_sha256=packets.digest(raw), sample_start=before['clock'],
            sample_end=after['clock'], revoked=after['revoked'], qualification=False)
        self.samples.append(sample)
        return raw

    def revoke(self, fence, base_mode):
        # The caller owns the original packet lock. Busy means not-applied; an
        # operator must stop coordination, never treat a failed withdrawal as OK.
        fd, _, _ = self.bind(fence, base_mode)
        from model_packet_lifecycle import _WRITE_TOKEN
        raw = packets.canonical(dict(reference_sha256=self.reference_sha256, purpose=PURPOSE))
        fence._store._immutable(fd, 'native-host-revoked-' + self.reference_sha256,
            raw, _lifecycle_token=_WRITE_TOKEN)
        fence._snapshot()
        return dict(status='revoked', reference_sha256=self.reference_sha256, qualification=False)
