# Runtime Compatibility

This repository uses four compatibility labels.

In current product naming, the Desktop control surface runs inside the ChatGPT
desktop app. This repository keeps `Codex Desktop` and `desktop` as stable
compatibility labels for Codex task, thread, worktree, UI, and scheduling
controls. The labels do not imply that shared reasoning or subagent delegation
is Desktop-only. See the maintained
[2026-09-01 compatibility evidence](codex-runtime-compatibility-evidence-2026-09-01.md).
The 2026-09-01 evidence records standalone CLI, Desktop application, and
Desktop-bundled CLI observations independently and rechecks the active Desktop
callable boundary including sidebar organization surfaces. The active
`desktop-sidebar-organization` skill implements a separate thin mutation
contract without collapsing the CLI and Desktop entry paths, and preserves the
distinction between the deprecated
`codex mcp-server`, Codex's MCP client configuration, connectors, plugins, and
native Desktop task/thread tools.

## `shared`

Works in Codex CLI, Codex Desktop, and supported IDE surfaces through repository
files, ordinary shell commands, git inspection, native Goal mode, and bounded
subagent delegation when those capabilities are available.

## `cli`

Designed primarily for Codex CLI. A Desktop user may still follow the workflow
manually, but the skill must document the fallback.

`cli-session-handoff` is the thin CLI control-plane adapter for one bounded,
explicitly authorized `codex exec --json` start, exact-UUID resume/fork, or
clean non-interactive fresh continuation. It is
separate from shared task selection/subagents and from Desktop task/thread
callables. Its redacted receipt is coordination evidence, not completion
authority. Its disposable private clone does not inherit the source checkout's
activated Python environment, so it must follow the repository's tracked
environment resolver when present and fail verification closed on a version or
dependency mismatch.

Fresh continuation is not a fork: it starts without copied conversation
history and requires the shared durable checkpoint. Interactive or dirty CLI
rollover degrades to a manual/current-session prompt without claiming success.

CLI `/plugins`, `/import`, and `/memories` are runtime configuration and
personalization controls. They are not `cli-session-handoff` operations and do
not grant session-mutation, repository-write, or completion authority.

## `desktop`

Requires Codex Desktop user-owned task, thread, worktree, UI, or scheduling
control. Shared main-agent reasoning and subagent delegation are not, by
themselves, Desktop-only behavior. A worktree's interpreter selection is also
not Desktop-only: the same repository-owned resolver contract applies to CLI
worktrees and disposable clones.

Desktop availability is capability-based rather than macOS-assumed. The Linux
desktop app is currently a preview, and features such as Computer Use may be
absent there. An unavailable Desktop capability uses the documented CLI,
manual, prompt, or sequential fallback without reading private runtime state.

## `plugin-dependent`

Requires an installed plugin, connector, or platform-specific tool. The
dependency must be named, and the workflow must define what happens when it is
unavailable.

This repository supports two separate distribution paths: its tracked
filesystem installer and the skills-only `codex-dev-skills` universal plugin.
Use only one path in a Codex profile. Desktop/CLI imports leave existing setup
in place, so imported skills must also be reviewed for name collisions before
installation.

## Runtime Memory Boundary

Local Codex memories, ChatGPT memory settings, and Computer History are
runtime personalization data. They are untrusted advisory context and are
separate from the repository's default-disabled `loop-memory-sqlite/v0` Memory
M1 adapter. Do not automatically copy app history or generated memory files
into a repository, M1 state, verification evidence, or completion records.

## Metadata

Every skill should include a runtime line near the top:

```markdown
Runtime compatibility: shared
```

The README skill table must use the same value.

## Native Capability Boundary

The canonical mapping is [Native Runtime Capability Contract](native-runtime-capabilities.md):

- Goal mode is shared but may be created only when explicitly requested.
- Bounded subagents are shared; ownership must be disjoint and the main agent
  must verify and integrate their output.
- CLI session start/resume/non-interactive fork and manual interactive fork are owned by the CLI adapter after shared
  orchestration selects the handoff; it requires exact mutation authority and
  parent integration.
- Custom-agent files are public local runtime configuration. Capability classes
  and cost-aware capability tiers remain shared semantics; concrete
  model/reasoning mappings require runtime preflight and may differ across CLI,
  Desktop, and IDE availability. A higher-tier fallback is recorded, while a
  lower tier cannot silently satisfy a higher-tier route.
- Desktop user-owned task/thread/worktree actions and Desktop scheduling are
  thin runtime adapters over shared workflow semantics.
- Context-health assessment is shared across Desktop, CLI, and IDE. Desktop may
  use an authorized fresh `create_thread`; CLI phase one may use clean
  non-interactive `fresh-continuation`; IDE assumes no independent task control
  plane and uses current-session or prompt fallback.
