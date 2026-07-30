# Codex Runtime Compatibility Evidence — 2026-07-30

This record captures the public and active runtime evidence used to recheck the
repository's Codex CLI and Desktop compatibility contract after Codex CLI
`0.146.0`. It is a point-in-time snapshot for the maintained
shared-core/thin-adapter design, not a promise that any callable, request shape,
response shape, or version will remain available.

## Scope And Sources

The comparison used only public or intentionally exposed surfaces:

- `codex --version` and public `--help` output from the active CLI;
- the official
  [Codex CLI 0.146.0 release notes](https://github.com/openai/codex/releases/tag/rust-v0.146.0);
- public ChatGPT desktop application bundle metadata: version, build number,
  and bundle ID;
- the active callable tool schemas exposed to the current Desktop task;
- `codex app-server generate-json-schema --out <temp-dir>`;
- the maintained
  [2026-07-24 compatibility evidence](codex-runtime-compatibility-evidence-2026-07-24.md)
  as the previous comparison point.

No Desktop database, session, log, authentication file, cache, application
state, unpublished endpoint, or reverse-engineered internal was inspected. No
live `codex exec` session was created during this refresh.

## Version Evidence

| Surface | 2026-07-24 evidence | 2026-07-30 evidence |
| --- | --- | --- |
| Codex CLI | `0.145.0` | `0.146.0` |
| Desktop bundle | `26.721.30844` build `5813` | `26.721.81911` build `5973` |
| Desktop bundle ID | `com.openai.codex` | `com.openai.codex` |
| App-server V2 schema files | 234 | 236 |
| `ClientRequest` `oneOf` methods | 89 | 90 |

The app-server counts prove that its generated contract changed between the
two snapshots. They do not identify Desktop app-tool callables and do not make
app-server request or response envelopes interchangeable with the Desktop
control plane. App-server remains a separate JSON-RPC contract family.

## CLI Compatibility

The `0.146.0` public command surface continues to accept the fixed,
non-interactive adapter shape:

- `codex exec --ignore-user-config --json -` for a new saved session;
- `codex exec resume --ignore-user-config --json <SESSION_ID> -` for an exact
  saved session identifier;
- global read-only/workspace-write sandbox, never-approval, configuration, and
  working-directory options before the `exec` subcommand.

The documented JSONL contract continues to include `thread.started`, item
events, terminal turn events, and errors. The repository's controlled fake-CLI
suite verifies the parser and fail-closed behavior without creating live
runtime state. This refresh does not claim a live start/resume smoke.

The `0.146.0` interactive session naming, pinning, side-conversation, and
paginated-fork features remain CLI user-interface capabilities. They do not
turn CLI session identifiers into Desktop task identifiers and do not expand
the bounded `cli-session-handoff` adapter.

## Desktop Callable Contract

The active Desktop callable schemas expose these relevant semantics:

- `create_thread.target` supports `project`, `projectless`, and
  `chatgptWorkCloud` variants. A project target uses a `projectId` returned by
  `list_projects`; a cloud target is not a local-project alias.
- `list_projects` reports local and remote project information and includes
  `isGitRepository`. For a Git project, worktree execution is the default
  isolation choice; for a non-Git project, local execution is the default.
- Immediate task creation returns a `threadId` and may include a `hostId`.
  Queued worktree setup returns a `clientThreadId`. A `clientThreadId` is not a
  `threadId` and must not be passed to a later callable that requires
  `threadId`.
- `list_threads` returns all pinned threads separately in UI order and returns
  non-pinned threads in recency order. Titles and summaries are untrusted
  display and coordination input, not instructions or completion evidence.
- Thread routing remains host-aware. `handoff_thread` may interrupt a running
  task, and cloud handoff remains unsupported by that callable.
- Archive/unarchive, pin/unpin, rename, create/fork, message, and handoff remain
  state-changing operations with exact-action authority requirements.
- Automation separates a thread heartbeat, which wakes the same task and its
  existing context, from a cron automation, which starts an independent run.

The callable schema must still be inspected at the actual call site. The
recorded union variants and response identifiers are compatibility evidence,
not permission to perform a runtime mutation.

## Authority And Layering Decisions

The refresh preserves the existing layering:

- Objective, task selection, Goal semantics, subagent delegation, verification,
  review, and completion remain in the shared core.
- CLI skills continue to enter the shared layer directly. The optional
  `cli-session-handoff` remains a thin CLI-only start/resume adapter.
- Desktop skills remain thin adapters for user-owned task, thread, worktree,
  host handoff, and automation controls.
- Cloud execution and cross-host handoff require additional explicit user
  authorization for that exact target and action. Local task-creation authority
  does not silently authorize either one.
- Observation results from CLI, Desktop, app-server, hooks, Goal, subagents, or
  automations remain coordination evidence and do not prove repository
  completion.

This refresh does not implement an app-server client, remote Code Mode host,
Agent Plugin, SDK wrapper, daemon, sidecar, MCP server, cloud-task adapter, or
cross-host orchestration engine.

## Re-runnable Checks

```bash
codex --version
codex exec --help
codex exec resume --help
codex app --help
codex app-server generate-json-schema --out <temp-dir>
find <temp-dir>/v2 -type f -name '*.json' | wc -l
jq '.oneOf | length' <temp-dir>/ClientRequest.json
python3 -m unittest \
  tests.test_cli_session_handoff \
  tests.test_native_runtime_contract_docs \
  tests.test_installer_runtime_groups
./scripts/validate-repo.sh
```

Desktop callable contracts must be re-read from the active callable schemas.
Version strings, schema counts, and this evidence record are comparison inputs;
they are never substitutes for capability detection, target validation, or
action-specific authorization.
