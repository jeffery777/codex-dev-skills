# Issue #115 Codex CLI Session Handoff

## Objective

Add a Codex CLI-native session handoff adapter that can start or resume one
bounded non-interactive CLI run through the documented `codex exec` surface
while preserving the existing shared-core/thin-adapter architecture.

## Source Of Truth

- Repository instructions: `AGENTS.md`
- GitHub objective: Issue #115
- Runtime capability contract: `docs/native-runtime-capabilities.md`
- Runtime compatibility policy: `policies/runtime-compatibility-policy.md`
- Shared workflow contract: `policies/reusable-workflow-contract.md`
- Implementation plan: `docs/loops/issue-115/implementation-plan.md`
- Task manifest: `docs/loops/issue-115/task-manifest.yaml`

Repository files, Git state, verification, review evidence, and accepted
platform state remain authoritative. A child CLI session identifier, process
exit, agent summary, or handoff receipt is coordination evidence only.

## Architecture

### CLI Entry

Codex CLI invokes shared skills directly. After shared orchestration has
selected a bounded handoff, `cli-session-handoff` may use the stable
non-interactive CLI surface:

- `codex exec --json -` with the prompt on stdin to start a saved CLI session;
- `codex exec resume --json <SESSION_ID> -` with the prompt on stdin to
  continue a known session.

The adapter does not call Desktop tools, inspect private session storage, or
use the experimental app-server control plane.

### Shared Core

The shared layer continues to own objective, task selection, task brief,
authority, verification, review, integration, and completion. It supplies a
bounded prompt and consumes a redacted handoff receipt. It does not assume how
the runtime represents a session.

### Desktop Entry

Desktop task, thread, worktree, host-handoff, and automation operations remain
owned by the Desktop adapter and its active callable schema. A CLI session ID
is not a Desktop `threadId` or queued `clientThreadId`.

## Scope

### In Scope

- A `cli-session-handoff` skill installed through a dedicated CLI group that
  depends on, but is not part of, the shared delivery workflow.
- A versioned JSON request/result contract for one `start` or `resume`.
- Explicit, canonical Codex executable and Git-worktree target validation.
- Fixed subprocess argv construction with no shell interpolation.
- Explicit read-only or workspace-write sandbox selection.
- Bounded timeout, output, JSONL line, and private-clone patch limits.
- Public JSONL event parsing for session identifier and terminal status.
- Machine-readable receipts with deterministic failure classes and a fixed
  omission marker instead of untrusted child-summary text.
- Offline fake-executable tests and an opt-in live smoke procedure.
- Runtime, usage, troubleshooting, installer, and routing documentation.
- macOS/Linux private-clone target isolation with best-effort process-tree
  cleanup and fail-closed fallback on other hosts.

### Out Of Scope

- Desktop `create_thread`, Desktop task observation, or cross-host handoff.
- Interactive CLI UI automation.
- CLI `fork` automation in the initial contract.
- App-server, remote-control, daemon, sidecar, scheduler, or shared queue.
- Raw transcript persistence or reads from CLI/desktop private runtime state.
- Credentials in request/result artifacts.
- Automatic chaining, retry, promotion, commit, push, PR, merge, release, or
  deployment.
- Treating child output as repository completion evidence.

## Definition Of Done

- The three runtime layers and identifier families remain distinct.
- One bounded `start` and one bounded `resume` operation have a versioned,
  fail-closed contract.
- The executor never invokes a shell and rejects ambiguous targets, non-Git
  workspaces, unsafe executables, permission widening, malformed events,
  duplicate terminal/session events, excessive output, timeout, interruption,
  and non-zero execution.
- The result records only public capability/version evidence, target Git
  identity, operation, session identifier when emitted, terminal
  classification, exit status, a fixed omitted-summary marker, and safety
  invariants.
- Offline tests perform no live Codex session creation.
- A live smoke remains a separately authorized runtime-state mutation.
- Existing shared/CLI/Desktop contract and loop safety tests remain green.
- A deep code review finds no unresolved blocking issue before commit or PR
  readiness.

## Authority And Human Gates

- Issue creation and local branch creation are authorized for this objective.
- Local implementation and offline verification are authorized.
- A real `codex exec` start/resume creates or mutates CLI session state and
  consumes model/runtime resources; it requires explicit live-smoke authority.
- Commit, push, PR creation, platform comments, merge, release, and publication
  remain separate human gates.
