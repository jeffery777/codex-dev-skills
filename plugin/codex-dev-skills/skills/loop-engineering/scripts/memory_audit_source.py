"""Audit 專用的固定 Git loose-object reader；不執行 Git 或解讀 repository config。

只支援 host 已接受的本機 SHA-1 commit/tree/blob。每個物件完整驗 hash，拒絕
symlink、非一般檔案、缺物件及 packed-only repository；不 fetch 或展開其他來源。
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import stat
import time
import zlib

import memory_governance_contract as c
import memory_governance_storage as db
from memory_governance_local import MAX_ARTIFACT_BYTES, RepositoryArtifact

MAX_OBJECT_BYTES = MAX_ARTIFACT_BYTES + 128
MAX_COMPRESSED_BYTES = MAX_OBJECT_BYTES + 1024
MAX_PATH_PARTS = 16


@dataclass(frozen=True)
class GitRepositoryBinding:
    root: Path
    directory_identity: tuple[int, int]
    git_identity: tuple[int, int]
    objects_identity: tuple[int, int]
    repository_id: str


@dataclass(frozen=True)
class ArtifactPermit:
    source_id: str
    revision: str
    path: str
    sha256: str


def _path_parts(value):
    c.text(value, 1024)
    parts = value.split('/')
    c.require(len(parts) <= MAX_PATH_PARTS and all(
        part not in {'', '.', '..'} and '\\' not in part and '\x00' not in part for part in parts),
        'source-unavailable')
    return parts


def _oid(value):
    c.require(type(value) is str and re.fullmatch('[0-9a-f]{40}', value) is not None, 'source-unavailable')
    return value


def _signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


class PinnedGitReader:
    """允許集合由可信 host 程式提供；provenance 只能選中已接受的 tuple。

    check() 每個 I/O chunk 前後重查 authority／撤銷／總時間。時間限制為本機
    同步 I/O 的合作式 deadline，不聲稱能中斷 OS 中不可中斷的 filesystem syscall。
    """

    def __init__(self, binding, repository: GitRepositoryBinding, permits: tuple[ArtifactPermit, ...],
                 *, check, max_bytes=MAX_ARTIFACT_BYTES, timeout_ms=250):
        c.require(type(repository) is GitRepositoryBinding and type(permits) is tuple
                  and 1 <= len(permits) <= 16, 'source-unavailable')
        c.integer(max_bytes, 1, MAX_ARTIFACT_BYTES)
        c.integer(timeout_ms, 1, 1000)
        c.opaque(repository.repository_id)
        c.require(repository.repository_id == c.decode(binding.scope_bytes)['repository_id'], 'source-unavailable')
        for permit in permits:
            c.require(type(permit) is ArtifactPermit, 'source-unavailable')
            c.opaque(permit.source_id)
            _oid(permit.revision)
            _path_parts(permit.path)
            c.digest_text(permit.sha256)
        c.require(len(set((p.source_id, p.revision, p.path) for p in permits)) == len(permits), 'source-unavailable')
        self.binding, self.repository, self.permits = binding, repository, permits
        self.check, self.max_bytes, self.timeout_ms = check, max_bytes, timeout_ms
        self._observed = {}

    def _check(self, deadline):
        self.check()
        c.require(time.monotonic() < deadline, 'source-timeout')

    def _directory(self, stack, path, identity=None, *, parent=None):
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        stack.callback(os.close, fd)
        info = os.fstat(fd)
        c.require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
                  and not info.st_mode & 0o022 and (identity is None or db.identity(info) == identity),
                  'source-identity-mismatch')
        return fd

    def _object(self, objects, oid, expected, deadline):
        _oid(oid)
        self._check(deadline)
        with ExitStack() as stack:
            bucket = self._directory(stack, oid[:2], parent=objects)
            fd = os.open(oid[2:], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=bucket)
            stack.callback(os.close, fd)
            before = os.fstat(fd)
            # 同一 snapshot 固定首次成功驗證的物件，不讓後續失敗改寫揭露基準。
            c.require(oid not in self._observed or self._observed[oid] == _signature(before),
                      'source-identity-mismatch')
            c.require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                      and before.st_nlink == 1 and not before.st_mode & 0o022
                      and before.st_dev == self.repository.objects_identity[0]
                      and before.st_size <= MAX_COMPRESSED_BYTES, 'source-unavailable')
            compressed = bytearray()
            while len(compressed) <= MAX_COMPRESSED_BYTES:
                self._check(deadline)
                chunk = os.read(fd, min(8192, MAX_COMPRESSED_BYTES + 1 - len(compressed)))
                if not chunk:
                    break
                compressed.extend(chunk)
            after = os.fstat(fd)
            c.require(len(compressed) == before.st_size and _signature(before) == _signature(after)
                      and _signature(os.stat(oid[2:], dir_fd=bucket, follow_symlinks=False)) == _signature(before),
                      'source-identity-mismatch')
        self._check(deadline)
        try:
            decoder = zlib.decompressobj()
            raw = decoder.decompress(compressed, MAX_OBJECT_BYTES + 1)
            c.require(len(raw) <= MAX_OBJECT_BYTES and decoder.eof and not decoder.unused_data
                      and not decoder.unconsumed_tail, 'source-too-large-or-incomplete')
        except zlib.error as exc:
            raise c.ContractError('source-integrity-failed') from exc
        c.require(hashlib.sha1(raw).hexdigest() == oid, 'source-integrity-failed')
        header, separator, content = raw.partition(b'\0')
        c.require(separator and header == expected.encode() + b' ' + str(len(content)).encode(),
                  'source-integrity-failed')
        self._check(deadline)
        self._observed.setdefault(oid, _signature(before))
        return content

    def validate_disclosure(self):
        """只重查已驗證物件與目錄的身分，不讀新內容或嘗試修復。"""
        repo = self.repository
        with ExitStack() as stack:
            root = self._directory(stack, repo.root, repo.directory_identity)
            git = self._directory(stack, '.git', repo.git_identity, parent=root)
            objects = self._directory(stack, 'objects', repo.objects_identity, parent=git)
            for oid, expected in self._observed.items():
                with ExitStack() as item_stack:
                    bucket = self._directory(item_stack, oid[:2], parent=objects)
                    c.require(_signature(os.stat(oid[2:], dir_fd=bucket, follow_symlinks=False)) == expected,
                              'source-identity-mismatch')

    def _blob(self, objects, permit, deadline):
        commit = self._object(objects, permit.revision, 'commit', deadline)
        first = commit.split(b'\n', 1)[0]
        c.require(re.fullmatch(b'tree [0-9a-f]{40}', first) is not None, 'source-integrity-failed')
        oid = first[5:].decode('ascii')
        parts = _path_parts(permit.path)
        for index, part in enumerate(parts):
            tree = self._object(objects, oid, 'tree', deadline)
            offset, matched, names = 0, None, set()
            while offset < len(tree):
                end = tree.find(b'\0', offset)
                c.require(end >= offset and end + 21 <= len(tree), 'source-integrity-failed')
                mode, separator, name = tree[offset:end].partition(b' ')
                c.require(separator and name not in names and name not in {b'', b'.', b'..'}
                          and b'/' not in name, 'source-integrity-failed')
                names.add(name)
                if name == part.encode('utf-8'):
                    matched = (mode, tree[end + 1:end + 21].hex())
                offset = end + 21
            c.require(matched is not None, 'source-unavailable')
            mode, oid = matched
            c.require(mode in ({b'100644', b'100755'} if index == len(parts) - 1 else {b'40000'}),
                      'source-unavailable')
        content = self._object(objects, oid, 'blob', deadline)
        c.require(len(content) <= self.max_bytes and hashlib.sha256(content).hexdigest() == permit.sha256,
                  'source-integrity-failed')
        return content

    def read_artifact(self, binding, provenance_bytes):
        self.check()
        c.require(binding == self.binding, 'root-binding-drift')
        provenance = c.decode(provenance_bytes, 16384)
        reference = provenance.get('reference', {})
        match = [p for p in self.permits if provenance.get('kind') == 'repo-artifact'
                 and p.source_id == provenance.get('source_id') and p.revision == provenance.get('source_revision')
                 and p.path == reference.get('path') and p.sha256 == provenance.get('source_digest')
                 and reference.get('repository_id') == self.repository.repository_id]
        c.require(len(match) == 1, 'source-unavailable')
        permit, repo = match[0], self.repository
        deadline = time.monotonic() + self.timeout_ms / 1000
        c.require(type(repo.root) is type(Path()) and repo.root.is_absolute()
                  and repo.root == repo.root.resolve(strict=True), 'source-identity-mismatch')
        with ExitStack() as stack:
            root = self._directory(stack, repo.root, repo.directory_identity)
            git = self._directory(stack, '.git', repo.git_identity, parent=root)
            objects = self._directory(stack, 'objects', repo.objects_identity, parent=git)
            content = self._blob(objects, permit, deadline)
            # 名稱與開啟的 descriptor 均須仍指向 host 固定物件。
            c.require(db.identity(repo.root.lstat()) == repo.directory_identity
                      and db.identity(os.stat('.git', dir_fd=root, follow_symlinks=False)) == repo.git_identity
                      and db.identity(os.stat('objects', dir_fd=git, follow_symlinks=False)) == repo.objects_identity,
                      'source-identity-mismatch')
            self._check(deadline)
        return RepositoryArtifact(permit.source_id, repo.repository_id, permit.revision,
                                  permit.path, content, 'current')
