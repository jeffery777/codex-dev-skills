# Issue #124 Loop Spec — V2d-B Improvement Lineage And Projections

## Objective

Deliver V2d-B as strict, deterministic, standard-library-compatible public
contracts for improvement lineage and non-authoritative projections. Preserve
the accepted `loop-operational-evidence/v0` contract byte-for-byte at its
public boundary and keep real records, private evidence, synchronization,
graph execution, and promotion outside this repository.

## Sources Of Truth

- `AGENTS.md`
- GitHub Issue #124
- `docs/operational-evidence-contract.md`
- `docs/programs/operational-evidence/README.md`
- `docs/programs/operational-evidence/architecture-decisions.md`
- `docs/programs/operational-evidence/continuation.md`
- `docs/programs/operational-evidence/implementation-phases.md`
- `docs/roadmap.md`
- this spec, the Issue #124 implementation plan, task manifest, and ledger

## Facts And Design Decision

Facts:

- `loop-operational-evidence/v0` has an exact five-kind envelope, rejects
  unknown fields and versions, and has no extension field.
- Its accepted spec requires a new reviewed version for any additional field,
  kind, taxonomy code, locator kind, or enum.
- Improvement records and projections have different lifecycles from run
  evidence: records describe cross-run lineage, while projections are
  regenerable derived views.
- V2d-B must consume validated V2d-A documents without making them mutable,
  authoritative, or dependent on projection tooling.

Decision:

- Keep `loop-operational-evidence/v0` unchanged.
- Add `loop-improvement-lineage/v0` for exact `improvement-record` documents.
- Add `loop-evidence-projection/v0` for exact
  `human-readable-projection-manifest` and `typed-graph-projection-manifest`
  documents.
- Compose the families only in bundle/projection validation through exact
  contract, kind, id, and digest references.

This is a separate-family composition boundary, not
`loop-operational-evidence/v1`. A later revision may introduce a new version
only through a separately reviewed compatibility decision. Validators must
continue to reject unknown versions rather than interpreting them
permissively.

## Shared Strictness

Both new families use:

- JSON objects only;
- strict UTF-8 and duplicate-key rejection;
- sorted-key compact canonical JSON;
- lowercase SHA-256 content digests;
- JSON booleans, null, bounded safe integers, and no floating point;
- bounded document, string, array, and nesting sizes no weaker than V2d-A;
- exact field sets and bounded enums;
- identifiers restricted to the existing safe ASCII identifier grammar;
- the existing timestamp grammar when a timestamp is required;
- defense-in-depth rejection of credentials, secrets, tokens, emails, private
  paths, raw logs, tracebacks, shell transcripts, and uncontrolled free text;
- generic error codes/messages that never echo rejected values.

The implementation may reuse reviewed V2d-A canonicalization, loading,
privacy, and invariant helpers, but it must not weaken or reinterpret V2d-A
validation. Any shared-helper refactor requires exact V2d-A regression tests.

## Exact False-Authority Invariants

Every new record and projection contains exactly:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

The object has identical field names and values to V2d-A. It is a composition
rule, not an extension of the V2d-A envelope. Validation must reject a missing
field, additional field, true value, or semantically equivalent replacement.

A validated record, role label, lineage, projection, digest, referenced
verification/review artifact, or successful CLI result:

- does not authenticate an actor;
- does not prove repository, task, objective, verification, or review
  completion;
- does not satisfy a human or platform gate;
- does not authorize an external write, promotion, activation, commit, push,
  PR, merge, tag, release, deploy, or projection-target mutation.

## `loop-improvement-lineage/v0`

### Envelope

An improvement record has exactly:

- `contract_version`: `loop-improvement-lineage/v0`;
- `kind`: `improvement-record`;
- `record_id`: bounded opaque identifier;
- `improvement_id`: bounded stable improvement identifier;
- `objective_id`: bounded opaque objective identifier;
- `repository`: exact object containing only `repository_id`, using the V2d-A
  identifier grammar;
