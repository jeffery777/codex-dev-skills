# Issue #109 Verification And Review Receipt

Status: pre-publication evidence

Authority: advisory review and verification evidence only

## Scope Verified

- exact repository-local GitNexus index-only default;
- strict GitNexus config validation and negative fixtures;
- ready pull-request linkage to open same-repository Issues;
- trusted-base, read-only GitHub Actions boundary;
- PR template, policy, README, roadmap, and v0.9.1 alignment;
- no change to V2c completion, review, external-write, or merge authority.

## Verification Evidence

The following checks passed:

```bash
python3 scripts/validate-gitnexus-config.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_gitnexus_config_guard \
  tests.test_pr_issue_link
bash -n scripts/validate-repo.sh
./scripts/validate-repo.sh
git diff --check
```

The focused suite contains 13 tests. Full repository validation also passed
the existing loop contract, workflow eval, custom-agent profile, routing, and
external-memory suites.

`actionlint` was unavailable in the qualification environment. Workflow
structure and security invariants are covered by repository tests, shell
syntax validation covers the repository entrypoint, and GitHub remains the
authoritative workflow parser after publication.

## Live GitNexus Check

A bare `gitnexus analyze` was run with the tracked `.gitnexusrc` present.
GitNexus first detected an inconsistent derived FTS index; a full rebuild of
that ignored, reproducible index restored a known-good state. A subsequent
bare analysis completed with zero changed, added, or deleted source files.

Before/after hashes for tracked `AGENTS.md` and the pre-existing ignored
generated instruction and skill files were identical. No instruction or skill
file was created, removed, or rewritten. The ignored pre-existing files were
deliberately left in place because deleting machine-local artifacts is outside
Issue #109.

## Review Gate

Gate result: PASS

Review mode: `code-review-deep` through `code-review-gate`

| Finding | Severity | Disposition | Evidence |
| --- | --- | --- | --- |
| `CR-109-001` unbounded unique Issue references could multiply API calls | MUST-FIX | Fixed | Limit of 20 unique references, per-request timeout, five-minute job timeout, and pre-lookup regression test. |
| `CR-109-002` malformed `pull_request` event shape could raise a traceback before validation | MUST-FIX | Fixed | Safe type guard and CLI-level invalid-event regression test. |
| `CR-109-003` cross-repository closing references could be ignored when a valid local reference was also present | MUST-FIX | Fixed | Explicit external-reference rejection and mixed local/external regression tests. |
| `DOC-109-001` README overstated CLI override behavior | SHOULD-FIX | Fixed | Text now distinguishes repository default protection from explicit controller invocation evidence. |
| `DOC-109-002` receipt named an excluded provider-specific instruction file | MUST-FIX | Fixed | Replaced with a provider-neutral description and reran repository hygiene validation. |
| `DOC-109-003` new documentation/template files contained trailing whitespace | NIT | Fixed | Removed whitespace and reran staged diff hygiene. |

The final rerun found no remaining MUST-FIX, SHOULD-FIX, NIT, or
Needs-Human-Decision item.

## Security And Authority Notes

- The workflow reads metadata through `pull_request_target`, checks out only
  the event's base SHA, pins the checkout action by full commit SHA, disables
  persisted Git credentials, and grants only read permissions.
- Pull-request head code, branch scripts, and body content are never executed.
- Event and API payload sizes, unique Issue references, API request time, and
  total job time are bounded.
- API origins must be credential-free HTTPS origins.
- Validator errors do not include the GitHub token.
- A valid Issue link and a green check provide traceability only.

## Bootstrap And Residual Risk

The pull request that introduces the workflow cannot run the new
`pull_request_target` check because the workflow is absent from its base
revision. Its standalone `Closes #109` line must therefore be inspected
manually before merge. After the workflow reaches the default branch, later
ready pull requests are covered.

Issue state can change after a successful check. Exact-head merge review must
therefore confirm that the linked Issue remains appropriate and no required
gate has been bypassed. Branch-protection configuration is outside this issue.
