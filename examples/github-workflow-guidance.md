# GitHub Workflow Guidance Example

Use this example when a maintainer wants Codex to inspect or prepare GitHub issue, pull request, review, or check-run work while keeping platform writes explicit.

Runtime compatibility: plugin-dependent. This guidance requires an installed GitHub plugin or connector, with authenticated `gh` available only as a qualified fallback. Prefer the GitHub plugin or connector for PR metadata, issue comments, review threads, changed files, checks, and platform-side mutations. Use `gh` only when the plugin does not expose the exact needed operation or reports insufficient permission for it; record which condition required the fallback.

## Maintainer Request

```text
Use GitHub workflow guidance for this PR readiness task.
Read local git state first, then inspect the GitHub PR through the installed GitHub plugin or connector.
Summarize blockers, checks, review comments, and the smallest safe next action.
Do not post comments, submit reviews, request reviewers, rerun checks, label issues, merge, close issues, or perform any other platform write unless I explicitly authorize the exact action.
```

## Read-Only Flow

1. Inspect local git state, current branch, upstream, remotes, and diff before platform reads.
2. Verify the remote owner, repository, PR or issue number, and head SHA.
3. Use the GitHub plugin or connector for PR info, issue comments, review threads, changed files, checks, and workflow run summaries.
4. Use local git for working-tree facts and base-to-head diffs.
5. Treat chat summaries and stale review artifacts as context only until repository files and platform metadata confirm them.
6. Separate findings into local-code, documentation, CI, review-thread, and platform-policy categories.
7. Recommend the smallest safe next action and name the next human gate.

Read-only operations may include:

- fetching PR metadata, changed filenames, reviews, comments, and check summaries;
- comparing `origin/main..HEAD` with the PR changed-file list;
- reading issue context before choosing a local maintenance task;
- summarizing CI failure logs when the platform tool exposes them.

## Platform Write Gate

Stop before any GitHub write unless the maintainer has authorized the exact action. Platform writes include:

- posting issue, PR, or review comments;
- submitting a pull request review;
- requesting or removing reviewers;
- adding, removing, or replacing labels;
- resolving review threads;
- rerunning workflow jobs;
- closing or reopening issues;
- merging, closing, or retargeting pull requests.

Review evidence, gate evidence, or a readiness summary does not by itself authorize local commits, pushes, deploys, platform comments, review submissions, merges, or other external writes.

Before an authorized write, restate:

- target repository and PR or issue number;
- exact write action;
- current head SHA when the action depends on a branch state;
- reviewed files or threads;
- verification evidence;
- residual risk.

## Dependency Unavailable

If the GitHub plugin or connector is unavailable or lacks the exact operation,
classify that condition before considering authenticated `gh`. If neither path
is available, do not scrape browser state or local app internals as a
substitute. Report the missing dependency and choose the safest remaining
local-only path:

```text
GitHub platform metadata is unavailable in this runtime.
I can still inspect local git state and `origin/main..HEAD`, but PR comments, review threads, labels, and checks are unverified until a GitHub plugin, connector, or authenticated `gh` session is available.
```

CLI fallback examples:

```bash
git status --short --branch
git remote -v
git diff --name-status origin/main..HEAD
git diff --stat origin/main..HEAD
gh pr view --json number,title,state,headRefName,baseRefName,headRefOid,mergeable
gh pr checks
```

If `gh` is unauthenticated, classify that as a platform-auth failure instead of retrying with unrelated tools.

## Merge Readiness Pattern

For a PR merge readiness task:

1. Confirm local branch, base ref, head SHA, and changed files.
2. Run the repo-required local validation and review gates.
3. Treat pre-commit review as input evidence only; it cannot supply the
   exact-head Merge Review verdict.
4. Fetch GitHub changed files, comments, reviews, workflow runs, statuses, and
   unresolved threads, then bind them to the exact repository, PR, base, head,
   merge base, and diff identity.
5. Reconcile local evidence with platform evidence and validate the normalized
   `exact-head-merge-review/v1` snapshot offline with
   `./scripts/project-python scripts/validate-exact-head-merge-review.py <snapshot.json>`.
   When the repository configures hosted enforcement, also verify the
   `exact-head-merge-readiness/v2` envelope and its dedicated-App
   `Exact-Head Merge Readiness` check are attached to the live PR head. The
   authoritative receipt comes from a complete strict JSON body; never use
   Markdown scraping as the evidence contract.
6. Post a Merge Review receipt only when the maintainer explicitly authorizes
   that platform write, then read the receipt back and bind its digest.
7. Merge only when the maintainer explicitly authorizes merge, required
   dedicated-App readiness is successful, a final live readback still matches
   every receipt and gate binding, and no blockers remain. The controller must
   not execute PR-head code or include its own check in upstream required CI.

## Report Shape

```text
GitHub workflow summary:
- Repository: owner/name
- PR: #123
- Head SHA: abc123
- Dependency: GitHub plugin available
- Local diff: matches PR changed-file list
- Checks: no workflow runs reported
- Review threads: no unresolved blockers
- Exact-head gate: required only when configured; dedicated App identity verified
- Recommended next action: post merge review comment, then merge if authorized
- Human gate: platform write and merge require exact authorization
```