- `recorded_at`: strict timestamp;
- `producer`: exact bounded producer object;
- `payload`: exact improvement payload;
- `authority_invariants`: the exact false-authority object;
- `record_digest`: SHA-256 of the canonical record with `record_digest`
  omitted.

The envelope contains no extension, title, description, note, message, URL,
absolute path, or arbitrary metadata field.

The envelope repository id must equal both baseline and candidate
`source_revision.repository_id` values.

### Cross-Family Document Reference

Every V2d-A document reference has exactly:

```json
{
  "contract_version": "loop-operational-evidence/v0",
  "kind": "<allowed-v2d-a-kind>",
  "document_id": "<opaque-id>",
  "document_digest": "<lowercase-sha256>"
}
```

Bundle validation resolves all four fields against a supplied, independently
validated V2d-A document. A digest without matching contract, kind, and id is
not a valid reference.

### Evidence Snapshot Reference

`baseline` and `candidate` each have exactly:

- `snapshot_id`: bounded opaque identifier;
- `run_receipt`: a `run-receipt` reference;
- `environment_fingerprint`: an `environment-fingerprint` reference;
- `artifact_reference_set`: an `artifact-reference-set` reference;
- `evidence_set_digest`: the exact digest returned by V2d-A set validation;
- `environment_key`: canonical SHA-256 of the referenced environment payload;
- `source_revision`: exact V2d-A repository/commit object.

The three referenced documents must share the record objective/repository and
resolve within the same validated V2d-A set. `source_revision` must equal the
referenced run receipt source revision. `environment_key` is recomputed; a
caller-supplied value is never trusted.

V0 requires baseline and candidate `environment_key` values to match exactly.
Environment normalization, compatibility waivers, or policy-based comparison
requires a future contract version.

### Improvement Payload

The payload has exactly:

- `predecessor`: null or an exact improvement-record reference containing
  `record_id`, `improvement_id`, and `record_digest`;
- `baseline`: one evidence snapshot reference;
- `candidate`: one evidence snapshot reference;
- `source_failures`: an ordered unique array of zero or more
  `failure-summary` references;
- `evaluation_artifacts`: an ordered unique array of one or more artifact
  references resolved from the baseline or candidate artifact-reference set;
- `role_assignments`: exact proposer, evaluator, independent verifier, and
  promoter assignments;
- `candidate_disposition`: one of `proposed`, `evaluated`, `verified`, or
  `rejected`.

An evaluation-artifact entry has exactly `snapshot_role` (`baseline` or
`candidate`) and `artifact`. `artifact` repeats all six exact V2d-A artifact
fields: `artifact_id`, `artifact_kind`, `locator_kind`, `locator`,
`content_sha256`, and `media_type`. All fields must equal one item in the
selected snapshot's supplied validated artifact-reference set. The record does
not dereference locators.

`source_failures` are sorted by `(document_id, document_digest)`.
`evaluation_artifacts` are sorted by
`(snapshot_role, artifact_id, content_sha256)`. Unsorted, duplicate, missing,
or conflicting references fail closed. Source-failure references may resolve
from either supplied snapshot, but the combined baseline/candidate document
inventory must not contain one document id with different content.

### Role Assignments

`role_assignments` has exactly:

- `proposer`;
- `evaluator`;
- `independent_verifier`;
- `promoter`.

Each assignment has exactly `actor_kind` (`human`, `agent`, `tool`, or `ci`)
and a bounded opaque `actor_id`. All four `actor_id` values must be distinct
in V0; changing `actor_kind` cannot make a reused id independent.

Role labels are declared separation, not identity authentication or authority.
The record `producer` must exactly equal the assigned proposer. The assigned
independent verifier and promoter must each differ from the producer of the
referenced candidate run receipt as well as from the assigned proposer and
evaluator. `verified` requires at least one candidate-snapshot `verification`
artifact and one candidate-snapshot `review` artifact. The contract cannot
authenticate who created either artifact; it proves only that the declared
role identities are structurally distinct and that typed artifacts resolve.
No disposition, including `verified`, represents promotion or completion. V0
has no `promoted`, `approved`, `merged`, `released`, or `deployed`
disposition.

