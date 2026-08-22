# Issue #169 Exact Future Wrapper V1 Removal Plan

## Status and authority

This is a reviewable plan for a **future** destructive slice. Issue #169 is
non-destructive: it must not delete, archive, execute, or reactivate wrappers.
A later Issue may use this plan only after independent review accepts it and
the user explicitly authorizes the exact destructive targets.

Recovery baseline: `864fe8cf61553f6d7db52456a31235da0456f2d3` (`v0.17.1`).
It is a recovery reference, not permission to overwrite a later branch or
restore unrelated changes.

## Exact manifest

### 1. Delete the 32 historical artifacts only after readiness passes

```text
delete: scripts/desktop_runtime_capability_discovery.py
delete: scripts/desktop_runtime_contract_compare.py
delete: scripts/desktop_runtime_create_thread_authorization_gate.py
delete: scripts/desktop_runtime_create_thread_callable_bundle.py
delete: scripts/desktop_runtime_create_thread_callable_wiring.py
delete: scripts/desktop_runtime_create_thread_executor.py
delete: scripts/desktop_runtime_create_thread_executor_boundary.py
delete: scripts/desktop_runtime_create_thread_executor_shell.py
delete: scripts/desktop_runtime_create_thread_live_smoke.py
delete: scripts/desktop_runtime_create_thread_preflight.py
delete: scripts/desktop_runtime_evidence_pipeline.py
delete: scripts/desktop_runtime_read_thread_preflight.py
delete: scripts/desktop_runtime_session_compatibility_cache.py
delete: scripts/desktop_runtime_session_compatibility_handshake.py
delete: scripts/desktop_runtime_session_compatibility_status.py
delete: scripts/desktop_runtime_wrapper_planner.py
delete: tests/test_desktop_runtime_capability_discovery.py
delete: tests/test_desktop_runtime_contract_compare.py
delete: tests/test_desktop_runtime_create_thread_authorization_gate.py
delete: tests/test_desktop_runtime_create_thread_callable_bundle.py
delete: tests/test_desktop_runtime_create_thread_callable_wiring.py
delete: tests/test_desktop_runtime_create_thread_executor.py
delete: tests/test_desktop_runtime_create_thread_executor_boundary.py
delete: tests/test_desktop_runtime_create_thread_executor_shell.py
delete: tests/test_desktop_runtime_create_thread_live_smoke.py
delete: tests/test_desktop_runtime_create_thread_preflight.py
delete: tests/test_desktop_runtime_evidence_pipeline.py
delete: tests/test_desktop_runtime_read_thread_preflight.py
delete: tests/test_desktop_runtime_session_compatibility_cache.py
delete: tests/test_desktop_runtime_session_compatibility_handshake.py
delete: tests/test_desktop_runtime_session_compatibility_status.py
delete: tests/test_desktop_runtime_wrapper_planner.py
```

`tests/test_desktop_wrapper_security_fixtures.py` and
`tests/fixtures/desktop_wrapper_security_invariants.yaml` are the initial
independent security-fixture receiver. They, plus any exact supplemental
fixture tests required by the readiness crosswalk, must pass before removing
the 16 historical test modules.

### 2. Delete obsolete quarantine controls in the same removal slice

```text
delete: docs/desktop-runtime-wrapper-v1-inventory.yaml
delete: scripts/validate-desktop-wrapper-legacy.py
delete: tests/test_desktop_wrapper_legacy.py
rewrite: scripts/validate-repo.sh — remove only legacy validator/test invocation; retain `check_desktop_wrapper_security_fixtures`.
```

Remove only their legacy validator/test invocation from `scripts/validate-repo.sh`.
Retain the separate `check_desktop_wrapper_security_fixtures` wiring. Do not
leave a stale empty-inventory validator or a glob that silently permits a
future wrapper.

### 3. Disposition for every classified reference

The Issue #169 inventory has **23** classified references. The 32 artifacts
above are a separate exact set: 16 scripts plus 16 focused tests. Their
relationship is intentional: the inventory classifies all non-artifact files
that mention the wrapper family; it does not duplicate artifact paths as
references. Every inventory reference has one action below.

