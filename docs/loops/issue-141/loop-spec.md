# Issue #141 Loop Spec — V3-B Isolated Candidate Evaluation

## Objective

Deliver Loop Engineering V3-B as a strict, deterministic, offline,
manual/CI-compatible isolated candidate-evaluation contract. It consumes one
validated V3-A proposal plus the complete V2d-B/V2d-A closed source set,
compares bounded baseline and candidate observations under one fixed policy,
produces a separately reproducible independent-verification result, and
prepares a promotion packet that cannot promote or perform an action.

The optional advisory-context seam is provider-neutral. `memory-off` is the
default and complete path. Synthetic advisory context is adopted only after
the existing V2b production retrieval-decision function accepts every supplied
record. Context remains data and cannot change policy, limits, thresholds,
authority, completion, verification, or promotion.

Target release: **TBD / human decision**.

## Sources Of Truth

- `AGENTS.md`
- GitHub Issue #141
- `docs/loops/issue-135/roadmap-spec.md`
- `docs/operational-evidence-contract.md`
- `docs/improvement-lineage-contract.md`
- `docs/improvement-proposal-contract.md`
- `docs/external-memory-contract.md`
- `docs/programs/operational-evidence/README.md`
- `docs/programs/operational-evidence/implementation-phases.md`
- `docs/programs/operational-evidence/continuation.md`
- `docs/programs/operational-evidence/architecture-decisions.md`
- current V2d-A, V2d-B, V3-A, and V2b production modules and tests
- this spec, implementation plan, task manifest, ledger, and bound receipts

Chat summaries, handoffs, role labels, scores, evals, V2b receipts, evaluation
results, verification results, and promotion packets are context only. They do
not authenticate actors, authorize execution or external writes, satisfy a
gate, prove completion, or authorize promotion.

## Verified Entry Decision

Before implementation, current repository and platform evidence established:

1. accepted default branch `main` and the fresh worktree both started at
   `b4671f5ea4188f64e75318fc99febf1711098cc0`;
2. the latest Release is v0.12.1, non-draft and non-prerelease;
3. annotated tag v0.12.1 peels to accepted main;
4. no pre-existing open Issue or PR covered V3-B;
5. Issue #141 now owns the exact scope and Issue #135 supplies the accepted
   roadmap boundary;
6. the tracked resolver selects Python 3.12.9 with PyYAML 6.0.3;
7. GitNexus was refreshed to exact accepted main;
8. existing V3-A generation/validation and V2b retrieval-decision functions
   have high upstream blast radius.

The additive design below therefore calls the existing validators without
changing V2d-A, V2d-B, V3-A, or V2b semantics.

## Contract Family And Composition

V3-B adds the downstream family `loop-candidate-evaluation/v0`. It does not
extend an existing envelope. The one-way composition is:

```text
loop-operational-evidence/v0
  -> loop-improvement-lineage/v0
  -> loop-improvement-proposal/v0
  -> loop-candidate-evaluation/v0
```

The new family has four exact kinds:

- `evaluation-input`: caller-supplied bounded synthetic observations;
- `evaluation-result`: deterministic comparison generated from validated
  sources and the input;
- `independent-verification-result`: deterministic replay comparison produced
  by the declared V3-A independent-verifier role;
- `promotion-packet`: content-bound handoff data that is permanently
  non-promotional.

Every generator first calls V3-A `validate_proposal_set`, which regenerates the
complete proposal set through V2d-B and V2d-A. A caller-provided valid, score,
rank, completion, environment-equivalence, verification, or promotion flag is
never trusted.

## Isolation And Execution Model

V3-B uses a closed synthetic evaluator. "Execution" means evaluating exact
structured baseline and candidate observations with the production policy
below. It does not execute arbitrary candidate code or a command.

The implementation contains no subprocess, shell, network, Git, platform,
artifact-dereference, hook, scheduler, queue, controller, service, database,
filesystem-output, or external-write path. The CLI reads only explicitly named
bounded regular non-symlink JSON files and writes only bounded canonical JSON
to stdout or a generic rejection to stderr.

This boundary is shared by manual and CI use. Equivalent explicit inputs must
produce byte-identical canonical output regardless of caller surface, locale,
wall clock, filesystem order, or argument order.

## Shared Strictness And Bounds

V3-B reuses V2d-A strict JSON/canonicalization/privacy primitives:

- strict UTF-8 JSON objects with duplicate-key rejection;
- exact field sets and closed enums;
- recursively sorted compact ASCII JSON and lowercase SHA-256 digests;
- no floating point and integers restricted to the JSON-safe range;
- safe ASCII identifiers, lowercase commit digests, and bounded strings;
- maximum depth 32, array size 256, string size 512 bytes, and document size
  131,072 bytes;
