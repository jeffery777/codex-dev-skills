---
description: Run an implementation -> review -> follow-up -> re-review loop until blockers are closed or a human gate is reached.
---

# review-loop

Runtime compatibility: shared

## Purpose

Use this skill when the user asks for an implementation plus review closure loop.

## Workflow

1. Implement the requested bounded change using `implementation-slice` semantics.
2. Classify the diff.
3. Route code or mixed changes to `code-review-gate`; route docs-only changes to `docs-review-gate`.
4. If findings remain, run `review-follow-up-plan`.
5. Apply fixes through `review-follow-up-implementation` or `docs-review-follow-up`.
6. Run `review-follow-up-review`.
7. Repeat until no blockers remain, max rounds are reached, or a human gate is required.

## Defaults

- Max rounds: 2.
- Keep changes scoped.
- Defer non-blocking findings when fixing them would expand scope.
- Stop before commit, push, merge, deploy, destructive action, or platform publication unless explicitly authorized.

## Output

- Round-by-round summary
- Findings fixed
- Findings deferred
- Verification evidence
- Remaining risk
- Next human gate
