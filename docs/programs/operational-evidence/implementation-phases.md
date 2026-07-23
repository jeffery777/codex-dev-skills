# Operational Evidence Program Phases

## Phase 0 — v0.9.1 Alignment, Guardrails, And Pilot Adoption

**Purpose:** Close README drift and obtain one real notify-only hook observation
before designing the evidence contracts.

**Deliverables:**

- README and roadmap alignment;
- v0.9.1 release notes;
- untracked machine-local hook adoption;
- sanitized, non-authoritative live evidence;
- exact index-only GitNexus repository defaults;
- trusted-base, read-only ready-PR Issue-linkage validation;
- version, release-readiness, and post-bootstrap CI evidence;
- this durable program plan.

**Exit criteria:** Issue #107 and Issue #109 DoD pass through PRs #108 and
#110; the Issue #111 verification, formal documentation/release-readiness
gates, and post-bootstrap PR-linkage check pass; and v0.9.1 is formally tagged
and released. No Operational Evidence schema is implemented in this phase.

## Phase 1 — V2d-A Operational Evidence V0 Core

**Target release:** v0.10.0

**Deliverables:**

- `loop-operational-evidence/v0` envelope and versioning rules;
- `run-receipt` contract;
- machine-readable `iteration-summary` contract;
- `failure-summary` contract and bounded failure taxonomy;
- redacted `environment-fingerprint` contract;
- typed `artifact-reference-set` contract;
- authority/data-placement matrix;
- redaction policy;
- strict offline validators;
- positive, negative, tamper, duplicate-key, unknown-field, secret, private-path,
  and raw-log fixtures/tests;
- relationship rules for existing ledger, route, worker, integration, memory,
  verification, and review artifacts.

**Explicit exclusions:**

- improvement records;
- Obsidian rendering or synchronization;
- graph projection manifests;
- private PoC data;
- hooks, plugins, controllers, schedulers, databases, and automatic promotion.

## Phase 2 — V2d-B Projection And Improvement Lineage

**Deliverables:**

- `improvement-record` contract;
- baseline/candidate lineage;
- proposer, evaluator, independent verifier, and promoter role separation;
- tool-neutral human-readable projection manifest;
- optional Obsidian reference profile;
- minimum typed graph projection manifest;
- deterministic projection fixtures and validators.

**Explicit exclusions:**

- production Obsidian sync;
- private evidence store implementation;
- graph execution engine or graph database;
- automatic candidate promotion.

## Phase 3 — Private Manual/CI Proof Of Concept

This phase occurs outside the public repository except for public bug fixes or
contract revisions discovered by the PoC.

**Required scenarios:**

- successful run;
- verification failure;
- review or human-gate stop;
- environment difference;
- baseline/candidate comparison;
- artifact-reference resolution;
- failure taxonomy classification;
- deterministic lineage reconstruction;
- projection regeneration from validated records.

**Public repository rule:** Commit only generic contracts, validators, tests,
and synthetic examples. Do not commit the private records produced by the PoC.

## Phase 4 — V3-A Manual/CI Evidence-To-Proposal

**Retained work from the original V3-A direction:**

- deterministic candidate scoring and duplicate suppression;
- proposal and hypothesis generation;
- use of the existing eval harness as one evaluation input;
- adversarial fixtures for false-complete, wrong-route, unauthorized-action,
  evidence-completeness, recovery, and semantic-equivalence behavior;
- proposal, patch, branch, artifact, or draft-PR output;
- explicit human/platform promotion gate.

**New prerequisite:** Every proposal must link validated source run/failure
records, environment fingerprint, artifact references, baseline evidence, and
an improvement record.

## Phase 5 — V3-B Isolated Candidate Evaluation

**Deliverables:**

- isolated baseline and candidate execution;
- same-policy comparison;
- environment-difference handling;
- independent verification result;
- regression and authority-invariant checks;
- promotion packet preparation without promotion.

## Phase 6 — V3-C Optional Resident Automation

This phase is not automatically approved by completing earlier phases.

**Deferred work:**

- SessionStart/Stop resident self-improvement hooks;
- plugin bootstrap;
- scheduler or background controller;
- shared queue;
- persistent database services;
- cross-host execution;
- automatic retry orchestration;
- graph execution engine;
- automatic promotion.

**Entry criteria:** At least two material operational needs—such as repeated
batch demand, multiple queued objectives, shared atomic claim/lease
coordination, cross-host execution, or a demonstrated human bottleneck—must
exist. Security/privacy review and a new architecture decision are required.

## Original V3-A Work Mapping

| Original work area | Revised stage | Disposition |
| --- | --- | --- |
| Run receipt and iteration summary | V2d-A | Move earlier as public evidence primitives. |
| Failure summary and failure taxonomy | V2d-A | Move earlier and validate before candidate generation. |
| Environment fingerprint and artifact references | V2d-A | Move earlier with strict redaction and reference rules. |
| Authority/data-placement and redaction policy | V2d-A | Make explicit prerequisites rather than implicit V3-A assumptions. |
| Improvement record and baseline/candidate lineage | V2d-B | Define after core evidence identity and references stabilize. |
| Human-readable/Obsidian projection | V2d-B | Keep as a non-authoritative, tool-neutral projection boundary. |
| Typed graph projection | V2d-B | Keep projection-only; defer graph execution and storage. |
| Real cross-run evidence collection | Private manual/CI PoC | Validate public contracts without placing private records in this repository. |
| Candidate scoring, duplicate suppression, and hypothesis generation | V3-A | Retain after the V3-A re-entry gate passes. |
| Proposal, patch, branch, artifact, or draft-PR production | V3-A | Retain as proposal-only output with no self-promotion. |
| Baseline/candidate execution and regression comparison | V3-B | Separate candidate production from independent evaluation. |
| Scheduler, resident hooks, controller, shared queue, or database | V3-C or later | Defer until operational evidence proves a need and a new gate approves it. |
| Automatic promotion, merge, release, or deployment | Not planned | Exclude from self-improvement authority. |

## V3-A Re-Entry Acceptance Gate

Evidence-Driven Self-Improvement may begin only when:

1. V2d contracts and validators are reviewed and versioned.
2. The private PoC covers success, failure, gate, and baseline/candidate cases.
3. Every PoC record validates without prohibited sensitive material.
4. Environment differences can be represented without private paths,
   hostname, username, or raw config.
5. Improvement lineage can be reconstructed deterministically from content
   digests and references.
6. Human-readable and typed graph projections regenerate from validated inputs
   and remain non-authoritative.
7. No required evidence depends on uncontrolled free text.
8. Proposer and promoter roles are separated.
9. No public-repo reverse dependency on a private platform exists.
10. Existing V1/V2 false-complete, unauthorized-action, external-write,
    review, human-gate, and no-backend tests remain green.

Failure of any item routes work back to V2d or the private PoC instead of
weakening the gate.
