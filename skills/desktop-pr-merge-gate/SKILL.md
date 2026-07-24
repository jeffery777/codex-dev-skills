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
4. Return the shared gate's readiness summary without adding a second
   Desktop-specific decision.
5. Stop before committing, pushing, creating PRs, publishing, merging, deploying, posting platform comments, submitting reviews, or resolving platform threads unless the exact action is explicitly authorized.

## Output

- PR readiness
- Merge readiness
- Evidence summary
- Blockers
- External actions requiring human approval
- Compatibility route used: `merge-readiness-gate`
