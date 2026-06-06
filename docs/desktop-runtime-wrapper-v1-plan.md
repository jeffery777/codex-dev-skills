# Desktop Runtime Wrapper V1 Feasibility And Implementation Plan

This document answers whether the repository can move from the accepted Desktop runtime adapter boundary toward first implementation slices. The completed V1 slices now exist as non-state-changing helpers: a request planner and fallback generator, a capability metadata normalization helper, a contract comparison helper, a create-thread runtime-call preflight helper, a read-thread runtime-call preflight helper, and an end-to-end evidence pipeline example. They do not implement a daemon, MCP server, app-server client, background service, Desktop runtime integration, catalog entry, installer entry, skill, or runtime-call path.

## Decision

Implementation is conditionally feasible for a V1 Desktop runtime wrapper, but only as a narrow convenience layer over runtime thread tools or documented APIs that are already exposed by the active runtime.

The first implementation slice is complete as a non-state-changing request planner and fallback generator. It validates a prepared thread-action request, records the minimum contract evidence needed for a future runtime call, can consume normalized capability evidence supplied by the discovery helper, and produces either structured dry-run evidence or a CLI-compatible paste-ready fallback. It does not create, fork, continue, message, or read a Desktop thread.

The read-only capability discovery slice is also complete as a non-state-changing metadata normalizer. It accepts only caller-supplied documented metadata, such as an active tool list excerpt, connector metadata, official documentation, or runtime-reported schema that has already been gathered and supplied to the helper. It records action names, read-only or state-changing classification, required request fields, minimum response fields, capability source, contract version or `version unavailable`, `last_verified`, and helper version. The planner can accept this normalized output as `capability_evidence`, select the requested target action, and stop or fall back when the evidence is unavailable, missing, mismatched, unclear, or sourced from forbidden Desktop runtime hints. It does not gather metadata itself, inspect Desktop private runtime state, or call any Desktop thread tool.

The contract comparison slice is also complete as a non-state-changing compatibility re-check helper. It compares old wrapper contract evidence against newer normalized capability evidence before a runtime, connector, schema, or documentation change is trusted. It returns `compatible` when the tool/API name, action classification, required request fields, and minimum response fields still match; `fallback` when the capability is unavailable or missing; and `stopped` when the comparison detects changed request shape, response shape, classification, tool/API name, missing evidence, or forbidden Desktop runtime source hints. State-changing actions such as `create-thread` may be compared as evidence only; comparison does not authorize or call the runtime tool.

The create-thread preflight slice is also complete as a non-state-changing readiness helper. It consumes target repo evidence, prepared prompt evidence, normalized `create-thread` capability evidence, and compatible contract comparison evidence, then returns `ready`, `fallback`, or `stopped`. `ready` only means evidence is ready for a future separately approved `create_thread` runtime call; it does not mean the helper called `create_thread`, opened a thread, or authorized commit, push, PR creation, merge, or any other external write. The helper returns `fallback` when capability or comparison evidence is unavailable or exact thread-action authorization is false, and `stopped` when contract evidence is incompatible or unclear, the action classification is not `state-changing`, repo/remote/branch/expected-head evidence is incomplete, private source hints appear, or external-write boundaries are not blocked.

The read-thread preflight slice is also complete as a non-state-changing readiness helper. It consumes target repo and thread-id evidence, read-request purpose evidence, normalized `read-thread` capability evidence, and compatible contract comparison evidence, then returns `ready`, `fallback`, or `stopped`. `ready` only means evidence is ready for a future separately approved read-only `read_thread` runtime call; it does not mean the helper called `read_thread`, read a Desktop thread, or authorized commit, push, PR creation, merge, or any other external write. The helper keeps runtime-call authorization out of scope and stops if a caller tries to treat preflight as runtime-call authorization.

The evidence pipeline slice is also complete as a non-state-changing CLI example. It chains caller-supplied capability metadata through discovery, old/new contract comparison, and create/read preflight helpers, then emits one aggregate evidence record. It supports running a single target action when maintainers want narrower evidence, and its top-level `summary` makes ready/fallback/stopped reasons easier for review gates and maintainers to scan. It is meant to make the planner -> discovery -> compare -> preflight order easy to run and inspect. It does not gather metadata itself, call Desktop thread tools, read Desktop private runtime state, or authorize runtime calls or external writes.

The next candidate slice before any runtime-call path is a session capability handshake and compatibility cache model. A future wrapper should avoid re-checking the underlying runtime schema before every API or runtime tool call. Instead, the first wrapper use in each Codex CLI or Codex Desktop process/session should perform one documented capability handshake, compare the current runtime contract with the wrapper's recorded contract, and store a session-scoped compatibility status. Later wrapper use in the same process/session should read that compatibility status rather than spending another runtime/tool/schema lookup. A compatible status can permit action-specific preflight to proceed; fallback or stopped status must cause later use to fallback or stop. This cache is not durable across Codex CLI/Desktop restarts and must not replace action authorization, target validation, permission handling, or response validation.