### Identity, Duplicate, Conflict, And Lineage Rules

- `improvement_id` is stable identity; `record_digest` is exact content
  identity.
- Duplicate `record_id` or `improvement_id` values fail closed.
- Multiple supplied digests for one stable identity are conflicts, not
  revisions.
- A predecessor reference must resolve by record id, improvement id, and
  digest.
- A root record has `predecessor: null`.
- A non-root record baseline `evidence_set_digest` must equal its
  predecessor's candidate `evidence_set_digest`; otherwise the baseline is
  stale.
- A record cannot use the same evidence-set digest for baseline and candidate.
- Predecessor cycles, self-links, missing predecessors, repository/objective
  mismatches, environment mismatches, and source-reference tampering fail
  closed.
- Branching is allowed: multiple candidate records may share one predecessor.
  Branching does not imply conflict or promotion.
- Deterministic lineage order is topological depth, then `improvement_id`,
  then `record_digest`. Inputs need not arrive in that order; validator output
  must.

The validator reconstructs only the supplied closed set. It does not discover
records, decide which branch is current, or infer a promoted baseline.

## `loop-evidence-projection/v0`

### Common Projection Envelope

Every projection manifest has exactly:

- `contract_version`: `loop-evidence-projection/v0`;
- `kind`: one supported projection kind;
- `projection_id`: the exact deterministic id
  `<projection-kind>:<source-record-set-digest>`;
- `source_record_set_digest`: canonical digest of the ordered validated
  improvement-record digests;
- `source_records`: ordered exact improvement-record references;
- `payload`: exact kind payload;
- `authority_invariants`: the exact false-authority object;
- `projection_digest`: SHA-256 of the canonical manifest with
  `projection_digest` omitted.

Projection manifests contain no wall-clock generation timestamp. Re-running
the same contract version over the same validated record set must produce
byte-identical canonical JSON and identical rendered output.

`source_record_set_digest` is
`sha256(canonical_json({"record_digests": <ordered-record-digests>}))`.
`source_records` use lineage order and each contains exactly `record_id`,
`improvement_id`, and `record_digest`.

### Human-Readable Projection Manifest

Kind `human-readable-projection-manifest` payload has exactly:

- `format`: `markdown`;
- `ordering`: `lineage-depth-improvement-id-record-digest`;
- `renderer_version`: `loop-human-projection/v0`;
- `output_locator`: exact object
  `{"locator_kind": "opaque-id", "locator": "<projection-id>"}`;
- `sections`: an ordered array of exact derived section descriptors;
- `rendered_content_sha256`: digest of the deterministic UTF-8 Markdown
  rendering.

Each section is derived from one record and has exactly:

- `section_id`: `section:improvement:<record-digest>`;
- `lineage_depth`: non-negative integer;
- `improvement_id`;
- `record_digest`;
- `predecessor_improvement_id`: null for a root, otherwise the resolved id;
- `baseline_evidence_set_digest`;
- `candidate_evidence_set_digest`;
- `candidate_disposition`;
- `proposer`, `evaluator`, `independent_verifier`, and `promoter`, each as the
  exact `actor_kind`/`actor_id` assignment from the source record.

Sections are in lineage order. The Markdown renderer emits UTF-8 with LF
newlines, one final newline, and this exact structure:

```text
# Improvement lineage <source-record-set-digest>

## <improvement-id>
- depth: <decimal-depth>
- record: <record-digest>
- predecessor: <improvement-id-or-none>
- baseline: <evidence-set-digest>
- candidate: <evidence-set-digest>
- disposition: <candidate-disposition>
- proposer: <actor-kind>:<actor-id>
- evaluator: <actor-kind>:<actor-id>
- independent-verifier: <actor-kind>:<actor-id>
- promoter: <actor-kind>:<actor-id>
```

