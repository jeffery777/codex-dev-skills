#!/usr/bin/env python3
"""Verify one explicitly selected, fixed Core snapshot. No network or writes."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import posixpath
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REVISION = "3a3fd41e5fb994b4429a67d76d1b0655d972d150"
REVIEWED_HEAD = "139ef2ff29af70c7592910c2ec598a9943cc934f"
MARKDOWN_DIGEST = "cf5a027c818967a5c1bc46fabb36aba88b8264bde0c3ee81e2c4aff813d2a428"
LICENSE_DIGEST = "49d64e81e9fd3b12470c1da48367b120b28d404ca08edfdd950278e28e4da34f"
SET_DIGEST = "348a1307aad1887476f9a483231299931e38f61e7488048a0211f39a67f6504a"
DOMAIN = "codex-core-document-set/v1"
FILES = (
    "LICENSE", "README.md",
    "contracts/authorization-and-stops.md",
    "contracts/exact-head-and-evidence.md",
    "contracts/review-and-security.md", "contracts/workflow.md",
    "docs/architecture/dependency-inventory.md",
    "docs/architecture/migration-plan.md", "docs/architecture/project-split.md",
    "docs/provenance/source-map.md", "docs/provenance/upstream-notices.md",
)
MAX_FILE_BYTES = 128 * 1024
MAX_TOTAL_BYTES = 256 * 1024
MAX_LOCK_BYTES = 16 * 1024
DIRECTORIES = {str(p) for name in FILES for p in PurePosixPath(name).parents if str(p) != "."}
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+[^)]*)?\)")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class SnapshotError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise SnapshotError("duplicate JSON key")
        value[key] = item
    return value


def fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise SnapshotError(f"invalid {label} fields")
    return value


def canonical_set(records):
    ordered = sorted(records, key=lambda row: row["path"].encode("utf-8"))
    data = json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256(DOMAIN.encode("utf-8") + b"\0" + data)


@contextmanager
def directory(parent_fd, relative):
    """Walk only fixed components; never follow snapshot/lock ancestor symlinks."""
    fd = os.dup(parent_fd)
    try:
        for part in relative.split("/"):
            if part in {"", ".", ".."}:
                raise SnapshotError("unsafe directory path")
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def regular_bytes(parent_fd, name, limit, *, private=False, expected_size=None):
    # O_NONBLOCK prevents a raced FIFO from blocking before fstat rejects it.
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        mode = stat.S_IMODE(info.st_mode)
        if not stat.S_ISREG(info.st_mode) or mode & 0o133:
            raise SnapshotError("resource must be regular, non-executable and not group/world writable")
        if private and mode != 0o600:
            raise SnapshotError("filesystem resource mode must be 0600")
        if not mode & 0o400 or info.st_size > limit:
            raise SnapshotError("resource is unreadable or exceeds size limit")
        if expected_size is not None and info.st_size != expected_size:
            raise SnapshotError("file size does not match lock")
        data = stream.read(limit + 1)
        if len(data) > limit or len(data) != info.st_size:
            raise SnapshotError("resource size changed or exceeds limit")
        return data


def inventory(snapshot_fd, *, complete=True):
    found = set()

    def walk(fd, prefix=""):
        # Directory names/count/depth are bounded by the fixed reviewed allowlist.
        names = os.listdir(fd)
        if len(names) > len(FILES) + len(DIRECTORIES):
            raise SnapshotError("unexpected snapshot inventory")
        for name in names:
            relative = prefix + name
            if relative not in FILES and relative not in DIRECTORIES:
                raise SnapshotError(f"unexpected snapshot entry: {relative}")
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if relative in DIRECTORIES:
                if not stat.S_ISDIR(info.st_mode):
                    raise SnapshotError("snapshot directory must not be a symlink/special entry")
                with directory(fd, name) as child:
                    walk(child, relative + "/")
            else:
                if not stat.S_ISREG(info.st_mode):
                    raise SnapshotError("snapshot file must be regular and non-symlink")
                found.add(relative)
    walk(snapshot_fd)
    if complete and found != set(FILES):
        raise SnapshotError("missing required snapshot files")
    return found


@contextmanager
def optional_directory(parent_fd, name):
    # Only a missing fixed directory is optional, not missing entries during a
    # later inventory/read. All callers pass one fixed allowlisted component.
    try:
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
    except FileNotFoundError:
        yield None
        return
    try:
        yield fd
    finally:
        os.close(fd)


def preflight_destination(root: Path):
    """Inspect an optional partial destination; never repair or delete its data.

    Existing listed bytes may differ for the installer's reviewed force-update
    path. Existing entries must still satisfy inventory/type/mode/size controls.
    Full pinned-byte validation is a separate mandatory postcondition.
    """
    if root.is_symlink() or ".." in root.parts:
        raise SnapshotError("explicit root must not be a symlink or contain traversal")
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return
    try:
        with optional_directory(root_fd, "orchestration") as parent:
            if parent is None:
                return
            with optional_directory(parent, "core") as snapshot:
                if snapshot is not None:
                    found = inventory(snapshot, complete=False)
                    total = 0
                    for name in sorted(found):
                        path = PurePosixPath(name)
                        if len(path.parts) == 1:
                            data = regular_bytes(snapshot, path.name, MAX_FILE_BYTES, private=True)
                        else:
                            with directory(snapshot, path.parent.as_posix()) as folder:
                                data = regular_bytes(folder, path.name, MAX_FILE_BYTES, private=True)
                        total += len(data)
                        if total > MAX_TOTAL_BYTES:
                            raise SnapshotError("destination exceeds total size limit")
            try:
                os.stat("core.lock.json", dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                regular_bytes(parent, "core.lock.json", MAX_LOCK_BYTES, private=True)
    finally:
        os.close(root_fd)


def parse_lock(data):
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(SnapshotError("invalid JSON constant")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError("lock must be strict UTF-8 JSON") from exc
    fields(value, ("contract", "source", "consumer", "upstream_markdown_set", "document_set"), "lock")
    if value["contract"] != "codex-core-document-lock/v1":
        raise SnapshotError("unsupported lock contract")
    expected_source = {
        "repository": "jeffery777/engineering-workflow-core", "revision": REVISION,
        "reviewed_head": REVIEWED_HEAD, "pull_request": 14, "version": None,
    }
    if value["source"] != expected_source or type(value["source"].get("pull_request")) is not int:
        raise SnapshotError("unreviewed source repository/revision/PR/version")
    if value["consumer"] != {
        "repository": "jeffery777/codex-dev-skills",
        "import_baseline_revision": "eb53e1683d6227d36205baefd55b4f20aafbadab",
        "assembler_contract": "core-snapshot/v1",
    }:
        raise SnapshotError("consumer/import baseline identity mismatch")
    if value["upstream_markdown_set"] != {
        "algorithm": "utf8-path-tab-sha256-lf/v1", "sha256": MARKDOWN_DIGEST,
    }:
        raise SnapshotError("upstream Markdown set identity mismatch")
    document_set = fields(value["document_set"], ("algorithm", "sha256", "files"), "document set")
    if document_set["algorithm"] != DOMAIN or document_set["sha256"] != SET_DIGEST:
        raise SnapshotError("document set identity mismatch")
    rows = document_set["files"]
    if not isinstance(rows, list) or len(rows) != len(FILES):
        raise SnapshotError("lock inventory must contain exactly 11 files")
    total = 0
    for row in rows:
        fields(row, ("path", "sha256", "size_bytes", "mode"), "file record")
        if row["path"] not in FILES or row["mode"] != "100644":
            raise SnapshotError("unsafe/unlisted path or Git mode")
        if not isinstance(row["sha256"], str) or not DIGEST.fullmatch(row["sha256"]):
            raise SnapshotError("invalid file digest")
        size = row["size_bytes"]
        if type(size) is not int or not 0 < size <= MAX_FILE_BYTES:
            raise SnapshotError("invalid file byte size")
        total += size
    if [row["path"] for row in rows] != list(FILES) or total > MAX_TOTAL_BYTES:
        raise SnapshotError("duplicate, unsorted or excessive lock inventory")
    if canonical_set(rows) != SET_DIGEST:
        raise SnapshotError("canonical document set digest mismatch")
    return value


def check_links(contents):
    anchors = {}
    for path, text in contents.items():
        explicit = set(re.findall(r'<a id="([^"]+)"', text))
        headings = re.findall(r"^#{1,6}\s+(.+)$", text, re.MULTILINE)
        anchors[path] = explicit | {re.sub(r"[^\w\s-]", "", h).strip().lower().replace(" ", "-") for h in headings}
    for path, text in contents.items():
        for raw in LINK.findall(text):
            url = urlsplit(raw)
            if url.scheme or url.netloc:
                continue  # Provenance links are never fetched or executed.
            relative = unquote(url.path)
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), relative)) if relative else path
            if relative.startswith("/") or target not in contents:
                raise SnapshotError(f"broken/escaping local link in {path}")
            if url.fragment and unquote(url.fragment) not in anchors[target]:
                raise SnapshotError(f"missing local anchor in {path}")


def validate(root: Path, layout="source"):
    if layout not in {"source", "filesystem"}:
        raise SnapshotError("unknown layout")
    if root.is_symlink() or ".." in root.parts:
        raise SnapshotError("explicit root must not be a symlink or contain traversal")
    private = layout == "filesystem"
    prefix, name = ("orchestration", "core") if private else ("vendor", "engineering-workflow-core")
    # The caller selects one root; no cwd, environment or alternative-root fallback.
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with directory(root_fd, prefix) as parent:
            with directory(parent, name) as snapshot:
                inventory(snapshot)  # Reject unknown entries before any document-byte read.
                lock_bytes = regular_bytes(parent, name + ".lock.json", MAX_LOCK_BYTES, private=private)
                lock = parse_lock(lock_bytes)
                contents, hashes = {}, {}
                for row in lock["document_set"]["files"]:
                    path = PurePosixPath(row["path"])
                    if len(path.parts) == 1:
                        data = regular_bytes(snapshot, path.name, MAX_FILE_BYTES, private=private,
                                             expected_size=row["size_bytes"])
                    else:
                        with directory(snapshot, path.parent.as_posix()) as folder:
                            data = regular_bytes(folder, path.name, MAX_FILE_BYTES, private=private,
                                                 expected_size=row["size_bytes"])
                    hashes[row["path"]] = sha256(data)
                    if hashes[row["path"]] != row["sha256"]:
                        raise SnapshotError(f"file digest mismatch: {row['path']}")
                    contents[row["path"]] = data.decode("utf-8")
                markdown = "".join(path + "\t" + hashes[path] + "\n" for path in FILES if path.endswith(".md"))
                if sha256(markdown.encode("utf-8")) != MARKDOWN_DIGEST or hashes["LICENSE"] != LICENSE_DIGEST:
                    raise SnapshotError("upstream Markdown/LICENSE digest mismatch")
                check_links(contents)
    finally:
        os.close(root_fd)
    return {
        "contract": "codex-core-snapshot-verification/v1", "status": "verified",
        "core_revision": REVISION, "document_set_sha256": SET_DIGEST,
        "upstream_markdown_set_sha256": MARKDOWN_DIGEST, "files": len(FILES),
        "layout": layout, "validator_contract": "core-snapshot/v1",
        "python": platform.python_version(),
        "runtime_qualified": False, "authorization_granted": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="one explicit package/templates root")
    parser.add_argument("--layout", choices=("source", "filesystem"), default="source")
    parser.add_argument("--preflight-destination", action="store_true",
                        help="read-only check of optional partial filesystem destination")
    args = parser.parse_args()
    try:
        if args.preflight_destination:
            if args.layout != "filesystem":
                raise SnapshotError("destination preflight requires filesystem layout")
            preflight_destination(args.root)
            result = {"status": "destination-preflight-passed", "complete_snapshot_verified": False,
                      "runtime_qualified": False, "authorization_granted": False}
        else:
            result = validate(args.root, args.layout)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (SnapshotError, OSError, UnicodeError, TypeError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
