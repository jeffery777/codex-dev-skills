# Loop Engineering External Memory Contract `loop-memory/v1`

This is the normative field contract implemented by
`scripts/memory_contract.py`. It is backend-neutral and contains no persistence,
network, or adapter implementation. The executable validator is authoritative
for exact field sets, types, bounds, and deterministic decisions.

## Canonical Encoding

Canonical bytes are UTF-8 JSON with recursively sorted object keys, no extra
whitespace, JSON-native escaping, and finite numbers only. Input parsing rejects
duplicate keys and documents larger than 131072 encoded bytes. This algorithm
is contract-local; it is not described as RFC 8785/JCS.

`canonical_digest` on a memory record is SHA-256 over the canonical record after
removing only `canonical_digest`. `response_digest` follows the same rule for a
query response. Receipt digests cover the full receipt body before adding only
`receipt_digest`.

## Common Repository Identity

Every request and record contains:

```json
{
  "canonical_repository_id": "github:1257912727",
  "canonical_remote": "https://github.com/owner/repository",
  "repository_identity_digest": "<sha256-of-the-other-fields>",
  "principal_scope": {
    "tenant": "<sha256-or-not-applicable>",
    "workspace": "<sha256-or-not-applicable>",
    "user": "<sha256-or-not-applicable>"
  },
  "source_revision": {"kind": "git", "commit_sha": "<40-hex>", "branch": "<optional>"},
  "path_scope": ["."],
  "worktree_id_digest": "<sha256>"
}
```

The trusted caller derives this identity from current repository/Git/runtime
evidence. An adapter-returned label or directory basename is never sufficient.
Forks have distinct stable repository ids. A rename preserves a stable id while
the caller updates and rebinds the canonical remote. Path scope prevents
monorepo collisions; principal digests prevent cross-user/workspace/tenant reuse.

## Capability Handshake

`kind: capability-handshake` requires an adapter id/version,
supported schema versions, consistency and isolation semantics, every named
capability, observed time, and status. Each capability state is `supported`,
`unsupported`, or `unknown` with bounded semantics. Shared capabilities are:

`read_query`, `write_upsert`, `invalidate`, `tombstone`, `delete`, `namespaces`,
`repository_isolation`, `filters`, `pagination`, `ttl_retention`, `atomicity`,
`idempotency`, `provenance_preservation`, `sensitivity_handling`, and `audit`.

Handshake status distinguishes `ready`, `degraded`, `unavailable`, `disabled`,
`incompatible`, and `untrusted`. A capability is never silently simulated.
The handshake cannot self-declare trust or embed conformance evidence. The
current-session caller must separately map the adapter id to an accepted
conformance receipt digest and its exact adapter-version/capability fingerprint;
without that out-of-band mapping, or after adapter version/capability drift,
retrieval safely falls back to no memory. The caller also supplies
`max_handshake_age_seconds`, current time, clock availability, and maximum
future skew. A stale or future-skewed handshake, or an unavailable clock,
falls back to no memory.

## Query Request And Response

`kind: query-request` binds operation/request/idempotency ids, repository,
namespace, normalized repository-relative scope, record kinds, bounded limit,
required capabilities, and namespaced extensions.

`kind: query-response` binds the exact request ids and digest, adapter id,
status, records, partial flag, structured errors, replay nonce, response digest,
and extensions. Status distinguishes `ok`, `partial`, `unavailable`, `timeout`,
`unsupported`, `incompatible`, and `untrusted`.

## Memory Record

`kind: memory-record` requires:

- stable record id and kind;
- exact repository identity, namespace, bounded record path scope, and canonical digest;
- exactly one bounded inline `content` or digest-only `content_ref`;
- producer id/type/source-identity digest;
- provenance source references, an exact Git revision equal to the bound record
  repository revision, and evidence digests;
- at least one repository-artifact provenance reference inside the record
  scope, so an adapter cannot self-label unrelated content into a scoped query;
- created, observed, last-verified, expiry, TTL, and retention fields;
- sensitivity classification plus explicit credential/PII flags;
- literal `authority: advisory` and non-authoritative confidence;
- lifecycle state `active`, `superseded`, `tombstoned`, or `invalidated`, plus
  supersedes/invalidates ids and reason;
- opaque, non-dereferenceable backend locator;
- request/idempotency/sequence binding and required capabilities;
- bounded reverse-domain namespaced extensions.

Unknown shared fields fail closed. Extensions never gain shared semantics or
authority. Absolute paths, parent traversal, symlinks-as-identity, and local
file/HTTP locators are not accepted as shared content references.

Canonical JSON is UTF-8 with no BOM or insignificant whitespace. Object keys
must be printable ASCII and are sorted lexicographically; array order is
preserved; strings must contain valid Unicode scalar values and use standard
UTF-8 JSON encoding; lone surrogates are rejected. Booleans and null use
standard JSON encoding. JSON numbers
are limited to integers in the interoperable range
`[-9007199254740991, 9007199254740991]`; floating-point values are rejected and
decimal quantities must use a reviewed string or bounded integer unit. Record
`confidence` is an integer percentage from 0 through 100 and never carries
authority. These restrictions make the golden canonical bytes reproducible in
Python, JavaScript, and future adapters without relying on runtime-specific
float formatting.

