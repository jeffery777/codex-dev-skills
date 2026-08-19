# Release Notes: v0.15.1

Status: release candidate; commit, push, pull request creation, merge, tag,
GitHub Release, and deployment are not created or authorized by this document.

v0.15.1 is a backward-compatible runtime-adapter and control-plane patch over
v0.15.0. It preserves separate CLI and Desktop entrypoints over the shared
delivery, review, and human-gate layers.

## Codex Runtime Compatibility

- Records Codex CLI 0.148.0 and Desktop dependency bundle 26.818.11542 as
  point-in-time evidence.
- Adds bounded non-interactive `codex exec fork` to the CLI session handoff
  executor while keeping interactive `codex fork` a separate manual path.
- Adds Desktop `fork_thread` worktree routing for same-task continuation with
  completed history, queued `clientThreadId` handling, and later ready-thread
  resolution.
- Removes the unverified `/subagents` slash-command claim and retains the
  documented `/agent` selector.

## GitHub Control Plane

- Adds one shared connector-first policy inherited by CLI and Desktop delivery
  entrypoints.
- Uses the GitHub plugin for connector-supported metadata and platform writes,
  local `git` for checkout state, and `gh` only when the exact connector
  operation is unavailable or its permission is insufficient.
- Requires the fallback reason and exact GitHub target to be recorded without
  weakening external-write human gates.

## GitNexus Hook Lifecycle

- Expands the optional `PostToolUse` matcher from Bash-only to `Bash` and
  `apply_patch` without parsing commands, patches, responses, or transcripts.
- Keeps the runner synchronous because background hooks may overlap, finish
  out of order, or be cancelled when a session ends.
- Binds every machine-local config to one exact checkout. Primary-directory
  branches and linked worktrees retain separate worktree identities and index
  aliases; a config for one rejects another checkout.
- Leaves linked-worktree automatic refresh fail-closed. A feature worktree
  cannot update the primary checkout's index.
- Defines post-merge behavior honestly: a remote PR/MR merge does not mutate a
  local index. Advance the primary checkout locally first; a subsequent clean
  `SessionStart` or completed `Bash`-matched shell/unified-exec event may then
  refresh the merged HEAD.

## Compatibility And Rollback

Existing start/resume requests, shared workflow authority, installer groups,
skill names, Desktop deprecated aliases, and Memory M0/M1 contracts remain
compatible. Disable or remove the optional GitNexus hook config to return to
the no-hook path; no index deletion is part of rollback. Reinstall v0.15.0 only
through the normal reviewed installer path if the entire patch must be rolled
back.

## Verification And Release Gate

```bash
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python -m unittest tests.test_gitnexus_hook
./scripts/project-python -m unittest tests.test_github_control_plane_policy
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

The patch release is appropriate because all public changes are additive or
correct stale compatibility guidance; no migration or incompatible workflow
contract is introduced. The annotated `v0.15.1` tag and non-draft,
non-prerelease GitHub Release must bind the exact reviewed merge commit only
after separate human approval.

## Traceability

- Issue #155: <https://github.com/jeffery777/codex-dev-skills/issues/155>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.15.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.15.0...v0.15.1>
