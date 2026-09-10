"""Local-port process-loss fixture; only a fresh empty test root is accepted."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(Path(__file__).parent)]
import memory_governance_contract as c
import memory_governance_core as module
from local_ports import SyntheticLocalPorts

root, stage = Path(sys.argv[1]), sys.argv[2]
if root.is_symlink() or not root.is_dir() or list(root.iterdir()):
    raise SystemExit('fresh empty synthetic root required')
if stage not in {'before-transaction', 'after-item-write', 'before-commit', 'after-commit'}:
    raise SystemExit('unknown checkpoint')
ports = SyntheticLocalPorts(root)
core = module.GovernanceCore(ports.host, enabled=True)
core.initialize()
preview = core.preview('add', '00000000-0000-4000-8000-000000000003', ports.candidate())
handle = core.authorize(preview)
binding = ports.registry.binding()
# Only request identity and host root identities reach the test parent. The full
# preview, confirmation and executable handle are deliberately lost with this process.
print(c.canonical({'operation_id': preview['operation_id'], 'preview_digest': c.digest(preview),
                   'directory_identity': list(binding.directory_identity), 'main_identity': list(binding.main_identity),
                   'lock_identity': list(binding.lock_identity)}).decode(), flush=True)

def checkpoint(name):
    if name == stage:
        os._exit(73)

module._checkpoint = checkpoint
core.execute(handle)
raise SystemExit('fault point was not reached')
