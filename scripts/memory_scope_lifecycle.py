"""Issue #231 的純 metadata 合成 oracle；沒有 I/O、backend 或執行授權。"""

from __future__ import annotations

import copy

from memory_governance_g0 import (
    choice, digest, digest_text, fields, identifier, integer, require, sequence,
)

VERSION = "memory-scope-lifecycle-synthetic/v0"
# 僅為合成案例預算，不是 G0 profile 或生產預設。
MAX_STORES = 8
MAX_MATCHES = 32
MAX_TARGETS = 8
CONFIRMATION_SECONDS = 300
OBSERVATION_SECONDS = 60
BACKENDS = {"managed", "document", "native"}
COVERAGE = {"complete", "partial", "unknown", "unavailable"}
OUTCOMES = {"succeeded", "not-executed", "failed", "unknown"}


def result(**values: object) -> dict:
    return copy.deepcopy({
        **values, "schema_version": VERSION, "operation_authorized": False,
        "runtime_proven": False, "write_performed": False,
    })


def boolean(value: object) -> bool:
    require(type(value) is bool, "invalid-boolean")
    return value


def ids(value: object, maximum: int) -> list:
    value = sequence(value, maximum)
    for item in value:
        identifier(item)
    require(len(set(value)) == len(value), "duplicate-id")
    return value


def route(candidate: dict) -> dict:
    """驗證結構化路由聲明；不解析自然語言，也不讀取來源。"""
    c = fields(candidate, {
        "content_id", "requested_scope", "project_id", "backend", "kind",
        "source_id", "verified", "reusable", "project_private", "now", "valid_until",
    })
    identifier(c["content_id"])
    scope = choice(c["requested_scope"], {"unspecified", "global", "project"})
    backend = choice(c["backend"], BACKENDS | {"unspecified"})
    kind = choice(c["kind"], {"procedure", "fact", "rule"})
    for key in ("verified", "reusable", "project_private"):
        boolean(c[key])
    for key in ("source_id", "project_id"):
        if c[key] is not None:
            identifier(c[key])
    now, until = integer(c["now"]), integer(c["valid_until"])
    decision, reason = "preview-only", "single-destination"
    if not c["verified"] or c["source_id"] is None or until <= now:
        decision, reason = "needs-evidence", "source-unverified-or-stale"
    elif scope == "global" and (c["project_private"] or not c["reusable"]):
        decision, reason = "needs-clarification", "visibility-or-applicability"
    elif scope == "unspecified":
        if c["reusable"] and not c["project_private"]:
            scope = "global"
        elif c["project_private"] and c["project_id"] is not None:
            scope = "project"
        else:
            decision, reason = "needs-clarification", "ambiguous-scope"
    if decision == "preview-only":
        if scope == "project" and c["project_id"] is None:
            decision, reason = "needs-clarification", "missing-project-identity"
        elif kind == "rule" and backend not in {"document", "unspecified"}:
            decision, reason = "needs-clarification", "rules-require-governed-document"
        else:
            if backend == "unspecified":
                if kind == "rule" or (scope == "global" and kind == "procedure"):
                    backend = "document"
                else:
                    decision, reason = "needs-clarification", "ambiguous-backend"
            if backend == "native":
                decision, reason = "runtime-management-required", "native-owned"
            elif backend == "managed" and scope == "global":
                decision, reason = "design-decision-required", "global-backend-unaccepted"
    return result(decision=decision, reason=reason, content_id=c["content_id"],
                  scope=scope, project_id=c["project_id"] if scope == "project" else None,
                  backend=backend, source_id=c["source_id"], valid_until=until)


def key(target: dict) -> tuple[str, str]:
    return target["store_id"], target["item_id"]


def state_digest(snapshot: dict) -> str:
    """綁定狀態與查詢範圍；允許同狀態的新時間觀察。"""
    return digest({k: v for k, v in snapshot.items() if k not in {"observed_at", "valid_until"}})


def fresh(snapshot: dict, now: int) -> None:
    require(snapshot["observed_at"] <= integer(now) < snapshot["valid_until"], "stale-observation")


