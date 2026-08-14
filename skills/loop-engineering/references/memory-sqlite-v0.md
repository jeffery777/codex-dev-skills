# Memory M1 SQLite/FTS5 Reference `loop-memory-sqlite/v0`

Use this reference only with the explicit `scripts/sqlitectl.py` entrypoint.
The adapter is default-disabled and local/manual/CI-only. Released memory-off,
V2b, V2d, V3, and M0 modules do not import it.

## Authority And Placement

Every execute route first reconstructs the complete
`loop-memory-operation/v0` request with caller-owned authority, eligibility,
and trusted-time acceptance inputs. It then requires an exact live
adapter/schema/capability fingerprint and an approved state-root identity.
Database rows and adapter output cannot self-authorize.

State routes require explicit absolute `--state-root` and
`--repository-root` paths. They must be disjoint. The pre-existing state root
and database must be current-user-owned, non-symlink, regular where applicable,
single-linked, and non-group/world-accessible. Machine-local paths and database
material never enter public receipts or Git.

## Capability Probe

`probe` uses a fresh isolated temporary database. It disables extension
loading; verifies exact FTS5 `unicode61 remove_diacritics 2` token and `AND`
behavior; and fingerprints SQLite version/source/build options, Python sqlite
API, OS/architecture, fixed schema, adapter policy, bounds, and observed
behavior. Drift fails closed. There is no `LIKE`, tokenizer, vector, or other
query fallback.

## Fixed Schema

Schema version 1 contains exact `metadata`, `records`, `records_fts`, and
`operations` objects plus one fixed lookup index. Every DDL statement and
`user_version` value participates in the schema fingerprint. Initialization
creates only an absent database inside an approved pre-existing root. Missing,
unknown, partial, or drifted schema rejects: no migration and no repair.

## Structured Query

The adapter consumes a released V2b query request plus exactly one namespaced
extension:

```json
{
  "dev.jeffery.memory-sqlite/query": {
    "match": "all",
    "terms": ["bounded", "tokens"]
  }
}
```

Terms are a sorted unique list of 1–16 ASCII word tokens. Raw SQL, FTS
expressions/operators, tokenizer selection, DDL, pragmas, ordering, and
extension loading are not accepted. The adapter owns a fixed quoted `AND`
compiler, binds every caller value as a SQL parameter, applies exact
repository/principal/namespace/revision/path predicates, and orders by `bm25`,
record id, then digest. Returned bytes must pass the released V2b response
validator.

## Atomic Operation

`upsert`, `invalidate`, `tombstone`, and logical `delete` are the only
operations. First apply stores logical state and the original canonical M0
execution receipt in one transaction. Exact idempotent replay returns a new
receipt bound to the stored original without a second mutation. Conflict,
timeout, lock, disk, integrity, schema, fingerprint, transaction, and commit
uncertainty cannot claim success. Logical delete retains canonical record and
operation bytes but removes the record from active retrieval. Physical purge
is unsupported.

## CLI

```bash
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py probe
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py initialize \
  --state-root /approved/local/root --repository-root /current/repository
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py query \
  <query-request.json> --state-root /approved/local/root \
  --repository-root /current/repository
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py execute \
  <authority.json> <mutation-candidate.json> <eligibility-receipt.json> \
  --accepted-authority-receipts <accepted-authority.json> \
  --accepted-eligibility-receipts <accepted-eligibility.json> \
  --trusted-time <trusted-time.json> \
  --accepted-trusted-time-receipts <accepted-time.json> \
  --state-root /approved/local/root --repository-root /current/repository
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py receipt \
  <authority.json> <mutation-candidate.json> <eligibility-receipt.json> \
  --accepted-authority-receipts <accepted-authority.json> \
  --accepted-eligibility-receipts <accepted-eligibility.json> \
  --trusted-time <trusted-time.json> \
  --accepted-trusted-time-receipts <accepted-time.json> \
  --state-root /approved/local/root --repository-root /current/repository
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py integrity \
  --state-root /approved/local/root --repository-root /current/repository
./scripts/project-python <installed-loop-engineering>/scripts/sqlitectl.py \
  qualification-receipt <qualification-input.json> <safety-observation.json> \
  <execution-evidence.json>...
```

There is no install, enable, service, network, provider/MCP, automatic recall/
write, raw database console, migration, repair, purge, promotion, or release
route.

## Qualification And Privacy

Only already validated public/internal inline V2b records may be stored.
Credentials, PII, private paths, raw chats/sessions/logs, confidential or
restricted data, and unredacted machine configuration reject generically.
No encryption or shared-host confidentiality claim is made.

The qualification-receipt helper binds an exact M0 qualification input, live
adapter tuple, zero-failure safety observation, and supplied execution-evidence
bundles. Each bundle reconstructs the complete M0 authority/eligibility/
trusted-time request and validates an applied receipt against the live adapter
and platform before its digest can enter qualification. Caller acceptance
remains separate. Passing proves safety/conformance only; efficacy and the
independent human/platform promotion gate remain unresolved. Target release is
**TBD / human decision**.
