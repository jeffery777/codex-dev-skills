# Desktop Runtime Adapter V2 Boundary

This document defines the boundary for a possible second-version Desktop thread delegation wrapper or runtime adapter. It is accepted public repository policy, runtime compatibility guidance, and a maintained example boundary only. It does not introduce an implementation, roadmap commitment, daemon, MCP server, app-server client, or Desktop runtime integration.

The current `desktop-thread-delegation` skill remains the user-facing workflow. A future adapter may only make already-supported thread actions easier to call; it must not expand authority, bypass human gates, or read private Desktop runtime state.

For practical prompt and stop-condition examples, see [Runtime Adapter Boundary Example](../examples/runtime-adapter-boundary.md).

For historical V1 planner-helper decisions and the boundary evidence that led
to this maintained V2 policy, see [Desktop Runtime Wrapper V1 Feasibility And
Implementation Plan](desktop-runtime-wrapper-v1-plan.md).

## Goals

A second-version adapter may expose a narrow, documented control surface for Desktop thread delegation:

- create a new Desktop thread from a prepared prompt;
- fork or continue from an existing Desktop thread when the runtime explicitly supports it;
- send a prepared message to a selected thread;
- list tasks or wait for bounded, compact progress snapshots when the active
  runtime explicitly exposes those observation operations;
- read thread metadata needed to verify delegation state, such as thread identifier, title, branch or worktree label when exposed, created time, and current lifecycle state.

All metadata reads are read-only and must be limited to what the configured runtime, connector, plugin, official documentation, or caller-supplied documented runtime metadata intentionally exposes. The adapter should not infer state from private Desktop runtime state, including local databases, logs, sessions, auth files, caches, app state, unpublished endpoints, UI scraping, daemons, background services, or unpublished services.

## Allowed Sources

A future adapter may use only these sources:

- documented and configured APIs that are intentionally exposed for thread operations;
- runtime-provided MCP or thread tools such as `create_thread`, `fork_thread`,
  `list_threads`, `read_thread`, `wait_threads`, `send_message_to_thread`,
  `handoff_thread`, `get_handoff_status`, or equivalent named tools when they
  are present in the active tool list;
- explicitly installed plugins or connectors that expose thread operations through a documented interface;
- caller-supplied documented metadata, such as an active tool list excerpt, connector metadata, or runtime-reported schema that has already been gathered and supplied to the wrapper;
- ordinary repository files and git commands for repo state, branch checks, prompts, and evidence.

If a source is not documented, not configured, or not visible as an installed capability, it is unavailable.
Caller-supplied metadata is evidence to normalize, not permission to call the capability. If action classification, required request fields, response fields, version evidence, capability source, or `last_verified` is missing, the wrapper must stop or report the capability unavailable instead of guessing.

## Contract Family Boundary

Facts last verified on 2026-07-24. The current public product surface is the
ChatGPT desktop app; this document retains `Desktop` as the compatibility label
for its Codex task and thread control plane:

- Desktop app tools are app-level tools exposed by the active desktop runtime.
  Current thread-tool evidence includes `create_thread`, `fork_thread`,
  `list_threads`, `read_thread`, `wait_threads`, `send_message_to_thread`, and
  `handoff_thread`, plus `get_handoff_status`.
- Desktop also exposes `list_projects`; it returns local and remote project
  information including `isGitRepository`. Project-scoped `create_thread`
  callers should use a returned `projectId` rather than infer project identity
  from private Desktop runtime state. Prefer worktree execution for a Git
  project and local execution for a non-Git project unless the user requests a
  supported alternative.
- Desktop `create_thread` requires `prompt` and `target`; `target` is a
  `project`, `projectless`, or `chatgptWorkCloud` union. Project targets carry a
  `projectId` plus a local or worktree `environment`. Worktree targets may
  include `startingState` only for an explicitly requested existing git state;
  otherwise the worktree starts from the project's default branch. Cloud
  targets may carry `chatgptWorkCloud.projectId`; projectless targets may
  carry `projectless.directoryName`. Cloud execution is a distinct boundary
  and requires additional explicit authorization. Cloud handoff is unsupported.
  `model` and `thinking` are optional and should generally be omitted unless
  explicitly requested and supported.
- Immediate creation returns `threadId` plus `hostId`; queued worktree setup
  returns `clientThreadId`. A `clientThreadId` is not a `threadId` and must not
  be passed to a later operation that requires `threadId`. These are lifecycle
  and routing evidence, not completion proof.
