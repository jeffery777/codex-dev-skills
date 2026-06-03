---
description: Deep merge readiness gate for high-risk, release-sensitive, or policy-required changes.
---

# merge-review-deep

Runtime compatibility: shared

## Purpose

Use this skill for final or high-risk merge readiness where routine review is insufficient.

## Additional Focus

- closure quality for prior findings
- rollback or recovery path
- security and privacy readiness
- data or migration safety
- stale artifact reuse
- hidden regression risk
- release and operational evidence

## Workflow

Follow `merge-review`, then re-check evidence from source files and commands rather than relying only on summaries.

## Output

Use the `merge-review` output structure and add Deep Gate Notes.
