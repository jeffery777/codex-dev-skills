# Release Notes: v0.22.0

Status: v0.22.0 release candidate prepared through Issue #205. Merge, annotated
tag creation, and provider Release publication remain separate human gates.

## Provider-Neutral Exact-Head Merge Review

- Separates exact-head content review from optional forge enforcement.
- Binds content review to repository, change request when present, exact base,
  head, merge base, complete range identity, deterministic verification,
  findings, dispositions, code/documentation coherence, and residual risk.
- Requires final complete-range comparison of documentation claims with code,
  configuration, specifications, tests, and observed behavior. A changed head
  invalidates the content verdict.
- Reports `content_review` independently from `platform_enforcement`, allowing
  GitLab CE and other repositories to use `NOT_CONFIGURED` without pretending
  that provider state was inspected.
- Retains the existing GitHub App, Actions, Checks, strict-JSON receipt,
  connector readback, and ruleset controls as an explicit optional GitHub
  enforcement profile. This repository continues to select that profile.

## Cumulative Changes Since v0.21.0

- PR #204 refreshed point-in-time standalone Codex CLI 0.152.0 compatibility
  evidence while preserving independent CLI and Desktop runtime boundaries.
- Issue #205 introduces the provider-neutral content-readiness model, provider
  status separation, coherence-focused Merge Review, updated workflow routing,
  templates, tests, documentation, installer inventory, and plugin mirrors.
- Existing GitHub exact-head collectors and strict offline envelope validators
  remain available and retain their fail-closed trust boundaries.

The published `v0.21.0` reference is an annotated tag object targeting commit
`3fd140b64b079d6ee0a0a9ee9d06f570ba3587cf`; its GitHub Release is non-draft
and non-prerelease. These connector/fallback-verified facts establish only the
base publication boundary and do not prove publication of v0.22.0.

## Compatibility And Boundaries

The repository source/package version is `0.22.0` in `catalog.yaml`, with
matching installer and plugin manifest versions. This is a pre-1.0 minor release
because it changes the public shared Merge Review and readiness
contracts while retaining existing GitHub enforcement as an opt-in compatible
profile.

Repositories that relied on the installed shared workflow no longer inherit
GitHub platform objects merely from requesting content Merge Review. A
repository that requires GitHub enforcement must select the GitHub profile in
its repo policy. GitLab CE repositories may use exact local or MR ranges and
offline validation without GitHub; a GitLab provider adapter remains optional
future integration rather than a hidden claim of verified pipeline, discussion,
approval, or protected-branch state.

This candidate does not authorize merge, auto-merge, provider comments,
reviews, tag creation, Release publication, deployment, ruleset mutation, or
destructive cleanup.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python -m unittest \
  tests.test_exact_head_merge_review_contract_docs \
  tests.test_github_control_plane_policy \
  tests.test_release_state_contract \
  tests.test_plugin_packaging \
  tests.test_runtime_compatibility_release_docs
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

Require complete base-to-head `merge-review-deep`, explicit documentation/code
coherence inspection, relevant Security Diff Scan, and the provider-neutral
formal gate. Because this repository selects the GitHub profile, its hosted CI,
receipt publication/readback, dedicated-App check, ruleset, and exact-head
readback remain additional requirements before merge. None authorizes merge.

After a separately authorized merge, annotated `v0.22.0` tag creation and
non-draft/non-prerelease GitHub Release publication each retain their own
preview, conflict check, mutation authorization, and post-mutation readback.

## Traceability

- Issue #205: <https://github.com/jeffery777/codex-dev-skills/issues/205>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.21.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.21.0...v0.22.0>
