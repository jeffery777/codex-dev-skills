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

The current development milestone is Loop Engineering V2b: V1 remains the
production workflow/authority core, V2a adds heterogeneous subagent routing,
and V2b adds a backend-neutral external memory safety contract. External memory
is optional advisory/cache/coordination input and never replaces repository,
Git, verification, review, protected authorization, accepted platform state,
or completion truth. No production memory backend is included.

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

Loop Engineering V2a custom-agent profiles are a separate opt-in because they
write local runtime configuration. Inspect the inventory and mapping metadata,
then install only when wanted:

```bash
./install.sh manifest | rg codex-agent-profiles
sed -n '1,240p' skills/loop-engineering/references/agent-profile-registry.json
python3 scripts/validate-agent-profiles.py
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
python3 scripts/validate-agent-profiles.py preflight \
  --role loop_v2a_balanced_worker \
  --runtime-facts /path/to/runtime-facts.json \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents
./install.sh install codex-agent-profiles
```

For project-scoped adoption, scan the project destination and the user layer,
then install with the same explicit target:

```bash
python3 scripts/validate-agent-profiles.py preflight \
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
seven profile destinations before changing any dependency skill, template, or
profile. Dependency installation retains the existing installer sync behavior;
the all-profile preflight prevents a profile collision from causing a partial
expanded-group update. It also protects profile paths from overwrite, symlink
traversal, and partial group mutation. After install, validate the
deployed directory and identify it explicitly
so byte-identical expected instances are distinguished from modified or
cross-root collisions:

```bash
python3 ~/.codex/skills/loop-engineering/scripts/profile_preflight.py \
  --profile-dir ~/.codex/agents \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents
python3 ~/.codex/skills/loop-engineering/scripts/profile_preflight.py preflight \
  --profile-dir ~/.codex/agents \
  --destination-root ~/.codex/agents \
  --agent-root .codex/agents \
  --role loop_v2a_balanced_worker \
  --runtime-facts /path/to/runtime-facts.json
```

When `CODEX_DEV_SKILLS_TARGET=agents` selected the alternative skill root,
replace `~/.codex/skills` above with `~/.agents/skills`. A non-empty
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
low for exploration, Terra medium for routine implementation, Sol medium for
advanced bounded implementation, Sol high for deep/security review, and Sol
xhigh for narrowly selected exceptional research. Exact model and reasoning
availability remains current-session runtime evidence. Selection uses the
lowest sufficient same-class tier, never alphabetical profile order, and never
allows a lower tier to satisfy a higher-tier route silently.

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
local edits before retrying. A forced update writes each replaced profile to
the adjacent `<profile>.toml.bak` first and refuses the whole profile update
before mutation if a required backup already exists. To restore, stop using the
new profile, review the `.bak`, move it back to the original `.toml` path, and
rerun profile validation. Remove backups only after confirming the intended
configuration. Removing the profiles leaves V1 shared/sequential semantics
available.

`codex-review-workflow` and `codex-delivery-workflow` install their shared review gate dependencies automatically. Install `shared-review-gates` directly only when you want the formal gate adapters and orchestration templates without the review primitives.

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

`loop-engineering` is a thin entrypoint over the existing phase skills. It should classify the current state, route to the smallest suitable workflow, verify evidence, and stop at human gates. It does not replace focused implementation, review primitives, formal gates, milestone continuation, task continuation, shared subagents, or Desktop user-owned task/thread/worktree controls.

If `project-orchestrator` receives a single clear implementation task, it should route to `implementation-slice` semantics and avoid unnecessary project-level planning.

For automated review closure, let `project-orchestrator` or `project-delivery` compose the primitive shared workflows dynamically. A user or repo policy may set the maximum number of review/fix rounds; the default is 2.

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
python3 skills/loop-engineering/scripts/memoryctl.py --help
python3 skills/loop-engineering/scripts/memoryctl.py validate <document.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-retrieval <decision.json> \
  --trusted-conformance-receipts <current-session-trusted-receipts.json> \
  --trusted-source-digests <current-repository-source-digests.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-write <candidate.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 skills/loop-engineering/scripts/memoryctl.py conformance <transcript.json> \
  --trusted-source-digests <current-repository-source-digests.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 scripts/eval-memory-contract.py
```

