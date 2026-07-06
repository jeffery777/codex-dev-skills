---
name: docs-review
description: Read-only review for docs-only or docs-dominant changes.
---

# docs-review

Runtime compatibility: shared

## Purpose

Use this skill when the changed surface is documentation.

## Review Focus

- accuracy against code, specs, or product behavior
- missing prerequisites or unsafe instructions
- confusing structure
- stale links or names
- private or machine-specific material
- unsupported claims

## Workflow

1. Inspect docs diff and relevant source evidence.
2. Separate correctness issues from style preferences.
3. Report blockers first.
4. Include verification commands when applicable.

## Output

- Executive Summary
- MUST-FIX
- SHOULD-FIX
- NITS
- Questions
- Re-runnable Verification Commands
