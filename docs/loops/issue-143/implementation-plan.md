# Issue #143 Implementation Plan

## Task Slices

### R0 — Baseline And Collision Check

Re-fetch main; verify Issue #143 ownership, worktree state, latest Release,
v0.13.0 tag/Release absence, and no open ownership collision before branching.

### R1 — Release Record Alignment

Set catalog/installer and release contract tests to 0.13.0; add final release
notes; align README, roadmap, release-readiness, and Operational Evidence
status/continuation without changing V3-B behavior or later-stage authority.

### R2 — Verification And Review

Run the tracked Python preflight, focused release tests/evals, full unit suite,
repository validation, installer/package reads, shell syntax, diff hygiene,
privacy scans, docs review, deep security/privacy review, and formal release
readiness.

### R3 — Draft PR And Exact-Head Gate

Commit and push the reviewed candidate, open a draft PR linked to Issue #143,
replace the release-notes PR placeholder, rerun affected checks, verify hosted
CI and remote equality, submit final review, transition ready, wait for the
ready-triggered CI, and merge using expected-head SHA.

### R4 — Tag And Release Publication

Re-fetch accepted main, verify the exact release merge and repeated v0.13.0
tag/Release absence, create and push an annotated tag without force, publish a
non-draft/non-prerelease GitHub Release from the finalized notes, and re-read
public main/tag/Release evidence.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Main claims publication without a Release | Merge only when the exact approved tag/Release sequence can follow. |
| Existing or moved tag | Recheck local and remote absence; never overwrite or move it. |
| Release overclaims V3-B or later stages | Bind every claim to Issue #141 / PR #142 and preserve explicit exclusions. |
| Version-source drift | Test catalog, installer, README, and release notes together. |
| Stale PR traceability | Add the assigned PR URL before final review. |
| Hidden regression | Run focused, full, repository, installer, privacy, security, and hosted checks. |
| Destructive recovery | Stop for a new human decision; never delete or rewrite implicitly. |

## Rollback

Before publication, revert only through a normal reviewed change. After
publication, never move/delete the tag or delete the Release without a separate
recovery decision. Installed-state rollback remains out of scope.
