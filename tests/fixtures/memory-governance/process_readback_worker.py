"""獨立 writer/reader 程序；只由新建 fixture 的明確合成 TCB descriptors 組成。

此 fixture 不安裝、不供 CLI discovery，不認證任意 caller JSON 為 production 權限。
Reader 不接收 preview、candidate 或 confirmation，亦不從 DB 重建 source approval。
"""
from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sys
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(Path(__file__).parent)]
import memory_governance_contract as c
import memory_governance_core as module
import memory_governance_storage as db
from memory_governance_host import RootBinding
from memory_governance_local import LocalClock, SingleRootRegistry
from local_ports import SyntheticLocalPorts


def compose(data):
    """Parent 已獨立建立／核對 fixture；本程序不採納檔案現在的 identity。"""
    c.fields(data, {'root', 'scope', 'profile', 'directory_identity', 'main_identity', 'lock_identity',
                    'filesystem_id', 'adapter_fingerprint', 'git_root', 'git_identity', 'gitdir_identity',
                    'git_config_digest', 'source_revision', 'approved', 'readback_ids', 'source_current',
                    'readable', 'copies', 'clock_offset', 'capacity_unavailable'})
    ports = SyntheticLocalPorts.__new__(SyntheticLocalPorts)
    binding = RootBinding(Path(data['root']), *(tuple(data[k]) for k in
                          ('directory_identity', 'main_identity', 'lock_identity')),
                          c.canonical(data['scope']), c.canonical(data['profile']), data['filesystem_id'],
                          data['adapter_fingerprint'], frozenset({'audit', 'recall', 'readback', 'content-write'}))
    ports.registry = SingleRootRegistry(binding)
    clock = LocalClock()
    class TestClock:
        def clock(self):
            sample = clock.clock()
            return replace(sample, utc_seconds=sample.utc_seconds + data['clock_offset'])
    ports.clock_port = TestClock()
    ports.accepted = ports.qualified = True
    ports.readable, ports.source_current = data['readable'], data['source_current']
    ports.safety = 'safe'
    ports.readback_ids, ports.approved = set(data['readback_ids']), data['approved']
    ports.calls, ports.runtime = [], db.runtime_facts()
    ports.git_root = Path(data['git_root'])
    ports.git_identity, ports.gitdir_identity = tuple(data['git_identity']), tuple(data['gitdir_identity'])
    ports.source_revision = data['source_revision']
    assert db.identity(ports.git_root.stat()) == ports.git_identity
    assert db.identity((ports.git_root / '.git').stat()) == ports.gitdir_identity
    ports.git_config = (ports.git_root / '.git/config').read_bytes()
    assert hashlib.sha256(ports.git_config).hexdigest() == data['git_config_digest']
    def copies(_binding):
        if data['copies'] is None:
            raise c.ContractError('synthetic-copies-unavailable')
        return {**data['copies'], 'observed_at': ports.clock_port.clock().utc_seconds}
    ports.external_copies = copies
    ports.host = ports.compose()
    return ports


def main():
    request = c.decode(sys.stdin.buffer.read(c.MAX_ENVELOPE + 1))
    mode = request['mode']
    if mode == 'read':
        c.fields(request, {'mode', 'host', 'operation_id', 'preview_digest'})
    else:
        c.fields(request, {'mode', 'host', 'operation', 'candidate', 'restore_revision', 'checkpoint'})
    ports = compose(request['host'])
    core = module.GovernanceCore(ports.host, enabled=True)
    if mode == 'read':
        original = db.connect
        def readonly(*args, **kwargs):
            assert not kwargs.get('writer'), 'reader opened writer'
            return original(*args, **kwargs)
        def measure(*args, **kwargs):
            raise OSError('synthetic postflight capacity unavailable')
        def replay_rejected():
            try:
                core.execute(module.ExecutionHandle(request['operation_id']))
            except c.ContractError as error:
                return str(error) == 'handle-unrecognized-or-consumed'
            return False
        with mock.patch.object(db, 'connect', side_effect=readonly):
            assert replay_rejected()
            context = mock.patch.object(db, 'measure', side_effect=measure) if request['host']['capacity_unavailable'] else None
            if context is not None:
                context.start()
            try:
                result = core.readback(request['operation_id'], request['preview_digest'])
            finally:
                if context is not None:
                    context.stop()
        print(c.canonical({'result': result, 'calls': ports.calls, 'pid': os.getpid(), 'replay_rejected': True}).decode())
        return
    assert mode == 'write'
    preview = core.preview(request['operation'], '00000000-0000-4000-8000-000000000003', request['candidate'],
                           restore_revision=request['restore_revision'])
    handle = core.authorize(preview)
    print(c.canonical({'operation_id': preview['operation_id'], 'preview_digest': c.digest(preview),
                       'pid': os.getpid()}).decode(), flush=True)
    stage = request['checkpoint']
    assert stage in {'before-transaction', 'after-item-write', 'before-commit', 'after-commit', 'reply-loss'}
    def checkpoint(name):
        if name == stage:
            os._exit(73)
    with mock.patch.object(module, '_checkpoint', side_effect=checkpoint):
        core.execute(handle)
    # The operation reply is deliberately never emitted, even after readback succeeded.
    os._exit(74)


if __name__ == '__main__':
    try:
        main()
    except c.ContractError as error:
        print(c.canonical({'error': str(error), 'pid': os.getpid()}).decode())
        raise SystemExit(2)
