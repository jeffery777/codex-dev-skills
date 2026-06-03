---
description: Routine merge readiness review for base-to-head changes.
---

# merge-review

Runtime compatibility: shared

## Purpose

Use this skill to decide whether a branch appears ready for PR or merge review from a quality and DoD perspective.

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
