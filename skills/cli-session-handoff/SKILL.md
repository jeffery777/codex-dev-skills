---
name: cli-session-handoff
description: Thin Codex CLI session control adapter for one bounded non-interactive start, resume, fork, or fresh continuation, or one manual interactive fork, dashboard, or queued message, already selected by shared orchestration.
---

# cli-session-handoff

Runtime compatibility: cli

## Purpose

Use this skill only after `loop-engineering`, `project-orchestrator`,
`project-delivery`, or `task-continuation` has selected a bounded handoff and
the user explicitly wants a separate, resumed, forked, inspected, or queued
Codex CLI session action.

This is a thin CLI control-plane adapter. It does not select the task, redefine
completion, replace shared subagents, or control Desktop tasks. The originating
session remains responsible for integration, verification, review, and
completion.

## Runtime Boundary

The automated adapter uses only the documented stable non-interactive CLI:

- `codex exec --json` for a new saved CLI session;
- `codex exec resume <SESSION_ID> --json` for a known saved CLI session;
- `codex exec fork <SESSION_ID> --json` for a new saved session that copies the
  completed history of an exact known source session.
- `codex exec --json` for a new saved `fresh-continuation` session whose prompt
  is bound to a validated durable checkpoint and deliberately copies no prior
  conversation history.

The documented interactive CLI separately exposes
`codex fork <SESSION_ID>` for a new chat from a saved interactive session.
This skill may prepare that exact paste-ready command and working-directory
choice as a manual handoff, but the repo-owned executor does not automate the
TUI or implement interactive fork.

Codex CLI 0.149.0 also exposes `codex agents` as an interactive session
dashboard and `codex queue --thread <THREAD> --message <TEXT>` as a public
message-delivery command. This skill may prepare those manual operations only
after the exact dashboard mutation or queued message is authorized. Use a
canonical session UUID for queue guidance even though the CLI accepts an exact
session name; a display name is not stable identity. The private-clone executor
does not automate either command because they do not share the isolated
`codex exec --json` terminal-turn contract.

`codex doctor --json` is a read-only, redacted diagnostic fallback. It does not
prove that a specific session operation is supported, replace active public
CLI help/schema inspection, or authorize app-server, remote-control, private
runtime-state, or historical Desktop wrapper access.

The automated `codex exec` and manual interactive-fork paths do not use
interactive UI automation, Desktop `create_thread`, private session files,
direct app-server or remote-control APIs, a caller-started daemon, or a
sidecar. The public `codex agents` command is the explicit exception: it owns
its documented connection to the runtime-managed shared local app-server
daemon without authorizing this adapter to start or control that daemon
directly. A CLI session identifier is not a Desktop `threadId` or
`clientThreadId`.

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
   - `fork` for a new non-interactive session from an exact known source UUID,
     executed through the private-clone path and expected to return a different
     public session UUID;
   - `fresh-continuation` for phase-one clean-worktree, non-interactive,
     same-repository/same-objective rollover after the shared assessment selects
     `prepare-fresh-rollover`. It starts a new session rather than resuming or
     forking history;
   - `interactive-fork` when the same interactive task needs a new chat that
     keeps saved history and intentionally reuses the session directory or
     another exact existing checkout/worktree.
   - `agents-dashboard` when the user explicitly wants to browse or control
     sessions interactively; searching or viewing is observation, while start,
     open, rename, and stop actions retain the authority required for the exact
     selected mutation.
   - `manual-queue` when the user explicitly wants to deliver one bounded
     nonsensitive message to an exact canonical session UUID. Queue acceptance
     is dispatch/wakeup evidence only, not processing or completion evidence.
   - `doctor` only for requested runtime diagnosis through the redacted public
     output; never as a substitute for operation capability checks.
4. Prepare a self-contained prompt that requires the child to re-read
   source-of-truth files, stay within scope, avoid further session dispatch,
   run verification with the repository-selected environment, and return
   changed files, evidence, questions, and residual risk. When an executable
   `scripts/project-python` exists, require it for Python dependency checks,
   scripts, evals, and tests; never substitute bare system Python.
   For fresh continuation, append the canonical checkpoint as data plus its
   SHA-256 and stable rollover ID. Require one destination writer, source
   stop-writing, material progress evidence, exact replay no-op, and no recursive handoff.
   The executor independently matches the checkpoint canonical host/path to `origin`,
   digest-binds clean worktree state, and atomically updates one locked durable
   ledger indexed by both rollover ID and checkpoint digest below the Git control directory
   before the runtime call; caller-supplied
   `seen_rollovers` is not the runtime idempotency barrier.
