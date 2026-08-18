---
name: task-continuation
description: Select the next safe task from durable project context, prepare a bounded continuation prompt or task brief, and stop at human gates when continuation is unsafe.
---

# task-continuation

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill when a larger bounded project is underway and Codex needs to continue safely by choosing the next task, preparing a continuation prompt or task brief for another session, worker, or sequential execution path, and preserving enough verified handoff context without treating chat memory as source of truth.

This shared skill prepares continuation artifacts and may route disjoint bounded
packets to shared subagents when supported. It does not guarantee opening a new
user-owned Codex task or conversation; that is a runtime control-plane action.

## Workflow

1. Re-bootstrap from durable repository files: repo instructions, project specs, plans, task manifests, status docs, review evidence, policies, templates, and git state.
2. Identify canonical task states. Represent safety concerns as `blocked` with a
   safety blocker kind; use `unknown` only as a discovery classification before
   materializing canonical state.
3. Compare chat or handoff summaries against repository files. Treat summaries as context only.
4. Select the smallest ready task that advances the bounded objective without expanding scope.
5. Choose the recommended execution mode:
   - `continue-current-session`
   - `new-session-prompt`
   - `shared-subagent`
   - `cli-session-handoff`
   - `desktop-task-handoff`
   - `stop-for-human-gate`
6. Prepare a continuation prompt or task brief when continuation is safe.
7. Route `cli-session-handoff` only when the user explicitly authorized one
   bounded CLI session mutation and the active CLI adapter can validate the
   exact executable, worktree, Git head, sandbox, and session identifier.
8. Require the next session or worker to re-read source-of-truth files before editing.
9. Stop for a human decision when continuation would cross a gate.

## Stop Conditions

Stop instead of preparing executable continuation when there is source-of-truth conflict, product ambiguity, scope expansion, destructive action, external write, public contract change, data model or migration risk, auth, permission, privacy, payment, security, deployment, or insufficient verification for a high-risk change.

## Output

- Current state facts
- Inferences and uncertainty
- Candidate tasks by status
- Recommended next task
- Recommended execution mode
- Continuation prompt or task brief, if safe
- Current task summary, if useful
- Required source-of-truth files for the next agent to read
- Verification, review primitive, and formal gate requirements for the current stage
- Human gate, if any

## Templates

Use these templates when a target repository needs durable continuation artifacts:

- `../../templates/orchestration/task-manifest.template.yaml` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/task-manifest.template.yaml`
- `../../templates/orchestration/task-continuation-report.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/task-continuation-report.template.md`
- `../../templates/orchestration/next-session-prompt.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/next-session-prompt.template.md`
- `../../templates/orchestration/current-task-summary.template.md` or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/current-task-summary.template.md`
