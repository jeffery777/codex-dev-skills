# Merge Readiness Workflow

Runtime compatibility: shared

Use this workflow only when a formal branch readiness gate is needed before PR handoff, merge readiness, or final human approval.

For ordinary base-to-head merge quality and DoD review, use `merge-review`. For high-risk, release-sensitive, or policy-required changes, use `merge-review-deep`. This workflow consumes that review evidence and reports a formal readiness decision; it is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

1. Confirm base, head, repository identity, and changed files.
2. Read plans, DoD, prior reviews, current `merge-review` or `merge-review-deep` evidence, verification output, and unresolved questions.
3. If current merge review evidence is missing, run or request `merge-review` or `merge-review-deep` based on risk before making the gate decision.
4. Verify that blockers were fixed with evidence.
5. Check docs, migration notes, release notes, or operational evidence when applicable.
6. Decide gate result: READY, BLOCKED, or NEEDS HUMAN DECISION.
7. Stop before commit, push, merge, deploy, platform comments, review submissions, or publication unless the user explicitly authorized the exact action.
8. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.
