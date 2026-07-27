# CLI Session Handoff Example

Use `cli-session-handoff` only after shared orchestration has selected a
bounded task and the user has explicitly authorized one CLI session start or
resume. The CLI session control plane is independent from Desktop
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
```

After confirming the absolute CLI executable, canonical worktree, exact HEAD,
read-only or workspace-write ceiling, timeout, and authorization, prepare a
request from the example:

```bash
python3 skills/cli-session-handoff/scripts/cli_session_handoff.py --example
python3 skills/cli-session-handoff/scripts/cli_session_handoff.py \
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
