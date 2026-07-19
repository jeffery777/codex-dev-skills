# Issue 97 Review Disposition

This file is the durable finding ledger for V2c-A. Findings are not closed by
chat, Goal status, worker reports, or passing tests alone. Each disposition must
bind concrete diff, verification, review, or scan-native evidence.

The P4 code/docs/security PASS receipts below are historical evidence for the
initial adapter snapshot published as `67be3d9`. They do not by themselves
close the later bounded P5 validator-contract diff. Frozen P5 rounds through
round 16 have historical PASS evidence. The current post-fix diff closed through
round-20 code review, round-8 docs review, and the earlier final native Security
Diff Scan. The initial `21e4e0a` publication readback passed; the later bounded
closure fix still requires current review, final-diff validation, publication,
and a new remote readback.

| Finding | Severity | Status | Disposition / Evidence |
| --- | --- | --- | --- |
| MF-CODE-001 | MUST-FIX | fixed, re-reviewed | Dirty/untracked state now fails closed; round 2 confirmed closure. |
| MF-CODE-002 | MUST-FIX | fixed, re-reviewed | Derived-tree symlink/special/hardlink/device preflight and postflight reject unsafe trees; round 2 confirmed closure. |
| MF-CODE-003 | MUST-FIX | fixed, re-reviewed | Timeout, normal-exit, output-limit, and qualification descendants are cleaned and confirmed; round 3 passed. |
| MF-CODE-004 | MUST-FIX | fixed, re-reviewed | Non-default remote ports remain identity-significant; round 2 confirmed closure. |
| MF-CODE-005 | MUST-FIX | fixed, re-reviewed | Shared refresh deadline covers qualification/runtime hashing and derived pre/post traversal; round 4 passed. |
| MF-CODE-006 | MUST-FIX | fixed, re-reviewed | Qualification uses the bounded group-safe runner with shared probe deadline and live output cap; round 3 passed. |
| MF-CODE-007 | MUST-FIX | fixed, re-reviewed | Operator errors use stable redacted codes; ENOEXEC probe contains no local path. |
| SF-CODE-005 | SHOULD-FIX | fixed, re-reviewed | Unconfirmed selector-setup cleanup reports `process-group-cleanup-failed`; round 4 passed. |
| MF-CODE-008 | MUST-FIX | fixed, re-reviewed | Metadata open/read/parse/select/canonicalization/mirror convergence share the refresh deadline; round 5 passed. |
| MF-CODE-009 | MUST-FIX | fixed, re-reviewed | FD/no-follow `scandir` traversal checks each entry and rejects all scan/stat/open errors; round 5 passed. |
| MF-CODE-010 | MUST-FIX | fixed, re-reviewed | `cacheKeys` item types/lengths are checked before dedupe; nested JSON values return stable corrupt disposition without traceback; round 6 passed. |
| SF-CODE-001..004 | SHOULD-FIX | fixed, re-reviewed | Handshake requalification, effective-ignore verification, honest conformance semantics, and temporary-environment isolation confirmed in round 2. |
| MF-DOC-001 | MUST-FIX | fixed, re-reviewed | Spec/manifest digests and protected-event ledger are current; audit/validation pass; final docs gate passed. |
| MF-DOC-002 | MUST-FIX | fixed, re-reviewed | Tested `qualify`, `status`, `refresh`, and stateless `disable` operator entrypoint documented; final docs gate passed. |
| MF-DOC-003 | MUST-FIX | fixed, re-reviewed | Evidence-bundle and runtime fingerprint names, bindings, and uses are separated; final docs gate passed. |
| SF-DOC-001 | SHOULD-FIX | fixed, re-reviewed | `unsupported` is explicit in readiness checks. |
| SF-DOC-002 | SHOULD-FIX | fixed, re-reviewed | Backend-neutral oracle and capability-specific unsupported/fallback evidence are separated. |
| NIT-DOC-001 | NIT | fixed, re-reviewed | Platform label normalized to `macOS arm64 live qualification`. |
| MF-SEC-001 | MUST-FIX engineering control | fixed, re-reviewed, rescanned | Blocking FIFO metadata open from the first security scan was replaced with `O_NONBLOCK | O_NOFOLLOW` plus descriptor-bound type validation; real-FIFO and missing-constant regressions passed, formal post-fix deep review passed, and the final native scan found no reportable issue. |
| SF-POSTSEC-001 | SHOULD-FIX | fixed, re-reviewed | FIFO regression now asserts `os.read` is never called before non-regular-file rejection. |
| SF-POSTSEC-002 | SHOULD-FIX | fixed, re-reviewed | Missing-`O_NONBLOCK` portability regression now asserts fail-closed behavior occurs before `open`. |
| MF-P5-VC-01 | MUST-FIX | fixed, re-reviewed | Terminal ledgers are rejected before transition preview, including `--reopen`; the production-entrypoint regression passes. |
| MF-P5-VC-02 | MUST-FIX | fixed, re-reviewed | Premature P5 completion events were withdrawn. Final closure is rebuilt only after the current verification, docs/deep review, and Security Diff Scan. |
| SF-P5-VC-01 | SHOULD-FIX | fixed, re-reviewed | Exact/ancestor and active/non-final/missing/malformed/unknown/diverged/wrong-branch plus terminal transition/reopen paths now have helper and production-entrypoint coverage. |
| SF-P5-DOC-01 | SHOULD-FIX | fixed, final docs gate passed | Public detached-HEAD rejection now has real detached Git coverage in both production entrypoints; round-8 closed the objective-level docs gate. |
| MF-P5-FCR4-001..004 | MUST-FIX | fixed, round 10 re-reviewed | Complete ignored/worktree and `.git` administrative snapshots, refresh-child isolation, replacement-neutral Git, and staged inclusion of `git_source.py` are confirmed. |
| MF-P5-CV-001..003 | MUST-FIX | fixed, round 10 re-reviewed | FD/lstat marker binding, forged mutable RepositoryState rejection, and coherent repository observation are confirmed. |
| MF-P5-CV-R5-001 / MF-P5-CV-R6-001 | MUST-FIX | fixed, round 10 re-reviewed | Snapshot and final-qualification branch races now fail before the runner; regressions record zero runner calls. |
| MF-P5-FCR7-001 / MF-P5-CV-R8-001 | MUST-FIX | fixed, round 10 re-reviewed | Bounded Git probes clean their PGID on successful, timeout, output, parent-exit, and interrupt paths; interrupts are re-raised. |
| SF-P5-FCR4-001 / SF-P5-FCR7-001..002 / SF-P5-CV-R9-001..002 | SHOULD-FIX | fixed, round 10 re-reviewed | Git probes are bounded, filesystem integers including signed mtime are canonical strings, entry/file/depth bounds have tests, and the public support envelope is explicit. |
| MF-P5-SEC11-001 | MUST-FIX engineering control | fixed, re-reviewed, final rescan passed | Git child processes receive a locale-only allowlist plus fixed controls; ambient PATH, macOS developer-tool selectors, Linux/macOS loader selectors, and executable-path variables are removed. |
| MF-P5-SEC11-002 | MUST-FIX engineering control | fixed, re-reviewed, final rescan passed | The trusted `git_executable` binding now reaches repository identity, complete snapshot, Git-control, refresh, and operator production paths; an adapter-level argv execution regression passes. |
| MF-P5-SEC11-003 | MUST-FIX engineering control | fixed, re-reviewed, final rescan passed | Git rejects every symlink component. GitNexus/Node reject parent and multi-hop symlinks while preserving only the explicit single-final-link policy and fingerprint. |
| MF-P5-SEC11-004 | MUST-FIX engineering control | fixed, re-reviewed, final rescan passed | Exact `/usr/bin/env node` and `/usr/bin/env -S node` launchers require the independently bound/fingerprinted Node runtime; other env launch syntax fails closed. |
| SF-P5-SEC11-001 / NIT-P5-SEC11-001 | SHOULD-FIX / NIT | fixed, round-14 defensive re-review passed | Node regular/symlink fingerprints have persistent regressions and the stale environment variable was removed. |
| MF-P5-R12-001 | MUST-FIX ledger continuation | fixed, re-reviewed, final rescan passed | `source_rebound` is a protected, native-Git-verified checkpoint bridge. It binds the live target HEAD, repo-confined spec/manifest descriptors, event-time expiry dispositions, current-session authorization, and a repeated pre-replace CAS check. |
| MF-P5-R12-003 | MUST-FIX qualification evidence | fixed, re-reviewed, final rescan passed | The current GitNexus 1.6.9 qualification evidence was regenerated with the current runtime fingerprint; historical evidence is retained only as historical context. |
| MF-P5-R12-004 | MUST-FIX root classification | fixed, re-reviewed, final rescan passed | Explicit root-path handling now returns a classified rejection instead of an unbound local exception. |
| SF-P5-R12-001 | SHOULD-FIX coverage/documentation | fixed, round-15 deep review passed | Production-entrypoint Git executable coverage and public executable-boundary documentation were added. |
| MF-P5-SEC12-001 / MF-P5-SEC14-001 | MUST-FIX lock boundary | fixed, re-reviewed, final rescan passed | Refresh lock acquisition is descriptor-bound, rejects unsafe parent/file ownership and link topology, and verifies identity around cross-process flock acquisition. A mandatory deterministic fixed-OS-temp canonical-root lock prevents alternate process temp selectors or configured directories from bypassing serialization; a real child-process regression covers contention and reacquisition. |
| MF-P5-SEC12-002 | MUST-FIX Git filter boundary | fixed, re-reviewed, final rescan passed | Local and enabled-worktree filter/include/external-attributes selectors are rejected before any worktree-reading Git command or refresh child. |
| MF-P5-SR14-001 | MUST-FIX target contract binding | fixed, re-reviewed, final rescan passed | Source rebound now requires spec and manifest target-HEAD regular blobs, identical stage-zero index entries, and exact working bytes/modes; modified, staged, untracked, and HEAD-divergent fixtures fail closed and the full binding is repeated before CAS. |
| MF-P5-SR14-002 | MUST-FIX nonblocking input boundary | fixed, re-reviewed, final rescan passed | Ledger, event, spec, and manifest inputs use descriptor-bound `O_NOFOLLOW | O_NONBLOCK` bounded regular-file reads; FIFO, device, hardlink, symlink, oversize, identity, and path-swap fixtures fail closed without blocking. |
| MF-P5-SR14-003 | MUST-FIX idempotent recovery | fixed, re-reviewed, final rescan passed | An exact already-recorded protected source rebound reaches the core idempotency no-op before ancestor-only preflight, still requires current protected-history re-attestation, performs no write, and rejects changed same-key input. |
| SF-P5-SR14-001 | SHOULD-FIX mode boundary | fixed, round-14 defensive re-review passed | Source rebound compares full `S_IMODE`, rejects special permission bits, and atomic ledger replacement preserves the verified original mode. |
| MF-P5-NATIVE-001 | MUST-FIX package provenance | fixed, re-reviewed, final rescan passed | Caller-owned accepted entry, native interpreter, and complete package-tree digests are required before any GitNexus process. The package tree is rehashed at every use through descriptor-bound no-follow reads, and driver version/fingerprint drift forced live requalification. |
| SF-P5-NATIVE-002 | SHOULD-FIX live freshness | superseded and corrected by `V2CA-MF-TRUSTED-TIME-001` | Live source rebound and claim transitions reject future event timestamps against current-session trusted time, while durable lease/disposition semantics use recorded event time in both live application and replay. |
| MF-P5-R16-001 | MUST-FIX package read boundary | fixed, re-reviewed, final rescan passed | Package regular files and contained direct symlink targets are opened from bound directory descriptors with no-follow/nonblocking controls; absolute, escaping, parent-link, target-link, directory, special-file, and file-to-link race cases fail closed. |
| V2CA-MF-TRUSTED-TIME-001 | MUST-FIX durable event semantics | apply-to-replay split fixed; superseded by `V2CA-R18-MF-LEASE-001` | Durable lease/disposition semantics now use `occurred_at` consistently, but round 18 found that live current-lease freshness must remain an additional acceptance condition. |
| V2CA-MF-HOME-TOCTOU-002 | MUST-FIX isolated-home lifecycle | fixed; round-18 re-review closed | A device/inode-keyed thread plus cross-process lock now serializes the isolated home across repositories. Its verified directory descriptor and both locks span refresh; emptiness is checked under lock and immediately before execution. Cross-process, timeout, unsafe-lock, same-inode contamination, and release regressions pass. |
| V2CA-MF-FALLBACK-003 | MUST-FIX recovery threshold | fixed; round-18 re-review closed | `reporting_retry_count` is a reporting-only legacy alias; non-reporting phases require their own worker retry count. Core, CLI, and eval negative cases pass. |
| V2CA-R18-MF-LEASE-001 | MUST-FIX live lease freshness | fixed; round-19 re-review closed | Live acquisition and active-claim transitions require `trusted_time < lease_expires_at`; source rebound requires event-time and trusted-time expiry classifications to match. Round 19 closed this in-memory matrix and opened the separate commit-boundary finding tracked below. |
| V2CA-R19-MF-LEASE-COMMIT-TOCTOU-001 | MUST-FIX commit-boundary freshness | fixed; round-20 re-review closed | `apply-event --write` re-runs live acceptance with a fresh trusted time after source/CAS validation and immediately before ledger replacement. Acquisition, transition, and rebound deadline-crossing regressions preserve original ledger bytes. |
| MF-DOC-TRUSTED-TIME-001 | MUST-FIX documentation | fixed; round-4 docs review closed | Templates and ledger docs distinguish trusted-time freshness from durable event-time semantics. |
| SF-DOC-TRUSTED-TIME-001 | SHOULD-FIX documentation | fixed; round-4 docs review closed | Public text states that `loopctl` supplies current UTC while direct library callers inject `trusted_time`. |
| MF-DOC-STATUS-001 | MUST-FIX status accuracy | fixed; final docs review closed | The headline labels earlier PASS receipts as frozen historical evidence and the current post-fix gate chronology accurately. |
| MF-DOC-STATUS-002 / MF-DOC-VERIFY-001 / SF-DOC-HISTORY-001 | MUST-FIX / SHOULD-FIX documentation | fixed; round-6 docs review closed | Review chronology, current post-A3 verification evidence, and historical supersession are explicit. |
| MF-DOC-STATUS-003 / SF-DOC-VERIFY-002 | MUST-FIX / SHOULD-FIX documentation | fixed; final docs review closed | Round-18 is marked closed by round 19, the separate commit-boundary finding remains distinct, and all three post-scan fix integration receipts are counted. |
| MF-DOC-STATUS-004 | MUST-FIX status accuracy | rejected as stale; final docs review closed | The routed reviewer quoted text already replaced by the concurrent round-20 status update. Current source contains no claim that round 6 remains pending. |
| P5-FINAL-SCAN-CANDIDATES | Security scan candidate set | rejected by final policy; native scan complete | Seven candidate ledgers closed through discovery, validation, and attack-path analysis. None reached protected authority, mutation, query/context adoption, gate, merge, publication, or completion authority; canonical findings are empty and native scan `559c572f-d3fe-44a0-a6f3-c13be1e78521` completed. |
| P5-FINAL-CLOSURE-CLAIMS | MUST-FIX ledger materialization and terminal ordering | fixed, tested, re-reviewed, final native diff scan passed | Source rebound now advances every materialized claim source revision, including released and expired claims. Objective completion now rejects active claims, and final closure must release P5 after task completion. The focused regressions, 651-test full suite, repository validation, 36-event active-ledger audit, final closure code/docs reviews, and scan `5848409e-ca54-4b85-98a8-82b66aff6702` passed with 0 reportable findings. |

