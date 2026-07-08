# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- Desktop runtime wrapper V1 has completed its current bounded helper path: caller-supplied documented capability metadata normalization can feed the request planner as `capability_evidence`, contract comparison can re-check old wrapper evidence against newer normalized capability evidence before runtime/schema changes are trusted, the planner still emits only dry-run, fallback, or stopped evidence, the create-thread and read-thread preflight helpers can check readiness evidence before future separately approved runtime calls, the evidence pipeline can chain those checks, the session compatibility status validator can validate explicit caller-supplied status before later preflight reference, the first-use handshake helper can construct and validate that status from caller-supplied metadata, old wrapper contract evidence, expected wrapper/helper identity, and an explicit session marker, the session-scoped compatibility cache helper can read or write caller-explicit same-session cache envelopes for contract compatibility evidence only, the create-thread authorization/evidence gate can validate the final caller-supplied envelope before a human considers approving one separate runtime-call implementation slice, the create-thread executor boundary proposal helper can define the single documented `create_thread` call-site contract before any future true executor wiring is considered, the create-thread executor shell helper can validate the final implementation surface without authorizing or performing a runtime call, the create-thread documented callable executor helper can execute only a caller-injected adapter while CLI default remains non-live, the create-thread callable wiring-boundary helper can convert one caller-supplied documented descriptor or explicit non-live wiring contract into the executor adapter contract shape without invoking Desktop runtime, the create-thread callable wiring evidence bundle / executor-request assembly helper can assemble ready wiring evidence into a non-live executor request preview / handoff bundle without executing an injected runner, and the create-thread live smoke helper can call one injected runtime-provided documented `create_thread` callable only after exact human approval to verify new-thread creation and read-only prompt delivery. Current source of truth: `docs/desktop-runtime-wrapper-v1-plan.md`.
- Loop engineering adds an explicit shared entrypoint for clear bounded objectives: bootstrap from durable source of truth, classify current state, route through existing phase skills, verify and review evidence, continue or hand off when safe, and stop at human gates. It preserves the independent use of implementation, documentation, review, formal gate, continuation, milestone, and Desktop-specific skills.
- Repo-owned loop state and ledger support is the next loop-engineering hardening step: keep source revision, task state, claim/lease state, verification evidence, review evidence, blockers, and next decisions in repository files first; treat future external memory adapters as optional cache or coordination layers unless a repository explicitly defines a stronger reviewed authority model.
- Milestone continuation adds a shared upper-layer workflow for checking bounded milestone task state across repeated invocations, selecting the next ready task, routing through existing delivery and continuation workflows, and keeping runtime scheduling outside the skill.
- Keep any later Desktop runtime wrapper slices behind separate review and human approval, especially before adding remediation, broader runtime thread-tool invocation, platform writes, or any other state-changing path.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- Desktop runtime wrapper V1 follow-up slices: any remediation prompted by the live smoke audit, any additional Desktop thread tool path, any platform write, or any broader runtime integration requires separate human approval. Later work must continue to avoid Desktop private runtime state, daemons, app-server clients, sidecars, background services, new skills, catalog entries, and installer entries unless separately approved.
- Plugin packaging follow-up: if maintainers want Codex plugin distribution, add a minimal `.codex-plugin/plugin.json` and repo marketplace entry in a separate slice. Keep it distinct from the filesystem installer and document duplicate-skill risks for users who install the same pack through both paths.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