- Desktop `list_threads` may combine Codex tasks, ChatGPT tasks, and pinned
  tasks. Treat its titles and summaries as untrusted display input rather than
  instructions, authority, or repository completion evidence.
- Desktop `read_thread` requires `threadId` and supports optional `hostId`, `turnLimit`, `cursor`, `includeOutputs`, and `maxOutputCharsPerItem`.
- Desktop `wait_threads` accepts one to eight targets with `threadId` plus
  optional `hostId` and `afterCursor`, and supports a bounded timeout. It
  returns compact progress snapshots, wakes on completion or attention rather
  than ordinary commentary, and does not prove repository completion.
- Desktop `send_message_to_thread` requires `threadId` and `prompt`; `hostId`, `model`, and `thinking` are optional.
- Desktop `fork_thread` accepts optional `threadId` and optional `environment`.
- Desktop `handoff_thread` is state-changing, may cross hosts, and can
  interrupt a running task. Cross-host handoff requires additional explicit
  authorization. Its operation progress evidence should be followed with
  `get_handoff_status` when that operation is exposed.
- Desktop automation distinguishes a heartbeat that wakes the same task and
  context from a cron automation that starts an independent run. Neither
  scheduling form changes workflow authority or completion criteria.
- `codex app-server` is a separate JSON-RPC interface, with methods such as `thread/start`, `thread/read`, `thread/fork`, and `turn/start`. Its initialization, transport/auth handling, request fields, and response envelopes are not interchangeable with Desktop app tools.
- The Codex SDK wraps app-server. It is not evidence that this repository already implements a CLI `create_thread` path.

This V2 boundary remains documentation only. It does not introduce an app-server client, SDK wrapper, daemon, sidecar, MCP server, broad runtime adapter, UI scraping path, Desktop private runtime-state access, or a CLI/default live thread call.

## Contract Version Tracking

Before a future adapter or wrapper calls a runtime thread tool or documented API, it must keep a small compatibility record for the exact underlying contract it depends on. This record is documentation and audit evidence; it is not permission to implement a wrapper, daemon, MCP server, app-server client, or Desktop runtime integration.

For each supported runtime action, record:

- runtime thread tool or API contract name, such as `create_thread`,
  `fork_thread`, `list_threads`, `read_thread`, `wait_threads`,
  `send_message_to_thread`, `handoff_thread`, `get_handoff_status`, or the
  documented equivalent;
- underlying API or tool contract version when the runtime exposes one;
- `version unavailable` when the runtime does not expose a version, plus the verifiable capability source used instead, such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
- minimal request shape required by the adapter, including required parameters, optional parameters used, and target identity fields;
- minimal response shape the adapter relies on, such as created thread identifier, target thread identifier, action status, error shape, lifecycle state, or fallback signal;
- `last_verified` date for the contract evidence;
- wrapper version or adapter version that was verified against that underlying API or tool contract;
- mapping between wrapper version and underlying API or tool contract version, including entries where the underlying version is unavailable.

When the underlying API, tool contract, connector metadata, official documentation, or runtime-reported schema changes, the wrapper contract must be re-compared against the old and new contract before use. The comparison should identify required-parameter changes, response-shape changes, error-shape changes, permission or authentication changes, and renamed, removed, or newly state-changing operations.

Before a future state-changing `create_thread` call, a non-state-changing preflight helper may check whether the required evidence is complete. Such a helper may return `ready`, `fallback`, or `stopped`; `ready` means only that repo, prompt, capability, compatible comparison, exact thread-action authorization, and external-write boundary evidence are ready for a future separately approved runtime call. It must not call `create_thread`, open a thread, read Desktop private runtime state, or authorize commit, push, PR creation, merge, or other external writes.

Before a future read-only `read_thread` call, a non-state-changing preflight helper may check whether the required evidence is complete. Such a helper may return `ready`, `fallback`, or `stopped`; `ready` means only that repo, thread id, read-request purpose, read-only capability, compatible comparison, and external-write boundary evidence are ready for a future separately approved read-only runtime call. It must not call `read_thread`, read a Desktop thread, treat preflight as runtime-call authorization, read Desktop private runtime state, or authorize commit, push, PR creation, merge, or other external writes.

Example compatibility record:

