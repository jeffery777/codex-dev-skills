# Issue #159 Implementation Plan

## Objective

Deliver the smallest fail-closed v0.16.1 fix for the Linux qualification
timeout defect: an explicitly configured refresh must use one bounded
monotonic deadline across executable qualification, repository preflight,
controller execution, and postconditions. Standalone qualification keeps its
existing independent limits.

## Source Of Truth

- GitHub Issue #159
- `SECURITY.md`
- `docs/loops/issue-157/loop-spec.md`
- `docs/native-runtime-capabilities.md`
- `docs/external-memory-contract.md`
- `skills/loop-engineering/scripts/gitnexus_adapter.py`
- `skills/loop-engineering/scripts/gitnexus_hook.py`
- `tests/test_gitnexus_adapter.py`
- `tests/test_gitnexus_hook.py`

## Contract Decisions

1. The existing refresh timeout range, `1..3600` seconds, remains the only
   operator-configurable refresh budget. The fix does not increase it.
2. A refresh entrypoint validates that value before contacting GitNexus and
   derives one absolute monotonic deadline. Qualification and the controller
   receive the same deadline; neither may reset or extend it.
3. Direct `qualify` and non-refresh status calls keep the existing 10-second
   default and `1..300` standalone qualification validation.
4. Auto-on-demand hook qualification uses the configured refresh deadline;
   notify-only hook qualification retains standalone behavior.
5. Detected absolute-budget expiry remains fail closed with stable
   `probe-deadline-expired` behavior, no index adoption, and no added GitNexus
   authority. The bounded analyze process slice remains distinct: exhausting
   it before the absolute deadline reports `refresh-timeout` and also fails
   closed.

## Task Slices

1. Add bounded deadline construction/validation and optional caller-owned
   deadline plumbing to qualification without weakening standalone limits.
2. Make `RefreshController.refresh()` cap work to both its configured timeout
   and any earlier caller deadline, then thread the same deadline through the
   operator refresh and auto-on-demand hook paths.
3. Add deterministic clock-controlled tests for slow-but-valid qualification,
   expiry, invalid/boundary timeout arguments, standalone behavior, shared
   operator/hook deadlines, and controller exhaustion before runner execution.
4. Align source and generated plugin package, v0.16.1 manifests, installer,
   catalog, README, roadmap, release readiness, runtime/usage contracts,
   version tests, and release notes.
5. Run focused suites, relevant GitNexus evals, repository validation, formal
   review/security/readiness gates, and close every in-scope finding.
6. Publish only from the reviewed exact head, prove release identities, then
   run one predeclared Rocky Linux released-artifact qualification attempt in a
   new sibling evidence root while preserving prior evidence and host bounds.

## Expected Affected Files

- Adapter/hook source and generated plugin copies
- Adapter/hook tests and version-contract tests
- Issue #159 plan and v0.16.1 release notes
- README, roadmap, release readiness, native runtime, and external-memory docs
- `catalog.yaml`, `install.sh`, and plugin manifest/package

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

Run version-contract suites selected by the changed assertions and narrower
deadline tests before the full focused suites.

## Review Plan

- Formal mixed-code review through `code-review-gate`.
- Formal documentation review through `docs-review-gate`.
- `security-diff-scan` over the exact base-to-head diff.
- `merge-review-deep` for release-sensitive cross-module alignment.
- `merge-readiness-gate` bound to the final exact local HEAD and clean worktree.

## Rollback And Recovery

The change only reuses an already configured bounded refresh budget. Rollback
restores the v0.16.0 entrypoint timing behavior; it does not delete indexes,
clear circuit breakers, rewrite repositories, or alter old Rocky evidence.

## Human Gates

The user authorized Issue creation, branch delivery, commit, push, PR, clean
exact-head merge, annotated tag, GitHub Release, and the bounded Rocky Linux
requalification for this objective. Stop on any new repository gate, identity
or permission conflict, destructive requirement, scope expansion, insufficient
high-risk verification, or release-head drift.
