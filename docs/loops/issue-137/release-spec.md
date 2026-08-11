# Issue #137 v0.12.0 Release Closure

## Objective

Publish the reviewed V3-A proposal-only baseline as v0.12.0 through one bounded
release-preparation change and a separately authorized annotated tag and
GitHub Release. Keep Issue #135 / PR #136 planning-only and do not implement
V3-B, Agent Memory, or V3-C.

## Verified Starting Baseline

- Accepted main at task bootstrap: `b48ea6edb065c40bd798dd3d428b69f33cfb8315`.
- V3-A implementation: Issue #133 / merged PR #134.
- V3-B and Agent Memory roadmap: Issue #135 / merged PR #136, docs-only.
- Latest formal Release at task bootstrap: v0.11.1.
- Remote v0.12.0 tag at task bootstrap: absent.
- `catalog.yaml` and `install.sh`: already 0.12.0.

Mutable Git and GitHub state must be re-read at every merge and publication
gate. These facts are starting evidence, not authority to publish.

## Release Candidate Boundary

The candidate may finalize release notes, README and roadmap/program status,
release metadata contract tests, and Issue #137 planning/review receipts. It
must not change runtime implementation, public contract semantics, fixtures,
eval behavior, installer behavior, dependencies, workflows, or release content
after v0.12.0.

The final repository wording describes the intended published state. It may be
merged only as part of an approved merge-to-publication sequence that binds an
annotated `v0.12.0` tag and non-draft/non-prerelease GitHub Release to the exact
reviewed release merge commit. If publication cannot safely follow merge, stop
instead of knowingly leaving main in a false published state.

## Definition Of Done

- Release notes have the actual release date, final traceability, compare URL,
  rollback, verification, privacy, and authority boundaries.
- README, roadmap, Operational Evidence docs, catalog, installer, and release
  metadata tests agree on v0.12.0.
- V3-A remains proposal-only; V3-B, M0 qualification, M1/M2, PlugMem/Mem0,
  V3-C, activation, promotion, and deployment remain unperformed.
- Local and hosted verification pass on the exact reviewed head with no
  unresolved review findings.
- The release PR is merged with expected-head-SHA protection only after the
  final human publication decision.
- Annotated tag and GitHub Release point to the exact reviewed merge commit and
  public evidence is recorded in Issue #137.

## Stop Conditions

- accepted main, release ownership, tag, or Release state conflicts;
- a runtime/public-contract change becomes necessary;
- release notes exceed verified merged behavior;
- verification, hosted CI, review, privacy, or exact-head evidence fails;
- merge cannot be followed by the approved exact tag and Release sequence;
- an existing v0.12.0 tag would need deletion, movement, or replacement;
- recovery would be destructive or ambiguous.

## Human Gates

Commit, push, and draft-PR preparation remain bounded delivery actions. Ready
transition, merge, annotated tag push, and GitHub Release publication require
the final exact-head evidence and explicit human authorization. Tag/Release
deletion, tag movement, history rewrite, deploy, activation, promotion, and
global installation remain outside this task.
