# Codex Runtime Compatibility Evidence — 2026-08-28

This is point-in-time compatibility evidence for Issue #192. It records
official OpenAI documentation, local public Codex CLI help, public Desktop
bundle metadata, and callable schemas exposed to the active Codex Desktop
task. It does not read or commit Desktop databases, logs, sessions, caches,
credentials, app state, local plugin caches, memory files, or machine-local
configuration.

## Observed Runtime

| Surface | Observation | Classification |
| --- | --- | --- |
| Standalone Codex CLI | `codex-cli 0.150.1` | Local public command output from `/opt/homebrew/bin/codex`; this is the CLI adapter surface. |
| ChatGPT Desktop app | `26.820.80927` (`CFBundleVersion` `7271`) | Local public application bundle metadata; not a stable callable API version. |
| Desktop-bundled Codex CLI | `codex-cli 0.150.0-alpha.8` | Local public command output from the Desktop application bundle; not assumed equal to the standalone CLI. |
| Desktop task tools | Active callable schemas described below | Current-session contract evidence; schema version is unavailable unless a result explicitly provides one. |

These observations are independent. The repository must not collapse the
standalone CLI, Desktop application, and Desktop-bundled CLI into one global
runtime-version assertion. Every adapter still capability-detects the surface
it actually uses.

## Official Documentation Baseline

Official OpenAI documentation continues to define skills as a shared workflow
format available in the ChatGPT desktop app and Codex CLI, with
`$HOME/.agents/skills` as the documented user-level filesystem discovery
location. Plugins remain a separate distribution lifecycle shared across
ChatGPT and Codex. See [Build skills](https://learn.chatgpt.com/docs/build-skills)
and [Package your plugin](https://developers.openai.com/plugins/build/plugins).

Official [Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
continues to identify `codex exec` as the CLI automation entrypoint and
documents JSONL output, explicit sandbox selection, `--ignore-user-config`,
resume, and structured output. The repository's `cli-session-handoff` adapter
continues to use a smaller fixed `codex exec --json` boundary and does not adopt
unrelated interactive, remote, profile, approval-reviewer, or bypass flags.

Official [Codex app-server](https://learn.chatgpt.com/docs/app-server)
documentation describes a separate JSON-RPC integration family and states that
generated TypeScript or JSON Schema artifacts are specific to the Codex version
that generated them. This repository does not implement an app-server client,
daemon, sidecar, or SDK integration. The current runtime update does not create
a reason to add one.

## Observed Public CLI Surface

Local public help confirms that the standalone CLI retains:

- `codex exec`, including non-interactive start, exact-session `resume`, and
  exact-session `fork`;
- `codex agents` and `codex queue` as separate CLI session-control surfaces;
- `codex plugin` and `codex mcp` as runtime configuration and external-tool
  control planes;
- `codex app-server` as an experimental, separately versioned integration
  surface; and
- the deprecated `codex mcp-server` command, which is still present in this
  observed CLI.

The presence of `codex app`, `codex update`, remote app-server options,
`--strict-config`, `--approve-for-me`, `--dangerously-bypass-hook-trust`, and
`--thread-source` in public help does not expand the CLI adapter's authority or
fixed argv. No adapter change is required for those unrelated controls.

`codex mcp-server` exposes Codex itself as an MCP server and remains distinct
from Codex's MCP client configuration, external MCP servers, connectors,
plugins, and native Desktop task/thread tools. Its observed presence does not
define a removal date or reverse its documented deprecation.

## Active Desktop Callable Facts

The active callable schemas preserve separate project, thread, scheduling, and
display control planes:

- project discovery and task creation through `list_projects` and
  `create_thread`, including `project`, `projectless`, and
  `chatgptWorkCloud` targets;
- project `local` or `worktree` execution, with optional worktree
  `startingState` for an exact `working-tree` or caller-supplied branch/ref and
  `create-branch` only for an explicitly requested exact new branch name;
- same-directory or worktree `fork_thread`, with completed history only;
- `list_threads`, `list_archived_threads`, `read_thread`, and bounded
  `wait_threads` observation;
- `send_message_to_thread`, `handoff_thread`, `get_handoff_status`, archive,
  pin, title, and immutable sharing mutations;
- explicit navigation or display through `navigate_to_codex_page` and
  `open_in_codex`; and
- `automation_update`, with same-thread heartbeat as the default recurring
  path and cron reserved for explicitly standalone project work.

The active create/fork lifecycle still distinguishes an immediately usable
`threadId` from a queued `clientThreadId`. The identifiers are not
interchangeable. Host-sensitive follow-up preserves a runtime-returned
`hostId`; it does not infer locality from the current UI or a filesystem path.

These descriptions are current-session evidence, not a published stable schema.
They do not authorize a live session/thread mutation, sharing action,
or private runtime-state inspection. They also do not authorize commit, push,
PR creation, merge, release, deployment, or any other external write.

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
4. The filesystem installer and universal plugin remain separate distribution
   paths; one Codex profile uses only one path for this skill pack.
5. Historical `desktop_runtime_*` wrappers are inactive. They are not an
   app-server migration path and must not be imported, executed, or
   recommended.

## Validation Observations

The compatibility assessment exposed two repository-validation reliability
issues rather than runtime-interface incompatibilities:

- ignored `__pycache__/*.pyc` files from retired Desktop wrapper sources can
  make a live-checkout source-inventory test report a false reintroduction; and
- a concurrent fresh-continuation loser can fail closed as
  `continuity_replay_state_unavailable` when an operating-system durability
  operation fails, in addition to the ordinary busy, conflict, or idempotent
  replay classifications.

The source inventory should ignore Python cache/bytecode artifacts while still
rejecting matching source or directory artifacts. Concurrent tests must retain
the exactly-one-winner invariant and verify that every loser classification
stops before a CLI session call.

## Compatibility Decisions

1. Preserve the shared-core/thin-adapter architecture and independent CLI and
   Desktop entrypoints.
2. Record standalone CLI, Desktop application, and Desktop-bundled CLI versions
   independently.
3. Keep current adapters on documented public CLI or active native callable
   boundaries; add no app-server, SDK, daemon, or private-state path.
4. Stabilize the repository validation baseline before Issue #186 shards the
   complete suite behind the existing aggregate check.
