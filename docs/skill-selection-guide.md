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
| A branch needs base-to-head merge quality review. | `merge-review` | Routine merge review primitive for scope, DoD alignment, test evidence, docs sync, and unresolved findings. |
| A branch needs a formal readiness decision before PR handoff, merge readiness, or final approval. | `merge-readiness-gate` | Formal branch readiness gate that summarizes evidence, blockers, residual risk, and the human approval boundary. |
| Codex should classify the next safe action or run a bounded review/fix closure loop. | `project-orchestrator` | Routes between planning, implementation, docs update, review primitives, formal gates, continuation, or human decision. |
| Codex should carry a bounded objective through discovery, implementation, verification, review, docs sync, and PR readiness. | `project-delivery` | Delivery workflow for multi-step but bounded objectives that still stop at the next human gate. |
| Codex Desktop should coordinate delegated project work across Desktop threads or workers. | `desktop-project-delivery` | Desktop-only delivery entry point; CLI fallback is `project-delivery` plus explicit task briefs or continuation prompts. |
| Codex Desktop should choose the next safe task and decide whether to continue here or hand off to a new thread. | `desktop-thread-delegation` | Desktop-only continuation adapter that can use runtime thread tools when authorized, while falling back to a paste-ready prompt. |

## Review Primitive Or Formal Gate

Use review primitives for ordinary feedback:

- `code-review` for code or mixed diffs.
- `docs-review` for docs-only or docs-dominant diffs.
- `code-review-deep` for high-risk code or mixed diffs.

Use formal gates only when the workflow needs a blocking readiness decision:

- `code-review-gate` for code or mixed commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `docs-review-gate` for docs-only or docs-dominant commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `merge-readiness-gate` for branch readiness before PR handoff, merge readiness, or final human approval.

Formal gates are evidence and decision layers. They do not replace routine review primitives for every review pass.

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

- `project-orchestrator` to choose the next safe action, route work, or run a bounded review closure loop.
- `project-delivery` to advance a bounded objective through implementation, verification, review, docs sync, and PR readiness.
- `desktop-project-delivery` only when the Desktop runtime is intentionally part of the workflow.
- `desktop-thread-delegation` when the Desktop runtime may open a new thread, but the main thread must still choose the next safe task and retain review or merge gates.

## Desktop Thread Delegation

Choose `desktop-thread-delegation` only when the active runtime is Codex Desktop and the workflow may continue in the current thread, prepare a handoff prompt, or use a supported Desktop thread action. Desktop thread delegation is Desktop-only runtime behavior, not a Codex CLI guarantee.

The CLI fallback is a paste-ready prompt, task brief, continuation prompt, or sequential execution path. Do not state or imply that Codex CLI can open, fork, continue, or message Desktop threads unless a documented or configured thread capability is actually available.

Before relying on any runtime thread tool or documented API, record contract evidence consistent with [Runtime Compatibility](runtime-compatibility.md) and [Desktop Runtime Adapter V2 Boundary](runtime-adapter-v2.md):

- runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, `read_thread`, or the documented equivalent;
- underlying tool or API contract version when exposed;
- `version unavailable` when no version is exposed, plus a verifiable capability source such as the active tool list, connector metadata, official documentation version, or runtime-reported schema;
- minimal request shape used by the workflow, including required parameters, optional parameters used, and target identity fields;
- minimal response shape relied on by the workflow, such as created thread identifier, target thread identifier, action status, error shape, lifecycle state, or fallback signal;
- `last_verified` date for the contract evidence;
- wrapper, workflow, or adapter mapping to the underlying contract, including mappings where the underlying version is unavailable.

After a runtime, connector, schema, or documentation change, re-compare the old and new contract before using the thread action. Pay particular attention to required parameters, response shape, error shape, permission or authentication changes, and renamed, removed, or newly state-changing operations.

## Merge Readiness

Use `merge-review` when you want read-only base-to-head review of merge quality and DoD alignment.

Use `merge-review-deep` when the branch is high-risk, release-sensitive, or policy-required.

Use `merge-readiness-gate` when the workflow needs a formal readiness state before PR handoff, merge readiness, or final approval. The gate can report readiness, blockers, residual risk, and the next human decision; it does not authorize merge by itself.

## Rule Of Thumb

Start with the smallest direct skill. Move to orchestration, delivery, deep review, or formal gates only when the task scope, risk, or repo policy needs that extra structure.
