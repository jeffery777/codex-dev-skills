---
name: docs-review-gate
description: Thin formal documentation review gate adapter around docs-review before commit, PR readiness, or merge readiness.
---

# docs-review-gate

Runtime compatibility: shared

## Purpose

Use this skill only when docs-only or docs-dominant changes need a formal documentation gate before commit readiness, PR readiness, or merge readiness.

For ordinary user-facing documentation review, use `docs-review` directly.

This gate is a thin adapter around `docs-review`. It is responsible for evidence capture and the blocking decision; it is not a separate documentation review primitive.

## Workflow

1. Confirm docs scope.
2. Run `docs-review` as the underlying review primitive.
3. Give every MUST-FIX, SHOULD-FIX, and NIT a stable finding id and record one disposition: `Fixed`, `Deferred`, `Rejected`, or `Needs Human Decision`.
4. For every deferred item, record a durable target, owner, reason, remaining risk, verification plan, and promotion trigger.
5. Check for private paths, local runtime state, unsupported claims, and stale instructions, then rerun `docs-review` against the final diff.
6. Block commit, PR, or merge readiness when a MUST-FIX remains unresolved, any finding lacks a durable disposition, a deferred item lacks required follow-up fields, or a `Needs Human Decision` item remains open.

NITS are non-blocking only after explicit disposition; they must not disappear from the gate evidence.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Findings
- Finding Dispositions
- Evidence
- Required Follow-up
