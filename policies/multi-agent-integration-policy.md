# Multi-agent Integration Policy

Use this policy when combining outputs from multiple agents or work packets.

## Integration Checks

- Inspect current git state before integrating.
- Verify each output stayed within assigned ownership.
- Detect overlapping edits, missing files, unexpected deletions, generated-file churn, and test removal.
- Run relevant verification after integration, not only per-worker verification.
- Route integrated changes through the appropriate review gate.

## Ownership

Ownership must be explicit before delegation. When two workers touch the same file or contract, the main agent must reconcile the overlap and explain the final decision.

## Evidence

Integration reports should list:

- worker/task source
- files accepted
- files rejected or reworked
- verification run
- residual risks
- human decisions needed
