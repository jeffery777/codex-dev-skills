# Release Notes: v0.9.2

Release date: 2026-07-27

v0.9.2 is a runtime-compatibility maintenance release for the V2c-B feature
baseline. It refreshes the independent Codex CLI and Codex Desktop entry
surfaces and adds an opt-in CLI-only bounded session handoff adapter over the
shared delivery layer. It does not implement V2d-A, change completion
authority, or add a scheduler, daemon, app-server client, database, or graph
runtime.

## Runtime Interface Refresh

- Updated public compatibility evidence for Codex CLI 0.145.0 and Desktop
  26.721.30844 without treating either runtime's identifiers as interchangeable.
- Kept shared orchestration, planning, verification, review, completion, and
  human-gate contracts runtime-neutral.
- Retained two active Desktop entry/control-plane adapters and routed three
  historical Desktop gates through deprecated compatibility aliases to shared
  workflows.
- Changed the installer default from `~/.codex/skills` to
  `~/.agents/skills`, retained explicit legacy mode, and added fail-closed
  cross-root collision and uninstall safeguards.

## CLI Session Handoff

- Added the `codex-cli-session-handoff` installer group. It is CLI-only,
  depends on the shared review and delivery groups, and is not installed
  transitively by the shared or Desktop groups.
- Added one versioned, fail-closed adapter for bounded `codex exec` `start`
  and `resume` operations. The adapter uses fixed argv, sends prompts on stdin,
  and accepts only explicit `read-only` or `workspace-write` sandbox ceilings.
- Runs the child in a disposable private clone with its source remote removed.
  Read-only changes are discarded; workspace-write transfers at most one
  bounded patch after the original target identity and clean state are
  rechecked.
- Rejects ambiguous executables and worktrees, unknown or duplicate fields,
  malformed or conflicting JSONL events, noncanonical session IDs, permission
  widening, excessive output, timeout, interruption, child commits, sparse
  checkouts, and submodule indexes.
- Isolates Git identity probes and child execution from ambient repository,
  worktree, index, object-store, namespace, discovery, and injected Git config
  selectors.
- Emits a bounded non-authoritative receipt without raw transcripts, untrusted
  child summaries, credentials, private runtime paths, publication authority,
  or completion claims.

## Installation And Update

Review local differences before updating:

```bash
./install.sh diff --all
./install.sh update --all
```

Install only the CLI session handoff capability and its shared dependencies:

```bash
./install.sh install codex-cli-session-handoff
```

The CLI group does not alter Desktop packaging. `./install.sh install --all`
includes both CLI and Desktop workflow groups but continues to exclude the
explicit opt-in custom-agent profile group.

Restart Codex or begin a new task after installation so changed skills and
templates are rediscovered.

## Verification

The merged feature work completed:

- 702 tests for the runtime-interface refresh candidate;
- 743 tests for the final CLI handoff candidate;
- focused runtime, installer, CLI adapter, and native contract suites;
- repository validation, formal deep review, and merge-readiness review with
  no unresolved findings;
- final CLI handoff security diff scan
  `4166d367-cfbb-426a-af4a-afc83e48c808` with complete coverage and zero
  reportable findings.

Re-run the v0.9.2 release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

The final release-only diff scan and exact-head merge-readiness evidence must
be recorded on the Issue #117 pull request after that pull request exists and
the scan is sealed. This file does not claim that those later gates have
already completed.

## Rollback

Review `./install.sh diff --all` before reinstalling or updating from v0.9.1.
Do not delete, move, or overwrite existing skills, machine-local state, CLI
sessions, Desktop tasks, or unrelated configuration as an implicit rollback.

The CLI handoff adapter is opt-in. Not installing or invoking its dedicated
group preserves the shared and Desktop paths unchanged.

## Traceability

- Runtime-interface issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/113>
- Runtime-interface PR:
  <https://github.com/jeffery777/codex-dev-skills/pull/114>
- CLI handoff issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/115>
- CLI handoff PR:
  <https://github.com/jeffery777/codex-dev-skills/pull/116>
- Release issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/117>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.9.1...v0.9.2>
