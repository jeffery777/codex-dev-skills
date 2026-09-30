"""單專案本機 descriptor；只保存身分，不保存人類接受或可重播 grant。

位置由 operator 精確指定，不自動探索任何既有 memory。全部查讀皆由 enabled
正式入口在取得當次讀取接受後呼叫。同 UID 為 TCB，內容自洽本身不提供授權。
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import stat

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_host import RootBinding
from memory_audit_source import GitRepositoryBinding
from memory_maintenance_dispatch import CAPABILITIES

NAME = 'binding.json'
MAX_DESCRIPTOR = 16384
FIELDS = {'contract_version', 'enabled', 'workspace_identity', 'root_identity',
          'main_identity', 'lock_identity', 'repository', 'repository_identity',
          'git_identity', 'objects_identity', 'scope', 'profile', 'filesystem_id',
          'adapter_fingerprint'}


def directory(path, *, private=True):
    c.require(type(path) is type(Path()) and path.is_absolute()
              and path == path.resolve(strict=True), 'unsafe-root')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        c.require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                  and not info.st_mode & (0o077 if private else 0o022), 'unsafe-root')
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_file(directory_fd, name, maximum):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        c.require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                  and not before.st_mode & 0o077 and before.st_nlink == 1
                  and before.st_dev == os.fstat(directory_fd).st_dev
                  and before.st_size <= maximum, 'unsafe-descriptor')
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(fd, min(8192, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        named = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        signature = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns,
                                st.st_uid, st.st_mode, st.st_nlink)
        c.require(len(data) == before.st_size and signature(before) == signature(after)
                  == signature(named), 'descriptor-drift')
        return bytes(data), signature(before)
    finally:
        os.close(fd)


def file_identity(value):
    c.require(type(value) is list and len(value) == 2, 'invalid-file-identity')
    return tuple(c.integer(n) for n in value)


@dataclass(frozen=True)
class LocalBinding:
    workspace: Path
    data: bytes
    signature: tuple
    binding: RootBinding
    repository: GitRepositoryBinding

    def check(self, *, enabled=True, sources=True):
        fd = directory(self.workspace)
        try:
            data, signature = read_file(fd, NAME, MAX_DESCRIPTOR)
            c.require(data == self.data and signature == self.signature, 'descriptor-drift')
            value = c.decode(data, MAX_DESCRIPTOR)
            c.require(db.identity(os.fstat(fd)) == file_identity(value['workspace_identity']),
                      'root-binding-mismatch')
            c.require(not enabled or value['enabled'] is True, 'request-revoked')
        finally:
            os.close(fd)
        root = db.root_fd(self.binding)
        try:
            db.inventory(root, self.binding)
        finally:
            os.close(root)
        if not sources:
            return
        repo = self.repository
        for path, expected in ((repo.root, repo.directory_identity),
                               (repo.root / '.git', repo.git_identity),
                               (repo.root / '.git/objects', repo.objects_identity)):
            fd = directory(path, private=False)
            try:
                c.require(db.identity(os.fstat(fd)) == expected, 'source-identity-mismatch')
            finally:
                os.close(fd)


def load(workspace, adapter_fingerprint, *, enabled=True, sources=True):
    fd = directory(workspace)
    try:
        data, signature = read_file(fd, NAME, MAX_DESCRIPTOR)
        value = c.decode(data, MAX_DESCRIPTOR)
        c.fields(value, FIELDS)
        c.require(value['contract_version'] == 'mg1-local-binding/v1'
                  and type(value['enabled']) is bool and c.canonical(value) == data,
                  'invalid-descriptor')
        c.require(db.identity(os.fstat(fd)) == file_identity(value['workspace_identity']),
                  'root-binding-mismatch')
    finally:
        os.close(fd)
    limits = c.profile(value['profile'])
    scope = c.scope(value['scope'], c.digest(limits), c.digest(c.POLICY))
    c.require(scope['schema_fingerprint'] == db.SCHEMA_FINGERPRINT
              and value['adapter_fingerprint'] == adapter_fingerprint, 'qualification-unavailable')
    c.opaque(value['filesystem_id'])
    binding = RootBinding(workspace / 'managed', file_identity(value['root_identity']),
        file_identity(value['main_identity']), file_identity(value['lock_identity']),
        c.canonical(scope), c.canonical(limits), value['filesystem_id'], adapter_fingerprint, CAPABILITIES)
    c.require(type(value['repository']) is str, 'source-unavailable')
    repository = GitRepositoryBinding(Path(value['repository']), file_identity(value['repository_identity']),
        file_identity(value['git_identity']), file_identity(value['objects_identity']), scope['repository_id'])
    result = LocalBinding(workspace, data, signature, binding, repository)
    result.check(enabled=enabled, sources=sources)
    # A separately opened read-only connection verifies the initialized schema/scope.
    with db.locked(binding), closing(db.connect(binding, limits)) as connection:
        db.metadata(connection, scope)
    return result


def create_descriptor(workspace_fd, value):
    """新檔 exclusive create；失敗保留 partial，不能重試覆寫或自動刪除。"""
    c.fields(value, FIELDS)
    data = c.canonical(value, MAX_DESCRIPTOR)
    fd = os.open(NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                 dir_fd=workspace_fd)
    try:
        offset = 0
        while offset < len(data):
            n = os.write(fd, data[offset:])
            c.require(n > 0, 'output-unavailable')
            offset += n
        os.fsync(fd)
        os.fsync(workspace_fd)
    finally:
        os.close(fd)
    actual, _ = read_file(workspace_fd, NAME, MAX_DESCRIPTOR)
    c.require(actual == data, 'initialization-readback-mismatch')


def set_enabled(current, enabled):
    """精確設定須由入口先交人工接受；原子 replacement 使 pending 身分立即失效。"""
    c.require(type(enabled) is bool, 'invalid-descriptor')
    with db.locked(current.binding, exclusive=True):
        _set_enabled_locked(current, enabled)


def _set_enabled_locked(current, enabled):
    current.check(enabled=False, sources=False)
    value = c.decode(current.data, MAX_DESCRIPTOR)
    value['enabled'] = enabled
    fd = directory(current.workspace)
    temp_name = 'binding-' + os.urandom(16).hex() + '.json'
    temp = None
    try:
        temp = os.open(temp_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                       0o600, dir_fd=fd)
        data = c.canonical(value, MAX_DESCRIPTOR)
        offset = 0
        while offset < len(data):
            n = os.write(temp, data[offset:])
            c.require(n > 0, 'output-unavailable')
            offset += n
        os.fsync(temp)
        current.check(enabled=False, sources=False)
        os.replace(temp_name, NAME, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
        actual, _ = read_file(fd, NAME, MAX_DESCRIPTOR)
        c.require(actual == data, 'descriptor-drift')
    finally:
        if temp is not None:
            os.close(temp)
        os.close(fd)
    # On failure even a temporary file remains for diagnosis; no implicit cleanup.
