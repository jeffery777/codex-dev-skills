# Milestone Continuation Example

Use `milestone-continuation` when a bounded milestone should keep moving across repeated Codex invocations until the milestone is complete or the next human gate is reached.

This is a shared workflow. It can be used manually in Codex CLI or Codex Desktop. Runtime scheduling, such as a Codex Desktop heartbeat or automation, is separate from the skill itself.

## Manual Invocation

```text
Use milestone-continuation for MVP1.

Read first:
- AGENTS.md
- docs/milestones/MVP1.md
- docs/tasks/MVP1.yaml
- docs/status.md
- docs/milestone-continuation-requirements.md
- skills/milestone-continuation/SKILL.md
- skills/project-delivery/SKILL.md
- skills/task-continuation/SKILL.md

Check whether the current task is complete using its DoD, verification commands,
scope, docs sync needs, and review evidence.

If the current task is incomplete, continue it with the smallest safe action.
If the current task is complete, update or prepare the task-state update and choose
the next smallest ready task that advances MVP1.

Route implementation, docs sync, review, or handoff through the existing smallest
workflow that fits the current state.

Stop for product ambiguity, source-of-truth conflict, scope expansion, destructive
action, external write, commit/push/PR/merge/deploy/release approval, platform-side
mutation, material security/privacy/data/migration/payment/permission risk, or
insufficient verification for a high-risk change.

At the end, report milestone status, current task status, selected next task,
files changed, verification run, remaining risk, and the next human gate.
```

## Scheduled Desktop Wording

When Codex Desktop heartbeat or automation is available, the schedule belongs to the runtime instruction:

```text
Wake this thread every 5 minutes and run the MVP1 milestone-continuation loop.
```

The skill still controls only what happens after the thread wakes up. It does not implement a scheduler, daemon, background service, runtime adapter, app-server client, or Desktop thread-tool wrapper.

## Expected Flow

1. Re-read durable source-of-truth files and current git state.
2. Treat chat and handoff summaries as context only.
3. Classify tasks with canonical lifecycle states. Record safety concerns as
   blocked with blocker kind `safety`; use unknown only as an inspection result.
4. Check the current task against DoD and verification commands.
5. Continue the current task, select the next ready task, or stop at a human gate.
6. Route work through `project-delivery`, `project-orchestrator`, `task-continuation`, `implementation-slice`, `docs-update`, or `desktop-thread-delegation` as appropriate.
7. Run relevant verification, inspect the diff, and report residual risk.

## Desktop Handoff

Use `desktop-thread-delegation` only when a selected task should move to a new Codex Desktop thread and the runtime exposes a supported thread tool.

Before opening, forking, or messaging a Desktop thread, the main thread must prepare the prompt, record contract/version evidence, restate the target repo and branch/worktree expectation, and obtain explicit authorization for the exact runtime action.

If thread creation is unavailable, return a paste-ready prompt instead:

```text
Continue this bounded milestone-continuation task in a new Codex session.

Read first:
- AGENTS.md
- docs/milestones/MVP1.md
- docs/tasks/MVP1.yaml
- docs/status.md
- skills/milestone-continuation/SKILL.md
- skills/task-continuation/SKILL.md
- skills/project-delivery/SKILL.md

Context only:
- The main thread selected this task from the MVP1 milestone state.
- Re-check repository files and git state before editing.
- Do not rely on this prompt over repository files.

Task:
- Continue the selected MVP1 task using the smallest safe action.

Rules:
- Keep changes scoped to the selected task.
- Do not commit, push, create PRs, merge, deploy, post platform comments,
  submit reviews, perform destructive actions, or edit unrelated files.
- Stop if source-of-truth files conflict, scope expands, verification is
  insufficient for the risk, or a human decision is needed.

Expected return:
- Changed files.
- Verification evidence.
- Current task status.
- Remaining risk.
- Open questions or human gate.
```

## CLI Fallback

In Codex CLI or any runtime without scheduling or thread creation, invoke the skill manually, prepare a continuation prompt, or execute the next safe task sequentially in the current session. Do not claim that CLI can open or manage Codex Desktop threads unless a documented thread capability is actually available.
