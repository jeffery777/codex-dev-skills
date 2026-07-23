# Issue #111 Implementation Plan

## Objective

Close repository-side v0.9.1 release readiness and leave an accurate
Operational Evidence handoff while preserving all authority, privacy, and
publication boundaries.

## Task Slices

### P0 — Version And Release Alignment

- Update `install.sh` and `catalog.yaml` to `0.9.1`.
- Set the release date and make README current-release references consistent.
- Update roadmap completion and next-feature sequencing.

### P1 — Operational Evidence Handoff

- Add Issue #109 guardrails to the program baseline and Phase 0 deliverables.
- Make Phase 0 exit criteria include Issues #107/#109, formal gates, linkage
  evidence, and the formal v0.9.1 release.
- Distinguish the Issue #111 release closure from the later V2d-A Issue.

### P2 — Verification And Formal Gates

- Run focused and full repository tests, shell/config validation, repository
  validation, diff hygiene, version consistency, and privacy checks.
- Confirm `.gitnexusrc` remains exact and bare analysis does not rewrite
  instruction or provider files.
- Run GitNexus change detection and formal mixed/code, docs, and release
  readiness reviews.
- Record only bounded, rerunnable evidence under Issue #111.

### P3 — Ready PR And Post-Bootstrap Evidence

- Commit and push the reviewed candidate.
- Open a ready PR with a standalone `Closes #111` line.
- Confirm the linkage job uses trusted base code, read-only permissions, and
  resolves #111 as an open Issue rather than a PR.
- Record the first post-bootstrap run, push the evidence-only update, and
  confirm the final-head checks.
- Run exact-head `merge-review-deep`, post the review result, and merge using
  the expected head SHA.

### P4 — Separate Release Gate

- Report the merged `main` SHA, proposed `v0.9.1` tag, release notes path,
  verification/review evidence, residual risk, and recovery method.
- Stop for explicit approval before tag creation or GitHub Release
  publication.
- Inspect installed-skill status and differences only after the release, then
  update one explicitly confirmed discovery root.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Release metadata claims V2d is implemented | State that V2c-B remains the feature baseline and V2d-A is next. |
| Historical evidence is rewritten | Restrict new receipts to `docs/loops/issue-111/`. |
| Linkage CI is mistaken for authority | Preserve the policy boundary in docs and receipts. |
| A PR number is accepted instead of an Issue | Verify GitHub metadata for #111 and the live linkage check. |
| Public files leak local data | Run candidate privacy/path/credential scans and inspect the diff. |
| Tag or release is published prematurely | Stop after merge at the separate tag/release human gate. |

## Rollback

Revert the bounded release-closure commit without resetting unrelated work.
If v0.9.1 has already been installed, inspect `./install.sh diff --all` before
selecting a prior release; do not overwrite modified local skills or config.
Tag or release recovery, if later needed, must target the exact published
object and follow a separate explicit decision.
