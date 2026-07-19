# P5 Post-Scan Deep Code Review — Round 18

Gate result: **BLOCKED**.

Round 18 closed `V2CA-MF-HOME-TOCTOU-002` and
`V2CA-MF-FALLBACK-003`, and confirmed that the earlier apply-to-replay
inconsistency was removed. It found one replacement MUST-FIX:

- `V2CA-R18-MF-LEASE-001`: backdated live acquisition, active-claim
  transition, or source rebound could pass after the lease had expired at the
  current trusted time. Live writes must preserve deterministic event-time
  replay while additionally requiring the affected lease to remain fresh at
  trusted current time. A rebound whose lease classification differs between
  event time and trusted time must fail closed.

SHOULD-FIX: 0. NIT: 0. The gate remains blocked until focused regressions,
full verification, and an independent re-review pass.
