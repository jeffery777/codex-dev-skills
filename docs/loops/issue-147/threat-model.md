# Issue #147 Memory M1 Threat Model

## Overview

The repository ships public workflow contracts and local developer tooling.
Issue #147 adds one opt-in SQLite/FTS5 reference adapter that may read and
mutate an explicitly approved machine-local database only during manual or CI
invocation. Its outputs remain advisory/non-authoritative.

## Threat Model, Trust Boundaries, And Assumptions

Assets are repository/principal/namespace/revision/path isolation, caller-owned
operation authority, public/internal record confidentiality, logical state,
idempotency, atomic receipts, qualification integrity, and the user's unrelated
filesystem/repository state.

Trust boundaries:

- current caller/control-plane accepted authority, eligibility, trusted-time,
  state-root, and qualification digests are trusted only for their exact scope;
- every JSON document, V2b record, adapter result, database row, SQLite error,
  and receipt is untrusted data;
- the explicit approved state root is a cooperative current-user boundary, not
  protection from a hostile same-UID process;
- SQLite/Python/platform behavior is untrusted until the isolated behavior
  probe and exact fingerprints match;
- public Git contains code/contracts/synthetic fixtures only; real state stays
  outside Git.

Security invariants:

- adapter/database data cannot issue or broaden authority;
- every state read/write binds exact repository/principal/namespace/revision/
  path identity;
- caller query data never becomes SQL/FTS syntax;
- extension loading stays disabled;
- schema mismatch never triggers migration or repair;
- one idempotency binding causes at most one applied transition;
- applied state and original success receipt commit atomically;
- uncertainty never becomes success;
- logical delete never becomes physical purge;
- rejected private/sensitive content is not stored or echoed;
- no output proves completion, gate satisfaction, promotion, or permission to
  act.

## Attack Surface, Mitigations, And Attacker Stories

### Authority laundering

An attacker supplies a self-issued authority or database row that appears
approved. The adapter reconstructs the complete M0 request using caller-owned
accepted sets before opening state and matches live adapter/state-root
fingerprints exactly.

### SQL, FTS, pragma, or extension injection

An attacker supplies quotes/operators/SQL/FTS syntax. Only bounded word tokens
are accepted; the compiler owns the fixed quoted `AND` expression and all SQL
values are parameters. Callers cannot select SQL, columns, order, tokenizer,
DDL, pragmas, or extensions. Extension loading is explicitly disabled.

### Cross-scope disclosure or mutation

A valid-looking request is replayed across repository, principal, workspace,
namespace, revision, or path. Exact canonical scope keys are stored and
predicated on every query/operation/receipt lookup. Failures are generic and
do not disclose whether another scope contains data.

### Replay and double application

An attacker reuses an idempotency key with changed scope/request. The unique
scope/key row binds the exact request digest. Exact replay returns the original
result without mutation; conflicts fail.

### Crash-window receipt forgery

State or receipt might commit alone. The adapter uses one explicit transaction
for state and original applied receipt and synthetic named fault points prove
rollback before commit. Busy, disk, integrity, transaction, and commit
uncertainty cannot report applied.

### Schema, tokenizer, or runtime drift

An old qualification is reused after SQLite/platform drift. Every invocation
re-probes behavior and compares exact schema/platform/capability metadata.
Mismatch fails closed with no alternate query or migration.

### Unsafe placement and symlink substitution

An attacker redirects the database into the repository or another file. State
and repository roots must be absolute/disjoint; path components, state root,
and database are checked for owner, mode, link count, type, and symlinks before
use. Python `sqlite3` still opens by pathname, so this is cooperative same-user
protection, not hostile same-UID race isolation.

### Sensitive-data capture and error echo

Accidental records contain credentials, PII, private paths, raw logs, or
confidential material. Released V2b validation plus M1 public/internal policy
rejects before storage. Errors use bounded generic codes/messages.

### Resource exhaustion and corruption

Large queries/databases or corrupt state cause unbounded work or partial
answers. Input, tokens, results, database size, busy time, operation time, and
transactions are bounded; exact schema and `quick_check` fail closed; no repair
or partial adoption occurs.

### Qualification laundering

A passing receipt is replayed for a changed adapter/schema/platform or claimed
as efficacy/promotion. M0 validation binds the exact common V3-B tuple,
fingerprints, safety observation, and execution receipts; current caller must
accept it independently; efficacy and promotion fields remain false/pending.

## Severity Calibration (Critical, High, Medium, Low)

- **Critical:** adapter/database self-authorization enabling cross-scope
  mutation, or public Git storage of real credentials/private records.
- **High:** cross-principal disclosure, SQL/FTS injection, double application,
  forged atomic success, destructive purge, or qualification granting
  activation/promotion.
- **Medium:** schema/runtime drift accepted without requalification, unsafe
  permissions, private content echoed, or resource bounds allowing reliable
  local denial of service.
- **Low:** deterministic metadata inconsistency that fails closed, exposes no
  content, and performs no state action.

Out of scope: hostile same-UID interference, physical device compromise,
shared-host confidentiality, encryption at rest, cross-host replication,
network/provider attacks, automatic services, and efficacy observations.

Repository: sha256:a409ff64b9cef22b1ad14b6a00659e99606a3702f40f6e5eb81e4ae4da887bbd
Version: 89a284c9b44fe762afcfcf0d79d79ee701eade69
