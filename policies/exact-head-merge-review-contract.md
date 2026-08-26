# Exact-Head Merge-Review Contract

Use this contract after a pull request exists and before any workflow reports
merge readiness. It prevents implementation review evidence from being
mistaken for review of the immutable pull-request head.

## Evidence Roles

Pre-commit code, documentation, deep, and security reviews prove properties of
the content they inspected. They may be reused as inputs to later review when
their source revision and scope still match, but their verdict does not satisfy
exact-head Merge Review.

Exact-head Merge Review is a separate base-to-head integration review. Its
platform-visible receipt binds repository, pull-request number, exact base,
head and merge-base SHAs, diff identity, review mode, and findings. The current
platform snapshot separately binds required hosted CI, PR state, review-thread
state, receipt identity and digest, and readback time. The complete normalized
evidence plus the report's residual-risk section supports the gate; a local
report, chat handoff, worker summary, goal state, or pre-PR review is not a
substitute.

Merge readiness is the formal decision that the exact-head evidence is current
and complete. Merge authorization remains a separate human or accepted
platform action. Review evidence must always state that it does not authorize
merge.

## Required Transition

The only successful transition is:

```text
PR_CREATED
  -> EXACT_HEAD_CI_PASSED
  -> EXACT_HEAD_MERGE_REVIEW_PASSED
  -> RECEIPT_PLATFORM_READBACK_CONFIRMED
  -> MERGE_READINESS_READY
  -> HUMAN_MERGE_AUTHORIZED
```

Do not skip a state or infer one from a later state. PR creation or a new push
invalidates every pre-commit verdict for merge-readiness purposes. A change to
the repository identity, PR number, base, head, merge base, diff identity,
required CI result, finding disposition, unresolved review threads, or receipt
readback returns the flow to `REVIEW_REQUIRED` at the earliest affected state.

## Receipt And Snapshot

`exact-head-merge-review/v1` remains the advisory-review evidence vocabulary.
Use `exact-head-merge-readiness/v2` for the hosted, platform-enforced
normalized envelope. The v2 envelope has exactly `contract`, `receipt`,
`platform_snapshot`, and `gate` top-level fields. Its strict JSON receipt is
the authoritative data contract; a human-readable Markdown rendering may
accompany it, but Markdown scraping must not be used to reconstruct evidence.

The v2 receipt and connector-read platform snapshot must agree on:

- repository and positive pull-request number;
- a positive exact-head `receipt_sequence` that uniquely orders structured
  receipts without relying on cross-object IDs or timestamps;
- exact 40-hex base, head, and merge-base SHAs;
- a deterministic, versioned canonical range-identity digest;
- `merge-review` or `merge-review-deep` mode;
- required hosted CI workflow IDs, names, paths, events, policy-pinned Git
  blobs, run attempts, the
  trusted `exact-pr-head/v1` display-title binding to PR number/head SHA, and
  successful conclusions;
- current open, non-draft, mergeable state;
- zero unresolved review threads;
- zero open `MUST-FIX`, `SHOULD-FIX`, and `NIT` findings after recorded
  dispositions;
- a positive platform receipt identifier and matching GitHub issue-comment
  URL, canonical receipt digest from the complete strict
  JSON receipt body, and readback time;
- `receipt_authority: advisory_review_evidence` and
  `merge_authorized: false`.

The `receipt` records the reviewed identity, findings and dispositions,
residual risk, reusable pre-commit evidence, and the required-CI policy. Each
required-CI identity includes its policy-pinned workflow ID/name/path/event and
Git blob, run and attempt, policy context, trusted display-title PR/head
binding, conclusion, and repository/run-bound details URL. The `platform_snapshot` repeats the live
base/head/merge-base/range identity and
binds the receipt readback, upstream checks, unresolved-thread count and
digest, and findings digest. The `gate` records the publishing workflow/run,
the `Exact-Head Merge Readiness` check and run, its source App identity, exact
head SHA, and conclusion. The upstream required-CI set must not include the
gate itself.