def discover(context: dict, stores: list) -> dict:
    """校驗已供應的查詢結果，不搜尋磁碟；缺席儲存一律 unknown。"""
    fields(context, {"principal_id", "project_ids", "requested_stores", "observed_at", "valid_until"})
    principal = identifier(context["principal_id"])
    projects = ids(context["project_ids"], MAX_STORES)
    requested = ids(context["requested_stores"], MAX_STORES)
    require(bool(requested), "empty-search-scope")
    observed = integer(context["observed_at"])
    until = integer(context["valid_until"])
    require(observed < until <= observed + OBSERVATION_SECONDS, "invalid-observation-window")
    registry, roots = {}, set()
    for store in sequence(stores, MAX_STORES):
        fields(store, {"store_id", "root_id", "principal_id", "scope", "project_id", "backend",
                       "readable", "capability", "coverage", "matches"})
        sid = identifier(store["store_id"])
        root_id = identifier(store["root_id"])
        require(root_id not in roots, "duplicate-root-alias")
        roots.add(root_id)
        require(sid not in registry, "duplicate-store")
        require(sid in requested, "unrequested-store")
        require(identifier(store["principal_id"]) == principal, "principal-mismatch")
        scope = choice(store["scope"], {"global", "project"})
        if scope == "global":
            require(store["project_id"] is None, "global-project-mismatch")
        else:
            require(identifier(store["project_id"]) in projects, "project-out-of-scope")
        choice(store["backend"], BACKENDS)
        readable = boolean(store["readable"])
        coverage = choice(store["coverage"], COVERAGE)
        capability = choice(store["capability"], {"none", "managed-erase", "document-edit", "native-management"})
        allowed = {"managed": {"none", "managed-erase"},
                   "document": {"none", "document-edit"},
                   "native": {"none", "native-management"}}
        require(capability in allowed[store["backend"]], "backend-capability-mismatch")
        matches = sequence(store["matches"], MAX_MATCHES)
        if not readable or coverage in {"unknown", "unavailable"}:
            require(not matches and capability == "none", "unreadable-results")
        if not readable:
            require(coverage in {"unknown", "unavailable"}, "unreadable-coverage")
        seen = set()
        for match in matches:
            fields(match, {"item_id", "revision", "state", "content_digest", "summary_id", "source_id",
                           "condition_id", "match", "related_projects", "independently_reusable",
                           "project_private"})
            item_id = identifier(match["item_id"])
            require(item_id not in seen, "duplicate-item")
            seen.add(item_id)
            integer(match["revision"], 1)
            choice(match["state"], {"active", "stopped", "pending", "erased"})
            digest_text(match["content_digest"])
            for field in ("summary_id", "source_id", "condition_id"):
                identifier(match[field])
            choice(match["match"], {"exact", "semantic"})
            ids(match["related_projects"], MAX_STORES)
            boolean(match["independently_reusable"])
            boolean(match["project_private"])
        registry[sid] = store
    targets, coverage = [], []
    for sid in sorted(requested):
        store = registry.get(sid)
        coverage.append({"store_id": sid, "status": store["coverage"] if store else "unknown"})
        if store:
            for match in store["matches"]:
                targets.append({**{k: store[k] for k in (
                    "store_id", "root_id", "principal_id", "scope", "project_id", "backend", "capability",
                )}, **match})
    require(len(targets) <= MAX_MATCHES, "search-budget-exceeded")
    return result(principal_id=principal, project_ids=sorted(projects),
                  observed_at=observed, valid_until=until,
                  coverage=coverage, targets=sorted(targets, key=key),
                  registrations=[{k: v for k, v in registry[sid].items() if k != "matches"}
                                 for sid in sorted(registry)],
                  external_copies="unknown", coverage_scope="requested-registered-stores-only")


def checked_snapshot(snapshot: dict) -> dict:
    """重新建構 canonical snapshot，拒絕偽造 flags、scope 與結果欄位。"""
    fields(snapshot, {"schema_version", "operation_authorized", "runtime_proven", "write_performed",
                      "principal_id", "project_ids", "coverage", "targets", "registrations",
                      "external_copies", "coverage_scope", "observed_at", "valid_until"})
    requested = []
    for coverage in sequence(snapshot["coverage"], MAX_STORES):
        fields(coverage, {"store_id", "status"})
        sid = identifier(coverage["store_id"])
        require(sid not in requested, "duplicate-store")
        choice(coverage["status"], COVERAGE)
        requested.append(sid)
    stores = {}
    for registration in sequence(snapshot["registrations"], MAX_STORES):
        fields(registration, {"store_id", "root_id", "principal_id", "scope", "project_id", "backend",
                              "readable", "capability", "coverage"})
        sid = identifier(registration["store_id"])
        require(sid not in stores, "duplicate-store")
        stores[sid] = {**registration, "matches": []}
    matches = sequence(snapshot["targets"], MAX_MATCHES)
    metadata = {"store_id", "root_id", "principal_id", "scope", "project_id", "backend", "capability"}
    match_fields = {"item_id", "revision", "state", "content_digest", "summary_id", "source_id", "condition_id",
                    "match", "related_projects", "independently_reusable", "project_private"}
    for target in matches:
        fields(target, metadata | match_fields)
        sid = identifier(target["store_id"])
        require(sid in stores, "unregistered-target")
        meta = {k: target[k] for k in metadata}
        require(all(stores[sid][k] == v for k, v in meta.items()), "store-metadata-mismatch")
        stores[sid]["matches"].append({k: target[k] for k in match_fields})
    rebuilt = discover({"principal_id": snapshot["principal_id"], "project_ids": snapshot["project_ids"],
                        "requested_stores": requested, "observed_at": snapshot["observed_at"],
                        "valid_until": snapshot["valid_until"]}, list(stores.values()))
    require(digest(rebuilt) == digest(snapshot), "invalid-snapshot")
    return rebuilt


