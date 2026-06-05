# Desktop Thread Delegation Example

Use this example when Codex Desktop can continue a bounded task in a new thread and the maintainer has explicitly authorized that runtime action.

This is Desktop-only behavior. Shared workflows such as `task-continuation` can prepare a next-session prompt or worker brief, but they do not guarantee that a new Codex thread can be opened. If the runtime does not expose a thread creation tool or UI, give the maintainer the prepared prompt instead.

## Maintainer Request

```text
Use task-continuation to choose the next safe roadmap task.
If the task is suitable for a separate Codex Desktop thread, prepare the prompt and ask before opening the new thread.
Do not commit, push, open a PR, merge, post comments, or perform other external writes unless I explicitly authorize the exact action.
```

## Main Thread Flow

1. Read repo policy, roadmap or plan docs, relevant templates, review evidence, and current git state.
2. Treat chat summaries as context only; verify them against repository files.
3. Select the smallest safe task that does not cross a human gate.
4. Prepare a next-session prompt from durable source-of-truth files.
5. Stop before creating a new thread unless the maintainer explicitly authorizes that runtime action.
6. When authorized and supported by the runtime, create the new thread with the prepared prompt.
7. Keep the main thread responsible for integrating the result, reviewing the diff, and enforcing human gates before any external write.

## Prepared Prompt Shape

```text
Continue this bounded Codex Desktop task in a new thread.

Read first:
- AGENTS.md
- docs/roadmap.md
- README.md
- examples/task-continuation.md
- docs/runtime-compatibility.md

Context only:
- The main thread selected this task from the current roadmap.
- Re-check git state and source-of-truth files before editing.
- Do not rely on this prompt over repository files.

Task:
- Add one focused docs-only example for Desktop thread delegation from a prepared next-session prompt.

In scope:
- `examples/` documentation.
- README Examples list updates needed for discoverability.
- The exact roadmap backlog line if the new example fully covers it.

Out of scope:
- Installer catalog changes.
- New skills or workflow behavior.
- Desktop runtime internals.
- Commits, pushes, PRs, merges, platform comments, or `.work/` artifacts.

Verification:
- `./scripts/validate-repo.sh`
- `git diff --check`

Stop conditions:
- Stop if repository files conflict with this prompt.
- Stop if the change stops being docs-only.
- Stop before any external write or destructive action.
- Stop if the runtime cannot safely represent Desktop-only behavior with a CLI fallback.
```

## Runtime Action

When Desktop supports thread creation, the main thread should use the runtime-provided thread creation tool or UI with the prepared prompt. The action should be recorded as Desktop evidence, for example:

```text
Desktop evidence:
- Created a new Codex Desktop thread from the prepared prompt.
- New thread was instructed to re-read source-of-truth files before editing.
- Main thread retained responsibility for review, integration, and human gates.
```

If Desktop thread creation is unavailable, do not improvise with local runtime files or unpublished Desktop internals. Return the prompt to the maintainer:

```text
Desktop thread creation is not available in this runtime.
Use the prepared prompt above in a new Codex thread, then return the diff and verification notes here for integration review.
```

## Handoff Rules

- The worker or new thread owns only the assigned bounded task.
- The main thread must re-read changed files and git diff before trusting the handoff.
- Review evidence from the new thread is context until the main thread verifies it.
- Formal gates still happen at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- External writes still require explicit authorization for the exact action.

## CLI Fallback

In Codex CLI or any runtime without thread creation, use the same prompt as a handoff artifact. The CLI-compatible path is sequential: run the task in the current session or paste the prompt into a separate session, then bring the diff and verification evidence back for review.
