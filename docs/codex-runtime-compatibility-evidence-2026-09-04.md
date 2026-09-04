# Codex Runtime Compatibility Evidence — 2026-09-04

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
| Standalone Codex CLI | `codex-cli 0.153.2` | Local public command output from the PATH-selected standalone executable; this is the CLI adapter surface. |
| ChatGPT Desktop app | `26.901.22334` (`CFBundleVersion` `7746`) | Local public application bundle metadata; not a stable callable API version. |
| Desktop-bundled Codex CLI | `codex-cli 0.153.0` | Local public command output from the Desktop application bundle; not assumed equal to the standalone CLI. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless a result explicitly provides one. |

These observations are independent. The repository must not collapse the
standalone CLI, Desktop application, and Desktop-bundled CLI into one global
runtime-version assertion. Every adapter still capability-detects the surface
it actually uses.

## Official Documentation Baseline

Official OpenAI [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
documentation identifies `codex exec` as the CLI automation entrypoint.
`--json` emits JSONL events, and `codex exec resume <SESSION_ID>` continues a
known session. The page does not publish `codex exec fork` as part of that
stable contract. Standalone and Desktop-bundled public help nevertheless
expose `codex exec fork <SESSION_ID>` in the observed builds, so the repo
classifies that operation from public help rather than a documented stability
promise. This is an observed and locally qualified public-help surface.

Official OpenAI [Developer commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
documentation classifies the parent `codex exec` command as stable, `codex
app-server` as experimental, `codex doctor` as stable, and `codex mcp-server`
as deprecated. It documents the separate interactive `codex fork` command.
The repo-owned executor keeps its smaller fixed non-interactive
start/resume/fork argv, qualifies the active CLI through read-only help, and
fails closed if an invocation is unavailable or incompatible.

No exact official changelog entry for Codex CLI `0.153.2` was located during
this refresh. Version-specific conclusions therefore come from the observed
public executables and current official interface documentation, not from an
inferred release-note promise.

Official [Codex app-server](https://learn.chatgpt.com/docs/app-server)
documentation describes a separate JSON-RPC integration family. Generated
TypeScript and JSON Schema artifacts are specific to the Codex version that
generated them. The deprecation of `codex mcp-server` does not deprecate Codex
MCP client configuration, external MCP servers, connectors, plugins, or
native Desktop task/thread tools.

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

`codex app-server`, `codex mcp-server`, `codex mcp`, plugins, remote control,
and cloud commands remain distinct control planes. They are not aliases and
are not interchangeable with native Desktop callables. No live `codex exec
--json` start, resume, or fork was run; the real JSONL stream is therefore not
live-qualified by this evidence.

## Active Desktop Callable Facts

The active callable schemas preserve separate project, thread, scheduling,
display, and sidebar-organization control planes. Existing project/thread
semantics remain available through `list_projects`, `create_thread`,
`fork_thread`, `list_threads`, `list_archived_threads`, `read_thread`,
`wait_threads`, `send_message_to_thread`, `handoff_thread`,
`get_handoff_status`, `share_thread`, `navigate_to_codex_page`,
`open_in_codex`, `read_thread_terminal`, and `automation_update`.

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

Additional current callables include `set_thread_archived` and
`set_thread_title` for task metadata/lifecycle changes, plus account, voice,
workspace, and plugin helpers: `get_usage_limits`, `consume_usage_reset`,
`capture_screen_context`, `end_realtime_voice_call`,
`load_workspace_dependencies`, and `uninstall_plugin`. This inventory records
availability only. Those operations are not adopted into the repository's
thread adapters, and state-changing or voice-only callables retain their own
explicit authority and context requirements.

These descriptions are current-session evidence, not a published stable schema.
No Desktop list call or mutation was executed. Consequently, the prior
point-in-time `list_projects` `schemaVersion: 2` and `list_threads`
`schemaVersion: 4` response observations were not live-revalidated here. The
repo-owned `desktop-sidebar-organization` skill remains a separate Desktop-only
thin adapter with exact-target, dry-run, response-validation, readback,
reorder, and delete gates.

The active create/fork schema still distinguishes an immediately usable
`threadId` from a queued `clientThreadId`. The identifiers are not
interchangeable. These callables do not authorize a live session/thread mutation, sharing action,
or private runtime-state inspection. They also do not authorize commit, push,
PR creation, merge, release, deployment, or any other external write.

## Layering Assessment

No production adapter or shared-core change is required by the observed
standalone CLI update:

1. Shared planning, delivery, review, human-gate, Goal, and subagent semantics
   remain capability-neutral.
2. `cli-session-handoff` remains the CLI-only bounded session adapter over the
   documented start/resume surface plus the observed and locally qualified
   non-interactive fork surface.
3. `desktop-project-delivery`, `desktop-thread-delegation`, and
   `desktop-sidebar-organization` remain thin Desktop-only entry/control-plane
   adapters over the shared layer.
4. Newly observed Desktop helpers remain outside those adapters unless a
   separately scoped requirement and authority boundary is accepted.
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
codex plugin --help
codex debug models --bundled
codex app-server --help
codex mcp-server --help
```

Run the plugin JSON shape probe only through the repository's isolated public-
help smoke, which supplies temporary home, Codex, and XDG roots:

```sh
./scripts/project-python -m unittest \
  tests.test_cli_session_handoff.CodexPublicHelpCompatibilityTests
```

The same smoke builds the exact adapter argv and replaces only the final
prompt token with `--help`. Public Desktop bundle metadata and the bundled
executable can be checked with the platform's plist reader and the bundled
CLI's `--version`/`--help` forms. Do not inspect Desktop databases, logs,
sessions, caches, credentials, app state, or unpublished internals.

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
6. Keep newly observed task metadata, account, voice, workspace, and plugin
   helpers outside existing adapters until separately required and reviewed.
