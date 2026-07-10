# Review Workflow

Runtime compatibility: shared

Use this workflow for code, mixed, or documentation review.

1. Confirm review scope and diff range.
2. Stay read-only unless the user explicitly asks for fixes.
3. Read repo policy, changed files, and relevant context.
4. Lead with findings ordered by severity.
5. Include file and line evidence when available.
6. Distinguish blockers from non-blocking improvements.
7. Include re-runnable verification commands.

Use `code-review` for ordinary code or mixed read-only review. Use `code-review-deep` for high-risk code or mixed changes. Use `docs-review` for docs-only or docs-dominant changes.

Use `code-review-gate` or `docs-review-gate` only when a workflow needs a formal blocking decision for commit readiness, PR readiness, merge readiness, or an explicit repo policy gate. Gates route to the review primitives and record evidence; they are not the default review primitive for every closure-loop pass.

## Orchestrated Closure Loop

`project-orchestrator` or `project-delivery` may run a bounded review closure loop using primitive shared workflows instead of a dedicated closure skill:

1. Apply the requested bounded change through `implementation-slice` or `docs-update`.
2. Run `code-review` for code or mixed changes, or `docs-review` for docs-only or docs-dominant changes. Escalate to `code-review-deep` when the code or mixed diff is high-risk.
3. Give every MUST-FIX, SHOULD-FIX, and NIT a stable id, then classify it as fix now, defer, reject with rationale, or needs human decision.
4. Fix accepted code or mixed findings through `implementation-slice`; fix accepted docs-only findings through `docs-update`.
5. Rerun the relevant review primitive and record disposition, owner, durable target, promotion trigger, evidence, verification, and remaining risk with `templates/review/review-follow-up.template.md`. Deferred findings must never exist only in chat or transient review output.
6. Run `code-review-gate` or `docs-review-gate` only when the loop reaches formal commit readiness, PR readiness, merge readiness, or another repo-policy blocking decision.

A formal gate may pass only after every finding has a durable disposition. NITS
do not block merely because of severity, but an unrecorded NIT blocks the gate
because it can be silently lost.

Default max rounds: 2, unless the user or repo policy sets a different maximum.

Stop before commit, push, PR creation, merge, deploy, platform comments, review submissions, destructive action, external publication, unclear findings, scope expansion, or material security, data, migration, or public-contract risk.
