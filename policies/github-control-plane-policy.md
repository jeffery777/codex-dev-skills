# GitHub Control Plane Policy

Use this policy whenever a shared workflow reads or mutates GitHub state. It
applies equally to Codex CLI and Codex Desktop entrypoints; runtime adapters
must not duplicate or weaken it.

## Control Plane Order

1. Read local repository state with local `git`: checkout, branch, upstream,
   remotes, worktrees, index, working tree, commits, and base-to-head diffs.
2. Use the installed GitHub plugin or connector as the primary GitHub control plane
   for repository metadata, Issues, pull requests, comments, reviews,
   labels, checks, workflow metadata, and every platform mutation it exposes.
3. Use `gh` only when the GitHub plugin or connector does not expose the exact
   required operation, or when that operation fails because the connector's
   granted permission is insufficient.

A repository habit, an existing shell snippet, convenience, or familiarity
with `gh` is not enough to bypass an available connector operation.

## Fallback Classification

Before using `gh`, record one of these reasons:

- `connector-operation-unavailable`: the active GitHub plugin has no callable
  for the exact required operation;
- `connector-permission-insufficient`: the callable exists but the connector
  reports that its granted GitHub permission cannot perform the operation.

Do not treat target mismatch, ambiguous repository identity, validation
failure, authentication conflict, rate limit, transient service failure, or an
unreviewed schema change as permission insufficiency. Classify those failures
and stop or retry through the same control plane only when that is safe.

After a justified fallback, verify the same exact owner/repository, Issue or
pull-request number, branch/head SHA when relevant, authentication context,
and result that the connector path would have required. Report the fallback
reason in the delivery or readiness evidence.

## Mutation And Authority Boundary

Connector-first does not authorize a GitHub write. Creating or editing Issues,
opening or updating pull requests, posting comments or reviews, changing
labels, rerunning checks, merging, tagging, and publishing Releases still
require the exact authority and human gate defined by the active workflow.

Local `git` remains the normal control plane for branch creation and working
tree state. Commit, push, force updates, tag creation, and destructive Git
operations retain their separate authority and safety requirements.

## Dependency Unavailable

If neither an applicable GitHub connector operation nor an authenticated,
authorized `gh` fallback is available, continue only with local Git evidence
that is sufficient for the current read-only task. Mark GitHub metadata as
unverified and stop before any platform-dependent claim or mutation. Do not
scrape browser UI or inspect private application state as a substitute.
