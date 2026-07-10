---
name: milestone-continuation
description: Continue a bounded milestone across repeated invocations by checking task completion, selecting the next ready task, routing through existing workflows, and stopping at human gates.
---

# milestone-continuation

Runtime compatibility: shared

## Purpose

Use this skill when a bounded milestone, such as `MVP1`, should keep advancing across repeated Codex invocations until the milestone is complete or the next human gate is reached.

This skill is an upper-layer continuation loop. It does not replace `project-delivery`, `project-orchestrator`, `task-continuation`, or `desktop-thread-delegation`. It decides what should happen each time Codex is invoked, then routes the work through the smallest existing workflow that fits the current state.

Scheduling is outside this skill. A prompt may request a cadence such as every 5 minutes or every 10 minutes, but the actual wakeup must come from the active runtime, such as Codex Desktop heartbeat or automation. In runtimes without scheduling, use manual invocation, a paste-ready continuation prompt, task brief, or sequential execution path.

## CLI Fallback

Codex CLI does not provide the Scheduled management interface. Run the
milestone loop in the current session, use shared subagents for independent
bounded packets when supported, or prepare a paste-ready prompt, task brief,
continuation prompt, or sequential execution path. Do not claim that CLI holds
Desktop app task/thread tools.

## Workflow

1. Re-bootstrap from durable repository files:
   - repo instructions and policies;
   - milestone spec;
   - task manifest;
   - status docs or continuation reports;
   - implementation plans, review evidence, relevant templates, and current git state.
2. Treat chat summaries, prior handoffs, and wakeup prompts as context only. Repository files remain the source of truth.
3. Confirm the target milestone is still valid and not blocked by source-of-truth conflict.
4. Classify loop lifecycle separately from canonical task lifecycle. Loop
   lifecycle may be `active`, `blocked`, `complete`, or `cancelled`. Task state:
   - `planned`
   - `in_progress`
   - `ready`
   - `blocked`
   - `reviewing`
   - `done`
   - `accepted`
   - `cancelled`
   - `unknown`
   Safety concerns are `blocked` with blocker kind `safety`; `unknown` is an
   inspection classification rather than a persisted task status.
5. Check the current task against its DoD, verification commands, scope, docs sync requirements, and review evidence. Do not treat passing tests alone as proof of completion.
6. If the current task is incomplete, choose the smallest safe action that continues that task.
7. If the current task is complete, update or prepare the task-state update, then select the smallest ready task that advances the milestone without scope expansion.
8. Route the selected action:
   - use `implementation-slice` semantics for one clear implementation task;
   - use `docs-update` for bounded docs sync;
   - use `project-orchestrator` when the next action needs routing;
   - use `project-delivery` when the milestone needs delivery ownership through implementation, verification, review, and docs sync;
   - use `task-continuation` when another session, worker, or sequential path needs a bounded prompt or task brief;
   - use shared subagents for independent bounded packets with disjoint ownership;
   - use `desktop-thread-delegation` only when a separate user-owned Desktop task/thread handoff is needed, supported, and explicitly authorized.
9. Run the smallest relevant verification for the action taken, inspect the diff when files changed, and report residual risk.
10. Stop when the milestone is complete or a human gate is reached.

## Task Selection Rules

- Prefer the smallest ready task with clear DoD and verification.
- Prefer tasks that directly advance the selected milestone.
- Do not select tasks with unclear source of truth, unmet dependencies, unclear ownership, material risk, or product ambiguity.
- Do not expand scope merely because the runtime is scheduled to wake up again.
- If multiple tasks are ready, choose the one with the smallest blast radius and clearest verification.
- If no ready task exists, prepare a clear human-gate report instead of inventing work.

## Runtime Scheduling

The skill defines what to do after each invocation. It does not create the invocation schedule.

Acceptable invocation wording:

```text
Use milestone-continuation for MVP1.
Every time this thread wakes up, check the current task against its DoD.
If it is complete, choose the next smallest ready task.
Continue until MVP1 is complete or a human gate is reached.
```

When Codex Desktop scheduling is available, the user may pair the skill with a runtime instruction:

```text
Wake this thread every 5 minutes and run the MVP1 milestone-continuation loop.
```

If the runtime cannot honor the requested cadence, report the limitation and provide the safest available fallback.

## Human Gates

Stop before continuing, delegating, or mutating when the next step involves:

- product ambiguity or unclear milestone semantics;
- source-of-truth conflict;
- scope expansion;
- destructive action;
- external write;
- commit, push, PR creation, release, deploy, merge, platform comments, review submissions, or platform-side mutation;
- material security, privacy, data, migration, payment, deployment, auth, or permission risk;
- insufficient verification for a high-risk change;
- unclear Desktop thread tool contract, permission, target identity, branch, worktree, or response shape;
- unpublished Desktop internals, private runtime state, UI scraping, daemons, sidecars, app-server clients, or unsupported runtime adapters.

## Output

- Current milestone status
- Current task status
- Facts from repository files
- Inferences and uncertainty
- Verification used to decide whether the current task is complete
- Selected next task, if any
- Execution mode
- Workflow routed to
- Files changed, if any
- Verification run or still required
- Review or gate requirement
- Residual risk
- Human gate, if any

## Templates

Use existing orchestration templates when the target repository needs durable artifacts:

- `templates/orchestration/task-manifest.template.yaml`
- `templates/orchestration/task-continuation-report.template.md`
- `templates/orchestration/current-task-summary.template.md`
- `templates/orchestration/next-session-prompt.template.md`
- `templates/orchestration/implementation-plan.template.md`
- `templates/orchestration/project-spec.template.md`
