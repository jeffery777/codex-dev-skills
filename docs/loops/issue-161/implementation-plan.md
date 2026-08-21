# Issue #161 Implementation Plan

## Objective

Publish the smallest backward-compatible v0.16.2 runtime-adapter patch for
Codex CLI 0.149.0 and the current Desktop thread-sharing surface without
merging the independent CLI and Desktop entrypoints or changing shared
completion authority.

## Scope

1. Record dated public runtime evidence for CLI 0.149.0, Desktop dependency
   bundle 26.818.22352, and the active Desktop callable schemas.
2. Extend the CLI adapter contract with:
   - manual interactive `codex agents` discovery and control;
   - manual bounded `codex queue` delivery to an exact UUID;
   - read-only `codex doctor --json` diagnostics.
3. Extend the Desktop adapter contract with explicit, privacy-sensitive
   `share_thread` handling and separate revocation guidance.
4. Preserve runtime-neutral shared task selection, authority, verification,
   review, and completion semantics.
5. Add deterministic documentation-contract coverage and align README,
   roadmap, release readiness, version metadata, release notes, and generated
   plugin package.

## Design Decisions

- `codex queue` remains a manual CLI control-plane operation in this patch.
  The existing repo-owned executor is intentionally a private-clone
  `codex exec --json` boundary; routing `queue` through it would falsely imply
  workspace isolation and terminal-turn evidence that the command does not
  provide.
- Queue guidance uses an argv token list and never interpolates arbitrary
  message text into a shell command. Shell-specific output requires a known
  shell and verified literal quoting for the complete message.
- Use an exact canonical session UUID for queue guidance even though the CLI
  also accepts an exact session name. Display names are not stable identity.
- `codex agents` may discover, open, rename, start, or stop tasks. It is not
  classified as wholly read-only; every selected mutation retains its exact
  authorization gate.
- `codex doctor --json` is redacted diagnostic evidence only. It does not
  replace active-schema capability detection or authorize historical wrapper
  execution.
- `share_thread` creates an immutable link and therefore requires explicit
  user intent, known audience, and user-confirmed complete-thread review plus
  inspection of available content. Link creation is not represented
  as reversible through a callable when the active runtime exposes no revoke
  operation; revocation remains a separate data-controls action.
- Removed skill-level model delegation has no migration impact because this
  repository keeps concrete model mappings in explicit opt-in custom-agent
  profiles rather than skill frontmatter.

## Verification

```bash
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

## Release Boundary

The implementation may prepare reviewed v0.16.2 source, version metadata,
release notes, and tag readiness. Commit, push, PR creation, merge, annotated
tag creation on the exact reviewed merge commit, GitHub Release publication,
and deployment remain separately verified actions. Issue #161 does not weaken
those identity or human-gate requirements.
