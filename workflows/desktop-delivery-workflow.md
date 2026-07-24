# Desktop Delivery Workflow

Runtime compatibility: desktop

Use this workflow in Codex Desktop when the user delegates a bounded project objective.

1. Main agent reads durable repo artifacts, current files, and git state.
2. Main agent defines source-of-truth, phase plan, ownership, verification, and human gates.
3. Worker tasks are bounded and include expected files, DoD, and verification.
4. Workers do not commit, push, create PRs, publish, merge, deploy, post platform comments, submit reviews, or perform destructive actions.
5. Main agent integrates outputs, checks ownership, and runs verification.
6. Main agent collects integrated output review evidence with `code-review` for ordinary code or mixed changes, `code-review-deep` for high-risk code or mixed changes, or `docs-review` for docs-only or docs-dominant changes.
7. Main agent routes formal decisions directly to `code-review-gate`,
   `docs-review-gate`, or `merge-readiness-gate` only when the workflow reaches
   formal commit readiness, PR readiness, merge readiness, or another
   repo-policy blocking decision.
8. Main agent prepares PR or merge readiness evidence.
9. Main agent stops for human approval before external writes, including commit, push, PR creation, platform comments, review submissions, or final merge/deploy actions.

CLI fallback: use `project-delivery` and `project-orchestrator` with prompts, task briefs, continuation prompts, or a sequential execution path. Run review primitives after the fallback produces changed files or evidence, and use formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.

`desktop-project-delivery` and `desktop-thread-delegation` are the active
Desktop entry and control-plane adapters. `desktop-spec-plan-gate`,
`desktop-implementation-gate`, and `desktop-pr-merge-gate` remain installable
only as deprecated compatibility aliases that route to shared skills; they do
not add Desktop callable behavior.
