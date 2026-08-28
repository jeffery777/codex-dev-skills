# codex-dev-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Runtime: Codex CLI + Desktop](https://img.shields.io/badge/runtime-Codex%20CLI%20%2B%20Desktop-blue)](#runtime-compatibility)
[![Repo hygiene](https://img.shields.io/badge/hygiene-validate--repo.sh-informational)](#verification)

`codex-dev-skills` is an OSS maintenance workflow pack for OpenAI Codex CLI and Codex Desktop.

In current product naming, the Desktop surface runs inside the ChatGPT desktop
app. This repository retains `Codex Desktop` and `desktop` as compatibility
labels for Codex task, thread, worktree, and scheduling controls; those labels
do not make shared reasoning or subagent delegation Desktop-only.

It helps maintainers move beyond one-off prompts. Teams can combine reusable
skills, an executable loop contract, native goals, shared subagents, formal
gates, and thin runtime adapters to run bounded implementation, review,
handoff, and release-readiness workflows consistently.

Repository source/package version is declared by `catalog.yaml`; `install.sh`
and the package-local plugin manifest must match it. A matching release-notes
file is a point-in-time candidate-preparation record, not publication proof.
Current publication state comes from GitHub Release metadata and the
corresponding annotated tag through the connector-first control plane. Ordinary
offline validation checks source/package parity and candidate structure without
network access. Active guidance intentionally carries no mutable latest-release
or development-candidate pointer. See the
[release-state contract](policies/release-state-contract.md).

The v0.18.2 source snapshot refreshed the public Codex CLI/MCP compatibility
boundary for the 2026-08-24 `codex mcp-server` deprecation and added a
backward-compatible `--skip-unit-tests` validator mode so exact-head CI keeps
all checks and one full discovery pass without rerunning the validator's
44-module focused subset. It did not remove general MCP client support, weaken
repository validation, or change runtime, installer, security, data, or
completion authority contracts.
Issue #175 / PR #176 published the post-release state-coherence patch at merge
commit `b5cb03ae467222215f42c3081cad796ad3a2ecf3`; the annotated `v0.18.1`
tag and non-draft, non-prerelease GitHub Release bind that exact commit. The
repository has no deployment target or publish/deploy workflow, so deployment
is not applicable and GitHub Release publication is not deployment evidence.
This is historical traceability, not a current-publication pointer.
v0.18.0 published the Desktop Runtime
Wrapper V1 retirement through Issue #174 / PR #173 at merge commit
`3b789e2f9749f2643b6fe75397d22f6e21a71ce2`; the annotated `v0.18.0` tag and
non-draft, non-prerelease GitHub Release bind that exact commit. The repository
has no deployment target or publish/deploy workflow, so deployment is not
applicable and GitHub Release publication is not deployment evidence. v0.17.1
published the documentation-coherence patch through Issue #167 / PR #168.
Memory M1 was published in v0.14.0 through Issue
#147 / PR #148. v0.14.2 published the installer-backup isolation
hotfix through Issue #151 / PR #152. v0.15.0 published lower-overhead agent
coordination guidance and a Terra-high `senior` routing tier through Issue #153
/ PR #154. v0.15.1 published the CLI/Desktop/GitHub control-plane compatibility
patch through Issue #155. v0.16.0 published the exact GitNexus index lifecycle
and content-bound evidence identity through Issue #157. v0.16.1, published
through Issue #159, makes qualification and refresh share one configured,
bounded deadline without changing the M0/M1 feature or authority baseline.
v0.16.2, published through Issue #161 / PR #162, refreshes the independent CLI
and Desktop adapters for CLI 0.149 session dashboard/queue behavior and
immutable Desktop thread sharing without changing shared completion authority.
v0.16.3, published through Issue #163 / PR #164, established the historical
Desktop runtime wrapper V1 retirement preparation; Issue #171 subsequently
retired the obsolete helper family while preserving independent security
fixtures and native runtime contracts.
v0.17.0, published through Issue #165 / PR #166, adds a shared context-continuity
assessment, durable fresh-rollover checkpoint, single-writer transfer,
lineage/idempotency/anti-recursion, Desktop/CLI/IDE capability matrix, and a
clean non-interactive CLI fresh-continuation path. Two unfinished review/fix
rounds trigger assessment only; no task is created automatically.
V3-B remains the released evaluation baseline from v0.13.0.
The v0.12.1 compatibility patch through Issue #139 updated Desktop/CLI runtime
adapters and repository verification before V3-B without changing shared
completion authority.
V1 remains
the production workflow/authority core, V2a adds heterogeneous subagent
routing, V2b adds a backend-neutral external-memory safety contract, V2c-A
adds the qualified default-disabled GitNexus adapter/controller boundary, and
V2c-B adds optional trusted lifecycle freshness hooks. V2d-A adds the strict
offline `loop-operational-evidence/v0` envelope, run/iteration/failure/
environment/artifact document family, bounded taxonomy, redaction boundary,
typed relationships, synthetic fixtures, and deterministic evals. V2d-B adds
the separate `loop-improvement-lineage/v0` and
`loop-evidence-projection/v0` families, deterministic Markdown/typed-graph
views, and an optional non-mutating Obsidian reference profile without
changing V2d-A. V3-A adds the downstream
`loop-improvement-proposal/v0` family, deterministic integer scoring, stable
ties and duplicate suppression, complete evidence lineage, bounded structured
hypotheses/intents, and a stdout-only manual/CI CLI. All output remains
proposal-only behind an independent pending human/platform promotion gate.
V3-B adds the downstream `loop-candidate-evaluation/v0` family, bounded
same-policy synthetic baseline/candidate comparison, exact environment
equivalence, deterministic independent replay, a memory-off default with an
optional V2b-validated advisory-context seam, and a permanently
non-promotional packet.
v0.9.1 aligned the
public handoff, recorded one bounded notify-only adoption, and added repository
guardrails for index-only GitNexus analysis and ready-PR Issue linkage.
v0.9.2 refreshes the independent Codex CLI and Desktop runtime interfaces,
makes `~/.agents/skills` the safe default installer target while retaining an
explicit legacy mode, and adds an opt-in CLI-only bounded `start`/`resume`
session handoff adapter over the shared delivery layer. v0.9.3 adds one
repository-owned Code Mode tool-orchestration policy, deploys it with the
workflow groups that need substantial tool execution, and validates source,
installed-target, dependency, manifest, update, and runtime-reference
consistency. Runtime observations, handoff
receipts, external memory, GitNexus metadata, hook output, and linkage CI
remain advisory and never replace repository, Git, verification, review,
protected authorization, accepted platform state, or completion truth. No
activated production memory backend, scheduler, daemon, or automatic hook
activation is included.

V2d-A and V2d-B remain public, non-sensitive contract prerequisites. The
private manual/CI qualification and V3-A re-entry evidence remain outside this
repository; Issue #133 implements only the public evidence-to-proposal slice.
No slice moves private runtime state into public Git. See the
[Operational Evidence program](docs/programs/operational-evidence/README.md).

Issue #135 defines the staged re-entry roadmap. Issue #143 published V3-B in
v0.13.0, Issue #145 delivered Memory M0, and Issue #147 / PR #148 publish the
default-disabled local Memory M1 reference adapter in v0.14.0. V3-C resident
automation remains later and separately gated. V3-B exposes a provider-neutral
optional context seam, while M0 and M1 add separate operation, qualification,
and SQLite/FTS5 reference families without changing V2b or V3 authority. See the
[V3-B and Agent Memory roadmap spec](docs/loops/issue-135/roadmap-spec.md).

This is not a general prompt collection. It is a curated set of public, reusable workflow contracts for open source and team repositories.

## Who It Is For

- Open source maintainers who want Codex to help with routine repo maintenance.
- Teams using Codex CLI or Codex Desktop for implementation, review, and merge readiness.
- Contributors who need explicit human gates before destructive actions, pushes, releases, or merges.
- Early adopters who want reusable skills instead of one-off prompts.

## Quick Start

Inspect available install groups:

```bash
./install.sh list
```

Install CLI-compatible review workflows to get the normal `code-review` and `docs-review` entry points:

```bash
./install.sh install codex-review-workflow
```

Install CLI-compatible loop, implementation, and delivery workflows when you want Codex to keep a bounded objective moving through planning, implementation, verification, review, documentation sync, continuation, and formal gates:

```bash
./install.sh install codex-delivery-workflow
```

Install the CLI-only live session handoff adapter separately. This group
depends on the shared delivery workflow but does not alter Desktop packaging:

```bash
./install.sh install codex-cli-session-handoff
```

Loop Engineering V2a custom-agent profiles are a separate opt-in because they
write local runtime configuration. Inspect the inventory and mapping metadata,
then install only when wanted:

```bash
./install.sh manifest | rg codex-agent-profiles
sed -n '1,240p' skills/loop-engineering/references/agent-profile-registry.json
./scripts/project-python scripts/validate-agent-profiles.py
```

The profile group is excluded from `--all`. Set
`CODEX_CUSTOM_AGENTS_DIR=/trusted/project/.codex/agents` together with
`CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES` for explicit trusted-project
adoption. Shared skills do not choose a permanently current model; runtime
profiles are replaceable and must be preflighted.

Create a runtime-facts JSON file from the active public runtime/model surface;
do not inspect Desktop databases, sessions, logs, auth, caches, or private state.
Omit unknown model fields instead of guessing:

```json
{
  "custom_agent_surface": "available",
  "parent_sandbox_mode": "workspace-write",
  "available_models": ["replace-with-a-model-reported-by-this-runtime"],
  "reasoning_efforts": {
    "replace-with-a-model-reported-by-this-runtime": ["medium"]
  },
  "compatible_profiles": {},
  "parent_default": {
    "available": true,
    "capability_classes": ["balanced-worker"],
    "capability_tiers": {"balanced-worker": ["everyday"]}
  },
  "sequential": {
    "available": true,
    "capability_classes": ["balanced-worker"],
    "capability_tiers": {"balanced-worker": ["everyday"]}
  }
}
```

`parent_sandbox_mode` is current-session evidence from the active public
runtime/configuration. A `workspace-write` worker profile is usable only when
the parent sandbox is at least `workspace-write`; otherwise routing falls back
without activating that profile. Read-only profiles cannot widen the supported
profile sandbox and may remain usable when the parent value is unknown.
Version 2 parent/default and sequential fallbacks require both
`capability_classes` and `capability_tiers`; version 1 route inputs retain their
legacy fallback interpretation.

Preflight each role before installation. Scan both the destination root and the
other applicable configuration layer so an alias filename with the same agent
`name` is still detected. For user-level adoption from a trusted project:

```bash
./scripts/project-python scripts/validate-agent-profiles.py preflight \
  --role loop_v2a_balanced_worker \
  --runtime-facts /path/to/runtime-facts.json \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents
./install.sh install codex-agent-profiles
```

For project-scoped adoption, scan the project destination and the user layer,
then install with the same explicit target:

```bash
./scripts/project-python scripts/validate-agent-profiles.py preflight \
  --role loop_v2a_balanced_worker \
  --runtime-facts /path/to/runtime-facts.json \
  --destination-root /trusted/project/.codex/agents \
  --agent-root ~/.codex/agents
CODEX_CUSTOM_AGENTS_DIR=/trusted/project/.codex/agents \
CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES \
./install.sh install codex-agent-profiles
```

The collision preflight checks TOML `name` identities across those roots. For
install and update, the installer first validates the repository profile
sources against the canonical installed-skill registry, then preflights all
eight profile destinations before changing any dependency skill, template, or
profile. Dependency installation retains the existing installer sync behavior;
the all-profile preflight prevents a profile collision from causing a partial
expanded-group update. It also protects profile paths from overwrite, symlink
traversal, and partial group mutation. After install, validate the
deployed directory and identify it explicitly
so byte-identical expected instances are distinguished from modified or
cross-root collisions:

```bash
python3 ~/.agents/skills/loop-engineering/scripts/profile_preflight.py \
  --profile-dir ~/.codex/agents \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents
python3 ~/.agents/skills/loop-engineering/scripts/profile_preflight.py preflight \
  --profile-dir ~/.codex/agents \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents \
  --role loop_v2a_balanced_worker \
  --runtime-facts /path/to/runtime-facts.json
```

When `CODEX_DEV_SKILLS_TARGET=legacy` selects the compatibility skill root,
replace `~/.agents/skills` above with `~/.codex/skills`. A non-empty
`compatible_profiles` runtime fact must contain structured validated evidence
(`name`, absolute regular TOML path, capability class and tier,
config/model/reasoning booleans, expected sandbox,
allowed workflow scope, and profile digest),
not a bare profile name. Preflight exits `0` for `ready` or `fallback-safe`, `2` for a required
`human-gate`, and `1` for invalid input. Its JSON distinguishes `ready`,
`unknown`, `unavailable`, `sandbox-constraint-unknown-or-widening`, and
`custom-surface-unavailable`; a safe fallback is
not a claim that the requested model/profile is available.

The production `loopctl.py agent-route` command reruns this preflight and only
selects a custom-agent profile when the matching TOML is actually present in
the declared destination with the expected digest. Pre-install `ready` means
the source is adoptable; it does not claim the role is already installed. The
route document must point to the canonical registry shipped with the installed
skill. Runtime/model facts are separate current-session evidence and are
required on the command line:

```bash
python3 <skill-dir>/scripts/loopctl.py agent-route <decision-input.yaml> \
  --runtime-facts /path/to/current-runtime-facts.json
```

Integrate a worker receipt only after reading the current Git checkout, worker
artifacts, main-agent verification artifacts, and selected profile from their
trusted roots. The assignment freshness flag is a current-session assertion,
not repository data:

```bash
python3 <skill-dir>/scripts/loopctl.py agent-integrate <receipt.yaml> \
  --repo-root /path/to/current/repository \
  --artifact-root /path/to/worker-output \
  --verification-root /path/to/main-agent-verification \
  --assignment-fresh \
  --profile-path /path/to/selected-custom-profile.toml
```

Omit `--profile-path` only when the route receipt records a parent/default or
sequential fallback rather than a selected custom profile. Integration rejects
same-commit branch switches, stale Git revisions, missing or symlinked files,
worker and verification digest mismatches, alternate profiles, and
self-attested current-state fields in the receipt document.

Route contract version 2 preserves the four workflow capability classes and
adds ordered cost-aware tiers: Luna low for mechanical read-only work, Terra
low for exploration, Terra medium for routine implementation, Terra high for
complex bounded implementation, Sol medium for multi-trigger advanced bounded
implementation, Sol high for deep/security review, and Sol xhigh for narrowly
selected exceptional research. Terra xhigh and Luna max remain eval-only
candidates rather than installed defaults. Exact model and reasoning
availability remains current-session runtime evidence. Selection uses the
lowest sufficient same-class tier, never alphabetical profile order, and never
allows a lower tier to satisfy a higher-tier route silently.

The `loop_v2a_` filename and role namespace identifies the V2a heterogeneous
agent-routing contract; it is not the current repository release or V3 program
version. Renaming installed profiles requires a separately reviewed migration
with aliases, collision handling, installer state migration, and a documented
compatibility window.

Rollback user-level adoption only after reviewing local differences:

```bash
./install.sh diff codex-agent-profiles
./install.sh uninstall codex-agent-profiles --yes
```

For project-scoped rollback, use the same target variables used for install:

```bash
CODEX_CUSTOM_AGENTS_DIR=/trusted/project/.codex/agents \
CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES \
./install.sh diff codex-agent-profiles
CODEX_CUSTOM_AGENTS_DIR=/trusted/project/.codex/agents \
CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES \
./install.sh uninstall codex-agent-profiles --yes
```

Uninstall refuses modified profiles and removes nothing from the group until
all installed profile files pass its pre-delete check. Preserve and reconcile
local edits before retrying. A forced update stores each replaced skill,
template, or profile in a deterministic managed backup slot under
`${XDG_STATE_HOME:-$HOME/.local/state}/codex-dev-skills/backups/v1/`, outside
both Codex skill discovery roots. Slots are separated by a digest of the
canonical target root and by artifact kind; an existing slot blocks the whole
forced update before mutation rather than being overwritten. The installer
also fails closed when a backup or destination boundary is unsafe or when a
same-device rename cannot be guaranteed. To restore after a failed replacement,
use the reported managed backup location only after reviewing it and the target.
When rollback succeeds, the original is restored; if any restoration step emits
`CRITICAL`, preserve all reported locations for manual recovery rather than
assuming a no-partial-mutation outcome.

Before an `install` or non-force `update` mutates a selected discovery target,
the installer validates its state and receipt boundary. If that boundary is
unsafe, selected skills, templates, and agent profiles remain unchanged. This
is a bounded preflight guarantee, not unconditional atomicity for disk-full,
hostile same-UID interference, or every other runtime failure.
It rejects multiply linked regular target-tree files and receipts in the
relevant preflight. A force transaction additionally rejects multiply linked
sources and staged payloads. For an existing receipt it also performs a no-write append open
(with final-symlink protection where the platform provides it) and verifies the
opened descriptor's identity. Read-only, immutable, or append-only receipts
therefore fail closed. It never silently repairs a link count, file flag, or
receipt permission.
On Linux, immutable/append-only inspection uses the filesystem flag ioctl; an
inspection error, including an unsupported filesystem or special ABI, also
fails closed rather than degrading to open/fstat-only validation.

The managed transaction lock coordinates only cooperating installer processes
that resolve to the same canonical `XDG_STATE_HOME` managed-state namespace.
For a forced update, it is acquired only after complete filesystem and profile
input preflight; the locked apply phase rechecks affected identities and backup
slots before replacement.
Different state roots targeting the same authorized custom destination do not
share that lock; apply-time identity checks fail closed on ordinary detected
drift, but do not provide process isolation. Use OS/account isolation for a
hostile same-UID process. Within the supported cooperating model, a managed
backup slot is never silently overwritten.
Removing the profiles leaves V1 shared/sequential semantics available.

`codex-review-workflow`, `codex-delivery-workflow`, and
`codex-cli-session-handoff` install their shared dependencies automatically.
Install `shared-review-gates` directly only when you want the formal gate
adapters and orchestration templates without the review primitives.

Use the installed skills in Codex by name, for example:

```text
Use loop-engineering for issue #123 and keep the bounded objective moving until PR readiness or the next human gate.
Use implementation-slice to make this focused parser fix and run the targeted tests.
Use code-review on the current working tree.
Use docs-review for the docs-only changes in this branch.
Use milestone-continuation for MVP1.
Use merge-review for main..HEAD.
Use merge-review-deep for the release-sensitive main..HEAD diff.
Use merge-readiness-gate before PR handoff for main..HEAD. Treat the result as gate evidence only; do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

For Codex Desktop delegated delivery, install the Desktop group only when that workflow is intentional:

```bash
./install.sh install desktop-delivery-workflow
```

## How Projects Use These Skills

These skills work best when the target repository keeps durable project context in files that Codex can read before editing: repo-level `AGENTS.md`, project specs, implementation plans, review templates, and policy files.

The workflows are not limited to single task-id execution. When scope is clear, they can advance a bounded milestone slice, such as one MVP capability area, through discovery, planning, implementation, verification, review, documentation sync, and PR readiness.

Global Codex guidance adds useful baseline safety, while repo-level files define the project-specific source of truth. See `docs/usage-model.md` for the recommended project artifacts, delivery scope, and instruction layering model.

For adoption examples that pair well with this repository:

- [examples/global-codex-profile.md](examples/global-codex-profile.md) shows a reusable user-level baseline for `~/.codex/AGENTS.md`.
- [examples/project-agents-overlay.md](examples/project-agents-overlay.md) shows how a repository can layer project-specific rules without weakening global safeguards.
- [examples/project-workflow-overlay.md](examples/project-workflow-overlay.md) shows a compact project workflow overlay for delegated delivery, review closure, PR readiness, and release/tag gates.

## Usage Examples

These examples are written as prompts you can give to Codex after installing the relevant skill group.

### Focused Implementation

Use `implementation-slice` when the desired change is clear and should stay small:

```text
Use implementation-slice to add validation for empty config values.
Read the existing parser tests first, keep the change scoped, run the smallest relevant test command, and do not commit.
```

Codex should inspect repo instructions and current git state, edit only the needed files, run focused verification, inspect the diff, and report residual risk.

### Choosing An Entry Point

For a compact first-time decision guide, see [docs/skill-selection-guide.md](docs/skill-selection-guide.md).
It also explains when to choose routine review versus deep review for code, docs, and merge readiness work.

Use the smallest entry point that matches the request:

- `implementation-slice` for one clear coding task.
- `planning` when the next action or DoD needs to be defined before editing.
- `code-review` for ordinary read-only review of code or mixed diffs.
- `loop-engineering` when Codex should own the repeated bootstrap, route, act, verify, review, continue, handoff, or stop cycle for a clear bounded objective.
- `project-orchestrator` when Codex should classify the task, choose the next safe action, or decide whether to continue, hand off, review, or stop.
- `project-delivery` when the objective is larger than one task but still bounded.
- `milestone-continuation` when a bounded milestone should be checked and advanced across repeated invocations until complete or blocked by a human gate.
- `cli-session-handoff` only after shared orchestration has selected a bounded
  handoff and the user explicitly authorizes one new, resumed, forked,
  dashboard, or queued-message CLI session action.

`loop-engineering` is a thin entrypoint over the existing phase skills. It should classify the current state, route to the smallest suitable workflow, verify evidence, and stop at human gates. It does not replace focused implementation, review primitives, formal gates, milestone continuation, task continuation, shared subagents, or Desktop user-owned task/thread/worktree controls.

If `project-orchestrator` receives a single clear implementation task, it should route to `implementation-slice` semantics and avoid unnecessary project-level planning.

For automated review closure, let `project-orchestrator` or `project-delivery` compose the primitive shared workflows dynamically. A user or repo policy may set the maximum number of review/fix rounds; the default is 2.
When work is still incomplete at that threshold, run context-health assessment;
do not automatically replace the task. See
[Context Continuity And Fresh-Context Rollover](docs/context-continuity.md).

### CLI And Desktop Entry Paths

Codex CLI enters the shared layer directly through skills such as
`loop-engineering`, `project-delivery`, `project-orchestrator`, and the review
primitives. CLI `/agent` exposes shared subagent threads.
User-facing CLI session controls such as `/new`, `/fork`, `/resume`, and
`/archive` manage saved CLI sessions; they are not aliases for Desktop
`create_thread` callables.

CLI `/plugins` opens the universal plugin browser, `/import` imports supported
setup from another agent, and `/memories` controls local memory use for the
current chat. These are runtime configuration or personalization controls, not
`cli-session-handoff` operations. Imports leave existing setup in place, so
review imported skills/plugins for duplicate names before adding this pack
through another distribution path.

After shared orchestration selects a bounded handoff,
`cli-session-handoff` may use the documented stable
`codex exec --json`, `codex exec resume <SESSION_ID> --json`, or
`codex exec fork <SESSION_ID> --json` surface. The
adapter requires one exact authorization, a clean canonical Git worktree,
matching expected HEAD, an explicit read-only or workspace-write sandbox, and
a fixed no-publication/no-recursion prompt boundary. The child runs in a
disposable private clone; an authorized write result is transferred as a
bounded patch only after the original clean worktree is rechecked. It captures
only a bounded receipt and replaces child-summary text with a fixed omission
marker. It does not use Desktop identifiers, app-server,
private session files, or child output as repository completion evidence.
For a long-running interactive task that needs a new chat while preserving
saved history and an existing checkout/worktree, the adapter may instead
prepare the public `codex fork <SESSION_ID>` command with an exact UUID and an
explicit `tui.resume_cwd` current/session choice. That is a manual interactive
handoff; the private-clone executor does not automate it.

CLI 0.149 also exposes `codex agents` and `codex queue`. Treat `codex agents`
as an interactive CLI control plane: observation is coordination evidence, and
start/open/rename/stop actions each require exact mutation authority. Prepare
`codex queue` manually only with a canonical session UUID and one bounded,
nonsensitive message represented as one argv token without shell interpolation;
queue acceptance proves dispatch/wakeup only. Neither
command enters the private-clone executor or becomes shared completion
authority. `codex doctor --json` is redacted diagnostic evidence only.

Use `/app` in an interactive CLI session, or `codex app <path>` from the shell,
when the user intentionally wants to continue in the ChatGPT desktop app. Once
there, `desktop-project-delivery` may add Desktop task, thread, worktree,
handoff, or scheduling controls while still routing execution, verification,
review, and completion through the shared layer. A surface transition changes
the runtime adapter, not the objective, authority, or completion contract.

### Routine Code Review

Use `code-review` when you want read-only feedback on a working tree, branch, or patch. This is the normal user-facing entry point for code review:

```text
Use code-review on the current working tree.
Prioritize correctness bugs, regressions, missing tests, and contract risks. Stay read-only.
```

Expected output starts with findings, then questions and re-runnable verification commands.

Use `code-review-gate` only when a workflow needs a formal gate before commit readiness, PR readiness, or merge readiness.
The gate is a thin adapter: it routes routine diffs to `code-review`, escalates high-risk diffs to `code-review-deep`, records evidence, and blocks on unresolved MUST-FIX findings.

### Routine Documentation Review

Use `docs-review` when you want read-only feedback on docs-only or docs-dominant changes. This is the normal user-facing entry point for documentation review:

```text
Use docs-review on the current working tree.
Check accuracy, stale names or links, unsupported claims, and confusing structure. Stay read-only.
```

Use `docs-review-gate` only when a workflow needs a formal documentation gate before commit readiness, PR readiness, or merge readiness.
The gate is a thin adapter: it runs `docs-review`, records evidence, checks for private paths, local runtime state, unsupported claims, and stale instructions, then blocks on unresolved MUST-FIX findings.

### Orchestrated Review Closure

Use `project-orchestrator` when Codex should implement, review, fix blockers, and re-review until it reaches a human gate:

```text
Use project-orchestrator to implement the requested docs validation improvement.
Run at most two review/fix rounds. Stop before commit, push, PR creation, release, platform comments, review submissions, or any external write.
```

The orchestrator uses the smallest shared primitives that fit the current state: `implementation-slice`, `docs-update`, `code-review`, `code-review-deep`, `docs-review`, and merge-readiness workflows when applicable. It uses `code-review-gate` or `docs-review-gate` only for formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decisions. This keeps the same closure model usable in Codex CLI and Codex Desktop.

### Loop Engineering

Use `loop-engineering` when the objective is clear and Codex should keep selecting the next safe workflow until the objective is complete or a human gate is reached:

```text
Use loop-engineering for issue #123.
Read the issue, repo instructions, implementation plan, task manifest, review evidence, and current git state before editing.
Continue through planning, implementation, verification, review, docs sync, continuation, and PR readiness while the objective and DoD remain clear.
Stop before destructive actions, external writes, commit, push, PR creation, merge, release, deploy, platform comments, review submissions, material risk, or unclear source of truth unless I explicitly authorize the exact action.
```

The loop entrypoint repeatedly bootstraps from durable repository files,
executes the production route and transition contract, verifies evidence, and
decides whether to continue, prepare a handoff, stop, or complete. When the user
explicitly requests a native goal, Goal mode controls progress without widening
permissions or replacing repository completion evidence. Independent bounded
packets may use shared subagents in current Desktop, CLI, and IDE runtimes. See
[docs/loop-engineering.md](docs/loop-engineering.md),
[workflows/loop-engineering-workflow.md](workflows/loop-engineering-workflow.md),
and [native runtime capabilities](docs/native-runtime-capabilities.md).

The active skill invokes `loopctl.py decide` with a structured decision input
and an explicit trusted `--protected-history-sha256 <verified-digest-or-none>`;
the prose route table explains the result but does not replace the executable
routing function.

For long review/fix loops, use the separate read-only continuity assessment:

```bash
./scripts/project-python skills/loop-engineering/scripts/loopctl.py \
  context-health /path/to/context-health.yaml
./scripts/project-python scripts/eval-context-continuity.py
```

The five outcomes are continue, reground, parallel bounded subagent delegation,
fresh rollover preparation, and a human gate. Fork keeps completed conversation
history; fresh rollover starts only from the durable checkpoint. The source
stops writing before the destination becomes the sole delivery owner. Stable
lineage makes exact replay a no-op and rejects recursive rollover without
material progress. Graph lineage remains advisory and cannot create a task,
choose a writer, or prove completion.

The bundled comparison suite is provenance-labelled synthetic contract data:
it verifies fail-closed routing and bootstrap-inclusive accounting, not an
empirical A/B claim. The bounded v0.17.0 same-objective empirical pair is
recorded in
[`docs/loops/issue-165/paired-run-evidence.md`](docs/loops/issue-165/paired-run-evidence.md)
with raw-result fields, artifact digests, a predeclared rubric, and explicit
order/cache/generalization limits. It supported the v0.17.0 release candidate
without turning one pair into a universal performance claim.

When a loop needs durable memory across repeated invocations, workers, worktrees,
or handoffs, add a repo-owned loop ledger:

```text
Use loop-engineering for issue #123.
If the repo does not already have loop state, create docs/loops/issue-123/ from the loop spec, loop-state-ledger, task manifest, current-task-summary, iteration-report, and task-claim/lease templates.
Treat stable task definitions, validated events, the materialized ledger,
fenced claims, and verification/review evidence according to their documented
authority boundaries.
External memory may be used only as cache or coordination unless this repo explicitly defines a stronger reviewed authority model.
```

V2b makes that boundary executable without requiring a backend:

```bash
./scripts/project-python skills/loop-engineering/scripts/memoryctl.py --help
./scripts/project-python skills/loop-engineering/scripts/memoryctl.py validate <document.json>
./scripts/project-python skills/loop-engineering/scripts/memoryctl.py decide-retrieval <decision.json> \
  --trusted-conformance-receipts <current-session-trusted-receipts.json> \
  --trusted-source-digests <current-repository-source-digests.json>
./scripts/project-python skills/loop-engineering/scripts/memoryctl.py decide-write <candidate.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
./scripts/project-python skills/loop-engineering/scripts/memoryctl.py conformance <transcript.json> \
  --trusted-source-digests <current-repository-source-digests.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
./scripts/project-python scripts/eval-memory-contract.py
```

The caller-owned JSON inputs use exact shapes: trusted conformance receipts are
`{"<adapter-id>":{"receipt_digest":"<sha256>","adapter_fingerprint":"<sha256>"}}`;
trusted sources are `{"<repository-relative-path>":"<sha256>"}`; trusted
acceptance evidence is `{"receipt_digests":["<sha256>"]}`. These files are
control-plane evidence and must not be copied from the adapter transcript.

With no adapter, or with an unavailable, partial, unsupported, incompatible, or
untrusted adapter, the loop safely continues with V1/V2a and no memory. See the
[external memory contract](docs/external-memory-contract.md).

The Agent Memory M0 readiness contract and the thin, default-disabled,
local/manual/CI-only SQLite/FTS5 M1 safety/conformance baseline were published
in v0.14.0 through Issues #145 and #147. M1 remains optional and inactive: its
publication is not activation, promotion, or efficacy evidence, and missing or
drifted FTS5 support fails closed to no memory. M2 and V3-C remain behind new
evidence and explicit human decisions; PlugMem and Mem0 remain excluded.

V2d-A adds independently usable operational evidence without a backend:

```bash
./scripts/project-python skills/loop-engineering/scripts/evidencectl.py --help
./scripts/project-python skills/loop-engineering/scripts/evidencectl.py validate <document.json>
./scripts/project-python skills/loop-engineering/scripts/evidencectl.py validate-set <document.json>...
./scripts/project-python scripts/eval-operational-evidence.py
```

The validator accepts only strict `loop-operational-evidence/v0` JSON, checks
canonical digests, bounded failure taxonomy, redacted environment fields,
typed artifact references, and cross-document relationships, and always
preserves false authorization/completion/promotion invariants. It is offline,
does not dereference artifacts, and does not mutate a ledger or external
system. See the
[operational evidence contract](docs/operational-evidence-contract.md).

V2d-B adds independently usable improvement lineage and deterministic
projections without changing V2d-A:

```bash
./scripts/project-python skills/loop-engineering/scripts/improvementctl.py --help
./scripts/project-python skills/loop-engineering/scripts/improvementctl.py validate-set \
  <record.json>... --evidence <v2d-a-document.json>...
./scripts/project-python skills/loop-engineering/scripts/improvementctl.py project-human \
  <record.json>... --evidence <v2d-a-document.json>...
./scripts/project-python skills/loop-engineering/scripts/improvementctl.py project-graph \
  <record.json>... --evidence <v2d-a-document.json>...
./scripts/project-python scripts/eval-improvement-lineage.py
```

The human and typed graph outputs are source-derived, regenerable, and
non-authoritative. The optional Obsidian profile is declarative only; no vault
or graph runtime is installed or mutated. See the
[improvement lineage contract](docs/improvement-lineage-contract.md).

V3-A adds a proposal-only evidence-to-proposal layer downstream of unchanged
V2d-A/B:

```bash
./scripts/project-python skills/loop-engineering/scripts/proposalctl.py --help
./scripts/project-python skills/loop-engineering/scripts/proposalctl.py generate \
  --record <record.json> --evidence <v2d-a-document.json>
./scripts/project-python skills/loop-engineering/scripts/proposalctl.py validate \
  <proposal-set.json> \
  --record <record.json> --evidence <v2d-a-document.json>
./scripts/project-python scripts/eval-improvement-proposal.py
```

Generation reruns strict V2d validation, derives fixed integer scores,
suppresses exact structured duplicates, and preserves full lineage and role
separation. Output intents describe only patch, branch, artifact, or draft-PR
suggestions. The CLI cannot apply, commit, push, create a PR, approve, activate,
promote, merge, release, deploy, or write an external system. See the
[improvement proposal contract](docs/improvement-proposal-contract.md).

V3-B adds isolated candidate evaluation downstream of unchanged V2d-A/B and
V3-A and is released in **v0.13.0**:

```bash
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py --help
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py evaluate \
  <evaluation-input.json> --proposal-set <proposal-set.json> \
  --record <record.json> --evidence <v2d-a-document.json>
./scripts/project-python skills/loop-engineering/scripts/evaluationctl.py verify \
  <evaluation-result.json> <evaluation-input.json> \
  --proposal-set <proposal-set.json> --record <record.json> \
  --evidence <v2d-a-document.json>
./scripts/project-python scripts/eval-candidate-evaluation.py
```

The closed evaluator compares bounded synthetic observations under one fixed
policy and exact public environment equivalence; it never runs arbitrary
candidate code. Independent replay must match exactly. A promotion packet can
only report `qualified-awaiting-human-decision` or `not-qualified` and cannot
apply, approve, commit, push, create a PR, promote, merge, release, deploy,
activate, or write externally. `memory-off` is the default complete path.
Optional V2b-validated `synthetic-advisory` context is digest-bound data only
and cannot change policy, completion, authority, or promotion. No Memory M1/M2
backend, SQLite/FTS5, PlugMem, Mem0, provider/MCP integration, or V3-C is
included. See the
[candidate evaluation contract](docs/candidate-evaluation-contract.md).

Memory M0 is an additive offline readiness layer owned by Issue #145. It keeps
V2b and V3-B unchanged and adds no backend:

```bash
./scripts/project-python skills/loop-engineering/scripts/operationctl.py --help
./scripts/project-python skills/loop-engineering/scripts/qualificationctl.py --help
./scripts/project-python scripts/eval-memory-operation.py
./scripts/project-python scripts/eval-memory-qualification.py
```

`loop-memory-operation/v0` separates V2b eligibility, caller-owned exact
operation authority, authorized-request composition, future adapter execution,
atomic execution receipt, and independent acceptance. Requests require
caller-accepted trusted-time evidence and full-chain revalidation.
`loop-memory-qualification/v0` is a safety/conformance-only paired wrapper
around unchanged V3-B outputs because released V3-B cannot represent a
memory-off/on pair; its exact tuple includes the verifier and a scope-bound M1
receipt document. Memory-off remains complete, default, and zero backend/
filesystem touch. Physical purge, automatic migration, efficacy claims,
SQLite/FTS5 execution, schema/database creation, persistence, providers/MCP,
PlugMem/Mem0, automatic recall/write, and V3-C remain excluded. M0 is included
in **v0.14.0** and remains a non-backend authority and qualification layer. See the
[operation contract](docs/memory-operation-contract.md) and
[qualification contract](docs/memory-qualification-contract.md).

Memory M1 is an additive reference-adapter candidate owned by Issue #147. It
adds the explicit `loop-memory-sqlite/v0` local/manual/CI-only SQLite/FTS5
adapter without importing it from memory-off or any released V2/V3/M0 module:

```bash
./scripts/project-python skills/loop-engineering/scripts/sqlitectl.py probe
./scripts/project-python scripts/eval-memory-sqlite.py
```

The adapter requires an explicit approved machine-local state root, an exact
isolated FTS5 behavior probe and platform/build/tokenizer/schema fingerprint,
bounded structured query terms, parameterized SQL, complete M0 authority
reconstruction, and atomic logical state plus receipt. Extension loading, raw
SQL/FTS expressions, automatic migration/repair, physical purge, providers/
MCP, services, network, automatic recall/write, cross-host use, private data,
and efficacy claims remain excluded. The adapter is default-disabled and does
not install, activate, or promote itself. The reviewed reference baseline is
released in **v0.14.0**; publication does not establish efficacy or authorize
activation. See the
[M1 reference contract](docs/memory-sqlite-reference-contract.md).

V2c-A adds a default-disabled, version-gated GitNexus driver boundary. The live
macOS qualification covers GitNexus `1.6.9`, a runtime-produced qualification
fingerprint, and metadata schema `5`. Human-oriented `status` and `list` output is never parsed.
Although qualification observed a direct JSON query surface, this baseline
deliberately declares `read_query` and every write/upsert/invalidate/tombstone/
delete operation unsupported. It therefore cannot manufacture memory context
or report a successful backend mutation.

The runtime control-plane flow is:

1. **Qualify:** discover an explicitly configured executable, apply the regular
   file or explicit symlink policy, and bind its exact version, entry bytes,
   every script interpreter (when applicable), observed analyze flags, schema,
   and capability policy. Any drift requires qualification and V2b
   conformance again.
2. **Inspect status:** derive repository identity and freshness from the exact
   Git top-level with a real local `.git` marker (including reciprocal
   linked-worktree binding) and a verified commit-object HEAD;
   repository-local `core.worktree` cannot substitute an enclosing repository
   identity,
   a complete tracked snapshot, strict version-gated metadata, and the
   `gitnexus-index-identity/v1` sidecar. The sidecar binds the exact checkout,
   branch/detached state, HEAD, complete relevant content digest, dirty state,
   tool qualification, analyze configuration, indexed time, and observation
   time. Treat stale,
   dirty, missing, partial, unsupported, incompatible, corrupt, or unknown state
   as no memory.
3. **Enable:** opt in through machine-local runtime configuration. Executable
   paths, `GITNEXUS_HOME`, registries, indexes, and credentials never belong in
   repository files.
4. **Refresh when explicitly requested:** use only `analyze --index-only` with
   an expected HEAD, a unique isolated alias and `GITNEXUS_HOME`, offline
   extension policy, bounded environment, timeout, lock, replacement-object
   neutralization, and complete before/after worktree plus Git-administration
   checks. Automatic refresh remains disabled.
5. **Disable or roll back:** remove the runtime opt-in and ignore adapter
   receipts. Continue with repo-owned state; do not delete, reset, restore, or
   rewrite repository files or user indexes as part of rollback.

For maintainers running GitNexus directly in this repository, the tracked
`.gitnexusrc` sets `analyze.indexOnly` to `true`. This makes a bare
`gitnexus analyze` index-only by default and prevents GitNexus from generating
or rewriting repository instruction and provider-skill files. The repository
validator requires that exact minimal setting; `--skip-agents-md` is not an
equivalent substitute because it can still permit other generated files. CLI
and controller paths still pass `--index-only` explicitly so their invocation
evidence remains self-contained rather than depending only on repository
defaults.

The supported operator entrypoint is the repo-owned module. It persists no
configuration and redacts machine-local paths from JSON output:

PR base/head evidence is a separate library-only artifact:
`gitnexus-pr-review-identity/v1`, produced by
`build_pr_review_identity()` from two clean committed snapshots in the same
canonical repository. It is not an operator command and has no persistence or
adoption path. A consumer must recompute it from live qualified inputs and
compare `pr_review_identity_digest`; a supplied serialized document alone is
never trusted and its authority invariants never satisfy review, gates, or
completion.

```bash
ADAPTER=skills/loop-engineering/scripts/gitnexus_adapter.py
./scripts/project-python "$ADAPTER" qualify \
  --executable "$GITNEXUS_EXECUTABLE" --allow-symlink \
  --node-executable "$GITNEXUS_NODE_EXECUTABLE" --allow-node-symlink \
  --package-root "$GITNEXUS_PACKAGE_ROOT" \
  --accepted-executable-sha256 "$GITNEXUS_EXECUTABLE_SHA256" \
  --accepted-runtime-sha256 "$GITNEXUS_NODE_SHA256" \
  --accepted-package-sha256 "$GITNEXUS_PACKAGE_SHA256"

./scripts/project-python "$ADAPTER" status \
  --executable "$GITNEXUS_EXECUTABLE" --allow-symlink \
  --node-executable "$GITNEXUS_NODE_EXECUTABLE" --allow-node-symlink \
  --package-root "$GITNEXUS_PACKAGE_ROOT" \
  --accepted-executable-sha256 "$GITNEXUS_EXECUTABLE_SHA256" \
  --accepted-runtime-sha256 "$GITNEXUS_NODE_SHA256" \
  --accepted-package-sha256 "$GITNEXUS_PACKAGE_SHA256" \
  --git-executable "$GIT_EXECUTABLE" \
  --repo-root "$CANONICAL_REPO_ROOT" \
  --repository-id "$CANONICAL_REPOSITORY_ID" \
  --expected-remote "$EXPECTED_ORIGIN"
```

`status` is disabled by default. Add `--enabled` only to opt in for that one
status/handshake invocation; the current baseline still falls back to no memory
because `read_query` is unsupported. An explicit refresh additionally requires
a new, empty, pre-created machine-local home and two independent opt-in flags:

```bash
./scripts/project-python "$ADAPTER" refresh \
  --executable "$GITNEXUS_EXECUTABLE" --allow-symlink \
  --node-executable "$GITNEXUS_NODE_EXECUTABLE" --allow-node-symlink \
  --package-root "$GITNEXUS_PACKAGE_ROOT" \
  --accepted-executable-sha256 "$GITNEXUS_EXECUTABLE_SHA256" \
  --accepted-runtime-sha256 "$GITNEXUS_NODE_SHA256" \
  --accepted-package-sha256 "$GITNEXUS_PACKAGE_SHA256" \
  --git-executable "$GIT_EXECUTABLE" \
  --repo-root "$CANONICAL_REPO_ROOT" \
  --repository-id "$CANONICAL_REPOSITORY_ID" \
  --expected-remote "$EXPECTED_ORIGIN" \
  --expected-head "$EXPECTED_HEAD" \
  --gitnexus-home "$EMPTY_ISOLATED_GITNEXUS_HOME" \
  --lock-directory "$MACHINE_LOCAL_LOCK_DIRECTORY" \
  --enabled --confirm-explicit-refresh

./scripts/project-python "$ADAPTER" disable
```

Standalone `qualify` and `status` qualification retain the 10-second default
and `1..300` standalone limit. A `refresh` first validates its existing
`--timeout-seconds` value (`1..3600`, 120 by default), creates one monotonic
deadline, and charges executable qualification, repository preflight,
controller execution, and postconditions to that same budget. The deadline is
never reset between phases; detected absolute-budget expiry is
`probe-deadline-expired` and no index is adopted. The analyze runner receives a
bounded slice that reserves time for postconditions; exhausting that slice
before the absolute deadline remains `refresh-timeout` and is also fail closed.
Auto-on-demand hooks use the configured refresh deadline in
the same way, while notify-only hooks retain standalone qualification limits.

`--executable` and the caller-owned accepted entry/package digests are mandatory
and never fall back to ambient `PATH` or tool self-report. `--package-root`
must be a canonical machine-local directory containing the resolved entry; its
complete descriptor-bound regular-file tree and contained direct relative file
symlinks are compared before the CLI runs and at every later use. Derive the
accepted digests from a separately trusted package installation manifest or an
explicitly approved local measurement; adapter output cannot promote its own
measurement into caller-owned trust. Every
script entry is launched only through a bound native interpreter and that
interpreter identity is included in the qualification fingerprint. When the
resolved GitNexus entry begins with exact `#!/usr/bin/env node` or
`#!/usr/bin/env -S node`, `--node-executable` and
`--accepted-runtime-sha256` are mandatory; an allowed absolute
shebang interpreter is resolved and fingerprinted independently. Unsupported
launcher syntax and script-on-script interpreters fail closed. Omit the Node
arguments only for a directly executable or allowed non-env-node entry. Resolve
any permitted symlink target during local setup and keep machine-local paths
and accepted digests outside repository files. The caller must regenerate the
accepted evidence and rerun qualification/conformance after any entry,
interpreter, package, version, or capability drift.

Repository identity helpers likewise ignore ambient `PATH`, Apple developer
tool selectors, dynamic-loader variables, and executable-path environment
variables. Omitting `--git-executable` uses the operating system's default
executable search path (`os.defpath`); a trusted operator or library caller may
instead supply an explicit absolute path. The regular, canonical, non-symlink
Git executable is bound before every use, and no machine-local value is
committed.

Status and refresh fail closed before worktree-reading Git commands when local
or enabled worktree configuration defines content filters, external config
includes, or an external attributes file. The refresh lock directory must
resolve outside the repository to a current-user-owned directory that is not
group/world writable; parent symlinks and symlinked or hard-linked lock files
are rejected. Refresh takes its cross-process advisory lock on a verified
descriptor (not a pathname), uses `flock`, and rechecks the descriptor identity
after acquisition. It always takes a deterministic, fixed-OS-temp per-user lock
for the canonical repository root before any optional configured-directory
lock; different `TMPDIR` values or `--lock-directory` arguments cannot create
parallel refresh lanes. This protects cooperating same-UID local processes; it is
not a distributed lock or a defense against a same-UID process that can modify
the machine-local control plane. The same verified lock directory also holds a
device/inode-keyed lock for the isolated home. The controller keeps that home
open by descriptor for the full refresh, checks emptiness after locking and
again immediately before the runner, and therefore rejects cooperating
cross-repository reuse of one home.

`disable` is stateless: the caller stops supplying `--enabled` and ignores prior
receipts. It does not delete indexes or rewrite repository/user configuration.

V2c-B adds an optional hook runner on top of that unchanged controller. Codex
currently has no native `post-commit` hook event, so the integration uses two
compensating checks:

- `SessionStart` checks freshness for `startup`, `resume`, `clear`, and
  `compact` sources;
- `PostToolUse` for `Bash` and `apply_patch` rechecks live Git state after
  repository activity and reports a commit/HEAD change without parsing or
  trusting the shell command, patch, or response.

The tool hook is not complete interception. A Git mutation performed through an
uncovered tool, another process, or another client may not trigger it;
`SessionStart` is the compensating check. Notify-only mode is the default. In
auto-on-demand mode, a clean stale or missing index may be refreshed only
through `RefreshController` with exact expected HEAD and all V2c-A checks.
Dirty worktrees, identity conflicts, corrupt metadata, failed qualification,
and unsafe paths remain notification-only or fail safe.

GN-FU-01 makes exactness stricter than commit equality. A clean qualified
refresh atomically writes `codex-index-identity.json` below the ignored
`.gitnexus/` derived-index root only after metadata postconditions pass. Later
status and hook checks recompute complete content, including untracked and
ignored paths, and require an exact sidecar match. Missing v1 evidence is
explicitly stale/advisory; dirty tracked, untracked, mixed, detached, or
content-drifted state cannot be reported as exact. Primary `main`, primary
issue branches, linked worktrees, and PR base/head pairs use distinct aliases
bound to checkout, HEAD, and content. Linked-worktree automatic refresh remains
unsupported, and a remote merge still has no local effect until primary
`main` advances locally.

Bind each machine-local hook config to one exact checkout root. A branch in the
primary project directory and a linked worktree have separate worktree identity
digests and must not share or overwrite one index alias. Linked-worktree
automatic refresh remains unqualified and reports that boundary without
touching the primary checkout's index. A remote PR/MR merge does not advance a
local checkout; update the primary checkout first, then let its next
`SessionStart` or completed `Bash`-matched shell/unified-exec event refresh the
clean merged HEAD.

The installer copies inactive examples to
`~/.codex/templates/hooks/gitnexus-v2c-b/`; it does not create or enable a
project hook. Review these sources before materializing machine-local values:

```bash
HOOK_RUNNER=skills/loop-engineering/scripts/gitnexus_hook.py
HOOK_TEMPLATE=templates/hooks/gitnexus-v2c-b/hooks.json.template
CONFIG_TEMPLATE=templates/hooks/gitnexus-v2c-b/config.json.template

./scripts/project-python "$HOOK_RUNNER" \
  --config /absolute/machine-local/gitnexus-v2c-b.json \
  --validate-config
```

Create the active configuration outside the repository as a current-user-owned
regular file that is not group/world writable. Replace every placeholder in
both templates, inspect any existing `.codex/hooks.json` instead of overwriting
it, and keep the active machine-specific hook definition untracked. Project
hooks load only for a trusted project and must be reviewed through `/hooks`
before they run.

To enable auto-on-demand refresh, change `mode` from `notify-only` to
`auto-on-demand` and replace `refresh: null` with:

```json
{
  "gitnexus_home_parent": "/absolute/secure/machine-local/isolated-homes",
  "lock_directory": "/absolute/secure/machine-local/locks",
  "timeout_seconds": 120
}
```

Both directories must already exist outside the repository and be owned by the
current user without group/world write permission. Each eligible refresh creates
a new `0700` isolated home below the configured parent because V2c-A requires a
fresh empty home. The hook does not automatically delete those derived homes;
inspect exact targets and retain or clean them through a separate explicit
operator action. A failed controller run also creates one repository-bound
`0600` `.codex-v2c-b-auto-disabled-<digest>.json` circuit-breaker marker in the
parent. Later hooks notify but do not retry until the operator inspects the
failure and explicitly clears that exact marker. Disable or remove the hook
definition to roll back without deleting the index or changing
V2c-A/no-backend behavior.

Refresh accepts only a clean, directly verifiable worktree boundary with no
tracked path below `.gitnexus/`—including case or normalization aliases that
are missing from the worktree and therefore cannot be compared with
`samefile()`—and a pre-existing `.git/info/exclude` entry for `.gitnexus/`.
Conservative Unicode-normalized, case-folded lexical equivalence rejects those
tracked aliases before the runner executes. It fails closed if GitNexus changes
tracked, untracked, ignored, or protected worktree content; any `.git`
administrative state; repository identity; or qualified metadata. Git probes
and descendants ignore replacement refs, disable repository-local fsmonitor,
hooks, and untracked-cache extensions, reject interactive credential prompts,
ignore system/global Git configuration, and use `GIT_NO_LAZY_FETCH=1` to
prevent implicit promisor remote/helper access. Probe output and time are
bounded. macOS arm64
has live qualification evidence;
Linux coverage in the repository remains deterministic fixture-based
portability evidence. The v0.16.1 release gate separately requires a bounded
released-artifact requalification on Rocky Linux 9.8; that external run does
not grant GitNexus authority or replace repository verification.

The complete-snapshot safety envelope supports at most 250,000 filesystem
entries, directory depth 256, and 512 MiB per regular file, all within the
configured total refresh deadline (120 seconds by default). A repository or
Git packfile outside those bounds is not partially indexed: refresh fails
closed before the runner or rejects adoption, and the operator must use the
no-memory path unless a later driver version is separately qualified for a
wider envelope.

See [docs/loop-state-ledger.md](docs/loop-state-ledger.md) for the repo-owned loop state contract.

### Bounded Milestone Slice

Use `project-delivery` when the objective is larger than a single task but still bounded:

```text
Use project-delivery to advance the MVP1 import-validation scope to PR readiness.
Read the repo plan and acceptance criteria first, split the work into safe slices, update docs if behavior changes, run review primitives and required formal gates, and stop before commit, push, PR creation, release, platform comments, or review submissions.
```

This pattern is useful when a maintainer wants Codex to carry a small capability area forward without granting authority to publish or merge.

Use `milestone-continuation` when a bounded milestone should keep advancing across repeated invocations:

```text
Use milestone-continuation for MVP1.
Every time this thread wakes up, read the milestone spec, task manifest, status docs, review evidence, and current git state.
If the current task is incomplete, continue it with the smallest safe action.
If it is complete, choose the next smallest ready task.
Continue until MVP1 is complete or a human gate is reached.
```

The skill defines what to do after each invocation. Runtime cadence, such as a Codex Desktop heartbeat every 5 or 10 minutes, is configured by the active runtime and is not hardcoded in the skill.

### Task Continuation

Use `task-continuation` when a larger bounded task needs the next safe unit of work and a prompt, task brief, continuation prompt, or sequential execution path:

```text
Use task-continuation to choose the next smallest safe task from the repo plan and status files.
Prepare a continuation prompt or task brief if continuation should move to another session or worker, but do not claim that a shared skill can open the session itself.
```

The skill prepares continuation artifacts from durable repository context.
Shared subagents can handle bounded packets when available; opening a separate
user-owned Desktop task or thread remains a runtime-specific control-plane
action.

### Codex CLI Session Handoff

Use `cli-session-handoff` only after `task-continuation` or another shared
orchestrator has already selected the task:

```text
Use cli-session-handoff for the already selected bounded task.
Start one clean Codex CLI session in the exact worktree and sandbox I authorize.
Do not commit, push, open pull requests, merge, perform platform writes, or dispatch another session.
Return the bounded handoff receipt; I will verify the worktree and child result separately.
```

The adapter uses prompt stdin so task text is not placed in process argv,
parses bounded public JSONL events, and supports exact-UUID resume and
non-interactive fork. A real start, resume, or fork is a runtime-state mutation
and requires explicit authority;
offline tests use controlled fake executables and create no Codex session.
The disposable private clone does not inherit a checkout's activated Python
environment. When the repository provides `scripts/project-python`, the child
must use it for Python dependency checks, scripts, evals, and tests; an
unavailable pinned environment blocks verification rather than authorizing a
fallback to bare system Python.
For same-task interactive continuation, it may prepare an exact-UUID
`codex fork` command that reuses the selected existing directory without
creating a Git worktree; executing that fork is also a runtime-state mutation,
while merely preparing the command is not. This manual path is not sent through
the executor.

### Merge Readiness

Use `merge-review` when you want the normal base-to-head merge quality and DoD review:

```text
Use merge-review for main..HEAD.
Check scope alignment, tests, docs, unresolved review findings, and residual risk. Stay read-only.
```

The result is review evidence. It does not grant authority to commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes.

Use `merge-review-deep` when the diff is high-risk, release-sensitive, or policy-required:

```text
Use merge-review-deep for main..HEAD.
Re-check closure evidence, rollback path, security/privacy, migration safety, and hidden regression risk. Stay read-only.
```

The deep result is still review evidence, not merge authorization.

After a PR exists, follow the
[exact-head Merge-Review contract](policies/exact-head-merge-review-contract.md).
Pre-commit review evidence may be reused when its revision and scope still
apply, but its verdict cannot replace PR-bound Merge Review. Merge readiness
requires exact repository/PR/base/head/merge-base/range identity, successful
hosted CI, closed findings, zero unresolved threads, and a platform-visible
receipt that was read back for the current head. Any relevant drift invalidates
the receipt.

Repositories that opt into platform enforcement also require the dedicated-App
`Exact-Head Merge Readiness` check. Its trusted default-branch collector binds
the live PR head, base/merge-base/range identity, upstream CI, findings,
threads, strict
JSON receipt digest, and check identity without executing untrusted PR code.
GitHub natively enforces live-head success, strict updates, and resolved
conversations; receipt and finding drift is reprojected after a relevant event
is processed rather than atomically with the Merge click. The check cannot
count itself as upstream CI. GitHub
App setup, ruleset mutation or activation, and merge remain separate human
gates; see [the hosted gate guide](docs/exact-head-merge-gate-app.md).

Every ready-for-review pull request must also contain a standalone closing
reference to an open Issue in this repository, for example:

```text
Closes #123
```

Draft pull requests may omit it while being prepared. The repository template
and read-only CI check implement
[the PR-to-Issue linkage policy](policies/pull-request-issue-linkage-policy.md).
A valid link provides traceability only; it does not replace verification,
formal review, human approval, merge authority, or completion evidence.

Use `merge-readiness-gate` only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval:

```text
Use merge-readiness-gate for main..HEAD.
Check the plan, diff, tests, and review evidence. Report READY, BLOCKED, or NEEDS HUMAN DECISION. Do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

The gate is a thin adapter and evidence-and-decision layer: it summarizes verification, review evidence, blocking decisions, residual risk, and the human approval boundary. It is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes. Before any authorized merge or platform-side mutation, repeat connector-first readback and confirm every exact-head receipt binding still matches and no blocker remains.

After a remediation, code review and Security Diff Scan may rerun over the
smallest affected boundary that proves closure, with an explicit rationale for
reused evidence. A changed PR head always receives a new complete base-to-head
Merge Review and platform receipt readback. Clean internal stages may advance
without an additional human stop when the next action is read-only or already
authorized.

### Codex Desktop Delegated Delivery

Use `desktop-project-delivery` when shared project delivery also needs Desktop
task, thread, worktree, or scheduling controls. Ordinary subagent delegation is
shared and does not require this Desktop adapter:

```text
Use desktop-project-delivery to prepare this feature for PR readiness.
Coordinate implementation and review, integrate the output, run verification, and stop for product ambiguity, destructive actions, external writes, or final merge approval.
```

CLI fallback: use `project-delivery`, `project-orchestrator`, prompts, task briefs, continuation prompts, or a sequential execution path; run review primitives after the fallback produces changed files or evidence; and use formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates. See [docs/runtime-compatibility.md](docs/runtime-compatibility.md) for the Desktop-to-CLI fallback mapping.

Use `desktop-thread-delegation` only after shared orchestration has selected a
bounded handoff and the user explicitly wants a separate Desktop task or
thread:

```text
Use desktop-thread-delegation for the bounded task already selected by shared orchestration.
Choose only whether that selected task continues here or moves to a new Desktop task/thread/worktree.
If a new Desktop task is appropriate, prepare the handoff prompt and ask before opening it.
If thread creation is unavailable, return the prompt for me to paste manually.
Keep review, commit, PR, merge, platform comments, and other external writes behind explicit authorization.
```

The main thread remains responsible for integrating returned work, checking the diff, running verification, and enforcing review or merge gates.

The active runtime contract is [docs/native-runtime-capabilities.md](docs/native-runtime-capabilities.md).
The latest maintained comparison is
[Codex runtime compatibility evidence (2026-08-28)](docs/codex-runtime-compatibility-evidence-2026-08-28.md).
It records that `codex mcp-server`, the command that exposed Codex itself as an
MCP server, is deprecated but not removed in observed standalone CLI 0.150.1.
It also records Desktop 26.820.80927 and its bundled CLI 0.150.0-alpha.8 as
separate point-in-time observations rather than one global version. This does
not deprecate Codex's external MCP client configuration, connectors, or native
Desktop task/thread tools.
Use only a callable exposed by the current runtime, validate its target and
response at the call site, and preserve the same CLI fallback. The
Desktop Runtime Wrapper V1 is retired and provides no runnable or importable
integration path. Current behavior is owned by the
[Native Runtime Capability Contract](docs/native-runtime-capabilities.md) and
the documented active runtime callable; validate each action's authority,
target, and response at the call site. The [V1 retirement record](docs/desktop-runtime-wrapper-v1-deprecation.md)
and [historical plan](docs/desktop-runtime-wrapper-v1-plan.md) are
non-executable context only.

After an authorized Desktop `create_thread`, emit the current runtime's
created-task UI directive with the returned ready `threadId` or queued
`clientThreadId`. Keep dispatch, UI registration, exact-ID registry
observation, explicit navigation, sidebar visibility, and repository completion
separate. A stale sidebar is not authority to create a duplicate task, and
pinning changes placement rather than registration.

Choose the Desktop action from the handoff intent: use a same-directory
`fork_thread` for the same task, completed history, and existing
checkout/worktree; use a worktree `fork_thread` for the same task and completed
history when a newly isolated checkout is required; for a fresh task use
`create_thread` with the exact project
ID and a concise non-empty safe `title`. Use only approved nonsensitive task
metadata and preview the exact title; never copy prompt text or sensitive
details, and use the fixed `Project task` fallback when safety is uncertain. A
Git project defaults to `worktree`; use `local` only when the user explicitly
requests the saved project checkout.
Non-Git projects default to `local`, and `projectless` remains limited to
intentional non-project work. In a worktree, run repository verification
through its tracked environment resolver (this repository uses
`./scripts/project-python`) or stop when the pinned environment is unavailable.
Omit worktree `startingState` for the project default branch. Use
`working-tree` only for an explicitly requested current checkout including
uncommitted changes; a branch state requires the exact requested `branchName`,
and `create-branch` is allowed only for that exact explicitly requested new
name.

When the user explicitly requests a thread share, the Desktop adapter may use
the exposed `share_thread` callable only after previewing the exact thread,
deriving the account/workspace audience from public product context, and asking
the user to confirm review of the complete thread for sensitive material.
Recent, truncated, or paginated reads are insufficient by themselves. The link
is an immutable read-only snapshot and does not follow later
thread changes. Link creation, delivery, revocation through ChatGPT data
controls, and repository completion are separate states; the adapter must not
claim automatic rollback when the callable exposes creation only.

## Runtime Compatibility

| Label | Meaning |
| --- | --- |
| `shared` | Works in Codex CLI and Codex Desktop with ordinary repository files and shell/git inspection. |
| `cli` | Designed primarily for Codex CLI. Desktop may use the same steps manually or through an equivalent thread. |
| `desktop` | Requires Desktop user-owned task, thread, worktree, UI, or scheduling control. |
| `plugin-dependent` | Requires an installed plugin, connector, or platform tool. The skill must name the dependency. |

The canonical Code Mode batching and concurrency contract is
[Code Mode Tool Orchestration Policy](policies/code-mode-tool-orchestration-policy.md).
Relevant skills reference that single source; filesystem installation places it
at
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`.

## Skills

| Skill | Runtime | Purpose |
| --- | --- | --- |
| `loop-engineering` | shared | Explicit loop entrypoint for clear bounded objectives; routes through planning, implementation, verification, review, continuation, handoff, and gates until complete or stopped. |
| `cli-session-handoff` | cli | Start, resume, fork, or clean non-interactive fresh-continue one authorized bounded CLI session, or prepare one exact manual interactive fork, after shared orchestration selects the handoff. |
| `planning` | shared | Produce scoped implementation plans with assumptions, risks, DoD, and verification. |
| `milestone-continuation` | shared | Continue a bounded milestone across repeated invocations by checking task completion, choosing the next ready task, and stopping at human gates. |
| `project-delivery` | shared | Carry a bounded delivery objective through discovery, plan, implementation, review, docs sync, and PR readiness or the next human gate. |
| `project-orchestrator` | shared | Route bounded work across planning, implementation, review, continuation, handoff, or human gates. |
| `implementation-slice` | shared | Implement a bounded change after read-only inspection, then verify and inspect the diff. |
| `docs-update` | shared | Update user or project docs from code, specs, and verified behavior. |
| `code-review` | shared | Normal user-facing entry point for routine read-only review of code or mixed diffs. |
| `code-review-deep` | shared | Higher-scrutiny review for security, packaging, data, migration, or cross-module risk. |
| `docs-review` | shared | Normal user-facing entry point for read-only review of docs-only or docs-dominant changes. |
| `merge-review` | shared | Normal user-facing entry point for base-to-head merge quality and DoD review evidence. |
| `merge-review-deep` | shared | Higher-scrutiny merge review evidence for high-risk, release-sensitive, or policy-required changes. |
| `code-review-gate` | shared | Thin formal gate adapter that routes to `code-review` or `code-review-deep` before commit, PR, or merge readiness. |
| `docs-review-gate` | shared | Thin formal gate adapter around `docs-review` before commit, PR, or merge readiness. |
| `merge-readiness-gate` | shared | Thin formal branch readiness evidence-and-decision layer before PR handoff, merge readiness, or final human approval. |
| `review-artifact-cleanup` | shared | Dry-run first cleanup workflow for review artifacts. |
| `closure-triage` | shared | Select the next smallest safe packet from repo policy, project overlays, and current state. |
| `task-continuation` | shared | Select the next safe task and prepare a continuation prompt or task brief from durable project context. |
| `desktop-project-delivery` | desktop | Thin Desktop UX adapter over shared project delivery. |
| `desktop-thread-delegation` | desktop | Control a user-authorized Desktop task/thread/worktree handoff selected by shared orchestration. |
| `desktop-spec-plan-gate` | desktop | Deprecated compatibility alias; new workflows use shared `planning`. |
| `desktop-implementation-gate` | desktop | Deprecated compatibility alias; new workflows use shared review primitives and formal gates. |
| `desktop-pr-merge-gate` | desktop | Deprecated compatibility alias; new workflows use shared `merge-readiness-gate`. |

## Workflows

- `workflows/loop-engineering-workflow.md`
- `workflows/implementation-workflow.md`
- `workflows/review-workflow.md`
- `workflows/merge-readiness-workflow.md`
- `workflows/desktop-delivery-workflow.md`

Shared orchestration templates include loop engineering specs, repo-owned loop state ledgers, loop iteration reports, loop handoff prompts, task claim/lease templates, task briefs, task manifests, next-session prompt templates, current task summaries, project specs, implementation plans, closure triage overlays, task continuation reports, integration review reports, and orchestrator gate reports.

## Examples

- [Basic implementation](examples/basic-implementation.md)
- [Code review](examples/code-review.md)
- [Docs review](examples/docs-review.md)
- [Loop engineering](examples/loop-engineering.md)
- [Orchestrated review closure](examples/orchestrated-review-closure.md)
- [Multi-step maintenance](examples/multi-step-maintenance.md)
- [Milestone continuation](examples/milestone-continuation.md)
- [Task continuation](examples/task-continuation.md)
- [CLI session handoff](examples/cli-session-handoff.md)
- [Desktop thread delegation](examples/desktop-thread-delegation.md)
- [Runtime adapter boundary](examples/runtime-adapter-boundary.md)
- [Language verification](examples/language-verification.md)
- [GitHub workflow guidance](examples/github-workflow-guidance.md)
- [Merge review and readiness](examples/merge-review.md)
- [Desktop project delivery](examples/desktop-project-delivery.md)

See `docs/roadmap.md` for the near-term public roadmap.
The release-notes file derived from the source/package version is candidate
preparation only. GitHub tag and Release metadata provide publication truth.
`docs/release-notes-v0.18.2.md` and `docs/release-notes-v0.18.1.md` are
preserved as point-in-time candidate records;
`docs/release-notes-v0.18.0.md`, `docs/release-notes-v0.17.1.md`, `docs/release-notes-v0.17.0.md`, `docs/release-notes-v0.16.3.md`, `docs/release-notes-v0.16.2.md`, `docs/release-notes-v0.16.0.md`, `docs/release-notes-v0.15.1.md`, and `docs/release-notes-v0.15.0.md` record published releases;
`docs/release-notes-v0.14.2.md`, `docs/release-notes-v0.14.1.md`, `docs/release-notes-v0.14.0.md`, `docs/release-notes-v0.13.0.md`, `docs/release-notes-v0.12.1.md`,
`docs/release-notes-v0.12.0.md`, and
`docs/release-notes-v0.1.0.md` remain historical point-in-time records.

## Installation

Choose exactly one distribution path for a Codex profile.

### Universal plugin

The repo-scoped marketplace at `.agents/plugins/marketplace.json` points to the
narrow generated package at `plugin/codex-dev-skills/`, not the checkout root.
That package contains only the manifest, tracked skills, and allowlisted shared
policy/template/runtime-contract resources. Canonical sources remain under the
top-level `skills/`, `policies/`, `templates/`, and `docs/` trees; run
`./scripts/project-python scripts/sync-plugin-package.py --write` after changing
packaged sources and verify parity without `--write`. This prevents ignored or
untracked checkout state from entering the Codex plugin cache: verification
rejects every extra file, directory, symlink, or special entry anywhere under
the package root, in addition to checking canonical bytes and file modes. In
the ChatGPT desktop app, use the repository marketplace source.
In Codex CLI, configure this checked-out marketplace and install the plugin:

```bash
codex plugin marketplace add .
codex plugin add codex-dev-skills@codex-dev-skills-local
codex plugin list --json
```

Start a new chat/session after installation. Do not also run the filesystem
installer for the same profile. `/plugins` is the interactive CLI browser;
plugin installation remains runtime configuration and does not expand workflow
authority.

### Filesystem installer

Use the Codex-only installer:

```bash
./install.sh list
./install.sh install shared-review-gates
./install.sh install codex-review-workflow
./install.sh install codex-delivery-workflow
./install.sh install codex-cli-session-handoff
```

`./install.sh install --all` installs every group, including Desktop-only workflows. Use it only when you want the Desktop group installed too.

For practical installer troubleshooting across install, diff, update, and uninstall flows, see [docs/troubleshooting.md](docs/troubleshooting.md).

Install only shared review gates:

```bash
./install.sh install shared-review-gates
```

Install CLI-compatible review workflows:

```bash
./install.sh install codex-review-workflow
```

Install CLI-compatible loop and delivery workflows:

```bash
./install.sh install codex-delivery-workflow
```

Install the CLI-only live session handoff adapter:

```bash
./install.sh install codex-cli-session-handoff
```

The installed Loop Engineering YAML CLI has one explicit Python dependency.
Install it into the Python environment that will run `loopctl.py`:

```bash
python3 -m pip install -r ~/.agents/skills/loop-engineering/requirements.txt
```

When `CODEX_DEV_SKILLS_TARGET=legacy` is used, replace `~/.agents/skills` with
`~/.codex/skills`. The installer reports this prerequisite but does not
silently modify the user's Python environment. `loopctl.py --help` remains
available before the dependency is installed; YAML commands fail closed with
the same installation instruction.

Install Codex Desktop delivery workflows:

```bash
./install.sh install desktop-delivery-workflow
```

Check installed state and local differences:

```bash
./install.sh status
./install.sh diff shared-review-gates
./install.sh diff --all
```

`./install.sh diff --all` checks every group, including Desktop-only workflows.

Update installed files from this repository:

```bash
./install.sh update shared-review-gates
./install.sh update codex-review-workflow
./install.sh update codex-delivery-workflow
./install.sh update codex-cli-session-handoff
```

`./install.sh update --all` updates every group, including Desktop-only workflows. Use it only when that is intentional.

Uninstall is destructive because it removes installed Codex skills and templates for the selected group. It requires explicit confirmation:

```bash
./install.sh uninstall shared-review-gates --yes
```

Use the same target mode that was used to install the group. For a legacy installation:

```bash
CODEX_DEV_SKILLS_TARGET=legacy ./install.sh uninstall shared-review-gates --yes
```

Installer scope:

- New installations use the documented Codex user-skill discovery location at `~/.agents/skills/<skill>/`.
- Existing legacy installations remain available through `CODEX_DEV_SKILLS_TARGET=legacy`, which targets `~/.codex/skills/<skill>/`; the installer does not silently move or delete either installation.
- Codex templates are installed to `~/.codex/templates/...`.
- Custom `CODEX_SKILLS_DIR` or `CODEX_TEMPLATES_DIR` overrides require `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`.
- The installer refuses symlink target roots and symlink target paths before install, update, diff, or uninstall.
- Install preflight treats byte-identical existing skills/templates as
  idempotent and refuses any differing existing or imported artifact before
  changing an expanded group.
- Install/update uses `codex plugin list --json` when available and refuses a
  detected installed `codex-dev-skills` plugin. If the CLI is unavailable or
  too old to provide JSON plugin state, it warns and retains the filesystem
  fallback; the operator must still use only one distribution path.
- Fresh installs and forced replacements normalize installed skill directories
  to `0700`, regular files to `0600`, and source-executable files to `0700`.
  This applies to custom/project targets too and can remove other local
  accounts' read access. Existing unsafe paths fail closed; the installer does
  not silently repair them with `chmod`.
- Installer state is stored under `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it.
- State records only non-sensitive metadata such as repository name, version, action, group, and timestamp.
- The installer never overwrites `~/.codex/AGENTS.md`.

Use only one skill installation target for this pack in a given Codex profile.
Installing the same skill names into both `~/.codex/skills` and
`~/.agents/skills`, importing another copy, or activating the universal plugin
beside a filesystem install can produce duplicate selectors. The installer
does not remove, migrate, or rewrite imported/plugin state automatically.

## Verification

Run the repository hygiene check before proposing a release or PR:

```bash
# The resolver fails closed unless the tracked .python-version is honored.
./scripts/project-python --version
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/validate-repo.sh
```

This validates catalog/release consistency, required skill metadata, runtime
labels, symlink safety, structured loop YAML, event/transition behavior,
workflow eval thresholds, the maintained focused unit groups, and public
hygiene checks. The zero-argument command remains backward compatible and
includes all direct eval acceptance scripts.

When a full unittest discovery pass is also required, avoid rerunning the
validator's focused unit groups:

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
```

`--skip-unit-tests` omits only the embedded unit-test groups; hygiene,
catalog/installer/version consistency, plugin parity, validators, and direct
eval acceptance checks still run. It is the CI orchestration mode, not a
weaker structural check. Unknown, duplicate, extra, and positional arguments
fail before validation begins. Ordinary documentation or contract changes may
use focused tests plus this checks-only orchestration and rely on exact-head CI
for full discovery. Runtime, installer, security, and release-sensitive
changes should run the checks-only orchestration and one full discovery pass
both locally and in exact-head CI.

PyYAML is the only Python runtime dependency and is required by the structured
ledger commands.
The repository pins Python 3.12.9 with `.python-version`.
`scripts/project-python` selects `CODEX_PROJECT_PYTHON`, a repository `.venv`,
`pyenv`, or an already-correct `python3`, in that order, and rejects a version
mismatch. This makes saved checkouts, Desktop worktrees, CLI disposable clones,
and CI use the same interpreter contract. If the PyYAML preflight fails, inspect
the selected project environment before installing anything. Never copy a
`.venv` into a worktree or install through a different interpreter; only after
confirming the resolved environment genuinely lacks the dependency, use
`./scripts/project-python -m pip install -r requirements.txt`.

For tag, release notes, and PR readiness checks, see [docs/release-readiness.md](docs/release-readiness.md).

## Included Scope

This repository includes public software development workflows for:

- planning and implementation
- loop engineering for bounded objectives
- backend-neutral external memory validation and conformance without a backend
- docs updates and docs review
- code review and deep code review
- orchestrated review closure and formal review gates
- merge readiness gates
- delegated delivery
- Codex Desktop orchestration
- shared CLI/Desktop policies and templates

## Excluded Scope

This repository intentionally does not include:

- legacy non-Codex workflows
- presentation or PPTX workflows
- unverified frontend UI workflow packs
- knowledge, Obsidian, or vault capture workflows
- private runtime state, local application state, logs, local databases, machine-specific config, credentials, or private paths

## Contribution Guidelines

Contributions should keep the repository public, runtime-compatible, and low-surprise:

- keep skill names clear to external users
- mark runtime compatibility in every skill and README table
- keep review mode read-only unless the user explicitly asks to fix
- avoid private paths, local runtime files, credentials, and machine-specific assumptions
- separate facts from inference
- include verification steps for workflow changes

## Safety And Privacy

Never add credentials, private keys, local runtime files, logs, local databases, app state, or machine-specific config. When a workflow discusses sensitive data, keep examples generic and never include real values.
