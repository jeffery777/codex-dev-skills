# Task Continuation Report

## Source Of Truth Read

- `<path>`

## Current State Facts

- `<verified-fact>`

## Inferences And Uncertainty

- `<inference-or-unknown>`

## Candidate Tasks

| Task | Status | Risk | Notes |
| --- | --- | --- | --- |
| `<task-id>` | `<planned | ready | in_progress | blocked | reviewing | done | accepted | cancelled | unknown>` | `<low | medium | high>` | `<include blocker kind such as safety when applicable>` |

## Recommended Next Task

- Task: `<task-id>`
- Objective: `<bounded-objective>`
- Execution mode: `<continue-current-session | shared-subagent | new-session-prompt | desktop-task-handoff | stop-for-human-gate>`; describe CLI fallback in prose as a prompt, task brief, continuation prompt, or sequential execution path.
- Reason: `<why-this-is-the-smallest-safe-next-task>`

## Required Context For Next Agent

- Source-of-truth files to read first:
  - `<path>`
- Current task summary:
  - `<context-only-summary>`

## Verification And Gates

- Verification:
  - `<command>`
- Review primitive:
  - `<code-review | docs-review | code-review-deep | none>`
- Formal gate:
  - `<code-review-gate | docs-review-gate | none>`
- Formal gate trigger:
  - `<commit readiness | PR readiness | merge readiness | explicit repo-policy blocking decision | none>`
- Human gate:
  - Required: `<true | false>`
  - Reason: `<reason-if-required>`

## Residual Risk

- `<risk>`
