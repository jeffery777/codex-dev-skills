"""固定單 root／固定 Git source 的可信 maintenance factory 與單次 dispatch。"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import threading

import memory_governance_contract as c
import memory_governance_storage as db
from memory_audit_adapter import AcceptedSourceReview, audit_environment
from memory_audit_source import PinnedGitReader
from memory_governance_local import LocalHost, RepositorySource, SingleRootRegistry
from memory_maintenance_authority import (MaintenanceAuthority, MaintenanceAuthorityProvider,
                                          MaintenanceRequest, intent)

CAPABILITIES = frozenset({'content-write', 'readback', 'recall', 'audit'})
PORT_FILES = ('memory_maintenance_authority.py', 'memory_maintenance_dispatch.py',
              'memory_maintenance.py', 'memory_maintenance_preflight.py', 'governancectl.py')


def maintenance_environment(binding, runtime, operation):
    c.g1_operation(operation)
    return {'operation': operation, 'base': audit_environment(binding, runtime),
            'maintenance_ports': {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                                  for name in PORT_FILES}}


@dataclass(frozen=True)
class MaintenanceQualification:
    binding_digest: str
    operation: str
    environment_bytes: bytes
    evidence_id: str
    expires_at: int


class MaintenanceHost(LocalHost):
    """TCB 組合元件；不提供 initialize，不接受 AuditReadAuthority 的升格。"""

    def __init__(self, factory, authority, *, read_only=False):
        self.factory, self.authority, self.read_only = factory, authority, read_only
        self.operation = c.decode(authority.grant.request.intent_bytes, 20000)['operation']
        # Stop adopts no content and must remain possible with unavailable sources.
        self.reader = (None if self.operation == 'stop' else
                       PinnedGitReader(factory.binding, factory.repository, factory.permits, check=self.check))
        self.reviewer = (None if self.operation == 'stop' else
                         AcceptedSourceReview(factory.accepted_sources, revoked=factory.source_revoked, authority=authority))
        super().__init__(SingleRootRegistry(factory.binding), source=RepositorySource(self.reader, self.reviewer),
                         authority=authority, qualification=self, clock=authority.clock)

    def check(self):
        self.authority.check()
        c.require(self.binding() == self.factory.binding == self.authority.grant.binding,
                  'root-binding-mismatch')
        qualification = self.factory.qualification
        c.require(type(qualification) is MaintenanceQualification
                  and qualification.operation == self.operation
                  and qualification.binding_digest == db.binding_digest(self.binding())
                  and qualification.expires_at > self.authority.clock.clock().utc_seconds
                  and self.factory.qualification_revoked(qualification.evidence_id) is False,
                  'qualification-unavailable')

    def clock(self):
        # Core calls this again inside the transaction and immediately before commit.
        # Keep the request's shorter TTL/revocation and qualification live at those checks.
        self.check()
        if self.reader is not None:
            self.reader.validate_disclosure()
            c.require(self.reviewer.disclosure_valid(), 'source-unavailable')
        return self.authority.clock.clock()

    def qualify(self, binding, runtime, operation):
        self.check()
        if self.reader is not None:
            self.reader.validate_disclosure()
            c.require(self.reviewer.disclosure_valid(), 'source-unavailable')
        allowed = {'readback', 'recall', 'audit'} | (set() if self.read_only else {self.operation, 'authorize'})
        return (binding == self.binding() and operation in allowed
                and runtime['platform'] in {'Darwin', 'Linux'} and runtime['temp_store'] == 'memory'
                and self.factory.qualification.environment_bytes
                == c.canonical(maintenance_environment(binding, runtime, self.operation)))

    def authorize_read(self, binding, purpose, operation_id):
        self.check()
        c.require(not self.read_only or purpose != 'preview', 'capability-unavailable')
        if self.reader is not None:
            self.reader.validate_disclosure()
            c.require(self.reviewer.disclosure_valid(), 'source-unavailable')
        return self.authority.authorize_read(binding, purpose, operation_id)

    def accept_preview(self, binding, preview_bytes):
        self.check()
        c.require(not self.read_only, 'capability-unavailable')
        result = self.authority.accept_preview(binding, preview_bytes)
        self.check()
        return result

    def committed_work_bytes(self, binding):
        self.check()
        c.require(binding == self.binding(), 'root-binding-mismatch')
        return self.factory.storage.committed_work_bytes(binding)

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        c.require(self.qualify(binding, runtime, operation), 'qualification-unavailable')
        return self.factory.storage.work_budget(binding, runtime, files, operation, candidate_bytes)

    def bind_initialized(self, binding, main, lock):
        raise c.ContractError('capability-unavailable')

    def fresh_reader(self):
        self.check()
        return MaintenanceHost(self.factory, self.authority, read_only=True)


class MaintenanceHostFactory:
    """所有建構參數只能由 trusted host 提供；無 CLI/env/import loader。

    Source acceptance 與 operation-specific qualification 必須獨立接受。
    storage port 沿用核心 J/T/G work budget 契約，不能以容量自述取代。
    """

    def __init__(self, *, binding, repository, permits, accepted_sources, qualification,
                 provider, source_revoked, qualification_revoked, storage):
        c.require(binding.capabilities == CAPABILITIES and binding.main_identity is not None
                  and binding.lock_identity is not None, 'capability-unavailable')
        c.require(type(provider) is MaintenanceAuthorityProvider and provider.binding == binding,
                  'authority-unavailable')
        self.binding, self.repository, self.permits = binding, repository, permits
        self.accepted_sources, self.qualification = accepted_sources, qualification
        self.provider, self.storage = provider, storage
        self.source_revoked, self.qualification_revoked = source_revoked, qualification_revoked

    def create_host(self, request):
        c.require(type(request) is MaintenanceRequest, 'authority-unavailable')
        scope = c.decode(self.binding.scope_bytes)
        c.require(request.scope_digest == c.digest(scope) and request.principal_id == scope['principal_id'],
                  'request-scope-mismatch')
        value = intent(c.decode(request.intent_bytes, 20000))
        grant = self.provider.take(request)
        authority = MaintenanceAuthority(self.provider, grant)
        authority.check()
        c.require(callable(getattr(self.storage, 'committed_work_bytes', None))
                  and callable(getattr(self.storage, 'work_budget', None)), 'storage-port-unavailable')
        c.require(type(self.qualification) is MaintenanceQualification
                  and self.qualification.operation == value['operation'], 'qualification-unavailable')
        host = MaintenanceHost(self, authority)
        c.require(host.qualify(self.binding, db.runtime_facts(), value['operation']), 'qualification-unavailable')
        return host


class MaintenanceDispatch:
    """先消耗後建構；例外、讀回或輸出失败均不能使 dispatch 再次可用。"""

    def __init__(self, factory, request):
        c.require(type(factory) is MaintenanceHostFactory and type(request) is MaintenanceRequest,
                  'authority-unavailable')
        self.factory, self.request = factory, request
        self._pid, self._used, self._lock = os.getpid(), False, threading.Lock()

    def acquire(self):
        c.require(os.getpid() == self._pid, 'process-changed')
        with self._lock:
            c.require(not self._used, 'dispatch-consumed')
            self._used = True
        return self.factory.create_host(self.request)
