# Release Notes: v0.2.1

Release date: 2026-06-12

These release notes summarize the v0.2.1 patch release candidate. This release primarily updates the skill pack for current Codex API and Codex Desktop contract drift, while preserving the existing Desktop runtime wrapper V1 safety boundary.

## Highlights

- Updated Desktop runtime wrapper V1 documentation, fixtures, and tests for current Codex Desktop app tool contracts.
- Recorded current Codex app-server JSON-RPC and Codex SDK boundaries so they are not confused with Desktop app tools or with an implemented CLI live runtime path.
- Hardened the V1 create-thread live smoke response validation for current Desktop response shapes.
- Added retrospective merge review evidence records for early PR process gaps.

## Codex API And Desktop Contract Updates

The main v0.2.1 compatibility update is the Codex API / Desktop contract refresh from 2026-06-12.

Desktop app tool contract evidence now records:

- `create_thread` requires `prompt` plus `target`, where `target` can be project or projectless. Optional fields include `model` and `thinking`.
- `read_thread` requires `threadId` and supports optional `turnLimit`, `cursor`, `includeOutputs`, and `maxOutputCharsPerItem`.
- `send_message_to_thread` requires `threadId` plus `prompt`, with optional `model` and `thinking`.
- `fork_thread` accepts optional `threadId` and optional `environment`; fork metadata must not be treated as implicit prompt delivery.

The release also documents the boundary between:

- Codex Desktop app tools, such as `create_thread`, `read_thread`, `send_message_to_thread`, and `fork_thread`;
- `codex app-server` JSON-RPC methods, such as `thread/start`, `thread/read`, `thread/fork`, and `turn/start`;
- Codex SDK wrappers over app-server.

This repository still does not implement a CLI `create_thread` live runtime path, app-server adapter, daemon, MCP server, sidecar, UI scraper, Desktop private runtime state reader, or broad runtime adapter.

## Live Smoke Compatibility

The V1 create-thread live smoke helper now accepts current and existing response shapes:

- `threadId`
- `thread_id`
- `pendingWorktreeId`

Raw Desktop responses that omit wrapper-only fields such as `status`, `private_runtime_state_read`, or `external_write_performed` can be accepted when the returned thread identifier is valid. If private-state or external-write flags are present, they must still be boolean `false`.

Tests cover:

- `threadId` success;
- legacy `thread_id` success;
- `pendingWorktreeId` success;
- rejected private runtime state or external write indicators;
- CLI/default and test paths remaining non-live unless a documented callable is explicitly injected.

## Retrospective Evidence Repair

v0.2.1 also includes a retrospective governance note for early merged PR formal merge review evidence gaps:

- PR #1 is recorded as missing durable platform-side formal merge review evidence at merge time.
- PR #2 is recorded as a post-merge backfill / timing exception, not a total evidence absence.

The durable record is `docs/retrospective-merge-review-evidence-2026-06-12.md`. Matching retrospective notes were also posted to PR #1 and PR #2 after PR #63 was formally reviewed and merged.

This evidence repair does not retroactively convert missing or late platform-side evidence into a valid pre-merge formal review trail.

## Safety And Compatibility

- No state-changing Desktop thread tool is called by default or in tests.
- No new Desktop runtime integration path is added.
- No app-server adapter or SDK wrapper implementation is added.
- No private Desktop runtime state, local app state, logs, sessions, caches, SQLite databases, credentials, or machine-local config are included.
- Future app-server, SDK, SSH-to-Linux CLI, or broader runtime adapter work remains a separate design and implementation slice requiring explicit human approval.

## Verification

Run from the repository root:

```bash
python -m unittest discover -s tests -p 'test_desktop_runtime_*.py'
./scripts/validate-repo.sh
git diff --check
```

Verification used for the v0.2.1 candidate:

- `python -m unittest discover -s tests -p 'test_desktop_runtime_*.py'` passed with 261 tests.
- `./scripts/validate-repo.sh` passed; sensitive-term review emitted policy-only hits, and all hard checks passed.
- `git diff --check` passed with no output.

## Residual Risk

- GitHub has no configured status checks for these PR heads; release confidence relies on local verification and formal review evidence.
- The live smoke created a read-only audit thread and verified the raw Desktop response shape, but the audit task completion itself was out of scope.
- Retrospective evidence repair improves the durable audit trail but cannot prove that PR #1 had platform-side formal merge review evidence before merge.
- PR #2 remains a timing exception because its durable GitHub evidence was posted after merge.
