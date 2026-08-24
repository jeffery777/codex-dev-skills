# Release Notes: v0.18.0

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and deployment require separately
authorized exact-state delivery flows.

v0.18.0 is the pre-1.0 minor release closure for the Desktop Runtime Wrapper
V1 retirement over v0.17.1. The release delta includes Issue #169 / PR #170
sunset, readiness, and recovery preparation followed by Issue #171 / PR #172
physical removal. The minor classification reflects the deliberate
removal of a public repository helper family rather than a backward-compatible
patch.

## Desktop Runtime Wrapper V1 Retirement

- Removes 16 historical `scripts/desktop_runtime_*.py` helpers and their 16
  focused `tests/test_desktop_runtime_*.py` files.
- Removes the obsolete inventory, legacy validator, and legacy validator test.
- Rewrites active guidance so the retired helper family is non-executable
  history rather than a supported compatibility or invocation path.
- Preserves wrapper-independent security fixtures and native authorization,
  identity, fail-closed, private-state, external-write, and non-execution
  contracts.
- Retains native CLI and Desktop adapters without adding a replacement wrapper,
  legacy smoke path, unpublished internal API, or broader completion authority.

The exact pre-closure feature/removal delta
`v0.17.1..66b8b02309e5254248c72302d19bf37d3ddbc43e` contains two commits and
66 files: 4 added, 35 deleted, and 27 modified, with 1,316 insertions and
18,929 deletions. The final tagged release delta will additionally include this
release-closure metadata, documentation, and contract-test slice. The generated
plugin copies changed by PR #172 were regenerated from canonical sources and
remain subject to exact inventory, byte, and mode parity checks.

## Compatibility And Distribution

The removed V1 files were retired and absent from the active catalog,
installer, plugin entrypoints, hooks, and native runtime paths before physical
removal. Repository scans cannot exclude an external clone or dynamically
constructed third-party command that still names a removed file; such a caller
must migrate to the current native runtime contract instead of restoring an
active wrapper.

This release aligns the catalog, installer receipt version, package-local
plugin manifest, README, roadmap, readiness guidance, and version contract
tests at 0.18.0. It does not change machine-local runtime state, install or
activate a plugin, or define a repository deployment target. The repository has
no publish/deploy workflow, and a GitHub Release is not deployment evidence.

## Recovery And Rollback

For package rollback, reinstall from the GitHub-generated source archive bound
to the reviewed annotated `v0.17.1` tag; the Release has no separately uploaded
package asset. For source-level recovery of the removal, the exact pre-removal
baseline is
`2cb1d539596a4bea6c5a8306c9fdea1eba831220`: restore only the reviewed 58
canonical/control paths, then regenerate the four package copies from canonical
sources. Do not reset a shared branch, overwrite unrelated work, edit generated
copies directly, or silently recreate an active wrapper. The v0.17.1 commit
alone does not restore later sunset preparation.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs tests.test_plugin_packaging tests.test_candidate_evaluation_contract_docs tests.test_improvement_lineage_contract_docs tests.test_improvement_proposal_contract_docs tests.test_memory_m0_contract_docs
./scripts/project-python -m unittest tests.test_installer_agent_profiles tests.test_installer_runtime_groups
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs tests.test_desktop_wrapper_security_fixtures
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
git status --short --branch
```

Formal finding-free review, a fresh zero-finding security diff scan, exact-head
CI, and merge readiness must be current for the release-closure change. The
annotated `v0.18.0` tag and non-draft, non-prerelease GitHub Release may bind
only the exact release-closure pull request merge commit after their separate
human gates. Publication does not authorize deployment or cleanup.

## Traceability

- Preparation Issue #169: <https://github.com/jeffery777/codex-dev-skills/issues/169>
- Preparation PR #170: <https://github.com/jeffery777/codex-dev-skills/pull/170>
- Removal Issue #171: <https://github.com/jeffery777/codex-dev-skills/issues/171>
- Removal PR #172: <https://github.com/jeffery777/codex-dev-skills/pull/172>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.17.1>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.17.1...v0.18.0>
