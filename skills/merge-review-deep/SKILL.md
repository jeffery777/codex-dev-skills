---
name: merge-review-deep
description: Higher-scrutiny merge review for high-risk, release-sensitive, or policy-required changes.
---

# merge-review-deep

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

For release-sensitive review, follow
`../../policies/release-state-contract.md` relative to this skill in source or
plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/release-state-contract.md`
after filesystem installation.

Exact-head evidence: follow
`../../policies/exact-head-merge-review-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation when a PR exists or merge readiness is assessed.

## Purpose

Use this skill for high-risk, release-sensitive, or policy-required merge review where routine `merge-review` is insufficient.

This is a deeper review primitive, not the formal branch readiness gate. Use `merge-readiness-gate` when a workflow must summarize evidence into a branch readiness decision before PR handoff, merge readiness, or final human approval. The deep review result is evidence only; it does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Additional Focus

- closure quality for prior findings
- rollback or recovery path
- security and privacy readiness
- data or migration safety
- stale artifact reuse
- hidden regression risk
- release and operational evidence
- transition-safe release state across source/package, candidate,
  publication, active-guidance, and historical-record roles

## Workflow

Follow `merge-review`, then re-check evidence from source files and commands rather than relying only on summaries.

Re-evaluate whether pre-commit review and Security Diff Scan evidence still
applies to the exact head. After a fix, rerun those reviews over the smallest
scope that proves the remediation and its affected boundaries, widening when
their assumptions changed. A changed PR head always requires a new complete
base-to-head Merge Review and platform receipt readback.

For a configured hosted gate, independently inspect its dedicated GitHub App
identity, check/run identity, live-head attachment, strict JSON receipt digest,
and upstream-CI exclusion. Treat any drift in base/head/merge-base/range, CI,
findings, review threads, receipt, or gate identity as a blocker; the check
does not itself authorize merge.

For a release-sensitive change, classify every relevant assertion into the
five release-state roles, run the offline release-state validator, and verify
that active guidance remains true after successful publication. Distinguish
pre-mutation payload/conflict checks from post-mutation platform readback;
neither tests nor a proposed tag/Release payload prove publication.

## Output

Use the `merge-review` output structure and add Deep Gate Notes.
