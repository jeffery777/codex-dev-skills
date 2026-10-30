#!/usr/bin/env python3
"""Build the installer's reviewed data-only catalogs; repository Python needs YAML."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "installer/source-catalogs.json"
REVISIONS = (
    "6b5b0d0bf4e61119a5a87761fc4a6c4d35002e1c",
    "43c650e1196a3a702e2240bd79dd24539fa893a7",
    "f18b202595aea27c9d872c480d2e1b067340b163",
    "e23e18ed0512ece04ca6b6dceba3a6a1cf59b9fd",
    "6cd58e3a776ef705a9cee17ba7e24c6b21181395",
    "73cee30f5aee09c9218505624f1caa433ef72946",
)


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def target(source: str) -> str:
    if source == "vendor/engineering-workflow-core.lock.json":
        return "orchestration/core.lock.json"
    for prefix, replacement in (("vendor/engineering-workflow-core/", "orchestration/core/"),
                                ("policies/", "orchestration/policies/"), ("templates/", "")):
        if source.startswith(prefix):
            return replacement + source[len(prefix):]
    return source


def snapshot(revision: str) -> dict:
    raw = git("show", f"{revision}:catalog.yaml")
    catalog = yaml.safe_load(raw)
    tree = {}
    for row in git("ls-tree", "-rz", revision).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            tree[path.decode()] = (mode, kind, oid)
    groups = {}
    for name, group in catalog["groups"].items():
        artifacts = []
        for kind in ("skills", "templates", "agent_profiles"):
            for item in group.get(kind, []):
                source = item["source"]
                directory = kind == "skills"
                paths = sorted(p for p in tree if p.startswith(source + "/")) if directory else [source]
                files = {}
                for path in paths:
                    mode, blob_kind, oid = tree[path]
                    if mode not in ("100644", "100755") or blob_kind != "blob":
                        raise ValueError(f"unsafe source: {path}")
                    relative = path[len(source) + 1:] if directory else ""
                    files[relative] = {"sha256": hashlib.sha256(git("cat-file", "blob", oid)).hexdigest(),
                                       "executable": mode == "100755"}
                artifacts.append({"source": source, "kind": kind,
                                  "relative": pathlib.PurePosixPath(source).name if kind != "templates" else target(source),
                                  "type": "directory" if directory else "file", "files": files})
        groups[name] = {"depends_on": group.get("depends_on", []), "artifacts": artifacts}
    lock_path = "vendor/engineering-workflow-core.lock.json"
    core = json.loads(git("show", f"{revision}:{lock_path}"))["source"] if lock_path in tree else None
    return {"catalog_sha256": hashlib.sha256(raw).hexdigest(), "reviewed_revision": revision,
            "version": catalog["version"], "core": core, "groups": groups}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalogs = [snapshot(rev) for rev in REVISIONS]
    digests = [item["catalog_sha256"] for item in catalogs]
    if not catalogs or len(digests) != len(set(digests)):
        raise ValueError("ambiguous or empty reviewed source catalogs")
    content = json.dumps({"schema": 1, "repository": "jeffery777/codex-dev-skills",
                          "catalogs": catalogs}, indent=2) + "\n"
    if args.check:
        if OUTPUT.read_text() != content:
            raise SystemExit("installer catalog data differs from the reviewed Git snapshots")
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        OUTPUT.write_text(content)


if __name__ == "__main__":
    main()
