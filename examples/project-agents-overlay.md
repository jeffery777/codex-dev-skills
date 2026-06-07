# Project AGENTS Overlay Example

Use this example when a repository wants a repo-level `AGENTS.md` that works with the reusable skills in this project.

This is an example, not a required template. Adapt names, commands, and gates to the target repository.

## Example Repo Baseline

```markdown
# Project Codex Instructions

This repository uses Codex CLI and Codex Desktop for bounded implementation, documentation updates, review, and PR readiness.

## Core Rules

- Read before write.
- Inspect current files and git state before mutation.
- Keep changes scoped to the requested objective.
- Do not overwrite unrelated user changes.
- Prefer existing project patterns over new abstractions.
- Run relevant verification after changes.
- Separate facts from inference.
- Mark runtime-specific behavior explicitly.

## Source Of Truth

- `AGENTS.md` defines repository operating rules.
- `docs/roadmap.md` defines current roadmap status.
- Project specs and implementation plans define requirements, Definition of Done, risks, and verification.
- Review artifacts are evidence, but repository files remain the durable source of truth.

## Review Mode

When asked for review, stay read-only unless the maintainer explicitly asks for fixes.

Use:

- `code-review` for ordinary code or mixed diffs.
- `code-review-deep` for security, packaging, migration, data, or cross-module risk.
- `docs-review` for docs-only or docs-dominant changes.
- `merge-review` for normal base-to-head merge evidence.
- `merge-review-deep` for release-sensitive or high-risk merge evidence.

Formal gate adapters such as `code-review-gate`, `docs-review-gate`, and `merge-readiness-gate` are used only for commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.

## Human Gates

Stop before:

- destructive actions
- external writes
- commit, push, PR creation, merge, tag, release, deploy, platform comments, or review submissions
- material security, privacy, data, migration, deployment, payment, or permission risk
- unclear product or public-contract decisions

## Runtime Compatibility

- Shared workflows must work from repository files and ordinary shell/git inspection.
- Desktop-only thread delegation must be labeled Desktop-only and include a CLI fallback.
- Do not read or commit Desktop private runtime state, local databases, logs, sessions, caches, auth files, app state, or machine-local config.
```

## Why This Pairs With The Skills

This overlay gives Codex durable project context before it invokes skills such as `implementation-slice`, `project-delivery`, `desktop-thread-delegation`, `docs-review-gate`, or `merge-readiness-gate`.

The goal is not to duplicate every skill instruction. The repo overlay should define project-specific source of truth, verification commands, and human gates; the installed skills provide reusable workflow behavior.
