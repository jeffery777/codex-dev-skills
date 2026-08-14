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

**Status:** Implemented by Issue #121; release publication remains separately
authorized.

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
- positive, negative, tamper, duplicate-key, unknown-field, secret,
  standalone-token, private-path, raw-log, invalid-reference,
  duplicate-document-id, and cross-record-mismatch fixtures/tests;
- relationship rules for existing ledger, route, worker, integration, memory,
  verification, and review artifacts.

**Explicit exclusions:**

- improvement records;
- Obsidian rendering or synchronization;
- graph projection manifests;
- private PoC data;
- hooks, plugins, controllers, schedulers, databases, and automatic promotion.

**Exit criteria:** the public contract and portable skill reference agree with
the strict offline validator; the five document kinds and bundle relationships
validate; required positive/adversarial fixtures and eval thresholds pass;
repository validation passes; and deep code, docs, security/privacy, and
formal readiness reviews have no unresolved MUST-FIX findings.

## Phase 2 — V2d-B Projection And Improvement Lineage

**Target release:** v0.11.0

**Status:** Implemented by Issue #124; release publication remains separately
authorized.

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

**Exit criteria:** both composed contract families validate independently;
lineage, role, privacy, authority, tamper, and deterministic projection
fixtures/evals pass; existing V2d-A remains green; and deep code, docs,
security/privacy, formal readiness, and exact-head merge reviews have no
unresolved MUST-FIX findings.

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

**Target release:** v0.12.0

**Status:** Implemented by Issue #133 / PR #134 and released in v0.12.0 through
the separately reviewed Issue #137 release closure. Activation and promotion
remain separately authorized.

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

**Delivered boundary:** `loop-improvement-proposal/v0` reruns V2d-B/V2d-A
validation, emits only deterministic proposal sets, uses fixed integer scoring,
stable ties and duplicate suppression, and preserves exact false-authority and
proposal-only fields. `proposalctl.py` reads explicit bounded files and writes
only stdout/stderr. The independent human/platform promotion gate is always
required and pending.

**Explicit exclusions:** PlugMem, Mem0, external-memory adapters, private PoC
records, candidate execution, apply/commit/push/PR-create operations, automatic
approval/promotion, and all V3-B/V3-C runtime services.

**Exit criteria:** focused/adversarial thresholds and V1-through-V2d
regressions pass; packaging/docs agree; deep code/docs/security and formal
exact-head gates have no unresolved MUST-FIX; and hosted CI passes on the exact
draft-PR head. At delivery readiness the PR remains draft; its later merge is a
separate accepted platform event and does not authorize release or promotion.

**Release interlock:** V3-A implementation and merge alone did not publish
v0.12.0. Issue #137 separately closes the exact annotated-tag and GitHub
Release gate. Issue #135 documents the remaining order but does not implement
V3-B, Agent Memory, or later automation.

## Phase 5 — V3-B Isolated Candidate Evaluation

**Target release:** v0.13.0

**Status:** Issue #141 / PR #142 implement and qualify
`loop-candidate-evaluation/v0`; Issue #143 publishes the reviewed baseline in
v0.13.0 through a separate exact tag/Release gate.

**Entry criteria:** v0.12.0 release closure is verified from current GitHub
state; a new V3-B Issue/spec owns the exact execution, sandbox, authority,
privacy, environment-equivalence, scenario, and acceptance rules; and no
public-contract ambiguity remains.

**Deliverables:**

- isolated baseline and candidate synthetic-observation evaluation;
- same-policy comparison;
- environment-difference handling;
- independent verification result;
- regression and authority-invariant checks;
- promotion packet preparation without promotion;
- an optional provider-neutral context/evaluation seam that accepts only
  explicit V2b-validated advisory context and keeps memory-off as the default.

The delivered execution model is intentionally closed and synthetic: it
evaluates bounded observation documents and never runs arbitrary candidate
code or commands. Accepted optional context is labeled `synthetic-advisory`;
`memory-on` is reserved for a separately qualified M1 adapter.

