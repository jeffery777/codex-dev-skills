---
name: merge-review
description: Normal user-facing entry point for provider-neutral exact-head merge quality, coherence, and DoD review.
---

# merge-review

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

Exact-head content evidence: when a pull request, merge request, another change
request, or formal merge-readiness range exists, follow
`../../policies/exact-head-merge-review-contract.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation.

## Purpose

Use this skill for ordinary complete base-to-head merge quality, content
coherence, and DoD review. The review is provider-neutral and may run against a
GitHub pull request, GitLab merge request, another forge object, or an exact
local range.

This is review evidence, not a formal branch gate. It does not authorize
commit, push, change-request creation, merge, deployment, provider comments,
review submission, or another external write.

## Workflow

1. Confirm repository identity, exact base/head/merge-base revisions, complete
   diff identity, and change-request identity when one exists.
2. Read repo instructions, plan, DoD, prior reviews, and verification evidence.
3. Inspect the complete diff for scope alignment, missing tests, regressions,
   and unresolved findings. Pre-commit evidence is reusable input only.
4. Run deterministic offline repository, version/package, schema, generated-
   artifact, and documentation checks supplied by the repository.
5. Perform an explicit code ↔ documentation coherence review: compare user-
   visible claims, commands, paths, feature states, compatibility statements,
   configuration, release scope, and migration guidance with source evidence.
   Record why no docs change is needed when behavior changes without one.
6. Classify every finding and retain a durable disposition. Report residual
   risk even when verification passes.
7. If repository policy selects a provider enforcement profile, inspect that
   profile separately. Do not require GitHub or another provider merely to pass
   content review, and do not infer provider verification from content review.
8. Report both dimensions:
   - `content_review: PASSED | BLOCKED | NEEDS_HUMAN_DECISION`
   - `platform_enforcement: VERIFIED | UNVERIFIED | BLOCKED | NOT_CONFIGURED`

A changed head invalidates the exact-head content verdict and requires a new
complete base-to-head review. State explicitly that neither dimension
authorizes merge.

## Output

- Content Review status
- Platform Enforcement status
- Base/head/merge-base and diff identity
- Blocking and non-blocking findings
- DoD and code/documentation coherence
- Deterministic verification evidence
- Finding dispositions
- Selected provider profile evidence, if any
- Residual risk
- Required human gate
