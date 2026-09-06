# Runtime Adapter Boundary Example

Use this example when a Codex Desktop workflow wants to delegate thread actions through a supported runtime tool while preserving the boundary from [Desktop Runtime Adapter V2 Boundary](../docs/runtime-adapter-v2.md).

This is a documentation example only. It belongs to accepted public repository policy, runtime compatibility guidance, and maintained examples. It does not implement a wrapper, runtime adapter, daemon, MCP server, app-server client, Desktop runtime integration, or roadmap commitment.

## Maintainer Request

```text
Use desktop-thread-delegation for this bounded task.
If this runtime exposes documented thread tools, verify repo identity, branch state, expected head, and my explicit authorization before creating, forking, or messaging a thread.
If thread tools are unavailable, give me a paste-ready prompt, task brief, continuation prompt, or continue through a sequential execution path when safe.
Stop if the only path depends on private Desktop runtime state, unpublished endpoints, UI scraping, daemons, background services, unclear API contracts, unclear auth or permissions, destructive actions, or external writes I did not explicitly authorize.
```

## Scenario 1: Supported Thread Tools

When the active runtime exposes tools such as `create_thread`, `fork_thread`, or `send_message_to_thread`, treat them as state-changing Desktop runtime actions. Verify and record the boundary before calling the tool.

Preflight checklist:

1. Confirm repository identity with ordinary git inspection:
   - working directory
   - `git remote -v`
   - current branch and upstream
   - `git status --short --branch`
2. Confirm the expected branch or expected head SHA when the thread action depends on local git state.
3. Record the runtime thread tool or API contract name, such as `create_thread`, `fork_thread`, `send_message_to_thread`, or the documented equivalent.
4. Record the underlying API or tool contract version when exposed.
5. If no version is exposed, record `version unavailable` and the verifiable capability source, such as active tool list, connector metadata, official documentation version, or runtime-reported schema.
6. Record the minimal request shape and response shape the caller relies on.
7. Record `last_verified` date and the wrapper version to underlying API or tool contract mapping.
8. Summarize the prepared prompt, intended thread action, and recipient thread if one exists.
9. Preserve placement intent: use same-directory fork for same-task
   continuation, exact-project worktree creation by default for a fresh task in
   a Git project, exact-project local creation for a non-Git project or an
   explicitly requested saved checkout, and projectless creation only for
   non-project work. Do not treat a
   no-new-worktree constraint as projectless intent.
10. State in-scope and out-of-scope files or categories.
11. Verify explicit authorization for the exact action; reuse it when already
    established for unchanged target, scope, and effect.
12. Keep commit, push, PR creation, PR comments, review submissions, merge, deploy, destructive actions, and other platform-side mutation behind separate explicit authorization.

Example evidence before calling a supported tool:

```text
Thread action preflight:
- Repo: jeffery777/codex-dev-skills from origin remote.
- Branch: codex/example-task, upstream origin/codex/example-task.
- Expected head: 1234567890abcdef1234567890abcdef12345678.
- Dirty state: docs-only changes in examples/example.md; untracked .work/ is out of scope.
- Action: create a new Desktop thread from the prepared prompt below.
- Runtime contract: create_thread.
- Underlying contract version: version unavailable.
- Capability source: active tool list in the current runtime.
- Workflow/API mapping: desktop-thread-delegation -> active create_thread callable.
- Request shape minimum: prompt and target required; project targets use
  projectId plus local/worktree environment; title, model, thinking, and an
  explicitly requested worktree startingState are callable options. The
  adapter supplies title on every create.
- Adapter title: concise non-empty safe title derived from the authorized
  objective, for example `Improve workflow efficiency`. Exclude credentials,
  private paths, customer/incident details, and untrusted registry text. Use a
  generic title only when a safe specific one is unavailable. It is display
  metadata, not project identity, and needs no separate approval.
- Placement intent: fresh task in a Git project, so use project worktree by
  default. Use project local only for an explicitly requested saved checkout;
  for same-task continuation, use fork_thread same-directory instead.
- Worktree environment: use the repository's tracked setup and interpreter
  resolver; in this repository run `./scripts/project-python`, never a
  mismatched bare system Python.
- Response shape minimum: threadId plus hostId for ready creation, or
  clientThreadId for queued worktree setup. Preserve runtime-provided errors
  because the callable does not expose a stable structured error union.
- Association verification: require the ready task's observed projectId to
  match the selected projectId; title equality alone is insufficient. Treat a
  delayed or unavailable association as unverified and do not create a
  duplicate.
- Last verified: YYYY-MM-DD.
- Human authorization: maintainer explicitly authorized creating this thread only.
- External writes still blocked: commit, push, PR creation, platform comments, review submissions, merge, deploy, destructive actions.
```

Example prepared prompt:

