---
description: Shared project orchestration layer that routes bounded work across planning, implementation, review, continuation, handoff, or human gates.
---

# project-orchestrator

Runtime compatibility: shared

## Purpose

Use this skill when Codex needs to decide how to advance a bounded project or task: handle it as a single implementation slice, plan first, delegate or hand off, run review, prepare continuation, or stop for a human gate.

This skill is the shared orchestration layer for Codex CLI and Codex Desktop. It may use Desktop worker delegation only when the runtime supports it. In Codex CLI, it must execute sequentially in the current session or prepare durable handoff artifacts such as task briefs or next-session prompts.

## Routing Rules

- If the task is already a single clear implementation slice, use `implementation-slice` semantics and do not over-plan.
- If the user delegates a larger bounded delivery objective, select `project-delivery` as the outer workflow.
- If already operating inside `project-delivery`, select the next phase or slice instead of routing back to `project-delivery`.
- If source-of-truth or task order is unclear, use `planning`, `closure-triage`, or `task-continuation`.
- If review evidence is needed, route code or mixed changes to `code-review-gate` and docs-only changes to `docs-review-gate`.
- If the next unit should move to another session or worker, prepare a bounded task brief or next-session prompt.
- Stop when a human gate is required.

## Workflow

1. Discover source-of-truth files and current state.
2. Classify the request as a single task, bounded delivery objective, review, follow-up, continuation, or unsafe/ambiguous work.
3. Select the smallest safe next action and the appropriate skill or workflow.
4. Choose execution mode: current session, sequential CLI handoff, Desktop worker delegation, or stop for human decision.
5. Integrate or inspect results before advancing.
6. Run relevant verification and review gates.
7. Prepare continuation or readiness evidence when useful.

## Output

- Request classification
- Selected next action
- Execution mode
- Skill or workflow routed to
- Verification and review gate
- Handoff or continuation prompt, if useful
- Human gate, if any