State-changing thread calls can be considered only after the completed evidence-only helpers remain stable, after the session capability handshake and compatibility cache slice is designed and reviewed, and after a separate human decision approves adding a runtime-call path for one documented action.

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

For a future session capability handshake, callers may perform this comparison once per Codex CLI/Desktop process/session and record a session-scoped compatibility status. The status should be valid only for the current process/session or runtime lifecycle marker. If the runtime exposes no lifecycle marker, the status must explicitly say it is current-process/current-session scoped. Restarting Codex CLI/Desktop invalidates the status and requires a new handshake before the wrapper trusts the runtime contract again.

The compatibility cache should record at least:

- wrapper, skill package, or repository commit version;
- helper version;
- target action, such as `read-thread` or `create-thread`;
- tool/API name, such as `read_thread` or `create_thread`;
- runtime-reported version, or `version unavailable` when no version is exposed;
- capability source;
- schema/contract hash or equivalent normalized contract evidence;
- comparison result: `compatible`, `fallback`, or `stopped`;
- `last_verified`;
- session identity or runtime lifecycle marker, or an explicit current-process/current-session scoped marker when no runtime marker is available.

The compatibility status must not cache or replace:

- exact runtime action authorization;
- external-write authorization;
- destructive-action approval;
- target repo, branch, thread id, or expected-head validation;
- auth or permission failure results;
- actual runtime tool-call response validation.

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

## Later Slice Candidates

Later slices require separate review and human approval:

- a non-state-changing session compatibility status schema;
- a first-use handshake planner/helper that accepts caller-supplied documented metadata, compares it with recorded wrapper contract evidence, and emits session-scoped compatibility status without reading Desktop private runtime state;
- a compatibility cache read/write helper, initially designed around repo-safe session-scoped artifacts or explicit caller-supplied status rather than a daemon, sidecar, app-server client, Desktop private state, or background service;
- docs that distinguish contract compatibility, action authorization, and preflight readiness;
- a single state-changing `create-thread` call path using an already exposed runtime tool;
- additional `fork-thread` or `send-message` paths only after the single-action path is stable.

The session capability handshake and compatibility cache slice should be prioritized before any true runtime-call path. Each later slice must keep private runtime state prohibited. Runtime-call slices may rely on a compatible session status for contract compatibility only, but must still re-check authorization, target evidence, and actual runtime responses at the point of use.

## Next-Session Handoff

Recommended next Desktop runtime wrapper V1 slice:

1. Add a non-state-changing session compatibility status schema.
2. Add a first-use handshake planner/helper that accepts caller-supplied documented metadata only, compares it with recorded wrapper contract evidence, and returns `compatible`, `fallback`, or `stopped` session status.
3. Add a compatibility cache read/write helper using a repo-safe session-scoped artifact or explicit caller-supplied status model. Do not introduce a daemon, MCP server, app-server client, sidecar, background service, Desktop private runtime state reader, skill, catalog item, or installer entry.
4. Update docs to state that contract compatibility may be session-cached, while exact runtime action authorization, external-write authorization, destructive-action approval, target repo/branch/thread-id/expected-head validation, auth/permission failures, and runtime response validation cannot be replaced by cache.
5. Add tests proving first use creates compatible status, same-session use reuses compatible status, wrapper/helper version changes invalidate status, schema hash or normalized contract evidence changes invalidate or stop status, fallback/stopped status blocks runtime paths, and no Desktop private runtime state is read.

Definition of done for that slice:

- It remains non-state-changing and evidence-only.
- It does not call `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or documented equivalents.
- It does not read Desktop private runtime state.
- It does not add a skill, catalog item, installer entry, daemon, MCP server, app-server client, sidecar, or background service.
- It documents that Codex CLI/Desktop restart invalidates session compatibility status.

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
- future session compatibility cache tests proving first-use status creation, same-session status reuse, wrapper/helper version invalidation, schema hash or normalized contract evidence invalidation, fallback/stopped status blocking, and no Desktop private runtime state access;
- docs review for public claims and runtime compatibility;
- code review gate only if the implementation slice is used for commit or PR readiness.

## Stop Conditions Before Later Implementation Slices

Stop before implementing later wrapper code when:

- the implementation location, public API shape, or packaging target is unclear;
- the runtime capability source cannot be recorded without private Desktop runtime state;
- a later slice would need a daemon, MCP server, app-server client, background service, new skill, catalog entry, or installer entry;
- the proposed code would call state-changing thread tools without separate explicit approval;
- the proposed code would treat cached compatibility as runtime action authorization, external-write authorization, destructive-action approval, target validation, auth/permission success, or runtime response validation;
- tests would require Desktop private runtime files or unpublished Desktop internals;
- external-write or destructive-action boundaries are ambiguous;
- maintainers have not approved the specific later implementation slice.
