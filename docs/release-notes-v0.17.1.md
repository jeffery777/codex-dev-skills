# Release Notes: v0.17.1

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and deployment require the separately
authorized exact-state delivery flow.

v0.17.1 is a backward-compatible public-documentation coherence patch over
v0.17.0. It implements Issue #167 without changing shared orchestration,
Codex CLI or Desktop adapters, Memory behavior, completion authority, or any
installed runtime operation.

## Documentation Coherence

- Corrects README guidance that still described the already published Memory
  M0/M1 work as planning-only.
- Replaces the durable Operational Evidence continuation bootstrap that still
  routed future work to completed Issue #147 and the v0.13.0 baseline.
- Records the exact current boundary: V3-B shipped in v0.13.0; M0 and the
  default-disabled local/manual/CI-only SQLite/FTS5 M1 safety/conformance
  baseline shipped in v0.14.0; M1 remains inactive, non-promotional, and
  unsupported by efficacy evidence.
- Keeps M2 and V3-C behind new evidence, an authorized Issue, and explicit
  human decisions.
- Preserves historical release notes and completed Issue receipts as
  point-in-time records.

## Compatibility And Rollback

Existing skills, workflows, templates, policies, installer groups, plugin
contents, contract schemas, and runtime adapters remain behaviorally
compatible. Rollback requires only reinstalling the reviewed v0.17.0 package;
it does not change memory state, tasks, sessions, worktrees, or runtime state.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_memory_m0_contract_docs tests.test_candidate_evaluation_contract_docs tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

Independent documentation review, exact-head CI, and merge readiness must be
current and finding-free. The annotated `v0.17.1` tag and non-draft,
non-prerelease GitHub Release must bind the exact reviewed merge commit only
after separate human authorization.

## Traceability

- Issue #167: <https://github.com/jeffery777/codex-dev-skills/issues/167>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.17.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.17.0...v0.17.1>
