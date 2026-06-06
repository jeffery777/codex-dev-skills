# Desktop Runtime Adapter V2 Boundary

This document defines the boundary for a possible second-version Desktop thread delegation wrapper or runtime adapter. It is a specification and safety contract only. It does not introduce an implementation, daemon, MCP server, app-server client, or Desktop runtime integration.

The current `desktop-thread-delegation` skill remains the user-facing workflow. A future adapter may only make already-supported thread actions easier to call; it must not expand authority, bypass human gates, or read private local runtime state.

For practical prompt and stop-condition examples, see [Runtime Adapter Boundary Example](../examples/runtime-adapter-boundary.md).

## Goals

A second-version adapter may expose a narrow, documented control surface for Desktop thread delegation:

- create a new Desktop thread from a prepared prompt;
- fork or continue from an existing Desktop thread when the runtime explicitly supports it;
- send a prepared message to a selected thread;
- read thread metadata needed to verify delegation state, such as thread identifier, title, branch or worktree label when exposed, created time, and current lifecycle state.

All metadata reads are read-only and must be limited to what the configured runtime, connector, or plugin intentionally exposes. The adapter should not infer state from private files, logs, UI scraping, or unpublished services.

## Allowed Sources

A future adapter may use only these sources:

- documented and configured APIs that are intentionally exposed for thread operations;
- runtime-provided MCP or thread tools such as `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or equivalent named tools when they are present in the active tool list;
- explicitly installed plugins or connectors that expose thread operations through a documented interface;
- ordinary repository files and git commands for repo state, branch checks, prompts, and evidence.

If a source is not documented, not configured, or not visible as an installed capability, it is unavailable.

## Contract Version Tracking

Before a future adapter or wrapper calls a runtime thread tool or documented API, it must keep a small compatibility record for the exact underlying contract it depends on. This record is documentation and audit evidence; it is not permission to implement a wrapper, daemon, MCP server, app-server client, or Desktop runtime integration.

For each supported runtime action, record:

- runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or the documented equivalent;
- underlying API or tool contract version when the runtime exposes one;
- `version unavailable` when the runtime does not expose a version, plus the verifiable capability source used instead, such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
- minimal request shape required by the adapter, including required parameters, optional parameters used, and target identity fields;
- minimal response shape the adapter relies on, such as created thread identifier, target thread identifier, action status, error shape, lifecycle state, or fallback signal;
- `last_verified` date for the contract evidence;
- wrapper version or adapter version that was verified against that underlying API or tool contract;
- mapping between wrapper version and underlying API or tool contract version, including entries where the underlying version is unavailable.

When the underlying API, tool contract, connector metadata, official documentation, or runtime-reported schema changes, the wrapper contract must be re-compared against the old and new contract before use. The comparison should identify required-parameter changes, response-shape changes, error-shape changes, permission or authentication changes, and renamed, removed, or newly state-changing operations.

Example compatibility record:

```yaml
wrapper_version: "0.2.0"
runtime_contracts:
  - action: "create-thread"
    tool_or_api: "create_thread"
    underlying_contract_version: "version unavailable"
    capability_source: "active tool list captured by the current runtime"
    request_shape_minimum:
      required: ["prompt"]
      optional_used: ["title", "repository", "branch"]
    response_shape_minimum:
      required: ["thread_id or pending_worktree_id", "status"]
      errors: ["message"]
    last_verified: "YYYY-MM-DD"
```

## Prohibited Sources

A future adapter must not use:

- Codex Desktop local SQLite databases;
- Desktop logs, sessions, auth files, caches, app state, or other private local runtime files;
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
- external write boundary, including commit, push, PR creation, PR comments, review submission, merge, deploy, destructive actions, and platform-side mutation;
- audit evidence showing which tool or documented API was used and the result returned.

Opening, forking, or messaging a thread is a Desktop runtime action. It is not permission to edit unrelated files, publish changes, post platform comments, merge, deploy, or resolve review threads.

## CLI Fallback

When a supported Desktop thread action is unavailable, the adapter must fall back to one of these CLI-compatible outcomes:

- generate a paste-ready prompt that the maintainer can use in a new Codex thread;
- run the work sequentially in the current session when the user has authorized current-thread execution and repo policy allows it;
- prepare a task brief, continuation prompt, or handoff artifact from durable repository files.

The fallback must state that no Desktop thread was opened. It must not claim that Codex CLI can spawn Desktop threads unless a documented or configured thread capability is actually available.

## Stop Conditions

Stop before calling an adapter, tool, API, or fallback when:

- the API contract, required parameters, or expected result shape is unclear;
- the underlying API or tool contract version is unknown and there is no verifiable capability source to record;
- a runtime, connector, schema, or documentation change has not been compared against the wrapper compatibility record;
- authentication, permission, target identity, branch, or worktree state is unclear;
- the action would touch private local runtime state such as Desktop databases, logs, sessions, auth files, caches, or app state;
- the only available path depends on unpublished app-server endpoints, UI scraping, or a remote-control daemon;
- the action would perform a destructive operation or external write without explicit authorization for that exact target;
- expected head, branch, worktree, or remote checks fail;
- source-of-truth files conflict and the conflict cannot be cheaply resolved.

When stopped, return the reason, the lowest-risk next option, and any paste-ready prompt that can be used without private runtime access.

## Output Contract

A future adapter should return structured evidence that the main thread can review:

- requested action;
- tool, plugin, connector, or documented API used;
- runtime thread tool or API contract name and underlying contract version, or `version unavailable` with the verifiable capability source;
- wrapper version to underlying API or tool contract mapping used for the call;
- minimal request and response shape relied on by the caller;
- `last_verified` date for the recorded contract evidence;
- target thread or created thread identifier when exposed;
- prompt or message summary;
- repository, branch, and expected head evidence used by the caller;
- action result or fallback result;
- unresolved questions and residual risk.

The main thread remains responsible for integration, diff inspection, verification, documentation review, commit readiness, PR readiness, merge readiness, and final human approval.
