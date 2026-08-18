---
name: cli-session-handoff
description: Thin Codex CLI session control adapter for one bounded start, resume, or interactive fork handoff already selected by shared orchestration.
---

# cli-session-handoff

Runtime compatibility: cli

## Purpose

Use this skill only after `loop-engineering`, `project-orchestrator`,
`project-delivery`, or `task-continuation` has selected a bounded handoff and
the user explicitly wants a separate, resumed, or interactively forked Codex
CLI session.

This is a thin CLI control-plane adapter. It does not select the task, redefine
completion, replace shared subagents, or control Desktop tasks. The originating
session remains responsible for integration, verification, review, and
completion.

## Runtime Boundary

The automated adapter uses only the documented stable non-interactive CLI:

- `codex exec --json` for a new saved CLI session;
- `codex exec resume <SESSION_ID> --json` for a known saved CLI session.

The documented interactive CLI separately exposes
`codex fork <SESSION_ID>` for a new chat from a saved interactive session.
This skill may prepare that exact paste-ready command and working-directory
choice as a manual handoff, but the repo-owned executor does not automate the
TUI or implement interactive fork.

Neither path uses interactive UI automation, Desktop `create_thread`, private
session files, app-server, remote-control, a daemon, or a sidecar. A CLI
session identifier is not a Desktop `threadId` or `clientThreadId`.

## Workflow

1. Re-read the already selected task brief, source-of-truth files, exact scope,
   expected Git head, verification, stop conditions, and current Git state.
2. Return to shared orchestration if the task is ambiguous, no longer ready,
   overlaps active ownership, or needs a different worktree.
3. Choose one operation:
   - `start` for a new, clean, bounded non-interactive CLI session in the
     executor's private clone;
   - `resume` only for an exact known UUID returned by a prior public CLI
     event and executed through the same non-interactive private-clone path;
   - `interactive-fork` when the same interactive task needs a new chat that
     keeps saved history and intentionally reuses the session directory or
     another exact existing checkout/worktree.
4. Prepare a self-contained prompt that requires the child to re-read
   source-of-truth files, stay within scope, avoid further session dispatch,
   run verification with the repository-selected environment, and return
   changed files, evidence, questions, and residual risk. When an executable
   `scripts/project-python` exists, require it for Python dependency checks,
   scripts, evals, and tests; never substitute bare system Python.
5. For `start` or `resume`, select the least sandbox required: `read-only` for inspection and
   `workspace-write` only when the user authorized implementation in the exact
   target worktree. The child runs in a private clone at the expected HEAD;
   read-only changes are discarded, while a bounded binary patch is applied to
   the original only after its clean identity is rechecked.
6. For `interactive-fork`, require an exact session UUID and choose the public
   working-directory behavior deliberately. `tui.resume_cwd = "session"`
   selects the saved session directory, `"current"` selects the invocation
   directory, and an unset value prompts when they differ. A same-task fork may
   reuse a dirty existing worktree only when ownership is exclusive, the
   source session will not continue writing concurrently, and the user
   intentionally chose that exact directory. Do not use `--last`, a display
   name, private session state, or a newly created worktree as a substitute.
7. Confirm explicit authorization for one CLI session mutation. The adapter's
   marker records the decision but cannot create authority by itself.
8. For `start` or `resume`, run the repo-owned executor with a JSON request on
   stdin:

   ```bash
   ./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py --request - < request.json
   ```

   For `interactive-fork`, return a paste-ready
   `codex fork <SESSION_ID>` command and the chosen directory policy for the
   user to run interactively; do not send it through the executor.
9. Treat non-interactive `completed` as process/session handoff evidence only.
   A prepared interactive-fork command is a handoff artifact, not evidence that
   a fork occurred. After the user runs it, treat only the public CLI result as
   session dispatch evidence. Re-read the target worktree and verify the diff
   independently before accepting any child result.
10. If capability or validation fails, keep the prepared prompt as a manual
   continuation artifact or continue in the current session.

## Non-Interactive Request Policy

Use the installed executor's non-live `--example` output as the canonical
request shape. In addition:

- `codex_executable`, `workspace`, and `expected_head` must identify the exact
  call site;
- `prompt_boundary_version` must select the supported canonical boundary
  appendix, which the executor appends after the task prompt;
- the worktree must be clean before a new child process starts;
- the private clone does not inherit the source checkout's activated virtual
  environment; use the repository's tracked environment resolver when present,
  and return verification blocked if its pinned interpreter or dependencies are
  unavailable instead of installing through a different interpreter;
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

## Interactive Fork Policy

- Use only the documented `codex fork <SESSION_ID>` surface with an exact UUID.
- Record whether the selected working directory is the saved `session`
  directory or the invocation `current` directory; do not guess when they
  differ.
- Use public `-C <DIR>` and `tui.resume_cwd` behavior when needed; do not read
  private session files to recover a path.
- Treat a dirty existing checkout/worktree as eligible only for exclusive
  same-task continuation with no concurrent writer. It is not eligible for the
  automated private-clone executor.
- Do not create or select a new Git worktree when the intent is to reuse the
  existing one.
- Do not claim the repo-owned executor supports `codex fork`; it remains a
  manual interactive handoff.

## Output

- Operation and result classification
- For an interactive fork, exact UUID command, selected directory policy, and
  explicit manual-execution boundary
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
- the worktree is dirty for an automated `start` or `resume`, or a dirty
  interactive-fork target lacks exclusive same-task ownership;
- the task could overlap another active writer;
- the prompt asks for destructive, publication, credential, private-state,
  permission-widening, or further session-dispatch behavior;
- only experimental or private runtime interfaces could satisfy the request;
- a live smoke, commit, push, PR, merge, release, or deployment lacks its own
  required human gate.
