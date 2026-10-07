# Release Notes: v0.34.0

Status: limited release candidate for Issue #316; publication unverified.

Prepared on 2026-10-07 for the Issue #316 A/B foundation branch
`codex/issue-316-ab-foundation`. This records candidate contents only, not an
annotated tag, published Release, or installation.

## Local Role Model Mapping

- Add default-off user-owned role model mappings to V2 agent routing.
- Bind provider configuration, runtime, model/effort, canonical/effective profile,
  reviewed scope and quality evidence without changing capability or authority.
- Fail closed for enabled invalid/unavailable/drifted mappings; preserve user
  configuration across installer updates and recheck mappings at integration.
- Require per-model context capacity evidence, output/reasoning reserves,
  safe compaction thresholds and current version-matched catalog metadata.
- Keep standalone CLI, bundled CLI and Desktop capability evidence separate.
  Desktop arbitrary custom model selection remains unverified; no real model
  receives production qualification from the synthetic transport PoC.
- Add a default-off, pure advisory failover planner bound to V2 classification.
  It returns `dispatched: false`; actual mixed-model CLI/Desktop execution,
  planner wiring, persistent handoff and live role qualification remain separate.

Verification procedure: [Issue #316 engineering plan](plans/issue-316-local-model-mapping.md).
Execution and review evidence stays in ignored `.work/verification/issue-316/`.
## Compatibility And Boundaries

Default-off retains baseline profiles and candidate qualification. Enabled mappings
require per-runtime provider, model, effort and context evidence. Desktop arbitrary
custom aliases and long-context acceptance remain unverified.

## Verification And Release Gate

Candidate verification and independent review are recorded in the Issue #316
ignored evidence directory; source/package parity is offline evidence only. Preserve
separate human gates.

Commit, content push, PR creation, merge, annotated tag, GitHub Release and
installation each require their applicable authorization and gate. Publication
truth must be read from the exact tag and non-draft, non-prerelease Release.

## Traceability

Issue #316: <https://github.com/jeffery777/codex-dev-skills/issues/316>

Branch: `codex/issue-316-ab-foundation`. No PR, merge,
annotated tag or Release is asserted by this preparation record.
