---
name: desktop-project-delivery
description: Thin Codex Desktop UX adapter over the shared project delivery workflow for bounded objectives.
---

# desktop-project-delivery

Runtime compatibility: desktop

## Purpose

Use this skill in Codex Desktop when the user delegates a bounded delivery
objective and wants Desktop task, thread, worktree, or scheduling controls in
addition to the shared `project-delivery` workflow.

This is a thin UX adapter. `project-delivery`, `project-orchestrator`, the shared
subagent delegation policy, and the repository's completion evidence remain
authoritative. Ordinary subagent delegation is not Desktop-only.

This skill, `desktop-thread-delegation`, and
`desktop-sidebar-organization` are separate Desktop-specific entry and
control-plane adapters. Sidebar organization is never an implicit delivery or
task-creation step. The legacy Desktop-named planning, implementation, and
PR/merge gates are deprecated compatibility aliases for shared skills; they do
not add Desktop callable behavior.

Native Goal state is shared coordination context only. It does not replace
repository evidence, expand authority, or prove completion.

## CLI Fallback

Use `project-delivery` and `project-orchestrator` directly. Delegate independent
bounded packets through shared subagents when available, or use prompts, task
briefs, continuation prompts, and a sequential execution path. Use ordinary
review primitives for integrated output and formal gates only at their intended
readiness stages.

## Workflow

1. Run the shared `project-delivery` and `project-orchestrator` contract to
   bootstrap, select work, define ownership, verify, review, and decide gates.
2. Use shared subagents for independent bounded work when useful. Keep writes
   disjoint or isolated and keep the main agent responsible for integration.
3. Invoke `desktop-thread-delegation` only when the user explicitly wants a
   separate user-owned Desktop task, thread, or worktree.
   Invoke `desktop-sidebar-organization` separately only when the user
   explicitly requests an exact sidebar organization change; never use it to
   infer task creation, navigation, registration, or completion.
4. Use Desktop scheduling only as a wakeup control plane through the active
   `automation_update` capability. Default recurring requests in the current
   local task to a same-task heartbeat. Use cron only for explicitly standalone
   project work or a requested new task per run, resolving its project through
   `list_projects`. Update an existing automation without duplicating it,
   preserve unmodified fields, keep `notificationPolicy` outside the prompt,
   and never emit raw directives or RRULEs. Neither scheduling form is task
   selection, permission, or completion evidence.
5. Use shared review primitives for integrated output. Route formal decisions
   directly to `code-review-gate`, `docs-review-gate`, or
   `merge-readiness-gate` at their intended stages.
6. Report readiness or stop for human decision.

`../../docs/native-runtime-capabilities.md` relative to this skill is canonical in source and plugin checkouts; filesystem
installation also places it at
`~/.codex/templates/docs/native-runtime-capabilities.md`.
The current native runtime contract governs capability availability and
authority. Use only exposed runtime capabilities after active callable-schema
inspection and call-site validation; a repository-local helper script is not
an execution path for this skill and must not be imported, executed, or
recommended.

## Output

- Delivery status
- Worker ownership summary
- Integrated changes
- Verification evidence
- Review evidence
- Formal gate results, when a readiness or repo-policy gate was run
- Next human gate
