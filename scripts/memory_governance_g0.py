"""MG1 G0 合成契約檢查；不提供儲存、執行或授權能力。"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from pathlib import Path

VERSION = "mg1-g0-synthetic/v0"
MAX_INPUT_BYTES = 1_048_576
MAX_NUMBER = 2**53 - 1
ID = re.compile(r"synthetic-[a-z0-9][a-z0-9-]{0,63}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
OPERATIONS = {"add", "update", "stop", "resume", "restore", "erase-content", "prune-history", "compact"}
GROWTH = {"add", "update", "resume", "restore"}
SANITIZING = {"erase-content", "prune-history"}
MANAGED_FILES = {"main", "fts-shadow", "wal", "journal", "temp"}
PROFILE_FIELDS = {
    "max_items", "max_versions", "history_seconds", "max_payload_bytes",
    "max_proofs", "proof_seconds", "confirmation_seconds", "max_scan_items",
    "budget_bytes", "reserve_bytes", "maintenance_proof_reserve", "marker_seconds",
}


class ContractError(ValueError):
    """只回傳固定錯誤碼，不回顯輸入內容或路徑。"""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def fields(value: object, expected: set[str]) -> dict:
    require(type(value) is dict and set(value) == expected, "invalid-fields")
    return value


def integer(value: object, minimum: int = 0, maximum: int = MAX_NUMBER) -> int:
    require(type(value) is int and minimum <= value <= maximum, "invalid-integer")
    return value


def identifier(value: object) -> str:
    require(type(value) is str and ID.fullmatch(value) is not None, "invalid-synthetic-id")
    return value


def digest_text(value: object) -> str:
    require(type(value) is str and DIGEST.fullmatch(value) is not None, "invalid-digest")
    return value


def choice(value: object, allowed: set[str]) -> str:
    require(type(value) is str and value in allowed, "invalid-enum")
    return value


def sequence(value: object, maximum: int) -> list:
    require(type(value) is list and len(value) <= maximum, "invalid-list")
    return value


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise ContractError("invalid-json") from exc


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate-key")
        result[key] = value
    return result


def _constant(_value: str) -> None:
    raise ContractError("invalid-json")


def read_json(path: str | Path) -> dict:
    """有界讀取顯式 regular file；拒絕各路徑元件的 symlink 與 special file。"""
    fd = None
    directory = None
    try:
        absolute = Path(os.path.abspath(path))
        directory = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY)
        for component in absolute.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode) and opened.st_size <= MAX_INPUT_BYTES,
                "unsafe-input")
        with os.fdopen(fd, "rb") as stream:
            fd = None
            data = stream.read(MAX_INPUT_BYTES + 1)
        require(len(data) <= MAX_INPUT_BYTES, "input-too-large")
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
        require(type(value) is dict, "invalid-json")
        return value
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid-input") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if directory is not None:
            os.close(directory)


def scope(value: object) -> dict:
    value = fields(value, {"principal_id", "root_id"})
    for item in value.values():
        identifier(item)
    return value


def profile(value: object) -> dict:
    value = fields(value, PROFILE_FIELDS)
    for item in value.values():
        integer(item, 1)
    require(value["max_items"] <= 100 and value["max_versions"] <= 20
            and value["max_proofs"] + value["maintenance_proof_reserve"] <= 100
            and value["max_scan_items"] <= 100,
            "checker-limit")
    require(value["reserve_bytes"] < value["budget_bytes"]
            and value["max_payload_bytes"] <= value["budget_bytes"]
            and value["confirmation_seconds"] <= value["proof_seconds"],
            "invalid-profile")
    return value


def version(value: object, limits: dict, now: int) -> dict:
    value = fields(value, {"revision", "created_at", "retired_at", "body", "summary", "cues"})
    integer(value["revision"], 1)
    integer(value["created_at"], 0, now)
    if value["retired_at"] is not None:
        integer(value["retired_at"], value["created_at"], now)
    for name in ("body", "summary"):
        require(type(value[name]) is str and value[name].startswith("synthetic:")
                and len(value[name]) > len("synthetic:"), "synthetic-content-required")
    cues = sequence(value["cues"], 16)
    require(bool(cues), "missing-cues")
    for cue in cues:
        identifier(cue)
    require(len(set(cues)) == len(cues), "duplicate-cues")
    require(len(canonical(value)) <= limits["max_payload_bytes"], "payload-limit")
    return value


def phases(value: object, operation: str, reclaim: bool) -> str:
    value = fields(value, {"transaction", "sanitization", "compaction", "outcome"})
    tx = choice(value["transaction"], {"succeeded", "failed", "unknown"})
    san = choice(value["sanitization"], {"succeeded", "pending", "failed", "not-requested"})
    comp = choice(value["compaction"], {"succeeded", "pending", "failed", "not-requested"})
    if tx != "succeeded":
        require(san == comp == "not-requested", "phase-order")
        outcome = "failed" if tx == "failed" else "state-unknown"
    elif operation in SANITIZING:
        require(san != "not-requested", "missing-sanitization")
        if san != "succeeded":
            require(comp == "not-requested", "phase-order")
            outcome = "sanitization-pending"
        elif reclaim:
            require(comp != "not-requested", "missing-compaction")
            outcome = "complete" if comp == "succeeded" else "space-reclaim-pending"
        else:
            require(comp == "not-requested", "unrequested-compaction")
            outcome = "complete"
    elif operation == "compact":
        require(san == "not-requested" and comp != "not-requested", "phase-order")
        outcome = "complete" if comp == "succeeded" else "space-reclaim-pending"
    else:
        require(san == comp == "not-requested", "unrequested-maintenance")
        outcome = "complete"
    require(value["outcome"] == outcome, "false-success")
    return outcome


def state(value: object, limits: dict, now: int) -> dict:
    value = fields(value, {"scope", "epoch", "reject_before", "items", "proofs", "storage"})
    scope(value["scope"])
    integer(value["epoch"], 1)
    integer(value["reject_before"], 0, now)
    seen = set()
    for item in sequence(value["items"], limits["max_items"]):
        fields(item, {"item_id", "identity_epoch", "erased_at", "status",
                      "current_revision", "indexed_revision", "versions"})
        item_id = identifier(item["item_id"])
        integer(item["identity_epoch"], 1, value["epoch"])
        require(item_id not in seen, "duplicate-item")
        seen.add(item_id)
        status = choice(item["status"], {"active", "stopped", "erased"})
        current = integer(item["current_revision"], 1)
        versions = sequence(item["versions"], limits["max_versions"])
        numbers = []
        for entry in versions:
            version(entry, limits, now)
            numbers.append(entry["revision"])
        require(numbers == sorted(set(numbers)), "revision-order")
        if status == "erased":
            require(not versions and item["indexed_revision"] is None, "erased-content-present")
            integer(item["erased_at"], 0, now)
        else:
            require(item["erased_at"] is None, "unexpected-erasure-marker")
            require(bool(numbers) and numbers[-1] == current, "current-version-mismatch")
            require(versions[-1]["retired_at"] is None
                    and all(v["retired_at"] is not None for v in versions[:-1]),
                    "invalid-retirement")
            require(all(v["retired_at"] <= following["created_at"]
                        for v, following in zip(versions, versions[1:])), "invalid-retirement")
            expected_index = current if status == "active" else None
            require(type(item["indexed_revision"]) is type(expected_index)
                    and item["indexed_revision"] == expected_index, "index-revision-mismatch")
    proof_ids = set()
    for proof in sequence(value["proofs"], limits["max_proofs"] + limits["maintenance_proof_reserve"]):
        fields(proof, {"operation_id", "preview_digest", "operation", "item_id",
                       "identity_epoch", "reclaim_space", "issued_at", "recorded_at", "epoch", "result"})
        operation_id = identifier(proof["operation_id"])
        require(operation_id not in proof_ids, "duplicate-operation")
        proof_ids.add(operation_id)
        digest_text(proof["preview_digest"])
        operation = choice(proof["operation"], OPERATIONS)
        if operation == "compact":
            require(proof["item_id"] is None and proof["identity_epoch"] is None, "compact-item-scope")
        else:
            require(identifier(proof["item_id"]) in seen, "proof-item-missing")
            integer(proof["identity_epoch"], 1, value["epoch"])
            require(any(i["item_id"] == proof["item_id"] and i["identity_epoch"] == proof["identity_epoch"]
                        for i in value["items"]), "proof-identity-mismatch")
        require(type(proof["reclaim_space"]) is bool, "invalid-boolean")
        require(operation in SANITIZING or proof["reclaim_space"] == (operation == "compact"),
                "unrequested-compaction")
        integer(proof["issued_at"], 0, now)
        integer(proof["recorded_at"], proof["issued_at"], now)
        integer(proof["epoch"], 1, value["epoch"])
        if operation != "compact":
            require(proof["identity_epoch"] <= proof["epoch"], "proof-identity-mismatch")
        if operation == "erase-content":
            require(any(i["item_id"] == proof["item_id"] and i["status"] == "erased"
                        for i in value["items"]), "erase-proof-content-present")
        result = proof["result"]
        fields(result, {"transaction", "sanitization", "compaction", "outcome"})
        phases(result, operation, proof["reclaim_space"])
        require(result["transaction"] == "succeeded", "non-durable-proof")
    storage = fields(value["storage"], {"file_bytes", "free_bytes", "reclaimable_bytes"})
    for count in storage.values():
        integer(count)
    require(storage["reclaimable_bytes"] <= storage["file_bytes"], "invalid-storage")
    require(storage["file_bytes"] <= limits["budget_bytes"], "storage-budget")
    # 計入正文、歷史、proof 及控制資料；這只校驗合成 byte 聲明，不量測 SQLite。
    require(len(canonical({k: v for k, v in value.items() if k != "storage"}))
            <= storage["file_bytes"], "underreported-storage")
    return value


def context(value: object, before: dict, limits: dict) -> dict:
    value = fields(value, {"contract_version", "scope", "now", "before_digest",
                          "profile_digest", "accepted_confirmations", "accepted_retention", "accepted_continuations",
                          "capabilities"})
    require(value["contract_version"] == VERSION, "unsupported-version")
    require(scope(value["scope"]) == before["scope"], "scope-mismatch")
    integer(value["now"])
    require(digest_text(value["before_digest"]) == digest(before), "stale-state")
    require(digest_text(value["profile_digest"]) == digest(limits), "unaccepted-profile")
    for key in ("accepted_confirmations", "accepted_retention", "accepted_continuations"):
        entries = sequence(value[key], 100)
        for entry in entries:
            digest_text(entry)
        require(len(set(entries)) == len(entries), "duplicate-acceptance")
    caps = sequence(value["capabilities"], 4)
    for cap in caps:
        choice(cap, {"audit", "item-write", "erase-content", "root-maintenance"})
    require(len(set(caps)) == len(caps), "duplicate-capability")
    return value


def _preview(value: object, before: dict, limits: dict, ctx: dict) -> dict:
    value = fields(value, {"scope", "operation_id", "nonce", "issued_at", "expires_at", "epoch",
                          "before_digest", "profile_digest",
                          "operation", "item_id", "identity_epoch", "expected_revision", "next_version",
                          "restore_revision", "erase_revisions", "managed_files",
                          "unmanaged_copies", "reclaim_space"})
    require(scope(value["scope"]) == before["scope"], "scope-mismatch")
    require(digest_text(value["before_digest"]) == digest(before), "stale-preview")
    require(digest_text(value["profile_digest"]) == digest(limits), "preview-profile-mismatch")
    identifier(value["operation_id"])
    identifier(value["nonce"])
    issued = integer(value["issued_at"], 0, ctx["now"])
    expiry = integer(value["expires_at"], issued + 1)
    require(expiry - issued <= limits["confirmation_seconds"] and ctx["now"] < expiry,
            "confirmation-expired")
    require(integer(value["epoch"], 1) == before["epoch"]
            and issued >= before["reject_before"], "request-before-floor")
    require(value["operation_id"] not in {p["operation_id"] for p in before["proofs"]},
            "replayed-request")
    op = choice(value["operation"], OPERATIONS)
    require(type(value["reclaim_space"]) is bool, "invalid-boolean")
    erase = sequence(value["erase_revisions"], limits["max_versions"])
    for revision in erase:
        integer(revision, 1)
    require(erase == sorted(set(erase)), "invalid-delete-set")
    managed = sequence(value["managed_files"], len(MANAGED_FILES))
    for file_kind in managed:
        choice(file_kind, MANAGED_FILES)
    require(len(set(managed)) == len(managed), "duplicate-managed-file")
    unmanaged = sequence(value["unmanaged_copies"], 16)
    for other in unmanaged:
        identifier(other)
    require(len(set(unmanaged)) == len(unmanaged), "duplicate-unmanaged-copy")
    if op == "compact":
        require(value["item_id"] is None and value["expected_revision"] is None
                and value["identity_epoch"] is None and value["reclaim_space"] is True, "compact-item-scope")
    else:
        identifier(value["item_id"])
        integer(value["identity_epoch"], 1, before["epoch"])
        if op == "add":
            require(value["expected_revision"] is None, "add-revision")
            require(value["identity_epoch"] == before["epoch"], "stale-identity-epoch")
        else:
            integer(value["expected_revision"], 1)
    if op in {"add", "update", "restore"}:
        version(value["next_version"], limits, ctx["now"])
        require(value["next_version"]["created_at"] == ctx["now"], "new-version-time")
        require(value["next_version"]["retired_at"] is None, "invalid-retirement")
    else:
        require(value["next_version"] is None, "unexpected-content")
    if op == "restore":
        integer(value["restore_revision"], 1)
    else:
        require(value["restore_revision"] is None, "unexpected-restore")
    if op in SANITIZING:
        require(bool(erase) and set(managed) == MANAGED_FILES, "incomplete-delete-set")
    elif op == "compact":
        require(not erase and set(managed) == MANAGED_FILES, "incomplete-maintenance-set")
    else:
        require(not erase and not managed and not value["unmanaged_copies"]
                and not value["reclaim_space"], "unrequested-maintenance")
    caps = set(ctx["capabilities"])
    required = {"root-maintenance"} if op == "compact" else {"item-write"}
    if op in SANITIZING:
        # 合成 profile 涵蓋資料庫級殘留處理，須明確 root 權限；不是推定單筆權限。
        required = {"erase-content", "root-maintenance"}
    require(required <= caps, "missing-capability")
    return value


def _items_after(before: dict, preview: dict, limits: dict, now: int) -> list:
    """只建立供比較的記憶體投影，不能執行任何 backend 動作。"""
    items = copy.deepcopy(before["items"])
    op = preview["operation"]
    if op == "compact":
        return items
    target = next((i for i in items if i["item_id"] == preview["item_id"]), None)
    if op == "add":
        require(target is None, "identity-reuse")
        require(preview["next_version"]["revision"] == 1, "new-identity-revision")
        items.append({"item_id": preview["item_id"], "identity_epoch": preview["identity_epoch"],
                      "erased_at": None, "status": "active", "current_revision": 1,
                      "indexed_revision": 1, "versions": [copy.deepcopy(preview["next_version"])]})
        require(len(items) <= limits["max_items"], "item-limit")
        return items
    require(target is not None, "missing-target")
    require(target["identity_epoch"] == preview["identity_epoch"], "identity-epoch-mismatch")
    require(target["current_revision"] == preview["expected_revision"], "revision-conflict")
    require(target["status"] != "erased", "erased-identity")
    if op in {"update", "restore"}:
        new = preview["next_version"]
        require(new["revision"] == target["current_revision"] + 1, "revision-conflict")
        if op == "restore":
            old = next((v for v in target["versions"]
                        if v["revision"] == preview["restore_revision"]), None)
            require(old is not None, "missing-restore-version")
            require(all(new[k] == old[k] for k in ("body", "summary", "cues")), "restore-content-mismatch")
        target["versions"][-1]["retired_at"] = now
        target["versions"].append(copy.deepcopy(new))
        require(len(target["versions"]) <= limits["max_versions"], "history-limit")
        require(all(now - v["retired_at"] <= limits["history_seconds"]
                    for v in target["versions"][:-1]), "history-expired")
        target["current_revision"] = new["revision"]
        target["indexed_revision"] = new["revision"] if target["status"] == "active" else None
    elif op == "stop":
        require(target["status"] == "active", "invalid-lifecycle")
        target["status"], target["indexed_revision"] = "stopped", None
    elif op == "resume":
        require(target["status"] == "stopped", "invalid-lifecycle")
        target["status"], target["indexed_revision"] = "active", target["current_revision"]
    elif op == "erase-content":
        require(preview["erase_revisions"] == [v["revision"] for v in target["versions"]],
                "incomplete-delete-set")
        target["status"], target["indexed_revision"], target["versions"] = "erased", None, []
        target["erased_at"] = now
    elif op == "prune-history":
        selected = set(preview["erase_revisions"])
        require(selected <= {v["revision"] for v in target["versions"]}
                and target["current_revision"] not in selected, "invalid-history-delete-set")
        target["versions"] = [v for v in target["versions"] if v["revision"] not in selected]
    return items


def _storage_after(before: dict, after: dict, result: dict, limits: dict, *, growth: bool) -> None:
    old, new = before["storage"], after["storage"]
    require(old["free_bytes"] >= limits["reserve_bytes"], "maintenance-reserve")
    if growth:
        require(old["file_bytes"] + limits["reserve_bytes"] <= limits["budget_bytes"]
                and new["file_bytes"] + limits["reserve_bytes"] <= limits["budget_bytes"],
                "maintenance-reserve")
        require(len(after["proofs"]) <= limits["max_proofs"], "proof-reserve")
    if result["compaction"] == "succeeded":
        reclaimed = old["file_bytes"] - new["file_bytes"]
        require(0 <= reclaimed <= old["reclaimable_bytes"]
                and new["free_bytes"] == old["free_bytes"] + reclaimed
                and new["reclaimable_bytes"] == old["reclaimable_bytes"] - reclaimed,
                "reclaim-measurement-mismatch")
    else:
        require(new["file_bytes"] >= old["file_bytes"], "unproven-space-reclaim")
        require(new["free_bytes"] == old["free_bytes"] - (new["file_bytes"] - old["file_bytes"]),
                "storage-delta-mismatch")


def _retention(value: dict, before: dict, after: dict, limits: dict, ctx: dict) -> None:
    require("root-maintenance" in ctx["capabilities"], "missing-capability")
    require(before["storage"]["free_bytes"] >= limits["reserve_bytes"], "maintenance-reserve")
    confirmed = integer(value["confirmed_at"], before["reject_before"], ctx["now"])
    require(ctx["now"] - confirmed < limits["confirmation_seconds"], "confirmation-expired")
    transition = {"before_digest": digest(before), "after_digest": digest(after),
                  "profile_digest": digest(limits), "confirmed_at": confirmed}
    require(digest(transition) in ctx["accepted_retention"], "unaccepted-retention")
    require(after["epoch"] == before["epoch"] + 1
            and before["reject_before"] < after["reject_before"] <= ctx["now"], "floor-not-advanced")
    require(after["storage"] == before["storage"], "retention-content-changed")
    removed = [p for p in before["proofs"] if p["result"]["outcome"] == "complete"
               and confirmed - p["recorded_at"] > limits["proof_seconds"]]
    kept = [p for p in before["proofs"] if p not in removed]
    require(all(p in after["proofs"] for p in kept if p["result"]["outcome"] != "complete"),
            "pending-proof-pruned")
    require(after["proofs"] == kept, "invalid-proof-retention")
    referenced = {(p["item_id"], p["identity_epoch"]) for p in kept}
    markers = [i for i in before["items"] if i["status"] == "erased"
               and confirmed - i["erased_at"] > limits["marker_seconds"]
               and (i["item_id"], i["identity_epoch"]) not in referenced]
    require(after["items"] == [i for i in before["items"] if i not in markers], "invalid-marker-retention")
    require(bool(removed or markers), "empty-retention")
    require(all(p["issued_at"] < after["reject_before"] for p in removed)
            and all(i["erased_at"] < after["reject_before"] for i in markers), "replay-floor-gap")


def _continuation(value: dict, before: dict, after: dict, limits: dict, ctx: dict) -> None:
    operation_id = identifier(value["operation_id"])
    old = next((p for p in before["proofs"] if p["operation_id"] == operation_id), None)
    require(old is not None and old["result"]["outcome"] != "complete", "no-pending-operation")
    required = {"root-maintenance"} | ({"erase-content"} if old["operation"] in SANITIZING else set())
    require(required <= set(ctx["capabilities"]), "missing-capability")
    acceptance = {"before_digest": digest(before), "after_digest": digest(after),
                  "profile_digest": digest(limits),
                  "operation_id": operation_id, "result": value["result"], "confirmed_at": value["confirmed_at"]}
    integer(value["confirmed_at"], max(before["reject_before"], old["recorded_at"]), ctx["now"])
    require(ctx["now"] - value["confirmed_at"] < limits["confirmation_seconds"], "confirmation-expired")
    require(digest(acceptance) in ctx["accepted_continuations"], "unaccepted-continuation")
    result = value["result"]
    phases(result, old["operation"], old["reclaim_space"])
    require(result["transaction"] == "succeeded", "continuation-transaction")
    for phase in ("sanitization", "compaction"):
        require(old["result"][phase] != "succeeded" or result[phase] == "succeeded", "phase-regression")
    expected = copy.deepcopy(before["proofs"])
    revised = next(p for p in expected if p["operation_id"] == operation_id)
    revised["result"], revised["recorded_at"] = copy.deepcopy(result), ctx["now"]
    require(after["items"] == before["items"] and after["proofs"] == expected, "unexpected-continuation-change")
    _storage_after(before, after, result, limits, growth=False)


def validate_case(value: object, caller_context: object = None) -> dict:
    """檢查合成聲明的一致性；輸出永不授權操作或宣稱 runtime 能力。"""
    require(type(value) is dict and len(canonical(value)) <= MAX_INPUT_BYTES, "invalid-case")
    require(value.get("contract_version") == VERSION, "unsupported-version")
    identifier(value.get("case_id"))
    mode = choice(value.get("mode"), {"off", "audit", "maintenance", "retention", "continuation"})
    base_fields = {"contract_version", "case_id", "mode"}
    verdict = {"contract_version": VERSION, "case_id": value["case_id"], "status": "conformant",
               "operation_authorized": False, "runtime_proven": False, "write_performed": False}
    if mode == "off":
        fields(value, base_fields)
        require(caller_context is None, "off-context-forbidden")
        return verdict
    common = base_fields | {"profile", "before", "after"}
    fields(value, common | ({"preview", "confirmation", "result"} if mode == "maintenance"
                            else {"operation_id", "result", "confirmed_at"} if mode == "continuation"
                            else {"confirmed_at"} if mode == "retention"
                            else {"inventory"} if mode == "audit" else set()))
    limits = profile(value["profile"])
    # 先結構檢查，再讀分開提供的合成 caller context。
    fields(value["before"], {"scope", "epoch", "reject_before", "items", "proofs", "storage"})
    ctx = context(caller_context, value["before"], limits)
    before = state(value["before"], limits, ctx["now"])
    after = state(value["after"], limits, ctx["now"])
    require(before["scope"] == after["scope"], "scope-mismatch")
    if mode == "audit":
        require("audit" in ctx["capabilities"], "missing-capability")
        require(before == after, "audit-state-changed")
        inventory = fields(value["inventory"], {"item_ids", "complete", "reason", "scanned_count", "snapshot_digest"})
        ids = sequence(inventory["item_ids"], limits["max_scan_items"])
        for item_id in ids:
            identifier(item_id)
        all_ids = {i["item_id"] for i in before["items"]}
        require(len(set(ids)) == len(ids) and set(ids) <= all_ids, "invalid-inventory")
        require(type(inventory["complete"]) is bool
                and inventory["complete"] == (set(ids) == all_ids), "false-completeness")
        require(digest_text(inventory["snapshot_digest"]) == digest(before), "audit-snapshot-mismatch")
        require(integer(inventory["scanned_count"], 0, limits["max_scan_items"]) == len(ids), "scan-count-mismatch")
        reason = choice(inventory["reason"], {"complete", "limit", "source-unavailable", "corrupt", "not-started"})
        require((reason == "complete") == inventory["complete"], "inventory-reason-mismatch")
        if reason == "limit":
            require(len(ids) == limits["max_scan_items"], "inventory-reason-mismatch")
        if reason == "not-started":
            require(not ids, "inventory-reason-mismatch")
        return verdict
    if mode == "retention":
        _retention(value, before, after, limits, ctx)
        return verdict
    require(after["epoch"] == before["epoch"] and after["reject_before"] == before["reject_before"],
            "unexpected-floor-change")
    if mode == "continuation":
        _continuation(value, before, after, limits, ctx)
        return verdict
    require(all(p["result"]["outcome"] == "complete" for p in before["proofs"]), "pending-maintenance")
    preview = _preview(value["preview"], before, limits, ctx)
    confirmation = fields(value["confirmation"], {"principal_id", "preview_digest", "confirmed_at"})
    require(identifier(confirmation["principal_id"]) == ctx["scope"]["principal_id"], "scope-mismatch")
    require(digest_text(confirmation["preview_digest"]) == digest(preview), "preview-mismatch")
    integer(confirmation["confirmed_at"], preview["issued_at"], ctx["now"])
    require(digest(confirmation) in ctx["accepted_confirmations"], "unaccepted-confirmation")
    expected_items = _items_after(before, preview, limits, ctx["now"])
    result = value["result"]
    phases(result, preview["operation"], preview["reclaim_space"])
    if result["transaction"] != "succeeded":
        # unknown 代表這份聲明無可證明的狀態變更；不把 before 當 backend 真實現況。
        require(before == after, "uncommitted-state-claimed")
        return verdict
    require(after["items"] == expected_items, "unexpected-item-change")
    proof = {"operation_id": preview["operation_id"], "preview_digest": digest(preview),
             "operation": preview["operation"], "item_id": preview["item_id"],
             "identity_epoch": preview["identity_epoch"], "reclaim_space": preview["reclaim_space"],
             "issued_at": preview["issued_at"], "recorded_at": ctx["now"],
             "epoch": preview["epoch"], "result": copy.deepcopy(result)}
    require(after["proofs"] == before["proofs"] + [proof], "non-atomic-proof")
    _storage_after(before, after, result, limits, growth=preview["operation"] in GROWTH)
    return verdict