- Hooks are optional guardrails, not complete enforcement.
- Goal, subagent, scheduler, hook, and thread state are coordination evidence;
  they do not prove repository completion.

When a capability is unavailable, preserve the same objective, authority,
verification, review, and human-gate rules through the current session,
sequential execution, a task brief, or a paste-ready continuation prompt.

The complete five-outcome contract, capability matrix, migration notes, and
cost/quality comparison are in
[Context Continuity And Fresh-Context Rollover](context-continuity.md).

Absence of the custom-agent surface preserves V1 sequential/shared semantics.
It must not be reported as task completion or as a permanent Goal failure.

Absence of an external-memory adapter likewise preserves V1/V2a behavior. V2b
validation is shared and offline. A concrete adapter is plugin-dependent and
must declare its actual capabilities; unavailable or incompatible operations
are disabled rather than simulated.

## GitNexus Adapter Boundary

The V2c-A GitNexus driver is shared Python code around a machine-local external
CLI. Executable discovery/configuration must work in Codex Desktop on macOS and
Codex CLI on Linux without committing an executable path, `GITNEXUS_HOME`,
registry, index, database, credential, or other machine-local state. The adapter
is disabled until the runtime explicitly supplies and qualifies that local
configuration.

The shared operator surface is
`skills/loop-engineering/scripts/gitnexus_adapter.py`. Its `qualify`, `status`,
`refresh`, and `disable` subcommands use only machine-local arguments and emit
redacted JSON. The adapter stores no enable bit: `--enabled` is a per-invocation
opt-in, and refresh also requires `--confirm-explicit-refresh`. This identical
control boundary is intended for Desktop/macOS and CLI/Linux; only macOS arm64
has live GitNexus evidence in V2c-A.

The runtime control plane must also provide a canonical package root and
caller-owned accepted SHA-256 values for the entry, complete package tree, and
bound interpreter when present. The adapter checks them before invoking the
tool and rechecks the package tree at use time. These values are machine-local
configuration and must not be committed.

GitNexus 1.6.9 has live macOS arm64 qualification for executable discovery,
required flags, schema-5 metadata, isolated offline index-only refresh, and
tracked/Git-control postconditions. Linux has portability fixtures for POSIX
paths, regular-file/symlink policy, subprocess argv/environment, timeout/lock,
and metadata handling, but no live GitNexus qualification. Do not present those
fixtures as Linux runtime evidence.

Refresh is supported only where the controller can prove the direct worktree
and Git administrative boundary, including a pre-existing `.git/info/exclude`
entry and stable `.git/info/exclude`, `.git/config`, and `.git/HEAD` digests.
Linked-worktree or ambiguous Git administrative layouts fail closed rather than
guessing a path. Human `status`/`list` output is never parsed. `read_query` and
all backend write operations remain unsupported in this baseline, regardless of
whether the executable exposes additional unqualified surfaces.

## GitNexus Hook Boundary

The V2c-B hook runner is shared Python code intended for the current Codex CLI
and desktop hook contract on POSIX hosts. It uses only documented
`SessionStart` and `PostToolUse` JSON fields for `Bash` and `apply_patch`. The
current live evidence does not provide a native `post-commit` event or complete
tool interception, so these paths are best-effort freshness signals and
`SessionStart` is the compensating check. Codex supports background command
hooks, but this runner remains synchronous because background invocations may
overlap, finish out of order, or be cancelled with the session.

Project hooks load only for trusted projects and non-managed command hooks must
be reviewed and trusted. Templates are installed inertly; neither CLI nor
Desktop installation activates a hook or writes runtime config. Hooks disabled,
unavailable, skipped, or unsupported leave V2c-A and the no-backend workflow
unchanged. Controller failure installs a repository-bound machine-local circuit
breaker so later events cannot retry automatically without operator clearance.
Windows command/runtime behavior is not qualified in this increment; the
runner fails safe outside POSIX rather than claiming portability.

## Desktop Thread And Task Actions

Use only the documented callable exposed by the active runtime. Before an
action, verify:

- exact action and target identity;
- request and response fields used by the call;
- whether the action is read-only or state-changing;
- runtime/tool contract version, or `version unavailable` plus the capability
  source and `last_verified` date;
- permission and authentication failure handling;
- the user authorization required for that exact action.

For example, current Desktop task creation returns a `threadId` for immediate
creation or a queued `clientThreadId`. Treat those as different lifecycle
signals and validate the actual response before relying on it. Do not infer a
callable from private Desktop state, UI scraping, local databases, logs,
sessions, or caches.

