# Issue #147 Loop Spec — Memory M1 SQLite/FTS5 Reference Adapter

## Status And Objective

Issue #147 implements one additive, default-disabled, local/manual/CI-only
SQLite/FTS5 reference adapter downstream of the released Memory M0 contracts.
It qualifies safety and conformance for one exact adapter, schema, capability,
and platform tuple. It does not enable memory or change any
V1/V2/V3/M0 authority or completion contract.

Target release: **v0.14.0**, selected by the maintainer after the initial
implementation review. Release does not authorize activation or efficacy.

## Sources Of Truth

- GitHub Issue #147;
- `AGENTS.md`, `SECURITY.md`, `README.md`, `docs/roadmap.md`, and
  `docs/release-readiness.md`;
- `docs/loops/issue-135/roadmap-spec.md` and `docs/loops/issue-145/*`;
- the Operational Evidence program and OE-013 through OE-015;
- released V2b, V2d-A/B, V3-A/B, Memory M0 contracts, production validators,
  tests, and evals;
- this Issue-owned spec, ADR, threat model, plan, task packet, and receipts.
- `follow-ups.md` for non-blocking deferred risks and promotion triggers.

Current repository/Git, caller-owned accepted evidence, verification, review,
and accepted platform state remain authoritative. Adapter output, database
content, fingerprints, receipts, qualification results, scores, and evals are
context/evidence only.

## Entry Facts, Inference, And Unverified Claims

Verified facts:

- accepted base and `origin/main` are
  `89a284c9b44fe762afcfcf0d79d79ee701eade69`;
- Issue #145 is closed and PR #146 is merged at that commit;
- there were no open Issue/PR collisions before Issue #147 was created;
- the tracked resolver selects Python 3.12.9 and PyYAML 6.0.3;
- at task entry, the latest tag/Release was `v0.13.0`; the later maintainer
  decision selected v0.14.0 for the reviewed M1 baseline;
- the GitNexus saved-project `main` index is 15 commits stale and no exact-head
  index is accepted or rebuilt;
- production M0 validates authority, requests, receipts, and qualification
  wrappers but contains no backend executor.

Accepted inference: an additive Python standard-library reference module can
qualify SQLite/FTS5 only after an isolated temporary-database behavior probe
and exact fingerprint binding.

Unverified until qualification runs: host SQLite source/build/options,
tokenizer behavior, platform/filesystem behavior, lock/timeout/fault behavior,
and conformance of the exact runtime tuple. Efficacy, encryption, shared-host
confidentiality, physical purge, and cross-host behavior remain unverified and
out of scope.

## Additive Public Boundary

The new `loop-memory-sqlite/v0` family is implemented by a separate adapter
module and explicit CLI. It does not alter `loop-memory/v1`,
`loop-memory-operation/v0`, `loop-memory-qualification/v0`, V2d-A/B, V3-A, or
V3-B.

The adapter is inert until one explicit CLI route is invoked. Memory-off does
not import or call the adapter and receives no state root, database path,
backend handle, or provider configuration.

## Capability Qualification

Every adopted invocation first performs a behavior probe in a fresh isolated
temporary database. The probe:

- disables extension loading;
- creates the exact FTS5 virtual-table shape with the fixed `unicode61`
  tokenizer policy;
- inserts synthetic terms and proves fixed phrase/token behavior and stable
  ordering;
- captures SQLite version/source id/compile options, Python sqlite API version,
  tokenizer policy, adapter/schema policy, OS, and architecture;
- emits schema, platform, and capability fingerprints from canonical public
  fields only.

Missing FTS5, changed behavior, a different tokenizer/build/platform/schema,
or extension-loading uncertainty fails closed. There is no fallback to
`LIKE`, another tokenizer, a vector index, or an alternate query engine.

## Placement Boundary

State routes require two explicit absolute paths: an approved state root and
the repository root. They must be disjoint. The state root must already exist,
be current-user-owned, non-symlink, and non-group/world-accessible. Every path
component is resolved and rechecked before use. The database must be a
current-user-owned regular non-symlink file with one link and restrictive
permissions. These path and metadata checks do not claim protection against a
hostile same-UID process racing pathname access.

The M0 state-root identity digest binds canonical path identity, device,
inode, owner, and mode without publishing the path. Database, WAL/journal,
locks, temporary files, backups, and real records stay machine-local and are
never repository artifacts.

## Fixed Schema

Schema version 1 is exact and fingerprinted. It contains:

- `metadata` for exact adapter/schema/capability/platform bindings;
- `records` for canonical V2b record bytes, scope keys, digest, lifecycle
  state, and deterministic sequence;
- `records_fts` for fixed FTS5 indexing of active inline content;
- `operations` for exact request/idempotency bindings and the original applied
  M0 execution receipt.

Every table, column, constraint, index, virtual-table definition, and
`user_version` value participates in the schema fingerprint. Existing missing,
unknown, drifted, or partial schema fails closed. Initialization is allowed
only for a pre-approved root with no database and performs no migration.
Automatic migration, repair, vacuum/purge, backup, and restore are absent.

## Structured Query

The adapter consumes a validated V2b `query-request`. Search input exists only
in the namespaced `dev.jeffery.memory-sqlite/query` extension with exact fields:

- a sorted unique non-empty list of 1–16 ASCII word tokens, each at most 64
  characters;
- fixed `match: all` semantics.

