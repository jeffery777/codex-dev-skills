# Issue #111 Release Verification Receipt

Date: 2026-07-23

Status: pre-publication local verification passed

Authority: advisory verification evidence only

## Candidate Scope

The candidate aligns v0.9.1 version and release metadata, records the completed
Issue #107 and Issue #109 baselines, updates the Operational Evidence Phase 0
handoff, and adds Issue #111 planning and release evidence. It does not change
runtime feature behavior or implement V2d-A.

Issue #107 and Issue #109 point-in-time receipts are unchanged.

## Verification Results

| Check | Result |
| --- | --- |
| Python runtime | Pass; Python 3.12.9 |
| `bash -n install.sh` | Pass |
| `bash -n scripts/validate-repo.sh` | Pass |
| GitNexus repository config validator | Pass; exact index-only configuration |
| GitNexus config and PR linkage tests | Pass; 13 tests |
| V2c-B hook tests | Pass; 27 tests |
| V2c-A adapter tests | Pass; 79 tests |
| Full repository test discovery | Pass; 693 tests |
| `./scripts/validate-repo.sh` | Pass |
| `git diff --check` | Pass |
| Version alignment | Pass; installer, catalog, README current release, and release notes all identify 0.9.1 |
| Historical receipt isolation | Pass; no diff under Issue #107 or Issue #109 |
| Candidate sensitive-data scan | Pass; no private path, user identifier, private-key marker, or credential-value pattern found |

## GitNexus Evidence

The installed index initially reported fresh at repository HEAD
`03bfbe9b30eb7fb8553be54a0ac27131289503d1`.

The first bare `gitnexus analyze` encountered a pre-existing inconsistency in
the ignored, reproducible full-text index. It exited without changing tracked
worktree state, `AGENTS.md`, the ignored generated instruction file, or the
ignored provider-skill files.

A forced full rebuild restored a known-good ignored index. A subsequent bare
`gitnexus analyze` succeeded with zero changed, added, or deleted source files.
Before/after hashes for the repository instruction and provider-skill files
were identical across both the rebuild and bare retry.

The initial unstaged GitNexus `detect_changes` run classified the tracked
candidate as low risk with no affected execution flows. After all Issue #111
files were staged, the final run covered 14 changed files and 39 changed
symbols, remained low risk, and found no affected execution flows.

The initial index inconsistency is a derived-index maintenance event, not
evidence of a tracked repository regression. No raw analyzer log or
machine-local path is retained in this receipt.

## Re-runnable Commands

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-gitnexus-config.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_gitnexus_config_guard \
  tests.test_pr_issue_link
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

## Residual Risk

- The ready-PR linkage workflow and Issue metadata must still be verified on
  GitHub after the branch is pushed.
- Exact-head deep merge review must still run after the final PR head is known.
- Tag creation, GitHub Release publication, and local installed-skill update
  remain outside this receipt and require their separate human gates.
