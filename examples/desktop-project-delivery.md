# Desktop Project Delivery Example

Use `desktop-project-delivery` in Codex Desktop for delegated bounded work:

```text
Use desktop-project-delivery to deliver this feature to PR readiness.
Review integrated output with code-review or docs-review, escalating high-risk code or mixed changes to code-review-deep.
Use desktop-implementation-gate only for formal Desktop integration before commit readiness.
Use code-review-gate or docs-review-gate only for formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decisions.
Stop for product ambiguity, external writes such as commit, push, PR creation, platform comments, or review submissions; destructive actions; or final merge approval.
```

CLI fallback: use `project-delivery` and `project-orchestrator`, prepare prompts, task briefs, continuation prompts, or a sequential execution path, re-read handoff evidence before trusting it, and run formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.

See [runtime compatibility](../docs/runtime-compatibility.md) for the Desktop-to-CLI fallback mapping.
