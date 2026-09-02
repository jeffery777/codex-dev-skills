# GitHub Exact-Head Enforcement Profile

Select this optional provider profile only when repository policy requires the
GitHub App/check/receipt/ruleset enforcement model. It extends
`policies/exact-head-merge-review-contract.md`; it does not replace the
provider-neutral content review or authorize a GitHub write.

## Profile Transition

After `CONTENT_READINESS_READY`, this profile requires current GitHub evidence:

```text
EXACT_HEAD_CI_PASSED
  -> RECEIPT_PLATFORM_READBACK_CONFIRMED
  -> GITHUB_EXACT_HEAD_ENFORCEMENT_VERIFIED
```

Only then may `platform_enforcement` be `VERIFIED`. A new push or drift in the
repository, pull request, base, head, merge base, range identity, required CI,
finding disposition, unresolved review threads, receipt, check, source App, or
readback invalidates the affected provider evidence. Content evidence remains a
separate dimension and is invalidated only by the content contract's rules.

## Receipt And Snapshot

`exact-head-merge-review/v1` remains the advisory GitHub review-receipt
vocabulary. `exact-head-merge-readiness/v2` is the hosted, platform-enforced
normalized envelope with exactly `contract`, `receipt`, `platform_snapshot`,
and `gate` top-level fields. The complete strict JSON receipt is authoritative;
Markdown scraping must not reconstruct it.

The receipt and connector-read snapshot bind the exact repository and positive
pull-request number; positive receipt sequence; 40-hex base, head, and merge-
base SHAs; deterministic range digest; review mode; policy-pinned hosted CI;
open non-draft mergeable state; zero unresolved review threads; closed finding
dispositions with zero open `MUST-FIX`, `SHOULD-FIX`, and `NIT` findings;
complete receipt identifier, GitHub issue-comment URL and digest; readback time;
`receipt_authority: advisory_review_evidence`; and `merge_authorized: false`.

Each required-CI identity includes its policy-pinned workflow ID, name, path,
event and Git blob; run and attempt; policy context; trusted
`exact-pr-head/v1` display-title binding to the PR number and head SHA;
successful conclusion; and repository/run-bound details URL. The upstream
required-CI set excludes the readiness check itself.

The offline validator consumes already normalized data. It does not access
GitHub, authenticate a reviewer, create or publish a receipt, submit a review,
authorize merge, or replace final live readback. Source and plugin checkouts use
`scripts/validate-exact-head-merge-review.py`; filesystem installation uses the
same installed script with one explicit normalized JSON input path or bounded
stdin.

## Connector-First Control Plane

Follow `policies/github-control-plane-policy.md`. Read the live pull request,
CI, reviews, unresolved threads, receipt, and check identity through the
connector-first GitHub control plane. Repeat live readback immediately before
an authorized merge. Neither an earlier receipt nor a successful historical
check proves current platform enforcement.

## Hosted Collector Trust Boundary

The trusted default-branch collector resolves the live pull request and writes
the check explicitly to `pull_request.head.sha`; it never infers that SHA from
a default-branch event. It must not checkout, import, execute, cache, or consume
artifacts from PR-head code.

The collector uses a dedicated GitHub App with minimum metadata/read,
pull-requests/read, issues/read, actions/read, and checks/write permissions.
Protected credentials are available only to trusted default-branch workflow
code. Repository contents and compare endpoints use a distinct read-only
`GITHUB_TOKEN`; the App token has no contents permission, and identical token
selectors or values are rejected.

Fork pull requests may receive the same metadata evaluation, but no
pull-request-controlled code receives those credentials. A shared GitHub
Actions identity is not an adequate trust source for the readiness check.

Each relevant evaluation creates a fresh check run because completed checks are
immutable lifecycle history. Native latest selection for the exact context,
App, and head must identify that fresh check before evaluation and after
publication; older successes cannot substitute. The authoritative prior check
retains the compact App pointer and receipt sequence tombstone, preventing the
same ID and sequence from silently replacing a selected receipt. Both success
and failure publication require exact completed-check and native-latest
readback. A malformed prior pointer is superseded by a fresh verified failure
rather than leaving an older success authoritative. Historical same-context
check runs are expected, and readiness never depends on permanent history
beyond GitHub's per-suite 1,000-run limit.

This is an event-driven projection rather than an atomic transaction with the
Merge click. A stronger receipt/finding guarantee would require a GitHub-native
pre-merge predicate or App-controlled merge path, which remains outside this
profile's authority.

## Ruleset Enforcement

When selected, the GitHub ruleset is the enforcement point. It requires pull
requests, blocks deletion and non-fast-forward updates, requires resolved
review conversations, dismisses stale approvals after pushes, enables strict
required checks, preserves the repository validation and closing-Issue checks,
and binds `Exact-Head Merge Readiness` to the dedicated App integration ID. It
has no bypass actors.

Approval-count policy remains a separate human decision because a single-owner
repository can deadlock on self-approval; it is not a substitute for the
App-backed exact-head check.

Rollout remains separately authorized: review trusted controller code; install
and protect the App; run a canary; read back the App integration ID; update the
ruleset while disabled; prove documented drift cases fail closed; then activate
only the reviewed enforcement field and verify a fresh pull-request merge box.
Do not require the readiness check before the canary identifies its App.

## Authority Boundary

This profile does not authorize connector or `gh` fallback use, receipt
publication, check creation, App installation, secret or environment changes,
ruleset mutation, commit, push, pull-request creation, merge, tag creation,
GitHub Release publication, deployment, or another external write.
