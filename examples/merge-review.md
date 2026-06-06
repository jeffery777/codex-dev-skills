# Merge Review Examples

Use `merge-review` for the normal base-to-head merge quality and DoD review:

```text
Use merge-review for main..HEAD.
Check scope alignment, verification evidence, docs, unresolved review findings, and residual risk. Stay read-only.
```

The result is review evidence, not authority to commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes.

Use `merge-review-deep` when the diff is high-risk, release-sensitive, or policy-required:

```text
Use merge-review-deep for main..HEAD.
Re-check closure evidence, rollback path, security/privacy, migration safety, release notes, and hidden regression risk. Stay read-only.
```

Use `merge-readiness-gate` only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval:

```text
Use merge-readiness-gate for main..HEAD.
Read the current merge-review or merge-review-deep evidence, summarize blockers and residual risk, and report READY, BLOCKED, or NEEDS HUMAN DECISION. Do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

The gate is a thin evidence-and-decision layer. It is not another merge review primitive and does not automatically authorize merge or any other external write. Before an authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.
