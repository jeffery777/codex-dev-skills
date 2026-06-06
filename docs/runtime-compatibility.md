# Runtime Compatibility

This repository uses four compatibility labels.

## `shared`

Works in Codex CLI and Codex Desktop using repository files, ordinary shell commands, git inspection, and durable artifacts. Shared workflows must not require Desktop-only orchestration.

## `cli`

Designed primarily for Codex CLI. A Desktop user may still follow the workflow manually, but the skill should document the fallback.

## `desktop`

Requires Codex Desktop behavior such as main-agent orchestration, worker delegation, or Desktop-specific handoff. Desktop workflows must not be presented as guaranteed CLI workflows.

## `plugin-dependent`

Requires an installed plugin, connector, or platform-specific tool. The dependency must be named, and the workflow must define what happens when the dependency is unavailable.

## Metadata

Every skill should include a runtime line near the top:

```markdown
Runtime compatibility: shared
```

The README skill table must include the same value.

## Fallbacks

Desktop-only workflows should provide a CLI fallback such as a prompt, task brief, continuation prompt, or sequential execution path. Review steps such as `code-review`, `docs-review`, or high-risk `code-review-deep` may still be used after the fallback produces changed files or evidence. Use formal `code-review-gate` or `docs-review-gate` only for commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision.

CLI-only workflows should provide a Desktop fallback such as running the same read-plan-implement-verify sequence in a Desktop thread, with Desktop-only actions clearly omitted.

For the policy boundary of a possible future Desktop runtime-call adapter, see [Desktop Runtime Adapter V2 Boundary](runtime-adapter-v2.md).
For the completed non-state-changing Desktop runtime wrapper V1 planner, capability metadata normalization, contract comparison, create-thread preflight, read-thread preflight, evidence pipeline, session compatibility status validation, first-use handshake, session-scoped compatibility cache, and create-thread authorization/evidence gate helpers, see [Desktop Runtime Wrapper V1 Feasibility And Implementation Plan](desktop-runtime-wrapper-v1-plan.md).

## Desktop To CLI Fallback Mapping

Desktop orchestration can coordinate multiple workers, but the reusable workflow contract should still describe what a CLI-compatible fallback can do with ordinary repository files and commands.

Desktop thread actions are runtime actions, not CLI guarantees. When a Desktop workflow creates, forks, continues, or messages a thread through a runtime-provided tool or documented API, the CLI-compatible fallback is still a prompt, task brief, continuation prompt, or sequential execution path. The fallback must not claim that Codex CLI can open, fork, continue, message, or control Desktop threads unless a documented or configured thread capability is actually available.

| Desktop orchestration step | CLI-compatible fallback |
| --- | --- |
| Main agent defines scope, source of truth, ownership, verification, and human gates. | Use `project-delivery` or `project-orchestrator` in the current session to read repo policy, inspect git state, and write a bounded plan or task brief. |
| Main agent delegates bounded work to Desktop workers. | Execute the packets sequentially in the current CLI session, or prepare durable prompts, task briefs, or continuation prompts for separate CLI sessions. |
| Workers return changes or evidence to the main agent. | Re-read the changed files, task brief, verification output, and git diff before trusting the handoff. Treat chat summaries as context, not source of truth. |
| Main agent integrates worker output. | Apply or keep only scoped file changes, inspect ownership boundaries, and reject unrelated edits before validation. |
| Main agent reviews integrated output. | Run `code-review`, `code-review-deep`, or `docs-review` as the ordinary review primitive for the changed surface. |
| Main agent runs a formal Desktop integration gate. | Use `code-review-gate` or `docs-review-gate` only when the stage is commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision. |
| Main agent prepares PR or merge readiness. | Run `merge-review` or `merge-review-deep` for base-to-head evidence, then use `merge-readiness-gate` only when a formal readiness decision is needed. |
| Main agent commits, pushes, creates PRs, publishes, merges, deploys, posts platform comments, submits reviews, or resolves platform threads. | Stop unless the user explicitly authorized the exact external write or destructive action. |

