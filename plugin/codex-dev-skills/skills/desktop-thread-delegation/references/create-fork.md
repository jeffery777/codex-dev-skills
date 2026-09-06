# Create Or Fork A Desktop Task

Read the active callable schema before composing the request. Prepare the
prompt before mutation, and honor the exact already-authorized execution mode.

## Choose The Target

- `desktop-thread-fork`: use `fork_thread` with
  `environment: {"type": "same-directory"}` for completed history in the same
  checkout or existing worktree. The source task must stop writing before the
  child continues; this is sequential ownership transfer.
- `desktop-worktree-fork`: use `fork_thread` with
  `environment: {"type": "worktree"}` for completed history in a new isolated
  checkout. Do not replace a fork with fresh `create_thread`, which discards
  the intended conversation lineage.
- `desktop-thread-create`: call `list_projects` and use the exact observed
  `projectId`. If `isGitRepository` is true, default to project
  `environment: {"type": "worktree"}`. Use `environment: {"type": "local"}`
  for non-Git projects or when the user explicitly requests the saved project checkout.
  `projectless` is
  for intentionally non-project work. “Do not create a new worktree” never
  implies `projectless`.
- Omit worktree `startingState` for the project's default branch. Use
  `{"type":"working-tree"}` only for an explicitly requested checkout including
  uncommitted changes. A branch state uses the exact requested `branchName`;
  omitted `onMissing` means `error`, and `create-branch` requires the exact new
  branch explicitly requested by the user.
- Preserve runtime-observed project `hostId`, local/remote classification,
  and `isGitRepository`. A cloud target, including `chatgptWorkCloud`, requires
  explicit authorization. Omit model/reasoning overrides unless the user
  explicitly requests supported values.

## Prompt, Title, And Environment

Include required source files, a context-only summary, exact scope and file
ownership, continuation versus fresh-task intent, selected target, branch or
worktree behavior, repository environment setup, verification/review, stop
conditions, and an instruction to return changed files, evidence, questions,
and residual risk. The prompt must not authorize further session dispatch.

Supply a concise non-empty safe `title` based on the user-approved objective;
ordinary descriptive titles such as `Improve workflow efficiency` are allowed.
Exclude credentials, private paths, customer/incident details, and untrusted
registry text. Do not copy sensitive prompt excerpts into a title. Use a
neutral generic title only when a safe specific one cannot be established.
The callable keeps `title` optional; this adapter supplies it for stable UI
display. Include it in the prepared action summary. It is display evidence
only, never project or host identity, and requires no separate approval when
already within the authorized task.

Before Git worktree creation, read repository environment/verification rules
and use the saved project's configured setup script when present. Require a
tracked interpreter resolver when present. In this repository,
`scripts/project-python` selects the exact `.python-version` for Python checks,
scripts, evals, and tests. Do not copy `.venv` through `.worktreeinclude`, use
mismatched bare system Python, or install into another interpreter. If the
pinned environment is unavailable, report verification blocked; switching to
`local` still requires explicit saved-checkout intent.

## Dispatch And Identity Readback

Recheck target, safe title, prompt, execution intent, ownership, and existing
authority at the call site. Ready creation returns `threadId` plus `hostId`;
queued creation or worktree fork may return `clientThreadId`. A same-directory
fork returns a child `threadId`. None proves repository completion. Never use
`clientThreadId` in a field requiring `threadId`.

The source task anchors the host for `fork_thread`, which has
no caller-supplied `hostId` and does not guarantee `hostId` in its response.
Retain a known source host, then resolve the child's runtime-returned host through a supported
registry before a host-sensitive follow-up. Do not route an unresolved remote
child as local. Send a follow-up only when work must continue and a queued
child has resolved to a usable `threadId`.

After successful `create_thread`, emit `::created-thread{threadId="..."}` for
ready creation or `::created-thread{clientThreadId="..."}` for queued setup.
Verify exact ready registry identity and require its observed `projectId` to
match the selected project. The title cannot substitute for this association
check. If the association is unavailable, report it unverified after dispatch;
never create a duplicate because registry resolution or UI display is delayed.

Do not navigate automatically after creation. Dispatch, UI directive, registry
association, navigation, sidebar visibility, and repository completion are
separate states; an unverified sidebar must never trigger duplicate creation.