The caller-owned JSON inputs use exact shapes: trusted conformance receipts are
`{"<adapter-id>":{"receipt_digest":"<sha256>","adapter_fingerprint":"<sha256>"}}`;
trusted sources are `{"<repository-relative-path>":"<sha256>"}`; trusted
acceptance evidence is `{"receipt_digests":["<sha256>"]}`. These files are
control-plane evidence and must not be copied from the adapter transcript.

With no adapter, or with an unavailable, partial, unsupported, incompatible, or
untrusted adapter, the loop safely continues with V1/V2a and no memory. See the
[external memory contract](docs/external-memory-contract.md).

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
   a complete tracked snapshot, and strict version-gated metadata. Treat stale,
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

The supported operator entrypoint is the repo-owned module. It persists no
configuration and redacts machine-local paths from JSON output:

```bash
ADAPTER=skills/loop-engineering/scripts/gitnexus_adapter.py
python3 "$ADAPTER" qualify \
  --executable "$GITNEXUS_EXECUTABLE" --allow-symlink \
  --node-executable "$GITNEXUS_NODE_EXECUTABLE" --allow-node-symlink \
  --package-root "$GITNEXUS_PACKAGE_ROOT" \
  --accepted-executable-sha256 "$GITNEXUS_EXECUTABLE_SHA256" \
  --accepted-runtime-sha256 "$GITNEXUS_NODE_SHA256" \
  --accepted-package-sha256 "$GITNEXUS_PACKAGE_SHA256"

python3 "$ADAPTER" status \
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
python3 "$ADAPTER" refresh \
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

python3 "$ADAPTER" disable
```

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
- `PostToolUse` for `Bash` rechecks live Git state after shell activity and
  reports a commit/HEAD change without parsing or trusting the shell command.

The Bash hook is not complete interception. A Git mutation performed through an
uncovered tool, another process, or another client may not trigger it;
`SessionStart` is the compensating check. Notify-only mode is the default. In
auto-on-demand mode, a clean stale or missing index may be refreshed only
through `RefreshController` with exact expected HEAD and all V2c-A checks.
Dirty worktrees, identity conflicts, corrupt metadata, failed qualification,
and unsafe paths remain notification-only or fail safe.

The installer copies inactive examples to
`~/.codex/templates/hooks/gitnexus-v2c-b/`; it does not create or enable a
project hook. Review these sources before materializing machine-local values:

```bash
HOOK_RUNNER=skills/loop-engineering/scripts/gitnexus_hook.py
HOOK_TEMPLATE=templates/hooks/gitnexus-v2c-b/hooks.json.template
CONFIG_TEMPLATE=templates/hooks/gitnexus-v2c-b/config.json.template

python3 "$HOOK_RUNNER" \
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
Linux coverage is fixture-based portability evidence, not a live qualification.

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

Use `merge-readiness-gate` only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval:

```text
Use merge-readiness-gate for main..HEAD.
Check the plan, diff, tests, and review evidence. Report READY, BLOCKED, or NEEDS HUMAN DECISION. Do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

The gate is a thin adapter and evidence-and-decision layer: it summarizes verification, review evidence, blocking decisions, residual risk, and the human approval boundary. It is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.

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
[Codex runtime compatibility evidence (2026-07-21)](docs/codex-runtime-compatibility-evidence-2026-07-21.md).
Use only a callable exposed by the current runtime, validate its target and
response at the call site, and preserve the same CLI fallback. The
`desktop_runtime_*` scripts and [historical V1 plan](docs/desktop-runtime-wrapper-v1-plan.md)
remain regression and migration evidence only; active Loop Engineering skills
must not import, execute, or recommend them.

## Runtime Compatibility

