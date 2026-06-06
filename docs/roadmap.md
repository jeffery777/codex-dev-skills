# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- Desktop runtime wrapper V1 has completed its current non-state-changing helper path: caller-supplied documented capability metadata normalization can feed the request planner as `capability_evidence`, contract comparison can re-check old wrapper evidence against newer normalized capability evidence before runtime/schema changes are trusted, the planner still emits only dry-run, fallback, or stopped evidence, and the create-thread and read-thread preflight helpers can check readiness evidence before future separately approved runtime calls. Current source of truth: `docs/desktop-runtime-wrapper-v1-plan.md`.
- Keep any later Desktop runtime wrapper slices behind separate review and human approval, especially before adding runtime thread-tool invocation or any state-changing path.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- Desktop runtime wrapper V1 later slices: at most one explicitly approved runtime thread-tool call path after the non-state-changing planner, capability evidence, contract comparison, create-thread preflight, and read-thread preflight paths remain stable. Later work must continue to avoid Desktop private runtime state, daemons, app-server clients, sidecars, background services, new skills, catalog entries, and installer entries unless separately approved.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
