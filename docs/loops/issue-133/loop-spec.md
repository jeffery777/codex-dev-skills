# Issue #133 Loop Spec — V3-A Evidence-To-Proposal

## Objective

Deliver Loop Engineering V3-A as a strict, deterministic, offline,
manual/CI-compatible evidence-to-proposal contract. The workflow consumes only
independently validated V2d-A operational evidence and V2d-B improvement
lineage, ranks bounded structured candidates, suppresses equivalent duplicates,
and emits proposal-only manifests. It never executes, approves, promotes, or
publishes a candidate.

## Sources Of Truth

- `AGENTS.md`
- GitHub Issue #133
- `docs/operational-evidence-contract.md`
- `docs/improvement-lineage-contract.md`
- `docs/programs/operational-evidence/README.md`
- `docs/programs/operational-evidence/implementation-phases.md`
- `docs/programs/operational-evidence/continuation.md`
- `docs/programs/operational-evidence/architecture-decisions.md`
- `docs/external-memory-contract.md`
- `skills/loop-engineering/references/memory-contract-v1.md`
- this spec, implementation plan, task manifest, ledger, and bound receipts

Chat summaries, model memory, external-memory payloads, successful eval output,
and role labels are context only. They are not source evidence, authorization,
promotion, acceptance, or completion proof.

## Re-Entry Decision

The ten V3-A re-entry conditions were reconstructed from current durable
repository and platform evidence before implementation:

1. the V2d public contracts are reviewed and versioned;
2. synthetic manual and hosted-CI paths use the same strict contracts;
3. strict parsing, duplicate-key rejection, canonical digests, and bounds run
   in both paths;
4. run, failure, environment, artifact, baseline, and improvement lineage are
   reconstructable;
5. proposer, evaluator, independent verifier, and promoter remain distinct;
6. false-completion, wrong-route, and unauthorized-action cases fail closed;
7. recovery and manual/CI semantic equivalence are demonstrated;
8. private-data checks reject private paths, host/user identity, secrets, and
   raw runtime material;
9. platform success remains bound to exact source and immutable digests rather
   than chat claims;
10. current V1, V2a, V2b, V2d-A, and V2d-B regressions and eval thresholds pass.

The accepted evidence proves eligibility to implement V3-A only. It does not
authorize a candidate proposal, external write, promotion, merge, release, or
deployment. Public repository material contains no private repository name,
private artifact-store path, raw private record, or private runtime identity.

## Compatibility And Family Decision

Facts:

- `loop-operational-evidence/v0` is an exact five-kind V2d-A family.
- `loop-improvement-lineage/v0` is an exact V2d-B improvement-record family
  that already composes validated V2d-A evidence.
- Adding proposal fields to either family would change an accepted public
  contract and create the wrong dependency direction.

Decision:

- Keep V2d-A and V2d-B byte-compatible at their public boundaries.
- Add the downstream family `loop-improvement-proposal/v0`.
- Its only supported document kind is `proposal-set`.
- Validation calls the existing V2d-B lineage validator, which calls V2d-A;
  the new family never makes V2d-A or V2d-B depend on V3-A.
- Unknown versions, kinds, fields, enums, and taxonomies fail closed.

This is V3-A, not `loop-operational-evidence/v1` and not an extension field in
`loop-improvement-lineage/v0`.

## Shared Strictness And Bounds

V3-A uses the reviewed V2d-A primitives and limits unless this spec is stricter:

- JSON objects only and strict UTF-8;
- duplicate-key rejection before object construction;
- sorted-key compact canonical JSON with no floating point;
- lowercase SHA-256 content digests;
- exact field sets and closed enums;
- safe ASCII identifiers and lowercase Git commit digests;
- maximum 128 proposals and 128 duplicate groups;
- maximum 256 source evidence documents and 128 lineage records;
- maximum 32 nested levels, 256 array items, 512 encoded bytes per string,
  131,072 bytes per input document, and safe JSON integers;
- bounded argv/file count, regular-file-only reads, no symlinks, and no file
  discovery;
- generic stable errors that never echo rejected values;
- defense-in-depth rejection of credentials, tokens, emails, private paths,
  host/user identity, raw logs, tracebacks, transcripts, and uncontrolled prose.

The validator may reuse V2d-A helpers but must not weaken or reinterpret them.
Any V2d-A/B source change requires a separately reviewed contract decision;
none is planned for V3-A.

