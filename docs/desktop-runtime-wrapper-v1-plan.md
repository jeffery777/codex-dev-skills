# Desktop Runtime Wrapper V1 Feasibility And Implementation Plan

This document answers whether the repository can move from the accepted Desktop runtime adapter boundary toward first implementation slices. The completed V1 slices now exist as bounded helpers: a request planner and fallback generator, a capability metadata normalization helper, a contract comparison helper, a create-thread runtime-call preflight helper, a read-thread runtime-call preflight helper, an end-to-end evidence pipeline example, a session compatibility status validator, a first-use session compatibility handshake helper, a session-scoped compatibility cache helper, a create-thread authorization/evidence boundary gate, a create-thread executor boundary proposal helper, a create-thread executor shell implementation-surface helper, a single documented create-thread callable executor helper, and a single documented create-thread callable wiring-boundary helper. The executor helper can execute only a caller-injected documented callable adapter after call-site validation; the CLI default remains non-live and falls back when no runner is injected. The wiring-boundary helper can convert one caller-supplied documented `create_thread` descriptor or explicit non-live adapter wiring contract into the executor helper's injected adapter contract shape; it does not invoke Desktop runtime. These helpers do not implement a daemon, MCP server, app-server client, background service, Desktop runtime integration, catalog entry, installer entry, skill, live Desktop runtime executor, or broad runtime-call path.

## Decision

Implementation is conditionally feasible for a V1 Desktop runtime wrapper, but only as a narrow convenience layer over runtime thread tools or documented APIs that are already exposed by the active runtime.

The first implementation slice is complete as a non-state-changing request planner and fallback generator. It validates a prepared thread-action request, records the minimum contract evidence needed for a future runtime call, can consume normalized capability evidence supplied by the discovery helper, and produces either structured dry-run evidence or a CLI-compatible paste-ready fallback. It does not create, fork, continue, message, or read a Desktop thread.

The read-only capability discovery slice is also complete as a non-state-changing metadata normalizer. It accepts only caller-supplied documented metadata, such as an active tool list excerpt, connector metadata, official documentation, or runtime-reported schema that has already been gathered and supplied to the helper. It records action names, read-only or state-changing classification, required request fields, minimum response fields, capability source, contract version or `version unavailable`, `last_verified`, and helper version. The planner can accept this normalized output as `capability_evidence`, select the requested target action, and stop or fall back when the evidence is unavailable, missing, mismatched, unclear, or sourced from forbidden Desktop runtime hints. It does not gather metadata itself, inspect Desktop private runtime state, or call any Desktop thread tool.

The contract comparison slice is also complete as a non-state-changing compatibility re-check helper. It compares old wrapper contract evidence against newer normalized capability evidence before a runtime, connector, schema, or documentation change is trusted. It returns `compatible` when the tool/API name, action classification, required request fields, and minimum response fields still match; `fallback` when the capability is unavailable or missing; and `stopped` when the comparison detects changed request shape, response shape, classification, tool/API name, missing evidence, or forbidden Desktop runtime source hints. State-changing actions such as `create-thread` may be compared as evidence only; comparison does not authorize or call the runtime tool.

The create-thread preflight slice is also complete as a non-state-changing readiness helper. It consumes target repo evidence, prepared prompt evidence, normalized `create-thread` capability evidence, and compatible contract comparison evidence, then returns `ready`, `fallback`, or `stopped`. `ready` only means evidence is ready for a future separately approved `create_thread` runtime call; it does not mean the helper called `create_thread`, opened a thread, or authorized commit, push, PR creation, merge, or any other external write. The helper returns `fallback` when capability or comparison evidence is unavailable or exact thread-action authorization is false, and `stopped` when contract evidence is incompatible or unclear, the action classification is not `state-changing`, repo/remote/branch/expected-head evidence is incomplete, private source hints appear, or external-write boundaries are not blocked.

The read-thread preflight slice is also complete as a non-state-changing readiness helper. It consumes target repo and thread-id evidence, read-request purpose evidence, normalized `read-thread` capability evidence, and compatible contract comparison evidence, then returns `ready`, `fallback`, or `stopped`. `ready` only means evidence is ready for a future separately approved read-only `read_thread` runtime call; it does not mean the helper called `read_thread`, read a Desktop thread, or authorized commit, push, PR creation, merge, or any other external write. The helper keeps runtime-call authorization out of scope and stops if a caller tries to treat preflight as runtime-call authorization.

The evidence pipeline slice is also complete as a non-state-changing CLI example. It chains caller-supplied capability metadata through discovery, old/new contract comparison, and create/read preflight helpers, then emits one aggregate evidence record. It supports running a single target action when maintainers want narrower evidence, and its top-level `summary` makes ready/fallback/stopped reasons easier for review gates and maintainers to scan. It is meant to make the planner -> discovery -> compare -> preflight order easy to run and inspect. It does not gather metadata itself, call Desktop thread tools, read Desktop private runtime state, or authorize runtime calls or external writes.

The session compatibility status slice is also complete as a non-state-changing validation helper. It accepts an explicit caller-supplied session compatibility status and verifies that the wrapper/package/repo identity, helper version, target action, tool/API name, runtime-reported version or `version unavailable`, capability source, schema hash or normalized contract evidence, comparison result, `last_verified`, and session identity or current-process/current-session scoped marker are coherent. It returns `ready` only when the status can be referenced by a later preflight for contract compatibility evidence; `fallback` and `stopped` block later runtime-call paths. This helper does not perform the first-use handshake, write or read a compatibility cache, call Desktop thread tools, read Desktop private runtime state, validate target identity, validate permissions, validate runtime responses, or authorize runtime calls or external writes.

The first-use session compatibility handshake slice is also complete as a non-state-changing status construction helper. It accepts caller-supplied documented capability metadata, old wrapper contract evidence, expected wrapper/helper identity, and an explicit caller-supplied session marker. It runs capability normalization, contract comparison, session status construction, and status validation in order, then returns `ready`, `fallback`, or `stopped`. `ready` only means the produced and validated session compatibility status can be referenced by a later preflight; it does not authorize runtime calls or external writes. `fallback` and `stopped` block later runtime-call paths. This helper does not read or write a compatibility cache, call Desktop thread tools, read Desktop private runtime state, validate target identity, validate permissions, validate runtime responses, or authorize runtime calls or external writes.

The session-scoped compatibility cache slice is also complete as a non-state-changing cache evidence helper. It accepts only caller-explicit cache file paths and caller-supplied cache envelopes that contain validated session compatibility status, wrapper/package/repo identity, cache helper version, status helper version, target action, tool/API name, runtime-reported version or `version unavailable`, capability source, schema hash or normalized contract evidence, comparison result, `last_verified`, session identity, cache scope, lifecycle marker, and `created_at` plus `expires_at` or an explicit same-session-only marker. It returns `ready`, `fallback`, or `stopped`. `ready` only means same-session cache evidence can be referenced by later preflight for contract compatibility evidence; it does not authorize runtime calls or external writes. `fallback` and `stopped` block later runtime-call paths. This helper rejects Desktop private runtime-looking cache paths or source hints, does not call Desktop thread tools, does not read Desktop private runtime state, does not validate target identity, validate permissions, validate runtime responses, or authorize runtime calls or external writes, and does not add a daemon, MCP server, app-server client, sidecar, background service, skill, catalog item, or installer entry.

The create-thread authorization/evidence boundary gate is also complete as a non-state-changing pre-runtime-call helper. It accepts only caller-supplied evidence for one future `create_thread` implementation slice and checks the exact target action, tool/API name, repo, remote, branch, expected head, prepared prompt summary/body, compatible create-thread preflight evidence, same-session compatibility status evidence, same-session cache evidence, exact caller intent for `authorized_runtime_action: "create-thread"`, a human approval marker for the next implementation boundary, external-write and destructive-action blocks, target validation evidence, permission/auth failure handling placeholders, runtime response validation placeholders, `runtime_call_performed: false`, and `desktop_private_runtime_state_read: false`. It returns `ready`, `fallback`, or `stopped`. `ready` only means the authorization/evidence envelope is sufficient for a human to consider approving a separate single `create_thread` runtime-call implementation; it does not authorize or perform a runtime call. `fallback` and `stopped` block later runtime-call paths. Cache, status, and preflight evidence cannot replace exact action authorization, target validation, permission/auth failure handling, or runtime response validation. This helper does not call Desktop thread tools, does not read Desktop private runtime state, and does not add a daemon, MCP server, app-server client, sidecar, background service, skill, catalog item, installer entry, or runtime-call executor.

The create-thread executor boundary proposal helper is also complete as a non-state-changing runtime-call implementation boundary helper. It accepts ready caller-supplied authorization gate evidence, verifies the exact `create-thread` action and `create_thread` tool/API, repo, remote, branch, expected head, prepared prompt summary/body, exact human-approved proposal boundary marker, `runtime_call_performed: false`, `desktop_private_runtime_state_read: false`, blocked external writes, absent or false destructive approval, and a single-tool executor contract. It requires the future executor contract to re-check target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status at the call site. It returns `ready`, `fallback`, or `stopped`. `ready` only means the runtime-call implementation proposal/boundary is sufficient for a human to consider approving a later true executor wiring slice; it does not authorize or perform a runtime call. `fallback` and `stopped` block later runtime-call paths. Authorization gate, cache, status, and preflight evidence cannot replace actual call-site target validation, permission/auth failure handling, or runtime response validation. This helper does not call Desktop thread tools, does not read Desktop private runtime state, and does not add a daemon, MCP server, app-server client, sidecar, background service, skill, catalog item, installer entry, or runtime-call executor.

