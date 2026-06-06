# Desktop Runtime Wrapper V1 Feasibility And Implementation Plan

This document answers whether the repository can move from the accepted Desktop runtime adapter boundary toward a first implementation slice. The first slice now exists as a non-state-changing planner helper. It does not implement a daemon, MCP server, app-server client, background service, Desktop runtime integration, catalog entry, installer entry, or skill.

## Decision

Implementation is conditionally feasible for a V1 Desktop runtime wrapper, but only as a narrow convenience layer over runtime thread tools or documented APIs that are already exposed by the active runtime.

The first implementation slice is complete as a non-state-changing request planner and fallback generator. It validates a prepared thread-action request, records the minimum contract evidence needed for a future runtime call, and produces either structured dry-run evidence or a CLI-compatible paste-ready fallback. It does not create, fork, continue, message, or read a Desktop thread.

State-changing thread calls can be considered only after the first slice proves the request and evidence contract, and after a separate human decision approves adding a runtime-call path for one documented action.

## Objective

Wrapper V1 should make the existing `desktop-thread-delegation` boundary easier to apply without expanding authority:

- normalize one prepared Desktop thread-action request into a small structured shape;
- verify that the request identifies the repository, branch or expected head when relevant, intended action, prompt summary, and external-write boundary;
- record compatibility evidence for the runtime thread tool or documented API the wrapper would rely on;
- return a dry-run result, stop result, or CLI-compatible fallback when the runtime capability is unavailable or unsafe;
- preserve the main-thread responsibility for integration, verification, review evidence, commit readiness, PR readiness, merge readiness, and human approval.

## Non-Goals

Wrapper V1 must not:

- implement a daemon, MCP server, app-server client, sidecar, background service, or Desktop runtime integration;
- read or mutate Desktop private runtime state;
- use unpublished app-server endpoints, reverse-engineered Desktop internals, UI scraping, local runtime directories, or broad Desktop filesystem discovery;
- add a new public skill, catalog item, installer entry, or workflow alias in the first implementation slice;
- authorize commit, push, PR creation, merge, deploy, platform comments, review submissions, destructive actions, or other external writes;
- replace `desktop-thread-delegation`, `desktop-project-delivery`, review primitives, formal review gates, or `merge-readiness-gate`.

## Source Of Truth

Allowed sources for V1 planning and implementation:

- repository files, including `docs/runtime-adapter-v2.md`, `docs/runtime-compatibility.md`, `docs/source-classification.md`, examples, skills, templates, policies, and git state;
- runtime-provided thread tools that are visible in the active tool list, such as `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or documented equivalents;
- explicitly installed plugins or connectors that expose thread actions through documented metadata or schemas;
- official or runtime-reported schema evidence when the runtime provides it;
- ordinary shell and git inspection for repo identity, branch, upstream, dirty state, expected head, and changed-file evidence.

Forbidden sources remain forbidden even when technically accessible:

- Codex Desktop local SQLite databases;
- Desktop logs, sessions, auth files, caches, app state, local runtime directories, or private runtime files;
- unpublished app-server endpoints or reverse-engineered Desktop internals;
- UI scraping as a substitute for a supported runtime tool or documented API;
- remote-control daemons, wrapper daemons, sidecars, background services, or app-server clients;
- broad filesystem scans intended to discover Desktop runtime state.

## Runtime Assumptions

V1 may rely on a runtime thread tool or documented API only when all of these are true:

- the capability is visible in the active runtime, installed plugin, connector metadata, official documentation, or runtime-reported schema;
- the action name and whether it is read-only or state-changing are clear;
- required request parameters are known;
- the minimum response fields used by the wrapper are known;
- authentication, permission, target identity, and failure semantics are clear enough to stop safely;
- the compatibility evidence includes `last_verified` and either a contract version or `version unavailable` plus a verifiable capability source.

If the runtime does not expose a version, `version unavailable` is acceptable only when the capability source is recorded. An unknown version without a verifiable capability source blocks implementation and use.

## Minimum Schema

The first implementation slice should use a minimal request schema like this:

```yaml
action: "plan-thread-action"
target_action: "create-thread | fork-thread | send-message | read-thread"
runtime_contract:
  tool_or_api: "create_thread"
  underlying_contract_version: "version unavailable"
  capability_source: "active tool list | connector metadata | official documentation | runtime-reported schema"
  last_verified: "YYYY-MM-DD"
  wrapper_version: "0.1.0"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "optional commit SHA"
  thread_id: "optional existing thread identifier"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt or message body"
boundaries:
  in_scope: ["docs/runtime-adapter-v2.md"]
  out_of_scope: ["wrapper code", ".work/", "Desktop private runtime state"]
  external_writes_blocked: true
authorization:
  thread_action_authorized: false
  external_write_authorized: false
```

The first implementation slice should return a minimal response schema like this:

```yaml
status: "dry-run | fallback | stopped"
requested_action: "plan-thread-action"
target_action: "create-thread"
runtime_contract:
  tool_or_api: "create_thread"
  underlying_contract_version: "version unavailable"
  capability_source: "active tool list"
  last_verified: "YYYY-MM-DD"
  wrapper_mapping: "wrapper 0.1.0 -> create_thread version unavailable"
request_shape_relied_on:
  required: ["prompt.body", "target.repo", "runtime_contract.tool_or_api"]
  optional_used: ["target.branch", "target.expected_head", "target.thread_id"]
