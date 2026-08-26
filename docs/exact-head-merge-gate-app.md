# Exact-Head Merge Gate App

This document defines the hosted control-plane boundary for the reusable
`exact-head-merge-readiness/v2` contract. It complements, but does not replace,
the offline `exact-head-merge-review/v1` evidence contract.

## Purpose

`Exact-Head Merge Readiness` is a required GitHub check that prevents a pull
request from merging while its exact-head Merge Review evidence is absent,
stale, malformed, or attached to another commit. It records readiness only; it
does not approve, merge, enable auto-merge, tag, publish a Release, deploy,
post a comment, resolve a review thread, or modify repository contents.

The check is published by a dedicated GitHub App, not the shared GitHub Actions
App identity. Its check context is exactly `Exact-Head Merge Readiness`.

## Trusted Controller

The collector workflow is stored and executed from the trusted default branch.
It reads GitHub metadata, normalizes a bounded snapshot, validates it offline,
and creates or updates the single dedicated-App check run for the current live
`pull_request.head.sha`. It must re-read the pull request before reporting
success and fail closed if the repository, PR number, base, head, merge base,
or range identity changed. Its compact App-owned `external_id` stays below the
GitHub limit and is the durable pointer to the one current receipt comment for
that repository, PR, and head. Relevant events are grouped by live head; unrelated
comments are no-ops, and scheduled reconciliation repairs coalesced events.
The matrix and concurrency key carry the platform-read head SHA, not just the
PR number. Before success, the controller also proves through a bounded commit-
to-pulls read that this head belongs to exactly one open PR; a shared head is
failed closed because GitHub required checks are commit-scoped while receipts,
bases, merge bases, findings, and threads are PR-scoped.

The controller must not checkout, import, execute, cache, or consume artifacts
from PR-head code. In particular, it must not use a default-branch event's
`GITHUB_SHA` as a proxy for the PR head. The separate Repository Validation
workflow uses the fork-safe `pull_request` event, `contents: read`, no secret,
and no persisted checkout credential. The controller requires its policy-
pinned Git blob at both the live PR base and head before accepting the result.
It shares no artifact, cache, workspace, runner, or token with the credential-
bearing controller.

The App has only metadata/read, pull-requests/read, issues/read, actions/read,
and checks/write permissions. Store its credentials in a protected environment
that only trusted default-branch workflow code may use. Registration,
installation, protected-environment configuration, and credential placement
are independent human gates.

For a single-maintainer repository, do not add an environment required-reviewer
rule to this event-driven controller: doing so queues every relevant receipt or
drift event behind manual deployment approval. Restrict deployment branches to
the trusted default branch instead. The secret boundary comes from trusted
workflow code and the absence of any PR-content execution/data path in the
credential-bearing job, not from exposing secrets to an untrusted job and
asking a reviewer to approve it.

## Evidence Contract

The normalized envelope has exactly these top-level fields:

```text
contract
receipt
platform_snapshot
gate
```

`contract` is `exact-head-merge-readiness/v2`. The authoritative receipt is
the complete body of exactly one GitHub issue comment, represented as strict
JSON. Every receipt carries a positive `receipt_sequence`; the highest unique
sequence, capped at signed 64-bit maximum `9223372036854775807`, for the exact
head supersedes the App-owned pointer. The pointer keeps
the current ID/sequence as a tombstone, so deletion or invalid edit cannot fall
back to an older clean receipt. The collector reads at most 500 comments across
bounded pages and fails closed above that explicit capacity. It never scans
Markdown or sorts IDs across unrelated platform object types. Human-readable
Markdown can link to the JSON comment, but it is not an input contract.

This repository's operational policy accepts receipt comments only when
GitHub reports `author_association: OWNER`. Repository association is the
receipt-authority boundary, not merely an anti-spam hint: broadening it to
`MEMBER` or `COLLABORATOR` is a separate policy and security decision because
it would let that role self-attest findings and dispositions. The generic
collector supports those platform associations only when an explicit trusted
repo-local policy deliberately selects them.

The collector validates and binds:

- repository and positive PR number;
- exact base, head, merge-base, and versioned canonical range-identity digest;
- current open, non-draft, mergeable PR state;
- every required hosted CI workflow ID/name/path/event and Git blob, run and
  attempt, the trusted `exact-pr-head/v1` run-name contract that embeds the
  platform PR number and head SHA, successful conclusion, and exact
  repository/run-bound details URL;
- zero unresolved review threads plus its canonical digest;
- closed findings and recorded dispositions plus their canonical digest;
- receipt ID, URL, whole-body digest, authority, and `merge_authorized: false`;
- collector workflow/run, custom check/run, dedicated App identity, exact head,
  and successful conclusion.

