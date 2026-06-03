---
description: Deep read-only code review for high-risk changes involving security, data, packaging, migrations, external integrations, or cross-module contracts.
---

# code-review-deep

Runtime compatibility: shared

## Purpose

Use this skill when routine review is not enough because the change has material blast radius or hidden failure modes.

## Additional Focus

- data integrity and migration rollback
- permission and identity boundaries
- sensitive data handling
- dependency and packaging risk
- concurrency and idempotency
- cross-module contracts
- observability and failure modes

## Workflow

Follow `code-review`, then add adversarial checks for edge cases, stale assumptions, rollback gaps, and evidence quality.

## Output

Use the `code-review` output structure and add a Deep Risk Notes section.