The fallback does not claim that Codex CLI can spawn Desktop workers. It preserves the same safety model by replacing parallel worker delegation with durable prompts, task briefs, continuation prompts, sequential execution, explicit review evidence, and the same human gates.

## Evidence

Evidence should state where it came from:

- CLI evidence: command, working directory, exit status, and relevant output summary.
- Desktop evidence: thread action, worker output, artifact path, screenshot path, or manually verified UI state.

When Desktop evidence comes from a runtime thread tool or documented API, include contract compatibility evidence before relying on the action result:

- runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or the documented equivalent;
- underlying API or tool contract version when the runtime exposes one;
- `version unavailable` when no version is exposed, plus a verifiable capability source such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
- minimal request shape the workflow used, including required parameters, optional parameters used, and target identity fields;
- minimal response shape the workflow relies on, such as created thread identifier, target thread identifier, action status, error shape, lifecycle state, or fallback signal;
- `last_verified` date for the contract evidence;
- workflow, wrapper, or adapter mapping to the underlying contract, including mappings where the underlying version is unavailable.

The compatibility record should make clear which workflow, wrapper, or adapter version was checked against which underlying tool or API contract. After a runtime, connector, schema, or documentation change, re-compare the old and new contract before use, with particular attention to required parameters, response shape, error shape, permission or authentication changes, and renamed, removed, or newly state-changing operations.

When evidence comes from caller-supplied documented capability metadata instead of a runtime call, label it as normalized metadata only. It can record action name, read-only or state-changing classification, required request fields, minimum response fields, capability source, contract version or `version unavailable`, `last_verified`, and helper version. The Desktop runtime wrapper V1 planner may accept that normalized evidence as `capability_evidence` and use it only to decide dry-run, fallback, or stopped output. It must not imply that a Desktop thread tool was called or that Codex CLI can operate Desktop threads.

Before relying on a runtime, connector, schema, or documentation change, compare the old wrapper contract evidence with the newer normalized capability evidence. The Desktop runtime wrapper V1 contract comparison helper can perform that re-check from caller-supplied evidence only: unchanged tool/API name, classification, required request fields, and minimum response fields return `compatible`; missing or unavailable capability returns `fallback`; changed contract fields, unclear evidence, or forbidden private runtime hints return `stopped`. This comparison is evidence only and does not authorize or call state-changing tools such as `create_thread`, `fork_thread`, or `send_message_to_thread`.

For future runtime-call paths, Desktop runtime wrapper V1 should use a session capability handshake and compatibility cache instead of re-checking runtime schema before every call. The first wrapper use in each Codex CLI/Desktop process/session may compare caller-supplied documented capability metadata with the wrapper's recorded contract and construct a session-scoped compatibility status. The V1 session-scoped compatibility cache helper may read or write a caller-explicit cache envelope for same-session contract compatibility evidence only. Restarting Codex CLI/Desktop invalidates the status and requires another handshake.

Compatibility status or cache evidence should include the wrapper or skill package version, helper version, status helper version when applicable, target action, tool/API name, runtime-reported version or `version unavailable`, capability source, schema/contract hash or equivalent normalized contract evidence, comparison result, `last_verified`, session identity or an explicit current-process/current-session scoped marker, cache scope, lifecycle marker, and `created_at` plus `expires_at` or an explicit same-session-only marker. It must not cache or replace exact runtime action authorization, external-write authorization, destructive-action approval, target repo/branch/thread-id/expected-head validation, auth or permission failure results, or actual runtime response validation.

When evidence comes from an explicit caller-supplied session compatibility status, validate that status before any later preflight references it. The V1 session compatibility status validator checks the wrapper/package/repo identity, helper version, target action, tool/API name, runtime-reported version or `version unavailable`, capability source, schema hash or normalized contract evidence, comparison result, `last_verified`, and session identity or explicit current-process/current-session marker. Its `ready` status means only that the status can be referenced by a later preflight for contract compatibility evidence. `fallback` or `stopped` must block later runtime-call paths.

