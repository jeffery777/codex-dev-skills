# Task Continuation Example

Use `task-continuation` when a bounded project needs Codex to choose the next safe task from durable repository context and prepare a continuation prompt or task brief:

```text
Use task-continuation to continue this bounded docs milestone.
Read repo policy, the current roadmap, task manifest or plan, review evidence, and git state first.
Choose the smallest safe next task, recommend an execution mode, and prepare a prompt, task brief, continuation prompt, or sequential execution path if continuation is safe.
Stop instead of preparing executable continuation if the next step would require scope expansion, external writes, destructive actions, product decisions, or unclear source of truth.
```

Expected triage flow:

1. Re-read source-of-truth files such as `AGENTS.md`, roadmap or plan docs, task manifests, relevant templates, review evidence, and current git state.
2. Classify candidate tasks with canonical states; record safety concerns as
   `blocked` with blocker kind `safety`, and use `unknown` only until inspection
   establishes a persisted state.
3. Treat chat summaries and handoff notes as context only, then verify them against repository files.
4. Select the smallest ready task that advances the bounded objective without crossing a human gate.
5. Choose one execution mode:
   - `continue-current-session` when the current session can safely finish the next task.
   - `shared-subagent` when an independent bounded packet has disjoint ownership
     and the current Codex surface supports subagents.
   - `new-session-prompt` when the work should move to another CLI or generic Codex session.
   - `desktop-task-handoff` only when the user requests a separate user-owned
     Desktop task/thread and the runtime exposes that control plane.
   - `stop-for-human-gate` when the next step needs a maintainer decision.
6. Include required source-of-truth files, in-scope and out-of-scope work, expected files, DoD, verification, review primitive, formal gate trigger, and stop conditions.

CLI continuation prompt example using `new-session-prompt` mode:

```text
Use task-continuation for this bounded continuation task.

Read first:
- AGENTS.md
- docs/roadmap.md
- templates/orchestration/task-continuation-report.template.md
- templates/orchestration/next-session-prompt.template.md

Context only:
- Previous session selected the next docs-only task from the roadmap.
- Verification in the previous session passed, but you must re-run relevant checks after editing.

Task:
- Add one focused task-continuation example that shows next safe task selection and handoff prompts.

In scope:
- `examples/` documentation and README discovery updates needed to make the example findable.

Out of scope:
- Installer catalog changes, new skills, workflow behavior changes, commits, pushes, PRs, merges, or `.work/` artifacts.

Verification:
- ./scripts/validate-repo.sh
- git diff --check

Stop conditions:
- Stop if repo files conflict with this prompt, if the diff stops being docs-only, or before any external write.
```

Desktop task brief example using `desktop-task-handoff` mode:

```text
Worker task: draft the task-continuation example only.

Read first:
- AGENTS.md
- skills/task-continuation/SKILL.md
- templates/orchestration/next-session-prompt.template.md
- templates/orchestration/task-continuation-report.template.md

Expected output:
- A proposed `examples/task-continuation.md` diff.
- A short verification note.
- Open questions or stop conditions encountered.

Rules:
- Do not commit, push, create PRs, merge, post platform comments, submit reviews, or edit files outside the assigned docs example.
- Treat this brief as context only; repository files are the source of truth.
```

Use the templates under `templates/orchestration/` when a target repository needs durable artifacts. Do not create those artifacts by default for every continuation task; prepare prompts, task briefs, or continuation prompts only when they help another session, worker, or sequential execution path continue safely.
