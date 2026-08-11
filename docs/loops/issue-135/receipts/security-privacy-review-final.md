# Issue #135 Deep Authority, Security, And Privacy Review

## Executive Summary

This review treated the roadmap as a future data/authority boundary rather
than as ordinary prose. The final diff keeps memory context-only, preserves the
V2b no-backend default, separates eligibility/authority/execution/acceptance/
promotion, and places every backend or automation step behind later evidence
and human gates.

Final review result: no unresolved MUST-FIX or SHOULD-FIX finding.

## Findings And Dispositions

### SEC-135-001 — SHOULD-FIX — Fixed

The first threat model omitted direct SQL/FTS construction and resource-abuse
risks.

Disposition: **Fixed**. M1 now requires behavior-based FTS5 qualification,
parameterized SQL, no raw caller SQL/FTS expression, disabled extension
loading, deterministic tokenizer/build fingerprinting, resource bounds,
integrity checks, and fail-closed requalification.

### PRIV-135-001 — SHOULD-FIX — Fixed

Initial placement text said machine-local but did not explicitly state the CI
artifact default or future permission boundary.

Disposition: **Fixed**. The spec now requires a current-user-owned
non-symlink location with future reviewed directory/file permissions and makes
CI databases ephemeral and non-uploaded by default.

### SEC-135-002 — NIT — Deferred

Standard SQLite does not itself establish encrypted-at-rest or hostile
same-user isolation.

Disposition: **Deferred**.

- Durable target: the separately approved future Memory M1 Issue/spec/ADR and
  security review.
- Owner: future M1 delivery owner and independent security reviewer.
- Reason: M1 currently excludes confidential/restricted content, secrets,
  credentials, PII, raw logs, shared-host multi-tenancy, and cross-host use.
- Remaining risk: theft by a principal already able to read the approved local
  runtime directory is not solved by this roadmap.
- Verification plan: exact placement/permission tests, negative cross-scope
  access tests, threat-model review, and explicit qualification failure if the
  host confidentiality assumption is not met.
- Promotion trigger: any request to store confidential/restricted material,
  share a database across principals/hosts, or claim stronger at-rest
  confidentiality.

### AUTH-135-001 — NIT — Fixed

An execution receipt could be mistaken for authorization or completion if its
role were not explicit.

Disposition: **Fixed**. Architecture and contract docs now require separate
caller-owned operation authority, atomic adapter execution evidence, independent
acceptance, and a still-pending promotion gate. Execution receipts remain
non-authoritative audit/context evidence.

## Deep Risk Notes

- V3-B changes no memory backend and defaults to memory-off.
- M1 is single-host local/manual/CI only and has no daemon, network listener,
  MCP server, scheduler, controller, or automatic recall/write path.
- FTS5 unavailability or fingerprint drift disables memory-on rather than
  selecting another query engine.
- Identity, idempotency, concurrency, crash, lifecycle, purge, corruption,
  query injection, resource exhaustion, and privacy failure cases are explicit
  future qualification requirements.
- Physical deletion remains destructive and separately authorized; expiry
  alone cannot authorize purge.
- PlugMem and Mem0 remain excluded and disabled.

## Re-Runnable Checks

```bash
rg -n 'api[_-]?key|access[_-]?token|BEGIN .*PRIVATE|hostname|username' \
  README.md docs/roadmap.md docs/external-memory-contract.md \
  docs/programs/operational-evidence docs/loops/issue-135
python3 scripts/eval-memory-contract.py
./scripts/validate-repo.sh
git diff --check
```
