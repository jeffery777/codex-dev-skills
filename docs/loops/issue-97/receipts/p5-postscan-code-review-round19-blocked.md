# P5 Post-Scan Deep Code Review — Round 19

Gate result: **BLOCKED**.

Round 19 confirmed the in-memory live/replay lease matrix, isolated-home lock,
and reporting fallback fixes. It found one write-boundary MUST-FIX:

- `V2CA-R19-MF-LEASE-COMMIT-TOCTOU-001`: `apply-event --write` sampled trusted
  current time before serialization, source revalidation, and compare-and-swap,
  but did not revalidate immediately before `os.replace`. A lease could cross
  its deadline in that interval and still be committed active.

SHOULD-FIX: 0. NIT: 0. The fix must re-run live acceptance with fresh trusted
time at the commit boundary, reject any lease/classification drift without a
write, and cover acquisition, active transition, and source rebound.
