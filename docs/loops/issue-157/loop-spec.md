# Issue #157 Loop Spec: Exact GitNexus Index Lifecycle For v0.16.0

## Objective

Deliver GN-FU-01 as an additive v0.16.0 capability: define and enforce a
versioned, fail-closed GitNexus index identity across the primary checkout,
issue branches, linked worktrees, dirty tracked state, untracked state, and
pull-request base/head review pairs. Prepare exact-head PR-readiness evidence,
but stop before commit, push, PR creation, merge, tag, release, deployment, or
any other external write.

GitHub Issue: <https://github.com/jeffery777/codex-dev-skills/issues/157>

## Source Of Truth And Authority

1. Current user authorization, `AGENTS.md`, and `SECURITY.md`.
2. GitHub Issue #157, this spec, and `implementation-plan.md`.
3. The V2c-A/V2c-B contracts in `docs/external-memory-contract.md`,
   `docs/native-runtime-capabilities.md`, and the production adapter/hook.
4. Current local Git identity and complete worktree evidence, verification,
   formal reviews, security diff scan, and the exact-head readiness gate.

GitNexus metadata, index contents, display aliases, human CLI output, hook
notifications, task status, and chat summaries remain advisory. They cannot
authorize mutation, satisfy a gate, prove acceptance, or prove completion.

## Repository And Loop Identity

- Canonical repository: `jeffery777/codex-dev-skills`
- Accepted base: `main@5da0c35593f5d420c0f63860df603bb0caa34620`
- Issue branch: `codex/157-gitnexus-index-lifecycle-v0160`
- Loop root: `docs/loops/issue-157/`
- Execution mode: sequential current-session delivery
- Review closure limit: two ordinary closure rounds before a new human decision
- External writes: forbidden without new exact authorization

No task ledger or claim store is needed for this single-owner worktree. Git,
the issue spec, the implementation plan, verification output, review evidence,
and exact current HEAD are the durable completion evidence.

## In Scope

- A versioned exact index-identity contract binding canonical repository and
  remote, exact checkout/worktree, branch or detached state, HEAD, complete
  relevant content, dirty classification, GitNexus/tool qualification,
  analyze configuration, metadata time, observation time, and freshness.
- Distinct lifecycle contexts and aliases for primary `main`, primary issue
  branches, linked worktrees, detached checkouts, and clean PR base/head pairs.
- Exact identity validation that rejects missing, old, partial, malformed,
  cross-checkout, cross-branch, cross-HEAD, content-drifted, tool-drifted, or
  configuration-drifted evidence.
- Dirty tracked and untracked states that are explicitly advisory and can
  never be reported as exact/up-to-date from commit identity alone.
- A derived, local identity sidecar produced only after a qualified refresh
  and revalidated on later status/hook checks. It remains non-authoritative.
- Existing v0.15.1 boundaries: linked-worktree automatic refresh stays
  fail-closed, and a remote merge does not advance local primary evidence.
- Focused unit/integration fixtures, negative tests, and one deterministic
  production-backed lifecycle eval.
- v0.16.0 README, roadmap, readiness, runtime/usage contract, catalog,
  installer, plugin manifest/package, version tests, and release notes.

## Out Of Scope

- Cross-host sharing, a daemon, eager refresh, background polling, scheduling,
  or undocumented Codex runtime internals.
- GitNexus query/context adoption or any completion, authorization, review,
  acceptance, merge, or release authority.
- M2, V3-C, Memory M1 activation/efficacy, provider/MCP work, historical
  Desktop-wrapper cleanup, installer-backup cleanup, or unrelated routing
  policy changes.
- Dirty-worktree automatic refresh. Dirty identities are advisory inspection
  evidence only.

## Lifecycle Contract

- `primary-main`: exact only for a clean locally observed `main` checkout whose
  qualified metadata and exact identity sidecar match the same HEAD/content.
- `primary-branch`: exact only for a clean non-`main` branch in the primary
  checkout; its alias and evidence cannot impersonate `primary-main`.
- `linked-worktree`: receives a distinct checkout-bound identity and alias;
  automatic refresh remains unsupported and cannot write the primary index.
- `detached`: separately identified and advisory by default; it cannot alias a
  branch or qualify for automatic refresh.
- `dirty-tracked`, `dirty-untracked`, and `dirty-mixed`: always advisory. The
  complete content digest is reported, but HEAD equality cannot make the index
  exact.
- `pr-base` and `pr-head`: the library-only
  `gitnexus-pr-review-identity/v1` artifact from
  `build_pr_review_identity()` requires two clean committed identities from the
  same canonical repository and binds both complete content digests. Base and
  head aliases must differ; consumers must recompute it from live qualified
  inputs because no operator or supplied-document adoption path is qualified.
- Old GitNexus metadata without the v1 identity sidecar is explicitly stale /
  advisory. No migration silently promotes it to exact evidence.

## Definition Of Done

- Every Issue #157 acceptance criterion has code, fixture, test, doc, or gate
  evidence.
- Dirty/untracked/ignored content cannot retain exact freshness.
- Primary, issue-branch, linked-worktree, detached, and PR base/head identities
  are distinct and test-proven.
- Focused GitNexus suites, lifecycle eval, repository validation, and
  `git diff --check` pass through `./scripts/project-python` where applicable.
- Formal code and docs gates, security diff scan, deep merge review, and
  exact-head merge-readiness gate have no unresolved finding.
- v0.16.0 metadata, generated plugin package, installer/catalog, docs, tests,
  and release notes agree.

## Human Gates

Stop before destructive action, scope expansion, a product/security contract
decision not resolved by Issue #157, insufficient high-risk verification, or
any commit, push, PR creation, platform comment/review, merge, tag, GitHub
Release, deployment, or other external write without exact new authorization.