The create-thread executor shell implementation-surface helper is also complete as a non-state-changing executor shell helper. It accepts ready caller-supplied executor boundary proposal evidence, verifies the exact `create-thread` action and `create_thread` tool/API, repo, remote, branch, expected head, prepared prompt summary/body, exact human-approved executor-shell implementation marker, `runtime_call_performed: false`, `desktop_private_runtime_state_read: false`, blocked external writes, absent or false destructive approval, and an explicit non-executed callable descriptor or injected-adapter placeholder. It establishes the single call-site contract that a future true executor must satisfy: target identity must be rechecked at the call site, authorization intent must be rechecked at the call site, permission/auth failures must be classified and returned, runtime response shape must be validated, returned thread id must be validated, and returned status must be validated. It returns `ready`, `fallback`, or `stopped`. `ready` only means the executor shell implementation surface is sufficient for a human to consider approving a later true documented `create_thread` callable wiring slice; it does not authorize or perform a runtime call. `fallback` and `stopped` block later runtime-call paths. Proposal, authorization gate, cache, status, and preflight evidence cannot replace actual call-site target validation, permission/auth failure handling, or runtime response validation. This helper does not call Desktop thread tools, does not read Desktop private runtime state, and does not add a daemon, MCP server, app-server client, sidecar, background service, skill, catalog item, installer entry, or live runtime-call executor.

The single documented create-thread callable executor helper is also complete as the first executor implementation helper. It accepts ready executor shell evidence, rechecks exact `create-thread` action and `create_thread` tool/API, repo, remote, branch, expected head, prepared prompt summary/body, exact human-approved executor implementation marker, `runtime_call_performed: false` before execution, `desktop_private_runtime_state_read: false`, blocked external writes, absent or false destructive approval, and an explicit caller-supplied documented callable adapter contract. It may execute only a Python caller-injected adapter and then validates permission/auth failures, response shape, returned thread id, and returned status. `ready` means only that the injected adapter execution contract completed under this helper; the response labels `desktop_runtime_call_performed: false` and does not imply the CLI default called Desktop runtime. With no injected runner, the helper returns `fallback` and blocks later runtime paths. True Desktop runtime `create_thread` callable injection or use still requires separate human approval and a runtime-provided documented callable.

The single documented create-thread callable wiring-boundary helper is also complete as a non-live wiring helper. It accepts ready executor helper evidence plus a caller-supplied documented `create_thread` callable descriptor or explicit non-live adapter wiring contract, verifies the exact target action, tool/API, repo, remote, branch, expected head, prepared prompt summary/body, exact human-approved callable wiring marker, `runtime_call_performed: false` before wiring, `desktop_private_runtime_state_read: false`, blocked external writes, absent or false destructive approval, single documented descriptor source, and the executor call-site requirements that still must be satisfied by the executor helper. It returns `ready` only when that descriptor can be converted into the previous executor helper's injected adapter contract shape. It does not discover, obtain, import, or invoke a Desktop runtime callable. CLI/default use without a descriptor returns `fallback`; tests use explicit non-live adapter wiring. `fallback` or `stopped` blocks later runtime paths. Prior shell, proposal, gate, cache, preflight, or executor evidence cannot replace actual executor call-site target validation, permission/auth handling, response validation, returned thread id validation, or returned status validation.

State-changing Desktop runtime thread calls can be considered only after the bounded helpers remain stable and after a separate human decision approves connecting at most one documented `create_thread` tool path.

## Objective

Wrapper V1 should make the existing `desktop-thread-delegation` boundary easier to apply without expanding authority:

- normalize one prepared Desktop thread-action request into a small structured shape;
- verify that the request identifies the repository, branch or expected head when relevant, intended action, prompt summary, and external-write boundary;
- record compatibility evidence for the runtime thread tool or documented API the wrapper would rely on;
- return a dry-run result, stop result, or CLI-compatible fallback when the runtime capability is unavailable or unsafe;
- normalize caller-supplied documented capability metadata and allow the planner to use that normalized evidence without calling runtime tools;
- compare old wrapper contract evidence with newer normalized capability evidence before relying on a runtime/schema change;
- preflight create-thread readiness evidence before any future separately approved runtime-call path;
- preflight read-thread readiness evidence before any future separately approved read-only runtime-call path;
- provide an end-to-end CLI evidence example that links discovery, comparison, and preflight results without calling runtime tools;
- validate caller-supplied session compatibility status before any later preflight references it;
- build and validate first-use session compatibility status from caller-supplied documented metadata and an explicit session marker;
- read or write caller-explicit same-session compatibility cache envelopes for contract compatibility evidence only;
- validate a caller-supplied create-thread authorization/evidence envelope before any separate runtime-call implementation is considered;
- validate a caller-supplied create-thread executor boundary proposal before any separate true runtime-call executor wiring is considered;
- validate a caller-supplied create-thread executor shell implementation surface before any separate true documented `create_thread` callable is wired;
- execute one caller-injected documented create-thread callable adapter under the executor helper contract while keeping CLI default non-live;
- convert one caller-supplied documented `create_thread` callable descriptor or explicit non-live adapter wiring contract into the executor helper's injected adapter contract shape while keeping CLI/default/tests non-live;
- preserve the main-thread responsibility for integration, verification, review evidence, commit readiness, PR readiness, merge readiness, and human approval.

## Non-Goals

Wrapper V1 must not:

- implement a daemon, MCP server, app-server client, sidecar, background service, or Desktop runtime integration;
- discover, obtain, or infer a Desktop runtime callable by reading private runtime state or broad runtime sources;
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
- caller-supplied documented metadata that has already been gathered outside the helper, such as an active tool list excerpt, connector metadata, official documentation, or runtime-reported schema;
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

For read-only capability discovery, the helper may normalize only metadata supplied by the caller. If the supplied metadata does not identify the action, tool or API name, read-only or state-changing classification, required request fields, minimum response fields, source, contract version or `version unavailable`, and `last_verified`, the helper must return `stopped` or `unavailable`. It must not infer missing fields from Desktop private runtime state, broad filesystem scans, logs, UI state, unpublished endpoints, or background services.

For planner integration, callers may pass the discovery helper output as `capability_evidence`. The planner may use only normalized fields from that object. It must return fallback when the target capability is unavailable or missing, and it must stop when the normalized capability classification, tool/API name, request shape, response shape, source, contract version, `last_verified`, or forbidden-source boundary is unclear.

For contract comparison, callers may pass old wrapper contract evidence and newer normalized discovery output. The comparison helper may use only documented fields supplied by the caller. It must return fallback when the target capability is missing or unavailable, and it must stop when the required request fields, minimum response fields, classification, tool/API name, source, contract version, `last_verified`, or forbidden-source boundary is unclear or changed.

For first-use session capability handshake evidence, callers may perform this comparison once per Codex CLI/Desktop process/session and construct a session-scoped compatibility status. The status should be valid only for the current process/session or runtime lifecycle marker. If the runtime exposes no lifecycle marker, the status must explicitly say it is current-process/current-session scoped. Restarting Codex CLI/Desktop invalidates the status and requires a new handshake before the wrapper trusts the runtime contract again.

The session-scoped compatibility cache helper records:

- wrapper, skill package, or repository commit version;
- cache helper version;
- status helper version;
- target action, such as `read-thread` or `create-thread`;
- tool/API name, such as `read_thread` or `create_thread`;
- runtime-reported version, or `version unavailable` when no version is exposed;
- capability source;
- schema/contract hash or equivalent normalized contract evidence;
- comparison result: `compatible`, `fallback`, or `stopped`;
- `last_verified`;
- session identity or runtime lifecycle marker, or an explicit current-process/current-session scoped marker when no runtime marker is available;
- cache scope and lifecycle marker;
- cache `created_at` plus `expires_at` or an explicit same-session-only marker.

The compatibility status and cache evidence must not cache or replace:

- exact runtime action authorization;
- external-write authorization;
- destructive-action approval;
- target repo, branch, thread id, or expected-head validation;
- auth or permission failure results;
- actual runtime tool-call response validation.

For the completed create-thread authorization/evidence gate, callers must provide a separate envelope after create-thread preflight, session compatibility status, and same-session cache evidence are already available. The gate verifies exact `target_action: "create-thread"`, `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, compatible preflight evidence, same-session status/cache evidence, `authorized_runtime_action: "create-thread"`, a human approval marker scoped to the next implementation boundary only, `external_write_authorized: false`, absent or false destructive-action approval, explicit target validation, permission/auth failure handling requirements, runtime response validation requirements, `runtime_call_performed: false`, and `desktop_private_runtime_state_read: false`.

This gate is not a runtime-call executor and not runtime-call authorization for the helper itself. Its `ready` status means only that the envelope is complete enough for a human to consider approving a separate single `create_thread` implementation slice. `fallback` or `stopped` must block the later runtime path. Cache, status, and preflight evidence are contract/readiness evidence only and cannot satisfy action authorization, target validation, permission/auth failure handling, or runtime response validation.

For the completed create-thread executor boundary proposal helper, callers must provide ready authorization gate evidence plus a new proposal envelope for one possible future executor. The helper verifies exact `target_action: "create-thread"`, `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, ready authorization gate evidence, `authorized_runtime_action: "create-thread"`, a proposal-only human approval marker, `external_write_authorized: false`, absent or false destructive-action approval, `runtime_call_performed: false`, `desktop_private_runtime_state_read: false`, a single documented tool path of `create_thread`, and executor contract requirements for call-site target validation, permission/auth failure handling, runtime response validation, and separate human approval before executor use.

