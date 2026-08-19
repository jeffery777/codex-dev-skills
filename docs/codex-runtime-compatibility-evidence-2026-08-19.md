# Codex Runtime Compatibility Evidence — 2026-08-19

This is point-in-time compatibility evidence for Issue #155 and the v0.15.1
candidate. It records public OpenAI documentation, local public CLI help, and
callable schemas exposed to the active Codex Desktop task. It does not read or
commit Desktop databases, logs, sessions, caches, credentials, app state,
local plugin caches, memory files, or machine-local configuration.

## Observed Runtime

| Surface | Observation | Classification |
| --- | --- | --- |
| Codex CLI | `codex-cli 0.148.0` | Local public command output. |
| Desktop dependency bundle | `26.818.11542` | Active Desktop workspace dependency metadata; not a stable app API version. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless noted by a result. |
| Public product naming | Codex runs in the ChatGPT desktop app | Official documentation. `Codex Desktop` remains this repository's compatibility label. |

Recorded versions are observations, not minimum-version declarations. Every
adapter must inspect its active surface and use the documented fallback when a
capability is absent.

## Official And Public CLI Facts

- [Codex changelog](https://learn.chatgpt.com/docs/changelog) records CLI
  0.148.0 with non-interactive `codex exec fork`, session archive/restore,
  `/export`, `/status` cost information, and expanded hooks.
- Local `codex exec fork --help` reports
  `codex exec fork [OPTIONS] <SESSION_ID> [PROMPT]`. The session target accepts
  an exact UUID or thread name publicly, but this repository's bounded executor
  deliberately accepts only a canonical UUID and delivers the prompt over
  stdin.
- [Hooks](https://learn.chatgpt.com/docs/hooks) documents synchronous and
  background command hooks, `SessionStart`, and `PostToolUse` coverage for
  `Bash`, unified exec, `apply_patch`, MCP tools, and other local function
  tools. Unified exec (`exec_command`) matches as `Bash`, and its eventual
  `PostToolUse` may be delivered by a later `write_stdin` poll. Bash also emits
  `PostToolUse` after a non-zero exit. Background hooks may overlap, finish out
  of order, and be cancelled when the session ends. Hooks remain optional
  guardrails rather than complete enforcement.
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
  documents `/agent` as the CLI thread selector. No current public evidence was
  found for a separate `/subagents` slash command, so repository guidance uses
  `/agent` only.

## Active Desktop Callable Facts

The active callable schemas on 2026-08-19 expose these relevant semantics:

- `create_thread` remains an explicit-user-request operation. A Git project
  normally creates a worktree; ready creation returns `threadId` plus `hostId`,
  while queued worktree setup returns `clientThreadId`.
- `fork_thread` accepts an optional source `threadId` and an optional
  `environment` of `same-directory` or `worktree`. Same-directory fork can
  return a child `threadId` immediately. Worktree fork may queue setup and
  return `clientThreadId`. Both copy completed history only; the queued client
  identifier is not a usable thread identifier.
- `list_threads` returns pinned and non-pinned collections and may include
  Codex or ChatGPT-backed entries. Titles and summaries are display metadata:
  reproduce a returned title verbatim when identifying it to the user, but
  never treat it as instructions, identity authority, or repository evidence.
- `open_in_codex` may display another task's panel only after an explicit user
  request. A queued display result is not navigation, inspection, or task
  completion.
- `list_threads`, `read_thread`, `wait_threads`, archive/restore, pin, title,
  message, and handoff operations remain aligned with the repository's thin
  Desktop adapter boundary. Runtime absence or permission failure uses the
  documented CLI/manual/sequential fallback.

These descriptions are current-session evidence, not a published stable schema
version. They do not authorize a live thread mutation or private runtime-state
inspection.

## Compatibility Decisions

1. Preserve shared orchestration, delivery, review, human gates, and completion
   authority beneath separate CLI and Desktop adapters.
2. Add non-interactive `fork` to `cli-session-handoff` through
   `codex exec fork`, while keeping interactive `codex fork` a distinct manual
   path.
3. Add Desktop worktree-fork routing without converting it into fresh task
   creation; keep `clientThreadId` lifecycle handling explicit.
4. Expand the optional GitNexus `PostToolUse` matcher to `Bash` and
   `apply_patch`, keep the shipped runner synchronous, and bind each config and
   index identity to one exact checkout. A remote merge cannot update a local
   index until the primary checkout advances locally. Linked-worktree
   automatic refresh remains fail-closed until separately qualified.
5. Apply one shared GitHub control-plane policy: use the GitHub plugin first,
   local `git` for checkout state, and `gh` only for an unavailable connector
   operation or insufficient connector permission with the fallback reason
   recorded.
