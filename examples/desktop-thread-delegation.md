# Desktop Thread Delegation Example

Use `desktop-thread-delegation` when Codex Desktop should choose the next safe task, decide whether it belongs in the current thread or a new thread, and preserve main-thread review responsibility.

This is Desktop-only behavior. Desktop thread actions are runtime actions, not CLI guarantees. Shared workflows such as `task-continuation` can prepare a prompt, task brief, or continuation prompt, but they do not guarantee that a new Codex Desktop thread can be opened. If the runtime does not expose a documented thread creation capability, use the CLI-compatible prompt, task brief, continuation prompt, or sequential execution path instead.

## Maintainer Request

```text
Use desktop-thread-delegation to choose the next safe roadmap task.
Decide whether the task should continue in this thread or move to a separate Codex Desktop thread.
If the current thread is suitable and repo policy or my authorization allows it, continue here.
If a separate thread is better, prepare the prompt and ask before opening the new thread.
Before any Desktop thread tool call, record the runtime tool/API contract name, exposed version or `version unavailable` plus capability source, minimal request/response compatibility summary, `last_verified`, and workflow, wrapper, or adapter mapping to the underlying contract.
Do not commit, push, create PRs, merge, deploy, post platform comments, submit reviews, or perform other external writes unless I explicitly authorize the exact action.
```

## Main Thread Flow

1. Read repo policy, roadmap or plan docs, relevant templates, review evidence, and current git state.
2. Treat chat summaries as context only; verify them against repository files.
3. Select the smallest safe task that does not cross a human gate.
4. Decide whether the task should run in the current thread, move to a new thread, or stop for a human gate.
5. If the current thread is suitable, continue only when workflow rules allow it or the maintainer has authorized it.
6. If a new thread is suitable, prepare a prompt, task brief, or continuation prompt from durable source-of-truth files.
7. Stop before creating a new thread unless the maintainer explicitly authorizes that runtime action.
8. Before any supported Desktop thread tool call, record the contract/version tracking fields from [docs/runtime-adapter-v2.md](../docs/runtime-adapter-v2.md).
9. When authorized and supported by the runtime, create the new thread with the prepared prompt.
10. Keep the main thread responsible for integrating the result, reviewing the diff, and enforcing human gates before any external write.

## Prepared Prompt Shape

```text
Continue this bounded Codex Desktop task in a new thread.

Read first:
- AGENTS.md
- docs/roadmap.md
- README.md
- docs/runtime-adapter-v2.md
- examples/task-continuation.md
- docs/runtime-compatibility.md

Context only:
- The main thread selected this task from the current roadmap.
- The main thread decided this task is better suited to a separate thread than the current thread.
- Re-check git state and source-of-truth files before editing.
- Do not rely on this prompt over repository files.

Task:
- Add one focused docs-only example for Desktop thread delegation from a prepared continuation prompt.

In scope:
- `examples/` documentation.
- README Examples list updates needed for discoverability.
- The exact roadmap backlog line if the new example fully covers it.

Out of scope:
- Installer catalog changes.
- New skills or workflow behavior.
- Desktop runtime internals, local databases, logs, sessions, auth files, caches, app state, unpublished endpoints, UI scraping, daemons, background services, or private runtime state.
- Commits, pushes, PRs, merges, deploys, platform comments, review submissions, or `.work/` artifacts.

Verification:
- `./scripts/validate-repo.sh`
- `git diff --check`

Contract evidence to record before any Desktop thread tool call:
- Runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, or the documented equivalent.
- Underlying API or tool contract version when exposed.
- If no version is exposed, `version unavailable` plus a verifiable capability source such as active tool list, connector metadata, official documentation version, or runtime-reported schema.
- Minimal request and response shape compatibility summary.
- `last_verified`.
- Workflow, wrapper, or adapter mapping to the underlying contract.
- Re-compare old and new contracts after runtime, connector, schema, or documentation changes.

Stop conditions:
- Stop if repository files conflict with this prompt.
- Stop if the change stops being docs-only.
- Stop before any external write or destructive action.
- Stop if the runtime cannot safely represent Desktop-only behavior with a CLI fallback.
- Stop if the runtime contract, exposed version or capability source, request shape, response shape, permissions, authentication, or wrapper mapping is unclear.
```

## Runtime Action

When Desktop supports thread creation, the main thread should use the runtime-provided thread creation tool or UI with the prepared prompt. The action should be recorded as Desktop evidence, for example:

```text
Desktop evidence:
- Created a new Codex Desktop thread from the prepared prompt.
- New thread was instructed to re-read source-of-truth files before editing.
- Runtime contract: create_thread.
- Underlying contract version: version unavailable.
- Capability source: active tool list in the current runtime.
- Request/response compatibility: prompt is required; title, repository, and branch are used when exposed; response must expose a created thread identifier or pending worktree identifier, action status, and error message shape.
- Wrapper/API mapping: no wrapper or adapter implementation; desktop-thread-delegation workflow at current repo revision -> create_thread version unavailable.
- Last verified: YYYY-MM-DD.
- Main thread retained responsibility for review, integration, and human gates.
```

If Desktop thread creation is unavailable, do not improvise with private Desktop runtime state, local runtime files, unpublished endpoints, UI scraping, daemons, background services, or unpublished Desktop internals. Return the prompt to the maintainer:

```text
Desktop thread creation is not available in this runtime.
Use the prepared prompt above in a separate Codex session or in a Codex Desktop thread when Desktop is intentionally selected, then return the diff and verification notes here for integration review.
```

## Handoff Rules

- The worker or new thread owns only the assigned bounded task.
- The main thread must re-read changed files and git diff before trusting the handoff.
- Review evidence from the new thread is context until the main thread verifies it.
- Formal gates still happen at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- External writes still require explicit authorization for the exact action.

## CLI Fallback

In Codex CLI or any runtime without thread creation, use the same prompt as a handoff artifact, prepare a task brief or continuation prompt, or run through a sequential execution path in the current session. Bring the diff and verification evidence back for review before trusting the handoff.
