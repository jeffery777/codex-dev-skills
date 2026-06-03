---
description: Codex Desktop main-agent orchestration building block for software delivery projects.
---

# desktop-project-orchestrator

Runtime compatibility: desktop

## Purpose

Use this skill when the main agent needs to organize a Desktop project across spec, plan, implementation, integration, review, and handoff.

## CLI Fallback

Use `planning`, `implementation-slice`, and review gates sequentially with explicit handoff notes.

## Workflow

1. Discover source-of-truth files and current state.
2. Define phase plan, ownership boundaries, and verification.
3. Delegate only bounded tasks.
4. Review worker output before integration.
5. Run `desktop-implementation-gate` before commit readiness.
6. Run `desktop-pr-merge-gate` before PR or merge readiness.

## Output

- Phase plan
- Delegation map
- Integration status
- Gate decisions
- Human decisions needed
