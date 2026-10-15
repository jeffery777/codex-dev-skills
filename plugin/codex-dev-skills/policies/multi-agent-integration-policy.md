# Multi-agent Integration Policy

Use this policy when combining outputs from multiple agents or work packets.

## Integration Checks

- Inspect current git state before integrating.
- Verify each output stayed within assigned ownership.
- Detect overlapping edits, missing files, unexpected deletions, generated-file churn, and test removal.
- Run relevant verification after integration, not only per-worker verification.
- Route integrated changes through the appropriate review primitive: `code-review` for ordinary code or mixed changes, `code-review-deep` for high-risk code or mixed changes, and `docs-review` for docs-only or docs-dominant changes.
- Run `code-review-gate` or `docs-review-gate` only when integration reaches formal commit readiness, PR readiness, merge readiness, or an explicit repo-policy blocking decision.
- Treat `desktop-implementation-gate` as a deprecated compatibility alias for
  these shared review and formal-gate routes; new workflows must not add a
  second Desktop-specific integration decision.

## Ownership

Ownership must be explicit before delegation. When two workers touch the same file or contract, the main agent must reconcile the overlap and explain the final decision.

Do not create separate workers merely to mirror planning, implementation,
testing, documentation, code-review, and security-review labels. Combine
tightly coupled authoring work under one owner, then preserve independence at
the review boundary. Separate planning or documentation only when ambiguity,
contract weight, artifact volume, or an independently verifiable boundary
justifies the additional bootstrap and handoff cost.

## Coordination

- Batch only disjoint packets whose dispatch decisions are already fixed.
- While workers run, continue useful parent-owned work before waiting.
- Wait on the active set and consume state changes; do not busy-poll each
  worker or re-read unchanged status.
- Integrate completed receipts without blocking on unrelated remaining work.
- A progress heartbeat is not integration evidence and should not trigger a
  new review or replacement worker.

## Evidence

Integration reports should list:

- worker/task source
- files accepted
- files rejected or reworked
- verification run
- review evidence collected
- formal gate result, if a readiness or repo-policy gate was run
- residual risks
- human decisions needed
