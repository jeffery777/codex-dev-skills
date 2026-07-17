# Issue 97 Review Disposition

This file is the durable finding ledger for V2c-A. Findings are not closed by
chat, Goal status, worker reports, or passing tests alone. Each disposition must
bind concrete diff, verification, review, or scan-native evidence.

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

Round evidence:

- `receipts/p4-code-review-round1.md`
- `receipts/p4-code-review-round2.md`
- `receipts/p4-code-review-round3.md`
- `receipts/p4-code-review-round4.md`
- `receipts/p4-code-review-round5.md`
- `receipts/p4-code-review-round6-final.md`
- `receipts/p4-code-review-round7-post-security-fix-final.md`

Final code gate: **PASS**. Open code MF/SF/NIT: none.

Final security gate: **PASS**. Codex Security native scan status `completed`,
coverage `complete`, 3/3 surfaces `no_issue_found`, reportable findings `0`.
See `receipts/p4-security-diff-scan-final.md`. Open security MF/SF/NIT: none.

Accepted residuals are documented in the final code-gate receipt. Their owner
is the V2c adapter maintainer; reconsider them if the adapter later enables a
structured query capability, auto-refresh, non-local filesystems, or live Linux
qualification.
- `receipts/p4-docs-review-round1.md`
- `receipts/p4-docs-review-round2-final.md`

V2c-B follow-up owner: future Loop Engineering hooks objective. Promotion
trigger: V2c-A adapter/controller qualification and ready-for-review acceptance.
