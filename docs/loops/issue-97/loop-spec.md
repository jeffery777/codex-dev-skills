# Loop Engineering V2c-A: GitNexus Safe Adapter Baseline

## Objective

Deliver Issue #97 as an independently reviewable V2c-A increment: qualify the
exact GitNexus 1.6.9 runtime, add a version-gated read-only advisory adapter and
safe derived-index refresh controller, prove V2b conformance and fail-closed
behavior, complete formal review/security/readiness evidence, and publish a
ready-for-review PR without merging or releasing.

GitHub issue: <https://github.com/jeffery777/codex-dev-skills/issues/97>

## Source Of Truth And Authority

1. Current user authorization and `AGENTS.md`.
2. GitHub Issue #97, this spec, the implementation plan, and task manifest.
3. The existing V2b contract in `docs/external-memory-contract.md`,
   `skills/loop-engineering/references/memory-contract-v1.md`, production
   contract/CLI code, tests, and the mandatory conformance oracle.
4. Current Git identity, branch, HEAD, complete tracked worktree state,
   verification, formal review, security-scan-native state, and accepted
   GitHub state.

GitNexus metadata, index contents, display labels, CLI human output, Goal
status, subagent reports, route receipts, and chat summaries are context or
coordination evidence only. They cannot authorize mutation or prove completion.

## Repo-Owned Loop Ledger

- Root: `docs/loops/issue-97/`
- Task manifest: `docs/loops/issue-97/task-manifest.yaml`
- Materialized ledger: `docs/loops/issue-97/loop-state-ledger.yaml`
- Events: `docs/loops/issue-97/events/`
- Route/integration receipts: `docs/loops/issue-97/receipts/`
- Review disposition: `docs/loops/issue-97/review-disposition.md`
- Source revision: `codex/v2c-gitnexus-adapter@a75728b15f5d15ba7bf1a7e6e3a2dd934915592e`

Stable requirements live here and in the manifest. Validated append-only events
are the operational integrity record; the ledger is their reconstructable
view. Runtime Goal and worker states are never completion truth.

## In Scope

- Executable discovery with explicit regular-file/symlink policy, exact version,
  observed flags, capability fingerprint, and drift requalification.
- Canonical repository identity, normalized remote, Git root/branch/HEAD,
  complete tracked state/digest, indexed revision, and explicit freshness state.
- Version-gated use of GitNexus 1.6.9 structured metadata only where qualified;
  human-oriented status/query output is not a stable parser contract.
- Read-only advisory retrieval receipts bound to request, principal, namespace,
  repository/path/query/source/provenance/digest/TTL/freshness/fingerprint.
- Deterministic reject, quarantine, disable, and no-memory fallback for unsafe
  identity, freshness, provenance, content, replay, lifecycle, path, or runtime.
- Explicit, default-disabled, local derived-index refresh using only structured
  argv `gitnexus analyze --index-only ...` with confinement, environment,
  timeout, lock, expected-HEAD, full tracked-state, and postcondition checks.
- V2b handshake, capability, receipt, disposition, invalidation, rollback,
  idempotency, audit, conformance, and no-backend integration.
- Unit, integration, fixture, negative, tamper, stale, dirty-tree, wrong-repo,
  symlink, unsafe-path, timeout, partial/corrupt metadata, drift, and unexpected
  tracked-mutation tests.
- Necessary public docs, runtime compatibility, rollout/rollback, roadmap, and
  PR/release-readiness guidance.

## Out Of Scope

- Hooks, SessionStart/post-commit automation, scheduling, or eager auto-index.
- GitNexus setup, skills injection, wiki, OpenWiki, Codebase Memory MCP,
  production databases, remote/shared index synchronization, or `@latest`.
- Global profile changes, machine-local executable paths/registries/indexes/
  databases/credentials, release/tag/GitHub Release, deploy, or merge.

## Safety Contract

- The adapter is disabled by default and read-only advisory when enabled.
- Unsupported write/upsert/invalidate/tombstone/delete operations are reported
  unsupported; the adapter never simulates success.
- Qualification and refresh may invoke only an exact discovered executable with
  argv, never a shell command string, and only with `analyze --index-only`.
- The controller verifies target Git root, path confinement, symlink policy,
  environment allowlist, timeout, per-target lock, expected HEAD, exit status,
  indexed revision, and full tracked status/diff/digest before and after.
- Any tracked mutation fails closed, rejects the new index, disables automatic
  capability, preserves evidence, and never resets/restores/stashes/stages.
- Root and nested AGENTS.md, other supported assistant instruction files,
  `.codex/`, skills, workflow, policy,
  and instruction files receive explicit protected-path comparison in addition
  to the complete tracked-state comparison.
- Stale, unknown, conflict, incompatible, corrupt, unsafe, or mismatched state
  falls back to no memory without weakening V1/V2a/V2b.

## Definition Of Done

- Every Issue #97 capability and safety requirement is implemented or stopped
  at an explicit source-of-truth human gate; no DoD is silently narrowed.
- GitNexus 1.6.9 qualification binds exact executable resolution, version,
  observed flags, metadata schema/capabilities, and Mac evidence.
- Freshness distinguishes `fresh`, `stale`, `missing`, `partial`, `unsupported`,
  `incompatible`, `corrupt`, and `unknown`; dirty state is never equal to HEAD.
- V2b mandatory conformance passes with caller-owned trusted evidence and no
  removal or weakening of difficult cases; no-backend default remains usable.
- Focused and full repository validation, hygiene, runtime compatibility,
  fixture qualification, mutation negatives, and `git diff --check` pass.
- Formal deep code review, docs review, Codex Security diff scan, and readiness
  gates have no unresolved MUST-FIX; SF/NIT items are fixed or durably disposed.
- Commit, push, Issue-linked ready-for-review PR, and evidence links are
  traceable; PR remains unmerged and no release/global-profile mutation occurs.

## Loop Policy And Human Gates

- Entry: `loop-engineering`; outer workflow: `project-delivery`.
- Execution: current session plus disjoint shared subagents; main agent owns
  integration and independent verification.
- Review closure limit: two formal rounds per review stage unless a fresh
  security scan contract requires its own continuation.
- Issue creation, branch creation, commit, push, and PR creation are authorized
  only after their named evidence gates. Merge/release are not authorized.
- Stop for product semantics, V2b source conflict, GitNexus stable-interface
  conflict, unexpected repository mutation, security-policy conflict,
  insufficient high-risk verification, destructive action, or scope expansion.

## V2c-B Follow-Up

After this controller qualifies, a separate V2c-B objective may add stale
notifications and opt-in auto-on-demand refresh for commit/SessionStart events.
Hooks remain optional guardrails; V2c-A must remain safe without them.