Callers cannot supply SQL, FTS expressions, operators, columns, tokenizer,
DDL, pragmas, ordering, or pagination cursors. The adapter compiles tokens to
one fixed quoted `AND` expression, uses bound SQL parameters for every caller
value, applies exact repository/principal/namespace/revision/path predicates,
and orders by `bm25`, record id, then record digest. Returned bytes must pass
the released V2b query-response validator.

## Authorized Operations And Atomic Receipts

`execute` receives the exact authority, mutation candidate, eligibility
receipt, accepted authority/eligibility/trusted-time sets, trusted-time receipt,
and expected pre-state. It reconstructs the M0 authorized request through the
released production function before opening the database.

The request's adapter/schema/capability and state-root identity must match the
live qualified tuple. Only `upsert`, `invalidate`, `tombstone`, and logical
`delete` are supported. Upsert stores one already validated public/internal
V2b record. Other operations retain bytes/history and remove the record from
active retrieval. Physical purge is unsupported.

One scope-bound idempotency key maps to one exact request digest. First apply
updates logical state and inserts the canonical M0 `applied` receipt in the
same SQLite transaction. Exact replay returns a canonical M0
`idempotent-replay` receipt bound to the stored original without another state
change. Conflicting replay and every lock, timeout, disk/resource, integrity,
schema, fingerprint, transaction, or commit uncertainty return failure or a
generic rejection and never claim success.

## Bounds And Recovery

- input JSON: released strict 131072-byte bound;
- query tokens: 16; result limit: released maximum 100;
- database size: 64 MiB qualification envelope checked before adoption and
  inside each mutation transaction before receipt/commit;
- busy timeout: fixed 1000 ms; operation deadline: 5000 ms;
- record content and total canonical record bytes: released V2b bounds;
- integrity: exact schema plus bounded `quick_check` before state use.

Recovery can return a verified stored original applied receipt only after
reconstructing the complete M0 authority, eligibility, trusted-time, adapter,
state-root, and expected-pre-state chain. It cannot synthesize success,
migrate/repair, discard history, purge, or promote. Named
fault injection is test-only and covers pre-state, before-receipt, and
pre-commit failures; production CLI exposes no fault option.

## Privacy And Authority

Only validated public/internal records are accepted. Secrets, credentials,
PII, private paths, raw chats/sessions/transcripts/logs, confidential/restricted
data, and unredacted machine configuration reject before storage with generic
non-echoing errors. No encryption or shared-host confidentiality claim is made.

Every output keeps M0/V2b false-authority invariants. Qualification can report
only safety/conformance and a pending independent human/platform gate. It
cannot authorize completion, review, acceptance, promotion, merge, release,
deploy, activation, install, or another external write.

## Acceptance Matrix

| Scenario | Required result |
| --- | --- |
| memory-off | complete deterministic result; zero adapter/filesystem touch |
| FTS5 missing/drifted | unavailable/fail closed; no fallback query |
| extension loading | disabled and not caller configurable |
| schema missing/drifted | reject; no migration or repair |
| raw SQL/FTS/operator input | reject before database query |
| wrong repo/principal/namespace/revision/path | empty/reject without disclosure |
| missing/untrusted/expired authority | reject before database open |
| applied operation | one atomic logical-state plus receipt transaction |
| exact replay | bound replay receipt; no second mutation |
| conflicting replay | failed/rejected; no mutation |
| lifecycle operation | deterministic state; retained bytes; no retrieval |
| physical purge | unsupported |
| lock/timeout/fault/integrity uncertainty | failed; no success claim |
| unsafe root/file permissions or symlink | reject before state adoption |
| sensitive/private record | generic reject; no storage or echo |
| qualification | exact tuple, zero safety failures, human gate pending |
| efficacy or release claim | stop at human gate |

## Definition Of Done

- Issue-owned spec/ADR/threat model/plan/task packet are exact and reviewed.
- Public reference, fixed schema, API/CLI, adapter, synthetic fixtures, tests,
  and deterministic eval cover the acceptance matrix.
- Qualification revalidates complete M0 execution-evidence bundles; a
  standalone or resealed receipt digest cannot enter the passing tuple.
- Released V2b/V2d/V3/M0 semantics remain unchanged and regressions pass.
- Packaging, repository validator, and public docs are aligned without install
  or activation.
- Full verification, static impact evidence, deep quality/security/privacy
  review, and formal commit-readiness evidence have no unresolved MUST-FIX.
- Work stops before commit for exact human authorization.
- After the maintainer's 2026-08-14 authorization, commit and push are allowed
  only if final code review and security diff scan report no findings; PR,
  release selection, merge, tag, Release, install, activation, promotion, and
  deploy remain separate human gates.

## Out Of Scope And Stop Conditions

Provider/MCP, PlugMem/Mem0, network/service/daemon/scheduler/hook/queue,
automatic recall/write, cross-host, hostile same-UID isolation, V3-C, physical
purge, migration/repair, backup/restore, shared/multi-tenant database,
encryption claims, confidential/restricted/real/private records, efficacy,
release selection, install/activation/promotion, PR/merge/tag/Release/deploy
are out of scope. Deferred risks and their re-entry triggers are recorded in
`follow-ups.md`; that ledger does not authorize follow-up implementation.

Stop for ambiguity in public contract, authority, privacy/data model, purge,
efficacy, shared tenancy, encryption, cross-host behavior, or scope.
