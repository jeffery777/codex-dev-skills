# Operational Evidence And Self-Improvement Program

Status: Phase 0 changes from Issues #107 and #109 are merged; v0.9.1 release
closure is tracked in Issue #111; V2d implementation has not started.

## Purpose

This directory is the durable handoff for development after the v0.9.1
alignment release. It records why Operational Evidence V0 must precede
Evidence-Driven Self-Improvement, which public/private boundaries must remain
intact, and how the work is divided into independently reviewable stages.

The next feature milestone is:

> **Loop Engineering V2d: Operational Evidence Contract V0**

The proposed repository release for that milestone is v0.10.0. The later
milestone name **Loop Engineering V3-A: Evidence-Driven Self-Improvement**
remains reserved.

## Current Baseline

- V1 provides the production workflow and authority core.
- V2a provides capability routing and route/worker/integration receipts.
- V2b provides a backend-neutral external-memory safety contract.
- V2c-A provides a qualified, default-disabled GitNexus adapter/controller
  boundary.
- V2c-B provides optional, trusted lifecycle freshness hooks.
- Issue #109 adds an exact index-only GitNexus repository default and
  trusted-base, read-only ready-PR Issue-linkage guardrail. These controls are
  repository hygiene and traceability evidence, not completion or merge
  authority.
- The repository does not yet define a general run receipt, failure taxonomy,
  redacted environment fingerprint, typed artifact-reference set, or
  improvement lineage contract.

Existing ledgers, route receipts, worker receipts, memory receipts, GitNexus
qualification fingerprints, and iteration reports are useful inputs, but none
of them independently supplies the missing cross-run operational evidence
model.

## Accepted Dependency Order

1. v0.9.1 alignment, live notify-only hook adoption, repository guardrails,
   and release closure.
2. V2d-A — Operational Evidence V0 core contracts.
3. V2d-B — Projection boundary and improvement lineage.
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
