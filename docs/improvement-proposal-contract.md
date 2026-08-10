# Improvement Proposal Contract V0

Loop Engineering V3-A adds one strict downstream public family:

- `loop-improvement-proposal/v0` for deterministic `proposal-set` manifests.

It composes validated `loop-improvement-lineage/v0` records and their complete
`loop-operational-evidence/v0` closed set. It does not add or change V2d-A/B
fields, kinds, versions, validation, or authority.

The portable installed reference is
[`skills/loop-engineering/references/improvement-proposal-v0.md`](../skills/loop-engineering/references/improvement-proposal-v0.md).

## Input Eligibility

Generation reruns the V2d-B lineage validator over explicit records and V2d-A
documents. It never trusts caller-provided `valid`, score, rank, completion, or
promotion flags. An eligible V0 source record:

- has disposition `proposed`, `evaluated`, or `verified`;
- contains at least one exact, resolving failure-summary reference;
- resolves baseline/candidate run receipts, environments, artifacts, set
  digests, source revisions, evaluation artifacts, and all four roles;
- preserves exact false-authority invariants.

Validated `rejected` records and records without a source failure are listed as
ineligible and emit no proposal. Missing, tampered, conflicting, incomplete, or
private source input fails closed.

## Proposal Set

The exact envelope contains:

- `contract_version`: `loop-improvement-proposal/v0`;
- `kind`: `proposal-set`;
- deterministic proposal-set id and V2d-B source-record-set digest;
- `score_policy_version`: `loop-proposal-score/v0`;
- ordered selected proposals;
- deterministic duplicate-suppression receipts;
- ordered ineligible source-record references;
- exact false-authority fields;
- canonical SHA-256 content digest.

There is no generated timestamp or caller-supplied id. The same source bytes,
including reversed input order on manual and CI surfaces, produce identical
canonical JSON and digest.

## Complete Source Lineage

Every proposal retains exact:

- source-record-set digest and improvement record id/improvement id/digest;
- repository and objective ids;
- baseline and candidate evidence-set digests, run/environment/artifact refs,
  environment keys, and source revisions;
- ordered source failure refs and evaluation artifacts;
- source disposition and proposer/evaluator/verifier/promoter assignments.

Validation regenerates the complete proposal set from independently validated
V2d-A/B inputs and requires exact equality. A digest alone never substitutes
for contract, kind, id, revision, environment, artifact, or record identity.

## Score, Hypothesis, Intent, And Dedupe

`loop-proposal-score/v0` is integer-only. It sums fixed disposition, failure
category priority, candidate verification/review observation, typed evaluation
artifact, and recovery-signal components. Caller weights, time, locale,
filesystem order, free text, actor identity, and eval self-report cannot affect
the score.

The hypothesis is a closed `address-<failure-category>` code plus the first
canonical failure category/code/phase. Output intent is a description-only
enum: patch, branch, artifact, or draft-PR suggestion. No prose, command,
template, URL, or executable payload exists.

Duplicate identity is the canonical digest of repository, objective, baseline
set, exact source-failure refs, hypothesis code, and output intent. Equivalent
branches choose one winner by descending score, then record digest,
improvement id, and record id. Global rank uses descending score, duplicate
signature, then the same source identity. Suppressed sources remain visible in
the manifest.

## Proposal-Only Boundary

Every proposal contains exactly:

```json
{
  "proposal_only": true,
  "runtime_action_performed": false,
  "external_write_performed": false,
  "promotion_decision": "not-authorized"
}
```

Every proposal and proposal set also preserves:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

Role labels are declared data, not authentication. The independent
human/platform promotion gate is always required and `pending`. A valid
proposal, high score, successful eval, verified source record, or CLI success
does not authorize or prove apply, commit, branch, push, PR, approval,
activation, promotion, merge, tag, release, deployment, or completion.

## Offline CLI

```bash
python3 skills/loop-engineering/scripts/proposalctl.py generate \
  --record <record.json> --evidence <v2d-a-document.json>

python3 skills/loop-engineering/scripts/proposalctl.py validate \
  <proposal-set.json> \
  --record <record.json> --evidence <v2d-a-document.json>
```

Repeat `--record` and `--evidence` for each explicit file. The CLI rejects
symlinks, unsafe file types, duplicate keys, unknown routes/fields/versions,
oversized/deep/count-bound input, tamper, incomplete lineage, private data, and
action/authority escalation. It emits bounded canonical JSON to stdout or a
generic structured rejection to stderr.

It has no apply, Git, network, platform, artifact-dereference, hook, scheduler,
queue, database, graph runtime, resident controller, external-memory, or write
operation.

## Privacy And Data Placement

Public Git stores only contracts, code, synthetic fixtures, tests, evals, and
docs. Real evidence/proposals, private repository or artifact-store identity,
credentials, PII, host/user identity, private paths/config, and raw runtime
logs/transcripts remain private and untracked. Rejected values are not echoed.

PlugMem, Mem0, and every external-memory backend remain excluded and disabled.
No external-memory compatibility exception may weaken this contract.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_proposal \
  tests.test_proposalctl \
  tests.test_eval_improvement_proposal \
  tests.test_improvement_proposal_contract_docs \
  tests.test_operational_evidence \
  tests.test_improvement_lineage
python3 scripts/eval-improvement-proposal.py
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-improvement-lineage.py
./scripts/validate-repo.sh
```

The V3-A eval requires all decision/completeness/recovery/equivalence/score/
tie/dedupe/lineage/privacy rates to equal 1.0, with zero false-complete,
wrong-route, unauthorized-action, false-authority, external-write, or promotion
outcomes. Passing remains conformance evidence only.
