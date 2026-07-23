# Issue #109 Repository Guardrails

## Objective

Deliver two bounded repository guardrails:

1. make GitNexus analysis index-only by default so it cannot regenerate
   repository instruction or provider-skill files; and
2. require every ready-for-review pull request to close an open Issue in this
   repository.

These controls protect local repository hygiene and GitHub traceability. They
do not add completion, review, merge, release, or protected authorization.

## Source Of Truth

- Repository instructions: `AGENTS.md`
- GitHub objective: Issue #109
- External-memory boundary: `docs/external-memory-contract.md`
- V2c-A contract: `docs/loops/issue-97/loop-spec.md`
- Pull-request linkage policy:
  `policies/pull-request-issue-linkage-policy.md`
- Implementation plan: `docs/loops/issue-109/implementation-plan.md`
- Task manifest: `docs/loops/issue-109/task-manifest.yaml`

Repository files, Git state, verification, formal review, and accepted
platform state remain authoritative. GitNexus indexes, CI status, and
PR-to-Issue links remain bounded evidence only.

## Scope

### In Scope

- Remove only the uncommitted GitNexus-generated block from `AGENTS.md`.
- Track an exact `.gitnexusrc` default with `analyze.indexOnly: true`.
- Fail closed when that repository default is missing, broadened, duplicated,
  malformed, symlinked, oversized, or disabled.
- Add a pull-request template with a standalone closing-Issue placeholder.
- Add a least-privilege metadata-only CI check for ready pull requests.
- Require every referenced number to identify an open same-repository Issue,
  not a pull request.
- Add validators, deterministic tests, documentation, and release alignment.

### Out Of Scope

- Changing GitHub's shared Issue/pull-request numbering sequence.
- Enabling hooks, automatic GitNexus refresh, or V3-A behavior.
- Branch-protection or repository-settings mutation.
- Checking out or executing untrusted pull-request head content.
- Automatic approval, review submission, merge, release, promotion, or Issue
  mutation.
- Scheduler, daemon, controller service, database, graph runtime, or private
  operational evidence.

## Definition Of Done

- Bare repository-local GitNexus analysis honors the tracked index-only
  default and does not change `AGENTS.md` or create provider instruction/skill
  files.
- Repository validation rejects any broader `.gitnexusrc`.
- The PR template presents one exact standalone `Closes #ISSUE_NUMBER` line.
- The CI workflow skips drafts and validates ready pull requests against open
  same-repository Issues using only trusted base code and read-only
  permissions.
- Missing, closed, nonexistent, cross-repository, and pull-request references
  fail closed.
- Focused tests, repository validation, diff hygiene, formal implementation
  review, documentation review, and merge review pass without unresolved
  blockers.

## Bootstrap Limitation

GitHub resolves `pull_request_target` workflow code from the base branch.
Therefore the pull request that first introduces this workflow cannot be
validated by that new check. Its linkage must be verified manually, and the
limitation must be recorded in its review evidence. Later pull requests are
covered after this change reaches the default branch.

## Human Gates

Stop before any unexpected expansion of repository instructions, workflow
permissions, external write, or authority semantics. Commit, push, PR, review
comment, and merge follow the explicit publication authority for Issue #109.
