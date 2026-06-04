# Usage Model

`codex-dev-skills` works best when Codex has durable project context to read before it edits. The goal is to make workflow behavior repeatable across Codex CLI, Codex Desktop, and future maintainer sessions without relying only on chat history.

## Project Artifacts

Useful project-level artifacts include:

- `AGENTS.md` for repo-specific operating rules, verification commands, review expectations, and human gates.
- Project specs that state objective, users, scope, out-of-scope work, requirements, Definition of Done, risks, human gates, and verification strategy.
- Implementation plans that split work into small slices with source of truth, ownership, affected files, review gates, rollback or recovery notes, and open questions.
- Task manifests and continuation reports that record completed, blocked, ready, and unsafe tasks for bounded multi-step work.
- Next-session prompts and current task summaries that preserve verified handoff context while requiring the next agent to re-read repository files.
- Review report templates for code review, docs review, review finding disposition, and merge readiness.
- Policy files for runtime compatibility, destructive actions, delegation, review artifacts, release gates, and merge gates.

The included templates under `templates/orchestration/` and `templates/review/` are starting points for these artifacts.

## Delivery Scope

The workflows can handle more than a single task id when the objective is still bounded.

Good fits:

- A focused implementation slice with clear expected behavior.
- Task routing when the user wants Codex to choose whether to plan, implement, review, continue, hand off, or stop.
- An orchestrated review closure loop for a small patch.
- One bounded milestone capability, such as an MVP import-validation scope.
- Continuing a larger bounded task by selecting the next safe unit of work and preparing a prompt for a later session or worker.
- A docs sync after verified behavior changes.
- A merge-readiness check after implementation, verification, and review evidence exist.

Poor fits without more human direction:

- Open-ended product discovery.
- Broad rewrites without an agreed plan.
- Work that changes public contracts, data, auth, payment, deployment, or infrastructure risk without explicit gates.
- Any task that expects Codex to push, release, deploy, merge, or perform destructive actions without exact approval.

## Human Gates

The workflows can carry local work to PR readiness, but they intentionally stop before:

- product ambiguity
- scope expansion
- destructive actions
- external writes
- commit, push, release, deploy, or merge
- material security, privacy, data, migration, payment, or permission risk

Shared workflows can prepare prompts and worker briefs for future work, but actually opening a new Codex conversation is runtime-specific. Use Codex Desktop delegation, a CLI runner, MCP tool, plugin, or equivalent orchestrator only when that runtime is available and intentionally selected.

For small or single-task work, prefer the smallest direct skill such as `implementation-slice`, `planning`, or `code-review`. `project-orchestrator` may still be used as a router, but it should downgrade a clear single task to the matching focused workflow instead of forcing a project-level delivery loop.

Review gates provide evidence. They do not replace maintainer approval.

## Global Rules And Repo Rules

Global Codex rules are useful for cross-repository baseline behavior:

- read before write
- inspect git state before mutation
- separate facts from inference
- avoid unrelated refactors
- protect unrelated user changes
- verify after edits
- require explicit approval before destructive or external actions

Repo-level files should define project-specific source of truth:

- branch and release conventions
- accepted verification commands
- product requirements and Definition of Done
- review artifact formats
- project-specific policies, templates, and gates
- platform-specific publishing or merge rules

In practice:

1. Global rules define baseline safety and collaboration habits.
2. Repo-level `AGENTS.md`, specs, plans, policies, and templates define project-specific source of truth.
3. These skills execute against that durable context and stop at the next human gate when needed.
