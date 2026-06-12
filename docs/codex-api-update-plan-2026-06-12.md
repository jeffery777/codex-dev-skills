# Codex API Update Check And Plan - 2026-06-12

## Objective

Check whether the current Codex CLI and Codex Desktop exposed interfaces affect this skill pack, then define the smallest safe update plan.

## Sources Checked

Facts:

- Local repository was updated to `origin/main` before this check.
- Local CLI reports `codex-cli 0.139.0`.
- Official Codex manual was refreshed with `openai-docs` into local cache on 2026-06-12.
- `codex app-server generate-json-schema --out /private/tmp/codex-app-server-schema-check` succeeded and produced v2 JSON schemas.
- Current Codex Desktop session exposes app-level thread tools through the active tool list: `create_thread`, `fork_thread`, `read_thread`, `send_message_to_thread`, `handoff_thread`, `list_threads`, `set_thread_title`, `set_thread_pinned`, and `set_thread_archived`.

Official source references:

- https://developers.openai.com/codex/app-server
- https://developers.openai.com/codex/sdk
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/mcp

## Interface Findings

### Codex app-server

Facts:

- The documented programmatic interface is `codex app-server`, using JSON-RPC 2.0 style messages over `stdio`, experimental WebSocket, Unix socket, or `off`.
- Clients must call `initialize`, then send `initialized`, before other app-server methods.
- The current app-server schema includes v2 methods and schemas such as `ThreadStartParams`, `ThreadStartResponse`, `ThreadForkParams`, `ThreadForkResponse`, `ThreadReadParams`, `ThreadReadResponse`, `ThreadListParams`, `ThreadListResponse`, and `TurnStartParams`.
- `ThreadStartResponse` and `ThreadForkResponse` return a `thread` object rather than the Desktop tool response shape used by this repository's V1 live smoke helper.
- `TurnStartParams` requires `threadId` and `input`.
- Some app-server fields and methods are gated by `initialize.params.capabilities.experimentalApi`.
- App-server WebSocket auth now includes capability-token and signed-bearer-token modes.

Inference:

- This repository should continue to treat app-server as a separate documented API family, not as a drop-in replacement for Desktop app tool calls.
- If this skill pack ever adds an app-server adapter, it should be a new, separately reviewed slice with generated schema evidence, initialization handling, transport/auth handling, and explicit human gates.

### Codex Desktop app tools

Facts:

- The current Desktop session tool schema exposes `create_thread` as:
  - `prompt` required.
  - `target` required, with `project` or `projectless` union.
  - Project targets require `projectId` and `environment`, where environment can be local or worktree.
  - Optional `model` and `thinking`.
- `fork_thread` accepts an optional source `threadId` and optional environment.
- `read_thread` requires `threadId` and supports `turnLimit`, `cursor`, `includeOutputs`, and `maxOutputCharsPerItem`.
- `send_message_to_thread` requires `threadId` and `prompt`, with optional `model` and `thinking`.
- `handoff_thread`, thread title, pin, and archive operations are also state-changing Desktop thread actions.

Inference:

- The V1 wrapper's "caller-supplied documented callable" safety model still fits the updated Desktop tool surface.
- The wrapper's contract fixtures and docs should be updated to record the current request shape more precisely, especially `create_thread.target.project/projectless`, optional `thinking`, `read_thread.includeOutputs`, and the response spelling expected by Desktop.

## Impact On This Skill Pack

Needs update:

- `create_thread` response compatibility should explicitly accept and test `threadId` as well as the existing `thread_id` and `pendingWorktreeId` shapes, because current Desktop app conventions and final-response directives use camelCase `threadId`.
- Capability metadata examples should be refreshed from the active tool list:
  - `create-thread`: required request fields should include `prompt` and `target`.
  - `read-thread`: required request fields should use `threadId`, not only `thread_id`.
  - `send-message`: required request fields should include `threadId` and `prompt`.
  - `fork-thread`: required request fields depend on same-directory versus worktree fork; no implicit prompt delivery should be assumed.
- Runtime compatibility docs should distinguish:
  - Desktop app tools: `create_thread`, `read_thread`, etc.
  - app-server JSON-RPC: `thread/start`, `thread/read`, `thread/fork`, `turn/start`, etc.
  - Codex SDK wrappers over app-server.
- Any future live path beyond the current single `create_thread` smoke must remain blocked until separately approved.

Does not need immediate behavioral expansion:

- Do not add a daemon, app-server client, MCP server, sidecar, private Desktop state reader, UI scraper, broad live thread adapter, or automatic thread action.
- Do not call Desktop thread tools from CLI/default paths.
- Do not treat generated app-server schema as authorization to perform state-changing Desktop actions.

## Proposed Task Slices

1. Contract evidence refresh
   - Add current Desktop tool metadata examples for `create_thread`, `read_thread`, `send_message_to_thread`, and `fork_thread`.
   - Update docs to record `codex-cli 0.139.0`, schema generation command, and `last_verified: 2026-06-12`.

2. Response-shape compatibility hardening
   - Update the V1 create-thread live smoke helper to validate `threadId`, `thread_id`, or `pendingWorktreeId`.
   - Add tests for `threadId` success and conflicting id fields.
   - Accept raw Desktop responses that omit `private_runtime_state_read` and `external_write_performed`, while still rejecting those fields when they are present and not boolean `false`.

3. Request-shape documentation refresh
   - Update `docs/runtime-compatibility.md`, `docs/runtime-adapter-v2.md`, and `docs/desktop-runtime-wrapper-v1-plan.md` to distinguish Desktop tool schema from app-server JSON-RPC schema.
   - Make the CLI fallback language clear for app-server/SDK routes.

4. Capability discovery examples
   - Update examples or tests that still imply `thread_id` is the only read-thread request field.
   - Add a fixture showing current active-tool-list metadata for Desktop tools.

5. Verification
   - Run `./scripts/validate-repo.sh`.
   - Run the focused Desktop runtime wrapper test set:
     - `python -m unittest discover -s tests -p 'test_desktop_runtime_*.py'`
   - Regenerate app-server schema to `/private/tmp` and record only command/output summary, not generated schema files.

## Definition Of Done

- Docs clearly separate Desktop app tools from app-server JSON-RPC and SDK surfaces.
- V1 wrapper tests pass with camelCase `threadId` and existing `pendingWorktreeId` response shapes.
- No Desktop private runtime state, logs, sessions, auth files, caches, SQLite databases, unpublished endpoints, UI scraping, daemon, sidecar, MCP server, or app-server client is introduced.
- No state-changing Desktop tool is called by default or in tests.
- Update evidence is reproducible from official docs, current active tool schema, and local CLI-generated schema.

## Risks And Human Gates

- Human gate: any change that actually calls `create_thread`, `fork_thread`, `send_message_to_thread`, `handoff_thread`, or any app-server thread mutation must receive exact user approval for that action.
- Human gate: any app-server adapter implementation must be a separate reviewed implementation slice because it introduces transport, initialization, auth, streaming, and experimental API handling.
- Risk: Desktop app tool schema and app-server schema are different. Treating one as the other could make the wrapper validate the wrong fields or miss a response-shape break.
- Risk: `threadId` versus `thread_id` naming drift can cause false negatives in the live smoke helper if not explicitly handled.
