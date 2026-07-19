# P5 Post-Scan Deep Code Review — Round 17

Gate result: **BLOCKED**.

The routed `loop_v2a_deep_reviewer` (`gpt-5.6-sol`, high reasoning) reviewed
the complete mixed diff read-only. The profile was selected by the production
V2a classifier because the packet combines cross-module public-contract,
concurrency, external-tool, and high-verification risk. Cost degradation was
false. Route evidence is in `p5-postscan-deep-review-route.json`.

Open MUST-FIX findings:

- `V2CA-MF-TRUSTED-TIME-001`: live `claim_expired` and `source_rebound`
  accepted states could disagree with deterministic replay because live
  classification used trusted current time while replay used `occurred_at`.
- `V2CA-MF-HOME-TOCTOU-002`: the isolated home identity was rebound around
  execution, but a same-inode content race and cross-repository shared-home
  concurrency were not serialized.
- `V2CA-MF-FALLBACK-003`: legacy `reporting_retry_count` could raise the retry
  threshold outside the reporting phase.

SHOULD-FIX: 0. NIT: 0. Existing focused tests, the 22-case Loop Engineering
eval, and the 31-case V2b oracle passed but did not cover these counterexamples.
The gate stays blocked until all three findings are fixed, regression-tested,
and independently re-reviewed.
