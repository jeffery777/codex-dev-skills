# Release Notes: v0.14.2

Status: release candidate; merge, tag, GitHub Release, and deployment are not
created or authorized by this document.

v0.14.2 is an installer-backup isolation hotfix over v0.14.1. It does not
change the released Memory M0/M1 contracts, workflow completion authority, or
plugin distribution model.

## Filesystem Installer Backup Isolation

- Moves forced-update backups for filesystem skills, templates, and agent
  profiles into a deterministic managed hierarchy below
  `${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/`, outside
  `~/.agents/skills` and `~/.codex/skills` discovery roots.
- Separates backup slots by canonical target-root digest and artifact kind, so
  default, legacy, and explicitly authorized custom targets do not share a
  slot. The slot ends in the artifact-relative target plus `.bak`; an existing
  slot blocks the complete forced update before mutation and is never
  overwritten.
- Preserves staged replacement and recovery: unsafe paths, symlink or special
  file boundaries, backup collisions, and unsupported cross-device rename
  conditions fail closed. The managed root rejects checkout, target, and
  standard discovery-root overlap and requires current-user ownership with no
  group/world-write access. Every replacement is staged before mutation;
  replacement failure attempts to roll prior changes back in reverse order.
  The transaction lock is acquired after complete filesystem/profile input
  preflight, and the locked apply phase rechecks identities and backup slots.
  Successful rollback restores the prior state; restoration failure reports
  recoverable locations with `CRITICAL` status rather than claiming an
  unconditional atomic or no-partial result.
- Normalizes fresh and forced replacement permissions: directories are `0700`,
  regular files `0600`, and source-executable files `0700`. This includes
  authorized custom/project targets and can remove other local accounts' read
  access; unsafe existing paths fail closed rather than being silently repaired.
- Validates the installer state and receipt boundary before an `install` or
  non-force `update` changes a selected discovery target. An unsafe boundary
  leaves the selected skills, templates, and agent profiles unchanged. This is
  a bounded preflight guarantee, not an unconditional atomicity claim for
  disk-full, hostile same-UID interference, or every runtime failure.
- Rejects multiply-linked regular target-tree files and receipts in relevant
  preflight. Force transactions additionally reject multiply-linked sources and
  staged payloads. Existing receipts must also pass an append-open-without-write
  and descriptor-identity check, using final-symlink protection where the
  platform provides it; read-only, immutable, or append-only receipts fail
  closed without an automatic `unlink`, `chflags`, or permission repair.
  On Linux, a filesystem-flag ioctl inspection error, including unsupported
  filesystem or special ABI, also fails closed rather than falling back to
  open/fstat-only validation.
- Keeps legacy discovery-root `*.bak` user-owned. Guidance begins with a
  read-only inventory and never automatically deletes, moves, or adopts
  unknown data.

## Verification And Release Gate

The release candidate requires focused isolated installer tests covering skill,
template, and profile updates; collision and failure injection; path and device
boundaries; and duplicate-discovery prevention. It also requires catalog/plugin
version alignment, repository validation, diff inspection, code/deep/docs
review, security-diff evidence, exact-head merge readiness, and isolated
non-force `install`/`update` state-boundary failure tests that prove selected
targets remain unchanged, including multiply-linked and read-only, immutable,
or append-only receipt cases, plus force-transaction source/staged-payload
link-count cases and Linux filesystem-flag ioctl failure cases.

```bash
./scripts/project-python -m unittest \
  tests.test_installer_runtime_groups \
  tests.test_installer_agent_profiles \
  tests.test_plugin_packaging \
  tests.test_native_runtime_contract_docs
./scripts/validate-repo.sh
git diff --check
```

The annotated `v0.14.2` tag and GitHub Release must bind the exact reviewed
merge commit after separate human approval. This candidate does not authorize
merge, tag creation, release publication, or deployment.

## Residual Risk And Recovery Boundary

The managed transaction lock serializes cooperating installer processes, and
apply-time identity checks detect ordinary drift. It is not a guarantee against
a hostile non-cooperating process under the same UID changing a path between a
check and rename; that threat requires operating-system or account isolation.
Within supported cooperating use, an existing managed backup is never silently
overwritten. Cooperation requires the same canonical `XDG_STATE_HOME` managed
state namespace; distinct state roots for one custom target have different
locks, and apply-time checks do not make them isolated. Older v0.14.1 state
chains, selected target roots, or installer-managed artifacts made group/world
writable by a permissive `umask` fail closed; the troubleshooting guide provides
a dry-run, exact-path, manually approved `chmod go-w` remediation that neither
recurses through a home directory nor mutates unknown legacy backups.

## Traceability

- Issue: <https://github.com/jeffery777/codex-dev-skills/issues/151>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.14.1...v0.14.2>
