# Merge Readiness Workflow

Runtime compatibility: shared

Use this workflow only when a formal branch readiness gate is needed before
change-request handoff, merge readiness, or final human approval.

When a pull request, merge request, another change request, or exact local
merge range exists, follow `policies/exact-head-merge-review-contract.md`.

For ordinary complete base-to-head quality and coherence review, use
`merge-review`. For high-risk, release-sensitive, or policy-required changes,
use `merge-review-deep`. This workflow consumes that review evidence; it is not
another review primitive and does not authorize an external write.

1. Confirm repository, change-request identity when applicable, exact
   base/head/merge-base revisions, changed files, and diff identity.
2. Read plans, DoD, current review evidence, deterministic verification,
   dispositions, and unresolved questions.
3. Require current exact-head review evidence. Pre-commit or prior-head review
   cannot supply the verdict.
4. Verify offline repository/version/package checks and explicit semantic code
   ↔ documentation coherence across the complete range.
5. Decide `content_review` as `PASSED`, `BLOCKED`, or
   `NEEDS_HUMAN_DECISION`.
6. Resolve the repository's provider enforcement profile independently. Report
   `platform_enforcement` as `VERIFIED`, `UNVERIFIED`, `BLOCKED`, or
   `NOT_CONFIGURED`. Do not require GitHub objects when the GitHub profile was
   not selected.
7. When the optional GitHub profile is selected, follow
   `policies/github-exact-head-enforcement-profile.md` and preserve all hosted
   CI, thread, receipt, dedicated-App check, ruleset, and final readback
   requirements. A required selected profile that is not `VERIFIED` blocks the
   overall formal gate without changing a valid content-review result.
8. For release-sensitive work, apply `policies/release-state-contract.md` and
   keep source/package version, candidate preparation, provider publication
   truth, active guidance, and historical records distinct.
9. Report Content Review, Platform Enforcement, and Overall Formal Gate
   separately. A changed head invalidates content review; provider drift
   invalidates only the affected provider evidence.
10. Stop before commit, push, change-request creation, merge, deployment,
    provider comments/reviews, publication, or another external write unless
    the exact action is already authorized.
