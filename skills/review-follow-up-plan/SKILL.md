---
description: Build a read-only follow-up plan from review findings, questions, and verification gaps.
---

# review-follow-up-plan

Runtime compatibility: shared

## Purpose

Use this skill after code, docs, or merge review identifies findings that need triage before implementation.

## Workflow

1. Read the latest review report, current git state, relevant source files, and any prior follow-up notes.
2. Classify each item as must-fix, should-fix, question, nit, deferred, withdrawn, or needs human decision.
3. Preserve finding IDs when available.
4. Recommend the smallest safe execution order.
5. List verification needed for each item.

## Output

- Source artifacts used
- Finding classification table
- Recommended fix order
- Questions for the user
- Verification checklist
- Stop conditions

## Rules

- Do not edit files.
- Do not mark an item closed without evidence.
- Do not invent fixes that are not grounded in reviewed findings.
