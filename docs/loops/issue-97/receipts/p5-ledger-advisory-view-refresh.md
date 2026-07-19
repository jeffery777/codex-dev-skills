# P5 ledger advisory-view refresh

Status: **materialized advisory fields synchronized**.

The Issue #97 event history, source revision, task statuses, evidence, blockers,
claims, gates, lifecycle, state revision, protected history, and event hashes
were not changed by this refresh. Those fields remain reconstructable and are
validated by executable replay.

The non-authoritative `current_loop.selected_task_id`, its decision summary,
and the historical P3/P4 residual wording were synchronized to the already
materialized state after the round-14 defensive review, round-15 deep code
review, and final isolated refresh. They now select P5 and accurately retain the
final docs gate and native Security Diff Scan as pending. These advisory fields
are outside the protected event payload and cannot authorize mutation,
publication, a gate, or completion.

The refresh is a generated-view correction, not a historical event rewrite or
authority bypass. Structural validation and semantic event replay must pass
after the edit.
