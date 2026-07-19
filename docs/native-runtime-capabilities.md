# Native Runtime Capability Contract

This document defines the capability-neutral boundary between the shared Loop
Engineering contract and the runtime control planes that can invoke it. The
shared contract owns objective, task, evidence, review, and completion
semantics. Runtime capabilities may start, coordinate, observe, or wake work,
but they do not become completion authority.

Facts in the current capability table were last verified on 2026-07-10 from
the active callable schemas and the public Codex documentation. Every adapter
must still inspect the capability exposed by its active runtime instead of
assuming that a recorded schema is permanently available.

The custom-agent configuration facts below were last verified on 2026-07-11
from the public Codex subagent documentation. Runtime model availability and
reasoning support remain session capabilities and must still be preflighted.

## Shared Contract

The shared loop core must express an operation in capability-neutral terms:

```yaml
capability:
  kind: "goal | subagent | scheduler | thread | hook | sequential"
  available: true
  source: "active-tool-list | runtime-schema | official-documentation"
  operations: ["inspect"]
  mutation_class: "read-only | runtime-state-changing"
  last_verified: "YYYY-MM-DD"
```

The core may select an adapter only after it has classified the current task,
checked source-of-truth state, and established the authority required for the
operation. Capability availability never grants broader filesystem, network,
platform-write, destructive-action, or publication authority.

## Authority Mapping

| State or evidence | Authority | Not sufficient for |
| --- | --- | --- |
| Objective, Definition of Done, task transition, verification, and review evidence | Repo-owned loop state, current git state, accepted project artifacts, and accepted platform state | None; these are the completion authorities selected by the repository contract. |
| Native goal status, usage, or budget | Runtime progress control | Proving a task or objective complete without repo evidence. |
| Subagent status or summary | In-flight coordination evidence | Accepting changed files, verification, review, or completion without integration checks. |
| Desktop thread status or task summary | Desktop control-plane observation | Proving the delegated work satisfies its task brief or DoD. |
| Scheduled run or heartbeat | Wakeup evidence | Expanding scope, changing task priority, or granting permission. |
| Hook result | Guardrail or advisory evidence | Replacing sandboxing, approval policy, review, or complete enforcement. |
| Sequential fallback progress | Current-session working context | Replacing durable state when a repeated loop requires it. |

When runtime evidence conflicts with current repository or accepted platform
state, the loop must re-bootstrap and resolve the conflict before advancing.

## Capability Families

### Native goal

Goal semantics are shared whenever the active Codex runtime exposes Goal mode.
Official guidance describes goals as durable objectives for long-running work,
but adapters must capability-detect the active surface rather than assume
universal availability. Goal is a runtime progress controller around the
shared loop, not a second task ledger.

- Create a goal only when the user or an applicable higher-level instruction
  explicitly requests a goal.
- Inspect an active goal for status and budget information when the runtime
  exposes that operation.
- Mark a goal complete only after the shared completion audit succeeds.
- Mark a goal blocked only under the runtime's documented blocked threshold;
  difficulty, uncertainty, or an incomplete iteration is not enough.
- Pause, resume, edit, clear, and budget controls remain user- or
  runtime-controlled unless the active callable explicitly grants them.
- Starting a goal does not broaden sandbox or approval permissions.

When native goal capability is unavailable, the loop continues in the current
session or through the sequential fallback; absence of Goal mode is not itself
a blocker.

### Shared subagents

Subagent delegation is shared across current Desktop, Codex CLI, and IDE
surfaces. It is not Desktop-only behavior. The shared orchestration policy owns:

- bounded task briefs, file or work-packet ownership, DoD, and verification;
- spawn, observe, steer, wait, collect, and interrupt semantics when exposed;
- disjoint ownership or isolated worktrees for write-heavy parallel work;
- main-agent integration, diff inspection, verification, and review;
- treatment of worker summaries as context rather than completion proof.

The active runtime may present subagent activity differently, but that UI
difference does not change the shared delegation contract. Subagents are also
distinct from user-owned Desktop tasks created with a thread tool.

