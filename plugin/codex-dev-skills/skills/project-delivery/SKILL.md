---
name: project-delivery
description: Carry a bounded software delivery objective through discovery, planning, implementation, verification, review, docs sync, and PR readiness or the next human gate.
---

# project-delivery

Runtime compatibility: shared

GitHub control plane: follow
`../../policies/github-control-plane-policy.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/github-control-plane-policy.md`
after filesystem installation, when the target repository is hosted on GitHub.

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill when the user delegates an end-to-end project goal and expects the agent to act as delivery owner until the next real human gate.

For a single clear implementation task, prefer `implementation-slice`. Use `project-delivery` when the objective is larger than one slice but still bounded.

## Workflow

1. Bootstrap from repo instructions, current git state, plans, specs, docs, status files, and review artifacts.
2. Apply `project-orchestrator` routing rules to classify the objective, select the next phase, and decide whether to proceed, hand off, or stop.
3. Produce or update a plan when the source of truth is incomplete.
4. Implement in small slices using `implementation-slice` semantics. When
   delegation helps, split by disjoint ownership and parallelism rather than
   discipline; keep code, focused tests, and directly related docs with the
   implementation owner by default.
5. Run relevant verification and inspect the diff.
6. Route code or mixed changes through `code-review`, high-risk code or mixed changes through `code-review-deep`, and docs-only or docs-dominant changes through `docs-review`.
7. Use `code-review-gate` or `docs-review-gate` only when commit readiness, PR readiness, merge readiness, or repo policy requires a formal blocking decision.
8. If reviews or gates produce actionable blockers, close them by returning to the smallest primitive workflow and rerunning the relevant review primitive or formal gate within the configured round limit.
9. Sync docs or status files when that is part of the repo policy.
10. Prepare PR readiness evidence, but do not commit, push, create PRs, publish, merge, deploy, post platform comments, submit reviews, or perform destructive actions without the required human gate.

For concurrent workers, dispatch the fixed independent set once, continue
parent-owned work, and use one supported wait-for-any/mailbox wait rather than
polling each worker. Workers should emit only a blocker needing a decision and
one final receipt. Integrate completed receipts while remaining workers
continue, and reuse the original worker for bounded follow-up when safe.

## Stop Conditions

Stop for product ambiguity, source-of-truth conflict, broad scope expansion, external writes, destructive actions, material security or data risk, or insufficient verification for high-risk changes.

## Output

- Delivery status
- Files changed
- Verification evidence
- Review or gate result
- Review closure rounds used
- Remaining risk
- Next human gate, if any