Session compatibility status validation is not a first-use handshake, not a compatibility cache write path, not a compatibility cache read path, and not a runtime-call path. It does not authorize runtime actions or external writes, validate targets or permissions, validate runtime responses, read Desktop private runtime state, or call Desktop thread tools.

When evidence comes from the first-use session compatibility handshake helper, treat it as status construction and validation evidence only. The helper may normalize caller-supplied documented metadata, compare it with old wrapper contract evidence, construct a session compatibility status, and validate that status with the status validator. Its `ready` status means only that the constructed session status can be referenced by later preflight. It is not a compatibility cache read path, not a compatibility cache write path, not a runtime-call path, and not authorization for runtime actions or external writes.

When evidence comes from the session-scoped compatibility cache helper, treat it as same-session contract compatibility evidence only. The helper reads or writes only an explicit caller-supplied cache file path and rejects Desktop private runtime-looking paths or source hints. Its `ready` status means only that same-session cache evidence may be referenced by later preflight; it does not authorize a runtime call, external write, target validation, permission handling, or runtime response validation. `fallback`, `stopped`, session marker mismatch, stale or expired cache, wrapper/helper/status helper version mismatch, and schema hash or normalized contract evidence mismatch must block later runtime-call paths.

Before a future `create_thread` runtime call, the V1 create-thread preflight helper can check readiness evidence from caller-supplied fields only. It requires repo, remote, branch, expected head, prepared prompt summary/body, normalized `create-thread` capability evidence classified as `state-changing`, compatible contract comparison output, exact `create-thread` authorization, `external_write_authorized: false`, and `external_writes_blocked: true`. Its `ready` status means evidence is ready for a future separately approved runtime call only; the helper does not call `create_thread`, does not read Desktop private runtime state, and does not authorize commit, push, PR creation, merge, or other external writes.

Before a future `create_thread` runtime-call implementation is added or used, the V1 create-thread authorization/evidence gate can check the final caller-supplied envelope. It requires exact `target_action: "create-thread"` and `tool_or_api: "create_thread"`, repo, remote, branch, expected head, prepared prompt summary/body, ready create-thread preflight evidence, ready same-session compatibility status evidence, ready same-session cache evidence, `authorized_runtime_action: "create-thread"`, a human approval marker scoped to next-step implementation only, explicit target validation, declared permission/auth failure handling requirements, declared runtime response validation requirements, `external_write_authorized: false`, absent or false destructive-action approval, `runtime_call_performed: false`, and `desktop_private_runtime_state_read: false`. Its `ready` status means only that a human can consider separately approving one future implementation slice. It does not authorize or perform the runtime call. Cache, status, and preflight evidence cannot replace action authorization, target validation, permission/auth failure handling, or response validation. `fallback` or `stopped` must block the later runtime path.

Before a future read-only `read_thread` runtime call, the V1 read-thread preflight helper can check readiness evidence from caller-supplied fields only. It requires repo, remote, branch, thread id, read-request summary and expected fields, normalized `read-thread` capability evidence classified as `read-only`, compatible contract comparison output, `external_write_authorized: false`, and `external_writes_blocked: true`. Its `ready` status means evidence is ready for a future separately approved read-only runtime call only; the helper does not call `read_thread`, does not read Desktop private runtime state, does not treat preflight as runtime-call authorization, and does not authorize commit, push, PR creation, merge, or other external writes.

When maintainers want to inspect the full V1 evidence order, the evidence pipeline helper can chain caller-supplied metadata through discovery, contract comparison, and create/read preflight in one CLI output. Its aggregate `ready`, `fallback`, or `stopped` status is evidence only. It does not collect metadata, call `create_thread` or `read_thread`, read Desktop private runtime state, treat preflight as runtime-call authorization, or authorize commit, push, PR creation, merge, or other external writes.

When evidence is incomplete, mark the claim as unverified.