This proposal helper is not a runtime-call executor and not runtime-call authorization. Its `ready` status means only that the proposed executor boundary is complete enough for a human to consider approving a later true `create_thread` wiring slice. `fallback` or `stopped` must block the later runtime path. Authorization gate, cache, status, and preflight evidence are evidence only and cannot satisfy actual call-site target validation, permission/auth failure handling, or runtime response validation.

For the completed create-thread executor shell implementation-surface helper, callers must provide ready executor boundary proposal evidence plus a new shell envelope for one possible future documented callable path. The helper verifies exact `target_action: "create-thread"`, `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, ready executor boundary proposal evidence, `authorized_runtime_action: "create-thread"`, an executor-shell-only human approval marker, `external_write_authorized: false`, absent or false destructive-action approval, `runtime_call_performed: false`, `desktop_private_runtime_state_read: false`, `surface_only: true`, `runtime_call_authorized: false`, an explicit non-executed callable descriptor or injected-adapter placeholder for `create_thread`, and call-site contract requirements for target identity, authorization intent, permission/auth failure classification, runtime response shape, returned thread id, and returned status.

This shell helper is not a live runtime executor and not runtime-call authorization. Its `ready` status means only that the implementation surface is complete enough for a human to consider separately approving a later true documented `create_thread` callable wiring slice. `fallback` or `stopped` must block the later runtime path. Proposal, authorization gate, cache, status, and preflight evidence are evidence only and cannot satisfy actual call-site target validation, permission/auth failure handling, or runtime response validation.

For the completed single documented create-thread callable executor helper, callers must provide ready executor shell evidence plus a new executor envelope and, outside the CLI default path, a Python caller-injected adapter. The helper verifies exact `target_action: "create-thread"`, `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, ready executor shell evidence, `authorized_runtime_action: "create-thread"`, an executor implementation human approval marker, `external_write_authorized: false`, absent or false destructive-action approval, `runtime_call_performed: false` before execution, `desktop_private_runtime_state_read: false`, explicit call-site target and authorization rechecks, an explicit caller-supplied documented callable adapter, and `live_desktop_runtime: false`.

This executor helper does not discover or obtain a Desktop runtime callable. The CLI default has no injected runner and therefore returns `fallback`. When a Python caller supplies an explicit non-live test adapter or separately approved documented callable adapter, the helper validates permission/auth failure classification, runtime response shape, returned thread id, returned status, `desktop_runtime_call_performed: false`, no private runtime state read, and no external write. A `ready` result means the injected adapter contract completed under this helper; it does not mean a live Desktop runtime `create_thread` call was performed. True Desktop runtime `create_thread` callable injection or use remains separate future work and still requires human approval and a runtime-provided documented callable.

For the completed single documented create-thread callable wiring-boundary helper, callers must provide ready executor evidence plus a new wiring envelope with a caller-supplied documented `create_thread` descriptor or explicit non-live adapter wiring contract. The helper verifies exact `target_action: "create-thread"`, `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, ready previous executor evidence, `authorized_runtime_action: "create-thread"`, a callable-wiring human approval marker, `external_write_authorized: false`, absent or false destructive-action approval, `runtime_call_performed: false` before wiring, `desktop_private_runtime_state_read: false`, allowed caller-supplied documented descriptor source, no runtime lookup, no direct runtime call shape, no live Desktop runtime flag, and only the `create_thread` path.

This wiring helper does not discover, obtain, import, or invoke a Desktop runtime callable. The CLI default has no descriptor and therefore returns `fallback`. When a caller supplies a documented descriptor or explicit non-live wiring contract, the helper converts it into the executor helper's injected adapter contract shape with `live_desktop_runtime: false`. A `ready` result means callable wiring readiness only; it does not mean a live Desktop runtime `create_thread` call was performed or authorized. Prior proposal, gate, cache, preflight, shell, or executor evidence cannot replace actual executor call-site target validation, permission/auth handling, response validation, returned thread id validation, or returned status validation. True Desktop runtime `create_thread` callable injection or use remains separate future work and still requires human approval and a runtime-provided documented callable.

For the completed session compatibility status validation slice, callers supply the status explicitly. The helper validates that the supplied status matches the expected wrapper/package/repo identity, helper version, target action, tool/API name, and schema hash or normalized contract evidence. It returns `ready` only when the compatible status can be referenced by a later preflight. It returns `fallback` when the supplied comparison result is `fallback`, and `stopped` when the supplied comparison result is `stopped` or when status evidence is missing, mismatched, unclear, sourced from forbidden Desktop runtime hints, or attempts to include authorization or target/permission/response validation substitutes.

This validation slice is not the first-use handshake, not a cache read path, not a cache write path, and not a runtime-call path. It does not infer runtime lifecycle state; when the runtime does not provide a lifecycle marker, the caller must explicitly mark the status as current-process/current-session scoped.

For the completed first-use session compatibility handshake slice, callers supply documented capability metadata, old wrapper contract evidence, expected wrapper/helper identity, and an explicit session identity marker. The helper normalizes the supplied metadata, compares it with the old wrapper contract, constructs a session compatibility status object, and validates that status with the session compatibility status validator. It returns `ready` only when the produced status is validated and can be referenced by later preflight. It returns `fallback` when comparison or status validation falls back, and `stopped` when discovery, comparison, status construction, status validation, wrapper/helper identity, schema hash or normalized contract evidence, session marker, private runtime source hints, or authorization-substitute fields are unsafe or unclear.

This first-use handshake slice is not a compatibility cache read path, not a compatibility cache write path, and not a runtime-call path. If the runtime does not provide a lifecycle marker, the caller must explicitly supply a current-process/current-session scoped marker. The helper does not infer runtime lifecycle from Desktop private runtime state.

For the completed session-scoped compatibility cache slice, callers supply an explicit cache file path and an explicit cache envelope for writes, or an explicit cache file path plus expected identity/schema/session evidence for reads. The helper validates the envelope against the expected wrapper/package/repo identity, cache helper version, status helper version, target action, tool/API name, schema hash or normalized contract evidence, session marker, and same-session lifecycle marker. It returns `ready` only when a compatible cache envelope can be referenced by later preflight for same-session contract compatibility evidence. It returns `fallback` when the cached comparison result is `fallback`, and `stopped` when the cached comparison result is `stopped` or when evidence is missing, mismatched, expired, stale, sourced from forbidden Desktop runtime hints, points at Desktop private runtime-looking paths, or attempts to include authorization or target/permission/response validation substitutes.

This session-scoped cache slice is not a first-use handshake, not a runtime-call path, and not an authorization layer. Codex CLI/Desktop restart, session marker mismatch, stale or expired cache, wrapper/helper/status helper version mismatch, and schema hash or normalized contract evidence mismatch invalidate or stop cache reuse. The helper does not infer runtime lifecycle from Desktop private runtime state, and it rejects Desktop private runtime-looking cache paths rather than reading them.

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
capability_evidence: "optional normalized output from desktop_runtime_capability_discovery.py"
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
  normalized_capability: "optional selected capability when capability_evidence was supplied"
request_shape_relied_on:
  required: ["prompt.body", "target.repo", "runtime_contract.tool_or_api"]
  optional_used: ["target.branch", "target.expected_head", "target.thread_id", "capability_evidence"]
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

Callers may also pass normalized discovery output under `capability_evidence`. In that path, the planner selects the capability matching `target_action`, copies the tool/API name, capability source, contract version, and `last_verified` into runtime contract evidence, and records the selected normalized capability in dry-run output. The planner returns fallback when the target action is missing or unavailable, and stopped when classification, request shape, response shape, or source evidence is unclear.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not read Desktop private runtime state, unpublished endpoints, UI state, daemons, sidecars, background services, app-server clients, catalog entries, installer entries, or skill metadata as runtime state. It does not add a daemon, MCP server, app-server client, sidecar, background service, new skill, catalog item, or installer entry.

The CLI-compatible fallback prompt must state that no Desktop thread was opened, forked, continued, messaged, or read. It must rely only on durable request fields supplied to the planner and preserve the external-write gate.

Focused tests live in `tests/test_desktop_runtime_wrapper_planner.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Read-Only Capability Discovery Slice

Completed read-only discovery slice:

1. Added a small metadata normalizer that accepts only caller-supplied documented runtime metadata.
2. Validates the source, action name, read-only or state-changing classification, required request fields, minimum response fields, contract version or `version unavailable`, `last_verified`, and helper version evidence.
3. Emits structured evidence with status `available`, `unavailable`, or `stopped`.
4. Stops instead of guessing when metadata is ambiguous or points at forbidden Desktop runtime sources.
5. Keeps runtime thread-tool invocation and Desktop metadata gathering out of the slice.

This slice is useful before any future runtime-call adapter because it makes the capability evidence explicit without treating discovery as authority to call the capability.

The normalized discovery output is also the current planner input path for capability evidence. This path remains non-state-changing: it proves that planner decisions can be based on caller-supplied documented metadata without calling `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or documented equivalents.

## Capability Discovery Implementation Artifact

The read-only metadata helper is `scripts/desktop_runtime_capability_discovery.py`.
It accepts a prepared JSON request containing caller-supplied documented metadata, normalizes each capability, and emits structured JSON evidence.

Usage examples:

```bash
python3 scripts/desktop_runtime_capability_discovery.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_capability_discovery.py --pretty < capability-metadata.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "normalize-runtime-capability-metadata"
metadata_source:
  source: "active tool list | connector metadata | official documentation | runtime-reported schema | installed plugin metadata | documented API"
  contract_version: "version unavailable"
  last_verified: "YYYY-MM-DD"
  available: true
