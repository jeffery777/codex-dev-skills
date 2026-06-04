---
description: Codex Desktop delegated project delivery entrypoint for bounded objectives.
---

# desktop-project-delivery

Runtime compatibility: desktop

## Purpose

Use this skill in Codex Desktop when the user delegates a bounded delivery objective and expects main-agent ownership through planning, worker delegation, integration, review, docs sync, and PR readiness or the next human gate.

## CLI Fallback

Use `project-delivery` and `project-orchestrator` with generated task briefs and separate implementation/review passes.

## Workflow

1. Main agent bootstraps from durable repo artifacts and git state.
2. Main agent uses `project-orchestrator` to define scope, ownership, phase plan, verification, and human gates.
3. Workers receive bounded task briefs and must not commit, publish, merge, or perform destructive actions.
4. Main agent integrates worker output, checks ownership, runs verification, and routes review gates.
5. Main agent reports readiness or stops for human decision.

## Output

- Delivery status
- Worker ownership summary
- Integrated changes
- Verification evidence
- Review gate results
- Next human gate
