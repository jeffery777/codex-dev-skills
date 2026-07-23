# Operational Evidence Program Continuation

## Release Closure Gate

- Issue #107 and PR #108 completed the v0.9.1 alignment and notify-only pilot.
- Issue #109 and PR #110 completed the repository guardrails.
- Issue #111 owns only version alignment, release readiness, post-bootstrap
  linkage evidence, and the formal v0.9.1 release closure.
- Merge of the Issue #111 PR closes the repository change, but tag creation
  and GitHub Release publication remain a separate human gate.
- Open the V2d-A implementation Issue only after v0.9.1 is tagged and released.

## Next Bounded Issue

After v0.9.1 is merged and released, open:

> **Define `loop-operational-evidence/v0` core contracts and fail-closed
> validators**

### Scope

- versioned operational-evidence envelope;
- run receipt;
- iteration summary;
- failure summary and bounded taxonomy;
- redacted environment fingerprint;
- artifact reference set;
- authority/data-placement matrix;
- redaction policy;
- strict validator;
- synthetic fixtures and tests;
- integration rules for existing ledger, route, worker, memory, verification,
  review, and GitNexus references.

### Required Invariants

Every validated document must preserve:

```text
used_as_authorization: false
used_as_completion_evidence: false
external_write_authorized: false
promotion_authorized: false
```

The validator must reject unknown or duplicate fields, self-authorization,
unbounded free text where a bounded field is required, credential/secret
patterns, private absolute paths, raw large logs, unsupported environment
details, broken digests, and cross-record identity or lineage mismatches.

### Out Of Scope

- improvement record;
- Obsidian renderer or sync;
- graph projection manifest;
- private PoC data;
- hooks, plugins, schedulers, controllers, databases, graph runtime;
- proposal generation or automatic promotion.

### Definition Of Done

- contracts are versioned, strict, documented, and independently usable;
- non-sensitive examples validate;
- negative and tamper fixtures fail closed;
- relationships to existing receipts and authority are explicit;
- repository validation and focused evals pass;
- docs, code, security/privacy, and formal readiness reviews have no unresolved
  MUST-FIX findings.

## New Task Bootstrap Checklist

A future Codex task should:

1. Read `AGENTS.md`, `README.md`, `docs/roadmap.md`, and this directory.
2. Confirm Issues #107, #109, and #111 are closed and v0.9.1 is tagged and
   released.
3. Inspect current Git status, branch, upstream, and installed GitNexus index
   freshness.
4. Search GitHub for an existing V2d-A issue before creating one.
5. Create the Issue before the implementation branch.
6. Reassess repository facts instead of trusting chat summaries.
7. Keep the first issue limited to V2d-A core contracts.
8. Run GitNexus impact analysis before changing any implementation symbol and
   `detect_changes` before commit.
9. Stop at public-contract, privacy, authorization, publication, merge, tag,
   and release gates required by current policy.

## Handoff Summary

- Accepted target: V2d Operational Evidence Contract V0 before V3-A.
- Required predecessor: finish Issue #111, publish v0.9.1 through the separate
  release gate, then open the V2d-A Issue.
- Next implementation slice: V2d-A core contracts and validators.
- Public repo role: contracts and synthetic evidence only.
- Private role: real operational records and later PoC execution.
- Projection role: tool-neutral first; Obsidian is a reference view only.
- Graph role: typed projection first; no graph runtime or database.
- Automation role: manual/CI first; controller deferred.
- Candidate role: proposal-only until independent verification and promotion.