capabilities:
  - action: "read-thread"
    tool_or_api: "read_thread"
    classification: "read-only | state-changing"
    request:
      required: ["thread_id"]
      optional: ["include_metadata"]
    response:
      required: ["status", "thread_id"]
      errors: ["message"]
    source: "runtime-reported schema"
    contract_version: "version unavailable"
    last_verified: "YYYY-MM-DD"
```

The helper output includes:

- status: `available`, `unavailable`, or `stopped`;
- action name and tool/API name;
- read-only or state-changing classification;
- required and optional request fields;
- minimum response fields and error fields;
- capability source;
- contract version or `version unavailable`;
- `last_verified`;
- discovery helper version and mapping to the underlying contract.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not collect active tool lists itself, scan the filesystem, read Desktop private runtime state, use unpublished endpoints, inspect UI state, run daemons, use sidecars, start background services, or add a public skill, catalog item, installer entry, or workflow alias.

Focused tests live in `tests/test_desktop_runtime_capability_discovery.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Contract Comparison Implementation Artifact

The compatibility re-check helper is `scripts/desktop_runtime_contract_compare.py`.
It accepts a prepared JSON request containing old wrapper contract evidence and newer normalized capability evidence, then compares only the documented fields the wrapper relies on.

Usage examples:

```bash
python3 scripts/desktop_runtime_contract_compare.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_contract_compare.py --pretty < contract-comparison.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "compare-runtime-contract-evidence"
target_action: "read-thread"
old_contract:
  action: "read-thread"
  tool_or_api: "read_thread"
  classification: "read-only"
  required_request_fields: ["thread_id"]
  minimum_response_fields: ["status", "thread_id"]
  capability_source: "active tool list"
  contract_version: "version unavailable"
  last_verified: "YYYY-MM-DD"
new_capability_evidence:
  status: "available"
  capabilities:
    - action: "read-thread"
      tool_or_api: "read_thread"
      classification: "read-only"
      required_request_fields: ["thread_id"]
      minimum_response_fields: ["status", "thread_id"]
      capability_source: "runtime-reported schema"
      contract_version: "version unavailable"
      last_verified: "YYYY-MM-DD"
```

The helper output includes:

- status: `compatible`, `fallback`, or `stopped`;
- compared action, tool/API name, classification, required request fields, and minimum response fields;
- old and new contract evidence summaries;
- stop reason and residual risk when evidence is missing, changed, unavailable, or unsafe.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize state-changing thread actions, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_contract_compare.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Preflight Implementation Artifact

The create-thread runtime-call preflight helper is `scripts/desktop_runtime_create_thread_preflight.py`.
It accepts a prepared JSON request containing target repo evidence, a prepared prompt, normalized `create-thread` capability evidence, compatible contract comparison output, safety boundaries, and exact thread-action authorization.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_preflight.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_preflight.py --pretty < create-thread-preflight.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "preflight-create-thread-runtime-call"
target_action: "create-thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
capability_evidence:
  status: "available"
  capabilities:
    - action: "create-thread"
      tool_or_api: "create_thread"
      classification: "state-changing"
      required_request_fields: ["prompt"]
      minimum_response_fields: ["status", "thread_id"]
      capability_source: "active tool list"
      contract_version: "version unavailable"
      last_verified: "YYYY-MM-DD"
contract_comparison:
  status: "compatible"
  target_action: "create-thread"
  contract_comparison:
    compared_fields: ["action", "tool_or_api", "classification", "required_request_fields", "minimum_response_fields"]
    old_contract: "old create-thread contract evidence"
    new_capability: "new normalized create-thread capability evidence"
boundaries:
  in_scope: ["durable repo files or task scope"]
  out_of_scope: [".work/", "Desktop private runtime state"]
  external_writes_blocked: true
authorization:
  thread_action_authorized: true
  authorized_thread_action: "create-thread"
  external_write_authorized: false
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- prompt summary/body presence evidence;
- contract comparison status and compared fields;
- selected `create-thread` capability classification, request shape, response shape, source, version, and `last_verified`;
- authorization evidence for the exact thread action and external-write boundary;
- `runtime_call_performed: false`;
- a readiness note stating that `ready` is evidence only for a future separately approved runtime call.

The helper returns `fallback` when normalized create-thread capability evidence or compatible contract comparison evidence is unavailable, or when exact thread-action authorization is false. It returns a paste-ready prompt and states that no Desktop thread was opened, created, forked, messaged, or read.

The helper returns `stopped` when contract comparison stopped or is not compatible, request or response evidence is unclear, create-thread classification is not `state-changing`, repo/remote/branch/expected-head evidence is incomplete, forbidden private source hints appear, or external writes are requested or no longer blocked.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_create_thread_preflight.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Authorization Gate Implementation Artifact

The create-thread authorization/evidence boundary helper is `scripts/desktop_runtime_create_thread_authorization_gate.py`.
It accepts a prepared JSON envelope containing caller-supplied target evidence, prompt evidence, create-thread preflight evidence, same-session compatibility status/cache evidence, explicit authorization intent, target validation evidence, permission/auth failure handling placeholders, runtime response validation placeholders, and safety boundary fields.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_authorization_gate.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_authorization_gate.py --pretty < create-thread-authorization-envelope.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "authorize-create-thread-runtime-call-envelope"
target_action: "create-thread"
tool_or_api: "create_thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
boundaries:
  external_writes_blocked: true
  runtime_call_performed: false
  desktop_private_runtime_state_read: false
authorization:
  authorized_runtime_action: "create-thread"
  human_approval_marker: "human-approval-required-before-runtime-call-implementation"
  human_approval_scope: "next-step-implementation-only"
  external_write_authorized: false
  destructive_action_approved: false
target_validation:
  caller_confirmed: true
  repo: "same repo as target.repo"
  remote: "same remote as target.remote"
  branch: "same branch as target.branch"
  expected_head: "same head as target.expected_head"
permission_failure_handling:
  requirements_declared: true
  satisfied_by_preflight_or_cache: false
  requirements: ["stop on auth or permission failure"]
runtime_response_validation:
  requirements_declared: true
  satisfied_by_preflight_or_cache: false
  minimum_response_fields: ["status", "thread_id"]
current_session_identity:
  marker_type: "current-session"
  marker: "current-session scoped"
preflight_evidence: "ready output from desktop_runtime_create_thread_preflight.py"
session_status_evidence: "ready output from desktop_runtime_session_compatibility_status.py"
session_cache_evidence: "ready read output from desktop_runtime_session_compatibility_cache.py"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- exact authorized runtime action evidence;
- human approval marker evidence scoped to next-step implementation only;
- external-write, destructive-action, runtime-call-performed, and private-runtime-read boundary evidence;
- target validation, permission/auth failure handling, and runtime response validation placeholder evidence;
- `runtime_call_performed: false`, `private_runtime_state_read: false`, and `external_write_performed: false`;
- a readiness note stating that `ready` only means a human can consider separately approving one future `create_thread` implementation slice.

The helper returns `fallback` when the human approval marker for the next implementation boundary is missing. It returns `stopped` when the exact target action or tool/API name is wrong, repo/remote/branch/expected-head evidence is incomplete, preflight/status/cache evidence is fallback or stopped, cache evidence is stale or session-mismatched, external writes are authorized, destructive-action approval is present, target validation is missing or mismatched, permission/auth failure handling is missing or treated as satisfied by cache/preflight, runtime response validation is missing or treated as satisfied by cache/preflight, forbidden Desktop private runtime-looking source hints appear, a runtime call has already been performed, or Desktop private runtime state was read.

`ready` is not permission to call `create_thread`. It is not runtime-call execution authorization for the helper. It only means the evidence envelope is complete enough for a human to consider approving a separate implementation in future work. The true runtime-call implementation remains future work and needs separate human approval.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, validate a real runtime response, handle real auth failures, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, background service, or runtime-call executor.

