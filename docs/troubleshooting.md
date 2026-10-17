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
ordinary filesystem diff tools. An identical managed target with a matching
inventory supports idempotent install; `install` never overwrites different content.
Unknown/imported files are not adopted even when identical. `--force` does not
permit overwriting local edits. See [fixed-source ownership limits](installer-source-integrity.md).

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

`diff` performs read-only target validation and comparison. Existing, partially
missing and entirely missing targets are inspected without creating skills,
templates, agent profiles, state, backups or locks, including on error exits.
Missing installed artifacts are reported as `missing installed`; content
differences are reported by `diff`. A missing repository source produces a
source-path error from `diff` when the installed artifact exists. If both are
missing, the installed artifact is reported missing first. None of these results
proves that a runtime's native tools are available or unavailable.
Custom-target opt-in and symlink/path checks still apply to inspection. Read
permission errors remain errors; comparison does not repair permissions.

### Linux UID Namespaces

Install/update ownership failures report the visible owner UID, current UID
and mode when an ancestor has an untrusted owner. On Linux they also report
`/proc/self/uid_map` (inside UID, outside UID, range length) and the kernel's
overflow UID when readable. Mapping output is bounded to complete rows within
4096 bytes; a truncated diagnostic explicitly directs you to read the full
mapping in that namespace. These values describe the current namespace;
the outside column need not identify the ultimate host in nested namespaces.
An overflow UID can represent an unmapped owner or a real account. It cannot
prove that the directory is owned by host root, and is never trusted merely
because it equals `65534`.

Compare these read-only commands in the failing namespace and a trusted host
shell, substituting the exact ancestor named by the error:

```bash
id -u
stat -c '%u:%g %a %n' /home
cat /proc/self/uid_map
cat /proc/sys/kernel/overflowuid
```

If mapping prevents ownership verification, perform an already-authorized
installation from the verified host context using its normal permissions.
Do not `chmod` or `chown` host ancestors to compensate for UID mapping. Missing
or unreadable mapping information does not relax the refusal. Symlinks,
foreign owners, unsafe writable ancestors, target identity, backup and rollback
checks remain in force for mutations. `diff` needs read access and safe paths,
not mutation ownership; use it to distinguish installation drift from this
write-preflight limitation.

## Update

更新與回復的雙語規範見 [固定來源安裝與回復](installer-source-integrity.md)。
只有具 canonical target inventory 的管理檔可以替換。舊 metadata-only receipt 不會自動
遷移；`--previous-source` 會停止。自訂／unknown／unmanaged 檔即使同 bytes 或使用
`--force`，也不會被認領、覆寫或刪除。

See [fixed-source installation and recovery](installer-source-integrity.md) for the
bilingual contract. The current installer consumes the selected supported local Git
payload. It does not execute old source code. Before any replacement it checks the
complete old inventory, fixed new payload, state/receipts, paths and identities.

```bash
./install.sh update --all --source /trusted/fixed-checkout
```

A cross-version update/downgrade must explicitly select every managed group. A narrower
request stops. `--all` does not newly install opt-in profiles; already-managed profiles
remain part of the complete version replacement. Custom bytes, extra/missing files,
links and unsafe owner/mode stop. `--force` does not waive ownership or integrity checks.

All install/update paths use the same transaction and lock. Staging and temporary
originals stay in owner-safe state outside known discovery roots and selected targets,
including canonical/direct-entry aliases. A cross-filesystem rename stops. New files
and retired files participate in the same transaction. Full payload, retired-file
absence, Core and inventory-receipt readback precede success.

Regular target files, sources, staged payloads and receipts must have one link. Receipts
undergo no-write append-open and descriptor checks; read-only/immutable/append-only
receipts stop. Linux also requires successful filesystem flag inspection. The installer
does not repair permissions, ownership, links or flags.

Fresh payloads use 0700 directories, 0600 files and 0700 source-executable files.
After a complete transaction, verified reconstructible originals need no permanent
whole-package backup. An optional fixed-source cache can support offline recovery;
future source availability is not guaranteed. Historical backups remain untouched.

On ordinary failure, the existing reverse rollback restores originals where possible.
A failed restore reports nonzero and `CRITICAL`, retaining exact recovery paths.
Preserve those paths and inspect the full state before manual recovery. Cleanup/unlock
failure after commit also returns nonzero and reports pending work. A history row or
receipt alone never proves that the full payload is usable.

### Historical Managed Backups

Older installers used deterministic slots under
`${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/`.
This installer does not delete or reuse those historical slots. Inspect their provenance,
bytes and original target mapping before an operator decides any recovery action.
Do not delete unknown backups or treat a lock/PID alone as proof that no installer runs.
For a failed current transaction, use only its reported recovery locations.

### Legacy Adjacent Backups

Older installers may have left `*.bak` entries inside skill discovery roots.
This installer does not move, delete or adopt them. Inventory and inspect them first.
Any relocation or cleanup requires a separate exact operator decision and a verified
recovery destination outside discovery. Do not use force-update as a cleanup command.

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
