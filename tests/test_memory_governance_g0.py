from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "memory-governance-g0"
sys.path.insert(0, str(ROOT / "scripts"))

import memory_governance_g0 as g0  # noqa: E402


SCOPE = {"principal_id": "synthetic-principal", "root_id": "synthetic-root"}
PROFILE = {
    "max_items": 10,
    "max_versions": 4,
    "history_seconds": 5_000,
    "max_payload_bytes": 1_000,
    "max_proofs": 10,
    "proof_seconds": 500,
    "confirmation_seconds": 60,
    "max_scan_items": 10,
    "budget_bytes": 100_000,
    "reserve_bytes": 10_000,
    "maintenance_proof_reserve": 2,
    "marker_seconds": 200,
}
STORAGE = {"file_bytes": 8_000, "free_bytes": 64_000, "reclaimable_bytes": 2_000}
NOW = 1_000


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def version(revision: int, *, created_at: int, suffix: str, retired_at: int | None = None) -> dict:
    return {
        "revision": revision,
        "created_at": created_at,
        "retired_at": retired_at,
        "body": f"synthetic: body {suffix}",
        "summary": f"synthetic: summary {suffix}",
        "cues": [f"synthetic-cue-{suffix}"],
    }


def state(*, items: list[dict], proofs: list[dict] | None = None, epoch: int = 1,
          reject_before: int = 0, storage: dict | None = None) -> dict:
    return {
        "scope": copy.deepcopy(SCOPE),
        "epoch": epoch,
        "reject_before": reject_before,
        "items": copy.deepcopy(items),
        "proofs": copy.deepcopy(proofs or []),
        "storage": copy.deepcopy(storage or STORAGE),
    }


def item(*, status: str = "active", versions: list[dict] | None = None) -> dict:
    versions = copy.deepcopy(versions or [version(1, created_at=900, suffix="one")])
    current = versions[-1]["revision"]
    return {
        "item_id": "synthetic-item",
        "identity_epoch": 1,
        "erased_at": None,
        "status": status,
        "current_revision": current,
        "indexed_revision": current if status == "active" else None,
        "versions": versions,
    }


def projection(before: dict, preview: dict, result: dict, *, now: int) -> dict:
    """Independent expected-state projection for the synthetic test cases."""
    after = copy.deepcopy(before)
    operation = preview["operation"]
    if operation != "compact":
        target = next((entry for entry in after["items"]
                       if entry["item_id"] == preview["item_id"]), None)
        if operation == "add":
            after["items"].append({
                "item_id": preview["item_id"], "identity_epoch": preview["identity_epoch"],
                "erased_at": None, "status": "active", "current_revision": 1,
                "indexed_revision": 1, "versions": [copy.deepcopy(preview["next_version"])],
            })
        elif operation in {"update", "restore"}:
            if target["versions"]:
                target["versions"][-1]["retired_at"] = now
                target["versions"].append(copy.deepcopy(preview["next_version"]))
                target["current_revision"] = preview["next_version"]["revision"]
                target["indexed_revision"] = target["current_revision"] if target["status"] == "active" else None
        elif operation == "stop":
            target["status"], target["indexed_revision"] = "stopped", None
        elif operation == "resume":
            target["status"], target["indexed_revision"] = "active", target["current_revision"]
        elif operation == "erase-content":
            target["status"], target["indexed_revision"], target["versions"] = "erased", None, []
            target["erased_at"] = now
        elif operation == "prune-history":
            target["versions"] = [entry for entry in target["versions"]
                                  if entry["revision"] not in preview["erase_revisions"]]
    after["proofs"].append({
        "operation_id": preview["operation_id"], "preview_digest": g0.digest(preview),
        "operation": operation, "item_id": preview["item_id"],
        "identity_epoch": preview["identity_epoch"], "reclaim_space": preview["reclaim_space"],
        "issued_at": preview["issued_at"], "recorded_at": now, "epoch": preview["epoch"],
        "result": copy.deepcopy(result),
    })
    return after


def rebind(case: dict, context: dict, *, preview: bool = True,
           confirmation: bool = True, retention: bool = True,
           continuation: bool = True) -> tuple[dict, dict]:
    """Rebind only public digest commitments after a deliberate fixture mutation."""
    case, context = copy.deepcopy(case), copy.deepcopy(context)
    context["before_digest"] = g0.digest(case["before"])
    context["profile_digest"] = g0.digest(case["profile"])
    if case.get("mode") == "maintenance" and preview:
        case["preview"]["before_digest"] = g0.digest(case["before"])
        case["preview"]["profile_digest"] = g0.digest(case["profile"])
    if case.get("mode") == "maintenance" and confirmation:
        case["confirmation"]["preview_digest"] = g0.digest(case["preview"])
        context["accepted_confirmations"] = [g0.digest(case["confirmation"])]
    if case.get("mode") == "continuation" and continuation:
        acceptance = {
            "before_digest": g0.digest(case["before"]), "after_digest": g0.digest(case["after"]),
            "profile_digest": g0.digest(case["profile"]),
            "operation_id": case["operation_id"], "result": case["result"],
            "confirmed_at": case["confirmed_at"],
        }
        context["accepted_continuations"] = [g0.digest(acceptance)]
    if case.get("mode") == "retention" and retention:
        transition = {
            "before_digest": g0.digest(case["before"]), "after_digest": g0.digest(case["after"]),
            "profile_digest": g0.digest(case["profile"]), "confirmed_at": case["confirmed_at"],
        }
        context["accepted_retention"] = [g0.digest(transition)]
    return case, context


