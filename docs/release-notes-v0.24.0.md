# Release Notes: v0.24.0

Status: release candidate prepared through Issue #223. This point-in-time
record describes source/package preparation. Merge, annotated tag and GitHub
Release publication retain separate human gates, satisfied by concrete
maintainer authorization. Provider readback establishes publication separately.

## Workflow And Instruction Efficiency

- Split the largest Loop Engineering, CLI handoff and Desktop delegation
  entry points into short selectors and operation-specific references.
  Ordinary bounded delivery uses `project-delivery`; durable loop state is
  loaded when explicitly selected or required by repository policy.
- Reuse review and bootstrap evidence while its scope, source and assumptions
  remain valid. Every changed PR head still requires a complete base-to-head
  Merge Review. Protected authorization and privacy checks remain reachable.
- Honor existing authorization for exact, reversible Desktop sidebar actions;
  preserve ambiguity, destructive-action and scope-change gates.
- Make installed CLI examples independent of this repository's interpreter
  wrapper. Keep deprecated Desktop gate aliases explicitly callable with
  implicit invocation disabled, and move retired runtime-helper examples into
  a clearly historical, non-executable document.

Across the 25 Skill entry points, static UTF-8 bytes decrease from 138,803 to
93,493 (32.6%). The three largest entries decrease from 71,853 to 22,196 bytes
(69.1%). Conditional references retain the detailed contracts. These are
source-text measurements, not measured model tokens, latency or cost savings.

## Compatibility And Boundaries

- V2 task input accepts optional `quality_preference: balanced | quality-first`,
  defaulting to `balanced`. Exceptional research routing additionally requires
  at least three complexity triggers and explicit `quality-first` preference.
  All fallback paths require an exceptional task requirement before using an
  exceptional profile. Security and other safety hard triggers retain priority.
- Routine read-only review has an `everyday` minimum tier while preserving the
  read-only reviewer class. Existing higher-tier fallback profiles remain;
  this release does not enable a cheaper reviewer or change model defaults.
- New V2 receipts bind `routing_policy_revision: v2-2026-09-06`. Existing V1
  behavior and historical V2 receipt validation remain supported. Historical
  semantics are validator-only and cannot be selected for new route creation.
  Frozen pre-change fixtures test original receipt digests and dispositions.
- Retain all eleven agent profiles, qualification requirements, sandbox
  restrictions, advisory memory and integration completion boundaries.
- Correct the Memory pilot eval's version-specific positive fixture to use
  the repository baseline version. Version conflict rejection and qualification
  thresholds remain unchanged, so later source/package bumps remain testable.

## Verification And Release Gate

The implementation received independent routing, workflow/documentation and
security review, source/plugin parity checks, installed-resource tests and the
complete local test shard suite. Release metadata checks and exact-head hosted
CI are required again for the proposed release head. See
`docs/loops/issue-223/verification-and-review.md` for results and limits.

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

`catalog.yaml`, installer and plugin manifest agree on `0.24.0`. This is a
pre-1.0 minor release because installed workflow selection and routing options
change. Existing release notes remain historical records. No personal runtime
configuration, automatic model adoption, paid live-model trials, provider-policy
changes or deployment are included. Bounded model evaluation follow-ups are in
`docs/loops/issue-223/model-evaluation-follow-up.md`.

## Traceability

Issue #223: <https://github.com/jeffery777/codex-dev-skills/issues/223>
