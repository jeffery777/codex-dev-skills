# Reusable Workflow Contract

This contract defines the shared shape for Codex CLI and Codex Desktop development workflows.

## Shared Phases

1. Read source-of-truth files and current state.
2. Plan the smallest safe task slice.
3. Implement or delegate within scope.
4. Verify with relevant commands.
5. Inspect the diff.
6. Run review primitives when required; reserve formal review gates for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions.
7. Sync docs or status when required.
8. Stop at human gates for ambiguity, risk, destructive actions, or external writes.

## Runtime Differences

Codex CLI may execute phases sequentially in one session or through prompts, task briefs, continuation prompts, or another explicit sequential execution path.

Codex Desktop may use main-agent orchestration and worker delegation, but Desktop runtime behavior does not replace durable repository artifacts or human gate policy.

## Review And Merge

Review primitives such as `code-review`, `docs-review`, and high-risk `code-review-deep` provide ordinary quality evidence. Formal `code-review-gate` and `docs-review-gate` runs provide blocking readiness evidence only when commit readiness, PR readiness, merge readiness, or explicit repo policy requires that decision. Neither review evidence nor formal gate evidence by itself authorizes commit, push, merge, deploy, or platform publication.
