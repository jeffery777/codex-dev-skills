# Candidate Evaluation Contract

Status: V3-B isolated candidate evaluation candidate implementation. Target
release remains **TBD / human decision**.

`loop-candidate-evaluation/v0` is a strict offline family downstream of
`loop-improvement-proposal/v0`, `loop-improvement-lineage/v0`, and
`loop-operational-evidence/v0`. It compares one bounded synthetic baseline and
candidate, independently replays the comparison, and emits a promotion packet
that cannot promote or perform an action.

## Isolation And Authority

The evaluator does not run candidate code. It has no subprocess, shell,
network, Git, platform, hook, scheduler, queue, controller, daemon, database,
artifact-dereference, filesystem-output, or external-write path. The CLI reads
only explicit bounded regular non-symlink JSON files and writes canonical JSON
to stdout or one generic rejection to stderr.

Every generated document retains the four false-authority fields from V2d-A:

- `used_as_authorization: false`;
- `used_as_completion_evidence: false`;
- `external_write_authorized: false`;
- `promotion_authorized: false`.

The promotion packet additionally states that approval, promotion, merge,
release, deploy, activation, external write, and runtime action were not
performed. Its independent human/platform promotion gate always remains
required and `pending`.

## Contract Kinds

- `evaluation-input` binds one selected V3-A proposal, scenario-set digest,
  baseline and candidate observations, false-authority fields, and its digest.
- `evaluation-result` binds the complete validated proposal/lineage source,
  fixed policy, optional advisory-context digest summary, deterministic
  comparison, and its digest.
- `independent-verification-result` regenerates the expected result and passes
  only on exact equality. Structural role separation is not actor
  authentication, approval, completion, or promotion evidence.
- `promotion-packet` binds the exact result and verification. It is either
  `qualified-awaiting-human-decision` or `not-qualified`; neither state grants
  permission to act.

Every operation regenerates the V3-A proposal from the complete explicit
V2d-B/V2d-A source set. Missing, tampered, stale, or mismatched lineage fails
before comparison.

## Fixed Evaluation Policy

The `loop-candidate-acceptance/v0` policy is not caller-configurable:

- `1..128` identical synthetic scenarios;
- identical public environment fingerprints;
- baseline and candidate outcome `passed`, all scenarios passed, and zero
  decision, recovery, determinism, authority, and privacy failures;
- duration `0..60000` milliseconds and resource units `0..1000000`;
- candidate duration and resource use no more than 2000 basis points above a
  valid baseline;
- independent deterministic replay before a packet may say
  `qualified-awaiting-human-decision`.

Status priority is `baseline-invalid`, `input-mismatch`,
`environment-mismatch`, `execution-uncertain`, `regressed`, then `qualified`.
Timeout, resource-bound, interrupted, and uncertain observations therefore
cannot claim success.

Manual and CI callers use the same contract. Equivalent explicit inputs,
including permuted source-file order, produce byte-identical canonical output.

## Optional Advisory Context

The default complete mode is `memory-off`. The optional provider-neutral seam
accepts only a complete V2b retrieval-decision input plus explicit trusted
conformance receipts and trusted repository-source digests. It calls the
existing production `memory_contract.decide_retrieval` function.

Only a non-fallback receipt in which every inline record is uniquely
`adopt-as-context` becomes `synthetic-advisory`. Output retains record ids,
record digests, receipt digest, set digest, and count; it never echoes content.
Missing, partial, stale, untrusted, sensitive, conflicting, unsupported, mixed,
or invalid context becomes explicit `memory-off`. Context cannot change the
proposal, policy, thresholds, observations, environment rule, comparison,
verifier, completion, authority, or promotion state. `memory-on` is reserved
for a later separately qualified M1 adapter.

No SQLite, FTS5, database, schema, migration, Memory M1/M2 backend, PlugMem,
Mem0, provider, or MCP implementation is included.

## CLI

```bash
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py evaluate \
  <evaluation-input.json> --proposal-set <proposal-set.json> \
  --record <record.json> --evidence <evidence.json>
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py verify \
  <evaluation-result.json> <evaluation-input.json> \
  --proposal-set <proposal-set.json> --record <record.json> --evidence <evidence.json>
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py packet \
  <evaluation-result.json> <verification-result.json> <evaluation-input.json> \
  --proposal-set <proposal-set.json> --record <record.json> --evidence <evidence.json>
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py validate-packet \
  <promotion-packet.json> <evaluation-result.json> \
  <verification-result.json> <evaluation-input.json> \
  --proposal-set <proposal-set.json> --record <record.json> --evidence <evidence.json>
```

Repeat `--record` and `--evidence` for the complete explicit source set. The
optional context files are `--memory-decision`,
`--trusted-conformance-receipts`, and `--trusted-source-digests`. Omission or a
partial triple stays memory-off.

Action routes such as apply, branch, commit, push, PR creation, approval,
activation, promotion, merge, release, and deploy are unsupported.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_candidate_evaluation tests.test_evaluationctl \
  tests.test_eval_candidate_evaluation tests.test_candidate_evaluation_contract_docs
./scripts/project-python scripts/eval-candidate-evaluation.py
```

Use only synthetic fixtures in public Git. Real evidence/evaluations, raw
chats, sessions, logs, credentials, PII, host/user identity, private paths,
runtime databases, and private configuration remain outside this repository.
