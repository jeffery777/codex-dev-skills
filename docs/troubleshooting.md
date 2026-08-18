# Installer Troubleshooting

This guide covers low-risk troubleshooting for the Codex-only installer.
It only uses commands supported by `install.sh` and aligned with README installer guidance.

## Start With Inspection

Before changing installed files, inspect the available groups and current state:

```bash
./install.sh list
./install.sh status
```

`status` prints the configured skills target, templates target, and recent installer state.
If no state has been recorded yet, that does not prove nothing is installed; it only means the installer has no recorded history in its state file.

Installer writes normally target:

- `~/.agents/skills/<skill>/` by default
- `~/.codex/skills/<skill>/` when `CODEX_DEV_SKILLS_TARGET=legacy` is set explicitly
- `~/.codex/templates/...`
- `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it

Use one skills target per Codex profile for this pack. Before install or update, the installer refuses skill-name collisions between `~/.agents/skills` and `~/.codex/skills`. It never moves or deletes an existing installation automatically. Use `./install.sh status` to inspect cross-target collisions; use `CODEX_DEV_SKILLS_TARGET=legacy` when intentionally maintaining an existing legacy installation.

The universal `codex-dev-skills` plugin is a separate distribution path. Check
it with `codex plugin list --json`. Do not keep the plugin active beside a
filesystem installation of the same skills.

Custom `CODEX_SKILLS_DIR` or `CODEX_TEMPLATES_DIR` values require `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`.

## Install

Use `list` first when the group name is uncertain:

```bash
./install.sh list
```

Install one group at a time when you want the smallest write:

```bash
./install.sh install shared-review-gates
./install.sh install codex-review-workflow
./install.sh install codex-delivery-workflow
./install.sh install codex-cli-session-handoff
```

`./install.sh install --all` installs every group, including Desktop-only workflows.
Use it only when that broader scope is intentional.

If install fails with an unknown group error, re-run `./install.sh list` and choose one of the listed group names.
If an existing installation is intentionally maintained under `~/.codex/skills`, re-run the intended command with `CODEX_DEV_SKILLS_TARGET=legacy` instead of creating a duplicate under the default target.
If install fails because custom target paths are rejected, remove the custom target override or set `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES` only after confirming the target is narrow and intentional.

If install reports that the `codex-dev-skills` plugin is installed, choose one
distribution path. Remove the plugin through the normal Codex plugin control
plane before installing files, or keep the plugin and do not run this
installer. The installer does not mutate plugin state.

If install reports a differing existing or imported artifact, inspect it with
ordinary filesystem diff tools. A byte-identical target is accepted as an
idempotent install; different content is never overwritten by `install`.
Only use `update --force` after establishing that the target is a managed
filesystem installation and reviewing its backup behavior.

When the active CLI is missing or too old for `codex plugin list --json`, the
installer warns and retains the filesystem fallback. This warning does not
prove that no plugin or imported copy exists; review the Desktop Plugins tab,
CLI `/plugins`, and both standard skill roots.

Risk: install is an external write. It copies skills and templates into the configured Codex target directories and records installer state.

## Diff

Use `diff` before update when you need to see whether installed files differ from this repository:

```bash
./install.sh diff shared-review-gates
./install.sh diff --all
```

`./install.sh diff --all` checks every group, including Desktop-only workflows.
Use a single-group diff first when you are trying to understand one workflow area.

If diff reports a missing installed skill or template, install or update the relevant group instead of forcing a broad update.
If diff reports local differences, review the output before running any update command.

Risk: diff is intended as inspection, but the installer initializes target directories before commands that inspect installed files.
Avoid custom target overrides unless the target directory has already been confirmed.

## Update

Update one group when you want the smallest write:

```bash
./install.sh update shared-review-gates
./install.sh update codex-review-workflow
./install.sh update codex-delivery-workflow
./install.sh update codex-cli-session-handoff
```

`./install.sh update --all` updates every group, including Desktop-only workflows.
Use it only when that broader scope is intentional.

When installed files have local modifications, update prints a warning and does not overwrite them by default.
Review `./install.sh diff <group>` before deciding whether to force the update.

Use force only after reviewing the diff and confirming the installed local changes can be replaced:

```bash
./install.sh update shared-review-gates --force
```

Risk: update is an external write. With `--force`, the installer backs up the existing target and overwrites installed skills or templates from this repository.

Update also refuses when the universal plugin is installed. Updating one
distribution path while leaving the other active would recreate the duplicate
discovery condition even if their current bytes match.

## CLI Session Handoff

Inspect the non-live example first:

```bash
python3 skills/cli-session-handoff/scripts/cli_session_handoff.py --example
```

This prints a request shape and performs no Codex runtime call. A real
`--request` start or resume creates or mutates CLI session state and requires
explicit authority for the exact executable, workspace, expected HEAD,
sandbox, prompt, and session UUID when resuming.

Common fail-closed results:

- `capability_unavailable`: the absolute executable is missing, unsafe,
  repository-controlled, or does not identify a documented Codex CLI.
- `target_mismatch` or `dirty_workspace`: the canonical Git root, exact HEAD,
  or clean-worktree precondition failed.
- `authorization_missing` or `permission_widening`: the one-session marker or
  sandbox ceiling is insufficient.
- `prompt_boundary_missing`: the request does not select the supported
  canonical boundary appendix that prohibits commit, push, PR, merge, platform
  writes, and nested session dispatch.
- `timeout`, `output_limit`, or `malformed_jsonl`: the child did not stay
  within the bounded public CLI contract.
- `isolation_error` or `integration_error`: the disposable private clone could
  not be prepared or cleaned, or its bounded patch could not be applied to the
  still-clean authorized worktree.
- `child_boundary_violation`: the child changed Git HEAD despite the fixed
  no-commit boundary; no child patch is integrated.
- `capability_unavailable` for sparse checkout or submodules: those worktree
  shapes are not yet qualified for private-clone handoff and require a manual
  continuation or separately reviewed workflow.

Do not fix these failures by adding arbitrary CLI flags, reading private
session files, using `--last`, widening to `danger-full-access`, or starting an
app-server/remote-control daemon. Revalidate the target and prepare a manual
continuation prompt when the safe adapter path is unavailable.

## Uninstall

Uninstall is destructive because it removes installed Codex skills and templates for the selected group.
It requires `--yes`:

```bash
./install.sh uninstall shared-review-gates --yes
./install.sh uninstall --all --yes
```

Use the same target mode that was used for installation. For a legacy installation, prefix uninstall with `CODEX_DEV_SKILLS_TARGET=legacy`. The installer refuses a mismatched target and will not remove shared templates while dependent skills remain in the alternate standard discovery root.

Use a single-group uninstall when possible.
`./install.sh uninstall --all --yes` removes every installed group target managed by this installer, including Desktop-only workflows.

Before uninstalling, run:

```bash
./install.sh status
./install.sh diff shared-review-gates
```

Replace `shared-review-gates` with the exact group you plan to uninstall.
If the diff shows local modifications, preserve them outside the installed target before uninstalling.

Risk: uninstall is destructive and an external write. It removes installed Codex skill directories and template files for the selected group and records installer state.

## Safe Recovery Pattern

For most installer issues, use this order:

1. Inspect groups with `./install.sh list`.
2. Inspect state with `./install.sh status`.
3. Inspect local differences with `./install.sh diff <group>`.
4. Run the smallest matching `install`, `update`, or `uninstall` command.
5. Use `--all`, `--force`, or `--yes` only after confirming the target and risk.
