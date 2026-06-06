---
description: Higher-scrutiny merge review for high-risk, release-sensitive, or policy-required changes.
---

# merge-review-deep

Runtime compatibility: shared

## Purpose

Use this skill for high-risk, release-sensitive, or policy-required merge review where routine `merge-review` is insufficient.

This is a deeper review primitive, not the formal branch readiness gate. Use `merge-readiness-gate` when a workflow must summarize evidence into a branch readiness decision before PR handoff, merge readiness, or final human approval. The deep review result is evidence only; it does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

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
