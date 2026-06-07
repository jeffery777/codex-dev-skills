# Release Security Evidence: v0.2.0

Date: 2026-06-07

This file records public, release-safe security evidence for the v0.2.0 release candidate. It is not a vulnerability advisory and does not include sensitive exploit detail.

## Scope

The release security review covered:

- repository policy and security guidance;
- README, roadmap, release-readiness, source-classification, and wrapper-plan documentation;
- `catalog.yaml` and `install.sh`;
- Desktop runtime wrapper V1 Python helpers under `scripts/`;
- wrapper helper tests under `tests/`;
- public skills, examples, policies, workflows, and templates.

Primary risk areas reviewed:

- unsafe local installer writes or deletes;
- credential, private-path, local runtime-state, log, session, cache, auth, app-state, or machine-local config leakage;
- Desktop private runtime-state access;
- misleading `ready` evidence;
- uncontrolled platform writes, merge/release claims, or runtime-call authorization claims;
- daemon, MCP server, app-server client, sidecar, background-service, catalog, installer, or new-skill expansion.

## Finding And Remediation

One valid in-scope finding was confirmed and remediated before release:

- The live `create_thread` smoke helper accepted runtime responses that did not explicitly prove no private runtime-state read and no external write before returning `ready`.

Remediation:

- `scripts/desktop_runtime_create_thread_live_smoke.py` now requires runtime responses to include `private_runtime_state_read: false` and `external_write_performed: false`.
- `tests/test_desktop_runtime_create_thread_live_smoke.py` adds regression coverage for missing and non-boolean response flags, including the case where one flag is present and the other is missing.

Suppressed / non-issue areas:

- `install.sh` destructive operations remain explicit local installer actions guarded by static groups, target-root validation, suspicious path rejection, symlink component checks, and `--yes` or `--force` command intent.
- Session compatibility cache reads and writes remain caller-explicit evidence operations and do not replace authorization, target validation, permission handling, or runtime response validation.

## Verification Evidence

Commands run from the repository root:

```bash
python3 --version
python3 -m unittest tests.test_desktop_runtime_create_thread_live_smoke
python3 -B -m unittest discover -s tests
env PYTHONPYCACHEPREFIX=/tmp/codex-dev-skills-pycache python3 -B -m py_compile scripts/*.py
./scripts/validate-repo.sh
git diff --check
```

Observed results:

- `python3 --version`: Python 3.9.6 in this runtime.
- focused live-smoke tests: 25 tests passed after remediation.
- full test suite: 255 tests passed after remediation.
- `py_compile`: passed with `PYTHONPYCACHEPREFIX` set to `/tmp/codex-dev-skills-pycache` to avoid macOS user-cache writes in the sandbox.
- `./scripts/validate-repo.sh`: passed; sensitive-term output was reviewed as policy-only, boundary-only, or regression-test wording.
- `git diff --check`: passed.

## Residual Risk

- The active `python3` command in this environment was Python 3.9.6, while `.python-version` records Python 3.12.9. The available-runtime tests and compile checks passed, but exact pinned-runtime execution was not available through `python3` in this shell.
- The review was source and test based. It did not publish a GitHub Release and did not exercise a real Desktop runtime outside the bounded live smoke helper contract.
- Future broader Desktop runtime integrations, remediation paths, additional live runtime actions, or platform-write paths remain outside v0.2.0 and require separate design, review, and human approval.
