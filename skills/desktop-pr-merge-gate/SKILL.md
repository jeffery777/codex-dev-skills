---
description: Codex Desktop PR and merge readiness gate that summarizes evidence without publishing or merging.
---

# desktop-pr-merge-gate

Runtime compatibility: desktop

## Purpose

Use this skill before PR readiness, platform publication, or merge decisions in a Desktop-orchestrated project.

## CLI Fallback

Use `merge-readiness-gate` and platform-specific tools only when explicitly authorized.

## Workflow

1. Confirm branch, base, head, changed files, and repository identity.
2. Gather verification, review, docs, and implementation evidence.
3. Run `merge-readiness-gate`.
4. Prepare a readiness summary.
5. Stop before committing, pushing, creating PRs, publishing, merging, deploying, posting platform comments, submitting reviews, or resolving platform threads unless the exact action is explicitly authorized.

## Output

- PR readiness
- Merge readiness
- Evidence summary
- Blockers
- External actions requiring human approval
