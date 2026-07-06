---
name: desktop-spec-plan-gate
description: Codex Desktop gate for spec, plan, and DoD drafts before implementation delegation.
---

# desktop-spec-plan-gate

Runtime compatibility: desktop

## Purpose

Use this skill before Desktop implementation work when the project needs a reviewed spec, implementation plan, or DoD.

## CLI Fallback

Use `planning` and request user confirmation before implementation when ambiguity remains.

## Workflow

1. Read existing specs, docs, repo policy, and current state.
2. Delegate drafting only when the runtime supports it.
3. Main agent reviews drafts for scope, source-of-truth alignment, risk, and testability.
4. Stop for user confirmation if product semantics, public API, data model, or migration behavior is unclear.

## Output

- Spec/plan status
- DoD
- Risks
- Open questions
- Implementation readiness decision
