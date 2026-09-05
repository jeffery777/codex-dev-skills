# Issue #217 — qualification discovery integration

Base: `1f5b3bf722751da59aa8bc63d6ba0388dbb25c0d`.
Branch: `codex/qualification-autoload`.

## Objective

Ordinary shared workflow delegation must not require the user to provide
candidate JSON or qualification paths repeatedly. The parent assesses the
task and gathers current public runtime facts; the existing router discovers
explicitly approved user records and applies the same preflight/fallback.

## Implementation packets

1. Add bounded, strict, local user-store loading to V2 `agent-route`. Match the
   canonical candidate, class/tier, profile/evidence digests, task scope,
   runtime and expiry. Explicit runtime candidate keys retain precedence,
   including empty opt-out. Preserve V1 and current-facts input compatibility.
2. Wire parent responsibilities into shared orchestration/delivery and the
   Desktop adapter. Keep one detailed procedure in Loop Engineering and one
   schema reference installed with the workflow. Support stdin facts for
   agent-generated current observations; never restore cached availability.
3. Test positive selection and negative trust/scope/revocation cases, installed
   package parity and docs coherence. Independently review the local file and
   qualification boundary, address findings and run proportional security scan.

## Trust and non-goals

The one-time approved store is user-owned; repository content must not create
qualification authority. Evidence is data, not executable instructions. Scope
labels cannot judge task quality: the parent must read and match actual
evidence. The loader verifies declared bindings, not model performance.

Current native role availability is separate from profile installation. CLI,
Desktop and API are distinct runtime identities. No private Desktop state,
daemon, global conversation interception, blanket Astra routing, permission
widening or additional model benchmarks are required by this change.

## Definition of done

- Existing agent-route automatically discovers approved records without a new
  per-task qualification-path option; parent skills invoke it for the user.
- Missing, unsafe, revoked, expired, changed or nonmatching records do not
  enable candidates; explicit empty candidates opt out.
- Current availability and sandbox gates still control execution; lower tiers
  never satisfy higher-tier work and native dispatch is not inferred.
- Relevant tests and installer/plugin/documentation parity pass; independent
  review records findings and limits without equating tests with quality proof.
- Actual personal records remain outside the public repository.

## Delivery and release scope

This is implementation on a new Issue, not a modification of the historical
#215 acceptance record. Source/package version remains 0.23.0; candidate version
selection and publication are separate. No existing release note is rewritten.
Commit, PR, merge and personal adoption require their applicable authorization;
review evidence alone does not grant it.
