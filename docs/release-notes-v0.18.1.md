# Release Notes: v0.18.1

Status: release candidate; commit, push, pull request creation, merge,
annotated tag creation, GitHub Release, and any future deployment require
separately authorized exact-state delivery flows.

v0.18.1 is a backward-compatible post-release state-coherence patch over
v0.18.0. It implements Issue #175 by aligning active release guidance,
traceability, version metadata, and drift-prevention contracts with the
published v0.18.0 state. It does not change shared orchestration, Codex CLI or
Desktop adapters, Memory runtime contracts, installer logic, target selection,
installed payload behavior, or completion authority. Installer receipt
metadata advances normally to 0.18.1.

## Published v0.18.0 Baseline

- Issue #171 / PR #172 delivered the Desktop Runtime Wrapper V1 retirement;
  Issue #174 / PR #173 published that work as v0.18.0.
- PR #173 merged as
  `3b789e2f9749f2643b6fe75397d22f6e21a71ce2`.
- The annotated `v0.18.0` tag and non-draft, non-prerelease GitHub Release bind
  that exact merge commit. At the 2026-08-24 source-of-truth preflight, GitHub
  main was that same exact commit and the tag-to-main divergence was 0/0.
- The repository has no deployment target or publish/deploy workflow.
  Deployment is therefore not applicable, and GitHub Release publication is
  not deployment evidence.

## State Coherence

- Corrects active README, roadmap, readiness, and Operational Evidence
  continuation guidance that still described v0.18.0 as candidate or prepared.
- Replaces the stale post-v0.17.0 continuation boundary with the bounded Issue
  #175 scope while requiring current discovery and new authority for later
  implementation.
- Aligns catalog, installer receipt metadata, and the package-local plugin
  manifest at 0.18.1.
- Adds contract coverage for the v0.18.0 published baseline, the v0.18.1
  candidate role, exact publication traceability, and the deployment boundary.
- Preserves v0.18.0 and older release notes as historical point-in-time records
  rather than backfilling post-release maintenance into them.
- Keeps M1 inactive and non-promotional; M2, V3-C, and Memory activation remain
  behind new evidence, an authorized Issue, and explicit human decisions.

## Compatibility And Rollback

Existing skills, workflows, templates, policies, installer groups, plugin
payloads, contract schemas, and runtime adapters remain behaviorally
compatible. The source rollback baseline is the reviewed annotated `v0.18.0`
tag at `3b789e2f9749f2643b6fe75397d22f6e21a71ce2`. Revert only this bounded
documentation, metadata, and test slice; regenerate package copies only from
canonical sources and do not reset a shared branch or overwrite unrelated work.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_runtime_compatibility_release_docs tests.test_operational_evidence_status_docs tests.test_plugin_packaging tests.test_candidate_evaluation_contract_docs tests.test_improvement_lineage_contract_docs tests.test_improvement_proposal_contract_docs tests.test_memory_m0_contract_docs
./scripts/project-python -m unittest tests.test_installer_agent_profiles tests.test_installer_runtime_groups
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
git status --short --branch
```

Independent documentation review, repository verification, exact-head CI, and
merge readiness must be current and finding-free. Commit, push, PR creation,
merge, annotated tag creation, GitHub Release publication, platform comments,
reviews, deployment, and cleanup remain separately gated.

## Traceability

- State-coherence Issue #175: <https://github.com/jeffery777/codex-dev-skills/issues/175>
- v0.18.0 release-closure Issue #174: <https://github.com/jeffery777/codex-dev-skills/issues/174>
- v0.18.0 release-closure PR #173: <https://github.com/jeffery777/codex-dev-skills/pull/173>
- Base annotated tag: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.18.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.18.0...v0.18.1>
