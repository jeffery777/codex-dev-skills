# Issue #145 Loop Spec — Memory M0 Readiness

## Status And Objective

This specification qualifies a provider-neutral Memory M0 boundary. It adds no
backend and does not authorize M1. The delivery defines two additive offline
families:

- `loop-memory-operation/v0` for caller-owned operation authority,
  deterministic authorized-operation composition, and non-authoritative
  atomic execution receipts;
- `loop-memory-qualification/v0` for a paired safety/conformance wrapper over
  existing validated V3-B results without changing V3-B.

Target release: **TBD / human decision**.

## Sources Of Truth

- GitHub Issue #145;
- `AGENTS.md`, `SECURITY.md`, `README.md`, `docs/roadmap.md`, and
  `docs/release-readiness.md`;
- `docs/loops/issue-135/roadmap-spec.md`;
- the Operational Evidence program documents and OE-013 through OE-015;
- the released V2b, V2d-A, V2d-B, V3-A, and V3-B contracts, portable
  references, production validators, tests, and evals;
- this Issue-owned spec, ADR, threat model, plan, task packet, and gate
  receipt.

Chat summaries, Issue prose, worker reports, memory content, role labels,
scores, eval results, and execution receipts are context only. Current
repository/Git state, accepted caller evidence, verification, review,
protected authorization, and accepted platform state remain authoritative.

## Verified Entry Facts

- Repository `jeffery777/codex-dev-skills` is public and defaults to `main`.
- The branch base, accepted `origin/main`, annotated `v0.13.0` peeled target,
  and latest non-draft/non-prerelease Release target are
  `47d1178a8fcabaa5ca23af15e615aa0eaf9d7257`.
- Issues #135, #141, and #143 are closed; PRs #142 and #144 are merged.
- Issue #145 was created only after open Issue/PR and semantic collision checks
  returned empty.
- The tracked resolver selects Python 3.12.9 with PyYAML 6.0.3.
- No exact-head GitNexus index exists for this worktree. Sibling indexes are
  not accepted as exact-head evidence, and no analysis was authorized.
- Production has no SQLite/FTS5 backend, database/schema, operation-authority
  verifier, mutation executor, or atomic execution receipt.

## Facts, Inference, And Unverified Claims

Verified contract facts:

- V2b mutation candidates are candidate-only and cannot authorize or execute.
- Current V3-B has one fixed comparison and a digest-only advisory-context
  summary that cannot alter comparison policy or outcome.
- Existing V2d/V3 outputs preserve exact false-authority fields.

Accepted design inference:

- New downstream families can compose the current contracts without changing
  their v0/v1 semantics.
- Current V3-B cannot represent a paired memory-off/memory-on qualification;
  an additive wrapper is required.

Unverified and deferred to M1:

- exact SQLite library/build, FTS5/tokenizer, schema, OS/filesystem, locking,
  permissions, crash, disk-full, corruption, migration-refusal, and
  transaction evidence;
- memory efficacy, quality, latency, or resource-benefit claims;
- encryption-at-rest and shared-host confidentiality.

## One-Way Artifact Chain

```text
V2b mutation candidate
  -> V2b eligibility receipt
  -> caller-owned operation authority
  -> authorized-operation request
  -> future adapter execution
  -> atomic execution receipt
  -> independent acceptance/promotion
```

No artifact authorizes or proves the next step. The M0 CLI validates and
composes explicit input bytes only. It never dispatches an adapter or performs
an operation.

## Shared Strictness

Both families use strict bounded UTF-8 JSON:

- duplicate keys, unknown fields, floats, lone surrogates, unsafe identifiers,
  unsafe paths, oversized/deep inputs, tamper, private data, and modified
  authority fields reject;
- canonical JSON is recursively key-sorted, compact, UTF-8, integer-only, and
  limited to the JSON-safe integer range;
- documents are limited to 131,072 bytes, depth 32, arrays 256, strings 512
  UTF-8 bytes, and safe identifiers 128 ASCII characters unless stricter;
- timestamps require explicit timezone and lower-case SHA-256 digests;
- CLI inputs are explicit regular non-symlink files opened through the same
  bounded no-follow snapshot pattern used by released validators;
- errors are stable, generic, bounded, and non-echoing.

## `loop-memory-operation/v0`

### Common envelope

Every document has exactly:

