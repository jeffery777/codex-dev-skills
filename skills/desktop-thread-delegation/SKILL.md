---
name: desktop-thread-delegation
description: Codex Desktop thread delegation workflow for choosing the next safe task, continuing in the current thread when appropriate, or handing off through a new thread when authorized and supported.
---

# desktop-thread-delegation

Runtime compatibility: desktop

## Purpose

Use this skill in Codex Desktop when a larger bounded objective needs Codex to choose the next safe task, decide whether it belongs in the current thread or a new thread, and prepare a durable handoff without crossing human gates.

This first version uses runtime-provided thread tools only when they are already available. Desktop thread actions are runtime actions, not CLI guarantees. This skill is accepted public repository policy and workflow guidance only; it does not implement a runtime adapter, standalone wrapper, daemon, MCP server, app-server client, CLI `fork`, or Desktop runtime integration.

## CLI Fallback

Use `task-continuation` and `project-orchestrator` to select the next safe task and prepare a prompt, task brief, or continuation prompt. In Codex CLI, execute the task through a sequential execution path in the current session or give the prepared prompt to the maintainer for a separate session. Do not claim that CLI can open, fork, continue, or message a Codex Desktop thread unless a documented or configured thread capability is actually available.

## Workflow

1. Re-read source-of-truth files and current state:
   - repo instructions and policies;
   - roadmap, plan, task manifest, or status docs;
   - relevant templates and examples;
   - review evidence when repo policy points to it;
   - current git branch, status, upstream, and diff.
2. Classify candidate tasks as `done`, `ready`, `blocked`, `unsafe`, or `unknown`.
3. Select the smallest ready task that advances the bounded objective without scope expansion.
4. Decide the execution mode:
   - `continue-current-thread` when the task is small, state is already loaded, ownership is clear, and workflow rules or user authorization allow the current thread to do the work.
   - `new-thread-prompt` when the task is bounded but would benefit from a separate thread, fresh context, separate worktree, or independent focus.
   - `desktop-thread-create` when `new-thread-prompt` is appropriate, the Desktop runtime exposes a thread creation or fork tool, and the maintainer has explicitly authorized opening the thread.
   - `stop-for-human-gate` when the next action involves product ambiguity, scope expansion, destructive action, external write, security/privacy/data/deployment risk, or unclear source of truth.
5. If `continue-current-thread` is selected, do the task only within the permissions already granted by repo policy and the user. Stop before commit, push, PR creation, merge, deploy, platform comments, review submissions, destructive actions, or other external writes unless explicitly authorized.
6. If a new thread is appropriate, prepare a prompt before creating anything. The prompt must require the new thread to re-read source-of-truth files before editing.
7. Before preparing to call a Desktop thread tool, record the contract/version tracking evidence required by [Desktop Runtime Adapter V2 Boundary](../../docs/runtime-adapter-v2.md):
   - runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, or the documented equivalent;
   - underlying API or tool contract version when the runtime exposes one;
   - `version unavailable` when no version is exposed, plus a verifiable capability source such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
   - minimal request and response shape compatibility summary;
   - `last_verified`;
   - wrapper or adapter version to underlying contract mapping.
8. When the runtime, connector, schema, or documentation changes, re-compare the old and new contract before calling the tool. Stop if required parameters, response shape, error shape, permissions, authentication, or state-changing behavior are unclear.
9. Before calling a Desktop thread tool, restate the target repo, execution mode, prepared prompt summary, expected branch or worktree behavior, contract/version evidence, and human gates. Ask for or confirm explicit authorization.
10. If the runtime provides a supported thread creation or fork tool, call it with the prepared prompt after authorization.
11. If the tool is unavailable or fails for capability reasons, return the prepared prompt to the maintainer as a paste-ready handoff.
12. Keep the main thread responsible for integration, verification, review evidence, commit readiness, PR readiness, and merge gates.

## Thread Tool Policy

Allowed first-version tool use:

- runtime-provided thread tools such as `create_thread`, `fork_thread`, or equivalent Desktop actions when they are exposed in the active tool list;
- read-only inspection of thread metadata through runtime-provided tools when needed to verify handoff state.

Before any allowed tool use, record the runtime API/tool contract evidence listed in the workflow above. The record is compatibility evidence only; it does not authorize a wrapper, daemon, MCP server, app-server client, Desktop runtime integration, or direct use of experimental endpoints.

Disallowed first-version tool use:

- editing Codex Desktop local databases, logs, sessions, auth files, caches, app state, or other private runtime state;
- using unpublished endpoints, scraping unpublished Desktop UI state, or reverse-engineered Desktop internals as a substitute for a thread tool;
- starting app-server daemons, remote-control daemons, wrapper daemons, sidecars, or background services;
- using experimental app-server thread endpoints directly.

Those disallowed paths are outside the accepted public repository policy, runtime compatibility guidance, and maintained examples. They must not be treated as a roadmap item, accepted implementation, or fallback path for this skill.

## Prompt Requirements

A new-thread prompt should include:

- required source-of-truth files to read first;
- context-only summary from the main thread;
- exact task scope;
- in-scope and out-of-scope files or categories;
- expected branch or worktree behavior;
- runtime thread tool or API contract evidence to record before any thread action, including contract name, exposed version or `version unavailable` plus capability source, minimal request/response compatibility summary, `last_verified`, and workflow, wrapper, or adapter mapping to the underlying contract;
- verification commands;
- review primitive or formal gate expectations;
- stop conditions;
- instruction to return changed files, verification evidence, open questions, and residual risk to the main thread.

## Output

- Current state facts
- Inferences and uncertainty
- Candidate tasks and statuses
- Selected next safe task
- Execution mode
- Whether current-thread execution is allowed
- Prepared prompt, when a new thread or handoff is appropriate
- Thread tool capability, contract/version tracking evidence, and action taken, if any
- CLI fallback, if no thread tool is available
- Integration and review responsibilities retained by the main thread
- Human gate

## Stop Conditions

Stop instead of executing or delegating when source-of-truth files conflict, the target task is ambiguous, the work expands scope, ownership overlaps, verification would be insufficient for the risk, the next step requires external writes, the runtime contract name or minimal request/response shape is unclear, the underlying contract version is unavailable without a verifiable capability source, runtime or connector changes have not been compared against the recorded contract, or the only available path depends on unpublished Desktop internals.