def maintenance_case(operation: str) -> tuple[dict, dict, dict]:
    before_item = item()
    if operation == "resume":
        before_item = item(status="stopped")
    if operation in {"restore", "prune-history"}:
        before_item = item(versions=[version(1, created_at=900, suffix="one", retired_at=950),
                                     version(2, created_at=950, suffix="two")])
    before = state(items=[before_item])
    next_version = None
    restore_revision = None
    erase_revisions: list[int] = []
    managed_files: list[str] = []
    reclaim_space = False
    item_id: str | None = "synthetic-item"
    expected_revision: int | None = before_item["current_revision"]
    if operation == "add":
        item_id, expected_revision = "synthetic-added", None
        next_version = version(1, created_at=NOW, suffix="added")
    elif operation == "update":
        next_version = version(2, created_at=NOW, suffix="updated")
    elif operation == "restore":
        next_version = version(3, created_at=NOW, suffix="one")
        restore_revision = 1
    elif operation in {"erase-content", "prune-history"}:
        erase_revisions = [entry["revision"] for entry in before_item["versions"]]
        if operation == "prune-history":
            erase_revisions = [1]
        managed_files = ["main", "fts-shadow", "wal", "journal", "temp"]
    elif operation == "compact":
        item_id, expected_revision = None, None
        # Root maintenance is deliberately outside any item identity epoch.
        # The preview is completed below after its common fields are assembled.
        managed_files = ["main", "fts-shadow", "wal", "journal", "temp"]
        reclaim_space = True
    result = {
        "transaction": "succeeded", "sanitization": "not-requested",
        "compaction": "not-requested", "outcome": "complete",
    }
    if operation in {"erase-content", "prune-history"}:
        result["sanitization"] = "succeeded"
    if operation == "compact":
        result["compaction"] = "succeeded"
    preview = {
        "scope": copy.deepcopy(SCOPE), "operation_id": f"synthetic-{operation}-request",
        "nonce": f"synthetic-{operation}-nonce", "issued_at": 990, "expires_at": 1_010,
        "epoch": 1, "operation": operation, "item_id": item_id, "identity_epoch": 1,
        "expected_revision": expected_revision, "next_version": next_version,
        "restore_revision": restore_revision, "erase_revisions": erase_revisions,
        "managed_files": managed_files, "unmanaged_copies": [], "reclaim_space": reclaim_space,
        "before_digest": "0" * 64, "profile_digest": "0" * 64,
    }
    if operation == "compact":
        preview["identity_epoch"] = None
    after = projection(before, preview, result, now=NOW)
    if operation == "compact":
        after["storage"] = {"file_bytes": 7_000, "free_bytes": 65_000, "reclaimable_bytes": 1_000}
    case = {
        "contract_version": g0.VERSION, "case_id": f"synthetic-{operation}-case",
        "mode": "maintenance", "profile": copy.deepcopy(PROFILE), "before": before,
        "after": after, "preview": preview,
        "confirmation": {"principal_id": SCOPE["principal_id"], "preview_digest": "0" * 64,
                         "confirmed_at": NOW},
        "result": result,
    }
    context = {
        "contract_version": g0.VERSION, "scope": copy.deepcopy(SCOPE), "now": NOW,
        "before_digest": "0" * 64, "profile_digest": "0" * 64,
        "accepted_confirmations": [], "accepted_retention": [], "accepted_continuations": [],
        "capabilities": ["audit", "item-write", "erase-content", "root-maintenance"],
    }
    case, context = rebind(case, context)
    expected = projection(case["before"], case["preview"], case["result"], now=NOW)
    if operation == "compact":
        expected["storage"] = {
            "file_bytes": 7_000, "free_bytes": 65_000, "reclaimable_bytes": 1_000,
        }
    case["after"] = expected
    # The test projection is authoritative for this test; production internals are not used.
    return case, context, expected


def rebase_maintenance(case: dict, context: dict, before: dict, *, now: int) -> tuple[dict, dict]:
    """Bind a hand-built request to a supplied synthetic pre-state without production projections."""
    case, context = copy.deepcopy(case), copy.deepcopy(context)
    case["before"] = copy.deepcopy(before)
    case["preview"].update({
        "epoch": before["epoch"], "issued_at": now - 10, "expires_at": now + 10,
    })
    case["confirmation"]["confirmed_at"] = now
    context["now"] = now
    case["after"] = projection(case["before"], case["preview"], case["result"], now=now)
    case, context = rebind(case, context)
    case["after"] = projection(case["before"], case["preview"], case["result"], now=now)
    return case, context


def continuation_case(before: dict, result: dict, *, now: int,
                      storage: dict | None = None) -> tuple[dict, dict]:
    after = copy.deepcopy(before)
    pending = after["proofs"][-1]
    pending["result"] = copy.deepcopy(result)
    pending["recorded_at"] = now
    if storage is not None:
        after["storage"] = copy.deepcopy(storage)
    case = {
        "contract_version": g0.VERSION, "case_id": f"synthetic-continuation-{now}",
        "mode": "continuation", "profile": copy.deepcopy(PROFILE),
        "before": copy.deepcopy(before), "after": after,
        "operation_id": pending["operation_id"], "result": copy.deepcopy(result),
        "confirmed_at": now,
    }
    context = {
        "contract_version": g0.VERSION, "scope": copy.deepcopy(SCOPE), "now": now,
        "before_digest": "0" * 64, "profile_digest": "0" * 64,
        "accepted_confirmations": [], "accepted_retention": [], "accepted_continuations": [],
        "capabilities": ["audit", "item-write", "erase-content", "root-maintenance"],
    }
    return rebind(case, context)


def retention_case(before: dict, after: dict, *, now: int,
                   confirmed_at: int | None = None) -> tuple[dict, dict]:
    case = {
        "contract_version": g0.VERSION, "case_id": f"synthetic-retention-{now}", "mode": "retention",
        "profile": copy.deepcopy(PROFILE), "before": copy.deepcopy(before), "after": copy.deepcopy(after),
        "confirmed_at": now if confirmed_at is None else confirmed_at,
    }
    context = {
        "contract_version": g0.VERSION, "scope": copy.deepcopy(SCOPE), "now": now,
        "before_digest": "0" * 64, "profile_digest": "0" * 64,
        "accepted_confirmations": [], "accepted_retention": [], "accepted_continuations": [],
        "capabilities": ["audit", "item-write", "erase-content", "root-maintenance"],
    }
    return rebind(case, context)


