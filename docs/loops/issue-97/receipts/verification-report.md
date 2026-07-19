# Issue 97 Verification Report

Status: **published adapter baseline and prior gates passed; bounded final
closure fix verified, formally reviewed, and scan-native finalized**. The
closure fix still requires publication and remote readback.
Historical snapshots and scans remain chronology only and do not prove the
current working tree complete.

## Current P5 Post-Fix Verification

- Final closure rerun: 651/651 full repository unit tests passed in 105.371
  seconds; repository validation passed with 150 loop tests, 35 profile and
  installer tests, 45 routing tests, and 46 V2b tests. The 36-event active
  ledger audit and `git diff --check` also passed. See
  `p5-final-closure-fix-verification.md`.
- Pre-publication full repository unit suite: 649/649 passed in 86.239 seconds after the final
  commit-boundary lease fix.
- GitNexus adapter suite: 79/79 passed in 63.629 seconds.
- Loop core, CLI, and eval unit subset: 158/158 passed.
- Loop Engineering eval: 23/23 passed; false completion, unauthorized action,
  and wrong-route counts were zero.
- Repository validation passed: loop 148, agent profiles/installer 35, routing
  45, and external-memory/V2b 46.
- Mandatory memory oracle: 31/31 passed; all correctness, determinism, evidence,
  and fallback rates were `1.0`; false authority/completion count was `0`.
- `git diff --check`: passed.
- Final closure native diff scan `5848409e-ca54-4b85-98a8-82b66aff6702`:
  complete, 1/1 source worklist row, 0 reportable findings, no deferred rows or
  open questions. See `p5-final-closure-security-diff-scan.md`.
- Worker integration receipts for all three post-scan fix packets were accepted with
  `completion_proven: false` after the main-agent reruns above.

## Historical P4 Test And Contract Matrix

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'`:
  570/570 passed in 44.028s.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter`:
  40/40 passed in 22.001s, including real-FIFO nonblocking and
  missing-`O_NONBLOCK` fail-closed regressions.
- Repository V2b contract/conformance gate: 46/46 passed.
- `python3 scripts/eval-memory-contract.py`: 31/31 cases passed; decision,
  deterministic, evidence, and fallback rates were `1.0`; false authority or
  completion count was `0`.
- `python3 scripts/eval-loop-engineering.py`: passed; false completion and
  unauthorized action counts were `0`.
- `python3 scripts/eval-agent-routing.py`: 24/24 passed; authority invariance,
  determinism, evidence completeness, and route correctness rates were `1.0`.
- `python3 scripts/validate-agent-profiles.py`: valid, no conflicts.
- `./scripts/validate-repo.sh`: passed, including install/catalog, skill
  metadata, loop ledger, runtime compatibility, public hygiene, V2a, and V2b
  validation.
- `git diff --check`: passed.
- Python compile and shell syntax checks included by the repository validation:
  passed.

## Current Security And Review Gates

- Final native scan `559c572f-d3fe-44a0-a6f3-c13be1e78521` completed against
  immutable branch-diff head
  `e91b3cf69b711c9bb5deeb4f87ec43af4a42456e`. All 13 worklist rows and all 7
  candidate ledgers closed; the mechanical final policy rejected every
  candidate and the canonical report contains 0 reportable findings, 0
  deferred rows, and 0 open questions. Native finalization succeeded. See
  `p5-final-security-diff-scan.md`.
- Native scan `874c187c-5e2b-4180-aa93-3dea61808255` completed against immutable
  snapshot `1a1a054ddeaa9739532c2fc8f7f5529b45e4a7b3`. It reported one low-priority
  finding and validated two additional engineering controls. All three are now
  fixed and covered by regressions; this scan is historical because it predates
  the fixes.
- Round-17 deep review independently found the same contract boundary plus two
  related blockers. Round 18 closed the home-lock and fallback findings but
  found a backdated live-lease blocker; round 19 then found the corresponding
  pre-replacement recheck gap. Both are now fixed and covered by the 651-test
  full rerun above. Round-20 code review and round-8 docs review closed with no
  open MF/SF/NIT, and the final native rescan passed.
- Linux was not live-tested and is represented only by portability fixtures
  and contract evidence.

## Current Live macOS Qualification

The complete current controller requalified GitNexus `1.6.9` after detecting
Node runtime byte drift from the historical evidence. Qualification fingerprint
`86c6ec65b0b207a591759b35650acd914a812139327b9efe5933983b04d6029e`
bound the accepted entry, current Node runtime, complete package tree, exact
version, and observed capability flags.

A fresh synthetic local refresh invoked only the structured `analyze
--index-only` path. It returned `refreshed / qualified-index-adoptable` with
receipt `3a15f4f71f6e70e867f8844eb82dddf815a52c21e87d225552604cdb9009ad78`.
Tracked, staged, protected, complete worktree, and Git-control evidence was
unchanged; only expected ignored derived/local runtime state changed. See
`gitnexus-1.6.9-qualification.md` for the redacted digest matrix.

## Historical Live macOS Qualification

The evidence below predates the post-scan isolated-home lifecycle lock and is
retained only as historical proof that the qualified argv and mutation checks
worked. The current driver must be requalified before final readiness.

The production controller was run from the final code against a fresh isolated
clone at `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`, with a new empty local home,
isolated registry/lock state, offline extension policy, and the required local
exclude precondition. It invoked only the qualified argv equivalent of
`gitnexus analyze --index-only --name <isolated-alias> <canonical-root>`.

- GitNexus: `1.6.9`; runtime fingerprint:
  `8106875b9184184ca7a7a8c788d6799f3c1c55ac72821f5a3a54893506da176d`.
- Result: `refreshed / qualified-index-adoptable`.
- Schema/indexed revision: `5` /
  `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`.
- Tracked file hashes: 244.
- Tracked-state before/after:
  `f71ff4c3c53ba19931bb8f314824bd5cc010c5088a27fb2e037c394fd0453183`.
- Complete-status before/after:
  `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Protected-state before/after:
  `3e4dc14220f747b41e90bbf6fd898953ed6e7418a859ee29f40074d027d28b2c`.
- Git-control before/after:
  `30e24a5f5ed5353f147f596b7938f3e3bc7d14ba744341678df7cca538cbaa59`.
- Refresh receipt:
  `489e21fe9da9e7b3ccb6fa220b2b51b6696ce24aa90807a6eaae5155894a07db`.
- Automatic refresh, mutation authority, external-write authority, and
  completion proof remained false.

Linux was not live-tested. POSIX process/path/FD/lock/deadline behavior is
covered by portability fixtures and is not represented as live Linux evidence.
