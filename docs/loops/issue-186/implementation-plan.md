# Issue #186 Repository Test Sharding Plan

## Objective

Split the complete Python unittest inventory into stable functional shards while
preserving exactly one platform-facing required check named
`Validate repository`. Local validation remains offline, and the exact-head
readiness collector continues to consume only that aggregate context.

## Source Of Truth

- GitHub Issue #186 defines scope and Definition of Done.
- `tests/test-shards.yaml` owns shard identifiers and explicit module
  membership.
- `scripts/test-shards.py` validates the manifest, emits the hosted matrix, and
  runs one shard through the repository-selected Python interpreter.
- `.github/workflows/repository-validation.yml` owns hosted orchestration and
  the stable aggregate check.
- `.github/exact-head-merge-readiness-policy.json` continues to pin the one
  upstream workflow and aggregate context; individual shard jobs are not
  policy inputs.

## Delivery Slices

1. Add a strict, offline manifest validator and deterministic single-shard
   runner.
2. Partition every `tests/test_*.py` module exactly once by functional
   ownership and add validator tests for duplicate, missing, extra, malformed,
   empty, and symlinked entries.
3. Replace the monolithic hosted discovery job with a validated matrix, a
   separate repository-structure job, and one `always()` aggregate job that
   succeeds only when planning, structure, and every matrix child succeed.
4. Document focused, impacted-shard, local all-shard, and hosted aggregate
   verification tiers.
5. Record the Issue baseline and exact hosted post-change timing evidence
   without turning one observation into a performance guarantee.

## Definition Of Done

- The manifest union equals the discovered repository test-module inventory;
  duplicates and unassigned or nonexistent modules fail closed.
- Every shard runs independently with
  `./scripts/project-python scripts/test-shards.py run <shard>`.
- Hosted CI runs every manifest shard with useful per-shard job names and
  `fail-fast: false`.
- Exactly one job is named `Validate repository`; its success requires
  successful manifest planning, repository-wide checks, and the complete
  matrix result. Failure, cancellation, skipping, timeout, or a missing matrix
  prevents aggregate success.
- Shard identifiers do not appear in ruleset or exact-head required-context
  policy.
- Focused tests, manifest tests, every shard, package parity, release-state,
  repository validation, and `git diff --check` pass.
- Hosted before/after evidence records individual shard durations and critical
  path with run identity and exact commit.

## Risks And Human Gates

- The repository-validation workflow blob is pinned by exact-head policy.
  Changing the workflow and its pin cannot pass the active gate while the PR
  base still contains the old blob. Before merge, a separately authorized
  ruleset disable/readback, reviewed merge, canary, and re-enable/readback
  sequence is required.
- Matrix job names are diagnostic only. Renaming or rebalancing them must not
  change the required context.
- Test counts do not predict runtime. Functional ownership is primary; hosted
  timing may justify a later explicit rebalance without changing the aggregate
  contract.
- Commit, push, PR creation, ruleset mutation, merge, release, and deployment
  remain separate gates.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_test_shards tests.test_exact_head_merge_readiness_workflow
./scripts/project-python scripts/test-shards.py validate
./scripts/project-python scripts/test-shards.py list --format json
./scripts/project-python scripts/test-shards.py run <affected-shard>
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```