One blank line separates sections. Identifiers already use the safe ASCII
grammar; renderers must not perform locale-sensitive transformation. There is
no arbitrary title, annotation, prose, HTML, script, template, or
caller-supplied Markdown field.

Validation can either regenerate the Markdown and compare its digest, or emit
the canonical rendering. It performs no filesystem write unless a future
separately authorized CLI operation is explicitly added; V2d-B validation and
render commands write only to stdout.

### Optional Obsidian Reference Profile

Obsidian is an optional declarative mapping documented and shipped as a
synthetic reference profile:

- profile id `obsidian-reference/v0`;
- inputs are the validated tool-neutral human projection only;
- stable note id comes from `improvement_id`;
- frontmatter values come only from exact ids, enums, digests, and source
  references;
- links are deterministic escaped wiki links derived from stable ids;
- no vault path, absolute path, workspace state, plugin, query engine, watcher,
  synchronization, conflict resolution, or write operation is part of the
  profile.

The core projection validator has no Obsidian dependency. The profile is
validated as checked-in synthetic configuration and documentation, not as a
required runtime.

### Typed Graph Projection Manifest

Kind `typed-graph-projection-manifest` payload has exactly:

- `schema_version`: `loop-typed-graph/v0`;
- `ordering`: `node-type-node-id-then-edge-type-from-to`;
- `nodes`: a deterministically ordered array;
- `edges`: a deterministically ordered array.

Allowed node types are:

- `improvement`;
- `evidence-snapshot`;
- `operational-document`;
- `artifact`;
- `role-assignment`.

Every node has exactly `node_id`, `node_type`, `source_ref`, and
`content_sha256`. Allowed edge types are:

- `predecessor-of`;
- `baseline-of`;
- `candidate-of`;
- `references-document`;
- `references-artifact`;
- `proposed-by`;
- `evaluated-by`;
- `verified-by`;
- `promotion-owned-by`.

Every edge has exactly `edge_id`, `edge_type`, `from_node_id`, `to_node_id`,
and `source_record_digest`.

`source_ref` is an exact tagged object:

- improvement: `record_ref`;
- evidence snapshot: `record_ref`, `snapshot_role`, `snapshot_id`, and
  `evidence_set_digest`;
- operational document: one cross-family document reference;
- artifact: `record_ref`, `snapshot_role`, and the exact six-field artifact;
- role assignment: `record_ref`, `role`, `actor_kind`, and `actor_id`.

For a canonical source-ref object `R`, a node id is
`node:<node-type>:<sha256(canonical_json(R))>`, and `content_sha256` is the same
full digest. For the exact object
`E = {"edge_type": ..., "from_node_id": ..., "to_node_id": ...,
"source_record_digest": ...}`, an edge id is
`edge:<edge-type>:<sha256(canonical_json(E))>`. Nodes sort by
`(node_type, node_id)` and edges by
`(edge_type, from_node_id, to_node_id, edge_id)`.

User-supplied display labels and properties are unsupported. Edges must
resolve to supplied nodes, duplicates and conflicts fail closed, and the graph
must encode the same predecessor DAG as the validated record set.

The manifest is a serializable projection only. Validation does not import a
graph library, connect to a database, execute a query, persist a graph, or
grant graph-derived authority.

## CLI Boundary

Add one portable CLI, provisionally `improvementctl.py`, with bounded offline
operations:

- `validate-record <record.json> <v2d-a-document>...`;
- `validate-set <record.json>... --evidence <v2d-a-document>...`;
- `project-human <record.json>... --evidence <v2d-a-document>...`;
- `project-graph <record.json>... --evidence <v2d-a-document>...`;
- `validate-projection <manifest.json> <record.json>... --evidence ...`.

