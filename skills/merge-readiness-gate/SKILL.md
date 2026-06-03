---
description: Formal branch readiness gate after implementation, verification, and review evidence exist.
---

# merge-readiness-gate

Runtime compatibility: shared

## Purpose

Use this skill when deciding whether a branch is ready to publish, hand off, or merge.

## Workflow

1. Confirm base, head, remote identity when relevant, and changed files.
2. Read plan, DoD, review reports, verification evidence, and unresolved questions.
3. Run `merge-review` or `merge-review-deep` based on risk.
4. Verify that MUST-FIX findings are closed with evidence.
5. Stop for final human approval before merge, deploy, destructive actions, or external publication unless the user has explicitly authorized the exact action.

## Output

- Gate Result: READY | BLOCKED | NEEDS HUMAN DECISION
- Base and head
- Evidence reviewed
- Blockers
- Residual risk
- Next approved action