## Retrieval Disposition

`kind: retrieval-decision-input` combines handshake, request, response, and
current authoritative context. Current context supplies bounded clock skew,
explicit maximum handshake age,
replay sets, source relations, and conflict evidence. Caller-trusted
adapter/conformance receipt digests and current repository-artifact source
digests are separate current-session input to the production function/CLI and
are not read from the adapter-controlled document.
An adapter cannot self-promote through its own handshake. `decide-retrieval`
validates in this order:

1. contract, adapter trust, handshake freshness, request/response binding,
   request and per-record capability requirements, and replay;
2. record digest, repository/principal/namespace/query-path identity, and the
   order-independent lifecycle graph, where only controllers with verified
   current repository provenance, exact revision relation, matching identity,
   and safe content can make tombstones/invalidations or superseders dominate
   targeted active records;
3. repository/user-instruction/memory conflicts, declared sensitivity,
   deterministic credential/PII indicators, and prompt injection;
4. source-revision relation, future timestamp/skew, TTL, and expiry freshness;
5. advisory adoption only when no reason remains.

Per-record outcomes are `adopt-as-context`, `reject`, or `quarantine`.
Disabled/unavailable/timeout/partial/unsupported/incompatible/untrusted states
set `fallback_to_no_memory`; V1/V2a continues without memory. A receipt always
sets mutation authorization, external-write authorization, gate satisfaction,
and completion proof to false.

## Write Eligibility

`kind: write-eligibility-input` is an offline candidate decision only. Eligibility
requires a durable lesson, verified root cause, digest-bound accepted
verification and review receipt documents, a separate current-session allowlist
of their receipt digests, exact receipt-to-record source revision binding,
candidate record digest binding,
complete accepted evidence digests,
authoritative source kinds, safe
sensitivity, active lifecycle, and no injection indicator. Chat summaries,
worker self-reports, memories, secrets, credentials, PII, guesses, unverified
root causes, and temporary incidents fail eligibility.

The receipt sets `candidate_only: true`, `write_performed: false`,
`external_write_authorized: false`, and `completion_proven: false`. V2b never
writes a backend.

`kind: mutation-candidate-request` defines future `upsert`, `invalidate`,
`tombstone`, and `delete` envelopes with repository/namespace/target,
operation/request/idempotency ids, eligibility receipt digest, and exact
required capability. It fixes `candidate_only` to true and both
`external_write_authorized` and `write_performed` to false. V2c must add current
out-of-band authority and adapter execution evidence; the V2b document cannot
grant either.

## Adapter Conformance

`kind: adapter-conformance-transcript` is an offline transcript of handshake
evidence and deterministic retrieval/write-decision cases. It does not contain
trusted repository source digests or accepted-receipt allowlists. The exact mandatory
case inventory (`retrieval-valid`, `retrieval-disabled`, `retrieval-partial`,
`retrieval-stale-handshake`, `retrieval-future-handshake`,
`retrieval-unknown-clock`, `retrieval-handshake-age-boundary`, `write-valid`,
and `write-sensitive`) and expected oracle are owned by the V2b production contract;
an adapter cannot omit cases or choose an empty expectation. `memoryctl.py
conformance` requires caller-captured repository source digests and accepted
receipt digests through separate required CLI inputs. The emitted receipt binds
canonical digests of both independent evidence sets. At retrieval time the trusted caller
must map the adapter id to that current receipt digest independently of the
adapter handshake. This one-way promotion is non-circular: the handshake is
untrusted input, the conformance output is computed afterward, and only that
output digest may be admitted by the caller for a later retrieval.
Test adapters belong under `tests/` only. Passing conformance does not install,
start, trust forever, or authorize an adapter; current runtime/repository
evidence is still required at use time.

The caller-owned CLI inputs use these exact JSON shapes:

- trusted conformance receipts:
  `{"<adapter-id>":{"receipt_digest":"<sha256>","adapter_fingerprint":"<sha256>"}}`;
- trusted repository sources:
  `{"<repository-relative-path>":"<sha256>"}`;
- trusted acceptance receipts: `{"receipt_digests":["<sha256>"]}`.

## Extension Policy

Extension keys use `reverse.domain/name`. At most 16 keys and 4096 canonical
bytes per structured value are accepted. Unknown top-level fields are rejected.
An extension cannot redefine identity, authority, permissions, lifecycle,
digest, capability, disposition, gate, or completion semantics.

## Operations Reserved For V2c

The v1 schema can describe write/upsert, invalidation, tombstone, deletion,
retention, consistency, and audit capabilities, but V2b implements only
validation, eligibility, disposition, receipt, and offline conformance. A future
V2c adapter must pass this contract before it may perform an operation.
