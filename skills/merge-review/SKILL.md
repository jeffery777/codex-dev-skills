---
name: merge-review
description: Normal user-facing entry point for base-to-head merge quality and DoD review.
---

# merge-review

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

Exact-head evidence: when a pull request exists or merge readiness is being
assessed, follow `../../policies/exact-head-merge-review-contract.md` relative
to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation.

## Purpose

Use this skill for ordinary base-to-head merge quality and DoD review.

This is the normal user-facing merge review entry point. It reports review evidence and residual risk, but it is not a formal branch readiness gate and does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Workflow

1. Confirm repository, PR number, exact base/head/merge-base SHAs, and diff
   identity. A pre-commit review may supply evidence but cannot supply the
   exact-head verdict.
2. Read repo instructions, plan, DoD, prior reviews, and verification evidence.
3. Inspect the diff for scope alignment, missing tests, regressions, and unresolved review findings.
4. Read hosted CI and unresolved review threads through the platform control
   plane. Reject missing, failing, stale, or head-mismatched evidence.
5. Check that docs, migrations, and operational notes are updated when required.
6. Produce an exact-head receipt, publish it only with authority, and read it
   back before a formal gate reports merge readiness. Its authoritative body is
   strict JSON, not scraped Markdown. Where configured, verify the dedicated
   GitHub App's `Exact-Head Merge Readiness` v2 check is attached to the live
   PR head and binds the same base/head/merge-base/range identity, CI, findings,
   threads, receipt digest, and check identity. Native live-head and resolved-
   conversation rules apply at merge time; other relevant drift invalidates
   the hosted projection after the controller processes its event.
7. Report readiness with evidence and residual risk. State explicitly that the
   receipt does not authorize merge.

## Output

- Merge Readiness: Ready | Not Ready | Needs Human Decision
- Blocking Findings
- Non-blocking Findings
- DoD Alignment
- Verification Evidence
- PR-bound exact-head evidence, platform receipt readback, and configured
  hosted-gate identity
- Residual Risk
