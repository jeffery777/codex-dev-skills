# Issue #111 v0.9.1 Release Closure

## Objective

Complete the bounded v0.9.1 release-closure repository change after Issues
#107 and #109, align the Operational Evidence durable handoff, and prove the
post-bootstrap pull-request linkage guardrail without implementing V2d-A.

## Source Of Truth

- Repository instructions: `AGENTS.md`
- GitHub objective: Issue #111
- Release notes: `docs/release-notes-v0.9.1.md`
- Release readiness: `docs/release-readiness.md`
- Pull-request linkage policy:
  `policies/pull-request-issue-linkage-policy.md`
- Operational Evidence program:
  `docs/programs/operational-evidence/README.md`
- Implementation plan: `docs/loops/issue-111/implementation-plan.md`
- Task manifest: `docs/loops/issue-111/task-manifest.yaml`

Repository files, Git state, verification, formal review, and accepted GitHub
state remain authoritative. Release notes, GitNexus metadata, hooks, CI, and
program projections remain bounded evidence only.

## Scope

### In Scope

- Set installer and catalog version metadata to `0.9.1`.
- Finalize v0.9.1 release notes and README current-release references.
- Record Issue #107/PR #108 and Issue #109/PR #110 as completed baselines.
- Align Operational Evidence Phase 0 and continuation with the release gate.
- Add Issue #111 planning, verification, review, and post-bootstrap CI
  evidence.
- Publish and merge one ready PR that closes Issue #111 after all required
  checks and exact-head review pass.

### Out Of Scope

- V2d contracts, validators, fixtures, or private proof-of-concept data.
- V3-A, scheduler, daemon, controller service, database, graph runtime,
  resident automation, or automatic promotion.
- Rewriting Issue #107 or Issue #109 point-in-time receipts.
- Tag creation, GitHub Release publication, or installed-skill update before
  the separate human release gate.

## Definition Of Done

- README, installer, catalog, roadmap, and release notes agree on v0.9.1.
- Operational Evidence documents include the Issue #109 guardrail baseline
  and keep V2d-A after the formal v0.9.1 release.
- Existing Issue #107 and Issue #109 receipts are unchanged.
- Required local verification, privacy inspection, GitNexus checks, formal
  code/docs/release-readiness gates, and exact-head deep merge review pass
  without unresolved findings.
- The ready PR contains a standalone `Closes #111` line.
- The trusted-base, read-only linkage workflow confirms #111 is an open Issue,
  not a pull request.
- The PR is merged only with its reviewed expected head SHA.

## Authority And Human Gates

- Issue creation, branch creation, commit, push, ready PR creation, merge
  review comment, and expected-head merge are authorized for this bounded
  release-closure change after their prerequisite evidence passes.
- CI linkage proves traceability only and cannot authorize completion or merge.
- Tag `v0.9.1`, GitHub Release publication, and local installed-skill update
  remain separate human gates.
