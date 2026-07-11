# Release Notes: v0.6.1

Release date: 2026-07-11

v0.6.1 is a compatibility patch for the Loop Engineering V2a custom-agent
profiles published in v0.6.0. It aligns the balanced worker, deep reviewer, and
security reviewer runtime templates with the `gpt-5.6-sol` model ID reported by
the current Codex Desktop runtime while preserving exact-ID validation,
replaceable runtime mappings, and safe degradation.

## Changes

- Changed the three deep-capability profile templates from `gpt-5.6` to
  `gpt-5.6-sol`.
- Kept the read-heavy fast explorer mapped to `gpt-5.6-terra`.
- Regenerated the canonical profile digests so deployed configuration remains
  bound to reviewed repository sources.
- Added regression coverage proving that `gpt-5.6` is not silently treated as
  an alias for `gpt-5.6-sol`.
- Kept capability classes, sandbox expectations, permissions, workflow scope,
  receipt contracts, fallback order, human gates, and completion criteria
  unchanged.

## Runtime Evidence And Limitations

The active Codex Desktop task schema verified on 2026-07-11 reports
`gpt-5.6-sol`, `gpt-5.6-terra`, and `gpt-5.6-luna`, along with other supported
model IDs. The V2a profiles reference only the exact models required by their
reviewed role mappings; the shared workflow does not treat this list as a
permanent model catalog.

Model and reasoning availability remain runtime capabilities. Each host must
provide current-session runtime facts and pass preflight before a profile is
selected. An unavailable exact mapping follows the same-class, parent/default,
sequential, and human-gate fallback contract instead of assuming an alias.

## Update From v0.6.0

Review local differences before updating existing skills:

```bash
./install.sh diff --all
./install.sh update --all
```

For a first-time user-level adoption, install the opt-in custom-agent profiles
only after all four roles pass current-runtime preflight:

```bash
./install.sh diff codex-agent-profiles
./install.sh install codex-agent-profiles
```

To update profiles already installed from v0.6.0, preflight all four roles
against the same selected destination, review local differences, and then use
the explicit forced update path:

```bash
./install.sh diff codex-agent-profiles
./install.sh update codex-agent-profiles --force
```

Without `--force`, any differing installed profile stops the update. With
`--force`, each differing profile is copied to an adjacent
`<profile>.toml.bak` before replacement; an existing required backup path stops
the whole group before mutation. Preserve and reconcile local profiles and
backups instead of deleting or overwriting them blindly.

For a trusted project-scoped install or update, pass the same exact project
agents path as profile preflight's `--destination-root`, then set the documented
`CODEX_CUSTOM_AGENTS_DIR` and `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`
variables to that path for installer diff and mutation. The profile group
remains excluded from `--all`.

Restart Codex or begin a new task after installation so the changed skills and
profiles are discovered.

## Verification

Run from the repository root:

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-agent-routing.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

Release preparation must rerun runtime-profile preflight with current public
runtime facts, full repository verification, the security diff scan, formal
review, and release-readiness gates against the exact v0.6.1 candidate.

## Rollback

Use installer diff before update or uninstall. Installer backup and modified
destination refusal remain authoritative; do not overwrite locally modified
profiles. Removing the V2a profiles leaves Loop Engineering V1 shared and
sequential semantics available.

This release does not add model aliasing, V2b external memory, V2c memory
backends, private Desktop integration, or any new permission or external-write
authority.
