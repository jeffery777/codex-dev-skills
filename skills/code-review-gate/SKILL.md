---
name: code-review-gate
description: Formal code review gate before commit, PR readiness, or merge readiness.
---

# code-review-gate

Runtime compatibility: shared

## Purpose

Use this skill when code or mixed changes need a formal review gate before commit readiness, PR readiness, or merge readiness.

For ordinary user-requested code review, use `code-review`. This skill is a thin gate adapter: it routes to the appropriate review primitive, records evidence according to repo policy, and decides whether unresolved MUST-FIX findings block the gate.

## Workflow

1. Classify the diff as code, mixed, generated, or docs-dominant.
2. Use `code-review` for routine risk.
3. Escalate to `code-review-deep` for security, data, migration, packaging, dependency, external integration, or cross-module risk.
4. Write or summarize evidence according to repo policy.
5. Block commit or merge readiness on MUST-FIX findings.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Review Mode
- Findings
- Evidence
- Required Follow-up