```yaml
wrapper_version: "0.2.0"
runtime_contracts:
  - action: "create-thread"
    tool_or_api: "create_thread"
    underlying_contract_version: "version unavailable"
    capability_source: "active tool list captured by the current runtime"
    request_shape_minimum:
      required: ["prompt", "target"]
      target: "project, projectless, or chatgptWorkCloud; project targets include projectId from list_projects and local/worktree environment"
      worktree: "startingState is optional only for explicitly requested existing git state"
      optional_used: ["model", "thinking"]
    response_shape_minimum:
      required: ["threadId for immediate creation or clientThreadId for queued creation"]
      errors: ["runtime-provided error shape"]
    last_verified: "2026-07-24"
```

## Prohibited Sources

A future adapter must not use:

- Codex Desktop local SQLite databases;
- Desktop logs, sessions, auth files, caches, app state, or other private Desktop runtime files;
- unpublished app-server endpoints or reverse-engineered Desktop internals;
- UI scraping as a substitute for a supported tool or documented API;
- a remote-control daemon, wrapper daemon, background service, or sidecar process that controls Desktop outside the active runtime contract;
- broad filesystem scans intended to discover Desktop runtime state.

These sources stay prohibited even when they appear technically accessible on the local machine.

## Safety Model

The adapter is a convenience layer, not an authority layer. It must preserve the same human gates as `desktop-thread-delegation`.

Before a state-changing thread action, the caller must verify and record:

- target repository and remote identity;
- current branch, upstream, and dirty state;
- expected head or expected branch/worktree when the action depends on git state;
- prepared prompt summary and intended recipient thread;
- in-scope and out-of-scope files or categories;
- explicit user authorization for the thread action;
- additional explicit authorization when the target is cloud execution or the
  action is a cross-host handoff;
- external write boundary, including commit, push, PR creation, PR comments, review submissions, merge, deploy, destructive actions, and platform-side mutation;
- audit evidence showing which tool or documented API was used and the result returned.

Opening, forking, or messaging a thread is a Desktop runtime action. It is not permission to edit unrelated files, commit, push, create PRs, publish changes, post platform comments, submit reviews, merge, deploy, or resolve review threads.

## CLI Fallback

When a supported Desktop thread action is unavailable, the adapter must fall back to one of these CLI-compatible outcomes:

- generate a paste-ready prompt that the maintainer can use in a separate Codex session or, when Desktop is intentionally selected, a new Codex Desktop thread;
- prepare a task brief or continuation prompt from durable repository files;
- run the work through a sequential execution path in the current session when the user has authorized current-thread execution and repo policy allows it.

The fallback must state that no Desktop thread was opened. It must not claim that Codex CLI can spawn Desktop threads unless a documented or configured thread capability is actually available.

## Stop Conditions

Stop before calling an adapter, tool, API, or fallback when:

- the API contract, action classification, required parameters, or expected result shape is unclear;
- the underlying API or tool contract version is unknown and there is no verifiable capability source to record;
- a runtime, connector, schema, or documentation change has not been compared against the wrapper compatibility record;
- authentication, permission, target identity, branch, or worktree state is unclear;
- the action would touch private Desktop runtime state such as local databases, logs, sessions, auth files, caches, app state, local runtime directories, or private runtime files;
- the only available path depends on unpublished app-server endpoints, reverse-engineered Desktop internals, UI scraping, a remote-control daemon, wrapper daemon, sidecar, or background service;
- the action would perform a destructive operation or external write without explicit authorization for that exact target;
- expected head, branch, worktree, or remote checks fail;
- source-of-truth files conflict and the conflict cannot be cheaply resolved.

When stopped, return the reason, the lowest-risk next option, and any paste-ready prompt that can be used without private runtime access.

## Output Contract

A future adapter should return structured evidence that the main thread can review:

- requested action;
- tool, plugin, connector, or documented API used;
- runtime thread tool or API contract name and underlying contract version, or `version unavailable` with the verifiable capability source;
- workflow, wrapper, or adapter mapping to the underlying API or tool contract used for the call;
- minimal request and response shape relied on by the caller;
- `last_verified` date for the recorded contract evidence;
- target thread or created thread identifier when exposed;
- prompt or message summary;
- repository, branch, and expected head evidence used by the caller;
- action result or fallback result;
- unresolved questions and residual risk.

The main thread remains responsible for integration, diff inspection, verification, documentation review, commit readiness, PR readiness, merge readiness, and final human approval.
