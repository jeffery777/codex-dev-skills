# Loop Engineering V2c-B: GitNexus Hook-Driven Index Freshness

## Objective

Deliver Issue #103 as an independently reviewable V2c-B increment that uses
trusted, opt-in Codex lifecycle hooks to detect stale GitNexus index state and,
only when separately enabled, request an on-demand refresh through the
qualified V2c-A controller.

## Source Of Truth

- Repo instructions: `AGENTS.md`
- GitHub objective: Issue #103
- V2c roadmap: `docs/roadmap.md`
- V2c-A contract: `docs/external-memory-contract.md`
- Runtime hook boundary: `docs/native-runtime-capabilities.md`
- Implementation plan: `docs/loops/issue-103/implementation-plan.md`
- Task manifest: `docs/loops/issue-103/task-manifest.yaml`
- V2c-A implementation: `skills/loop-engineering/scripts/gitnexus_adapter.py`
- Current public hook contract: `https://learn.chatgpt.com/docs/hooks`

## Repo-Owned Loop Ledger

- Ledger root: `docs/loops/issue-103`
- Task manifest: `docs/loops/issue-103/task-manifest.yaml`
- Ledger: `docs/loops/issue-103/loop-state-ledger.yaml`
- Review disposition: `docs/loops/issue-103/review-disposition.md`
- Source revision:
  `codex/issue-103-v2c-b-hooks@012d1de0148362468c3861fff65883577c58be01`

The spec and manifest define stable requirements. Repository files, Git,
verification, and review evidence prove completion. Hook output, runtime
summaries, and GitNexus metadata remain advisory context only.

## Scope

### In Scope

- A strict, bounded hook runner for `SessionStart` and `PostToolUse`.
- `SessionStart` freshness checks for `startup`, `resume`, `clear`, and
  `compact` sources.
- A `PostToolUse` `Bash` compensation signal that rechecks freshness after
  shell actions, including but not limited to successful commits.
- An exact machine-local configuration contract that binds repository identity,
  accepted GitNexus qualification digests, and optional refresh resources.
- Notify-only behavior by default.
- Separately enabled auto-on-demand refresh through `RefreshController` only.
- Repo-owned, inactive hook and machine-local config templates.
- Tests, documentation, rollout, rollback, and formal review evidence.

### Out Of Scope

- Parsing shell commands to decide whether a commit occurred.
- Claiming that tool hooks intercept every Git mutation path.
- Eager reindex on every commit or every tool call.
- Schedulers, daemons, sidecars, background services, or an app-server client.
- New GitNexus query, write, wiki, setup, or bare `analyze` capabilities.
- Activating hooks during installation or writing global/project Codex config.
- Plugin marketplace packaging, cross-host index synchronization, or shared
  databases.
- Commit, push, PR creation, merge, release, or deployment without a later
  exact human authorization.

## Normative Behavior

1. The hook runner accepts one absolute, current-user-owned, non-symlink,
   non-group/world-writable machine-local JSON configuration file.
2. It reads at most 64 KiB of UTF-8 JSON from stdin, rejects duplicate keys,
   and uses only documented hook fields. It never reads the transcript.
3. The hook `cwd` must resolve inside the exact configured repository root.
4. Every invocation requalifies the configured GitNexus executable and derives
   live repository identity, snapshot, and metadata freshness through V2c-A.
5. `fresh` exits successfully without model-visible noise.
6. Any non-fresh state produces a concise advisory disposition. It never makes
   stale metadata adoptable.
7. `notify-only` never refreshes.
8. `auto-on-demand` may refresh only when the state is `stale` because the
   indexed revision differs from a clean current HEAD, or `missing` on a clean
   current HEAD. Dirty worktrees are notification-only.
9. Refresh delegates to V2c-A with exact expected HEAD, explicit runtime opt-in,
   a fresh `0700` child below an approved machine-local `GITNEXUS_HOME` parent,
   lock directory, and controller postconditions. Hook-created homes are not
   automatically deleted; failure evidence and cleanup remain operator-owned.
10. Refresh failure returns a bounded warning and preserves no-backend behavior.
    It also writes a secure repository-bound machine-local circuit-breaker
    marker so later hooks cannot retry automatically until an operator inspects
    and explicitly clears that marker.
11. Hooks disabled, absent, untrusted, skipped, unsupported, or unable to
    observe a path do not change V1/V2a/V2b/V2c-A correctness.

## Loop Policy

- Entry skill: `loop-engineering`
- Default execution mode: `current-session`
- Review closure round limit: `3`
- Desktop runtime actions allowed: `none`
- External writes allowed only with exact authorization: `yes`; Issue #103 and
  local branch creation were explicitly authorized, while later publication
  actions are not yet authorized.

## Definition Of Done

- Hook and config schemas are strict, bounded, path-safe, and tested.
- Project adoption is explicit, reviewable, inactive by default, and reversible.
- `SessionStart` and `PostToolUse` produce deterministic freshness dispositions.
- Notify-only is the default and cannot reach the refresh controller.
- Auto-on-demand uses only the qualified V2c-A controller and never refreshes a
  dirty or identity-conflicted repository.
- No hook output grants mutation, external-write, gate, review, or completion
  authority.
- No machine-local paths, qualification files, indexes, credentials, or active
  Codex config are committed.
- Existing V2b/V2c-A verification and all new hook tests pass.
- Public docs state hook coverage limits, opt-in, trust review, rollout, and
  rollback.
- Deep code review, docs review, and PR-readiness evidence have no unresolved
  MUST-FIX findings.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
python3 scripts/eval-memory-contract.py
./scripts/validate-repo.sh
git diff --check
```

## Human Gates

Stop before product-semantic expansion, destructive action, external write not
already authorized, commit, push, PR creation, release, merge, deployment,
plugin packaging, global profile/config mutation, or weakening the V2b/V2c-A
security and evidence boundary.
