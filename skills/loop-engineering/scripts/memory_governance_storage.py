"""MG1 G1 內部 SQLite／檔案機制；只有已通過 host 邊界的 core 使用。"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import sys
from dataclasses import dataclass

import memory_governance_contract as c
from memory_governance_host import RootBinding

MAIN = "managed.sqlite3"
LOCK = "coordination.lock"
JOURNAL = MAIN + "-journal"
SQL = (
    "CREATE TABLE root_meta (singleton INTEGER PRIMARY KEY CHECK(singleton=1), document BLOB NOT NULL) STRICT",
    "CREATE TABLE items (item_id TEXT PRIMARY KEY, identity_epoch INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','stopped')), current_revision INTEGER NOT NULL, revision_high_water INTEGER NOT NULL, erased_at INTEGER, FOREIGN KEY(item_id,current_revision) REFERENCES versions(item_id,revision) DEFERRABLE INITIALLY DEFERRED) STRICT",
    "CREATE TABLE versions (item_id TEXT NOT NULL REFERENCES items(item_id), revision INTEGER NOT NULL, document BLOB NOT NULL CHECK(length(document)<=16384), PRIMARY KEY(item_id,revision)) STRICT",
    "CREATE TABLE current_search (item_id TEXT NOT NULL, revision INTEGER NOT NULL, cue TEXT NOT NULL, summary TEXT NOT NULL, PRIMARY KEY(item_id,revision,cue), FOREIGN KEY(item_id,revision) REFERENCES versions(item_id,revision)) STRICT",
    "CREATE INDEX search_cue ON current_search(cue,item_id)",
    "CREATE TABLE proofs (sequence INTEGER PRIMARY KEY, operation_id TEXT NOT NULL UNIQUE, item_id TEXT NOT NULL REFERENCES items(item_id), document BLOB NOT NULL CHECK(length(document)<=2048)) STRICT",
)
CONTENT_FAMILY = "mg1-managed-content/v2"
PROOF_FAMILY = "mg1-operation-proof/v2"
SCHEMA_FINGERPRINT = c.digest({"schema": CONTENT_FAMILY, "proof": PROOF_FAMILY, "sql": list(SQL)})


def binding_digest(binding: RootBinding) -> str:
    """只由 host-owned 實體 binding 重算；不輸出路徑或建立持久登錄。"""
    material = {key: list(getattr(binding, key)) for key in
                ("directory_identity", "main_identity", "lock_identity")}
    return c.digest({**material, "scope_digest": c.digest(c.decode(binding.scope_bytes, 4096)),
                     "filesystem_id": binding.filesystem_id, "adapter_fingerprint": binding.adapter_fingerprint})


def runtime_facts() -> dict:
    # 只探測獨立 :memory: 連線，且僅由已 enabled 的 host 邊界呼叫。
    # compile/source/OS 指紋仍須 host 另驗 filesystem/temp/峰值資格。
    with contextlib.closing(sqlite3.connect(":memory:")) as probe:
        source_id = probe.execute("SELECT sqlite_source_id()").fetchone()[0]
        options = probe.execute("PRAGMA compile_options").fetchmany(257)
        c.require(len(options) <= 256, "build-unavailable")
    return {"sqlite_version": sqlite3.sqlite_version, "sqlite_source_id": source_id,
            "compile_options": sorted(row[0] for row in options), "python_version": sys.version.split()[0],
            "schema_fingerprint": SCHEMA_FINGERPRINT, "sql_fingerprint": c.digest(list(SQL)),
            "platform": os.uname().sysname, "os_release": os.uname().release,
            "journal_mode": "delete", "page_size": 4096, "temp_store": "memory"}


def identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _regular(value: os.stat_result, device: int) -> None:
    c.require(stat.S_ISREG(value.st_mode) and value.st_uid == os.geteuid()
              and value.st_mode & 0o077 == 0 and value.st_nlink == 1
              and value.st_dev == device, "unsafe-managed-file")


def root_fd(binding: RootBinding) -> int:
    """root 僅來自可信登錄；拒絕 symlink、不同 identity 與寬鬆存取。"""
    path = binding.root
    c.require(type(path) is type(Path()) and path.is_absolute()
              and path == path.resolve(strict=True), "unsafe-root")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        c.require(identity(info) == binding.directory_identity and info.st_uid == os.geteuid()
                  and info.st_mode & 0o077 == 0, "root-identity-mismatch")
        return fd
    except BaseException:
        os.close(fd)
        raise


def inventory(directory: int, binding: RootBinding, *, initialized: bool = True) -> dict:
    result = {}
    with os.scandir(directory) as entries:
        for entry in entries:
            c.require(len(result) < 3 and entry.name in {MAIN, LOCK, JOURNAL}, "unexpected-managed-file")
            info = entry.stat(follow_symlinks=False)
            _regular(info, binding.directory_identity[0])
            result[entry.name] = info
    if initialized:
        c.require(MAIN in result and LOCK in result, "missing-managed-file")
        c.require(identity(result[MAIN]) == binding.main_identity
                  and identity(result[LOCK]) == binding.lock_identity, "file-identity-mismatch")
    return result


@contextlib.contextmanager
def locked(binding: RootBinding, *, exclusive: bool = False):
    directory = root_fd(binding)
    lock = None
    try:
        entries = inventory(directory, binding)
        lock = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        c.require(identity(os.fstat(lock)) == binding.lock_identity, "file-identity-mismatch")
        try:
            fcntl.flock(lock, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise c.ContractError("busy") from exc
        entries = inventory(directory, binding)
        c.require(JOURNAL not in entries or entries[JOURNAL].st_size == 0, "recovery-required")
        yield directory
        inventory(directory, binding)
    finally:
        if lock is not None:
            os.close(lock)
        os.close(directory)


def measure(directory: int, binding: RootBinding, limits: dict) -> tuple[list[dict], dict]:
    entries = inventory(directory, binding)
    files = []
    total = 0
    roles = {MAIN: ("main", "main"), LOCK: ("lock", "coordination-lock"), JOURNAL: ("journal", "journal")}
    for name, before in entries.items():
        total += before.st_size
        c.require(total <= limits["data_limit_bytes"], "data-limit-exceeded")
        digest = hashlib.sha256()
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            opened = os.fstat(fd)
            c.require(identity(opened) == identity(before) and opened.st_size == before.st_size, "file-drift")
            remaining = before.st_size
            while remaining:
                data = os.read(fd, min(remaining, 65536))
                c.require(bool(data), "file-drift")
                digest.update(data)
                remaining -= len(data)
            after = os.fstat(fd)
            c.require(not os.read(fd, 1) and identity(after) == identity(opened)
                      and after.st_size == before.st_size and after.st_mtime_ns == before.st_mtime_ns, "file-drift")
        finally:
            os.close(fd)
        file_id, role = roles[name]
        files.append({"file_id": file_id, "role": role, "bytes": before.st_size, "sha256": digest.hexdigest()})
    files.sort(key=lambda item: item["file_id"])
    fs = os.fstatvfs(directory)
    available = min(c.MAX_NUMBER, fs.f_bavail * fs.f_frsize)
    return files, {"filesystem_id": binding.filesystem_id, "managed_bytes": total,
                   "available_work_bytes": available, "coverage": "complete", "work_budget": None}


def connect(binding: RootBinding, limits: dict, *, writer: bool = False) -> sqlite3.Connection:
    path = binding.root / MAIN
    info = path.lstat()
    c.require(identity(info) == binding.main_identity, "file-identity-mismatch")
    c.require(info.st_size <= limits["data_limit_bytes"], "data-limit-exceeded")
    connection = sqlite3.connect(path.as_uri() + ("?mode=rw&cache=private" if writer else "?mode=ro&cache=private"),
                                 uri=True, isolation_level=None, timeout=0)
    try:
        # 未編入 extension-loading 的 Python 沒有此 method；能力本來即不存在。
        if hasattr(connection, "enable_load_extension"):
            connection.enable_load_extension(False)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, c.MAX_ENVELOPE)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA foreign_keys=ON")
        c.require(identity(path.lstat()) == binding.main_identity, "file-identity-mismatch")
        for key, expected in (("page_size", 4096), ("journal_mode", "delete"), ("auto_vacuum", 2)):
            c.require(connection.execute("PRAGMA " + key).fetchone()[0] == expected, "pragma-mismatch")
        if writer:
            for key, value in (("synchronous", "EXTRA"), ("secure_delete", "ON"), ("temp_store", "MEMORY")):
                connection.execute("PRAGMA " + key + "=" + value)
            connection.execute("PRAGMA max_page_count=" + str(limits["data_limit_bytes"] // 4096))
            for key, expected in (("synchronous", 3), ("secure_delete", 1), ("temp_store", 2),
                                  ("max_page_count", limits["data_limit_bytes"] // 4096)):
                c.require(connection.execute("PRAGMA " + key).fetchone()[0] == expected, "pragma-mismatch")
        else:
            connection.execute("PRAGMA query_only=ON")
        for key, expected in (("trusted_schema", 0), ("foreign_keys", 1)):
            c.require(connection.execute("PRAGMA " + key).fetchone()[0] == expected, "pragma-mismatch")
        return connection
    except BaseException:
        connection.close()
        raise


def initialize(binding: RootBinding, limits: dict, scope: dict, now: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """只接受已授權空目錄；失敗保留部分產物，不自動覆寫／修復／清理。"""
    directory = root_fd(binding)
    lock = main = None
    connection = None
    try:
        c.require(binding.main_identity is None and binding.lock_identity is None, "already-initialized")
        c.require(not inventory(directory, binding, initialized=False), "root-not-empty")
        lock = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main = os.open(MAIN, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        connection = sqlite3.connect((binding.root / MAIN).as_uri() + "?mode=rw&cache=private", uri=True,
                                     isolation_level=None, timeout=0)
        for setting in ("page_size=4096", "journal_mode=DELETE", "synchronous=EXTRA", "auto_vacuum=INCREMENTAL",
                        "secure_delete=ON", "temp_store=MEMORY", "foreign_keys=ON", "trusted_schema=OFF",
                        "max_page_count=" + str(limits["data_limit_bytes"] // 4096)):
            connection.execute("PRAGMA " + setting)
        for key, expected in (("page_size", 4096), ("journal_mode", "delete"), ("auto_vacuum", 2),
                              ("synchronous", 3), ("secure_delete", 1), ("temp_store", 2),
                              ("foreign_keys", 1), ("trusted_schema", 0),
                              ("max_page_count", limits["data_limit_bytes"] // 4096)):
            c.require(connection.execute("PRAGMA " + key).fetchone()[0] == expected, "pragma-mismatch")
        connection.execute("BEGIN IMMEDIATE")
        for statement in SQL:
            connection.execute(statement)
        metadata = {"contract_version": CONTENT_FAMILY, **scope, "epoch": 1, "reject_before": now}
        connection.execute("INSERT INTO root_meta VALUES (1,?)", (c.canonical(metadata),))
        connection.commit()
        connection.close()
        connection = None
        os.fsync(main)
        os.fsync(lock)
        os.fsync(directory)
        return identity(os.fstat(main)), identity(os.fstat(lock))
    finally:
        if connection is not None:
            connection.close()
        if main is not None:
            os.close(main)
        if lock is not None:
            os.close(lock)
        os.close(directory)


def metadata(connection: sqlite3.Connection, scope: dict) -> dict:
    actual = connection.execute("SELECT sql FROM sqlite_schema WHERE sql IS NOT NULL ORDER BY sql").fetchmany(len(SQL) + 1)
    c.require([row[0] for row in actual] == sorted(SQL), "schema-mismatch")
    rows = connection.execute("SELECT singleton,document FROM root_meta").fetchmany(2)
    c.require(len(rows) == 1 and rows[0][0] == 1, "metadata-mismatch")
    data = c.decode(rows[0][1], 4096)
    c.fields(data, {"contract_version", *scope, "epoch", "reject_before"})
    c.require(data["contract_version"] == CONTENT_FAMILY
              and {k: data[k] for k in scope} == scope, "metadata-mismatch")
    # G1 不實作 retention；任何 epoch 切換均為不支援的 root。
    c.require(c.integer(data["epoch"], 1) == 1, "epoch-unavailable")
    c.integer(data["reject_before"])
    return data


def load_item(connection: sqlite3.Connection, item_id: str, scope: dict, limits: dict) -> dict | None:
    row = connection.execute("SELECT item_id,identity_epoch,status,current_revision,revision_high_water,erased_at FROM items WHERE item_id=?", (item_id,)).fetchone()
    if row is None:
        return None
    item = dict(zip(("item_id", "identity_epoch", "status", "current_revision", "revision_high_water", "erased_at"), row))
    c.uuid(item["item_id"])
    c.require(c.integer(item["identity_epoch"], 1) == 1, "identity-epoch-mismatch")
    c.one_of(item["status"], {"active", "stopped"})
    c.require(item["erased_at"] is None, "erased-unavailable")
    c.integer(item["current_revision"], 1)
    c.require(item["revision_high_water"] == item["current_revision"], "revision-mismatch")
    rows = connection.execute("SELECT revision,document FROM versions WHERE item_id=? ORDER BY revision", (item_id,)).fetchmany(limits["max_versions"] + 1)
    c.require(1 <= len(rows) <= limits["max_versions"], "version-limit")
    versions = []
    for revision, data in rows:
        value = c.decode(data, limits["max_payload_bytes"])
        c.validate_version(value, scope, limits)
        c.require(value["revision"] == revision == len(versions) + 1, "revision-mismatch")
        if versions:
            c.require(versions[-1]["retired_at"] == value["created_at"], "retirement-mismatch")
        versions.append(value)
    c.require(versions[-1]["retired_at"] is None and versions[-1]["revision"] == item["current_revision"], "current-mismatch")
    expected = c.projection(versions[-1], item["status"])
    actual = connection.execute("SELECT cue,summary,revision FROM current_search WHERE item_id=? ORDER BY cue", (item_id,)).fetchmany(17)
    c.require([dict(zip(("cue", "summary", "revision"), row)) for row in actual] == expected, "projection-mismatch")
    item["versions"] = versions
    item["projection_digest"] = c.digest(expected)
    return item


def logical_item(item: dict) -> dict:
    return {**item, "versions": [{"revision": v["revision"], "version_digest": c.digest(v)} for v in item["versions"]]}


def _logical_state_digest(items, scope: dict, limits: dict, meta: dict) -> str:
    """串流已排序的 compact logical items，不保存版本全文。"""
    hasher = hashlib.sha256()
    hasher.update(b'{"epoch":' + c.canonical(meta["epoch"]) + b',"items":[')
    for emitted, item in enumerate(items):
        c.require(emitted < limits["max_items"], "item-limit")
        if emitted:
            hasher.update(b",")
        hasher.update(c.canonical(item))
    hasher.update(b'],"reject_before":' + c.canonical(meta["reject_before"]) + b',"scope":' + c.canonical(scope) + b'}')
    return hasher.hexdigest()


def state_digest(connection: sqlite3.Connection, scope: dict, limits: dict, meta: dict,
                 replacement: dict | None = None) -> str:
    """以 canonical key/order 串流 logical state；不把 root 全文物化到 RAM。"""
    def items():
        replaced = False
        for (item_id,) in connection.execute("SELECT item_id FROM items ORDER BY item_id"):
            if replacement is not None and not replaced and replacement["item_id"] <= item_id:
                yield logical_item(replacement)
                replaced = True
            if replacement is None or item_id != replacement["item_id"]:
                yield logical_item(load_item(connection, item_id, scope, limits))
        if replacement is not None and not replaced:
            yield logical_item(replacement)
    return _logical_state_digest(items(), scope, limits, meta)


@dataclass(frozen=True)
class Snapshot:
    digest: str
    epoch: int
    reject_before: int
    clock_floor: int
    items: int
    proofs: int


def snapshot(connection: sqlite3.Connection, scope: dict, limits: dict) -> Snapshot:
    meta = metadata(connection, scope)
    counts = {table: connection.execute("SELECT count(*) FROM " + table).fetchone()[0]
              for table in ("items", "versions", "current_search", "proofs")}
    c.require(counts["items"] <= limits["max_items"] and counts["versions"] <= counts["items"] * limits["max_versions"]
              and counts["current_search"] <= counts["items"] * 16
              and counts["proofs"] <= limits["max_proofs"] + limits["maintenance_proof_reserve"], "storage-count-limit")
    c.require(connection.execute("PRAGMA foreign_key_check").fetchone() is None, "integrity-failed")
    current_digest = state_digest(connection, scope, limits, meta)
    previous = c.digest({"scope": scope, "epoch": meta["epoch"], "reject_before": meta["reject_before"], "items": []})
    floor = meta["reject_before"]
    last_per_item = {}
    versions_seen = {}
    status_seen = {}
    replayed = {}
    for number, (sequence, operation_id, item_id, data) in enumerate(connection.execute("SELECT sequence,operation_id,item_id,document FROM proofs ORDER BY sequence"), 1):
        c.require(number <= counts["proofs"] and sequence == number, "proof-sequence-mismatch")
        record = c.g1_proof(c.decode(data, 2048))
        c.require(record["contract_version"] == PROOF_FAMILY, "proof-version-unavailable")
        c.require(record["readback_basis"]["scope_digest"] == c.digest(scope), "proof-basis-mismatch")
        c.require(record["operation_id"] == operation_id and record["item_id"] == item_id
                  and record["before_digest"] == previous and record["recorded_at"] >= floor
                  and record["acceptance_epoch"] == meta["epoch"], "proof-chain-mismatch")
        floor = record["recorded_at"]
        operation = record["operation"]
        prior_revision = versions_seen.get(item_id, 0)
        c.require(record["before_revision"] == prior_revision, "proof-version-mismatch")
        if operation == "add":
            c.require(item_id not in status_seen, "proof-lifecycle-mismatch")
            status_seen[item_id] = "active"
        else:
            c.require(item_id in status_seen, "proof-lifecycle-mismatch")
            if operation in {"stop", "resume"}:
                required = "active" if operation == "stop" else "stopped"
                c.require(status_seen[item_id] == required, "proof-lifecycle-mismatch")
                status_seen[item_id] = "stopped" if operation == "stop" else "active"
        if operation in {"add", "update", "restore"}:
            c.require(record["after_revision"] == versions_seen.get(item_id, 0) + 1, "proof-version-mismatch")
            versions_seen[item_id] = record["after_revision"]
        c.require(record["after_revision"] == versions_seen.get(item_id), "proof-version-mismatch")
        version_row = connection.execute("SELECT document FROM versions WHERE item_id=? AND revision=?",
                                         (item_id, record["after_revision"])).fetchone()
        c.require(version_row is not None, "proof-version-mismatch")
        version = c.validate_version(c.decode(version_row[0], limits["max_payload_bytes"]), scope, limits)
        c.require(record["recorded_at"] >= version["validation"]["verified_at"], "proof-time-mismatch")
        if operation == "restore":
            source_row = connection.execute("SELECT document FROM versions WHERE item_id=? AND revision=?",
                                            (item_id, record["restore_source_revision"])).fetchone()
            c.require(source_row is not None, "proof-version-mismatch")
            retained = c.validate_version(c.decode(source_row[0], limits["max_payload_bytes"]), scope, limits)
            c.restore_content(version, retained)
        c.require(record["projection_digest"] == c.digest(c.projection(version, status_seen[item_id])),
                  "proof-projection-mismatch")
        if operation == "add":
            replayed[item_id] = {"item_id": item_id, "identity_epoch": 1, "status": "active",
                                 "current_revision": 1, "revision_high_water": 1,
                                 "erased_at": None, "versions": []}
        logical = replayed[item_id]
        if operation in {"add", "update", "restore"}:
            if prior_revision:
                retired_row = connection.execute("SELECT document FROM versions WHERE item_id=? AND revision=?",
                                                  (item_id, prior_revision)).fetchone()
                c.require(retired_row is not None, "proof-version-mismatch")
                retired = c.decode(retired_row[0], limits["max_payload_bytes"])
                c.require(retired["retired_at"] == version["created_at"], "retirement-mismatch")
                logical["versions"][-1]["version_digest"] = c.digest(retired)
            # 後續 update 已在 stored version 填入 retired_at；歷史當時 current 尚未退休。
            historical_current = {**version, "retired_at": None}
            logical["versions"].append({"revision": record["after_revision"],
                                         "version_digest": c.digest(historical_current)})
        logical.update(status=status_seen[item_id], current_revision=record["after_revision"],
                       revision_high_water=record["after_revision"], projection_digest=record["projection_digest"])
        previous = _logical_state_digest((replayed[key] for key in sorted(replayed)), scope, limits, meta)
        c.require(record["after_digest"] == previous, "proof-state-mismatch")
        last_per_item[item_id] = (record["after_revision"], record["projection_digest"])
    c.require(previous == current_digest and len(last_per_item) == counts["items"], "proof-state-mismatch")
    for (item_id,) in connection.execute("SELECT item_id FROM items ORDER BY item_id"):
        item = load_item(connection, item_id, scope, limits)
        c.require(status_seen[item_id] == item["status"]
                  and last_per_item.get(item_id) == (item["current_revision"], item["projection_digest"]), "proof-current-mismatch")
    return Snapshot(current_digest, meta["epoch"], meta["reject_before"], floor, counts["items"], counts["proofs"])


def write_item(connection: sqlite3.Connection, item: dict) -> None:
    connection.execute("INSERT INTO items VALUES (?,?,?,?,?,?) ON CONFLICT(item_id) DO UPDATE SET status=excluded.status,current_revision=excluded.current_revision,revision_high_water=excluded.revision_high_water",
                       tuple(item[k] for k in ("item_id", "identity_epoch", "status", "current_revision", "revision_high_water", "erased_at")))
    for version in item["versions"]:
        connection.execute("INSERT INTO versions VALUES (?,?,?) ON CONFLICT(item_id,revision) DO UPDATE SET document=excluded.document",
                           (item["item_id"], version["revision"], c.canonical(version, 16384)))
    connection.execute("DELETE FROM current_search WHERE item_id=?", (item["item_id"],))
    connection.executemany("INSERT INTO current_search VALUES (?,?,?,?)",
                           [(item["item_id"], row["revision"], row["cue"], row["summary"])
                            for row in c.projection(item["versions"][-1], item["status"])])
