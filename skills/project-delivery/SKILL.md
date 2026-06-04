---
description: Carry a bounded software delivery objective through discovery, planning, implementation, verification, review, docs sync, and PR readiness or the next human gate.
---

# project-delivery

Runtime compatibility: shared

## Purpose

Use this skill when the user delegates an end-to-end project goal and expects the agent to act as delivery owner until the next real human gate.

For a single clear implementation task, prefer `implementation-slice`. Use `project-delivery` when the objective is larger than one slice but still bounded.

## Workflow

1. Bootstrap from repo instructions, current git state, plans, specs, docs, status files, and review artifacts.
2. Apply `project-orchestrator` routing rules to classify the objective, select the next phase, and decide whether to proceed, hand off, or stop.
3. Produce or update a plan when the source of truth is incomplete.
4. Implement in small slices using `implementation-slice` semantics.
5. Run relevant verification and inspect the diff.
6. Route code or mixed changes through `code-review-gate`; route docs-only changes through `docs-review-gate`.
7. If review gates produce actionable blockers, close them by returning to the smallest primitive workflow and rerunning the relevant gate within the configured round limit.
8. Sync docs or status files when that is part of the repo policy.
9. Prepare PR readiness evidence, but do not push, publish, merge, deploy, or perform destructive actions without the required human gate.

## Stop Conditions

Stop for product ambiguity, source-of-truth conflict, broad scope expansion, external writes, destructive actions, material security or data risk, or insufficient verification for high-risk changes.

## Output

- Delivery status
- Files changed
- Verification evidence
- Review gate result
- Review closure rounds used
- Remaining risk
- Next human gate, if any
