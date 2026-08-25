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

Use `exact-head-merge-review/v1` for normalized offline validation. The receipt
and connector-read platform snapshot must agree on:

- repository and positive pull-request number;
- exact 40-hex base, head, and merge-base SHAs;
- a deterministic diff digest;
- `merge-review` or `merge-review-deep` mode;
- required hosted CI names, run identifiers, exact head SHAs, and successful
  conclusions;
- current open, non-draft, mergeable state;
- zero unresolved review threads;
- zero open `MUST-FIX`, `SHOULD-FIX`, and `NIT` findings after recorded
  dispositions;
- a positive platform receipt identifier and matching GitHub issue-comment or
  pull-request-review URL, canonical receipt digest, and readback time;
- `receipt_authority: advisory_review_evidence` and
  `merge_authorized: false`.

The offline validator consumes normalized data already read through the GitHub
connector-first control plane. It does not access GitHub, authenticate the
reviewer, create a receipt, submit a review, authorize merge, or replace the
final live readback immediately before an authorized merge.

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

## Platform Enforcement Boundary

This repository contract makes conforming Codex workflows fail closed. It
cannot prevent a person or another integration from bypassing the workflow and
pressing Merge. Repository owners should separately consider a GitHub ruleset
that requires pull requests, exact-head CI, resolved conversations, stale
approval dismissal, and an applicable required review or check. Ruleset
creation and bypass policy remain separate platform decisions.

## Authority Boundary

This contract does not authorize commit, push, pull-request creation, platform
comments or reviews, merge, tag creation, GitHub Release publication,
deployment, ruleset mutation, or another external write.
