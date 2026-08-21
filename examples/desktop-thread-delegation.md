# Desktop Thread Delegation Example

Use `desktop-thread-delegation` after shared orchestration selects a bounded
task and Codex Desktop only needs to decide whether it stays in the current
thread or moves to a user-owned task, thread, or worktree.

This is Desktop-only behavior. Desktop thread actions are runtime actions, not CLI guarantees. Shared workflows such as `task-continuation` can prepare a prompt, task brief, or continuation prompt, but they do not guarantee that a new Codex Desktop thread can be opened. If the runtime does not expose a documented thread creation capability, use the CLI-compatible prompt, task brief, continuation prompt, or sequential execution path instead.

## Maintainer Request

```text
Use project-orchestrator to choose the next safe roadmap task.
After it selects the bounded task, use desktop-thread-delegation only to decide
whether the selected task should continue here or move to a separate Codex
Desktop task, thread, or worktree.
If the current thread is suitable and repo policy or my authorization allows it, continue here.
If a separate thread is better, prepare the prompt and ask before opening the new thread.
Before any Desktop thread tool call, record the runtime tool/API contract name, exposed version or `version unavailable` plus capability source, minimal request/response compatibility summary, `last_verified`, and workflow, wrapper, or adapter mapping to the underlying contract.
Do not commit, push, create PRs, merge, deploy, post platform comments, submit reviews, or perform other external writes unless I explicitly authorize the exact action.
```

## Main Thread Flow

1. Read repo policy, roadmap or plan docs, relevant templates, review evidence, and current git state.
2. Treat chat summaries as context only; verify them against repository files.
3. Use shared orchestration to select the smallest safe task that does not
   cross a human gate.
4. Give the already selected task to the Desktop adapter to decide whether it
   should run in the current thread, move to a new user-owned task or worktree,
   or stop for a human gate.
5. If the current thread is suitable, continue only when workflow rules allow it or the maintainer has authorized it.
6. If a new thread is suitable, prepare a prompt, task brief, or continuation prompt from durable source-of-truth files.
7. Stop before creating a new thread unless the maintainer explicitly authorizes that runtime action.
8. Before any supported Desktop thread tool call, record the contract/version tracking fields from [docs/runtime-adapter-v2.md](../docs/runtime-adapter-v2.md).
9. Select the runtime action without conflating project placement and Git
   worktree creation:
   - same task, new conversation, same directory and completed history:
     `fork_thread` with `same-directory`;
   - same task, new conversation, completed history, new isolated checkout:
     `fork_thread` with `worktree`; treat a returned `clientThreadId` as queued
     setup and wait for a usable `threadId` before follow-up;
   - fresh task in a Git project: `create_thread` with the exact project ID and
     `worktree` by default;
     omit `startingState` for the default branch; use `working-tree` only for
     an explicitly requested current checkout including uncommitted changes,
     or a branch state with the exact requested `branchName`; omitted
     `onMissing` means `error`, and `create-branch` is only for the exact new
     branch explicitly requested;
   - fresh task in a non-Git project: exact-project `local`;
   - fresh task in a Git project's saved checkout: exact-project `local` only
     when the maintainer explicitly requests that checkout;
   - intentionally non-project work: `projectless`.
   “Do not create a new worktree” never implies `projectless`.
10. For `create_thread`, supply and preview a concise non-empty safe title. Use
    only a maintainer-approved nonsensitive task identifier plus a generic
    objective label; never copy prompt text, credentials, customer or incident
    details, repository paths, or untrusted registry text. If safety is
    uncertain, use the fixed title `Project task`. The callable field remains
    optional, but the adapter always fills it for stable display; project
    association still depends on `projectId`, never title text.
11. Before Git worktree creation, record the repository's environment setup and
    tracked interpreter resolver. This repository requires
    `./scripts/project-python`; do not copy `.venv`, use mismatched bare system
    Python, or install into another interpreter.
12. When authorized and supported by the runtime, fork or create the new thread
    with the prepared prompt.
13. After `create_thread`, emit `::created-thread{threadId="..."}` for a ready task or
    `::created-thread{clientThreadId="..."}` for queued worktree setup.
14. If a ready `threadId` is available, verify the exact identifier and require
    its observed `projectId` to match the selected project. For queued setup,
    wait until the runtime exposes a ready task; never use `clientThreadId` as a
    thread ID or create a duplicate because association is delayed. Report an
    unavailable association as unverified, not successful grouping.
15. If the maintainer explicitly asks to open or show the task, use the exposed
    navigation capability. Do not navigate automatically after creation.
