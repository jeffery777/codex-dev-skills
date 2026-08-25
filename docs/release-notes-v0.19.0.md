# Release Notes: v0.19.0

Status: release candidate for Issue #181 with Issue #183 exact-head
merge-review hardening. Commit, push, pull request creation, merge, annotated
tag creation, and GitHub Release publication remain separate human gates.

v0.19.0 is a backward-compatible workflow-contract release over v0.18.2. It
defines a reusable, non-recursive release-state contract so successful
publication does not make tracked active guidance stale and require a later
coherence patch.

## Release-State Contract

- Defines five distinct roles: repository source/package version, candidate
  preparation, GitHub tag/Release publication truth, active guidance, and
  historical point-in-time release notes.
- Makes `catalog.yaml` the canonical offline source/package version and keeps
  installer and package-local plugin manifest parity fail closed.
- Treats GitHub Release metadata and its corresponding annotated tag as
  publication truth without making ordinary repository validation depend on
  network access or GitHub scraping.
- Prohibits mutable tracked current-publication and current-candidate pointers
  in active README, roadmap, and release-readiness guidance.
- Preserves earlier release notes as point-in-time records instead of rewriting
  them after publication.

## Review And Publication Gates

- Adds release-state classification to project rules, release-sensitive deep
  review, merge readiness, project delivery, and the pull request checklist.
- Requires reviewers to test transition safety: active guidance must remain
  true after successful publication, not only at the reviewed pre-publication
  snapshot.
- Separates pre-mutation identity, payload, conflict, and transition checks from
  post-mutation connector-first readback of the annotated tag object,
  dereferenced commit, Release target, draft state, and prerelease state.
- Keeps tag creation and GitHub Release publication as separately authorized
  mutations. Repository tests and proposed platform payloads do not prove
  publication.
- Issue #183 adds an exact-head Merge-Review contract after PR #182 exposed
  that pre-commit deep review evidence could be described as if it were the
  PR-bound Merge Review verdict. Pre-commit evidence remains reusable input,
  but merge readiness now requires exact PR/base/head/merge-base/diff identity,
  successful hosted CI, closed findings, zero unresolved threads, and
  platform-visible receipt readback.
- Remediation code review and Security Diff Scan may be proportional to the
  affected boundary with recorded reuse rationale; every changed PR head still
  requires a new complete base-to-head Merge Review.

## Offline Validation

- Adds `scripts/validate-release-state.py` to validate source/package parity,
  the matching candidate record's minimum structure, known mutable active-
  guidance assertions, and required policy anchors without network access.
  Semantic role classification and historical-note preservation remain
  base-to-head review responsibilities.
- Integrates that validator into `scripts/validate-repo.sh` and adds focused
  positive and fail-closed tests.
- Removes current-version literals from unrelated active contract tests while
  retaining version literals that are genuine historical fixtures.
- Preserves catalog, installer, generated plugin package, and installed-policy
  parity.

## Compatibility And Boundaries

The release adds workflow, policy, validation, review, and documentation
contracts. It does not change installer target selection, installed runtime
behavior, Memory behavior, security authority, completion authority,
deployment behavior, or merge/tag/Release authorization. The repository still
has no deployment target or publish/deploy workflow.

Revert the candidate changes to restore the approved source baseline
`72bae32b517344f0db00a49df86114eed9626033`. No data migration or destructive
cleanup is involved.

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

Require independent release-sensitive review, security diff scan, exact-head
CI, and merge readiness before merge. Annotated tag `v0.19.0` and a non-draft,
non-prerelease GitHub Release remain later, separate human gates.

## Traceability

- Issue #181: <https://github.com/jeffery777/codex-dev-skills/issues/181>
- Issue #183: <https://github.com/jeffery777/codex-dev-skills/issues/183>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.18.2>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.18.2...v0.19.0>
