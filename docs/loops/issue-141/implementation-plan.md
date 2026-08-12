# Issue #141 Implementation Plan — V3-B Isolated Candidate Evaluation

## Objective

Implement the accepted additive V3-B contract, prove every required scenario
and false-authority boundary, and carry the Issue through exact-head draft-PR
readiness without merge, release, deployment, activation, or promotion.

## Verified Prerequisites

- Issue #141 is open and owns this scope; no open PR collides with it.
- Branch `codex/141-v3b-isolated-evaluation` began clean at accepted main
  `b4671f5ea4188f64e75318fc99febf1711098cc0`.
- Latest Release v0.12.1 and annotated tag evidence satisfy the earlier release
  prerequisite without selecting a V3-B release target.
- The tracked resolver selects Python 3.12.9 and PyYAML 6.0.3.
- GitNexus is current at the accepted base. Existing V3-A and V2b production
  entrypoints are high-impact, so V3-B is a new downstream module/CLI.
- External memory has no backend. V3-B uses memory-off or synthetic V2b-validated
  advisory context only.

## Task Slices

1. Freeze exact family, schemas, fixed policy, isolation, environment,
   independent verification, context, packet, privacy, and CLI semantics.
2. Implement strict evaluation input/result, replay verification, promotion
   packet, and validation in `candidate_evaluation.py`.
3. Implement explicit-file stdout/stderr-only `evaluationctl.py` routes.
4. Add public synthetic fixtures, unit/CLI/docs tests, deterministic evals,
   and repository-validator integration.
5. Align public/portable contracts, README, roadmap, program docs,
   release-readiness guidance, skill reference, and package inventory without
   changing version or release metadata.
6. Run focused and full verification; routine/deep code, docs, security,
   privacy, and formal reviews; close findings; commit/push; open a draft PR;
   and verify hosted CI on the exact head.

## Expected Change Surface

### Production and portable contract

- `skills/loop-engineering/scripts/candidate_evaluation.py`
- `skills/loop-engineering/scripts/evaluationctl.py`
- `skills/loop-engineering/references/candidate-evaluation-v0.md`
- `docs/candidate-evaluation-contract.md`

Existing V2d-A/B, V3-A, and V2b production modules are consumed but not
expected to change.

### Tests, fixtures, and evals

- `evals/candidate-evaluation/`
- `scripts/eval-candidate-evaluation.py`
- `tests/test_candidate_evaluation.py`
- `tests/test_evaluationctl.py`
- `tests/test_eval_candidate_evaluation.py`
- `tests/test_candidate_evaluation_contract_docs.py`
- `scripts/validate-repo.sh`

### Documentation and packaging references

- `skills/loop-engineering/SKILL.md`
- `README.md`
- `docs/roadmap.md`
- `docs/release-readiness.md`
- `docs/programs/operational-evidence/*.md`
- `docs/loops/issue-141/`
- `install.sh` and `catalog.yaml` only when required to package the new files;
  version values must remain `0.12.1` and target release remains TBD.

## Scenario And DoD Matrix

| Scenario | Evidence |
| --- | --- |
| pass/pass | core unit and eval |
| regression | comparison unit and eval |
| bad baseline/source | source and comparison negative tests |
| verifier failure | replay/packet tests |
| environment mismatch | environment tests/eval |
| lineage tamper/missing/mismatch | V3-A regeneration tests/eval |
| deterministic replay/permutation | repeated unit/CLI/eval bytes |
| false authority/action/promotion | unit/CLI/eval zero counts |
| memory-off | default unit/CLI/eval path |
| valid synthetic context | V2b production decision fixture |
| invalid context classes | fallback matrix |
| manual/CI equivalence | repeated explicit-file CLI output |
| timeout/resource/interrupted/uncertain | non-qualified comparison cases |
| packet cannot act | wrong-route CLI tests and packet invariants |

## Verification Plan

Use the tracked resolver for every Python command, beginning with:

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
```

Focused:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_candidate_evaluation \
  tests.test_evaluationctl \
  tests.test_eval_candidate_evaluation \
  tests.test_candidate_evaluation_contract_docs \
  tests.test_improvement_proposal \
  tests.test_proposalctl \
  tests.test_improvement_lineage \
  tests.test_operational_evidence \
  tests.test_memory_contract \
  tests.test_memoryctl
./scripts/project-python scripts/eval-candidate-evaluation.py
./scripts/project-python scripts/eval-improvement-proposal.py
./scripts/project-python scripts/eval-improvement-lineage.py
./scripts/project-python scripts/eval-operational-evidence.py
./scripts/project-python scripts/eval-memory-contract.py
```

Expanded:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
./install.sh manifest
./install.sh diff --all
bash -n install.sh scripts/validate-repo.sh scripts/project-python
git diff --check
git status --short --branch
git ls-files --others --exclude-standard
```

Installer diff is read-only evidence and may report machine-local drift. It
must not update installed state. After commit, rerun exact-head checks and
bind review/CI evidence to the final SHA.

## Review Plan

- pre-implementation `planning`, `docs-review`, and formal docs gate over the
  exact packet bytes;
- routine `code-review` and `code-review-deep` over the implementation;
- docs review and formal docs gate;
- security diff phases covering threat model, discovery, validation, and
  attack-path analysis for parsing, untrusted context, environment,
  isolation, authority, privacy, timeout/resource, and packet boundaries;
- formal code gate, exact-head `merge-review-deep`, and
  `merge-readiness-gate`;
- hosted GitHub Actions, review/thread state, draft state, and local/remote/PR
  head equality.

Every MUST-FIX and SHOULD-FIX is fixed and re-reviewed. Every NIT receives a
durable disposition.

## Risks And Controls

- Existing-contract drift: additive module; existing validators are called,
  not edited or bypassed.
- Arbitrary execution: closed observation schema; no command/code/subprocess.
- Environment laundering: exact finite fingerprints and explicit mismatch.
- Candidate self-verification: verifier replay is derived from the distinct
  declared role and exact regenerated bytes.
- Context injection: production V2b decision; all-record adoption; no content
  echo; context cannot affect policy or outcome semantics.
- False promotion: exact packet-only/action-false objects and pending gate.
- Privacy leakage: strict fields, whole-document checks, generic errors, and
  synthetic public fixtures only.
- Surface drift: canonical output excludes caller surface and wall clock.

## Migration, Rollback, And Stop Conditions

No migration is required. Rollback removes only V3-B public files. It does not
delete or rewrite evidence, Git history, platform state, memory, runtime state,
or external systems.

Stop on source conflict; public-contract, execution-authority, sandbox,
privacy, environment, or threshold ambiguity; any need for a backend or V3-C;
destructive action; version/release-target change; ready transition; merge;
tag; Release; deploy; activation; or promotion.
