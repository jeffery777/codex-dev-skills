# Issue #147 Memory M1 Architecture Decisions

## M1-001 — Add One Separate Reference Adapter

Keep released V2b/V2d/V3/M0 modules unchanged. Add
`loop-memory-sqlite/v0` as a replaceable reference implementation, not a new
authority layer.

## M1-002 — Require Explicit Default-Disabled Entry

Only explicit local/manual/CI CLI routes may import or invoke the adapter.
Memory-off receives no adapter input and remains zero-touch.

## M1-003 — Qualify Behavior, Not A Version String

Probe FTS5 in a fresh temporary database and bind observed query/tokenizer
behavior, SQLite source/build/options, schema policy, Python API, OS, and
architecture into the capability fingerprint. Drift requires requalification.

## M1-004 — Fix The Query Grammar

Accept structured tokens only through one namespaced V2b extension. Compile a
fixed quoted `AND` query and parameterize all caller values. Raw SQL, raw FTS,
operators, tokenizer selection, DDL, pragmas, and extension loading are absent.

## M1-005 — Use One Exact Schema Without Migration

Schema version 1 and every DDL byte are fingerprinted. Initialize only an
absent database in an approved pre-existing root. Mismatch fails closed; there
is no automatic migration, repair, purge, backup, or restore.

## M1-006 — Bind Scope At Storage And Query Boundaries

Persist the exact V2b repository/principal/namespace/revision/path scope key
and require it in every record, query, lifecycle transition, and receipt
lookup. A shared or multi-tenant database claim is not made.

## M1-007 — Reconstruct M0 Authority Before State Access

Use `memory_operation.build_authorized_request` with the complete caller-owned
authority, eligibility, and trusted-time chain before opening the adopted
database. Adapter/database content cannot self-authorize.

## M1-008 — Commit State And Applied Receipt Together

Store logical state and the canonical original M0 applied receipt in one
transaction. Exact replay is read-only and binds the original receipt;
conflicting replay and uncertainty cannot become success.

## M1-009 — Keep Delete Logical

Delete removes a record from active retrieval while retaining canonical bytes
and operation history. Physical purge stays unsupported and human-gated.

## M1-010 — Qualify Only Safety And Conformance

Produce an M0-compatible M1 qualification receipt only for the exact tested
tuple and observed safety outcomes. Do not claim efficacy, activation,
promotion, or release readiness.

## M1-011 — Keep Release Selection Human-Owned

The maintainer selected **v0.14.0** after the implementation review. Passing
tests, evals, or qualification did not select the version and still cannot
install, enable, publish, or promote the adapter by itself.
