# Issue #111 Post-Bootstrap PR Linkage Evidence

Status: live post-bootstrap check passed

Authority: traceability evidence only

## Purpose

Issue #111 is the first eligible real release PR after the linkage workflow
entered `main` through PR #110. This receipt records the live post-bootstrap
check without treating CI as completion, review, merge, or release authority.

## Live Evidence

- Ready PR: #112.
- Initial checked head:
  `a22d7a47ae54ac9533eed2a93ac0f0b478d3573c`.
- Base revision:
  `03bfbe9b30eb7fb8553be54a0ac27131289503d1`.
- PR body: contains one standalone `Closes #111` line.
- Issue metadata: #111 was open and did not contain GitHub's `pull_request`
  marker.
- Event: `pull_request_target`.
- Check: `Validate closing Issue` completed successfully in 7 seconds.
- Run:
  <https://github.com/jeffery777/codex-dev-skills/actions/runs/29992649038>
- Job:
  <https://github.com/jeffery777/codex-dev-skills/actions/runs/29992649038/job/89158725888>

The live job completed the named `Check out trusted base revision` and
`Validate PR-to-Issue linkage` steps successfully. The base workflow grants
only read access to `contents`, `issues`, and `pull-requests`, checks out the
event base SHA, disables persisted credentials, and does not check out or
execute pull-request head code.

The receipt update changes the PR head and therefore triggers another linkage
run. The final-head check result is accepted GitHub platform state and must be
confirmed immediately before exact-head merge review; it is not copied back
into this self-referential receipt.

## Expected Boundary

The check may prove that the ready PR names an open same-repository Issue. It
cannot prove implementation, verification, review closure, completion, merge
readiness, authorization, tag readiness, or release readiness.

This receipt must be updated only from accepted GitHub metadata after the live
ready PR exists. Raw workflow logs, tokens, private paths, and machine-local
state must not be copied into the repository.

## Non-Blocking Platform Annotation

GitHub reported that the pinned checkout action targets Node.js 20 and was
forced to run on Node.js 24. The job passed, and the action remains pinned by
full commit SHA, so this does not block the v0.9.1 release closure. A separate
post-release guardrail maintenance Issue should update the pinned checkout
action after the replacement SHA and workflow behavior receive the same
security review. Promotion trigger: before GitHub removes forced compatibility
for the current action runtime.
