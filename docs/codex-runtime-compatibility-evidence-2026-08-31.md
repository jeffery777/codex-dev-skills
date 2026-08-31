# Codex Runtime Compatibility Evidence — 2026-08-31

This is point-in-time compatibility evidence for the maintained runtime
contract. It records official OpenAI documentation, local public Codex CLI
help, public Desktop bundle metadata, and callable schemas exposed to the
active Codex Desktop task. It does not read or commit Desktop databases, logs,
sessions, caches, credentials, app state, local plugin caches, memory files,
or machine-local configuration.

## Evidence Classes

| Class | Establishes | Does not establish |
| --- | --- | --- |
| Official OpenAI documentation | Published concepts and documented public interfaces at the verification date. | Availability in every installed build or a permanently stable local schema. |
| Local public CLI output/help | Commands, options, usage, version output, and read-only JSON shapes exposed by the observed executable. | Permission to start, resume, fork, or otherwise mutate a session. The plugin-list query still reads isolated local runtime state. |
| Public Desktop bundle metadata | Application and bundled-executable versions from the installed public bundle. | A Desktop callable API version or private runtime state. |
| Active callable schema | Request and response fields offered to this task by the current Desktop runtime. | A published stable contract, successful mutation, or repository completion. |

## Observed Runtime

| Surface | Observation | Classification |
| --- | --- | --- |
| Standalone Codex CLI | `codex-cli 0.151.0` | Local public command output from the PATH-selected standalone executable; this is the CLI adapter surface. |
| ChatGPT Desktop app | `26.825.51511` (`CFBundleVersion` `7377`) | Local public application bundle metadata; not a stable callable API version. |
| Desktop-bundled Codex CLI | `codex-cli 0.151.0-alpha.7.2` | Local public command output from the Desktop application bundle; not assumed equal to the standalone CLI. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless a result explicitly provides one. |

These observations are independent. The repository must not collapse the
standalone CLI, Desktop application, and Desktop-bundled CLI into one global
runtime-version assertion. Every adapter still capability-detects the surface
it actually uses.

## Official Documentation Baseline

