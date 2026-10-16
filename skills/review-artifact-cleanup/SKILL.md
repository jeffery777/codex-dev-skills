---
name: review-artifact-cleanup
description: Dry-run first cleanup workflow for review artifacts.
---

# review-artifact-cleanup

Runtime compatibility: shared

Artifact lifecycle: follow `../../policies/review-artifact-policy.md` in source
or plugin, or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/review-artifact-policy.md`
after filesystem installation. That policy loads the full fixed Core workflow
and authorization/stops; read before classification or action.

## Purpose

Use this skill to classify old review artifacts before cleanup.

## Rules

- Default mode is dry-run.
- SAFE_TO_DELETE is only a candidate label after replacement coverage and
  effective retention/protection/reference checks; it grants no authority.
- Missing retention policy/period means KEEP and pending, not immediate cleanup.
- Preserve unresolved/intermittent, shared/still-referenced and security/data-loss
  evidence; unrelated PASS or context slimming cannot retire it.
- Never delete current review evidence, unresolved findings, source-of-truth docs, or artifacts referenced by open work.
- Apply mode requires exact operation authority. Irreversible deletion requires
  confirmation at action time for exact targets/impact; prior plan approval is
  insufficient. Higher-priority retention/protection duties still apply.

## Workflow

1. Identify the review artifact root from repo policy or `.work/review/`.
2. List artifacts with timestamps, sharing/references, retention/protection
   requirements and current status. Verify replacement covers the original failure
   and affected boundaries; keep cause/fix/old-new revisions/scope/outcome/readable
   replacement reference in an existing report/index. Missing originals are unverified.
3. Classify as SAFE_TO_DELETE, KEEP, or NEEDS_EXPLICIT_OVERRIDE.
4. In dry-run, report only.
5. In apply mode, act only on eligible exact paths under the policy above,
   preview/dry-run and action-time authority; if any requirement is missing, keep
   the artifact and report pending. No cleanup is implied by classification.

## Output

- Mode
- Classified paths
- Reason for each classification
- Action taken or skipped