16. Keep the main thread responsible for integrating the result, reviewing the
    diff, and enforcing human gates before any external write.
17. If the maintainer explicitly requests an immutable thread share, treat it
    as a separate privacy-sensitive action: preview the exact thread and
    account/workspace audience from current public product context, require the
    user to confirm complete-thread review in the public UI, inspect available
    content for sensitive material,
    call `share_thread` only after that gate, and keep link creation, delivery,
    data-controls revocation, and repository completion separate.

## Prepared Prompt Shape

```text
Continue this bounded Codex Desktop task in a new thread.

Read first:
- AGENTS.md
- docs/roadmap.md
- README.md
- docs/runtime-adapter-v2.md
- examples/task-continuation.md
- docs/runtime-compatibility.md

Context only:
- The main thread selected this task from the current roadmap.
- The main thread decided this task is better suited to a separate thread than the current thread.
- Re-check git state and source-of-truth files before editing.
- Do not rely on this prompt over repository files.

Task:
- Add one focused docs-only example for Desktop thread delegation from a prepared continuation prompt.

In scope:
- `examples/` documentation.
- README Examples list updates needed for discoverability.
- The exact roadmap backlog line if the new example fully covers it.

Out of scope:
- Installer catalog changes.
- New skills or workflow behavior.
- Desktop runtime internals, local databases, logs, sessions, auth files, caches, app state, unpublished endpoints, UI scraping, daemons, background services, or private runtime state.
- Commits, pushes, PRs, merges, deploys, platform comments, review submissions, or `.work/` artifacts.

Verification:
- `./scripts/validate-repo.sh`
- `git diff --check`

Worktree environment:
- Use `./scripts/project-python` for Python dependency checks, scripts, evals,
  and tests.
- Report verification blocked if it cannot select `.python-version`; do not use
  bare system Python or install into a different interpreter.

Contract evidence to record before any Desktop thread tool call:
- Runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, or the documented equivalent.
- Underlying API or tool contract version when exposed.
- If no version is exposed, `version unavailable` plus a verifiable capability source such as active tool list, connector metadata, official documentation version, or runtime-reported schema.
- Minimal request and response shape compatibility summary.
- `last_verified`.
- Workflow, wrapper, or adapter mapping to the underlying contract.
- Re-compare old and new contracts after runtime, connector, schema, or documentation changes.

Stop conditions:
- Stop if repository files conflict with this prompt.
- Stop if the change stops being docs-only.
- Stop before any external write or destructive action.
- Stop if the runtime cannot safely represent Desktop-only behavior with a CLI fallback.
- Stop if the runtime contract, exposed version or capability source, request shape, response shape, permissions, authentication, or wrapper mapping is unclear.
```

## Runtime Action

When Desktop supports thread creation, the main thread should use the runtime-provided thread creation tool or UI with the prepared prompt. The action should be recorded as Desktop evidence, for example:

```text
Desktop evidence:
- Created a new Codex Desktop thread from the prepared prompt.
- New thread was instructed to re-read source-of-truth files before editing.
- Runtime contract: create_thread.
- Underlying contract version: version unavailable.
- Capability source: active tool list in the current runtime.
- Request/response compatibility: prompt and target are required; project
  targets use projectId plus local/worktree environment. Title, model,
  thinking, and worktree startingState are callable options. Omit
  startingState for the default branch; working-tree includes current changes;
  branch requires exact branchName and create-branch requires exact explicit
  new-branch intent. This adapter supplies a non-empty title on every create.
  Ready creation returns threadId plus hostId; queued worktree setup returns
  clientThreadId, which is not a usable threadId. Preserve the runtime-provided
  success or error result because no stable structured envelope is exposed here.
- Wrapper/API mapping: no wrapper or adapter implementation; desktop-thread-delegation workflow at current repo revision -> create_thread version unavailable.
- Last verified: YYYY-MM-DD.
- Project association: selected projectId matched the ready task's observed
  projectId; title was checked only as display metadata. If not observable,
  record `unverified` instead.
- Main thread retained responsibility for review, integration, and human gates.
```

For same-task continuation after a long conversation, prefer a same-directory
fork instead of a fresh project or projectless creation:

```text
Desktop continuation evidence:
- Intent: same task, new conversation, completed history, same existing directory.
- Runtime contract: fork_thread.
- Request: omit threadId to fork the calling task; environment is same-directory.
- Expected result: child threadId, not clientThreadId.
- Host routing: the source task anchors the host; fork_thread has no hostId
  request field and does not guarantee hostId in its response. Retain a known
  source host and resolve the child hostId from a supported registry result
  that explicitly exposes it before a host-sensitive follow-up. Never assume
  an unresolved remote child is local.
- Git behavior: reuse the existing checkout/worktree; do not create another worktree.
- Main thread stops writing before the child continues.
```