The offline validator consumes normalized data already read through the GitHub
connector-first control plane. It does not access GitHub, authenticate the
reviewer, create a receipt, submit a review, authorize merge, or replace the
final live readback immediately before an authorized merge. Ordinary offline
repository validation remains network-independent; the hosted collector reads
GitHub state, normalizes it, and invokes the validator on that bounded input.

In source or plugin checkouts, run the validator at
`scripts/validate-exact-head-merge-review.py`. Filesystem installation places
the same file at
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/scripts/validate-exact-head-merge-review.py`.
Invoke it with the active workflow's qualified Python interpreter and one
explicit normalized JSON input path or `-` for bounded stdin.

## Review And Remediation Scope

After a finding is fixed, rerun code review and Security Diff Scan over the
smallest scope that can prove the fix and its affected boundaries. Record why
unchanged prior evidence remains applicable. Escalate to a wider rerun when the
fix changes shared contracts, data or trust boundaries, generated artifacts,
packaging, or the assumptions of earlier evidence.

Any changed PR head still requires a new exact-head Merge Review and receipt
readback over the complete base-to-head integration risk. Proportional fix
review never permits reusing an old exact-head verdict for a new SHA.

When required reviews and scans have no unresolved findings, the workflow may
advance autonomously through later read-only or already-authorized stages.
Stop only for an actual human decision, missing authority, environment or
permission failure, material ambiguity or risk, destructive action, or an
external write that has not already been authorized for the bounded objective.

## Hosted Enforcement And Trust Boundary

The hosted `Exact-Head Merge Readiness` check is the platform-enforced v2
projection of this contract. A trusted default-branch collector must resolve
the live pull request and write the check explicitly to its current
`pull_request.head.sha`; it must never rely on `GITHUB_SHA` from
`issue_comment`, `workflow_run`, or another default-branch event. It must not
checkout, import, execute, cache, or consume artifacts from PR-head code.

The collector is published by a dedicated GitHub App identity with the minimum
metadata/read, pull-requests/read, issues/read, actions/read, and checks/write
permissions. Its credentials belong only to a protected environment usable by
trusted default-branch workflow code. Fork PRs may receive the same metadata
evaluation, but no PR-controlled code receives those credentials. A shared
GitHub Actions identity is not an adequate trust source for this check.

GitHub atomically enforces that the dedicated check succeeds on the current
head, strict up-to-date policy, and resolved review conversations. The
controller re-evaluates base, merge base, range identity, hosted CI,
finding disposition, current receipt body/digest, check identity, and source
App identity when a relevant event or scheduled reconciliation is processed.
The compact App pointer retains the current receipt sequence as a tombstone;
only a unique higher exact-head sequence can supersede it. This is an event-driven
projection, not an atomic transaction with the Merge click. A stronger
receipt/finding guarantee would require a GitHub-native pre-merge predicate or
App-controlled merge path, which remains outside this contract's authority.

The repository ruleset is the enforcement point. It must require pull
requests, block deletion and non-fast-forward updates, require resolved review
conversations, dismiss stale approvals after pushes, enable strict required
checks, and require `Exact-Head Merge Readiness` bound to the dedicated App
integration ID. Hosted CI is a policy-pinned input to the gate rather than a
same-name shared-App merge predicate. It has no bypass actors. Because a single-owner repository can
deadlock on self-approval, approval-count policy is a separate human decision;
it must not be substituted for the App-backed exact-head check.

Roll out in this order: merge and independently review the trusted controller;
register/install the App and protect its environment through separate human
gates; run a canary; read back its App integration ID; update the ruleset while
disabled; prove every documented drift case fails closed; then activate only
the `enforcement` field through another human gate and verify a fresh PR merge
box. Do not require the check before the canary identifies its App. The check
does not authorize auto-merge, merge, tag creation, Release publication, or
deployment.

## Authority Boundary

This contract does not authorize commit, push, pull-request creation, platform
comments or reviews, merge, tag creation, GitHub Release publication,
deployment, ruleset mutation, or another external write.
