# Desktop Runtime Wrapper V1 Deprecation Contract

The `desktop_runtime_*` helper family is frozen historical compatibility and
regression evidence. It is not an active CLI or Desktop runtime adapter, is not
installed or packaged as an entrypoint, and must not be imported, executed, or
recommended by active skills, examples, policies, catalog entries, or installer
groups.

## Canonical Inventory

[desktop-runtime-wrapper-v1-inventory.yaml](desktop-runtime-wrapper-v1-inventory.yaml)
is the machine-readable source of truth for retained wrapper scripts, focused
tests, classified references, generated-copy boundaries, prohibited active
surfaces, and sunset requirements. Generated plugin files are never listed as
independent sources; existing plugin parity validation owns those copies.

Repository maintainers run the strict offline check from a source checkout
with:

```bash
./scripts/project-python scripts/validate-desktop-wrapper-legacy.py
./scripts/project-python -m unittest tests.test_desktop_wrapper_legacy
```

The validator fails closed when the inventory is malformed, an artifact or
reference is missing or unclassified, a generated path is promoted into the
canonical inventory, or an active surface contains a runnable legacy script
reference. A passing result proves inventory consistency only. It does not
make the wrappers safe or current, authorize their execution, or establish
repository completion.

## Active Replacement

Use [Native Runtime Capability Contract](native-runtime-capabilities.md) for
current shared, CLI, and Desktop capability ownership. CLI session operations
remain in the CLI adapter; Desktop task and thread operations remain in the
Desktop adapter; shared workflows retain task selection, verification, review,
completion, and human-gate semantics.

Historical wrapper response shapes, cache records, preflight status, injected
callable evidence, and smoke results never override the active callable schema
or call-site validation.

## Sunset And Removal Gate

Physical archive or deletion is a separate destructive slice. It may be
proposed only after all inventory sunset requirements are independently
verified:

1. zero active runnable consumers;
2. native adapter coverage for every retained behavior that is still current;
3. useful historical security assertions extracted into fixtures independent
   of wrapper entrypoints;
4. no executable legacy guidance in canonical or generated documentation;
5. a separately reviewed plan naming exact deletion targets, recovery path,
   and verification; and
6. explicit user authorization for the destructive action.

Until that gate passes, maintain the inventory and isolated regression tests;
do not expand the wrapper family or add new consumers.

Issue #169 records the non-destructive preparation evidence in
[`loops/issue-169/readiness-crosswalk.md`](loops/issue-169/readiness-crosswalk.md)
and the separately reviewable future manifest in
[`loops/issue-169/future-removal-plan.md`](loops/issue-169/future-removal-plan.md).
The wrapper-independent security fixture is enforced separately from the
retained legacy test chain. These artifacts are preparation and review inputs;
they do not satisfy independent review or destructive-action authorization by
themselves.
