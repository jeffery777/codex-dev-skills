# Issue #103 Verification Report

Date: 2026-07-21

Branch: `codex/issue-103-v2c-b-hooks`

Base HEAD: `012d1de0148362468c3861fff65883577c58be01`

## Final Results

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook`
  - PASS, 27/27.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter`
  - PASS, 79/79.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_native_runtime_contract_docs`
  - PASS, 8/8.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_memory_contract tests.test_memoryctl`
  - PASS, 43/43.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests`
  - PASS, 680/680 in 107.737 seconds.
- `./scripts/validate-repo.sh`
  - PASS.
  - Loop engineering contracts: 150/150.
  - Agent profile/installer contracts: 35/35.
  - Agent routing contracts: 45/45.
  - External memory contracts: 46/46.
- `bash -n install.sh`
  - PASS.
- JSON template parsing with `python3 -m json.tool`
  - PASS for both V2c-B templates.
- `git diff --check`
  - PASS.

## Covered Behavior

- Strict bounded hook/config JSON, duplicate-key rejection, unknown-field
  rejection, NUL/path, ownership, permissions, and repository confinement.
- `SessionStart` and `PostToolUse` `Bash` event validation and output shapes.
- Fresh silence, stale/corrupt notifications, ordinary dirty-tree noise
  suppression, and changed-HEAD compensation behavior.
- Notify-only default and dirty/unsafe states never reaching refresh.
- Auto-on-demand delegation only to V2c-A `RefreshController` with explicit
  opt-in and expected HEAD.
- Fresh per-refresh `0700` isolated homes under a secure machine-local parent.
- Durable `0600` repository-bound circuit breaker after controller failure and
  no automatic retry until operator clearance.
- Real Git boundary integration proving that a clean commit makes prior metadata
  stale without parsing the Bash command.
- Installer/catalog parity and inert template installation.

## Verification Limits

- No active Codex project hook was installed or trusted during repository tests.
- No live auto-on-demand GitNexus refresh was performed in this slice; the
  unchanged V2c-A live macOS qualification and 79 controller tests remain the
  refresh execution evidence.
- POSIX behavior is qualified by local macOS execution and fixtures. Windows is
  explicitly unsupported by the hook runner in this increment.
