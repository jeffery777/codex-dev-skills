# Codex Development Skills Baseline

This public repository contains Codex CLI and Codex Desktop software development workflows. Treat this file as a repo baseline for maintaining the repository itself.

## Core Rules

- Read before write.
- Inspect current files and git state before mutation when the directory is a git repository.
- Verify target, scope, identity, environment/context, and current state before mutation.
- Keep changes scoped to the requested objective.
- Do not overwrite unrelated user changes.
- Prefer existing repository patterns over new abstractions.
- Run relevant verification after changes.
- Separate facts from inference.
- Mark unverified claims explicitly.
- Mark runtime-specific behavior explicitly.

## Review Mode

When the user asks for review, stay read-only unless they explicitly ask for fixes. Findings should lead with risks, bugs, regressions, missing tests, or policy violations.

## Destructive Actions

Destructive actions require explicit confirmation. This includes deletion, force updates, history rewrites, broad external mutation, direct trunk updates, and cleanup actions that cannot be previewed.

## Runtime Compatibility

Do not depend on unpublished Codex Desktop internals. Desktop-only behavior must be labeled Desktop-only and should provide a CLI fallback when possible.

Do not sync local runtime state, credential files, application state, logs, sessions, caches, SQLite databases, or machine-local config into this repository.
