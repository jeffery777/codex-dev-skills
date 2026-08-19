# Issue #151 Implementation Plan

## Objective

Publish a bounded v0.14.2 hotfix that moves filesystem-installer force-update
backups out of Codex skill discovery roots while preserving recoverability,
whole-update preflight, staged replacement, and no-partial-success guarantees.
Successful rollback must restore the pre-update group; if rollback itself
fails, the installer must fail closed, retain recoverable data, and report its
exact managed locations rather than claiming atomic completion.

Tracking issue: <https://github.com/jeffery777/codex-dev-skills/issues/151>

## Source Of Truth

- `AGENTS.md` and `SECURITY.md`
- GitHub Issue #151
- `install.sh`
- `tests/test_installer_runtime_groups.py`
- `tests/test_installer_agent_profiles.py`
- `tests/test_plugin_packaging.py`
- `README.md`
- `docs/troubleshooting.md`
- `docs/roadmap.md`
- `docs/release-readiness.md`
- `catalog.yaml`
- `plugin/codex-dev-skills/.codex-plugin/plugin.json`

The accepted entry revision is
`f5461ab3ffb4f2c47218d579cd4dd684dcac6182`, the v0.14.1 merge commit and
the verified `origin/main` revision when Issue #151 and branch
`codex/151-installer-backup-isolation-v0142` were created.

## Design Decision

Forced updates will use one deterministic managed backup root:

```text
${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/
  <sha256(canonical-target-root)>/
    skills/<relative-target>.bak
    templates/<relative-target>.bak
    agent-profiles/<relative-target>.bak
```

The canonical target-root digest isolates default, legacy, and explicitly
authorized custom targets without writing an absolute machine path into a
backup name. A deterministic backup slot preserves the current safety
contract: an unresolved backup blocks another forced update and is never
silently overwritten.

The transaction lock serializes only cooperating installer processes using the
same canonical `XDG_STATE_HOME` managed-state namespace. Distinct state roots
aimed at the same authorized custom target do not share a lock; apply-time
identity checks fail closed on detected ordinary drift but do not provide
hostile same-UID process isolation. The supported cooperating model preserves
the never-silent-overwrite guarantee.
The lock is acquired only after complete filesystem and profile input preflight;
the locked apply phase rechecks affected identities and backup slots before
replacement.

Fresh installs and forced replacements normalize directories to `0700`, regular
files to `0600`, and source-executable files to `0700`; this also applies to
custom/project targets and can remove other local accounts' read access.
Existing unsafe paths fail closed and are never silently repaired with `chmod`.

The installer will not add a backup-root override in v0.14.2. The managed root
must be machine-local, non-symlinked, current-user-owned, and not group/world
writable. It must not overlap the repository, either standard skill discovery
root, or the selected skill, template, or agent-profile roots. Every backup
parent and destination parent must be on the same filesystem before mutation;
cross-filesystem rename is unsupported and fails closed.

## Implementation Slices

1. Add centralized managed-root validation and deterministic artifact-to-backup
   mapping for skills, templates, and agent profiles.
2. Preflight every source, destination, backup slot, path boundary, symlink or
   special-file condition, and filesystem device for the complete expanded
   update before target mutation.
   `install` and non-force `update` also validate their installer state and
   receipt boundary before mutating a selected discovery target; an unsafe
   boundary must leave those selected targets unchanged.
   Regular target-tree files and receipts must have link count one. A force
   transaction additionally requires this of its sources and staged payloads.
   Existing receipts must pass a no-write append-open and descriptor identity
   check, using final-symlink protection where the platform provides it;
   immutable, append-only, or read-only paths fail closed without automatic
   repair. On Linux, filesystem-flag ioctl errors, including unsupported
   filesystem or special ABI, also fail closed without an open/fstat-only
   fallback.
3. Stage replacement content beside each destination, then apply the update as
   a bounded transaction. If backup or replacement fails, restore the current
   artifact and roll earlier artifacts back in reverse order. Preserve data and
   report exact recovery locations if rollback itself fails.
