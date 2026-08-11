# Issue #135 Task Packet

## Scope

This packet governs one docs-only planning delivery on
`codex/135-v3b-memory-roadmap`. It may update only the Issue #135 documentation
surface listed in `implementation-plan.md` and may prepare review/verification
receipts. It may not implement or enable V3-B, M0, M1, M2, or V3-C behavior.

## Tasks

| Task | Deliverable | Completion evidence |
| --- | --- | --- |
| T1 baseline and impact | Current Git/GitHub/Release/GitNexus/V2b evidence recorded without private state | Roadmap spec and verification receipt |
| T2 roadmap spec | M0/M1/M2 definitions, gap matrix, provider-neutral protocol, threat model, V3-B seam, next Issue brief | Docs review |
| T3 program alignment | Roadmap, program README/phases/continuation, and architecture decisions agree | Link/text checks and docs review |
| T4 memory boundary | README and external-memory docs preserve no-backend and context-only authority | V2b regression tests/eval |
| T5 readiness | Complete verification, deep review, formal gate, exact-head CI, and draft PR | Bound receipts and platform evidence |

## Definition Of Done

- [ ] Every changed file is documentation and belongs to Issue #135.
- [ ] The sequence is v0.12.0 release closure, V3-B, M1, then V3-C.
- [ ] M0 is defined as readiness design/qualification and is not claimed
      complete.
- [ ] M1 is default-disabled, local/manual/CI-only, deterministic, thin, and
      SQLite/FTS5-specific only as a later reference candidate.
- [ ] FTS5 is capability-probed and fails closed; no substitute query path is
      silently simulated.
- [ ] Repository/principal/namespace/path isolation, digest eligibility,
      idempotency, atomic execution receipts, lifecycle, recovery, security,
      and privacy requirements are explicit.
- [ ] M2 and V3-C remain behind later evidence and human gates.
- [ ] V3-B's optional context seam is provider-neutral and memory-off by
      default; it does not embed M1 or weaken V2b.
- [ ] Repo-owned source/ledger authority, context-only external memory,
      operation authority, acceptance, and promotion boundaries remain strict.
- [ ] PlugMem and Mem0 remain excluded and disabled.
- [ ] No private data, secret, machine-local state, or unapproved target
      release appears.
- [ ] No claim says v0.12.0, V3-B, M0 qualification, M1, M2, or V3-C is
      completed by this Issue.
- [ ] Local validation, reviews, formal gates, hosted exact-head CI, and draft
      state checks pass with no unresolved MUST-FIX finding.

## Scenario Matrix

| Scenario | Pass condition |
| --- | --- |
| Unreleased v0.12.0 | V3-B implementation remains a later gated Issue |
| No backend | Existing workflow remains fully usable and no capability is simulated |
| V3-B context omitted | Exact memory-off default |
| V3-B context invalid | Fail closed to memory-off with unchanged authority/thresholds |
| FTS5 missing or changed | Future M1 unavailable; requalification required |
| Wrong identity/scope | Future query and operation reject without disclosure |
| Replay/concurrent writer | At most one applied transition and one bound original result |
| Crash/timeout/disk/lock failure | No partial-success claim |
| Lifecycle conflict or purge | Deterministic state rule; exact destructive authority required |
| Sensitive/private content | Generic rejection; no storage or echo |
| M1 evidence missing | M2 and memory-dependent V3-C remain blocked |
| Runtime/test edit required now | Stop without scope expansion |

## Stop Conditions

- non-docs changes become necessary;
- authoritative sources conflict;
- V2b/public-contract/data-model semantics must change;
- operation authority, privacy, isolation, destructive lifecycle, or acceptance
  rules remain ambiguous;
- a backend, provider, database, MCP server, hook, scheduler, queue, controller,
  service, automatic recall/write, or cross-host action would be implemented;
- exact-head validation or hosted CI fails without a docs-only fix;
- the next action is ready-for-review, merge, tag, GitHub Release, deploy,
  activation, or promotion.

## Final Boundary

Draft-PR readiness is the terminal state for this Issue. A draft PR does not
release v0.12.0, implement V3-B, qualify M0, implement or enable Agent Memory,
integrate PlugMem/Mem0, authorize V3-C, or grant merge authority.
