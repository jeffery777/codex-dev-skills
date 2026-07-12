# Repo-Owned Loop State And Ledger

Repo-owned loop state is the baseline durable memory layer for
`loop-engineering`. Stable definitions live in the loop spec and task manifest;
validated append-only events are the operational integrity record, and the
ledger task view is their reconstructable materialization. Replay proves
internal consistency but not actor identity or external approval provenance. This lets Codex recover,
continue, hand off, and audit a bounded objective without an external adapter.

V2b external memory is an optional advisory/cache/coordination layer. Its
versioned receipt may be referenced by digest, but it cannot replace the
repository contract, validated events, protected authorization, or completion
evidence.

## Purpose

Loop Engineering V1 ledger schema v2 records enough durable state for any later
Codex session or maintainer to answer these questions from repository files:

- What objective is active?
- Which task is next?
- Who owns an in-flight task?
- Which lease or claim prevents duplicate work?
- What changed in the last iteration?
- Which verification and review evidence supports a status change?
- Should the loop continue, hand off, stop for a human gate, or complete?

## Recommended Files

A target repository can choose paths, but the recommended layout is:

```text
docs/loops/<objective-id>/loop-spec.md
docs/loops/<objective-id>/loop-state-ledger.yaml
docs/loops/<objective-id>/task-manifest.yaml
docs/loops/<objective-id>/current-task-summary.md
docs/loops/<objective-id>/iteration-YYYYMMDD-HHMM.md
docs/loops/<objective-id>/claims/<task-id>.yaml
```

Use the provided templates:

- `templates/orchestration/loop-engineering-spec.template.md`
- `templates/orchestration/loop-decision-input.template.yaml`
- `templates/orchestration/loop-event.template.yaml`
- `templates/orchestration/loop-state-ledger.template.yaml`
- `templates/orchestration/task-manifest.template.yaml`
- `templates/orchestration/current-task-summary.template.md`
- `templates/orchestration/loop-iteration-report.template.md`
- `templates/orchestration/task-claim-lease.template.yaml`

## Authority And State Model

The loop spec and task manifest define stable requirements and task
definitions. They do not duplicate mutable task status. The ledger contains an
append-only `events` array plus the reconstructed task, claim, gate, and loop
view. Claim records coordinate ownership only when their store can provide
atomic acquisition and fencing.

Git, verification, review, and accepted platform state provide completion
evidence. Goal state, subagent summaries, scheduler runs, hooks, Desktop thread
status, and chat summaries remain progress or coordination context.

Task status values:

| Status | Meaning |
| --- | --- |
| `planned` | Known task that is not ready to start. |
| `ready` | Dependencies, DoD, scope, and verification are clear enough to start. |
| `in_progress` | The task is actively being worked. |
| `blocked` | Progress requires a human decision or missing prerequisite. |
| `reviewing` | Implementation is ready for review or formal gate evidence. |
| `done` | The task's DoD and verification evidence are satisfied. |
| `accepted` | A maintainer or required gate accepted the completed task. |
| `cancelled` | Work was explicitly removed from the active objective. |

`done` is not the same as `accepted`. Use `done` when evidence supports task
completion. Use `accepted` only when the required human, review, or merge gate
has explicitly accepted that result.

Claim and lease files have a separate lifecycle: `active`, `released`,
`expired`, or `revoked`. Safety selection is a blocker kind rather than a task
lifecycle status.

## Source Revision

Every ledger artifact should record the source revision it was based on:

```yaml
source_revision:
  branch: "<branch>"
  head_sha: "<git-sha>"
  spec_sha256: "<sha256>"
  task_manifest_sha256: "<sha256>"
  previous_ledger_sha256: "<sha256-or-empty>"
  # migration_source_sha256: "<immutable-v1-source-sha256>"  # migration snapshots only
  updated_at: "<iso-8601>"
state_revision:
  sequence: 0
  last_event_hash: "<event-sha256-or-empty>"
```

The contract revision protects stable definitions; the state revision protects
operational writers. A mutating event must name the expected sequence and
previous event hash. The ledger must never contain a hash of its own complete
bytes; use a previous snapshot hash or canonical payload hash that excludes the
integrity field.

