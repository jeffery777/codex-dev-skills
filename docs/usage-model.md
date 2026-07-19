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

Machine-local executable selection is runtime control-plane state. Repository
Git probes ignore ambient `PATH` and executable-path environment variables,
using the OS default executable search path; a trusted library caller may pass
an explicit absolute path directly. GitNexus operations require an explicit
absolute CLI path. Every script entry has a bound, fingerprinted native
interpreter: exact `#!/usr/bin/env node` or `#!/usr/bin/env -S node` entries
require an explicit Node path; unsupported launch syntax fails closed. Git
itself must be a native executable, not a script wrapper.
Keep those values out of project artifacts and public receipts.

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

V2b external memory can accelerate bootstrap or exploration only after strict
identity, provenance, digest, freshness, conflict, sensitivity, lifecycle, and
adapter-capability validation. The adopted payload stays data-only. Memory
availability does not change model selection, sandbox, permissions, external
write authority, human gates, verification, review, or completion criteria.

The V2c-A GitNexus integration is a deliberately narrow local driver, not an
enabled memory backend. Its machine-local control-plane flow is qualify, inspect,
explicitly enable, explicitly refresh when needed, and disable/roll back. The
qualified 1.6.9 baseline uses strict schema-5 metadata for identity, indexed
revision, and freshness, but parses neither human status/list output nor query
content into memory records. `read_query` and all backend mutation operations
are unsupported, so the effective retrieval behavior remains no memory.

An explicit refresh is a local derived-index operation, not a memory operation.
It requires `analyze --index-only`, exact expected HEAD, a clean direct
worktree, pre-existing local `.git/info/exclude` protection, an isolated alias
and `GITNEXUS_HOME`, offline environment, timeout/lock, and complete before/after
complete worktree (including ignored paths), protected, complete local `.git`
administrative-tree, replacement-neutral Git, local and enabled-worktree
filter/include/attributes rejection, and metadata checks. Refresh uses a
descriptor-bound cross-process `flock` in a current-user-owned machine-local
lock directory. One deterministic fixed-OS-temp per-user lock for the canonical
repository root is mandatory before any optional instance lock, so different
temp environments or configured directories still serialize; that is coordination for cooperating same-UID local processes,
not a distributed or hostile-same-UID security boundary. The isolated home has
its own device/inode-keyed cross-repository lock; the controller holds its
directory descriptor and rechecks emptiness under that lock immediately before
execution. If any check is unknown or
changes unexpectedly, reject the index and preserve the evidence without
resetting, restoring, stashing, staging, or committing. Disabling the adapter
does not require deleting local indexes or changing repository documents.

Use the supported repo-owned operator entrypoint documented in README:
`gitnexus_adapter.py qualify`, `status`, `refresh`, and `disable`. `status`
persists no opt-in; `--enabled` applies to one invocation. `refresh` additionally
requires `--confirm-explicit-refresh`, an exact expected HEAD, and a fresh empty
isolated home. Qualify, status, and refresh also require caller-owned accepted
entry, interpreter-when-applicable, and complete package-tree digests plus an
explicit canonical machine-local package root; those values are checked before
tool execution and remain outside repository files. Omitting `--enabled` or
running `disable` is the rollback path.

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
