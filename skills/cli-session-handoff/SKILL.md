---
name: cli-session-handoff
description: Thin Codex CLI session control adapter for one bounded non-interactive start, resume, fork, or fresh continuation, a callable-selected native TUI create/fork, or one manual interactive fork, dashboard, or queued message, already selected by shared orchestration.
---

# cli-session-handoff

Runtime compatibility: cli

## Entry And Operation Selection

Use this thin CLI control-plane adapter after shared orchestration has selected
a bounded task and the user explicitly wants the CLI session action. It does
not choose tasks, replace shared subagents, or control Desktop tasks. The
originating session owns integration, verification, review, and completion.

先依 `../../docs/native-runtime-capabilities.md` 的 Thread Capability Discovery
核對正式清單與可用的 deferred discovery；filesystem 安裝使用
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/docs/native-runtime-capabilities.md`。
初始缺少不等於 unavailable；不可觀察時保留 unknown。CLI/TUI 原生工具依完整
namespace/schema 選取，不能因 SSH、OS 或同名工具而套用 Desktop payload。

Read only the reference for the selected operation before acting:

| Operation | Use when | Required reference |
| --- | --- | --- |
| `tui-thread-create`, `tui-thread-fork` | 當次公開 callable 確認為原生 TUI 契約 | [Native TUI](references/native-tui.md) |
| `start` | New bounded session in a clean private clone | [Non-interactive](references/non-interactive.md) |
| `resume` | Continue the exact known public session UUID | [Non-interactive](references/non-interactive.md) |
| `fork` | Copy completed history into a new public session UUID | [Non-interactive](references/non-interactive.md) |
| `fresh-continuation` | Shared assessment selected fresh rollover | [Fresh continuation](references/fresh-continuation.md) and [Non-interactive](references/non-interactive.md) |
| `interactive-fork` | Manual same-task fork in the selected existing directory | [Interactive fork](references/interactive-fork.md) |
| `agents-dashboard`, `manual-queue`, `doctor` | Requested manual session control or diagnosis | [Dashboard, queue, diagnosis](references/dashboard-queue.md) |

Inspect active public CLI help and the installed executor's request shape;
point-in-time documentation does not override the executable's capabilities.
Reuse unchanged scope/authority evidence already established in this session.
A request marker cannot grant authority. Do not ask again merely to confirm a
tool name or unchanged action that the user already explicitly requested.

## Invariants

- Verify the exact task, repository, expected head, executable, sandbox,
  session identity, readiness, and ownership before the operation. Return to
  shared orchestration if any is ambiguous or work overlaps another writer.
- Shell executor operations require a clean worktree and use the private-clone
  executor. Only `read-only` or already-authorized `workspace-write` is allowed.
  Source identity must be rechecked before applying a bounded child patch.
- Resume/fork identifiers come from public CLI events and must be exact UUIDs,
  never display names or `--last`. CLI session IDs are not Desktop `threadId`
  or `clientThreadId` values. Native TUI IDs follow their own reference.
- Child prompts prohibit recursive session dispatch and preserve repository
  environment, verification, and publication boundaries. Missing pinned
  runtime/dependencies are verification blockers, not permission to switch
  interpreters or install elsewhere.
- No interactive UI automation, private session files, unpublished APIs,
  direct app-server/remote-control calls, caller-started daemons, or sidecars.
  `codex agents` may own its documented runtime-managed daemon connection;
  this grants no permission to control that daemon directly.
- Do not pass arbitrary flags, model overrides, extra writable roots,
  environment overrides, approval bypasses, or `danger-full-access`.
- Tests use fake executables and never create a live session. A live smoke,
  commit, push, PR, merge, release, or deployment needs its own required gate.

## Result And Fallback

Report the operation, result classification, public session UUID when emitted,
terminal event/exit status, observed CLI version and executable digest without
machine-local paths, exact target head and redacted workspace label. Preserve
the fixed omission marker for untrusted child summaries. Report additional
operation-specific evidence from the selected reference only when applicable.

Dispatch, manual command preparation, and runtime completion are distinct from
repository completion. Independently inspect and verify the target diff before
accepting a child result. On capability or validation failure, return the
prepared prompt as a manual artifact or continue in the current session.

Stop for absent authority, ambiguous identity, overlapping writers, unsupported
runtime semantics, sensitive/destructive/publication requests, permission
widening, or a required human gate. Interactive-fork dirty-worktree eligibility
and queue message/quoting restrictions are in their mandatory references.
