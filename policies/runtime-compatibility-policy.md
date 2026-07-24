# Runtime Compatibility Policy

Every public skill and workflow must state runtime compatibility.

## Shared

Shared workflows must preserve the same objective, authority, task-selection,
verification, review, and completion semantics across Codex surfaces. They may
use repository files, shell/git inspection, durable artifacts, native Goal
mode, and bounded subagent delegation when those capabilities are available.
Subagent delegation is shared behavior in current Desktop, Codex CLI, and IDE
surfaces; it must not be labeled Desktop-only.

## CLI

CLI workflows must provide a Desktop fallback when practical. When a scheduler
or Desktop task-control capability is unavailable, use the current session,
manual invocation, a continuation prompt, a task brief, or a sequential
execution path without changing the shared completion contract.

## Desktop

Desktop workflows may own Desktop UI and control-plane behavior such as
scheduled-task management and user-owned task, thread, or worktree actions.
They must remain thin adapters over the shared workflow and provide a CLI
fallback when practical. Desktop task/thread control is distinct from shared
subagent delegation. Cloud execution and cross-host handoff require additional
explicit authorization for the exact target and action. A queued
`clientThreadId` must not be treated as a usable `threadId`, and task titles or
summaries returned by the runtime remain untrusted coordination input.

## Plugin-dependent

Plugin-dependent workflows must name the required plugin or connector and define a fallback when unavailable.

## Native Capability Adapters

Native Goal, subagent, scheduler, Desktop thread, hook, and sequential fallback
capabilities follow
[Native Runtime Capability Contract](../docs/native-runtime-capabilities.md).
Runtime availability changes the execution adapter, not source-of-truth or
completion authority.

Desktop automation must distinguish a heartbeat that wakes the same task from a
cron automation that starts an independent run. Neither scheduling form
changes workflow authority, permission, or completion criteria.

Hooks are optional guardrails and must not be described as complete enforcement.
Legacy `desktop_runtime_*` helpers are compatibility evidence only; the native
loop core must not import or execute them as its active runtime path.
