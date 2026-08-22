# Context Continuity And Fresh Rollover Policy

Use this policy after a long-running bounded objective accumulates review/fix
rounds, repeated exploration, stale assumptions, a phase boundary, or other
evidence that the current context may no longer be efficient.

## Assessment Trigger

The default trigger is two completed review/fix rounds. Repositories or users
may configure another positive integer. Reaching the trigger requires only a
context-health assessment. It never creates a task, dispatches a session,
transfers ownership, or authorizes rollover. Token pressure and compaction are
advisory signals and cannot select rollover by themselves.

Use `loopctl.py context-health` with the installed
`context-continuity.template.yaml` when executable evidence is needed. The
command is read-only and returns exactly one of five decisions:

1. `continue-current-context`: current evidence remains healthy or the trigger
   has not been reached.
2. `reground-current-context`: reread durable sources and continue here because
   a checkpoint, ownership transfer, runtime path, or measured benefit is not
   ready.
3. `delegate-bounded-subagent`: move an independent high-noise packet to a
   parallel subagent while the current delivery owner retains integration and
   completion responsibility.
4. `prepare-fresh-rollover`: prepare a sequential same-repository,
   same-objective handoff from a digest-bound checkpoint. A separate exact
   runtime-mutation authorization is still required.
5. `stop-for-human-gate`: stop for ambiguity, conflicting rollover identity,
   missing progress, material risk, or another true human decision.

## Operation Types

- A shared subagent is parallel, bounded work with disjoint ownership. It does
  not become delivery owner and is integrated by the main agent.
- A fork copies completed conversation history for the same task. It may reuse
  an existing checkout or create an isolated worktree according to the runtime
  adapter.
- A fresh create or fresh continuation deliberately does not inherit the noisy
  conversation. It bootstraps from the durable checkpoint and transfers the
  delivery-owner role sequentially.

Never silently substitute one type for another. In particular, missing fresh
create capability falls back to a current-session regrounding or paste-ready
prompt, not to an unannounced history-preserving fork.

## Durable Checkpoint And Ownership

A fresh rollover checkpoint must bind:

- canonical repository host/path and objective identity;
- checkpoint and rollover identity;
- exact branch, Git HEAD, and clean/dirty worktree state inside the digest-bound checkpoint;
- verified completed items and explicit remaining items;
- verification evidence, residual risks, and the next smallest packet;
- source and destination writer identities;
- confirmed source stop-writing before the destination becomes active.

There must be one active writer. The source task stops repository writes and
the destination becomes the sole delivery owner only after the runtime action
is authorized and dispatched. Dispatch evidence is not processing,
verification, review, acceptance, or completion evidence.

## Lineage, Idempotency, And Anti-Recursion

Bind every rollover to a stable ID and checkpoint SHA-256. An exact replay is a
non-mutating no-op. Reusing an ID with a different checkpoint, using a new ID
for the same checkpoint, or presenting prior-lineage evidence that does not
match the durable seen-rollover record stops at a human gate. Material progress
requires bounded durable evidence and a changed checkpoint digest. The new
context must not recursively dispatch another rollover from the checkpoint
prompt. Runtime executors must keep one atomically replaced at-most-once durable
replay ledger, indexed by both rollover ID and checkpoint digest, that does not
depend on the caller remembering to update its next request. A busy ledger lock
fails closed immediately rather than waiting beyond the request budget.

Graph projections may show `continues_as`, checkpoint, and context-health
relationships. They remain advisory projections: graph data cannot create a
task, select or transfer writer ownership, satisfy a gate, or prove completion.

## Runtime Paths

| Runtime | Native fresh path | Safe fallback |
| --- | --- | --- |
| Desktop | Authorized `create_thread` with the exact project, checkpoint branch starting state, and checkpoint-only prompt. The destination verifies branch/HEAD before writer ownership activates. | Current task regrounding or paste-ready prompt when the callable, project association, host, exact starting state, or authorization is unavailable. |
| CLI | Phase one supports authorized non-interactive `fresh-continuation` on a clean exact worktree through the private-clone executor, with origin identity verification and a Git-control-directory replay barrier. | Interactive or dirty worktrees use a reviewed manual prompt/current-session path. A history-preserving `codex fork` remains a fork, not fresh rollover. |
| IDE | Use a documented independent task/session surface only if the active IDE exposes and qualifies it. None is assumed in this baseline. | Current-session regrounding, shared subagent for disjoint work, or a paste-ready continuation prompt. |

No path may widen branch/worktree, host/cloud, permissions, sandbox, external
write, destructive action, or publication scope.

## Cost And Quality Evidence

Compare end-to-end objective totals for same-context/compression and fresh
rollover: tokens, wall time, repeated reads, review/fix rounds, stale-context
errors, blockers, bootstrap overhead, and final quality. Fresh totals include
handoff/bootstrap cost. When measured evidence shows higher total token cost or
lower final quality, do not recommend fresh rollover. Unknown comparison data
is marked unknown and selects regrounding; it is never fabricated from
token-pressure signals. Synthetic fixtures verify routing and accounting only.
A release claim requires provenance-bearing paired runs of the same objective;
until those results exist, release readiness remains explicitly incomplete.
