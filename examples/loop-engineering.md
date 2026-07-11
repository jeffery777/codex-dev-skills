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

## Repo-Owned Loop Ledger

```text
Use loop-engineering for issue #123.

Create or update docs/loops/issue-123/ using the loop-state-ledger, loop spec, task manifest, current task summary, iteration report, and task claim/lease templates.
Use the loop spec and manifest for stable definitions, validated events for
operational transitions, and the repo-owned ledger as their reconstructable
current view. Use git, verification, review, and accepted platform state for
completion evidence.
Do not treat external memory, worker reports, chat summaries, or Desktop thread summaries as completion evidence unless repo files, git state, verification, review evidence, or accepted platform state confirm them.
```

The ledger baseline works in Codex CLI and Codex Desktop because it is ordinary
repository state. Shared subagents and Desktop automation/task/thread/worktree
adapters may use it, but runtime state does not replace repository authority.

## Heterogeneous Subagent Routing

```text
Use loop-engineering for this bounded objective.

Classify ambiguity, reasoning depth, context volume, security/data/migration/public-contract
risk, write blast radius, latency/cost sensitivity, independence, and verification burden.
Select an installed custom-agent role only after preflight. Record the route receipt,
worker receipt, and main-agent integration disposition. If the requested profile is
unavailable, try the same capability class, then a safe parent/default model, then run
sequentially. Stop at a human gate rather than downgrading high-risk work unsafely.
Do not let the role or model expand permissions, scope, external-write authority, gates,
or completion criteria.
```

Materialize the installed decision and integration templates, then keep live
runtime and filesystem evidence out of those documents:

```bash
python3 <skill-dir>/scripts/loopctl.py agent-route <decision-input.yaml> \
  --runtime-facts /path/to/current-runtime-facts.json
python3 <skill-dir>/scripts/loopctl.py agent-integrate <receipt.yaml> \
  --repo-root /path/to/current/repository \
  --artifact-root /path/to/worker-output \
  --verification-root /path/to/main-agent-verification \
  --assignment-fresh \
  [--profile-path /path/to/selected-custom-profile.toml]
```

The optional profile flag is required when the route selected a custom profile
and omitted for parent/default or sequential fallback. Both commands fail
closed on stale or self-attested evidence.

## Desktop Handoff Boundary

```text
Use loop-engineering for this bounded objective.

If a task is independent and bounded, use a shared subagent with disjoint
ownership. If I explicitly want a separate user-owned Desktop task/thread,
first prepare a task brief and claim/lease proposal.
Only open, fork, read, or message a Desktop thread if the runtime exposes the documented capability, the target and response shape are clear, and I explicitly authorize that exact action.
If Desktop thread tools are unavailable, return a paste-ready handoff prompt instead.
```
