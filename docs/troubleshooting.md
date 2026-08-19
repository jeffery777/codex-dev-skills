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

Both `install` and `update` preflight resolve the active CLI (or an absolute
`CODEX_CLI`) and run the documented `plugin list --json` read-only probe before
target mutation. A missing, unsafe, unreadable, unsupported, or malformed
probe produces a warning and retains the filesystem fallback; it does not prove
that the plugin distribution is absent.

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

Before an `install` or a non-force `update` mutates a selected discovery target,
the installer validates its state and receipt boundary. If that boundary is
unsafe, the command fails before changing the selected skills, templates, or
agent profiles. This preflight guarantee is limited to that boundary failure;
it is not a claim of unconditional atomicity for disk-full, hostile same-UID,
or every other runtime failure.
Regular files in selected target trees and existing receipts must have exactly
one link. A force transaction additionally requires that its sources and staged
payloads have exactly one link. Existing receipts are also opened for append
without writing bytes, using final-symlink protection where the platform
provides it; the opened descriptor identity must still match. A read-only,
immutable, or append-only receipt therefore fails closed before selected-target
mutation. Where the platform exposes file flags, immutable and append-only
flags are rejected directly. On Linux, the installer requires the filesystem
flag ioctl; an error, including an unsupported filesystem or special ABI, fails
closed and is not allowed to degrade to append-open/fstat-only validation.
Other platforms without file-flag support still require the append-open and
descriptor-identity capability check. The installer never repairs a link count,
receipt mode, or file flag automatically.

Use force only after reviewing the diff and confirming the installed local changes can be replaced:

```bash
./install.sh update shared-review-gates --force
```

Risk: update is an external write. With `--force`, the installer backs up the existing target and overwrites installed skills or templates from this repository.

For a forced update, each replaced skill, template, or agent profile is first
placed in a deterministic managed slot below
`${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/`. The slot
is outside `~/.agents/skills` and `~/.codex/skills`. Its exact shape is
`<sha256(canonical-target-root)>/<skills|templates|agent-profiles>/<relative-target>.bak`.
The managed root and backup parents must be current-user-owned, non-symlinked,
and not group/world writable. Newly created managed state-chain directories use
`umask 077`; existing state-chain directories are validated rather than having
their permissions silently changed. The installer rejects a managed root that
overlaps the checkout, a selected target, or either standard skill discovery
root.

Before any target replacement, the installer builds the complete expanded
update, verifies every required slot, validates boundaries and ownership, checks
same-device rename for each backup, and stages each replacement beside its
destination. It refuses the whole update before mutation if any required slot
already exists, a path is unsafe, or a same-device rename cannot be established.
It never silently overwrites a managed backup.
For force updates it acquires the managed transaction lock only after complete
filesystem and profile input preflight; once locked, apply rechecks relevant
identities and backup slots before replacement. This ordering does not provide
hostile same-UID process isolation.

### Fresh And Forced Replacement Permissions

Fresh installs and forced replacements normalize newly installed skill
directories to `0700`, regular files to `0600`, and source-executable files to
`0700`. This applies equally to default, legacy, and explicitly authorized
custom/project targets. It can therefore remove read access for other local
accounts that previously could inspect the target. Existing unsafe target or
state paths fail closed; the installer does not silently use `chmod` to repair
their ownership or mode.

If replacement fails, the installer attempts to restore the original from the
managed slot and rolls earlier replacements back in reverse order. Only a
successful rollback restores the prior complete state. If a restore step also
fails, it emits a `CRITICAL` message that identifies the managed backup
location; preserve the reported target, staged, and backup locations for manual
recovery rather than assuming an atomic or no-partial result.

### Managed Backup Runbook

Start with read-only inspection. Run `./install.sh diff <group>` and retain the
exact `managed backup: PATH` printed by the successful forced update; that path
is the only managed-backup location the installer reports. Inspect the backup,
current target, and repository source before making a decision. A pre-existing
managed slot is a collision disposition, not disposable installer clutter: the
installer intentionally stops and leaves it untouched. Compare it with the
current target and decide whether it is recovery evidence, a previous successful
backup to retain, or a separately approved restoration candidate.

Restore only after an explicit operator decision and after confirming that no
installer transaction is active. Preserve the current replacement by moving it
to a newly created recovery directory outside either skill discovery root; do
not delete it. Then move the exact managed backup back to its original target.
This is a reversible manual move while both locations are retained. Re-run
`./install.sh diff <group>` and inspect both standard skill roots before
resuming work. If any move fails, stop, keep every remaining location, and use
the reported paths for manual recovery.

### Legacy Adjacent Backups

Older installer versions may have left `*.bak` directories immediately under a
skill discovery root. First inventory them without changing anything:

```bash
find ~/.agents/skills ~/.codex/skills -maxdepth 1 -name '*.bak' -print 2>/dev/null
```

Treat every result as potentially user-owned data. This installer does not
automatically delete, move, or adopt legacy backups. For each result, inspect
its type and contents, identify the canonical sibling without the `.bak`
suffix, and compare the two before treating it as an installer backup. If the
canonical sibling or repository source cannot be identified, classify the entry
as unknown and leave it in place.

