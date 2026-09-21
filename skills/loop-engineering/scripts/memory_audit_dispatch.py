"""單次盤點要求的可信程式串接；沒有 argv/env/config loader 或 production 註冊。

控制面負責原子消耗 grant（包含跨 factory／程序的重播拒絕）。Request 只有身分，
不能產生讀取權；本模組只組合控制面已接受的 authority/source/qualification。
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import threading

import memory_governance_contract as c
from memory_audit_adapter import (AcceptedSourceReview, AuditOnlyHost, AuditReadAuthority,
                                  ReadGrant)
from memory_governance_local import SingleRootRegistry


@dataclass(frozen=True)
class AuditRequest:
    principal_id: str
    request_id: str
    scope_digest: str


class AuditHostFactory:
    """固定單 root 的 TCB factory；take_grant 必須原子消耗當次已授權要求。

    take_grant(request) 回傳既有 ReadGrant 或拒絕，不能從 request/旗標自動批准。
    即使後續建構、資格或讀取失敗，控制面也不得再發放相同 request 的 grant。
    接受來源及 qualification 的更新由 host 重新接受並建構 factory，不讀 repo 設定。
    """

    def __init__(self, *, binding, repository, permits, accepted_sources, qualification,
                 take_grant, clock, request_revoked, source_revoked, qualification_revoked):
        c.require(binding.capabilities == frozenset({'audit'}), 'capability-unavailable')
        self.binding = binding
        self.repository, self.permits = repository, permits
        self.accepted_sources, self.qualification = accepted_sources, qualification
        self.take_grant, self.clock = take_grant, clock
        self.request_revoked, self.source_revoked = request_revoked, source_revoked
        self.qualification_revoked = qualification_revoked

    def create_host(self, request: AuditRequest) -> AuditOnlyHost:
        c.require(type(request) is AuditRequest, 'read-unavailable')
        c.uuid(request.principal_id)
        c.uuid(request.request_id)
        scope = c.decode(self.binding.scope_bytes)
        c.require(request.principal_id == scope['principal_id']
                  and request.scope_digest == c.digest(scope), 'read-unavailable')
        grant = self.take_grant(request)
        c.require(type(grant) is ReadGrant and grant.binding == self.binding, 'read-unavailable')
        authority = AuditReadAuthority(grant, principal_id=request.principal_id,
                                       request_id=request.request_id,
                                       revoked=self.request_revoked, clock=self.clock)
        c.require(authority.valid(self.binding), 'read-unavailable')
        review = AcceptedSourceReview(self.accepted_sources, revoked=self.source_revoked,
                                      authority=authority)
        return AuditOnlyHost(SingleRootRegistry(self.binding), authority=authority,
                             repository=self.repository, permits=self.permits,
                             source_review=review, qualification=self.qualification,
                             qualification_revoked=self.qualification_revoked)


class AuditDispatch:
    """每個已接受要求一個 dispatch；先消耗，再呼叫 factory，失敗不重試。

    lock 只保護同程序單次消耗，不作跨程序 authority store。重新要求需由控制面
    接受新 request/grant；複製物件或重啟程序不能替代控制面的防重播。
    """

    def __init__(self, factory: AuditHostFactory, request: AuditRequest):
        c.require(type(factory) is AuditHostFactory and type(request) is AuditRequest, 'read-unavailable')
        self._factory, self._request = factory, request
        self._pid, self._used = os.getpid(), False
        self._lock = threading.Lock()

    def acquire(self) -> AuditOnlyHost:
        c.require(os.getpid() == self._pid, 'read-unavailable')
        c.require(self._lock.acquire(blocking=False), 'read-unavailable')
        try:
            c.require(not self._used, 'read-unavailable')
            self._used = True
        finally:
            self._lock.release()
        # 不持有 dispatch lock 執行 callback，也不在失敗後重設 consumed 狀態。
        return self._factory.create_host(self._request)
