# Release Notes: v0.9.0

Release date: 2026-07-21

v0.9.0 ships Loop Engineering V2c-B: optional Codex lifecycle hooks that keep
GitNexus derived-index freshness visible and may, only after separate explicit
opt-in, request an on-demand refresh through the qualified V2c-A controller.
The no-backend path remains the default, and hook output remains advisory data
rather than mutation, approval, review, gate, or completion authority.

## Changes

- Added a bounded hook runner for documented `SessionStart` sources and
  `PostToolUse` `Bash` events. It does not read transcripts or parse shell
  command strings.
- Added clean-HEAD freshness notifications without claiming complete commit
  interception. Codex currently has no native `post-commit` lifecycle event;
  `SessionStart` is the compensation path for changes the Bash hook did not
  observe.
- Kept `notify-only` as the default. `auto-on-demand` is separately configured
  and can refresh only a clean stale or missing index through the existing
  V2c-A `RefreshController` with exact expected HEAD.
- Added strict 64 KiB input/config bounds, duplicate and unknown field
  rejection, absolute path checks, current-user ownership and permissions,
  repository confinement, executable qualification, and fail-closed output.
- Added one fresh `0700` isolated GitNexus home per eligible refresh and a
  repository-bound `0600` circuit-breaker marker after controller failure.
  Later hooks refuse automatic retry until an operator explicitly clears the
  exact marker.
- Added inactive hook and machine-local config templates to the installer
  catalog. Installation does not activate hooks, grant project trust, write
  active configuration, or enable auto refresh.
- Added 27 focused hook tests, including malformed input, unsafe paths, dirty
  worktrees, changed HEAD, controller delegation, circuit breaker behavior,
  template defaults, and a real Git commit boundary.
- Updated the README, usage model, external-memory contract, runtime
  compatibility, release readiness, roadmap, and Loop Engineering references.

## Authority And Compatibility

Project hooks remain opt-in and run only for trusted projects after normal
Codex hook review. Disabled, absent, untrusted, skipped, malformed, timed-out,
unsupported, or failed hooks preserve V1/V2a/V2b/V2c-A correctness and the
no-memory fallback.

Automatic refresh never runs for a dirty, identity-conflicted, corrupt,
incompatible, partial, unknown, or unsafe repository state. The V2c-A
controller remains solely responsible for structured argv, environment
isolation, locks, qualification, repository preconditions, mutation detection,
and metadata postconditions.

The hook runner is qualified for POSIX behavior through local macOS execution
and deterministic fixtures. Windows hook execution is explicitly unsupported
in this release. No live V2c-B auto-on-demand GitNexus refresh was performed;
the unchanged V2c-A live macOS qualification and controller tests remain the
refresh-execution evidence.

## Update From v0.8.1

Review local differences before updating installed skills and templates:

```bash
./install.sh diff --all
./install.sh update --all
```

The installer copies inactive V2c-B examples only. To adopt hooks, review the
templates, materialize machine-local absolute paths outside the repository,
validate the config, inspect any existing project hook file rather than
overwriting it, and review the resulting project hook through `/hooks`.

Restart Codex or begin a new task after installation so changed skills,
references, and templates are rediscovered.

## Verification

The reviewed V2c-B feature baseline completed:

- 680/680 full repository tests;
- 27/27 focused V2c-B hook tests;
- 79/79 unchanged V2c-A adapter/controller tests;
- repository validation with 150 loop, 35 profile/installer, 45 routing, and
  46 external-memory contract tests;
- formal deep code review, documentation review, PR-readiness review, ledger
  remediation gate, and final merge-readiness review with no open findings;
- a valid terminal Issue #103 ledger with 26 replayable events after the
  reviewed feature branch was committed and merged.

Re-run the release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

## Rollback

Disable or remove the materialized V2c-B hook definition to return immediately
to V2c-A or the no-backend path. Do not delete derived indexes, isolated homes,
or circuit-breaker evidence as an implicit rollback action. Inspect exact
machine-local targets and perform any cleanup separately.

Source rollback may reinstall v0.8.1 after reviewing installer differences.
It does not require resetting, restoring, staging, committing, or otherwise
rewriting a repository that may contain user work.

## Traceability

- Feature issue: <https://github.com/jeffery777/codex-dev-skills/issues/103>
- Feature PR: <https://github.com/jeffery777/codex-dev-skills/pull/104>
- Release issue: <https://github.com/jeffery777/codex-dev-skills/issues/105>
- Compare: <https://github.com/jeffery777/codex-dev-skills/compare/v0.8.1...v0.9.0>