Official OpenAI [Build skills](https://learn.chatgpt.com/docs/build-skills)
documentation defines skills as a shared workflow format for ChatGPT and
Codex. It documents repository discovery from `.agents/skills` while walking
from the current directory to the repository root, user discovery from
`$HOME/.agents/skills`, admin discovery from `/etc/codex/skills`, and system
skills bundled by OpenAI. Same-name skills are not merged, so duplicate
filesystem and plugin installations remain a collision risk.

Official [Package your plugin](https://developers.openai.com/plugins/build/plugins)
documentation requires `.codex-plugin/plugin.json`. A plugin may package
skills, MCP server configuration, registered MCP server mappings, assets, and
lifecycle hooks. Installation or enablement does not automatically trust
non-managed plugin hooks; the user must review and trust the current hook
definition. This distribution lifecycle remains separate from local skill
authoring and discovery.

Official [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
documentation identifies `codex exec` as the CLI automation entrypoint.
`--json` emits JSONL events including `thread.started`, turn terminal events,
item events, and errors; `codex exec resume <SESSION_ID>` continues a known
session. Observed public help additionally retains `codex exec fork
<SESSION_ID>`. The repo adapter keeps its smaller fixed start/resume/fork argv
and does not adopt unrelated flags or broader authority.

Official [Codex app-server](https://learn.chatgpt.com/docs/app-server)
documentation describes a separate JSON-RPC integration family. Generated
TypeScript and JSON Schema artifacts are specific to the Codex version that
generated them. Official [MCP server](https://learn.chatgpt.com/docs/mcp-server)
documentation separately marks `codex mcp-server` deprecated and points new
integrations to app-server. This does not deprecate Codex MCP client
configuration, external MCP servers, connectors, plugins, or native Desktop task/thread tools.

Official [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
documentation requires `name`, `description`, and `developer_instructions` in
standalone custom-agent TOML files. Supported inherited or explicit session
configuration includes `model`, `model_reasoning_effort`, `sandbox_mode`,
`mcp_servers`, and `skills.config`. Runtime model and reasoning availability
still require current-session preflight.

## Observed Public CLI Surface

Public help for both observed CLI executables retains these shapes:

- `codex exec [OPTIONS] [PROMPT]`, with `resume`, `fork`, `review`, and `help`
  subcommands and `--json` JSONL output;
- `codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]`, with exact identifier,
  `--last`, and `--json` forms;
- `codex exec fork [OPTIONS] <SESSION_ID> [PROMPT]`, with a required source
  identifier and `--json`;
- `codex plugin list --json`, returning an object with `installed` and
  `available` arrays; and
- plugin lifecycle commands for add, list, remove, and marketplace management.

Observed installed plugin entries carry identity, version, installed/enabled
state, source, marketplace, and policy fields. The JSON contains machine-local
paths and installation state, so this evidence records only the public shape,
not the local values. The public-help smoke likewise asserts the shape without
persisting the output.

`codex app-server` exposes its own daemon/proxy/schema-generation and transport
surface. `codex mcp-server` exposes Codex as an MCP server over stdio. `codex
mcp` configures MCP clients and servers used by Codex. Plugins package reusable
skills and optional MCP integrations. These command families are not aliases
and are not interchangeable with native Desktop callables.

No live `codex exec --json` start, resume, or fork was run for this refresh.
Such a smoke would create runtime session state and may call a live model, so it
remains a separately authorized, human-gated follow-up rather than default
repository validation.

## Active Desktop Callable Facts

The active callable schemas preserve separate project, thread, scheduling,
display, and sidebar-organization control planes. Existing project/thread
semantics remain available through `list_projects`, `create_thread`,
`fork_thread`, `list_threads`, `list_archived_threads`, `read_thread`,
`wait_threads`, `send_message_to_thread`, `handoff_thread`,
`get_handoff_status`, `share_thread`, `navigate_to_codex_page`,
`open_in_codex`, and `automation_update`.

Project-scoped creation still selects `local` or `worktree` execution. A
worktree target may omit `startingState` for the default branch, use
`working-tree` only when explicitly requested, or name an exact branch/ref.
Immediate and queued lifecycle results continue to use `threadId` and
`clientThreadId` respectively.

The active schema also exposes sidebar organization operations:

- `create_sidebar_section`, `rename_sidebar_section`, and
  `delete_sidebar_section`;
- `move_thread_to_sidebar_section` and `move_project_to_sidebar_section`;
- `reorder_section`, `reorder_sidebar_projects`, and
  `reorder_sidebar_sections`; and
- `list_threads` and `list_projects` as the read-only identity/discovery
  surfaces used before an organization mutation.

These descriptions are current-session evidence, not a published stable schema.
No sidebar mutation was executed. This refresh does not implement a sidebar section mutation contract or broaden `desktop-thread-delegation`; a future
Desktop-only thin adapter should first classify exact target identity,
complete-list reorder preconditions, mutation authority, response shape, and
fallback behavior.

The active create/fork lifecycle still distinguishes an immediately usable
`threadId` from a queued `clientThreadId`. The identifiers are not
interchangeable. These callables do not authorize a live session/thread mutation, sharing action,
or private runtime-state inspection. Sidebar mutation is likewise not
authorized. They also do not authorize commit, push, PR creation, merge,
release, deployment, or any other external write.

## Layering Assessment

No production adapter or shared-core change is required by the observed
runtime update:

1. Shared planning, delivery, review, human-gate, Goal, and subagent semantics
   remain capability-neutral.
2. `cli-session-handoff` remains the CLI-only bounded session adapter over the
   public non-interactive surface.
3. `desktop-project-delivery` and `desktop-thread-delegation` remain thin
   Desktop-only task/thread/worktree/scheduling entrypoints over the shared
   layer.
4. Sidebar organization remains an observed Desktop-only callable family and
   a future adapter topic, not part of this implementation.
5. The filesystem installer and universal plugin remain separate distribution
   paths; one Codex profile uses only one path for this skill pack.
6. Historical `desktop_runtime_*` wrappers are inactive. They are not an
   app-server migration path and must not be imported, executed, or
   recommended.

## Reproducible Public Checks

These commands are read-only public-interface checks. They do not include a
prompt, session identifier, or live JSONL invocation:

```sh
codex --version
codex --help
codex exec --help
codex exec resume --help
codex exec fork --help
codex plugin list --json
codex plugin --help
codex app-server --help
codex mcp-server --help
```

Public Desktop bundle metadata and the bundled executable can be checked with
the platform's plist reader and the bundled CLI's `--version`/`--help` forms.
Do not inspect Desktop databases, logs, sessions, caches, credentials, app
state, or unpublished internals.

## Compatibility Decisions

1. Preserve the shared-core/thin-adapter architecture and independent CLI and
   Desktop entrypoints.
2. Record standalone CLI, Desktop application, and Desktop-bundled CLI versions
   independently.
3. Keep current adapters on documented public CLI or active native callable
   boundaries; add no app-server, SDK, daemon, or private-state path.
4. Keep the new public-help smoke read-only and shape-based. Missing Codex CLI
   produces a clear test skip; no live model or session smoke is part of the
   default suite.
5. Defer sidebar mutation semantics to a separately scoped, Desktop-only thin
   adapter decision.
