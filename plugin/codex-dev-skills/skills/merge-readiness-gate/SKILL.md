---
name: merge-readiness-gate
description: Thin formal gate that keeps exact-head content readiness separate from optional provider enforcement.
---

# merge-readiness-gate

Runtime compatibility: shared

Exact-head content evidence: follow
`../../policies/exact-head-merge-review-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation.

Release state: when the diff or readiness decision is release-sensitive,
follow `../../policies/release-state-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/release-state-contract.md`
after filesystem installation.

When repository policy selects GitHub hosted enforcement, additionally follow
`../../policies/github-exact-head-enforcement-profile.md` in source or plugin
checkouts, or its installed
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/github-exact-head-enforcement-profile.md`
copy after filesystem installation. Also follow
`../../policies/github-control-plane-policy.md` in source or plugin checkouts,
or its installed
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/github-control-plane-policy.md`
copy after filesystem installation. Do not load or require that profile for an
unselected provider.

## Purpose

Use this skill only when a workflow needs a formal decision before change-
request handoff, merge readiness, or final human approval. It summarizes
existing review and verification evidence; it is not another review primitive
and does not authorize an external write.

## Workflow

1. Confirm repository, exact base/head/merge-base revisions, changed files,
   diff identity, and change-request/provider identity when applicable.
2. Read the plan, DoD, current `merge-review` or `merge-review-deep` evidence,
   verification output, dispositions, and unresolved questions.
3. Require a current complete base-to-head content review. Pre-commit or prior-
   head verdicts cannot satisfy this gate.
4. Require deterministic offline validation plus explicit semantic code ↔ docs
   coherence evidence. Tests alone are insufficient.
5. Decide `content_review` independently as
   `PASSED | BLOCKED | NEEDS_HUMAN_DECISION`.
6. Determine whether repository policy selected a provider profile:
   - no profile: `platform_enforcement: NOT_CONFIGURED`;
   - selected but unreadable/incomplete: `UNVERIFIED`;
   - selected with a failing or stale requirement: `BLOCKED`;
   - selected with complete current evidence: `VERIFIED`.
7. A required provider profile that is not `VERIFIED` blocks overall formal
   merge readiness, but does not erase a valid content-review result. GitHub-
   specific receipts, checks, Apps, Actions, or rulesets are required only by
   the selected GitHub profile.
8. For release-sensitive work, keep source/package version, candidate
   preparation, provider publication truth, active guidance, and historical
   records distinct.
9. A changed head invalidates content review; relevant provider drift
   invalidates provider verification. Repeat final provider readback only when
   that selected profile requires it.
10. Stop for final human approval before commit, push, change-request creation,
    merge, deploy, provider comments/reviews, publication, or another external
    write unless the exact action is already authorized.

## Output

- Content Review: PASSED | BLOCKED | NEEDS_HUMAN_DECISION
- Platform Enforcement: VERIFIED | UNVERIFIED | BLOCKED | NOT_CONFIGURED
- Overall Formal Gate: READY | BLOCKED | NEEDS_HUMAN_DECISION
- Exact base/head/merge-base and diff identity
- Code/documentation coherence and verification evidence
- Findings and dispositions
- Selected provider profile and evidence, if any
- Residual risk
- Human approval boundary
