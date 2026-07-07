---
name: loop-engineering
description: Run an explicit loop engineering workflow for a clear bounded objective by repeatedly bootstrapping, routing, verifying, reviewing, continuing, handing off, or stopping at human gates.
---

# loop-engineering

Runtime compatibility: shared

## Purpose

Use this skill when the user asks Codex to run a loop engineering workflow, keep a bounded objective moving autonomously, or act as the delivery owner across repeated plan/implement/verify/review/continue cycles until the objective is complete or a human gate is reached.

This is a thin user-facing loop entrypoint. It classifies the current state, chooses the next safe workflow, integrates evidence, reports progress, and stops at gates. It does not replace `planning`, `implementation-slice`, `docs-update`, `project-orchestrator`, `project-delivery`, `task-continuation`, `milestone-continuation`, review primitives, formal gates, or Desktop-only delegation skills.

## Loop Contract

Each loop iteration must:

1. Re-bootstrap from durable repository source of truth:
   - repo instructions and policies;
   - project specs, loop specs, plans, task manifests, status docs, and reports;
   - review evidence, verification commands, templates, and current git state.
2. Treat chat summaries, prior handoffs, runtime summaries, and worker self-reports as context only.
3. Classify the request and current state:
   - `single-clear-task`
   - `bounded-delivery-objective`
   - `review-closure-loop`
   - `milestone-continuation-loop`
   - `handoff-or-continuation`
   - `desktop-delegation`
   - `human-gate`
   - `complete`
4. Choose the smallest workflow that can safely advance the objective.
5. Execute or prepare exactly that workflow, then verify and inspect evidence before deciding the next loop state.
6. Record or report what changed, what was verified, what remains uncertain, and which next action is selected.
7. Continue only while the objective, source of truth, permissions, risk, and verification are clear.

## Routing

| Loop state | Route to | Notes |
| --- | --- | --- |
| One clear implementation task | `implementation-slice` semantics | Keep edits scoped, verify, inspect diff, and report residual risk. |
| Docs-only or docs-dominant sync | `docs-update` | Update docs from verified specs, code, plans, or behavior. |
| Need task classification or review/fix closure | `project-orchestrator` | Use the smallest primitive workflow and bounded review closure rounds. |
| Bounded objective through PR readiness | `project-delivery` | Carry discovery, planning, implementation, verification, review, docs sync, and PR-readiness evidence to the next human gate. |
| Repeated milestone wakeups | `milestone-continuation` | Use durable milestone/task state; runtime scheduling remains outside the shared skill. |
| Next safe task or handoff prompt | `task-continuation` | Prepare continuation prompts, task briefs, or sequential execution paths from durable context. |
| Ordinary code or mixed review | `code-review` or `code-review-deep` | Use deep review for security, data, packaging, migration, release, or cross-module risk. |
| Ordinary docs review | `docs-review` | Use docs review for docs-only or docs-dominant changes. |
| Formal readiness decision | `code-review-gate`, `docs-review-gate`, or `merge-readiness-gate` | Use only for commit readiness, PR readiness, merge readiness, or explicit repo-policy gates. |
| Codex Desktop worker or thread handoff | `desktop-project-delivery` or `desktop-thread-delegation` | Desktop-only; requires supported runtime capability and exact user authorization before state-changing thread actions. |

## Runtime Boundaries

Shared loop behavior may read durable repository files, inspect git state, run local verification, prepare prompts or task briefs, and continue in the current session when safe.

Desktop-only behavior includes heartbeat wakeups, worker delegation, thread creation, thread forking, thread messaging, and thread inspection. A Desktop action may be used only when the active runtime exposes a documented capability, the target and response shape are clear, and the user has authorized the exact action.

In Codex CLI or any runtime without thread or scheduler capability, use the current session, a paste-ready prompt, a task brief, a continuation prompt, or a sequential execution path. Do not claim that a shared loop skill can open, fork, continue, read, or message a Desktop thread unless a documented or configured capability is actually available.

## Human Gates

Stop before continuing, delegating, mutating, or publishing when the next step involves:

- product ambiguity, unclear requirements, or unclear Definition of Done;
- source-of-truth conflict;
- scope expansion beyond the bounded objective;
- destructive action;
- external write without exact authorization;
- commit, push, PR creation, release, deploy, merge, platform comment, review submission, label/status mutation, or other platform-side mutation without exact authorization;
- material security, privacy, data, migration, payment, deployment, auth, permission, packaging, or public-contract risk;
- insufficient verification for a high-risk change;
- unclear worker ownership, task claim, lease state, or stale in-flight work;
- unsupported Desktop runtime behavior, unpublished Desktop internals, private runtime state, UI scraping, daemon, sidecar, app-server client, or unreviewed runtime adapter path.

## Completion Rules

Do not mark the loop objective complete from intent, chat memory, a summary, or passing tests alone. Completion requires source-of-truth evidence for every explicit requirement, named artifact, DoD item, verification command, review/gate requirement, and human-gate condition.

If evidence is incomplete, weak, indirect, or contradictory, continue gathering evidence, choose the next safe task, or stop at a human gate.

## Output

- Loop objective and current classification
- Source-of-truth files inspected
- Facts, inferences, and uncertainty
- Selected route and execution mode
- Files changed, if any
- Verification run and result
- Review or formal gate evidence, if used
- Loop iteration result: `continue`, `handoff-prepared`, `blocked-by-human-gate`, or `complete`
- Next selected task or required human decision
- Residual risk

## Templates

Use these templates when a target repository needs durable loop artifacts:

- `templates/orchestration/loop-engineering-spec.template.md`
- `templates/orchestration/loop-iteration-report.template.md`
- `templates/orchestration/loop-handoff-prompt.template.md`
- `templates/orchestration/task-claim-lease.template.yaml`

Reuse existing project, task, and review templates whenever they are sufficient instead of creating loop-specific duplicates.
