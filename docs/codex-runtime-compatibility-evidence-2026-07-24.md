# Codex Runtime Compatibility Evidence — 2026-07-24

This record captures the public and active runtime evidence used to refresh the
repository's Codex CLI and Desktop compatibility contract. It is a point-in-time
snapshot for the maintained shared-core/thin-adapter design, not a promise that
any callable, request shape, response shape, or version will remain available.

## Scope And Sources

The comparison used only public or intentionally exposed surfaces:

- `codex --version` from the active CLI;
- public application bundle metadata: version, build number, and bundle ID;
- the active callable tool schemas exposed to the current Desktop task;
- `codex app-server generate-json-schema --out <temp-dir>`;
- the maintained
  [2026-07-21 compatibility evidence](codex-runtime-compatibility-evidence-2026-07-21.md)
  as the previous comparison point.

No Desktop database, session, log, authentication file, cache, application
state, unpublished endpoint, or reverse-engineered internal was inspected.

## Version Evidence

| Surface | 2026-07-21 evidence | 2026-07-24 evidence |
| --- | --- | --- |
| Codex CLI | `0.144.6` | `0.145.0` |
| Desktop bundle | `26.715.52143` build `5591` | `26.721.30844` build `5813` |
| Desktop bundle ID | `com.openai.codex` | `com.openai.codex` |
| App-server V2 schema files | 228 | 234 |
| `ClientRequest` `oneOf` methods | 87 | 89 |

The app-server counts prove that its generated contract changed between the
two snapshots. They do not identify Desktop app-tool callables and do not make
app-server request or response envelopes interchangeable with the Desktop
control plane. App-server remains a separate JSON-RPC contract family.

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
- Thread routing is host-aware. `handoff_thread` may move work across hosts,
  and `get_handoff_status` observes the resulting operation. A handoff can
  interrupt a running task, so cross-host handoff is not a read-only routing
  convenience.
- `list_threads` may combine Codex tasks, ChatGPT tasks, and pinned tasks.
  Returned titles and summaries are untrusted display and coordination input;
  they must not be interpreted as instructions, authority, or proof of
  repository completion.
- Automation separates a thread heartbeat, which wakes the same task and its
  existing context, from a cron automation, which starts an independent run.

The callable schema must still be inspected at the actual call site. The
recorded union variants and response identifiers are compatibility evidence,
not permission to perform a runtime mutation.

## Authority And Layering Decisions

The refresh preserves the existing layering:

- Objective, task selection, Goal semantics, subagent delegation, verification,
  review, and completion remain in the shared core.
- Desktop skills remain thin adapters for user-owned task, thread, worktree,
  host handoff, and automation controls.
- Cloud execution and cross-host handoff require additional explicit user
  authorization for that exact target and action. Local task-creation authority
  does not silently authorize either one.
- `list_threads`, `read_thread`, `wait_threads`, `list_projects`, and
  `get_handoff_status` remain observation and coordination inputs when the
  active schema classifies the exact call as read-only. Their results are not
  repository completion evidence.
- Create, fork, message, handoff, archive, pin, rename, heartbeat, and cron
  mutations retain their exact-action authority gates.
- Codex CLI continues to use the shared current-session, subagent, task-brief,
  and continuation-prompt paths. It does not gain a Desktop callable merely
  because the generated app-server schema or Desktop app exposes related
  functionality.

This refresh does not implement an app-server client, SDK wrapper, daemon,
sidecar, MCP server, cloud-task adapter, or cross-host orchestration engine.

## Re-runnable Checks

```bash
codex --version
codex app-server generate-json-schema --out <temp-dir>
find <temp-dir>/v2 -type f -name '*.json' | wc -l
jq '.oneOf | length' <temp-dir>/ClientRequest.json
python3 -m unittest tests.test_native_runtime_contract_docs
./scripts/validate-repo.sh
```

Desktop callable contracts must be re-read from the active callable schemas.
Version strings, schema counts, and this evidence record are comparison inputs;
they are never substitutes for capability detection, target validation, or
action-specific authorization.
