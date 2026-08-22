# Issue #167 Implementation Plan

## Objective

Publish the smallest backward-compatible v0.17.1 documentation-coherence
patch. Align active public guidance and the durable Operational Evidence
continuation handoff with the released V3-B, Memory M0, and default-disabled
Memory M1 baselines without changing runtime or authority behavior.

## Accepted Baseline

- `v0.17.0` / `5cef51d` is the accepted source and release baseline.
- V3-B was published in v0.13.0.
- Memory M0 and the default-disabled local/manual/CI-only SQLite/FTS5 M1
  safety/conformance baseline were published in v0.14.0.
- M1 publication is not activation, promotion, or efficacy evidence.
- M2 and V3-C require new evidence, an authorized Issue, and explicit human
  decisions.
- Shared, CLI, and Desktop runtime adapters are unchanged by this patch.

## Task Slices

1. Correct the stale README Agent Memory status without rewriting historical
   release notes or completed Issue evidence.
2. Replace the stale Issue #147 / v0.13.0 continuation bootstrap with
   current-platform discovery and explicit future-work gates.
3. Scan active documentation for equivalent stale claims and add deterministic
   regression assertions.
4. Align v0.17.1 catalog, installer, plugin manifest, README, roadmap,
   release-readiness guidance, release notes, and current-version tests.
5. Verify generated package parity, focused/full tests, documentation review,
   exact-head CI, merge readiness, and release identity.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_memory_m0_contract_docs tests.test_candidate_evaluation_contract_docs tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

## Release Boundary

The user authorized commit, push, pull-request creation, merge, annotated tag
`v0.17.1`, and a non-draft/non-prerelease GitHub Release only after the final
diff is finding-free, CI passes on the exact PR head, and merge readiness
succeeds. No deployment, Memory activation, M2/V3-C implementation, or
historical Desktop wrapper deletion is included.
