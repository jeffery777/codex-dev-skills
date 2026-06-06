# GitHub Workflow Guidance Example

Use this example when a maintainer wants Codex to inspect or prepare GitHub issue, pull request, review, or check-run work while keeping platform writes explicit.

Runtime compatibility: plugin-dependent. This guidance requires an installed GitHub plugin, connector, or authenticated platform tool such as `gh`. Prefer the GitHub plugin or connector for PR metadata, issue comments, review threads, changed files, checks, and platform-side mutations. Use `gh` only when the plugin does not expose the needed read or the repository workflow already relies on it.

## Maintainer Request

```text
Use GitHub workflow guidance for this PR readiness task.
Read local git state first, then inspect the GitHub PR through the installed GitHub plugin or connector.
Summarize blockers, checks, review comments, and the smallest safe next action.
Do not post comments, request reviewers, rerun checks, label issues, merge, close issues, or perform any other platform write unless I explicitly authorize the exact action.
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
- requesting or removing reviewers;
- adding, removing, or replacing labels;
- resolving review threads;
- rerunning workflow jobs;
- closing or reopening issues;
- merging, closing, or retargeting pull requests.

Before an authorized write, restate:

- target repository and PR or issue number;
- exact write action;
- current head SHA when the action depends on a branch state;
- reviewed files or threads;
- verification evidence;
- residual risk.

## Dependency Unavailable

If the GitHub plugin, connector, or authenticated platform tool is unavailable, do not scrape browser state or local app internals as a substitute. Report the missing dependency and choose the safest fallback:

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
3. Fetch GitHub changed files, comments, reviews, workflow runs, and statuses.
4. Reconcile local evidence with platform evidence.
5. Post a merge review comment only when the maintainer explicitly authorizes that platform write.
6. Merge only when the maintainer explicitly authorizes merge, the head SHA still matches, and no blockers remain.

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
- Recommended next action: post merge review comment, then merge if authorized
- Human gate: platform write and merge require exact authorization
```
