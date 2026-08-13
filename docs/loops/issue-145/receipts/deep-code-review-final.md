# Issue #145 Deep Code Review — Final

Date: 2026-08-13

## Executive Summary

**PASS.** The final uncommitted mixed diff is additive, keeps released
V2b/V2d/V3-A/V3-B production modules unchanged, and has no unresolved
MUST-FIX, SHOULD-FIX, or NIT finding.

Review mode was read-only after the final fix round. Focus included authority,
identity, digest binding, expiry, lifecycle, idempotency, atomicity, replay,
zero-touch, privacy, file parsing, packaging, and public-contract drift.

## Finding Dispositions

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| M0-REV-001 | MUST-FIX | Upsert record scope could differ from the candidate envelope | Fixed; exact repository and namespace equality plus negative test/eval |
| M0-REV-002 | MUST-FIX | Execution receipt pre-state was parsed but not bound to the request | Fixed; exact expected-pre-state equality plus tamper test/eval |
| M0-REV-003 | MUST-FIX | `runtime_action_performed: false` conflicted with a future receipt reporting an executor outcome | Fixed; renamed to validator-specific offline invariant and rebound docs/fixture |
| M0-REV-004 | MUST-FIX | Memory-on safety input could report zero backend touches | Fixed; on arm now requires at least one touch and one execution-receipt digest |
| M0-REV-005 | MUST-FIX | A resealed qualification result could change common V3-B semantics or drop its on arm | Fixed; sealed common bindings and exact on-arm-presence/result reconstruction checks |
| M0-SEC-001 | MUST-FIX | Standalone request/receipt validation trusted self-asserted authority | Fixed; full caller-owned chain reconstruction |
| M0-SEC-002 | MUST-FIX | Authority freshness used time without accepted provenance | Fixed; caller-accepted trusted-time receipt and carried lifecycle bindings |
| M0-SEC-003 | MUST-FIX | Paired qualification omitted verifier assignment | Fixed; canonical verifier digest is an exact common binding |
| M0-SEC-004 | MUST-FIX | M1 receipt digest could replay across qualification scope | Fixed; strict receipt binds id, V3-B tuple, fingerprints, safety, and execution receipts |
| M0-SEC-005 | MUST-FIX | Security eval metrics were literals or incomplete oracles | Fixed; adversarial outcomes drive metrics and cover reseal/replay |
| M0-REV-006 | MUST-FIX | Memory-off accepted an unused M1 receipt option | Fixed; M1 options reject unless an on arm is present |

No finding was deferred, rejected, or left for a hidden follow-up.

## Deep Risk Notes

- The validator proves document conformance, not that a future adapter,
  transaction, lock, or durable receipt exists.
- Caller-owned accepted digest maps and trusted-time evidence remain the control-plane trust boundary;
  adapter, database, request, and receipt data cannot self-accept.
- Exact SQLite build/tokenizer/platform qualification remains a future M1
  responsibility and is intentionally absent here.
- Physical purge, efficacy, migration, shared-host confidentiality, activation,
  and release selection remain human gates.

## Re-runnable Verification

Use the commands in `verification-report.md`, especially full unittest
discovery, both M0 evals, `./scripts/validate-repo.sh`, and `git diff --check`.
