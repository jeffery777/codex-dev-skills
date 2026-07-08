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

- Current loop state: `<single-clear-task | bounded-delivery-objective | review-closure-loop | milestone-continuation-loop | handoff-or-continuation | desktop-delegation | human-gate | complete>`
- Selected route: `<skill-or-workflow>`
- Execution mode: `<current-session | sequential-execution | prompt-only | delegated-worker-brief | desktop-runtime-action | stop-for-human-gate>`

## Task Ledger Update

- Task id: `<task-id-or-none>`
- Previous status: `<planned | ready | claimed | in_progress | blocked | reviewing | done | accepted | unsafe | none>`
- New status: `<planned | ready | claimed | in_progress | blocked | reviewing | done | accepted | unsafe | none>`
- Claim / lease: `<created | extended | released | unchanged | not-applicable>`
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

## Next Decision

- Iteration result: `<continue | handoff-prepared | blocked-by-human-gate | complete>`
- Next selected task: `<task-id-or-none>`
- Human decision needed: `<yes | no>`
- Residual risk:
  - `<risk-or-none>`
