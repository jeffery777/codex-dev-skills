# Issue #147 Implementation Plan — Memory M1 SQLite/FTS5

## Objective

Implement the bounded Issue #147 spec as one additive default-disabled
reference adapter, qualify safety/conformance, preserve upstream contracts,
and stop before PR after the conditionally authorized commit/push gate.

## Task Slices

1. Freeze and inspect the Issue-owned spec, ADR, threat model, plan, and task
   packet.
2. Add `memory_sqlite.py` with isolated FTS5 probe, exact fingerprints, secure
   placement, fixed schema, structured query, M0 execution, integrity, receipt
   lookup, and qualification-receipt helpers.
3. Add `sqlitectl.py` with explicit probe/initialize/query/execute/receipt/
   integrity/qualification-receipt routes and generic errors.
4. Add portable/public contract docs and the exact fixed schema reference.
5. Add synthetic fixtures, focused unit/CLI/docs tests, deterministic eval
   runner/suite, package inventory, repository validator integration, and
   public roadmap/continuation docs.
6. Run focused and full verification, local static impact analysis, Codex
   Security diff scan, deep code/public-contract/security/privacy review, fix
   MUST-FIX findings within two rounds, and commit/push only when the final code
   review and security diff scan report no findings.
7. Record non-blocking out-of-scope residual risks with owner, target,
   verification plan, and promotion trigger; stop before PR or release action.

## Expected Change Surface

- `skills/loop-engineering/scripts/{memory_sqlite,sqlitectl}.py`;
- `skills/loop-engineering/references/memory-sqlite-v0.md`;
- `docs/memory-sqlite-reference-contract.md`;
- `evals/memory-sqlite/`, `scripts/eval-memory-sqlite.py`;
- focused adapter/CLI/docs/eval tests;
- `skills/loop-engineering/SKILL.md`, README, roadmap, release-readiness,
  Operational Evidence continuation/ADR docs, `catalog.yaml`, `install.sh`, and
  `scripts/validate-repo.sh` only as required for additive packaging;
- `docs/loops/issue-147/` planning and evidence receipts.

Existing V2b/V2d/V3/M0 production modules are consumers/regressions only and
must not change.

## Verification Strategy

- resolver/PyYAML preflight;
- focused adapter/CLI/docs/eval tests;
- all M0 plus V2b/V3-B regression tests/evals;
- all released production eval runners;
- full unittest discovery;
- repository validator, installer manifest/diff consistency, shell syntax,
  Python compile checks, `git diff --check`, status/untracked inspection;
- state-root tests use isolated temporary directories only and do not install,
  activate, retain, or publish databases;
- the user-authorized GitNexus issue-branch index is advisory while the
  worktree is dirty; supplement it with local import/call-site, complete
  diff/untracked inspection, full-test, validator, and review evidence.

## Risks And Controls

- authority laundering: full M0 reconstruction before state open;
- query injection: exact token grammar, fixed compiler, parameterized SQL;
- runtime/schema drift: behavior probe and exact fingerprints per invocation;
- placement: explicit disjoint secure roots plus path-component and file
  metadata checks within the cooperative same-user boundary;
- atomicity/replay: one transaction and unique request binding;
- recovery overclaim: named synthetic faults, uncertainty is failure;
- privacy: public/internal only, generic errors, synthetic fixtures;
- backend creep: no service/network/hooks/automatic path;
- release creep: TBD and no version/release-note change.

## Review And Gates

- planning/threat-model evidence before implementation;
- deep code/public-contract/security/privacy review after implementation;
- Codex Security diff scan and formal commit-readiness evidence;
- at most two review/fix rounds unless a new human decision is required;
- commit and push require final code review plus security diff scan with no
  findings under the maintainer's explicit authorization;
- stop before PR, merge, tag, Release, install, activation, promotion, release
  target selection, or deploy.
