"""Host-owned、process-local 單次 maintenance authority；無持久化或資料 loader。

Request 只描述意圖。accept_request 與 accept_preview 必須來自真正 host 接受介面；
本模組不實作 CLI/TTY/JSON 接受。重啟、fork、複製及重建 provider 均不恢復 grant。
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading
import uuid

import memory_governance_contract as c
from memory_governance_host import ClockSample, RootBinding


def intent(value):
    c.fields(value, {'operation', 'item_id', 'candidate', 'restore_revision'})
    c.g1_operation(value['operation'])
    c.uuid(value['item_id'])
    if value['operation'] in {'add', 'update', 'restore'}:
        c.require(type(value['candidate']) is dict, 'candidate-unavailable')
        c.canonical(value['candidate'], 16384)
    else:
        c.require(value['candidate'] is None, 'unexpected-candidate')
    if value['operation'] == 'restore':
        c.integer(value['restore_revision'], 1)
    else:
        c.require(value['restore_revision'] is None, 'unexpected-restore-source')
    return c.decode(c.canonical(value, 20000), 20000)


@dataclass(frozen=True, eq=False)
class MaintenanceRequest:
    principal_id: str
    request_id: str
    scope_digest: str
    intent_bytes: bytes


@dataclass(frozen=True, eq=False)
class MutationGrant:
    binding: RootBinding
    request: MaintenanceRequest
    issued: ClockSample
    expires_at: int


class MaintenanceAuthorityProvider:
    """TCB API：只在 host 真正接受意圖後發放可預覽要求，非 mutation 確認。

    RAM object identity 登錄與原子 take 跨 factory 防重播；pid/clock process_id
    防 fork，restart 空登錄不恢復任何 request。沒有 import/restore grant API。
    同程序所有 factory 必須使用原 owner provider，不能以 JSON 建立新 authority。
    Host 接受 callback 不得從 argv、confirmed=true 或 request 自述推導接受。
    """

    def __init__(self, *, binding, clock, accept_request, accept_preview, request_revoked):
        c.require(type(binding) is RootBinding, 'root-binding-mismatch')
        self.binding, self.clock = binding, clock
        self.accept_request, self.accept_preview = accept_request, accept_preview
        self.request_revoked = request_revoked
        self._pid, self._closed = os.getpid(), False
        self._requests, self._taken = {}, set()
        self._lock = threading.Lock()

    def _check(self):
        c.require(not self._closed and self._pid == os.getpid(), 'authority-unavailable')

    def close(self):
        with self._lock:
            self._closed = True
            self._requests.clear()

    def accept(self, value, *, lifetime_seconds=300):
        self._check()
        c.integer(lifetime_seconds, 1, 300)
        data = c.canonical(intent(value), 20000)
        # No lock while waiting at a host UI. This acceptance permits preview only.
        c.require(self.accept_request(self.binding, data) is True, 'request-not-accepted')
        self._check()
        issued = self.clock.clock()
        c.require(type(issued) is ClockSample, 'clock-untrusted')
        scope = c.decode(self.binding.scope_bytes)
        request = MaintenanceRequest(scope['principal_id'], str(uuid.uuid4()), c.digest(scope), data)
        grant = MutationGrant(self.binding, request, issued, issued.utc_seconds + lifetime_seconds)
        with self._lock:
            self._check()
            self._requests[request.request_id] = grant
        return request

    def take(self, request):
        self._check()
        c.require(type(request) is MaintenanceRequest, 'authority-unavailable')
        with self._lock:
            self._check()
            grant = self._requests.get(request.request_id)
            c.require(grant is not None and grant.request is request
                      and request.request_id not in self._taken, 'request-consumed-or-unrecognized')
            self._taken.add(request.request_id)
        return grant

    def pending(self, request):
        """只讀準備度；不產生或消耗 grant，不讀 managed/source 資料。"""
        self._check()
        with self._lock:
            grant = self._requests.get(request.request_id)
            c.require(grant is not None and grant.request is request
                      and request.request_id not in self._taken, 'request-consumed-or-unrecognized')
        sample = self.clock.clock()
        c.require(type(sample) is ClockSample and sample.process_id == grant.issued.process_id
                  and grant.issued.utc_seconds <= sample.utc_seconds < grant.expires_at
                  and grant.issued.monotonic_ns <= sample.monotonic_ns
                  < grant.issued.monotonic_ns + (grant.expires_at - grant.issued.utc_seconds) * 1_000_000_000,
                  'expired-or-clock-changed')
        c.require(self.request_revoked(request.request_id) is False, 'request-revoked')

    def current(self, grant):
        with self._lock:
            self._check()
            c.require(self._requests.get(grant.request.request_id) is grant
                      and grant.request.request_id in self._taken, 'authority-unavailable')
        c.require(self.request_revoked(grant.request.request_id) is False, 'request-revoked')


class MaintenanceAuthority:
    def __init__(self, provider, grant):
        c.require(type(provider) is MaintenanceAuthorityProvider and type(grant) is MutationGrant,
                  'authority-unavailable')
        c.require(grant.binding == provider.binding, 'root-binding-mismatch')
        self.provider, self.grant, self.clock = provider, grant, provider.clock
        self._last, self._invalid = grant.issued, False
        self._preview_id, self._confirmation_used = None, False
        self._lock = threading.Lock()

    def check(self):
        c.require(not self._invalid, 'authority-unavailable')
        try:
            self.provider.current(self.grant)
            sample = self.clock.clock()
            c.require(type(sample) is ClockSample and sample.process_id == self.grant.issued.process_id
                      and self._last.utc_seconds <= sample.utc_seconds < self.grant.expires_at
                      and self._last.monotonic_ns <= sample.monotonic_ns
                      and sample.monotonic_ns - self.grant.issued.monotonic_ns
                      < (self.grant.expires_at - self.grant.issued.utc_seconds) * 1_000_000_000,
                      'expired-or-clock-changed')
            self._last = sample
        except Exception:
            self._invalid = True
            raise

    def authorize_read(self, binding, purpose, operation_id):
        self.check()
        c.require(binding == self.grant.binding, 'root-binding-mismatch')
        if purpose == 'preview':
            c.uuid(operation_id)
            with self._lock:
                c.require(self._preview_id is None, 'request-consumed-or-unrecognized')
                self._preview_id = operation_id
            return True
        return ((purpose == 'readback' and operation_id == self._preview_id)
                or (purpose in {'recall', 'audit'} and operation_id is None and self._confirmation_used))

    def accept_preview(self, binding, preview_bytes):
        self.check()
        value = c.decode(preview_bytes)
        expected = c.decode(self.grant.request.intent_bytes, 20000)
        c.require(binding == self.grant.binding and value['scope'] == c.decode(binding.scope_bytes)
                  and value['operation_id'] == self._preview_id
                  and value['operation'] == expected['operation'] and value['item_id'] == expected['item_id']
                  and value['candidate'] == expected['candidate']
                  and value['target_revisions'] == ([expected['restore_revision']] if expected['operation'] == 'restore' else []),
                  'request-preview-mismatch')
        with self._lock:
            c.require(not self._confirmation_used, 'confirmation-consumed')
            self._confirmation_used = True
        # Core verifies exact AcceptedPreview bytes and confirmation binding/TTL.
        # No authority/DB lock remains held while waiting for this callback.
        result = self.provider.accept_preview(binding, preview_bytes)
        self.check()
        return result

    def external_copies(self, binding):
        self.check()
        c.require(binding == self.grant.binding, 'root-binding-mismatch')
        return {'coverage': 'unknown', 'observed_at': self.clock.clock().utc_seconds, 'copies': []}

    def accept_initialization(self, binding):
        return False
