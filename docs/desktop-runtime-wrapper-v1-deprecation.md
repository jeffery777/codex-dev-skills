# Desktop Runtime Wrapper V1 Retirement Record

Desktop Runtime Wrapper V1 is retired. Its repository-owned helper artifacts
and focused legacy validation chain are no longer present, supported, or
available as a runtime integration path.

This document is a non-executable historical record. It contains no invocation
instructions, import guidance, or compatibility promise for V1. Historical
response shapes, cache records, preflight status, callable evidence, and smoke
results never override an active runtime callable schema or call-site
validation.

## Current Contract Ownership

[Native Runtime Capability Contract](native-runtime-capabilities.md) owns the
current shared, CLI, and Desktop capability boundary. Native adapters own
runtime-specific invocation; shared workflows own task selection, verification,
review, completion, and human-gate semantics.

Current runtime actions must validate the exact action and target identity,
permission or authentication outcome, response shape, returned identity, and
status at the call site. Capability evidence does not grant permission, and no
runtime action authorizes filesystem mutation, destructive action, publication,
or another external write without its own exact authority.

## Preserved Historical Safety Evidence

The useful V1 safety cases remain as wrapper-independent fixtures in
[`tests/fixtures/desktop_wrapper_security_invariants.yaml`](../tests/fixtures/desktop_wrapper_security_invariants.yaml).
They preserve authorization, identity, fail-closed, private-state,
external-write, and non-execution expectations without importing or executing
a retired helper.

Issue #169's [readiness crosswalk](loops/issue-169/readiness-crosswalk.md) and
[future removal plan](loops/issue-169/future-removal-plan.md) remain historical
review and recovery evidence. They are not executable guidance and do not
authorize restoration, publication, or any platform mutation.
