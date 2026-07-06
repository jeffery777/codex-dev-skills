---
name: desktop-implementation-gate
description: Codex Desktop formal integration gate for worker outputs before commit readiness.
---

# desktop-implementation-gate

Runtime compatibility: desktop

## Purpose

Use this skill after workers produce implementation output when the main agent needs a formal integration gate before commit readiness. For ordinary integrated output review evidence, use `code-review`, `code-review-deep`, or `docs-review` first.

## CLI Fallback

Use `implementation-slice` followed by `code-review`, `code-review-deep` for high-risk code or mixed changes, or `docs-review`. Use `code-review-gate` or `docs-review-gate` only when a formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decision is required.

## Workflow

1. Inspect git state and changed files.
2. Verify worker output matches assigned ownership.
3. Detect overlapping edits, missing files, deleted tests, generated artifacts, and unexpected scope.
4. Run relevant verification.
5. Confirm integrated output review evidence exists from `docs-review` for docs-only or docs-dominant changes, `code-review` for ordinary code or mixed changes, or `code-review-deep` for high-risk code or mixed changes.
6. Route to `docs-review-gate` or `code-review-gate` only when the current stage requires a formal blocking decision.
7. Block commit readiness on unresolved MUST-FIX findings.

## Output

- Integration result
- Ownership checks
- Verification evidence
- Review evidence
- Formal gate result, when `code-review-gate` or `docs-review-gate` was run
- Commit readiness
