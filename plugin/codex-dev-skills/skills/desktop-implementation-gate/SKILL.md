---
name: desktop-implementation-gate
description: Deprecated Desktop compatibility alias that routes integration review and readiness to shared review skills.
---

# desktop-implementation-gate

Runtime compatibility: desktop

Compatibility status: deprecated compatibility alias

## Purpose

This name is retained so existing prompts and installations continue to work.
It does not use a Desktop callable or create a distinct Desktop integration
decision. New callers should use shared review primitives and formal gates
directly.

## CLI Fallback

Use `implementation-slice` followed by `code-review`, `code-review-deep` for
high-risk code or mixed changes, or `docs-review`. Use `code-review-gate` or
`docs-review-gate` only when a formal commit readiness, PR readiness, merge
readiness, or repo-policy blocking decision is required. The behavior is the
same because these capabilities are shared.

## Workflow

1. Apply the shared multi-agent integration policy to ownership and overlap
   checks, then inspect git state and changed files.
2. Run relevant verification.
3. Route ordinary integrated output to `docs-review` for docs-only or
   docs-dominant changes, `code-review` for ordinary code or mixed changes, or
   `code-review-deep` for high-risk code or mixed changes.
4. Route to `docs-review-gate` or `code-review-gate` only when the current stage
   requires a formal blocking decision.
5. Block commit readiness on unresolved MUST-FIX findings.

## Output

- Integration result
- Ownership checks
- Verification evidence
- Review evidence
- Formal gate result, when `code-review-gate` or `docs-review-gate` was run
- Commit readiness
- Compatibility route used
