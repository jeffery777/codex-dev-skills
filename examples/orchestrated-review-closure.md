# Orchestrated Review Closure Example

Use `project-orchestrator` when Codex should compose implementation, review, blocker fixes, and re-review for a bounded task:

```text
Use project-orchestrator to improve the maintainer docs for this workflow.
Run at most two review/fix rounds. Use docs-review for ordinary docs review evidence, and use docs-review-gate only if the workflow reaches formal commit readiness, PR readiness, merge readiness, or a repo-policy blocking decision.
Stop before commit, push, PR creation, merge, release, platform comments, review submissions, or any external write unless I explicitly authorize it.
```

Expected flow:

1. Read repo policy, source-of-truth docs, current git state, and the requested scope.
2. Route the work to the smallest fitting primitive, such as `implementation-slice` or `docs-update`.
3. Run the ordinary review primitive for the changed surface, such as `docs-review` for docs-only changes.
4. Fix MUST-FIX findings that are safe and in scope, then re-run the relevant review.
5. Use formal gates only for commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision.
6. Stop at the next human gate before external writes or final approval.

For a larger but still bounded delivery objective, use `project-delivery` as the outer workflow and let it compose the same primitives.
