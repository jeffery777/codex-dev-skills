# Loop Engineering

These examples show how to invoke the `loop-engineering` entrypoint after installing the delivery workflow group.

## Bounded Feature To PR Readiness

```text
Use loop-engineering for issue #123.

Read the repo instructions, issue, implementation plan, task manifest, review evidence, and current git state before editing.
Autonomously continue through planning, implementation, verification, review, docs sync, and PR readiness while the objective and DoD remain clear.
Use existing phase skills as needed.
Stop before destructive actions, external writes, commit, push, PR creation, merge, release, deploy, platform comments, review submissions, material risk, or unclear source of truth unless I explicitly authorize the exact action.
```

## Review Closure Loop

```text
Use loop-engineering on the current branch.

Classify whether this is a review closure loop.
Run the appropriate review primitive, fix MUST-FIX findings that are safe and in scope, rerun review, and stop after two review/fix rounds or at the next human gate.
Do not commit, push, create a PR, merge, or submit platform comments unless explicitly authorized.
```

## Milestone Loop With Runtime Wakeups

```text
Use loop-engineering for MVP1.

Every time this thread wakes up, re-read the milestone spec, task manifest, status docs, review evidence, and git state.
If the current task is complete, choose the next smallest ready task.
If the current task is incomplete, continue it with the smallest safe action.
Continue until MVP1 is complete or a human gate is reached.
```

The cadence is runtime behavior. In Codex Desktop, a heartbeat or automation may wake the thread. In Codex CLI, use a manual invocation, continuation prompt, task brief, or sequential execution path.

## Desktop Handoff Boundary

```text
Use loop-engineering for this bounded objective.

If a task is better suited for a separate Desktop worker, first prepare a task brief and claim/lease proposal.
Only open, fork, read, or message a Desktop thread if the runtime exposes the documented capability, the target and response shape are clear, and I explicitly authorize that exact action.
If Desktop thread tools are unavailable, return a paste-ready handoff prompt instead.
```
