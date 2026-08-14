# Release Notes: v0.14.0

Release date: 2026-08-14

v0.14.0 publishes the Memory M0 authority/qualification boundary from Issue
#145 / PR #146 and the default-disabled SQLite/FTS5 Memory M1 reference adapter
from Issue #147 / PR #148. This is a safety/conformance release; it makes no
efficacy or activation claim.

## Memory M0 Authority And Qualification

- Added `loop-memory-operation/v0` caller-owned exact operation authority,
  authorized-request composition, and atomic execution-receipt contracts.
- Added `loop-memory-qualification/v0` safety/conformance-only paired
  memory-off/on qualification while preserving the complete zero-touch
  memory-off path.
- Preserved the released V2b, V2d, V3-A, and V3-B authority, completion, and
  promotion boundaries.

## Memory M1 SQLite/FTS5 Reference Adapter

- Added the replaceable `loop-memory-sqlite/v0` adapter and explicit
  local/manual/CI-only CLI routes.
- Kept the adapter default-disabled and required an explicitly approved,
  machine-local state root outside the repository.
- Added an isolated temporary-database FTS5 behavior probe plus exact SQLite
  build, tokenizer, platform, schema, adapter, and capability fingerprints.
- Accepted only strict bounded structured queries compiled to parameterized
  SQL; raw SQL, raw FTS expressions, caller-selected tokenizers, pragmas, DDL,
  and extension loading remain unavailable.
- Enforced repository, principal, namespace, revision, and path isolation;
  exact-match schema; no automatic migration or repair; scope-bound
  idempotency; logical lifecycle operations; and atomic state plus receipt.
- Added bounded lock, timeout, result, transaction, and database limits with
  synthetic fault/rollback and recovery cases.

## Privacy, Data Placement, And Boundaries

- Public fixtures contain only synthetic public/internal non-sensitive data.
- Secrets, credentials, PII, raw logs/chats/sessions, private paths, and real
  records remain excluded.
- The release makes no encryption-at-rest, shared-host confidentiality,
  multi-tenant, cross-host, physical-purge, or physical-durability claim.
- Provider/MCP adapters, PlugMem/Mem0, network services, daemons, schedulers,
  hooks, automatic recall/write, efficacy evaluation, activation, promotion,
  and V3-C remain outside this release.

## Qualification

- The deterministic M1 eval covers 18 safety/conformance cases and emits zero
  efficacy claims.
- The reviewed candidate passed focused M1 tests, full repository discovery,
  repository validation, deep code/documentation review, exact-head GitNexus
  impact analysis, and Codex Security diff scans with no unresolved findings.
- Qualification binds only the observed Python 3.12.9, PyYAML 6.0.3, SQLite
  3.51.0, Darwin arm64, schema, tokenizer, and adapter tuple. Other platforms
  remain unqualified follow-up work.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/project-python scripts/eval-memory-operation.py
./scripts/project-python scripts/eval-memory-qualification.py
./scripts/project-python scripts/eval-memory-sqlite.py
./scripts/validate-repo.sh
./install.sh manifest
git diff --check
```

The annotated `v0.14.0` tag is bound to the exact reviewed PR #148 merge
commit. A GitHub Release is not published by this delivery because that
separate platform write was not authorized.

## Rollback

Review `./install.sh diff --all` before reinstalling. Rolling back to v0.13.0
removes the public Memory M0/M1 contracts, adapter, CLI, tests, evals, and docs.
It does not delete or rewrite machine-local SQLite state, installed runtime
state, Git/platform state, or external systems. Memory remains default-off.

## Traceability

- Memory M0 issue: <https://github.com/jeffery777/codex-dev-skills/issues/145>
- Memory M0 pull request: <https://github.com/jeffery777/codex-dev-skills/pull/146>
- Memory M1 issue: <https://github.com/jeffery777/codex-dev-skills/issues/147>
- Memory M1 pull request: <https://github.com/jeffery777/codex-dev-skills/pull/148>
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.13.0...v0.14.0>
