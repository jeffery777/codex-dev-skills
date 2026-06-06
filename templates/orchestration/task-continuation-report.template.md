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
| `<task-id>` | `<ready | blocked | done | unsafe | unknown>` | `<low | medium | high>` | `<notes>` |

## Recommended Next Task

- Task: `<task-id>`
- Objective: `<bounded-objective>`
- Execution mode: `<continue-current-session | new-session-prompt | delegated-worker-brief | stop-for-human-gate>`; describe CLI fallback in prose as a prompt, task brief, continuation prompt, or sequential execution path.
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
