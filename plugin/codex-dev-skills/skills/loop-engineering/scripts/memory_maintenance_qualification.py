"""固定官方 SQLite／POSIX build 的受限 disk work 准入，非完整 MG1 資格。

來源及推導見 references/memory-maintenance-local-storage.md。同 UID 與 build
程序為已接受的 TCB；source ID／compile options 不證明抗惡意二進位偽造。
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import replace
import os
from pathlib import Path
import uuid

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_core import GovernanceCore
from memory_governance_host import RootBinding
from memory_governance_local import LocalClock, LocalHost, SingleRootRegistry
from memory_maintenance_dispatch import CAPABILITIES
import memory_maintenance_binding as b

SOURCE_ID = '2026-07-24 19:02:57 bf7c7f30031888f4e796e429ab3978879485813aaca6f641c7b33e4e09459bcc'
ARCHIVE_SHA3 = '628a44cfe82c66aed1ccbbe85a562d2e33ebe64b3288981ed76285612227934e'
PAGE = 4096
SECTOR_MAX = 65536
DATA_LIMIT = 268435456
QUALIFICATION = 'mg1-local-disk-v1'
REQUIRED_OPTIONS = frozenset({'TEMP_STORE=3', 'OMIT_LOAD_EXTENSION', 'THREADSAFE=1',
    'MAX_MMAP_SIZE=0', 'MAX_WORKER_THREADS=0', 'ENABLE_LOCKING_STYLE=0'})


def verify_runtime(runtime):
    c.require(runtime['python_version'] == '3.12.9' and runtime['platform'] == 'Darwin'
              and runtime['sqlite_version'] == '3.53.4' and runtime['sqlite_source_id'] == SOURCE_ID,
              'qualification-unavailable')
    options = set(runtime['compile_options'])
    c.require(REQUIRED_OPTIONS <= options and not any(
        word in option for option in options for word in ('CODEC', 'OS_OTHER', 'DEFAULT_UNIX_VFS', 'OMIT_DISKIO', 'OMIT_MEMORYDB')),
        'qualification-unavailable')
    c.require(runtime['schema_fingerprint'] == db.SCHEMA_FINGERPRINT
              and runtime['sql_fingerprint'] == c.digest(list(db.SQL))
              and runtime['cache_spill'] == 'off' and runtime['locking_mode'] == 'normal'
              and runtime['temp_store'] == 'memory' and runtime['page_size'] == PAGE
              and runtime['journal_mode'] == 'delete'
              and runtime['initial_page_limit'] == db.INITIAL_PAGE_LIMIT == 64,
              'qualification-unavailable')


def disk_bounds(main_bytes, ceiling):
    c.integer(main_bytes)
    c.integer(ceiling, 1)
    c.require(main_bytes % PAGE == 0 and main_bytes <= ceiling and ceiling % PAGE == 0,
              'invalid-storage-size')
    journal = (main_bytes // PAGE) * (PAGE + 8) + 2 * SECTOR_MAX
    growth = ceiling - main_bytes
    required = ((journal + growth + PAGE - 1) // PAGE) * PAGE
    return journal, growth, required


class LocalStorage:
    def __init__(self, binding, *, check):
        self.binding, self.check = binding, check

    def verify_runtime(self, runtime):
        self.check()
        verify_runtime(runtime)
        c.require(c.decode(self.binding.profile_bytes)['data_limit_bytes'] == DATA_LIMIT,
                  'qualification-unavailable')

    def qualify(self, binding, runtime, operation):
        c.require(binding == self.binding, 'root-binding-mismatch')
        self.verify_runtime(runtime)
        return operation in {'initialize', 'audit', 'readback'}

    def evidence(self):
        return {'qualification_id': QUALIFICATION, 'sqlite_source_id': SOURCE_ID,
            'archive_sha3_256': ARCHIVE_SHA3, 'page_bytes': PAGE, 'sector_max_bytes': SECTOR_MAX,
            'data_limit_bytes': DATA_LIMIT, 'disk_temp_bound_bytes': 0,
            'journal_formula': 'N*(4096+8)+2*65536', 'growth_formula': 'D-M',
            'admission_is_reservation': False, 'full_database_stop_guaranteed': False,
            'physical_full_or_power_loss_qualified': False, 'rss_or_deadline_qualified': False}

    def committed_work_bytes(self, binding):
        self.check()
        c.require(binding == self.binding, 'root-binding-mismatch')
        # One cooperative writer holds the existing root coordination lock. No
        # background jobs/reservations are admitted by this adapter.
        return 0

    def work_budget(self, binding, runtime, files, operation, candidate_bytes):
        self.verify_runtime(runtime)
        c.require(binding == self.binding, 'root-binding-mismatch')
        c.g1_operation(operation)
        c.require({f['role'] for f in files} <= {'main', 'coordination-lock', 'journal'}
                  and len([f for f in files if f['role'] == 'main']) == 1
                  and all(f['bytes'] == 0 for f in files if f['role'] != 'main'), 'recovery-required')
        main = next(f['bytes'] for f in files if f['role'] == 'main')
        # Match actual page_count, file size and effective writer pragmas, not
        # just the file list's internally consistent JSON.
        with closing(db.connect(binding, c.decode(binding.profile_bytes))) as connection:
            c.require(connection.execute('PRAGMA page_count').fetchone()[0] * PAGE == main,
                      'storage-drift')
        journal, growth, required = disk_bounds(main, DATA_LIMIT)
        return {'qualification_id': QUALIFICATION, 'file_snapshot_digest': c.digest(files),
            'journal_bound_bytes': journal, 'temp_bound_bytes': 0,
            'growth_bound_bytes': growth, 'required_work_bytes': required}


def initialize_local(workspace, repository, repository_id, ui, adapter_fingerprint, *, on_mutation_attempt=None):
    c.opaque(repository_id)
    parent = b.directory(workspace.parent, private=False)
    repo_fds = []
    workspace_fd = root_fd = None
    clock = LocalClock()
    start = clock.clock()
    try:
        parent_identity = db.identity(os.fstat(parent))
        for path in (repository, repository / '.git', repository / '.git/objects'):
            repo_fds.append(b.directory(path, private=False))
        repo_ids = [db.identity(os.fstat(fd)) for fd in repo_fds]
        # Loose object reader does not accept alternates, worktree .git files,
        # replacement refs, or a caller-selected executable/loader.
        c.require(not workspace.exists() and not workspace.is_symlink(), 'root-not-empty')
        verify_runtime(db.runtime_facts())
        limits = {**c.DEFAULT_PROFILE, 'data_limit_bytes': DATA_LIMIT,
                  'maintenance_max_bytes': DATA_LIMIT * 5 // 4}
        scope = {'principal_id': str(uuid.uuid4()), 'root_id': str(uuid.uuid4()),
            'repository_id': repository_id, 'schema_fingerprint': db.SCHEMA_FINGERPRINT,
            'profile_digest': c.digest(limits), 'policy_fingerprint': c.digest(c.POLICY)}
        # The enforced 64-page new database ceiling bounds both growth and any
        # initialization journal, conservatively counting 64 old pages too.
        init_journal = 64 * (PAGE + 8) + 2 * SECTOR_MAX
        init_growth = 64 * PAGE
        init_required = ((init_journal + init_growth + PAGE - 1) // PAGE) * PAGE
        def check_parent():
            ui.check()
            from memory_maintenance_local import fingerprint
            c.require(fingerprint() == adapter_fingerprint, 'qualification-unavailable')
            sample = clock.clock()
            c.require(start.utc_seconds <= sample.utc_seconds < start.utc_seconds + 300
                      and start.monotonic_ns <= sample.monotonic_ns < start.monotonic_ns + 300_000_000_000,
                      'expired-or-clock-changed')
            fresh = b.directory(workspace.parent, private=False)
            try:
                c.require(db.identity(os.fstat(fresh)) == parent_identity, 'root-binding-mismatch')
                fs = os.fstatvfs(fresh)
                c.require(fs.f_bavail * fs.f_frsize >= init_required, 'insufficient-space')
            finally:
                os.close(fresh)
            verify_runtime(db.runtime_facts())
            for path, expected in zip((repository, repository / '.git', repository / '.git/objects'), repo_ids):
                fresh = b.directory(path, private=False)
                try:
                    c.require(db.identity(os.fstat(fresh)) == expected, 'source-identity-mismatch')
                finally:
                    os.close(fresh)
        check_parent()
        view = {'contract_version': 'mg1-local-initialization/v1', 'workspace': str(workspace),
            'parent_identity': list(parent_identity), 'repository': str(repository),
            'repository_identities': [list(i) for i in repo_ids], 'scope': scope,
            'profile': limits, 'policy': c.POLICY, 'runtime': db.runtime_facts(),
            'adapter_fingerprint': adapter_fingerprint, 'enabled_after_creation': False,
            'initial_page_limit': 64, 'journal_bound_bytes': init_journal,
            'growth_bound_bytes': init_growth, 'required_work_bytes': init_required,
            'creates': ['workspace 0700', 'managed 0700', 'managed.sqlite3 0600',
                        'coordination.lock 0600', 'binding.json 0600'],
            'failure_policy': 'retain partial; no replay, overwrite, repair or cleanup'}
        c.require(ui.accept('CREATE', c.canonical(view)), 'request-not-accepted')
        check_parent()
        # mkdir is exclusive. Existing or racing paths cannot be overwritten.
        if on_mutation_attempt is not None:
            on_mutation_attempt()
        os.mkdir(workspace.name, mode=0o700, dir_fd=parent)
        os.fsync(parent)
        workspace_fd = b.directory(workspace)
        os.mkdir('managed', mode=0o700, dir_fd=workspace_fd)
        os.fsync(workspace_fd)
        root = workspace / 'managed'
        root_fd = b.directory(root)
        binding = RootBinding(root, db.identity(os.fstat(root_fd)), None, None,
            c.canonical(scope), c.canonical(limits), 'posix-' + str(os.fstat(root_fd).st_dev),
            adapter_fingerprint, CAPABILITIES | {'initialize'})
        registry = SingleRootRegistry(binding)
        def check():
            check_parent()
            opened = db.root_fd(binding)
            os.close(opened)
        class InitAuthority:
            def accept_initialization(self, actual):
                check()
                c.require(actual == binding, 'root-binding-mismatch')
                accepted = ui.accept('INITIALIZE', c.canonical({**view,
                    'root_identity': list(binding.directory_identity),
                    'workspace_identity': list(db.identity(os.fstat(workspace_fd)))}))
                check()
                return accepted
        storage = LocalStorage(binding, check=check)
        host = LocalHost(registry, authority=InitAuthority(), qualification=storage, clock=clock)
        result = GovernanceCore(host, enabled=True).initialize()
        rebound = replace(registry.binding(), capabilities=CAPABILITIES)
        # Fresh metadata/schema/item/proof readback precedes a disabled descriptor.
        with db.locked(rebound), closing(db.connect(rebound, limits)) as connection:
            snapshot = db.snapshot(connection, scope, limits)
            c.require(snapshot.digest == result['state_digest'] and snapshot.items == snapshot.proofs == 0,
                      'initialization-readback-mismatch')
        descriptor = {'contract_version': 'mg1-local-binding/v1', 'enabled': False,
            'workspace_identity': list(db.identity(os.fstat(workspace_fd))),
            'root_identity': list(rebound.directory_identity), 'main_identity': list(rebound.main_identity),
            'lock_identity': list(rebound.lock_identity), 'repository': str(repository),
            'repository_identity': list(repo_ids[0]), 'git_identity': list(repo_ids[1]),
            'objects_identity': list(repo_ids[2]), 'scope': scope, 'profile': limits,
            'filesystem_id': rebound.filesystem_id, 'adapter_fingerprint': adapter_fingerprint}
        b.create_descriptor(workspace_fd, descriptor)
        b.load(workspace, adapter_fingerprint, enabled=False)
        return {'status': 'initialized', 'outcome': 'applied', 'write_performed': True,
                'enabled': False, 'scope': scope, 'state_digest': snapshot.digest,
                'local_contract': 'mg1-local-operation/v1', 'full_mg1_qualified': False}
    finally:
        for fd in [root_fd, workspace_fd, parent, *repo_fds]:
            if fd is not None:
                os.close(fd)
