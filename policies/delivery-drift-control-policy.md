# Delivery Drift Control Policy

Long-running work drifts when runtime memory, summaries, or stale artifacts replace current repository state. Use this policy at phase boundaries and after any interruption.

## Re-bootstrap Triggers

Re-read durable project artifacts:

- at the start of each phase
- after context compaction or resume
- after branch, base, or review scope changes
- before switching from ordinary review primitives to formal review gates
- before commit, PR readiness, merge readiness, or external writes

## Durable Sources

Prefer repository-owned instructions, specs, plans, status files, review artifacts, verification evidence, and current git state.

## Rules

- Do not treat memory, chat summaries, or worker output as authoritative over repo files.
- Mark stale or missing evidence explicitly.
- If the current state conflicts with prior summaries, inspect cheaply before deciding.
- Stop for human decision when the conflict affects behavior, public contract, data, security, or delivery scope.
