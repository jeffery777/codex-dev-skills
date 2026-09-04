# Memory M1 SQLite/FTS5 Reference Adapter Contract

`loop-memory-sqlite/v0` is the default-disabled local/manual/CI-only Memory M1
reference adapter. It is downstream of unchanged V2b, V3-B, and Memory M0
contracts and qualifies only one exact adapter/schema/capability/platform
tuple.

## Default-Off Boundary

No released module imports this adapter on memory-off. The only entrypoint is
the explicit `sqlitectl.py` CLI or a direct trusted library call. There is no
ambient discovery, home/config lookup, service, daemon, scheduler, hook,
provider/MCP, network, or automatic recall/write path.

## Probe And Fingerprints

Every state adoption behavior-probes FTS5 in a fresh temporary database,
disables extension loading, and verifies fixed `unicode61 remove_diacritics 2`
token behavior. The capability fingerprint binds SQLite version/source/build
options, Python sqlite API, tokenizer behavior, fixed limits, schema,
adapter version, OS, and architecture. Any missing capability or drift fails
closed with no alternate query implementation.

## Exact Schema V1

The schema fingerprint covers these exact semantic objects:

- `metadata(key, value)` with exact adapter/schema/capability/platform values;
- `records` with scope digest/JSON, record id/digest/kind, lifecycle state,
  sequence, inline content, canonical record JSON, and unique scope/id;
- `records_fts` as FTS5 content with the fixed tokenizer;
- `operations` with scope/idempotency primary key, exact request/operation/
  target binding, and original canonical receipt JSON/digest;
- `records_scope_lookup` over scope/path/lifecycle/kind/id/digest;
- `PRAGMA user_version=1`.

Initialization is allowed only when the database is absent inside an approved
pre-existing root. Existing schema must match exactly and pass bounded
`quick_check`. No migration, repair, purge, backup, restore, or vacuum route is
present.

## Placement And Isolation

State and repository roots are explicit absolute and disjoint. The state root
and database must be current-user-owned, non-symlink, restrictively
permissioned, and type/link-count safe. The M0 authority binds the state-root
identity digest. Every query, operation, and receipt lookup binds exact V2b
repository/principal/namespace/revision/path scope. A shared/multi-tenant or
cross-host database is not qualified.

## Query Contract

Search input is exactly the structured namespaced extension documented in the
portable reference. Terms are bounded word tokens; `match` is fixed to `all`.
The adapter owns the quoted `AND` FTS expression, uses parameterized SQL for
all caller values, and returns deterministic `bm25`, record-id, digest order.
Raw SQL, raw FTS expressions, operators, tokenizer/column/order selection,
DDL, pragmas, and extension loading reject.

## M0 Execution Contract

Before opening state, execution rebuilds the M0 authorized request from the
exact caller-owned authority, eligibility, and trusted-time chain. The live
adapter/schema/capability and state-root identity must match.

Applied state plus the original M0 execution receipt commit in one SQLite
transaction. Exact replay performs no mutation and binds the stored applied
receipt. Conflicting replay and every uncertain failure cannot claim success.
Invalidate, tombstone, and delete remove active FTS retrieval but retain
record/history bytes. Delete is logical; physical purge is unsupported.
Receipt recovery reconstructs and validates the same complete M0 authority,
eligibility, trusted-time, adapter, state-root, and expected-pre-state chain;
repository identity plus an idempotency key alone cannot read a receipt.

## Bounds, Privacy, And Qualification

Query tokens, input bytes, result count, record bytes, database size, busy
time, operation time, and integrity work are bounded. Named transaction faults
exist only as direct test hooks and are not exposed by the production CLI.

Only public/internal synthetic or caller-validated records are eligible.
Secrets, credentials, PII, private paths, raw chats/sessions/transcripts/logs,
confidential/restricted data, and unredacted machine configuration reject
without echo. Database/WAL/journal/locks and real records remain machine-local
and outside public Git. No encryption/shared-host confidentiality claim is
made.

Qualification produces only an M0-compatible candidate receipt for the exact
tuple and zero-failure safety observation. Every referenced execution digest
comes from an exact evidence bundle whose complete M0 authority, eligibility,
trusted-time, authorized request, applied receipt, live adapter, and platform
bindings are revalidated. The current caller must accept it separately. It
cannot prove efficacy, completion, review, promotion, merge, deploy,
activation, or another external write. The exact reviewed default-disabled
reference baseline is released in **v0.14.0**; release does not qualify other
platform tuples or authorize activation.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_sqlite tests.test_sqlitectl tests.test_eval_memory_sqlite \
  tests.test_memory_sqlite_contract_docs
./scripts/project-python scripts/eval-memory-sqlite.py
```

## Thin Local Pilot Façade

The v0.23.0 `memory-m1-local-pilot/v1` façade is an explicit caller library,
not a replacement adapter. It accepts one trimmed line of at most 512 UTF-8
bytes and, before an M1 open/write, applies the existing V2b sensitivity rules
plus lexical rejection for chat/log markers, secrets, credentials, PII,
private or absolute paths, and configuration assignments. This is a narrow
machine-checkable input boundary, not a general DLP guarantee. Its four profile
labels do not alter this schema, record kinds, fingerprints, or M0 authority semantics.
For remember/recall the exact profile/class is stored in canonical
`dev.jeffery.memory-pilot/profile` record extensions, binding it to the record
digest and M0 chain. Invalidate carries no class assertion; it is only the M0
exact-target logical transition.
V2b evaluates the complete bounded M1 result before the façade selects adopted
digests for the requested class, preserving cross-class lifecycle dominance.
Selected records are exposed only as an advisory projection of canonical
digest, pilot class, one-line content, and source references; no authority or
completion field is projected.
