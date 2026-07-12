# Release Notes: v0.7.0

Release date: 2026-07-12

v0.7.0 adds cost-aware custom-agent routing to Loop Engineering V2a. The route
keeps workflow authority separate from model cost: capability class continues
to control sandbox and allowed work, while a new ordered tier selects the
lowest verified Luna, Terra, or Sol profile sufficient for the task.

This is an independently usable release. It does not require a V2c external
memory or code-intelligence adapter, and disabled or unavailable external
memory leaves V1 and V2a behavior unchanged.

## Changes

- Added route contract version 2 with an explicit workload kind and separate
  `mechanical`, `efficient`, `everyday`, `advanced`, `deep`, and `exceptional`
  capability tiers. Version 1 route inputs remain supported.
- Added a Luna-low mechanical reader for clear, repeatable read-only work.
- Kept Terra-low exploration read-only and mapped routine bounded
  implementation to Terra medium.
- Added a Sol-medium advanced worker for difficult but bounded implementation.
- Kept deep and security review on Sol high, with read-only sandboxes and no
  authority to edit, publish, merge, deploy, or claim completion.
- Added a narrowly selected, read-only Sol-xhigh exceptional researcher.
  Exceptional routing requires multiple documented quality-first triggers; it
  is not the default for ordinary multi-step work.
- Made routing select the lowest sufficient same-class tier, record higher-tier
  cost degradation, and reject silent substitution by an insufficient tier.
- Bound all installable agent profiles to the canonical reviewed registry and
  fail closed on malformed registry data or mismatched profile content.
- Tightened the security-reviewer profile around defensive, local-first
  validation using static analysis, local fixtures, negative tests, synthetic
  inputs, and other non-invasive checks.
- Expanded profile, routing, preflight, loop-control, and deterministic eval
  coverage for the new tier contract and fallback behavior.

## Authority And Compatibility

Model and reasoning availability remain current-session runtime evidence.
Profiles do not grant new permission, mutation authority, external-write
authority, or completion authority. The parent agent still owns integration,
verification, review, human gates, and completion.

The fallback order remains fail-safe: use the lowest-cost sufficient profile in
the same class, then a proven-sufficient parent/default model, then proven-
sufficient sequential execution, and finally a human gate when higher-risk work
cannot degrade safely. Unknown availability never counts as completion
evidence.

V1 routing remains compatible. V2b remains backend-neutral and useful with no
backend; external memory cannot become instruction, authorize an action,
satisfy a gate, or prove completion. V2c adapter work is reserved for a future
v0.8.0 release.

## Update From v0.6.1

Review local differences before updating existing skills:

```bash
./install.sh diff --all
./install.sh update --all
```

The custom-agent profile group remains opt-in and excluded from `--all`. Before
installing or updating it, preflight every intended role against current
runtime facts and the exact destination. For a first-time user-level install:

```bash
./install.sh diff codex-agent-profiles
./install.sh install codex-agent-profiles
```

For profiles already installed from an earlier release, review differences and
use the explicit forced update path only after preflight succeeds:

```bash
./install.sh diff codex-agent-profiles
./install.sh update codex-agent-profiles --force
```

Without `--force`, a differing installed profile stops the update. With
`--force`, each differing profile is copied to an adjacent
`<profile>.toml.bak` before replacement; an existing required backup path stops
the whole group before mutation. Preserve and reconcile local profiles and
backups instead of deleting or overwriting them blindly.

For a trusted project-scoped install or update, use the documented
`CODEX_CUSTOM_AGENTS_DIR` and `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`
boundary with the same destination used by profile preflight. This release does
not modify `~/.codex/config.toml` or install global profiles automatically.

Restart Codex or begin a new task after installation so changed skills and
profiles are discovered.

## Verification

The release candidate was checked with the repository's syntax, profile,
routing, deterministic eval, unit-test, catalog, installer, public-hygiene,
documentation-review, deep-review, and release-readiness gates.

Re-run the local verification from the repository root:

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

The feature baseline from issue #93 and PR #94 also completed a defensive,
local-only security diff scan with no reportable findings. The v0.7.0 release
slice changes only version metadata and release documentation; it does not
change installer execution, routing logic, permissions, or external behavior.

## Rollback

Inspect installer differences before update or uninstall. Installer backup and
modified-destination refusal remain authoritative; do not overwrite locally
modified profiles. Removing the V2a profiles leaves Loop Engineering V1 shared
and sequential semantics available. With external memory disabled or absent,
the repository-owned workflow remains authoritative.

This release does not add a V2c adapter, automatically change machine-local
configuration, publish private runtime state, widen security validation into
external systems, or grant new deployment or publication authority.

Compare: https://github.com/jeffery777/codex-dev-skills/compare/v0.6.1...v0.7.0
