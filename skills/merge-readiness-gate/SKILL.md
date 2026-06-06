---
description: Thin formal branch readiness gate after implementation, verification, and review evidence exist.
---

# merge-readiness-gate

Runtime compatibility: shared

## Purpose

Use this skill only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval.

This gate is a thin adapter and evidence-and-decision layer around existing review primitives. It summarizes verification, review evidence, blocking decisions, residual risk, and the human approval boundary. It is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Workflow

1. Confirm base, head, remote identity when relevant, and changed files.
2. Read plan, DoD, review reports, verification evidence, and unresolved questions.
3. Run or read the current `merge-review` or `merge-review-deep` evidence based on risk.
4. Verify that MUST-FIX findings are closed with evidence.
5. Stop for final human approval before commit, push, merge, deploy, destructive actions, platform comments, review submissions, or external publication unless the user has explicitly authorized the exact action.
6. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.

## Output

- Gate Result: READY | BLOCKED | NEEDS HUMAN DECISION
- Base and head
- Evidence reviewed
- Blockers
- Residual risk
- Human approval boundary
- Next human decision or action boundary
