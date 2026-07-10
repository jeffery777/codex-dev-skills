---
name: desktop-thread-delegation
description: Thin Codex Desktop task and thread control adapter for a handoff already selected by the shared orchestration workflow.
---

# desktop-thread-delegation

Runtime compatibility: desktop

## Purpose

Use this skill only after `loop-engineering`, `project-orchestrator`,
`project-delivery`, or `task-continuation` has selected a bounded handoff and
the user wants Codex Desktop to continue it in a user-owned task, thread, or
worktree.

This is a thin Desktop UX adapter over the shared workflow contract. It does
not perform ordinary task selection, redefine completion, or own shared
subagent delegation. Subagents remain available through the shared delegation
policy in current Desktop, CLI, and IDE runtimes.

## CLI Fallback

Use the already selected task brief in the current CLI session, delegate
bounded packets through shared subagents when supported, or return a durable
continuation prompt. Do not claim that CLI holds Desktop app task/thread tools.

## Workflow

1. Re-read the selected task brief, source-of-truth files, ownership, review
   evidence, and current git state. Return to shared orchestration if the
   selected task is no longer ready.
2. Decide the Desktop execution mode:
   - `continue-current-thread` when the task is small, state is already loaded, ownership is clear, and workflow rules or user authorization allow the current thread to do the work.
   - `new-thread-prompt` when the task is bounded but would benefit from a separate thread, fresh context, separate worktree, or independent focus.
   - `desktop-thread-create` when `new-thread-prompt` is appropriate, the Desktop runtime exposes a thread creation or fork tool, and the maintainer has explicitly authorized opening the thread.
   - `stop-for-human-gate` when the next action involves product ambiguity, scope expansion, destructive action, external write, security/privacy/data/deployment risk, or unclear source of truth.
3. If a new task is appropriate, prepare the prompt before creating anything.
   Creating a new or background Desktop task requires an explicit user request.
4. Inspect the active callable schema. For project-scoped creation, call the
   documented project-list operation first and pass its `projectId`; do not
   infer project identity from private runtime state. Omit model and reasoning
   overrides unless the user explicitly requests supported values.
5. Recheck the target, prompt, local or worktree behavior, and authorization at
   the actual call site. Treat `threadId` as created-task dispatch evidence and
   `clientThreadId` as queued worktree dispatch evidence; neither proves task
   completion.
6. If the runtime provides a supported create or fork operation, call it only
   after the exact task action is authorized. A fork copies completed history;
   send a follow-up only when the child must continue working.
7. Use list/read operations for observation. Treat create, fork, send, handoff,
   archive, pin, and rename as runtime-state mutations requiring authority for
   the exact action.
8. If the capability is unavailable or fails, return the prepared prompt as a
   paste-ready handoff or continue through the shared sequential fallback.
9. Keep the originating task responsible for integration, verification, review
   evidence, commit readiness, PR readiness, and merge gates.

## Thread Tool Policy

Allowed tool use:

- runtime-provided project and task/thread tools when they are exposed in the active tool list;
- read-only inspection of thread metadata through runtime-provided tools when needed to verify handoff state.

The repository's `docs/native-runtime-capabilities.md` is canonical; filesystem
installation also places it at
`~/.codex/templates/docs/native-runtime-capabilities.md`. Active callable schema
plus call-site validation governs native operations.

Disallowed tool use:

- editing Codex Desktop local databases, logs, sessions, auth files, caches, app state, or other private runtime state;
- using unpublished endpoints, scraping unpublished Desktop UI state, or reverse-engineered Desktop internals as a substitute for a thread tool;
- starting app-server daemons, remote-control daemons, wrapper daemons, sidecars, or background services;
- using experimental app-server thread endpoints directly.

Legacy `desktop_runtime_*` preflight, handshake, cache, injected-callable, and
smoke helpers are compatibility evidence only, not this adapter's active
runtime path. This skill must not import or execute them.

## Prompt Requirements

A new-thread prompt should include:

- required source-of-truth files to read first;
- context-only summary from the main thread;
- exact task scope;
- in-scope and out-of-scope files or categories;
- expected branch or worktree behavior;
- target project and local or worktree execution behavior;
- verification commands;
- review primitive or formal gate expectations;
- stop conditions;
- instruction to return changed files, verification evidence, open questions, and residual risk to the main thread.

## Output

- Current state facts
- Inferences and uncertainty
- Selected task readiness re-check
- Already selected task identifier and brief
- Execution mode
- Whether current-thread execution is allowed
- Prepared prompt, when a new thread or handoff is appropriate
- Native task/thread capability and action taken, if any
- CLI fallback, if no thread tool is available
- Integration and review responsibilities retained by the main thread
- Human gate

## Stop Conditions

Stop instead of executing or delegating when source-of-truth files conflict,
the selected task is ambiguous or no longer ready, the work expands scope,
ownership overlaps, verification would be insufficient for the risk, the next
step lacks required authority, current callable request or response semantics
are unclear, or the only available path depends on unpublished Desktop
internals or legacy wrapper execution.