Focused tests live in `tests/test_desktop_runtime_create_thread_authorization_gate.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Executor Boundary Proposal Artifact

The create-thread executor boundary proposal helper is `scripts/desktop_runtime_create_thread_executor_boundary.py`.
It accepts a prepared JSON envelope containing ready authorization gate evidence, target evidence, prompt evidence, proposal-only human approval evidence, safety boundaries, and a single-tool executor contract proposal.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_executor_boundary.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_executor_boundary.py --pretty < create-thread-executor-boundary.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "propose-create-thread-runtime-call-executor-boundary"
target_action: "create-thread"
tool_or_api: "create_thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
boundaries:
  external_writes_blocked: true
  runtime_call_performed: false
  desktop_private_runtime_state_read: false
authorization:
  authorized_runtime_action: "create-thread"
  human_approval_marker: "human-approved-create-thread-runtime-call-executor-boundary-proposal-only"
  human_approval_scope: "proposal-helper-only-no-runtime-call"
  external_write_authorized: false
  destructive_action_approved: false
executor_contract:
  single_tool_path: "create_thread"
  call_site_rechecks:
    - "target_identity"
    - "authorization_intent"
    - "permission_auth_failure_result"
    - "runtime_response_shape"
    - "returned_thread_id"
    - "returned_status"
  target_validation:
    required_at_call_site: true
    satisfied_by_prior_evidence: false
  permission_failure_handling:
    required_at_call_site: true
    satisfied_by_prior_evidence: false
    requirements: ["stop on auth failure", "stop on permission failure"]
  response_validation:
    required_at_call_site: true
    satisfied_by_prior_evidence: false
    minimum_response_fields: ["status", "thread_id"]
  human_approval_boundary:
    required_before_executor_use: true
    scope: "proposal-helper-only-no-runtime-call"
  external_writes_blocked: true
authorization_gate_evidence: "ready output from desktop_runtime_create_thread_authorization_gate.py"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- prompt summary/body presence evidence;
- proposal-only human approval marker evidence;
- required future executor re-checks for target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status;
- executor contract evidence for a single documented `create_thread` tool path;
- `runtime_call_performed: false`, `private_runtime_state_read: false`, and `external_write_performed: false`;
- a readiness note stating that `ready` only means a human can consider separately approving one future true executor wiring slice.

The helper returns `fallback` when the exact proposal-only human approval marker is missing. It returns `stopped` when ready authorization gate evidence is missing, fallback, or stopped; the exact target action or tool/API name is wrong; repo/remote/branch/expected-head evidence is incomplete; prompt summary/body is missing; external writes are authorized; destructive-action approval is present; a runtime call has already been performed; Desktop private runtime state was read; required call-site rechecks are missing; prior gate/cache/status/preflight evidence is treated as satisfying call-site target validation, permission/auth failure handling, or runtime response validation; forbidden Desktop private runtime-looking source hints appear; or the contract claims more than one documented `create_thread` tool path.

`ready` is not permission to call `create_thread`. It is not runtime-call execution authorization for the helper. It only means the executor boundary proposal is complete enough for a human to consider approving a separate true executor in future work. The true `create_thread` call path remains future work and needs separate human approval. If that future work is approved, it should connect at most one documented `create_thread` tool path and must re-check target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status at the actual call site.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, validate a real runtime response, handle real auth failures, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, background service, or runtime-call executor.

Focused tests live in `tests/test_desktop_runtime_create_thread_executor_boundary.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Executor Shell Implementation-Surface Artifact

The create-thread executor shell helper is `scripts/desktop_runtime_create_thread_executor_shell.py`.
It accepts a prepared JSON envelope containing ready executor boundary proposal evidence, target evidence, prompt evidence, executor-shell-only human approval evidence, safety boundaries, an explicit non-executed callable descriptor or injected-adapter placeholder, and the single call-site contract a future true executor must satisfy.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_executor_shell.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_executor_shell.py --pretty < create-thread-executor-shell.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "validate-create-thread-executor-shell-surface"
target_action: "create-thread"
tool_or_api: "create_thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
boundaries:
  external_writes_blocked: true
  runtime_call_performed: false
  desktop_private_runtime_state_read: false
authorization:
  authorized_runtime_action: "create-thread"
  human_approval_marker: "human-approved-create-thread-executor-shell-implementation-surface-only"
  human_approval_scope: "executor-shell-only-no-runtime-call"
  external_write_authorized: false
  destructive_action_approved: false
executor_shell:
  implementation_marker: "human-approved-create-thread-executor-shell-implementation-surface-only"
  surface_only: true
  runtime_call_authorized: false
  callable_descriptor:
    descriptor_type: "caller-supplied-callable-descriptor | injected-adapter-placeholder | explicit-non-executed-contract-record"
    tool_or_api: "create_thread"
    execution_allowed: false
    runtime_call_shape_present: false
  call_site_contract:
    target_identity_rechecked: true
    authorization_intent_rechecked: true
    permission_auth_failure_classified_and_returned: true
    runtime_response_shape_validated: true
    returned_thread_id_validated: true
    returned_status_validated: true
    target_validation:
      satisfied_by_prior_evidence: false
    permission_failure_handling:
      satisfied_by_prior_evidence: false
    response_validation:
      satisfied_by_prior_evidence: false
executor_boundary_proposal_evidence: "ready output from desktop_runtime_create_thread_executor_boundary.py"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- prompt summary/body presence evidence;
- executor-shell-only human approval marker evidence;
- the non-executed callable descriptor or injected-adapter placeholder evidence;
- required call-site contract evidence for target identity, authorization intent, permission/auth failure classification and return, runtime response shape, returned thread id, and returned status;
- `runtime_call_performed: false`, `private_runtime_state_read: false`, and `external_write_performed: false`;
- a readiness note stating that `ready` only means the implementation surface is sufficient for a human to consider separately approving one future true documented `create_thread` callable wiring slice.

The helper returns `fallback` when the exact executor-shell implementation marker is missing. It returns `stopped` when ready executor boundary proposal evidence is missing, fallback, or stopped; the exact target action or tool/API name is wrong; repo/remote/branch/expected-head evidence is incomplete; prompt summary/body is missing; external writes are authorized; destructive-action approval is present; a runtime call has already been performed; Desktop private runtime state was read; the callable descriptor allows execution or includes a direct runtime-call shape; required call-site validation, permission/auth handling, or response validation contract fields are missing; prior proposal/gate/cache/preflight evidence is treated as satisfying call-site target validation, permission/auth failure handling, or runtime response validation; or forbidden Desktop private runtime-looking source hints appear.

`ready` is not permission to call `create_thread`. It is not runtime-call execution authorization for the helper. It only means the executor shell implementation surface is complete enough for a human to consider approving a separate true documented callable in future work. The true `create_thread` call path remains future work and needs separate human approval. If that future work is approved, it should connect at most one documented `create_thread` tool path and must re-check target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status at the actual call site.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, validate a real runtime response, handle real auth failures, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, background service, or live runtime-call executor.

Focused tests live in `tests/test_desktop_runtime_create_thread_executor_shell.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Documented Callable Executor Implementation Artifact

The create-thread documented callable executor helper is `scripts/desktop_runtime_create_thread_executor.py`.
It accepts a prepared JSON envelope containing ready executor shell evidence, target evidence, prompt evidence, executor implementation human approval evidence, explicit call-site target and authorization rechecks, safety boundaries, and one caller-supplied documented callable adapter contract.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_executor.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_executor.py --pretty < create-thread-executor.json
```

The CLI default is non-live. The second command validates the envelope but returns `fallback` because the CLI path does not inject a runner and the helper must not locate, import, or discover a Desktop runtime callable by itself. Tests and future controlled integrations call `execute_create_thread_with_injected_adapter(request, runner=...)` from Python when they need explicit injected adapter execution.

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "execute-create-thread-documented-callable-adapter"
target_action: "create-thread"
tool_or_api: "create_thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
boundaries:
  external_writes_blocked: true
  runtime_call_performed: false
  desktop_private_runtime_state_read: false
authorization:
  authorized_runtime_action: "create-thread"
  human_implementation_marker: "human-approved-create-thread-documented-callable-executor-implementation"
  human_implementation_scope: "single-documented-callable-adapter-non-live-by-default"
  external_write_authorized: false
  destructive_action_approved: false
call_site_validation:
  target_identity_rechecked_here: true
  authorization_intent_rechecked_here: true
  target_validation:
    satisfied_by_prior_evidence: false
  permission_failure_handling:
    satisfied_by_prior_evidence: false
  response_validation:
    satisfied_by_prior_evidence: false
callable_adapter:
  mode: "explicit-injected-non-live-test-adapter | explicit-injected-documented-callable-adapter"
  tool_or_api: "create_thread"
  documented_callable: true
  caller_supplied: true
  live_desktop_runtime: false
  external_write_authorized: false
executor_shell_evidence: "ready output from desktop_runtime_create_thread_executor_shell.py"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- prompt summary/body presence evidence;
- executor implementation human approval marker evidence;
- injected callable adapter contract evidence;
- `runtime_call_performed` with a meaning field that distinguishes injected adapter execution from Desktop runtime execution;
- `desktop_runtime_call_performed: false`, `private_runtime_state_read: false`, and `external_write_performed: false`;
- returned thread id and returned status only after a successful injected adapter response is validated.

The helper returns `ready` only when a caller-injected adapter completes and returns a valid response with a non-empty `thread_id`, allowed returned status, `desktop_runtime_call_performed: false`, no private runtime state read, and no external write. It returns `fallback` when the exact executor implementation marker is missing or when no injected runner is supplied. It returns `stopped` when ready executor shell evidence is missing, fallback, or stopped; the exact target action or tool/API name is wrong; repo/remote/branch/expected-head evidence is incomplete; prompt summary/body is missing; external writes are authorized; destructive-action approval is present; a runtime call has already been performed before execution; Desktop private runtime state was read; call-site target or authorization rechecks are missing; prior proposal/gate/cache/preflight/shell evidence is treated as satisfying call-site target validation, permission/auth failure handling, or runtime response validation; the injected adapter reports auth/permission failure; the runtime response shape, returned thread id, or returned status is invalid; or forbidden Desktop private runtime-looking source hints appear.

`ready` is not permission to connect a live Desktop runtime callable. It only means the injected documented callable adapter contract completed under this helper. True Desktop runtime `create_thread` callable injection or use still requires separate human approval and a runtime-provided documented callable. The next live wiring slice, if approved, must connect at most one documented `create_thread` tool path and must continue to re-check target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status at the actual call site.

The helper does not call `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, background service, or live Desktop runtime executor.

Focused tests live in `tests/test_desktop_runtime_create_thread_executor.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Create-Thread Callable Wiring Boundary Artifact

The create-thread callable wiring-boundary helper is `scripts/desktop_runtime_create_thread_callable_wiring.py`.
It accepts a prepared JSON envelope containing ready executor helper evidence, target evidence, prompt evidence, callable-wiring human approval evidence, safety boundaries, explicit executor call-site requirements, and one caller-supplied documented `create_thread` callable descriptor or explicit non-live adapter wiring contract.

