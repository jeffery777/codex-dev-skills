"""Read-only operator input constraints, never authority or qualification.

The trusted local host supplies protected originals outside the repository.
Same-UID host code remains in the TCB. Hashes and file modes cannot establish
human authorization, secret-free content or OS isolation by themselves.
"""
from __future__ import annotations

import json
import hashlib
import os
import pathlib
import subprocess
import stat
import time
from dataclasses import dataclass

import agent_qualification as trust
import git_source
import model_packet_store as packets

MAX_BYTES = 131072
MAX_FILES = 16
MAX_SOURCE_BYTES = 524288
MAX_GRANT_LIFETIME = 86400


class InputError(ValueError):
    pass


def _shape(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise InputError('task-input-schema-rejected')
    return value


def _path(value):
    if type(value) is not str or not value or '\\' in value or any(ord(c) < 32 for c in value):
        raise InputError('task-input-path-rejected')
    parts = value.split('/')
    if any(p in {'', '.', '..'} or p.startswith('.') or p.lower() in
           {'auth.json', 'credentials', 'credentials.json', 'secrets.yaml', 'config.toml', 'id_rsa', 'id_ed25519'}
           or p.lower().endswith(('.pem', '.key', '.env')) for p in parts):
        raise InputError('task-input-path-rejected')
    return parts


def _read(directory, relative, limit, *, private=False):
    parts = _path(relative)
    fd = os.dup(directory)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
            trust._check(os.fstat(fd), directory=True)
            if private and os.fstat(fd).st_mode & 0o077:
                raise InputError('task-input-not-private')
            if private:
                try:
                    os.stat('.git', dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise InputError('task-input-repository-controlled')
        opened = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(opened); trust._check(before)
            if before.st_nlink != 1 or before.st_size > limit or (private and before.st_mode & 0o077):
                raise InputError('task-input-file-rejected')
            raw = os.read(opened, limit + 1)
            after = os.fstat(opened)
            linked = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_mode, s.st_nlink)
            if len(raw) != before.st_size or identity(before) != identity(after) or identity(after) != identity(linked):
                raise InputError('task-input-changed-during-read')
            return raw
        finally:
            os.close(opened)
    finally:
        os.close(fd)


def _artifact(home, ref):
    _shape(ref, {'path', 'sha256'})
    if type(ref['path']) is not str or not ref['path'].startswith('model-task-inputs/'):
        raise InputError('task-input-reference-rejected')
    packets._sha(ref['sha256'])
    fd = trust._directory(home)
    try:
        raw = _read(fd, ref['path'], MAX_BYTES, private=True)
    finally:
        os.close(fd)
    if packets.digest(raw) != ref['sha256']:
        raise InputError('task-input-digest-mismatch')
    return raw


def _task_key(record):
    return packets.digest(packets.canonical({'task_id': record['task_id'],
        'workspace': record['source']['workspace']}))


def _revocation_directory(home):
    fd = trust._directory(pathlib.Path(home))
    try:
        for part in ('model-task-inputs', 'revocations'):
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
            info = os.fstat(fd); trust._check(info, directory=True)
            if info.st_mode & 0o077:
                raise InputError('task-revocation-store-not-private')
            try:
                os.stat('.git', dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise InputError('task-revocation-store-repository-controlled')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _not_revoked(home, record):
    fd = _revocation_directory(home)
    try:
        try:
            os.stat(_task_key(record) + '.json', dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise InputError('task-grant-revoked')
    finally:
        os.close(fd)


def revoke_task(home, reference):
    """Revoke the task named by a protected record, even after source expiry."""
    try:
        record = _shape(json.loads(_artifact(home, reference), object_pairs_hook=trust._pairs),
            {'schema_version', 'enabled', 'observed_at', 'expires_at', 'task_id', 'scope',
             'request', 'acceptance', 'source', 'destinations', 'grant'})
        workspace = record['source']['workspace']
        if (record['schema_version'] != 2 or type(record['task_id']) is not str or not record['task_id']
                or type(workspace) is not str or not pathlib.PurePath(workspace).is_absolute()
                or str(pathlib.PurePath(workspace)) != workspace):
            raise InputError('task-revoke-identity-rejected')
        key = _task_key(record)
        if record['grant']['path'] != 'model-task-inputs/grants/' + key + '.json':
            raise InputError('task-revoke-grant-mismatch')
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise InputError('task-revoke-record-rejected') from None
    fd = _revocation_directory(home)
    try:
        name = key + '.json'
        try:
            marker = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=fd)
            created = True
        except FileExistsError:
            marker = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            created = False
        try:
            info = os.fstat(marker); trust._check(info)
            if info.st_nlink != 1 or info.st_mode & 0o077:
                raise InputError('task-revocation-marker-rejected')
            if created:
                raw = packets.canonical({'schema_version': 1, 'task_key': key, 'revoked_at': int(time.time())})
                while raw:
                    count = os.write(marker, raw)
                    if count <= 0:
                        raise InputError('task-revocation-write-failed')
                    raw = raw[count:]
            os.fsync(marker)
        finally:
            os.close(marker)
        os.fsync(fd)
        return key
    finally:
        os.close(fd)


def _grant(home, record, original, source_identity, now):
    task_key = _task_key(record)
    ref = record['grant']
    if (type(ref) is not dict or ref.get('path') != 'model-task-inputs/grants/' + task_key + '.json'):
        raise InputError('task-grant-reference-rejected')
    grant = _shape(json.loads(_artifact(home, ref), object_pairs_hook=trust._pairs),
        {'schema_version', 'task_key', 'task_id', 'scope', 'request_sha256',
         'acceptance_sha256', 'source_sha256', 'destinations', 'actions',
         'sandbox_ceiling', 'issued_at', 'expires_at'})
    if (type(grant['schema_version']) is not int or grant['schema_version'] != 1
            or grant['task_key'] != task_key or grant['task_id'] != record['task_id']
            or grant['scope'] != record['scope']
            or grant['request_sha256'] != record['request']['sha256']
            or grant['acceptance_sha256'] != record['acceptance']['sha256']
            or grant['source_sha256'] != source_identity[2]
            or grant['destinations'] != record['destinations']
            or grant['actions'] != ['start'] or original.get('operation') != 'start'
            or type(original.get('authorization')) is not dict
            or grant['sandbox_ceiling'] != original['authorization'].get('sandbox_ceiling')
            or grant['sandbox_ceiling'] not in {'read-only', 'workspace-write'}
            or type(grant['issued_at']) is not int or type(grant['expires_at']) is not int
            or not grant['issued_at'] <= now < grant['expires_at']
            or grant['expires_at'] > grant['issued_at'] + MAX_GRANT_LIFETIME
            or record['expires_at'] > grant['expires_at']):
        raise InputError('task-grant-scope-or-time-rejected')
    _not_revoked(home, record)
    return grant


def _source(record):
    source = _shape(record, {'workspace', 'head', 'index_sha256', 'origin_sha256', 'files'})
    root = pathlib.Path(source['workspace'])
    if not root.is_absolute() or str(root.resolve(strict=True)) != str(root):
        raise InputError('task-source-root-rejected')
    git_source.verified_git_root(root)
    marker = git_source.validated_git_marker(root)
    if git_source.verified_git_head(root) != source['head']:
        raise InputError('task-source-head-mismatch')
    environment = git_source.sanitized_git_environment()
    environment['GIT_WORK_TREE'] = str(root)
    files = source['files']
    if type(files) is not dict or not 1 <= len(files) <= MAX_FILES:
        raise InputError('task-source-scope-rejected')
    for name in files:
        _path(name)
    # Object/index metadata never refreshes working files or invokes clean/
    # process filters. Whole-checkout cleanliness remains the existing CLI gate
    # after qualified containment; this port checks only the designated scope.
    arguments = ['--literal-pathspecs', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false']
    tree_raw = git_source.run_git(root, arguments + ['ls-tree', '-z', 'HEAD', '--', *files], environment=environment).stdout
    index_raw = git_source.run_git(root, arguments + ['ls-files', '--stage', '-z', '--', *files], environment=environment).stdout
    def entries(raw, tree):
        result = {}
        for entry in raw.rstrip('\0').split('\0'):
            meta, name = entry.split('\t', 1)
            mode, middle, last = meta.split(' ')
            if name in result or mode not in {'100644', '100755'} or (middle != 'blob' if tree else last != '0'):
                raise InputError('task-source-index-or-tree-rejected')
            result[name] = (mode, last if tree else middle)
        return result
    tree = entries(tree_raw, True)
    if set(tree) != set(files) or entries(index_raw, False) != tree:
        raise InputError('task-source-index-or-tree-mismatch')
    origin = git_source.run_git(root, ['config', '--get', 'remote.origin.url'], environment=environment).stdout.strip()
    if packets.digest(origin.encode()) != source['origin_sha256']:
        raise InputError('task-source-origin-mismatch')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    total = 0
    try:
        for name, digest in files.items():
            packets._sha(digest)
            raw = _read(fd, name, MAX_BYTES)
            total += len(raw)
            if total > MAX_SOURCE_BYTES or packets.digest(raw) != digest:
                raise InputError('task-source-content-mismatch')
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != tree[name][1]:
                raise InputError('task-source-content-not-head')
            mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
            if bool(mode & stat.S_IXUSR) != (tree[name][0] == '100755'):
                raise InputError('task-source-mode-mismatch')
    finally:
        os.close(fd)
    git_fd = os.open(marker.git_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        index = packets.digest(_read(git_fd, 'index', 16 * 1024 * 1024))
    finally:
        os.close(git_fd)
    if index != source['index_sha256']:
        raise InputError('task-source-index-mismatch')
    if git_source.validated_git_marker(root) != marker or git_source.verified_git_head(root) != source['head']:
        raise InputError('task-source-changed-during-read')
    return (marker.binding_sha256, index, packets.digest(packets.canonical(source)))


@dataclass(frozen=True)
class TaskSourceInput:
    home: pathlib.Path
    reference: dict
    request: dict
    record: dict
    source_identity: tuple
    grant: dict

    @property
    def identity_sha256(self):
        # Renewal/reference aliases cannot change the objective or escape an
        # unknown attempt. Time is a live constraint, not the packet identity.
        stable = {k: v for k, v in self.record.items() if k not in
                  {'observed_at', 'expires_at', 'enabled', 'request', 'acceptance'}}
        stable.update(request_sha256=self.record['request']['sha256'],
                      acceptance_sha256=self.record['acceptance']['sha256'])
        return packets.digest(packets.canonical({'input': stable, 'source': self.source_identity}))

    def packet_identity(self, repository):
        stable = {'repository': repository, 'task_id': self.record['task_id'],
                  'scope': self.record['scope'], 'acceptance_sha256': self.record['acceptance']['sha256'],
                  'source_head': self.record['source']['head'], 'task_input_sha256': self.identity_sha256}
        return packets.digest(packets.canonical(stable))

    def verify(self, request, binding=None, validated=None):
        raw = _artifact(self.home, self.reference)
        record = json.loads(raw, object_pairs_hook=trust._pairs)
        if (json.loads(_artifact(self.home, record['request']), object_pairs_hook=trust._pairs) != self.request
                or not _artifact(self.home, record['acceptance'])):
            raise InputError('task-input-originals-changed')
        now = time.time()
        if (record != self.record or record['enabled'] is not True
                or type(record['observed_at']) is not int or type(record['expires_at']) is not int
                or not record['observed_at'] <= now < record['expires_at'] <= record['observed_at'] + 300):
            raise InputError('task-input-expired-disabled-or-changed')
        original = {k: v for k, v in request.items() if k != 'target_ref'}
        # A successor may reduce the existing sandbox ceiling. It cannot use
        # an input renewal to expand permissions or replace the original prompt.
        if (self.request.get('sandbox') == 'workspace-write' and original.get('sandbox') == 'read-only'
                and type(original.get('authorization')) is dict
                and original['authorization'].get('sandbox_ceiling') == 'read-only'):
            original = {**original, 'sandbox': 'workspace-write', 'authorization': {
                **original['authorization'], 'sandbox_ceiling': self.request['authorization']['sandbox_ceiling']}}
        if original != self.request or _source(record['source']) != self.source_identity:
            raise InputError('task-input-or-source-mismatch')
        if _grant(self.home, record, self.request, self.source_identity, now) != self.grant:
            raise InputError('task-grant-changed')
        if validated is not None and (str(validated.workspace), validated.expected_head) != (
                record['source']['workspace'], record['source']['head']):
            raise InputError('task-input-cli-source-mismatch')
        if binding is not None and (binding.task_id, binding.scope, binding.acceptance_sha256) != (
                record['task_id'], record['scope'], record['acceptance']['sha256']):
            raise InputError('task-input-target-contract-mismatch')
        # Use the existing stable typed execution identity. Planner identity
        # separately binds fresh context/qualification bytes in execute_next;
        # checkpoint renewal must not change the permitted provider/model.
        if binding is not None and binding.identity_sha256 not in record['destinations']:
            raise InputError('task-input-destination-mismatch')
        # Bounded source reads may consume the remaining lifetime. Read the
        # immutable originals again and sample the live clock at this boundary.
        _artifact(self.home, self.reference)
        _artifact(self.home, record['request'])
        _artifact(self.home, record['acceptance'])
        _grant(self.home, record, self.request, self.source_identity, time.time())
        final = time.time()
        if not (record['observed_at'] <= final < record['expires_at']
                and self.grant['issued_at'] <= final < self.grant['expires_at']):
            raise InputError('task-input-expired-during-readback')
        return self.identity_sha256

    def verify_launch_window(self, binding):
        """Sample one final clock after both protected stores have been read."""
        record = json.loads(_artifact(self.home, self.reference), object_pairs_hook=trust._pairs)
        if record != self.record or record['enabled'] is not True:
            raise InputError('task-input-expired-disabled-or-changed')
        _artifact(self.home, record['request'])
        _artifact(self.home, record['acceptance'])
        now = time.time()
        if _grant(self.home, record, self.request, self.source_identity, now) != self.grant:
            raise InputError('task-grant-changed')
        final = time.time()
        if not (record['observed_at'] <= final < record['expires_at']
                and self.grant['issued_at'] <= final < self.grant['expires_at']
                and binding.valid_from <= final < binding.valid_until):
            raise InputError('task-input-or-target-expired-during-readback')


def read_input(home, reference, task, failover_input, request):
    """Read originals and source; all existing authority/qualification gates remain."""
    try:
        raw = _artifact(home, reference)
        record = _shape(json.loads(raw, object_pairs_hook=trust._pairs), {'schema_version', 'enabled',
            'observed_at', 'expires_at', 'task_id', 'scope', 'request', 'acceptance', 'source', 'destinations', 'grant'})
        if (type(record['schema_version']) is not int or record['schema_version'] != 2
                or type(record['task_id']) is not str or not record['task_id']
                or type(record['scope']) is not str or not record['scope']):
            raise InputError('task-input-schema-rejected')
        original = json.loads(_artifact(home, record['request']), object_pairs_hook=trust._pairs)
        if type(original) is not dict or 'target_ref' in original:
            raise InputError('task-input-original-request-rejected')
        acceptance = _artifact(home, record['acceptance'])
        if not acceptance or (record['task_id'], record['scope'], record['acceptance']['sha256']) != (
                task['id'], task['qualification_scope'], failover_input['task']['acceptance_sha256']):
            raise InputError('task-input-objective-mismatch')
        destinations = record['destinations']
        if type(destinations) is not list or not 1 <= len(destinations) <= 16 or len(set(destinations)) != len(destinations):
            raise InputError('task-input-destinations-rejected')
        for destination in destinations:
            packets._sha(destination)
        source_identity = _source(record['source'])
        grant = _grant(home, record, original, source_identity, time.time())
        item = TaskSourceInput(home, dict(reference), original, record, source_identity, grant)
        item.verify(request)
        return item
    except (OSError, ValueError, TypeError, KeyError, RecursionError, subprocess.SubprocessError):
        raise InputError('task-input-or-source-rejected') from None
