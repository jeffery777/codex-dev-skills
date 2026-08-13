# Issue #145 Memory M0 Architecture Decisions

## M0-001 — Add Downstream Families

Keep `loop-memory/v1`, V2d-A/B, V3-A, and
`loop-candidate-evaluation/v0` unchanged. Add separate operation and
qualification families so their authority and lifecycle cannot leak upstream.

## M0-002 — Caller Owns Authority Acceptance

Operation authority binds one exact request, but it is usable only when the
current caller independently supplies accepted authority-, eligibility-, and
trusted-time-receipt digests. Request or receipt validation reconstructs the
whole chain; adapter, database, request, and receipt data cannot self-sign or
self-accept authority.

## M0-003 — Separate Authority, Composition, Execution, And Acceptance

Use separate authority, trusted-time receipt, authorized request, and execution
receipt kinds. Preserve issuance, expiry, nonce, state-root, and caller-owned
time evidence in the request. Execution remains future M1 behavior.

## M0-004 — Make Delete Logical In M0

M0 preserves the V2b `delete` operation name but fixes its M0 lifecycle effect
to `logical-delete`. Physical purge/hard delete is deferred because it is
destructive and requires exact storage, retention, backup, recovery, and human
authority decisions unavailable in M0.

## M0-005 — Add A Separate Paired Qualification Wrapper

Released V3-B cannot express a memory-off/on pair and forbids context from
changing comparison. Add `loop-memory-qualification/v0`; do not modify V3-B.

## M0-006 — Require A Zero-Touch Memory-Off Path

Memory-off accepts no backend configuration and performs no SQLite/FTS5 import,
probe, state-root discovery, or backend/filesystem call. This is a testable
contract, not an implementation convention.

## M0-007 — Limit M1 Data To Public/Internal-Only

Reject secrets, credentials, PII, private paths, raw chat/session/log data, and
unredacted machine config. Make no encryption-at-rest or shared-host
confidentiality claim. Either requirement triggers a later security decision.

## M0-008 — Fail Closed On Schema Or Capability Drift

Bind exact adapter, schema, capability, and platform fingerprints. Unknown or
drifted fingerprints fail closed. A strict M1 receipt also binds the exact
qualification id, V3-B/verifier tuple, fingerprints, safety observation, and
execution receipts so it cannot replay across scope. Automatic migration and
repair are excluded.

## M0-009 — Qualify Safety And Conformance Before Efficacy

M1 initially proves isolation, authority, atomicity, idempotency, lifecycle,
privacy, recovery, and deterministic behavior. Any memory-benefit claim needs a
new observation-production product decision and evidence source.
Readiness metrics are computed from executed negative-case outcomes rather
than fixed expected literals.

## M0-010 — Keep Release Selection Human-Owned

Target release stays **TBD / human decision**. Passing M0 validation, evals, or
reviews cannot select a release, authorize M1, or activate a backend.
