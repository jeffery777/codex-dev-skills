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
- Issue #133 and PR #134 delivered and merged V3-A proposal-only output.
  Draft-PR, eval, CI, score, validation, and merge state remain
  non-authoritative for later actions; v0.12.0 tag, GitHub Release, activation,
  and promotion are separate human gates. The latest published release remains
  v0.11.1 until current platform evidence proves otherwise.
- Issue #135 owns a docs-only V3-B re-entry and Agent Memory roadmap. It does
  not perform release closure, implement V3-B, complete M0 qualification, or
  implement/enable M1, M2, or V3-C.

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

## Next Bounded Stage

After v0.12.0 is separately tagged and released, reassess V3-B isolated
baseline/candidate execution as a new Issue/spec using the Issue #135 brief.
Do not infer V3-B authority from V3-A output. Require same-policy comparison,
independent execution verification, privacy/security review, and a promotion
packet that still cannot promote itself. V3-B may add only a provider-neutral,
optional V2b-validated context seam with memory-off as the default; it must not
embed SQLite or implement M1.

After V3-B evidence passes, a separate Issue/spec/ADR/security review may
qualify the default-disabled local/manual/CI-only SQLite/FTS5 M1 reference
adapter. M0 readiness defines the gap matrix, provider-neutral protocol,
operation authority, atomic execution receipt, lifecycle/concurrency, threat
model, and memory-off/on evaluation design but is not completed by Issue #135.
M2 requires successful M1 qualification. V3-C automatic recall/write,
persistent service, scheduler/controller, queue, or cross-host automation
requires another human gate. Later release targets remain TBD.

## New Task Bootstrap Checklist

A future Codex task should:

1. Read `AGENTS.md`, `README.md`, `docs/roadmap.md`, this program directory,
   and `docs/operational-evidence-contract.md`.
2. Confirm Issue #133, merged PR #134, exact-head CI/reviews, and any later
   v0.12.0 tag/Release state from current platform evidence.
3. Inspect current branch/status/upstream/diff, tags/releases, open issues, and
   the installed GitNexus index freshness.
4. Search GitHub for an existing V3-B issue or collision. If none exists,
   stop and obtain exact external-write authorization before creating one.
5. Reassess V3-A evidence and V3-B authority/privacy boundaries instead of
   trusting a chat summary or proposal score.
6. Keep V3-A proposal output separate from V3-B execution and V3-C services.
7. Run GitNexus impact analysis before implementation and `detect_changes`
   before commit.
8. Stop at public-contract, privacy, authority, external-write, merge, tag, and
   release gates required by current policy.
9. Read Issue #135 and `docs/loops/issue-135/roadmap-spec.md`; keep V3-B, M0,
   M1, M2, and V3-C claims and deliveries separate.

## Handoff Summary

- Prerequisite slice: V2d-A Operational Evidence V0 core in v0.10.0.
- Delivered public slice: V3-A manual/CI evidence-to-proposal contract.
- Next stage: separately gated V3-B isolated candidate evaluation.
- Release interlock: v0.12.0 tag and GitHub Release must be separately closed
  before V3-B implementation.
- Memory role: M0 readiness design first; M1 only after V3-B evidence; M2 only
  after M1 qualification. External memory remains optional context/cache.
- Public role: contracts, validators, synthetic fixtures, tests, and docs.
- Private role: real operational records and the later manual/CI PoC.
- Projection role: tool-neutral first; Obsidian remains an optional reference.
- Graph role: typed projection only; no graph runtime or database.
- Automation role: manual/CI first; controller deferred.
- Candidate role: V3-A remains proposal-only; V3-B must independently execute
  and verify before a separate human/platform promotion decision.
