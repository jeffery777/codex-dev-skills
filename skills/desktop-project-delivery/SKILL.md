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

This skill and `desktop-thread-delegation` are the Desktop-specific entry and
control-plane adapters. The legacy Desktop-named planning, implementation, and
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
4. Use Desktop scheduling only as a wakeup control plane. Distinguish a
   same-task heartbeat from an independent cron job, and do not treat either as
   task selection, permission, or completion evidence.
5. Use shared review primitives for integrated output. Route formal decisions
   directly to `code-review-gate`, `docs-review-gate`, or
   `merge-readiness-gate` at their intended stages.
6. Report readiness or stop for human decision.

The repository's `docs/native-runtime-capabilities.md` is canonical; filesystem
installation also places it at
`~/.codex/templates/docs/native-runtime-capabilities.md`.
Legacy `desktop_runtime_*` helpers are compatibility evidence only and are not
an active dependency of this skill.

## Output

- Delivery status
- Worker ownership summary
- Integrated changes
- Verification evidence
- Review evidence
- Formal gate results, when a readiness or repo-policy gate was run
- Next human gate
