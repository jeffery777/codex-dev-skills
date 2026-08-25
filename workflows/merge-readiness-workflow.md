# Merge Readiness Workflow

Runtime compatibility: shared

Use this workflow only when a formal branch readiness gate is needed before PR handoff, merge readiness, or final human approval.

When a PR exists, follow `policies/exact-head-merge-review-contract.md`.

For ordinary base-to-head merge quality and DoD review, use `merge-review`. For high-risk, release-sensitive, or policy-required changes, use `merge-review-deep`. This workflow consumes that review evidence and reports a formal readiness decision; it is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

1. Confirm repository, PR number, exact base/head/merge-base SHAs, changed
   files, and diff identity.
2. Read plans, DoD, prior reviews, current `merge-review` or `merge-review-deep` evidence, verification output, and unresolved questions.
3. If current PR-bound exact-head review evidence is missing, run or request
   `merge-review` or `merge-review-deep` based on risk. Pre-commit review
   evidence cannot supply the exact-head verdict.
4. Verify successful exact-head hosted CI, findings closure, zero unresolved
   review threads, and an authorized platform-visible receipt whose connector
   readback validates as `exact-head-merge-review/v1`.
5. Check docs, migration notes, release notes, or operational evidence when applicable. For release-sensitive work, apply `policies/release-state-contract.md`: keep source/package version, candidate preparation, GitHub publication truth, active guidance, and historical records distinct; block mutable tracked publication claims even when tests pass.
6. Decide gate result: READY, BLOCKED, or NEEDS HUMAN DECISION. Missing or stale
   repository/PR/base/head/merge-base/diff/CI/thread/receipt evidence is BLOCKED.
7. Stop before commit, push, merge, deploy, platform comments, review submissions, or publication unless the user explicitly authorized the exact action.
8. Before any authorized merge or platform-side mutation, repeat the live
   platform readback and confirm all bindings still match and no blocker remains.
