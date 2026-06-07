# Release Notes: v0.2.0

Release date: 2026-06-07

These release notes summarize the v0.2.0 release candidate. They focus on the completed Desktop runtime wrapper V1 bounded helper path, release-readiness evidence, and the pre-release security scan result.

Release security evidence: [docs/release-security-evidence-v0.2.0.md](release-security-evidence-v0.2.0.md).

## Highlights

- Completed the Desktop runtime wrapper V1 bounded helper path for thread-delegation-oriented workflows.
- Added public guidance that positions the wrapper helpers as reusable workflow evidence, not as an unattended release or runtime automation layer.
- Added adoption examples for a global Codex profile, project-level `AGENTS.md` overlay, and project workflow overlay.
- Kept later Desktop runtime integration, broader remediation paths, platform writes, and additional live runtime actions outside the v0.2.0 release scope unless separately approved.

## Wrapper V1 Scope

The v0.2.0 wrapper milestone includes helpers for:

- caller-supplied capability metadata normalization;
- runtime contract comparison;
- planner, create-thread preflight, and read-thread preflight evidence;
- session compatibility status, handshake, and same-session cache evidence;
- create-thread authorization, executor boundary, executor shell, callable executor, callable wiring, callable bundle, and single live smoke boundaries.

The live smoke path remains limited to one caller-injected documented `create_thread` callable after exact human approval and call-site validation. CLI/default and tests remain non-live unless a caller supplies the documented callable path required by the helper.

## Security Scan Summary

Pre-release repository-wide security scanning reviewed the public workflow, installer, documentation, examples, Python helper, and test surfaces for unsafe edits, credential exposure, destructive operations, local runtime-state leakage, and misleading runtime or merge-readiness claims.

Result: one valid in-scope security finding was confirmed and remediated before release.

Reviewed risk areas included:

- installer copy, update, diff, and uninstall path handling;
- catalog and installer source alignment;
- caller-supplied Desktop capability and compatibility evidence handling;
- same-session cache evidence read/write boundaries;
- live smoke runtime-call boundary wording and tests;
- public documentation claims about Desktop private runtime state, platform writes, and human gates.

Remediation summary:

- The live `create_thread` smoke helper now requires runtime responses to explicitly report `private_runtime_state_read: false` and `external_write_performed: false` before returning `ready`.
- Regression tests cover missing and non-boolean runtime response flags so evidence cannot silently default to safe values after a live smoke call.

## Safety And Compatibility

- No Desktop private runtime state, local application state, logs, sessions, caches, SQLite databases, credentials, or machine-local config are part of the release scope.
- No daemon, MCP server, app-server client, sidecar, background service, new skill, catalog entry, or installer entry is added by the wrapper V1 helpers.
- `ready` statuses remain evidence-scoped and do not imply commit, push, PR creation, platform comments, reviews, merge, release publication, deployment, or additional runtime-call authorization.
- Future broader runtime integration, remediation workflow expansion, or platform-write path remains a separate human-approved project slice.

## Verification

Run from the repository root:

```bash
python3 --version
python3 -B -m unittest discover -s tests
python3 -B -m py_compile scripts/*.py
./scripts/validate-repo.sh
git diff --check
```

Also run a scoped wording and symbol search before tagging to confirm the release notes or documentation did not introduce private runtime-state references, uncontrolled platform-write claims, or unsupported daemon/app-server/sidecar/background-service claims.

## Residual Risk

- The security scan was source and test based; it did not publish a GitHub Release and did not exercise a real Desktop runtime outside the already bounded live smoke helper contract.
- The installer remains a local filesystem installer and can remove installed skills/templates only through explicit uninstall or forced update flows; maintainers should continue previewing diffs before force updates.
- The wrapper V1 milestone documents and tests boundaries for a narrow helper path. It does not validate future runtime integrations that have not been separately designed, reviewed, and approved.
