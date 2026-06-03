---
description: Dry-run first cleanup workflow for review artifacts.
---

# review-artifact-cleanup

Runtime compatibility: shared

## Purpose

Use this skill to classify old review artifacts before cleanup.

## Rules

- Default mode is dry-run.
- Delete only exact paths classified as safe to delete.
- Never delete current review evidence, unresolved findings, source-of-truth docs, or artifacts referenced by open work.
- Apply mode requires explicit user confirmation.

## Workflow

1. Identify the review artifact root from repo policy or `.work/review/`.
2. List artifacts with timestamps, references, and current/latest status.
3. Classify as SAFE_TO_DELETE, KEEP, or NEEDS_EXPLICIT_OVERRIDE.
4. In dry-run, report only.
5. In apply mode, delete only confirmed SAFE_TO_DELETE exact paths.

## Output

- Mode
- Classified paths
- Reason for each classification
- Action taken or skipped
