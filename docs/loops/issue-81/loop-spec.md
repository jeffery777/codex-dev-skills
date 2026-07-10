# Loop Engineering V1: Issue 81

## Objective

Deliver an executable, evidence-driven loop engineering core for Codex CLI and
Codex Desktop. Keep workflow semantics shared, integrate native goal and
subagent capabilities through explicit adapters, and leave runtime-specific
thread, scheduling, and UI control outside the shared state machine.

GitHub issue: <https://github.com/jeffery777/codex-dev-skills/issues/81>

## Source Of Truth

- Repository policy: `AGENTS.md`
- GitHub objective and acceptance criteria: issue `#81`
- This loop spec
- Implementation plan: `docs/loops/issue-81/implementation-plan.md`
- Current branch and git diff
- Executable schema, transition, evaluation, and test results introduced by
  this objective

Runtime goal state, subagent summaries, scheduled wakeups, Desktop thread
status, and chat summaries are coordination context. They do not independently
prove repository task completion.

## Scope

### In Scope

- canonical loop and task lifecycle contracts;
- structured state validation and legal transition enforcement;
- revision, event integrity, idempotency, and claim fencing rules;
- deterministic, replayable v1 migration preview with an embedded provenance anchor;
- native goal and shared subagent capability mapping;
- runtime-specific scheduler and Desktop thread adapter boundaries;
- production-backed workflow eval fixtures and metrics;
- protected event provenance and out-of-band live authorization;
- resumable security-scan reporting and Goal/worker projection recovery;
- public docs, templates, catalog, installer, and validation alignment.

### Out Of Scope

- editing the separate global Codex profile repository;
- private or reverse-engineered Desktop runtime state;
- push, PR creation, merge, release, or deployment without separate exact
  authorization;
- broad deletion of legacy Desktop wrapper code in the same slice.

## Authority Model

1. The loop spec and task manifest define stable objective and task contracts.
2. Validated events define internally consistent operational task transitions;
   they do not authenticate their own origin.
3. A materialized state document is a derived view and must carry its source
   revision.
4. Claim state is coordination authority only when the active store can provide
   atomic acquisition and fencing. Without a shared store, concurrency is one.
5. Git, verification, review, and accepted platform state provide completion
   evidence.
6. Goal, subagent, scheduler, hook, and Desktop thread state never replace the
   preceding authorities.

## Completion Criteria

- One executable production core owns routing and transition decisions.
- Structured parsing rejects malformed or semantically invalid state.
- State changes reject stale revisions, invalid fencing tokens, event tampering,
  and conflicting idempotency replays.
- Manifest and operational task status no longer conflict.
- Native goal and shared subagent behavior are documented without model- or
  host-private assumptions.
- Workflow evals execute the production decision function and cover false
  completion, human gates, resume, claim conflicts, capability fallbacks, and
  CLI/Desktop semantic equivalence.
- Full repository validation and tests pass.
- Formal review has no unresolved MUST-FIX, SHOULD-FIX, or NIT findings.
- A follow-up Codex Security diff scan completes with no reportable findings.

## Human Gates

Stop for unresolved product semantics, destructive cleanup, dependency or
packaging changes whose public installation impact cannot be verified, push,
PR creation, merge, release, deployment, or other external publication not
already authorized.
