# Codex Runtime Compatibility Evidence — 2026-09-01

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
| Standalone Codex CLI | `codex-cli 0.152.0` | Local public command output from the PATH-selected standalone executable; this is the CLI adapter surface. |
| ChatGPT Desktop app | `26.825.51511` (`CFBundleVersion` `7377`) | Local public application bundle metadata; not a stable callable API version. |
| Desktop-bundled Codex CLI | `codex-cli 0.151.0-alpha.7.2` | Local public command output from the Desktop application bundle; not assumed equal to the standalone CLI. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless a result explicitly provides one. |

These observations are independent. The repository must not collapse the
standalone CLI, Desktop application, and Desktop-bundled CLI into one global
runtime-version assertion. Every adapter still capability-detects the surface
it actually uses.

## Official Documentation Baseline

Official OpenAI [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
documentation identifies `codex exec` as the CLI automation entrypoint.
`--json` emits JSONL events including `thread.started`, turn terminal events,
item events, and errors; `codex exec resume <SESSION_ID>` continues a known
session. The detailed non-interactive documentation does not publish `codex
exec fork` as part of that stable contract. Standalone and Desktop-bundled
public help nevertheless expose `codex exec fork <SESSION_ID>` in the observed
builds, so the repo classifies that operation as an observed and locally
qualified public-help surface rather than a documented stability promise.
This is an observed and locally qualified public-help surface, not permission
to run it or a permanent compatibility guarantee.

Official [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
documentation classifies the parent `codex exec` command as stable and
documents the separate interactive `codex fork` command. The repo-owned
executor keeps its smaller fixed non-interactive start/resume/fork argv,
qualifies the active CLI through read-only help, and fails closed if an
invocation is unavailable or incompatible.

Official [Codex CLI 0.152.0 changelog](https://learn.chatgpt.com/docs/changelog)
records credential-refresh progress in `codex exec`, package-style MCP server
names, per-tool MCP output limits, configurable app-server shell-command
timeouts, and `tools.update_plan.enabled = true` as the opt-in for the planning
tool now disabled by default. The shared `planning` skill does not require the
runtime planning tool, and installation of this pack must not force-enable it.
The other additions belong to MCP or app-server control planes that the current
CLI session adapter does not implement.

Official [Hooks](https://learn.chatgpt.com/docs/hooks) documentation retains the
common `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`, and
`permission_mode` fields. Its `SessionStart` and `PostToolUse` tables retain the
event-specific fields consumed by the optional GitNexus hook runner, including
`source`, `turn_id`, `tool_name`, `tool_use_id`, `tool_input`, and
`tool_response`.

Official [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
documentation requires `name`, `description`, and `developer_instructions` in
standalone custom-agent TOML files. Supported inherited or explicit session
configuration includes `model`, `model_reasoning_effort`, `sandbox_mode`,
`mcp_servers`, and `skills.config`. Runtime model and reasoning availability
still require current-session preflight.

Official [Codex app-server](https://learn.chatgpt.com/docs/app-server)
documentation describes a separate JSON-RPC integration family. Generated
TypeScript and JSON Schema artifacts are specific to the Codex version that
generated them. Official [MCP server](https://learn.chatgpt.com/docs/mcp-server)
documentation separately marks `codex mcp-server` deprecated and points new
integrations to app-server. This does not deprecate Codex MCP client
configuration, external MCP servers, connectors, plugins, or native Desktop task/thread tools.

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

The public-help smoke also exercised the production-style global prefix and
fixed config keys used by `cli-session-handoff`: `--sandbox read-only`,
`--ask-for-approval never`, `shell_environment_policy.inherit="core"`,
`shell_environment_policy.ignore_default_excludes=false`, `--cd`,
`--ignore-user-config`, and `--json`. Appending `--help` to the generated
start, resume, and fork argv kept the check read-only while proving that the
active parser accepts the adapter's argument layout.

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
repository validation. The real JSONL stream is therefore not live-qualified
by this evidence.

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
No Desktop task or sidebar mutation was executed. The repo-owned
`desktop-sidebar-organization` skill remains a separate Desktop-only thin
adapter with exact-target, dry-run, response-validation, readback, reorder,
and delete gates; it does not broaden `desktop-thread-delegation` or the shared
workflow layer.

The active create/fork lifecycle still distinguishes an immediately usable
`threadId` from a queued `clientThreadId`. The identifiers are not
interchangeable. These callables do not authorize a live session/thread mutation, sharing action,
or private runtime-state inspection. Sidebar mutation is likewise not
authorized by observation alone. They also do not authorize
commit, push, PR creation, merge, release, deployment, or any other external
write.

## Layering Assessment

No production adapter or shared-core change is required by the observed
standalone CLI update:

1. Shared planning, delivery, review, human-gate, Goal, and subagent semantics
   remain capability-neutral. Missing `update_plan` capability uses ordinary
   plan output or repository artifacts rather than forcing runtime config.
2. `cli-session-handoff` remains the CLI-only bounded session adapter over the
   documented start/resume surface plus the observed and locally qualified
   non-interactive fork surface.
3. `desktop-project-delivery`, `desktop-thread-delegation`, and
   `desktop-sidebar-organization` remain thin Desktop-only entry/control-plane
   adapters over the shared layer.
4. The filesystem installer and universal plugin remain separate distribution
   paths; one Codex profile uses only one path for this skill pack.
5. Historical `desktop_runtime_*` wrappers are inactive. They are not an
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
codex debug models --bundled
codex app-server --help
codex mcp-server --help
```

The test suite additionally builds the exact adapter argv and replaces only
the final prompt token with `--help`. Public Desktop bundle metadata and the
bundled executable can be checked with the platform's plist reader and the
bundled CLI's `--version`/`--help` forms. Do not inspect Desktop databases,
logs, sessions, caches, credentials, app state, or unpublished internals.

## Compatibility Decisions

1. Preserve the shared-core/thin-adapter architecture and independent CLI and
   Desktop entrypoints.
2. Record standalone CLI, Desktop application, and Desktop-bundled CLI versions
   independently.
3. Keep start/resume on the documented stable non-interactive contract;
   qualify non-interactive fork from the active public help and fail closed if
   it is unavailable.
4. Keep current adapters on documented public CLI or active native callable
   boundaries; add no app-server, SDK, daemon, remote-control, or private-state
   path.
5. Keep public-help smoke read-only and shape-based. Missing Codex CLI produces
   a clear test skip; no live model or session smoke is part of the default
   suite.
6. Keep the Desktop sidebar adapter independent from CLI session control and
   shared completion semantics.
