---
name: code-review-gate
description: Formal code review gate before commit, PR readiness, or merge readiness.
---

# code-review-gate

Runtime compatibility: shared

## Purpose

Use this skill when code or mixed changes need a formal review gate before commit readiness, PR readiness, or merge readiness.

For ordinary user-requested code review, use `code-review`. This skill is a thin gate adapter: it routes to the appropriate review primitive, records evidence according to repo policy, and decides whether every finding has a durable disposition.

## Workflow

1. Classify the diff as code, mixed, generated, or docs-dominant.
2. Use `code-review` for routine risk.
3. Escalate to `code-review-deep` for security, data, migration, packaging, dependency, external integration, or cross-module risk.
4. Give every MUST-FIX, SHOULD-FIX, and NIT a stable finding id and one disposition: `Fixed`, `Deferred`, `Rejected`, or `Needs Human Decision`.
5. Record each disposition according to repo policy. A deferred finding requires a durable target, owner, reason, remaining risk, verification plan, and promotion trigger that says when it becomes blocking.
6. Rerun the underlying review after fixes and verify the disposition record against the final diff.
7. Block commit or merge readiness when any MUST-FIX remains unresolved, any finding lacks a durable disposition, a deferred item lacks its required follow-up fields, or a `Needs Human Decision` item remains open.

NITS are non-blocking only after they are fixed, explicitly rejected with rationale, or durably deferred. They must not disappear from the gate result.

## Output

- Gate Result: PASS | BLOCKED | NEEDS HUMAN DECISION
- Review Mode
- Findings
- Finding Dispositions
- Evidence
- Required Follow-up
