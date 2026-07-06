---
name: docs-update
description: Update project documentation from verified code, specs, plans, or behavior.
---

# docs-update

Runtime compatibility: shared

## Purpose

Use this skill when docs need to be aligned with implemented behavior, plans, or repository policy.

## Workflow

1. Read the relevant code, specs, README, docs, and current git state when available.
2. Separate verified facts from inferred behavior.
3. Update only the docs in scope.
4. Avoid adding private paths, credentials, local runtime state, or machine-specific assumptions.
5. Run lightweight verification such as link checks, markdown lint when available, or targeted text checks.

## Output

- Docs changed
- Source evidence used
- Verification run
- Any unverified assumptions
