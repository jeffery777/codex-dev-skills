# Release Notes: v0.8.1

Release date: 2026-07-21

v0.8.1 is a compatibility-documentation patch for current Codex CLI and
ChatGPT desktop runtime surfaces. It updates the installed Desktop delegation
skill and public runtime contract without changing executable workflow code,
the shared orchestration core, or release authority.

## Changes

- Recorded current Codex CLI, desktop bundle, active task/thread callable, and
  generated app-server schema evidence.
- Clarified that the current public desktop product surface is the ChatGPT
  desktop app while `Codex Desktop` and `desktop` remain stable compatibility
  labels for Codex task, thread, worktree, and scheduling controls.
- Documented host-aware `wait_threads` observation using `threadId`, `hostId`,
  and `afterCursor`, including its bounded one-to-eight-target behavior.
- Preserved the shared CLI/Desktop/IDE subagent, verification, review, and
  completion contract. Desktop task tools remain thin runtime adapters.
- Kept app-server as a separate JSON-RPC contract family; this release does not
  add an app-server client, SDK wrapper, daemon, sidecar, or new MCP server.
- Added contract regression tests for product naming, runtime layering, and
  non-authoritative wait snapshots.

## Update From v0.8.0

Review local differences before updating installed skills:

```bash
./install.sh diff --all
./install.sh update --all
```

Restart Codex or begin a new task after installation so the updated Desktop
skill and templates are rediscovered.

## Verification

The v0.8.1 compatibility candidate completed:

- 653/653 full repository unit tests;
- repository validation, including loop, custom-agent, routing, installer, and
  external-memory contract suites;
- formal documentation review and merge-readiness gates with no open findings;
- app-server V2 schema regeneration with 228 JSON schema files and 87
  `ClientRequest` methods;
- GitNexus change analysis reporting low risk and no affected execution flows.

Re-run the release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

The security diff scan was not run because this patch changes documentation,
one installed skill contract, version metadata, and contract tests only. It
does not modify production code, dependencies, permissions, authentication,
data handling, or deployment behavior.

## Rollback

Reinstall or update from the v0.8.0 checkout after reviewing
`./install.sh diff --all`. Runtime evidence is advisory and dated; capability
detection at the active call site remains authoritative for callable
availability.

Compare: https://github.com/jeffery777/codex-dev-skills/compare/v0.8.0...v0.8.1