- `contract_version`: `loop-memory-operation/v0`;
- `kind`: an operation authority, trusted-time receipt, authorized request, or
  execution receipt;
- `document_id`;
- `repository` using the unchanged V2b repository shape;
- `namespace`, `source_revision`, and normalized `path_scope`;
- `payload`;
- exact operation false-authority/action invariants;
- `document_digest` over canonical bytes with only that field omitted.

The invariants deny use as authorization or completion evidence and deny
unrelated external-write, verification, review, acceptance, promotion, merge,
release, deploy, activation, and validator-runtime-action claims. A future
receipt may report an executor outcome as untrusted evidence, but M0 validation
does not prove that an executor or transaction existed. The authority kind can
authorize only its exact future memory operation after the current caller
independently accepts its control-plane receipt.

### `operation-authority`

The payload binds exactly:

- authority id, issuer principal, issuance/expiry, and one-use nonce;
- operation/request/idempotency ids;
- operation kind: `upsert`, `invalidate`, `tombstone`, or `delete`, exactly
  matching the V2b candidate, plus `lifecycle_effect: logical-delete` for
  `delete`;
- target record id, nullable target-before digest, candidate record digest,
  mutation-candidate digest, and accepted eligibility-receipt digests;
- expected lifecycle transition;
- adapter id/version, schema fingerprint, capability fingerprint, and required
  capabilities;
- approved state-root class and identity digest without a local path;
- independent authority-receipt digest.

The caller separately supplies three strict files, each shaped exactly as
`{"receipt_digests":["<sha256>"]}`: accepted authority receipts and accepted
eligibility receipts plus an accepted trusted-time receipt. Neither a document
nor an adapter may self-accept them. The authority document may state
`memory_operation_authorized: true` for its exact scope, while
`unrelated_external_write_authorized` remains false; the statement is not
usable until the current caller admits its receipt digest.

### `authorized-operation-request`

This generated kind binds exact authority, V2b candidate, eligibility, caller
acceptance sets, repository/principal/namespace/revision/path identity,
operation/target/candidate/idempotency identity, freshness, nonce,
adapter/schema/capability equality, expected pre-state, and expected
transition.

`authority_verified_for_exact_request` is a deterministic result of the
caller-supplied acceptance inputs. The request preserves authority id,
principal, issuance/expiry, nonce, state-root, and trusted observation-time
bindings. Validation always reconstructs the complete external chain; a
standalone resealed request cannot validate itself. `execution_performed` is
always false.

### `execution-receipt`

The receipt binds exact request/authority/eligibility/candidate digests,
scope/operation/idempotency identity, adapter/schema/capability/platform
fingerprints, transaction id, pre/post state, and outcome.

Outcomes are:

- `applied`: one atomic state-plus-receipt commit;
- `idempotent-replay`: exact original applied receipt, no second mutation;
- `failed`: deterministic bounded error class and no success claim.

Timeout, interruption, lock, disk, integrity, schema, fingerprint, transaction,
or commit uncertainty can only be `failed`. A receipt is validated evidence,
not proof that a real adapter or transaction exists; M1 must independently
qualify the executor.

## `loop-memory-qualification/v0`

The family contains `qualification-input` and `qualification-result` kinds.
The sealed input records exact common V3-B proposal/source-lineage,
evaluation-input, policy, comparison, and verifier-assignment digests so result validation can
reconstruct its semantic binding instead of trusting a resealed result.
The input composes two arms around complete, already validated V3-B
result/verification pairs:

- a wrapper `memory-off` arm whose V3-B context mode is `memory-off`;
- a wrapper `memory-on` arm that binds a V3-B result/verification pair plus one
  exact separately accepted future M1 qualification receipt and bounded M1
  safety observations.

A wrapper memory-on observation requires at least one backend touch and at
least one execution-receipt digest. A zero-touch on arm cannot qualify as M1
safety/conformance evidence.

`memory-on` is a wrapper mode, not a new V3-B context mode. The V3-B document
inside that arm remains an unchanged released V3-B result (`memory-off` or
`synthetic-advisory`) and is never claimed to have evaluated a backend.

