---
name: merge-readiness-gate
description: Thin formal branch readiness gate after implementation, verification, and review evidence exist.
---

# merge-readiness-gate

Runtime compatibility: shared

GitHub control plane: follow
`../../policies/github-control-plane-policy.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/github-control-plane-policy.md`
after filesystem installation, when GitHub metadata or mutations are involved.

Release state: when the diff or readiness decision is release-sensitive,
follow `../../policies/release-state-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/release-state-contract.md`
after filesystem installation.

Exact-head evidence: follow
`../../policies/exact-head-merge-review-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation when the gate concerns an existing PR.

## Purpose

Use this skill only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval.

This gate is a thin adapter and evidence-and-decision layer around existing review primitives. It summarizes verification, review evidence, blocking decisions, residual risk, and the human approval boundary. It is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Workflow

1. Confirm repository, PR, exact base/head/merge-base SHAs, remote identity,
   changed files, and diff identity.
2. Read plan, DoD, review reports, verification evidence, and unresolved questions.
3. Run or read current `merge-review` or `merge-review-deep` evidence based on
   risk. Pre-commit evidence is input only and cannot satisfy this PR-bound gate.
4. Require successful exact-head hosted CI, zero unresolved review threads,
   closed findings, a platform-visible receipt, and connector-first readback
   whose normalized `exact-head-merge-review/v1` evidence validates offline.
   When configured, also require `Exact-Head Merge Readiness` from its
   dedicated GitHub App, attached to the live PR head and validated as
   `exact-head-merge-readiness/v2`; the upstream CI set cannot contain this
   check. The receipt is supplied by a complete strict JSON body with a
   canonical receipt digest, not a Markdown parsing convention.
   In source or plugin checkouts use
   `../../scripts/validate-exact-head-merge-review.py`; filesystem installation
   uses
   `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/scripts/validate-exact-head-merge-review.py`
   with the active workflow's qualified Python interpreter.
5. For release-sensitive work, verify the offline source/package and candidate
   roles separately from connector-read tag/Release publication truth; reject
   tracked mutable publication assertions and unjustified historical-note
   rewrites.
6. Return `BLOCKED` when any receipt or hosted-gate binding is missing or
   stale. Base/head/merge-base, diff, CI, finding, thread, receipt, source-App,
   or gate-run drift invalidates `READY`.
7. Stop for final human approval before commit, push, merge, deploy, destructive actions, platform comments, review submissions, or external publication unless the user has explicitly authorized the exact action.
8. Before any authorized merge or platform-side mutation, repeat live readback,
   confirm every receipt binding still matches, and verify no blocker remains.

## Output

- Gate Result: READY | BLOCKED | NEEDS HUMAN DECISION
- Base and head
- PR, diff, CI, thread, platform receipt, and configured hosted-gate bindings
- Evidence reviewed
- Blockers
- Residual risk
- Human approval boundary
- Next human decision or action boundary
