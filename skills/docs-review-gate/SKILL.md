---
description: Formal documentation review gate before commit, PR readiness, or merge readiness.
---

# docs-review-gate

Runtime compatibility: shared

## Purpose

Use this skill when docs-only or docs-dominant changes need a formal review gate.

## Workflow

1. Confirm docs scope.
2. Run `docs-review`.
3. Check for private paths, local runtime state, unsupported claims, and stale instructions.
4. Block commit or merge readiness on MUST-FIX findings.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Findings
- Evidence
- Required Follow-up
