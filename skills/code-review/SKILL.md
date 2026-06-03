---
description: Routine read-only review for code or mixed diffs, focused on bugs, regressions, risk, and missing tests.
---

# code-review

Runtime compatibility: shared

## Purpose

Use this skill for routine review of working-tree, branch, or patch changes.

## Rules

- Review mode is read-only.
- Findings lead the response.
- Prioritize correctness, regressions, missing tests, contract risk, security baseline issues, and operational risk.
- Do not declare readiness only because tests pass.

## Workflow

1. Inspect repo instructions and current state.
2. Identify the diff range or changed files.
3. Read the changed code and relevant call sites.
4. Check tests or evidence that cover the changed behavior.
5. Report findings with file and line evidence.

## Output

- Executive Summary
- MUST-FIX
- SHOULD-FIX
- NITS
- Questions
- Re-runnable Verification Commands
