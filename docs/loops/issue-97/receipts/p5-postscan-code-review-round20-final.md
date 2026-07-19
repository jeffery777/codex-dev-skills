# P5 Post-Scan Deep Code Review — Round 20 Final

Gate result: **PASS**.

The routed deep-review worker was refused by the runtime classifier before it
could return the round-20 receipt. Under the documented, previously authorized
current-session fallback, the main agent completed the same read-only deep
review without changing scope or scan state. The refusal is capability evidence,
not review or completion authority.

Finding disposition:

- `V2CA-MF-TRUSTED-TIME-001`: fixed. Durable event-time semantics and
  apply-to-replay equality are restored.
- `V2CA-MF-HOME-TOCTOU-002`: fixed and independently closed in round 18.
- `V2CA-MF-FALLBACK-003`: fixed and independently closed in round 18.
- `V2CA-R18-MF-LEASE-001`: fixed and independently closed in round 19.
- `V2CA-R19-MF-LEASE-COMMIT-TOCTOU-001`: fixed. Every non-replay live write
  takes a second trusted-time sample after source/CAS validation, re-runs core
  live acceptance over the original state/event/authority, requires identical
  state, replay flag, and materialized ledger, then replaces the ledger. Three
  deterministic deadline-crossing regressions confirm zero ledger-byte change.

Open MUST-FIX: 0. Open SHOULD-FIX: 0. Open NIT: 0.

Verification reviewed:

- full unit suite: 649/649 passed;
- loop core/CLI/eval subset: 158/158 passed;
- GitNexus adapter: 79/79 passed;
- Loop Engineering eval: 23/23 passed;
- V2b oracle: 31/31 passed with false authority/completion zero;
- repository validation: loop 148, profiles/installer 35, routing 45, V2b 46;
- three commit-boundary regressions rerun independently: 3/3 passed;
- `git diff --check`: passed.

Residual timing risk is limited to the unavoidable interval between the final
trusted-time check and the atomic local replacement. The implementation places
no blocking I/O or externally controlled callback in that interval. This is
accepted within the cooperative local control-plane boundary and does not
authorize publication or replace the required final native diff scan.
