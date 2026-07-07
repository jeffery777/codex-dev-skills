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
