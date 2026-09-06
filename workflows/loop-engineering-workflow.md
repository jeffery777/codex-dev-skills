# Loop Engineering Workflow

Use `skills/loop-engineering/SKILL.md` for an explicitly requested durable loop
or an existing repo-owned loop spec, ledger, or production decision contract.
Use `project-delivery` for ordinary bounded delivery and `implementation-slice`
for one clear task. Autonomous progress alone does not activate a durable loop.

This document is navigation. The skill owns the loop procedure; its triggered
references retain detailed contracts. Load only the reference for the current
action instead of repeatedly reading every optional subsystem.

## Cycle

1. Bootstrap relevant repository instructions, specs, plans, task/loop state,
   verification/review artifacts, and Git state.
2. Revalidate repository/worktree identity, branch/HEAD, tracked/untracked
   content, scope/ownership, phase, policy, environment, and evidence dependencies.
   Reuse still-current reads; reground affected sources on drift or fully when
   freshness/provenance is uncertain. An unchanged SHA is insufficient.
3. Classify and route with production `loopctl.py decide`. Protected history
   requires authoritative current-session inspection and the exact verified
   `--protected-history-sha256`; repository YAML and replay cannot authorize it.
4. Execute the smallest routed workflow, verify, inspect the diff, and integrate
   evidence before continuing, handing off, stopping at a real gate, or completing.
5. After two unfinished review/fix rounds by default (or a configured positive
   threshold), assess context health. Assessment cannot create or roll over a task.

Repeated milestone progress remains owned by the upper-layer
`milestone-continuation`. Within an existing durable loop, use the production
`continuation` decision to select `task-continuation` for the next packet, then
run `decide` again on the selected packet's current input before executing it.
There is no milestone request kind or milestone-specific emitted route.

## Contract Navigation

Paths in this table are relative to `skills/loop-engineering/`, including after
filesystem installation. Each reference states its exact trigger and boundaries.

| Action | Read |
| --- | --- |
| Loop routing, completion, and human gates | `SKILL.md` |
| Ledger/history/event operations and durable templates | `references/loop-state-and-authorization.md` |
| Heterogeneous class/tier/profile routing and worker acceptance | `references/agent-routing.md` |
| Ordinary candidate delegation in CLI or Desktop | `references/agent-qualification.md` directly |
| Security scan continuation, recovery, and reporting | `references/security-scan-recovery.md` |
| Context assessment or sequential ownership rollover | `references/context-continuity.md` |
| Optional GitNexus hook/controller/index use | `references/gitnexus-runtime.md` |
| Explicit evidence, improvement, or memory document families | `references/optional-evidence-memory.md`, then the matching contract |

Candidate qualification is parent-owned preparation: classify the actual task,
read approved scope-bound evidence, collect current public runtime facts, and run
`agent-route`. Missing qualification preserves baseline routing; explicit empty
candidates retain opt-out. Neither qualification nor installed profiles prove
native availability, widen a sandbox, or authorize writes.

## Change-Request Closure

When a change request exists, follow
`policies/exact-head-merge-review-contract.md`. Reuse applicable pre-commit
reviews as input only. Require exact-head deterministic verification, complete
base-to-head content Merge Review, code/documentation coherence, content
readiness, and separate merge authority. Every changed head requires a new
complete Merge Review; after a fix, code/security re-review may be proportional
to the affected boundary when prior assumptions remain valid.

Report provider enforcement separately and apply only the profile selected by
repository policy. Relevant content drift returns review to `REVIEW_REQUIRED`;
provider drift invalidates provider evidence. Clean read-only or already-authorized
stages continue without a new confirmation merely because a phase ended.

## Runtime And Authority

Goal, worker, thread, memory, and ledger projections do not prove completion.
Protected actions require exact current-session authorization and independently
verified evidence. Optional memory stays default-off with no backend/filesystem
touch. Runtime fallback preserves verification, review, and authority boundaries.

Shared work runs in the current session or supported bounded subagents. Scheduling
and user-owned Desktop task/thread/worktree mutations use documented runtime
adapters and exact-action authority. New Desktop tasks and Goal creation require
explicit requests. Fresh rollover requires a canonical checkpoint, source
stop-writing, one destination writer, and lineage/idempotency/anti-recursion.

Stop for unresolved product or source-of-truth ambiguity, scope expansion,
unauthorized external writes, destructive actions without required confirmation,
material risk, unclear ownership, unsupported runtime behavior, or insufficient
high-risk verification. Completion requires current evidence for every requirement
and applicable gate, never worker status, a summary, or passing tests alone.