def preview(snapshot: dict, selected: list, request_id: str, now: int, expires_at: int) -> dict:
    snapshot = checked_snapshot(snapshot)
    identifier(request_id)
    integer(now)
    fresh(snapshot, now)
    require(now < integer(expires_at) <= now + CONFIRMATION_SECONDS, "invalid-expiry")
    targets = {key(t): t for t in snapshot["targets"]}
    selected_keys = []
    for selection in sequence(selected, MAX_TARGETS):
        fields(selection, {"store_id", "item_id"})
        selected_keys.append((identifier(selection["store_id"]), identifier(selection["item_id"])))
    require(bool(selected_keys) and len(set(selected_keys)) == len(selected_keys), "invalid-selection")
    require(all(k in targets for k in selected_keys), "unlisted-target")
    chosen = [targets[k] for k in sorted(selected_keys)]
    require(all(t["capability"] != "none" for t in chosen), "target-unavailable")
    require(all(t["state"] in {"active", "stopped"} for t in chosen), "target-needs-reconciliation")
    body = result(principal_id=snapshot["principal_id"], request_id=request_id,
                  issued_at=now, expires_at=expires_at, operation="erase-listed-content",
                  snapshot_digest=state_digest(snapshot), targets=chosen, coverage=snapshot["coverage"],
                  snapshot_observed_at=snapshot["observed_at"], snapshot_valid_until=snapshot["valid_until"],
                  registrations=snapshot["registrations"], project_ids=snapshot["project_ids"],
                  external_copies="unknown")
    return {**body, "preview_digest": digest(body)}


def checked_preview(value: dict) -> dict:
    fields(value, {"schema_version", "operation_authorized", "runtime_proven", "write_performed",
                   "principal_id", "request_id", "issued_at", "expires_at", "operation",
                   "snapshot_digest", "targets", "coverage", "registrations", "project_ids",
                   "external_copies", "preview_digest", "snapshot_observed_at", "snapshot_valid_until"})
    require(value["schema_version"] == VERSION and value["operation"] == "erase-listed-content",
            "invalid-preview")
    for field in ("operation_authorized", "runtime_proven", "write_performed"):
        require(value[field] is False, "invalid-authority-claim")
    identifier(value["principal_id"])
    identifier(value["request_id"])
    now = integer(value["issued_at"])
    require(now < integer(value["expires_at"]) <= now + CONFIRMATION_SECONDS, "invalid-expiry")
    digest_text(value["snapshot_digest"])
    require(digest({k: v for k, v in value.items() if k != "preview_digest"}) ==
            digest_text(value["preview_digest"]), "preview-digest-mismatch")
    # 用 canonical snapshot 驗證 targets 的全部 shape、principal、唯一性及能力。
    sequence(value["targets"], MAX_TARGETS)
    synthetic = result(principal_id=value["principal_id"], project_ids=value["project_ids"],
                       observed_at=value["snapshot_observed_at"], valid_until=value["snapshot_valid_until"],
                       coverage=value["coverage"], targets=value["targets"],
                       registrations=value["registrations"],
                       external_copies=value["external_copies"],
                       coverage_scope="requested-registered-stores-only")
    checked_snapshot(synthetic)
    fresh(synthetic, value["issued_at"])
    require(0 < len(value["targets"]) <= MAX_TARGETS and
            all(t["capability"] != "none" and t["state"] in {"active", "stopped"}
                for t in value["targets"]), "invalid-selection")
    return value


