# Loop Iteration Report

## Objective

- Loop objective: `<objective>`
- Issue or source-of-truth reference: `<url-or-path>`
- Branch: `<branch>`
- Head: `<sha>`
- Source revision: `<branch>@<sha>`
- Task manifest: `<path>`
- Current task: `<task-id-or-none>`

## Bootstrap Evidence

- Repo instructions read:
  - `<path>`
- Specs/plans/manifests read:
  - `<path>`
- Review or gate evidence read:
  - `<path>`
- Git state checked:
  - `<command-or-summary>`

## Classification

- Current loop state: `<single-clear-task | bounded-delivery-objective | review-closure-loop | milestone-continuation-loop | handoff-or-continuation | shared-subagent-delegation | desktop-delegation | human-gate | complete>`
- Selected route: `<skill-or-workflow>`
- Execution mode: `<current-session | shared-subagents | sequential-fallback | desktop-scheduled | desktop-thread | stop-for-human-gate>`

## Task Ledger Update

- Task id: `<task-id-or-none>`
- Previous status: `<planned | ready | in_progress | blocked | reviewing | done | accepted | cancelled | none>`
- New status: `<planned | ready | in_progress | blocked | reviewing | done | accepted | cancelled | none>`
- Claim / lease: `<acquired | renewed | released | revoked | unchanged | not-applicable>`
- State revision / event: `<sequence>@<event-hash>`
- Claim fencing token: `<generation>:<nonce-or-not-applicable>`
- Blocked reason: `<reason-or-empty>`
- Evidence artifact written:
  - `<path-or-none>`

## Work Performed

- Files changed:
  - `<path>`
- Summary:
  - `<item>`

## Verification

```bash
<command>
```

Result: `<passed | failed | skipped>`

## Review Or Gate Evidence

- Review primitive: `<none | code-review | code-review-deep | docs-review | merge-review | merge-review-deep>`
- Formal gate: `<none | code-review-gate | docs-review-gate | merge-readiness-gate | desktop-implementation-gate | desktop-pr-merge-gate>`
- Findings:
  - `<finding-or-none>`
- Exact-head merge-review state: `<not-applicable | PR_CREATED | EXACT_HEAD_CI_PASSED | EXACT_HEAD_MERGE_REVIEW_PASSED | RECEIPT_PLATFORM_READBACK_CONFIRMED | MERGE_READINESS_READY | HUMAN_MERGE_AUTHORIZED | REVIEW_REQUIRED>`
- PR/base/head/merge-base/diff binding: `<evidence-or-none>`
- Hosted CI and review-thread binding: `<evidence-or-none>`
- Platform receipt ID/digest/readback: `<evidence-or-none>`
- Pre-commit evidence reuse rationale: `<rationale-or-none>`

## Next Decision

- Iteration result: `<continue | handoff-prepared | blocked-by-human-gate | complete>`
- Next selected task: `<task-id-or-none>`
- Human decision needed: `<yes | no>`
- Residual risk:
  - `<risk-or-none>`
