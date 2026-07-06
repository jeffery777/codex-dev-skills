---
name: implementation-slice
description: Implement a bounded software change after read-only inspection, then verify and inspect the diff.
---

# implementation-slice

Runtime compatibility: shared

## Purpose

Use this skill for a focused implementation task where the target behavior is clear.

## Workflow

1. Read repo instructions, relevant files, tests, and current git state when available.
2. Identify affected files and likely verification before editing.
3. Make the smallest scoped change that satisfies the objective.
4. Avoid unrelated refactors and do not overwrite unrelated user changes.
5. Run the smallest relevant verification.
6. Inspect the diff before reporting.

## Commit Behavior

Do not commit unless the user explicitly asks for a commit or repo policy clearly requires it and the human gate is satisfied.

## Output

- Changed files
- Behavior changed
- Verification run
- Skipped verification, if any
- Residual risk
