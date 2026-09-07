#!/usr/bin/env python3
"""檢查 Issue #213 的離線合成 proposal cases；不授權或執行任何操作。"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata

from memory_governance_g0 import (
    ContractError, canonical, digest, digest_text, fields, integer, read_json, require,
)


CASES_VERSION = "mg1-production-cases-proposal/v0"
PROFILE_VERSION = "mg1-production-profile-proposal/v0"
POLICY = {
    "policy_id": "mg1-content-safety/v1",
    "prohibited": [
        "credentials", "pii", "private-paths", "raw-chats", "raw-logs", "raw-sessions",
        "restricted-data", "secrets", "unredacted-config",
    ],
    "unknown_action": "reject",
    "redaction": "new-candidate-and-preview",
}
PROFILE_FIELDS = {
    "max_items", "max_versions", "history_seconds", "max_payload_bytes", "max_proofs",
    "maintenance_proof_reserve", "proof_seconds", "marker_seconds", "confirmation_seconds",
    "max_scan_items", "data_limit_bytes", "maintenance_max_bytes",
}
MODEL_FIELDS = {
    "kind", "journal_copies", "temp_bytes", "growth_bytes", "warning_percent", "index_kind",
    "proof_bytes_ceiling", "witness_bytes_ceiling", "item_metadata_bytes_ceiling", "other_overhead_bytes",
}
WORKLOAD_FIELDS = {
    "case_id", "active_items", "stopped_items", "erased_markers", "versions_per_item",
    "version_bytes", "index_bytes_per_active_item", "proof_count", "witness_count",
}
READBACK_FIELDS = {
    "contract_version", "scope", "operation_id", "preview_digest", "observed_at", "result",
    "state_digest", "proof", "deleted_proofs", "deleted_markers", "managed_files",
    "external_copies", "sanitization", "space_reclaim", "storage", "related_proofs",
    "witness", "related_witnesses",
}
EXPECTED_PROFILE = {
    "max_items": 10_000,
    "max_versions": 10,
    "history_seconds": 2_592_000,
    "max_payload_bytes": 16_384,
    "max_proofs": 32_768,
    "maintenance_proof_reserve": 1_024,
    "proof_seconds": 2_592_000,
    "marker_seconds": 2_592_000,
    "confirmation_seconds": 300,
    "max_scan_items": 256,
    "data_limit_bytes": 4_294_967_296,
    "maintenance_max_bytes": 5_368_709_120,
}
FAULT_IDS = {
    "G0-ENVELOPE-01", "G0-EXTERNAL-COPIES-01", "G1-AUTH-01", "G1-CLOCK-01",
    "G1-CONTENT-01", "G1-CONTENT-02", "G1-INDEX-01", "G1-LIMIT-01",
    "G1-SENSITIVE-01", "G1-SOURCE-01", "G1-SOURCE-02", "G1-ATOMIC-01",
    "G1-AUDIT-01", "G1-AUDIT-02", "G2-COMPACT-01", "G2-ENVELOPE-01",
    "G2-ERASE-01", "G2-PRUNE-01", "G2-PRUNE-02", "G2-RETENTION-01", "G2-SPACE-01",
    "G0-RESTORE-SOURCE-01", "G1-CAPACITY-READBACK-01", "G0-RETENTION-BATCH-01",
    "G2-CONTINUATION-01", "G0-PROOF-SET-01", "G0-COMPACT-PLAN-01",
    "G0-RESTORE-CONTENT-01", "G0-WITNESS-CAPACITY-01", "G0-READBACK-FRESHNESS-01",
}
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
OPAQUE = re.compile(r"[A-Za-z0-9][-A-Za-z0-9._:]{0,63}\Z")


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


def profile(value: object) -> dict:
    value = fields(value, {"contract_version", "profile_id", "status", "profile", "model", "workloads"})
    require(value["contract_version"] == PROFILE_VERSION and value["status"] == "proposed",
            "invalid-profile-proposal")
    opaque(value["profile_id"])
    result = fields(value["profile"], PROFILE_FIELDS)
    for number in result.values():
        integer(number, 1)
    require(result == EXPECTED_PROFILE, "fixed-profile-mismatch")
    model = fields(value["model"], MODEL_FIELDS)
    require(model["kind"] == "synthetic-planning-estimate"
            and model["index_kind"] == "ordinary-current-only-projection", "invalid-profile-model")
    for key in MODEL_FIELDS - {"kind", "index_kind"}:
        integer(model[key], 1)
    require(model["witness_bytes_ceiling"] == 65_536, "fixed-profile-model-mismatch")
    workloads = value["workloads"]
    require(type(workloads) is list and 1 <= len(workloads) <= 16, "invalid-profile-workloads")
    case_ids = []
    for workload in workloads:
        workload = fields(workload, WORKLOAD_FIELDS)
        case_ids.append(opaque(workload["case_id"]))
        for key in WORKLOAD_FIELDS - {"case_id"}:
            integer(workload[key])
        require(workload["witness_count"] <= min(workload["proof_count"], result["maintenance_proof_reserve"]),
                "invalid-witness-count")
    require(len(set(case_ids)) == len(case_ids), "duplicate-profile-workload")
    return result


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


def state(value: object, expected_scope: dict, profile_limits: dict) -> dict:
    value = fields(value, {"scope", "epoch", "reject_before", "items"})
    require(scope(value["scope"], expected_scope["profile_digest"], expected_scope["policy_fingerprint"]) == expected_scope,
            "scope-mismatch")
    integer(value["epoch"], 1)
    integer(value["reject_before"])
    items = value["items"]
    require(type(items) is list and len(items) <= profile_limits["max_items"], "invalid-items")
    item_ids = []
    for item in items:
        item = fields(item, {
            "item_id", "identity_epoch", "status", "current_revision", "revision_high_water",
            "erased_at", "versions", "projection_digest",
        })
        item_ids.append(uuid(item["item_id"]))
        integer(item["identity_epoch"], 1, value["epoch"])
        status = one_of(item["status"], {"active", "stopped", "erased"}, "invalid-item-status")
        integer(item["revision_high_water"], 0)
        digest_text(item["projection_digest"])
        entries = item["versions"]
        require(type(entries) is list and len(entries) <= profile_limits["max_versions"], "invalid-versions")
        revisions = []
        for entry in entries:
            entry = fields(entry, {"revision", "version_digest"})
            revisions.append(integer(entry["revision"], 1))
            digest_text(entry["version_digest"])
        require(revisions == sorted(set(revisions)), "unordered-or-duplicate")
        if status == "erased":
            require(item["current_revision"] is None and item["erased_at"] is not None and not entries,
                    "invalid-erased-item")
            integer(item["erased_at"])
        else:
            require(item["erased_at"] is None and bool(entries), "invalid-retained-item")
            require(integer(item["current_revision"], 1) == revisions[-1]
                    and item["revision_high_water"] >= revisions[-1], "invalid-current-revision")
        if status != "active":
            require(item["projection_digest"] == digest([]), "invalid-inactive-projection")
    require(item_ids == sorted(item_ids) and len(set(item_ids)) == len(item_ids), "unordered-or-duplicate")
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
    require(coverage != "complete" or bool(value["copies"]), "empty-complete-copies")
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


def references(value: object, maximum: int, identifier=opaque) -> list:
    require(type(value) is list and len(value) <= maximum, "invalid-reference-set")
    identifiers = []
    for entry in value:
        entry = fields(entry, {"id", "digest"})
        identifiers.append(identifier(entry["id"]))
        digest_text(entry["digest"])
    require(identifiers == sorted(identifiers) and len(set(identifiers)) == len(identifiers),
            "unordered-or-duplicate")
    return value


def preview(value: object, expected_scope: dict, before: dict, after: dict, profile_limits: dict) -> dict:
    value = fields(value, {
        "contract_version", "scope", "operation_id", "nonce", "operation", "item_id",
        "acceptance_epoch", "issued_at", "expires_at", "before", "expected_after_digest",
        "candidate", "target_revisions", "target_proofs", "target_markers", "managed_files",
        "external_copies", "phases", "authority", "continuation", "storage", "compact",
    })
    require(value["contract_version"] == "mg1-preview/v1", "invalid-preview-version")
    require(scope(value["scope"], expected_scope["profile_digest"], expected_scope["policy_fingerprint"]) == expected_scope,
            "scope-mismatch")
    uuid(value["operation_id"])
    uuid(value["nonce"])
    operation = one_of(value["operation"], {
        "add", "update", "restore", "stop", "resume", "erase", "prune", "compact", "retention", "recovery",
        "continue-maintenance",
    }, "invalid-operation")
    if operation in {"compact", "retention", "recovery"}:
        require(value["item_id"] is None, "root-operation-item")
    elif value["item_id"] is not None:
        uuid(value["item_id"])
    else:
        require(operation == "continue-maintenance", "item-operation-item")
    integer(value["acceptance_epoch"], 1)
    issued = integer(value["issued_at"])
    expiry = integer(value["expires_at"], issued + 1)
    require(expiry - issued <= profile_limits["confirmation_seconds"], "invalid-preview-window")
    require(value["acceptance_epoch"] == before["epoch"]
            and issued >= before["reject_before"], "stale-preview-epoch-or-floor")
    before_binding = fields(value["before"], {"kind", "digest"})
    expected_kind = "recovery-file-snapshot" if operation == "recovery" else "logical-state"
    require(before_binding["kind"] == expected_kind, "invalid-before-kind")
    expected_before = digest(file_snapshot(value["managed_files"])) if operation == "recovery" else digest(before)
    require(digest_text(before_binding["digest"]) == expected_before, "before-digest-mismatch")
    if operation == "recovery":
        require(value["expected_after_digest"] is None, "recovery-after-digest")
    else:
        require(digest_text(value["expected_after_digest"]) == digest(after), "after-digest-mismatch")
    if operation in {"add", "update", "restore"}:
        require(value["candidate"] is not None, "missing-candidate")
        version(value["candidate"], profile_limits, expected_scope["policy_fingerprint"])
    else:
        require(value["candidate"] is None, "unexpected-candidate")
    revisions = value["target_revisions"]
    require(type(revisions) is list and len(revisions) <= profile_limits["max_versions"], "invalid-target-revisions")
    checked_revisions = [integer(revision, 1) for revision in revisions]
    require(checked_revisions == sorted(set(checked_revisions)), "unordered-or-duplicate")
    if operation == "restore":
        retained = {
            entry["revision"] for item in before["items"] if item["item_id"] == value["item_id"]
            for entry in item["versions"]
        }
        require(len(revisions) == 1 and revisions[0] in retained, "invalid-restore-source")
    else:
        require(bool(revisions) if operation in {"erase", "prune"} else not revisions, "invalid-target-revisions")
    batch_limit = 128 if operation == "retention" else 0
    references(value["target_proofs"], batch_limit, uuid)
    references(value["target_markers"], batch_limit, uuid)
    require(bool(value["target_proofs"] or value["target_markers"]) if operation == "retention"
            else not value["target_proofs"] and not value["target_markers"], "invalid-retention-targets")
    if operation == "compact":
        compact = fields(value["compact"], {"requested_pages", "page_size", "freelist_pages_before"})
        requested = integer(compact["requested_pages"], 1)
        require(integer(compact["page_size"], 1) == 4096
                and requested <= integer(compact["freelist_pages_before"], requested)
                <= profile_limits["data_limit_bytes"] // 4096,
                "invalid-compact-plan")
    else:
        require(value["compact"] is None, "unexpected-compact-plan")
    file_snapshot(value["managed_files"])
    require(any(entry["role"] == "main" for entry in value["managed_files"]), "missing-main-file")
    preflight_storage = storage(value["storage"], value["managed_files"], profile_limits)
    preflight_storage["work_budget"] = work_budget(preflight_storage["work_budget"], value["managed_files"], profile_limits)
    require(preflight_capacity_proven(preflight_storage, profile_limits), "preview-capacity-unproven")
    external_copies(value["external_copies"])
    phase = fields(value["phases"], {"content", "sanitization", "space_reclaim"})
    require(all(type(item) is str and item in {"requested", "not-requested"} for item in phase.values()),
            "invalid-phase-request")
    if operation in {"add", "update", "restore"}:
        require(phase["content"] == "requested" and phase["sanitization"] == phase["space_reclaim"] == "not-requested",
                "invalid-content-phase")
    elif operation in {"erase", "prune"}:
        require(phase["content"] == phase["sanitization"] == "requested", "missing-sanitization")
    elif operation == "compact":
        require(phase["space_reclaim"] == "requested"
                and phase["content"] == phase["sanitization"] == "not-requested", "invalid-compact-phases")
    elif operation == "continue-maintenance":
        require(phase["content"] == "not-requested"
                and bool({name for name in ("sanitization", "space_reclaim") if phase[name] == "requested"}),
                "invalid-continuation-phase")
    else:
        require(all(item == "not-requested" for item in phase.values()), "unexpected-phase-request")
    authority = ordered_unique(value["authority"], 4, lambda item: item)
    require(set(authority) <= {"readback", "content-write", "erase-content", "root-maintenance"}
            and "readback" in authority, "invalid-authority")
    if operation in {"add", "update", "restore", "stop", "resume"}:
        require("content-write" in authority, "missing-content-authority")
    if operation in {"erase", "prune"}:
        require({"erase-content", "root-maintenance"} <= set(authority), "missing-erase-authority")
    if operation in {"compact", "recovery", "retention"}:
        require("root-maintenance" in authority, "missing-maintenance-authority")
    expected_authority = {"readback", "root-maintenance"}
    if operation in {"add", "update", "restore", "stop", "resume"}:
        expected_authority = {"content-write", "readback"}
    elif operation in {"erase", "prune"} or (
        operation == "continue-maintenance" and phase["sanitization"] == "requested"
    ):
        expected_authority.add("erase-content")
    require(set(authority) == expected_authority, "unexpected-authority")
    continuation = value["continuation"]
    require((continuation is not None) == (operation == "continue-maintenance"),
            "unexpected-or-missing-continuation")
    if continuation is not None:
        continuation = fields(continuation, {"operation_id", "proof_digest", "remaining_phases"})
        uuid(continuation["operation_id"])
        digest_text(continuation["proof_digest"])
        ordered_unique(continuation["remaining_phases"], 2, lambda item: item)
        require(set(continuation["remaining_phases"]) <= {"sanitization", "space_reclaim"}
                and bool(continuation["remaining_phases"]), "invalid-continuation")
        require({name for name, requested in phase.items() if requested == "requested"}
                == set(continuation["remaining_phases"]), "continuation-phase-mismatch")
    require(len(canonical(value)) <= 262_144, "preview-too-large")
    return value


def proof(value: object, preview_value: dict | None = None, before: dict | None = None,
          after: dict | None = None) -> dict:
    value = fields(value, {
        "contract_version", "operation_id", "item_id", "identity_epoch", "acceptance_epoch",
        "before_revision", "after_revision", "recorded_at", "operation", "preview_digest",
        "before_digest", "after_digest", "projection_digest", "acceptance_evidence_id", "phase",
        "sanitization", "space_reclaim", "restore_source_revision", "target_revisions", "parent_operation_id",
        "witness_kind", "witness_digest",
    })
    require(value["contract_version"] == "mg1-operation-proof/v1", "invalid-proof-version")
    uuid(value["operation_id"])
    operation = one_of(value["operation"], {
        "add", "update", "restore", "stop", "resume", "erase", "prune", "compact", "retention", "recovery",
        "continue-maintenance",
    }, "invalid-proof-operation")
    root_operation = operation in {"compact", "retention", "recovery"} or (
        operation == "continue-maintenance" and preview_value is not None and preview_value["item_id"] is None
    )
    for key in ("identity_epoch", "before_revision", "after_revision"):
        integer(value[key])
    if root_operation:
        require(value["item_id"] is None and all(value[key] == 0 for key in ("identity_epoch", "before_revision", "after_revision")),
                "root-proof-fields")
    else:
        uuid(value["item_id"])
        integer(value["identity_epoch"], 1)
        integer(value["before_revision"])
        integer(value["after_revision"])
    integer(value["acceptance_epoch"], 1)
    integer(value["recorded_at"])
    digest_text(value["preview_digest"])
    digest_text(value["before_digest"])
    digest_text(value["after_digest"])
    if preview_value is not None:
        require(value["preview_digest"] == digest(preview_value), "proof-preview-mismatch")
        require(value["before_digest"] == digest(before), "proof-before-mismatch")
        require(value["after_digest"] == digest(after), "proof-after-mismatch")
        require(value["operation_id"] == preview_value["operation_id"]
                and value["operation"] == preview_value["operation"]
                and value["acceptance_epoch"] == preview_value["acceptance_epoch"], "proof-binding-mismatch")
        if preview_value["item_id"] is not None:
            require(value["item_id"] == preview_value["item_id"], "proof-target-mismatch")
            before_items = [item for item in before["items"] if item["item_id"] == value["item_id"]]
            after_items = [item for item in after["items"] if item["item_id"] == value["item_id"]]
            require(len(before_items) <= 1 and len(after_items) <= 1, "proof-target-mismatch")
            before_item = before_items[0] if before_items else None
            after_item = after_items[0] if after_items else None
            if operation == "add":
                require(before_item is None and after_item is not None
                        and value["identity_epoch"] == after_item["identity_epoch"], "proof-state-mismatch")
            else:
                require(before_item is not None and value["identity_epoch"] == before_item["identity_epoch"],
                        "proof-state-mismatch")
            expected_before_revision = 0 if before_item is None or before_item["status"] == "erased" else before_item["current_revision"]
            expected_after_revision = 0 if after_item is None or after_item["status"] == "erased" else after_item["current_revision"]
            expected_projection = digest([]) if after_item is None else after_item["projection_digest"]
            require(value["before_revision"] == expected_before_revision
                    and value["after_revision"] == expected_after_revision
                    and value["projection_digest"] == expected_projection, "proof-state-mismatch")
        else:
            projection = [
                {"item_id": item["item_id"], "projection_digest": item["projection_digest"]}
                for item in after["items"] if item["status"] == "active"
            ]
            require(value["projection_digest"] == digest(projection), "root-projection-mismatch")
        expected_targets = preview_value["target_revisions"] if operation in {"erase", "prune"} else []
        require(value["target_revisions"] == expected_targets, "proof-revision-target-mismatch")
        if operation == "restore":
            require(value["restore_source_revision"] == preview_value["target_revisions"][0],
                    "restore-source-mismatch")
    digest_text(value["projection_digest"])
    opaque(value["acceptance_evidence_id"])
    one_of(value["phase"], {"sanitization-pending", "space-reclaim-pending", "complete"}, "invalid-proof-phase")
    one_of(value["sanitization"], {"not-requested", "pending", "complete"}, "invalid-proof-maintenance")
    one_of(value["space_reclaim"], {"not-requested", "pending", "complete"}, "invalid-proof-maintenance")
    revisions = value["target_revisions"]
    require(type(revisions) is list and len(revisions) <= 10, "invalid-proof-target-revisions")
    checked_revisions = [integer(revision, 1) for revision in revisions]
    require(checked_revisions == sorted(set(checked_revisions)), "unordered-or-duplicate")
    if operation in {"erase", "prune"}:
        require(bool(revisions), "missing-proof-target-revisions")
    else:
        require(not revisions, "unexpected-proof-target-revisions")
    if operation == "restore":
        integer(value["restore_source_revision"], 1)
    else:
        require(value["restore_source_revision"] is None, "unexpected-restore-source")
    if operation == "continue-maintenance":
        uuid(value["parent_operation_id"])
    else:
        require(value["parent_operation_id"] is None, "unexpected-parent-operation")
    witness_kind = value["witness_kind"]
    witness_digest = value["witness_digest"]
    require((witness_kind is None) == (witness_digest is None), "invalid-proof-witness")
    if witness_kind is not None:
        one_of(witness_kind, {"retention", "continuation", "compact"}, "invalid-proof-witness")
        digest_text(witness_digest)
        require((witness_kind == operation or (operation == "continue-maintenance" and witness_kind == "continuation")),
                "invalid-proof-witness")
    if operation in {"erase", "prune"}:
        require(value["sanitization"] != "not-requested", "missing-proof-sanitization")
    if operation == "compact":
        require(value["space_reclaim"] != "not-requested" and value["sanitization"] == "not-requested",
                "invalid-compact-proof-phase")
    if operation in {"add", "update", "restore", "stop", "resume", "retention", "recovery"}:
        require(value["phase"] == "complete"
                and value["sanitization"] == value["space_reclaim"] == "not-requested",
                "unexpected-proof-maintenance")
    if preview_value is not None:
        require(all((value[name] != "not-requested") == (preview_value["phases"][name] == "requested")
                    for name in ("sanitization", "space_reclaim")), "proof-preview-phase-mismatch")
    if value["phase"] == "sanitization-pending":
        require(value["sanitization"] == "pending", "invalid-proof-phase")
    elif value["phase"] == "space-reclaim-pending":
        require(value["sanitization"] != "pending" and value["space_reclaim"] == "pending", "invalid-proof-phase")
    elif value["phase"] == "complete":
        require("pending" not in {value["sanitization"], value["space_reclaim"]}, "invalid-proof-phase")
    require(len(canonical(value)) <= 2048, "proof-too-large")
    return value


WITNESS_VERSION = "mg1-maintenance-witness/v1"


def witness(value: object, checked_proof: dict | None = None, limits: dict | None = None) -> dict | None:
    if value is None:
        require(checked_proof is None or checked_proof["witness_kind"] is None, "missing-proof-witness")
        return None
    require(checked_proof is None or checked_proof["witness_kind"] is not None, "unexpected-proof-witness")
    common = {"contract_version", "kind", "operation_id"}
    require(type(value) is dict, "invalid-witness")
    kind = value.get("kind")
    variants = {
        "retention": {"target_proofs", "target_markers", "before_proof_set_digest",
                      "after_proof_set_digest_without_self", "before_marker_set_digest", "after_marker_set_digest"},
        "continuation": {"parent_before_record", "parent_after_record_digest", "remaining_phases",
                         "before_proof_set_digest", "after_proof_set_digest_without_self"},
        "compact": {"plan", "freelist_pages_after", "actual_pages_reclaimed",
                    "file_snapshot_before_digest"},
    }
    require(type(kind) is str and kind in variants, "invalid-witness")
    value = fields(value, common | variants[kind])
    require(value["contract_version"] == WITNESS_VERSION, "invalid-witness-version")
    uuid(value["operation_id"])
    if checked_proof is not None:
        require(value["kind"] == checked_proof["witness_kind"]
                and value["operation_id"] == checked_proof["operation_id"]
                and digest(value) == checked_proof["witness_digest"], "witness-digest-mismatch")
    require(len(canonical(value)) <= 65_536, "witness-too-large")
    if kind == "retention":
        references(value["target_proofs"], 128, uuid)
        references(value["target_markers"], 128, uuid)
        require(bool(value["target_proofs"] or value["target_markers"]), "empty-witness-targets")
        for key in ("before_proof_set_digest", "after_proof_set_digest_without_self",
                    "before_marker_set_digest", "after_marker_set_digest"):
            digest_text(value[key])
    elif kind == "continuation":
        fields(value["parent_before_record"], {"proof", "witness"})
        require(len(canonical(value["parent_before_record"])) <= 8192, "parent-record-too-large")
        digest_text(value["parent_after_record_digest"])
        phases = ordered_unique(value["remaining_phases"], 2, lambda item: item)
        require(set(phases) <= {"sanitization", "space_reclaim"} and bool(phases), "invalid-witness-phases")
        digest_text(value["before_proof_set_digest"])
        digest_text(value["after_proof_set_digest_without_self"])
    else:
        plan = fields(value["plan"], {"requested_pages", "page_size", "freelist_pages_before"})
        active_limits = limits or EXPECTED_PROFILE
        requested = integer(plan["requested_pages"], 1)
        require(integer(plan["page_size"], 1) == 4096
                and requested <= integer(plan["freelist_pages_before"], requested)
                <= active_limits["data_limit_bytes"] // 4096, "invalid-compact-plan")
        digest_text(value["file_snapshot_before_digest"])
        if checked_proof is not None and checked_proof["phase"] != "complete":
            require(value["freelist_pages_after"] is None and value["actual_pages_reclaimed"] is None,
                    "invalid-pending-compact-witness")
        else:
            after_pages = integer(value["freelist_pages_after"])
            actual = integer(value["actual_pages_reclaimed"])
            require(0 <= actual <= requested and after_pages == plan["freelist_pages_before"] - actual,
                    "compact-reclaim-mismatch")
    return value


def record(value: object) -> dict:
    value = fields(value, {"proof", "witness"})
    checked = proof(value["proof"])
    witness(value["witness"], checked)
    return value


def record_digest(value: object) -> str:
    checked = record(value)
    return digest({"proof_digest": digest(checked["proof"]), "witness_digest": checked["proof"]["witness_digest"]})


def record_set_digest(values: object, excluded_id: str | None = None) -> str:
    require(type(values) is list and len(values) <= 33_792, "invalid-proof-records")
    leaves = []
    ids = []
    for entry in values:
        checked = record(entry)
        operation_id = checked["proof"]["operation_id"]
        ids.append(operation_id)
        if operation_id != excluded_id:
            leaves.append({"operation_id": operation_id, "record_digest": record_digest(checked)})
    require(len(set(ids)) == len(ids), "duplicate-proof-record")
    require(sum(entry["proof"]["witness_kind"] is not None for entry in values) <= 1_024,
            "witness-count-limit")
    return digest(sorted(leaves, key=lambda item: item["operation_id"]))


def marker_set_digest(values: object) -> str:
    require(type(values) is list and len(values) <= 10_000, "invalid-marker-records")
    leaves = []
    ids = []
    for entry in values:
        entry = fields(entry, {"item_id", "identity_epoch", "status", "current_revision", "revision_high_water",
                               "erased_at", "versions", "projection_digest"})
        marker_id = uuid(entry["item_id"])
        ids.append(marker_id)
        leaves.append({"id": marker_id, "digest": digest(entry)})
    require(len(set(ids)) == len(ids), "duplicate-marker-record")
    return digest(sorted(leaves, key=lambda item: item["id"]))


def readback(value: object, expected_scope: dict, preview_value: dict, before: dict, after: dict,
             checked_proof: dict, limits: dict, related_proofs: list | None = None,
             related_witnesses: list | None = None) -> dict:
    value = fields(value, READBACK_FIELDS)
    require(value["contract_version"] == "mg1-readback/v1", "invalid-readback-version")
    require(scope(value["scope"], expected_scope["profile_digest"], expected_scope["policy_fingerprint"]) == expected_scope,
            "scope-mismatch")
    require(uuid(value["operation_id"]) == preview_value["operation_id"], "readback-operation-mismatch")
    require(digest_text(value["preview_digest"]) == digest(preview_value), "readback-preview-mismatch")
    integer(value["observed_at"], preview_value["issued_at"])
    result = one_of(value["result"], {
        "applied", "not-applied", "state-unknown", "integrity-failed", "committed-but-not-adoptable",
        "committed-capacity-unproven",
    }, "invalid-readback-result")
    if value["state_digest"] is not None:
        digest_text(value["state_digest"])
    references(value["deleted_proofs"], 128, uuid)
    references(value["deleted_markers"], 128, uuid)
    file_snapshot(value["managed_files"])
    require(any(entry["role"] == "main" for entry in value["managed_files"]), "missing-main-file")
    measured_storage = storage(value["storage"], value["managed_files"], limits)
    require(measured_storage["work_budget"] is None, "postflight-work-budget")
    require(measured_storage["filesystem_id"] == preview_value["storage"]["filesystem_id"],
            "readback-filesystem-mismatch")
    readback_copies = external_copies(value["external_copies"])
    one_of(value["sanitization"], {"not-requested", "pending", "complete"}, "invalid-readback-maintenance")
    one_of(value["space_reclaim"], {"not-requested", "pending", "complete"}, "invalid-readback-maintenance")
    require(type(value["related_proofs"]) is list and value["related_proofs"] == (related_proofs or []),
            "invalid-related-proofs")
    require(type(value["related_witnesses"]) is list
            and value["related_witnesses"] == (related_witnesses or [])
            and len(value["related_witnesses"]) == len(value["related_proofs"]), "invalid-related-witnesses")
    witness(value["witness"], checked_proof, limits)
    for related_proof, related_witness in zip(value["related_proofs"], value["related_witnesses"]):
        witness(related_witness, proof(related_proof), limits)
    if result == "applied":
        require(value["proof"] == checked_proof and value["state_digest"] == digest(after), "incomplete-applied-readback")
        require(value["deleted_proofs"] == preview_value["target_proofs"]
                and value["deleted_markers"] == preview_value["target_markers"], "readback-delete-set-mismatch")
        preview_copies = preview_value["external_copies"]
        readback_copies = value["external_copies"]
        require({key: readback_copies[key] for key in ("coverage", "copies")}
                == {key: preview_copies[key] for key in ("coverage", "copies")}
                and readback_copies["observed_at"] >= preview_copies["observed_at"], "readback-binding-mismatch")
        require(postflight_capacity_proven(measured_storage, limits), "storage-capacity-unproven")
    elif result == "committed-capacity-unproven":
        require(value["proof"] == checked_proof and value["state_digest"] == digest(after)
                and not postflight_capacity_proven(measured_storage, limits), "invalid-capacity-readback")
    elif result == "not-applied":
        require(value["proof"] is None and value["state_digest"] == digest(before), "invalid-not-applied-readback")
    else:
        require(value["proof"] is None or value["proof"] == checked_proof, "invalid-readback-proof")
    if value["proof"] is not None:
        require(all(value[name] == checked_proof[name] for name in ("sanitization", "space_reclaim")),
                "readback-maintenance-mismatch")
        require(checked_proof["recorded_at"] <= readback_copies["observed_at"] <= value["observed_at"],
                "external-copy-observation-time")
    require(len(canonical(value)) <= 262_144, "readback-too-large")
    return value


def confirmation(value: object, expected_scope: dict, preview_value: dict) -> tuple[dict, int]:
    value = fields(value, {
        "contract_version", "scope", "operation_id", "nonce", "preview_digest", "confirmed_at", "expires_at",
        "host_evidence_id",
    })
    require(value["contract_version"] == "mg1-confirmation/v1", "invalid-confirmation-version")
    require(scope(value["scope"], expected_scope["profile_digest"], expected_scope["policy_fingerprint"]) == expected_scope,
            "scope-mismatch")
    require(uuid(value["operation_id"]) == preview_value["operation_id"]
            and uuid(value["nonce"]) == preview_value["nonce"]
            and digest_text(value["preview_digest"]) == digest(preview_value)
            and value["expires_at"] == preview_value["expires_at"], "confirmation-binding-mismatch")
    confirmed = integer(value["confirmed_at"], preview_value["issued_at"])
    require(confirmed < value["expires_at"], "confirmation-expired")
    opaque(value["host_evidence_id"])
    require(len(canonical(value)) <= 4096, "confirmation-too-large")
    return value, confirmed


def continuation_example(value: object, expected_scope: dict, limits: dict) -> None:
    value = fields(value, {
        "before_state", "after_state", "parent_before", "preview", "confirmation", "parent_after", "readback",
        "proof_records_before", "proof_records_after",
    })
    before = state(value["before_state"], expected_scope, limits)
    after = state(value["after_state"], expected_scope, limits)
    require(before == after, "continuation-state-changed")
    parent_before = proof(value["parent_before"])
    parent_after = proof(value["parent_after"])
    records_before = value["proof_records_before"]
    records_after = value["proof_records_after"]
    require(type(records_before) is list and type(records_after) is list, "invalid-proof-records")
    require(len(records_before) == 1, "continuation-parent-record-mismatch")
    parent_before_record = fields(records_before[0], {"proof", "witness"})
    require(parent_before_record["proof"] == parent_before, "continuation-parent-record-mismatch")
    parent_before_witness = witness(parent_before_record["witness"], parent_before, limits)
    require(parent_before["operation"] in {"erase", "prune", "compact"}
            and "pending" in {parent_before["sanitization"], parent_before["space_reclaim"]},
            "invalid-continuation-parent")
    immutable_fields = set(parent_before) - {"phase", "sanitization", "space_reclaim", "witness_digest"}
    require(all(parent_before[key] == parent_after[key] for key in immutable_fields), "parent-binding-mutated")
    parent_after_record = next((entry for entry in records_after if type(entry) is dict
                                and entry.get("proof") == parent_after), None)
    require(parent_after_record is not None, "continuation-parent-record-mismatch")
    parent_after_record = fields(parent_after_record, {"proof", "witness"})
    parent_after_witness = witness(parent_after_record["witness"], parent_after, limits)
    if parent_before["operation"] == "compact":
        require(parent_before_witness is not None and parent_after_witness is not None
                and parent_before_witness["kind"] == parent_after_witness["kind"] == "compact"
                and all(parent_before_witness[key] == parent_after_witness[key]
                        for key in ("contract_version", "kind", "operation_id", "plan", "file_snapshot_before_digest")),
                "parent-binding-mutated")
    else:
        require(parent_before_witness is None and parent_after_witness is None, "parent-binding-mutated")
    require(parent_after["phase"] == "complete" and "pending" not in {
        parent_after["sanitization"], parent_after["space_reclaim"]
    }, "invalid-continuation-parent")
    preview_value = preview(value["preview"], expected_scope, before, after, limits)
    require(preview_value["operation"] == "continue-maintenance"
            and preview_value["continuation"] is not None
            and preview_value["continuation"]["operation_id"] == parent_before["operation_id"]
            and preview_value["continuation"]["proof_digest"] == digest(parent_before), "continuation-parent-mismatch")
    require(preview_value["item_id"] == parent_before["item_id"], "continuation-target-mismatch")
    pending = [
        name for name in ("sanitization", "space_reclaim") if parent_before[name] == "pending"
    ]
    require(preview_value["continuation"]["remaining_phases"] == pending, "continuation-phase-mismatch")
    require(all(parent_after[name] == ("complete" if name in pending else parent_before[name])
                for name in ("sanitization", "space_reclaim")), "unauthorized-parent-phase-change")
    if "sanitization" in pending:
        require({"erase-content", "root-maintenance"} <= set(preview_value["authority"]),
                "missing-continuation-authority")
    confirmation_value, confirmed = confirmation(value["confirmation"], expected_scope, preview_value)
    require(confirmed >= max(parent_before["recorded_at"], before["reject_before"]),
            "continuation-before-parent")
    continuation_readback = fields(value["readback"], READBACK_FIELDS)
    child = proof(continuation_readback["proof"], preview_value, before, after)
    require(child["item_id"] == parent_before["item_id"]
            and child["identity_epoch"] == parent_before["identity_epoch"], "continuation-target-mismatch")
    require(child["phase"] == "complete" and all(
        child[name] == ("complete" if name in pending else "not-requested")
        for name in ("sanitization", "space_reclaim")
    ), "continuation-child-phase-mismatch")
    require(child["operation_id"] != parent_before["operation_id"]
            and child["parent_operation_id"] == parent_before["operation_id"]
            and child["acceptance_evidence_id"] == confirmation_value["host_evidence_id"], "invalid-continuation-child")
    child_witness = witness(continuation_readback["witness"], child, limits)
    require(child_witness is not None and child_witness["parent_before_record"] == parent_before_record
            and child_witness["parent_after_record_digest"] == record_digest(parent_after_record)
            and child_witness["remaining_phases"] == pending, "continuation-witness-mismatch")
    require(record_set_digest(records_before) == child_witness["before_proof_set_digest"]
            and record_set_digest(records_after, child["operation_id"])
            == child_witness["after_proof_set_digest_without_self"], "continuation-proof-set-mismatch")
    require(record_set_digest([records_before[0]]) == child_witness["before_proof_set_digest"],
            "continuation-proof-reconstruction-mismatch")
    require(records_after == [parent_after_record,
                              {"proof": child, "witness": child_witness}], "continuation-records-mismatch")
    readback(continuation_readback, expected_scope, preview_value, before, after, child, limits,
             [parent_after], [parent_after_witness])
    require(continuation_readback["related_witnesses"] == [parent_after_witness], "continuation-related-witness-mismatch")
    require(confirmation_value["host_evidence_id"] == child["acceptance_evidence_id"], "confirmation-proof-mismatch")
    require(confirmed <= child["recorded_at"] < preview_value["expires_at"]
            and continuation_readback["observed_at"] >= confirmed
            and child["recorded_at"] >= confirmed
            and continuation_readback["observed_at"] >= child["recorded_at"], "invalid-binding-time")


def candidate_transition(before: dict, after: dict, checked_preview: dict) -> None:
    candidate = checked_preview["candidate"]
    if candidate is None:
        return
    target_id = checked_preview["item_id"]
    before_items = [item for item in before["items"] if item["item_id"] == target_id]
    after_items = [item for item in after["items"] if item["item_id"] == target_id]
    require(after["epoch"] == before["epoch"] and after["reject_before"] == before["reject_before"],
            "candidate-root-state-mutated")
    require([item for item in before["items"] if item["item_id"] != target_id]
            == [item for item in after["items"] if item["item_id"] != target_id],
            "candidate-nontarget-mutated")
    if checked_preview["operation"] == "add":
        require(not before_items and len(after_items) == 1, "candidate-after-binding-mismatch")
        before_versions, before_current = {}, None
    else:
        require(len(before_items) == len(after_items) == 1, "candidate-after-binding-mismatch")
        require(all(before_items[0][key] == after_items[0][key]
                    for key in ("identity_epoch", "status", "erased_at")), "candidate-target-mutated")
        before_versions = {entry["revision"]: entry["version_digest"] for entry in before_items[0]["versions"]}
        before_current = before_items[0]["current_revision"]
    after_item = after_items[0]
    after_versions = {entry["revision"]: entry["version_digest"] for entry in after_item["versions"]}
    require(set(after_versions) == set(before_versions) | {candidate["revision"]}
            and after_item["current_revision"] == candidate["revision"]
            and candidate["revision"] > (before_items[0]["revision_high_water"] if before_items else 0)
            and after_item["revision_high_water"] == candidate["revision"]
            and after_versions.get(candidate["revision"]) == digest(candidate), "candidate-after-binding-mismatch")
    if checked_preview["operation"] == "add":
        require(after_item["status"] == "active", "candidate-target-mutated")
    if after_item["status"] == "active":
        projection = sorted([
            {"cue": cue, "summary": candidate["summary"], "revision": candidate["revision"]}
            for cue in candidate["cues"]
        ], key=lambda row: row["cue"])
        require(after_item["projection_digest"] == digest(projection), "candidate-projection-mismatch")
    else:
        require(after_item["status"] == "stopped" and after_item["projection_digest"] == digest([]),
                "candidate-projection-mismatch")
    for revision, version_digest in before_versions.items():
        if revision != before_current:
            require(after_versions.get(revision) == version_digest, "candidate-history-mutated")


def standard_example(value: object, expected_scope: dict, limits: dict, operation: str) -> tuple[dict, dict, dict, dict]:
    value = fields(value, {"before_state", "after_state", "preview", "confirmation", "readback"}
                   | ({"source_version"} if operation == "restore" else set()))
    before = state(value["before_state"], expected_scope, limits)
    after = state(value["after_state"], expected_scope, limits)
    checked_preview = preview(value["preview"], expected_scope, before, after, limits)
    require(checked_preview["operation"] == operation, "unexpected-example-operation")
    candidate_transition(before, after, checked_preview)
    confirmation_value, confirmed = confirmation(value["confirmation"], expected_scope, checked_preview)
    readback_value = fields(value["readback"], READBACK_FIELDS)
    checked_proof = proof(readback_value["proof"], checked_preview, before, after)
    require(checked_proof["acceptance_evidence_id"] == confirmation_value["host_evidence_id"],
            "confirmation-proof-mismatch")
    readback(readback_value, expected_scope, checked_preview, before, after, checked_proof, limits)
    require(confirmed <= checked_proof["recorded_at"] < checked_preview["expires_at"]
            and readback_value["observed_at"] >= checked_proof["recorded_at"], "invalid-binding-time")
    return before, after, checked_preview, checked_proof


def retention_example(value: object, expected_scope: dict, limits: dict) -> None:
    value = fields(value, {"before_state", "after_state", "preview", "confirmation", "readback",
                           "proof_records_before", "proof_records_after"})
    before, after, checked_preview, checked_proof = standard_example(
        {key: value[key] for key in ("before_state", "after_state", "preview", "confirmation", "readback")},
        expected_scope, limits, "retention")
    require(after["epoch"] == before["epoch"] + 1 and after["reject_before"] > before["reject_before"],
            "retention-floor-update-mismatch")
    before_retained = [item for item in before["items"] if item["status"] != "erased"]
    after_retained = [item for item in after["items"] if item["status"] != "erased"]
    require(before_retained == after_retained, "retention-retained-state-mutated")
    readback_value = fields(value["readback"], READBACK_FIELDS)
    checked_witness = witness(readback_value["witness"], checked_proof, limits)
    require(checked_witness is not None and checked_witness["target_proofs"] == checked_preview["target_proofs"]
            and checked_witness["target_markers"] == checked_preview["target_markers"], "retention-witness-target-mismatch")
    before_records = value["proof_records_before"]
    after_records = value["proof_records_after"]
    require(type(before_records) is list and type(after_records) is list, "invalid-proof-records")
    for entry in before_records + after_records:
        record(entry)
    before_by_id = {entry["proof"]["operation_id"]: entry for entry in before_records}
    after_ids = {entry["proof"]["operation_id"] for entry in after_records}
    require(len(before_by_id) == len(before_records), "duplicate-proof-record")
    for target in checked_witness["target_proofs"]:
        require(target["id"] in before_by_id and target["id"] not in after_ids
                and target["digest"] == record_digest(before_by_id[target["id"]]), "retention-proof-target-mismatch")
    require(record_set_digest(before_records) == checked_witness["before_proof_set_digest"]
            and record_set_digest(after_records, checked_proof["operation_id"])
            == checked_witness["after_proof_set_digest_without_self"], "retention-proof-set-mismatch")
    reconstructed_records = [entry for entry in after_records if entry["proof"]["operation_id"] != checked_proof["operation_id"]]
    reconstructed_records.extend(before_by_id[target["id"]] for target in checked_witness["target_proofs"])
    require(record_set_digest(reconstructed_records) == checked_witness["before_proof_set_digest"],
            "retention-proof-reconstruction-mismatch")
    require(after_records == [{"proof": checked_proof, "witness": checked_witness}], "retention-records-mismatch")
    before_markers = [item for item in before["items"] if item["status"] == "erased"]
    after_markers = [item for item in after["items"] if item["status"] == "erased"]
    before_marker_ids = {item["item_id"]: item for item in before_markers}
    after_marker_ids = {item["item_id"] for item in after_markers}
    for target in checked_witness["target_markers"]:
        require(target["id"] in before_marker_ids and target["id"] not in after_marker_ids
                and target["digest"] == digest(before_marker_ids[target["id"]]), "retention-marker-target-mismatch")
    require(marker_set_digest(before_markers) == checked_witness["before_marker_set_digest"]
            and marker_set_digest(after_markers) == checked_witness["after_marker_set_digest"],
            "retention-marker-set-mismatch")
    reconstructed_markers = after_markers + [before_marker_ids[target["id"]] for target in checked_witness["target_markers"]]
    require(marker_set_digest(reconstructed_markers) == checked_witness["before_marker_set_digest"],
            "retention-marker-reconstruction-mismatch")


def compact_example(value: object, expected_scope: dict, limits: dict) -> None:
    before, after, checked_preview, checked_proof = standard_example(value, expected_scope, limits, "compact")
    require(before == after, "compact-state-changed")
    readback_value = fields(value["readback"], READBACK_FIELDS)
    checked_witness = witness(readback_value["witness"], checked_proof, limits)
    require(checked_witness is not None and checked_witness["plan"] == checked_preview["compact"],
            "compact-witness-plan-mismatch")
    require(checked_witness["file_snapshot_before_digest"] == digest(checked_preview["managed_files"]),
            "compact-file-snapshot-mismatch")
    before_pages = checked_witness["plan"]["freelist_pages_before"]
    after_pages = checked_witness["freelist_pages_after"]
    actual = checked_witness["actual_pages_reclaimed"]
    require(0 <= actual <= checked_witness["plan"]["requested_pages"]
            and actual == before_pages - after_pages, "compact-reclaim-mismatch")


def restore_example(value: object, expected_scope: dict, limits: dict) -> None:
    before, after, checked_preview, checked_proof = standard_example(value, expected_scope, limits, "restore")
    source = version(value["source_version"], limits, expected_scope["policy_fingerprint"])
    target_id = checked_preview["item_id"]
    source_revision = checked_preview["target_revisions"][0]
    before_items = [item for item in before["items"] if item["item_id"] == target_id]
    require(len(before_items) == 1, "restore-source-version-mismatch")
    before_item = before_items[0]
    require(any(entry["revision"] == source_revision and entry["version_digest"] == digest(source)
                for entry in before_item["versions"]), "restore-source-version-mismatch")
    candidate = checked_preview["candidate"]
    require(candidate["revision"] > source["revision"], "restore-revision-mismatch")
    for key in ("kind", "body", "summary", "cues", "applicability", "procedure"):
        require(candidate[key] == source[key], "restore-content-mismatch")
    require(len(candidate["provenance"]) == len(source["provenance"]), "restore-content-mismatch")
    for source_entry, candidate_entry in zip(source["provenance"], candidate["provenance"]):
        require(all(candidate_entry[key] == source_entry[key] for key in (
            "source_id", "kind", "reference", "source_revision", "source_digest"
        )), "restore-content-mismatch")
        if source_entry["kind"] == "repo-artifact":
            require(source_entry["attestation"] is None and candidate_entry["attestation"] is None,
                    "restore-attestation-mismatch")
        else:
            source_attestation = source_entry["attestation"]
            candidate_attestation = candidate_entry["attestation"]
            require(candidate_attestation["scope_digest"] == digest(expected_scope)
                    and candidate_attestation["policy_fingerprint"] == expected_scope["policy_fingerprint"]
                    and candidate_attestation["binding_token"] != source_attestation["binding_token"]
                    and candidate["created_at"] <= candidate_attestation["accepted_at"]
                    <= candidate["validation"]["verified_at"] <= checked_preview["issued_at"],
                    "restore-attestation-mismatch")
    require(candidate["validation"]["evidence_id"] != source["validation"]["evidence_id"],
            "restore-validation-reused")
    after_items = [item for item in after["items"] if item["item_id"] == target_id]
    require(len(after_items) == 1, "restore-after-version-mismatch")
    after_item = after_items[0]
    require(any(entry["revision"] == candidate["revision"] and entry["version_digest"] == digest(candidate)
                for entry in after_item["versions"]), "restore-after-version-mismatch")
    require(checked_proof["restore_source_revision"] == source_revision, "restore-source-mismatch")


def maximum_width_witness(value: object, limits: dict) -> None:
    checked = witness(value, limits=limits)
    require(checked is not None and checked["kind"] == "retention"
            and len(checked["target_proofs"]) == len(checked["target_markers"]) == 128,
            "invalid-maximum-witness")


def evaluate(cases: object, profile_value: object) -> dict:
    limits = profile(profile_value)
    cases = fields(cases, {
        "contract_version", "status", "synthetic_only", "production_parameters_accepted", "runtime_proven",
        "operation_authorized", "source_note", "version_examples", "maximum_width_proof_example",
        "fault_cases", "binding_examples", "continuation_example", "retention_example", "compact_example",
        "restore_example", "maximum_width_witness_example",
    })
    require(cases["contract_version"] == CASES_VERSION and cases["status"] == "oracle-only-not-executed", "invalid-cases-status")
    require(cases["synthetic_only"] is True and all(cases[key] is False for key in (
        "production_parameters_accepted", "runtime_proven", "operation_authorized",
    )), "self-acceptance")
    text(cases["source_note"])
    raw_versions = cases["version_examples"]
    require(type(raw_versions) is list and len(raw_versions) == 2, "invalid-version-examples")
    binding = fields(cases["binding_examples"], {
        "policy", "scope", "before_state", "after_state", "preview", "confirmation", "readback",
    })
    policy_value = fields(binding["policy"], set(POLICY))
    require(policy_value == POLICY, "invalid-policy")
    policy_fingerprint = digest(POLICY)
    expected_scope = scope(binding["scope"], digest(limits), policy_fingerprint)
    checked_versions = [version(item, limits, policy_fingerprint) for item in raw_versions]
    require({item["kind"] for item in checked_versions} == {"fact", "procedure"}, "missing-version-kind")
    before = state(binding["before_state"], expected_scope, limits)
    after = state(binding["after_state"], expected_scope, limits)
    checked_preview = preview(binding["preview"], expected_scope, before, after, limits)
    candidate_transition(before, after, checked_preview)
    confirmation_value, confirmed = confirmation(binding["confirmation"], expected_scope, checked_preview)
    proof(cases["maximum_width_proof_example"])
    normal_readback = fields(binding["readback"], READBACK_FIELDS)
    checked_proof = proof(normal_readback["proof"], checked_preview, before, after)
    require(checked_proof["acceptance_evidence_id"] == confirmation_value["host_evidence_id"],
            "confirmation-proof-mismatch")
    readback(normal_readback, expected_scope, checked_preview, before, after, checked_proof, limits)
    require(normal_readback["witness"] is None and normal_readback["related_witnesses"] == [],
            "unexpected-normal-witness")
    require(confirmed <= checked_proof["recorded_at"] < checked_preview["expires_at"]
            and normal_readback["observed_at"] >= confirmed
            and checked_proof["recorded_at"] >= confirmed
            and normal_readback["observed_at"] >= checked_proof["recorded_at"], "invalid-binding-time")
    continuation_example(cases["continuation_example"], expected_scope, limits)
    retention_example(cases["retention_example"], expected_scope, limits)
    compact_example(cases["compact_example"], expected_scope, limits)
    restore_example(cases["restore_example"], expected_scope, limits)
    maximum_width_witness(cases["maximum_width_witness_example"], limits)
    faults = cases["fault_cases"]
    require(type(faults) is list and len(faults) == len(FAULT_IDS), "invalid-fault-oracles")
    actual_ids = []
    for fault in faults:
        fault = fields(fault, {"case_id", "trigger", "expected", "required_evidence"})
        actual_ids.append(text(fault["case_id"]))
        text(fault["trigger"])
        text(fault["expected"])
        text(fault["required_evidence"])
    require(len(set(actual_ids)) == len(actual_ids) and set(actual_ids) == FAULT_IDS, "invalid-fault-oracles")
    return {
        "contract_version": CASES_VERSION,
        "synthetic_cases_checked": 1,
        "fault_oracles_documented": len(FAULT_IDS),
        "production_parameters_accepted": False,
        "runtime_proven": False,
        "operation_authorized": False,
        "write_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", help="明確的合成 cases JSON regular file")
    parser.add_argument("--profile", required=True, help="明確的 profile JSON regular file")
    args = parser.parse_args()
    try:
        result = evaluate(read_json(args.cases), read_json(args.profile))
    except ContractError as error:
        print(json.dumps({"status": "rejected", "code": str(error), "operation_authorized": False}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
