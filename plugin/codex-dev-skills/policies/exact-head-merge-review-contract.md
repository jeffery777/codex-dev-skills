# Exact-Head Merge-Review Contract

Compatible provider-neutral entry for an existing change request or formal merge
content readiness. Follow [fixed Core loading](core-contract-loading.md) and read
full Core exact-head/evidence and review/security. A local exact range is available
when no forge adapter is configured; shared Markdown is not a validator or
provider-enforcement implementation.

## Evidence Roles

Core [exact-identity](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md#exact-identity)
binds complete base-to-head review to repository/change request, exact
base/head/merge-base, deterministic range/diff, mode/DoD, commands/results,
findings/dispositions/residual risk and code, documentation, configuration, package, and version coherence.
Pre-commit evidence may be reused while matching; their verdict does not satisfy
exact-head Merge Review. Keep existing report/template/validator field names.

## Content-Coherence Review

Read Core [exact-coherence](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md#exact-coherence).
Inspect the final complete base-to-head range, run applicable deterministic
offline checks and compare claims against code/config/spec/tests/observations.
Tests do not replace semantic coherence; review does not replace mechanical facts.

## Required Content Transition

Core [exact-transition](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md#exact-transition)
defines the duties. Existing Codex evidence identifiers remain:

    CHANGE_REQUEST_CREATED
      -> EXACT_HEAD_VERIFICATION_PASSED
      -> EXACT_HEAD_CONTENT_REVIEW_PASSED
      -> CONTENT_READINESS_READY
      -> HUMAN_MERGE_AUTHORIZED

Without a forge, use EXACT_RANGE_SELECTED. Identity/verification/finding/coherence
drift returns to REVIEW_REQUIRED. Every changed head requires a new complete
base-to-head Merge Review. Review evidence does not itself authorize merge;
existing explicit authority does not need to be asked again.

## Separate Readiness Dimensions

Core [exact-dimensions](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md#exact-dimensions)
separates content_review and platform_enforcement from operation authority.
Preserve PASSED/BLOCKED/NEEDS_HUMAN_DECISION and
VERIFIED/UNVERIFIED/BLOCKED/NOT_CONFIGURED. Content PASSED does not assert provider
objects were inspected; an unverified/blocked required profile blocks overall
readiness without erasing valid content evidence.

## Provider Profiles

Profiles are project-selected overlays, never inferred from the installed skill.
The selected GitHub implementation is
[github-exact-head-enforcement-profile](github-exact-head-enforcement-profile.md).
A GitLab CE repository may use this content contract without GitHub and choose its
own MR/pipeline/discussion/approval/protection/final-readback profile. Keep source
truth, content, provider evidence, live freshness and operation authority separate.

## Review And Remediation Scope

Core [review-findings](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-findings)
and [review-security](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-security)
define proportional fix review over the smallest scope that proves the affected
boundary, and necessary scan applicability. Record why unchanged evidence applies.
New heads still need complete range review. Security Diff Scan is assessed from
actual final diff and concerns; not applicable requires scope/rationale and is not
Passed. Clean internal reviews/scans may advance to authorized stages, subject to
real decision, authority, environment, permission, risk and destructive-action gates.

## Authority Boundary

Read Core authorization/stops. This policy and its tools do not authorize commit,
push, PR/MR, comments/reviews, merge, tags, Releases, deploy or provider-policy changes.
The [fixed-source obligations](../vendor/engineering-workflow-core/contracts/exact-head-and-evidence.md#exact-pinning)
do not enable downloads, updates, installations or another runtime.