response_shape_relied_on:
  required: ["status"]
  fallback_fields: ["paste_ready_prompt", "stop_reason"]
result:
  paste_ready_prompt: "optional CLI-compatible fallback prompt"
  stop_reason: "optional blocker"
  residual_risk: ["listed uncertainty"]
```

The first slice should not rely on a created thread identifier because it must not call a state-changing thread tool.

## Failure Modes And Fallbacks

The wrapper should stop or fall back when:

- the target runtime thread tool or documented API is unavailable;
- the tool contract name, request shape, response shape, version evidence, authentication, permission, repo identity, branch, expected head, or target thread is unclear;
- source-of-truth files conflict and the conflict cannot be cheaply resolved;
- runtime, connector, schema, or documentation changes have not been compared against recorded compatibility evidence;
- the only available path depends on Desktop private runtime state, unpublished endpoints, UI scraping, daemons, sidecars, background services, or app-server clients;
- a requested action would perform an external write, destructive action, or state-changing thread action without exact authorization.

CLI-compatible fallback behavior:

- state that no Desktop thread was opened, forked, continued, messaged, or read;
- return a paste-ready prompt, task brief, continuation prompt, or sequential execution plan based only on durable repository files;
- preserve the same review and external-write gates as `desktop-thread-delegation`;
- mark incomplete evidence as unverified instead of filling gaps from private runtime state.

## Human Gates

The wrapper is not an authority layer. It may prepare evidence, but it must stop before:

- any state-changing Desktop thread action unless the user explicitly authorized that exact thread action;
- commit, push, PR creation, publication, merge, deploy, platform comments, review submissions, destructive actions, or platform-side mutation unless the user explicitly authorized the exact external write;
- public contract changes when behavior is ambiguous;
- product-semantic decisions, scope expansion, material security/privacy/data/deployment risk, or unclear source of truth.

Authorization for a Desktop thread action is separate from authorization for external writes.

## First Implementation Slice

Completed first slice:

1. Added a small request planner that accepts the minimum schema above from a prepared caller.
2. Validates required fields and classifies the outcome as `dry-run`, `fallback`, or `stopped`.
3. Emits structured evidence and a paste-ready fallback prompt when the runtime capability is missing or state-changing use is not authorized.
4. Includes focused tests for the planner using only repository fixtures.
5. Keeps runtime thread-tool invocation out of the slice.

This slice is intentionally useful even without Desktop runtime access: it proves the evidence contract, fallback behavior, and stop conditions before any wrapper path can affect Desktop state.

## First Slice Implementation Artifact

The initial non-state-changing helper is `scripts/desktop_runtime_wrapper_planner.py`.
It accepts a prepared JSON request that follows the minimum schema above, validates required fields and contract evidence, classifies the result as `dry-run`, `fallback`, or `stopped`, and emits structured JSON evidence.
Callers may set optional `runtime_contract.available: false` when a documented runtime capability is known to be unavailable; the planner then emits a CLI-compatible fallback instead of treating private runtime state as a substitute.

Usage examples:

```bash
python3 scripts/desktop_runtime_wrapper_planner.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_wrapper_planner.py --pretty < prepared-request.json
```

The stdin request must be JSON and should follow the minimum schema above. Use `--example` to print a complete example request when preparing or updating a caller fixture.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not read Desktop private runtime state, unpublished endpoints, UI state, daemons, sidecars, background services, app-server clients, catalog entries, installer entries, or skill metadata as runtime state. It does not add a daemon, MCP server, app-server client, sidecar, background service, new skill, catalog item, or installer entry.

The CLI-compatible fallback prompt must state that no Desktop thread was opened, forked, continued, messaged, or read. It must rely only on durable request fields supplied to the planner and preserve the external-write gate.

Focused tests live in `tests/test_desktop_runtime_wrapper_planner.py` and can be rerun with:

```bash
python3 -m unittest discover -s tests
```

## Later Slice Candidates

Later slices require separate review and human approval:

- read-only capability discovery from documented runtime metadata when available;
- a single state-changing `create-thread` call path using an already exposed runtime tool;
- `read-thread` metadata verification when the runtime exposes a documented read-only tool;
- additional `fork-thread` or `send-message` paths only after the single-action path is stable.

Each later slice must re-check the underlying contract evidence and keep private runtime state prohibited.

## Verification Strategy

For this plan and post-merge documentation alignment:

- `./scripts/validate-repo.sh`
- `git diff --check`
- formal docs review

For the completed first implementation slice:

- schema validation tests for required and optional fields;
- fallback tests proving no Desktop thread action is claimed when capability is unavailable;
- stop-condition tests for missing contract evidence, unclear repo identity, external-write requests, and forbidden source hints;
- docs review for public claims and runtime compatibility;
- code review gate only if the implementation slice is used for commit or PR readiness.

## Stop Conditions Before Later Implementation Slices

Stop before implementing later wrapper code when:

- the implementation location, public API shape, or packaging target is unclear;
- the runtime capability source cannot be recorded without private Desktop runtime state;
- a later slice would need a daemon, MCP server, app-server client, background service, new skill, catalog entry, or installer entry;
- the proposed code would call state-changing thread tools without separate explicit approval;
- tests would require Desktop private runtime files or unpublished Desktop internals;
- external-write or destructive-action boundaries are ambiguous;
- maintainers have not approved the specific later implementation slice.
