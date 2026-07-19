# P5 Executable-Boundary Security Fix

Status: **fixed and locally verified; defensive and deep-code re-reviews passed, final docs gate and immutable rescan pending**.

The final defensive discovery/validation cycle found two local executable-origin
control gaps in the frozen working-tree snapshot:

- ambient `PATH` could select the Git TCB before repository identity probes;
- omitting the GitNexus executable allowed a PATH-selected program to
  self-report version/flags, and an env-node entry selected its interpreter from
  PATH.

Attack-path policy suppressed both from vulnerability reporting because the
repository establishes only a local developer/operator workflow and no
realistic lower-privileged attacker path or privilege delta. Engineering
disposition remained MUST-FIX because the V2c-A executable boundary is
fail-closed.

Round-11 formal review expanded the engineering finding into four concrete
boundaries: child-process environment selectors, production propagation of an
explicit Git executable, parent/multi-hop symlink rejection, and alternate
`/usr/bin/env -S node` launch syntax. The fix now makes production Git probes
use a locale-only allowlist plus fixed Git controls, ignoring ambient `PATH`,
`DEVELOPER_DIR`, loader selectors, and executable-path environment variables.
The operator/library `git_executable` value is propagated through repository
identity, complete snapshot, Git-control, and refresh paths. Omitting it uses
only the operating-system default search path. GitNexus qualification requires
an explicit absolute CLI path; exact `/usr/bin/env node` and
`/usr/bin/env -S node` entries additionally require an explicit Node path.
Git, CLI, and Node parent/multi-hop symlink paths fail closed; each permitted
single final CLI/Node symlink policy remains fingerprint-bound. Every accepted
GitNexus script entry now has a bound, fingerprinted native interpreter; Git
script wrappers and unsupported launcher forms fail closed. Machine-local path
values are not persisted.

Round-12 security review added two adjacent execution boundaries. Before any
worktree-reading Git operation, the adapter rejects `filter.*`, `include.path`,
`includeIf.*.path`, and `core.attributesFile` from local configuration and from
enabled worktree configuration. This stops repository-controlled clean/process
filters and external attributes/includes before the snapshot or refresh child.
The machine-local refresh lock is opened and checked by descriptor, locked with
cross-process `flock`, and rechecked after acquisition; unsafe parent paths,
symlinked files, hard-linked files, shared-writable directories, and ownership
mismatch fail closed. This is a cooperation boundary for local same-UID
processes, not a distributed lock or protection against a malicious same-UID
control-plane writer.
The canonical repository root always takes a deterministic fixed-OS-temp
per-user lock before an optional configured-directory lock. Separate processes
cannot bypass serialization with different temp selectors or lock directories;
the child-process regression also proves reacquisition after release.

Verification:

- five new tests produced four failures and one error before the fix;
- focused executable, source-rebound, repository-config, lock, and legitimate
  control regressions: 153/153 pass;
- repository full suite: 626/626 pass in 100.166 seconds;
- current V2b contract suites: 46/46 pass;
- mandatory conformance oracle: 31/31 pass, all rates `1.0`, false
  authority/completion `0`;
- original harmless ambient-Git fixture now reports `selected_fake=false`;
- original harmless GitNexus self-qualification fixture is rejected before
  execution with `explicit GitNexus executable path is required`;
- `git diff --check` passes.

Round-14 defensive security re-review passed with MF/SF/NIT all zero and
composite code/test digest
`957b6b09016939446b3ea1e866073ecf3f2bf0c5489b2bd25b0ed8c1cc5eadde`.
The final docs gate and immutable Security Diff Scan remain required.

No external target, credential, real index, repository reset, staging, commit,
or push was used for the validation or fix.
