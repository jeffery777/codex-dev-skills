# Release Notes: v0.17.0

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and deployment require the authorized
exact-state delivery flow and all stated gates.

v0.17.0 is an additive minor feature release over v0.16.3. It implements Issue
#165 by adding a public context-continuity and fresh-context rollover contract
without changing repository completion authority or silently migrating existing
loop ledgers.

## Context Continuity Contract

- Adds strict `loop-context-continuity/v1` assessment with five outcomes:
  continue, reground, bounded parallel subagent delegation, prepare fresh
  rollover, and stop for a human gate.
- Keeps the configurable default of two unfinished review/fix rounds as an
  assessment trigger only. Token or compaction pressure cannot authorize a
  task mutation by itself.
- Adds a canonical durable checkpoint, single destination writer, confirmed
  source stop-writing, stable lineage, exact-replay no-op, conflicting replay
  rejection, and anti-recursion without material progress.
- Keeps graph projections advisory; they cannot create tasks, transfer writer
  ownership, satisfy gates, or prove completion.

## Runtime Paths

- Desktop fresh rollover uses a separately authorized `create_thread` with the
  exact project, explicit checkpoint-branch starting state, and checkpoint-only
  prompt. Destination branch/HEAD verification precedes writer activation. Existing `fork_thread` behavior
  remains history-preserving and is not used as a fresh fallback.
- CLI adds phase-one `fresh-continuation` for a clean, non-interactive exact
  worktree through the existing isolated private-clone executor. It verifies
  the actual canonical `origin` host/path and claims rollover-ID plus
  checkpoint-digest indexed at-most-once ledger below the Git control directory using
  non-blocking, atomic descriptor-relative, file-and-directory-synced operations before
  calling the runtime. Dirty,
  interactive, unavailable, incomplete, and replay cases perform no CLI call
  and return a manual/current-session fallback.
- IDE has no assumed independent task control plane. Shared assessment,
  current-session regrounding, disjoint subagents, and paste-ready prompts form
  the safe baseline.
- No path relies on unpublished Desktop internals, private CLI state, UI
  scraping, app-server clients, daemons, or sidecars.

## Evaluation And Compatibility

The provenance-labelled synthetic comparison records end-to-end objective tokens including
handoff/bootstrap overhead, wall time, repeated reads, review/fix rounds,
stale-context errors, blockers, and final quality. Measured token shifting or a
quality regression selects regrounding rather than fresh rollover. It tests
routing and accounting only; it is not empirical A/B evidence. The bounded
same-objective pair in `docs/loops/issue-165/paired-run-evidence.md` records the
method, raw-result fields, artifact digests, predeclared rubric, token totals
including bootstrap, wall time, reads, rounds, stale errors, blockers, quality,
and limitations. Both conditions scored 8/8; the fresh checkpoint condition
used fewer tokens, less wall time, and fewer reads. This satisfies the empirical
candidate gate without claiming that one ordered pair generalizes to every
objective or runtime.

Existing CLI `start`, `resume`, `fork`, interactive fork, Desktop fork/create,
review closure, and loop ledger contracts remain compatible. Rollback returns
to v0.16.3 current-session, subagent, fork, and prompt paths without deleting
tasks, sessions, worktrees, runtime state, or repository history.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_context_continuity tests.test_eval_context_continuity tests.test_cli_session_handoff
./scripts/project-python scripts/eval-context-continuity.py
./scripts/project-python scripts/eval-loop-engineering.py
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Independent code and documentation review and the empirical paired-run gate
have passed for the feature commit. A fresh exact-head security diff scan, CI,
and exact-head merge readiness remain required after evidence updates. The annotated `v0.17.0` tag and
non-draft/non-prerelease GitHub Release must bind the exact reviewed merge
commit only after separate human authorization.

## Traceability

- Issue #165: <https://github.com/jeffery777/codex-dev-skills/issues/165>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.16.3>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.16.3...v0.17.0>
