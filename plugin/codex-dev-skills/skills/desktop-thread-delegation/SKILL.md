---
name: desktop-thread-delegation
description: Thin Codex Desktop task and thread control adapter for a handoff already selected by the shared orchestration workflow.
---

# desktop-thread-delegation

Runtime compatibility: desktop

## Entry And Operation Selection

Use this thin Desktop UX adapter after shared orchestration selects a bounded
handoff and the user wants it continued in a user-owned task, thread, or
worktree. It does not choose work, redefine completion, or own shared
subagent delegation. `Desktop` remains a runtime compatibility label for task,
worktree, and scheduling controls in the ChatGPT desktop app.

Continue in the current task when scope and ownership allow it. For a native
operation, read only the selected reference before acting:

| Mode or need | Required reference |
| --- | --- |
| `desktop-thread-create`, `desktop-thread-fork`, `desktop-worktree-fork` | [Create/fork](references/create-fork.md) |
| `desktop-fresh-rollover` | [Fresh rollover](references/fresh-rollover.md) and [Create/fork](references/create-fork.md) |
| Inspect, wait, navigate, display, or handoff | [Observation and handoff](references/observe-handoff.md) |
| `desktop-thread-share` | [Sharing and privacy](references/share.md) |

Creating a new or background Desktop task requires an explicit user request.
Prepare the concrete prompt and action first; reuse existing authorization
while its exact target, scope, and effect remain unchanged. Read-only discovery
needed by the authorized task does not require a new approval. Return a
`new-thread-prompt` when an operation is unavailable or lacks authority.

## Common Boundaries

- Re-read the selected brief, source files, ownership, review evidence, and Git
  state relevant to the operation. Return to orchestration if readiness changed.
- Active callable schema plus call-site validation governs native operations.
  `../../docs/native-runtime-capabilities.md` is the source/plugin reference;
  filesystem installation also places it at
  `~/.codex/templates/docs/native-runtime-capabilities.md`. Historical schema
  notes do not override the callable. Do not invent missing fields or IDs.
- Distinguish ready `threadId`, queued `clientThreadId`, and observed `hostId`.
  Never pass a queued ID as a ready ID or infer project/host identity from a
  title, summary, or private state. The selected reference defines exact
  project association and host readback.
- Prepare self-contained, scope-limited prompts and retain a single writer for
  sequential continuation. A child must re-read repository truth, use its
  selected verification environment, avoid recursive session dispatch, and
  return changed files, evidence, questions, and residual risk.
- Use only runtime-provided callables. Do not edit Desktop databases, logs,
  sessions, auth files, caches, or other private runtime state; use unpublished
  endpoints/UI scraping; or start app-server, remote-control, wrapper daemons,
  sidecars, or background services. Direct app-server thread endpoints are
  outside this adapter even when public. A repository-local helper is not a
  thread-control path and must not be imported, executed, or recommended.
- Sharing requires the separate disclosure review in its mandatory reference.
  Task creation/fork authority does not authorize sharing or other external
  writes. Destructive actions and material scope/risk changes retain gates.

## Result And Fallback

Report only applicable facts: selected action/target, prompt/title when prepared,
observed callable and result, ready/queued/host IDs, required association
readback, dispatch/UI/visibility distinctions, and unresolved risk or gate.
The originating task owns integration, verification, review, commit/PR
readiness, and merge gates. Goal, task, and scheduler states are coordination
context rather than repository completion proof.

If capabilities fail, return a paste-ready prompt or use shared sequential
execution/subagents when supported. CLI does not possess Desktop task tools.
Do not emulate them through private state or claim creation/transfer/completion
from a fallback. Stop for conflicting source truth, ambiguous identity/scope,
overlapping writers, insufficient high-risk verification, absent authority,
unclear callable semantics, or unresolved privacy/disclosure concerns.
