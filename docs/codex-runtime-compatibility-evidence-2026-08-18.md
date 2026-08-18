# Codex Runtime Compatibility Evidence — 2026-08-18

This is point-in-time compatibility evidence for Issue #149 and the v0.14.1
candidate. It records public OpenAI documentation and callable schemas exposed
to the active Codex Desktop task. It does not read or commit Desktop databases,
logs, sessions, caches, credentials, app state, local plugin caches, memory
files, or machine-local configuration.

## Observed Runtime

| Surface | Observation | Classification |
| --- | --- | --- |
| Codex CLI | `codex-cli 0.147.0` | Local public command output. |
| Desktop dependency bundle | `26.813.12317` | Active Desktop workspace dependency metadata; not a stable app API version. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable. |
| Public product naming | Codex runs in the ChatGPT desktop app | Official documentation. `Codex Desktop` remains this repository's compatibility label. |

Recorded versions are observations, not minimum-version declarations. Every
adapter must inspect its active surface and use the documented fallback when a
capability is absent.

## Official Product Facts

- [Plugins](https://learn.chatgpt.com/docs/plugins) states that ChatGPT and
  Codex share a universal plugin directory. Codex CLI opens its plugin browser
  with `/plugins`; installed skills and tools become available to new sessions.
- [Build plugins](https://learn.chatgpt.com/docs/build-plugins) and
  [Package your plugin](https://developers.openai.com/plugins/build/plugins)
  require `.codex-plugin/plugin.json` at the plugin root and allow a skills-only
  plugin to keep bundled workflows under `skills/`. A repo-scoped marketplace
  lives at `$REPO_ROOT/.agents/plugins/marketplace.json`.
- [Import from another agent](https://learn.chatgpt.com/docs/import) states
  that Desktop can import supported setup from documented third-party agents,
  including one Desktop-only source, while CLI `/import` supports the
  documented CLI subset. Imports can include instructions, settings, skills,
  plugins, projects, and recent work; they leave existing setup in place. This
  makes duplicate skill-source review an installation concern, not a CLI
  session-handoff action.
- [Scheduled tasks](https://learn.chatgpt.com/docs/automations) distinguishes
  a scheduled task inside an existing chat, which reuses that chat's context,
  from standalone runs that create independent chats and may run across
  projects or worktrees. Scheduled tasks are unattended runtime wakeups and do
  not change repository authority.
- [Memories](https://learn.chatgpt.com/docs/customization/memories) describes
  local Codex memories under `$CODEX_HOME/memories/`, off by default, with
  chat-level `/memories` controls. These generated runtime files are distinct
  from this repository's `loop-memory-sqlite/v0` Memory M1 reference adapter.
- [Computer History](https://learn.chatgpt.com/docs/customization/computer-history)
  is individually opt-in, requires memories, currently uses macOS app/site
  activity, and stores generated files under
  `$CODEX_HOME/memories/extensions/skysight/`. Its content can be sensitive and
  prompt-injected, so it is advisory context only and must not be copied into
  repository evidence or Memory M1 automatically.
- [ChatGPT desktop app for Linux](https://learn.chatgpt.com/docs/linux/linux-app)
  is a preview for specified Ubuntu, Debian, and Fedora desktop releases on x64
  and ARM64. Computer Use is not yet available in that Linux preview. Runtime
  adapters must capability-detect instead of treating macOS behavior as the
  cross-platform baseline.

## Active Desktop Callable Facts

The active callable schemas on 2026-08-18 expose these relevant semantics:

- `automation_update` owns recurring automation creation, update, view, and
  deletion. A heartbeat attached to the current local task is the default for
  recurring requests. Standalone cron work is used only when each run is
  independent or explicitly project-scoped. Project cron uses
  `list_projects`. Existing automation fields are preserved on update,
  duplicates are avoided, notification preferences stay in
  `notificationPolicy`, and callers do not emit raw directives or RRULEs.
- `create_thread` requires explicit user intent. Project creation first uses
  `list_projects`; Git projects default to worktree and non-Git projects to
  local unless the user explicitly requests the saved checkout. Worktree
  `startingState` is optional and supports `working-tree`, or `branch` with an
  exact caller-supplied `branchName`. Omitted `onMissing` means `error`;
  `create-branch` is allowed only for the exact new branch the user requested.
  Omitting `startingState` starts from the project default branch.
- `list_archived_threads` provides paginated archived-task discovery and treats
  titles and summaries as untrusted display data.
- `open_in_codex` displays a file, browser, terminal, or review tab in a Codex
  panel. It is display-only and is distinct from task navigation, task
  registration, sidebar visibility, and repository completion.
- `read_thread_terminal` reads current app-terminal output for the active
  Desktop task. It is observation only and cannot replace command verification
  or repository evidence.

These tool descriptions are current-session evidence, not a published stable
schema version. If the active runtime does not expose one of them, use the
documented CLI/manual/sequential fallback and report the unavailable state.

## Compatibility Decisions

1. Keep `project-delivery`, task selection, subagent delegation, verification,
   review, human gates, and completion authority shared.
2. Keep `cli-session-handoff` limited to one selected CLI session mutation.
   `/plugins`, `/import`, and `/memories` are runtime configuration controls,
   not session-handoff operations.
3. Keep `desktop-project-delivery` and `desktop-thread-delegation` as thin
   Desktop adapters. Add current automation, starting-state, archived-task,
   panel, terminal, and Linux degradation semantics without adding a private
   runtime integration.
4. Package a narrow allowlisted export of the canonical tracked skills and
   required shared resources as one skills-only plugin while retaining the
   filesystem installer as a separate distribution path. Do not activate both
   paths for the same profile.
5. Treat ChatGPT/Codex memories and Computer History as untrusted advisory
   runtime context. They never prove repository facts, completion, review,
   Memory M1 qualification, or operation authority.
