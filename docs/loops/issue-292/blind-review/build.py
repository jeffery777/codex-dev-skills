#!/usr/bin/env python3
"""Build fully synthetic, deterministic blind-review fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__import__('os').environ['CODEX_REVIEW_PILOT_ROOT']).resolve()

FIXTURE_README = '''# Synthetic review workspace

Review the proposed review_target.py, retention.py and maintenance.py changes.
The config <yaml-path> CLI operation accepts YAML; invalid YAML must return exit
2 with a controlled error: summary and no traceback. Valid YAML prints ok: and
returns zero. {lock_contract}

This exercise is single-runner and uses regular fixture-owned files, positive
PIDs of live processes owned by the current user, and numeric PID lock contents
with optional trailing newline. Concurrent races, malformed PID data, denied
permissions and unknown CLI commands are outside this bounded contract.

retention.py receives unique-ID records in active/completed states, finite
nonnegative timestamps, nonnegative TTL and integer latest_n >= 0. It keeps all
active records and completed records within TTL OR among latest_n newest
completed records. It returns the retained records; applying deletion is owned
by the caller, outside this fixture. No scheduler/deployed cleanup is claimed.
maintenance.py produces presentation labels from supported diagnostic messages;
its output does not authorize execution or decide policy.

Use only this independent synthetic workspace as evidence; no external systems.
'''

FIXTURE_AGENTS = '''# Synthetic fixture instructions

This fixture is synthetic. Do not modify workspace source/spec/guidance. You may
create controlled temporary reproduction data and your own child processes;
clean up only those outputs/processes. No network, installs, delegation, external
state, account/company data, or reading sibling runs/oracles. Use the supplied
./scripts/project-python -B and report only observed commands/results. Read
REVIEW.md for the supplied review rules; references not included in this
workspace are not required. Do not load outside repository data or skills.
'''

RETENTION = '''from __future__ import annotations

def retained(records, *, now, ttl_seconds, latest_n):
    completed = sorted((r for r in records if r["state"] == "completed"), key=lambda r: r["completed_at"], reverse=True)
    latest_ids = {r["id"] for r in completed[:latest_n]}
    return [r for r in records if r["state"] != "completed" or r["id"] in latest_ids or now - r["completed_at"] <= ttl_seconds]
'''

MAINTENANCE = '''from __future__ import annotations

def maintenance_label(message: str) -> str:
    text = message.lower()
    if "timeout" in text:
        return "timeout-message"
    if "converted twice" in text:
        return "duplicate-conversion-message"
    return "other-message"
'''

V1 = '''from __future__ import annotations
import os
import sys
import yaml

def load_config(path):
    try:
        return yaml.safe_load(open(path, encoding="utf-8"))
    except ValueError:
        raise ValueError("invalid configuration")

def owner_is_active(owner: int):
    try:
        os.kill(owner, 0)
    except (OSError, TypeError):
        return False
    return True

def acquire(lock, owner):
    if os.path.exists(lock):
        existing = open(lock, encoding="utf-8").read().strip()
        if owner_is_active(existing):
            print("error: active owner")
            return 3
    open(lock, "w", encoding="utf-8").write(str(owner))
    print("ok: acquired")
    return 0

def main(argv):
    if argv[1] == "config":
        try:
            load_config(argv[2])
        except ValueError:
            print("error: invalid configuration")
            return 2
        print("ok: configuration")
        return 0
    if argv[1] == "acquire":
        return acquire(argv[2], int(argv[3]))
    raise ValueError("unknown command")

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

V2 = '''from __future__ import annotations
import os
import sys
import yaml

def load_config(path):
    try:
        return yaml.safe_load(open(path, encoding="utf-8"))
    except yaml.scanner.ScannerError:
        raise ValueError("invalid configuration")

def owner_is_active(owner):
    try:
        os.kill(int(owner.strip()), 0)
    except OSError:
        return False
    return True

def run(lock, owner):
    if os.path.exists(lock) and owner_is_active(open(lock, encoding="utf-8").read()):
        print("error: active owner")
        return 3
    open(lock, "w", encoding="utf-8").write(str(owner) + "\\n")
    if open(lock, encoding="utf-8").read() != str(owner):
        print("error: lock ownership changed")
        return 4
    os.unlink(lock)
    print("ok: run")
    return 0

def main(argv):
    if argv[1] == "config":
        try:
            load_config(argv[2])
        except ValueError:
            print("error: invalid configuration")
            return 2
        print("ok: configuration")
        return 0
    if argv[1] == "run":
        return run(argv[2], int(argv[3]))
    raise ValueError("unknown command")

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

VARIANTS = {"v1": V1, "v2": V2}

def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(repo: Path) -> None:
    assert repo not in ROOT.parents and ROOT != repo, "fixture directory must be outside repository"
    target_root = ROOT / "fixtures"
    if target_root.exists():
        raise SystemExit("fixtures already exist; choose a new benchmark directory rather than overwriting them")
    manifest: dict[str, object] = {"schema": 1, "variants": {}}
    for name, source in VARIANTS.items():
        fixture = target_root / name
        write(fixture / "review_target.py", source)
        write(fixture / "retention.py", RETENTION)
        write(fixture / "maintenance.py", MAINTENANCE)
        lock_contract = ("The acquire <lock-path> <owner-pid> operation must refuse an existing live owner with exit 3 and preserve its lock; otherwise it writes the supplied owner and exits 0." if name == "v1" else "The run <lock-path> <owner-pid> operation must refuse an existing live owner with exit 3. With no lock, it must complete with exit 0 and release its own lock so the next run is possible.")
        write(fixture / "README.md", FIXTURE_README.format(lock_contract=lock_contract))
        write(fixture / "AGENTS.md", FIXTURE_AGENTS)
        review_sources = [
            ("skills/code-review/SKILL.md", repo / "skills" / "code-review" / "SKILL.md"),
            ("skills/code-review-deep/SKILL.md", repo / "skills" / "code-review-deep" / "SKILL.md"),
            ("skills/code-review/references/integration-boundaries.md", repo / "skills" / "code-review" / "references" / "integration-boundaries.md"),
        ]
        write(fixture / "REVIEW.md", "\n\n".join(f"# Source: {label}\n\n{path.read_text(encoding='utf-8').rstrip()}" for label, path in review_sources) + "\n")
        write(fixture / "data" / "normal.yaml", "name: normal\ncount: 2\n")
        write(fixture / "data" / "review-sentinel-malformed.yaml", "review-sentinel: [unterminated\n")
        shutil.copy2(repo / ".python-version", fixture / ".python-version")
        (fixture / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo / "scripts" / "project-python", fixture / "scripts" / "project-python")
        files = sorted(path for path in fixture.rglob("*") if path.is_file())
        manifest["variants"][name] = {"files": {str(path.relative_to(fixture)): digest(path) for path in files}}
    write(ROOT / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    if not (args.repo / ".python-version").is_file() or not (args.repo / "scripts" / "project-python").is_file():
        raise SystemExit("repo must contain .python-version and scripts/project-python")
    build(args.repo.resolve())

if __name__ == "__main__":
    main()
