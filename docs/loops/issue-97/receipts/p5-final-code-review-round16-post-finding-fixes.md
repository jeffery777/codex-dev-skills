# P5 Final Deep Code And Contract Review — Round 16

Historical note: the later round-17 review found that using trusted current
time as the durable expiry reference could produce events that deterministic
replay rejected. `V2CA-MF-TRUSTED-TIME-001` supersedes that part of this
receipt: trusted time is now only a live future-event freshness bound, while
durable lease semantics use `occurred_at` in both live application and replay.

Gate result: **PASS** for the post-finding code delta.

This current-session `code-review-deep` / `code-review-gate` re-review combined
the previously passed round-15 complete-diff review with a focused inspection
of the later package-provenance, trusted-time, and scan-recovery changes. The
configured review workers had already ended in runtime refusals, so the
documented bounded parent/current-session recovery path was used. No wording
evasion or expansion of authority occurred.

Finding disposition:

- `MF-P5-R16-001` — fixed and re-reviewed. Complete GitNexus package hashing
  now uses descriptor-bound, no-follow, nonblocking reads. Direct relative file
  symlinks are resolved lexically from the already-open package root; parent,
  target, absolute, escaping, directory, special-file, and regular-file-to-link
  race cases fail closed.
- MUST-FIX: 0 open.
- SHOULD-FIX: 0 open.
- NIT: 0 open.

Observed verification:

- full repository unit suite: 631/631 passed in 87.105 seconds;
- GitNexus adapter suite: 73/73 passed in 48.902 seconds;
- loop core: 61/61 passed;
- loopctl plus scan-recovery contract: 79/79 passed;
- Loop Engineering eval: 22/22 cases and state contract passed;
- repository validation: passed, including loop, installer/profile/routing,
  runtime compatibility, public hygiene, and V2b checks;
- mandatory V2b oracle: 31/31 passed with all rates `1.0` and false authority
  or completion count `0`;
- `git diff --check`: passed.

The final macOS qualification used GitNexus `1.6.9`, package-tree digest
`feecb1748b8fbd24dc54921269e815a65725d808269152283ffc459604f6b603`,
runtime fingerprint
`eed36a35ea944bf494f788212ce01a1b401d8e5a6a7a095cbbd67bebb63faa2d`,
and an isolated refresh receipt
`2c26daa0fa03e0d95e7f8cff8fcd4a092b3618c3f453588b8d31c4ab7a78626b`.
Tracked, protected, complete-status, worktree, and Git-control digests were
unchanged before and after.

Residuals remain unchanged: hostile same-UID mutation is outside the declared
cooperative local control-plane boundary, and Linux remains portability-fixture
evidence rather than live qualification. This gate does not substitute for the
required final native diff scan or authorize publication.
