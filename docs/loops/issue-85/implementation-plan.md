# Issue 85 Implementation Plan

## Baseline

- Repository: `jeffery777/codex-dev-skills`
- Default branch: `main`
- Starting revision: `a083451dfd43d249fb18e217b92a5035dccb2235` (`v0.5.0`)
- Working branch: `codex/loop-engineering-v2a-routing`
- V1 already provides authority, protected-event, claim, completion, shared-subagent,
  sequential-fallback, installer, and production-backed eval foundations.

## Task Slices

### P1 — Capability Classification And Routing Receipt

- Add deterministic factor validation and non-compensatory risk classification.
- Select capability class/role and return explainable route evidence.
- Preserve all V1 authority, external-write, human-gate, and completion decisions.
- Validate worker/integration receipts, including stale, partial, failed, and conflicting output.

### P2 — Runtime Profiles And Preflight

- Add four namespaced public custom-agent TOML sources and a machine-readable registry.
- Add a stdlib validator/preflight for schema, runtime availability, mappings, collision,
  sandbox expectations, fallback, and safe-stop decisions.
- Keep concrete model IDs confined to runtime-owned profile metadata with verification dates.

### P3 — Opt-In Packaging

- Add an explicit profile installer group and a separate custom-agent target root.
- Refuse unsafe paths, symlinks, implicit overwrite, modified uninstall, and backup collision.
- Support user-level default and explicit trusted-project adoption in isolated tests.
- Do not silently add profiles to the existing delivery group and do not bump release version.

### P4 — Evals, Documentation, And Compatibility

- Add production-backed V2a route evals and metrics for correctness, false completion,
  evidence completeness, determinism, and latency/cost proxies.
- Cover fast/balanced/deep/security routing, fallback, authority invariance, receipt failures,
  runtime variance, and no-custom-agent V1 behavior.
- Sync README, roadmap, policies, runtime docs, workflow/skill guidance, catalog, and examples.

### P5 — Verification And Finding Closure

- Run focused and full validation, isolated installer tests, source/install mapping checks,
  secrets/private-state scan, code/docs review, Codex Security diff scan, deep merge review,
  and merge-readiness gate.
- Fix in-scope findings and rerun the affected checks until no blocker remains.

### P6 — Publish To Human Gate

- Inspect final diff and Git identity, commit, push, and create a ready-for-review PR linked
  to issue #85 with DoD, verification, review/security evidence, rollout/rollback, and risk.
- Stop without merging at the independent merge-review human gate.

## Ownership

- A bounded worker may own production classifier/receipt code and focused tests.
- A separate bounded worker may own profile registry/validator sources and focused tests.
- The main agent owns installer/catalog/docs/evals integration, all cross-cutting verification,
  review closure, GitHub publication, and final evidence.

## Review Plan

- `code-review-deep` for executable routing, validation, and installer behavior.
- `docs-review` for public adoption/runtime/model claims.
- `codex-security:security-diff-scan` because the diff changes config generation/installation,
  runtime selection, permissions expectations, and receipt validation.
- `merge-review-deep` and `merge-readiness-gate` after findings close.

## Durable Follow-Up

V2b may define an optional external-memory abstraction, but it must not replace repository,
Git, verification, review, accepted platform state, or protected authorization. V2c may study
GitNexus or other backends only behind that separately reviewed V2b contract.
