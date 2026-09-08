from __future__ import annotations

import copy
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import memory_scope_lifecycle as lifecycle  # noqa: E402
from memory_governance_g0 import ContractError, digest  # noqa: E402


def candidate(**changes):
    return {"content_id": "synthetic-gitlab-method", "requested_scope": "unspecified",
            "project_id": "synthetic-project", "backend": "unspecified", "kind": "procedure",
            "source_id": "synthetic-source", "verified": True, "reusable": True,
            "project_private": False, "now": 100, "valid_until": 1000, **changes}


def match(**changes):
    return {"item_id": "synthetic-item", "revision": 1, "state": "active",
            "content_digest": "a" * 64, "summary_id": "synthetic-safe-summary",
            "source_id": "synthetic-source", "condition_id": "synthetic-condition",
            "match": "exact", "related_projects": ["synthetic-project"],
            "independently_reusable": False, "project_private": True, **changes}


def store(**changes):
    return {"store_id": "synthetic-managed", "root_id": "synthetic-root",
            "principal_id": "synthetic-principal", "scope": "project",
            "project_id": "synthetic-project", "backend": "managed", "readable": True,
            "capability": "managed-erase", "coverage": "complete", "matches": [match()], **changes}


def context(**changes):
    return {"principal_id": "synthetic-principal", "project_ids": ["synthetic-project"],
            "observed_at": 100, "valid_until": 160,
            "requested_stores": ["synthetic-managed", "synthetic-global", "synthetic-native"], **changes}


def registry():
    return [store(), store(store_id="synthetic-global", root_id="synthetic-ops-root", scope="global",
                           project_id=None, backend="document", capability="document-edit"),
            store(store_id="synthetic-native", root_id="synthetic-native-root", scope="global",
                  project_id=None, backend="native", readable=False, capability="none",
                  coverage="unavailable", matches=[])]


def snapshot():
    return lifecycle.discover(context(), registry())


def selection(snap):
    return [{k: t[k] for k in ("store_id", "item_id")} for t in snap["targets"]]


def preview(snap=None):
    snap = snapshot() if snap is None else snap
    return lifecycle.preview(snap, selection(snap), "synthetic-request", 100, 300)


def confirmation(value):
    return {k: value[k] for k in ("principal_id", "request_id", "preview_digest")}


def outcomes(value, rows):
    targets = {lifecycle.key(t): t for t in value["targets"]}
    return {**confirmation(value), "targets": [
        {"revision": targets.get(lifecycle.key(row), {}).get("revision", 1),
         "content_digest": targets.get(lifecycle.key(row), {}).get("content_digest", "a" * 64),
         **row} for row in rows]}


def summarize(value, rows):
    return lifecycle.summarize(value, confirmation(value), snapshot(), 101, outcomes(value, rows))


