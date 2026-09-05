---
name: project-orchestrator
description: Shared project orchestration layer that routes bounded work across planning, implementation, review, continuation, handoff, or human gates.
---

# project-orchestrator

Runtime compatibility: shared

GitHub control plane: when the target repository is hosted on GitHub and the
workflow reads or mutates GitHub state, follow
`../../policies/github-control-plane-policy.md` relative to this skill in
source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/github-control-plane-policy.md`
after filesystem installation.

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

Context continuity: follow
`../../policies/context-continuity-policy.md` relative to this skill in source
or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/context-continuity-policy.md`
after filesystem installation.

Exact-head content review: when routing an existing change request toward
merge readiness,
follow `../../policies/exact-head-merge-review-contract.md` relative to this
skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/exact-head-merge-review-contract.md`
after filesystem installation.

## Purpose

Use this skill when Codex needs to decide how to advance a bounded project or task: handle it as a single implementation slice, plan first, delegate or hand off, run review, prepare continuation, or stop for a human gate.

This skill is the shared orchestration layer for Codex CLI and Codex Desktop.
It may use bounded shared subagents when the runtime supports them and ownership
is disjoint. Desktop user-owned task/thread/worktree actions remain a separate
runtime adapter. When a capability is unavailable, use the current session,
prompts, task briefs, continuation prompts, or a sequential execution path.

## Routing Rules

- If the task is already a single clear implementation slice, use `implementation-slice` semantics and do not over-plan.
- If the user delegates a larger bounded delivery objective, select `project-delivery` as the outer workflow.
- If already operating inside `project-delivery`, select the next phase or slice instead of routing back to `project-delivery`.
- If source-of-truth or task order is unclear, use `planning`, `closure-triage`, or `task-continuation`.
- If ordinary review evidence is needed, route code or mixed changes to `code-review`, high-risk code or mixed changes to `code-review-deep`, and docs-only or docs-dominant changes to `docs-review`.
- If a formal blocking decision is required for commit readiness, PR readiness, merge readiness, or repo policy, route through `code-review-gate` or `docs-review-gate`.
- If review findings need closure, route fixes through the smallest primitive workflow: `implementation-slice` for code or mixed changes, `docs-update` for docs-only changes, then rerun the relevant review primitive or formal gate for the current stage.
- If a change request exists, never route pre-commit review evidence directly
  to merge readiness. Require deterministic verification, complete exact-head
  content Merge Review, code/documentation coherence, and the formal gate. A
  changed head invalidates the content verdict. Evaluate provider enforcement
  separately; require GitHub receipts, Checks, Apps, Actions, or rulesets only
  when repository policy selects the GitHub enforcement profile.
- When a fix closes findings, rerun code review and Security Diff Scan over the
  smallest justified affected scope; widen when shared assumptions changed.
  Continue automatically after clean internal stages when the next action is
  read-only or already authorized.
- Review closure loops default to 2 rounds unless the user or repo policy sets a different maximum. Reaching that threshold while work remains incomplete triggers the shared context-health assessment; it does not automatically create, fork, or roll over a task.
- Apply the context-continuity policy before choosing among current-context continuation, regrounding, bounded subagent delegation, fresh rollover preparation, or a human gate. Token/compaction pressure is advisory only.
- If the next unit should move to another session or worker, prepare a bounded continuation prompt or task brief.
- Stop when a human gate is required.

## Delegation Economy

Before selecting a custom-agent candidate, perform the shared automatic
qualification procedure in `loop-engineering` (Agent Routing). The parent
classifies the actual task, checks its qualified scope, gathers current public
runtime facts and invokes the installed `agent-route` command itself. Do not
ask the user to supply qualification JSON or repeat CLI arguments. The router
discovers the explicitly approved user-level store; a missing or inapplicable
record retains baseline routing. Do not turn a past CLI observation into
Desktop availability or infer native dispatch support from installation alone.

Delegate by disjoint ownership and useful parallelism, not by one worker per
discipline. Keep implementation, focused tests, and directly related docs with
one owner unless they form independently verifiable artifacts; keep author and
reviewer separate, and add an independent security reviewer only when the risk
or selected workflow requires it.

After dispatching a bounded independent set, continue parent-owned work and
then use one supported wait-for-any or mailbox wait for the active set. Do not
poll unchanged status. Workers report only decision-blocking questions and one
final structured receipt. Integrate completed results while other workers run,
and reuse the original worker for bounded follow-up when its ownership and
source revision remain valid.

## Workflow

1. Discover source-of-truth files and current state.
2. Classify the request as a single task, bounded delivery objective, review, follow-up, continuation, or safety-blocked/ambiguous work.
3. Select the smallest safe next action and the appropriate skill or workflow.
4. Choose execution mode: current session, shared subagents, sequential fallback, Desktop control-plane handoff, or stop for human decision.
5. Integrate or inspect results before advancing.
6. Run relevant verification and the review primitive or formal gate that matches the current stage.
7. Prepare continuation or readiness evidence when useful.
8. After the configured unfinished review/fix threshold, run or prepare the
   context-health assessment. Execute no runtime rollover action without a
   complete checkpoint, exclusive sequential ownership transfer, source
   stop-writing, safe runtime capability, idempotency/lineage checks, and the
   separate authorization required for that exact action.

## Output

- Request classification
- Selected next action
- Execution mode
- Skill or workflow routed to
- Verification and review or gate result
- Handoff or continuation prompt, if useful
- Human gate, if any
