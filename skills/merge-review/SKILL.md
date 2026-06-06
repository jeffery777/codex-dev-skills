---
description: Normal user-facing entry point for base-to-head merge quality and DoD review.
---

# merge-review

Runtime compatibility: shared

## Purpose

Use this skill for ordinary base-to-head merge quality and DoD review.

This is the normal user-facing merge review entry point. It reports review evidence and residual risk, but it is not a formal branch readiness gate and does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Workflow

1. Confirm base and head.
2. Read repo instructions, plan, DoD, prior reviews, and verification evidence.
3. Inspect the diff for scope alignment, missing tests, regressions, and unresolved review findings.
4. Check that docs, migrations, and operational notes are updated when required.
5. Report readiness with evidence and residual risk.

## Output

- Merge Readiness: Ready | Not Ready | Needs Human Decision
- Blocking Findings
- Non-blocking Findings
- DoD Alignment
- Verification Evidence
- Residual Risk
