# Operational Evidence Program Continuation

## Current Release Gate

- Issues #107, #109, #111, #113, #115, #117, and #119 completed the v0.9.x
  alignment, guardrail, runtime-interface, CLI handoff, and Code Mode policy
  prerequisites.
- Issue #121 delivered V2d-A and v0.10.0. Issue #124 implements V2d-B and owns
  v0.11.0 version metadata, release notes, and release-readiness preparation on
  the same implementation branch.
- Commit, push, PR creation, merge, tag `v0.11.0`, and GitHub Release
  publication remain separately authorized actions against reviewed state.
- V2d-A evidence and V2d-B records/projections remain advisory and cannot
  authorize those actions or prove Issue #124 complete.

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

## Next Bounded Stage

After v0.11.0 is reviewed and released, run the private manual/CI proof of
concept outside this public repository. Public follow-up is limited to generic
contract fixes discovered by that PoC. V3-A must not begin until the program
re-entry gate passes.

## New Task Bootstrap Checklist

A future Codex task should:

1. Read `AGENTS.md`, `README.md`, `docs/roadmap.md`, this program directory,
   and `docs/operational-evidence-contract.md`.
2. Confirm Issue #124, its PR, tag `v0.11.0`, and the GitHub Release are in the
   expected accepted state.
3. Inspect current branch/status/upstream/diff, tags/releases, open issues, and
   the installed GitNexus index freshness.
4. Search GitHub for an existing private-PoC/public-fix issue. If none exists,
   stop and obtain exact external-write authorization before creating one.
5. Reassess private PoC sequencing and V2d-B contract lessons instead of
   trusting a chat summary.
6. Keep V2d-B separate from V3 self-improvement execution and runtime services.
7. Run GitNexus impact analysis before implementation and `detect_changes`
   before commit.
8. Stop at public-contract, privacy, authority, external-write, merge, tag, and
   release gates required by current policy.

## Handoff Summary

- Prerequisite slice: V2d-A Operational Evidence V0 core in v0.10.0.
- Delivered public slice: V2d-B improvement lineage and projection contracts.
- Next stage: private manual/CI proof of concept.
- Public role: contracts, validators, synthetic fixtures, tests, and docs.
- Private role: real operational records and the later manual/CI PoC.
- Projection role: tool-neutral first; Obsidian remains an optional reference.
- Graph role: typed projection only; no graph runtime or database.
- Automation role: manual/CI first; controller deferred.
- Candidate role: proposal-only until independent verification and promotion.