class ScopeRoutingTests(unittest.TestCase):
    def assert_inert(self, value):
        for key in ("operation_authorized", "runtime_proven", "write_performed"):
            self.assertIs(value[key], False)

    def test_verified_generic_gitlab_method_suggests_one_global_document(self):
        value = lifecycle.route(candidate())
        self.assertEqual((value["decision"], value["scope"], value["backend"]),
                         ("preview-only", "global", "document"))
        self.assertIsNone(value["project_id"])
        self.assert_inert(value)

    def test_private_deployment_rule_stays_project_document(self):
        value = lifecycle.route(candidate(kind="rule", project_private=True, reusable=False))
        self.assertEqual((value["scope"], value["backend"]), ("project", "document"))
        self.assertEqual(value["decision"], "preview-only")

    def test_ambiguous_remember_requires_scope_or_backend(self):
        for changes in ({"reusable": False}, {"kind": "fact"},
                        {"requested_scope": "project", "project_id": None}):
            with self.subTest(changes=changes):
                self.assertEqual(lifecycle.route(candidate(**changes))["decision"], "needs-clarification")

    def test_explicit_project_managed_intent_is_preserved(self):
        value = lifecycle.route(candidate(requested_scope="project", backend="managed"))
        self.assertEqual((value["scope"], value["backend"], value["decision"]),
                         ("project", "managed", "preview-only"))

    def test_global_visibility_and_single_success_do_not_promote(self):
        for changes in ({"project_private": True}, {"reusable": False}):
            self.assertEqual(lifecycle.route(candidate(requested_scope="global", **changes))["decision"],
                             "needs-clarification")

    def test_stale_or_unverified_sources_require_evidence(self):
        for changes in ({"verified": False}, {"source_id": None}, {"valid_until": 100}):
            self.assertEqual(lifecycle.route(candidate(**changes))["decision"], "needs-evidence")

    def test_native_is_runtime_owned_and_global_managed_is_unaccepted(self):
        self.assertEqual(lifecycle.route(candidate(backend="native"))["decision"], "runtime-management-required")
        self.assertEqual(lifecycle.route(candidate(backend="managed"))["decision"], "design-decision-required")

    def test_rules_cannot_be_promoted_from_advisory_backend(self):
        for backend in ("managed", "native"):
            self.assertEqual(lifecycle.route(candidate(kind="rule", backend=backend))["decision"],
                             "needs-clarification")

    def test_rejects_unknown_fields_types_and_multiple_backends(self):
        for changes in ({"backend": ["managed", "native"]}, {"verified": 1},
                        {"now": True}, {"execute": True}, {"content_id": "/private/input"}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                lifecycle.route(candidate(**changes))


class DiscoveryTests(unittest.TestCase):
    def test_duplicates_across_stores_remain_separate_and_native_unavailable(self):
        value = snapshot()
        self.assertEqual(len(value["targets"]), 2)
        self.assertEqual(len({lifecycle.key(t) for t in value["targets"]}), 2)
        self.assertEqual(value["coverage"][-1], {"store_id": "synthetic-native", "status": "unavailable"})
        self.assertEqual(value["external_copies"], "unknown")

    def test_semantic_similarity_keeps_condition_and_identity(self):
        stores = registry()
        stores[0]["matches"].append(match(item_id="synthetic-other", condition_id="synthetic-other-condition",
                                           match="semantic"))
        value = lifecycle.discover(context(), stores)
        self.assertEqual(len(value["targets"]), 3)
        self.assertEqual(value["targets"][-1]["condition_id"], "synthetic-other-condition")

    def test_missing_registration_and_partial_results_are_not_absence(self):
        stores = registry()[:2]
        stores[0]["coverage"] = "partial"
        value = lifecycle.discover(context(), stores)
        self.assertEqual({c["status"] for c in value["coverage"]}, {"complete", "partial", "unknown"})

    def test_empty_complete_store_registration_is_bound(self):
        stores = registry()
        stores[0]["matches"] = []
        value = lifecycle.discover(context(), stores)
        self.assertEqual(lifecycle.checked_snapshot(value), value)
        self.assertEqual(len(value["registrations"]), 3)

    def test_cross_principal_unrequested_project_and_private_roots_fail(self):
        for changes in ({"principal_id": "synthetic-other"}, {"project_id": "synthetic-other"},
                        {"store_id": "synthetic-unregistered"}, {"root_id": "/real/path"}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                lifecycle.discover(context(), [store(**changes)])

    def test_inaccessible_store_cannot_supply_matches_or_claim_complete(self):
        for changes in ({"readable": False}, {"coverage": "unknown"}, {"capability": "native-management"}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                lifecycle.discover(context(), [store(**changes)])

    def test_duplicates_invalid_state_and_match_budget_fail(self):
        for stores in ([store(), store()], [store(matches=[match(), match()])],
                       [store(matches=[match(state="invented")])],
                       [store(matches=[match(item_id=f"synthetic-item-{i}") for i in range(33)])]):
            with self.assertRaises(ContractError):
                lifecycle.discover(context(), stores)

    def test_total_budget_is_not_per_store(self):
        stores = registry()
        for s in stores[:2]:
            s["matches"] = [match(item_id=f"synthetic-item-{i}") for i in range(17)]
        with self.assertRaisesRegex(ContractError, "search-budget-exceeded"):
            lifecycle.discover(context(), stores)

    def test_multiple_store_aliases_cannot_duplicate_underlying_root(self):
        stores = registry()
        stores[1]["root_id"] = stores[0]["root_id"]
        with self.assertRaisesRegex(ContractError, "duplicate-root-alias"):
            lifecycle.discover(context(), stores)

    def test_forged_snapshot_cannot_introduce_target_or_authority(self):
        for changes in ({"operation_authorized": True}, {"external_copies": "none"},
                        {"registrations": []}, {"schema_version": "production"}):
            with self.assertRaises(ContractError):
                lifecycle.checked_snapshot({**snapshot(), **changes})


class ConfirmationTests(unittest.TestCase):
    def test_exact_set_and_subset_remain_inert(self):
        snap = snapshot()
        for selected in (selection(snap), selection(snap)[:1]):
            value = lifecycle.preview(snap, selected, "synthetic-request", 100, 300)
            answer = lifecycle.confirm(value, confirmation(value), snap, 101, {})
            self.assertEqual(answer["decision"], "confirmation-consistent")
            for key in ("operation_authorized", "runtime_proven", "write_performed"):
                self.assertIs(answer[key], False)

    def test_selection_must_be_nonempty_unique_and_listed(self):
        selected = selection(snapshot())[:1]
        for bad in ([], selected * 2, [{"store_id": "synthetic-missing", "item_id": "synthetic-item"}],
                    [{"store_id": "synthetic-managed", "item_id": "*"}]):
            with self.assertRaises(ContractError):
                lifecycle.preview(snapshot(), bad, "synthetic-request", 100, 300)

    def test_target_limit_is_separate_from_discovery_limit(self):
        stores = [store(matches=[match(item_id=f"synthetic-item-{i}") for i in range(9)])]
        snap = lifecycle.discover(context(), stores)
        with self.assertRaises(ContractError):
            preview(snap)

    def test_pending_erased_or_incapable_target_requires_reconciliation(self):
        for changes in ({"matches": [match(state="pending")]}, {"matches": [match(state="erased")]},
                        {"capability": "none"}):
            snap = lifecycle.discover(context(), [store(**changes)])
            with self.assertRaises(ContractError):
                preview(snap)

    def test_expiry_future_and_confirmation_identity_fail(self):
        value = preview()
        for now in (99, 300, 301, True):
            with self.assertRaises(ContractError):
                lifecycle.confirm(value, confirmation(value), snapshot(), now, {})
        for field in ("principal_id", "request_id", "preview_digest"):
            bad = confirmation(value)
            bad[field] = "synthetic-wrong"
            with self.assertRaisesRegex(ContractError, "confirmation-mismatch"):
                lifecycle.confirm(value, bad, snapshot(), 101, {})

    def test_confirmation_lifetime_has_strict_synthetic_bound(self):
        for expiry in (100, 401, True):
            with self.assertRaises(ContractError):
                lifecycle.preview(snapshot(), selection(snapshot()), "synthetic-request", 100, expiry)

    def test_stale_and_future_readback_fail_but_fresh_same_state_passes(self):
        value = preview()
        for observed, until, now in ((100, 160, 160), (120, 180, 101), (99, 159, 101)):
            current = lifecycle.discover(context(observed_at=observed, valid_until=until), registry())
            with self.assertRaises(ContractError):
                lifecycle.confirm(value, confirmation(value), current, now, {})
        current = lifecycle.discover(context(observed_at=180, valid_until=240), registry())
        self.assertEqual(lifecycle.confirm(value, confirmation(value), current, 181, {})["decision"],
                         "confirmation-consistent")

    def test_observation_window_and_stale_preview_are_rejected(self):
        for until in (100, 161):
            with self.assertRaisesRegex(ContractError, "invalid-observation-window"):
                lifecycle.discover(context(valid_until=until), registry())
        with self.assertRaisesRegex(ContractError, "stale-observation"):
            lifecycle.preview(snapshot(), selection(snapshot()), "synthetic-request", 160, 300)

    def test_version_digest_state_condition_and_new_match_drift_fail(self):
        for changes in ({"revision": 2}, {"content_digest": "b" * 64}, {"state": "stopped"},
                        {"condition_id": "synthetic-new-condition"}):
            stores = registry()
            stores[0]["matches"][0].update(changes)
            current = lifecycle.discover(context(), stores)
            value = preview()
            with self.assertRaisesRegex(ContractError, "snapshot-drift"):
                lifecycle.confirm(value, confirmation(value), current, 101, {})
        stores = registry()
        stores[0]["matches"].append(match(item_id="synthetic-new"))
        with self.assertRaisesRegex(ContractError, "snapshot-drift"):
            lifecycle.confirm(value, confirmation(value), lifecycle.discover(context(), stores), 101, {})

    def test_root_capability_and_coverage_drift_fail(self):
        for changes in ({"root_id": "synthetic-new-root"}, {"capability": "none"}, {"coverage": "partial"}):
            stores = registry()
            stores[0].update(changes)
            value = preview()
            with self.assertRaisesRegex(ContractError, "snapshot-drift"):
                lifecycle.confirm(value, confirmation(value), lifecycle.discover(context(), stores), 101, {})

    def test_tampering_even_with_recomputed_digest_fails_binding(self):
        value = preview()
        value["targets"][0]["revision"] = 2
        value["preview_digest"] = digest({k: v for k, v in value.items() if k != "preview_digest"})
        with self.assertRaisesRegex(ContractError, "preview-snapshot-mismatch"):
            lifecycle.confirm(value, confirmation(value), snapshot(), 101, {})

    def test_seen_request_requires_reconciliation_and_id_cannot_rebind(self):
        value = preview()
        seen = {value["request_id"]: value["preview_digest"]}
        answer = lifecycle.confirm(value, confirmation(value), snapshot(), 101, seen)
        self.assertEqual(answer["decision"], "reconciliation-required")
        self.assertEqual(answer["retry_targets"], [])
        self.assertFalse(answer["operation_authorized"])
        with self.assertRaisesRegex(ContractError, "request-id-reused"):
            lifecycle.confirm(value, confirmation(value), snapshot(), 101, {value["request_id"]: "b" * 64})

    def test_seen_request_does_not_skip_current_snapshot_validation(self):
        value = preview()
        with self.assertRaises(ContractError):
            lifecycle.confirm(value, confirmation(value), {}, 101, {value["request_id"]: value["preview_digest"]})


class OutcomeAndRetirementTests(unittest.TestCase):
    def test_partial_failure_retries_only_failed_targets(self):
        value = preview()
        outcomes = [{**row, "status": status} for row, status in
                    zip(selection(snapshot()), ("succeeded", "failed"))]
        answer = summarize(value, outcomes)
        self.assertEqual(answer["overall"], "incomplete")
        self.assertEqual([r["status"] for r in answer["retry_candidates"]], ["failed"])
        self.assertEqual(lifecycle.key(answer["retry_candidates"][0]), lifecycle.key(outcomes[1]))
        self.assertFalse(answer["all_copies_forgotten"])

    def test_unknown_and_missing_reports_require_reconciliation(self):
        answer = summarize(preview(), [{**selection(snapshot())[0], "status": "unknown"}])
        self.assertEqual(len(answer["reconcile_required"]), 2)
        self.assertEqual(answer["retry_candidates"], [])

    def test_only_explicit_not_executed_is_a_retry_candidate(self):
        row = {**selection(snapshot())[0], "status": "not-executed"}
        answer = summarize(preview(), [row])
        self.assertEqual([r["status"] for r in answer["retry_candidates"]], ["not-executed"])
        self.assertEqual(lifecycle.key(answer["retry_candidates"][0]), lifecycle.key(row))
        self.assertEqual(len(answer["reconcile_required"]), 1)

    def test_success_is_only_supplied_listed_scope_and_never_all_copies(self):
        value = preview()
        answer = summarize(value, [{**r, "status": "succeeded"} for r in selection(snapshot())])
        self.assertEqual(answer["overall"], "listed-targets-succeeded")
        self.assertEqual(answer["retry_candidates"], [])
        self.assertEqual(answer["external_copies"], "unknown")
        self.assertFalse(answer["all_copies_forgotten"])
        self.assertFalse(answer["runtime_proven"])
        self.assertEqual(answer["preview_digest"], value["preview_digest"])
        self.assertEqual(answer["request_id"], value["request_id"])
        for expected, actual in zip(value["targets"], answer["targets"]):
            for field in ("root_id", "revision", "content_digest", "state", "condition_id"):
                self.assertEqual(expected[field], actual[field])

    def test_unknown_duplicate_or_extra_outcomes_fail(self):
        row = {**selection(snapshot())[0], "status": "succeeded"}
        for outcomes in ([row, row], [{**row, "status": "rolled-back"}], [{**row, "item_id": "synthetic-other"}]):
            with self.assertRaises(ContractError):
                summarize(preview(), outcomes)

    def test_summary_rejects_tampered_preview_wrong_request_or_version(self):
        original = preview()
        changed = copy.deepcopy(original)
        changed["targets"][0]["revision"] = 2
        changed["preview_digest"] = digest({k: v for k, v in changed.items() if k != "preview_digest"})
        with self.assertRaises(ContractError):
            summarize(changed, [{**selection(snapshot())[0], "status": "succeeded"}])
        good = outcomes(original, [{**selection(snapshot())[0], "status": "succeeded"}])
        for field in ("principal_id", "request_id", "preview_digest"):
            bad = {**good, field: "synthetic-other"}
            with self.assertRaisesRegex(ContractError, "outcome-binding-mismatch"):
                lifecycle.summarize(original, confirmation(original), snapshot(), 101, bad)
        for changes in ({"revision": 2}, {"content_digest": "b" * 64}):
            bad = copy.deepcopy(good)
            bad["targets"][0].update(changes)
            with self.assertRaisesRegex(ContractError, "outcome-version-mismatch"):
                lifecycle.summarize(original, confirmation(original), snapshot(), 101, bad)

    def test_ui_rename_offline_and_worktree_events_never_trigger_cleanup(self):
        for event in ("ui-removed", "renamed", "offline", "worktree-removed"):
            answer = lifecycle.retirement(snapshot(), "synthetic-project", event)
            self.assertEqual(answer["decision"], "no-cleanup-authority")
            self.assertEqual(answer["candidates"], [])

    def test_explicit_retirement_separates_private_global_relation(self):
        answer = lifecycle.retirement(snapshot(), "synthetic-project", "explicit-retirement")
        self.assertEqual(len(answer["candidates"]), 1)
        self.assertEqual(answer["relation_review"][0]["scope"], "global")
        self.assertFalse(answer["operation_authorized"])

    def test_independent_global_knowledge_retained_only_without_private_content(self):
        for private, expected in ((False, 1), (True, 0)):
            stores = registry()
            stores[1]["matches"][0].update(independently_reusable=True, project_private=private)
            answer = lifecycle.retirement(lifecycle.discover(context(), stores), "synthetic-project", "explicit-retirement")
            self.assertEqual(len(answer["retain"]), expected)

    def test_cross_project_relation_and_native_never_cascade(self):
        stores = registry()
        stores[0]["matches"][0]["related_projects"].append("synthetic-other-project")
        stores[2].update(readable=True, coverage="complete", capability="native-management", matches=[match()])
        answer = lifecycle.retirement(lifecycle.discover(context(), stores), "synthetic-project", "explicit-retirement")
        self.assertEqual(answer["candidates"], [])
        self.assertEqual(len(answer["relation_review"]), 3)

    def test_unrelated_project_and_global_knowledge_are_excluded(self):
        stores = registry()
        stores[1]["matches"][0]["related_projects"] = []
        stores.append(store(store_id="synthetic-other", root_id="synthetic-other-root", project_id="synthetic-other-project",
                            matches=[match(related_projects=[])]))
        ctx = context()
        ctx["project_ids"].append("synthetic-other-project")
        ctx["requested_stores"].append("synthetic-other")
        answer = lifecycle.retirement(lifecycle.discover(ctx, stores), "synthetic-project", "explicit-retirement")
        self.assertEqual(len(answer["candidates"]), 1)
        self.assertEqual(answer["relation_review"], [])

    def test_unknown_project_or_event_fails(self):
        for project, event in (("synthetic-unknown", "explicit-retirement"), ("synthetic-project", "timeout")):
            with self.assertRaises(ContractError):
                lifecycle.retirement(snapshot(), project, event)

    def test_pure_functions_never_open_files_and_do_not_mutate_inputs(self):
        ctx, stores = context(), registry()
        before = copy.deepcopy((ctx, stores))
        with patch("builtins.open", side_effect=AssertionError("unexpected-file-io")), \
             patch("os.open", side_effect=AssertionError("unexpected-file-io")), \
             patch("socket.socket", side_effect=AssertionError("unexpected-network-io")):
            lifecycle.route(candidate())
            snap = lifecycle.discover(ctx, stores)
            value = preview(snap)
            frozen = copy.deepcopy((snap, value))
            lifecycle.confirm(value, confirmation(value), snap, 101, {})
            summarize(value, [])
            lifecycle.retirement(snap, "synthetic-project", "explicit-retirement")
            self.assertEqual((snap, value), frozen)
        self.assertEqual((ctx, stores), before)

    def test_malformed_json_shapes_do_not_escape_contract_errors(self):
        def paths(value, path=()):
            yield path
            if isinstance(value, dict):
                for name, child in value.items():
                    yield from paths(child, path + (name,))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    yield from paths(child, path + (index,))

        checks = [(candidate(), lifecycle.route),
                  (registry(), lambda value: lifecycle.discover(context(), value)),
                  (snapshot(), lifecycle.checked_snapshot), (preview(), lifecycle.checked_preview)]
        for original, operation in checks:
            for path in paths(original):
                for replacement in (None, True, False, 0, -1, 1.5, "", [], {}):
                    value = copy.deepcopy(original)
                    if path:
                        parent = value
                        for name in path[:-1]:
                            parent = parent[name]
                        parent[path[-1]] = replacement
                    else:
                        value = replacement
                    try:
                        answer = operation(value)
                    except ContractError:
                        continue
                    for field in ("operation_authorized", "runtime_proven", "write_performed"):
                        self.assertIs(answer[field], False)


if __name__ == "__main__":
    unittest.main()
