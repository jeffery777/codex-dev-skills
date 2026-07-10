---
name: project-orchestrator
description: Shared project orchestration layer that routes bounded work across planning, implementation, review, continuation, handoff, or human gates.
---

# project-orchestrator

Runtime compatibility: shared

## Purpose

Use this skill when Codex needs to decide how to advance a bounded project or task: handle it as a single implementation slice, plan first, delegate or hand off, run review, prepare continuation, or stop for a human gate.

This skill is the shared orchestration layer for Codex CLI and Codex Desktop.
It may use bounded shared subagents when the runtime supports them and ownership
is disjoint. Desktop user-owned task/thread/worktree actions remain a separate
runtime adapter. When a capability is unavailable, use the current session,
prompts, task briefs, continuation prompts, or a sequential execution path.

## Routing Rules

- If the task is already a single clear implementation slice, use `implementation-slice` semantics and do not over-plan.
- If the user delegates a larger bounded delivery objective, select `project-delivery` as the outer workflow.
- If already operating inside `project-delivery`, select the next phase or slice instead of routing back to `project-delivery`.
- If source-of-truth or task order is unclear, use `planning`, `closure-triage`, or `task-continuation`.
- If ordinary review evidence is needed, route code or mixed changes to `code-review`, high-risk code or mixed changes to `code-review-deep`, and docs-only or docs-dominant changes to `docs-review`.
- If a formal blocking decision is required for commit readiness, PR readiness, merge readiness, or repo policy, route through `code-review-gate` or `docs-review-gate`.
- If review findings need closure, route fixes through the smallest primitive workflow: `implementation-slice` for code or mixed changes, `docs-update` for docs-only changes, then rerun the relevant review primitive or formal gate for the current stage.
- Review closure loops default to 2 rounds unless the user or repo policy sets a different maximum.
- If the next unit should move to another session or worker, prepare a bounded continuation prompt or task brief.
- Stop when a human gate is required.

## Workflow

1. Discover source-of-truth files and current state.
2. Classify the request as a single task, bounded delivery objective, review, follow-up, continuation, or safety-blocked/ambiguous work.
3. Select the smallest safe next action and the appropriate skill or workflow.
4. Choose execution mode: current session, shared subagents, sequential fallback, Desktop control-plane handoff, or stop for human decision.
5. Integrate or inspect results before advancing.
6. Run relevant verification and the review primitive or formal gate that matches the current stage.
7. Prepare continuation or readiness evidence when useful.

## Output

- Request classification
- Selected next action
- Execution mode
- Skill or workflow routed to
- Verification and review or gate result
- Handoff or continuation prompt, if useful
- Human gate, if any
