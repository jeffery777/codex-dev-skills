# Skill Selection Guide

This compact guide helps new users choose the smallest skill or gate that matches the work in front of them.

## Fast Decision Table

| Situation | Use | Why |
| --- | --- | --- |
| The change is one clear coding task. | `implementation-slice` | Focused implementation with read-before-write inspection, scoped edits, verification, and diff review. |
| The change is documentation alignment or a docs-only update. | `docs-update` | Updates docs from verified code, specs, plans, or behavior without introducing a broader delivery workflow. |
| You need ordinary read-only feedback on code or mixed changes. | `code-review` | Routine review primitive for correctness, regressions, contracts, and missing tests. |
| You need ordinary read-only feedback on docs-only or docs-dominant changes. | `docs-review` | Routine documentation review primitive for accuracy, stale names, links, unsupported claims, and structure. |
| The code or mixed diff is security-sensitive, release-sensitive, packaging-related, migration-related, or cross-module. | `code-review-deep` | Higher-scrutiny review primitive for material risk. |
| A workflow needs a formal blocking decision before commit readiness, PR readiness, merge readiness, or an explicit repo-policy gate. | `code-review-gate` or `docs-review-gate` | Formal gate adapters route to the right review primitive, record evidence, and block on unresolved MUST-FIX findings. |
| A branch needs base-to-head merge quality review. | `merge-review` | Routine merge review primitive for scope, DoD alignment, test evidence, docs sync, and unresolved findings. It produces review evidence, not merge authorization. |
| A branch needs a formal readiness decision before PR handoff, merge readiness, or final approval. | `merge-readiness-gate` | Formal branch readiness evidence-and-decision layer that summarizes evidence, blockers, residual risk, and the human approval boundary. |
| Codex should keep a clear bounded objective moving through repeated plan, implementation, verification, review, continuation, handoff, or gate decisions. | `loop-engineering` | Explicit loop entrypoint that repeatedly bootstraps from durable source of truth, routes to existing phase skills, verifies evidence, and stops at human gates. |
| Codex should classify the next safe action or run a bounded review/fix closure loop. | `project-orchestrator` | Routes between planning, implementation, docs update, review primitives, formal gates, continuation, or human decision. |
| Codex should carry a bounded objective through discovery, implementation, verification, review, docs sync, and PR readiness. | `project-delivery` | Delivery workflow for multi-step but bounded objectives that still stop at the next human gate. |
| A bounded milestone should be checked and advanced across repeated invocations until complete or blocked. | `milestone-continuation` | Upper-layer loop that checks task completion, selects the next ready task, and routes through existing workflows without owning runtime scheduling. |
| Codex Desktop should coordinate shared delivery with user-owned Desktop tasks, threads, worktrees, or scheduling. | `desktop-project-delivery` | Thin Desktop control-plane entry point over shared project delivery and subagent semantics. |
| Shared orchestration has selected a bounded handoff and Codex Desktop should choose its task/thread/worktree execution mode. | `desktop-thread-delegation` | Thin Desktop control-plane adapter that can use runtime thread tools when authorized, while falling back to the already selected task brief or continuation prompt. |

The three older Desktop-named gates remain installable only as deprecated
compatibility aliases:

| Compatibility name | Prefer | Contract |
| --- | --- | --- |
| `desktop-spec-plan-gate` | `planning` | No Desktop callable; preserves existing prompts while routing to shared planning and DoD behavior. |
| `desktop-implementation-gate` | `code-review`, `code-review-deep`, `docs-review`, then the matching shared formal gate when required | No Desktop callable or separate integration decision. |
| `desktop-pr-merge-gate` | `merge-readiness-gate` | No Desktop callable or separate merge decision. |

New workflows should not select these aliases. Use
`desktop-project-delivery` only for the Desktop delivery entry point and
`desktop-thread-delegation` only for the Desktop task/thread/worktree control
plane.

## Runtime Entry Boundary

Codex CLI enters shared skills directly. CLI `/agent` and `/subagents` expose
the shared subagent control plane, while `/new`, `/fork`, `/resume`, and
`/archive` manage CLI sessions rather than Desktop tasks. Use `/app` or
`codex app <path>` only when the user intentionally moves the work into the
ChatGPT desktop app.

Once work is in the Desktop surface, add `desktop-project-delivery` or
`desktop-thread-delegation` only for task, thread, worktree, handoff, or
scheduling controls. A runtime transition never changes the shared objective,
authority, verification, review, or completion contract.

## Review Primitive Or Formal Gate

Use review primitives for ordinary feedback:

- `code-review` for code or mixed diffs.
- `docs-review` for docs-only or docs-dominant diffs.
- `code-review-deep` for high-risk code or mixed diffs.

Use formal gates only when the workflow needs a blocking readiness decision:

- `code-review-gate` for code or mixed commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `docs-review-gate` for docs-only or docs-dominant commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `merge-readiness-gate` for branch readiness before PR handoff, merge readiness, or final human approval.

Formal gates are evidence and decision layers. They do not replace routine review primitives for every review pass, and their evidence does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes.

## Routine Versus Deep Review

Use routine review when the likely failure modes are local to the changed files and can be evaluated from the ordinary diff, nearby tests, and repo instructions.

Use deep review when the change has material blast radius, hidden failure modes, or evidence that needs to be challenged instead of accepted at face value.

