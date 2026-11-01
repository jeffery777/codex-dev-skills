#!/usr/bin/env python3
"""Read-only developer preparation; never select a formal Core or publish it."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA256 = "ea3f0bc43d3b93a0d07bc67551de0662a6cf684187038ec21f0569f9e4a35505"
PREPARATION_SHA256 = "5a4f1f25e80b3f036da6b8cab975a60d8ef901f9788766df60dd60a09074a93c"
BASELINE_REVISION = "7b66978a76597d09be1b55ad199a969b4ee59c0f"
REVIEWED_HEAD = "cbe3efa1ecc1d2ec04d2edc7078eb22c9dbec038"
MAX_FILE_BYTES = 131072


class PreparationError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreparationError("duplicate field")
        result[key] = value
    return result


def parse(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(PreparationError("nonfinite JSON")))


@contextmanager
def directory(path):
    path = Path(path).absolute()
    if ".." in path.parts:
        raise PreparationError("traversal")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def read(parent, name, *, source=False):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        mode = stat.S_IMODE(info.st_mode)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or mode & 0o133
                or not 0 < info.st_size <= MAX_FILE_BYTES or (source and mode != 0o644)):
            raise PreparationError("unsafe input")
        raw = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
        signature = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_ctime_ns)
        if len(raw) != info.st_size or signature(info) != signature(after):
            raise PreparationError("input changed")
        return raw


def fixed_snapshot(root, name, expected_digest):
    with directory(root / "tests/fixtures") as parent:
        raw = read(parent, name + ".lock.json")
    if digest(raw) != expected_digest:
        raise PreparationError("unreviewed preparation data")
    pin = parse(raw)
    rows = pin["files"]
    names = [row["path"] for row in rows]
    if names != sorted(set(names)) or any(
            not isinstance(p, str) or p.startswith("/") or "\\" in p
            or any(part in {"", ".", ".."} for part in p.split("/")) for p in names):
        raise PreparationError("invalid fixed paths")
    dirs = {str(p) for name in names for p in PurePosixPath(name).parents if str(p) != "."}
    captured = {}

    def walk(fd, prefix=""):
        entries = os.listdir(fd)
        if len(entries) > len(names) + len(dirs):
            raise PreparationError("excessive inventory")
        for leaf in entries:
            path = prefix + leaf
            info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
            if path in dirs and stat.S_ISDIR(info.st_mode):
                child = os.open(leaf, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    walk(child, path + "/")
                finally:
                    os.close(child)
            elif path in names and stat.S_ISREG(info.st_mode):
                captured[path] = read(fd, leaf, source=True)
            else:
                raise PreparationError("unexpected entry")

    with directory(root / "tests/fixtures" / name) as fd:
        walk(fd)
    if set(captured) != set(names):
        raise PreparationError("missing file")
    for row in rows:
        value = captured[row["path"]]
        if row["mode"] != "100644" or len(value) != row["size_bytes"] or digest(value) != row["sha256"]:
            raise PreparationError("fixed bytes or mode mismatch")
    collection = digest(b"".join(p.encode() + b"\t" + digest(v).encode() + b"\n"
                                  for p, v in sorted(captured.items())))
    if collection != pin["collection_sha256"]:
        raise PreparationError("collection mismatch")
    return pin, captured


def baseline(root=None):
    root = ROOT if root is None else Path(root)
    pin, files = fixed_snapshot(root, "core-feedback-baseline", BASELINE_SHA256)
    if pin["revision"] != BASELINE_REVISION or len(files) != 14:
        raise PreparationError("historical baseline identity")
    return files


def load_script(root, filename):
    spec = importlib.util.spec_from_file_location("fixed_core_development_" + filename, root / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inspect(root=None):
    root = ROOT if root is None else Path(root)
    pin, files = fixed_snapshot(root, "core-release-preparation", PREPARATION_SHA256)
    if (pin["reviewed_head"] != REVIEWED_HEAD or len(files) != 20
            or any(pin[k] is not None for k in ("publication_revision", "tag_object", "release_id"))
            or any(pin[k] is not False for k in ("formal_core_adopted", "runtime_qualified", "merge_authorized"))):
        raise PreparationError("preparation is not publication")
    old = baseline(root)
    candidate = load_script(root, "eval-core-feedback-candidate.py")
    candidate.ROOT = root
    _, criteria, _ = candidate.inspect(root / "tests/fixtures/core-feedback-candidate")
    for name, before in old.items():
        if not candidate.inserted_only(before, files[name]):
            raise PreparationError("baseline text removed")
    for name in (p for p in files if p.startswith("contracts/")):
        if files[name] != criteria[name].encode("utf-8"):
            raise PreparationError("evaluated contract changed")
    if files["LICENSE"] != old["LICENSE"]:
        raise PreparationError("license changed")
    markdown = b"".join(p.encode() + b"\t" + digest(v).encode() + b"\n"
                        for p, v in sorted(files.items()) if p.endswith(".md"))
    records = json.dumps(pin["files"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if (digest(markdown) != pin["markdown_collection_sha256"]
            or digest(b"codex-core-document-set/v1\0" + records) != pin["codex_document_set_sha256"]
            or sum(map(len, files.values())) != pin["total_bytes"]):
        raise PreparationError("migration values differ from fixed bytes")
    formal = load_script(root, "validate-core-contract-snapshot.py")
    formal.validate(root)
    formal.check_links({p: value.decode("utf-8") for p, value in files.items()})
    return {"status": "prepared-publication-pending", "reviewed_head": REVIEWED_HEAD,
            "files": len(files), "total_bytes": sum(map(len, files.values())),
            "publication_revision": None, "tag_object": None,
            "formal_core_adopted": False, "runtime_qualified": False, "merge_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-publication", action="store_true")
    args = parser.parse_args()
    try:
        result = inspect()
        print(json.dumps(result, sort_keys=True))
        return 1 if args.require_publication else 0
    except (PreparationError, OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print("Core preparation rejected: " + type(error).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
