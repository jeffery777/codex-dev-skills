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

Compose only the applicable shared contract, role and current packet using
`templates/orchestration/agent-task-brief.template.md`. Preserve the shared
`reusable-workflow-contract.md` contextual prompting and decision rules. A
brief references current routing/qualification evidence; it does not replace
the router, confer authority or require a new receipt schema.

Each delegated task should include:

- objective
- in-scope and out-of-scope work
- source files and policies to read
- expected outputs
- verification commands
- stop conditions
- receiving role, exclusive ownership, source revision and current diff evidence
- verified runtime/model/effort and existing route/profile reference when applicable
- assigned authority, routine decisions allowed, and unresolved parent decisions
- required checks, acceptance evidence, and conditions to expand verification
- escalation to parent for a capability mismatch; no in-place profile/effort changes
- reporting contract: blockers needing a decision plus one final receipt; no
  routine progress messages

## Stop Conditions

Stop delegation when ownership overlaps, source-of-truth files conflict, the task requires a product decision, or the worker would need external write permission.

## Codex Required Independent Reviewer Selection

For a required independent review, select a reviewer independent of the author
in role and responsibility, bound to the current reviewed revision or diff,
and meeting the task's stated read-only conditions and applicable qualification.
A writable general-purpose agent does not qualify merely because its brief
requests read-only behavior or its role name says reviewer.
A custom role under a writable parent does not establish separate read-only
permissions; use current supported control-plane evidence for the selected
route and the conditions that this task actually requires.

When the reviewer is unavailable, unsupported, or its required conditions remain
unknown, keep the required review incomplete and block only its dependent gate.
Do not count the author's self-review or the writable substitute as that required
review; independent, authorized safe work may continue.
Qualification alone does not complete a review: the current target still needs
the actual review, evidence, findings and dispositions under the existing gate.
A stale target or changed required condition returns to the affected checks.

Read-only workflow instructions do not establish technical isolation.
For every required reviewer, apply fixed Core's full
[effective read-only conditions](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-required-read-only)
through the loading contract. Verify current supported controls on all relevant
direct, shell and broker channels before counting the review; do not add
a whole-host no-write rule or an inventory of unrelated tools.
Assess only the selected route's exposed paths relevant to its required boundary.
If a relevant shell, broker, or other write path is exposed, a denial on another
tool does not establish that this path is constrained.
The parent persists the returned review under existing authority and retention
rules; this binding grants no reviewer write or publication authority.
This Codex binding does not qualify another runtime or change Core authority.

Only Core's explicit environment-specific exception permits a necessary retained
write channel. Apply its complete acceptance, detection, invalidation and
revalidation rules. Do not infer user acceptance, transfer another environment's
record, or label accepted residual risk as technical read-only qualification.

Contract-coverage tests check wording and references only; they do not run a
review, qualify a runtime, or enforce this binding at dispatch.