Usage examples:

```bash
python3 scripts/desktop_runtime_create_thread_callable_wiring.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_create_thread_callable_wiring.py --pretty < create-thread-callable-wiring.json
```

The CLI default is non-live. The second command validates the envelope but returns `fallback` when no caller-supplied descriptor is present. The helper must not locate, import, discover, obtain, or invoke a Desktop runtime callable by itself.

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "wire-create-thread-runtime-provided-callable-adapter"
target_action: "create-thread"
tool_or_api: "create_thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
prompt:
  summary: "short prepared prompt summary"
  body: "prepared prompt body"
boundaries:
  external_writes_blocked: true
  runtime_call_performed: false
  desktop_private_runtime_state_read: false
authorization:
  authorized_runtime_action: "create-thread"
  human_wiring_marker: "human-approved-create-thread-documented-callable-wiring-boundary"
  human_wiring_scope: "single-documented-create-thread-callable-wiring-non-live-by-default"
  external_write_authorized: false
  destructive_action_approved: false
executor_contract:
  target_identity_rechecked_by_executor: true
  authorization_intent_rechecked_by_executor: true
  permission_auth_failure_classified_by_executor: true
  runtime_response_shape_validated_by_executor: true
  returned_thread_id_validated_by_executor: true
  returned_status_validated_by_executor: true
  target_validation:
    satisfied_by_prior_evidence: false
  permission_failure_handling:
    satisfied_by_prior_evidence: false
  response_validation:
    satisfied_by_prior_evidence: false
callable_descriptor:
  descriptor_type: "runtime-provided-documented-callable-descriptor | runtime-provided-adapter-registration-envelope | explicit-non-live-adapter-wiring-contract"
  source_type: "caller-supplied-documented-runtime-metadata | active-tool-list-excerpt | runtime-provided-schema-excerpt | runtime-provided-documented-callable-descriptor | explicit-non-live-adapter-wiring-contract"
  source_excerpt: "documented source supplied by the caller"
  last_verified: "YYYY-MM-DD"
  target_action: "create-thread"
  tool_or_api: "create_thread"
  allowed_target_actions: ["create-thread"]
  required_request_fields: ["prompt.body", "target.repo"]
  minimum_response_fields: ["thread_id", "status"]
  caller_supplied: true
  documented_callable: true
  execution_allowed: false
  runtime_lookup_performed: false
  runtime_call_shape_present: false
  live_desktop_runtime: false
  external_write_authorized: false
previous_executor_evidence: "ready output from desktop_runtime_create_thread_executor.py"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and expected head evidence;
- prompt summary/body presence evidence;
- callable-wiring human approval marker evidence;
- descriptor source evidence;
- executor call-site requirements that must still be enforced by the executor helper;
- an `adapter_contract` and `executor_request_patch` matching the executor helper's `callable_adapter` shape;
- `runtime_call_performed: false`, `desktop_runtime_call_performed: false`, `private_runtime_state_read: false`, and `external_write_performed: false`.

The helper returns `ready` only when a caller-supplied documented descriptor or explicit non-live wiring contract can be converted into the executor helper's injected adapter contract shape. It returns `fallback` when the exact callable wiring marker or descriptor is missing. It returns `stopped` when ready previous executor evidence is missing, fallback, or stopped; the exact target action or tool/API name is wrong; repo/remote/branch/expected-head evidence is incomplete; prompt summary/body is missing; external writes are authorized; destructive-action approval is present; a runtime call has already been performed before wiring; Desktop private runtime state was read; the descriptor is malformed, sourced from private runtime-looking material, permits runtime lookup, includes a direct runtime call shape, or names any path other than `create_thread`; or prior evidence is treated as satisfying executor call-site target validation, permission/auth handling, or response validation.

`ready` is callable wiring readiness only. It does not mean a live Desktop runtime `create_thread` call was performed or authorized. True Desktop runtime `create_thread` callable injection or use still requires separate human approval and a runtime-provided documented callable. Any later live wiring slice must connect at most one documented `create_thread` tool path and must continue to re-check target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status at the actual call site.

The helper does not call `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize external writes, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, background service, or live Desktop runtime executor.

Focused tests live in `tests/test_desktop_runtime_create_thread_callable_wiring.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Read-Thread Preflight Implementation Artifact

The read-thread runtime-call preflight helper is `scripts/desktop_runtime_read_thread_preflight.py`.
It accepts a prepared JSON request containing target repo and thread-id evidence, read-request purpose evidence, normalized `read-thread` capability evidence, compatible contract comparison output, and safety boundaries.

Usage examples:

```bash
python3 scripts/desktop_runtime_read_thread_preflight.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_read_thread_preflight.py --pretty < read-thread-preflight.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "preflight-read-thread-runtime-call"
target_action: "read-thread"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  thread_id: "thread identifier supplied by the caller"
read_request:
  summary: "short reason for checking read-only evidence readiness"
  expected_fields: ["status", "thread_id"]
capability_evidence:
  status: "available"
  capabilities:
    - action: "read-thread"
      tool_or_api: "read_thread"
      classification: "read-only"
      required_request_fields: ["thread_id"]
      minimum_response_fields: ["status", "thread_id"]
      capability_source: "active tool list"
      contract_version: "version unavailable"
      last_verified: "YYYY-MM-DD"
contract_comparison:
  status: "compatible"
  target_action: "read-thread"
  contract_comparison:
    compared_fields: ["action", "tool_or_api", "classification", "required_request_fields", "minimum_response_fields"]
    old_contract: "old read-thread contract evidence"
    new_capability: "new normalized read-thread capability evidence"
boundaries:
  in_scope: ["durable repo files or task scope"]
  out_of_scope: [".work/", "Desktop private runtime state"]
  external_writes_blocked: true
authorization:
  thread_action_authorized: false
  external_write_authorized: false
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- target repo, remote, branch, and thread-id evidence;
- read-request summary and expected fields;
- contract comparison status and compared fields;
- selected `read-thread` capability classification, request shape, response shape, source, version, and `last_verified`;
- authorization evidence showing that runtime-call authorization remains separate from evidence readiness;
- `runtime_call_performed: false`;
- a readiness note stating that `ready` is evidence only for a future separately approved read-only runtime call.

The helper returns `fallback` when normalized read-thread capability evidence or compatible contract comparison evidence is unavailable. It returns a paste-ready prompt and states that no Desktop thread was opened, created, forked, messaged, or read.

The helper returns `stopped` when contract comparison stopped or is not compatible, request or response evidence is unclear, read-thread classification is not `read-only`, repo/remote/branch/thread-id evidence is incomplete, `read_request.expected_fields` is missing, forbidden private source hints appear, runtime-call authorization is treated as part of preflight, or external writes are requested or no longer blocked.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, collect metadata, infer runtime availability, authorize runtime calls, authorize external writes, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_read_thread_preflight.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## End-To-End Evidence Pipeline Example

The evidence-only pipeline helper is `scripts/desktop_runtime_evidence_pipeline.py`.
It accepts a prepared JSON request containing caller-supplied capability metadata, old wrapper contract evidence, target repo evidence, create-thread prompt evidence, read-thread purpose evidence, safety boundaries, and action-specific authorization evidence. It then runs the existing helpers in order:

1. normalize caller-supplied capability metadata;
2. compare old wrapper contract evidence with the normalized capability evidence for each requested action;
3. run create-thread and/or read-thread preflight using the comparison output;
4. emit one aggregate `ready`, `fallback`, or `stopped` evidence record.

Usage examples:

```bash
python3 scripts/desktop_runtime_evidence_pipeline.py --example --pretty
```

Print a single target action fixture:

```bash
python3 scripts/desktop_runtime_evidence_pipeline.py --example --target-action read-thread --pretty
```

```bash
python3 scripts/desktop_runtime_evidence_pipeline.py --pretty < desktop-runtime-evidence-pipeline.json
```

Run only one target action from a prepared fixture:

```bash
python3 scripts/desktop_runtime_evidence_pipeline.py --target-action create-thread --pretty < desktop-runtime-evidence-pipeline.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "build-desktop-runtime-wrapper-v1-evidence-pipeline"
target_actions: ["create-thread", "read-thread"]
metadata_request:
  requested_action: "normalize-runtime-capability-metadata"
  metadata_source:
    source: "active tool list | connector metadata | official documentation | runtime-reported schema | installed plugin metadata | documented API"
    contract_version: "version unavailable"
    last_verified: "YYYY-MM-DD"
    available: true
  capabilities: ["caller-supplied documented capability metadata"]
old_contracts:
  create-thread: "old create-thread wrapper contract evidence"
  read-thread: "old read-thread wrapper contract evidence"
target:
  repo: "owner/name"
  remote: "origin URL"
  branch: "branch-name"
  expected_head: "commit SHA expected by the caller"
  thread_id: "thread identifier supplied by the caller"
prompt:
  summary: "short prepared create-thread prompt summary"
  body: "prepared create-thread prompt body"
read_request:
  summary: "short reason for checking read-only evidence readiness"
  expected_fields: ["status", "thread_id"]
boundaries:
  in_scope: ["durable repo files or task scope"]
  out_of_scope: [".work/", "Desktop private runtime state"]
  external_writes_blocked: true
authorization:
  thread_action_authorized:
    create-thread: true
    read-thread: false
  external_write_authorized: false
