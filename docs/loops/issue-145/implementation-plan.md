# Issue #145 Implementation Plan — Memory M0 Readiness

## Objective

Implement the accepted additive M0 contracts, validators, CLIs, synthetic
fixtures, tests, and deterministic evals. Preserve released upstream
contracts, prove zero-touch memory-off, and stop before commit.

## Task Slices

1. Freeze and formally review the Issue-owned spec, ADR, threat model, plan,
   and task packet.
2. Add strict `memory_operation.py` and `operationctl.py` for operation
   authority, trusted time, request, receipt, and complete caller-owned
   revalidation inputs.
3. Add strict `memory_qualification.py` and `qualificationctl.py` for paired
   V3-B safety/conformance validation with a zero-touch memory-off path.
4. Add portable references and public contract docs without altering existing
   contract semantics.
5. Add synthetic fixtures, focused unit/CLI/docs tests, eval suites/runners,
   package inventory, repository validator integration, and public docs.
6. Run focused/full verification, GitNexus change detection where available,
   impact/diff inspection, deep code/docs/security/privacy review, and formal
   commit-readiness gate; stop before commit.

## Expected Change Surface

- `skills/loop-engineering/scripts/{memory_operation,operationctl,memory_qualification,qualificationctl}.py`
- `skills/loop-engineering/references/{memory-operation-v0,memory-qualification-v0}.md`
- `docs/{memory-operation-contract,memory-qualification-contract}.md`
- `evals/{memory-operation,memory-qualification}/`
- `scripts/eval-{memory-operation,memory-qualification}.py`
- focused tests for libraries, CLIs, docs, and evals;
- `skills/loop-engineering/SKILL.md`, README/roadmap/release-readiness/program
  docs, `catalog.yaml`, `install.sh`, and `scripts/validate-repo.sh` only as
  required to package/validate the additive files;
- `docs/loops/issue-145/` receipts.

No version or release-note change is expected. Existing V2b/V2d/V3 production
modules are consumers or regressions only and should not change.

## Verification

Begin with:

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
```

Focused commands will include new M0 tests/evals plus:

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_contract tests.test_memoryctl tests.test_eval_memory_contract \
  tests.test_candidate_evaluation tests.test_evaluationctl tests.test_eval_candidate_evaluation
./scripts/project-python scripts/eval-memory-contract.py
./scripts/project-python scripts/eval-operational-evidence.py
./scripts/project-python scripts/eval-improvement-lineage.py
./scripts/project-python scripts/eval-improvement-proposal.py
./scripts/project-python scripts/eval-candidate-evaluation.py
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
./install.sh manifest
./install.sh diff --all
bash -n install.sh scripts/validate-repo.sh scripts/project-python
git diff --check
git status --short --branch
git ls-files --others --exclude-standard
```

Installer commands are read-only consistency evidence and must not install,
update, activate, or delete anything.

## Risks And Controls

- Upstream drift: additive modules and separate references; regression tests.
- Authority laundering: complete caller-owned authority/eligibility/time chain
  is reconstructed; request self-assertion and backdating reject.
- Receipt overclaim: exact false-action fields and M1 proof disclaimer.
- Paired comparison ambiguity: verifier assignment and scope-bound M1 receipt
  are exact; valid reseal and replay cases are measured by eval outcomes.
- Delete risk: logical delete only; purge unsupported.
- Privacy: public/internal-only, generic errors, synthetic fixtures.
- Backend creep: source/diff scan rejects SQLite/FTS5/database/persistence paths.
- Release creep: target remains TBD and no version/release metadata changes.

## Review And Gates

- formal spec/ADR/threat-model/plan gate before production changes;
- deep code/public-contract/security/privacy review after implementation;
- docs review and formal code commit-readiness gate;
- two review/fix rounds maximum unless a new human decision is required;
- stop before commit for exact human authorization.

## Stop Conditions

Use the stop conditions in the spec and Issue #145. In particular, stop for
SQLite/FTS5/backend execution, persistence, V3-B changes, efficacy claims,
physical purge, confidential/restricted scope, unresolved security/public-
contract ambiguity, failed high-risk verification, or any unauthorized
external action.
