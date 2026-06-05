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

- `~/.codex/skills/<skill>/`
- `~/.codex/templates/...`
- `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it

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
```

`./install.sh install --all` installs every group, including Desktop-only workflows.
Use it only when that broader scope is intentional.

If install fails with an unknown group error, re-run `./install.sh list` and choose one of the listed group names.
If install fails because custom target paths are rejected, remove the custom target override or set `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES` only after confirming the target is narrow and intentional.

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

## Uninstall

Uninstall is destructive because it removes installed Codex skills and templates for the selected group.
It requires `--yes`:

```bash
./install.sh uninstall shared-review-gates --yes
./install.sh uninstall --all --yes
```

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
