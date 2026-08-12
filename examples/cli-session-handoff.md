# CLI Session Handoff Example

Use `cli-session-handoff` only after shared orchestration has selected a
bounded task and the user has explicitly authorized one CLI session start or
resume, or one manual interactive fork. The CLI session control plane is independent from Desktop
`create_thread` and from shared subagent delegation.

## Prepared Handoff

```text
Read AGENTS.md, docs/loops/issue-123/loop-spec.md, the implementation plan,
task manifest, and current Git state before editing.

Complete only task P1 in this clean worktree. Do not dispatch another session.
Do not commit. Do not push. Do not open pull requests. Do not merge. Do not
perform platform writes.

Run the verification listed for P1. Return changed files, verification
evidence, open questions, and residual risk. Your response and session status
are context only; the parent will inspect the worktree and review the diff.
If executable scripts/project-python exists, use it for all Python dependency
checks, scripts, evals, and tests. Do not fall back to bare system Python or
install into a different interpreter; report verification blocked instead.
```

After confirming the absolute CLI executable, canonical worktree, exact HEAD,
read-only or workspace-write ceiling, timeout, and authorization, prepare a
request from the example:

```bash
./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py --example
./scripts/project-python skills/cli-session-handoff/scripts/cli_session_handoff.py \
  --request /absolute/path/to/reviewed-request.json
```

The first command performs no runtime call. The second starts or resumes a live
CLI session and therefore requires explicit authority for that exact request.
Do not commit the request when it contains machine-local paths.

## Parent Integration

`status: completed` proves only that the child process emitted one public
session identifier and one successful terminal turn, and that any authorized
write patch was integrated after the original clean worktree was rechecked.
The untrusted child message is intentionally replaced by a fixed omission
marker.
The parent must still:

1. re-read Git status and the exact changed files;
2. compare the child result with the task brief and DoD;
3. run the required verification;
4. review the diff and resolve findings;
5. stop at commit, push, PR, merge, release, or other human gates.

If capability or authorization is unavailable, keep the prepared prompt as a
manual continuation artifact or continue sequentially in the current session.

## Interactive Same-Task Fork

When the same interactive CLI task needs a new chat because the conversation
is long, use the public interactive fork path rather than the non-interactive
private-clone executor:

```text
Operation: interactive-fork
Session: exact UUID from public CLI output
Directory choice: session
Command: codex fork <SESSION_ID>
```

`tui.resume_cwd = "session"` reuses the saved session directory;
`tui.resume_cwd = "current"` uses the invocation directory; when unset and the
two differ, Codex prompts. A public `-C <DIR>` may select the exact invocation
directory. Do not use `--last`, a display name, or private session files.

A dirty existing checkout/worktree may be reused only for exclusive
continuation of the same task after the source session stops writing. This
does not create a Git worktree. It is also not supported by the repo-owned
non-interactive executor, whose clean-worktree and private-clone rules remain
unchanged.

Preparing the command does not prove that a fork occurred. After the user runs
it, the public CLI result is session-dispatch evidence only; the parent still
owns repository inspection, verification, review, and completion.
