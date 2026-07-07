# Release Notes: v0.3.0

Release date: 2026-07-07

These release notes summarize the v0.3.0 release candidate. This release adds the explicit `loop-engineering` workflow capability while preserving the existing phase skills, review primitives, formal gates, installer groups, and Codex CLI / Codex Desktop runtime boundaries.

## Highlights

- Added `loop-engineering` as a shared user-facing skill for clear bounded objectives.
- Added `workflows/loop-engineering-workflow.md` to describe the repeatable bootstrap, classify, route, act, verify, review, continue, handoff, stop, or complete cycle.
- Added loop engineering templates for source-of-truth specs, iteration reports, handoff prompts, and task claim / lease records.
- Added loop engineering documentation and examples so users can discover the workflow directly from the README.
- Updated `codex-delivery-workflow` installer and catalog metadata so the loop skill and templates install with the existing delivery workflow group.
- Updated the installer state version to `0.3.0` and kept repository validation aligned with the README current release notes reference.

## Loop Engineering Entry Point

The new `loop-engineering` skill is a thin entrypoint over existing skills. It classifies the current objective and routes to the smallest suitable workflow:

- `implementation-slice` for one clear implementation task;
- `docs-update` for bounded documentation sync;
- `project-orchestrator` for route selection or bounded review closure;
- `project-delivery` for a bounded objective through PR readiness;
- `milestone-continuation` for repeated milestone progress from durable task state;
- `task-continuation` for next-task selection or handoff artifacts;
- review primitives and formal gates when evidence or readiness decisions are needed;
- Desktop-specific skills only when Desktop runtime behavior is intentionally selected and exactly authorized.

This release does not make `loop-engineering` a scheduler, worker runtime, platform writer, merge bot, or replacement for the focused phase skills.

## Installer And Catalog

`loop-engineering` is installed through the existing delivery workflow group:

```bash
./install.sh install codex-delivery-workflow
```

The group now includes:

- `skills/loop-engineering`
- `templates/orchestration/loop-engineering-spec.template.md`
- `templates/orchestration/loop-iteration-report.template.md`
- `templates/orchestration/loop-handoff-prompt.template.md`
- `templates/orchestration/task-claim-lease.template.yaml`
- `workflows/loop-engineering-workflow.md`

The installer target behavior remains unchanged from v0.2.2:

- `~/.codex/skills/<skill>/` remains the default target.
- `CODEX_DEV_SKILLS_TARGET=agents` installs skills under `~/.agents/skills/<skill>/`.
- Templates continue to install under `~/.codex/templates/...`.

## Runtime Boundaries

The loop engineering workflow remains shared and repository-artifact driven. It works in Codex CLI and Codex Desktop with ordinary repository files, shell commands, git inspection, and durable artifacts.

Desktop-only behavior remains explicitly labeled. Heartbeats, automations, worker delegation, thread creation, thread forking, thread messaging, and thread inspection require runtime support and exact user authorization before use.

This release does not add a live Desktop runtime adapter, app-server client, daemon, sidecar, UI scraper, MCP server, plugin package, marketplace entry, platform write path, or Desktop private runtime-state reader.

## Documentation Alignment

README and user-facing docs now explain:

- how to install the delivery workflow group that contains `loop-engineering`;
- how to invoke `loop-engineering` from a prompt;
- when to use `loop-engineering` versus `project-delivery`, `milestone-continuation`, `task-continuation`, or Desktop-specific delegation skills;
- which loop templates and workflow files are included.

## Verification

Run from the repository root:

```bash
./scripts/validate-repo.sh
git diff --check
bash -n install.sh
bash -n scripts/validate-repo.sh
```

Verification used for the v0.3.0 candidate:

- `./scripts/validate-repo.sh` passed.
- `git diff --check` passed with no output.
- `bash -n install.sh` passed.
- `bash -n scripts/validate-repo.sh` passed.
- PR and merge readiness evidence confirmed that README, installer metadata, catalog metadata, release notes, and the `loop-engineering` artifacts are aligned.

## Residual Risk

- GitHub has no configured status checks for these PR heads; release confidence relies on local verification and formal review evidence.
- `loop-engineering` is intentionally a thin orchestration entrypoint. Real project quality still depends on clear source-of-truth files, bounded objectives, verification commands, and human gates.
- Plugin packaging remains deferred, so users who want plugin distribution need a later package/marketplace slice.
