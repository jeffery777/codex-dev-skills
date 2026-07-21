# Codex Runtime Compatibility Evidence — 2026-07-21

This record captures the public and active runtime evidence used to refresh the
repository's Codex CLI and Desktop compatibility contract. It is evidence for
the maintained shared-core/thin-adapter design, not a permanent promise that a
specific callable or version will remain available.

## Scope And Sources

The comparison used only public or intentionally exposed surfaces:

- `codex --version` from the active CLI;
- public application bundle metadata: version, build number, and bundle ID;
- the active callable tool schemas exposed to the current Desktop task;
- `codex app-server generate-json-schema --out <temp-dir>`;
- public OpenAI documentation for the
  [ChatGPT desktop app](https://learn.chatgpt.com/docs/app),
  [changelog](https://learn.chatgpt.com/docs/changelog),
  [app-server](https://learn.chatgpt.com/docs/app-server), and
  [skills](https://learn.chatgpt.com/docs/build-skills).

No Desktop database, session, log, authentication file, cache, application
state, unpublished endpoint, or reverse-engineered internal was inspected.

## Verified Facts

- The active Codex CLI reported version `0.144.6`.
- The installed desktop bundle reported version `26.715.52143`, build `5591`,
  and bundle ID `com.openai.codex`.
- The public product name is the ChatGPT desktop app. The active Codex task
  surface still exposes task, thread, worktree, handoff, and scheduling
  controls. This repository therefore retains `Codex Desktop` and `desktop` as
  compatibility labels for that Codex control plane.
- Current thread-control callables include creation, fork, list, read, bounded
  wait, message, handoff, title, pin, and archive operations. Immediate
  creation may return `threadId` plus `hostId`; queued worktree setup may return
  `clientThreadId`.
- `wait_threads` accepts one to eight targets with `threadId` and optional
  `hostId` and `afterCursor`. It returns compact progress snapshots and wakes
  on completion or attention rather than ordinary commentary.
- The generated app-server V2 JSON schema contained 228 schema files. Its
  `ClientRequest` union contained 87 methods spanning thread and turn control,
  goals, skills, hooks, marketplace and plugins, filesystem operations,
  permission profiles, and MCP operations.
- App-server remains a separate JSON-RPC contract family. Its methods,
  initialization, transport, authentication, and envelopes are not
  interchangeable with Desktop app-tool callables.

## Maintained Decisions

The evidence does not require a new execution engine or a rewrite of the shared
workflow layer:

- Goal, subagent, task selection, evidence, verification, review, and
  completion semantics remain shared across supported runtimes.
- Desktop skills remain thin adapters for user-owned task, thread, worktree,
  handoff, and scheduling controls.
- `list_threads`, `read_thread`, and `wait_threads` are observation and
  coordination operations. Their output is progress context, not repository
  completion proof.
- Create, fork, send, handoff, archive, pin, and rename remain runtime-state
  mutations requiring authority for the exact action.
- Codex CLI keeps the existing fallback: current-session execution, shared
  subagents when exposed, task briefs, or paste-ready continuation prompts.
- This refresh does not implement an app-server client, SDK wrapper, daemon,
  sidecar, or new MCP server.

## Re-runnable Checks

```bash
codex --version
codex app-server generate-json-schema --out <temp-dir>
find <temp-dir>/v2 -type f -name '*.json' | wc -l
./scripts/validate-repo.sh
python -m unittest discover -s tests
```

The active callable schema must still be inspected at the actual call site.
Recorded dates and version strings are comparison evidence, not substitutes
for capability detection.

## Release Decision

This compatibility refresh changes installed Desktop skill guidance and the
public runtime contract, so it is a reasonable patch-release candidate. After
the implementation PR is merged, prefer a separate `v0.8.1` release slice that
aligns `catalog.yaml`, `install.sh`, the README current-release link, and a new
`docs/release-notes-v0.8.1.md`. Do not rewrite the v0.8.0 release notes.

Creating the tag and GitHub Release remains a separate exact human gate after
the release slice is reviewed and merged.
