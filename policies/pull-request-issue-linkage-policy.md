# Pull Request To Issue Linkage Policy

Every ready-for-review pull request must identify at least one open Issue in
this repository that the pull request will close.

## Required Form

Place one standalone closing line in the pull request body for each linked
Issue:

```text
Closes #123
```

`Fixes` and `Resolves`, including GitHub's supported grammatical variants, are
also accepted. Repository Issue and pull-request numbers share one sequence;
the numbers do not need to match.

## Validation Boundary

- Draft pull requests may omit the link while they are being prepared.
- Opening, editing, reopening, synchronizing, or marking a non-draft pull
  request ready runs the linkage check.
- Every closing reference must resolve to an open Issue in this repository.
- A pull request may name at most 20 unique closing Issues so one event cannot
  cause unbounded metadata lookups.
- A nonexistent number, closed Issue, pull-request number, or another
  repository does not satisfy the check.
- Release, maintenance, documentation, and implementation pull requests follow
  the same rule. Create the bounded Issue before the implementation branch.

The workflow uses the `pull_request_target` metadata event with read-only
`contents`, `issues`, and `pull-requests` permissions. It checks out only the
trusted base SHA and does not execute the pull request head. The validator
reads the event payload and Issue metadata; it does not edit Issues, submit
reviews, set labels, approve, merge, release, or perform other platform writes.

## Authority Boundary

A valid link proves traceability only. It does not prove implementation,
verification, review closure, completion, merge readiness, authorization, or
release readiness. GitHub's normal closing-keyword behavior closes the Issue
only after the pull request is merged into the default branch.

Human gates, review policies, external-write authorization, exact-head merge
review, and repository/Git completion evidence remain independently required.