Exact argv may be refined during implementation without changing semantics.
Commands read explicit files, perform no discovery or network access, emit
bounded canonical JSON/Markdown to stdout, return stable non-zero
dispositions, never echo rejected sensitive input, and never mutate records,
Git, a vault, a graph store, a ledger, or platform state.

## Privacy And Data Placement

Public Git may contain only contracts, validators, CLIs, synthetic fixtures,
tests, evals, reference profiles, relationship docs, and release docs.

Real improvement records, real operational evidence, projection outputs from
real records, actor identities, private PoC data, credentials, logs,
transcripts, machine paths/configuration, vaults, databases, caches, indexes,
and runtime state remain private or caller-controlled and untracked.

Identifiers are opaque and synthetic in fixtures. They must not contain
emails, usernames, hostnames, private paths, URLs, secrets, tokens, or prose.
Repository-relative artifact locators remain references and are never
dereferenced by V2d-B.

## Versioning, Migration, Rollback, Packaging, And Release

- Target release: v0.11.0.
- V2d-A documents require no migration and continue to validate with the
  existing validator/CLI.
- V2d-B has no in-place migration from V2d-A because it is a composed,
  separate-family contract.
- Unknown future family versions fail closed.
- Projection outputs are disposable and regenerable; rollback removes V2d-B
  code/docs/fixtures and regenerates nothing.
- No rollback deletes or rewrites caller records, vaults, databases, indexes,
  or runtime state.
- Install the new validator, CLI, and references through the existing
  `loop-engineering` skill package. Do not add a runtime-specific CLI or
  Desktop entrypoint.
- Align README, roadmap, program docs, portable references, installer/catalog,
  release readiness, version metadata, and `docs/release-notes-v0.11.0.md` on
  the same feature branch.
- Commit, push, PR creation, merge, tag `v0.11.0`, and GitHub Release are
  separate exact human gates.

## Fixtures, Tests, And Evals

Positive synthetic coverage must include:

- a root and descendant improvement record;
- a branched lineage;
- every candidate disposition;
- deterministic human projection;
- optional Obsidian profile mapping;
- deterministic typed graph projection.

Negative coverage must include:

- duplicate keys, unknown fields/versions, and tampered digests;
- duplicate/conflicting record or improvement identity;
- missing predecessor/reference and predecessor cycle;
- stale baseline and baseline/candidate equality;
- mismatched repository, objective, source revision, environment, or evidence
  set;
- invalid, missing, duplicate, or unsorted failure/artifact references;
- role identity collision, self-verification, and false promotion;
- authority escalation;
- private paths, synthetic secrets/tokens, raw logs, and uncontrolled free
  text;
- nondeterministic ordering, projection/source mismatch, broken graph edge,
  and rendered-content digest mismatch.

Eval thresholds require complete expected-case coverage, zero false
authorization/completion/external-write/promotion outcomes, and byte-identical
projection output across repeated runs.

## Definition Of Done

- Both new contract families and their composition rules are implemented and
  documented without changing V2d-A semantics.
- Improvement identity, baseline/candidate lineage, role separation, and
  deterministic reconstruction pass all positive and adversarial cases.
- Human and graph projections regenerate deterministically from validated
  records and remain non-authoritative.
- The Obsidian profile remains optional and declarative.
- Focused tests/evals and the full V1-through-V2d-A regression suite pass.
- Public docs, portable installed references, packaging, v0.11.0 metadata,
  release notes, and program continuation agree.
- Deep code, docs, security/privacy, formal readiness, and exact-head merge
  reviews have no unresolved MUST-FIX findings.

## Stop Conditions

Stop before implementation if review finds unresolved ambiguity in:

- contract family/version compatibility;
- evidence snapshot identity or stale-baseline semantics;
- role independence or false-authority behavior;
- privacy/data placement or projection injection;
- deterministic ordering/digest rules;
- migration, rollback, packaging, or release scope.

Stop before commit, push, PR creation/review submission, platform comment,
merge, tag, GitHub Release, deployment, or another external write without
exact authorization for that action.
