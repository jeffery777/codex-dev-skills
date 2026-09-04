# Issue #209 Architecture Decisions

1. Reuse M1 SQLite/FTS5, M0 operations, and V2b decision contracts unchanged.
2. Pilot taxonomy is bound in the canonical record extension
   `dev.jeffery.memory-pilot/profile`, not a record kind or authority source.
3. State roots are explicit and still validated by M1 as secure and disjoint.
4. The memory-off module has no adapter import and no filesystem operation.
5. CLI exposes explicit `remember`, `recall`, and `invalidate` bundle routes;
   callers still construct the existing exact M0 chain themselves. Invalidate
   has no class claim, because it is an exact M0 target transition.
6. V2b receives the complete bounded M1 response so lifecycle controllers from
   another pilot class can still suppress stale records. The façade selects
   class-matching adopted digests only after the unchanged V2b decision.
7. Pilot content is one trimmed line of at most 512 UTF-8 bytes and retains the
   existing V2b sensitivity/provenance checks plus pilot lexical exclusions.
   This is a narrow machine-checkable boundary, not a general data-loss-
   prevention claim.
8. Recall exposes the selected record only through a minimal advisory context
   projection. Synthetic non-regression compares one repository-authoritative
   task on the off/on arms; context reduction measures that exact projection,
   not a record digest placeholder.