def completed_proof(number: int) -> dict:
    return {
        "operation_id": f"synthetic-proof-{number}", "preview_digest": "0" * 64,
        "operation": "update", "item_id": "synthetic-item", "identity_epoch": 1,
        "reclaim_space": False, "issued_at": 700, "recorded_at": 800, "epoch": 1,
        "result": {"transaction": "succeeded", "sanitization": "not-requested",
                   "compaction": "not-requested", "outcome": "complete"},
    }


class MemoryGovernanceG0Tests(unittest.TestCase):
    def assert_conformant(self, case: dict, context: dict | None) -> dict:
        result = g0.validate_case(case, context)
        self.assertEqual({
            "contract_version": g0.VERSION, "case_id": case["case_id"], "status": "conformant",
            "operation_authorized": False, "runtime_proven": False, "write_performed": False,
        }, result)
        return result

    def assert_rejected(self, case: dict, context: dict, code: str) -> None:
        with self.assertRaisesRegex(g0.ContractError, f"^{code}$"):
            g0.validate_case(case, context)

    def test_golden_cases_are_conformant_and_never_claim_runtime_or_authority(self):
        paths = sorted(path for path in FIXTURES.glob("*.json") if not path.name.endswith(".context.json"))
        self.assertEqual(11, len(paths), "fixture corpus is the G0 conformance inventory")
        for path in paths:
            with self.subTest(name=path.stem):
                case = load_fixture(path.name)
                context = None if case["mode"] == "off" else load_fixture(f"{path.stem}.context.json")
                self.assert_conformant(case, context)

    def test_all_operations_have_an_independent_expected_state_projection(self):
        for operation in ("add", "update", "stop", "resume", "restore", "erase-content", "prune-history", "compact"):
            with self.subTest(operation=operation):
                case, context, expected = maintenance_case(operation)
                self.assertEqual(expected, case["after"])
                self.assert_conformant(case, context)
        erased, _, _ = maintenance_case("erase-content")
        target, proof = erased["after"]["items"][0], erased["after"]["proofs"][0]
        self.assertEqual(("erased", None, []), (target["status"], target["indexed_revision"], target["versions"]))
        self.assertTrue({"operation_id", "preview_digest", "operation", "item_id", "identity_epoch",
                         "reclaim_space", "issued_at", "recorded_at", "epoch", "result"} == set(proof))
        self.assertFalse({"body", "summary", "cues"} & set(proof))

    def test_confirmation_scope_revision_window_profile_and_context_pins_fail_closed(self):
        case, context, _ = maintenance_case("update")
        changed = copy.deepcopy(case)
        changed["preview"]["scope"]["root_id"] = "synthetic-other-root"
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "scope-mismatch")

        changed = copy.deepcopy(case)
        changed["preview"]["expected_revision"] = 99
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "revision-conflict")

        changed = copy.deepcopy(case)
        changed["preview"]["expires_at"] = NOW
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "confirmation-expired")

        changed = copy.deepcopy(case)
        changed["preview"]["before_digest"] = "0" * 64
        changed, changed_context = rebind(changed, context, preview=False, confirmation=False)
        self.assert_rejected(changed, changed_context, "stale-preview")

        changed = copy.deepcopy(case)
        changed["profile"]["max_versions"] = 3
        changed, changed_context = rebind(changed, context, preview=False, confirmation=False)
        self.assert_rejected(changed, changed_context, "preview-profile-mismatch")

        changed = copy.deepcopy(case)
        changed["confirmation"]["principal_id"] = "synthetic-other-principal"
        changed, changed_context = rebind(changed, context, confirmation=False)
        self.assert_rejected(changed, changed_context, "scope-mismatch")

        changed_context = copy.deepcopy(context)
        changed_context["before_digest"] = "0" * 64
        self.assert_rejected(case, changed_context, "stale-state")

        erase, erase_context, _ = maintenance_case("erase-content")
        erase["preview"]["unmanaged_copies"] = ["synthetic-copy", "synthetic-copy"]
        erase, erase_context = rebind(erase, erase_context)
        self.assert_rejected(erase, erase_context, "duplicate-unmanaged-copy")

    def test_pending_unknown_and_false_success_cannot_be_promoted_to_completion(self):
        case, context, _ = maintenance_case("erase-content")
        changed = copy.deepcopy(case)
        changed["result"].update({"sanitization": "pending", "outcome": "complete"})
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "false-success")

        case, context, _ = maintenance_case("update")
        unknown = copy.deepcopy(case)
        unknown["result"].update({
            "transaction": "unknown", "sanitization": "not-requested",
            "compaction": "not-requested", "outcome": "state-unknown",
        })
        unknown["after"] = copy.deepcopy(unknown["before"])
        unknown, unknown_context = rebind(unknown, context)
        self.assert_conformant(unknown, unknown_context)

        unknown["after"]["items"][0]["versions"][0]["body"] = "synthetic: uncommitted change"
        unknown, unknown_context = rebind(unknown, unknown_context)
        self.assert_rejected(unknown, unknown_context, "uncommitted-state-claimed")

    def test_retention_never_prunes_pending_proof_and_persists_floor_epoch(self):
        erased = load_fixture("erase-pending.json")["after"]
        before = copy.deepcopy(erased)
        before["proofs"].append(completed_proof(9))
        after = copy.deepcopy(before)
        after["epoch"], after["reject_before"] = 2, 1_500
        after["proofs"] = []
        changed, changed_context = retention_case(before, after, now=2_000)
        self.assert_rejected(changed, changed_context, "pending-proof-pruned")

        after["proofs"] = [before["proofs"][0]]
        case, context = retention_case(before, after, now=2_000)
        self.assert_conformant(case, context)

        changed = copy.deepcopy(case)
        changed["after"]["epoch"] = changed["before"]["epoch"]
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "floor-not-advanced")

        changed = copy.deepcopy(case)
        changed["after"]["reject_before"] = changed["before"]["reject_before"]
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "floor-not-advanced")

        stale_acceptance = copy.deepcopy(case)
        stale_acceptance["profile"]["history_seconds"] -= 1
        stale_acceptance, stale_acceptance_context = rebind(
            stale_acceptance, context, retention=False
        )
        self.assert_rejected(stale_acceptance, stale_acceptance_context, "unaccepted-retention")

        expired_confirmation = copy.deepcopy(case)
        expired_confirmation["confirmed_at"] = 1_940
        expired_confirmation, expired_confirmation_context = rebind(expired_confirmation, context)
        self.assert_rejected(expired_confirmation, expired_confirmation_context, "confirmation-expired")

        no_free_reserve = copy.deepcopy(case)
        no_free_reserve["before"]["storage"]["free_bytes"] = 0
        no_free_reserve["after"]["storage"]["free_bytes"] = 0
        no_free_reserve, no_free_reserve_context = rebind(no_free_reserve, context)
        self.assert_rejected(no_free_reserve, no_free_reserve_context, "maintenance-reserve")

        before_confirmation = copy.deepcopy(before)
        after_confirmation = copy.deepcopy(after)
        after_confirmation["reject_before"] = 1_100
        early_confirmation, early_confirmation_context = retention_case(
            before_confirmation, after_confirmation, now=1_400, confirmed_at=1_000
        )
        early_confirmation["profile"]["confirmation_seconds"] = 500
        early_confirmation, early_confirmation_context = rebind(
            early_confirmation, early_confirmation_context
        )
        self.assert_rejected(early_confirmation, early_confirmation_context, "invalid-proof-retention")

    def test_audit_requires_original_state_and_truthful_partial_inventory(self):
        case, context = load_fixture("audit.json"), load_fixture("audit.context.json")
        partial = copy.deepcopy(case)
        partial["inventory"] = {
            "item_ids": [], "complete": False, "reason": "not-started", "scanned_count": 0,
            "snapshot_digest": g0.digest(partial["before"]),
        }
        partial, partial_context = rebind(partial, context)
        self.assert_conformant(partial, partial_context)

        false_complete = copy.deepcopy(partial)
        false_complete["inventory"]["complete"] = True
        false_complete, false_context = rebind(false_complete, partial_context)
        self.assert_rejected(false_complete, false_context, "false-completeness")

        stale_snapshot = copy.deepcopy(partial)
        stale_snapshot["inventory"]["snapshot_digest"] = "0" * 64
        stale_snapshot, stale_context = rebind(stale_snapshot, partial_context)
        self.assert_rejected(stale_snapshot, stale_context, "audit-snapshot-mismatch")

        bad_count = copy.deepcopy(partial)
        bad_count["inventory"]["scanned_count"] = 1
        bad_count, bad_count_context = rebind(bad_count, partial_context)
        self.assert_rejected(bad_count, bad_count_context, "scan-count-mismatch")

        bad_reason = copy.deepcopy(partial)
        bad_reason["inventory"]["reason"] = "complete"
        bad_reason, bad_reason_context = rebind(bad_reason, partial_context)
        self.assert_rejected(bad_reason, bad_reason_context, "inventory-reason-mismatch")

        changed = copy.deepcopy(case)
        changed["after"]["storage"]["free_bytes"] += 1
        changed, changed_context = rebind(changed, context)
        self.assert_rejected(changed, changed_context, "audit-state-changed")

    def test_storage_quota_and_reserve_are_enforced_without_backend_measurement_claims(self):
        case, context, _ = maintenance_case("update")
        changed = copy.deepcopy(case)
        changed["before"]["storage"]["file_bytes"] = changed["profile"]["budget_bytes"] + 1
        changed, changed_context = rebase_maintenance(changed, context, changed["before"], now=NOW)
        self.assert_rejected(changed, changed_context, "storage-budget")

        changed = copy.deepcopy(case)
        changed["before"]["storage"]["free_bytes"] = changed["profile"]["reserve_bytes"] - 1
        changed, changed_context = rebase_maintenance(changed, context, changed["before"], now=NOW)
        self.assert_rejected(changed, changed_context, "maintenance-reserve")

    def test_replay_identity_index_capability_item_proof_and_storage_limits_fail_closed(self):
        case, context, _ = maintenance_case("update")
        replay = copy.deepcopy(case)
        replay["before"]["proofs"].append(completed_proof(1))
        replay["after"] = copy.deepcopy(replay["before"])
        replay["preview"]["operation_id"] = "synthetic-proof-1"
        replay, replay_context = rebind(replay, context)
        self.assert_rejected(replay, replay_context, "replayed-request")

        mismatch = copy.deepcopy(case)
        mismatch["before"]["epoch"] = mismatch["after"]["epoch"] = 2
        for document in (mismatch["before"], mismatch["after"]):
            document["items"][0]["identity_epoch"] = 2
        mismatch["after"]["proofs"][0].update({"identity_epoch": 2, "epoch": 2})
        mismatch["preview"].update({"epoch": 2, "identity_epoch": 1})
        mismatch, mismatch_context = rebind(mismatch, context)
        self.assert_rejected(mismatch, mismatch_context, "identity-epoch-mismatch")

        bad_index = copy.deepcopy(case)
        bad_index["after"]["items"][0]["indexed_revision"] = None
        bad_index, bad_index_context = rebind(bad_index, context)
        self.assert_rejected(bad_index, bad_index_context, "index-revision-mismatch")

        missing_capability = copy.deepcopy(case)
        missing_capability, missing_context = rebind(missing_capability, context)
        missing_context["capabilities"] = ["audit"]
        self.assert_rejected(missing_capability, missing_context, "missing-capability")

        add, add_context, _ = maintenance_case("add")
        add["profile"]["max_items"] = 1
        add, add_context = rebind(add, add_context)
        with self.assertRaises(g0.ContractError):
            g0.validate_case(add, add_context)

        proof_mismatch = copy.deepcopy(case)
        proof_mismatch["after"]["epoch"] = 2
        proof_mismatch["after"]["proofs"][0].update({"identity_epoch": 2, "epoch": 2})
        proof_mismatch, proof_context = rebind(proof_mismatch, context)
        self.assert_rejected(proof_mismatch, proof_context, "proof-identity-mismatch")

        underreported = copy.deepcopy(case)
        underreported["before"]["storage"]["file_bytes"] = 1
        underreported["before"]["storage"]["reclaimable_bytes"] = 0
        underreported, underreported_context = rebind(underreported, context)
        self.assert_rejected(underreported, underreported_context, "underreported-storage")

    def test_growth_respects_reserves_while_stop_erase_and_compact_remain_available(self):
        cases = {operation: maintenance_case(operation)[:2]
                 for operation in ("update", "stop", "erase-content", "compact")}
        for operation, (case, context) in cases.items():
            with self.subTest(operation=operation):
                case["profile"]["budget_bytes"] = 17_999
                case, context = rebase_maintenance(case, context, case["before"], now=NOW)
                if operation == "update":
                    self.assert_rejected(case, context, "maintenance-reserve")
                else:
                    self.assert_conformant(case, context)

    def test_proof_reserve_blocks_growth_but_not_audit(self):
        case, context, _ = maintenance_case("update")
        case["profile"]["max_proofs"] = 2
        case["before"]["proofs"] = [completed_proof(1), completed_proof(2)]
        case, context = rebase_maintenance(case, context, case["before"], now=NOW)
        self.assert_rejected(case, context, "proof-reserve")

        before = state(items=[item()], proofs=[completed_proof(1), completed_proof(2)])
        audit = {
            "contract_version": g0.VERSION, "case_id": "synthetic-proof-reserve-audit", "mode": "audit",
            "profile": {**PROFILE, "max_proofs": 2}, "before": before, "after": copy.deepcopy(before),
            "inventory": {"item_ids": ["synthetic-item"], "complete": True, "reason": "complete",
                          "scanned_count": 1, "snapshot_digest": g0.digest(before)},
        }
        audit_context = {
            "contract_version": g0.VERSION, "scope": copy.deepcopy(SCOPE), "now": NOW,
            "before_digest": "0" * 64, "profile_digest": "0" * 64,
            "accepted_confirmations": [], "accepted_retention": [], "accepted_continuations": [],
            "capabilities": ["audit"],
        }
        audit, audit_context = rebind(audit, audit_context)
        self.assert_conformant(audit, audit_context)

    def test_erase_retention_then_same_label_new_epoch_rejects_old_identity(self):
        add, add_context, _ = maintenance_case("add")
        add["preview"]["item_id"] = "synthetic-item"
        add, add_context = rebase_maintenance(add, add_context, state(items=[]), now=1_000)
        self.assert_conformant(add, add_context)

        erase, erase_context, _ = maintenance_case("erase-content")
        erase, erase_context = rebase_maintenance(erase, erase_context, add["after"], now=1_100)
        self.assert_conformant(erase, erase_context)

        retained = state(items=[], proofs=[], epoch=2, reject_before=1_500, storage=erase["after"]["storage"])
        retention, retention_context = retention_case(erase["after"], retained, now=2_000)
        self.assert_conformant(retention, retention_context)

        replacement, replacement_context, _ = maintenance_case("add")
        replacement["preview"].update({
            "item_id": "synthetic-item", "identity_epoch": 2,
            "next_version": version(1, created_at=2_000, suffix="replacement"),
        })
        replacement, replacement_context = rebase_maintenance(
            replacement, replacement_context, retained, now=2_000
        )
        self.assert_conformant(replacement, replacement_context)
        self.assertEqual(2, replacement["after"]["items"][0]["identity_epoch"])

        stale = copy.deepcopy(replacement)
        stale["preview"]["identity_epoch"] = 1
        stale, stale_context = rebind(stale, replacement_context)
        self.assert_rejected(stale, stale_context, "stale-identity-epoch")

        old_identity, old_context, _ = maintenance_case("update")
        old_identity["preview"].update({
            "identity_epoch": 1, "expected_revision": 1,
            "next_version": version(2, created_at=2_010, suffix="replacement-update"),
        })
        old_identity, old_context = rebase_maintenance(
            old_identity, old_context, replacement["after"], now=2_010
        )
        old_identity["after"]["proofs"][-1]["identity_epoch"] = 2
        self.assert_rejected(old_identity, old_context, "identity-epoch-mismatch")

    def test_pruning_unblocks_updates_but_cannot_restore_a_pruned_revision(self):
        pruned, pruned_context, _ = maintenance_case("prune-history")
        self.assert_conformant(pruned, pruned_context)

        update, update_context, _ = maintenance_case("update")
        update["preview"].update({
            "expected_revision": 2, "next_version": version(3, created_at=1_100, suffix="after-prune"),
        })
        update, update_context = rebase_maintenance(update, update_context, pruned["after"], now=1_100)
        self.assert_conformant(update, update_context)
        self.assertEqual(1_100, update["after"]["items"][0]["versions"][-2]["retired_at"])

        restore = copy.deepcopy(update)
        restore["preview"].update({
            "operation": "restore", "restore_revision": 1,
            "next_version": version(3, created_at=1_100, suffix="one"),
        })
        restore["after"] = copy.deepcopy(restore["before"])
        restore, restore_context = rebind(restore, update_context)
        self.assert_rejected(restore, restore_context, "missing-restore-version")

    def test_continuation_advances_only_pending_phases_without_rewriting_content_or_request(self):
        pending, pending_context, _ = maintenance_case("erase-content")
        pending["preview"]["reclaim_space"] = True
        pending["result"].update({"sanitization": "pending", "compaction": "not-requested",
                                  "outcome": "sanitization-pending"})
        pending["after"] = projection(pending["before"], pending["preview"], pending["result"], now=NOW)
        pending, pending_context = rebind(pending, pending_context)
        pending["after"] = projection(pending["before"], pending["preview"], pending["result"], now=NOW)
        self.assert_conformant(pending, pending_context)

        middle_result = {"transaction": "succeeded", "sanitization": "succeeded",
                         "compaction": "pending", "outcome": "space-reclaim-pending"}
        middle, middle_context = continuation_case(pending["after"], middle_result, now=1_010)
        self.assert_conformant(middle, middle_context)

        complete_result = {"transaction": "succeeded", "sanitization": "succeeded",
                           "compaction": "succeeded", "outcome": "complete"}
        complete, complete_context = continuation_case(
            middle["after"], complete_result, now=1_020,
            storage={"file_bytes": 7_000, "free_bytes": 65_000, "reclaimable_bytes": 1_000},
        )
        self.assert_conformant(complete, complete_context)

        changed_content = copy.deepcopy(middle)
        changed_content["after"]["items"] = [item()]
        changed_content, changed_context = rebind(changed_content, middle_context)
        self.assert_rejected(changed_content, changed_context, "erase-proof-content-present")

        changed_marker = copy.deepcopy(middle)
        changed_marker["after"]["items"][0]["erased_at"] = 999
        changed_marker, changed_marker_context = rebind(changed_marker, middle_context)
        self.assert_rejected(changed_marker, changed_marker_context, "unexpected-continuation-change")

        wrong_reclaim_result = {"transaction": "succeeded", "sanitization": "succeeded",
                                "compaction": "not-requested", "outcome": "complete"}
        wrong_reclaim, wrong_context = continuation_case(pending["after"], wrong_reclaim_result, now=1_010)
        wrong_reclaim["after"]["proofs"][-1]["reclaim_space"] = False
        wrong_reclaim, wrong_context = rebind(wrong_reclaim, wrong_context)
        self.assert_rejected(wrong_reclaim, wrong_context, "missing-compaction")

        old_acceptance = copy.deepcopy(middle_context)
        old_acceptance["accepted_continuations"] = ["0" * 64]
        self.assert_rejected(middle, old_acceptance, "unaccepted-continuation")

        stale_continuation = copy.deepcopy(middle)
        stale_continuation["profile"]["history_seconds"] -= 1
        stale_continuation, stale_continuation_context = rebind(
            stale_continuation, middle_context, continuation=False
        )
        self.assert_rejected(stale_continuation, stale_continuation_context, "unaccepted-continuation")

        regressed_result = {"transaction": "succeeded", "sanitization": "pending",
                            "compaction": "not-requested", "outcome": "sanitization-pending"}
        regressed, regressed_context = continuation_case(middle["after"], regressed_result, now=1_020)
        self.assert_rejected(regressed, regressed_context, "phase-regression")

    def test_full_file_budget_blocks_growth_but_stop_erase_and_compact_are_available(self):
        profile = {**PROFILE, "budget_bytes": 20_000, "reserve_bytes": 5_000}
        full = {"file_bytes": 20_000, "free_bytes": 5_000, "reclaimable_bytes": 1_000}
        for operation in ("update", "stop", "erase-content", "compact"):
            with self.subTest(operation=operation):
                case, context, _ = maintenance_case(operation)
                case["profile"] = copy.deepcopy(profile)
                case["before"]["storage"] = copy.deepcopy(full)
                case, context = rebase_maintenance(case, context, case["before"], now=NOW)
                if operation == "compact":
                    case["after"]["storage"] = {
                        "file_bytes": 19_000, "free_bytes": 6_000, "reclaimable_bytes": 0,
                    }
                if operation == "update":
                    self.assert_rejected(case, context, "maintenance-reserve")
                else:
                    self.assert_conformant(case, context)

    def test_cleanup_uses_proof_reserve_until_exhausted_while_audit_remains_available(self):
        limits = {**PROFILE, "max_proofs": 1, "maintenance_proof_reserve": 1}
        cleanup, cleanup_context, _ = maintenance_case("erase-content")
        cleanup["profile"] = copy.deepcopy(limits)
        cleanup["before"]["proofs"] = [completed_proof(1)]
        cleanup, cleanup_context = rebase_maintenance(cleanup, cleanup_context, cleanup["before"], now=NOW)
        self.assert_conformant(cleanup, cleanup_context)
        self.assertEqual(2, len(cleanup["after"]["proofs"]))

        exhausted, exhausted_context, _ = maintenance_case("erase-content")
        exhausted["profile"] = copy.deepcopy(limits)
        exhausted["before"]["proofs"] = [completed_proof(1), completed_proof(2)]
        exhausted, exhausted_context = rebase_maintenance(
            exhausted, exhausted_context, exhausted["before"], now=NOW
        )
        with self.assertRaises(g0.ContractError):
            g0.validate_case(exhausted, exhausted_context)

        before = state(items=[item()], proofs=[completed_proof(1), completed_proof(2)])
        audit = {
            "contract_version": g0.VERSION, "case_id": "synthetic-reserve-audit", "mode": "audit",
            "profile": limits, "before": before, "after": copy.deepcopy(before),
            "inventory": {"item_ids": ["synthetic-item"], "complete": True, "reason": "complete",
                          "scanned_count": 1, "snapshot_digest": g0.digest(before)},
        }
        audit_context = {
            "contract_version": g0.VERSION, "scope": copy.deepcopy(SCOPE), "now": NOW,
            "before_digest": "0" * 64, "profile_digest": "0" * 64,
            "accepted_confirmations": [], "accepted_retention": [], "accepted_continuations": [],
            "capabilities": ["audit"],
        }
        audit, audit_context = rebind(audit, audit_context)
        self.assert_conformant(audit, audit_context)

    def test_three_fixed_budget_identity_cycles_prune_markers_and_reject_stale_previews(self):
        limits = {
            **PROFILE, "max_items": 1, "max_proofs": 1, "maintenance_proof_reserve": 1,
            "budget_bytes": 100_000, "reserve_bytes": 10_000,
        }
        fixed_storage = {"file_bytes": 90_000, "free_bytes": 10_000, "reclaimable_bytes": 0}
        before = state(items=[], storage=fixed_storage)
        epochs: list[int] = []
        for cycle in range(3):
            added_at = 1_000 + cycle * 2_000
            add, add_context, _ = maintenance_case("add")
            add["profile"] = copy.deepcopy(limits)
            add["preview"].update({
                "item_id": "synthetic-item", "identity_epoch": before["epoch"],
                "next_version": version(1, created_at=added_at, suffix=f"cycle-{cycle}"),
            })
            add, add_context = rebase_maintenance(add, add_context, before, now=added_at)
            self.assert_conformant(add, add_context)
            epochs.append(add["after"]["items"][0]["identity_epoch"])

            erased_at = added_at + 10
            erase, erase_context, _ = maintenance_case("erase-content")
            erase["profile"] = copy.deepcopy(limits)
            erase["preview"]["identity_epoch"] = before["epoch"]
            erase, erase_context = rebase_maintenance(erase, erase_context, add["after"], now=erased_at)
            self.assert_conformant(erase, erase_context)

            retained = state(
                items=[], proofs=[], epoch=before["epoch"] + 1, reject_before=erased_at + 100,
                storage=fixed_storage,
            )
            retention, retention_context = retention_case(erase["after"], retained, now=erased_at + 1_000)
            retention["profile"] = copy.deepcopy(limits)
            retention, retention_context = rebind(retention, retention_context)
            self.assert_conformant(retention, retention_context)
            before = retained

        self.assertEqual([1, 2, 3], epochs)
        stale, stale_context, _ = maintenance_case("add")
        stale["profile"] = copy.deepcopy(limits)
        stale["preview"].update({
            "item_id": "synthetic-item", "identity_epoch": before["epoch"] - 1,
            "next_version": version(1, created_at=7_000, suffix="stale-epoch"),
        })
        stale, stale_context = rebase_maintenance(stale, stale_context, before, now=7_000)
        stale["preview"]["epoch"] = before["epoch"] - 1
        stale, stale_context = rebind(stale, stale_context)
        self.assert_rejected(stale, stale_context, "request-before-floor")

        too_old, too_old_context, _ = maintenance_case("add")
        fresh_now = before["reject_before"] + 5
        too_old["profile"] = copy.deepcopy(limits)
        too_old["preview"].update({
            "item_id": "synthetic-item", "identity_epoch": before["epoch"],
            "next_version": version(1, created_at=fresh_now, suffix="stale-floor"),
        })
        too_old, too_old_context = rebase_maintenance(too_old, too_old_context, before, now=fresh_now)
        too_old["preview"].update({
            "issued_at": before["reject_before"] - 1, "expires_at": before["reject_before"] + 10,
        })
        too_old, too_old_context = rebind(too_old, too_old_context)
        self.assert_rejected(too_old, too_old_context, "request-before-floor")

    def test_old_current_is_updateable_but_expired_history_requires_pruning(self):
        current = item(versions=[version(1, created_at=0, suffix="old-current")])
        case, context, _ = maintenance_case("update")
        case["profile"]["history_seconds"] = 50
        case["preview"]["next_version"] = version(2, created_at=1_000, suffix="fresh")
        case, context = rebase_maintenance(case, context, state(items=[current]), now=1_000)
        self.assert_conformant(case, context)

        expired = item(versions=[
            version(1, created_at=0, retired_at=0, suffix="expired-history"),
            version(2, created_at=1, suffix="current"),
        ])
        update, update_context, _ = maintenance_case("update")
        update["profile"]["history_seconds"] = 50
        update["preview"].update({
            "expected_revision": 2, "next_version": version(3, created_at=1_000, suffix="blocked"),
        })
        update, update_context = rebase_maintenance(update, update_context, state(items=[expired]), now=1_000)
        self.assert_rejected(update, update_context, "history-expired")

        prune, prune_context, _ = maintenance_case("prune-history")
        prune["profile"]["history_seconds"] = 50
        prune["preview"].update({"expected_revision": 2, "erase_revisions": [1]})
        prune, prune_context = rebase_maintenance(prune, prune_context, state(items=[expired]), now=1_000)
        self.assert_conformant(prune, prune_context)

        updated, updated_context, _ = maintenance_case("update")
        updated["profile"]["history_seconds"] = 50
        updated["preview"].update({
            "expected_revision": 2, "next_version": version(3, created_at=1_100, suffix="unblocked"),
        })
        updated, updated_context = rebase_maintenance(updated, updated_context, prune["after"], now=1_100)
        self.assert_conformant(updated, updated_context)

        for revisions in ([2], [99]):
            with self.subTest(revisions=revisions):
                invalid, invalid_context, _ = maintenance_case("prune-history")
                invalid["profile"]["history_seconds"] = 50
                invalid["preview"].update({"expected_revision": 2, "erase_revisions": revisions})
                invalid["after"] = state(items=[expired])
                invalid, invalid_context = rebind(invalid, invalid_context)
                self.assert_rejected(invalid, invalid_context, "invalid-history-delete-set")

    def test_each_required_capability_and_lifecycle_index_boundary_fails_closed(self):
        audit, audit_context = load_fixture("audit.json"), load_fixture("audit.context.json")
        audit_context["capabilities"] = ["item-write"]
        self.assert_rejected(audit, audit_context, "missing-capability")

        requirements = (
            ("update", "item-write"), ("erase-content", "erase-content"),
            ("erase-content", "root-maintenance"), ("prune-history", "erase-content"),
            ("prune-history", "root-maintenance"), ("compact", "root-maintenance"),
        )
        for operation, omitted in requirements:
            with self.subTest(operation=operation, omitted=omitted):
                case, context, _ = maintenance_case(operation)
                context["capabilities"] = [cap for cap in context["capabilities"] if cap != omitted]
                self.assert_rejected(case, context, "missing-capability")

        active, active_context, _ = maintenance_case("update")
        active["after"]["items"][0]["indexed_revision"] = None
        active, active_context = rebind(active, active_context)
        self.assert_rejected(active, active_context, "index-revision-mismatch")

        stopped, stopped_context, _ = maintenance_case("stop")
        stopped["after"]["items"][0]["indexed_revision"] = 1
        stopped, stopped_context = rebind(stopped, stopped_context)
        self.assert_rejected(stopped, stopped_context, "index-revision-mismatch")

        erased, erased_context, _ = maintenance_case("erase-content")
        erased["after"]["items"][0]["indexed_revision"] = 1
        erased, erased_context = rebind(erased, erased_context)
        with self.assertRaises(g0.ContractError):
            g0.validate_case(erased, erased_context)

        erased_case, erased_case_context, _ = maintenance_case("erase-content")
        self.assert_conformant(erased_case, erased_case_context)
        for operation, code in (("add", "identity-reuse"), ("update", "erased-identity"),
                                ("resume", "erased-identity"), ("restore", "erased-identity")):
            with self.subTest(operation=operation):
                rejected, rejected_context, _ = maintenance_case(operation)
                if operation == "add":
                    rejected["preview"].update({
                        "item_id": "synthetic-item", "identity_epoch": 1,
                        "next_version": version(1, created_at=1_100, suffix="reused"),
                    })
                elif operation in {"update", "restore"}:
                    rejected["preview"]["next_version"]["created_at"] = 1_100
                    if operation == "restore":
                        rejected["preview"].update({
                            "expected_revision": 1,
                            "next_version": version(2, created_at=1_100, suffix="one"),
                        })
                rejected, rejected_context = rebase_maintenance(
                    rejected, rejected_context, erased_case["after"], now=1_100
                )
                rejected["after"] = copy.deepcopy(rejected["before"])
                rejected, rejected_context = rebind(rejected, rejected_context)
                self.assert_rejected(rejected, rejected_context, code)

    def test_continuation_requires_fresh_post_record_confirmation_and_pending_blocks_new_work(self):
        pending, pending_context, _ = maintenance_case("erase-content")
        pending["preview"]["reclaim_space"] = True
        pending["result"].update({"sanitization": "pending", "compaction": "not-requested",
                                  "outcome": "sanitization-pending"})
        pending["after"] = projection(pending["before"], pending["preview"], pending["result"], now=NOW)
        pending, pending_context = rebind(pending, pending_context)
        pending["after"] = projection(pending["before"], pending["preview"], pending["result"], now=NOW)
        self.assert_conformant(pending, pending_context)

        result = {"transaction": "succeeded", "sanitization": "succeeded",
                  "compaction": "pending", "outcome": "space-reclaim-pending"}
        too_early, too_early_context = continuation_case(pending["after"], result, now=1_010)
        too_early["confirmed_at"] = pending["after"]["proofs"][0]["recorded_at"] - 1
        too_early, too_early_context = rebind(too_early, too_early_context)
        self.assert_rejected(too_early, too_early_context, "invalid-integer")

        expired, expired_context = continuation_case(pending["after"], result, now=1_070)
        expired["confirmed_at"] = 1_010
        expired, expired_context = rebind(expired, expired_context)
        self.assert_rejected(expired, expired_context, "confirmation-expired")

        blocked, blocked_context, _ = maintenance_case("update")
        blocked["preview"]["next_version"]["created_at"] = 1_010
        blocked, blocked_context = rebase_maintenance(blocked, blocked_context, pending["after"], now=1_010)
        blocked["after"] = copy.deepcopy(blocked["before"])
        blocked, blocked_context = rebind(blocked, blocked_context)
        self.assert_rejected(blocked, blocked_context, "pending-maintenance")


