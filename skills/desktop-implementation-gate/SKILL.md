---
description: Codex Desktop integration gate for worker outputs and review-before-commit.
---

# desktop-implementation-gate

Runtime compatibility: desktop

## Purpose

Use this skill after workers produce implementation output and before commit readiness.

## CLI Fallback

Use `implementation-slice` followed by `code-review-gate` or `docs-review-gate`.

## Workflow

1. Inspect git state and changed files.
2. Verify worker output matches assigned ownership.
3. Detect overlapping edits, missing files, deleted tests, generated artifacts, and unexpected scope.
4. Run relevant verification.
5. Route docs-only changes to `docs-review-gate`; route code or mixed changes to `code-review-gate`.
6. Block commit readiness on unresolved MUST-FIX findings.

## Output

- Integration result
- Ownership checks
- Verification evidence
- Review gate result
- Commit readiness
