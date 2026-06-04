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

Use `code-review-deep` for high-risk code or mixed changes. Use `docs-review` for docs-only or docs-dominant changes.

## Orchestrated Closure Loop

`project-orchestrator` or `project-delivery` may run a bounded review closure loop using primitive shared workflows instead of a dedicated closure skill:

1. Apply the requested bounded change through `implementation-slice` or `docs-update`.
2. Run `code-review-gate` for code or mixed changes, or `docs-review-gate` for docs-only changes.
3. If actionable blockers remain, classify each finding as fix now, defer, answer, withdrawn, or needs human decision.
4. Fix accepted code or mixed findings through `implementation-slice`; fix accepted docs-only findings through `docs-update`.
5. Rerun the relevant review gate and record disposition, evidence, verification, and remaining risk with `templates/review/review-follow-up.template.md` when useful.

Default max rounds: 2, unless the user or repo policy sets a different maximum.

Stop before commit, push, merge, deploy, destructive action, external publication, unclear findings, scope expansion, or material security, data, migration, or public-contract risk.
