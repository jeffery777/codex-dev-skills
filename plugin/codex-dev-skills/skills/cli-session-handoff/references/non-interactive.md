# Non-Interactive Start, Resume, And Fork

Read this reference for `start`, `resume`, `fork`, or `fresh-continuation`.
The adapter uses documented stable non-interactive start/resume forms:
`codex exec --json` and `codex exec resume <SESSION_ID> --json`.
`codex exec fork <SESSION_ID> --json` is an observed and locally qualified public-help
surface, not a documented stability promise. Check the active executable's
public help before relying on the selected operation.

## Prepare And Execute

1. Re-read the selected task brief, exact scope, expected Git head, source files,
   current Git state, verification, and stop conditions. Return to shared
   orchestration for ambiguous readiness, overlapping writers, or a different
   worktree requirement.
2. Prepare a self-contained prompt requiring source-of-truth reads, bounded
   scope, no further session dispatch, repository-selected verification, and
   changed files, evidence, questions, and residual risk. Require an executable
   tracked `scripts/project-python` when present; never substitute bare system
   Python for the repository's pinned environment.
3. Select `read-only` for inspection or `workspace-write` only for already
   authorized implementation. The child runs in a private clone at expected
   HEAD. Read-only changes are discarded; an authorized bounded binary patch
   is applied to the source only after its clean identity is rechecked.
4. Use the installed executor's non-live `--example` output to prepare the
   request. Verify the exact operation's existing user authorization at call
   time; the request marker records authority and cannot create it.
5. Run the executor with the reviewed JSON request on stdin, then independently
   inspect the target worktree and diff. `completed` is process/session handoff
   evidence only, not completion of the task.

## Portable Invocation

Resolve `HANDOFF_SKILL_DIR` to the absolute directory containing this installed
skill's `SKILL.md`, and `HANDOFF_PYTHON` to the absolute Python interpreter
already selected and checked for this environment. These are placeholders to
resolve from the installation and repository instructions, not directories to
create. Do not assume the target repository contains this project's scripts.
The installed `loop-engineering` dependency must remain a sibling skill.

```bash
"$HANDOFF_PYTHON" "$HANDOFF_SKILL_DIR/scripts/cli_session_handoff.py" --example
"$HANDOFF_PYTHON" "$HANDOFF_SKILL_DIR/scripts/cli_session_handoff.py" --request - < request.json
```

Only while maintaining a source checkout of **codex-dev-skills**, use its
tracked resolver from that checkout instead:

```bash
./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py --example
./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py --request - < request.json
```

The second command is a live session mutation. Ordinary verification uses
`--example` or fake executables only. Do not install an environment, widen
permissions, or call a live session to work around a missing interpreter.

## Request Policy


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
