# Issue #137 Release Verification

Date: 2026-08-11

Status: pre-commit release-candidate verification passed

Authority: advisory evidence for draft-PR preparation only

## Candidate

- Base: `origin/main@b48ea6edb065c40bd798dd3d428b69f33cfb8315`
- Branch: `codex/137-v0-12-0-release`
- Change class: release documentation, status metadata, one release contract
  test, and Issue #137 planning/review evidence
- Python: CPython 3.12.9 selected through the tracked `.python-version`
- PyYAML: 6.0.3

The candidate changes no runtime implementation, fixture, eval behavior,
installer behavior, dependency, workflow, public contract semantics, V3-B,
Agent Memory, or V3-C implementation.

## Passed Evidence

| Check | Result |
| --- | --- |
| Interpreter/PyYAML preflight | Pass; Python 3.12.9, PyYAML 6.0.3 |
| Release metadata contract test | Pass; 3 tests |
| Improvement-proposal eval | Pass; 17 negative cases, every positive rate 1.0, zero false authority/completion/write/promotion |
| Operational-evidence eval | Pass; 12/12 cases, zero false authority/completion |
| Improvement-lineage eval | Pass; 6 positive and 23 negative cases, zero false authority |
| External-memory eval | Pass; 31/31 cases, zero false authority/completion |
| Full unit discovery | Pass; 841 tests |
| Repository validator | Pass after the documented in-scope wording fix |
| Installer/catalog manifest | Pass; repo-owned sources and versions align at 0.12.0 |
| Shell syntax | Pass for `install.sh` and `scripts/validate-repo.sh` |
| Task manifest parse | Pass; Issue #137 and five bounded tasks |
| Diff hygiene | Pass |
| Targeted public-data scan | Pass; no matching private path, key/token assignment, private-key marker, or token prefix |

## Classified Observations

The first repository-validator run failed because README changed the required
machine-readable phrase `current v0.12.0 release notes` to `current published
release notes`. The validator's exact extraction contract was inspected, the
versioned phrase was restored without changing meaning, the focused release
test passed, and the independent full validator rerun passed. This is a fixed
release-doc contract finding, not a runtime regression.

`./install.sh diff --all` exits 1 because machine-local installed workflow
copies predate accepted V3-A/main content. It reports the already-merged
proposal module/reference and several installed skill/doc differences. The
command made no repository or installed-state change. Updating installed
copies is outside Issue #137; repository-owned package consistency is proven
by `./install.sh manifest`, the full suite, and `validate-repo.sh`.

## GitHub Baseline

- Issue #137 is open and is the only open v0.12.0 release owner found.
- PR #134 and PR #136 are merged.
- Latest formal Release is v0.11.1.
- Remote v0.12.0 tag is absent.

These reads must be repeated at the final merge/publication gate. They do not
authorize merge, tag creation, or GitHub Release publication.

## Re-runnable Commands

```bash
python3 -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_proposal_contract_docs
python3 scripts/eval-improvement-proposal.py
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-improvement-lineage.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh
./install.sh manifest
./install.sh diff --all
bash -n install.sh scripts/validate-repo.sh
git diff --check
```

## Pending Exact-Head Evidence

- committed and remote head equality;
- hosted draft-PR and ready-for-review CI;
- exact-head deep merge review and formal merge-readiness decision;
- repeated tag absence and latest-Release reads;
- final human authorization for ready transition, merge, annotated tag, and
  GitHub Release.
