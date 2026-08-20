# Issue #157 Implementation Plan

## Objective

Implement the Issue #157 loop spec as the smallest additive, fail-closed
extension of the qualified V2c-A adapter and V2c-B hook, align v0.16.0 public
artifacts, and prepare exact-head PR-readiness evidence.

## Source Of Truth

- `docs/loops/issue-157/loop-spec.md`
- GitHub Issue #157
- `docs/external-memory-contract.md`
- `docs/native-runtime-capabilities.md`
- `skills/loop-engineering/scripts/gitnexus_adapter.py`
- `skills/loop-engineering/scripts/gitnexus_hook.py`
- `tests/test_gitnexus_adapter.py`
- `tests/test_gitnexus_hook.py`

## Task Slices

1. Add a canonical complete-content digest and explicit tracked/untracked dirty
   classification to the repository snapshot without weakening existing race,
   path, size, symlink, or process bounds.
2. Add `gitnexus-index-identity/v1` builders and strict validators for primary,
   branch, linked-worktree, detached, and dirty contexts, plus the library-only
   `gitnexus-pr-review-identity/v1` base/head builder. Bind
   repository/worktree/ref/HEAD/content/tool/config/freshness fields and derive
   collision-resistant checkout-specific aliases.
3. Persist the exact identity as a bounded derived-index sidecar only after a
   qualified refresh. Make normal metadata assessment and hook freshness
   require and revalidate it; missing/legacy evidence is advisory/stale.
4. Preserve controller and hook mutation boundaries: dirty refresh rejected,
   detached/linked automatic refresh rejected, remote-only merge irrelevant,
   primary-local HEAD advance eligible only after all clean checks.
5. Add clean/dirty/untracked/ignored/linked/detached/PR fixtures, malformed and
   replay negative cases, controller/hook regressions, and a deterministic
   production-backed lifecycle eval.
6. Align README, roadmap, release readiness, native runtime and external-memory
   contracts, v0.16.0 release notes, catalog, installer, plugin manifest,
   generated plugin package, and version-contract tests.
7. Run focused and repository verification, inspect the diff, close formal
   review and security findings, and run deep merge plus exact-head readiness
   gates.

## Ownership And Execution

One current-session owner edits the production code, directly coupled tests,
eval, and docs in sequence. No subagent or cross-worktree mutation is used, so
there is no overlapping ownership or claim ambiguity.

## Expected Affected Files

- Adapter/hook source and generated plugin copies
- GitNexus adapter/hook tests and lifecycle eval fixtures/tests
- Issue #157 loop documents
- README, roadmap, release/readiness, runtime, and external-memory docs
- `catalog.yaml`, `install.sh`, plugin manifest, version-contract tests, and
  `docs/release-notes-v0.16.0.md`

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_eval_gitnexus_index_lifecycle
./scripts/project-python scripts/eval-gitnexus-index-lifecycle.py
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Add or run narrower tests whenever a finding identifies a specific contract
edge. Run the broader memory-contract evals if adapter handshake or shared
memory semantics change.

## Review Plan

- Formal high-risk mixed code review through `code-review-gate`.
- Formal documentation review through `docs-review-gate`.
- `security-diff-scan` over `main...HEAD` plus the uncommitted patch.
- `merge-review-deep` for release-sensitive cross-module alignment.
- `merge-readiness-gate` bound to the final exact local HEAD and worktree
  digest; stop before external writes.

## Rollback Or Recovery

The feature is additive and default-disabled. Rollback disables/ignores the
optional hook and identity sidecar; no index deletion or repository rewrite is
part of rollback. A missing or old sidecar falls back to advisory/stale rather
than being migrated or trusted.

## Resolved Decisions

- The identity contract is a separate Codex-owned sidecar because GitNexus
  schema 5 rejects unknown fields and remains untrusted.
- Exactness requires clean content plus a sidecar match; dirty identities are
  inspection-only and never automatically refreshed.
- No Spark routing-policy change belongs to this Issue. Any future proposal
  needs representative eval evidence and a separate decision.
