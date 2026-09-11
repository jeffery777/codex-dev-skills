"""MG1 G1 嚴格資料契約。純驗證不授權、不接觸 backend；G2 操作拒絕。"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata

MAX_NUMBER = 2**53 - 1
MAX_ENVELOPE = 262_144
G1_OPERATIONS = frozenset({"add", "update", "restore", "stop", "resume"})
SCHEMA_OPERATIONS = G1_OPERATIONS | {"erase", "prune", "compact", "retention", "recovery", "continue-maintenance"}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
OPAQUE = re.compile(r"[A-Za-z0-9][-A-Za-z0-9._:]{0,63}\Z")
POLICY = {
    "policy_id": "mg1-content-safety/v1",
    "prohibited": ["credentials", "pii", "private-paths", "raw-chats", "raw-logs",
                   "raw-sessions", "restricted-data", "secrets", "unredacted-config"],
    "unknown_action": "reject", "redaction": "new-candidate-and-preview",
}
DEFAULT_PROFILE = {
    "max_items": 10000, "max_versions": 10, "history_seconds": 2592000,
    "max_payload_bytes": 16384, "max_proofs": 32768, "maintenance_proof_reserve": 1024,
    "proof_seconds": 2592000, "marker_seconds": 2592000, "confirmation_seconds": 300,
    "max_scan_items": 256, "data_limit_bytes": 4294967296, "maintenance_max_bytes": 5368709120,
}

class ContractError(ValueError):
    """固定診斷碼；不可回顯不可信內容、路徑或來源。"""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ContractError(code)


def fields(value: object, expected: set[str]) -> dict:
    require(type(value) is dict and set(value) == expected, "invalid-fields")
    return value


def integer(value: object, minimum: int = 0, maximum: int = MAX_NUMBER) -> int:
    require(type(value) is int and minimum <= value <= maximum, "invalid-integer")
    return value


def digest_text(value: object) -> str:
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "invalid-digest")
    return value


def canonical(value: object, maximum: int = MAX_ENVELOPE) -> bytes:
    """深度、節點與輸出皆有界；拒絕 float、非字串 key 與循環。"""
    nodes = 0
    def check(item, depth):
        nonlocal nodes
        nodes += 1
        require(depth <= 32 and nodes <= maximum, "json-complexity")
        if type(item) is dict:
            require(all(type(k) is str for k in item), "invalid-json")
            for key, child in item.items():
                require(len(key) <= maximum, "input-too-large")
                check(child, depth + 1)
        elif type(item) is list:
            require(len(item) <= maximum, "input-too-large")
            for child in item:
                check(child, depth + 1)
        elif type(item) is str:
            require(len(item) <= maximum, "input-too-large")
        elif type(item) is int:
            integer(item)
        else:
            require(item is None or type(item) is bool, "invalid-json")
    try:
        check(value, 0)
        output = bytearray()
        encoder = json.JSONEncoder(sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        for chunk in encoder.iterencode(value):
            output.extend(chunk.encode("utf-8"))
            require(len(output) <= maximum, "encoding-too-large")
        return bytes(output)
    except (UnicodeError, TypeError, RecursionError) as exc:
        raise ContractError("invalid-json") from exc


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def decode(data: bytes, maximum: int = MAX_ENVELOPE) -> object:
    require(type(data) is bytes and len(data) <= maximum, "input-too-large")
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "duplicate-key")
            result[key] = value
        return result
    def reject(_value):
        raise ContractError("invalid-json")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=reject, parse_float=reject)
        canonical(value, maximum)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, ContractError):
            raise
        raise ContractError("invalid-json") from exc


def profile(value: object) -> dict:
    fields(value, set(DEFAULT_PROFILE))
    for number in value.values():
        integer(number, 1)
    require(all(value[k] == v for k, v in DEFAULT_PROFILE.items()
                if k not in {"data_limit_bytes", "maintenance_max_bytes"}), "unsupported-profile")
    require(value["data_limit_bytes"] in {268435456, 1073741824, 4294967296}
            and value["maintenance_max_bytes"] == value["data_limit_bytes"] * 5 // 4, "unsupported-profile")
    return value


def content_digest(value: dict) -> str:
    return digest({k: v for k, v in value.items() if k not in {"validation", "created_at", "retired_at"}})

def uuid(value: object) -> str:
    require(type(value) is str and UUID.fullmatch(value) is not None, "invalid-uuid")
    return value

def opaque(value: object) -> str:
    require(type(value) is str and OPAQUE.fullmatch(value) is not None, "invalid-opaque-id")
    return value

def utf8(value: str) -> bytes:
    try:
        return value.encode("utf-8")
    except UnicodeError as exc:
        raise ContractError("invalid-text") from exc

def text(value: object, maximum: int | None = None) -> str:
    require(type(value) is str and value != "", "invalid-text")
    encoded = utf8(value)
    if maximum is not None:
        require(len(encoded) <= maximum, "text-too-large")
    return value

def one_of(value: object, allowed: set[str], code: str = "invalid-enum") -> str:
    require(type(value) is str and value in allowed, code)
    return value

def ordered_unique(values: object, maximum: int, validator, code: str = "invalid-list") -> list:
    require(type(values) is list and len(values) <= maximum, code)
    checked = [validator(value) for value in values]
    require(all(type(value) is str for value in checked), "invalid-list")
    require(checked == sorted(checked) and len(set(checked)) == len(checked), "unordered-or-duplicate")
    return checked

def scope(value: object, profile_digest: str, policy_fingerprint: str) -> dict:
    value = fields(value, {
        "principal_id", "root_id", "repository_id", "schema_fingerprint", "profile_digest",
        "policy_fingerprint",
    })
    uuid(value["principal_id"])
    uuid(value["root_id"])
    opaque(value["repository_id"])
    digest_text(value["schema_fingerprint"])
    require(digest_text(value["profile_digest"]) == profile_digest, "profile-digest-mismatch")
    require(digest_text(value["policy_fingerprint"]) == policy_fingerprint, "policy-fingerprint-mismatch")
    return value

def version(value: object, profile_limits: dict, policy_fingerprint: str | None = None) -> dict:
    value = fields(value, {
        "revision", "created_at", "retired_at", "kind", "body", "summary", "cues",
        "applicability", "procedure", "provenance", "validation",
    })
    integer(value["revision"], 1)
    integer(value["created_at"])
    if value["retired_at"] is not None:
        integer(value["retired_at"], value["created_at"])
    kind = one_of(value["kind"], {"fact", "procedure"}, "invalid-version-kind")
    text(value["body"])
    text(value["summary"], 1024)
    cues = value["cues"]
    require(type(cues) is list and 1 <= len(cues) <= 16 and all(type(cue) is str for cue in cues),
            "invalid-cues")
    for cue in cues:
        text(cue, 128)
        require(cue == unicodedata.normalize("NFC", cue).casefold().strip() and cue != "", "invalid-cues")
    require(len(set(cues)) == len(cues), "invalid-cues")
    applicability = fields(value["applicability"], {"repository_id", "paths", "conditions"})
    opaque(applicability["repository_id"])
    paths = applicability["paths"]
    require(type(paths) is list and len(paths) <= 16 and all(type(path) is str and path for path in paths),
            "invalid-path")
    for path in paths:
        require("\x00" not in path and not path.startswith("/") and "//" not in path
                and all(part not in {"", ".", ".."} for part in path.split("/")), "invalid-path")
    conditions = applicability["conditions"]
    require(type(conditions) is list and len(conditions) <= 16
            and all(type(condition) is str and condition for condition in conditions), "invalid-conditions")
    provenance = value["provenance"]
    require(type(provenance) is list and 1 <= len(provenance) <= 8, "invalid-provenance")
    source_ids = []
    for source in provenance:
        source = fields(source, {"source_id", "kind", "reference", "source_revision", "source_digest", "attestation"})
        source_ids.append(opaque(source["source_id"]))
        source_kind = one_of(source["kind"], {"repo-artifact", "human-confirmed-decision"}, "invalid-source-kind")
        if source_kind == "repo-artifact":
            reference = fields(source["reference"], {"repository_id", "path"})
            opaque(reference["repository_id"])
            path = text(reference["path"])
            require("\x00" not in path and not path.startswith("/") and "//" not in path
                    and all(part not in {"", ".", ".."} for part in path.split("/")), "invalid-path")
            require(type(source["source_revision"]) is str and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source["source_revision"]) is not None,
                    "invalid-source-revision")
            require(source["attestation"] is None, "invalid-repository-attestation")
        else:
            fields(source["reference"], {"evidence_id"})
            opaque(source["reference"]["evidence_id"])
            opaque(source["source_revision"])
            attestation = fields(source["attestation"], {
                "scope_digest", "policy_fingerprint", "issuer_fingerprint", "accepted_at", "binding_token",
            })
            for key in ("scope_digest", "policy_fingerprint", "issuer_fingerprint"):
                digest_text(attestation[key])
            integer(attestation["accepted_at"])
            require(type(attestation["binding_token"]) is str, "invalid-attestation-token")
            try:
                token_bytes = attestation["binding_token"].encode("ascii")
            except UnicodeError as exc:
                raise ContractError("invalid-attestation-token") from exc
            require(1 <= len(token_bytes) <= 2048, "invalid-attestation-token")
        digest_text(source["source_digest"])
    require(len(set(source_ids)) == len(source_ids), "unordered-or-duplicate")
    if kind == "fact":
        require(value["procedure"] is None, "fact-procedure")
    else:
        procedure = fields(value["procedure"], {
            "prerequisites", "steps", "success_evidence", "invalidation_conditions",
        })
        for key in ("prerequisites", "steps", "success_evidence", "invalidation_conditions"):
            entries = procedure[key]
            require(type(entries) is list and 1 <= len(entries) <= 16, "invalid-procedure")
            if key == "success_evidence":
                require(all(type(entry) is str and entry in source_ids for entry in entries), "invalid-procedure-evidence")
            else:
                require(all(type(entry) is str and entry != "" for entry in entries), "invalid-procedure")
    validation = fields(value["validation"], {
        "content_digest", "evidence_id", "verified_at", "verifier_fingerprint", "policy_fingerprint", "eligibility",
    })
    material = {key: item for key, item in value.items() if key not in {"validation", "created_at", "retired_at"}}
    require(digest_text(validation["content_digest"]) == digest(material), "content-digest-mismatch")
    opaque(validation["evidence_id"])
    integer(validation["verified_at"])
    digest_text(validation["verifier_fingerprint"])
    require(digest_text(validation["policy_fingerprint"]) == (policy_fingerprint or validation["policy_fingerprint"]),
            "validation-policy-mismatch")
    require(validation["eligibility"] == "eligible", "invalid-eligibility")
    require(len(canonical(value)) <= profile_limits["max_payload_bytes"], "version-too-large")
    return value

def file_snapshot(value: object) -> list:
    require(type(value) is list and len(value) <= 32, "invalid-file-snapshot")
    file_ids = []
    for entry in value:
        entry = fields(entry, {"file_id", "role", "bytes", "sha256"})
        file_ids.append(opaque(entry["file_id"]))
        one_of(entry["role"], {"main", "journal", "temp", "coordination-lock"}, "invalid-file-role")
        integer(entry["bytes"])
        digest_text(entry["sha256"])
    require(file_ids == sorted(file_ids) and len(set(file_ids)) == len(file_ids), "unordered-or-duplicate")
    return value

def external_copies(value: object) -> dict:
    value = fields(value, {"coverage", "observed_at", "copies"})
    coverage = one_of(value["coverage"], {"complete", "partial", "unknown"}, "invalid-copy-coverage")
    integer(value["observed_at"])
    require(type(value["copies"]) is list and len(value["copies"]) <= 32, "invalid-copies")
    copy_ids = []
    for entry in value["copies"]:
        entry = fields(entry, {"copy_id", "kind", "observation"})
        copy_ids.append(opaque(entry["copy_id"]))
        one_of(entry["kind"], {"native-memory", "export", "backup", "host-history", "other"}, "invalid-copy-kind")
        one_of(entry["observation"], {"known-present", "unknown"}, "invalid-copy-observation")
    require(copy_ids == sorted(copy_ids) and len(set(copy_ids)) == len(copy_ids), "unordered-or-duplicate")
    # coverage 的真偽只由 host inventory 證明；validator 不從空清單推導 complete。
    return value

def storage(value: object, managed_files: list, limits: dict) -> dict:
    value = fields(value, {"filesystem_id", "managed_bytes", "available_work_bytes", "coverage", "work_budget"})
    opaque(value["filesystem_id"])
    managed_bytes = integer(value["managed_bytes"])
    available_work_bytes = integer(value["available_work_bytes"])
    one_of(value["coverage"], {"complete", "partial", "unknown"}, "invalid-storage-coverage")
    total = 0
    for entry in managed_files:
        total += integer(entry["bytes"])
        require(total <= 2**53 - 1, "invalid-integer")
    require(managed_bytes == total, "storage-byte-mismatch")
    return value

def work_budget(value: object, managed_files: list, limits: dict) -> dict:
    value = fields(value, {
        "qualification_id", "file_snapshot_digest", "journal_bound_bytes", "temp_bound_bytes",
        "growth_bound_bytes", "required_work_bytes",
    })
    opaque(value["qualification_id"])
    require(digest_text(value["file_snapshot_digest"]) == digest(managed_files), "work-budget-file-mismatch")
    bounds = [integer(value[key]) for key in ("journal_bound_bytes", "temp_bound_bytes", "growth_bound_bytes")]
    total = sum(bounds)
    require(total <= 2**53 - 1, "invalid-integer")
    pages = total // 4096 + (1 if total % 4096 else 0)
    require(pages <= (2**53 - 1) // 4096, "invalid-integer")
    required = pages * 4096
    require(integer(value["required_work_bytes"]) == required,
            "invalid-work-budget")
    return value

def preflight_capacity_proven(measurement: dict, limits: dict) -> bool:
    if measurement["work_budget"] is None:
        return False
    budget = measurement["work_budget"]
    growth = budget["growth_bound_bytes"]
    require(measurement["managed_bytes"] + growth <= 2**53 - 1, "invalid-integer")
    return (measurement["coverage"] == "complete"
            and measurement["managed_bytes"] + growth <= limits["data_limit_bytes"]
            and budget["required_work_bytes"] <= limits["maintenance_max_bytes"]
            and measurement["available_work_bytes"] >= budget["required_work_bytes"])


def postflight_capacity_proven(measurement: dict, limits: dict) -> bool:
    return measurement["coverage"] == "complete" and measurement["managed_bytes"] <= limits["data_limit_bytes"]


def copies_match(observation: dict, original: dict) -> bool:
    return (all(observation[key] == original[key] for key in ("coverage", "copies"))
            and observation["observed_at"] >= original["observed_at"])


def copies_digest(value: dict) -> str:
    """有界副本比較 commitment，不保留原集合或把 unknown 升為 complete。"""
    external_copies(value)
    return digest({key: value[key] for key in ("coverage", "copies")})


def readback_basis(value: object, recorded_at: int) -> dict:
    fields(value, {"scope_digest", "binding_digest", "copies_digest", "copies_observed_at", "readback_until"})
    for key in ("scope_digest", "binding_digest", "copies_digest"):
        digest_text(value[key])
    integer(value["copies_observed_at"], 0, recorded_at)
    require(integer(value["readback_until"]) == integer(recorded_at + DEFAULT_PROFILE["proof_seconds"]),
            "invalid-readback-window")
    return value


def basis_matches(record: dict, scope_value: dict, copies: dict, observed_at: int) -> bool:
    """純資料比較；真實 root/source/read 權限由 core 另驗，不能以此建立授權。"""
    basis = readback_basis(record["readback_basis"], record["recorded_at"])
    return (basis["scope_digest"] == digest(scope_value)
            and record["recorded_at"] <= copies["observed_at"] <= observed_at < basis["readback_until"]
            and copies["observed_at"] >= basis["copies_observed_at"]
            and copies_digest(copies) == basis["copies_digest"])


def validate_version(value: object, expected_scope: dict, limits: dict, *, candidate: bool = False) -> dict:
    canonical(value, limits["max_payload_bytes"])
    version(value, limits, expected_scope["policy_fingerprint"])
    require(value["applicability"]["repository_id"] == expected_scope["repository_id"], "source-scope-mismatch")
    require(value["created_at"] <= value["validation"]["verified_at"], "invalid-validation-time")
    if candidate:
        require(value["retired_at"] is None, "retired-candidate")
    for source in value["provenance"]:
        if source["kind"] == "repo-artifact":
            require(source["reference"]["repository_id"] == expected_scope["repository_id"], "source-scope-mismatch")
        else:
            att = source["attestation"]
            require(att["scope_digest"] == digest(expected_scope)
                    and att["policy_fingerprint"] == expected_scope["policy_fingerprint"], "attestation-binding")
            require(value["created_at"] <= att["accepted_at"] <= value["validation"]["verified_at"], "attestation-time")
    return value


def restore_content(candidate: dict, retained: dict) -> None:
    for key in ("kind", "body", "summary", "cues", "applicability", "procedure"):
        require(candidate[key] == retained[key], "restore-content-mismatch")
    require(len(candidate["provenance"]) == len(retained["provenance"]), "restore-source-mismatch")
    for new, old in zip(candidate["provenance"], retained["provenance"]):
        require({k: v for k, v in new.items() if k != "attestation"}
                == {k: v for k, v in old.items() if k != "attestation"}, "restore-source-mismatch")
        if new["kind"] == "human-confirmed-decision":
            require(new["attestation"]["binding_token"] != old["attestation"]["binding_token"], "restore-stale-attestation")
    require(candidate["validation"]["evidence_id"] != retained["validation"]["evidence_id"], "restore-stale-validation")


def projection(value: dict, status: str) -> list[dict]:
    return ([{"cue": cue, "summary": value["summary"], "revision": value["revision"]}
             for cue in sorted(value["cues"])] if status == "active" else [])


def g1_preview(value: object, expected_scope: dict, limits: dict) -> dict:
    canonical(value)
    fields(value, {
        "contract_version", "scope", "operation_id", "nonce", "operation", "item_id",
        "acceptance_epoch", "issued_at", "expires_at", "before", "expected_after_digest",
        "candidate", "target_revisions", "target_proofs", "target_markers", "managed_files",
        "external_copies", "phases", "authority", "continuation", "storage", "compact",
    })
    require(value["contract_version"] == "mg1-preview/v1", "invalid-preview-version")
    scope(value["scope"], expected_scope["profile_digest"], expected_scope["policy_fingerprint"])
    require(value["scope"] == expected_scope, "scope-mismatch")
    for key in ("operation_id", "nonce", "item_id"):
        uuid(value[key])
    operation = g1_operation(value["operation"])
    integer(value["acceptance_epoch"], 1)
    issued = integer(value["issued_at"])
    expiry = integer(value["expires_at"], issued + 1)
    require(expiry - issued <= limits["confirmation_seconds"], "invalid-preview-window")
    fields(value["before"], {"kind", "digest"})
    require(value["before"]["kind"] == "logical-state", "invalid-before-kind")
    digest_text(value["before"]["digest"])
    digest_text(value["expected_after_digest"])
    if operation in {"add", "update", "restore"}:
        validate_version(value["candidate"], expected_scope, limits, candidate=True)
        require(value["candidate"]["validation"]["verified_at"] <= issued, "future-validation")
    else:
        require(value["candidate"] is None, "unexpected-candidate")
    targets = value["target_revisions"]
    require(type(targets) is list, "invalid-target-revisions")
    if operation == "restore":
        require(len(targets) == 1, "invalid-restore-source")
        integer(targets[0], 1)
    else:
        require(targets == [], "unexpected-target-revisions")
    require(value["target_proofs"] == [] and value["target_markers"] == []
            and value["continuation"] is None and value["compact"] is None, "maintenance-unavailable")
    require(value["authority"] == ["content-write", "readback"], "invalid-authority")
    require(value["phases"] == {
        "content": "requested" if value["candidate"] is not None else "not-requested",
        "sanitization": "not-requested", "space_reclaim": "not-requested",
    }, "invalid-phases")
    file_snapshot(value["managed_files"])
    require(sum(f["role"] == "main" for f in value["managed_files"]) == 1, "missing-main-file")
    storage(value["storage"], value["managed_files"], limits)
    work_budget(value["storage"]["work_budget"], value["managed_files"], limits)
    require(preflight_capacity_proven(value["storage"], limits), "preview-capacity-unproven")
    external_copies(value["external_copies"])
    require(value["external_copies"]["observed_at"] <= issued, "future-observation")
    return value


def confirmation(value: object, preview_value: dict, now: int) -> dict:
    canonical(value, 4096)
    fields(value, {"contract_version", "scope", "operation_id", "nonce", "preview_digest",
                   "confirmed_at", "expires_at", "host_evidence_id"})
    require(value["contract_version"] == "mg1-confirmation/v1", "invalid-confirmation-version")
    integer(value["expires_at"])
    for key in ("scope", "operation_id", "nonce", "expires_at"):
        require(value[key] == preview_value[key], "confirmation-binding")
    require(digest_text(value["preview_digest"]) == digest(preview_value), "confirmation-binding")
    opaque(value["host_evidence_id"])
    confirmed = integer(value["confirmed_at"])
    require(preview_value["issued_at"] <= confirmed <= integer(now) < value["expires_at"], "expired")
    return value


def g1_proof(value: object, preview_value: dict | None = None, confirmation_value: dict | None = None) -> dict:
    canonical(value, 2048)
    require(type(value) is dict, "invalid-fields")
    family = one_of(value.get("contract_version"), {"mg1-operation-proof/v1", "mg1-operation-proof/v2"},
                    "invalid-proof-version")
    fields(value, {
        "contract_version", "operation_id", "item_id", "identity_epoch", "acceptance_epoch",
        "before_revision", "after_revision", "recorded_at", "operation", "preview_digest",
        "before_digest", "after_digest", "projection_digest", "acceptance_evidence_id", "phase",
        "sanitization", "space_reclaim", "restore_source_revision", "target_revisions",
        "parent_operation_id", "witness_kind", "witness_digest",
    } | ({"readback_basis"} if family == "mg1-operation-proof/v2" else set()))
    uuid(value["operation_id"])
    uuid(value["item_id"])
    op = g1_operation(value["operation"])
    integer(value["identity_epoch"], 1)
    integer(value["acceptance_epoch"], value["identity_epoch"])
    before = integer(value["before_revision"])
    after = integer(value["after_revision"], 1)
    integer(value["recorded_at"])
    if family == "mg1-operation-proof/v2":
        basis = readback_basis(value["readback_basis"], value["recorded_at"])
        if preview_value is not None:
            require(basis["scope_digest"] == digest(preview_value["scope"])
                    and basis["copies_digest"] == copies_digest(preview_value["external_copies"])
                    and basis["copies_observed_at"] == preview_value["external_copies"]["observed_at"],
                    "proof-basis-mismatch")
    require((before == 0 and after == 1) if op == "add" else
            (before >= 1 and (after > before if op in {"update", "restore"} else after == before)),
            "proof-revision-mismatch")
    for key in ("preview_digest", "before_digest", "after_digest", "projection_digest"):
        digest_text(value[key])
    opaque(value["acceptance_evidence_id"])
    require(value["phase"] == "complete" and value["sanitization"] == value["space_reclaim"] == "not-requested",
            "invalid-proof-phase")
    require(value["target_revisions"] == [] and value["parent_operation_id"] is None
            and value["witness_kind"] is None and value["witness_digest"] is None, "maintenance-unavailable")
    if op == "restore":
        integer(value["restore_source_revision"], 1, before)
    else:
        require(value["restore_source_revision"] is None, "unexpected-restore-source")
    if preview_value is not None:
        p = preview_value
        require(all(value[k] == p[k] for k in ("operation_id", "item_id", "operation", "acceptance_epoch"))
                and value["preview_digest"] == digest(p) and value["before_digest"] == p["before"]["digest"]
                and value["after_digest"] == p["expected_after_digest"], "proof-binding-mismatch")
        require(p["issued_at"] <= value["recorded_at"] < p["expires_at"], "proof-time-mismatch")
        if op == "restore":
            require(value["restore_source_revision"] == p["target_revisions"][0], "restore-source-mismatch")
    if confirmation_value is not None:
        require(value["acceptance_evidence_id"] == confirmation_value["host_evidence_id"]
                and value["recorded_at"] >= confirmation_value["confirmed_at"], "proof-acceptance-mismatch")
    return value


def g1_readback(value: object, expected_scope: dict, limits: dict, preview_value: dict | None = None) -> dict:
    canonical(value)
    fields(value, {"contract_version", "scope", "operation_id", "preview_digest", "observed_at", "result",
                   "state_digest", "proof", "related_proofs", "deleted_proofs", "deleted_markers", "managed_files",
                   "storage", "external_copies", "sanitization", "space_reclaim", "witness", "related_witnesses"})
    family = one_of(value["contract_version"], {"mg1-readback/v1", "mg1-readback/v2"}, "invalid-readback-version")
    require(value["scope"] == expected_scope, "scope-mismatch")
    uuid(value["operation_id"])
    digest_text(value["preview_digest"])
    integer(value["observed_at"])
    result = one_of(value["result"], {"applied", "not-applied", "state-unknown", "integrity-failed",
                                    "committed-but-not-adoptable", "committed-capacity-unproven"})
    if value["state_digest"] is not None:
        digest_text(value["state_digest"])
    require(all(value[k] == [] for k in ("related_proofs", "deleted_proofs", "deleted_markers", "related_witnesses"))
            and value["witness"] is None, "maintenance-unavailable")
    require(value["sanitization"] == value["space_reclaim"] == "not-requested", "maintenance-unavailable")
    file_snapshot(value["managed_files"])
    storage(value["storage"], value["managed_files"], limits)
    require(value["storage"]["work_budget"] is None, "post-work-budget")
    external_copies(value["external_copies"])
    require(value["external_copies"]["observed_at"] <= value["observed_at"], "future-observation")
    record = value["proof"]
    if record is not None:
        g1_proof(record, preview_value)
        require(record["contract_version"] == ("mg1-operation-proof/v2" if family == "mg1-readback/v2"
                                                else "mg1-operation-proof/v1"), "readback-proof-version")
        if family == "mg1-readback/v2":
            require(record["readback_basis"]["scope_digest"] == digest(expected_scope), "readback-proof-mismatch")
        require(record["operation_id"] == value["operation_id"]
                and record["preview_digest"] == value["preview_digest"]
                and record["recorded_at"] <= value["external_copies"]["observed_at"], "readback-proof-mismatch")
    if result in {"applied", "committed-but-not-adoptable", "committed-capacity-unproven"}:
        require(record is not None and value["state_digest"] == record["after_digest"], "readback-state-mismatch")
        if family == "mg1-readback/v2":
            require(basis_matches(record, expected_scope, value["external_copies"], value["observed_at"]),
                    "readback-copy-binding")
    if result == "applied":
        require(postflight_capacity_proven(value["storage"], limits)
                and sum(f["role"] == "main" for f in value["managed_files"]) == 1, "readback-capacity-unproven")
        if family == "mg1-readback/v1":
            require(preview_value is not None
                    and copies_match(value["external_copies"], preview_value["external_copies"]), "readback-copy-binding")
    elif result == "committed-capacity-unproven":
        require(not postflight_capacity_proven(value["storage"], limits), "invalid-capacity-readback")
    if preview_value is not None:
        require(value["preview_digest"] == digest(preview_value)
                and value["operation_id"] == preview_value["operation_id"]
                and value["storage"]["filesystem_id"] == preview_value["storage"]["filesystem_id"], "readback-binding")
    if result == "not-applied":
        require(record is None and preview_value is not None
                and value["state_digest"] == preview_value["before"]["digest"], "not-applied-unproven")
    return value


def g1_operation(value: object) -> str:
    """v1 schema 保留 G2 enum；本 validator 只驗證已實作 G1 subset。"""
    one_of(value, SCHEMA_OPERATIONS, "invalid-operation")
    require(value in G1_OPERATIONS, "capability-unavailable")
    return value