```text
Continue this bounded Codex Desktop task in a new thread.

Read first:
- AGENTS.md
- README.md
- docs/runtime-adapter-v2.md
- examples/runtime-adapter-boundary.md

Task:
- Draft one docs-only example for the runtime adapter boundary.

In scope:
- examples/ documentation.
- README or relevant docs links needed for discoverability.

Out of scope:
- Wrapper or runtime adapter implementation.
- Daemons, MCP servers, app-server clients, Desktop runtime internals, UI scraping, unpublished endpoints, background services, or private Desktop runtime state.
- Commits, pushes, PR creation, platform comments, review submissions, merges, deploys, destructive actions, or .work/ artifacts.

Verification:
- ./scripts/validate-repo.sh
- git diff --check

Contract evidence to record before any thread action:
- Runtime tool/API contract name.
- Underlying contract version, or "version unavailable" plus capability source.
- Minimal request and response shape.
- Last verified date.
- Workflow, wrapper, or adapter mapping to the underlying contract.
- Re-compare old and new contracts after any runtime, connector, schema, or documentation change.

Stop conditions:
- Stop if source-of-truth files conflict.
- Stop if the change stops being docs-only.
- Stop before external writes or destructive actions.
- Stop if the runtime tool contract, auth, permissions, repo identity, branch, worktree, or expected head is unclear.
```

After the tool returns, record only the documented result shape exposed by the runtime, such as created thread identifier, target thread, action result, prompt summary, contract version evidence, request/response compatibility summary, and unresolved risk. Do not inspect Desktop databases, logs, sessions, auth files, caches, app state, or other private Desktop runtime files to fill missing evidence.

## Scenario 2: No Thread Tool Available

When no documented thread capability is present in the active tool list, say that no Desktop thread was opened and choose the lowest-risk fallback.

Paste-ready prompt fallback:

```text
Desktop thread creation is not available in this runtime.
Use the prompt below in a separate Codex session or in a Codex Desktop thread when Desktop is intentionally selected, then return the diff and verification notes here for integration review.

[prepared prompt from the preflight]
```

Sequential CLI-compatible fallback:

```text
No documented thread tool is available, so I will continue sequentially in this session.
I will use repository files and ordinary shell/git inspection only.
I will not claim that a Desktop thread was opened.
I will stop before commits, pushes, PR creation, platform comments, review submissions, merges, deploys, destructive actions, or runtime-specific mutation unless explicitly authorized.
```

The fallback may prepare a prompt, task brief, continuation prompt, or sequential execution path from durable repository files when that helps another session continue safely. It must not emulate Desktop thread control with private Desktop runtime state, unpublished endpoints, UI scraping, daemons, or background services.

## Current Callable Evidence

Record the current callable name, source, required fields, relied-on response,
and exact authorization alongside the action. Reuse that record while the
schema and scope are unchanged; compare only affected fields after drift.
For example, a current `create_thread` request has required `prompt` and
`target`, and this adapter additionally supplies a safe `title`. A ready result
may expose `threadId` plus `hostId`; queued setup exposes `clientThreadId`.
Validate against the active schema rather than treating this prose as a stable
machine contract.

There is no repository helper to normalize, compare, plan, or preflight Desktop
thread actions. Call native tools directly after call-site validation. Retired
helper-shaped JSON is retained only in the
[non-executable historical example](../docs/history/runtime-adapter-v1-example.md).
Do not import, execute, or reconstruct it as a runtime integration.

## Scenario 3: Stop Instead Of Adapting

Stop before calling a thread tool, fallback, wrapper, API, or script when any of these conditions apply:

- API contract, required parameters, expected result shape, authentication, or permissions are unclear.
- Underlying API or tool contract version is unavailable and there is no verifiable capability source to record.
- Runtime, connector, schema, or documentation changes have not been compared against the wrapper compatibility record.
- Target repo, remote, branch, worktree, expected head, or recipient thread is unclear.
- The only available source is private Desktop runtime state such as local databases, logs, sessions, auth files, caches, app state, local runtime directories, or private runtime files.
- The only path depends on unpublished app-server endpoints, reverse-engineered Desktop internals, UI scraping, a remote-control daemon, wrapper daemon, sidecar, or background service.
- The action would perform a destructive operation or external write without explicit authorization for the exact target.
- Source-of-truth files conflict and the conflict cannot be resolved cheaply.

Stop response shape:

```text
Stopped before Desktop thread action.

Reason:
- The runtime does not expose a documented thread tool, and the only suggested path depends on private Desktop runtime state.

Lowest-risk next option:
- Use the paste-ready prompt below in a separate Codex session or an intentionally selected Codex Desktop thread, or authorize sequential execution in this session.

Paste-ready prompt:
- [include prompt that relies only on repository files and ordinary git inspection]
```

The main thread remains responsible for re-reading the returned diff, running verification, reviewing the evidence, and enforcing commit, PR, merge, and external-write gates.