Round evidence:

- `receipts/p4-code-review-round1.md`
- `receipts/p4-code-review-round2.md`
- `receipts/p4-code-review-round3.md`
- `receipts/p4-code-review-round4.md`
- `receipts/p4-code-review-round5.md`
- `receipts/p4-code-review-round6-final.md`
- `receipts/p4-code-review-round7-post-security-fix-final.md`
- `receipts/p5-validator-contract-code-review-final.md`
- `receipts/p5-validator-contract-docs-review-final.md`
- `receipts/p5-final-code-review-round10-final.md`
- `receipts/p5-round14-defensive-security-review-final.md`
- `receipts/p5-final-code-review-round15-final.md`
- `receipts/p5-final-code-review-round16-post-finding-fixes.md`
- `receipts/p5-postscan-code-review-round17-blocked.md`
- `receipts/p5-postscan-docs-review-round3-blocked.md`
- `receipts/p5-postscan-code-review-round18-blocked.md`
- `receipts/p5-postscan-docs-review-round4-blocked.md`
- `receipts/p5-postscan-code-review-round19-blocked.md`
- `receipts/p5-postscan-docs-review-round6-blocked.md`
- `receipts/p5-postscan-code-review-round20-final.md`
- `receipts/p5-postscan-docs-review-round7-stale.md`
- `receipts/p5-postscan-docs-review-round8-final.md`
- `receipts/p5-final-security-diff-scan.md`
- `receipts/p5-postscan-docs-review-round9-final.md`
- `receipts/p5-merge-readiness-final.md`
- `receipts/p5-final-closure-fix-verification.md`
- `receipts/p5-final-closure-code-review.md`
- `receipts/p5-final-closure-docs-review.md`
- `receipts/p5-final-closure-security-diff-scan.md`
- `receipts/p5-final-closure-evidence-docs-review.md`
- `receipts/p5-final-closure-merge-readiness.md`

