# Project Workflow Overlay Example

Use this example when a repository wants a compact workflow policy for delegated delivery, review closure, PR readiness, and release gates.

This is an example only. Keep the final policy in a project-owned file such as `docs/workflow.md`, `docs/release-readiness.md`, or a repo-level `AGENTS.md` section.

## Example Workflow Policy

```markdown
# Project Workflow Policy

## Delegated Delivery

When the maintainer delegates a bounded objective, Codex may carry the work to the next real human gate:

- inspect repository instructions, plans, relevant files, and git state
- split the objective into safe slices when needed
- implement scoped changes
- update docs when behavior or usage changes
- run relevant verification
- run ordinary review primitives and formal gates when required
- fix MUST-FIX findings and re-review before commit readiness

Codex must stop when requirements, scope, public behavior, data, security, deployment, permissions, or release semantics become ambiguous.

## Review Closure

Review findings use these buckets:

- `MUST-FIX`: blocks commit, PR readiness, merge readiness, or release readiness.
- `SHOULD-FIX`: should be addressed when safe and in scope; otherwise record the follow-up and reason.
- `NITS`: small cleanup or clarity items; address only when safe and low-risk.

Commit readiness requires no unresolved `MUST-FIX` findings from the applicable code or docs review gate.

## PR Readiness

Before PR creation, summarize:

- changed files and why they are in scope
- verification commands and results
- code review or docs review evidence
- unresolved risks, skipped checks, and human decisions

PR creation, platform comments, review submissions, and merge are external writes and require exact authorization.

## Merge Readiness

Before merge, re-check:

- PR head SHA and target branch
- CI or local verification evidence
- review closure evidence
- docs and release-note alignment when applicable
- whether merge review reports any `MUST-FIX`, `SHOULD-FIX`, or `NITS`

Do not merge until the required merge review has no unresolved blocking findings and the maintainer has authorized the merge.

## Release Or Tag Gate

Before creating a tag or publishing a release, report:

- target branch and HEAD SHA
- proposed version and tag name
- release scope
- release notes path or release summary
- verification evidence
- review and merge-readiness evidence
- skipped checks and residual risk

Tag creation and release publication require separate exact authorization.
```

## Pairing Notes

- Use `project-delivery` for bounded milestone work.
- Use `desktop-project-delivery` and `desktop-thread-delegation` only when Codex Desktop is intentionally selected.
- Use `task-continuation` when another session needs a durable prompt or task brief.
- Use `merge-review-deep` for release-sensitive changes.
- Keep version bumps and release tags behind explicit release authorization.
