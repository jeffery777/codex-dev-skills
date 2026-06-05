# Docs Review Example

Use `docs-review` for routine read-only review of docs-only or docs-dominant changes:

```text
Use docs-review on the current working tree.
Check accuracy against the repo, stale links or names, unsupported claims, confusing structure, and private or machine-specific material. Stay read-only.
```

Expected output leads with documentation findings, then questions and re-runnable verification commands.

Use `docs-review-gate` only when a workflow needs a formal documentation gate before commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision.

The gate wraps `docs-review` for evidence capture and the blocking decision. It is not the default entry point for ordinary documentation feedback.
