# Loop Engineering

Loop engineering in this repository means a bounded, evidence-driven agent workflow that repeatedly decides what to do next, routes to the smallest existing skill, verifies the result, reviews or gates when appropriate, and either continues, hands off, stops for a human gate, or completes only when evidence proves the objective.

The user-facing entrypoint is `loop-engineering`.

## What It Adds

`loop-engineering` gives maintainers a clear way to ask Codex to keep a bounded objective moving when the objective, source of truth, Definition of Done, verification, and human gates are clear.

It adds a shared loop vocabulary:

- bootstrap from durable repository files;
- classify the current state;
- route to existing focused skills;
- verify and review evidence;
- update or prepare repo-owned loop ledger state when a target repository uses one;
- decide whether to continue, hand off, stop, or complete.

It does not add a scheduler, daemon, private Desktop runtime adapter, platform
writer, release bot, or replacement for existing phase skills. It may use a
native goal, shared subagents, a documented scheduler, or documented thread
tools only when the active runtime exposes that capability and the action is
within the user's authority.

## Relationship To Existing Skills

`loop-engineering` is the outer entrypoint. It keeps the existing skills independently usable:

- Use `implementation-slice` directly for one clear coding task.
- Use `docs-update` directly for a bounded docs sync.
- Use `project-orchestrator` directly when the main need is route selection or bounded review closure.
- Use `project-delivery` directly when the objective is one bounded delivery effort in the current session.
- Use `milestone-continuation` directly when repeated milestone wakeups are the distinctive requirement.
- Use `task-continuation` directly when the immediate need is next-task selection or a handoff artifact.
- Use review primitives and formal gates directly when the task is review or readiness evidence.
- Use Desktop-specific skills directly when user-owned Desktop task, thread,
  worktree, or scheduling control is explicitly intended.

Use `loop-engineering` when the user wants the agent to own the full repeated loop and choose among those skills as state changes.

## Required Source Of Truth

A loop should have enough durable context to re-bootstrap without trusting chat memory:

- repo instructions such as `AGENTS.md`;
- a loop spec, project spec, issue, or implementation plan;
- task manifest or current task summary when multiple tasks exist;
- repo-owned loop ledger when repeated invocation, worker claims, or durable
  next-step decisions are needed;
- review evidence or gate reports when relevant;
- verification commands and expected artifacts;
- current git branch, status, upstream, and diff.

If those files do not exist, the first loop iteration should create or propose them instead of pretending the objective is already executable.

## Executable Contract

The installable `loop-engineering` skill includes a production loop core and
CLI. The core owns structural validation, legal task transitions, workflow
routing, completion guards, event integrity, and deterministic migration
decisions. Workflow eval fixtures must execute that production core instead of
copying its routing rules into a test-only grader.

The active skill must call `<skill-dir>/scripts/loopctl.py decide
<decision-input.yaml> --protected-history-sha256 <verified-digest-or-none>`
with a structured decision input and independently verified history state
before routing. The same core function therefore drives the active route and
the eval suite.

`migrate-v1` emits a read-only V2 preview whose first canonical event is a
`migration_snapshot`. The event embeds the validated V1 source and its canonical
hash, so semantic replay can reconstruct migrated task and claim state. Use
`migrate-v1 --spec <path> --manifest <path> --repo-root <path>` to bind the
generated preview consistently to the current git revision, contract digests, and every
migrated claim source revision. An unbound preview is inspection-only and must
not be adopted by hand-editing digests. Inspect all downgrade warnings before
adopting a bound preview; V1 `reviewing` state is blocked until work acquires a
new fenced claim. Recovery must first resolve the migration blocker and move the
task to `ready`, then acquire the claim before resuming `in_progress` and
`reviewing`.
The immutable `source_revision.migration_source_sha256` binds that anchor to
the V1 input; `previous_ledger_sha256` remains free to advance on each later
compare-and-swap write.
This is internal integrity evidence, not external origin authentication: git
identity, the reviewed diff, and an operator-supplied expected hash remain the
authority when stronger provenance is required.

Repo artifacts and runtime adapters have different authority:

