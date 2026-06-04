---
description: Select the next safe task from durable project context, prepare a bounded next-session prompt or worker brief, and stop at human gates when continuation is unsafe.
---

# task-continuation

Runtime compatibility: shared

## Purpose

Use this skill when a larger bounded project is underway and Codex needs to continue safely by choosing the next task, preparing a prompt for another session or worker, and preserving enough verified handoff context without treating chat memory as source of truth.

This shared skill prepares continuation artifacts. It does not guarantee opening a new Codex conversation. Automatic session creation is runtime-specific and requires Codex Desktop worker delegation, a CLI runner, MCP tool, plugin, or equivalent orchestrator.

## Workflow

1. Re-bootstrap from durable repository files: repo instructions, project specs, plans, task manifests, status docs, review evidence, policies, templates, and git state.
2. Identify completed, blocked, ready, unsafe, and unknown tasks.
3. Compare chat or handoff summaries against repository files. Treat summaries as context only.
4. Select the smallest ready task that advances the bounded objective without expanding scope.
5. Choose the recommended execution mode:
   - `continue-current-session`
   - `new-session-prompt`
   - `delegated-worker-brief`
   - `stop-for-human-gate`
6. Prepare a next-session prompt or worker brief when continuation is safe.
7. Require the next session or worker to re-read source-of-truth files before editing.
8. Stop for a human decision when continuation would cross a gate.

## Stop Conditions

Stop instead of preparing executable continuation when there is source-of-truth conflict, product ambiguity, scope expansion, destructive action, external write, public contract change, data model or migration risk, auth, permission, privacy, payment, security, deployment, or insufficient verification for a high-risk change.

## Output

- Current state facts
- Inferences and uncertainty
- Candidate tasks by status
- Recommended next task
- Recommended execution mode
- Next-session prompt or worker brief, if safe
- Current task summary, if useful
- Required source-of-truth files for the next agent to read
- Verification and review gate
- Human gate, if any

## Templates

Use these templates when a target repository needs durable continuation artifacts:

- `templates/orchestration/task-manifest.template.yaml`
- `templates/orchestration/task-continuation-report.template.md`
- `templates/orchestration/next-session-prompt.template.md`
- `templates/orchestration/current-task-summary.template.md`
