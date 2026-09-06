# Fresh Non-Interactive Continuation

Read together with [non-interactive execution](non-interactive.md) only after
shared orchestration selects `prepare-fresh-rollover` from a valid
`loop-context-continuity/v1` assessment.

This phase supports only clean-worktree, non-interactive CLI execution for
the same repository and objective. Start a new `codex exec --json` session;
do not resume or fork conversation history.

Append the canonical checkpoint as data with its SHA-256 and stable rollover
ID. Require one destination writer, confirmed source stop-writing, material
progress evidence, exact replay no-op, and no recursive handoff. The executor
matches checkpoint canonical host/path to `origin`, digest-binds clean worktree
state, and atomically updates one locked durable ledger indexed by both
rollover ID and checkpoint digest below the Git control directory before the
runtime call. Caller-supplied `seen_rollovers` is not the runtime idempotency
barrier. An exact request replay performs no second session call.

Dirty or interactive worktrees, incomplete checkpoints, missing capability,
or failed validation require manual/current-session continuation. Do not claim
automated transfer or success. Include rollover ID and checkpoint digest in
the operation result, retaining the originating session's completion duties.
