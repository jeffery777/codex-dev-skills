# Release Notes: v0.11.0

Release date: TBD

v0.11.0 introduces Loop Engineering V2d-B: strict improvement lineage and
deterministic non-authoritative projections.

## Improvement Lineage

- Added `loop-improvement-lineage/v0` without changing the exact
  `loop-operational-evidence/v0` family.
- Added baseline/candidate evidence-set identity, exact V2d-A references,
  environment matching, predecessor lineage, stale-baseline/conflict
  rejection, deterministic branching order, and tamper-evident record digests.
- Added distinct proposer, evaluator, independent verifier, and promoter
  declarations while keeping identity authentication and promotion outside the
  contract.

## Projection Boundary

- Added `loop-evidence-projection/v0` human-readable and typed graph manifests.
- Added deterministic source-derived ids, ordering, Markdown bytes, graph
  nodes/edges, and full content digests.
- Added an optional declarative Obsidian reference profile with no vault,
  plugin, synchronization, or runtime dependency.

## Validator, CLI, Fixtures, And Evals

- Added the standard-library `improvement_lineage.py` validator and bounded
  offline `improvementctl.py` CLI.
- Added public synthetic lineage/evidence fixtures, 23 adversarial eval cases,
  deterministic projection oracles, focused tests, and repository-validation
  integration.
- Kept all four authorization/completion/write/promotion invariants exactly
  false.

## Boundaries

This release adds no real operational/improvement records, private evidence
store, Obsidian mutation, graph database/runtime, scheduler, daemon,
controller, automatic candidate generation, promotion, merge, release, or
deployment. Codex CLI and Desktop retain their independent entry/control-plane
adapters over the shared Loop Engineering layer.

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
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
```

Release publication remains subject to exact-head deep code, documentation,
security/privacy, merge, and formal readiness gates plus separate human
authorization for merge, tag, and GitHub Release.

## Traceability

- V2d-B implementation issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/124>