```

The pipeline output includes a top-level `summary` with `readiness_counts`, per-target comparison/preflight status, the primary reason, and the recommended next step. The detailed `steps` array remains the evidence ledger for reviewers who need the helper-by-helper output. The pipeline helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not collect metadata, inspect Desktop private runtime state, infer runtime availability, authorize runtime calls, authorize external writes, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service. A `ready` aggregate result means every requested preflight returned evidence readiness only; it is not approval to perform a runtime call or external write.

Focused tests live in `tests/test_desktop_runtime_evidence_pipeline.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Session Compatibility Status Validation Artifact

The session compatibility status validator is `scripts/desktop_runtime_session_compatibility_status.py`.
It accepts a prepared JSON request containing the expected wrapper/package/repo identity and explicit caller-supplied compatibility status, then validates that the status can be referenced by a later preflight as contract compatibility evidence.

Usage examples:

```bash
python3 scripts/desktop_runtime_session_compatibility_status.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_session_compatibility_status.py --pretty < session-compatibility-status.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "validate-session-compatibility-status"
expected:
  wrapper_version: "0.1.0" # or skill_package_version / repo_commit
  helper_version: "0.1.0"
  target_action: "read-thread"
  tool_or_api: "read_thread"
  schema_hash: "sha256:..." # or normalized_contract_evidence
compatibility_status:
  wrapper_version: "0.1.0" # or matching skill_package_version / repo_commit
  helper_version: "0.1.0"
  target_action: "read-thread"
  tool_or_api: "read_thread"
  runtime_reported_version: "version unavailable"
  capability_source: "active tool list | connector metadata | documented API | installed plugin metadata | official documentation | runtime-reported schema"
  schema_hash: "sha256:..." # or normalized_contract_evidence
  comparison_result: "compatible | fallback | stopped"
  last_verified: "YYYY-MM-DD"
  session_identity:
    marker_type: "runtime-lifecycle | session-id | current-process | current-session"
    marker: "runtime lifecycle marker, session id, or explicit current-session scoped marker"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- selected wrapper/package/repo identity, helper version, target action, tool/API name, runtime-reported version, source, schema hash, comparison result, `last_verified`, and session marker summary;
- `runtime_call_performed: false`;
- `cache_write_performed: false`;
- `private_runtime_state_read: false`;
- `later_runtime_path_blocked: true` for `fallback` or `stopped`;
- a readiness note stating that `ready` means the status can be referenced by a later preflight only.

The helper returns `ready` only for a caller-supplied `compatible` status whose identity and schema evidence match the expected fields. It returns `fallback` for a caller-supplied `fallback` status, because later runtime-call paths must use fallback rather than trust a compatible contract. It returns `stopped` for a caller-supplied `stopped` status, wrapper/helper mismatch, target action or tool/API mismatch, schema hash or normalized contract evidence mismatch, missing or unclear session marker, forbidden private runtime hints, or attempts to store authorization, target validation, permission validation, or response validation in the status.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, perform a first-use handshake, write a compatibility cache, read a compatibility cache, authorize runtime calls, authorize external writes, validate targets or permissions, validate runtime responses, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_session_compatibility_status.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## First-Use Session Compatibility Handshake Artifact

The first-use session compatibility handshake helper is `scripts/desktop_runtime_session_compatibility_handshake.py`.
It accepts a prepared JSON request containing caller-supplied documented capability metadata, old wrapper contract evidence, expected wrapper/helper identity, and an explicit session identity marker. It then runs the V1 evidence order:

1. normalize caller-supplied capability metadata;
2. compare old wrapper contract evidence with the normalized capability evidence;
3. construct a session compatibility status object;
4. validate that status with `scripts/desktop_runtime_session_compatibility_status.py`;
5. emit one `ready`, `fallback`, or `stopped` evidence record.

Usage examples:

```bash
python3 scripts/desktop_runtime_session_compatibility_handshake.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_session_compatibility_handshake.py --pretty < session-compatibility-handshake.json
```

The stdin request must be JSON and should use this minimal shape:

```yaml
requested_action: "build-session-compatibility-handshake"
target_action: "read-thread"
expected:
  wrapper_version: "0.1.0" # or skill_package_version / repo_commit
  handshake_helper_version: "0.1.0"
  status_helper_version: "0.1.0"
  target_action: "read-thread"
  tool_or_api: "read_thread"
  schema_hash: "optional expected sha256:..." # or normalized_contract_evidence
old_contract:
  action: "read-thread"
  tool_or_api: "read_thread"
  classification: "read-only"
  required_request_fields: ["thread_id"]
  minimum_response_fields: ["status", "thread_id"]
  capability_source: "runtime-reported schema"
  contract_version: "version unavailable"
  last_verified: "YYYY-MM-DD"
metadata_request:
  requested_action: "normalize-runtime-capability-metadata"
  metadata_source:
    source: "active tool list | connector metadata | documented API | installed plugin metadata | official documentation | runtime-reported schema"
    contract_version: "version unavailable"
    last_verified: "YYYY-MM-DD"
    available: true
  capabilities: ["caller-supplied documented capability metadata"]
session_identity:
  marker_type: "runtime-lifecycle | session-id | current-process | current-session"
  marker: "runtime lifecycle marker, session id, or explicit current-session scoped marker"
```

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- an evidence `steps` ledger for capability discovery, contract comparison, and session status validation;
- the constructed `session_compatibility_status`;
- the validator output under `validated_status`;
- `runtime_calls_performed: false`;
- `cache_read_performed: false`;
- `cache_write_performed: false`;
- `private_runtime_state_read: false`;
- `later_runtime_path_blocked: true` for `fallback` or `stopped`;
- a readiness note stating that `ready` means first-use handshake evidence only.

The helper returns `ready` only when caller-supplied metadata compares as compatible and the constructed session status validates. It returns `fallback` when comparison or status validation falls back. It returns `stopped` when discovery, comparison, status construction, status validation, wrapper/helper identity, schema hash or normalized contract evidence, session marker, private runtime source hints, or authorization-substitute fields are unsafe or unclear.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, write a compatibility cache, read a compatibility cache, authorize runtime calls, authorize external writes, validate targets or permissions, validate runtime responses, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_session_compatibility_handshake.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Session-Scoped Compatibility Cache Artifact

The session-scoped compatibility cache helper is `scripts/desktop_runtime_session_compatibility_cache.py`.
It accepts prepared JSON requests to write or read a caller-explicit cache file. The cache envelope stores contract compatibility evidence only and is scoped to the current process/session.

Usage examples:

```bash
python3 scripts/desktop_runtime_session_compatibility_cache.py --example --pretty
```

```bash
python3 scripts/desktop_runtime_session_compatibility_cache.py --pretty < session-compatibility-cache.json
```

The write request should use this minimal shape:

```yaml
requested_action: "write-session-compatibility-cache"
cache_file: "/absolute/caller/supplied/cache-file.json"
expected:
  wrapper_version: "0.1.0" # or skill_package_version / repo_commit
  cache_helper_version: "0.1.0"
  status_helper_version: "0.1.0"
  target_action: "read-thread"
  tool_or_api: "read_thread"
  schema_hash: "sha256:..." # or normalized_contract_evidence
current_session_identity:
  marker_type: "runtime-lifecycle | session-id | current-process | current-session"
  marker: "runtime lifecycle marker, session id, or explicit current-session scoped marker"
cache_envelope:
  wrapper_version: "0.1.0" # or matching skill_package_version / repo_commit
  cache_helper_version: "0.1.0"
  status_helper_version: "0.1.0"
  target_action: "read-thread"
  tool_or_api: "read_thread"
  runtime_reported_version: "version unavailable"
  capability_source: "active tool list | connector metadata | documented API | installed plugin metadata | official documentation | runtime-reported schema"
  schema_hash: "sha256:..." # or normalized_contract_evidence
  comparison_result: "compatible | fallback | stopped"
  last_verified: "YYYY-MM-DD"
  session_identity:
    marker_type: "runtime-lifecycle | session-id | current-process | current-session"
    marker: "runtime lifecycle marker, session id, or explicit current-session scoped marker"
  cache_scope: "same-session"
  cache_lifecycle_marker: "same-session-only"
  same_session_only: true
  created_at: "YYYY-MM-DDTHH:MM:SSZ"
  expires_at: "optional YYYY-MM-DDTHH:MM:SSZ"
  compatibility_status: "validated session compatibility status object"
