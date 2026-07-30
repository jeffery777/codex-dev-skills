# Improvement Lineage And Projection Contracts V0

Loop Engineering V2d-B adds two strict, offline public contract families:

- `loop-improvement-lineage/v0` for cross-run `improvement-record` lineage;
- `loop-evidence-projection/v0` for deterministic human-readable and typed
  graph projection manifests.

They compose validated `loop-operational-evidence/v0` documents by exact
contract, kind, id, and digest reference. They do not add a V2d-A kind or
field, and existing V2d-A documents require no migration.

The portable installed reference is
[`skills/loop-engineering/references/improvement-lineage-v0.md`](../skills/loop-engineering/references/improvement-lineage-v0.md).

## Improvement Records

Every record has an exact envelope containing:

- contract/kind, stable record and improvement ids;
- objective and repository identity;
- timestamp and producer;
- exact payload;
- the four false-authority invariants;
- a canonical SHA-256 record digest.

The payload binds:

- an optional exact predecessor;
- baseline and candidate snapshots;
- typed source-failure and evaluation-artifact references;
- distinct proposer, evaluator, independent verifier, and promoter roles;
- a bounded non-promotional candidate disposition.

A snapshot binds one validated V2d-A set digest, run receipt, environment
fingerprint, artifact-reference set, environment key, and exact source
revision. Baseline and candidate environments must match in V0. A child
baseline must equal its predecessor candidate; missing predecessors, stale
baselines, cycles or cycle attempts, identity conflicts, reference tampering,
role collision, and environment mismatch fail closed.

Branching is allowed. Deterministic order is lineage depth, improvement id,
then record digest. The validator reconstructs only the supplied closed set;
it does not select a current or promoted branch.

## Role And Authority Boundary

All four role ids are distinct. The record producer equals the proposer, and
the candidate run producer cannot be the declared independent verifier or
promoter. A `verified` disposition requires resolved candidate verification
and review artifacts.

These are structural checks over declared data. They do not authenticate an
actor or artifact author. No role, artifact, disposition, record, digest, or
projection authorizes or proves completion, external writes, promotion,
commit, push, PR, merge, tag, release, or deployment.

Every record and projection contains exactly:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

## Deterministic Projections

`human-readable-projection-manifest` deterministically derives a Markdown
section for each validated record. It accepts no arbitrary prose, HTML,
script, or template field. Projection ids, source-set digests, ordering,
output locator, section ids, rendered bytes, and manifest digests are
source-derived.

`validate-projection` validates the manifest against the complete source set.
It does not attest to a separately stored or displayed Markdown file.
Consumers that persist or display Markdown must use the `project-human`
rendering from the same invocation or compare the exact UTF-8 bytes with the
manifest `rendered_content_sha256` before presentation.

`typed-graph-projection-manifest` contains exact typed nodes and edges for
improvements, snapshots, V2d-A documents, artifacts, and role assignments.
Node/edge ids are full canonical SHA-256 derivations. The manifest is a
serialized view only; it performs no graph query, storage, or execution.

The optional
[`obsidian-reference-profile-v0.json`](../skills/loop-engineering/references/obsidian-reference-profile-v0.json)
maps the tool-neutral human projection to stable ids, frontmatter fields, and
escaped wiki links. It has no Obsidian dependency and performs no vault read,
write, watch, synchronization, plugin, query, or conflict-resolution action.

## Offline CLI

```bash
python3 skills/loop-engineering/scripts/improvementctl.py validate-record \
  <record.json> --evidence <v2d-a-document.json>...

python3 skills/loop-engineering/scripts/improvementctl.py validate-set \
  <record.json>... --evidence <v2d-a-document.json>...

python3 skills/loop-engineering/scripts/improvementctl.py project-human \
  <record.json>... --evidence <v2d-a-document.json>...

python3 skills/loop-engineering/scripts/improvementctl.py project-graph \
  <record.json>... --evidence <v2d-a-document.json>...

python3 skills/loop-engineering/scripts/improvementctl.py validate-projection \
  <manifest.json> <record.json>... --evidence <v2d-a-document.json>...
```

Commands read only explicit files, emit bounded stdout/stderr, perform no
network or artifact dereference, and do not mutate records, projections, Git,
ledgers, vaults, graph stores, or platforms.

## Privacy And Data Placement

This repository stores only contracts, validators, synthetic fixtures, tests,
evals, declarative reference profiles, and documentation. Real operational or
improvement records, real projections, actor identities, logs, transcripts,
credentials, private paths, machine configuration, vaults, databases, caches,
indexes, and private PoC data stay outside public Git.

Unknown fields/versions, duplicate JSON keys, floats, oversized/deep inputs,
unsafe identifiers/paths, recognized credential and common Git-provider token
forms, raw logs, uncontrolled free text, and modified authority fields reject
without echoing the rejected value. Pattern checks are defense in depth; real
records must never place secret values in identifier fields.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_lineage \
  tests.test_improvementctl \
  tests.test_eval_improvement_lineage \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-improvement-lineage.py
python3 scripts/eval-operational-evidence.py
./scripts/validate-repo.sh
```

Success means only that the supplied public records and projections conform.
It does not satisfy a project or publication gate.
