# Issue #115 Verification Report

Last verified: 2026-07-27

Status: post-remediation implementation verification and formal review pass.
A fresh security diff scan of this exact working-tree snapshot is still
pending before commit or PR readiness.

## Candidate Scope

The candidate adds one macOS/Linux-qualified Codex CLI session adapter, its skill,
offline fake-executable tests, runtime-layer documentation, installer/catalog
routing, and Issue #115 planning and review evidence.

The current verification did not create a live CLI session, call Desktop task
tools, implement an app-server client, publish repository changes, or treat
child output as completion evidence.

## Results

| Check | Result |
| --- | --- |
| Full unit suite | Pass: 743 tests in 151.265 seconds |
| Repository validation | Pass |
| Native CLI/Desktop runtime contract stage | Pass: 47 tests |
| Loop engineering contract stage | Pass: 150 tests |
| CLI adapter focused suite | Pass: 32 tests in 34.169 seconds |
| Detached-descendant timeout stability | Pass: 10 additional consecutive runs |
| Runtime-group isolated installer suite | Pass: selected-group uninstall preserves dependencies; direct dependency removal refuses installed dependents; inherited custom targets remain untouched |
| Minimal live Codex CLI start | Historical pre-remediation pass on Codex CLI 0.145.0: exit 0, `turn.completed`, valid public session UUID; not rerun after private-clone changes |
| `git diff --check` | Pass |
| Deep code review | Pass: the post-ambient-Git-remediation formal gate found no open MUST-FIX, SHOULD-FIX, NIT, or question |
| Documentation review | Pass after request-authorization and stdin examples were corrected |
| Security diff scan | Pending for the current snapshot. Historical scan `d36bc891-0b28-4fd9-b019-ec6840be1def` completed with 0 reportable findings, but reproduced the now-fixed ambient Git target-identity defect and cannot serve as final evidence. |

## Residual Coverage

- One previously authorized minimal `codex exec` start was run against a clean
  temporary clone in read-only mode before the isolation remediation. Start,
  resume, private-clone isolation, bounded patch integration, version-probe
  cleanup, and process-identity checks are covered by offline contract tests;
  no post-remediation live session was created.
- macOS is covered by the current 743-test suite and repeated lifecycle
  regression. Linux behavior is exercised by platform-specific code paths in
  offline tests where possible but was not run on a live Linux host. Other
  hosts still receive a capability fallback.
- Offline fakes validate the documented JSONL contract but cannot prove a
  future Codex CLI release has not changed its behavior.
- The final post-ambient-Git-remediation security diff scan has not yet run.
- No commit, push, pull request, merge, release, or external platform write was
  performed.

See `live-cli-smoke.md` for the sanitized live evidence and environment
limitation.
