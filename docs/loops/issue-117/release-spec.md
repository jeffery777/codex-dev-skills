# Issue #117 v0.9.2 Release Closure

## Objective

Publish the already merged post-v0.9.1 runtime-compatibility work as v0.9.2
without implementing V2d-A or changing the accepted V3-A dependency order.

## Accepted Baseline

- Base tag: `v0.9.1`
- Runtime-interface refresh: Issue #113 / PR #114
- CLI session handoff: Issue #115 / PR #116
- Release closure: Issue #117
- Next feature milestone: V2d-A, proposed for v0.10.0

## Scope

- Set the installer and catalog version to `0.9.2`.
- Make README current-release and installer guidance match shipped behavior.
- Add v0.9.2 release notes covering PRs #114 and #116.
- Update roadmap and Operational Evidence handoff status without rewriting
  historical release notes or point-in-time receipts.
- Run full repository verification, documentation/formal review, release-only
  security diff review, exact-head merge review, tag creation, and GitHub
  Release publication.

## Out Of Scope

- V2d-A contracts or validators.
- V2d-B lineage, human-readable projection, or graph projection.
- V3-A proposal generation or candidate scoring.
- Runtime services, schedulers, daemons, databases, or graph engines.
- Installer behavior changes beyond the version value.

## Definition Of Done

- README, `install.sh`, `catalog.yaml`, and the current release-notes path all
  identify v0.9.2.
- Installer/catalog group descriptions remain aligned with runtime boundaries.
- Repository validation and the release-sensitive formal gate pass.
- The release-only security diff scan has no unresolved findings.
- A ready PR closes Issue #117 and merges without bypassing required checks.
- Tag `v0.9.2` and the GitHub Release point to the reviewed merge commit.

## Authority Boundary

Repository edits, verification, review, commit, push, PR creation, merge, tag,
and release publication are authorized by the maintainer for this bounded
release. Destructive cleanup, force updates, deployment, V2d implementation,
and any change to completion or promotion authority remain unauthorized.
