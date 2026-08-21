# Release Notes: v0.16.3

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and deployment require the authorized
exact-state delivery flow and all stated gates.

v0.16.3 is a backward-compatible repository safety and maintenance patch over
v0.16.2. It implements Issue #163 without changing installed workflow
authority, native CLI/Desktop identifiers, runtime mutation behavior, or the
Memory and GitNexus contracts.

## Historical Wrapper Quarantine

- Adds a strict machine-readable inventory for the retained historical
  compatibility evidence: `desktop_runtime_*` scripts, tests, classified references, generated-copy
  boundary, and sunset requirements.
- Adds a bounded, strict-UTF-8, non-symlink YAML/source validator with duplicate
  and non-scalar key rejection, fixed active roots, file-count/per-file/aggregate
  limits, and fail-closed traversal errors.
- Rejects new wrapper artifacts, unclassified or stale references, runnable
  legacy paths in active surfaces, imports from ordinary `scripts/` consumers,
  and imports from non-historical tests while preserving exact inventoried
  compatibility fixtures.
- Integrates the validator and its adversarial tests into the standard
  repository validation command, reports zero detected active runnable
  consumers within the enforced literal/import boundary, and retains exact
  canonical/plugin parity.

## Security Review Remediation

The first security diff scan identified one Low/P3 protection-mechanism gap:
an ordinary script could import a historical wrapper, add itself to the
classified-reference inventory, and still pass the dedicated quarantine check.
The final implementation exempts only the exact inventoried historical
artifacts and adds focused import/path regression cases. Publication requires a
fresh full-diff security scan with zero reportable findings after that fix and
all release metadata are present.

## Compatibility And Rollback

Existing installer groups, packaged skills, workflow authority, CLI session
handoff, Desktop task/thread controls, and historical regression fixtures remain
compatible. Rollback is the normal reviewed reinstall of v0.16.2; it does not
delete wrapper evidence, runtime state, sessions, threads, caches, or user
configuration. Physical wrapper archive or deletion remains a separate,
explicitly authorized destructive slice.

## Verification And Release Gate

```bash
./scripts/project-python scripts/validate-desktop-wrapper-legacy.py
./scripts/project-python -m unittest tests.test_desktop_wrapper_legacy
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Formal code/documentation review, a fresh zero-finding security diff scan, CI,
and exact-head merge readiness must all pass. The annotated `v0.16.3` tag and
non-draft, non-prerelease GitHub Release must bind the exact reviewed merge
commit only after those conditions are proven.

## Traceability

- Issue #163: <https://github.com/jeffery777/codex-dev-skills/issues/163>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.16.2>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.16.2...v0.16.3>
