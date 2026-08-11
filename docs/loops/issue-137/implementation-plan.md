# Issue #137 Implementation Plan

## Task Slices

### R0 — Baseline And Collision Check

Re-fetch main, read Issue #137, verify current release/tag state, confirm the
working tree, and search for release ownership collisions before branching.

### R1 — Release Record Alignment

Finalize v0.12.0 release notes, README current-release text, roadmap/program
status, and the release metadata contract test. Preserve catalog and installer
version 0.12.0 unless authoritative evidence shows drift.

### R2 — Verification And Review

Run the pinned Python preflight, focused release tests/evals, full unit suite,
repository validation, installer/package reads, shell syntax, diff hygiene,
privacy scans, docs review, deep security/privacy review, formal docs/release
gate, and exact-head merge review.

### R3 — Draft PR Readiness

Commit and push the reviewed release candidate, open a draft PR linked to
Issue #137, replace the release-notes PR placeholder with the assigned PR URL,
rerun affected checks, and prove hosted CI and remote exact-head equality.

### R4 — Human Merge And Publication Gate

Present the exact base/head, verification, review, CI, tag-absence, release
body, and recovery evidence. After explicit authorization, transition ready,
wait for ready-triggered CI, merge using expected-head SHA, re-fetch main,
create/push annotated tag v0.12.0, publish the non-draft/non-prerelease GitHub
Release, and independently verify public tag/Release state.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Main claims publication without a Release | Merge only as part of the approved merge/tag/Release sequence. |
| Existing or moved tag | Recheck local and remote tag absence; never overwrite or move. |
| Release includes unimplemented roadmap work | Label Issue #135 / PR #136 planning-only and preserve all later gates. |
| Stale PR traceability | Add the assigned PR URL before final review. |
| Hidden release regression | Run focused, full, repository, installer, privacy, and hosted checks. |
| Recovery becomes destructive | Stop for a new human decision; never delete or rewrite implicitly. |

## Rollback

Before publication, revert only the bounded release candidate through a normal
reviewed change. After publication, never move/delete the tag or delete the
Release without a separate recovery decision. Rolling back installed content
is out of scope and must not overwrite machine-local modifications.