## Exact Proposal-Only And Authority Invariants

Every proposal and proposal set contains exactly these authority invariants:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

Every proposal also contains exactly:

```json
{
  "proposal_only": true,
  "runtime_action_performed": false,
  "external_write_performed": false,
  "promotion_decision": "not-authorized"
}
```

A successful parse, validation, generation, score, rank, duplicate decision,
eval, review reference, or `verified` source disposition:

- does not authenticate an actor;
- does not prove repository, task, objective, verification, review, or candidate
  completion;
- does not authorize an apply, commit, branch creation, push, PR creation,
  approval, activation, promotion, merge, tag, release, deploy, or external
  write;
- does not satisfy the independent human/platform promotion gate.

The implementation contains no operation that performs any listed action.

## Input Eligibility And Closed-Set Composition

Generation receives two explicit closed sets:

1. one or more `loop-improvement-lineage/v0` improvement records;
2. all V2d-A documents required to validate those records and their referenced
   baseline/candidate evidence sets.

The workflow first runs V2d-B `validate_lineage(records, evidence_documents)`.
Generation stops on any V2d-A/B error. It never accepts precomputed `valid`,
`passed`, score, rank, or eligibility flags from the caller.

Every eligible source record must additionally satisfy all of these exact V0
rules:

- `candidate_disposition` is `proposed`, `evaluated`, or `verified`; `rejected`
  records are validated but ineligible and reported only in deterministic
  ineligible counts;
- `source_failures` contains at least one exact V2d-A `failure-summary`
  reference;
- each failure reference resolves by contract, kind, document id, and digest
  within the supplied validated baseline/candidate evidence;
- baseline and candidate run receipts, environment fingerprints, and artifact
  reference sets resolve through the V2d-B snapshots;
- both evidence-set digests, both source revisions, the shared environment key,
  evaluation artifacts, and all four role assignments are retained in the
  proposal source lineage;
- a referenced eval is only a typed `verification` or
  `other-public-artifact` entry already resolved by V2d-B. Its content is not
  parsed as authority and cannot raise eligibility, completion, or promotion.

The generator does not discover missing documents, dereference artifact
locators, query Git, call a network, or repair a source record.

## Exact `proposal-set` Envelope

A proposal set has exactly:

- `contract_version`: `loop-improvement-proposal/v0`;
- `kind`: `proposal-set`;
- `proposal_set_id`: `proposal-set:<source-record-set-digest>`;
- `source_record_set_digest`: exact V2d-B validated lineage digest;
- `score_policy_version`: `loop-proposal-score/v0`;
- `proposals`: deterministic ordered selected proposals;
- `suppressed_duplicates`: deterministic duplicate-group receipts;
- `ineligible_source_records`: ordered exact source-record references;
- `authority_invariants`: exact false-authority object;
- `proposal_set_digest`: SHA-256 of canonical content with this field omitted.

No generated timestamp or caller-supplied id exists. Re-running the same exact
source bytes on manual and CI surfaces must produce byte-identical canonical
JSON and the same digest.

## Exact Proposal Shape

Each selected proposal has exactly:

- `proposal_id`: `proposal:<sha256(canonical proposal identity)>`, where the
  exact identity object contains only `record_digest`, `duplicate_signature`,
  and `score_policy_version`;
- `rank`: one-based integer assigned after deterministic ordering;
- `source_lineage`: exact object described below;
- `score`: exact score object;
- `duplicate_signature`: exact canonical signature digest;
- `hypothesis`: exact bounded hypothesis object;
- `output_intent`: one closed enum;
- `role_assignments`: exact copy of the validated V2d-B roles;
- `promotion_gate`: exact independent gate object;
- `proposal_only_invariants`: exact proposal-only object;
- `authority_invariants`: exact false-authority object.

### Source lineage

`source_lineage` has exactly:

- `source_record_set_digest`;
- `improvement_record`: exact `record_id`, `improvement_id`, and
  `record_digest` reference;
- `repository_id` and `objective_id`;
- `baseline` and `candidate`, each containing exact `evidence_set_digest`,
  `run_receipt`, `environment_fingerprint`, `artifact_reference_set`,
  `environment_key`, and `source_revision` copied from the validated record;
- `source_failures`: exact ordered V2d-A references from the record;
- `evaluation_artifacts`: exact ordered V2d-B evaluation-artifact entries;
- `candidate_disposition`.