- maximum 128 lineage records and 256 operational-evidence documents;
- generic stable errors that do not echo rejected input;
- defense-in-depth rejection of credentials, tokens, PII, emails, host/user
  identity, private/home/absolute paths, URLs, raw logs, tracebacks,
  transcripts, executable commands, and uncontrolled templates.

V3-B-specific bounds are:

- scenarios: `1..128`;
- duration: `0..60000` milliseconds per observation;
- resource units: `0..1000000` per observation;
- all failure counts: `0..scenario_count`;
- candidate duration and resource regression: at most 2000 basis points above
  the valid baseline, evaluated as integer cross-products.

No caller-supplied threshold, weight, override, environment equivalence rule,
or authority extension exists.

## Exact `evaluation-input`

The input has exactly:

- `contract_version`: `loop-candidate-evaluation/v0`;
- `kind`: `evaluation-input`;
- `proposal_id`: one exact selected proposal from the validated V3-A set;
- `scenario_set_digest`: SHA-256 identity for the caller-owned synthetic
  scenario inventory;
- `baseline` and `candidate`: exact sealed observation objects;
- `authority_invariants`: the exact four false-authority fields;
- `evaluation_input_digest`: canonical digest with this field omitted.

Each observation has exactly:

- `snapshot_role`: `baseline` or `candidate`;
- `evidence_set_digest` and `source_revision`, which must equal the selected
  proposal source snapshot;
- `environment_fingerprint`: the finite public V2d-A environment payload;
- `scenario_set_digest` and `scenario_count`;
- `outcome`: `passed`, `failed`, `timeout`, `resource-bound`, `interrupted`, or
  `uncertain`;
- `passed_scenarios`;
- `decision_failures`, `recovery_failures`, `determinism_failures`,
  `authority_failures`, and `privacy_failures`;
- `duration_ms` and `resource_units`;
- `observation_digest`: canonical digest with this field omitted;
- exact false-authority fields.

The input contains no command, code, free prose, expected status, threshold,
promotion state, or verifier assertion.

## Fixed Policy And Comparison Order

The generated result records `loop-candidate-acceptance/v0` and one canonical
policy digest. The policy requires:

- identical scenario set and count;
- exact baseline/candidate execution-environment fingerprint equality;
- valid baseline `passed` with all scenarios passed and every failure count
  zero;
- candidate `passed` with all scenarios passed and every failure count zero;
- candidate duration and resource units within the fixed 2000-basis-point
  baseline regression ceiling;
- exact false-authority fields;
- a later passing independent verification before the promotion packet can be
  marked `qualified-awaiting-human-decision`.

Comparison status uses this deterministic priority:

1. `baseline-invalid` for invalid/failing/uncertain baseline observation;
2. `input-mismatch` for scenario identity or count mismatch;
3. `environment-mismatch` for non-equivalent public environment fingerprints;
4. `execution-uncertain` for timeout, resource-bound, interruption, or
   uncertain candidate outcome;
5. `regressed` for a failed candidate, any nonzero candidate failure count, or
   duration/resource regression;
6. `qualified` only when every preceding rule passes.

A status describes the bounded comparison only. It is not task completion,
acceptance, approval, promotion, or permission to act.

## Optional V2b Advisory Context Seam

The API accepts either no context arguments or the complete triple:

1. one V2b `retrieval-decision-input` document;
2. caller-owned trusted conformance receipt mapping;
3. caller-owned trusted repository-source digest mapping.

When all three are present, V3-B calls the existing production
`memory_contract.decide_retrieval`. Context is adopted only when:

- the receipt has `fallback_to_no_memory: false`;
- the response is complete and contains at least one record;
- every record has exactly one `adopt-as-context` disposition;
- every adopted record has inline bounded content already accepted by V2b;
- record ids and digests resolve exactly and are unique.

The V3-B output retains only the V2b receipt digest, a canonical sorted set of
record ids/digests, its context-set digest, and the count. It never echoes
context content.

No arguments means `memory-off` with reason `not-requested`. Incomplete input,
V2b rejection, fallback, missing/partial/stale/untrusted/sensitive/conflicting/
unsupported content, mixed dispositions, empty adoption, or identity mismatch
produces `memory-off` with one bounded generic reason. Evaluation continues
under the identical fixed policy. Synthetic accepted context uses mode
`synthetic-advisory`; `memory-on` is reserved for a later qualified M1 adapter
and is not claimed by V3-B.

Context cannot change proposal, observations, policy, thresholds, limits,
environment equivalence, comparison status, verifier identity, or promotion
state. It is a digest-bound evaluation input only.

## Independent Verification

The verifier regenerates the expected evaluation result from the complete
V3-A/V2d sources, evaluation input, and optional context inputs. The verifier
assignment is copied from the selected V3-A proposal and remains structurally
distinct from proposer, evaluator, candidate producer, and promoter under the
existing V2d-B rules.

