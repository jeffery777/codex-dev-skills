# Operational Evidence Program Continuation

## Current Release Gate

- Issues #107, #109, #111, #113, #115, #117, and #119 completed the v0.9.x
  alignment, guardrail, runtime-interface, CLI handoff, and Code Mode policy
  prerequisites.
- Issue #121 delivered V2d-A in v0.10.0. Issue #124 and PR #126 delivered
  V2d-B in v0.11.0; Issue #127 owns the final release closure.
- Annotated tag `v0.11.0` and the GitHub Release are bound to the reviewed
  release-closure merge commit.
- V2d-A evidence and V2d-B records/projections remain advisory. Issue #124
  completion and release publication depend on accepted repository/platform
  state, not on those records or projections.
- The private manual/CI qualification satisfied the ten V3-A re-entry
  conditions without placing private identities or records in public Git.
- Issue #133 and PR #134 delivered and merged V3-A proposal-only output. Issue
  #137 publishes that baseline as v0.12.0 through a separately reviewed release
  merge, annotated tag, and GitHub Release. Draft-PR, eval, CI, score,
  validation, merge, tag, and Release state remain non-authoritative for later
  activation or promotion actions.
- Issue #135 owns a docs-only V3-B re-entry and Agent Memory roadmap. It does
  not perform release closure, implement V3-B, complete M0 qualification, or
  implement/enable M1, M2, or V3-C.
- Issue #141 owns the bounded V3-B `loop-candidate-evaluation/v0` candidate.
  Its memory-off default, optional V2b-validated advisory context, deterministic
  verifier, and non-promotional packet do not implement or enable M1 or V3-C.
- Issue #143 publishes the reviewed Issue #141 / PR #142 V3-B baseline as
  v0.13.0 through a separate exact merge/tag/GitHub Release gate.

## Delivered V2d-A Boundary

Issue #121 adds:

- the versioned `loop-operational-evidence/v0` envelope;
- run receipt and machine-readable iteration summary;
- failure summary with bounded category/code taxonomy;
- redacted environment fingerprint;
- typed artifact-reference set;
- exact false-authority invariants;
- public data-placement and redaction rules;
- strict offline document and bundle validation;
- positive, tamper, duplicate-key, unknown-field, synthetic-secret,
  standalone-token, private-path, raw-log, invalid-reference,
  duplicate-document-id, and cross-record-mismatch fixtures/tests;
- relationship rules for ledgers, events, route/worker/integration/memory
  receipts, verification/review artifacts, Git commits/platform artifacts, and
  GitNexus fingerprints.

It does not add improvement records, projections, private PoC data, automatic
collection, hooks, plugins, schedulers, controllers, databases, graph
execution, or automatic promotion.

## Delivered V2d-B Boundary

Issue #124 adds:

- strict composed improvement-record and projection families;
- baseline/candidate and predecessor lineage;
- declared proposer/evaluator/verifier/promoter separation;
- deterministic Markdown and typed graph manifests;
- an optional dependency-free Obsidian reference profile;
- strict validators, bounded CLI, synthetic fixtures, tests, and evals.

It excludes production Obsidian synchronization, private evidence stores,
graph databases/execution, schedulers, controllers, and promotion.

## Delivered V3-A Boundary

Issue #133 adds strict deterministic evidence-to-proposal generation and
validation, fixed scores, stable ties/deduplication, complete V2d-A/B source
lineage, bounded hypothesis/output enums, proposal-only invariants, a pending
independent promotion gate, synthetic adversarial evals, and a stdout-only CLI.
It excludes external memory, candidate execution, runtime automation, and
promotion.

## Released V3-B Boundary

Issue #141 / PR #142 implement and qualify V3-B isolated baseline/candidate
synthetic evaluation using the Issue #135 brief; Issue #143 publishes that
reviewed baseline as v0.13.0.
Do not infer V3-B authority from V3-A output. Require same-policy comparison,
independent deterministic replay verification, privacy/security review, and a promotion
packet that still cannot promote itself. V3-B may add only a provider-neutral,
optional V2b-validated context seam with memory-off as the default; it must not
embed SQLite or implement M1.

After v0.13.0 publication and Memory M0 were verified, Issue #147 separately
authorized the bounded implementation and safety/conformance qualification of
the default-disabled local/manual/CI-only SQLite/FTS5 M1 reference adapter. M0
readiness defines the gap matrix, provider-neutral protocol,
operation authority, atomic execution receipt, lifecycle/concurrency, threat
model, and memory-off/on evaluation design but is not completed by Issue #135.
Issue #145 owns the intervening M0-only offline qualification candidate. It
keeps V2b/V3-B unchanged, treats delete as logical, proves zero-touch
memory-off, and limits paired qualification to safety/conformance. It does not
implement or authorize SQLite/FTS5 M1 by itself. Issue #147 remains a
candidate, not acceptance, activation, promotion, efficacy, or release
evidence.
M2 requires successful M1 qualification. V3-C automatic recall/write,
persistent service, scheduler/controller, queue, or cross-host automation
requires another human gate. Later release targets remain TBD.

## Next Task Bootstrap Checklist

An Issue #147 M1 delivery or continuation task should:

1. Read `AGENTS.md`, `README.md`, `docs/roadmap.md`, this program directory,
   and `docs/operational-evidence-contract.md`.
2. Confirm Issue #141, merged PR #142, Issue #143, and the current v0.13.0
   tag/Release state from current platform evidence.
3. Inspect current branch/status/upstream/diff, tags/releases, open issues, and
   the installed GitNexus index freshness.
4. Verify Issue #141 / PR #142 and Issue #143 exact release evidence rather
   than trusting a chat summary, packet, or proposal score.
5. Treat memory-off as the accepted V3-B default and verify Issue #147's exact
   bounded Issue/spec/ADR/security scope before any M1 implementation.
6. Keep V3-A proposal, V3-B evaluation, M1 backend qualification, and V3-C
   services separate.
7. Run GitNexus impact analysis before implementation and `detect_changes`
   before commit.
8. Stop at public-contract, privacy, authority, external-write, merge, tag, and
   release gates required by current policy.
9. Read Issue #135 and `docs/loops/issue-135/roadmap-spec.md`; keep V3-B, M0,
   M1, M2, and V3-C claims and deliveries separate.

## Handoff Summary

- Prerequisite slice: V2d-A Operational Evidence V0 core in v0.10.0.
- Delivered public slice: V3-A manual/CI evidence-to-proposal contract.
- Released candidate: Issue #141 / PR #142 V3-B isolated candidate evaluation
  in v0.13.0 through Issue #143.
- Next stage after verified v0.13.0 publication and Issue #145 M0: Issue #147
  bounded M1 reference-adapter implementation and safety/conformance
  qualification. This document does not accept, activate, promote, or release
  M1.
- Release interlock: Issue #143 separately closes the v0.13.0 annotated-tag and
  GitHub Release gate; future work must still verify current platform evidence.
- Memory role: M0 readiness design first; M1 only after V3-B evidence; M2 only
  after M1 qualification. External memory remains optional context/cache.
- Public role: contracts, validators, synthetic fixtures, tests, and docs.
- Private role: real operational records and the later manual/CI PoC.
- Projection role: tool-neutral first; Obsidian remains an optional reference.
- Graph role: typed projection only; no graph runtime or database.
- Automation role: manual/CI first; controller deferred.
- Candidate role: V3-A remains proposal-only; V3-B must independently evaluate
  synthetic observations and replay-verify before a separate human/platform
  promotion decision.