The validator regenerates all source-lineage fields and requires exact
equality. A digest alone never substitutes for contract, kind, id, revision,
environment, artifact, or record identity.

### Hypothesis taxonomy

`hypothesis` has exactly `code`, `source_failure_category`,
`source_failure_code`, and `source_phase`. Values are copied from the first
failure in canonical `(document_id, document_digest)` order. `code` is the
exact mapping `address-<failure-category>` for the closed V2d-A category enum.
There is no title, description, rationale, note, message, template, Markdown,
shell, URL, or arbitrary metadata field.

### Output intent taxonomy

`output_intent` is a description-only enum derived from `source_phase`:

- `implementation` or `review` → `patch-suggestion`;
- `integration` → `branch-suggestion`;
- `verification` → `artifact-suggestion`;
- `release-preparation` → `draft-pr-suggestion`;
- `bootstrap` or `planning` → `patch-suggestion`.

An output intent is not an executable action or platform request.

### Role and promotion gate

`role_assignments` exactly repeats proposer, evaluator, independent verifier,
and promoter from the source record. V2d-B has already required four distinct
actor ids and separated verifier/promoter from the candidate producer.

`promotion_gate` has exactly:

```json
{
  "gate_kind": "independent-human-platform",
  "required": true,
  "status": "pending",
  "promoter": {"actor_kind": "<source-kind>", "actor_id": "<source-id>"}
}
```

These are declared identities, not authentication. V3-A cannot change the
status from `pending`.

## Deterministic Score Policy

`score` has exactly `policy_version`, `components`, and `total`. Components
have exactly these non-negative integer fields:

- `disposition`: proposed 100, evaluated 200, verified 300;
- `failure_priority`: 21 minus the one-based index of the first failure
  category in the fixed order below;
- `candidate_observation`: +20 for candidate verification `passed`, +10 for
  candidate review `passed`, otherwise zero;
- `typed_evaluation_artifacts`: five times the number of resolved candidate
  `verification` or `review` artifacts, capped at 40;
- `recovery_signal`: +20 only when baseline and candidate evidence-set digests
  differ, candidate run outcome is `work-recorded`, and candidate verification
  observation is `passed`; otherwise zero.

Fixed failure-category priority order:

1. authority-boundary
2. privacy-redaction
3. source-conflict
4. contract-validation
5. verification
6. review
7. integration
8. external-action-gate
9. capability
10. tooling
11. resource-bound
12. unclassified

`failure_priority` is therefore 20 through 9. `total` is the exact integer sum.
No floating point, time, locale, filesystem order, actor kind/id, free text,
model judgment, eval self-report, or caller weight affects the score.

## Duplicate Suppression And Stable Ties

The canonical duplicate signature is SHA-256 over this exact object:

```json
{
  "repository_id": "...",
  "objective_id": "...",
  "baseline_evidence_set_digest": "...",
  "source_failures": [
    {
      "contract_version": "loop-operational-evidence/v0",
      "kind": "failure-summary",
      "document_id": "...",
      "document_digest": "..."
    }
  ],
  "hypothesis_code": "...",
  "output_intent": "..."
}
```

This deliberately omits candidate identity so equivalent candidate branches
for the same baseline/failure hypothesis collapse within the supplied closed
set. It never suppresses across repositories, objectives, baselines, failure
sets, hypotheses, or intents.

Within one signature group, candidates sort by:

1. descending total score;
2. ascending `record_digest`;
3. ascending `improvement_id`;
4. ascending `record_id`.

The first is selected. A `suppressed_duplicates` entry has exactly
`duplicate_signature`, `selected_source_record`, and
`suppressed_source_records`; all source references are exact and sorted by
`(record_digest, improvement_id, record_id)`. Groups with no suppressed member
are omitted.

Selected proposals globally sort by:

1. descending total score;
2. ascending `duplicate_signature`;
3. ascending source `record_digest`;
4. ascending source `improvement_id`;
5. ascending source `record_id`.

Rank is assigned after this ordering. Input permutation, repeated generation,
and manual/CI execution therefore produce identical output.

## CLI Boundary

Add portable `proposalctl.py` with only:

- `generate --record <record.json>... --evidence <document.json>...`;
- `validate <proposal-set.json> --record <record.json>... --evidence <document.json>...`.