5. For `start`, `resume`, `fork`, or `fresh-continuation`, select the least sandbox required: `read-only` for inspection and
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
8. For `start`, `resume`, `fork`, or `fresh-continuation`, run the repo-owned executor with a JSON request on
   stdin:

   ```bash
   ./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py --request - < request.json
   ```

   For `interactive-fork`, return a paste-ready
   `codex fork <SESSION_ID>` command and the chosen directory policy for the
   user to run interactively. For `agents-dashboard`, return `codex agents` and
   identify which later dashboard actions require a separate mutation gate. For
   `manual-queue`, preview the exact UUID and complete message, recheck that the
   message contains no credentials, private paths, customer/incident details,
   shell-control text, or further-dispatch request, then return an exact argv
   token list for `codex queue`, with the complete message as one token. Do not
   interpolate arbitrary message text into a paste-ready shell command. Provide
   a shell command only when the user's exact shell is known and every message
   byte is encoded with that shell's verified literal-quoting rules. Do not send
9. Treat non-interactive `completed` as process/session handoff evidence only.
   A prepared interactive-fork command is a handoff artifact, not evidence that
   a fork occurred. A prepared dashboard or queue command is likewise not
   execution evidence. After the user runs one, treat only the public CLI
   result as observation, mutation, or queue-dispatch evidence as applicable.
   Re-read the target worktree and verify the diff independently before
   accepting any destination result.
10. If capability or validation fails, keep the prepared prompt as a manual
    continuation artifact or continue in the current session.
    Interactive or dirty-worktree fresh continuation always uses this fallback;
    it is never reported as an automated success.

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
- a `resume` or `fork` target must be an exact UUID, never `--last` or a
  display name; `resume` must emit the same UUID, while `fork` must emit the
  newly created session UUID;
- normal tests must use fake executables and must not create a live session.
- `fresh-continuation` additionally requires a strict
  `loop-context-continuity/v1` assessment selecting fresh rollover, clean CLI
  non-interactive capability, a complete checkpoint, confirmed source stop,
  and an unseen rollover ID; an exact request replay is stopped by durable
  local Git-control evidence and performs no second session call.

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
- Do not confuse automated `codex exec fork` with interactive `codex fork`;
  only the latter remains a manual interactive handoff.

## Dashboard And Queue Policy

- `codex agents` is an interactive CLI control plane over the runtime's shared
  local app-server daemon. Using the public command does not authorize starting
  an app-server or remote-control daemon directly.
- Dashboard discovery or viewing is observation. Starting, opening, renaming,
  or stopping a task is a distinct runtime-state action and requires exact
  authority at selection time.
- Prepare `codex queue` only with a canonical UUID. Do not use a session name,
  `--last`, private state, or dashboard display text as identity authority.
- Preview and validate the full queued message. It must be bounded,
  nonsensitive, non-destructive, free of shell-control text, and within the
  already selected task scope.
- Represent the queue invocation as an argv token list. Never concatenate or
  interpolate the message into a shell command. If an executable shell command
  is explicitly requested, require a known shell and verified literal quoting
  for the complete message; otherwise keep the argv-only boundary.
- Queue acceptance proves only that delivery was requested. It does not prove
  the destination woke, processed the message, changed files, passed checks, or
  completed repository work.
- Do not pass model, sandbox, approval, remote endpoint, profile, extra
  directory, or bypass flags unless a separately reviewed future adapter
  defines and verifies those semantics.

## Output

- Operation and result classification, plus rollover ID and checkpoint digest
  for fresh continuation
- For an interactive fork or dashboard, a paste-ready command; for queue, the
  exact UUID, reviewed message, argv token list, quoting classification, and
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
- workspace, expected head, executable, sandbox, or resume/fork identifier is
  ambiguous;
- the worktree is dirty for an automated `start`, `resume`, `fork`, or
  `fresh-continuation`, or a dirty
  interactive-fork target lacks exclusive same-task ownership;
- the task could overlap another active writer;
- the prompt asks for destructive, publication, credential, private-state,
  permission-widening, or further session-dispatch behavior;
- a queued message contains sensitive or shell-control content, lacks an exact
  UUID, expands the selected task, requires unreviewed
  model/sandbox/approval/remote flags, or cannot be represented without unsafe
  shell interpolation;
- only experimental or private runtime interfaces could satisfy the request;
- a live smoke, commit, push, PR, merge, release, or deployment lacks its own
  required human gate.
