# Multi-Step Maintenance Example

Use `project-orchestrator` when a maintainer wants Codex to triage an issue or maintenance request, choose the smallest safe task, and carry it through review closure before stopping at a human gate:

```text
Use project-orchestrator to triage this maintenance request and choose the next smallest safe docs-only task.
Read repo policy, current git state, README, roadmap, and relevant examples first.
If the task is safe and scoped, implement it, run the relevant validation, use docs-review for review evidence, and fix any in-scope MUST-FIX findings.
Stop before commit, push, PR creation, merge, release, issue updates, PR comments, review submissions, or any external write unless I explicitly authorize that step.
```

Expected flow:

1. Read repo instructions, current branch, working tree state, remotes, and any roadmap or issue context that defines the request.
2. Triage the request against current repo state, separating facts from assumptions and rejecting scope that would require new skills, installer changes, or unrelated workflow changes.
3. Select the smallest safe task that resolves the request, such as one docs-only example update, one README pointer, or one roadmap cleanup.
4. Plan the exact files to edit, then make only the scoped documentation or template-text changes.
5. Run the smallest relevant validation, such as the repo validation script and `git diff --check`.
6. Use the ordinary review primitive for the changed surface, such as `docs-review` for docs-only changes.
7. Fix safe, in-scope MUST-FIX findings and re-run validation and review until blockers are closed or the configured round limit is reached.
8. Stop at the human gate before commit, push, PR creation, merge, release, issue updates, PR comments, review submissions, or any other external write.

If the maintainer later authorizes external writes, Codex should restate the changed files, validation, review outcome, and residual risk before commit, push, PR creation, platform comments, review submissions, or merge.