```

The read request omits `cache_envelope` and supplies `requested_action: "read-session-compatibility-cache"`, the same `cache_file`, the expected identity/schema fields, and the current session identity marker.

The helper output includes:

- status: `ready`, `fallback`, or `stopped`;
- selected wrapper/package/repo identity, cache helper version, status helper version, target action, tool/API name, runtime-reported version, source, schema hash, comparison result, `last_verified`, session marker, cache scope, lifecycle marker, and created/expiry summary;
- `runtime_call_performed: false`;
- `private_runtime_state_read: false`;
- `cache_read_performed` or `cache_write_performed` only for the explicit cache file operation;
- `later_runtime_path_blocked: true` for `fallback` or `stopped`;
- a readiness note stating that `ready` means same-session cache evidence can be referenced by a later preflight only.

The helper returns `ready` only when the cache envelope is compatible, matches expected identity and schema evidence, uses a same-session cache scope, and matches the current session marker. It returns `fallback` for cached `fallback` comparison evidence. It returns `stopped` for cached `stopped` comparison evidence, wrapper/helper/status helper mismatch, schema hash or normalized contract evidence mismatch, missing or mismatched session marker, stale or expired cache, forbidden private runtime source hints, Desktop private runtime-looking cache paths, or attempts to store authorization, target validation, permission validation, or response validation in cache evidence.

The helper does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or any documented equivalent. It does not inspect Desktop private runtime state, perform a first-use handshake, authorize runtime calls, authorize external writes, validate targets or permissions, validate runtime responses, or add a public skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.

Focused tests live in `tests/test_desktop_runtime_session_compatibility_cache.py` and can be rerun with:

```bash
python3 -B -m unittest discover -s tests
```

## Later Slice Candidates

Later slices require separate review and human approval:

- a single state-changing live Desktop runtime `create-thread` call path using one documented runtime-provided callable, after the injected executor and callable wiring-boundary helpers remain stable.

Each later slice must keep private runtime state prohibited. Runtime-call slices may rely on a compatible session status, same-session cache evidence, preflight evidence, authorization gate evidence, executor boundary proposal evidence, executor shell evidence, injected executor helper evidence, or callable wiring evidence for their documented purpose only, but must still re-check authorization intent, target identity, permission/auth failure result, runtime response shape, returned thread id, and returned status at the point of use.

## Next-Session Handoff

Recommended next Desktop runtime wrapper V1 slice:

1. If maintainers approve true wiring, connect at most one documented runtime-provided `create_thread` callable path through the existing injected executor helper.
2. Keep cache/status/preflight/gate/proposal/shell/injected-executor/wiring evidence scoped to evidence only; exact runtime action authorization, external-write authorization, destructive-action approval, target repo/branch/expected-head validation, auth/permission failure handling, and runtime response validation must still happen at the point of use.
3. Do not introduce a daemon, MCP server, app-server client, sidecar, background service, Desktop private runtime state reader, skill, catalog item, or installer entry.

Definition of done for that slice:

- It has separate human approval for the exact runtime action before implementation.
- It connects at most one documented `create_thread` runtime callable path.
- It does not read Desktop private runtime state.
- It does not add a skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.
- It documents and tests that prior evidence is not call-site target validation, permission/auth handling, or runtime response validation, and that Codex CLI/Desktop restart invalidates session compatibility status.

## Verification Strategy

For this plan and post-merge documentation alignment:

- `./scripts/validate-repo.sh`
- `git diff --check`
- formal docs review

For the completed first implementation slices:

- schema validation tests for required and optional fields;
- fallback tests proving no Desktop thread action is claimed when capability is unavailable;
- stop-condition tests for missing contract evidence, unclear repo identity, external-write requests, and forbidden source hints;
- capability discovery tests proving caller-supplied metadata is normalized, unavailable metadata is reported as unavailable, ambiguous classification stops, and forbidden source hints stop;
- contract comparison tests proving compatible evidence returns `compatible`, missing or unavailable capability returns `fallback`, changed request shape, response shape, classification, or tool/API name returns `stopped`, forbidden private source hints stop, and state-changing evidence is compared without authorizing runtime calls;
- create-thread preflight tests proving compatible evidence plus exact authorization returns `ready`, unavailable capability or comparison evidence returns `fallback`, thread action authorization false returns `fallback`, incompatible or unclear comparison evidence returns `stopped`, read-only create-thread classification stops, external-write authorization stops, missing repo/remote/branch/expected-head evidence stops, forbidden source hints stop, and no `create_thread` call is made;
- read-thread preflight tests proving the discovery-to-comparison-to-preflight evidence chain returns `ready`, unavailable capability or comparison evidence returns `fallback`, incompatible comparison evidence returns `stopped`, state-changing read-thread classification stops, preflight-scoped runtime-call authorization stops, external-write authorization stops, missing thread-id or expected-fields evidence stops, forbidden source hints stop, and no `read_thread` call is made;
- evidence pipeline tests proving discovery-to-comparison-to-create/read-preflight order returns aggregate `ready`, missing old contract evidence returns aggregate `fallback`, changed request shape returns aggregate `stopped`, single target action filtering works, summary fields make target reasons scannable, read-thread runtime-call authorization remains out of scope, request inputs are not mutated, and no runtime call is made;
- session compatibility status tests proving compatible status returns `ready`, fallback/stopped status blocks later runtime paths, wrapper/helper version mismatch stops, schema hash or normalized contract evidence mismatch stops, missing session marker stops or requires an explicit current-process/current-session scoped marker, status cannot replace action authorization/external-write authorization/target validation/permission handling/response validation, and no Desktop private runtime state is read;
- first-use session compatibility handshake tests proving compatible metadata creates a validated `ready` session status, fallback/stopped comparison blocks later runtime paths, wrapper/helper version mismatch stops, schema hash or normalized contract evidence mismatch stops, missing session marker stops, explicit current-session scoped marker is accepted, status cannot replace action authorization/external-write authorization/target validation/permission handling/response validation, no cache read/write occurs, no Desktop private runtime state is read, and no Desktop thread tool symbols are introduced;
- session-scoped compatibility cache tests proving same-session status reuse through an explicit cache envelope, fallback/stopped cached status blocking, wrapper/cache helper/status helper version invalidation, schema hash or normalized contract evidence invalidation, missing or mismatched session marker stops, explicit current-session scoped markers are accepted only for same-session cache envelopes, stale or expired cache stops, cache evidence cannot replace authorization/target/permission/response validation, Desktop private runtime-looking paths and source hints are rejected, no Desktop private runtime state is read, and no Desktop thread tool symbols, daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- create-thread authorization gate tests proving a complete caller-supplied envelope returns `ready`, missing exact action/tool or target evidence stops, fallback/stopped preflight/status/cache evidence blocks, stale or session-mismatched cache evidence blocks, external-write or destructive-action approval stops, cache/preflight/status evidence cannot replace authorization/target/permission/response validation, missing human approval marker returns `fallback`, private runtime-looking source hints stop, no Desktop private runtime state is read, and no Desktop thread tool call functions, daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- create-thread executor boundary proposal tests proving a complete proposal envelope returns `ready`, missing authorization gate evidence stops, fallback/stopped authorization gate evidence blocks, wrong action/tool stops, missing repo/remote/branch/expected-head or prompt evidence stops, external-write or destructive-action approval stops, runtime-call-performed or private-runtime-state-read evidence stops, prior evidence cannot replace call-site target validation/permission handling/response validation, missing proposal-only human approval marker returns `fallback`, private runtime-looking paths and source hints are rejected, no Desktop thread tool call shapes are introduced, and no daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- create-thread executor shell tests proving a complete implementation-surface envelope returns `ready`, missing executor boundary proposal evidence stops, fallback/stopped proposal evidence blocks, wrong action/tool stops, missing repo/remote/branch/expected-head or prompt evidence stops, external-write or destructive-action approval stops, runtime-call-performed or private-runtime-state-read evidence stops, prior proposal/gate/cache/preflight evidence cannot replace call-site target validation/permission handling/response validation, missing executor-shell implementation marker returns `fallback`, callable descriptors cannot authorize execution or contain direct runtime-call shapes, private runtime-looking paths and source hints are rejected, no Desktop thread tool call shapes are introduced, and no daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- create-thread documented callable executor tests proving a complete non-live injected callable envelope returns `ready`, missing/fallback/stopped shell evidence blocks, wrong action/tool stops, missing repo/remote/branch/expected-head or prompt evidence stops, external-write or destructive-action approval stops, runtime-call-performed or private-runtime-state-read evidence before execution stops, prior proposal/gate/cache/preflight/shell evidence cannot replace call-site target validation/permission handling/response validation, missing executor implementation marker returns `fallback`, auth/permission failures are classified and returned, malformed adapter response stops, missing returned thread id stops, invalid returned status stops, successful injected adapter execution is clearly labeled as injected adapter execution rather than Desktop runtime execution, private runtime-looking paths and source hints are rejected, no additional Desktop thread tool call shapes are introduced, and no daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- create-thread callable wiring-boundary tests proving a complete caller-supplied documented descriptor returns `ready`, CLI/default without a descriptor returns `fallback`, missing/fallback/stopped previous executor evidence blocks, wrong action/tool stops, missing repo/remote/branch/expected-head or prompt evidence stops, external-write or destructive-action approval stops, runtime-call-performed or private-runtime-state-read evidence before wiring stops, prior evidence cannot replace executor call-site target validation/permission handling/response validation, missing callable wiring marker returns `fallback`, malformed descriptors stop, non-`create_thread` descriptors stop, private runtime-looking paths and source hints are rejected, successful non-live wiring is clearly labeled as callable wiring readiness rather than Desktop runtime execution, tests do not invoke live Desktop runtime, no additional Desktop thread tool call shapes are introduced, and no daemon, MCP server, app-server client, sidecar, or background service claims are introduced;
- docs review for public claims and runtime compatibility;
- code review gate only if the implementation slice is used for commit or PR readiness.

## Stop Conditions Before Later Implementation Slices

Stop before implementing later wrapper code when:

- the implementation location, public API shape, or packaging target is unclear;
- the runtime capability source cannot be recorded without private Desktop runtime state;
- a later slice would need a daemon, MCP server, app-server client, background service, new skill, catalog entry, or installer entry;
- the proposed code would call state-changing thread tools without separate explicit approval;
- the proposed code would treat cached compatibility, preflight evidence, authorization gate evidence, executor boundary proposal evidence, or executor shell evidence as runtime action authorization, external-write authorization, destructive-action approval, target validation, auth/permission success, or runtime response validation;
- tests would require Desktop private runtime files or unpublished Desktop internals;
- external-write or destructive-action boundaries are ambiguous;
- maintainers have not approved the specific later implementation slice.
