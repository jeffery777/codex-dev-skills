# Issue #145 Task Packet

## Scope

This packet owns one M0-only additive delivery on
`codex/145-memory-m0-readiness`, based on
`47d1178a8fcabaa5ca23af15e615aa0eaf9d7257`. It stops before commit.

## Tasks

| Task | Deliverable | Completion evidence |
| --- | --- | --- |
| T1 bootstrap | Git/GitHub/Release/contracts/Python/GitNexus facts | spec and gate receipt |
| T2 design | spec, ADR, threat model, plan, packet | formal plan gate |
| T3 operation family | caller-owned time, full-chain validator, offline CLI | focused adversarial tests/eval |
| T4 qualification family | paired V3-B safety wrapper and zero-touch off mode | focused tests/eval |
| T5 public integration | references/docs/package/validator alignment | repo validation |
| T6 closure | full verification, impact/diff, deep/docs/security review | commit-readiness receipt |

## Definition Of Done

- [x] Additive families preserve all released upstream semantics.
- [x] Caller-owned authority, eligibility, and trusted-time acceptance are
      separate inputs; requests and receipts reconstruct the full chain.
- [x] Applied/replay/failure receipt semantics are exact and non-authoritative.
- [x] Logical delete is supported; physical purge is absent.
- [x] Memory-off is complete, default, and zero backend/filesystem touch.
- [x] Paired qualification binds verifier assignment and a scope-bound M1
      receipt, is safety/conformance-only, and cannot claim efficacy/promotion.
- [x] Public/internal-only privacy, placement, schema-drift, no-migration,
      concurrency, and recovery boundaries are tested.
- [x] New and existing focused/full tests/evals pass.
- [x] Deep code/docs/security/privacy and formal readiness review have no
      unresolved blocker.
- [x] No SQLite/FTS5/backend/persistence/provider/MCP/automation/private-data/
      release-target change enters the diff.
- [x] No commit, push, PR, review/comment, merge, release, deploy, install,
      activation, or promotion occurs.

## Stop Conditions

Stop on any spec/authority/delete/privacy/qualification ambiguity, scope
expansion, destructive behavior, backend/runtime implementation, efficacy
claim, source-of-truth conflict, failed high-risk verification, unresolved
review blocker, or unauthorized external action.
