# Codex Runtime Compatibility Evidence — 2026-08-12

This point-in-time record evaluates the current Codex Desktop callable surface
and Codex CLI against the repository's shared workflow and runtime adapters. It
does not promise that a callable, schema, UI behavior, or CLI version will
remain available.

## Scope And Sources

The assessment used only:

- callable descriptions and schemas exposed to the current Desktop task;
- normalized, read-only `list_projects` and `list_threads` result shapes;
- `codex --version` and public CLI help;
- repository code, tests, `.python-version`, and environment policy;
- official [Local environments](https://learn.chatgpt.com/docs/environments/local-environment)
  and [Git worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees)
  guidance;
- the maintained
  [2026-07-31 compatibility evidence](codex-runtime-compatibility-evidence-2026-07-31.md)
  as the previous comparison point.

No Desktop database, log, session, authentication file, cache, application
state, unpublished endpoint, UI scrape, or reverse-engineered internal was
read. No live task was created, forked, messaged, handed off, renamed, pinned,
archived, or navigated for this assessment.

## Version And Schema Evidence

| Surface | 2026-07-31 | 2026-08-12 | Classification |
| --- | --- | --- | --- |
| Codex CLI | `0.146.0` | `0.147.0` | CLI docs/test evidence refresh |
| Desktop bundle | `26.727.40816` build `6067` | version unavailable | no current public bundle evidence recorded |
| Desktop callable contract | version unavailable | version unavailable | active schema remains the call-site source |
| `list_projects` result | `schemaVersion: 2` | `schemaVersion: 2` | no observed schema-version change |
| `list_threads` result | `schemaVersion: 2` | `schemaVersion: 4` | Desktop adapter change |

The observed `list_threads` schema version 4 separates pinned tasks into
`pinnedThreads`, where entries carry `pinnedIndex`, and non-pinned tasks into
`threads`. Titles and summaries remain untrusted display metadata.

## `create_thread` Contract And Title Decision

The active callable requires `prompt` and `target`. `title`, `model`, and
`thinking` are optional. A project target carries the exact `projectId` returned
by `list_projects` plus a local or worktree environment. Ready creation returns
`threadId` and `hostId`; queued worktree setup returns `clientThreadId`, which is
not a usable `threadId`.

No exposed contract or official guidance states that omitting `title` changes
project association. The target's `projectId`, not the display title, is the
identity-bearing field. A live filled-versus-omitted A/B test would create user
tasks and was not authorized, so that behavior remains unverified rather than
inferred.

The conservative adapter policy is:

- keep `title` optional in the callable contract;
- supply a concise non-empty safe title on every adapter-issued `create_thread`
  call, using only a maintainer-approved nonsensitive task identifier plus a
  generic objective label;
- never copy prompt text, credentials, customer or incident details,
  repository paths, or untrusted registry text into the title;
- use the fixed title `Project task` when a safe specific title cannot be
  established, and preview the exact title at the call site;
- for project-scoped creation, verify the exact ready `threadId` in a supported
  registry result and require its observed `projectId` to match the selected
  project;
- treat title equality as display evidence only;
- wait for queued worktree setup to expose a ready task before association
  verification, and never create a duplicate because readiness or UI display
  is delayed;
- report project association as unverified when the runtime cannot expose it.

This closes the UI-stability concern without falsely claiming that title text
controls project grouping.

## Environment Selection

The active callable description sets these defaults:

- same-task continuation with completed history: `fork_thread` with
  `same-directory`;
- fresh task in a Git project: project `worktree` by default;
- fresh task in a non-Git project: project `local`;
- fresh task in a Git project's saved checkout: project `local` only when the
  user explicitly requests that checkout;
- intentionally non-project work: `projectless`.

Official worktree guidance describes each managed worktree as a separate
checkout and recommends project local-environment setup scripts for dependencies
and tools. Official local-environment guidance states that those setup scripts
run for new worktrees. `.worktreeinclude` may copy selected ignored files, but a
virtual environment is checkout-specific and must not be copied as a portable
runtime.

## Shared Python Environment Finding

The failure mode is shared, not Desktop-only:

- a Desktop managed worktree is a new checkout and does not inherit the saved
  checkout's activated virtual environment;
- an ordinary CLI shell opened in another Git worktree has the same property;
- `cli-session-handoff` runs a child in a disposable private clone with
  `shell_environment_policy.inherit="core"`, so it also cannot rely on the
  source checkout's activated environment.

Repository policy already required `.python-version`, but repository validation
used bare `python3`. On the assessed machine, bare `python3` selected Python
3.13.2 without PyYAML, while `pyenv` honored the tracked Python 3.12.9 and found
PyYAML 6.0.3. That proves interpreter resolution, not dependency absence, was
the immediate failure.

The shared fix is the tracked `scripts/project-python` resolver. It selects an
explicit `CODEX_PROJECT_PYTHON`, repository `.venv`, `pyenv`, or an
already-correct `python3`, in that order; it rejects any interpreter whose exact
version differs from `.python-version`. Repository validation, Desktop
worktree prompts, and CLI private-clone prompts use the same resolver. Missing
runtime or dependencies block verification and never authorize installing into
a different interpreter.

## Layering Decision

- Shared repository layer: add the fail-closed Python resolver and route the
  repository validation entrypoint through it.
- Desktop adapter: adopt current Git-worktree default, fill `title`, verify
  project association by `projectId`, and carry repository environment setup
  into worktree prompts.
- CLI adapter: update the private-clone prompt boundary to require the same
  repository resolver and report unavailable verification rather than using
  bare system Python.
- Shared workflow semantics: unchanged. Objective, task selection, evidence,
  review, and completion authority remain above both runtime adapters.
- Live Desktop mutation: not performed and still requires exact user
  authorization.

## Re-runnable Checks

```bash
codex --version
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
./scripts/project-python -m unittest tests.test_project_python
./scripts/project-python -m unittest tests.test_cli_session_handoff tests.test_native_runtime_contract_docs
./scripts/validate-repo.sh
git diff --check
```

Desktop callable schemas and read-only result shapes must still be re-read at
the actual call site. This evidence does not authorize a live Desktop task
action, dependency installation, or external write.
