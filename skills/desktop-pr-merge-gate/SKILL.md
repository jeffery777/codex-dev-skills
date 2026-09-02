---
name: desktop-pr-merge-gate
description: Deprecated Desktop compatibility alias that routes PR and merge readiness to the shared merge-readiness gate.
---

# desktop-pr-merge-gate

Runtime compatibility: desktop

Compatibility status: deprecated compatibility alias

## Purpose

This name is retained so existing prompts and installations continue to work.
It does not use a Desktop callable or define a Desktop-specific merge decision.
New callers should use `merge-readiness-gate` directly.

## CLI Fallback

Use `merge-readiness-gate` and platform-specific tools only when explicitly
authorized. The readiness behavior is the same because the authoritative gate
is shared.

## Workflow

1. Confirm branch, base, head, changed files, and repository identity.
2. Gather verification, review, docs, and implementation evidence.
3. Run `merge-readiness-gate`.
4. For an existing change request, preserve the shared
   `exact-head-merge-review-contract.md` requirement. Pre-commit review
   evidence cannot replace exact-head content Merge Review. Report optional
   provider enforcement separately.
5. Return the shared gate's readiness summary without adding a second
   Desktop-specific decision.
6. Stop before committing, pushing, creating PRs, publishing, merging, deploying, posting platform comments, submitting reviews, or resolving platform threads unless the exact action is explicitly authorized.

## Output

- Change-request readiness
- Merge readiness
- Evidence summary
- Blockers
- External actions requiring human approval
- Compatibility route used: `merge-readiness-gate`