| Label | Meaning |
| --- | --- |
| `shared` | Works in Codex CLI and Codex Desktop with ordinary repository files and shell/git inspection. |
| `cli` | Designed primarily for Codex CLI. Desktop may use the same steps manually or through an equivalent thread. |
| `desktop` | Requires Desktop user-owned task, thread, worktree, UI, or scheduling control. |
| `plugin-dependent` | Requires an installed plugin, connector, or platform tool. The skill must name the dependency. |

## Skills

| Skill | Runtime | Purpose |
| --- | --- | --- |
| `loop-engineering` | shared | Explicit loop entrypoint for clear bounded objectives; routes through planning, implementation, verification, review, continuation, handoff, and gates until complete or stopped. |
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
| `desktop-spec-plan-gate` | desktop | Desktop gate for spec, plan, and DoD drafts. |
| `desktop-implementation-gate` | desktop | Desktop formal integration gate for worker outputs before commit readiness. |
| `desktop-pr-merge-gate` | desktop | Desktop PR and merge readiness gate that summarizes evidence without publishing or merging. |

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
- [Desktop thread delegation](examples/desktop-thread-delegation.md)
- [Runtime adapter boundary](examples/runtime-adapter-boundary.md)
- [Language verification](examples/language-verification.md)
- [GitHub workflow guidance](examples/github-workflow-guidance.md)
- [Merge review and readiness](examples/merge-review.md)
- [Desktop project delivery](examples/desktop-project-delivery.md)

See `docs/roadmap.md` for the near-term public roadmap, `docs/release-notes-v0.9.0.md` for the current v0.9.0 release notes, and `docs/release-notes-v0.1.0.md` for the historical v0.1.0 release notes.

## Installation

Use the Codex-only installer:

```bash
./install.sh list
./install.sh install shared-review-gates
./install.sh install codex-review-workflow
./install.sh install codex-delivery-workflow
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

The installed Loop Engineering YAML CLI has one explicit Python dependency.
Install it into the Python environment that will run `loopctl.py`:

```bash
python3 -m pip install -r ~/.codex/skills/loop-engineering/requirements.txt
```

When `CODEX_DEV_SKILLS_TARGET=agents` is used, replace `~/.codex/skills` with
`~/.agents/skills`. The installer reports this prerequisite but does not
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
```

`./install.sh update --all` updates every group, including Desktop-only workflows. Use it only when that is intentional.

Uninstall is destructive because it removes installed Codex skills and templates for the selected group. It requires explicit confirmation:

```bash
./install.sh uninstall shared-review-gates --yes
```

Installer scope:

- Codex skills are installed to `~/.codex/skills/<skill>/` by default to preserve existing installations.
- To opt in to the current Codex user-skill discovery location, run installer commands with `CODEX_DEV_SKILLS_TARGET=agents`; this installs skills to `~/.agents/skills/<skill>/`.
- Codex templates are installed to `~/.codex/templates/...`.
- Custom `CODEX_SKILLS_DIR` or `CODEX_TEMPLATES_DIR` overrides require `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`.
- The installer refuses symlink target roots and symlink target paths before install, update, diff, or uninstall.
- Installer state is stored under `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it.
- State records only non-sensitive metadata such as repository name, version, action, group, and timestamp.
- The installer never overwrites `~/.codex/AGENTS.md`.

Use only one skill installation target for this pack in a given Codex profile. Installing the same skill names into both `~/.codex/skills` and `~/.agents/skills`, or later through a plugin package, can make duplicate skills appear in selectors.

Plugin packaging is intentionally not added by the local installer. If this pack later ships a `.codex-plugin/plugin.json` and repo marketplace entry, treat that as a separate distribution path and avoid installing the same skill names through both the plugin and the filesystem installer.

## Verification

Run the repository hygiene check before proposing a release or PR:

```bash
python3 --version
python3 -m pip install -r requirements.txt
./scripts/validate-repo.sh
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-memory-contract.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

This validates catalog/release consistency, required skill metadata, runtime
labels, symlink safety, structured loop YAML, event/transition behavior,
workflow eval thresholds, and public hygiene checks. PyYAML is the only Python
runtime dependency and is required by the structured ledger commands.
The repository pins Python 3.12.9 with `.python-version`; confirm the active
runtime before installing dependencies.

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
