# Skill Selection Guide

This compact guide helps new users choose the smallest skill or gate that matches the work in front of them.

## 選擇契約與執行方式

下表選出適用技能的必要契約；一般規劃、實作、文件與審查可由模型直接完成，
或採用符合契約的原生／內建／本地方式，不必因入口不同重做同一工作。
先讀所選技能與[共用選用規則](../policies/reusable-workflow-contract.md#contract-preserving-capability-selection)，
保留必要步驟、工具、證據、輸出及 gate。直接呼叫一般技能也適用，不必先啟動
`project-orchestrator`；使用者指定技能或方法時仍依其要求。

只檢查當次相關能力，不掃描整套環境，也不依模型自評認定品質等價。能力未知或
不相容就使用既有安全流程；部分相容則保留有效證據並補足缺口。原生 review
只有 PASS 時，不能藉由重排欄位取得 gate 通過。持久記憶的 scope、backend、
寫入與刪除仍由專屬資料契約控制，不因可用原生 recall 而切換。

這是執行自由度的相容性調整，不保證模型行為或效能。
代表性[契約審查案例](loops/issue-232/selection-cases.md)區分預期判定與實測證據。

## Fast Decision Table

| Situation | Use | Why |
| --- | --- | --- |
| The change is one clear coding task. | `implementation-slice` | Focused implementation with read-before-write inspection, scoped edits, verification, and diff review. |
| The change is documentation alignment or a docs-only update. | `docs-update` | Updates docs from verified code, specs, plans, or behavior without introducing a broader delivery workflow. |
| You need ordinary read-only feedback on code or mixed changes. | `code-review` | Routine review primitive for correctness, regressions, contracts, and missing tests. |
| You need ordinary read-only feedback on docs-only or docs-dominant changes. | `docs-review` | Routine documentation review primitive for accuracy, stale names, links, unsupported claims, and structure. |
| The code or mixed diff is security-sensitive, release-sensitive, packaging-related, migration-related, or cross-module. | `code-review-deep` | Higher-scrutiny review primitive for material risk. |
| A workflow needs a formal blocking decision before commit readiness, PR readiness, merge readiness, or an explicit repo-policy gate. | `code-review-gate` or `docs-review-gate` | Formal gate adapters route to the right review primitive, record evidence, and block on unresolved MUST-FIX findings. |
| A branch needs base-to-head merge quality review. | `merge-review` | Reviews scope, DoD, verification and coherence for the exact content range. Provider enforcement follows the explicitly selected repo profile; pre-commit verdicts remain input only. |
| A branch needs a formal readiness decision before PR handoff, merge readiness, or final approval. | `merge-readiness-gate` | Records exact-head content readiness separately from optional provider CI/receipt/readback requirements. |
| The user explicitly selects a durable loop, or repo policy requires a loop spec, ledger and production decision contract. | `loop-engineering` | Routes from durable loop state through existing phase skills, verifies current evidence and stops at real human gates. |
| Codex should classify the next safe action or run a bounded review/fix closure loop. | `project-orchestrator` | Routes between planning, implementation, docs update, review primitives, formal gates, continuation, or human decision. |
| Codex should carry a bounded objective through discovery, implementation, verification, review, docs sync, and PR readiness. | `project-delivery` | Delivery workflow for multi-step but bounded objectives that still stop at the next human gate. |
| A bounded milestone should be checked and advanced across repeated invocations until complete or blocked. | `milestone-continuation` | Upper-layer loop that checks task completion, selects the next ready task, and routes through existing workflows without owning runtime scheduling. |
| Shared orchestration selected a bounded task and the user wants one separate, resumed, or forked Codex CLI session. | `cli-session-handoff` | Thin CLI control-plane adapter over documented stable non-interactive start/resume plus the observed and locally qualified public-help fork form, together with a manual exact-UUID interactive-fork handoff; the executor path validates the exact clean worktree and sandbox, while interactive fork directory reuse remains explicit. |
| Codex Desktop should coordinate shared delivery with user-owned Desktop tasks, threads, worktrees, or scheduling. | `desktop-project-delivery` | Thin Desktop control-plane entry point over shared project delivery and subagent semantics. |
| Shared orchestration has selected a bounded handoff and Codex Desktop should choose its task/thread/worktree execution mode. | `desktop-thread-delegation` | Thin Desktop control-plane adapter that can use runtime thread tools when authorized, while falling back to the already selected task brief or continuation prompt. |
| The user explicitly asks to create or rename a sidebar section, move an exact task/project, or reorder/delete exact sidebar identities in Codex Desktop. | `desktop-sidebar-organization` | Separate Desktop-only organization control plane with fresh discovery, exact-ID dry-run, explicit authority, readback, and fail-closed fallback. |

The three older Desktop-named gates remain installable only as deprecated
compatibility aliases:

| Compatibility name | Prefer | Contract |
| --- | --- | --- |
| `desktop-spec-plan-gate` | `planning` | No Desktop callable; preserves existing prompts while routing to shared planning and DoD behavior. |
| `desktop-implementation-gate` | `code-review`, `code-review-deep`, `docs-review`, then the matching shared formal gate when required | No Desktop callable or separate integration decision. |
| `desktop-pr-merge-gate` | `merge-readiness-gate` | No Desktop callable or separate merge decision. |

These aliases disable implicit invocation with `agents/openai.yaml` while
retaining explicit use. New workflows should not select them. Use
`desktop-project-delivery` only for the Desktop delivery entry point and
`desktop-thread-delegation` only for the Desktop task/thread/worktree control
plane. Use `desktop-sidebar-organization` only for an explicitly requested
sidebar organization action; it is not a task creation or navigation adapter.

## Runtime Entry Boundary

Codex CLI enters shared skills directly. CLI `/agent` exposes
the shared subagent control plane, while `/new`, `/fork`, `/resume`, and
`/archive` manage CLI sessions rather than Desktop tasks. Use `/app` or
`codex app <path>` only when the user intentionally moves the work into the
ChatGPT desktop app.

When shared orchestration has already selected a task,
`cli-session-handoff` may invoke one explicitly authorized
`codex exec --json` start or exact-UUID resume. It is not a task selector,
scheduler, background observer, or Desktop adapter. Its receipt cannot replace
parent diff inspection, verification, review, or completion evidence.

Once work is in the Desktop surface, add `desktop-project-delivery` or
`desktop-thread-delegation` only for task, thread, worktree, handoff, or
scheduling controls. Add `desktop-sidebar-organization` only for an exact
organization request after fresh list-based discovery. A runtime transition
never changes the shared objective, authority, verification, review, or
completion contract.

## Review Primitive Or Formal Gate

Use review primitives for ordinary feedback:

- `code-review` for code or mixed diffs.
- `docs-review` for docs-only or docs-dominant diffs.
- `code-review-deep` for high-risk code or mixed diffs.

Use formal gates only when the workflow needs a blocking readiness decision:

- `code-review-gate` for code or mixed commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `docs-review-gate` for docs-only or docs-dominant commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- `merge-readiness-gate` for branch readiness before PR handoff, merge readiness, or final human approval.

Formal gates are evidence and decision layers. Reuse a primitive result when its
diff, scope, source assumptions and verification remain valid; entering a gate
alone does not require another complete review. A changed request head still
requires complete exact-head Merge Review. Gate evidence does not authorize
commit, push, merge, deploy or other external actions.

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

- `loop-engineering` for explicitly selected or repo-required durable loops.
- `project-orchestrator` to choose the next safe action, route work, or run a bounded review closure loop.
- `project-delivery` to advance a bounded objective through implementation, verification, review, docs sync, and PR readiness.
- `milestone-continuation` to keep a bounded milestone moving across repeated invocations by checking the current task, selecting the next ready task, and stopping at human gates.
- `cli-session-handoff` only for one selected CLI session mutation after exact
  authorization and target validation.
- `desktop-project-delivery` only when the Desktop runtime is intentionally part of the workflow.
- `desktop-thread-delegation` when the Desktop runtime may open a new thread, but the main thread must still choose the next safe task and retain review or merge gates.
- `desktop-sidebar-organization` for a concrete Desktop organization request.
  Resolve IDs from the relevant registry; a reversible reorder needs current
  complete membership where required, while deletion retains its destructive gate.

Do not add a Desktop-prefixed gate after these entry points. Planning, ordinary
review, formal review gates, merge readiness, Goal evidence, subagent
delegation, and completion semantics remain shared. Goal state is coordination
context, not repository completion proof.

Use `project-delivery` for ordinary bounded delivery; autonomous continuation
and baseline subagents alone do not require a ledger. Use `loop-engineering`
when its durable contract is explicitly selected or required. Use
`milestone-continuation` for repeated milestone progress from task state, and
`task-continuation` when the immediate goal is selecting a next task or handoff.

Read only the selected operation references in the loop and runtime-adapter
entry points. Candidate qualification, optional memory, GitNexus and scan
recovery have separate triggers; moving them out of the entry point does not
relax their contracts when applicable.

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
plus `hostId` from a queued `clientThreadId`; do not infer current schema from
historical examples. Desktop Runtime Wrapper V1 is retired and provides no
runnable or importable workflow path.
Use `wait_threads` only as bounded, host-aware observation when exposed; its
compact snapshots are not shared-subagent semantics or completion evidence.

## Desktop Sidebar Organization

Choose `desktop-sidebar-organization` only for the exposed Desktop sidebar
control plane. Start with fresh `list_threads` and/or `list_projects`, build a
dry-run plan from exact runtime IDs, and fail closed on stale, duplicate,
missing, queued, or incomplete identities. Titles and summaries are untrusted
display text. CLI/manual fallback returns the exact plan without claiming that
a sidebar mutation ran; it must not create or navigate a task, scrape UI or
private state, or start a daemon.

## Merge Readiness

Use `merge-review` when you want read-only base-to-head review of merge quality and DoD alignment.

Use `merge-review-deep` when the branch is high-risk, release-sensitive, or policy-required.

Use `merge-readiness-gate` when the workflow needs a formal readiness state before PR handoff, merge readiness, or final approval. The gate can report readiness, blockers, residual risk, and the next human decision; it does not authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes by itself. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.

## Rule Of Thumb

Start with the smallest direct skill. Move to orchestration, delivery, deep review, or formal gates only when the task scope, risk, or repo policy needs that extra structure.
