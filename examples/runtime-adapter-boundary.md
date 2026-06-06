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
9. State in-scope and out-of-scope files or categories.
10. Ask for explicit human authorization for the exact thread action.
11. Keep commit, push, PR creation, PR comments, review submissions, merge, deploy, destructive actions, and other platform-side mutation behind separate explicit authorization.

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
- Wrapper/API mapping: wrapper 0.2.0 -> create_thread version unavailable.
- Request shape minimum: prompt required; title, repository, and branch used when exposed.
- Response shape minimum: created thread identifier or pending worktree identifier, action status, and error message shape.
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

## Minimal Caller-Supplied Capability Metadata

A non-state-changing helper may normalize metadata the caller already supplied, but it must not gather that metadata by scanning Desktop files or calling thread tools. This example is evidence only; it does not open, fork, message, continue, or read a Desktop thread.

```json
{
  "requested_action": "normalize-runtime-capability-metadata",
  "metadata_source": {
    "source": "runtime-reported schema",
    "contract_version": "version unavailable",
    "last_verified": "YYYY-MM-DD",
    "available": true
  },
  "capabilities": [
    {
      "action": "read-thread",
      "tool_or_api": "read_thread",
      "classification": "read-only",
      "request": {
        "required": ["thread_id"],
        "optional": ["include_metadata"]
      },
      "response": {
        "required": ["status", "thread_id"],
        "errors": ["message"]
      },
      "source": "runtime-reported schema",
      "contract_version": "version unavailable",
      "last_verified": "YYYY-MM-DD"
    }
  ]
}
```

If the caller cannot supply the action classification, required request fields, minimum response fields, source, contract version or `version unavailable`, and `last_verified`, the helper should return `stopped` or `unavailable` rather than filling gaps from private runtime state.

The planner may consume that normalized discovery output as caller-supplied `capability_evidence`. This still does not open, fork, message, continue, or read a Desktop thread:

```json
{
  "action": "plan-thread-action",
  "target_action": "read-thread",
  "capability_evidence": {
    "status": "available",
    "capabilities": [
      {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["thread_id"],
        "optional_request_fields": ["include_metadata"],
        "minimum_response_fields": ["status", "thread_id"],
        "error_response_fields": ["message"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": "YYYY-MM-DD",
        "discovery_helper_version": "0.1.0"
      }
    ]
  },
  "target": {
    "repo": "owner/name",
    "remote": "origin URL",
    "branch": "branch-name",
    "thread_id": "thread identifier supplied by caller"
  },
  "prompt": {
    "summary": "Read documented thread metadata.",
    "body": "Prepare read-only evidence only; do not call Desktop private runtime state."
  },
  "boundaries": {
    "in_scope": ["docs/runtime-adapter-v2.md"],
    "out_of_scope": [".work/", "Desktop private runtime state"],
    "external_writes_blocked": true
  },
  "authorization": {
    "thread_action_authorized": false,
    "external_write_authorized": false
  }
}
```

If the target action is missing from `capability_evidence`, the planner returns a CLI-compatible fallback. If the classification is mismatched, the request or response shape is unclear, or the evidence points at forbidden Desktop runtime sources, the planner stops.

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