`independent-verification-result` contains:

- the selected proposal and source-set identities;
- declared verifier assignment;
- observed evaluation-result digest when the supplied result has a valid
  envelope, otherwise null;
- expected regenerated evaluation-result digest;
- `status`: `passed` only for exact equality, otherwise `failed`;
- bounded `failure_code`: null, `invalid-evaluation-result`, or
  `evaluation-mismatch`;
- `structural_independence_only: true`;
- exact false-authority fields and canonical verification digest.

Role structure does not authenticate the actor. A passing replay does not
prove completion or promotion.

## Promotion Packet Boundary

The packet validates the supplied evaluation and verification envelopes,
regenerates the expected verifier result, and binds exact proposal/source,
policy, context, comparison, evaluation, and verification digests.

Its disposition is:

- `qualified-awaiting-human-decision` only when comparison is `qualified` and
  independent verification is `passed`;
- `not-qualified` for every other valid combination.

Every packet contains exactly:

```json
{
  "packet_only": true,
  "runtime_action_performed": false,
  "external_write_performed": false,
  "approval_performed": false,
  "promotion_performed": false,
  "merge_performed": false,
  "release_performed": false,
  "deploy_performed": false,
  "activation_performed": false
}
```

It also preserves the four false-authority fields and a required independent
human/platform promotion gate with status `pending`. No packet route can apply,
commit, branch, push, create a PR, approve, promote, merge, release, deploy, or
activate anything.

## CLI Contract

`evaluationctl.py` exposes only:

```bash
evaluationctl.py evaluate <input> --proposal-set <set> --record <record> --evidence <document>
evaluationctl.py verify <result> <input> --proposal-set <set> --record <record> --evidence <document>
evaluationctl.py packet <result> <verification> <input> --proposal-set <set> --record <record> --evidence <document>
evaluationctl.py validate-packet <packet> <result> <verification> <input> --proposal-set <set> --record <record> --evidence <document>
```

Repeat record/evidence flags for the explicit closed set. Optional context uses
three named files; an omitted or partial triple is represented as the explicit
memory-off fallback defined above. Unsupported routes, action verbs, unsafe
paths, symlinks, file types, and count/size bounds fail closed with generic
structured stderr and exit code 2.

## Scenario And Acceptance Matrix

| Scenario | Required deterministic result |
| --- | --- |
| Baseline pass / candidate pass | `qualified`; passing replay; qualified-awaiting-human-decision packet |
| Baseline pass / candidate regression | `regressed`; packet not-qualified |
| Baseline failure or invalid evidence | `baseline-invalid` or source rejection |
| Independent verification failure | `failed`; packet not-qualified |
| Environment mismatch | `environment-mismatch`; packet not-qualified |
| Tampered/missing/stale/mismatched V3-A/V2d lineage | reject before comparison |
| Replay and input permutation | byte-identical result, verifier, and packet |
| False completion/authority/action/promotion | reject; zero false outcomes |
| Memory off | default complete path |
| Valid synthetic advisory context | digest-bound; identical policy/outcome semantics |
| Invalid context classes | explicit memory-off fallback |
| Manual/CI equivalent input | byte-identical canonical output |
| Timeout/resource/interruption/uncertainty | no qualified or success claim |
| Promotion packet action attempt | unsupported route or contract rejection |

The eval suite requires decision, completeness, environment, verifier,
determinism, replay, context-fallback, lineage-rejection, privacy, resource,
manual/CI, and packet-boundary metrics to equal 1.0. False completion,
authority, action, external-write, and promotion counts must equal zero.

## Privacy, Migration, Rollback, And Recovery

Only code, contracts, synthetic fixtures, tests, evals, and docs belong in
public Git. Real evidence/evaluations, private repository/artifact identity,
credentials, PII, host/user identity, private paths/config, and logs remain
private and untracked.

V3-B is additive and requires no V2d/V3-A/V2b migration. Outputs are
regenerated rather than edited in place. Rollback removes the V3-B files and
leaves source evidence, Git/platform state, memory state, and external systems
untouched. Missing or mismatched input produces a stable rejection or
memory-off fallback; the implementation does not discover, repair, or mutate
source data.

## Explicit Exclusions And Human Gates

Excluded: SQLite, FTS5, database/schema/migration/file, M1/M2, provider/MCP,
PlugMem, Mem0, automatic recall/write, hooks, schedulers, queues, controllers,
daemons, services, cross-host coordination, V3-C, arbitrary code/command
execution, automatic approval/promotion, merge, release, deploy, activation,
and private runtime records.

Stop for public-contract, execution-authority, sandbox, privacy, environment,
threshold, or product-semantic ambiguity; scope expansion; destructive action;
history rewrite; ready transition; merge; tag; GitHub Release; deployment;
activation; or promotion. Target release remains TBD / human decision.