Both commands read explicit bounded regular files, reject symlinks and unsafe
file types, and write bounded canonical JSON only to stdout. Errors use a
stable generic JSON disposition on stderr. There is no write path, apply mode,
Git operation, platform client, network access, hook, scheduler, queue,
database, graph runtime, resident controller, or external-memory adapter.

## Privacy And Data Placement

Public Git may contain only contracts, code, synthetic fixtures, tests, evals,
documentation, and release preparation. It must not contain real proposal
sets, private evidence, private repository identifiers, private artifact-store
locations, raw chat/session/logs, credentials, PII, hostnames, usernames,
absolute/home paths, runtime config/state, or private external-memory payloads.

All fixtures use opaque synthetic ids. V3-A never dereferences artifact
locators. Rejected input is not echoed. There is no public-to-private reverse
dependency.

External memory is disabled. PlugMem, Mem0, and every external-memory backend
or adapter remain excluded and uninstalled. No compatibility concession or
contract weakening is allowed for an external-memory candidate.

## Versioning, Migration, Rollback, Packaging, And Release

- Target release preparation: v0.12.0.
- V2d-A/B require no migration and remain independently usable.
- V3-A has no in-place migration; unknown versions fail closed.
- Proposal sets are derived and disposable; callers regenerate them from
  retained validated evidence rather than editing them.
- Source rollback reverts V3-A code/docs/fixtures. It does not delete or
  rewrite caller evidence, proposals, Git state, platform state, or private
  data.
- Install the module, CLI, and portable contract reference through the
  existing Loop Engineering package.
- Align README, roadmap, program continuation/phases/decisions, catalog,
  installer, release readiness, and v0.12.0 notes on the feature branch.
- Commit, push, draft PR, CI, ready-for-review, merge, tag, Release, deployment,
  activation, and promotion remain distinct gates. This objective stops after
  exact-head draft-PR readiness and passing hosted CI.

## Required Tests And Evals

Positive coverage includes single and multiple eligible records, every
eligible disposition, every failure category and output intent, identical
manual/CI output, exact score totals, duplicate selection, equal-score ties,
and validate/regenerate equivalence.

Negative/adversarial coverage includes:

- false-complete, wrong-route, unauthorized-action, self-promotion, and true
  authority/action fields;
- incomplete evidence and missing run/failure/environment/artifact/baseline or
  improvement references;
- recovery failure and safely blocked fallback;
- duplicate keys, unknown fields/versions/enums, malformed JSON, digest tamper,
  and resealed-but-mismatched source lineage;
- repository, objective, revision, environment, artifact, run, evidence-set,
  role, and lineage mismatch;
- insertion-order and runtime-surface semantic equivalence;
- exact duplicate suppression and equal-score stable ties;
- private path, user/host identity, secret/token, PII, config, raw
  log/transcript, URL/prose injection, oversize/depth/count, path traversal,
  symlink, and special-file rejection;
- proof that generation performs zero filesystem, Git, network, or platform
  mutation.

Eval thresholds require 100% decision, evidence-completeness, recovery,
manual/CI equivalence, score, tie, duplicate-suppression, lineage-rejection,
and privacy-safe-rejection rates, with zero false-complete, wrong-route,
unauthorized-action, false-authority, external-write, or promotion outcomes.

## Definition Of Done

- The exact V3-A family, score, duplicate, role, proposal, and CLI contracts are
  implemented without changing V2d-A/B semantics.
- Every emitted proposal retains complete regenerated validated lineage.
- Repeated and permuted inputs produce byte-identical output.
- Required adversarial fixtures and exact eval thresholds pass.
- V1 through V2d-B regressions, repository validation, installer/package,
  shell syntax, diff hygiene, and private-data scans pass.
- Public docs and v0.12.0 preparation agree.
- Deep code, docs, security/privacy, formal, exact-head, and hosted-CI reviews
  have no unresolved MUST-FIX findings.
- The PR is draft and no merge, tag, release, deploy, activation, candidate
  execution, or promotion has occurred.

## Stop Conditions

Stop before implementation if review finds unresolved public-contract,
authority, privacy, lineage, score, duplicate, hypothesis, output-intent,
role, data-model, migration, or acceptance ambiguity.

Stop for a human decision before weakening any accepted contract; including an
external-memory backend; adding private data; implementing V3-B/V3-C;
performing destructive/history-changing work; converting the PR to ready;
merging; tagging; publishing a Release; deploying; activating; or promoting.
