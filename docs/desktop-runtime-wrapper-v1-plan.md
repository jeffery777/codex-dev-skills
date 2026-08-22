# Desktop Runtime Wrapper V1 Historical Record

## Status

This document is a frozen historical record of the former Desktop Runtime
Wrapper V1 experiment. It is not current integration guidance. The
`desktop_runtime_*` helper family remains quarantined historical evidence and
has no active entrypoint or supported consumer.

Runnable commands, request recipes, callable examples, and live-smoke handoff
instructions are intentionally omitted. Current behavior is owned by the
native runtime contracts and tests referenced from
[`docs/loops/issue-169/readiness-crosswalk.md`](loops/issue-169/readiness-crosswalk.md).

## Historical objective

V1 investigated whether a narrow repository-owned compatibility layer could
prepare and validate Desktop thread actions without depending on private
Desktop state. The experiment was deliberately incremental: each slice added
one evidence boundary while keeping default execution non-live.

The historical family covered these concerns:

- request planning and fallback representation;
- caller-supplied capability metadata normalization;
- old/new contract comparison;
- create-thread and read-thread readiness checks;
- session compatibility status, handshake, and cache evidence;
- authorization, executor-boundary, wiring, and bundle evidence;
- one separately approved live-smoke boundary.

Those mechanisms were experimental wrapper contracts, not public native
interfaces. Their JSON envelopes, status values, schema hashes, helper
versions, callable descriptors, injected runners, cache records, and smoke
markers are obsolete and must not be treated as supported behavior.

## Historical safety decisions

The useful outcome of V1 was its safety boundary rather than its helper
mechanisms:

- documented or caller-supplied capability evidence could describe
  availability but could not grant permission;
- readiness, cache, status, or comparison evidence could not replace exact
  action authorization;
- target identity, permission/auth failure, response shape, returned identity,
  and returned status required call-site validation;
- a queued client identifier was not interchangeable with a usable thread
  identifier;
- runtime actions did not authorize commit, push, PR mutation, merge, release,
  deployment, deletion, or other external writes;
- private Desktop databases, logs, sessions, auth files, caches, app state, and
  unpublished internals were outside the evidence boundary;
- default CLI and test paths remained non-live unless a separately authorized
  runtime boundary supplied the required callable;
- prior evidence could not turn a destructive or state-changing action into an
  implicitly approved action.

The retained current forms of these rules live in native capability and
runtime-adapter documentation. Wrapper-independent cases and expected outcomes
live in
[`tests/fixtures/desktop_wrapper_security_invariants.yaml`](../tests/fixtures/desktop_wrapper_security_invariants.yaml)
and are enforced without importing or executing a historical wrapper.

## Historical implementation outcome

The repository eventually contained sixteen bounded helper modules and sixteen
focused historical test modules. They demonstrated the planned evidence chain,
including successful, fallback, stopped, malformed-response, identity,
authorization, and session-mismatch cases.

That breadth also made the family expensive to understand and easy to mistake
for a supported runtime path. Native Desktop task controls later became the
canonical integration surface, so Issue #163 froze the V1 family instead of
continuing it. The freeze established an exact inventory, zero active
entrypoints, active-surface quarantine, and explicit sunset requirements.

Issue #169 then prepared the non-destructive evidence needed for a possible
future retirement:

- classified retained native semantics separately from obsolete wrapper
  mechanisms;
- preserved security invariants independently of wrapper entrypoints;
- removed executable historical guidance;
- documented exact future deletion, regeneration, verification, release-value,
  and recovery steps.

## Current source of truth

Use these current sources instead of reconstructing a V1 invocation:

- `docs/native-runtime-capabilities.md` for native capability and identity
  contracts;
- `docs/runtime-adapter-v2.md` for the shared adapter safety model;
- `skills/desktop-thread-delegation/SKILL.md` for the active Desktop
  task-control adapter;
- `docs/desktop-runtime-wrapper-v1-deprecation.md` for the quarantine and
  sunset contract;
- `docs/desktop-runtime-wrapper-v1-inventory.yaml` for the exact retained
  historical artifact inventory;
- `docs/loops/issue-169/readiness-crosswalk.md` for behavior disposition and
  exact successor evidence;
- `docs/loops/issue-169/future-removal-plan.md` for the separately reviewed,
  non-authorizing removal and recovery plan.

## Authority boundary

This historical record does not authorize wrapper execution, deletion,
archiving, restoration, publication, or any platform mutation. A future
physical removal remains a separate destructive task requiring an exact
reviewed diff, complete recovery evidence, and explicit user authorization.
