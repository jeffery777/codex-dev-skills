# Release Notes: v0.8.0

Release date: 2026-07-19

v0.8.0 adds the first production GitNexus adapter boundary to Loop Engineering.
The adapter is default-disabled, read-only and advisory, version-gated to the
qualified local runtime, and unable to replace repository evidence, human
authorization, review gates, or completion truth.

This is an independently usable V2c-A release. The separate V2c-B hooks and
stale-notification follow-up are not required for safe operation; hooks remain
optional guardrails and the adapter stays fail-closed when they are absent.

## Changes

- Added exact executable discovery and fingerprinting for the qualified
  GitNexus 1.6.9 command and its observed capability flags.
- Added canonical repository identity, branch, HEAD, tracked-worktree digest,
  indexed revision, metadata validation, and deterministic freshness states.
- Added a V2b-conformant advisory handshake and receipt boundary that binds
  accepted context to repository, request, principal, namespace, provenance,
  revision, freshness, digest, and adapter fingerprint.
- Kept `read_query` and every write, upsert, invalidate, tombstone, and delete
  capability explicitly unsupported because GitNexus 1.6.9 does not expose a
  qualified structured query interface.
- Added an explicit local derived-index refresh controller that invokes only
  structured `gitnexus analyze --index-only` argv after target, environment,
  timeout, locking, expected-HEAD, and path-confinement checks.
- Added complete tracked, staged, protected-file, Git-control, and worktree
  pre/postconditions. Unexpected repository mutation fails closed and remains
  available for human inspection; the controller never restores, resets,
  stashes, stages, commits, or hides user changes.
- Added tamper, stale, dirty-tree, wrong-repository, unsafe-path, symlink,
  timeout, partial/corrupt metadata, capability drift, replay, lifecycle, and
  unexpected tracked-mutation coverage.
- Documented explicit qualification, status, refresh, disable, rollout,
  rollback, macOS live evidence, Linux portability limits, and the V2c-B
  follow-up.

## Authority And Compatibility

GitNexus output is data, never instruction or authorization. The adapter cannot
authorize mutation, external writes, gates, merges, releases, or completion.
Stale, unknown, incompatible, conflicting, unsafe, or untrusted state rejects
adoption or falls back to no external memory.

The V2b no-backend default remains fully functional. Caller-owned repository,
principal, request, namespace, revision, and lifecycle evidence cannot be
replaced by adapter self-report. Unsupported query and mutation capabilities do
not simulate success.

Machine-local executable paths, registries, indexes, databases, credentials,
and runtime state are not part of the release. Runtime discovery supports the
documented macOS Codex Desktop and Linux Codex CLI configuration boundary, but
only macOS arm64 received live GitNexus qualification for this release; Linux
is represented by portability fixtures and contract tests.

## Update From v0.7.0

Review local differences before updating installed skills:

```bash
./install.sh diff --all
./install.sh update --all
```

The GitNexus adapter remains disabled until explicitly configured and
qualified. Do not copy a machine-local executable path or index from another
host or checkout. Follow the qualification and opt-in flow in
`docs/usage-model.md` and `docs/external-memory-contract.md` before enabling it.

Restart Codex or begin a new task after installation so changed skills,
references, templates, and profiles are rediscovered.

## Verification

The V2c-A feature candidate completed:

- 651/651 full repository unit tests;
- 79/79 GitNexus adapter tests;
- 46/46 repository V2b validation tests, including the mandatory 31/31
  conformance oracle;
- repository validation counts of 150 loop tests, 35 profile/installer tests,
  45 routing tests, and 46 V2b tests;
- formal deep code review, documentation review, terminal evidence review, and
  PR-readiness gates with no open MF, SF, or NIT findings;
- local defensive diff scans with complete reviewed worklists and no reportable
  findings;
- a live macOS GitNexus 1.6.9 `analyze --index-only` qualification whose
  tracked and protected repository state remained unchanged.

Re-run the release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

The v0.8.0 release slice updates version metadata, roadmap status, and release
documentation on top of the reviewed Issue #97 / PR #98 feature baseline. It
also allows an objectively completed terminal ledger to remain auditable from a
named descendant branch after merge or release preparation, while active
ledgers still require the exact branch and HEAD and detached checkouts remain
rejected. It does not change adapter execution or permissions.

## Rollback

Disable the adapter to return immediately to the no-backend path; disabling it
does not delete or rewrite repository files. Inspect installer differences
before updating or uninstalling, and preserve locally modified destinations.
The derived index and registry remain machine-local runtime state and are not
required to roll back the repository source.

This release does not add Codex hooks, post-commit hooks, SessionStart hooks,
automatic scheduling, eager reindexing, wiki generation, shared databases,
cross-host index synchronization, deployment, or global-profile changes.

Compare: https://github.com/jeffery777/codex-dev-skills/compare/v0.7.0...v0.8.0