### Custom-agent profiles

Local Codex clients support standalone custom-agent TOML files under
`~/.codex/agents/` for personal adoption and `.codex/agents/` for trusted-project
adoption. Each file requires `name`, `description`, and
`developer_instructions`; supported session configuration keys may include
`model`, `model_reasoning_effort`, `sandbox_mode`, `mcp_servers`, and
`skills.config`. See [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).

The profile is a runtime configuration layer, not workflow authority. Its
technical `sandbox_mode` may differ by role, so preflight compares it with the
current parent sandbox and refuses a custom profile that would widen that
boundary. A balanced `workspace-write` profile therefore requires an equal or
more permissive parent sandbox; read-only roles remain non-widening. Separately,
neither role nor model choice grants workflow mutation authority, external
actions, broader assigned scope, gate satisfaction, or completion. Active
parent permission controls and managed requirements continue to apply.

Cost-aware route contract version 2 keeps capability class separate from
capability tier. Class continues to bind sandbox and workflow scope; tier
records the minimum model/reasoning need. The ordered tiers are `mechanical`,
`efficient`, `everyday`, `advanced`, `deep`, and `exceptional`. Selection uses
registry tier rank rather than profile filename order and may choose a higher
tier only as an explicit cost-degraded same-class fallback. Parent/default and
sequential fallbacks require current-session evidence for both class and tier.

