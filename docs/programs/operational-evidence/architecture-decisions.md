# Operational Evidence Architecture Decisions

These decisions were accepted before starting V2d. They preserve the V1/V2
authority model while making later self-improvement and graph projection
possible.

## OE-001 — Keep `codex-dev-skills` Public And Contract-First

**Decision:** Keep public skills, workflow contracts, schemas, validators,
fixtures, tests, and non-sensitive examples in this repository. Keep real
private operational records outside it.

**Consequence:** The public repository remains independently useful with no
private platform and cannot become a dump of runtime state.

## OE-002 — Insert V2d Before V3-A

**Decision:** Add Operational Evidence Contract V0 as a prerequisite milestone;
do not replace V3-A and do not hide the work inside V3-A.

**Rationale:** Both Self-Improvement and Graph Engineering need the same
evidence primitives. A separate milestone exposes that dependency and allows
the contracts to be validated before candidate generation begins.

## OE-003 — Evidence And Projection Are Non-Authoritative

**Decision:** A run receipt, iteration summary, failure summary, environment
fingerprint, artifact reference, improvement record, graph projection, or
Obsidian projection is advisory unless an existing completion or protected
action contract independently accepts a referenced artifact.

**Consequence:** No record may set or imply:

- `used_as_authorization: true`
- `used_as_completion_evidence: true`
- `external_write_authorized: true`
- `promotion_authorized: true`

The V2d validators must reject self-authorization claims.

## OE-004 — Use A Tool-Neutral Projection Boundary

**Decision:** Define a human-readable projection contract first. Obsidian may
be documented as one reference profile, but the core contract must not depend
on Obsidian or a vault implementation.

**Consequence:** Obsidian is suitable for project/knowledge views, summaries,
links, and annotations. It is not a runtime authority, lock/lease/fencing
store, queue, scheduler, credential store, raw-log store, or completion
authority.

## OE-005 — Defer Runtime Services And Databases

**Decision:** Do not add PostgreSQL, graph databases, vector databases,
schedulers, daemons, or background controllers in V2d.

**Rationale:** The immediate uncertainty is schema, redaction, taxonomy,
lineage, and evaluation—not storage throughput or distributed coordination.

**Promotion trigger:** Reconsider a service only after a private PoC shows
concrete query, concurrency, retention, or cross-host requirements that files
and ordinary artifact storage cannot satisfy.

## OE-006 — Start With Manual Or CI Batch Execution

**Decision:** Initial self-improvement execution is manual or CI batch. It may
produce evidence and proposals but cannot promote candidates.

**Promotion trigger:** Consider a controller only after stable contracts,
repeated successful PoCs, an operational failure taxonomy, proposer/promoter
separation, and a real shared coordination requirement exist.

## OE-007 — Start Graph Engineering With A Typed Projection

**Decision:** The first graph deliverable is a typed projection manifest
derived from validated loop/task/evidence inputs.

**Consequence:** V2d may define node/edge types and a deterministic projection,
but it does not add a graph database or graph execution engine.

## OE-008 — Separate Candidate Production From Promotion

**Decision:** Candidate improvement can create a proposal, patch, branch,
artifact, or draft PR. It cannot approve, activate, merge, release, or deploy
itself.

**Consequence:** Baseline/candidate evaluation and independent verification are
required before a separate human or authoritative platform promotion decision.

## OE-009 — Private Implementations Depend On Public Contracts

**Decision:** The only allowed dependency direction is:

```text
private controller or companion platform
        depends on
codex-dev-skills public contracts
```

The public repository must not import, call, or require a private controller to
validate, test, install, or operate its public workflows.

## OE-010 — Treat The v0.9.1 Hook Run As Pilot Evidence

**Decision:** The v0.9.1 notify-only adoption report is a historical,
human-readable pilot receipt. It informs V2d field design but does not become
the operational-evidence schema by precedent.

**Consequence:** V2d must still define strict, versioned schemas and validators
instead of normalizing an ad hoc runtime report.
