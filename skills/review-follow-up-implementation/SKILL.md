---
description: Apply minimal code or mixed-diff fixes from review findings and prepare an item-by-item reply draft.
---

# review-follow-up-implementation

Runtime compatibility: shared

## Purpose

Use this skill to address code or mixed-diff review findings after `code-review`, `code-review-deep`, or `code-review-gate`.

## Workflow

1. Read repo instructions, current git state, latest review report, and relevant files.
2. Triage findings into fix now, defer, answer, withdrawn, or needs human decision.
3. Apply the smallest scoped fix for accepted items.
4. Run relevant verification for touched files.
5. Inspect the diff.
6. Prepare an item-by-item review reply draft.

## Output

- Review report used
- Changes by file
- Finding disposition
- Verification results
- Deferred items with reason and risk
- Reply draft

## Rules

- Do not expand scope beyond review findings.
- Do not use merge-stage or platform-comment assumptions unless explicitly requested.
- Do not commit, publish, or merge unless separately authorized.
