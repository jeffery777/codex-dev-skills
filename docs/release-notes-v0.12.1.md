# Release Notes: v0.12.1

Release date: 2026-08-12

v0.12.1 is a compatibility and verification-environment patch for
the V3-A feature baseline published in v0.12.0. It tracks Issue #139 and keeps
Codex CLI and Desktop as independent runtime adapters over unchanged shared
task selection, implementation, review, completion, and human-gate semantics.

## Codex Desktop Compatibility

- Added the current optional `create_thread.title` callable field and made a
  concise non-empty safe title mandatory at the Desktop adapter boundary for
  stable UI display. Title derivation accepts only approved nonsensitive task
  metadata, previews the exact value, and falls back to `Project task` rather
  than copying prompt or sensitive context.
- Kept project association bound to the exact `projectId`, not title text, and
  required ready-task registry verification when the runtime exposes the
  association.
- Prevented delayed worktree readiness or sidebar rendering from triggering a
  duplicate creation; queued `clientThreadId` remains distinct from
  `threadId`.
- Adopted the current environment default: fresh Git project tasks use a
  worktree, non-Git projects use local, and a Git saved checkout uses local only
  when explicitly requested.
- Refreshed point-in-time evidence for `list_projects` schema version 2 and
  `list_threads` schema version 4, including `pinnedThreads`, `pinnedIndex`, and
  non-pinned `threads`.

## Shared Worktree Verification

- Added executable `scripts/project-python`, which selects an explicit project
  interpreter, repository `.venv`, `pyenv`, or an already-correct `python3`,
  then rejects any version that differs from tracked `.python-version`.
- Routed repository validation, CI dependency installation, environment
  preflight, and the full unit suite through the same resolver.
- Applied the same rule to Desktop worktrees, ordinary CLI worktrees, and the
  CLI handoff disposable private clone. A missing pinned runtime or dependency
  blocks verification rather than permitting a mismatched bare system Python
  or installation into a different interpreter.
- Kept virtual environments checkout-specific and prohibited copying `.venv`
  through `.worktreeinclude`.

## Codex CLI Compatibility

- Recorded Codex CLI `0.147.0` as the current point-in-time control.
- Bumped the CLI handoff prompt boundary from
  `no-publication-no-recursion/v0` to
  `no-publication-no-recursion/v1` so stale requests fail closed until they
  acknowledge the repository interpreter contract.
- Left the CLI session operation contract at `codex-cli-session-handoff/v0`;
  no Desktop task identifier or callable moved into the CLI adapter.

## Boundaries

This patch adds no Desktop or CLI private-state reader, UI scraper, app-server
client, daemon, sidecar, background service, dependency auto-installer, forced
sidebar refresh, or live task mutation. The compatibility assessment created no
Desktop task. V3-B, Agent Memory, V3-C automation, and all proposal promotion
remain outside this patch.

## Verification

Re-run from the repository root:

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
```

The current local candidate passes all 846 discovered repository tests,
repository validation, and `git diff --check` with Python 3.12.9 and PyYAML
6.0.3. Pull-request CI and exact-merge-commit verification remain pending.

Tag and GitHub Release publication remain blocked until the branch is committed,
pushed, reviewed through a ready PR with passing CI, merged, and reverified at
the exact merge commit. The annotated `v0.12.1` tag and non-draft,
non-prerelease GitHub Release must point to that exact reviewed merge commit.

## Rollback

Review `./install.sh diff --all` before reinstalling. Rolling back to v0.12.0
restores the previous runtime-adapter guidance and bare validation entrypoints,
but it does not delete Desktop tasks, Git worktrees, CLI sessions, repositories,
project environments, installed skills, or machine-local state.

## Traceability

- Compatibility and release-candidate issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/139>
- Proposed compare, available after tag publication:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.12.0...v0.12.1>
