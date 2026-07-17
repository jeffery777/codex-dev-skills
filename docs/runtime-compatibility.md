# Runtime Compatibility

This repository uses four compatibility labels.

## `shared`

Works in Codex CLI, Codex Desktop, and supported IDE surfaces through repository
files, ordinary shell commands, git inspection, native Goal mode, and bounded
subagent delegation when those capabilities are available.

## `cli`

Designed primarily for Codex CLI. A Desktop user may still follow the workflow
manually, but the skill must document the fallback.

## `desktop`

Requires Codex Desktop user-owned task, thread, worktree, UI, or scheduling
control. Shared main-agent reasoning and subagent delegation are not, by
themselves, Desktop-only behavior.

## `plugin-dependent`

Requires an installed plugin, connector, or platform-specific tool. The
dependency must be named, and the workflow must define what happens when it is
unavailable.

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
- Custom-agent files are public local runtime configuration. Capability classes
  and cost-aware capability tiers remain shared semantics; concrete
  model/reasoning mappings require runtime preflight and may differ across CLI,
  Desktop, and IDE availability. A higher-tier fallback is recorded, while a
  lower tier cannot silently satisfy a higher-tier route.
- Desktop user-owned task/thread/worktree actions and Desktop scheduling are
  thin runtime adapters over shared workflow semantics.
- Hooks are optional guardrails, not complete enforcement.
- Goal, subagent, scheduler, hook, and thread state are coordination evidence;
  they do not prove repository completion.

When a capability is unavailable, preserve the same objective, authority,
verification, review, and human-gate rules through the current session,
sequential execution, a task brief, or a paste-ready continuation prompt.

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

## Evidence

Runtime evidence should record the command or callable, target, relevant input
shape, result or error classification, source runtime, and verification date.
Repository completion still requires current files, git state, verification,
review, and accepted platform state where applicable.

## Historical Wrapper Evidence

The `desktop_runtime_*` scripts and
[Desktop runtime wrapper V1 plan](desktop-runtime-wrapper-v1-plan.md) are
retained for regression and migration analysis only. They are not the active
Loop Engineering path and active skills must not import, execute, or recommend
them. If a future maintainer studies them, their recorded `thread_id` or
`pendingWorktreeId` response shapes must not override the active callable
schema.

## Safety Boundary

No compatibility label authorizes commit, push, PR creation, merge, deploy,
platform comments, review submission, destructive action, or another external
write. Those actions remain behind exact user authority and the applicable
human gate.
