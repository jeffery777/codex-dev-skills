# Issue #121 Merge Review Finding Resolution

Date: 2026-07-29

P4 formal-gate result: PASS

PR merge-gate result: PENDING renewed zero-findings review

Authority: review evidence only

## Finding

The initial PR #122 exact-head reviews found one blocker: the active ledger was
source-bound to implementation commit
`d498d3a314b47e7c6128f0ac4f4130b4e6f7765c`, while the PR head was its
authorized ledger-only descendant
`8d08d1823b986e047c43a321ae637decd88b6084`. Active ledgers require exact HEAD,
so production repository validation correctly failed closed.

## Resolution

The delegating user independently authorized the exact PR-head source rebound,
publication gate satisfaction, protected `P4-readiness` completion, and
terminal objective completion. Applying those events makes the ledger terminal
only after every planned task is done, no active claim remains, verification
and review evidence is bound, and the publication human gate is recorded as
satisfied for this delivery scope.

The terminal ledger intentionally remains source-bound to the reviewed PR
head. The existing terminal ancestor rule permits that authenticated source to
remain an ancestor after the ledger resolution is committed, avoiding an
impossible self-referential HEAD binding.

The historical authorization boundary in `review-disposition.md` is also
clarified as point-in-time evidence.

## Evidence Semantics

`P4-readiness` is the repository delivery formal gate. Its manifest scope
explicitly excludes commit, push, PR creation, merge, tag, and release
publication. Its protected completion records that the reviewed remediation
candidate, verification, review closure, and human authorization needed to
produce an exact-head PR are satisfied. It does not claim that the later
platform PR merge gate has passed.

The P4 completion event binds this finding-resolution receipt as its primary
passed review artifact. `merge-review-exact-head-initial.md` is retained as
historical counterevidence showing the original blocked state and the finding
that this receipt closes; it is not treated as a passed review result.

Likewise, terminal objective completion covers Issue #121's bounded
implementation and release-preparation delivery objective. It does not
authorize or prove PR merge, tag creation, or Release publication. The
post-commit exact-head Merge Review remains a separate gate, and its result
cannot be inferred from the protected completion events.

## P4 Formal-Gate Evidence

The P4 formal gate is PASS on terminal commit
`30db237abb5eb8576e10d4b7f244639206225d95`:

- `loopctl.py audit` reports 33 events, zero errors, and `status: valid`;
- `scripts/validate-loop-ledger.py` validates all three project ledgers;
- `scripts/validate-repo.sh` passes;
- the focused operational-evidence suite passes 44 tests;
- the operational-evidence eval passes 12/12 exact thresholds with zero false
  authority or completion;
- the full repository suite passes 796 tests;
- renewed deep code review reports 0 MUST-FIX, 0 SHOULD-FIX, and 0 NIT;
- renewed security/privacy review reports zero vulnerabilities and
  0 MUST-FIX, 0 SHOULD-FIX, and 0 NIT;
- the documentation artifact-disposition finding is closed by this receipt
  and the companion composite receipt explicitly recording their current P4
  PASS status while preserving the initial blocked history.

This evidence, not the protected authorization itself, supports the
machine-readable P4 `review: passed` state.

## Post-Completion Merge Gate

After the terminal-ledger commit:

- run `skills/loop-engineering/scripts/loopctl.py audit` with the Issue #121
  manifest and repository root;
- run `scripts/validate-loop-ledger.py`;
- run `scripts/validate-repo.sh`;
- run focused operational-evidence tests and eval;
- run `git diff --check`;
- repeat deep merge, documentation, and security/privacy review against the
  new exact PR head.

No PR comment or merge is permitted until those renewed reviews have zero
findings and GitHub still reports the exact head mergeable.

## Remaining Boundary

Merge authorization is conditional on the renewed no-findings result. Tag
`v0.10.0`, GitHub Release publication, deployment, and promotion remain
unauthorized post-merge actions.
