# Issue #143 v0.13.0 V3-B Release Closure

## Objective

Publish the reviewed V3-B isolated candidate-evaluation baseline as v0.13.0
through one bounded release-preparation change followed by an exact
merge-commit annotated tag and non-draft/non-prerelease GitHub Release.

## Verified Starting Baseline

- Accepted main at task bootstrap:
  `a70db2ce1b6f1330b96d60bbdb98e2966a6afea9`.
- V3-B implementation: Issue #141 / merged PR #142.
- Latest formal Release at task bootstrap: v0.12.1.
- Remote tag and GitHub Release v0.13.0 at task bootstrap: absent.
- No open Issue or PR collided with this release closure before Issue #143.
- `catalog.yaml` and `install.sh` identified the prior version 0.12.1.

Mutable Git and GitHub state must be re-read before branch, merge, tag, and
publication. These facts are starting evidence, not publication evidence.

## Release Candidate Boundary

The candidate may change version metadata, release notes, README and
roadmap/program status, release contract tests, and Issue #143 planning/review
receipts. It must not change runtime behavior, public contract semantics,
fixtures, eval behavior, dependencies, workflows, installer behavior beyond
the version string, or release content after v0.13.0.

The repository wording describes the intended published state. Merge is
permitted only when the authorized exact merge/tag/Release sequence can follow.
If publication cannot safely follow merge, stop rather than knowingly leaving
main inconsistent with public Release state.

## Release Truth

- Product version: `0.13.0`.
- Annotated tag and GitHub Release: `v0.13.0`.
- Feature scope: merged V3-B Issue #141 / PR #142 only.
- V3-B retains `memory-off` as the default, accepts only bounded V2b-validated
  advisory context, never runs arbitrary candidate code, and cannot promote or
  perform an external write.
- Memory M1/M2, SQLite/FTS5 backend implementation, PlugMem/Mem0,
  provider/MCP integration, V3-C, deployment, activation, and promotion remain
  absent.

## Definition Of Done

- Release notes include date, verified scope, qualification, exclusions,
  rollback, final traceability, and compare URL.
- README, roadmap/program docs, release readiness, catalog, installer, and
  release metadata tests agree on v0.13.0.
- Local and hosted exact-head verification pass with no unresolved review or
  security/privacy finding.
- Release PR is merged using expected-head-SHA protection.
- Annotated tag and GitHub Release bind the exact reviewed release merge
  commit, and latest-Release evidence is verified.
- No deployment, activation, promotion, global installation, M1/M2, PlugMem,
  Mem0, or V3-C action occurs.

## Stop Conditions

- accepted main, ownership, version, tag, or Release state conflicts;
- release notes exceed verified merged V3-B behavior;
- runtime or public-contract behavior would change;
- verification, hosted CI, review, privacy, or exact-head evidence fails;
- merge cannot be followed by the authorized exact tag and Release sequence;
- an existing v0.13.0 tag or Release would need deletion, movement, or
  replacement;
- recovery is destructive or ambiguous.

## Authority

The user's Issue #143 release request authorizes the bounded release delivery,
including reviewed commit/push/PR, ready transition, expected-head merge,
annotated v0.13.0 tag push, and non-draft/non-prerelease GitHub Release only
after every exact gate passes. It does not authorize force push, history
rewrite, tag/Release replacement or deletion, deployment, activation,
promotion, global installation, Memory work, V3-C, or destructive recovery.
