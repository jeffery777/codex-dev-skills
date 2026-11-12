# Issue #395: v0.41.0 preparation

## Goal And Sources

Prepare the minor source/package candidate from main
`1314bcd15fbe63d1abceab06e97ca64ab4dbf8b6` after verified Issue and remote
branch creation. The published v0.40.0 baseline dereferences annotated tag
object `19b64abefbb2501dee880dec673039af10ac6171` to
`e2210d49507ef24859deb7924598f4ba0424d518`; Release 438647297 was read back as
non-draft and non-prerelease. This is point-in-time source evidence, not a
tracked current-publication pointer.

The complete merged feature range contains 17 commits and 37 files. Include
PRs #388/#389, #390, #392 and #394. Minor is appropriate because the package
adds public App Server operations and a Desktop-to-CLI installation dependency.
Release preparation itself changes no runtime executor, gate policy, workflow,
schedule, Core or child authority. Unfinished #385 work stays separate.

## Candidate And Source Binding

Align catalog.yaml, install.sh and the plugin manifest at 0.41.0. Keep the
marketplace pointed at the narrow plugin package. Update README, roadmap,
changelog and the new release note, preserving all historical notes.

Review and freeze payload A before its real commit. Append only that actual
SHA as catalog record 20 in B; retain the prior 19 records exactly. No synthetic
mapping or placeholder revision belongs in the formal registry. Verify all
artifact bytes, modes, inventories, dependencies and immutable source identity.
A is not install-ready while its new catalog digest remains unregistered.

## Verification And Review

Freeze the historical 0.39.0-to-0.40.0 test to its real 0.40.0 source. New
current-target tests use each of the five registered 0.40.0 payloads, verify
all-managed-group requirements, installed helper, Core, profiles, unmanaged
state and downgrade restoration, and include one representative receipt
promotion rollback. Keep earlier historical mapping and fault tests.

Use scripts/project-python in each clean verification checkout. Run fresh
release-state and package checks, reproducible catalog generation, migration
cases, appropriate complete candidate unit tests and repository validation.
Report original failures, replacements and environment skips separately.
Previous #392 CI is historical input, not release-candidate verification.

Obtain independent release-sensitive code/docs review and impact-based
security applicability analysis. Classify source/package version, candidate
preparation, publication truth, active guidance and historical records. After
PR creation, use complete exact-head Merge Review and current provider checks
for readiness; precommit reviews do not replace that evidence.

## Boundaries And Later Gates

Preserve native-first selection, the separate exec route, explicit workspace
write authority and writer ownership, and the App Server network/integration,
recursion and publication limits. Existing isolated runtime and Desktop-placement
evidence does not qualify arbitrary versions or a production project. Issue
#251 and the historical identity-drift cause remain unresolved. Four earlier
CI environment skips remain limitations until matching evidence replaces them.

Commit, push and Draft PR preparation are within the approved scope. Ready,
merge, annotated tag, Release publication, user installation and live production
acceptance require separate authority and matching evidence. This plan grants
none of those later permissions. Full ASD-STE100 conformance is unverified.
