# Issue #135 Roadmap Spec — V3-B Re-Entry And Agent Memory

## Status And Objective

This is a docs-only planning specification. It defines the re-entry sequence
for V3-B and the M0/M1/M2 Agent Memory track. It does not release v0.12.0,
implement V3-B, complete M0 qualification, implement or enable a memory
backend, or authorize V3-C automation.

The required delivery order is:

1. close and publish v0.12.0 through a separate release Issue and human gate;
2. implement and qualify V3-B isolated candidate evaluation through a separate
   Issue;
3. qualify Memory M1 as a thin reference backend through a later separate
   Issue/spec/ADR/security review;
4. consider V3-C optional resident automation only after a new human decision.

M0 design can be refined while V3-B is planned, but M0 qualification evidence
must not be inferred from this document. Release closure, V3-B implementation,
M1 implementation, and V3-C automation remain separate deliveries.

No target release after v0.12.0 has been accepted. The release target for V3-B,
M1, M2, or V3-C is **TBD / human decision**.

## Sources And Evidence Boundary

Canonical sources are:

- GitHub Issue #135;
- `docs/roadmap.md`;
- `docs/programs/operational-evidence/README.md`;
- `docs/programs/operational-evidence/implementation-phases.md`;
- `docs/programs/operational-evidence/continuation.md`;
- `docs/programs/operational-evidence/architecture-decisions.md`;
- `docs/external-memory-contract.md`;
- `skills/loop-engineering/references/memory-contract-v1.md`;
- the current V2b validator, CLI, tests, and eval suite.

The repository, Git, current instructions, verification, review, protected
authorization, and accepted platform state remain authoritative. V3-A
proposals, V2b memory records, adapter receipts, scores, evals, and this roadmap
are advisory inputs only.

## Verified Baseline And Inference

Verified repository behavior:

- `loop-memory/v1` is strict, backend-neutral, and useful with no backend.
- It defines capability handshakes, query requests/responses, repository and
  principal identity, namespaces, advisory records, retrieval dispositions,
  write eligibility, mutation candidates, lifecycle states, conformance, and
  false-authority receipts.
- `memoryctl.py` only validates and produces offline decisions/receipts.
- `mutation-candidate-request` is permanently candidate-only in V2b and fixes
  `external_write_authorized` and `write_performed` to false.
- The tests and evals cover identity isolation, capabilities, idempotency
  inputs, lifecycle dominance, sensitivity, prompt injection, replay,
  deterministic decisions, and no-backend fallback.
- No production persistence, adapter write executor, database schema, network
  service, operation-authority verifier, or execution receipt exists.

Planning inference:

- A future backend can compose V2b without weakening it if execution authority
  remains out of band and every executed operation produces independently
  verifiable, non-authoritative evidence.
- SQLite/FTS5 is a suitable first reference candidate because it can remain
  local and replaceable, but suitability is not qualification. M1 must still
  pass capability, determinism, failure, security, privacy, and V3-B
  memory-off/on gates.

## Memory Track

### M0 — Backend Readiness

M0 is a design and qualification track, not a backend. It must produce reviewed
evidence for:

- the contract-to-runtime gap matrix below;
- a provider-neutral request/receipt protocol;
- separation of candidate eligibility, operation authority, execution, and
  promotion;
- data placement, schema/versioning, lifecycle, retention, recovery,
  concurrency, idempotency, security, and privacy decisions;
- a V3-B-compatible memory-off/on evaluation design;
- a fail-closed capability policy and acceptance thresholds.

This Issue defines the required evidence but does not claim that M0
qualification has passed.

### M1 — Thin Reference Backend Qualification

M1 may start only after V3-B qualification evidence exists and a separate
Issue/spec/ADR/security review is approved. The planned candidate is a thin,
replaceable SQLite/FTS5 adapter with all of these constraints:

- disabled by default;
- explicit local/manual/CI invocation only;
- no daemon, resident process, scheduler, hook activation, network listener,
  MCP server, or cross-host coordination;
- deterministic record/query ordering and canonical receipt bytes;
- behavior-based FTS5 capability probe in an isolated temporary database
  before adoption, bound to the exact SQLite library/build and tokenizer
  fingerprint rather than a version string alone;
- fail closed to no memory when FTS5, schema, transaction, lock, integrity,
  provenance, identity, or required capability evidence is unavailable;