Creating, forking, messaging, archiving, pinning, or otherwise mutating a
user-owned Desktop task requires the authority specified by the active runtime
and repository policy. A CLI fallback may prepare the same prompt or task brief
but must not claim to control Desktop tasks.

Creating an immutable Desktop thread-share link is additionally a
privacy-sensitive disclosure. Require explicit user intent, exact thread and
audience preview from public product context, and user-confirmed review of the
complete thread before `share_thread`; recent, truncated, or paginated reads
are insufficient by themselves. Runtime
secret-pattern redaction is defense in depth rather than a confidentiality
guarantee. The current callable creates links but does not revoke them; use the
documented ChatGPT data-controls path for review or revocation and keep link
creation, revocation, and repository completion separate.

For the same Desktop task moving to a new conversation, a supported
`fork_thread` same-directory action reuses the source checkout or existing
worktree, copies completed history, and remains anchored to the source host.
The fork request has no caller-supplied `hostId`, and its current response does
not guarantee one. Preserve a known source host, then obtain the child
`hostId` from supported registry evidence that explicitly exposes it before a
host-sensitive follow-up; never assume an unresolved remote child is local. A
fresh same-project task uses the exact `projectId` and its runtime-returned host
identity. Git projects default to worktree execution; non-Git projects use
local, and a Git project's saved checkout uses local only when the user
explicitly requests it. `projectless` is reserved for intentionally non-project
work. Cross-host continuation is a
separately authorized handoff with `destinationHostId`, not a fork option.

CLI `codex fork <SESSION_ID>` is the analogous CLI-only interactive control
for a new chat from a saved session. Use an exact UUID and an explicit
`tui.resume_cwd` current/session choice when directories differ. The
repo-owned `codex exec` handoff executor remains non-interactive and does not
automate this command.

CLI `codex agents` is a separate interactive session dashboard. Its observation
states do not prove repository completion, and each selected start/open/rename/
stop action retains its own mutation authority. CLI `codex queue` may be
prepared manually only for an exact canonical UUID and one bounded nonsensitive
message represented as one argv token without shell interpolation. Queue
acceptance is dispatch/wakeup evidence, not proof that the
destination processed the message. Neither command is routed through the
private-clone executor. `codex doctor --json` remains redacted diagnostics only.

After a successful `create_thread`, the Desktop adapter must emit the
runtime-provided created-task UI directive with the returned `threadId`, or
with `clientThreadId` while worktree setup is queued. The identifier types are
not interchangeable. Dispatch, the UI registration directive, exact-ID
registry observation, navigation, sidebar rendering, and repository completion
remain separate states.

Use an exposed navigation callable only when the user explicitly asks to open
or show the task. If it is unavailable or fails, provide the official chat
search and sidebar filter/archive checks; a `codex://threads/<threadId>` deep
link is limited to a local chat. Pinning changes sidebar placement rather than
task registration, and a stale sidebar must never cause duplicate creation or
private-state refresh attempts.

`list_threads`, `read_thread`, and `wait_threads` are observation and
coordination operations when the active callable schema classifies them that
way. A bounded wait may return compact progress for multiple tasks, but it is
not repository completion evidence and does not replace detailed reads,
integration checks, verification, or review.

Sidebar organization is a separate Desktop-only control plane. The
`desktop-sidebar-organization` skill uses fresh `list_threads` and
`list_projects` discovery, exact runtime IDs, a reviewed dry-run plan,
action-specific authorization, response validation, and post-mutation
readback. It fails closed rather than guessing from display names, stale or
partial snapshots, or queued `clientThreadId` values. Delete and complete-list
reorder remain human gates; CLI fallback is an exact manual plan, not a live
sidebar mutation.

## Evidence

Runtime evidence should record the command or callable, target, relevant input
shape, result or error classification, source runtime, and verification date.
Repository completion still requires current files, git state, verification,
review, and accepted platform state where applicable.

## Retired V1 Historical Context

Desktop Runtime Wrapper V1 is retired and is not an active compatibility
boundary. Its [retirement record](desktop-runtime-wrapper-v1-deprecation.md)
and [historical plan](desktop-runtime-wrapper-v1-plan.md) are non-executable
context only. They do not define a runnable or importable integration path.

Current callable schemas and call-site validation are authoritative. Historical
response shapes must not override validation of the requested action, target,
permission or authentication outcome, returned identity, or status. Native
runtime contracts retain the fail-closed, private-state, external-write, and
non-execution boundaries.

## Safety Boundary

No compatibility label authorizes commit, push, PR creation, merge, deploy,
platform comments, review submission, destructive action, or another external
write. Those actions remain behind exact user authority and the applicable
human gate.
