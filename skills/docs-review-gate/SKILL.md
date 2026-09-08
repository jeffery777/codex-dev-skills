---
name: docs-review-gate
description: Thin formal documentation review gate adapter around docs-review before commit, PR readiness, or merge readiness.
---

# docs-review-gate

Runtime compatibility: shared

執行方式選用：先讀 `../../policies/reusable-workflow-contract.md` 的
`Contract-Preserving Capability Selection`；本地安裝改讀
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。
可重用契約相容的原生／內建／本地執行結果；本技能的必要步驟、證據與輸出仍適用。

## Purpose

Use this skill only when docs-only or docs-dominant changes need a formal documentation gate before commit readiness, PR readiness, or merge readiness.

For ordinary user-facing documentation review, use `docs-review` directly.

This gate is a thin adapter around `docs-review`. It is responsible for evidence capture and the blocking decision; it is not a separate documentation review primitive.

## Workflow

1. Confirm docs scope.
2. Reuse an existing `docs-review` result when its revision or worktree diff identity, scope, source assumptions and verification evidence still match; otherwise run that primitive once.
3. Give every MUST-FIX, SHOULD-FIX, and NIT a stable finding id and record one disposition: `Fixed`, `Deferred`, `Rejected`, or `Needs Human Decision`.
4. For every deferred item, record a durable target, owner, reason, remaining risk, verification plan, and promotion trigger.
5. Ensure the review covers private paths, local runtime state, unsupported claims and stale instructions. After fixes or changed assumptions, rerun `docs-review` over the affected scope and verify dispositions against the final diff; unchanged evidence does not require a second review merely to enter this gate.
6. Block commit, PR, or merge readiness when a MUST-FIX remains unresolved, any finding lacks a durable disposition, a deferred item lacks required follow-up fields, or a `Needs Human Decision` item remains open.

NITS are non-blocking only after explicit disposition; they must not disappear from the gate evidence.

Shared rationale may cover a batch of NITs when every finding id remains
traceable. Reused pre-commit evidence never replaces complete base-to-head
exact-head Merge Review for a new change-request head.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Findings
- Finding Dispositions
- Evidence
- Required Follow-up