The result binds exact proposal/source lineage, scenario set, fixed V3-B
policy, environment class, limits, thresholds, verifier assignment structure,
adapter/schema/capability/platform fingerprints, and both result/verification
digests. A separate caller file shaped as
`{"qualification_receipt_digests":["<sha256>"]}` must admit the exact M1
receipt document. That document binds qualification id, the full common V3-B
tuple, adapter fingerprints, safety-observation digest, and execution-receipt
digests; cross-scope replay rejects. Initial status is safety/conformance only:

- `conformant-awaiting-human-decision`;
- `not-conformant`;
- `memory-on-unavailable`.

The wrapper cannot change either V3-B result or compare their candidate-quality
outcomes, and it cannot claim efficacy. `memory-on` may be represented only
when the caller supplies an independently accepted M1 qualification receipt
for the exact fingerprints. M0 tests use synthetic future-receipt shapes only
and do not claim an adapter exists.

## Memory-Off Zero-Touch Boundary

Memory-off accepts no backend handle, executable, state root, database path, or
provider config. It imports/probes no SQLite/FTS5 and performs no ambient
discovery. It must not create, open, read, write, stat, lock, or delete any
backend/database/journal/backup path. Tests instrument the backend/filesystem
seam and require zero calls.

## Lifecycle, Delete, Concurrency, And Recovery

- Lifecycle states are active, superseded, invalidated, tombstoned, and
  logically deleted with deterministic dominance.
- Physical purge/hard delete is excluded. Expiry/retention never authorizes
  deletion.
- One exact scope-bound idempotency key produces at most one applied state
  transition.
- M1 is single-host cooperative local/manual/CI coordination only.
- Schema mismatch fails closed; automatic migration and automatic repair are
  prohibited.
- Recovery may return an existing verified atomic receipt but cannot synthesize
  success, discard history, purge, migrate, repair, or promote.

## Privacy And Data Placement

M1 will require an explicitly approved current-user-owned non-symlink state
root with restrictive permissions. Its path and material never enter the
public contracts. Public Git stores only contracts, code, synthetic fixtures,
tests/evals, docs, and redacted summaries.

M1 is public/internal-only. Secrets, credentials, PII, private paths, raw
chats/sessions/transcripts/logs, and unredacted machine configuration reject
without echo and are never stored. No encryption/shared-host claim is made.

## M1 Candidate Inventory — Design Only

M0 may document candidate tables for metadata, records, lifecycle,
idempotency, authority/request digests, and atomic receipts; provider-neutral
API concepts; future `probe`, `query`, `execute`, `receipt`, and `integrity`
CLI concepts; and synthetic safety/fault fixtures. M0 must not import/probe
SQLite, execute SQL, create a schema/database, or persist state.

## Acceptance Matrix

| Scenario | Required result |
| --- | --- |
| memory-off | deterministic complete result and zero backend/filesystem touch |
| missing/untrusted authority | reject before composition/execution |
| adapter self-authority | reject |
| scope mismatch | reject without disclosure |
| expired authority or fingerprint drift | fail closed |
| untrusted/backdated clock or resealed request | reject after full-chain reconstruction |
| applied | one atomic state-plus-receipt transition shape |
| exact replay | original result, no second mutation |
| conflicting replay | reject |
| uncertain transaction | failed, never partial success |
| physical purge | unsupported and out of scope |
| private/sensitive input | generic rejection |
| paired qualification | exact source/policy/environment/threshold equality |
| verifier mismatch or M1 receipt replay | reject |
| readiness metrics | derive from executed adversarial outcomes, never literals |
| efficacy request | human product gate |

## Definition Of Done

- Issue-owned spec, ADR, threat model, plan, task packet, and gate are bound to
  the accepted base.
- Both additive references, validators, CLIs, synthetic fixtures, tests, and
  evals implement this spec without upstream contract changes.
- Existing focused and full production verification remains green.
- Impact/diff inspection and deep public-contract/security/privacy review have
  no unresolved blocker.
- The diff contains no SQLite/FTS5/backend/persistence/provider/MCP/automation,
  private data, efficacy claim, or release commitment.
- Work stops before commit for explicit human authorization.

## Stop Conditions

Stop for unresolved authority, paired-qualification, delete, privacy,
data-placement, or public-contract semantics; backend execution/persistence;
V3-B changes; efficacy claims; confidential/restricted data; encryption or
shared-host claims; physical purge; automatic migration/repair; cross-host
coordination; V3-C; release selection; destructive action; failed high-risk
verification; unresolved review blockers; or any unauthorized external write.