```text
rewrite: README.md — remove the frozen-family mention or state only that V1 is retired.
retain-historical: docs/codex-runtime-compatibility-evidence-2026-08-21.md — retain current-session evidence and the inactive-V1 conclusion without runnable guidance.
rewrite: docs/desktop-runtime-wrapper-v1-deprecation.md — replace the frozen/quarantine contract with a brief retirement record.
rewrite: docs/desktop-runtime-wrapper-v1-plan.md — retain historical context only; remove all runnable/importable V1 instructions.
retain-historical: docs/loops/issue-163/implementation-plan.md — retain the completed quarantine decision as commandless historical evidence.
retain-historical: docs/loops/issue-169/future-removal-plan.md — retain the reviewed deletion/recovery receipt; it is not executable guidance.
retain-historical: docs/loops/issue-169/readiness-crosswalk.md — retain behavior dispositions and evidence mapping; it is not executable guidance.
rewrite: docs/native-runtime-capabilities.md — remove V1 active-boundary wording and state the native contract owns current behavior.
retain-historical: docs/release-notes-v0.16.3.md — retain release fact/history without runnable wrapper commands.
retain-historical: docs/release-notes-v0.5.0.md — retain release fact/history without runnable wrapper commands.
rewrite: docs/release-readiness.md — remove legacy inventory/validator readiness checks.
retain-historical: docs/release-security-evidence-v0.2.0.md — preserve security history without executable commands; point to independent fixtures for current evidence.
rewrite: docs/roadmap.md — remove the frozen-wrapper milestone or mark it completed and retired.
rewrite: docs/runtime-compatibility.md — remove current-boundary reliance on the legacy family.
rewrite: docs/skill-selection-guide.md — remove legacy-helper selection guidance.
rewrite: docs/source-classification.md — remove the retained-wrapper classification.
rewrite: policies/runtime-compatibility-policy.md — remove compatibility-evidence-only wording for a family no longer present.
rewrite: skills/desktop-project-delivery/SKILL.md — remove legacy wrapper boundary wording.
rewrite: skills/desktop-thread-delegation/SKILL.md — remove legacy wrapper boundary wording.
rewrite: skills/loop-engineering/SKILL.md — remove legacy wrapper boundary wording.
retain-historical: tests/fixtures/desktop_wrapper_security_invariants.yaml — retain wrapper-independent security invariants; no wrapper entrypoint is imported or loaded.
rewrite: tests/test_native_runtime_contract_docs.py — remove assertions requiring the retired V1 boundary while retaining native contract coverage.
rewrite: tests/test_runtime_compatibility_release_docs.py — remove assertions requiring V1 release-boundary wording.
```

The three Issue #169 additions are explicitly retained as non-executable
evidence: the two files in `docs/loops/issue-169/` and
`tests/fixtures/desktop_wrapper_security_invariants.yaml`. No path absent from
the current 23-entry inventory is a removal-manifest target.

If release-note fidelity needs a wrapper name, keep it as plain historical
text and link to the tagged source; do not retain a runnable command.

### 4. Regenerate, never directly edit, generated copies

Regenerate from rewritten canonical sources:

```text
regenerate: plugin/codex-dev-skills/docs/native-runtime-capabilities.md
regenerate: plugin/codex-dev-skills/skills/desktop-project-delivery/SKILL.md
regenerate: plugin/codex-dev-skills/skills/desktop-thread-delegation/SKILL.md
regenerate: plugin/codex-dev-skills/skills/loop-engineering/SKILL.md
```

No historical wrapper script/test is a plugin entrypoint or generated copy at
the baseline. Package/catalog/installer/manifest scans remain required.

## Blast radius and release value

Facts: the Issue #169 inventory has 32 canonical artifacts and 23 classified
references; the deprecation contract says no active CLI/Desktop adapter,
entrypoint, or consumer may use them. The repository check cannot rule out an
external clone or a dynamically built external command.

Inference and accepted release decision: direct native execution risk is low,
but public compatibility and security-evidence loss remain material. Issue
#169 is a **no-release** preparation change. If a later explicitly authorized
physical-removal Issue completes, publish that removal as a **pre-1.0 minor
release**, not a patch.

## Recovery procedure

1. Record the exact pre-removal SHA and `git status --short --branch` in review
   evidence; confirm it descends from or deliberately supersedes `v0.17.1`.
2. If rollback is approved, restore only exact manifest paths from that SHA;
   do not reset a shared branch or overwrite unrelated work.
3. Restore canonical docs before regenerating plugin copies; generated files
   are never the source of truth.
4. Re-run all commands below, including independent fixtures and package
   parity. The legacy validator/test must be absent post-removal and cannot be
   completion evidence.
5. If public compatibility is needed, revert via a new reviewed release; do
   not recreate a wrapper in an active skill, catalog, installer, or native path.

Recovery is incomplete until the removal branch names its own exact baseline
and independent-fixture locations. `v0.17.1` alone cannot restore later work.

## Required verification for the destructive slice

Do not execute a wrapper or legacy smoke helper:

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs
./scripts/project-python -m unittest tests.test_desktop_wrapper_security_fixtures
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python -m unittest tests.test_plugin_packaging
./scripts/validate-repo.sh
rg -n 'desktop_runtime_' README.md CONTRIBUTING.md docs policies skills examples plugin/codex-dev-skills scripts tests catalog.yaml install.sh
git diff --check
git status --short --branch
```

Review any remaining historical wording from the second scan; a completed
physical-removal branch should normally contain no wrapper script/test paths.
Update `scripts/validate-repo.sh` before running the full suite.

## Human gates

1. Independent reviewer accepts the manifest, crosswalk, recovery procedure,
   release classification, and verification evidence.
2. Independent security review accepts wrapper-independent fixtures.
3. A maintainer resolves any active consumer or external compatibility promise.
4. The user explicitly authorizes deletion after reviewing the final diff and
   recovery evidence.
5. Commit, push, PR, merge, tag, Release, and deployment remain separate
   permissions; this plan grants none.
