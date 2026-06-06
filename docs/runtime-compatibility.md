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

For the pre-implementation boundary of a possible Desktop thread wrapper or runtime adapter, see [Desktop Runtime Adapter V2 Boundary](runtime-adapter-v2.md).

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
| Main agent publishes, pushes, merges, deploys, or resolves platform threads. | Stop unless the user explicitly authorized the exact external write or destructive action. |

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

When evidence is incomplete, mark the claim as unverified.
