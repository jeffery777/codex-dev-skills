#!/usr/bin/env python3
"""Data-only ownership and payload checks for install.sh (stdlib only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

REGISTRY = Path(__file__).resolve().parents[1] / "installer/source-catalogs.json"


def fail(message: str) -> None:
    raise ValueError(message)


def relative(value: str, empty: bool = False) -> str:
    if (not value and not empty) or (value and (PurePosixPath(value).is_absolute()
            or any(p in (".", "..", "") for p in value.split("/")))) or any(c in value for c in "\t\r\n\0"):
        fail(f"unsafe inventory path: {value!r}")
    return value


def no_links(path: Path) -> None:
    for parent in (path, *path.parents):
        if parent.is_symlink():
            fail(f"symlink inventory path: {parent}")


def read_file(path: Path) -> bytes:
    no_links(path)
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        fail(f"unsafe or hardlinked inventory file: {path}")
    if metadata.st_size > 8 * 1024 * 1024:
        fail(f"inventory input exceeds 8 MiB limit: {path}")
    with path.open("rb") as stream:
        return stream.read(8 * 1024 * 1024 + 1)


def load_json(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                fail(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def manifest(path: Path, expected_type: str) -> dict:
    no_links(path)
    if expected_type == "file":
        paths = [("", path)]
    else:
        if not path.is_dir():
            fail(f"missing managed directory: {path}")
        paths = []
        actual_dirs = set()
        for base, dirs, files in os.walk(path, followlinks=False):
            for name in dirs:
                child = Path(base) / name
                if child.is_symlink():
                    fail(f"symlink in managed directory: {child}")
                actual_dirs.add(child.relative_to(path).as_posix())
            paths.extend(((Path(base) / name).relative_to(path).as_posix(), Path(base) / name) for name in files)
        required_dirs = {p.as_posix() for rel, _ in paths for p in PurePosixPath(rel).parents if str(p) != "."}
        if actual_dirs != required_dirs:
            fail(f"unknown empty directory in managed payload: {path}")
    for candidate in [path, *path.rglob("*")] if expected_type == "directory" else [path]:
        metadata = candidate.lstat()
        if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022:
            fail(f"untrusted owner or writable payload: {candidate}")
    return {rel: {"sha256": hashlib.sha256(read_file(file)).hexdigest(),
                  "executable": bool(file.lstat().st_mode & 0o111)} for rel, file in sorted(paths)}


def fingerprint(path: Path, expected_type: str) -> str:
    if not os.path.lexists(path):
        return "missing"
    digest = hashlib.sha256()
    entries = [(".", path)]
    if expected_type == "directory":
        for base, dirs, files in os.walk(path, followlinks=False):
            dirs.sort()
            files.sort()
            entries.extend((os.path.relpath(Path(base) / name, path), Path(base) / name)
                           for name in dirs + files)
    for rel, candidate in entries:
        metadata = candidate.lstat()
        digest.update(rel.encode("utf-8", "surrogateescape") + b"\0")
        digest.update(f"{metadata.st_dev}:{metadata.st_ino}:{metadata.st_mode}:{metadata.st_uid}:{metadata.st_size}:{metadata.st_mtime_ns}".encode() + b"\0")
        if stat.S_ISREG(metadata.st_mode):
            digest.update(read_file(candidate))
    return digest.hexdigest()


def git(source: Path, *args: str) -> bytes:
    # No hooks, shell evaluation, network access, filters, or old source execution.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_NO_LAZY_FETCH"] = "1"
    return subprocess.check_output(["git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=false",
                                    "-C", str(source), *args], stderr=subprocess.PIPE, env=env)


def load_source(source: Path, catalogs: list[dict]) -> tuple[dict, dict]:
    no_links(source)
    try:
        partial = git(source, "config", "--get-regexp", r"^(extensions\.partialclone|remote\..*\.promisor)$")
    except subprocess.CalledProcessError as exc:
        if exc.returncode != 1:
            raise
    else:
        if partial:
            fail("partial/promisor sources are unsupported; use a complete local checkout")
    origin = git(source, "remote", "get-url", "origin").decode().strip()
    if origin not in ("https://github.com/jeffery777/codex-dev-skills.git", "https://github.com/jeffery777/codex-dev-skills",
                      "git@github.com:jeffery777/codex-dev-skills.git"):
        fail("source origin does not match jeffery777/codex-dev-skills")
    revision = git(source, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        fail("source HEAD is not an immutable full Git commit")
    catalog_bytes = read_file(source / "catalog.yaml")
    if catalog_bytes != git(source, "show", f"{revision}:catalog.yaml"):
        fail("source catalog differs from fixed Git revision")
    digest = hashlib.sha256(catalog_bytes).hexdigest()
    catalog = next((c for c in catalogs if c["catalog_sha256"] == digest), None)
    if catalog is None:
        fail("unsupported source catalog; review and add its data mapping before installation")
    tree = {}
    for row in git(source, "ls-tree", "-rz", revision).split(b"\0"):
        if row:
            meta, path = row.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            tree[path.decode()] = (mode, kind, oid)
    for group in catalog["groups"].values():
        for artifact in group["artifacts"]:
            prefix = relative(artifact["source"])
            expected = artifact["files"]
            if manifest(source / prefix, artifact["type"]) != expected:
                fail(f"source payload differs from reviewed catalog: {prefix}")
            tracked = {p[len(prefix) + 1:]: v for p, v in tree.items() if p.startswith(prefix + "/")} if artifact["type"] == "directory" else {"": tree.get(prefix)}
            if set(tracked) != set(expected):
                fail(f"Git source inventory differs: {prefix}")
            for rel, record in expected.items():
                entry = tracked[rel]
                if entry is None or entry[1] != "blob" or entry[0] != ("100755" if record["executable"] else "100644"):
                    fail(f"unsafe Git payload type or mode: {prefix}/{rel}")
                payload_path = source / prefix / rel if rel else source / prefix
                payload = read_file(payload_path)
                oid = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
                if oid != entry[2] or hashlib.sha256(payload).hexdigest() != record["sha256"]:
                    fail(f"Git payload differs from reviewed source: {prefix}/{rel}")
    return catalog, {"repository": "jeffery777/codex-dev-skills", "revision": revision,
                     "version": catalog["version"], "catalog_sha256": digest, "core": catalog["core"]}


def artifacts(catalog: dict, groups: list[str]) -> list[dict]:
    result = {}
    for name in groups:
        if name not in catalog["groups"]:
            fail(f"unsupported group: {name}")
        for item in catalog["groups"][name]["artifacts"]:
            key = item["kind"] + "/" + relative(item["relative"])
            if key in result and result[key] != item:
                fail(f"conflicting inventory: {key}")
            result[key] = item
    return [result[key] for key in sorted(result)]


def transaction_artifacts(items: list[dict]) -> list[dict]:
    """Move the verified complete Core collection as one existing directory unit.

    Receipts keep their per-file format. Directory rename/rollback also retains
    the exact old subdirectory inventory across thirteen/eleven-file transitions.
    """
    prefix = "orchestration/core/"
    core_items = [item for item in items
                  if item["kind"] == "templates" and item["relative"].startswith(prefix)]
    if not core_items:
        return items
    result = [item for item in items if item not in core_items]
    files = {}
    for item in core_items:
        if item["type"] != "file" or set(item["files"]) != {""}:
            fail("unsupported Core collection artifact")
        files[relative(item["relative"][len(prefix):])] = item["files"][""]
    result.append({"kind": "templates", "relative": "orchestration/core",
                   "source": "vendor/engineering-workflow-core", "type": "directory",
                   "files": dict(sorted(files.items()))})
    return sorted(result, key=lambda item: item["kind"] + "/" + item["relative"])


def reviewed_catalogs() -> list[dict]:
    catalogs = load_json(read_file(REGISTRY))["catalogs"]
    digests = [item["catalog_sha256"] for item in catalogs]
    if not catalogs or len(digests) != len(set(digests)):
        fail("ambiguous or empty reviewed source catalogs")
    return catalogs


def expand(catalog: dict, groups: list[str]) -> list[str]:
    selected = set()
    def visit(name: str) -> None:
        if name in selected:
            return
        if name not in catalog["groups"]:
            fail(f"unsupported group: {name}")
        selected.add(name)
        for dependency in catalog["groups"][name]["depends_on"]:
            visit(dependency)
    for name in groups:
        visit(name)
    return sorted(selected)


def check_payload(items: list[dict], roots: dict) -> dict:
    identities = {}
    for item in items:
        target = Path(roots[item["kind"]]) / relative(item["relative"])
        before = fingerprint(target, item["type"])
        if manifest(target, item["type"]) != item["files"]:
            fail(f"custom, missing, or unknown managed content; preserve and inspect: {target}")
        after = fingerprint(target, item["type"])
        if before != after:
            fail(f"managed content changed while verifying: {target}")
        identities[item["kind"] + "/" + item["relative"]] = after
    core = [item for item in items if item["kind"] == "templates" and item["relative"].startswith("orchestration/core/")]
    if core:
        expected = {item["relative"][len("orchestration/core/"):]: item["files"][""] for item in core}
        target = Path(roots["templates"]) / "orchestration/core"
        before = fingerprint(target, "directory")
        if manifest(target, "directory") != expected:
            fail("custom or unknown content in the managed Core collection; preserve and inspect")
        after = fingerprint(target, "directory")
        if before != after:
            fail("managed Core collection changed while verifying")
        identities["templates/orchestration/core"] = after
    return identities


def read_receipt(path: Path, catalogs: list[dict], roots: dict) -> dict | None:
    if not os.path.lexists(path):
        return None
    receipt = load_json(read_file(path))
    if not isinstance(receipt, dict) or set(receipt) != {"schema", "source", "roots", "groups", "artifacts"} or type(receipt.get("schema")) is not int or receipt.get("schema") != 1 or receipt.get("roots") != roots:
        fail("unsupported ownership receipt or changed canonical target roots")
    source = receipt["source"]
    if not isinstance(source, dict) or set(source) != {"repository", "revision", "version", "catalog_sha256", "core"}:
        fail("malformed receipt source identity")
    revision = source["revision"]
    if source["repository"] != "jeffery777/codex-dev-skills" or not isinstance(revision, str) or len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        fail("receipt requires the correct repository and a full immutable revision")
    catalog = next((c for c in catalogs if c["catalog_sha256"] == receipt.get("source", {}).get("catalog_sha256")), None)
    groups = receipt["groups"]
    if not isinstance(groups, list) or any(not isinstance(g, str) or not g for g in groups) or len(set(groups)) != len(groups) or catalog is None or expand(catalog, groups) != sorted(groups):
        fail("receipt groups must be unique and dependency-closed")
    if catalog is None or receipt.get("artifacts") != artifacts(catalog, receipt["groups"]):
        fail("ownership receipt inventory does not match a reviewed source catalog")
    if receipt["source"].get("version") != catalog["version"] or receipt["source"].get("core") != catalog["core"]:
        fail("ownership receipt source identity differs from reviewed catalog")
    return receipt


def profile_receipt_identity(path: Path, prior: dict | None) -> str:
    before = fingerprint(path, "file")
    if before == "missing":
        return before
    expected = {item["relative"]: item["files"][""]["sha256"] for item in prior["artifacts"]
                if item["kind"] == "agent_profiles"} if prior else {}
    records = {}
    for row in read_file(path).decode().splitlines():
        cells = row.split("\t")
        if len(cells) != 2 or cells[0] in records:
            fail("unknown or malformed profile receipt; preserve and inspect")
        records[relative(cells[0])] = cells[1]
    if records != expected:
        fail("profile receipt differs from verified prior inventory; preserve and inspect")
    if fingerprint(path, "file") != before:
        fail("profile receipt changed while verifying")
    return before


def plan(args: argparse.Namespace) -> dict:
    catalogs = reviewed_catalogs()
    roots = dict(zip(("skills", "templates", "agent_profiles"), [str(Path(p).resolve()) for p in args.roots]))
    catalog, identity = load_source(Path(args.source), catalogs)
    receipt_before = fingerprint(Path(args.receipt), "file")
    prior = read_receipt(Path(args.receipt), catalogs, roots)
    receipt_after = fingerprint(Path(args.receipt), "file")
    if receipt_before != receipt_after:
        fail("ownership receipt changed during planning")
    if prior is None and args.previous_source:
        fail("legacy receipts have no verifiable target-root binding; migration is unsupported without independent ownership evidence")
    elif args.previous_source:
        fail("--previous-source is only for a legacy install without an inventory receipt")
    old_items = prior["artifacts"] if prior else []
    identities = check_payload(old_items, roots)
    requested = args.groups.split()
    old_groups = prior["groups"] if prior else []
    if args.action == "uninstall":
        if not prior:
            fail("uninstall requires a verified ownership receipt")
        remaining = sorted(set(old_groups) - set(requested))
        old_catalog = next(c for c in catalogs if c["catalog_sha256"] == prior["source"]["catalog_sha256"])
        if expand(old_catalog, remaining) != remaining:
            fail("remaining managed groups depend on a selected uninstall group")
        groups = remaining
        new_items = artifacts(old_catalog, groups)
        identity = prior["source"]
    else:
        if args.action == "install" and prior and prior["source"]["catalog_sha256"] != identity["catalog_sha256"]:
            fail("use update to replace an existing managed version")
        if prior and prior["source"]["catalog_sha256"] != identity["catalog_sha256"] and args.selection != "--all" and not set(old_groups).issubset(requested):
            fail("cross-version replacement requires all managed groups; review and select --all explicitly")
        groups = expand(catalog, sorted(set(requested) | set(old_groups)))
        new_items = artifacts(catalog, groups)
    old_transactions = transaction_artifacts(old_items)
    new_transactions = transaction_artifacts(new_items)
    old_keys = {(item["kind"], item["relative"]) for item in old_transactions}
    new_keys = {(item["kind"], item["relative"]) for item in new_transactions}
    for item in new_transactions:
        target = Path(roots[item["kind"]]) / relative(item["relative"])
        if (item["kind"], item["relative"]) not in old_keys and os.path.lexists(target):
            fail(f"unmanaged existing content; no implicit adoption or overwrite: {target}")
        if (item["kind"], item["relative"]) not in old_keys:
            identities[item["kind"] + "/" + item["relative"]] = "missing"
    retired = [item for item in old_transactions if (item["kind"], item["relative"]) not in new_keys]
    old_by_key = {(item["kind"], item["relative"]): item for item in old_transactions}
    puts = [] if args.action == "uninstall" else [item for item in new_transactions
            if old_by_key.get((item["kind"], item["relative"])) != item]
    receipt = {"schema": 1, "source": identity, "roots": roots, "groups": groups, "artifacts": new_items}
    profile_digest = hashlib.sha256(roots["agent_profiles"].encode()).hexdigest()
    profile_receipt = str(Path(args.receipt).parent / f"agent-profile-{profile_digest}.tsv")
    receipt_identities = {args.receipt: receipt_after, args.history: fingerprint(Path(args.history), "file")}
    if any(item["kind"] == "agent_profiles" for item in new_items + retired):
        receipt_identities[profile_receipt] = profile_receipt_identity(Path(profile_receipt), prior)
    return {"receipt": receipt, "puts": puts, "retired": retired, "identities": identities, "source": str(Path(args.source).resolve()),
            "receipt_identities": receipt_identities, "action": args.action, "requested": requested}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    for name in ("source", "receipt", "history", "target-mode", "action", "groups", "selection"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--previous-source", default="")
    p.add_argument("--roots", nargs=3, required=True)
    sub.add_parser("emit")
    sub.add_parser("receipt")
    sub.add_parser("verify")
    sub.add_parser("verify-staged")
    p = sub.add_parser("identity")
    p.add_argument("path")
    p.add_argument("type")
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(plan(args), sort_keys=True))
        return
    if args.command == "identity":
        print(fingerprint(Path(args.path), args.type))
        return
    if args.command == "verify-staged":
        data = load_json(sys.stdin.buffer.readline())
        expected = {item["kind"] + "/" + item["relative"]: item for item in data["puts"]}
        seen = set()
        for line in sys.stdin:
            kind, rel, path = line.rstrip("\n").split("\t")
            key = kind + "/" + relative(rel)
            if key in seen or key not in expected:
                fail("unexpected staged payload inventory")
            item = expected[key]
            if manifest(Path(path), item["type"]) != item["files"]:
                fail(f"staged payload differs from fixed source: {key}")
            seen.add(key)
        if seen != set(expected):
            fail("incomplete staged payload inventory")
        return
    data = json.load(sys.stdin)
    receipt = data["receipt"]
    if args.command == "receipt":
        print(json.dumps(receipt, sort_keys=True))
    elif args.command == "emit":
        for operation, items in (("put", data["puts"]), ("retire", data["retired"])):
            for item in items:
                key = item["kind"] + "/" + relative(item["relative"])
                print("\t".join((operation, item["kind"], relative(item["relative"]), item["type"], relative(item["source"]), data["identities"][key])))
    elif args.command == "verify":
        check_payload(receipt["artifacts"], receipt["roots"])
        for item in data["retired"]:
            path = Path(receipt["roots"][item["kind"]]) / item["relative"]
            if os.path.lexists(path):
                fail(f"retired payload remains; incomplete version replacement: {path}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
