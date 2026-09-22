"""Host-owned audit 授權狀態；程式 API 是 TCB，不是人類確認或設定載入器。

磁碟只有 lifecycle，RAM grant 不可恢復。每個 provider 僅撤銷自己的要求；
儲存結果不明即永久停用該 provider。新 provider 須重新接受新要求。
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass, replace
import fcntl
import os
from pathlib import Path
import sqlite3
import threading
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_host import ClockSample, RootBinding
from memory_audit_adapter import ReadGrant
from memory_audit_dispatch import AuditRequest

MAX_REQUESTS = 1024
LIMITS = {'data_limit_bytes': 4 * 1024 * 1024}
SQL = (
    'CREATE TABLE authority_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), document BLOB NOT NULL) STRICT',
    "CREATE TABLE requests (request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, principal_id TEXT NOT NULL, scope_digest TEXT NOT NULL, expires_at INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('accepted','consumed','revoked'))) STRICT",
)
SCHEMA = c.digest({'contract': 'mg1-audit-authority/v1', 'sql': list(SQL)})


def target_digest(binding):
    c.require(type(binding) is RootBinding and binding.capabilities == frozenset({'audit'})
              and binding.main_identity is not None and binding.lock_identity is not None, 'read-unavailable')
    return c.digest({'root': str(binding.root), 'directory': list(binding.directory_identity),
                     'main': list(binding.main_identity), 'lock': list(binding.lock_identity),
                     'scope': c.decode(binding.scope_bytes), 'profile': c.decode(binding.profile_bytes),
                     'filesystem': binding.filesystem_id, 'adapter': binding.adapter_fingerprint,
                     'capabilities': sorted(binding.capabilities)})


@dataclass(frozen=True)
class AuthorityStoreBinding:
    files: RootBinding
    target_digest: str
    store_id: str


def _metadata(store):
    return c.canonical({'schema': SCHEMA, 'target_digest': store.target_digest, 'store_id': store.store_id})


def initialize_store(root: Path, target: RootBinding) -> AuthorityStoreBinding:
    """可信 host 明確授權建立；僅空 owner-only 目錄。失敗保留產物，不修復或覆寫。"""
    digest = target_digest(target)
    c.require(type(root) is type(Path()) and root.is_absolute()
              and root != target.root and root not in target.root.parents
              and target.root not in root.parents, 'unsafe-root')
    files = replace(target, root=root, directory_identity=db.identity(root.lstat()),
                    main_identity=None, lock_identity=None)
    directory = db.root_fd(files)
    lock = main = connection = None
    try:
        c.require(not db.inventory(directory, files, initialized=False), 'root-not-empty')
        lock = os.open(db.LOCK, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main = os.open(db.MAIN, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        files = replace(files, main_identity=db.identity(os.fstat(main)), lock_identity=db.identity(os.fstat(lock)))
        store = AuthorityStoreBinding(files, digest, str(uuid.uuid4()))
        connection = sqlite3.connect((root / db.MAIN).as_uri() + '?mode=rw&cache=private',
                                     uri=True, isolation_level=None, timeout=0)
        for setting in ('page_size=4096', 'journal_mode=DELETE', 'auto_vacuum=INCREMENTAL',
                        'synchronous=EXTRA', 'temp_store=MEMORY', 'trusted_schema=OFF',
                        'max_page_count=1024'):
            connection.execute('PRAGMA ' + setting)
        connection.execute('BEGIN IMMEDIATE')
        for statement in SQL:
            connection.execute(statement)
        connection.execute('INSERT INTO authority_meta VALUES (1,?)', (_metadata(store),))
        connection.commit()
        connection.close()
        connection = None
        os.fsync(main)
        os.fsync(lock)
        os.fsync(directory)
        db.inventory(directory, files)
        return store
    finally:
        if connection is not None:
            connection.close()
        for fd in (main, lock, directory):
            if fd is not None:
                os.close(fd)


@contextlib.contextmanager
def _connection(store, *, writer=False):
    # 共用已驗證的 owner/identity/flock/sidecar/readonly SQLite 機制，獨立 schema。
    with db.locked(store.files, exclusive=writer):
        with contextlib.closing(db.connect(store.files, LIMITS, writer=writer)) as connection:
            schema = connection.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name").fetchmany(3)
            c.require(schema == [(statement,) for statement in SQL], 'read-unavailable')
            c.require(connection.execute('SELECT singleton,document FROM authority_meta').fetchmany(2)
                      == [(1, _metadata(store))], 'read-unavailable')
            c.require(connection.execute('SELECT count(*) FROM requests').fetchone()[0] <= MAX_REQUESTS,
                      'resource-limit')
            try:
                if writer:
                    connection.execute('BEGIN IMMEDIATE')
                yield connection
            finally:
                if connection.in_transaction:
                    connection.rollback()


class AuditAuthorityProvider:
    """每次 host 接受呼叫 accept()，產生新 UUID；沒有磁碟 grant 載入器。

    accepted/consumed/revoked rows 是防重播紀錄，不是 bearer credentials。
    不同 instance/session、fork 或 restart 不能接手 RAM 授權。revoke 只處理
    本 instance 核發的要求；沒有跨程序 revoke-success 宣稱或自動重試。
    """

    def __init__(self, store: AuthorityStoreBinding, binding: RootBinding, *, clock):
        c.require(type(store) is AuthorityStoreBinding and store.target_digest == target_digest(binding),
                  'read-unavailable')
        self.store, self.binding, self.clock = store, binding, clock
        self._pid, self._session = os.getpid(), str(uuid.uuid4())
        self._mutex = threading.RLock()
        self._pending, self._live, self._known = {}, {}, set()
        self._failed = False

    def _check(self):
        c.require(not self._failed and self._pid == os.getpid(), 'read-unavailable')

    def close(self):
        if self._pid != os.getpid():
            # fork 可能繼承另一條 thread 持有的 mutex；子程序不能等待該 lock。
            self._failed = True
            self._pending.clear()
            self._live.clear()
            return
        with self._mutex:
            self._failed = True
            self._pending.clear()
            self._live.clear()

    def accept(self, *, lifetime_seconds=300) -> AuditRequest:
        """僅在 host 已收到新的明確授權後呼叫；本 API 本身不驗證人類身分。"""
        self._check()
        with self._mutex:
            self._check()
            c.integer(lifetime_seconds, 1, 300)
            sample = self.clock.clock()
            c.require(type(sample) is ClockSample, 'read-unavailable')
            c.integer(sample.utc_seconds)
            c.integer(sample.monotonic_ns)
            c.uuid(sample.process_id)
            c.integer(sample.utc_seconds + lifetime_seconds)
            request = AuditRequest(c.decode(self.binding.scope_bytes)['principal_id'], str(uuid.uuid4()),
                                   c.digest(c.decode(self.binding.scope_bytes)))
            grant = ReadGrant(self.binding, request.principal_id, request.request_id, sample,
                              sample.utc_seconds + lifetime_seconds)
            try:
                with _connection(self.store, writer=True) as connection:
                    c.require(connection.execute('SELECT count(*) FROM requests').fetchone()[0] < MAX_REQUESTS,
                              'resource-limit')
                    connection.execute('INSERT INTO requests VALUES (?,?,?,?,?,?)',
                                       (request.request_id, self._session, request.principal_id,
                                        request.scope_digest, grant.expires_at, 'accepted'))
                    connection.commit()
                    c.require(self._row(connection, request.request_id) == self._expected(grant, 'accepted'),
                              'read-unavailable')
                self._known.add(request.request_id)
                self._pending[request.request_id] = grant
                return request
            except BaseException:
                self.close()
                raise

    def _row(self, connection, request_id):
        return connection.execute('SELECT session_id,principal_id,scope_digest,expires_at,state FROM requests WHERE request_id=?',
                                  (request_id,)).fetchone()

    def _expected(self, grant, state):
        return (self._session, grant.principal_id, c.digest(c.decode(grant.binding.scope_bytes)),
                grant.expires_at, state)

    def pending_current(self, request: AuditRequest) -> bool:
        """僅觀察本 instance RAM／clock，不消耗、不查磁碟、不改 lifecycle。

        True 不是可執行性證明；take_grant 仍須核對持久紀錄並原子消耗。
        預檢失敗不關閉 provider，不把觀察當成新的接受要求。
        """
        if self._pid != os.getpid():
            return False
        with self._mutex:
            try:
                self._check()
                c.require(type(request) is AuditRequest, 'read-unavailable')
                grant = self._pending.get(request.request_id)
                if grant is None:
                    return False
                sample = self.clock.clock()
                return (request.principal_id == grant.principal_id
                        and request.scope_digest == c.digest(c.decode(self.binding.scope_bytes))
                        and type(sample) is ClockSample and sample.process_id == grant.issued.process_id
                        and grant.issued.utc_seconds <= sample.utc_seconds < grant.expires_at
                        and 0 <= sample.monotonic_ns - grant.issued.monotonic_ns
                        < (grant.expires_at - grant.issued.utc_seconds) * 1_000_000_000)
            except Exception:
                return False

    def take_grant(self, request: AuditRequest) -> ReadGrant:
        self._check()
        with self._mutex:
            self._check()
            c.require(type(request) is AuditRequest, 'read-unavailable')
            grant = self._pending.pop(request.request_id, None)
            c.require(grant is not None, 'read-unavailable')
            try:
                c.require(request.principal_id == grant.principal_id
                          and request.scope_digest == c.digest(c.decode(self.binding.scope_bytes)), 'read-unavailable')
                sample = self.clock.clock()
                c.require(type(sample) is ClockSample and sample.process_id == grant.issued.process_id
                          and grant.issued.utc_seconds <= sample.utc_seconds < grant.expires_at
                          and 0 <= sample.monotonic_ns - grant.issued.monotonic_ns
                          < (grant.expires_at - grant.issued.utc_seconds) * 1_000_000_000, 'read-unavailable')
                with _connection(self.store, writer=True) as connection:
                    c.require(self._row(connection, request.request_id) == self._expected(grant, 'accepted'),
                              'read-unavailable')
                    changed = connection.execute("UPDATE requests SET state='consumed' WHERE request_id=? AND state='accepted'",
                                                 (request.request_id,))
                    c.require(changed.rowcount == 1, 'read-unavailable')
                    connection.commit()
                    c.require(self._row(connection, request.request_id) == self._expected(grant, 'consumed'),
                              'read-unavailable')
                self._live[request.request_id] = grant
                return grant
            except BaseException:
                self.close()
                raise

    def revoke(self, request_id: str):
        """先使 owner RAM 授權失效再寫紀錄；失敗不回報撤銷已持久化。"""
        self._check()
        with self._mutex:
            self._check()
            c.require(request_id in self._known, 'read-unavailable')
            self._pending.pop(request_id, None)
            self._live.pop(request_id, None)
            try:
                with _connection(self.store, writer=True) as connection:
                    row = self._row(connection, request_id)
                    c.require(row is not None and row[0] == self._session, 'read-unavailable')
                    changed = connection.execute("UPDATE requests SET state='revoked' WHERE request_id=?", (request_id,))
                    c.require(changed.rowcount == 1, 'read-unavailable')
                    connection.commit()
                    c.require(self._row(connection, request_id)[-1] == 'revoked', 'read-unavailable')
            except BaseException:
                self.close()
                raise

    def revoked(self, request_id: str) -> bool:
        if self._pid != os.getpid():
            return True
        with self._mutex:
            try:
                self._check()
                grant = self._live.get(request_id)
                if grant is None:
                    return True
                with _connection(self.store) as connection:
                    if self._row(connection, request_id) != self._expected(grant, 'consumed'):
                        self.close()
                        return True
                return False
            except Exception:
                self.close()
                return True
