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

The repo-owned ledger is the source of truth for task selection, claim state,
completion evidence, and next-loop decisions. External memory, runtime
summaries, worker reports, and chat summaries are context only unless this
repository explicitly defines a stronger reviewed authority contract.

## Scope

### In Scope

- <item>

### Out Of Scope

- <item>

## Loop Policy

- Entry skill: `loop-engineering`
- Default execution mode: `<continue-current-session | sequential-execution | delegated-worker-brief | new-session-prompt>`
- Review closure round limit: `<number>`
- Desktop runtime actions allowed: `<none | read_thread | create_thread | fork_thread | send_message_to_thread>`
- External writes allowed only with exact authorization: `<yes | no>`

## Tasks

Use the task manifest as the task source of truth. Each task should include owner, claim, lease, DoD, verification, review, and human-gate fields when delegation or repeated invocation is expected.

Allowed task statuses:

- `planned`
- `ready`
- `claimed`
- `in_progress`
- `blocked`
- `reviewing`
- `done`
- `accepted`
- `unsafe`

`done` requires verification evidence and any required review or gate evidence.
`accepted` requires maintainer, merge, release, or formal gate acceptance
evidence.

## Claim And Lease Policy

- Ready tasks must be claimed before worker or thread delegation.
- Claimed or in-progress tasks with unexpired leases must not be reassigned.
- Expired leases require durable artifact inspection before recovery.
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