The V3-B memory seam records the exact mode and context/receipt digests while
keeping proposal, evidence, execution policy, environment class, authority
invariants, and acceptance thresholds identical. Missing, partial, stale,
untrusted, sensitive, conflicting, or unsupported context fails closed to
memory-off.

**Explicit exclusions:** SQLite, FTS5, any backend/provider/MCP adapter,
automatic recall/write, M1/M2 implementation, V2b weakening, resident hooks or
services, promotion, runtime-driven merge/release, and deployment.

**Exit criteria:** isolated synthetic-observation evaluation, comparison, environment handling,
independent verification, regressions, authority/privacy cases, deterministic
manual/CI behavior, and the promotion-packet boundary pass on an exact reviewed
head. V3-B output cannot promote itself.

**Release interlock:** Issue #143 separately binds v0.13.0 to the exact reviewed
release-closure merge commit. V3-B outputs, tests, evals, reviews, PRs, and CI
do not authorize promotion, deployment, activation, Memory M1, or V3-C.

## Memory Track — M0, M1, And M2

This track composes the program but does not change the numbered V3 authority
phases.

### M0 — Backend Readiness

**Status:** Issue #145 owns the additive offline qualification candidate.
Target release remains TBD / human decision.

M0 defines and qualifies the contract-to-runtime gap matrix,
provider-neutral request/receipt protocol, current operation authority,
execution receipts, data placement, lifecycle, retention, concurrency,
recovery, security/privacy threat model, and V3-B memory-off/on evaluation
design. It uses separate `loop-memory-operation/v0` and
`loop-memory-qualification/v0` families, keeps released contracts unchanged,
and adds no backend. Wrapper memory-on is safety/conformance-only; memory-off
is zero backend/filesystem touch. Issue #135 planning did not complete M0, and
Issue #145 evidence cannot authorize M1 by itself.
Exit evidence rejects forged requests, untrusted time, verifier mismatch, and
cross-scope M1 receipt replay, with eval metrics derived from those outcomes.

### M1 — Thin Reference Backend Qualification

**Status:** Issue #147 owns the exact bounded candidate. Acceptance and target
release remain TBD / human decision.

M1 started only after the V3-B baseline and a new Issue/spec/ADR/security
review authorized the exact scope. The candidate is a
default-disabled, deterministic, local/manual/CI-only SQLite/FTS5 reference
adapter. It must behavior-probe FTS5 and fail closed to no memory; isolate
repository/principal/namespace/path scope; bind eligibility and provenance by
digest; use only structured bounded query input and parameterized SQL; disable
extension loading; enforce idempotency; atomically commit state and its
execution receipt; implement explicit lifecycle operations; and remain
context/cache rather than authority. It adds no daemon, network service,
scheduler, controller, MCP server, automatic recall/write, or cross-host
coordination.

Issue #147 qualification proves safety/conformance only. It cannot prove
efficacy or authorize install, activation, promotion, release, or V3-C.

### M2 — Second Provider Or MCP Adapter

M2 is considered only after M1 qualification passes and a new human decision
approves it. It must prove the same provider-neutral contract and cannot weaken
V2b or add compatibility exceptions for PlugMem or Mem0.

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

**Entry criteria:** V3-B evidence and M1 qualification must pass first. At least
two material operational needs—such as repeated batch demand, multiple queued
objectives, shared atomic claim/lease coordination, cross-host execution, or a
demonstrated human bottleneck—must exist. Security/privacy review and a new
architecture decision are required.

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
| Provider-neutral memory-off/on context seam | V3-B | Keep memory optional, explicit, V2b-validated, and non-authoritative. |
| Backend readiness, authority/receipt protocol, and threat model | Memory M0 | Define and qualify the boundary without implementing persistence. |
| Default-disabled local SQLite/FTS5 reference adapter | Memory M1 | Qualify only after V3-B evidence and a separate security-reviewed Issue. |
| Second provider or MCP adapter | Memory M2 | Consider only after M1 qualification and a new human decision. |
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