4. Extend isolated temporary-root tests for default, legacy, and custom roots;
   all three artifact kinds; collision and injected failures; path, symlink,
   special-file, and device boundaries; legacy discovery-root backups; no
   duplicate discovered skills; successful expanded-group rollback; and
   explicit recoverability when a restore operation itself fails.
   Include non-force `install` and `update` state/receipt-boundary failures
   that show selected targets remain unchanged.
   Include multiply-linked target/receipt regressions, force-transaction
   source/staged-payload regressions, and immutable/append-only/read-only
   receipt cases, including Linux filesystem-flag ioctl failure.
5. Document the new backup and restore path. Add dry-run-first legacy `*.bak`
   inventory and cleanup guidance that never automatically deletes, moves, or
   claims ownership of unknown data.
6. Align the v0.14.2 installer, catalog, plugin manifest, README current release
   reference, contract tests, release readiness, roadmap, and release notes.
   Remove only the completed plugin-packaging backlog wording; do not implement
   GN-FU-01 or another feature.

## Definition Of Done

- Skill, template, and agent-profile force-update backups are outside both
  standard Codex skill discovery roots.
- Existing backup slots are never overwritten and block the complete update
  before target mutation.
- Default, legacy, and custom target roots receive distinct backup identities.
- Unsafe, overlapping, symlinked, special-file, or cross-filesystem paths fail
  closed before target mutation.
- Unsafe installer state or receipt boundaries fail before non-force `install`
  or `update` changes a selected discovery target; this bounded guarantee does
  not claim unconditional atomicity for disk-full, hostile same-UID, or every
  runtime failure.
- Multiply-linked regular target files and receipts, plus receipts that cannot
  pass the no-write append-open/descriptor-identity check, fail closed without
  automatic unlink, flag, or permission repair. Immutable or append-only
  receipt flags fail closed where the platform exposes them. Force transactions
  also reject multiply-linked sources and staged payloads. On Linux, a
  filesystem-flag ioctl error fails closed without an open/fstat-only fallback.
- Every expanded update is fully preflighted and staged before replacement;
  injected failures either restore the pre-update group or produce an explicit
  failed recovery state without any partial-success claim.
- Replacement failure attempts reverse-order restoration of the complete
  group. A successful rollback restores the original group; a restore failure
  preserves all recoverable data and reports the managed backup and recovery
  locations without recording a successful installer state.
- Legacy discovery-root `*.bak` handling is dry-run-first and never mutates
  unknown user data automatically.
- Tests use isolated temporary homes/state/targets and do not modify the real
  `~/.agents` or `~/.codex` trees.
- `install.sh`, `catalog.yaml`, plugin manifest, README, release notes, and
  version/docs contract tests agree on v0.14.2.
- `docs/release-notes-v0.14.2.md` remains a release candidate; merge, tag,
  GitHub Release, and deployment remain separate human gates.
- Focused and full verification, code and deep installer review, docs review,
  security diff scan, deep merge review, and exact-head merge readiness have no
  unresolved blocker.

## Verification Plan

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
bash -n install.sh scripts/validate-repo.sh scripts/project-python
./scripts/project-python -m unittest \
  tests.test_installer_runtime_groups \
  tests.test_installer_agent_profiles \
  tests.test_plugin_packaging \
  tests.test_native_runtime_contract_docs
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

Focused commands may be expanded when the final test ownership is known, but
they must not bypass the tracked Python resolver.

## Risks And Stop Conditions

- Stop if the managed root overlaps a discovery, repository, template, or
  profile boundary, or if path ownership/type/symlink evidence is uncertain.
- Stop a forced update before mutation when any destination and managed backup
  parent are on different filesystems.
- Treat an unexpected `EXDEV` after preflight as environmental drift; fail and
  restore rather than copy across filesystems.
- Do not guess ownership of legacy backups or automatically move/delete them.
- Close all MUST-FIX code, docs, security, and merge-review findings before PR
  readiness.
- Re-run review and readiness when the exact head changes.
- Merge, tag, GitHub Release, local/global deployment, and real-profile backup
  migration require separate explicit maintainer authorization.

## Out Of Scope

M2, V3-C, Memory M1 activation or efficacy, GN-FU-01 implementation,
historical wrapper cleanup, plugin distribution redesign beyond compatibility
needed by this fix, automatic mutation of existing user backups, merge, tag,
GitHub Release, and deployment.