Event timestamps are non-decreasing, and `source_revision.updated_at` matches
the final event. `objective_completed` is terminal: after it is accepted, only
an idempotent replay of an existing request is allowed. Reopening an objective
requires a new reviewed objective/ledger rather than appending contradictory
state after completion.

For a V1 migration anchor, `migration_source_sha256` is immutable internal
integrity evidence for the embedded source. It is distinct from the rolling
`previous_ledger_sha256` and does not authenticate external origin.
Bound migration stores spec and manifest references as repository-relative
paths and rejects contract files outside the target repository.

Before transition preview, audit, or mutation, the CLI resolves the loop spec
and task manifest, verifies their recorded SHA-256 digests, and compares the
recorded branch and HEAD with the target git repository. Claim acquisition also
requires the same branch, HEAD, spec digest, and manifest digest. A task may
enter `ready` only after every manifest dependency is `done` or `accepted`.

## Claim And Lease Rules

Claims prevent duplicate work when a task may be handled by another session,
worker, worktree, or Desktop thread.

Baseline rules:

- A ready task acquires an `active` claim before moving to `in_progress`.
- A valid claim requires an owner, lease, expected state revision, and fencing
  token containing a monotonically increasing generation plus unique nonce.
- Every owner transition must present the current fencing token.
- The active claim may remain through `reviewing` and `done`; release it before
  `accepted`. Expiry or revocation atomically materializes the task as
  `blocked`, so a stale owner cannot submit a later result.
- An active claim with an unexpired lease must not be reassigned.
- An expired lease is not automatic permission to overwrite work. First inspect
  durable artifacts, git state, and any supported runtime observation.
- Reacquisition increments the fencing generation, so a late stale owner cannot
  write a result after recovery.
- Files in separate clones or worktrees are not a shared lock. Without an
  atomic shared claim store, the loop must use concurrency one or stop for a
  coordination decision.

## Evidence Requirements

Status changes need evidence:

| Status change | Required evidence |
| --- | --- |
| `planned` -> `ready` | Scope, DoD, dependencies, and verification command are known. |
| `ready` -> `in_progress` | Active fenced claim, owner, lease, source revision, and selected execution mode. |
| Any -> `blocked` | Blocker reason and required human decision or missing artifact. |
| `in_progress` -> `reviewing` | Diff or changed artifact summary plus verification run. |
| `reviewing` -> `done` | Verification evidence and required review or gate evidence. |
| `done` -> `accepted` | Explicit maintainer or required platform acceptance evidence. |

Every mutation also requires a unique event id, idempotency key, expected state
revision, previous event hash, actor, timestamp, and canonical event hash.
Replaying the same idempotency key with identical input is a no-op; reusing it
with different input is rejected.

Protected actions add two independent requirements:

- The event receipt binds the exact action, actor/principal, task or gate scope,
  objective identity, concrete evidence artifact, immutable
  branch/HEAD/spec/manifest source digest, and canonical digest of the full
  protected payload excluding the authorization object. Rolling ledger
  timestamps and previous-snapshot hashes are excluded so a valid receipt
  remains replayable.
- The live write receives the exact action and authorization receipt digest
  from current-session control-plane input after the human or platform artifact
  is verified. Repository YAML cannot supply this authority.

The installed CLI keeps preview and mutation explicit:

```bash
python3 <installed-skill>/scripts/loopctl.py decide <decision-input.yaml> --protected-history-sha256 <verified-digest-or-none>
python3 <installed-skill>/scripts/loopctl.py validate <ledger.yaml>
python3 <installed-skill>/scripts/loopctl.py audit <ledger.yaml> --manifest <task-manifest.yaml>
python3 <installed-skill>/scripts/loopctl.py hash-event <event.yaml>
python3 <installed-skill>/scripts/loopctl.py transition <ledger.yaml> <task-id> <target> --manifest <task-manifest.yaml>
python3 <installed-skill>/scripts/loopctl.py transition <ledger.yaml> <task-id> <target> --manifest <task-manifest.yaml> --protected-history-sha256 <verified-history-digest>
python3 <installed-skill>/scripts/loopctl.py apply-event <ledger.yaml> <event.yaml> --manifest <task-manifest.yaml>
python3 <installed-skill>/scripts/loopctl.py apply-event <ledger.yaml> <event.yaml> --manifest <task-manifest.yaml> --write
python3 <installed-skill>/scripts/loopctl.py apply-event <ledger.yaml> <event.yaml> --manifest <task-manifest.yaml> --write --authorize-action <exact-action> --authorization-receipt-sha256 <verified-digest>
python3 <installed-skill>/scripts/loopctl.py apply-event <ledger.yaml> <event.yaml> --manifest <task-manifest.yaml> --write --protected-history-sha256 <verified-history-digest>
```

