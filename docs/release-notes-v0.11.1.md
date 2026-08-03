# Release Notes: v0.11.1

Release date: 2026-08-03

v0.11.1 is a compatibility and verification-environment patch release for the
V2d-B feature baseline introduced in v0.11.0. It publishes the reviewed Codex
Desktop and CLI adapter maintenance from Issue #129 / PR #130 without changing
shared task selection, implementation, verification, review, subagent
delegation, completion authority, or human gates.

## Codex Desktop Compatibility

- Refreshed the maintained public compatibility evidence from ChatGPT desktop
  app `26.721.81911` build `5973` to `26.727.40816` build `6067`,
  retaining bundle ID `com.openai.codex`.
- Added the required created-task UI directive after successful
  `create_thread`, with separate `threadId` and queued `clientThreadId`
  forms.
- Kept dispatch, UI registration, registry observation, navigation, sidebar
  rendering, pinning, and repository completion as distinct states. A stale
  sidebar cannot trigger duplicate task creation.
- Distinguished same-directory `fork_thread` continuation, fresh
  same-project local creation, intentionally isolated worktree creation, and
  deliberately projectless work.
- Preserved runtime-returned project and host identity, including fail-closed
  handling when a remote fork's child `hostId` cannot be resolved through a
  supported registry result.
- Limited automatic navigation to explicit user requests and retained only
  public search, sidebar, archive, and local-chat deep-link fallbacks.

## Codex CLI Compatibility

- Kept Codex CLI `0.146.0` as the version-unchanged control.
- Added a bounded CLI-only manual `codex fork <SESSION_ID>` handoff path with
  an exact UUID and explicit `tui.resume_cwd` `current` or `session`
  working-directory choice.
- Left the repo-owned non-interactive private-clone executor unchanged: it
  continues to support only `codex exec --json` start and exact-UUID
  `codex exec resume ... --json`.
- Kept CLI session identifiers separate from Desktop task identifiers and
  treated all dispatch results as coordination evidence rather than repository
  completion.

## Verification Environment

- Added repository guidance to activate the existing project environment or
  otherwise honor the tracked `.python-version` before Python verification.
- Added an interpreter and PyYAML identity preflight before dependency
  installation.
- Replaced unconditional installation guidance with a conditional install only
  after confirming that the selected project interpreter genuinely lacks
  PyYAML.
- Required one resolved interpreter for dependency checks, scripts, evals, and
  tests throughout a verification run.

## Boundaries

This release adds no Desktop or CLI private-state reader, UI scraper,
app-server client, daemon, sidecar, MCP server, forced sidebar refresh,
interactive TUI automation, new Git worktree policy, global skill deployment,
or private PoC content. Desktop-specific UI, project, thread, host, worktree,
and navigation behavior remains in the Desktop adapter; CLI session control
remains in the CLI adapter; shared workflow semantics remain unchanged.

## Verification

The release candidate completed 824 repository tests, the focused release,
installer, and runtime-contract suite, repository validation, and
`git diff --check` using Python 3.12.9 with PyYAML 6.0.3.

Re-run the release candidate checks from the repository root using the tracked
Python environment:

```bash
python3 --version
python3 -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
```

Release publication remains subject to exact-head code and documentation
review, a complete security diff scan, zero-findings Merge review, formal
readiness, and separate exact authorization for merge, tag, and GitHub Release.

## Rollback

Review `./install.sh diff --all` before reinstalling or updating. Rolling back
to v0.11.0 restores the prior published skill and documentation snapshot but
also removes the v0.11.1 compatibility and verification-environment guidance.
Do not delete or overwrite Desktop tasks, CLI sessions, repositories, installed
skills, or machine-local state as an implicit rollback.

## Traceability

- Compatibility issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/129>
- Compatibility PR:
  <https://github.com/jeffery777/codex-dev-skills/pull/130>
- Release issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/131>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.11.0...v0.11.1>