After an explicit operator decision, a known legacy backup may be moved to an
owner-controlled archive outside both discovery roots; retain the original
relative name and record its source/destination so the move can be reversed.
Do not delete unknown data. After any authorized move, restart Codex or refresh
its skill catalog, then re-run the inventory and inspect the catalog to verify
that the duplicate discovery entry is gone. Do not run a forced update as a
cleanup mechanism.

### Stale Managed Transaction Lock

The exact lock path is
`${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/.transaction.lock`.
If it exists, first confirm that no installer command is active and inspect its
`owner` file for the recorded PID and timestamp. A matching PID alone is not
proof because operating systems can reuse PIDs. Manual removal is an explicit
operator decision only after that check; target only this exact lock directory,
never the backup root or its slots. Afterward, restart with
`./install.sh diff <group>` before attempting an update.

### State-Chain Permissions And Threat Boundary

The transaction lock serializes cooperating installer processes, and apply-time
identity checks detect ordinary path or content drift after staging. This is not
a hostile same-UID isolation boundary: it does not claim to prevent a
non-cooperating process running as the same user from modifying a path in the
narrow interval between a check and a rename. Use operating-system or separate
account isolation for that threat. Within the supported cooperating-installer
model, an existing managed backup slot is never silently overwritten.

Cooperating processes must use the same canonical `XDG_STATE_HOME` and managed
state namespace to share this lock. Different state roots aimed at the same
authorized custom target have distinct locks. Apply-time identity checks may
fail closed on detected drift, but are not process isolation and do not close
the same-UID check/rename race described above.

Older v0.14.1 state directories created under a permissive `umask` can make an
`install` or `update` fail closed before selected-target mutation when the
state chain is group/world writable. Inspect before changing anything:

```bash
STATE_BASE="${XDG_STATE_HOME:-$HOME/.local/state}"
STATE_DIR="$STATE_BASE/codex-dev-skills"
SKILLS_DIR="${CODEX_SKILLS_DIR:-$HOME/.agents/skills}" # selected default target
TEMPLATES_DIR="${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}"
PROFILES_DIR="${CODEX_CUSTOM_AGENTS_DIR:-$HOME/.codex/agents}"
ls -ld "$STATE_BASE" "$STATE_DIR" "$STATE_DIR/backups" "$STATE_DIR/backups/v1"
ls -ld "$SKILLS_DIR" "$TEMPLATES_DIR" "$PROFILES_DIR"
find "$STATE_DIR/backups/v1" -maxdepth 3 -exec ls -ld {} \;
find "$STATE_DIR/backups/v1" -maxdepth 3 -type f -exec file {} \;
```

Also inspect each existing receipt's link count and flags without changing it.
For example, on macOS/BSD, after identifying the exact receipt path from
`./install.sh status`, run:

```bash
stat -f 'path=%N links=%l flags=%Sf mode=%Sp owner=%Su' -- /exact/receipt/path
```

`links` must be `1`. A flags value other than `none` can include immutable or
append-only flags such as `uchg` or `uappnd`. Do not automatically use `unlink`,
`chflags`, or a recursive repair command as an installer workaround. Preserve
the exact path and its inspection output, then obtain an explicit operator
decision for any platform-specific manual remediation; clearing an immutable or
append-only flag is not an installer action and must not be inferred from a
failed update. Do not bypass a Linux filesystem-flag ioctl failure by changing
installer options or falling back to a different receipt check.

For a legacy skills installation, set `SKILLS_DIR` to
`${CODEX_SKILLS_DIR:-$HOME/.codex/skills}` before inspection. For a custom
project target, set all three target variables to the exact values that will be
used for the update. Run `./install.sh diff <group>` first, then inspect only
the selected installer-managed skill directories, template files, and agent
profile files with `ls -ld` and compare their content with the repository
source. Do not infer ownership of neighbouring or unknown artifacts.

Confirm ownership, modes, and content; also confirm that no installer is active
by following the lock procedure above. Only after an explicit operator decision
may you remove group/world write permission from the exact, current-user-owned
installer directories or files that were inspected, for example:

```bash
# Include only roots that exist and were individually inspected.
chmod go-w -- "$STATE_DIR" "$STATE_DIR/backups" "$STATE_DIR/backups/v1"
chmod go-w -- "$SKILLS_DIR" "$TEMPLATES_DIR" "$PROFILES_DIR"
```

Record each exact path and its prior mode before the change so a mistaken
remediation can be manually reversed. Add any affected digest or artifact-kind
directory, selected skill directory, template file, or agent-profile file as an
explicit path only after inspecting it; never use a recursive `chmod`, a
home-directory target, a broader parent, or a wildcard. A legacy
group/world-writable path with confirmed current-user ownership may be repaired
through this manual gate. Stop instead if the owner is unclear, or if a selected
path is a symlink, special file, or otherwise cannot be inspected safely. After
both state and selected target artifacts are safe, re-run
`./install.sh diff <group>` before retrying the forced update.

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
