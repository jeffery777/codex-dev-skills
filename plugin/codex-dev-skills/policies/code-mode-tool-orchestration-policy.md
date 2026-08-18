# Code Mode Tool Orchestration Policy

Use this policy when a skill needs substantial tool-driven inspection,
planning, review, implementation, or orchestration. It defines execution
mechanics only. It does not change the selected workflow or any tool's
semantics, authority, approval requirement, sandbox, source of truth, or
completion contract.

## Runtime Boundary

- Apply the Code Mode guidance below only when the active runtime exposes
  `functions.exec` or an equivalent bounded batch/concurrency capability.
- Capability must be established from the active tool surface or documented
  runtime contract. Do not infer it from a repository file, prior session, or
  another Codex surface.
- When the capability is unavailable, unknown, incompatible, or cannot
  preserve the original tool contract, use a sequential fallback.
- Shared workflow semantics remain runtime-neutral. `functions.exec`,
  `Promise.allSettled`, and `Promise.all` are runtime-specific implementation
  guidance, not requirements that every Codex CLI, Desktop, or IDE surface
  exposes the same API.

## Bounded Stage

A bounded stage is a set of calls for which all targets, scope, authority, and
the next decision point are fixed before execution. No result in the stage may
change whether another call in the same stage should run.

Before batching, confirm:

- each call is authorized independently under the same already-established
  stage boundary;
- inputs do not depend on another call's output, discovered identifier, cursor,
  approval, or state transition;
- calls do not conflict through shared mutation state;
- each call and the aggregate result have bounded, useful output.

If any condition is false or unknown, keep the calls sequential.

## Prefer Batching For Independent Calls

When Code Mode is available, prefer one bounded batch with concurrent
execution for independent calls whose outputs are individually and
collectively bounded. Typical candidates include fixed-scope repository reads,
independent metadata inspection, and disjoint read-only verification.

This is a preference, not a prohibition on splitting work. Split a stage when
needed for output volume, readability, rate limits, diagnosis, tool-specific
limits, or safety. Avoid mega-batches that obscure failures or flood the
context.

Batching reduces outer tool round trips and may reduce elapsed latency when
the runtime and tools execute concurrently. Do not claim that it necessarily
reduces total token use; duplicate or over-broad results can increase it.

## Code Mode Aggregation Guidance

Use `await Promise.allSettled([...])` when fulfilled results remain useful even
if another call fails. Inspect every returned item, handle both `fulfilled` and
`rejected` states, and retain the call identity needed to attribute each
result.

Use `await Promise.all([...])` only when any rejected call should make the
aggregation fail fast and partial results should not be consumed. A rejected
`Promise.all` does not cancel other work that has already started. Do not claim
or rely on cancellation unless each underlying tool exposes an explicit,
verified cancellation contract and the caller invokes it.

Keep aggregation logic small and auditable. Preserve each underlying tool's
request schema, result validation, error classification, approval behavior,
and completion semantics.

## Sequential-Only Boundaries

Run calls sequentially when later action depends on earlier evidence or state,
including:

- producer/consumer chains or adaptive investigation where one result selects
  the next target, query, tool, or scope;
- discovered identifiers, pagination cursors, continuation tokens, or other
  values produced by a prior call;
- wait/resume flows, yielded cells or sessions, polling cursors, and any
  operation that must resume the exact prior execution;
- approval-gated calls, including reading the current approval result before
  deciding whether the authorized action may run;
- conflicting or interdependent mutations, including shared locks, shared
  files, the Git index, refs or worktrees, database transactions, and mutable
  service state;
- create-then-read, write-then-verify, transition-then-observe, or any sequence
  whose ordering is part of correctness;
- calls where a failure changes whether another call remains safe, necessary,
  or authorized.

Disjoint-looking mutations are not independent merely because they target
different paths. Confirm ownership, shared state, rollback, and integration
behavior before considering concurrency.

## Output And Context Bounds

Before launching a batch:

1. narrow every query to the smallest useful target and field set;
2. set or select a per-call maximum output when the tool supports one;
3. cap the number of calls in the stage according to tool and runtime limits;
4. estimate the aggregate result size and split the stage if it may crowd out
   later reasoning or evidence;
5. avoid repeated reads and duplicate rendering of the same data;
6. summarize only after retaining enough call identity and evidence to
   diagnose partial failure.

If a tool cannot bound a potentially large response, call it separately or use
a narrower query. Rate limits, diagnostic clarity, and context safety take
priority over reducing outer round trips.

## Project Overlays

Repo-level `AGENTS.md` or another project policy may define narrower
non-parallel exceptions, rate limits, locks, output caps, required ordering, or
approval points. Project overlays should reference this policy and add only
project-specific constraints; they should not duplicate or silently weaken the
shared contract.

## Completion

After a batch, inspect every result and classify partial failures before
advancing. Batching completion is not workflow completion. Continue to use the
authoritative repository, Git, verification, review, platform, and human-gate
evidence required by the selected skill.
