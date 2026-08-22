# Issue #165 Implementation Plan

## Objective

Add a shared, verifiable context-continuity contract that assesses context
health after a configurable review/fix threshold and can prepare a sequential
fresh-context rollover without confusing it with subagent delegation or a
history-preserving fork.

## Accepted Baseline

- `v0.16.3` / `944a65a` is the accepted source baseline.
- The default review/fix closure limit is two rounds; reaching it is only an
  assessment trigger and never authorizes task creation or rollover.
- Repository, Git, verification, review, and accepted platform evidence remain
  completion authority. Runtime and graph state remain advisory coordination
  evidence.
- The implementation branch is `codex/165-context-continuity-rollover` and the
  current task is the sole active writer.

## Task Slices

1. Define a strict `loop-context-continuity/v1` assessment, checkpoint,
   lineage, idempotency, comparison, and anti-recursion contract with five
   outcomes.
2. Expose read-only assessment through `loopctl.py`, add a shared template, and
   cover clean/dirty, interactive/non-interactive, missing-control-surface,
   replay/conflict, graph-advisory, and cost/quality cases.
3. Add a clean-worktree non-interactive CLI `fresh-continuation` operation that
   binds the validated checkpoint and rollover identity while preserving the
   existing private-clone, no-publication, and no-recursion boundary.
4. Align shared workflows, Desktop/CLI adapters, IDE fallback, capability
   matrix, examples, migration guidance, README, roadmap, and plugin package.
5. Prepare v0.17.0 metadata and release notes, run focused and complete
   verification, then obtain independent review and close every MUST-FIX before
   PR/release readiness.

## Design Decisions

- `completed_rounds >= assessment_trigger_rounds` emits an assessment result;
  it never invokes a runtime control plane.
- `fork` preserves completed conversation history. `fresh-rollover` starts
  from a durable checkpoint. `shared-subagent` is parallel bounded work and
  never transfers the delivery-owner role.
- A fresh rollover is eligible only for the same repository and objective,
  with a complete digest-bound checkpoint, one destination writer, confirmed
  source stop-writing, exact lineage, progress since the prior rollover, and a
  runtime-specific safe path.
- Exact rollover replay is a non-mutating no-op; reuse of a rollover ID with a
  different checkpoint or reuse of one checkpoint under a new ID fails closed.
  CLI dispatch also uses durable caller-independent replay evidence. A rollover
  without digest-changing, bounded material-progress evidence is rejected.
- Graph projection may report lineage but cannot create a task, choose a
  writer, satisfy a gate, or prove completion.
- CLI phase one automates only clean, non-interactive fresh continuation.
  Dirty or interactive CLI cases produce a manual prompt/fallback. Desktop
  uses documented `create_thread` only when exposed and authorized. IDE uses
  a current-session or paste-ready fallback when no independent control plane
  exists.
- Synthetic eval fixtures prove routing/accounting only. A provenance-bearing
  paired run of the same objective remains an explicit release gate; no
  synthetic value may be presented as empirical v0.17.0 evidence.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_context_continuity tests.test_cli_session_handoff
./scripts/project-python scripts/eval-context-continuity.py
./scripts/project-python scripts/eval-loop-engineering.py
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

## Human Gates

Commit, push, pull-request creation, merge, annotated tag `v0.17.0`, GitHub
Release, deployment, and every actual Desktop/CLI task or session mutation
remain separate exact-state human gates. This plan authorizes only local
implementation, verification, review, documentation sync, and readiness
preparation.
