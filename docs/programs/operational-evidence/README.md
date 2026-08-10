# Operational Evidence And Self-Improvement Program

Status: V2d-A is released in v0.10.0; V2d-B is released in v0.11.0; V3-A
proposal-only evidence-to-proposal is in v0.12.0 preparation through Issue
#133.

## Purpose

This directory is the durable handoff for development after the v0.9.x
maintenance releases. It records why Operational Evidence V0 must precede
Evidence-Driven Self-Improvement, which public/private boundaries must remain
intact, and how the work is divided into independently reviewable stages.

The current development feature milestone is:

> **Loop Engineering V3-A: Manual/CI Evidence-To-Proposal**

V3-A is limited to deterministic proposal generation. V3-B candidate execution
and V3-C automation remain deferred.

## Current Baseline

- V1 provides the production workflow and authority core.
- V2a provides capability routing and route/worker/integration receipts.
- V2b provides a backend-neutral external-memory safety contract.
- V2c-A provides a qualified, default-disabled GitNexus adapter/controller
  boundary.
- V2c-B provides optional, trusted lifecycle freshness hooks.
- V2d-A provides the strict offline `loop-operational-evidence/v0` document
  family, bounded failure taxonomy, redacted environment allowlist, typed
  artifact references, relationship validation, synthetic fixtures, and
  deterministic evals.
- V2d-B provides separate strict `loop-improvement-lineage/v0` and
  `loop-evidence-projection/v0` families, declared role separation,
  baseline/candidate lineage, deterministic Markdown/typed-graph projection,
  and an optional declarative Obsidian reference profile.
- V3-A provides strict `loop-improvement-proposal/v0` proposal sets,
  deterministic integer scoring, stable ties and duplicate suppression,
  complete validated lineage, bounded hypothesis/output enums, and a
  stdout-only manual/CI CLI. It cannot execute or promote a candidate.
- Issue #109 adds an exact index-only GitNexus repository default and
  trusted-base, read-only ready-PR Issue-linkage guardrail. These controls are
  repository hygiene and traceability evidence, not completion or merge
  authority.
- The repository does not store real operational/improvement/proposal records
  or the private proof-of-concept evidence.

Existing ledgers, route receipts, worker receipts, memory receipts, GitNexus
qualification fingerprints, and iteration reports are useful inputs, but none
of them independently supplies the missing cross-run operational evidence
model.

## Accepted Dependency Order

1. v0.9.1 alignment, live notify-only hook adoption, repository guardrails,
   release closure, and the v0.9.2 runtime-compatibility maintenance release.
2. V2d-A — Operational Evidence V0 core contracts (Issue #121, v0.10.0).
3. V2d-B — Projection boundary and improvement lineage (Issue #124, v0.11.0).
4. Private manual/CI proof of concept against the public contracts.
5. V3-A — Manual/CI evidence-to-proposal workflow.
6. V3-B — Isolated candidate evaluation workflow.
7. V3-C — Optional resident hooks/controller, only if operational evidence
   proves it is needed and the authority/control prerequisites exist.

See [implementation-phases.md](implementation-phases.md) for deliverables and
entry/exit criteria.

## Non-Negotiable Boundaries

- Operational evidence and human-readable projections are not completion
  authority.
- Repository data cannot provide protected authorization for itself.
- The public repository stores contracts, validators, fixtures, tests, and
  non-sensitive examples, not private operational records.
- Credentials, secret values, raw large logs, transcripts, private paths,
  local databases, and unredacted machine configuration do not enter Git.
- A private controller or platform may depend on this public repository; this
  repository must not depend on that private implementation.
- Candidate improvement may produce only a proposal, patch, branch, artifact,
  or draft PR until independent verification and human/platform promotion.
- Existing human gates, sandbox limits, review requirements, external-write
  policy, and completion evidence remain unchanged.

## Document Map

- [architecture-decisions.md](architecture-decisions.md) — accepted decisions
  and their consequences.
- [implementation-phases.md](implementation-phases.md) — staged delivery,
  original V3-A mapping, deferred work, and acceptance gates.
- [continuation.md](continuation.md) — next bounded issue and a new-task
  bootstrap checklist.
- [../../operational-evidence-contract.md](../../operational-evidence-contract.md)
  — implemented V2d-A public contract, authority/data-placement matrix,
  redaction policy, CLI, and verification.
- [../../improvement-lineage-contract.md](../../improvement-lineage-contract.md)
  — implemented V2d-B lineage, role, human projection, graph projection,
  optional Obsidian profile, CLI, and verification.
- [../../improvement-proposal-contract.md](../../improvement-proposal-contract.md)
  — implemented V3-A scoring, dedupe, lineage, proposal-only, CLI, privacy,
  and verification contract.

## Research Input Disposition

The research input with the working filename `deep-research-report (6).md` was
reviewed but is not tracked verbatim. It contains useful analysis, but its
embedded `turn...` citations are session-local and not resolvable by future
maintainers, and it mixes repository facts with inference and preliminary
scope.

Its accepted conclusions are superseded by the canonical documents in this
directory and by the Issue #107 planning records. The raw report remains
non-authoritative research context; future work should cite repository files,
tests, validators, current official runtime documentation, and accepted GitHub
state instead.
