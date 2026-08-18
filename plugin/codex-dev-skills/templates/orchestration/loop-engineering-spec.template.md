# Loop Engineering Spec: <objective-name>

Copy this template into a target repository only when a bounded objective needs an explicit loop engineering source of truth.

## Objective

<State the bounded objective Codex should advance.>

## Source Of Truth

- Repo instructions: `<path>`
- Project spec: `<path>`
- Implementation plan: `<path>`
- Task manifest: `<path>`
- Status or continuation report: `<path>`
- Review evidence: `<path>`

## Repo-Owned Loop Ledger

- Ledger root: `<docs/loops/objective-id>`
- Task manifest: `<docs/loops/objective-id/task-manifest.yaml>`
- Current task summary: `<docs/loops/objective-id/current-task-summary.md>`
- Iteration reports: `<docs/loops/objective-id/iteration-*.md>`
- Claim / lease files: `<docs/loops/objective-id/claims/*.yaml>`
- Source revision: `<branch>@<head-sha>`

The loop spec and task manifest define stable requirements. Validated events
define operational task transitions, and the ledger is their materialized
current view. A shared atomic store may coordinate ownership with fenced claims;
without one, concurrency is one. Git, verification, review, and accepted
platform state prove completion. Runtime summaries and chat summaries are
context only.

## Scope

### In Scope

- <item>

### Out Of Scope

- <item>

## Loop Policy

- Entry skill: `loop-engineering`
- Default execution mode: `<current-session | shared-subagents | sequential-fallback | desktop-scheduled | desktop-thread>`
- Review closure round limit: `<number>`
- Desktop runtime actions allowed: `<none | read_thread | create_thread | fork_thread | send_message_to_thread>`
- External writes allowed only with exact authorization: `<yes | no>`

## Tasks

Use the task manifest for stable task definitions. Mutable status comes from
validated events and the materialized ledger; claims are a separate,
fenced coordination lifecycle.

Allowed task statuses:

- `planned`
- `ready`
- `in_progress`
- `blocked`
- `reviewing`
- `done`
- `accepted`
- `cancelled`

`done` requires verification evidence and any required review or gate evidence.
`accepted` requires maintainer, merge, release, or formal gate acceptance
evidence.

## Claim And Lease Policy

- Ready tasks must acquire an active fenced claim before work begins.
- Active claims with unexpired leases must not be reassigned.
- Expired leases require durable artifact inspection before recovery.
- Reacquisition increments the fencing generation; stale owners cannot submit
  later transitions.
- Separate clones or worktrees default to concurrency one unless a shared claim
  store can provide atomic acquisition.
- Worker self-reports are context only; completion requires ledger, diff,
  verification, review, or platform evidence.

## Definition Of Done

- <criterion>

## Verification

```bash
<command>
```

## Human Gates

Stop before:

- product ambiguity or source-of-truth conflict
- scope expansion
- destructive actions
- external writes without exact authorization
- commit, push, PR creation, release, deploy, merge, platform comments, review submissions, label/status changes, or other platform mutation without exact authorization
- material security, privacy, data, migration, payment, deployment, auth, permission, packaging, or public-contract risk
- unsupported Desktop runtime behavior
- insufficient verification for a high-risk change