def confirm(value: dict, confirmation: dict, current: dict, now: int, seen: dict) -> dict:
    """只核對聲明。seen 是合成 replay 輸入，hash 不構成可信人類授權。"""
    value = checked_preview(value)
    fields(confirmation, {"principal_id", "request_id", "preview_digest"})
    require(confirmation == {k: value[k] for k in confirmation}, "confirmation-mismatch")
    require(value["issued_at"] <= integer(now) < value["expires_at"], "confirmation-expired")
    current = checked_snapshot(current)
    fresh(current, now)
    require(current["observed_at"] >= value["issued_at"], "readback-before-preview")
    require(current["principal_id"] == value["principal_id"], "principal-mismatch")
    require(type(seen) is dict and len(seen) <= MAX_MATCHES, "invalid-replay-state")
    for request_id, bound_digest in seen.items():
        identifier(request_id)
        digest_text(bound_digest)
    previous = seen.get(value["request_id"])
    if previous is not None:
        require(previous == value["preview_digest"], "request-id-reused")
        return result(decision="reconciliation-required", reason="request-seen-outcome-unknown",
                      request_id=value["request_id"], preview_digest=value["preview_digest"], retry_targets=[])
    require(state_digest(current) == value["snapshot_digest"], "snapshot-drift")
    # 重建原預覽的時間欄位；current 已獨立通過新鮮度與狀態檢查。
    original_time = {**current, "observed_at": value["snapshot_observed_at"],
                     "valid_until": value["snapshot_valid_until"]}
    regenerated = preview(original_time, [{k: t[k] for k in ("store_id", "item_id")} for t in value["targets"]],
                          value["request_id"], value["issued_at"], value["expires_at"])
    require(regenerated == value, "preview-snapshot-mismatch")
    return result(decision="confirmation-consistent", retry_targets=[])


def summarize(value: dict, confirmation: dict, execution_snapshot: dict,
              executed_at: int, outcomes: dict) -> dict:
    """彙整 supplied outcomes；沒有交易、重試、回滾或刪除證明。"""
    confirm(value, confirmation, execution_snapshot, executed_at, {})
    fields(outcomes, {"principal_id", "request_id", "preview_digest", "targets"})
    require(all(outcomes[k] == value[k] for k in ("principal_id", "request_id", "preview_digest")),
            "outcome-binding-mismatch")
    targets = {key(t): t for t in value["targets"]}
    supplied = {}
    for outcome in sequence(outcomes["targets"], MAX_TARGETS):
        fields(outcome, {"store_id", "item_id", "revision", "content_digest", "status"})
        target = (identifier(outcome["store_id"]), identifier(outcome["item_id"]))
        require(target in targets and target not in supplied, "unexpected-outcome")
        require(integer(outcome["revision"], 1) == targets[target]["revision"] and
                digest_text(outcome["content_digest"]) == targets[target]["content_digest"],
                "outcome-version-mismatch")
        supplied[target] = choice(outcome["status"], OUTCOMES)
    rows = [{**targets[k], "status": supplied.get(k, "unknown")} for k in sorted(targets)]
    statuses = {row["status"] for row in rows}
    overall = "listed-targets-succeeded" if statuses == {"succeeded"} else "incomplete"
    return result(overall=overall, targets=rows,
                  principal_id=value["principal_id"], request_id=value["request_id"],
                  preview_digest=value["preview_digest"], snapshot_digest=value["snapshot_digest"],
                  executed_at=executed_at, coverage=value["coverage"],
                  retry_candidates=[r for r in rows if r["status"] in {"failed", "not-executed"}],
                  reconcile_required=[r for r in rows if r["status"] == "unknown"],
                  external_copies="unknown", all_copies_forgotten=False)


def retirement(snapshot: dict, project_id: str, event: str) -> dict:
    """退場只產生分類；明確退場也必須再走固定集合預覽，不 cascade。"""
    snapshot = checked_snapshot(snapshot)
    require(identifier(project_id) in snapshot["project_ids"], "project-out-of-scope")
    choice(event, {"ui-removed", "renamed", "offline", "worktree-removed", "explicit-retirement"})
    if event != "explicit-retirement":
        return result(decision="no-cleanup-authority", candidates=[], relation_review=[], retain=[])
    candidates, review, retain = [], [], []
    for target in snapshot["targets"]:
        own = target["scope"] == "project" and target["project_id"] == project_id
        related = project_id in target["related_projects"]
        if not own and not related:
            continue
        if target["backend"] == "native" or (not own and target["scope"] == "project"):
            review.append(target)
        elif target["scope"] == "global":
            if target["independently_reusable"] and not target["project_private"]:
                retain.append(target)
            else:
                review.append(target)
        elif set(target["related_projects"]) - {project_id}:
            review.append(target)
        elif (target["backend"] == "managed" and target["capability"] == "managed-erase"
              and target["state"] in {"active", "stopped"}):
            candidates.append(target)
        else:
            review.append(target)
    return result(decision="preview-required", candidates=candidates,
                  relation_review=review, retain=retain, coverage=snapshot["coverage"],
                  external_copies="unknown")