General project configuration has higher documented precedence than user
configuration, but the public custom-agent page does not currently define every
same-name standalone-file collision. V2a therefore namespaces its roles,
detects collisions when the caller supplies the other applicable agent roots,
and reports an unresolved mapping instead of guessing. Project-scoped `.codex/`
layers are ignored for untrusted projects. See official
[Config basics](https://learn.chatgpt.com/docs/config-file/config-basic#configuration-precedence)
for general precedence and trust behavior.

The repository keeps reviewable profile sources under `agent-profiles/` so a
checkout does not auto-activate them. The `codex-agent-profiles` installer group
is explicit opt-in and is excluded from `--all`. The installed
`loop-engineering` skill includes `scripts/profile_preflight.py`, the canonical
profile registry, and `loopctl.py agent-route`; installation therefore preserves
the same validation and receipt contract outside the source checkout. Routing
rejects an alternate registry even when its contents look valid, and accepts
runtime/model availability only from the required `--runtime-facts`
current-session input. `agent-integrate` similarly reads exact Git branch/HEAD,
artifact bytes, verification files, and selected profile from explicit trusted
roots and checks exact worker/verification digests rather than trusting
repository-controlled receipt assertions.

### Scheduler

Scheduling is a runtime control-plane capability. Current Desktop and web
surfaces can manage scheduled tasks; Codex CLI and the IDE do not provide the
Scheduled management interface and instead prepare or test prompts, skills, and
scripts.

- A thread heartbeat returns to the current task and its context.
- A standalone scheduled task starts an independent run and may target a local
  project or isolated worktree when supported.
- A scheduled invocation runs the same shared loop iteration contract.
- Scheduling does not change objective, task ownership, permissions, human
  gates, or completion criteria.
- If scheduling is unavailable, use manual invocation, a continuation prompt,
  or the sequential fallback.

### Desktop thread control plane

Desktop thread tools manage user-owned tasks and their local or worktree
execution context. They are Desktop adapters, not the shared subagent primitive.

Current callable semantics include:

- `list_projects` returns project identifiers used for project-scoped creation.
- `create_thread` requires a prompt and a project or projectless target. A
  project target uses a returned `projectId` and selects local or worktree
  execution. Omit model and reasoning overrides unless the user explicitly
  requests supported values.
- A created task may return `threadId`; queued worktree setup may return
  `clientThreadId`. Either is dispatch evidence only.
- `fork_thread` may return a child thread identifier immediately for a
  same-directory fork or a client thread identifier while worktree setup is
  queued. A fork copies completed history only; send a follow-up only when work
  must continue in the child.
- `list_threads` and `read_thread` are observation operations.
- `send_message_to_thread`, `handoff_thread`, create, fork, archive, pin, and
  rename mutate runtime state and require the authority applicable to that
  exact action.

Creating a new or background Desktop task requires an explicit user request.
Before a project-scoped action, resolve the project through the documented
runtime capability; do not infer it from Desktop databases, logs, sessions,
caches, app state, or other private files.

### Hooks

Hooks are optional lifecycle guardrails. They can add context, run validation,
or deny supported tool calls when the active hook contract permits it. The loop
must still behave correctly when hooks are disabled, unsupported, or absent.

Hooks are not a complete enforcement boundary:

- current command hooks do not intercept every tool or equivalent action path;
- some parsed handler types and asynchronous behavior may be unsupported;
- a `SubagentStart` hook cannot be assumed to stop a subagent;
- hook output cannot replace sandboxing, approval policy, call-site target
  validation, integration review, or the completion audit.

Repo-local hooks should be opt-in through a trusted project configuration or a
separately packaged plugin. The Loop Engineering V1 native core must not depend
on a hook to remain safe or correct.

### Security scan workbench

A Codex Security workbench is a plugin-dependent workflow with its own durable
scan status, phase, target contract, and artifact directory. Those scan-native
records are authoritative for scan lifecycle. Goal status and worker status are
separate progress projections and cannot silently replace them.

- A scan that remains `running` is resumable even when Goal is blocked or a
  phase worker returns `safety_refused`.
- Worker refusal is a capability failure. Retry with a replacement worker or
  the current session before requesting exact parent scan-phase fallback authority.
- Parent scan-phase fallback authority must come from current-session control-plane
  input, never repository YAML.
- Partial scan artifacts, worker activity, Goal projection conflict, and turn
  boundaries are not reasons to invoke a terminal scan-failure operation.
- Completion and failure must follow the active scan skill's canonical artifact
  and recovery contract.
- If the UI suppresses detailed commentary, retain detailed evidence in durable
  artifacts and emit only a neutral fixed-format heartbeat. Do not infer task
  failure, repeatedly recreate Goal, or retry the same content with disguised
  wording. Bounded polling and current-session continuation remain available.

### External memory adapter

V2b provides a shared offline validation and disposition contract, not a
runtime adapter. A future adapter is plugin-dependent and must declare actual
read/write/invalidation/isolation/consistency/provenance/sensitivity/audit
capabilities and pass the V2b conformance harness. Adapter content, confidence,
timestamps, capability claims, and receipts remain untrusted advisory data.

No adapter is the default supported state. Disabled, unavailable, timeout,
partial, unsupported, incompatible, or untrusted memory disables only that
memory operation and preserves V1/V2a execution. Memory availability never
changes model selection, sandbox, permission, external-write authorization,
human gates, review, protected history, claim/lease state, or completion.

### Sequential fallback

The sequential fallback executes the same selected task in the current session
or prepares a durable continuation prompt or task brief. It preserves the same
source-of-truth, authority, verification, review, and completion rules. A
missing optional runtime capability changes execution mode, not task semantics.

For V2a profile routing, attempt the lowest sufficient same-class profile, a
parent/default mapping with explicit class/tier evidence, and current-session
sequential execution with the same evidence before stopping. Stop at a human
gate when the requested risk class or tier cannot be preserved safely.

## Legacy Desktop Wrapper Boundary

The `desktop_runtime_*` helper family is retained only as historical
compatibility evidence for the v0.x Desktop wrapper experiments. It is not the
active Loop Engineering runtime path, and its preflight, handshake, cache,
executor-envelope, injected-callable, or smoke evidence does not authorize or
implement a native capability call.

The native loop core and its adapters must not import or execute legacy Desktop
wrapper helpers. Current callable schemas and call-site validation govern native
operations. Historical tests may remain isolated until a separately reviewed
cleanup removes or archives them.

## References

- [Long-running work and Goal mode](https://learn.chatgpt.com/docs/long-running-work)
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Scheduled tasks](https://learn.chatgpt.com/docs/automations)
- [Hooks](https://learn.chatgpt.com/docs/hooks)
