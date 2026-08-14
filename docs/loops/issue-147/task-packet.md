# Issue #147 Task Packet — Memory M1 SQLite/FTS5

## Objective

Deliver the bounded Issue #147 reference adapter and safety/conformance
qualification on branch `codex/147-memory-m1-sqlite-fts5`, based on
`89a284c9b44fe762afcfcf0d79d79ee701eade69`, then pass the conditionally
authorized commit/push gate and stop before PR.

## Required Outputs

- [x] self-contained GitHub Issue #147 and issue branch;
- [x] spec, ADR, threat model, implementation plan, acceptance matrix;
- [x] additive adapter/CLI/fixed schema/public reference;
- [x] synthetic fixtures, tests, deterministic eval;
- [x] package/repository/public-doc alignment;
- [x] focused/full verification and static impact evidence;
- [x] deep quality/security/privacy review and MUST-FIX closure;
- [x] final code/security review with no findings, commit/push evidence, and PR
  human gate.

## Verification Evidence

- repository Python resolver: CPython 3.12.9 with PyYAML 6.0.3;
- focused M1 unit/CLI/eval/docs tests: 18 passed;
- deterministic M1 suite: 18 cases passed with zero safety/conformance
  failures and zero efficacy claims;
- full repository unit discovery: 903 passed;
- `scripts/validate-repo.sh`: passed, including the 18-test M1 validation
  stage;
- Git diff whitespace check: passed;
- GitNexus issue-branch index: advisory only while dirty; exact-content limits
  and the high-priority GN-FU-01 are recorded in `follow-ups.md`.

## Review Dispositions

- `M1-SEC-001` qualification-receipt laundering through digest-only evidence:
  **Fixed** by requiring and revalidating complete M0 execution-evidence
  bundles.
- `M1-CR-001` malformed qualification evidence could escape the CLI's generic
  rejection boundary: **Fixed** with an exact expected-error boundary and CLI
  regression test.
- `M1-CR-002` a successful transaction could cross the database-size envelope
  before the next open-time check: **Fixed** by checking transactional page
  count after state-plus-receipt insertion and rolling back as `disk-full`.
- `M1-DOC-001` out-of-scope residual risks lacked durable follow-up fields:
  **Fixed** in `follow-ups.md`.
- `M1-DOC-002` placement docs overstated descriptor-based protection:
  **Fixed** to describe path/metadata checks and the excluded hostile same-UID
  race precisely.
- `GN-FU-01` GitNexus main/branch/worktree/dirty-index lifecycle:
  **Deferred**, high priority. Owner, target, reason, remaining risk,
  verification plan, and promotion trigger are complete in `follow-ups.md`.

The final deep code/docs rerun reports no unresolved finding. Codex Security
diff scan `5caf2125-a619-4e3f-bf46-36dded0a13c5` sealed the exact candidate
snapshot with complete coverage and zero findings. Implementation commit
`2c4c609b12632eb3bbfe9a80b5c13b8a99134d8d` was pushed to the Issue branch.
PR creation, acceptance, release selection, merge, tag, Release, install,
activation, promotion, and deploy remain human gates.

## Definition Of Done

Use the exact Definition of Done and acceptance matrix in `loop-spec.md` and
GitHub Issue #147. Upstream production contracts stay byte-unchanged. Target
release stays **TBD / human decision**.

## Stop Conditions

Stop for source/public-contract/authority/privacy/data-model ambiguity,
physical purge, efficacy, shared/multi-tenant database, encryption, cross-host
behavior, destructive action, scope expansion, failed high-risk verification,
or any external write beyond the authorized Issue, branch, and conditionally
authorized commit/push. Commit/push may proceed only after final code review
and security diff scan both report no findings; PR and later actions remain
human gates.
