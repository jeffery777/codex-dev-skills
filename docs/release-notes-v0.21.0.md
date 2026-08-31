# Release Notes: v0.21.0

Status: release candidate prepared through Issue #201. Merge, annotated tag
creation, and non-draft/non-prerelease GitHub Release publication remain
separate human gates.

## Desktop Sidebar Organization

- Adds the installable Desktop-only `desktop-sidebar-organization` skill as a
  control plane separate from task/thread creation and navigation.
- Covers fresh `list_threads`/`list_projects` discovery and the active create,
  rename, delete, move, and reorder sidebar callables through exact identity,
  dry-run planning, action-specific authority, response validation,
  post-mutation readback, and fail-closed fallback.
- Treats pinned, custom, and default section values as typed destinations;
  treats titles and summaries as untrusted display data; and prevents queued
  `clientThreadId` values from being used as ready `threadId` identities.
- Requires complete membership exactly once for `reorder_section` and
  `reorder_sidebar_sections`. It preserves the documented partial-list
  semantics of `reorder_sidebar_projects`, where unlisted projects keep their
  current positions.
- Keeps delete and complete-list reorder behind high-risk or destructive human
  gates. Ordinary create, rename, and move still require an explicit exact
  target and desired state.
- Uses synthetic contract tests and packaging checks only. No live sidebar
  mutation, private Desktop state, unpublished internal endpoint, app-server
  client, wrapper daemon, sidecar, or background service is included.

## Cumulative Changes Since v0.20.0

This candidate covers the complete repository range after annotated
`v0.20.0` tag commit `764ab074e7a1b35a200faea5ae0a19ac92ec194e`
through the candidate head:

- Repository validation now uses a stable aggregate workflow with bounded
  deterministic test shards and recorded hosted timing evidence.
- Roadmap and repo-owned loop-state guidance were reconciled with completed
  Issues while preserving the Issue #188 / PR #189 canary and its separate
  destructive cleanup gate.
- The 2026-08-31 compatibility evidence independently records standalone
  Codex CLI 0.151.0, ChatGPT Desktop 26.825.51511 build 7377, and the bundled
  CLI 0.151.0-alpha.7.2. It observed the sidebar callables without executing a
  live mutation and remains a point-in-time historical evidence record.
- This Issue adds the independently installable sidebar organization contract,
  selection guidance, runtime documentation, installer/catalog wiring,
  plugin-package mirror, and offline tests.

At candidate preparation, connector-first GitHub readback confirmed that the
`v0.20.0` reference is an annotated tag object
`4bb94574176a890d179eed64246c9ba668236370` dereferencing to
`764ab074e7a1b35a200faea5ae0a19ac92ec194e`, and that its GitHub Release is
non-draft and non-prerelease. These facts establish the base publication
boundary only; they do not prove publication of v0.21.0.

## Compatibility And Boundaries

The repository source/package version is `0.21.0` in `catalog.yaml`, with
matching installer and plugin manifest versions. The new skill is additive and
Desktop-only. Existing shared orchestration, task/thread delegation, CLI
session handoff, completion authority, memory, deployment, and merge contracts
are unchanged.

The checked-in note is a point-in-time candidate-preparation record, not
publication truth. Publication truth remains the corresponding annotated tag
and GitHub Release metadata read through the connector-first control plane.
Historical v0.20.0 release notes are not rewritten by this candidate.

No deployment target or publish/deploy workflow is added. Memory M2, V3-C,
PlugMem, Mem0, resident automation, live sidebar canaries, Issue #188 / PR #189
cleanup, auto-merge, merge, tag creation, and GitHub Release publication remain
outside this implementation.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python -m unittest \
  tests.test_plugin_packaging \
  tests.test_installer_runtime_groups \
  tests.test_release_state_contract \
  tests.test_native_runtime_contract_docs \
  tests.test_runtime_compatibility_release_docs
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

Require formal release-sensitive code review, Security Diff Scan, exact-head
hosted CI, complete base-to-head Merge Review, strict-JSON receipt publication
and connector-first readback, and the dedicated-App `Exact-Head Merge
Readiness` check. A successful readiness result does not authorize merge.

After a separately authorized merge, annotated `v0.21.0` tag creation and
non-draft/non-prerelease GitHub Release publication each retain their own
preview, conflict check, mutation authorization, and post-mutation readback.

## Traceability

- Issue #201: <https://github.com/jeffery777/codex-dev-skills/issues/201>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.20.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.20.0...v0.21.0>
