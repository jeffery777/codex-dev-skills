---
description: Codex Desktop thread delegation workflow for choosing the next safe task, continuing in the current thread when appropriate, or handing off through a new thread when authorized and supported.
---

# desktop-thread-delegation

Runtime compatibility: desktop

## Purpose

Use this skill in Codex Desktop when a larger bounded objective needs Codex to choose the next safe task, decide whether it belongs in the current thread or a new thread, and prepare a durable handoff without crossing human gates.

This first version uses runtime-provided thread tools only when they are already available. It does not implement a standalone wrapper around the Codex app server, CLI `fork`, local runtime databases, or unpublished Desktop internals.

## CLI Fallback

Use `task-continuation` and `project-orchestrator` to select the next safe task and prepare a next-session prompt. In Codex CLI, execute the task sequentially in the current session or give the prepared prompt to the maintainer for a separate session. Do not claim that CLI can open a Codex Desktop thread unless a documented or configured thread tool is actually available.

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
5. If `continue-current-thread` is selected, do the task only within the permissions already granted by repo policy and the user. Stop before commit, push, PR, merge, platform comments, destructive actions, or other external writes unless explicitly authorized.
6. If a new thread is appropriate, prepare a prompt before creating anything. The prompt must require the new thread to re-read source-of-truth files before editing.
7. Before calling a Desktop thread tool, restate the target repo, execution mode, prepared prompt summary, expected branch or worktree behavior, and human gates. Ask for or confirm explicit authorization.
8. If the runtime provides a supported thread creation or fork tool, call it with the prepared prompt after authorization.
9. If the tool is unavailable or fails for capability reasons, return the prepared prompt to the maintainer as a paste-ready handoff.
10. Keep the main thread responsible for integration, verification, review evidence, commit readiness, PR readiness, and merge gates.

## Thread Tool Policy

Allowed first-version tool use:

- runtime-provided thread tools such as `create_thread`, `fork_thread`, or equivalent Desktop actions when they are exposed in the active tool list;
- read-only inspection of thread metadata through runtime-provided tools when needed to verify handoff state.

Disallowed first-version tool use:

- editing Codex Desktop local databases, runtime state, logs, caches, sessions, or auth files;
- scraping unpublished Desktop UI state as a substitute for a thread tool;
- starting app-server daemons, remote-control daemons, or wrapper services;
- using experimental app-server thread endpoints directly.

Those disallowed paths belong to a separate runtime-adapter implementation and must be labeled experimental.

## Prompt Requirements

A new-thread prompt should include:

- required source-of-truth files to read first;
- context-only summary from the main thread;
- exact task scope;
- in-scope and out-of-scope files or categories;
- expected branch or worktree behavior;
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
- Thread tool capability and action taken, if any
- CLI fallback, if no thread tool is available
- Integration and review responsibilities retained by the main thread
- Human gate

## Stop Conditions

Stop instead of executing or delegating when source-of-truth files conflict, the target task is ambiguous, the work expands scope, ownership overlaps, verification would be insufficient for the risk, the next step requires external writes, or the only available path depends on unpublished Desktop internals.
