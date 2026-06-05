# Code Review Example

Use `code-review` for routine read-only review:

```text
Use code-review on the current working tree.
Stay read-only and report findings before summary.
```

Expected output leads with findings, then questions and verification commands.

Use `code-review-deep` when the diff touches migrations, sensitive data, permission boundaries, deployment, or dependency risk.

Use `code-review-gate` only when a workflow needs a formal blocking decision before commit readiness, PR readiness, merge readiness, or an explicit repo-policy gate.