`transition` and `apply-event` without `--write` are read-only previews. A
protected preview reports its required action and receipt digest but does not
claim live authorization. Semantic audit uses the same replay-only integrity
path and must never be treated as authentication or publication authority.
`audit` reports the exact protected-history digest. A live transition or write
that consumes historical protected state requires current-session
re-attestation with `--protected-history-sha256`; repository history cannot
authorize itself. Idempotent replay remains a no-op and reports live
authorization as false.
`apply-event --write` validates the expected revision, current fencing token,
event type, idempotency input, and event hash before atomically replacing the
materialized ledger. The previous file digest is recorded as snapshot evidence.
The write path also uses a same-filesystem exclusive lock and a final byte-level
compare-and-swap check. This prevents cooperating processes from silently
overwriting one ledger path; it is not an atomic claim store across clones or
worktrees, so those environments still require concurrency one or an external
shared coordination adapter.

After atomic replacement, the CLI fsyncs the parent directory. If replacement
has committed but that durability sync fails, it returns nonzero with
`status: applied-durability-uncertain`, `writes_performed: true`, and a warning
that the ledger must be inspected before retrying. This outcome is not a safe
automatic retry signal.

Before consuming `accepted`, satisfied gate, or complete state for an external
action, revalidate the current approval or platform state. The durable receipt
explains what was previously authorized; it does not guarantee that an
external approval remains current.

Worker self-reports and chat summaries are context only. They help locate
artifacts but cannot prove completion without repository files, diffs,
verification output, review evidence, or accepted platform state.

## Loop Decision Rules

Each iteration must end with one decision:

- `continue`: another safe task or same-task action is ready.
- `handoff-prepared`: a prompt, task brief, or worker claim is ready, but the
  handoff action itself still follows runtime and human-gate rules.
- `blocked-by-human-gate`: the next safe step needs a human decision.
- `complete`: every explicit requirement, DoD item, verification item, review
  item, and human gate is satisfied by current evidence.

Do not mark a loop complete from intent, summaries, or passing tests alone.

## Runtime Boundary

The repo-owned ledger works in Codex CLI and Codex Desktop because it uses
ordinary files and git state.

Desktop-only features such as heartbeat automations and user-owned task,
worktree, or thread control may update or reference the ledger only through
documented runtime capabilities and exact authorization.

Sub-agents may work on tasks, but their reports must be verified against the
ledger, changed files, git diff, verification commands, and review evidence.

## Optional V2b External Memory

The V2b contract can validate future adapter records and record an advisory
receipt digest in the ledger. It may help locate active objectives, likely next
tasks, or prior context, but a receipt never proves task acceptance or loop
completion. Disabled/unavailable memory is the normal safe fallback. Concrete
storage, search, invalidation, deletion, or synchronization belongs to V2c.

When present, `external_memory` uses the exact `loop-memory/v1` reference
shape. `mode` is `disabled`, `advisory-cache`, or `coordination`;
`backend_status` is `disabled`, `unavailable`, `used`, or `degraded`.
`disabled` mode and status must appear together with no adapter or receipt.
`unavailable` requires a non-disabled mode and an opaque adapter id, but no
receipt. `used` or `degraded` requires a non-disabled mode, an opaque adapter
id, and at least one unique SHA-256 receipt digest. `authority` is always
`advisory-only`; `used_as_authorization` and
`used_as_completion_evidence` are always `false`. Unknown fields and
contradictory combinations fail ledger validation.

An opaque adapter id is 1–128 characters, starts with an ASCII letter or
digit, and thereafter contains only ASCII letters, digits, `.`, `_`, `:`, or
`-`. It is an identifier, not a URL, filesystem path, or backend locator.