- no silent fallback from FTS5 to `LIKE`, an unqualified tokenizer, a vector
  index, or another query implementation;
- structured bounded query input, parameterized SQL, no raw SQL or caller-owned
  FTS expression, and disabled SQLite extension loading;
- repository, principal, namespace, revision, and path-scope isolation;
- digest-bound write eligibility and repository provenance;
- caller-owned operation authority separate from the V2b candidate document;
- idempotent operation keys and atomic state-plus-execution-receipt commit;
- explicit upsert, invalidate, tombstone, delete, retention, and recovery
  behavior;
- explicit database, record, result, query, time, and transaction bounds plus
  fail-closed integrity checks;
- context/cache status only, never instruction, authorization, completion,
  review, gate, promotion, merge, release, or deployment authority.

Passing M1 qualification would qualify only the exact adapter version, schema,
SQLite/FTS5 capability fingerprint, platform envelope, and reviewed operation
set. It would not enable the adapter by default or approve V3-C.

### M2 — Second Provider Or MCP Adapter

M2 remains unplanned until M1 qualification passes. A second provider or MCP
adapter requires a separate human decision and must prove the same
provider-neutral conformance, identity, authority, privacy, lifecycle,
idempotency, and execution-receipt semantics. M2 cannot be used to relax V2b or
to retrofit compatibility for PlugMem, Mem0, or another product.

## Contract-To-Runtime Gap Matrix

| V2b contract surface | Current evidence | M0 requirement | Earliest implementation owner |
| --- | --- | --- | --- |
| Capability handshake | Exact capability states and trusted conformance binding | Define backend fingerprint, schema, SQLite and FTS5 probes, and drift invalidation | M1 |
| Query request/response | Digest-bound, bounded, isolated, replay-aware advisory retrieval | Define deterministic SQL/FTS ordering, pagination, timeout, integrity, and error mapping | M1 |
| Repository/principal/namespace identity | Exact digest-bound identity and path scope | Define machine-local database partition/key rules and negative cross-scope tests | M1 |
| Memory record and provenance | Strict advisory record with repository artifact source | Define normalized relational storage that round-trips exact canonical records | M1 |
| Retrieval decision | Fail-closed adoption/quarantine/rejection | Preserve the production decision unchanged; adapter never bypasses it | V3-B seam and M1 |
| Write eligibility | Offline, digest/revision/acceptance-bound candidate receipt | Define how an eligible receipt is supplied to an authority verifier without becoming authority | M0 |
| Mutation candidate | Describes upsert/lifecycle/delete but cannot authorize or write | Define provider-neutral authorized-operation input without changing the candidate invariants | M0, then M1 |
| Operation authority | Not implemented | Bind exact operation, identity, target/record digest, idempotency key, expiry, actor/principal, and authority receipt digest outside adapter data | M0, then separate M1 security review |
| Execution receipt | Not implemented | Bind candidate, authority, adapter/schema/capability fingerprint, transaction result, pre/post state digests, idempotent replay result, and false-authority invariants | M0, then M1 |
| Atomicity/concurrency | Capability names only | Define writer serialization, busy/lock failure, crash points, no partial-success claim, and atomic state-plus-receipt commit | M1 |
| Lifecycle/retention/delete | Validated states and candidate operations only | Define tombstone precedence, retention clock, deletion authority, recovery, backup, and no automatic destructive cleanup | M0, then M1 |
| Data placement | Machine-local backend material excluded from Git | Define secure local placement, ownership/permissions, backup policy, portability boundary, and explicit non-storage of secrets/PII/raw logs | M0, then M1 |
| V3-B evaluation | No provider-neutral memory comparison seam yet | Define an optional validated context input and identical memory-off/on evaluation envelope | V3-B |

No matrix row is marked implemented or qualified by this docs change.

## Provider-Neutral Operation Protocol

The future protocol must keep four artifacts distinct:

1. **Eligibility receipt:** V2b proves only that a candidate may be considered.
   It remains `candidate_only: true` and performs no write.
2. **Operation authority:** a current caller or accepted platform independently
   authorizes one exact operation. It binds repository/principal/namespace,
   target and record digest, operation kind, idempotency key, authority receipt
   digest, expiry, and the exact adapter capability fingerprint allowed to
   execute it.
