# Next Session Prompt

Use `task-continuation` for this bounded continuation task.

## Task

- Task id: `<task-id>`
- Objective: `<bounded-objective>`

## Read First

Re-read these repository files before editing. If these files conflict with this prompt, trust the repository files and report the conflict.

- `<path>`

## Handoff Summary

This summary is context only, not source of truth.

`<current-task-summary>`

## Scope

In scope:

- `<item>`

Out of scope:

- `<item>`

## Files

Files to inspect:

- `<path>`

Files expected to change:

- `<path>`

## Definition Of Done

- `<done-criterion>`

## Verification

- `<command>`

## Stop Conditions

Stop and report before editing or continuing if you encounter source-of-truth conflict, product ambiguity, scope expansion, destructive action, external write, public contract change, data model or migration risk, auth, permission, privacy, payment, security, deployment, or insufficient verification for a high-risk change.

## Rules

- Do not commit.
- Do not push, publish, merge, deploy, or perform destructive actions.
- Do not edit outside assigned scope.
- Treat summaries and chat history as context only.
- Report changed files, verification run, skipped checks, risks, and open questions.
