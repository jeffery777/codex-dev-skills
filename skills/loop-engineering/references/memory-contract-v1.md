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

## Qualified GitNexus V2c-A Driver

The first concrete driver baseline is default-disabled and qualified only for
GitNexus `1.6.9`, metadata schema `5`, and a runtime-produced driver fingerprint.
Qualification requires an explicit absolute machine-local CLI path and never
falls back to ambient `PATH`; an env-node entry also requires an explicit Node
path. Before execution, caller-owned accepted digests must match the entry,
bound interpreter, and complete canonical package tree under an explicit
machine-local package root. Package symlinks must be relative, contained, and
target a directly descriptor-bound regular file; parent and target symlinks are
not followed. Caller-owned accepted digests come from separately trusted
installation evidence or an explicitly approved local measurement, not adapter
self-report. That runtime fingerprint binds CLI bytes, every qualified
script-interpreter byte identity, exact version, observed analyze flags,
metadata filenames/schema/capability policy, and separate
CLI/runtime symlink policies.
The separate qualification evidence-bundle digest binds captured package and
raw help/status/query observations. Any
version, bytes, flag, schema, or capability drift makes the driver incompatible
until it is qualified and conformed again.

The driver does not parse human `status` or `list` output. Although the qualified
CLI exposed a direct JSON query command, its volatile/degraded and
instruction-like output was not accepted as a stable record interface.
Consequently `read_query` is `unsupported` in V2c-A. `write_upsert`,
`invalidate`, `tombstone`, and `delete` are also `unsupported`; the driver emits
an unsupported disposition rather than a success receipt. Strict schema-5
metadata can establish local index identity and freshness, but cannot become a
memory payload, caller-owned trust evidence, or completion proof.

Derived-index refresh is outside the memory payload lifecycle. It requires an
explicit runtime opt-in and only a qualified `analyze --index-only` argv, exact
repository binding and verified commit-object HEAD, a clean direct worktree with no tracked path below
`.gitnexus/` or filesystem case/normalization alias of that root, pre-existing local exclude
guard, isolated alias and `GITNEXUS_HOME`, offline bounded environment,
a fixed descendant-Git `core.fsmonitor=false` override,
an identity/status boundary with a real local non-symlink `.git` marker and
reciprocal binding for linked worktrees that rejects enclosing-repository
`core.worktree` aliases and forged pointers; refresh additionally requires a
direct `.git` directory and rejects linked-worktree `.git` files,
replacement-object neutralization, isolated system/global Git configuration,
disabled hooks/fsmonitor/untracked-cache extensions, rejection of local and
enabled-worktree `filter.*`, include, and external-attributes selectors,
`GIT_NO_LAZY_FETCH=1`,
bounded probe output/time, timeout, and a mandatory deterministic fixed-OS-temp
per-user canonical-root lock before any optional instance lock. The lock is a
cooperative same-UID boundary, not distributed or hostile-process isolation.
The isolated home has its own device/inode-keyed cross-repository lock; its
verified directory descriptor stays open for the full refresh and emptiness is
rechecked under that lock immediately before execution.
Refresh also requires complete before/after repository,
worktree (including ignored content), and `.git` administrative-tree checks. A tracked alias that
is absent from the worktree is still rejected through conservative Unicode NFC
normalization and case-folded lexical comparison; filesystem identity checks
are defense in depth rather than the only alias control. Any
unexpected state fails closed without reset, restore, stash, stage, commit, or
automatic retry. Machine-local paths, registries, indexes, databases, and
credentials are never shared contract fields or repository artifacts.
The V2c-A complete-snapshot envelope is limited to 250,000 entries, depth 256,
512 MiB per regular file, and the configured total refresh deadline (120
seconds by default); any exceeded bound is unsupported and falls back to no
memory rather than producing a partial refresh.

The mandatory backend-neutral V2b oracle remains unchanged and is a regression
check, not GitNexus read/write authority. Adapter-specific tests prove
unsupported/no-memory behavior. V2c-A creates no trusted conformance receipt
that authorizes GitNexus query or mutation capabilities.

## Extension Policy

Extension keys use `reverse.domain/name`. At most 16 keys and 4096 canonical
bytes per structured value are accepted. Unknown top-level fields are rejected.
An extension cannot redefine identity, authority, permissions, lifecycle,
digest, capability, disposition, gate, or completion semantics.

## Operations Reserved For Later V2c Capabilities

The v1 schema can describe write/upsert, invalidation, tombstone, deletion,
retention, consistency, and audit capabilities, but V2b implements only
validation, eligibility, disposition, receipt, and offline conformance. V2c-A
does not implement those backend mutations. Any later V2c adapter capability
must pass this contract and obtain separate current operation authority before
it may perform an operation.
