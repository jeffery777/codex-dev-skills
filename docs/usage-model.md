# Usage Model

`codex-dev-skills` works best when Codex has durable project context to read before it edits. The goal is to make workflow behavior repeatable across Codex CLI, Codex Desktop, and future maintainer sessions without relying only on chat history.

## Project Artifacts

Useful project-level artifacts include:

- `AGENTS.md` for repo-specific operating rules, verification commands, review expectations, and human gates.
- Project specs that state objective, users, scope, out-of-scope work, requirements, Definition of Done, risks, human gates, and verification strategy.
- Implementation plans that split work into small slices with source of truth, ownership, affected files, review primitives, formal gate triggers, rollback or recovery notes, and open questions.
- Task manifests and continuation reports that use canonical task states for
  bounded multi-step work. Safety concerns are `blocked` with blocker kind
  `safety`, not a separate lifecycle state.
- Loop specs, repo-owned loop state ledgers, and iteration reports that record a bounded objective, source-of-truth files, current route, source revision, task status, claim/lease state, verification evidence, review or gate evidence, blockers, residual risk, and the next loop decision.
- Next-session prompts and current task summaries that preserve verified handoff context while requiring the next agent to re-read repository files.
- Review report templates for code review, docs review, review finding disposition, and merge readiness.
- Policy files for runtime compatibility, destructive actions, delegation, review artifacts, release gates, and merge gates.

The included templates under `templates/orchestration/` and `templates/review/` are starting points for these artifacts.

## Delivery Scope

The workflows can handle more than a single task id when the objective is still bounded.

Good fits:

- A focused implementation slice with clear expected behavior.
- Task routing when the user wants Codex to choose whether to plan, implement, review, continue, hand off, or stop.
- Loop engineering for a clear bounded objective where Codex should repeatedly bootstrap from durable context, route to existing phase skills, verify evidence, review or gate when appropriate, and continue until completion or a human gate.
- An orchestrated review closure loop for a small patch.
- One bounded milestone capability, such as an MVP import-validation scope.
- Repeatedly advancing a bounded milestone from durable task state until the milestone is complete or a human gate is reached.
- Continuing a larger bounded task by selecting the next safe unit of work and preparing a prompt, task brief, continuation prompt, or sequential execution path.
- A docs sync after verified behavior changes.
- A normal merge review or formal branch readiness gate after implementation, verification, and review evidence exist.

Poor fits without more human direction:

- Open-ended product discovery.
- Broad rewrites without an agreed plan.
- Work that changes public contracts, data, auth, payment, deployment, or infrastructure risk without explicit gates.
- Any task that expects Codex to commit, push, create PRs, release, deploy, merge, post platform comments, submit reviews, or perform destructive actions without exact approval.

## Human Gates

The workflows can carry local work to PR readiness, but they intentionally stop before:

- product ambiguity
- scope expansion
- destructive actions
- external writes
- commit, push, PR creation, release, deploy, merge, platform comments, or review submissions
- material security, privacy, data, migration, payment, or permission risk

Shared workflows may use native Goal mode when explicitly requested and may
delegate bounded packets through shared subagents in supported Desktop, CLI,
and IDE runtimes. Goal and subagent state are coordination evidence, not
completion authority. Opening a separate user-owned Desktop task/thread and
managing scheduled work remain runtime-specific control-plane actions. CLI can
prepare and test scheduled prompts but does not provide the Scheduled
management interface.

`loop-engineering` is a shared entrypoint for repeated decision-making, routing,
verification, review, and stopping behavior. It can prepare Desktop handoff
prompts or route to Desktop-specific skills when the runtime and authorization
are available, but it does not itself provide scheduling, user-owned Desktop
task/thread control, platform writes, or merge authority.

For objectives that must survive repeated invocations, subagents, worktrees, or
handoffs, keep stable definitions in a loop spec/task manifest, operational
transitions in validated events, and the reconstructable current view in
`docs/loops/<objective-id>/loop-state-ledger.yaml`. Use fenced claims only when
the coordination store can provide atomic acquisition; separate worktrees are
not a shared lock. Completion remains reconstructable from repository files,
git state, verification evidence, review evidence, and accepted platform state.

For small or single-task work, prefer the smallest direct skill such as `implementation-slice`, `planning`, or `code-review`. `project-orchestrator` may still be used as a router, but it should downgrade a clear single task to the matching focused workflow instead of forcing a project-level delivery loop.

Review primitives such as `code-review`, `docs-review`, and high-risk `code-review-deep` provide ordinary review evidence. Formal `code-review-gate` and `docs-review-gate` runs are reserved for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions, and they do not replace maintainer approval.

## Global Guidance, Repo Instructions, And Rules

Global Codex guidance is useful for cross-repository baseline behavior:

- read before write
- inspect git state before mutation
- separate facts from inference
- avoid unrelated refactors
- protect unrelated user changes
- verify after edits
- require explicit approval before destructive or external actions

Repo-level instruction files should define project-specific source of truth:

- branch and release conventions
- accepted verification commands
- product requirements and Definition of Done
- review artifact formats
- project-specific policies, templates, and gates
- platform-specific publishing or merge rules

Use `AGENTS.md` for durable instruction layering, and `AGENTS.override.md` only when a temporary override should take precedence without deleting the base file. Use Codex `.rules` files for command permission exceptions, not as a substitute for workflow policy or human gates.

Runtime configuration remains outside these skills. Permission profiles, `codex exec` sandbox choices such as the default read-only automation posture, web search mode, MCP server setup, and project instruction discovery limits such as `project_doc_max_bytes` should be configured in Codex runtime settings or documented project setup. Skills may remind users to verify those settings, but they should not imply that installing this pack changes them.

In practice:

1. Global guidance defines baseline safety and collaboration habits.
2. Repo-level `AGENTS.md`, specs, plans, policies, and templates define project-specific source of truth.
3. These skills execute against that durable context and stop at the next human gate when needed.
