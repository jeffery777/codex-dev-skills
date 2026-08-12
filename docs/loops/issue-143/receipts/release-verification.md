# Issue #143 Release Verification

Date: 2026-08-12

Status: pre-commit release-candidate verification passed

Authority: advisory evidence for commit/push/draft-PR preparation only

## Candidate

- Base: `origin/main@a70db2ce1b6f1330b96d60bbdb98e2966a6afea9`
- Branch: `codex/143-v0130-release`
- Change class: version/release documentation and metadata, assertion-only
  release contract tests, and Issue #143 planning/review evidence
- Python: CPython 3.12.9 through tracked `scripts/project-python`
- PyYAML: 6.0.3

The candidate changes no V3-B runtime implementation, fixture/eval behavior,
dependency, workflow, public contract semantics, Memory backend, V3-C,
deployment, activation, or installed state.

## Passed Evidence

| Check | Result |
| --- | --- |
| Interpreter/PyYAML preflight | Pass; Python 3.12.9, PyYAML 6.0.3 |
| Focused release metadata contracts | Pass; 9 tests |
| Full unit discovery | Pass; 864 tests |
| Candidate-evaluation eval | Pass; 26 cases and zero false authority/completion/action/write/promotion |
| V3-A/V2d/V2b regression evals | Pass |
| Repository validator | Pass |
| Installer/catalog manifest | Pass; repo sources align at 0.13.0 |
| Installer diff | Read-only expected drift from installed v0.12.1; no state changed |
| Shell syntax and diff hygiene | Pass |
| Targeted privacy scan | Pass; no private path, secret assignment, private-key marker, or token prefix |
| GitNexus | Refreshed at accepted base; release diff is docs/metadata/test-only |

## Classified Observations

The first focused docs run exposed stale `TBD / human decision` wording in the
public V3-B contract/README and one outdated historical-note assertion. Both
were corrected in scope; focused tests and repository validation passed on the
final working diff.

`./install.sh diff --all` reports expected differences because machine-local
installed workflow copies predate merged V3-B and this release version. It made
no repository or installed-state change. `./install.sh manifest`, full tests,
and repository validation establish repository-owned consistency.

## Re-runnable Commands

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_candidate_evaluation_contract_docs \
  tests.test_improvement_lineage_contract_docs \
  tests.test_improvement_proposal_contract_docs
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/project-python scripts/eval-candidate-evaluation.py
./scripts/project-python scripts/eval-improvement-proposal.py
./scripts/project-python scripts/eval-improvement-lineage.py
./scripts/project-python scripts/eval-operational-evidence.py
./scripts/project-python scripts/eval-memory-contract.py
./scripts/validate-repo.sh
./install.sh manifest
./install.sh diff --all
bash -n install.sh scripts/validate-repo.sh scripts/project-python
git diff --check
```

## Pending Exact-Head Evidence

- assigned PR URL in final release notes;
- committed local/remote/PR head equality;
- hosted draft and ready exact-head CI;
- exact-head deep merge/readiness review;
- repeated tag/Release absence and exact merge SHA;
- public annotated tag and GitHub Release verification.