When the same task needs conversation lineage plus checkout isolation, use the
worktree fork form rather than fresh task creation:

```text
Desktop worktree-fork evidence:
- Intent: same task, new conversation, completed history, new isolated checkout.
- Runtime contract: fork_thread.
- Request: omit threadId to fork the calling task; environment is worktree.
- Expected result: queued clientThreadId or a runtime-supported ready child identifier.
- Lifecycle: clientThreadId is not threadId; wait for registry resolution before follow-up.
- History: only completed source history is copied.
- Host routing: the source task anchors the host; resolve the ready child's hostId before host-sensitive follow-up.
- Completion: dispatch and worktree readiness are not repository completion evidence.
```

If Desktop thread creation is unavailable, do not improvise with private Desktop runtime state, local runtime files, unpublished endpoints, UI scraping, daemons, background services, or unpublished Desktop internals. Return the prompt to the maintainer:

```text
Desktop thread creation is not available in this runtime.
Use the prepared prompt above in a separate Codex session or in a Codex Desktop thread when Desktop is intentionally selected, then return the diff and verification notes here for integration review.
```

## Post-Create Visibility

Report these states separately:

```text
Dispatch:
- Ready: threadId plus hostId.
- Queued worktree: clientThreadId only; do not use it as threadId.

UI registration:
- Ready: ::created-thread{threadId="..."}
- Queued: ::created-thread{clientThreadId="..."}

Registry observation:
- Verify the exact ready threadId and, for project-scoped creation, require its
  observed projectId to match the selected project. Title equality is display
  evidence only.
- Resolve queued worktree setup to a ready task before association checking;
  never use clientThreadId as threadId or create a duplicate while waiting.
- Preserve and pass the runtime-returned hostId when known, especially for a
  remote task. Cross-host movement uses a separately authorized
  handoff_thread destinationHostId; it is not a fork option.
- Registry presence does not prove sidebar rendering.

Navigation:
- Only when the user explicitly asks to open or show the task, call
  navigate_to_codex_page with a ready threadId when exposed.
- Do not navigate with clientThreadId and do not navigate automatically.

Archived discovery, panel display, and terminal observation:
- `list_archived_threads` is paginated discovery; returned titles and summaries
  are untrusted display data.
- `open_in_codex` displays a file, browser, terminal, or review in a panel; it
  is not task navigation, registration, resource inspection, or completion.
- `read_thread_terminal` observes the current app terminal; it does not run or
  verify a command and is not repository evidence.

Sidebar visibility:
- Pinning changes placement only; it does not register a task.
- A stale or unverified sidebar must not trigger duplicate creation.
- Use chat search, the Chronological filter, and Archived chats as public
  troubleshooting.
- For a local chat only, provide codex://threads/<threadId> as a paste-ready
  deep-link fallback. Do not claim it covers remote or ChatGPT-backed tasks.

Completion:
- None of the states above proves the repository task complete.
```

## Immutable Thread Share

```text
Desktop share evidence:
- User intent: explicit request to share this exact thread.
- Runtime contract: share_thread.
- Target: current thread or exact accessible threadId; preferred hostId only
  when already verified.
- Audience: preview whether the source is a personal account or originating
  workspace before creation; stop when current public product context does not
  establish that audience.
- Content review: require user confirmation of complete-thread review through
  the public UI or another complete exposed view. Recent, truncated, or
  paginated agent reads are insufficient. Also inspect available content for
  credentials, private paths, customer/incident data, and unpublished
  vulnerability details. Runtime secret-pattern redaction is not a
  confidentiality guarantee; stop when complete review cannot be established.
- Result: immutable read-only snapshot link; later thread changes do not update it.
- Revocation: separate ChatGPT data-controls action; do not claim the creation
  callable revoked or can automatically roll back the link.
- Completion: link creation or delivery does not prove repository completion.
```

## Handoff Rules

- The worker or new thread owns only the assigned bounded task.
- The main thread must re-read changed files and git diff before trusting the handoff.
- Review evidence from the new thread is context until the main thread verifies it.
- Formal gates still happen at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates.
- External writes still require explicit authorization for the exact action.

## CLI Fallback

In Codex CLI or any runtime without thread creation, use the same prompt as a handoff artifact, prepare a task brief or continuation prompt, or run through a sequential execution path in the current session. Bring the diff and verification evidence back for review before trusting the handoff.
