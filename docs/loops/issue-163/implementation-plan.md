# Issue #163 Implementation Plan

## Objective

Freeze and quarantine the historical Desktop runtime wrapper V1 chain behind
one strict repository-owned inventory and validation boundary. Preserve the
existing safety and compatibility fixtures without allowing active runtime
guidance, skills, packaging, or installer surfaces to execute or depend on the
legacy helpers.

## Accepted Baseline

- `v0.16.2` / `d783e80` is the accepted source baseline.
- CLI and Desktop are independent native control-plane adapters.
- Shared workflows own task selection, verification, review, completion, and
  human-gate semantics.
- The `desktop_runtime_*` helper family is historical compatibility evidence,
  not an active execution path or authority source.

## Task Slices

1. Add `docs/desktop-runtime-wrapper-v1-inventory.yaml` as the canonical,
   machine-readable inventory of retained wrapper scripts, focused tests,
   historical documents, and current boundary references.
2. Add a fail-closed validator and adversarial tests. The validator must reject
   malformed inventory data, missing or stale artifact entries, unclassified
   references, generated-copy entries in the canonical inventory, and active
   runnable references to legacy scripts.
3. Wire the validator into repository verification, remove runnable wrapper
   commands from active examples, and align current documentation with the
   quarantine and sunset boundary.
4. Verify the focused contract, full repository, generated plugin parity, Git
   whitespace, and final change impact; then run the formal code review gate.
5. Publish the backward-compatible quarantine as v0.16.3 after a fresh
   zero-finding security diff scan, exact-head CI, merge review, and merge
   readiness all pass.

## Design Decisions

- The inventory is canonical-source-only. Generated plugin content remains
  governed by the existing exact source/package parity validator.
- Artifact discovery is intentionally narrow and deterministic:
  `scripts/desktop_runtime_*.py` and
  `tests/test_desktop_runtime_*.py` must match the inventory exactly.
- Text references to `desktop_runtime_` must be classified explicitly. Active
  documentation may describe the historical boundary, but active surfaces may
  not contain a runnable `scripts/desktop_runtime_*` path.
- The validator reads only bounded regular, non-symlink UTF-8 files under the
  supplied repository root and never executes fixture-controlled content.
- This issue adds no runtime behavior, package entrypoint, installer group,
  hook, daemon, scheduler, or completion authority.

## Sunset Gate

A later archive or deletion issue may proceed only when all of the following
are independently verified:

1. the inventory and validator report zero active runnable consumers;
2. native CLI/Desktop adapter coverage replaces every retained behavioral
   requirement that is still current;
3. historical security assertions that remain useful have fixtures outside
   the executable wrapper chain;
4. documentation and generated plugin sources contain no executable legacy
   guidance;
5. a separately reviewed destructive-action plan names exact deletion targets,
   rollback/recovery evidence, and verification commands; and
6. the user explicitly authorizes that archive or deletion slice.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python scripts/validate-desktop-wrapper-legacy.py
./scripts/project-python -m unittest tests.test_desktop_wrapper_legacy
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

## Human Gates

The user authorized commit, push, pull-request creation, merge, annotated tag
`v0.16.3`, and a non-draft/non-prerelease GitHub Release only after the final
diff is finding-free across formal review and a fresh security diff scan, CI
passes, and exact-head merge readiness succeeds. Deployment and any physical
archive or deletion remain separate human gates.
