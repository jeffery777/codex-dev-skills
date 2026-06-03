---
description: Verify whether prior review findings were closed by the latest follow-up changes.
---

# review-follow-up-review

Runtime compatibility: shared

## Purpose

Use this skill after follow-up fixes to check closure without running an unnecessarily broad full review.

## Workflow

1. Read prior review findings, follow-up plan or reply, current diff, and verification evidence.
2. Check each targeted finding against actual files, not only summaries.
3. Classify closure as closed, partial, open, regression, or needs human decision.
4. Look for adjacent regressions in touched code paths or docs sections.
5. Recommend next action.

## Output

- Closure matrix
- Evidence checked
- New findings, if any
- Verification gaps
- Recommended next action

## Rules

- Do not silently close findings because evidence is missing.
- Distinguish not reproduced from verified fixed.
- Escalate to deep review when the follow-up changes security, data, migration, or public contract behavior.
