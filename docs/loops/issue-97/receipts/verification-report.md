# Issue 97 Verification Report

Status: passed after the post-security fix and final native security gate.

## Test And Contract Matrix

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

## Final Security And Review Gates

- Formal post-fix deep code re-review: PASS; open MF/SF/NIT: none.
- Final Codex Security diff scan:
  `a75728b15f5d15ba7bf1a7e6e3a2dd934915592e_20260717T015027Z`.
- Frozen snapshot:
  `codex-security-snapshot/v1:sha256:5c3edf9add7ffe2c326c789d1672ec8157578cd3948092c9a22d0960fda7d31d`.
- Native status `completed`; coverage `complete`; 4/4 source-like worklist
  rows closed; 3/3 surfaces `no_issue_found`; findings `0`; finalizer
  idempotency PASS.
- A dedicated validation worker was refused by the runtime classifier. The
  parent used the documented defensive recovery path without evasion or unsafe
  reproduction; scan-native finalization remains the completion authority.
- Linux was not live-tested and is represented only by portability fixtures
  and contract evidence.

## Final Live macOS Qualification

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
