# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- Evaluate whether a Desktop runtime wrapper V1 can move from docs-only planning to implementation. Current source of truth: `docs/desktop-runtime-wrapper-v1-plan.md`. The first implementation slice remains blocked until maintainers explicitly approve moving from planning to code.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- Desktop runtime wrapper V1 first implementation slice: a non-state-changing request planner and CLI-compatible fallback generator, with no Desktop thread-tool invocation, no private runtime state, no daemon, no app-server client, no new skill, and no catalog or installer entry.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