| Review need | Routine choice | Deep choice |
| --- | --- | --- |
| Working-tree or patch review | `code-review` | `code-review-deep` |
| Base-to-head merge quality review | `merge-review` | `merge-review-deep` |
| Docs-only or docs-dominant review | `docs-review` | Usually stay with `docs-review`; escalate only if the docs encode high-risk operational, security, migration, release, or compliance guidance. |

Routine review is usually enough for:

- small parser, UI, docs, or configuration fixes with narrow ownership;
- changes covered by focused tests or clear manual verification;
- non-release docs updates that do not change public contracts or operational instructions;
- follow-up fixes where prior findings are local and directly verifiable.

Deep review is appropriate when the diff touches or depends on:

- credentials, permissions, identity, tenant boundaries, sensitive data, payments, or billing;
- migrations, persistent data, rollback paths, deployment, infrastructure, or release readiness;
- dependency supply chain, packaging, file upload, parsing, external APIs, cryptography, or randomness;
- cross-module contracts, concurrency, idempotency, observability, or failure handling;
- stale review artifacts, summarized evidence, or prior blocker closure that needs source-level re-checking.

When unsure, start with routine review and escalate only the risky surface. For example, a docs-only README link fix should use `docs-review`; a release guide that changes rollback instructions may still need deeper scrutiny because the operational consequence is larger than the text diff.

## Focused Work Or Delivery Work

Use focused skills when the next action is already clear:

- `implementation-slice` for a bounded code change.
- `docs-update` for a bounded documentation change.
- `planning` when the scope, DoD, or verification strategy needs to be defined before editing.

Use orchestration or delivery skills when Codex must decide or coordinate multiple steps:

- `loop-engineering` to own the repeated bootstrap, classify, route, act, verify, review, continue, handoff, stop, or complete cycle for a clear bounded objective.
- `project-orchestrator` to choose the next safe action, route work, or run a bounded review closure loop.
- `project-delivery` to advance a bounded objective through implementation, verification, review, docs sync, and PR readiness.
- `milestone-continuation` to keep a bounded milestone moving across repeated invocations by checking the current task, selecting the next ready task, and stopping at human gates.
- `desktop-project-delivery` only when the Desktop runtime is intentionally part of the workflow.
- `desktop-thread-delegation` when the Desktop runtime may open a new thread, but the main thread must still choose the next safe task and retain review or merge gates.

Do not add a Desktop-prefixed gate after these entry points. Planning, ordinary
review, formal review gates, merge readiness, Goal evidence, subagent
delegation, and completion semantics remain shared. Goal state is coordination
context, not repository completion proof.

Use `loop-engineering` when the user wants the agent to own the whole repeated decision loop and dynamically choose among existing workflows as state changes. Use `project-delivery` directly when the request is one bounded delivery effort and does not need a named loop entrypoint. Use `milestone-continuation` instead of `project-delivery` when the distinctive need is repeated milestone progress from durable task state. Use `task-continuation` when the immediate goal is only to choose the next safe task or prepare a handoff prompt.

`loop-engineering` must remain a thin entrypoint. It does not replace implementation, documentation, review, formal gate, continuation, milestone, or Desktop delegation skills. It should classify, route, report, and stop rather than invent a second execution engine.

## Desktop Thread Delegation

Choose `desktop-thread-delegation` only when the active runtime is Codex Desktop and the workflow may continue in the current thread, prepare a handoff prompt, or use a supported Desktop thread action. Desktop thread delegation is Desktop-only runtime behavior, not a Codex CLI guarantee.

Shared subagent delegation remains available independently of this skill.
Choose this adapter only for a user-owned Desktop task/thread/worktree action or
Desktop scheduling. The CLI fallback is a paste-ready prompt, task brief,
continuation prompt, shared subagent packet, or sequential execution path. Do
not claim that a CLI session can control Desktop tasks unless a documented
callable is actually present.

Before using a runtime thread callable, record contract evidence consistent
with [Runtime Compatibility](runtime-compatibility.md):

- runtime thread tool or API contract name, such as `create_thread`,
  `fork_thread`, `list_threads`, `read_thread`, `wait_threads`,
  `send_message_to_thread`, `handoff_thread`, or the documented equivalent;
- underlying tool or API contract version when exposed;
- `version unavailable` when no version is exposed, plus a verifiable capability source such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
- minimal request shape used by the workflow, including required parameters, optional parameters used, and target identity fields;
- minimal response shape relied on by the workflow, such as created thread identifier, target thread identifier, action status, error shape, lifecycle state, or fallback signal;
- `last_verified` date for the contract evidence;
- workflow or adapter mapping to the underlying contract.

Validate target identity, permission/auth failures, and the actual response at
the call site. Current creation responses distinguish an immediate `threadId`
plus `hostId` from a queued `clientThreadId`; do not reuse historical wrapper
response shapes as active schema evidence. Legacy `desktop_runtime_*` helpers
remain historical compatibility evidence only and must not be executed by the
active workflow.
Use `wait_threads` only as bounded, host-aware observation when exposed; its
compact snapshots are not shared-subagent semantics or completion evidence.

## Merge Readiness

Use `merge-review` when you want read-only base-to-head review of merge quality and DoD alignment.

Use `merge-review-deep` when the branch is high-risk, release-sensitive, or policy-required.

Use `merge-readiness-gate` when the workflow needs a formal readiness state before PR handoff, merge readiness, or final approval. The gate can report readiness, blockers, residual risk, and the next human decision; it does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes by itself. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.

## Rule Of Thumb

Start with the smallest direct skill. Move to orchestration, delivery, deep review, or formal gates only when the task scope, risk, or repo policy needs that extra structure.
