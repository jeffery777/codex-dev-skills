# Repo-Owned Loop State And Ledger

Repo-owned loop state is the baseline memory layer for `loop-engineering`.
It lets Codex recover, continue, hand off, and audit a bounded objective without
requiring an external memory adapter.

External memory may be added later as an optional acceleration or coordination
layer. It must not replace this repository-owned ledger as the source of truth
unless a target repository explicitly defines and reviews that stronger
authority model.

## Purpose

A loop ledger records enough durable state for any later Codex session or
maintainer to answer these questions from repository files:

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
- `templates/orchestration/loop-state-ledger.template.yaml`
- `templates/orchestration/task-manifest.template.yaml`
- `templates/orchestration/current-task-summary.template.md`
- `templates/orchestration/loop-iteration-report.template.md`
- `templates/orchestration/task-claim-lease.template.yaml`

## State Model

Task status values:

| Status | Meaning |
| --- | --- |
| `planned` | Known task that is not ready to start. |
| `ready` | Dependencies, DoD, scope, and verification are clear enough to start. |
| `claimed` | A session or worker has claimed the task but has not reported active work yet. |
| `in_progress` | The task is actively being worked. |
| `blocked` | Progress requires a human decision or missing prerequisite. |
| `reviewing` | Implementation is ready for review or formal gate evidence. |
| `done` | The task's DoD and verification evidence are satisfied. |
| `accepted` | A maintainer or required gate accepted the completed task. |
| `unsafe` | The task is known but should not be selected without redesign or explicit approval. |

`done` is not the same as `accepted`. Use `done` when evidence supports task
completion. Use `accepted` only when the required human, review, or merge gate
has explicitly accepted that result.

Claim and lease files have their own lifecycle status, such as `stale` or
`released`. Do not confuse claim lifecycle status with task status in the loop
ledger.

## Source Revision

Every ledger artifact should record the source revision it was based on:

```yaml
source_revision:
  branch: "<branch>"
  head_sha: "<git-sha>"
  manifest_sha256: "<sha256-or-empty>"
  updated_at: "<iso-8601>"
```

The source revision prevents stale chat summaries, stale handoff prompts, or
older worker reports from silently overriding newer repository state. If a
source revision is missing or conflicts with git state, the loop should
re-bootstrap before selecting or completing a task.

## Claim And Lease Rules

Claims prevent duplicate work when a task may be handled by another session,
worker, worktree, or Desktop thread.

Baseline rules:

- A task should move from `ready` to `claimed` before delegation.
- A task should move from `claimed` to `in_progress` when work actually begins.
- A valid lease requires an owner, `claimed_at`, `lease_expires_at`, and source
  revision.
- A claimed or in-progress task with an unexpired lease must not be reassigned.
- An expired lease is not automatic permission to overwrite work. First inspect
  durable artifacts, git state, and any supported runtime observation.
- Recovery should choose the lowest-risk action: wait, extend the lease, ask a
  human, mark blocked, or release the claim after evidence supports doing so.

## Evidence Requirements

Status changes need evidence:

| Status change | Required evidence |
| --- | --- |
| `planned` -> `ready` | Scope, DoD, dependencies, and verification command are known. |
| `ready` -> `claimed` | Owner, lease, source revision, and selected execution mode. |
| `claimed` -> `in_progress` | Work has started and the lease remains valid. |
| Any -> `blocked` | Blocker reason and required human decision or missing artifact. |
| `in_progress` -> `reviewing` | Diff or changed artifact summary plus verification run. |
| `reviewing` -> `done` | Verification evidence and required review or gate evidence. |
| `done` -> `accepted` | Maintainer, merge, release, or formal gate acceptance evidence. |

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

Desktop-only features such as heartbeat automations, worktree creation, thread
creation, thread inspection, and worker messaging may update or reference the
ledger only through documented runtime capabilities and exact authorization.

Sub-agents may work on tasks, but their reports must be verified against the
ledger, changed files, git diff, verification commands, and review evidence.

## Optional External Memory Later

Future external memory adapters should be cache or coordination layers by
default. They may help list active objectives, find likely next tasks, or store
iteration summaries, but loop completion and task acceptance still require
repo-owned ledger evidence unless a repository deliberately defines a stronger
authority contract.
