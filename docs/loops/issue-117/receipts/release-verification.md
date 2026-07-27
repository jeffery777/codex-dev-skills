# Issue #117 v0.9.2 Release Verification

Date: 2026-07-27

Status: local verification passed; formal documentation gate passed after one
stale release-evidence statement was corrected

Authority: release-readiness evidence only

## Candidate

- Base: `main` at `64074e5349fc917e9d6b3243e87303df7d75dda7`
- Proposed tag: `v0.9.2`
- Included merged work: PR #114 and PR #116
- Release-only changes: version metadata, README current-release text, release
  notes, roadmap/program status, and Issue #117 release evidence

The candidate does not change installer behavior, CLI handoff implementation,
runtime permissions, completion authority, V2d contracts, V3 workflows, or
deployment behavior.

## Verification

| Check | Result |
| --- | --- |
| Python runtime | Pass: Python 3.12.9 |
| Full repository unit tests | Pass: 743 tests in 195.651 seconds |
| Repository validation | Pass |
| Loop engineering contracts | Pass: 150 tests |
| Native CLI/Desktop contracts | Pass: 47 tests |
| Custom-agent and isolated installer contracts | Pass: 41 tests |
| Routing evals | Pass: 45 tests |
| External-memory contracts and evals | Pass: 46 tests |
| GitNexus and PR-linkage guardrails | Pass: 13 tests |
| Installer/catalog manifest alignment | Pass |
| README/installer/catalog version alignment | Pass: all identify 0.9.2 |
| Shell syntax | Pass: `install.sh` and `scripts/validate-repo.sh` |
| Diff hygiene | Pass |
| Private-path and local-identifier scan | Pass |
| Documentation review gate | Pass after correcting the stale release-evidence statement; no open finding |

## Installer And Runtime Boundary Review

- `install.sh list` and `install.sh manifest` agree with `catalog.yaml`.
- `codex-cli-session-handoff` remains CLI-only and depends on the shared review
  and delivery groups.
- The shared and Desktop groups do not install the CLI adapter transitively.
- `--all` includes both CLI and Desktop workflow groups while excluding the
  explicit opt-in custom-agent profile group.
- README and release notes preserve independent CLI and Desktop entry points
  over shared orchestration, verification, review, and completion contracts.

## Re-runnable Commands

```bash
python3 --version
bash -n install.sh scripts/validate-repo.sh
./install.sh list
./install.sh manifest
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

## Remaining Gates

The final security diff scan must bind the exact post-receipt snapshot. Its
scan ID, digest, coverage, and finding count belong in the ready PR description
instead of being backfilled here after sealing the scan.

Commit, push, PR creation, merge, tag creation, and GitHub Release publication
remain subsequent actions in the authorized Issue #117 delivery sequence.