class MemoryGovernanceG0CliTests(unittest.TestCase):
    def run_cli(self, case: pathlib.Path, context: pathlib.Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(ROOT / "scripts" / "validate-memory-governance-g0.py"), str(case)]
        if context is not None:
            command.extend(["--context", str(context)])
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)

    def assert_generic_rejection(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        error = json.loads(result.stderr)
        self.assertEqual({"status", "code", "operation_authorized"}, set(error))
        self.assertEqual("rejected", error["status"])
        self.assertFalse(error["operation_authorized"])
        self.assertNotIn("Traceback", result.stderr)

    def test_off_never_reads_or_probes_context_and_cli_outputs_only_synthetic_verdict(self):
        with tempfile.TemporaryDirectory() as directory:
            context = pathlib.Path(directory) / "unreadable-context"
            context.symlink_to(pathlib.Path(directory) / "missing-target")
            result = self.run_cli(FIXTURES / "off.json", context)
        self.assertEqual(0, result.returncode, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertFalse(verdict["operation_authorized"])
        self.assertFalse(verdict["runtime_proven"])
        self.assertFalse(verdict["write_performed"])
        self.assertEqual("", result.stderr)

    def test_cli_rejects_missing_context_duplicate_nonfinite_unknown_version_and_invalid_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            missing_context = self.run_cli(FIXTURES / "update.json")
            self.assert_generic_rejection(missing_context)
            sources = {
                "duplicate.json": b'{"contract_version":"mg1-g0-synthetic/v0","contract_version":"mg1-g0-synthetic/v0"}',
                "nonfinite.json": b'{"contract_version":NaN}',
                "unknown.json": b'{"contract_version":"mg1-g0-synthetic/v0","case_id":"synthetic-off","mode":"off","extra":true}',
                "version.json": b'{"contract_version":"future","case_id":"synthetic-off","mode":"off"}',
                "unicode.json": b'{"contract_version":"mg1-g0-synthetic/v0","case_id":"\xed\xa0\x80","mode":"off"}',
            }
            for name, data in sources.items():
                path = directory / name
                path.write_bytes(data)
                with self.subTest(name=name):
                    self.assert_generic_rejection(self.run_cli(path))

    def test_cli_rejects_symlink_ancestor_fifo_and_oversize_input(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            real = directory / "real"
            real.mkdir()
            (real / "case.json").write_text(json.dumps(load_fixture("off.json")), encoding="utf-8")
            linked = directory / "linked"
            linked.symlink_to(real, target_is_directory=True)
            self.assert_generic_rejection(self.run_cli(linked / "case.json"))

            fifo = directory / "case.fifo"
            os.mkfifo(fifo)
            self.assert_generic_rejection(self.run_cli(fifo))

            oversize = directory / "oversize.json"
            with oversize.open("wb") as stream:
                stream.truncate(g0.MAX_INPUT_BYTES + 1)
            self.assert_generic_rejection(self.run_cli(oversize))


if __name__ == "__main__":
    unittest.main()
