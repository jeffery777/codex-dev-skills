# Release-State Contract

Use this provider-neutral contract for release preparation, release-sensitive
review, and publication readiness. It separates durable repository state from
mutable provider publication state so a successful publication does not
require a later tracked coherence patch.

## State Roles

### Repository Source And Package Version

`catalog.yaml` is the canonical offline source/package version. `install.sh`
and `plugin/codex-dev-skills/.codex-plugin/plugin.json` must match it exactly.
README prose, roadmap prose, release-note status, tags, and Releases do not
define this local version.

### Candidate Preparation

The release-notes file derived from the source/package version is a
point-in-time candidate-preparation record. Its Issue, branch, verification,
review, merge-readiness, or candidate wording does not prove publication.
Preparing or merging a candidate does not authorize an annotated tag or
provider Release.

### Publication Truth

The corresponding annotated tag is durable publication identity. When
repository policy selects a provider publication profile, its native Release
metadata is additional publication truth. Publication-sensitive checks must
verify the exact repository, tag object, dereferenced commit, provider Release
target, draft state, and prerelease state through that provider's control
plane. A tracked file must not mirror a mutable "latest" or current-publication
pointer.

Ordinary repository validation is offline. It must not access the network,
scrape GitHub, or fail merely because GitHub metadata is unavailable. Offline
validation proves source/package parity and candidate structure, not
publication.

### Active Guidance

README, roadmap, and release-readiness guidance describe stable capabilities
and these state roles. They must not assert a mutable current published version
or current development candidate. When a maintainer needs current publication
state, active guidance directs them to the annotated tag and configured
provider Release metadata.

### Historical Release Notes

Every checked-in release-notes file is a point-in-time historical record after
its candidate preparation. Candidate or pre-publication wording is preserved
after publication. A later release does not backfill an older note. Modifying
an existing note requires an independently verified factual or safety defect,
an explicit in-scope justification, and review that preserves its historical
role.

## Release-Sensitive Review

Reviewers must classify every relevant assertion as source/package version,
candidate preparation, publication truth, active guidance, or historical
record. A review must not declare readiness only because repository tests pass.

Before a tag or Release mutation, verify repository identity, branch, exact
HEAD, the proposed tag and Release payloads, conflicting or absent remote
state, and transition safety: active guidance must remain true if publication
succeeds. This is a preview and conflict check, not publication evidence.

After each separately authorized publication mutation, read back the annotated
tag object and dereferenced commit plus configured provider Release target,
draft state, and prerelease state through its normal control plane. Publication
is incomplete when a required readback is absent or conflicts with the approved
payload; a later tracked-file patch is not a substitute for resolving provider
state.

Before ordinary PR readiness, run the offline release-state validator. If
active guidance claims mutable publication state, if source/package versions
diverge, or if historical notes are rewritten only to reflect a later
publication event, the change is blocked.

The offline validator is a bounded structural and lexical regression control,
not a semantic reviewer or Git-history attestation. Reviewers still inspect the
base-to-head diff, classify all five roles, detect synonymous or contradictory
publication claims, and justify any historical-note modification.

## Authority Boundary

This contract does not authorize commit, push, pull request creation, merge,
tag creation, provider Release publication, deployment, comments, reviews,
labels, cleanup, or another external write. Each action retains its separate
human gate.
