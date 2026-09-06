# Fresh Desktop Rollover

Read with [create/fork mechanics](create-fork.md) only when shared context
health selected `prepare-fresh-rollover` for the same repository and objective.
Validate a complete canonical checkpoint, digest, lineage/idempotency, material
progress, one destination writer, and confirmed source stop-writing.

Use fresh `create_thread` with a checkpoint-only prompt; neither same-directory
nor worktree `fork_thread` is a substitute because forks copy completed
conversation history. Use the exact already selected project and set worktree
`startingState` to
`{"type":"branch","branchName":"<checkpoint-branch>","onMissing":"error"}`.
Never omit this state or substitute the default project branch for rollover.

After dispatch, the source performs no further repository writes and the
destination's ownership remains pending. Its first actions are read-only
`git branch --show-current` and `git rev-parse HEAD` checks against the
checkpoint. Only an exact match activates it as the sole writer. A mismatch
stops at a human gate and the source remains stopped. Exact replay never
creates a duplicate task.

If capability or validation is unavailable before dispatch, reground the source
or return the prepared prompt. Do not claim task creation, ownership transfer,
or completion without evidence. After uncertain dispatch, resolve identity
through supported observation before any new dispatch.
