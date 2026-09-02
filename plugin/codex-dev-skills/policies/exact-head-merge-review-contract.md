# Exact-Head Merge-Review Contract

Use this provider-neutral contract after a change request exists, or whenever a
workflow reports formal merge content readiness. A change request may be a
GitHub pull request, GitLab merge request, another forge-native review object,
or a locally identified base-to-head range when no provider adapter is
configured.

The contract prevents implementation evidence from being mistaken for review
of the immutable content that is actually proposed for merge. Provider-native
enforcement is a separate, optional profile and must never become the source of
truth for code, documentation, or version coherence.

## Evidence Roles

Pre-commit code, documentation, deep, and security reviews prove properties of
the content they inspected. They may be reused when their source revision,
scope, and assumptions still match, but their verdict does not satisfy
exact-head Merge Review.

Exact-head Merge Review is a complete base-to-head integration review. Bind it
to:

- repository identity and change-request identity when one exists;
- exact base, head, and merge-base revisions;
- deterministic diff or range identity;
- review mode and applicable Definition of Done;
- verification commands and results;
- findings, dispositions, and residual risk; and
- code, documentation, configuration, package, and version coherence.

A local report, chat handoff, worker summary, goal state, provider status, or
earlier review is not a substitute for this evidence.

## Content-Coherence Review

Every exact-head Merge Review must inspect the final complete range rather than
only the newest commit or files that happen to be documentation-dominant.
Reviewers must:

1. run deterministic offline repository, version, package, schema, generated-
   artifact, or documentation checks that the repository provides;
2. compare user-visible documentation claims with the code, configuration,
   specification, tests, and observed behavior that support them;
3. detect stale names, commands, paths, feature states, compatibility claims,
   release scope, and superseded descriptions;
4. confirm that changed user-visible behavior has corresponding documentation
   or record why no documentation change is required; and
5. classify every finding and retain a durable disposition before content
   readiness passes.

Tests alone do not prove semantic documentation coherence. Human or model
review alone does not replace deterministic checks for facts that can be
validated mechanically.

## Required Content Transition

The successful provider-neutral transition is:

```text
CHANGE_REQUEST_CREATED
  -> EXACT_HEAD_VERIFICATION_PASSED
  -> EXACT_HEAD_CONTENT_REVIEW_PASSED
  -> CONTENT_READINESS_READY
  -> HUMAN_MERGE_AUTHORIZED
```

When no forge-native change request exists, the first state may instead be
`EXACT_RANGE_SELECTED`. Do not skip a state or infer content readiness from a
later provider status. Merge authorization remains a separate human or
accepted platform action; review evidence must always state that it does not
authorize merge.

A new push or a change to repository identity, change-request identity, base,
head, merge base, diff identity, required verification, finding disposition,
or coherence evidence returns the content flow to `REVIEW_REQUIRED` at the
earliest affected state. Every changed head requires a new complete
base-to-head Merge Review.

## Separate Readiness Dimensions

Report these dimensions independently:

- `content_review`: `PASSED | BLOCKED | NEEDS_HUMAN_DECISION`
- `platform_enforcement`: `VERIFIED | UNVERIFIED | BLOCKED | NOT_CONFIGURED`

`content_review: PASSED` means the exact reviewed content satisfies the
provider-neutral contract. It does not claim that a forge pipeline, discussion,
approval rule, check, receipt, ruleset, or merge box was inspected.

`platform_enforcement: NOT_CONFIGURED` is valid when repository policy does not
select a provider profile. `UNVERIFIED` means a profile or relevant provider
state exists but current evidence was not read successfully. If repository
policy requires a provider profile, `UNVERIFIED` or `BLOCKED` prevents the
formal merge gate from reporting overall readiness without erasing otherwise
valid content-review evidence.

## Provider Profiles

Provider profiles are opt-in repository overlays. A profile may add pipeline,
review-thread, approval, receipt, status-check, protected-branch, release, or
final live-readback requirements. It must:

- name the selected provider and exact repository;
- define its normalized evidence and staleness rules;
- preserve this contract's exact-head and coherence requirements;
- distinguish provider verification from content review and merge authority;
- fail closed for claims that require unavailable or stale provider evidence;
  and
- avoid requiring its provider objects when the profile is not selected.

GitHub repositories that select the existing App/check/receipt/ruleset
enforcement use `policies/github-exact-head-enforcement-profile.md`. A GitLab
CE repository may use this content contract without GitHub, and may add a
separate GitLab profile for MR head, pipeline, discussion, approval, protected-
branch, and final readback evidence when its deployment exposes those controls.

## Review And Remediation Scope

After a finding is fixed, rerun code review and Security Diff Scan over the
smallest scope that proves the fix and affected boundaries. Record why
unchanged prior evidence remains applicable. Escalate when the fix changes
shared contracts, data or trust boundaries, generated artifacts, packaging,
documentation claims, or assumptions of earlier evidence.

Proportional fix review never permits reusing an old exact-head verdict for a
new head. Clean internal reviews and scans may advance automatically to later
read-only or already-authorized stages. Stop only for an actual human decision,
missing authority, environment or permission failure, material ambiguity or
risk, destructive action, or an unauthorized external write.

## Authority Boundary

This contract does not authorize commit, push, change-request creation,
platform comments or reviews, merge, tag creation, Release publication,
deployment, provider-policy mutation, or another external write.
