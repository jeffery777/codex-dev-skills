# Delivery Drift Control Policy

Long-running work drifts when runtime memory, summaries, or stale artifacts replace current repository state. Use this policy at phase boundaries and after any interruption.

## Re-bootstrap Triggers

Check current state and the relevant durable evidence:

- at the start of each phase
- after context compaction or resume
- after branch, base, or review scope changes
- before switching from ordinary review primitives to formal review gates
- before commit, PR readiness, merge readiness, or external writes

## Durable Sources

Prefer repository-owned instructions, specs, plans, status files, review artifacts, verification evidence, and current git state.

## Rules

- Do not treat memory, chat summaries, or worker output as authoritative over repo files.
- Bootstrap once, then read changed or newly relevant sources at the triggers
  above. A checkpoint may record branch/base/head, worktree diff identity, scope,
  phase, source paths and evidence references. A matching HEAD alone cannot
  establish freshness: uncommitted files, instructions, verification assumptions
  and provider state may have changed.
- Reuse prior reads and checks only while their inputs and scope remain valid.
  After compaction or resume, verify checkpoint references against current state;
  reconstruct the affected context when references are missing or conflicting.
- Do not copy every source or repeat a full bootstrap/report at each phase.
  Report the changed facts and link still-valid evidence. A changed request head
  still requires complete base-to-head exact-head Merge Review.
- Mark stale or missing evidence explicitly.
- If the current state conflicts with prior summaries, inspect cheaply before deciding.
- Stop for human decision when the conflict affects behavior, public contract, data, security, or delivery scope.
