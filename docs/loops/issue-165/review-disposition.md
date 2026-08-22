# Issue #165 Review Disposition

## Independent Review Baseline

- Reviewer: `independent_deep_review` (read-only)
- Baseline HEAD: `944a65a71b0d15b757627a91f1fb97279e3dc8ac`
- Initial verdict: not ready; six MUST-FIX, two SHOULD-FIX, one nit

## MUST-FIX Disposition

1. Missing comparison data now selects `reground-current-context`; malformed
   or unknown measurements cannot select fresh rollover.
2. Lineage now requires matching seen-rollover evidence, digest-changing
   progress evidence, and rejects one checkpoint under a new rollover ID. The
   CLI executor independently updates one atomic rollover-ID/checkpoint-digest
   indexed replay ledger below the Git control directory, so an unchanged
   request or a new ID for the same checkpoint cannot dispatch twice. The
   non-blocking descriptor-relative path atomically replaces the ledger and
   fsyncs files and parent directories.
3. The checkpoint digest now includes worktree state. CLI fresh continuation
   verifies clean state, exact branch/HEAD, and canonical `origin` host/path.
4. Desktop fresh rollover requires an exact checkpoint-branch `startingState`
   with `onMissing: error`; destination writer activation waits for a read-only
   exact branch/HEAD report.
5. Enum validation rejects non-string array/object/null input as a bounded
   `ContinuityContractError`, preserving the redacted stopped-receipt boundary.
6. Synthetic comparison data is provenance-labelled and explicitly unqualified
   as empirical release evidence. A paired run of the same objective remains a
   documented unsatisfied release gate; the candidate is not called releasable.

## SHOULD-FIX And Nit Disposition

- The completed CLI receipt binds the declared destination writer to the
  returned runtime session ID.
- Documentation now distinguishes assessment fallback selection from the
  executor's stopped/no-call receipt.
- Installer group text includes `fresh-continuation`.

## Verification After Fixes

- Final focused continuity/CLI/eval suite: 67 tests passed.
- Expanded context, CLI, runtime docs, plugin, release docs, and installer
  suite: 145 tests passed.
- Synthetic routing eval: 9/9 cases passed and reports
  `release_evidence_qualified: false`.
- Generated plugin package: 84 files verified.
- Final `./scripts/validate-repo.sh`: passed after all code and generated-package
  changes.
- Independent deep review ran five read-only rounds. The first four rounds
  identified and closed durability, identity, idempotency, Desktop-state,
  malformed-input, and evidence-qualification blockers. Round five reported
  PASS with no remaining MUST-FIX or scoped SHOULD-FIX; reviewed diff digest:
  `342e79892c128a1865fefade339ddf56970a77103e12e03d0491b31f5de5168b`.

The empirical paired-run release evidence remains intentionally unsatisfied,
so v0.17.0 is a justified minor candidate but not release-ready. Commit, push,
PR, merge, tag, and GitHub Release remain human gates.
