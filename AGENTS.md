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

## Python Verification Environment

- Use `./scripts/project-python` for this repository's dependency checks,
  scripts, evals, and unit tests. It resolves a repository `.venv`, `pyenv`, or
  an already-correct `python3` and fails closed unless the exact tracked
  `.python-version` is selected.
- Before installing a missing module, print the selected interpreter and verify
  PyYAML with `./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'`.
- If the resolver cannot select the pinned interpreter or import `yaml`, inspect
  environment resolution before treating PyYAML as absent. Do not fall back to
  bare system Python or install into a different Python environment.
- Use the same resolved Python interpreter for dependency checks, scripts,
  evals, and unit tests throughout a verification run.
- Git worktrees and disposable clones must run the tracked resolver too. Do not
  copy `.venv` through `.worktreeinclude`; create or configure an environment
  for the new checkout when the resolver reports that the pinned runtime is
  unavailable.

## Destructive Actions

Destructive actions require explicit confirmation. This includes deletion, force updates, history rewrites, broad external mutation, direct trunk updates, and cleanup actions that cannot be previewed.

## Runtime Compatibility

Do not depend on unpublished Codex Desktop internals. Desktop-only behavior must be labeled Desktop-only and should provide a CLI fallback when possible.

Do not sync local runtime state, credential files, application state, logs, sessions, caches, SQLite databases, or machine-local config into this repository.
