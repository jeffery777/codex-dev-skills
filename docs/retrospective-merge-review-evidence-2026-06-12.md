# Retrospective Merge Review Evidence Notes - 2026-06-12

## Purpose

This document records retrospective audit notes for early merged pull requests that did not have a clean durable pre-merge formal merge review evidence trail on GitHub.

This is a retrospective evidence repair record. It does not assert that missing or late platform-side evidence existed before merge, and it does not convert local or post-merge evidence into a pre-merge formal review trail.

## Source Evidence

Primary audit artifact:

- `.work/inbox/codex-dev-skills-pr-formal-merge-review-audit.md`

GitHub metadata rechecked during this remediation:

- PR #1: `https://github.com/jeffery777/codex-dev-skills/pull/1`
- PR #2: `https://github.com/jeffery777/codex-dev-skills/pull/2`

## PR #1 Retrospective Audit Record

PR:

- Number: `#1`
- Title: `[codex] Slim review closure workflow skills`
- URL: `https://github.com/jeffery777/codex-dev-skills/pull/1`
- Merged at: `2026-06-04T10:12:09Z`
- Base SHA: `fd3f91fe449a53cf2dd774b079614e4a997c989f`
- Head SHA: `7b73a544a99b9274124f3a3205ac8725aebe6e88`
- Merge commit SHA: `8d57e14dbb5f0e2b31a17f5c4ee6cde15bdfd955`

Retrospective finding:

- PR #1 lacked durable platform-side formal merge review evidence at merge time.
- The PR body included a `Review Evidence` section, but that section referenced local `.work/review/...` paths rather than a GitHub PR comment, submitted PR review, or equivalent platform-visible formal merge review record.
- A remediation recheck found no PR discussion timeline item carrying formal merge review evidence for PR #1.

Still-verifiable evidence:

- The GitHub PR title, branch, merge state, timestamps, base/head SHAs, and merge commit SHA.
- The PR body references three local `.work/review/...` artifact paths: one timestamped code-review gate artifact and two `current/latest...` pointers.
- The PR body records validation commands:
  - `git diff --check`
  - `./install.sh manifest`
  - `./scripts/validate-repo.sh`
  - `rg -n "review-loop|review-follow-up-plan|review-follow-up-implementation|docs-review-follow-up|review-follow-up-review|review follow-up|follow-up skill" README.md docs workflows skills catalog.yaml install.sh templates`

No longer provable from durable platform evidence:

- Whether the referenced local `.work/review/...` artifacts were complete, unchanged, and reviewed before merge.
- Whether a formal merge review gate approved the exact PR #1 head before merge.
- Whether the local review evidence was available to future maintainers through a durable platform-side record at merge time.

Classification:

- Gap type: missing platform evidence.
- Status after this document: retrospectively recorded, not retroactively converted to a valid pre-merge platform evidence trail.

Residual risk:

- Historical process evidence gap only. This note does not identify a current code defect in PR #1.

## PR #2 Retrospective Timing Exception

PR:

- Number: `#2`
- Title: `[codex] Clarify code review entrypoint`
- URL: `https://github.com/jeffery777/codex-dev-skills/pull/2`
- Merged at: `2026-06-05T01:25:47Z`
- Base SHA: `8d57e14dbb5f0e2b31a17f5c4ee6cde15bdfd955`
- Head SHA: `d8cee1840f0e0bd0e5fe064fb7b8504fa4217eca`
- Merge commit SHA: `3f4fbbaaafe75e889a579533564d08170a60fc16`

Retrospective finding:

- PR #2 has platform-side merge review evidence now, but the durable GitHub comment was created after merge.
- The merge review comment was created at `2026-06-05T01:26:49Z`, 62 seconds after `merged_at`.
- The comment itself states that the merge review was performed before merging and the comment was posted afterward to preserve the expected PR evidence trail. This note records the timing exception without treating the post-merge comment timestamp as pre-merge platform evidence.

Still-verifiable evidence:

- The GitHub PR title, branch, merge state, timestamps, base/head SHAs, and merge commit SHA.
- The post-merge GitHub PR comment titled `Merge Review Summary`.
- The comment records a `READY` result, reviewed base/head SHAs, changed files, validation evidence, and residual risk.

Classification:

- Gap type: post-merge backfill / timing exception.
- Status after this document: retrospectively recorded as a timing exception, not a total platform evidence absence.

Residual risk:

- The current PR page preserves the merge review summary, but the platform-side evidence was not present before merge.

## Future Gate Expectation

For future merges, local `.work/review/...` artifacts can support execution, but they should not be the only durable evidence once a PR is merged.

Before merge, the PR should contain durable platform-visible formal merge review evidence, such as a GitHub PR comment or submitted review, that records:

- base SHA
- head SHA
- reviewed scope
- blocker / non-blocker status
- verification evidence
- residual risk
- confirmation that the merge approval applies to the exact reviewed head SHA

## Boundary

This document is a historical audit note only. It does not authorize code changes, runtime behavior changes, PR comments, review submissions, merges, labels, status changes, or other platform writes.
