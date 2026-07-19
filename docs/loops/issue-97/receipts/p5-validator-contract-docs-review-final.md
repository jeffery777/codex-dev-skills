# P5 Validator Contract Formal Documentation Re-review

Gate Result: **PASS** for the bounded validator-contract documentation diff.

## Finding disposition

- MUST-FIX: none.
- SHOULD-FIX: none.
- NIT: none.
- The earlier detached-HEAD test gap was fixed and re-reviewed. Both
  `loopctl audit` and the repository validator now use a real detached Git HEAD
  and verify branch-mismatch fail-closed behavior.

## Contract alignment

- Active ledgers require an exact branch and HEAD.
- Only a `complete` lifecycle with final `objective_completed` may accept a
  same-branch ancestor source anchor.
- Unknown, missing, malformed, diverged, wrong-branch, and detached-HEAD states
  fail closed.
- Terminal objectives cannot transition, reopen, or append a new event.
- Historical P4/P5 receipts are explicitly scoped to the first `67be3d9`
  snapshot and cannot prove the current bounded diff complete.

Targeted detached-head tests and `git diff --check` passed. This documentation
gate has no authority over the pending native security scan, final readiness,
publication readback, or terminal ledger closure.
