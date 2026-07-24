---
name: desktop-spec-plan-gate
description: Deprecated Desktop compatibility alias that routes spec, plan, and DoD work to the shared planning skill.
---

# desktop-spec-plan-gate

Runtime compatibility: desktop

Compatibility status: deprecated compatibility alias

## Purpose

This name is retained so existing prompts and installations continue to work.
It does not use a Desktop callable or define a Desktop-specific planning gate.
New callers should use the shared `planning` skill directly.

## CLI Fallback

Use `planning`. The behavior is the same because the authoritative capability
is shared.

## Workflow

1. Route the request to `planning` and preserve its assumptions, risks, DoD,
   verification strategy, and human gates.
2. Use shared subagents only under the shared delegation policy.
3. If a later step needs a user-owned Desktop task or worktree, invoke
   `desktop-thread-delegation` separately after shared orchestration selects the
   bounded handoff.
4. Stop for user confirmation if product semantics, public API, data model, or
   migration behavior is unclear.

## Output

- Spec/plan status
- DoD
- Risks
- Open questions
- Implementation readiness decision
- Compatibility route used: `planning`
