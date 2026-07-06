# Release Notes: v0.2.2

Release date: 2026-07-06

These release notes summarize the v0.2.2 patch release candidate. This release refreshes the skill pack for current Codex CLI and Codex Desktop skill discovery, metadata, installer, and documentation behavior while preserving existing installer defaults.

## Highlights

- Added explicit `name` front matter to every checked-in `skills/*/SKILL.md`.
- Extended repository validation so missing skill metadata, mismatched skill directory/name values, and installer target drift fail repository hygiene.
- Preserved the existing `~/.codex/skills` installer target by default, with explicit opt-in support for `CODEX_DEV_SKILLS_TARGET=agents` to install user skills under `~/.agents/skills`.
- Updated the installer state version to `0.2.2` and added repository validation to keep it aligned with the current release notes version.
- Documented plugin packaging as a deliberate follow-up instead of adding a second distribution path in this patch release.
- Updated documentation language for current Codex instruction layering and runtime configuration boundaries.

## Skill Metadata Compatibility

Codex skills now include both required front matter fields:

- `name`
- `description`

The validation script checks every checked-in `skills/*/SKILL.md` for:

- a non-empty `name`;
- a non-empty `description`;
- a `name` value that matches the skill directory name;
- an accepted runtime compatibility label.

## Installer Compatibility

The installer keeps the legacy target as the default:

```bash
~/.codex/skills/<skill>/
```

To opt in to the current Codex user-skill discovery location, set:

```bash
CODEX_DEV_SKILLS_TARGET=agents
```

That mode installs skills under:

```bash
~/.agents/skills/<skill>/
```

The installer intentionally does not auto-migrate or dual-write skill targets. Use only one skills target per Codex profile for this pack, because duplicate skill names in both locations, or later through a plugin package, can appear as duplicate skills in selectors.

Installer state records now use version `0.2.2` for this release candidate. Repository validation checks that `install.sh VERSION` matches the current release notes version referenced from the README.

## Plugin Packaging Decision

This release does not add `.codex-plugin/plugin.json` or a repo marketplace entry.

Plugin packaging remains a follow-up because adding a plugin package in the same patch as filesystem installer migration would introduce a second distribution path and duplicate-skill risk. If maintainers later want plugin distribution, add the plugin manifest and marketplace entry in a separate reviewed slice and document how it relates to the filesystem installer.

## Documentation Alignment

Documentation now reflects current Codex terminology and boundaries for:

- `AGENTS.md` and `AGENTS.override.md` instruction layering;
- `.rules` files as command permission policy, not workflow policy;
- permission profiles and runtime configuration;
- `codex exec` default read-only automation posture;
- web search and MCP setup as runtime settings rather than behavior changed by installing this pack.

Desktop runtime claims remain conservative. This release does not add a live Desktop runtime adapter, app-server client, daemon, sidecar, UI scraper, MCP server, or Desktop private runtime-state reader.

## Verification

Run from the repository root:

```bash
./scripts/validate-repo.sh
git diff --check
bash -n install.sh
bash -n scripts/validate-repo.sh
```

Verification used for the v0.2.2 candidate:

- `./scripts/validate-repo.sh` passed.
- `git diff --check` passed with no output.
- `bash -n install.sh` passed.
- `bash -n scripts/validate-repo.sh` passed.
- Official Codex documentation was rechecked for skills, plugins, `AGENTS.md`, `.rules`, permissions, non-interactive mode, and app-server terminology.

## Residual Risk

- The release keeps `~/.codex/skills` as the default installer target to avoid disrupting existing users; users who expect current user-skill discovery under `~/.agents/skills` must opt in with `CODEX_DEV_SKILLS_TARGET=agents`.
- Plugin packaging is intentionally deferred, so users who want plugin distribution need a later package/marketplace slice.
- GitHub has no configured status checks for these PR heads; release confidence relies on local verification and formal review evidence.
