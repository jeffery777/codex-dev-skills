# Issue #133 Verification Report

Date: 2026-08-10

## Result

PASS for the complete pre-commit working tree represented by Codex Security
snapshot digest
`codex-security-snapshot/v1:sha256:b418d61419fec7cc4f1d84fde31a4e746547b7db9cb9e79412a95b315ce7e834`.

Authority: verification evidence only. It does not authorize apply, promotion,
ready-for-review, merge, tag, release, deployment, or activation.

## Interpreter

- `.python-version`: `3.12.9`
- resolved Python: CPython 3.12.9 from the active pyenv installation
- PyYAML: `6.0.3`
- the same resolved interpreter was used for every Python command below

## Focused And Adversarial Evidence

- focused V3-A/V2d contract, CLI, eval, and docs tests: 65 passed
- V3-A eval: 17/17 adversarial cases passed
- every decision, evidence-completeness, recovery, semantic-equivalence,
  score, tie, duplicate, lineage, and privacy rate: `1.0`
- false-complete, wrong-route, unauthorized action, false authority, external
  write, and promotion counts: `0`
- V2d-A eval: 12/12 cases passed
- V2d-B eval: 6 positive checks and 23 negative cases passed

## Expanded Evidence

- full unit discovery: 840 tests passed
- V1 Loop Engineering eval passed
- V2a agent-routing eval: 24/24 cases passed
- V2b memory-contract eval: 31/31 cases passed
- repository validator passed, including proposal contract and private-data
  policy checks
- installer and repository-validator shell syntax passed
- `git diff --check` passed
- GitNexus working-tree change detection reported low graph risk, 13 tracked
  files and 37 symbols, with no affected process; its omission of untracked
  files is explicitly not treated as complete change evidence

## Re-runnable Commands

```bash
python3 -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_proposal \
  tests.test_proposalctl \
  tests.test_eval_improvement_proposal \
  tests.test_improvement_proposal_contract_docs \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_improvement_lineage \
  tests.test_improvementctl
python3 scripts/eval-improvement-proposal.py
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-improvement-lineage.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
bash -n install.sh scripts/validate-repo.sh
git diff --check
```

## Remaining Gate

After commit, rerun exact-head verification and hosted GitHub Actions. A local
PASS is not platform evidence and cannot authorize merge or release.
