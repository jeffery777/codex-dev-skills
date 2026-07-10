# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- The former Desktop runtime wrapper V1 chain is frozen as historical
  compatibility and regression evidence. It is not an active execution path;
  future cleanup may archive or remove it only through a separately reviewed
  deprecation slice.
- Loop engineering adds an explicit shared entrypoint for clear bounded objectives: bootstrap from durable source of truth, classify current state, route through existing phase skills, verify and review evidence, continue or hand off when safe, and stop at human gates. It preserves the independent use of implementation, documentation, review, formal gate, continuation, milestone, and Desktop-specific skills.
- Repo-owned loop state and ledger support is the next loop-engineering hardening step: keep source revision, task state, claim/lease state, verification evidence, review evidence, blockers, and next decisions in repository files first; treat future external memory adapters as optional cache or coordination layers unless a repository explicitly defines a stronger reviewed authority model.
- Loop Engineering V1 is tracked in issue #81. It adds one production route and
  transition core, structured YAML validation, revision/event/idempotency
  guards, deterministic workflow evals, native Goal mode, shared subagents, and
  thin scheduler/Desktop task adapters. The v0.x Desktop wrapper chain becomes
  legacy compatibility evidence rather than the active runtime path.
- Milestone continuation adds a shared upper-layer workflow for checking bounded milestone task state across repeated invocations, selecting the next ready task, routing through existing delivery and continuation workflows, and keeping runtime scheduling outside the skill.
- Keep any later Desktop runtime wrapper slices behind separate review and human approval, especially before adding remediation, broader runtime thread-tool invocation, platform writes, or any other state-changing path.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- Historical wrapper cleanup: inventory tests and documents that still require
  `desktop_runtime_*`, define a compatibility sunset, then archive or remove
  them without connecting them to the active native path.
- Plugin packaging follow-up: if maintainers want Codex plugin distribution, add a minimal `.codex-plugin/plugin.json` and repo marketplace entry in a separate slice. Keep it distinct from the filesystem installer and document duplicate-skill risks for users who install the same pack through both paths.
- Global profile synchronization follows the accepted Loop Engineering V1
  authority, goal, subagent, and human-gate contract. The separate global
  profile repository should not be edited in issue #81.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
