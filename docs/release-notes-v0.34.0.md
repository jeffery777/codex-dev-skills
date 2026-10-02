# Release Notes: v0.34.0

Status: release candidate prepared through Issue #316.

Prepared on 2026-10-02 for Issue #316, branch
`codex/issue-316-local-model-mapping`. This is a point-in-time preparation
record, not evidence of an annotated tag, published Release, or installation.

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

Branch: `codex/issue-316-local-model-mapping`. No PR, merge,
annotated tag or Release is asserted by this preparation record.
