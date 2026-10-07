"""Default-off fixture permit contract; never production authority or admission.

Protected fixture originals exercise the future issuer boundary. They cannot
prove original human authorization or independently qualify a real CLI. No
consumer, production adapter, credential reader or dispatch is installed here.
The explicitly supplied private root and same-UID host code are in the TCB;
hash chaining detects corruption, not malicious same-UID journal rollback.
Partial/malformed writes remain unusable and are never repaired on open.
A fault after a complete write has an unknown outcome; reopen reads durable
state and cannot prove that the failed call had no effect.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import math
import os
import pathlib
import stat
import time

import agent_qualification as trust
import model_packet_store as packets
import model_task_ingress as ingress

DOMAIN = 'model-task-permit-fixture/v1'
ANCHOR = 'fixture-anchor.json'
JOURNAL = 'fixture-permits.jsonl'
MAX_BYTES = 1048576
MAX_EVENTS = 512
MAX_TTL = 60
MAX_GRANT_LIFETIME = 3600
MAX_DRIFT = 5
ACTIONS = {'fixture-start', 'fixture-read-only'}
EVIDENCE = {'authorization': 'fixture-authorization.json',
            'cli-qualification': 'fixture-cli-qualification.json'}


class PermitError(ValueError):
    """Expose only fixed reason identifiers, never input content."""


class GrantExpired(PermitError):
    """A valid task grant whose expiry was observed and must be fenced."""


def _require(condition, reason):
    if not condition:
        raise PermitError(reason)


def _sha(value):
    _require(type(value) is str and trust.SHA.fullmatch(value), 'fixture-digest-rejected')
    return value


def _digest(value):
    return packets.digest(packets.canonical(value))


def _shape(value, keys):
    _require(type(value) is dict and set(value) == set(keys), 'fixture-schema-rejected')
    return value


def _decode(raw):
    value = json.loads(raw, object_pairs_hook=trust._pairs)
    _require(packets.canonical(value) == raw, 'fixture-noncanonical-state')
    return value


def _identity(info):
    return [info.st_dev, info.st_ino]


def _clock():
    now = time.time()
    _require(type(now) in {int, float} and math.isfinite(now) and now > 0,
             'fixture-clock-rejected')
    return now


def _root(path):
    _require(isinstance(path, pathlib.Path) and path.is_absolute()
             and path == path.resolve(strict=True), 'fixture-root-rejected')
    fd = trust._directory(path)
    try:
        _require(not os.fstat(fd).st_mode & 0o077, 'fixture-root-not-private')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read(fd, name):
    # Ingress reads reject symlinks, hardlinks, ownership/mode drift and changes
    # between the opened and named inode. Keep all permit files at root level.
    return ingress._read(fd, name, MAX_BYTES, private=True)


def _write(fd, raw):
    offset = 0
    while offset < len(raw):
        written = os.write(fd, raw[offset:])
        _require(written > 0, 'fixture-partial-write')
        offset += written
    os.fsync(fd)


class FixturePermitIssuer:
    """Explicit opt-in fixture-only issue/readback/revoke with durable fencing.

    initialize() requires a preexisting empty private root outside Git. Opening
    an existing root never creates missing state. Revoke is sticky for the named
    task in its workspace, across source/target/action/reference renewals.
    The trusted target_reader(binding, request) rereads protected originals and
    returns the exact live Binding. Absence rejects issue/readback. Persisted
    monotonic samples constrain TTL across reopen; rollback or unknown epoch
    fences the observed reference durably. This is no boot identity attestation.
    """

    @classmethod
    def initialize(cls, root, *, enabled=False, target_reader=None):
        _require(enabled is True, 'fixture-issuer-disabled')
        fd = _root(root)
        try:
            _require(not os.listdir(fd), 'fixture-root-not-empty')
            anchor = {'domain': DOMAIN, 'root_identity': _identity(os.fstat(fd)),
                      'nonce_sha256': packets.digest(os.urandom(32))}
            raw = packets.canonical(anchor)
            anchor_fd = os.open(ANCHOR, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600, dir_fd=fd)
            try:
                _write(anchor_fd, raw)
            finally:
                os.close(anchor_fd)
            os.fsync(fd)
            journal_fd = os.open(JOURNAL, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=fd)
            try:
                event = {'domain': DOMAIN, 'sequence': 0, 'previous_sha256': '0'*64,
                         'observed_at': _clock(), 'kind': 'initialize', 'payload': {
                             'anchor_sha256': packets.digest(raw),
                             'anchor_identity': _identity(os.stat(ANCHOR, dir_fd=fd, follow_symlinks=False)),
                             'journal_identity': _identity(os.fstat(journal_fd))}}
                event['monotonic_at'] = time.monotonic()
                _write(journal_fd, packets.canonical(event) + b'\n')
            finally:
                os.close(journal_fd)
            os.fsync(fd)
        finally:
            os.close(fd)
        return cls(root, enabled=True, target_reader=target_reader)

    def __init__(self, root, *, enabled=False, target_reader=None):
        _require(enabled is True, 'fixture-issuer-disabled')
        self.root = root
        # Trusted injected bounded original-reader, not qualification authority.
        # It must reread the target store/artifacts and return the exact Binding.
        self.target_reader = target_reader
        fd = _root(root)
        try:
            self.anchor_raw = _read(fd, ANCHOR)
            anchor = _shape(_decode(self.anchor_raw), {'domain', 'root_identity', 'nonce_sha256'})
            _sha(anchor['nonce_sha256'])
            self.root_identity = _identity(os.fstat(fd))
            self.anchor_identity = _identity(os.stat(ANCHOR, dir_fd=fd, follow_symlinks=False))
            _require(anchor['domain'] == DOMAIN and anchor['root_identity'] == self.root_identity,
                     'fixture-root-identity-drift')
            self.journal_identity = _identity(os.stat(JOURNAL, dir_fd=fd, follow_symlinks=False))
        finally:
            os.close(fd)
        self.last_monotonic = time.monotonic()
        self.last_wall = None
        self.candidate_clock = None
        self.last_history = None
        with self._locked() as (_, _, raw):
            self._replay(raw)

    @contextmanager
    def _locked(self):
        fd = _root(self.root)
        journal_fd = None
        try:
            _require(_identity(os.fstat(fd)) == self.root_identity, 'fixture-root-identity-drift')
            journal_fd = os.open(JOURNAL, os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK,
                                 dir_fd=fd)
            info = os.fstat(journal_fd)
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                     and info.st_uid == os.getuid() and not info.st_mode & 0o077
                     and _identity(info) == self.journal_identity,
                     'fixture-journal-identity-drift')
            fcntl.flock(journal_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _require(_read(fd, ANCHOR) == self.anchor_raw, 'fixture-anchor-drift')
            raw = _read(fd, JOURNAL)
            self._check_named(fd, journal_fd)
            yield fd, journal_fd, raw
            self._check_named(fd, journal_fd)
        except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
            if isinstance(exc, PermitError):
                raise
            raise PermitError('fixture-state-unavailable-or-untrusted') from None
        finally:
            if journal_fd is not None:
                os.close(journal_fd)
            os.close(fd)

    def _check_named(self, fd, journal_fd):
        fresh = _root(self.root)
        try:
            _require(_identity(os.fstat(fresh)) == self.root_identity
                     and _read(fresh, ANCHOR) == self.anchor_raw
                     and _identity(os.stat(ANCHOR, dir_fd=fresh, follow_symlinks=False)) == self.anchor_identity,
                     'fixture-root-or-anchor-drift')
        finally:
            os.close(fresh)
        named = os.stat(JOURNAL, dir_fd=fd, follow_symlinks=False)
        opened = os.fstat(journal_fd)
        _require(_identity(named) == _identity(opened) == self.journal_identity
                 and stat.S_ISREG(named.st_mode) and named.st_nlink == 1
                 and not named.st_mode & 0o077, 'fixture-journal-identity-drift')

    def _replay(self, raw):
        _require(raw and raw.endswith(b'\n'), 'fixture-partial-state')
        lines = raw.splitlines()
        _require(len(lines) <= MAX_EVENTS, 'fixture-state-bound')
        tasks, previous, observed, observed_mono = {}, '0'*64, 0, 0
        for index, line in enumerate(lines):
            event = _shape(_decode(line), {'domain', 'sequence', 'previous_sha256',
                                         'observed_at', 'monotonic_at', 'kind', 'payload'})
            now = event['observed_at']
            mono = event['monotonic_at']
            _require(event['domain'] == DOMAIN and type(event['sequence']) is int
                     and event['sequence'] == index and event['previous_sha256'] == previous
                     and type(now) in {int, float} and math.isfinite(now) and now >= observed
                     and type(mono) in {int, float} and math.isfinite(mono) and mono >= observed_mono,
                     'fixture-history-drift')
            payload, kind = event['payload'], event['kind']
            if index == 0:
                _require(kind == 'initialize' and payload == {
                    'anchor_sha256': packets.digest(self.anchor_raw),
                    'anchor_identity': self.anchor_identity,
                    'journal_identity': self.journal_identity}, 'fixture-initial-state-drift')
            elif kind == 'issue':
                self._validate_permit(payload)
                key = payload['task_key']
                prior = tasks.get(key)
                _require(payload['issued_at'] == now and payload['issued_monotonic'] == mono
                         and (prior is None or
                         (not prior['revoked'] and now >= prior['permit']['expires_at']))
                         and payload['epoch'] == (0 if prior is None else prior['epoch'] + 1),
                         'fixture-issue-history-drift')
                tasks[key] = {'permit': payload, 'epoch': payload['epoch'], 'revoked': False, 'expired': False}
            elif kind in {'revoke', 'observe', 'expire'}:
                _shape(payload, {'task_key', 'epoch'})
                key = _sha(payload['task_key'])
                prior = tasks.get(key)
                _require(prior is not None and type(payload['epoch']) is int
                         and payload['epoch'] == prior['epoch'] + int(kind != 'observe')
                         and not prior['revoked'] and not (kind == 'observe' and prior['expired']),
                         'fixture-epoch-drift')
                prior['epoch'] = payload['epoch']
                prior['revoked'] = kind == 'revoke'
                prior['expired'] = kind == 'expire'
            elif kind == 'grant-expire':
                _shape(payload, {'task_key', 'epoch'})
                key = _sha(payload['task_key'])
                prior = tasks.get(key)
                _require(type(payload['epoch']) is int
                         and ((prior is None and payload['epoch'] == 0)
                         or (prior is not None and not prior['revoked']
                             and now >= prior['permit']['expires_at']
                             and payload['epoch'] == prior['epoch'] + 1)),
                         'fixture-grant-expiry-history-drift')
                tasks[key] = {'permit': None, 'epoch': payload['epoch'],
                              'revoked': True, 'expired': True}
            else:
                raise PermitError('fixture-event-rejected')
            previous, observed, observed_mono = packets.digest(line), now, mono
        if self.last_history is not None:
            count, digest = self.last_history
            _require(len(lines) >= count and packets.digest(lines[count-1]) == digest,
                     'fixture-history-rollback')
        self.last_history = (len(lines), previous)
        self.observed_monotonic = observed_mono
        return tasks, previous, observed, len(lines)

    def _validate_permit(self, value):
        keys = {'domain', 'task_key', 'epoch', 'action', 'session_sha256', 'input_sha256',
                'request_sha256', 'target_sha256', 'source_sha256', 'evidence_sha256',
                'issuer_sha256', 'issued_at', 'issued_monotonic', 'expires_at'}
        _shape(value, keys)
        _require(value['domain'] == DOMAIN and value['action'] in ACTIONS
                 and type(value['epoch']) is int and value['epoch'] >= 0
                 and value['issuer_sha256'] == _digest({'anchor': packets.digest(self.anchor_raw),
                                                       'journal_identity': self.journal_identity}),
                 'fixture-permit-rejected')
        for key in keys:
            if key.endswith('_sha256') or key == 'task_key':
                _sha(value[key])
        start, end = value['issued_at'], value['expires_at']
        _require(type(start) in {int, float} and type(end) in {int, float}
                 and math.isfinite(start) and math.isfinite(end) and 0 < end-start <= MAX_TTL,
                 'fixture-lifetime-rejected')
        _require(type(value['issued_monotonic']) in {int, float}
                 and math.isfinite(value['issued_monotonic']) and value['issued_monotonic'] > 0,
                 'fixture-monotonic-rejected')

    def _now(self, observed):
        self.candidate_clock = None
        now, monotonic = _clock(), time.monotonic()
        baseline = self.last_monotonic if observed == self.last_wall else self.observed_monotonic
        if type(monotonic) in {int, float} and math.isfinite(monotonic):
            self.candidate_clock = (now, monotonic)
        _require(type(monotonic) in {int, float} and math.isfinite(monotonic)
                 and now >= max(observed, self.last_wall or observed)
                 and monotonic >= max(self.last_monotonic, self.observed_monotonic)
                 and abs((now-observed)-(monotonic-baseline)) <= MAX_DRIFT,
                 'fixture-clock-rollback-or-epoch-unknown')
        self.last_monotonic = monotonic
        self.last_wall = now
        return now

    def _append(self, fd, journal_fd, raw, kind, payload, now):
        _, previous, _, count = self._replay(raw)
        _require(count < MAX_EVENTS, 'fixture-state-bound')
        event = packets.canonical({'domain': DOMAIN, 'sequence': count,
            'previous_sha256': previous, 'observed_at': now, 'monotonic_at': self.last_monotonic,
            'kind': kind, 'payload': payload}) + b'\n'
        _require(len(raw) + len(event) <= MAX_BYTES, 'fixture-state-bound')
        self._check_named(fd, journal_fd)
        _write(journal_fd, event)
        actual = _read(fd, JOURNAL)
        _require(actual == raw + event, 'fixture-write-readback-drift')
        self._replay(actual)

    def _constraints(self, source, request, binding, action, session_sha256):
        _require(type(source) is ingress.TaskSourceInput and action in ACTIONS,
                 'fixture-source-or-action-rejected')
        _sha(session_sha256)
        _require(callable(self.target_reader), 'fixture-live-target-reader-unavailable')
        live = self.target_reader(binding, request)
        _require(type(live) is type(binding) and live == binding, 'fixture-live-target-drift')
        # This is the existing original/source port, not a summary admission.
        source.verify(request, binding)
        source.verify_launch_window(binding)
        target = {key: getattr(binding, key) for key in (
            'target_id', 'identity_sha256', 'binding_sha256', 'store_sha256', 'task_sha256',
            'task_id', 'scope', 'acceptance_sha256', 'valid_from', 'valid_until')}
        for key in target:
            if key.endswith('_sha256'):
                _sha(target[key])
        return {'task_key': _digest({'task_id': source.record['task_id'],
                    'workspace': source.record['source']['workspace']}),
                'action': action, 'session_sha256': session_sha256,
                'input_sha256': source.identity_sha256, 'request_sha256': _digest(request),
                'target_sha256': _digest(target), 'source_sha256': _digest(source.source_identity)}

    @staticmethod
    def _grant_scope(source, constraints):
        # A single initial approval covers a bounded task, not each session.
        # The original input still limits every destination and sandbox.
        return {'task_key': constraints['task_key'],
                'input_sha256': source.identity_sha256,
                'request_sha256': _digest(source.request),
                'source_sha256': constraints['source_sha256'],
                'acceptance_sha256': source.record['acceptance']['sha256'],
                'destinations_sha256': _digest(source.record['destinations']),
                'sandbox_ceiling': source.request['authorization']['sandbox_ceiling']}

    def _evidence(self, fd, constraints, source, now):
        identities = {}
        for kind, name in EVIDENCE.items():
            raw = _read(fd, name)
            value = _decode(raw)
            if kind == 'authorization':
                _shape(value, {'domain', 'kind', 'scope', 'actions', 'approved_at', 'expires_at'})
                actions = value['actions']
                _require(value['domain'] == DOMAIN and value['kind'] == kind
                         and type(actions) is list and actions == sorted(set(actions))
                         and actions and set(actions) <= ACTIONS and constraints['action'] in actions
                         and type(value['approved_at']) is int and type(value['expires_at']) is int
                         and value['approved_at'] <= now
                         and value['approved_at'] < value['expires_at']
                         <= value['approved_at'] + MAX_GRANT_LIFETIME
                         and value['scope'] == self._grant_scope(source, constraints),
                         'fixture-task-grant-mismatch')
                if now >= value['expires_at']:
                    raise GrantExpired('fixture-task-grant-expired')
                grant_expiry = value['expires_at']
            else:
                _require(value == {'domain': DOMAIN, 'kind': kind, 'constraints': constraints},
                         'fixture-original-evidence-mismatch')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            identities[kind] = {'sha256': packets.digest(raw), 'identity': _identity(info)}
        return _digest(identities), grant_expiry

    def _recheck(self, fd, source, request, binding, constraints, evidence, now):
        _require(self._constraints(source, request, binding, constraints['action'],
                                  constraints['session_sha256']) == constraints
                 and self._evidence(fd, constraints, source, now)[0] == evidence,
                 'fixture-live-readback-drift')

    def _fence_grant(self, fd, journal_fd, raw, constraints, prior, now):
        self._append(fd, journal_fd, raw, 'grant-expire', {
            'task_key': constraints['task_key'],
            'epoch': 0 if prior is None else prior['epoch'] + 1}, now)

    def issue(self, source, request, binding, *, action, session_sha256, ttl=30):
        _require(type(ttl) is int and 0 < ttl <= MAX_TTL, 'fixture-lifetime-rejected')
        with self._locked() as (fd, journal_fd, raw):
            tasks, _, observed, _ = self._replay(raw)
            now = self._now(observed)
            start_monotonic = self.last_monotonic
            constraints = self._constraints(source, request, binding, action, session_sha256)
            prior = tasks.get(constraints['task_key'])
            _require(prior is None or (not prior['revoked'] and now >= prior['permit']['expires_at']),
                     'fixture-task-revoked-or-already-issued')
            try:
                evidence, grant_expiry = self._evidence(fd, constraints, source, now)
            except GrantExpired:
                # Record the observed grant expiry before returning rejection.
                # This also fences a task that never had a session permit.
                self._fence_grant(fd, journal_fd, raw, constraints, prior, now)
                raise
            self._recheck(fd, source, request, binding, constraints, evidence, now)
            # Slow source/evidence reads cannot extend the sampled lifetime.
            final = self._now(now)
            end = min(now + ttl, grant_expiry, source.record['expires_at'], binding.valid_until)
            if final >= grant_expiry:
                self._fence_grant(fd, journal_fd, raw, constraints, prior, final)
                raise GrantExpired('fixture-task-grant-expired')
            _require(final < end and self.last_monotonic-start_monotonic < ttl,
                     'fixture-expired-during-issue')
            value = {'domain': DOMAIN, **constraints, 'epoch': 0 if prior is None else prior['epoch']+1,
                     'issuer_sha256': _digest({'anchor': packets.digest(self.anchor_raw),
                                              'journal_identity': self.journal_identity}),
                     'evidence_sha256': evidence, 'issued_at': final, 'expires_at': end}
            value['issued_monotonic'] = self.last_monotonic
            self._validate_permit(value)
            self._append(fd, journal_fd, raw, 'issue', value, final)
            return self._reference(value)

    @staticmethod
    def _reference(value):
        return {'domain': DOMAIN, 'task_key': value['task_key'], 'epoch': value['epoch'],
                'permit_sha256': _digest(value)}

    def _lookup(self, tasks, reference, *, for_revoke=False):
        _shape(reference, {'domain', 'task_key', 'epoch', 'permit_sha256'})
        _sha(reference['task_key']); _sha(reference['permit_sha256'])
        _require(reference['domain'] == DOMAIN and type(reference['epoch']) is int,
                 'fixture-reference-rejected')
        current = tasks.get(reference['task_key'])
        _require(current is not None and not current['revoked']
                 and (for_revoke or not current['expired'])
                 and self._reference(current['permit']) == reference,
                 'fixture-revoked-stale-or-unknown-permit')
        return current['permit']

    def _live_time(self, fd, journal_fd, raw, value, observed):
        try:
            now = self._now(observed)
            elapsed = self.last_monotonic-value['issued_monotonic']
            _require(value['issued_at'] <= now < value['expires_at']
                     and 0 <= elapsed < value['expires_at']-value['issued_at']
                     and abs(elapsed-(now-value['issued_at'])) <= MAX_DRIFT,
                     'fixture-permit-expired-or-clock-drift')
            return now
        except PermitError:
            # Fence an observed expiry/rollback durably before rejecting it.
            # Use the last valid clock watermark if the current sample is bad.
            stamp = self.candidate_clock or (observed, self.observed_monotonic)
            self.last_monotonic = max(self.observed_monotonic, self.last_monotonic, stamp[1])
            self._append(fd, journal_fd, raw, 'expire', {
                'task_key': value['task_key'], 'epoch': value['epoch']+1},
                max(observed, stamp[0], self.last_wall or observed))
            raise

    def readback(self, reference, source, request, binding, *, action, session_sha256):
        with self._locked() as (fd, journal_fd, raw):
            tasks, _, observed, _ = self._replay(raw)
            value = self._lookup(tasks, reference)
            now = self._live_time(fd, journal_fd, raw, value, observed)
            constraints = self._constraints(source, request, binding, action, session_sha256)
            evidence, grant_expiry = self._evidence(fd, constraints, source, now)
            _require(all(value[key] == entry for key, entry in constraints.items())
                     and evidence == value['evidence_sha256']
                     and value['expires_at'] <= grant_expiry,
                     'fixture-permit-constraint-drift')
            self._recheck(fd, source, request, binding, constraints,
                          value['evidence_sha256'], now)
            final = self._live_time(fd, journal_fd, raw, value, now)
            self._append(fd, journal_fd, raw, 'observe', {
                'task_key': value['task_key'], 'epoch': value['epoch']}, final)
            # Digest-only readback carries no production readiness claim.
            return dict(value)

    def revoke(self, reference):
        # Revocation needs no current source/target or unexpired evidence.
        with self._locked() as (fd, journal_fd, raw):
            tasks, _, observed, _ = self._replay(raw)
            now = self._now(observed)
            # Only the exact retained permit reference can revoke after expiry;
            # a replaced/renewed permit still rejects its stale predecessor.
            value = self._lookup(tasks, reference, for_revoke=True)
            epoch = tasks[value['task_key']]['epoch']+1
            self._append(fd, journal_fd, raw, 'revoke', {
                'task_key': value['task_key'], 'epoch': epoch}, now)
            return {'domain': DOMAIN, 'task_key': value['task_key'],
                    'epoch': epoch, 'revoked': True}
