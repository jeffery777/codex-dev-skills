# Agent Delegation Policy

Use this policy when a workflow delegates work to another agent, session, or worker.

## Delegation Rules

- Delegate only bounded tasks with clear scope, expected files, DoD, and verification.
- Split work by disjoint ownership, artifact boundaries, independence, and
  useful parallelism rather than assigning one worker per discipline. Keep
  tightly coupled implementation, focused tests, and directly related docs
  with one owner by default. Keep code review independent from the author, and
  use an independent security reviewer when security risk triggers it.
- Dispatch a bounded set of already-independent packets together when the
  runtime supports it. The main agent should continue parent-owned inspection,
  integration preparation, or verification work while workers run.
- The delegating agent remains responsible for integration, review, and human gates.
- Workers must not commit, push, create PRs, publish, merge, deploy, post platform comments, submit reviews, or perform destructive actions.
- Workers must report changed files, commands run, skipped checks, risks, and open questions.
- Heterogeneous version 2 routes must also record task factors, workload kind,
  selected capability class, tier, and role, resolved or unresolved runtime
  mapping, fallback, assigned scope and
  ownership, source revision, profile digest, and the worker receipt.
- The main agent records whether it accepted, reworked, rejected, or deferred
  the result after independent verification. Failed, partial, stale,
  conflicting, or ownership-mismatched receipts cannot prove completion.
- Runtime facts and assignment freshness are current-session control-plane
  evidence. Do not infer them from a repository decision or receipt document.
  Independently read current Git, worker artifacts, verification artifacts, and
  any selected profile before accepting an integration receipt.
- Worker summaries are evidence, not source of truth. Re-check important claims against repository files.
- Prefer event-driven coordination over status polling. Use one supported
  wait-for-any or mailbox wait for the active worker set, integrate completed
  results while other workers continue, and do not repeat list/read/wait calls
  when no state or cursor changed. Necessary waiting is not a failure; repeated
  unchanged polling is avoidable coordination overhead.
- Workers should send only a blocker that requires a parent decision and one
  final structured receipt. Routine progress narration must not wake the
  parent. Reuse the original worker for a bounded follow-up or re-review when
  its ownership and source revision remain valid instead of bootstrapping a
  replacement merely to request status.
- Security workers stay defensive and local-first. Prefer static analysis,
  local fixtures, negative tests, synthetic inputs, and minimal non-invasive
  validation. If runtime policy rejects a path, use safer local evidence or
  record the verification limit; do not evade the policy or access or change
  external systems.

## Task Brief Requirements

Each delegated task should include:

- objective
- in-scope and out-of-scope work
- source files and policies to read
- expected outputs
- verification commands
- stop conditions
- reporting contract: blockers needing a decision plus one final receipt; no
  routine progress messages

## Stop Conditions

Stop delegation when ownership overlaps, source-of-truth files conflict, the task requires a product decision, or the worker would need external write permission.
