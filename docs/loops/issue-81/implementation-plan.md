# Issue 81 Implementation Plan

## Baseline

- Branch: `codex/issue-81-loop-engineering-v1`
- Starting revision: `7fcd60bd73868a66b6442202ef92344826fb614f`
- Baseline repository tests: 267 passed
- Baseline loop tests: 4 passed
- Known release metadata drift: `catalog.yaml` reports `0.1.0`; installer and
  current release report `0.4.0`

## Work Packets

### P1 — Canonical State And Executable Core

- Add a production loop core inside the installable `loop-engineering` skill.
- Parse loop state structurally and validate schema and semantic invariants.
- Implement legal transitions, evidence guards, revision checks, event hashes,
  idempotency, and v1 migration preview.
- Add a CLI for validate, status, transition, audit, and migration preview.

Verification:

```bash
python3 -m unittest tests.test_loop_engineering_core
```

### P2 — Native Capability Convergence

- Define a shared capability-neutral contract for goal and subagents.
- Keep Desktop scheduling, task/thread/worktree management, and hooks in thin
  runtime adapters.
- Mark the legacy Desktop wrapper as compatibility evidence rather than the
  active native path.

Verification:

```bash
python3 -m unittest tests.test_native_runtime_contract_docs
```

### P3 — Workflow Eval Baseline

- Add deterministic JSON fixtures.
- Execute the production routing function rather than fixture-local logic.
- Grade routing, decisions, completion, violations, recovery, and runtime
  semantic equivalence.

Verification:

```bash
python3 scripts/eval-loop-engineering.py
python3 -m unittest tests.test_eval_loop_engineering
```

### P4 — Templates, Validation, And Documentation

- Align manifest, ledger, claim, and loop report contracts.
- Catch catalog, installer, and release version drift.
- Keep repository validation output concise and actionable.
- Update README, usage, runtime, selection, roadmap, and examples.

### P5 — Integration And Review

- Inspect all worker output and ownership boundaries.
- Run full tests and repository validation.
- Run deep code review plus documentation review.
- Close all MUST-FIX, SHOULD-FIX, and NIT findings, or record a durable owner,
  target, reason, verification plan, remaining risk, and promotion trigger for
  any explicitly deferred item.
- Prepare PR-readiness evidence and stop at the external publication gate.

### P6 — Security Finding Closure And Scan Resilience

- Bind active-claim transitions to the claim owner and reject early lease expiry.
- Require protected event receipts plus exact out-of-band live authorization for
  acceptance, gate satisfaction, claim revocation, and objective completion.
- Keep replay-only integrity validation separate from the live write boundary.
- Reject eval fixture paths outside the suite root and validate deep dependency
  graphs iteratively.
- Encode scan-native, Goal, and worker state separation plus bounded reporting
  fallback in production routing, eval fixtures, templates, and docs.
- Run a clean follow-up security diff scan before commit or push.

## Risks

- Adding a YAML dependency can make the installed skill unusable if dependency
  setup is not explicit and verified.
- An event/revision design that is only checked in tests but not used by the CLI
  would create eval theatre.
- Claim files in separate clones or worktrees cannot provide shared locking
  without a common coordination store.
- Removing legacy Desktop helpers in this issue would enlarge the regression
  surface; deprecation and isolation come first.