3. **Execution receipt:** the adapter reports `applied`, `idempotent-replay`,
   or `failed` and binds the exact candidate, authority, adapter/schema/
   capability fingerprint, transaction identity, and pre/post state digests.
   State and a successful receipt must commit atomically; uncertainty reports
   failure, never partial success.
4. **Independent acceptance/promotion:** repository verification, review, and
   the human/platform gate decide whether any result is accepted. Neither the
   authority document nor the execution receipt proves task completion or
   promotion.

The concrete schema remains an M0/M1 design decision. This spec freezes the
separation and required bindings, not a public `loop-memory/v1` extension.

## Data Placement, Lifecycle, Concurrency, Security, And Privacy

### Placement and lifecycle

- Database files, journals, locks, backups, runtime configuration, and
  capability fingerprints stay machine-local and outside the repository.
- Local placement must use a current-user-owned non-symlink directory with
  restrictive directory/file permissions defined by the future M1 security
  spec. CI databases are ephemeral and are not uploaded as artifacts by
  default.
- Public Git may contain only contracts, code, synthetic fixtures, tests,
  documentation, and redacted qualification summaries.
- Active, superseded, invalidated, tombstoned, and deleted states must preserve
  deterministic precedence and an auditable operation chain.
- Expiry and retention never authorize physical deletion. Destructive cleanup
  requires an exact operation authority and a recovery decision.
- M1 must define schema compatibility, migration refusal, rollback, corruption
  recovery, backup/restore scope, and crash recovery before implementation is
  accepted.

### Concurrency and idempotency

- One logical operation key may produce at most one applied state transition.
- Replays return the original bound result or an exact idempotent-replay
  receipt; they do not execute twice.
- Writers are serialized through qualified SQLite transaction semantics.
- Lock contention, timeout, process termination, disk-full, integrity failure,
  and receipt-write failure fail closed without a success claim.
- M1 is single-host local/CI coordination only. Distributed locking,
  multi-writer cross-host replication, and service availability are excluded.

### Threat model

| Threat | Required control | Residual/human gate |
| --- | --- | --- |
| Cross-repository or cross-principal disclosure | Digest-bound repository/principal/namespace/path predicates on every query and operation; negative isolation tests | Any shared database or multi-tenant design requires a new security decision |
| Prompt injection or stale context | Reuse V2b validation and current repository/instruction conflict checks after retrieval | Memory remains advisory and may be disabled at any time |
| Secret, credential, PII, private path, or raw-log capture | Deterministic rejection, non-echoing errors, public/internal-only M1 policy, synthetic tests | Confidential/restricted storage is out of M1 scope |
| Adapter self-authorization | Caller-owned operation authority and accepted capability fingerprint; candidate and receipt stay non-authoritative | Authority-schema ambiguity blocks M1 |
| Replay or duplicate mutation | Unique idempotency binding plus atomic original-result lookup | Any ambiguous replay fails closed |
| Crash between state and receipt | One transaction for state and successful receipt; crash-injection tests | No success may be reconstructed from adapter self-report alone |
| SQLite/FTS5 capability or schema drift | Runtime probe, integrity/schema check, exact fingerprint, fail closed to no memory | New runtime/schema requires requalification |
| SQL/FTS expression injection or extension loading | Structured bounded query fields, parameterized SQL, fixed qualified query construction, no raw SQL/FTS expression, extension loading disabled | Any new tokenizer or query grammar requires requalification |
| Resource exhaustion or corrupt database | Database/record/result/query/time/transaction bounds, integrity checks, no automatic repair or partial result adoption | Wider limits or repair tooling require a later reviewed envelope |
| Database theft or unsafe local permissions | Current-user-owned non-symlink placement with restrictive permissions; no secrets/PII/raw logs | Encryption or shared-host confidentiality requires a later security design |
| Destructive lifecycle operation | Exact scoped authority, tombstone/history rules, recovery plan, no automatic cleanup | Physical purge remains a separate destructive gate |
| Database content treated as completion/promotion | Exact false-authority invariants and independent repository/platform verification | No roadmap stage may remove the human/platform promotion gate |

## V3-B Provider-Neutral Context And Evaluation Seam

V3-B may implement an optional context input seam, but it must not contain a
SQLite backend or make memory required. The seam must:

