# Implementation Workflow

Runtime compatibility: shared

Use this workflow for a bounded software change.

1. Inspect repo instructions, current files, and git state.
2. Read the target code, tests, and docs before editing.
3. State the intended affected files and verification plan.
4. Implement the smallest scoped change.
5. Run relevant verification.
6. Inspect the diff.
7. Route to `code-review` or `docs-review` for ordinary review evidence; escalate code or mixed changes to `code-review-deep` when risk is high. Use `code-review-gate` or `docs-review-gate` only for commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision.
8. Report changed files, evidence, skipped checks, and residual risk.

Stop before external writes, destructive actions, broad refactors, or product-semantic decisions that are not already clear.

For review closure loops, use `project-orchestrator` or `project-delivery` to repeat these primitive shared steps within the configured round limit. Do not require a dedicated closure skill.