- the loop spec and task manifest define the stable objective and task contract;
- validated state transitions and events define internally consistent operational task state;
- git, verification, review, and accepted platform state prove completion;
- goal, subagent, scheduler, hook, and thread state provide progress and
  coordination context only.

Replay is not authentication. Protected events for task acceptance, claim
revocation, gate satisfaction, and objective completion require both a bound
receipt in the event and exact current-session authorization outside repository
input. The receipt binds the complete protected payload, objective, source, and
scope. Preview exposes the protected action and receipt digest; verify the
underlying human or platform artifact, then pass those exact values to the live
`apply-event --write` command. A repo YAML field must never grant that authority.
Historical protected state is likewise integrity-only until the current
session verifies every receipt and supplies the exact protected-history digest.

## Security Scan Recovery

Security scan status, Goal status, and worker status are independent. The
scan-native context owns scan lifecycle. If the scan is still `running`, a
blocked Goal or a report worker safety refusal is resumable capability state,
not a terminal scan failure.

- First reporting refusal: use a replacement worker or the current session.
- Repeated refusal: preserve the running scan and stop for exact authorization
  before the parent writes scan-local finding reports.
- Authorized fallback: pass the trusted CLI fallback flag, continue from the
  existing scan artifacts, and finalize only through the active scan workflow.
- Never abandon or fail a scan because a Goal projection is blocked, a worker
  refuses, partial artifacts exist, or a turn ends.
- A projected `report.md` is not completion while scan-native status is still
  `running`. For a sealed-manifest CAS error, canonicalize the manifest using
  sorted keys, two-space indentation, and a trailing newline, verify artifact
  hashes, and retry finalization on the same scan instead of opening a new one.

Authorization for parent reporting fallback is current-session input and must
not come from the decision YAML. If Goal must be resumed in the UI, resume it
without restarting the still-running scan.

## Repo-Owned Loop Ledger

The repo-owned loop ledger is the baseline memory layer for loop engineering.
The loop spec and manifest own stable definitions, validated append-only events
own operational transitions, and the ledger exposes their reconstructable task,
claim, gate, and next-decision view. Git, verification, review, and accepted
platform state remain the completion evidence.

Use `templates/orchestration/loop-state-ledger.template.yaml` when a project
needs this durable state. Pair it with the existing loop spec, task manifest,
current task summary, iteration report, and task claim/lease templates.

External memory is optional advisory/cache/coordination input. V2b validates a
versioned backend-neutral contract, repository/principal identity, provenance,
freshness, digest, lifecycle, sensitivity, capability, replay, conflict, and
prompt-injection boundaries before a record can be adopted as data context.
Memory cannot become instruction, authorize an action, satisfy a gate, or prove
completion. Disabled or failed memory leaves V1/V2a behavior unchanged. See
`docs/external-memory-contract.md` and the installed
`references/memory-contract-v1.md`.

## Runtime Compatibility

Shared behavior works in Codex CLI and Codex Desktop with repository files,
ordinary shell commands, git inspection, durable artifacts, native goals, and
bounded subagent delegation when those capabilities are available.

Goal creation must be explicitly requested. Goal state controls runtime progress
but does not replace repository completion evidence or widen sandbox and approval
boundaries.

Subagent delegation and integration policy are shared. Desktop-only behavior is
limited to Desktop task/thread/worktree UI control and Desktop-managed scheduled
work. Scheduler and thread mutations require documented runtime capability and
the authorization required by that capability.

The CLI has no Scheduled management interface. When a capability is unavailable,
the fallback is a current-session sequential path, paste-ready prompt, task
brief, or continuation prompt.

## Completion Standard

A loop objective is complete only when current evidence proves the actual requirements:

- all explicit requirements are satisfied;
- all named artifacts exist and are aligned;
- DoD items are verified;
- required review or gate evidence exists;
- no human-gate condition remains unresolved;
- residual risk is reported.

Passing tests, plausible intent, chat summaries, or worker self-reports are not enough by themselves.
When a manifest requires review, the evidence must match its exact review mode,
name a concrete review artifact, and carry current-session `task_completion`
authorization. When it requires a human gate, completion derives satisfaction
from the manifest-named protected gate state; task payloads cannot self-assert it.