Historical P4, round-14, and round-16 code gates are **PASS** for their frozen
diffs. Rounds 17 through 19 were **BLOCKED** while closing live/replay,
isolated-home, fallback, lease-freshness, and commit-boundary findings. The
round-19 fix and current 651-test full verification are recorded; round-20 code
gate and round-8 docs gate passed with no open MF/SF/NIT. Final native Security
Diff Scan `559c572f-d3fe-44a0-a6f3-c13be1e78521` completed with 13/13 worklist
coverage, 7/7 candidate-ledger closure, and 0 reportable findings. Round-9
evidence-only docs review closed the post-scan receipt delta with no open
MF/SF/NIT.

Historical P4 security gate: **PASS**. Codex Security native scan status `completed`,
coverage `complete`, 3/3 surfaces `no_issue_found`, reportable findings `0`.
See `receipts/p4-security-diff-scan-final.md`. This historical scan does not
cover the bounded validator-contract diff. The separate P5 scan recorded above
covers the published adapter diff through its bound snapshot; neither scan
covers the later unpublished final-closure fix.

Accepted residuals are documented in the final code-gate receipt. Their owner
is the V2c adapter maintainer; reconsider them if the adapter later enables a
structured query capability, auto-refresh, non-local filesystems, or live Linux
qualification.
- Goal runtime auto-blocking is a coordination limitation, not a V2c adapter
  defect. The separate workflow-runtime follow-up and bounded current-session
  degradation are recorded in `receipts/p5-goal-runtime-degradation.md`.
- `receipts/p4-docs-review-round1.md`
- `receipts/p4-docs-review-round2-final.md`

V2c-B follow-up owner: future Loop Engineering hooks objective. Promotion
trigger: V2c-A adapter/controller qualification and ready-for-review acceptance.