The upstream required-CI set must exclude `Exact-Head Merge Readiness` itself.
The validator stays offline and does not authenticate, call GitHub, post a
receipt, or authorize a merge; the control plane supplies the normalized input.

The collector has no implicit policy location. Every invocation must pass an
explicit repo-local `--policy`; the hosted workflow uses
`.github/exact-head-merge-readiness-policy.json`. That operational policy pins
this repository's workflow ID and is intentionally not installed into the
generic plugin/template package as a misleading cross-repository default.

The platform guarantee has two layers. GitHub rules enforce the live-head
required check, strict up-to-date policy, and resolved review conversations at
merge time. Receipt, finding, base/merge-base snapshot, range digest, and
controller identity are an event-driven projection. Relevant platform events
and a five-minute scheduled reconciliation rebuild authoritative live state;
head-scoped concurrency can coalesce pending events and is not the source of
truth. Scheduled reconciliation handles at most 250 open PRs per run, below
GitHub Actions' 256-job matrix limit, and fails
visibly rather than truncating a larger collection. The schedule has no
completion-time SLA. Before evaluating comments or other drift-prone evidence,
the controller changes any existing success check to `in_progress`; after
publishing success, it reads the completed check back and compares its head,
App, context, details URL, pointer, conclusion, title, and evidence digest.
This design does not claim an atomic
transaction between editing an issue comment and clicking Merge. Achieving
that stronger property would require a GitHub-native pre-merge predicate or
App-controlled merge authority, neither of which this contract grants.

Repository Validation `workflow_run` handling subscribes to both `in_progress`
and `completed`. A rerun therefore invalidates an earlier success while hosted
CI is running, and the head-filtered bounded run query accepts only a successful
latest run for the exact head before readiness can return to green.

## Ruleset Rollout

Use the existing default-branch ruleset. It must have no bypass actors and
require pull requests, deletion/non-fast-forward protection, resolved review
conversations, stale-review dismissal, strict required-check policy, and the
dedicated-App `Exact-Head Merge Readiness` check. Hosted CI provenance is an
input to that check; the shared GitHub Actions job check is not independently
authoritative.

Rollout has independent authority gates:

1. Merge the reviewed controller while the ruleset remains disabled.
2. Separately authorize App registration/installation and protected-environment
   configuration.
3. Run a canary PR, then read back the dedicated App integration ID from its
   exact custom check.
4. Separately authorize a full ruleset update that remains `disabled`, and read
   back its complete payload.
5. Prove head, CI, finding, thread, receipt, digest, and App-identity drift
   cases fail closed.
6. Separately authorize changing only `enforcement` to `active`, then verify a
   fresh PR's merge box.

Do not add the required check before the canary establishes the App identity.
Do not use a GitHub Actions integration ID in place of the dedicated App. A
single-owner repository can deadlock if it requires its author to self-approve;
approval-count policy remains a separate human decision and is not a substitute
for the App-backed exact-head check.

The workflow-definition blob is pinned in the policy at both PR base and head.
Therefore an ordinary PR cannot self-upgrade the required workflow or its pin
after enforcement is active. Maintenance must be a separate authorized gate:
disable the ruleset and read back that state, merge the reviewed workflow and
matching policy-blob update, run a canary, then separately reactivate and read
back the ruleset. Leaving enforcement active while changing either file would
make every upgrade PR permanently unready by design.

After the canary returns the dedicated App integration ID, the exact disabled
mutation preview for existing ruleset `21035619` is the following, with
`<DEDICATED_APP_INTEGRATION_ID_FROM_CANARY>` replaced by that read-back positive
integer and no other substitution. This is a preview, not mutation authority:

```json
{
  "name": "Restrict deletions_&Block force pushes",
  "target": "branch",
  "enforcement": "disabled",
  "bypass_actors": [],
  "conditions": {
    "ref_name": {
      "include": ["~DEFAULT_BRANCH"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": false,
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          {
            "context": "Exact-Head Merge Readiness",
            "integration_id": "<DEDICATED_APP_INTEGRATION_ID_FROM_CANARY>"
          }
        ]
      }
    }
  ]
}
```

At the ruleset human gate, reject the preview until the placeholder has become
an integer and the complete live ruleset is re-read. Update the full payload
with `PUT /repos/jeffery777/codex-dev-skills/rulesets/21035619`; do not patch a
partial rule list that could drop deletion or non-fast-forward protection.

## Verification

Run repository validation and the focused collector, validator, workflow, and
contract-document tests with `./scripts/project-python`. Hosted verification
must include a successful canary, an updated head, failing/stale CI,
base/merge-base/diff drift, open/closed/reopened findings and threads, edited
or deleted receipts, digest mismatch, wrong check/App identity, and a fork PR
secret-isolation check. After every authorized ruleset mutation, read back the
live complete payload through the connector-first GitHub control plane.
