# Release Notes: v0.20.0

Status: release candidate for Issue #185. Commit, push, pull request creation,
merge, GitHub App registration or installation, protected-environment or secret
configuration, ruleset mutation or activation, annotated tag creation, and
GitHub Release publication remain separate human gates.

v0.20.0 is a backward-compatible workflow-contract release over v0.19.0. It
adds a reusable, platform-enforced exact-head merge gate without granting new
merge, auto-merge, tag, Release, deployment, comment, review, or content-write
authority.

## Hosted Exact-Head Enforcement

- Defines `exact-head-merge-readiness/v2`, which combines the existing v1
  advisory-review evidence with a control-plane snapshot and publishing gate
  identity.
- Adds the `Exact-Head Merge Readiness` required-check contract, explicitly
  attached to the current live PR head rather than a default-branch event SHA.
- Requires exact base/head/merge-base/range identity, successful upstream CI,
  closed findings, zero unresolved review threads, a platform-visible strict
  JSON receipt and digest, and a dedicated App-backed check identity.
- Orders exact-head receipts by a unique positive sequence, preserves the
  current sequence as a compact App-owned tombstone, and reconciles open PRs
  on a five-minute schedule so coalesced Actions events converge.
- Uses native live-head, strict-up-to-date, and resolved-conversation rules for
  merge-time predicates. Relevant events serially invalidate the event-driven
  finding, receipt, range, check, and App-identity projection; it does not
  claim an atomic issue-comment-edit/merge transaction. The upstream
  required-CI set excludes the readiness check itself.

## Trust And Rollout Boundary

- Uses a trusted default-branch collector that does not checkout, import,
  execute, cache, or consume artifacts from untrusted PR-head code.
- Keeps Repository Validation on the fork-safe `pull_request` event with
  read-only contents, no referenced secret, and no persisted credential. The
  trusted controller accepts it only when the workflow Git blob at both PR
  base and head matches repository policy.
- Gives the dedicated GitHub App only metadata/read, pull-requests/read,
  issues/read, actions/read, and checks/write permissions. Its credentials are
  restricted to protected trusted-workflow execution; fork PRs receive no
  credential-bearing PR-code execution path.
- Preserves ordinary offline validation without network or authentication
  dependency. GitHub state is read through the connector-first control plane,
  normalized, and then validated locally.
- Defines a canary-first ruleset rollout: identify the dedicated App
  integration ID, update the ruleset while disabled, prove drift failures, and
  activate only through a later independent human gate.

## Compatibility And Boundaries

The release changes public workflow, policy, validation, documentation, and
packaging contracts. It preserves v1 advisory evidence semantics, installer
target selection, runtime behavior, Memory behavior, completion authority, and
the repository's lack of a deployment target or publish/deploy workflow.

Revert the candidate changes to restore the approved v0.19.0 source baseline.
No data migration or destructive cleanup is involved.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
git status --short --branch
```

Require focused v2 collector, validator, workflow-security, and contract tests;
independent release-sensitive review; Security Diff Scan; hosted canary and
drift checks; exact-head Merge Review; and final disabled/active ruleset
readback as applicable. Annotated tag `v0.20.0` and a non-draft,
non-prerelease GitHub Release remain later, separate human gates.

## Traceability

- Issue #185: <https://github.com/jeffery777/codex-dev-skills/issues/185>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.19.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.19.0...v0.20.0>
