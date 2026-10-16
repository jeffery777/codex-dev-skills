# Review Artifact Policy

Review artifacts are evidence, not source-of-truth replacements. Follow
[fixed Core loading](core-contract-loading.md); read full workflow and
authorization/stops, including Core
[wf-evidence-lifecycle](../vendor/engineering-workflow-core/contracts/workflow.md#wf-evidence-lifecycle),
[auth-data](../vendor/engineering-workflow-core/contracts/authorization-and-stops.md#auth-data)
and [auth-destructive](../vendor/engineering-workflow-core/contracts/authorization-and-stops.md#auth-destructive).

## Locations

Use repo policy when it names an artifact root. Otherwise, `.work/review/` is the default convention.

## Current And Historical Artifacts

- In existing reports, keep compact cause/fix/version/replacement references and
  current evidence first. Follow Core's Active, Superseded and Unresolved meanings;
  superseded is not a cleanup authorization.
- Verify replacement evidence covers the original failure and affected boundaries;
  record old/new revision, scope, outcome and readable evidence. An unrelated PASS
  cannot close an unresolved, intermittent or uncertain failure.
- Preserve current, shared, still-referenced, unresolved/intermittent,
  security/data-loss and policy-protected evidence. Summaries reduce repeated
  loading, not source retention; missing originals leave claims unverified.
- Before archive/move/cleanup, establish effective retention policy/period,
  protected exceptions, sharing/other users, exact scope, authority and preview.
  Without retention policy or period, retain and mark pending. No universal days.

## Cleanup Classes

- SAFE_TO_DELETE: only a candidate after verified replacement coverage, no active
  reference or protected exception, and effective retention requirements are met.
  The label alone grants no operation authority.
- KEEP: current, referenced, shared, unresolved/intermittent, security/data-loss,
  policy-protected, or missing required retention information.
- NEEDS_EXPLICIT_OVERRIDE: ambiguous/high-value cases requiring a decision; an
  override cannot waive higher-priority retention or authorization duties.

Cleanup requires a dry-run preview and exact operation authority. Irreversible
deletion requires confirmation at action time for exact targets and impact;
approval of a package/plan or context slimming is insufficient. This policy
executes no cleanup and does not require keeping every raw log forever.
