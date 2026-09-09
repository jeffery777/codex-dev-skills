"""Abrupt subprocess termination on synthetic roots; never installed."""
import os
from pathlib import Path
import sys
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
sys.path.insert(0, str(Path(__file__).parent))
import memory_governance_contract as c
import memory_governance_core as core_module
import memory_governance_storage as db
from synthetic_host import SyntheticHost, version

root, output, stage = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
host = SyntheticHost(root)
host._binding = replace(host._binding, main_identity=db.identity((root/db.MAIN).stat()),
                        lock_identity=db.identity((root/db.LOCK).stat()))
core = core_module.GovernanceCore(host, enabled=True)
value = version()
host.approve_source(value)
preview = core.preview('add', '00000000-0000-4000-8000-000000000003', value)
handle = core.authorize(preview)
# Test parent request reference outside managed root; no production preview cache.
output.write_bytes(c.canonical(preview))
writer = None
original_connect = db.connect

def connect(*args, **kwargs):
    global writer
    connection = original_connect(*args, **kwargs)
    if kwargs.get('writer'):
        writer = connection
    return connection

def checkpoint(name):
    if name == stage:
        os._exit(73)
    if name == 'before-commit' and stage == 'commit-vm':
        def interrupt():
            os._exit(73)
        writer.set_progress_handler(interrupt, 1)

db.connect = connect
core_module._checkpoint = checkpoint
core.execute(handle)
raise SystemExit('fault point was not reached')
