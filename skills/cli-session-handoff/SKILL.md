---
name: cli-session-handoff
description: Thin Codex CLI session control adapter for one bounded start or resume handoff already selected by shared orchestration.
---

# cli-session-handoff

Runtime compatibility: cli

## Purpose

Use this skill only after `loop-engineering`, `project-orchestrator`,
`project-delivery`, or `task-continuation` has selected a bounded handoff and
the user explicitly wants a separate or resumed Codex CLI session.

This is a thin CLI control-plane adapter. It does not select the task, redefine
completion, replace shared subagents, or control Desktop tasks. The originating
session remains responsible for integration, verification, review, and
completion.

## Runtime Boundary

The initial adapter uses only the documented stable non-interactive CLI:

- `codex exec --json` for a new saved CLI session;
- `codex exec resume <SESSION_ID> --json` for a known saved CLI session.

It does not use interactive UI automation, Desktop `create_thread`, private
session files, app-server, remote-control, a daemon, or a sidecar. A CLI
session identifier is not a Desktop `threadId` or `clientThreadId`.

## Workflow

1. Re-read the already selected task brief, source-of-truth files, exact scope,
   expected Git head, verification, stop conditions, and current Git state.
2. Return to shared orchestration if the task is ambiguous, no longer ready,
   overlaps active ownership, or needs a different worktree.
3. Choose one operation:
   - `start` for a new, clean, bounded CLI session;
   - `resume` only for an exact known UUID returned by a prior public CLI
     event.
4. Prepare a self-contained prompt that requires the child to re-read
   source-of-truth files, stay within scope, avoid further session dispatch,
   run verification, and return changed files, evidence, questions, and
   residual risk.
5. Select the least sandbox required: `read-only` for inspection and
   `workspace-write` only when the user authorized implementation in the exact
   target worktree. The child runs in a private clone at the expected HEAD;
   read-only changes are discarded, while a bounded binary patch is applied to
   the original only after its clean identity is rechecked.
6. Confirm explicit authorization for one CLI session mutation. The adapter's
   marker records the decision but cannot create authority by itself.
7. Run the repo-owned executor with a JSON request on stdin:

   ```bash
   python3 skills/cli-session-handoff/scripts/cli_session_handoff.py --request - < request.json
   ```

8. Treat `completed` as process/session handoff evidence only. Re-read the
   target worktree and verify the diff independently before accepting any child
   result.
9. If capability or validation fails, keep the prepared prompt as a manual
   continuation artifact or continue in the current session.

## Request Policy

Use the installed executor's non-live `--example` output as the canonical
request shape. In addition:

- `codex_executable`, `workspace`, and `expected_head` must identify the exact
  call site;
- `prompt_boundary_version` must select the supported canonical boundary
  appendix, which the executor appends after the task prompt;
- the worktree must be clean before a new child process starts;
- sparse-checkout worktrees and worktrees containing Git submodules are not
  qualified for the private-clone adapter and return a capability fallback;
- only `read-only` and `workspace-write` are supported;
- private-clone target isolation and best-effort process-tree cleanup are
  qualified on macOS and Linux; descendant cleanup binds observed PIDs to OS
  process-start tokens, and target-worktree integrity does not depend on
  polling observing every reparented descendant;
- the executable version probe has its own disposable working directory,
  process-tree cleanup, time limit, and streaming output bounds;
- arbitrary flags, model overrides, extra writable roots, environment
  overrides, approval bypasses, and `danger-full-access` are unsupported;
- a `resume` target must be an exact UUID, never `--last` or a display name;
- normal tests must use fake executables and must not create a live session.

## Output

- Operation and result classification
- Observed CLI version and executable digest, without a machine-local path
- Canonical target Git head and a redacted workspace label
- Public CLI session identifier when emitted
- Terminal event and process exit status
- Fixed omission marker in place of the untrusted final summary
- Explicit non-authoritative and parent-integration boundaries
- Failure class and safe fallback when the handoff does not complete

## Stop Conditions

Stop before execution when:

- exact user authority for the one session mutation is absent;
- workspace, expected head, executable, sandbox, or resume identifier is
  ambiguous;
- the worktree is dirty;
- the task could overlap another active writer;
- the prompt asks for destructive, publication, credential, private-state,
  permission-widening, or further session-dispatch behavior;
- only experimental or private runtime interfaces could satisfy the request;
- a live smoke, commit, push, PR, merge, release, or deployment lacks its own
  required human gate.
