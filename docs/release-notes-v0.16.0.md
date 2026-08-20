# Release Notes: v0.16.0

Status: release candidate; commit, push, pull request creation, merge, tag,
GitHub Release, and deployment are not created or authorized by this document.

v0.16.0 is an additive GitNexus evidence-identity release over v0.15.1. It
implements GN-FU-01 from Issue #157 without changing GitNexus, memory, review,
gate, completion, or release authority.

## Exact Index Identity

- Adds `gitnexus-index-identity/v1`, a Codex-owned sidecar beside strict
  GitNexus schema-5 metadata.
- Binds canonical repository/remote, exact checkout and worktree, branch or
  detached state, HEAD, tracked/status/worktree state, complete relevant
  content including untracked and ignored paths, lifecycle alias, GitNexus
  qualification, analyze configuration, metadata digest, indexed time, and
  observation time.
- Requires a clean exact sidecar match before status or hooks report
  `fresh/exact-clean-content`. Old or missing sidecars are stale/advisory.
- Classifies dirty tracked, dirty untracked, and mixed state as advisory; HEAD
  equality cannot promote any of them to exact.

## Lifecycle Isolation

- Gives primary `main`, primary issue branches, linked worktrees, detached
  checkouts, and PR base/head pairs distinct content-bound identities and
  aliases.
- Keeps linked-worktree automatic refresh fail-closed. A linked checkout cannot
  update or impersonate the primary index.
- Preserves the local post-merge boundary: a remote merge alone does not
  advance local evidence. Updated primary `main` must advance locally before a
  clean hook event may refresh it.
- Adds the library-only `gitnexus-pr-review-identity/v1` contract through
  `build_pr_review_identity()`. It binds both clean committed contents, roles,
  branches, worktrees, aliases, and identity digests while explicitly proving
  no review, gate, acceptance, or completion. It is not an operator command;
  consumers must recompute from live qualified inputs rather than adopt a
  supplied document.

## Safety And Compatibility

The sidecar is written atomically below the already ignored `.gitnexus/`
derived-index root only after qualified refresh postconditions. Missing,
malformed, tampered, content-drifted, wrong-worktree, wrong-HEAD,
tool-drifted, or configuration-drifted evidence fails closed. Query adoption,
cross-host sharing, daemons, schedulers, eager/background polling, and dirty
automatic refresh remain unsupported. Rollback disables/ignores the optional
hook and sidecar; it does not delete an index or rewrite repository state.

## Verification And Release Gate

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_eval_gitnexus_index_lifecycle
./scripts/project-python scripts/eval-gitnexus-index-lifecycle.py
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Formal code and documentation review, Security Diff Scan, deep merge review,
and exact-head merge-readiness evidence must be current and finding-free. The
annotated `v0.16.0` tag, non-draft/non-prerelease GitHub Release, and deployment
remain separate human approval gates.

## Traceability

- Issue #157: <https://github.com/jeffery777/codex-dev-skills/issues/157>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.15.1>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.15.1...v0.16.0>
