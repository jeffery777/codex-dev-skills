---
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
3. Record review evidence relevant to the requested readiness decision.
4. Check for private paths, local runtime state, unsupported claims, and stale instructions.
5. Block commit, PR, or merge readiness on unresolved MUST-FIX findings.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Findings
- Evidence
- Required Follow-up
