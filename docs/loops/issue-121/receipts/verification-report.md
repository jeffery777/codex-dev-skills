# Issue #121 Verification Report

Date: 2026-07-29

Status: final local working-tree verification passed

Authority: advisory verification evidence only

## Candidate

- Branch: `codex/issue-121-operational-evidence-v0`
- Base and current HEAD:
  `845c768ca6a8b0c6d8591a79aa5101c0dd12bd17`
- Upstream: none
- Candidate form: uncommitted Issue #121 working tree
- Prepared release: v0.10.0
- Published baseline: v0.9.3

The candidate contains the V2d-A public contract, validator, CLI, fixtures,
evals, tests, documentation, installer/catalog alignment, and v0.10.0 release
preparation. It does not contain a tag, GitHub Release, deployment, private
operational record, runtime service, database, hook, scheduler, controller, or
V2d-B/V3 implementation.

## Verification Results

| Check | Result |
| --- | --- |
| Python runtime | Pass: Python 3.12.9 |
| Shell syntax | Pass: `install.sh` and `scripts/validate-repo.sh` |
| Operational-evidence unit, CLI, and eval tests | Pass: 44 tests |
| Operational-evidence production eval | Pass: 12/12; every exact threshold passed |
| Loop Engineering eval | Pass: 23/23; no false completion or unauthorized action |
| External-memory eval | Pass: 31/31; no false authority or completion |
| Full repository test discovery | Pass: 796 tests in 160.203 seconds |
| Repository validation | Pass |
| Loop Engineering repository contracts | Pass: 150 tests |
| Native CLI/Desktop adapter contracts | Pass: 47 tests |
| Custom-agent and installer-profile contracts | Pass: 41 tests |
| Agent-routing contracts | Pass: 45 tests |
| External-memory repository contracts | Pass: 46 tests |
| Operational-evidence repository contracts | Pass: 44 tests |
| Ledger validation | Pass: three project ledgers |
| Installer/catalog/current-release alignment | Pass: v0.10.0 |
| Diff hygiene | Pass: `git diff --check` |
| Repository privacy scan | Pass: private paths and local user identifiers absent |

The operational-evidence eval proves deterministic positive validation and
exact fail-closed dispositions for tamper, duplicate-key, unknown-field,
synthetic assignment-secret, standalone-token, private-path, raw-log,
invalid-reference, duplicate-document-id, and cross-record-mismatch cases.
Every observation preserves all four false-authority invariants.

## GitNexus Evidence

Repository-qualified change detection reported 11 tracked changed files, 35
changed indexed symbols, no affected process, and low risk. GitNexus does not
map the new untracked files in this pre-commit working tree, so direct source,
test, diff, security, documentation, and formal review remain the controlling
evidence for the new validator and fixtures.

## GitHub And Release Readback

Read-only GitHub API inspection confirmed:

- Issue #121 is open and is the only open Issue;
- its title remains
  `Define loop-operational-evidence/v0 core contracts and fail-closed validators`;
- v0.9.3 is the newest published non-draft, non-prerelease GitHub Release;
- no v0.10.0 tag or GitHub Release exists.

This supports preparing v0.10.0 in the same branch. It does not authorize tag
creation or publication.

## Re-runnable Commands

```bash
python3 --version
bash -n install.sh scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

## Verification Limits

- HEAD still equals the base because commit is not authorized. This receipt
  binds the inspected working-tree snapshot, not an immutable commit.
- Live GitHub CI and ready-PR linkage cannot be observed before push and PR
  creation.
- Tag creation and GitHub Release publication require the reviewed merge
  commit and their own exact authorization.