- accept only explicit bounded context and a V2b retrieval receipt produced by
  the existing production decision;
- support an exact `memory-off` mode that supplies no adopted context and
  remains the default;
- reserve `memory-on` for a later qualified adapter while allowing synthetic
  contract fixtures during V3-B testing;
- bind the same proposal, baseline, candidate, source evidence, execution
  policy, environment class, limits, authority invariants, and acceptance
  thresholds in both modes;
- record memory mode and exact context/receipt digests as evaluation inputs,
  never as authority;
- canonicalize and deterministically order the exact adopted context set so
  input permutation cannot change the comparison;
- compare decision correctness, regression, determinism, recovery, privacy,
  resource cost, and false-authority outcomes;
- fail closed to memory-off when context is missing, partial, stale, untrusted,
  sensitive, conflicting, or unsupported;
- keep independent execution verification and the promotion packet separate
  from candidate execution.

V3-B qualification does not require M1 and cannot claim a memory-on result from
an unqualified backend. M1 qualification later reuses the accepted V3-B seam
to compare the exact no-memory baseline with the qualified adapter path.

## Scenario And Acceptance Matrix

| Scenario | Required result | Planned evidence owner |
| --- | --- | --- |
| v0.12.0 is not released | V3-B implementation remains blocked; this docs plan may merge independently | Release platform evidence |
| V3-B memory-off | Isolated baseline/candidate execution and same-policy comparison work with no backend | Future V3-B Issue |
| V3-B synthetic context seam | Explicit validated advisory input cannot change authority or thresholds | Future V3-B tests/eval |
| M1 FTS5 unavailable or drifted | `memory-on` is unavailable; fall back to no memory, with no simulated query | Future M1 capability tests |
| Wrong repository/principal/namespace/path | Query and operation reject without content disclosure | Future M1 isolation tests |
| Duplicate or replayed operation | No second mutation; exact original or idempotent-replay receipt | Future M1 transaction tests |
| Crash, disk-full, timeout, or lock contention | No partial-success claim; recover or fail closed | Future M1 fault injection |
| Lifecycle conflict | Deterministic precedence; no physical deletion without authority | Future M1 lifecycle tests |
| Sensitive/private content | Reject generically; do not store or echo | Future M1 security/privacy tests |
| Memory-on improves a metric | Still context-only; independent verification and promotion gate remain pending | Future M1 qualification |
| Memory-on regresses or is nondeterministic | M1 qualification fails; memory stays disabled | Future M1 qualification |
| M1 qualification absent | M2 and memory-dependent V3-C work remain blocked | Human/platform gate |
| Resident recall/write or service requested | Stop for a new V3-C architecture/security/privacy decision | Human gate |

## Next Independent V3-B Implementation Issue Brief

Do not create this Issue from the current docs task. After v0.12.0 release
closure is verified, a maintainer may use this brief:

**Title:** Implement V3-B isolated candidate evaluation

**Objective:** Consume validated V3-A proposal output and complete V2d source
lineage, execute baseline and candidate in isolated manual/CI environments,
compare them under one fixed policy, produce an independent verification result
and a promotion packet that cannot promote itself, and expose an optional
provider-neutral advisory-context seam with memory-off as the default.

**In scope:** exact proposal/evidence binding; isolated baseline/candidate
execution; same-policy and environment-difference handling; deterministic
regression/authority checks; independent verifier role; promotion-packet
preparation; synthetic adversarial fixtures; manual/CI equivalence; optional
explicit V2b-validated context input.

**Out of scope:** SQLite, FTS5, any backend/provider/MCP implementation,
automatic recall/write, V2b weakening, M1/M2, resident hooks/services, automatic
approval/promotion, release, deploy, and private records in public Git.

**Required scenarios:** baseline pass/candidate pass; baseline pass/candidate
regression; verification failure; environment mismatch; tampered/missing V3-A
lineage; false authority/action; memory-off; invalid/stale/conflicting synthetic
context; deterministic replay; zero external write or promotion.

**Human gates:** stop on public-contract, execution-authority, sandbox,
privacy, data-model, environment-equivalence, or acceptance-threshold ambiguity.
Merge, release, activation, promotion, and every M1 implementation action remain
separately authorized.

**Target release:** TBD / human decision.
