---
description: Codex Desktop delegated project delivery entrypoint for bounded objectives.
---

# desktop-project-delivery

Runtime compatibility: desktop

## Purpose

Use this skill in Codex Desktop when the user delegates a bounded delivery objective and expects main-agent ownership through planning, worker delegation, integration, review, docs sync, and PR readiness or the next human gate.

## CLI Fallback

Use `project-delivery` and `project-orchestrator` with prompts, task briefs, continuation prompts, or a sequential execution path. Use separate implementation and review passes in the current CLI session or in maintainer-run sessions. Use `code-review`, `code-review-deep`, or `docs-review` for ordinary integrated output review evidence; use formal gate adapters only for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions.

## Workflow

1. Main agent bootstraps from durable repo artifacts and git state.
2. Main agent uses `project-orchestrator` to define scope, ownership, phase plan, verification, and human gates.
3. Workers receive bounded task briefs and must not commit, publish, merge, or perform destructive actions.
4. Main agent integrates worker output, checks ownership, runs verification, and collects review evidence through `code-review`, `code-review-deep` for high-risk code or mixed changes, or `docs-review`.
5. Main agent runs `desktop-implementation-gate` only for formal Desktop integration before commit readiness, and runs `code-review-gate` or `docs-review-gate` only for formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decisions.
6. Main agent reports readiness or stops for human decision.

## Output

- Delivery status
- Worker ownership summary
- Integrated changes
- Verification evidence
- Review evidence
- Formal gate results, when a readiness or repo-policy gate was run
- Next human gate
