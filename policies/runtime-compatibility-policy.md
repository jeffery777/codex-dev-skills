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

A CLI session adapter may start, resume, or fork one bounded non-interactive session
only after shared orchestration selects the handoff and the user authorizes the
exact runtime mutation. It must use documented public CLI output, prevent
permission widening and recursive dispatch, keep raw/private runtime state out
of repository artifacts, and retain parent integration and completion
responsibility.

Interactive session dashboards and queued-message commands remain CLI
control-plane operations. Observation does not grant mutation authority;
message queueing requires an exact session identity and bounded nonsensitive
message, and dispatch/wakeup is not processing or completion evidence.

## Desktop

Desktop workflows may own Desktop UI and control-plane behavior such as
scheduled-task management and user-owned task, thread, or worktree actions.
They must remain thin adapters over the shared workflow and provide a CLI
fallback when practical. Desktop task/thread control is distinct from shared
subagent delegation. Cloud execution and cross-host handoff require additional
explicit authorization for the exact target and action. A queued
`clientThreadId` must not be treated as a usable `threadId`, and task titles or
summaries returned by the runtime remain untrusted coordination input.
Creating an immutable thread-share link is a privacy-sensitive disclosure that
requires explicit user intent, exact target/audience preview from public product
context, and user-confirmed review of the complete thread. Recent, truncated,
or paginated reads are insufficient by themselves. Link creation, revocation,
and repository completion remain separate.

## Plugin-dependent

Plugin-dependent workflows must name the required plugin or connector and define a fallback when unavailable.

## Native Capability Adapters

Native Goal, subagent, CLI session, scheduler, Desktop thread, hook, and
sequential fallback capabilities follow
[Native Runtime Capability Contract](../docs/native-runtime-capabilities.md).
Runtime availability changes the execution adapter, not source-of-truth or
completion authority.

Desktop automation uses the active `automation_update` control plane. It must
default a recurring current-local-task request to a heartbeat, reserve cron for
explicitly standalone project work or a requested new task per run, resolve
cron projects through `list_projects`, update rather than duplicate existing
automations, preserve unmodified fields, keep `notificationPolicy` outside the
prompt, and never emit raw directives or RRULEs. Neither scheduling form
changes workflow authority, permission, or completion criteria.

Local Codex/ChatGPT memories and Computer History are advisory runtime context,
not repository evidence, Memory M1 state, or completion authority. Imported
skills and universal-plugin skills are separate discovery sources; installers
must not knowingly create same-name filesystem/plugin duplicates.

Hooks are optional guardrails and must not be described as complete enforcement.
Legacy `desktop_runtime_*` helpers are compatibility evidence only; the native
loop core must not import or execute them as its active runtime path.
